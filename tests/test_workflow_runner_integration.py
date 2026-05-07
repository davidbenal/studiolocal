"""Testes de integração do WorkflowRunner.

Cobre o fluxo completo de execução com Fal mockado:
- pipeline simples (1 step image)
- pipeline com human_pick (start pausa, resume continua)
- finalize.promote_to_library
- falha em step (rollback de state)
- referência cruzada entre steps via {{ steps.X.Y }}
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from lib.asset_store import AssetStore
from lib.fal_client import FalClient, FalError, FalResult
from lib.models_registry import ModelsRegistry
from lib.tracker import Tracker
from lib.workflow_runner import (
    WorkflowError,
    WorkflowPaused,
    WorkflowRunner,
    WorkflowSpec,
)


# --- Fakes -------------------------------------------------------------------


class FakeFalClient:
    """Substitui FalClient.call. Retorna URLs determinísticas por modelo+chamada."""

    def __init__(self):
        self.calls: list[dict] = []

    def call(self, model_name: str, params: dict) -> FalResult:
        self.calls.append({"model": model_name, "params": params})
        n = int(params.get("num_outputs", 1))
        idx = len(self.calls)
        urls = [f"https://fake.fal.ai/{model_name}/{idx}/{i}.bin" for i in range(n)]
        return FalResult(
            request_id=f"req-{idx}",
            output_urls=urls,
            raw_response={"model": model_name},
            elapsed_s=0.01,
        )


def _fake_download(url: str, dest: Path) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"fake-binary-content")
    return len(b"fake-binary-content")


# --- Fixtures ----------------------------------------------------------------


@pytest.fixture
def setup(tmp_path: Path, monkeypatch):
    """Monta um runner com FS tmp + tracker tmp + Fal mockado."""
    monkeypatch.setattr(FalClient, "download", staticmethod(_fake_download))

    tracker = Tracker(tmp_path / "tracker.db")
    tracker.apply_migrations()
    store = AssetStore(tmp_path)
    registry = ModelsRegistry()
    fal = FakeFalClient()
    runner = WorkflowRunner(tracker, registry, fal, store)

    project_id = tracker.create_project("teste-wf", "Teste WF", ["test:wf"], None)
    session_id = tracker.open_session(project_id)
    return {
        "runner": runner,
        "tracker": tracker,
        "store": store,
        "fal": fal,
        "project_id": project_id,
        "project_slug": "teste-wf",
        "session_id": session_id,
        "tmp": tmp_path,
    }


def _write_workflow(tmp_path: Path, content: dict) -> WorkflowSpec:
    p = tmp_path / "wf.yaml"
    p.write_text(yaml.safe_dump(content))
    return WorkflowSpec.from_yaml(p)


# --- Testes ------------------------------------------------------------------


def test_pipeline_simples_um_step_image(setup):
    spec = _write_workflow(
        setup["tmp"],
        {
            "schema": "studiolocal/workflow/v1",
            "slug": "simple",
            "name": "Simple",
            "description": "1 step",
            "inputs": {"prompt": {"type": "string", "required": True}},
            "steps": [
                {
                    "id": "gen",
                    "kind": "image",
                    "model": "nano-banana-pro",
                    "params": {"prompt": "{{ inputs.prompt }}", "num_outputs": 2},
                    "outputs": {"assets": "gen.assets"},
                }
            ],
            "finalize": {"promote_to_library": []},
        },
    )
    wid = setup["tracker"].create_workflow("simple", "Simple", "wf.yaml")

    run_id = setup["runner"].start(
        spec,
        project_id=setup["project_id"],
        project_slug=setup["project_slug"],
        session_id=setup["session_id"],
        inputs={"prompt": "uma garrafa azul"},
        workflow_id=wid,
    )

    # 1 chamada Fal
    assert len(setup["fal"].calls) == 1
    assert setup["fal"].calls[0]["model"] == "nano-banana-pro"
    assert setup["fal"].calls[0]["params"]["prompt"] == "uma garrafa azul"

    # Run done
    run = setup["tracker"].query("SELECT * FROM runs WHERE id = ?", (run_id,))[0]
    assert run["status"] == "done"
    assert run["finished_at"] is not None
    assert run["cost_brl"] > 0

    # 2 assets criados (num_outputs=2)
    assets = setup["tracker"].query(
        "SELECT * FROM assets WHERE project_id = ?", (setup["project_id"],)
    )
    assert len(assets) == 2
    assert all(a["status"] == "draft" for a in assets)
    # Arquivos baixados
    for a in assets:
        assert (setup["store"].root / a["file_path"]).exists()


def test_pipeline_human_pick_pausa_e_persiste_state(setup):
    spec = _write_workflow(
        setup["tmp"],
        {
            "schema": "studiolocal/workflow/v1",
            "slug": "pick",
            "name": "Pick",
            "description": "img+pick+upscale",
            "inputs": {"prompt": {"type": "string", "required": True}},
            "steps": [
                {
                    "id": "candidates",
                    "kind": "image",
                    "model": "nano-banana-pro",
                    "params": {"prompt": "{{ inputs.prompt }}", "num_outputs": 4},
                    "outputs": {"assets": "candidates.assets"},
                },
                {
                    "id": "pick",
                    "kind": "human_pick",
                    "prompt_to_user": "Escolha 1 dos 4",
                    "from": "{{ steps.candidates.assets }}",
                    "outputs": {"selected": "pick.selected"},
                },
                {
                    "id": "upscale",
                    "kind": "upscale",
                    "model": "clarity",
                    "params": {"input_asset": "{{ steps.pick.selected }}", "scale": 2},
                    "outputs": {"asset": "upscale.asset"},
                },
            ],
            "finalize": {"promote_to_library": []},
        },
    )
    wid = setup["tracker"].create_workflow("pick", "Pick", "wf.yaml")

    with pytest.raises(WorkflowPaused) as exc_info:
        setup["runner"].start(
            spec,
            project_id=setup["project_id"],
            project_slug=setup["project_slug"],
            session_id=setup["session_id"],
            inputs={"prompt": "X"},
            workflow_id=wid,
        )

    paused = exc_info.value
    assert paused.step_id == "pick"
    assert "Escolha" in paused.prompt_to_user
    assert len(paused.options) == 4

    # Run em estado "paused" no DB
    run = setup["tracker"].query("SELECT * FROM runs WHERE id = ?", (paused.run_id,))[0]
    assert run["status"] == "paused"
    assert run["finished_at"] is None
    state = json.loads(run["state"])
    assert state["pending_step"] == "pick"
    assert "candidates" in state["step_outputs"]

    # Apenas 1 chamada Fal (candidates), upscale ainda não rodou
    assert len(setup["fal"].calls) == 1


def test_pipeline_resume_apos_human_pick(setup):
    spec = _write_workflow(
        setup["tmp"],
        {
            "schema": "studiolocal/workflow/v1",
            "slug": "resume",
            "name": "Resume",
            "description": "test resume",
            "inputs": {"prompt": {"type": "string", "required": True}},
            "steps": [
                {
                    "id": "candidates",
                    "kind": "image",
                    "model": "nano-banana-pro",
                    "params": {"prompt": "{{ inputs.prompt }}", "num_outputs": 2},
                    "outputs": {"assets": "candidates.assets"},
                },
                {
                    "id": "pick",
                    "kind": "human_pick",
                    "prompt_to_user": "Escolha",
                    "from": "{{ steps.candidates.assets }}",
                    "outputs": {"selected": "pick.selected"},
                },
                {
                    "id": "upscale",
                    "kind": "upscale",
                    "model": "clarity",
                    "params": {"input_asset": "{{ steps.pick.selected }}", "scale": 2},
                    "outputs": {"asset": "upscale.asset"},
                },
            ],
            "finalize": {"promote_to_library": []},
        },
    )
    wid = setup["tracker"].create_workflow("resume", "Resume", "wf.yaml")

    # start → pausa
    with pytest.raises(WorkflowPaused) as exc_info:
        setup["runner"].start(
            spec,
            project_id=setup["project_id"],
            project_slug=setup["project_slug"],
            session_id=setup["session_id"],
            inputs={"prompt": "X"},
            workflow_id=wid,
        )
    run_id = exc_info.value.run_id
    candidate_asset_ids = exc_info.value.options
    assert len(candidate_asset_ids) == 2

    # resume com user input — pega o primeiro asset
    selected_id = candidate_asset_ids[0]
    setup["runner"].resume(
        spec,
        run_id=run_id,
        project_id=setup["project_id"],
        project_slug=setup["project_slug"],
        session_id=setup["session_id"],
        user_input={"selected": selected_id},
    )

    # Run done
    run = setup["tracker"].query("SELECT * FROM runs WHERE id = ?", (run_id,))[0]
    assert run["status"] == "done"
    assert run["finished_at"] is not None

    # 2 chamadas Fal: candidates + upscale (pick não chama Fal)
    assert len(setup["fal"].calls) == 2
    assert setup["fal"].calls[1]["model"] == "clarity"
    # input_asset foi resolvido para o ID selecionado (interpolação devolveu int cru)
    assert setup["fal"].calls[1]["params"]["input_asset"] == selected_id


def test_finalize_promote_to_library_move_e_atualiza_db(setup):
    spec = _write_workflow(
        setup["tmp"],
        {
            "schema": "studiolocal/workflow/v1",
            "slug": "promote",
            "name": "Promote",
            "description": "test finalize",
            "inputs": {},
            "steps": [
                {
                    "id": "gen",
                    "kind": "image",
                    "model": "nano-banana-pro",
                    "params": {"prompt": "X", "num_outputs": 1},
                    "outputs": {"asset": "gen.asset"},
                }
            ],
            "finalize": {"promote_to_library": ["{{ steps.gen.asset }}"]},
        },
    )
    wid = setup["tracker"].create_workflow("promote", "Promote", "wf.yaml")

    setup["runner"].start(
        spec,
        project_id=setup["project_id"],
        project_slug=setup["project_slug"],
        session_id=setup["session_id"],
        inputs={},
        workflow_id=wid,
    )

    assets = setup["tracker"].query(
        "SELECT * FROM assets WHERE project_id = ?", (setup["project_id"],)
    )
    assert len(assets) == 1
    a = assets[0]
    assert a["status"] == "library"
    assert a["promoted_at"] is not None
    # arquivo movido para library/
    assert "library/" in a["file_path"]
    assert (setup["store"].root / a["file_path"]).exists()


def test_falha_em_step_marca_run_failed(setup):
    """Se Fal levanta FalError, runner marca generation/run como failed e propaga."""

    class FailingFal:
        def __init__(self):
            self.calls = []

        def call(self, model, params):
            self.calls.append((model, params))
            raise FalError("Fal indisponível: 503")

    setup["runner"].fal = FailingFal()

    spec = _write_workflow(
        setup["tmp"],
        {
            "schema": "studiolocal/workflow/v1",
            "slug": "fail",
            "name": "Fail",
            "description": "test failure",
            "inputs": {},
            "steps": [
                {
                    "id": "gen",
                    "kind": "image",
                    "model": "nano-banana-pro",
                    "params": {"prompt": "X", "num_outputs": 1},
                    "outputs": {"assets": "gen.assets"},
                }
            ],
            "finalize": {"promote_to_library": []},
        },
    )
    wid = setup["tracker"].create_workflow("fail", "Fail", "wf.yaml")

    with pytest.raises(WorkflowError, match="falhou"):
        setup["runner"].start(
            spec,
            project_id=setup["project_id"],
            project_slug=setup["project_slug"],
            session_id=setup["session_id"],
            inputs={},
            workflow_id=wid,
        )

    # Run com status=failed e finished_at preenchido
    runs = setup["tracker"].query("SELECT * FROM runs ORDER BY id DESC LIMIT 1")
    assert runs[0]["status"] == "failed"
    assert runs[0]["finished_at"] is not None

    # Generation com status=failed e error preenchido
    gens = setup["tracker"].query("SELECT * FROM generations ORDER BY id DESC LIMIT 1")
    assert gens[0]["status"] == "failed"
    assert "503" in gens[0]["error"]


def test_referencia_cruzada_entre_steps_via_interpolacao(setup):
    """Step 2 usa output de step 1 via {{ steps.gen.asset }}."""
    spec = _write_workflow(
        setup["tmp"],
        {
            "schema": "studiolocal/workflow/v1",
            "slug": "chain",
            "name": "Chain",
            "description": "chain steps",
            "inputs": {},
            "steps": [
                {
                    "id": "base",
                    "kind": "image",
                    "model": "nano-banana-pro",
                    "params": {"prompt": "base img", "num_outputs": 1},
                    "outputs": {"asset": "base.asset"},
                },
                {
                    "id": "up",
                    "kind": "upscale",
                    "model": "clarity",
                    "params": {
                        "input_asset": "{{ steps.base.asset }}",
                        "scale": 4,
                    },
                    "outputs": {"asset": "up.asset"},
                },
            ],
            "finalize": {"promote_to_library": []},
        },
    )
    wid = setup["tracker"].create_workflow("chain", "Chain", "wf.yaml")

    setup["runner"].start(
        spec,
        project_id=setup["project_id"],
        project_slug=setup["project_slug"],
        session_id=setup["session_id"],
        inputs={},
        workflow_id=wid,
    )

    assert len(setup["fal"].calls) == 2
    base_call, up_call = setup["fal"].calls
    assert base_call["model"] == "nano-banana-pro"
    assert up_call["model"] == "clarity"

    # Asset_id do upscale param deve ser int (interpolação devolveu valor cru)
    base_assets = setup["tracker"].query(
        "SELECT id FROM assets WHERE generation_id = "
        "(SELECT MIN(id) FROM generations WHERE project_id = ?)",
        (setup["project_id"],),
    )
    assert isinstance(up_call["params"]["input_asset"], int)
    assert up_call["params"]["input_asset"] == base_assets[0]["id"]


def test_custo_total_da_run_acumula(setup):
    spec = _write_workflow(
        setup["tmp"],
        {
            "schema": "studiolocal/workflow/v1",
            "slug": "cost",
            "name": "Cost",
            "description": "test cost",
            "inputs": {},
            "steps": [
                {
                    "id": "img1",
                    "kind": "image",
                    "model": "nano-banana-pro",
                    "params": {"prompt": "X", "num_outputs": 4},
                    "outputs": {"assets": "img1.assets"},
                },
                {
                    "id": "img2",
                    "kind": "image",
                    "model": "nano-banana-2",
                    "params": {"prompt": "Y", "num_outputs": 2},
                    "outputs": {"assets": "img2.assets"},
                },
            ],
            "finalize": {"promote_to_library": []},
        },
    )
    wid = setup["tracker"].create_workflow("cost", "Cost", "wf.yaml")

    run_id = setup["runner"].start(
        spec,
        project_id=setup["project_id"],
        project_slug=setup["project_slug"],
        session_id=setup["session_id"],
        inputs={},
        workflow_id=wid,
    )

    run = setup["tracker"].query("SELECT * FROM runs WHERE id = ?", (run_id,))[0]
    # nano-banana-pro × 4 + nano-banana-2 × 2 = 0.32*4 + 0.08*2 = 1.28 + 0.16 = 1.44
    assert run["cost_brl"] == pytest.approx(1.44, abs=0.01)
