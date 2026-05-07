"""Parser + executor de Workflow YAMLs.

Suporta pipelines lineares com 4 kinds de step: image, video, upscale, human_pick.
Steps human_pick PAUSAM a Run e persistem state. Resume com user input.

Não suporta branching/condicionais — composição complexa = Claude orquestrando
múltiplas Workflows conversacionalmente.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .asset_store import AssetStore
from .fal_client import FalClient
from .models_registry import ModelsRegistry
from .tracker import Tracker


class WorkflowError(RuntimeError):
    pass


class WorkflowPaused(Exception):
    """Sinaliza que a Run pausou em um human_pick. State já persistido."""

    def __init__(self, run_id: int, step_id: str, prompt_to_user: str, options: list[str]):
        self.run_id = run_id
        self.step_id = step_id
        self.prompt_to_user = prompt_to_user
        self.options = options
        super().__init__(f"Run {run_id} pausada no step '{step_id}'")


@dataclass
class WorkflowSpec:
    schema: str
    slug: str
    name: str
    description: str
    inputs: dict[str, dict[str, Any]]
    steps: list[dict[str, Any]]
    finalize: dict[str, Any] = field(default_factory=dict)
    source_session_id: int | None = None

    @classmethod
    def from_yaml(cls, path: Path) -> "WorkflowSpec":
        data = yaml.safe_load(path.read_text())
        if not data.get("schema", "").startswith("studiolocal/workflow/"):
            raise WorkflowError(f"Schema inválido em {path}")
        return cls(
            schema=data["schema"],
            slug=data["slug"],
            name=data["name"],
            description=data.get("description", ""),
            inputs=data.get("inputs", {}),
            steps=data.get("steps", []),
            finalize=data.get("finalize", {}),
            source_session_id=data.get("created_from_session"),
        )


_INTERP = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")


def _interpolate(value: Any, ctx: dict[str, Any]) -> Any:
    """Substitui {{ a.b.c }} dentro de strings (recursivo em dicts/lists)."""
    if isinstance(value, str):
        def _resolve(match: re.Match) -> str:
            path = match.group(1).split(".")
            cur: Any = ctx
            for p in path:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    return ""
            return "" if cur is None else str(cur)

        replaced = _INTERP.sub(_resolve, value)
        # se a string inteira era apenas a interpolação, devolve o valor cru
        m = _INTERP.fullmatch(value.strip())
        if m:
            path = m.group(1).split(".")
            cur: Any = ctx
            for p in path:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                else:
                    return None
            return cur
        return replaced
    if isinstance(value, dict):
        return {k: _interpolate(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate(v, ctx) for v in value]
    return value


@dataclass
class StepResult:
    step_id: str
    outputs: dict[str, Any]
    cost_brl: float = 0.0


class WorkflowRunner:
    def __init__(
        self,
        tracker: Tracker,
        registry: ModelsRegistry,
        fal: FalClient,
        store: AssetStore,
    ):
        self.tracker = tracker
        self.registry = registry
        self.fal = fal
        self.store = store

    # --- entry points ---------------------------------------------------------

    def start(
        self,
        workflow: WorkflowSpec,
        project_id: int,
        project_slug: str,
        session_id: int | None,
        inputs: dict[str, Any],
        workflow_id: int,
    ) -> int:
        run_id = self.tracker.create_run(workflow_id, project_id, session_id, inputs)
        try:
            self._execute(workflow, run_id, project_id, project_slug, session_id, inputs, state=None)
        except WorkflowPaused:
            raise
        return run_id

    def resume(
        self,
        workflow: WorkflowSpec,
        run_id: int,
        project_id: int,
        project_slug: str,
        session_id: int | None,
        user_input: dict[str, Any],
    ) -> None:
        row = self.tracker.query("SELECT * FROM runs WHERE id = ?", (run_id,))[0]
        state = json.loads(row["state"] or "{}")
        inputs = json.loads(row["inputs"] or "{}")
        # injeta user_input no step pendente
        pending_step = state.get("pending_step")
        if not pending_step:
            raise WorkflowError(f"Run {run_id} não está pausada")
        state["step_outputs"][pending_step] = user_input
        state["pending_step"] = None
        self._execute(
            workflow, run_id, project_id, project_slug, session_id, inputs, state
        )

    # --- core execution -------------------------------------------------------

    def _execute(
        self,
        workflow: WorkflowSpec,
        run_id: int,
        project_id: int,
        project_slug: str,
        session_id: int | None,
        inputs: dict[str, Any],
        state: dict[str, Any] | None,
    ) -> None:
        state = state or {"step_outputs": {}, "pending_step": None, "cost_total": 0.0}

        for idx, step in enumerate(workflow.steps):
            step_id = step["id"]
            if step_id in state["step_outputs"]:
                continue  # já executado

            ctx = {"inputs": inputs, "steps": state["step_outputs"]}

            if step["kind"] == "human_pick":
                # persiste pausa, levanta exceção
                state["pending_step"] = step_id
                self.tracker.update_run(run_id, status="paused", state=state)
                prompt = _interpolate(step.get("prompt_to_user", "Escolha"), ctx)
                from_list = _interpolate(step.get("from"), ctx) or []
                raise WorkflowPaused(run_id, step_id, str(prompt), list(from_list))

            params = _interpolate(step.get("params", {}), ctx)
            try:
                result = self._run_step(step, params, project_id, project_slug, session_id, run_id, idx)
            except Exception as e:
                self.tracker.update_run(
                    run_id, status="failed", state=state, finished=True
                )
                raise WorkflowError(f"Step '{step_id}' falhou: {e}") from e

            state["step_outputs"][step_id] = result.outputs
            state["cost_total"] = round(state["cost_total"] + result.cost_brl, 2)
            self.tracker.update_run(
                run_id, cost_brl=state["cost_total"], state=state
            )

        # finalize
        self._finalize(workflow, project_slug, state)
        self.tracker.update_run(run_id, status="done", finished=True)

    def _run_step(
        self,
        step: dict[str, Any],
        params: dict[str, Any],
        project_id: int,
        project_slug: str,
        session_id: int | None,
        run_id: int,
        step_index: int,
    ) -> StepResult:
        kind = step["kind"]
        model = step["model"]
        prompt = params.get("prompt") or params.get("input_image") or ""
        gen_id = self.tracker.create_generation(
            project_id=project_id,
            session_id=session_id or 0,
            model=model,
            kind=kind if kind != "upscale" else "upscale",
            prompt=str(prompt) if prompt else None,
            params=params,
            run_id=run_id,
            step_index=step_index,
        )

        try:
            fal_result = self.fal.call(model, params)
        except Exception as e:
            self.tracker.finish_generation(gen_id, status="failed", error=str(e))
            raise

        cost = self.registry.estimate_cost(model, params)
        # download e cria assets
        draft_dir = self.store.new_draft_dir(project_slug, topic_hint=step["id"])
        asset_ids: list[int] = []
        ext_map = {"image": "png", "video": "mp4", "upscale": "png"}
        ext = ext_map.get(kind, "bin")
        for i, url in enumerate(fal_result.output_urls):
            file_path = draft_dir / f"{i + 1:02d}.{ext}"
            size = FalClient.download(url, file_path)
            kind_for_asset = "video" if kind == "video" else "image"
            asset_id = self.tracker.create_asset(
                generation_id=gen_id,
                project_id=project_id,
                kind=kind_for_asset,
                file_path=self.store.relpath(file_path),
                bytes_size=size,
            )
            asset_ids.append(asset_id)

        self.tracker.finish_generation(
            gen_id, status="done", cost_brl=cost, fal_request_id=fal_result.request_id
        )

        outputs_decl = step.get("outputs", {}) or {}
        outputs: dict[str, Any] = {}
        # decl tipo "assets: candidates.assets" — mapeamos primary
        for key in outputs_decl:
            if kind == "image" and key in ("assets", "asset"):
                outputs[key] = asset_ids if key == "assets" else asset_ids[0]
            elif kind in ("video", "upscale") and key in ("asset", "assets"):
                outputs[key] = asset_ids[0] if key == "asset" else asset_ids
        if not outputs:
            outputs = {"assets": asset_ids, "asset": asset_ids[0] if asset_ids else None}
        return StepResult(step_id=step["id"], outputs=outputs, cost_brl=cost)

    def _finalize(
        self, workflow: WorkflowSpec, project_slug: str, state: dict[str, Any]
    ) -> None:
        promote_list = workflow.finalize.get("promote_to_library", []) or []
        ctx = {"steps": state["step_outputs"]}
        for ref in promote_list:
            asset_id = _interpolate(ref, ctx)
            if isinstance(asset_id, int):
                row = self.tracker.query(
                    "SELECT * FROM assets WHERE id = ?", (asset_id,)
                )
                if row:
                    src = self.store.root / row[0]["file_path"]
                    if src.exists():
                        new = self.store.promote(src, project_slug)
                        self.tracker.promote_asset(asset_id, self.store.relpath(new))
