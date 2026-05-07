"""Carrega models.yaml, valida params e calcula custo estimado por chamada."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

MODELS_YAML = Path(__file__).parent.parent / "models.yaml"


@dataclass
class ModelSpec:
    name: str
    kind: str  # image | video | upscale
    fal_endpoint: str
    display_name: str
    cost_brl_per_call: float
    params: dict[str, dict[str, Any]]
    notes: str = ""


class ModelsRegistry:
    def __init__(self, yaml_path: Path | None = None):
        self.yaml_path = yaml_path or MODELS_YAML
        with self.yaml_path.open() as f:
            data = yaml.safe_load(f)
        self._raw = data
        self.models: dict[str, ModelSpec] = {}
        for name, spec in data["models"].items():
            self.models[name] = ModelSpec(
                name=name,
                kind=spec["kind"],
                fal_endpoint=spec["fal_endpoint"],
                display_name=spec["display_name"],
                cost_brl_per_call=float(spec["cost_brl_per_call"]),
                params=spec.get("params", {}),
                notes=spec.get("notes", ""),
            )
        self.defaults: dict[str, str] = data.get("defaults", {})
        self.budget_alerts: dict[str, int] = data.get(
            "budget_alerts", {"warn_at_pct": 80, "block_at_pct": 100}
        )
        self.calibrated_at: str = data.get("calibrated_at", "")

    def get(self, name: str) -> ModelSpec:
        if name not in self.models:
            raise ValueError(
                f"Modelo desconhecido: {name}. Disponíveis: {list(self.models)}"
            )
        return self.models[name]

    def default_for(self, kind: str) -> ModelSpec:
        if kind not in self.defaults:
            raise ValueError(f"Sem default para kind={kind}")
        return self.get(self.defaults[kind])

    def validate_and_normalize(
        self, model_name: str, given: dict[str, Any]
    ) -> dict[str, Any]:
        """Valida params contra spec do modelo. Aplica defaults para campos
        opcionais. Retorna dict pronto para enviar ao fal_client.
        """
        spec = self.get(model_name)
        out: dict[str, Any] = {}

        for pname, pspec in spec.params.items():
            value = given.get(pname)
            ptype = pspec["type"]
            required = pspec.get("required", False)
            default = pspec.get("default")

            if value is None:
                if required:
                    raise ValueError(
                        f"Param obrigatório faltando para {model_name}: {pname}"
                    )
                if default is not None:
                    out[pname] = default
                continue

            # type check leve — confia em chamador para tipos exóticos (asset_ref, file)
            if ptype == "int":
                value = int(value)
                if "min" in pspec and value < pspec["min"]:
                    raise ValueError(f"{pname} < {pspec['min']}")
                if "max" in pspec and value > pspec["max"]:
                    raise ValueError(f"{pname} > {pspec['max']}")
            elif ptype == "float":
                value = float(value)
                if "min" in pspec and value < pspec["min"]:
                    raise ValueError(f"{pname} < {pspec['min']}")
                if "max" in pspec and value > pspec["max"]:
                    raise ValueError(f"{pname} > {pspec['max']}")
            elif ptype == "enum":
                allowed = pspec["values"]
                if value not in allowed:
                    raise ValueError(
                        f"{pname}={value!r} inválido. Aceitos: {allowed}"
                    )
            elif ptype == "string":
                value = str(value)

            out[pname] = value

        # passa-thru parâmetros desconhecidos não falha — útil para Fal endpoints
        # que aceitam params extra que não modelamos ainda
        for k, v in given.items():
            if k not in spec.params:
                out[k] = v

        return out

    def estimate_cost(self, model_name: str, params: dict[str, Any]) -> float:
        """Custo estimado de uma chamada. Se `num_outputs` existe, multiplica."""
        spec = self.get(model_name)
        n = int(params.get("num_outputs", 1))
        return round(spec.cost_brl_per_call * n, 2)
