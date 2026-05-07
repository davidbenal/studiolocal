"""Testes do workflow_runner — interpolação e parsing YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from lib.workflow_runner import WorkflowSpec, _interpolate


def test_interpolate_string_simples() -> None:
    ctx = {"inputs": {"prompt": "hero shot"}}
    assert _interpolate("uma foto de {{ inputs.prompt }}", ctx) == "uma foto de hero shot"


def test_interpolate_referencia_pura_devolve_valor_cru() -> None:
    """Quando a string é apenas uma interpolação, devolve o valor cru
    (não converte int→str). Importante para passar asset_ids como int."""
    ctx = {"steps": {"pick": {"selected": 42}}}
    result = _interpolate("{{ steps.pick.selected }}", ctx)
    assert result == 42
    assert isinstance(result, int)


def test_interpolate_em_dict_recursivo() -> None:
    ctx = {"inputs": {"prompt": "X"}}
    result = _interpolate(
        {"prompt": "{{ inputs.prompt }}", "n": 4},
        ctx,
    )
    assert result == {"prompt": "X", "n": 4}


def test_interpolate_em_lista() -> None:
    ctx = {"inputs": {"a": "1", "b": "2"}}
    result = _interpolate(["{{ inputs.a }}", "{{ inputs.b }}"], ctx)
    assert result == ["1", "2"]


def test_interpolate_path_inexistente_retorna_vazio() -> None:
    ctx = {"inputs": {}}
    assert _interpolate("a {{ inputs.X.Y.Z }} b", ctx) == "a  b"


def test_workflow_spec_from_yaml(tmp_path: Path) -> None:
    yaml_content = {
        "schema": "studiolocal/workflow/v1",
        "slug": "test",
        "name": "Test Workflow",
        "description": "test",
        "inputs": {"prompt": {"type": "string", "required": True}},
        "steps": [
            {
                "id": "gen",
                "kind": "image",
                "model": "nano-banana-pro",
                "params": {"prompt": "{{ inputs.prompt }}"},
            }
        ],
        "finalize": {"promote_to_library": []},
    }
    p = tmp_path / "wf.yaml"
    p.write_text(yaml.safe_dump(yaml_content))
    spec = WorkflowSpec.from_yaml(p)
    assert spec.slug == "test"
    assert len(spec.steps) == 1
    assert spec.steps[0]["model"] == "nano-banana-pro"


def test_workflow_spec_schema_invalido(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump({"schema": "outro/v1", "slug": "x", "name": "x"}))
    import pytest
    from lib.workflow_runner import WorkflowError

    with pytest.raises(WorkflowError):
        WorkflowSpec.from_yaml(p)
