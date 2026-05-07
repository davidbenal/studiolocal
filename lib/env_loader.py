"""Carrega credenciais respeitando a cascata definida pelo workspace_detector.

Ordem de prioridade:
  1. Variável de ambiente do shell (override absoluto — útil para CI/debug)
  2. Arquivos .env* na ordem retornada pelo detector
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from .workspace_detector import WorkspaceContext


class MissingCredential(Exception):
    pass


def load_key(name: str, ctx: WorkspaceContext) -> str:
    if name in os.environ and os.environ[name]:
        return os.environ[name]

    for env_file in ctx.env_files_priority:
        if env_file.exists():
            vals = dotenv_values(env_file)
            if vals.get(name):
                return vals[name]

    hint = (
        f"{ctx.studiolocal_root}/.env"
        if ctx.credential_strategy == "own"
        else "no .envmk ou .env do workspace pai"
    )
    raise MissingCredential(
        f"{name} ausente. Defina em {hint} ou exporte como variável de ambiente."
    )


def load_fal_key(ctx: WorkspaceContext) -> str:
    return load_key("FAL_KEY", ctx)


def all_keys(ctx: WorkspaceContext) -> dict[str, str]:
    """Retorna o merge final dos arquivos .env (sem incluir os.environ).
    Primeiro arquivo na cascata tem precedência sobre os seguintes.
    """
    merged: dict[str, str] = {}
    for env_file in reversed(ctx.env_files_priority):
        if env_file.exists():
            for k, v in dotenv_values(env_file).items():
                if v is not None:
                    merged[k] = v
    return merged
