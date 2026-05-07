"""Testes do models_registry — validação e cálculo de custo."""

from __future__ import annotations

import pytest

from lib.models_registry import ModelsRegistry


@pytest.fixture
def registry() -> ModelsRegistry:
    return ModelsRegistry()


def test_carrega_modelos_core(registry: ModelsRegistry) -> None:
    assert "nano-banana-2" in registry.models
    assert "nano-banana-pro" in registry.models
    assert "kling-3" in registry.models
    assert "seedance-2" in registry.models
    assert "clarity" in registry.models


def test_defaults(registry: ModelsRegistry) -> None:
    assert registry.defaults["image"] == "nano-banana-pro"
    assert registry.defaults["video"] == "seedance-2"
    assert registry.defaults["upscale"] == "clarity"


def test_validate_aplica_default_de_param(registry: ModelsRegistry) -> None:
    result = registry.validate_and_normalize(
        "nano-banana-pro", {"prompt": "X"}
    )
    assert result["num_outputs"] == 1
    assert result["aspect_ratio"] == "1:1"


def test_validate_rejeita_required_faltando(registry: ModelsRegistry) -> None:
    with pytest.raises(ValueError, match="obrigatório"):
        registry.validate_and_normalize("nano-banana-pro", {})


def test_validate_rejeita_enum_invalido(registry: ModelsRegistry) -> None:
    with pytest.raises(ValueError, match="inválido"):
        registry.validate_and_normalize(
            "nano-banana-pro", {"prompt": "X", "aspect_ratio": "21:9"}
        )


def test_validate_aplica_min_max(registry: ModelsRegistry) -> None:
    with pytest.raises(ValueError):
        registry.validate_and_normalize(
            "nano-banana-pro", {"prompt": "X", "num_outputs": 99}
        )


def test_estimate_cost_multiplica_por_num_outputs(registry: ModelsRegistry) -> None:
    cost = registry.estimate_cost("nano-banana-pro", {"prompt": "X", "num_outputs": 4})
    assert cost == 0.32 * 4


def test_estimate_cost_default_n_1(registry: ModelsRegistry) -> None:
    cost = registry.estimate_cost("clarity", {"input_asset": "x"})
    assert cost == 0.15
