"""Wrapper Fal.ai unificado para image/video/upscale.

Política V1: fail fast. Sem retry automático. Erros são propagados ao caller
(workflow_runner ou skill operacional) que decide se tenta de novo via comando
explícito do user.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .models_registry import ModelSpec, ModelsRegistry


class FalError(RuntimeError):
    pass


@dataclass
class FalResult:
    request_id: str | None
    output_urls: list[str]
    raw_response: dict[str, Any]
    elapsed_s: float


class FalClient:
    def __init__(self, api_key: str, registry: ModelsRegistry):
        if not api_key:
            raise FalError("FAL_KEY vazio")
        self._api_key = api_key
        self._registry = registry
        # fal-client real seria preferível, mas começamos com requests para
        # manter dependências mínimas. Substituível em V2.
        os.environ["FAL_KEY"] = api_key

    def _normalize_outputs(self, response: dict[str, Any], kind: str) -> list[str]:
        # Fal endpoints variam: alguns retornam {images: [{url}]}, outros
        # {video: {url}}, outros {image: {url}}. Cobrimos os casos conhecidos.
        if kind == "image":
            if "images" in response:
                return [img["url"] for img in response["images"]]
            if "image" in response and isinstance(response["image"], dict):
                return [response["image"]["url"]]
        if kind == "video":
            if "video" in response and isinstance(response["video"], dict):
                return [response["video"]["url"]]
            if "videos" in response:
                return [v["url"] for v in response["videos"]]
        if kind == "upscale":
            if "image" in response and isinstance(response["image"], dict):
                return [response["image"]["url"]]
        # fallback genérico — varre URLs no JSON
        urls: list[str] = []
        def _scan(obj: Any) -> None:
            if isinstance(obj, dict):
                for v in obj.values():
                    _scan(v)
            elif isinstance(obj, list):
                for v in obj:
                    _scan(v)
            elif isinstance(obj, str) and obj.startswith("http"):
                urls.append(obj)
        _scan(response)
        return urls

    def call(self, model_name: str, params: dict[str, Any]) -> FalResult:
        spec: ModelSpec = self._registry.get(model_name)
        normalized = self._registry.validate_and_normalize(model_name, params)
        url = f"https://fal.run/{spec.fal_endpoint}"
        headers = {
            "Authorization": f"Key {self._api_key}",
            "Content-Type": "application/json",
        }
        started = time.time()
        try:
            response = requests.post(url, json=normalized, headers=headers, timeout=300)
        except requests.RequestException as e:
            raise FalError(f"Falha de rede ao chamar {spec.fal_endpoint}: {e}") from e

        elapsed = round(time.time() - started, 2)
        if response.status_code >= 400:
            raise FalError(
                f"Fal {spec.fal_endpoint} retornou {response.status_code}: "
                f"{response.text[:500]}"
            )

        try:
            data = response.json()
        except ValueError as e:
            raise FalError(f"Resposta Fal não é JSON: {response.text[:200]}") from e

        request_id = response.headers.get("x-fal-request-id") or data.get("request_id")
        outputs = self._normalize_outputs(data, spec.kind)
        if not outputs:
            raise FalError(
                f"Fal {spec.fal_endpoint} respondeu OK mas sem URLs de output: {data}"
            )
        return FalResult(
            request_id=request_id,
            output_urls=outputs,
            raw_response=data,
            elapsed_s=elapsed,
        )

    @staticmethod
    def download(url: str, dest: Path) -> int:
        """Baixa URL para path. Retorna bytes escritos."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            total = 0
            with dest.open("wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
        return total
