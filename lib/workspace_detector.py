"""Detecta se o StudioLocal está rodando em modo embedded (dentro de um workspace
refinado como metaKosmos/Ktirio) ou standalone (próprio .env).

A heurística é simples: se houver `.envmk`, `.env` ou `CLAUDE.md` no PWD, é
embedded. Caso contrário, standalone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WorkspaceContext:
    mode: str  # "embedded" | "standalone"
    workspace_root: Path
    studiolocal_root: Path
    credential_strategy: str  # "inherit" | "own"
    env_files_priority: list[Path] = field(default_factory=list)

    def is_embedded(self) -> bool:
        return self.mode == "embedded"


def detect(pwd: Path | None = None) -> WorkspaceContext:
    pwd = (pwd or Path.cwd()).resolve()
    studiolocal_root = pwd / ".studiolocal"

    signals = {
        ".envmk": (pwd / ".envmk").exists(),
        "CLAUDE.md": (pwd / "CLAUDE.md").exists(),
        ".env": (pwd / ".env").exists(),
    }

    if any(signals.values()):
        return WorkspaceContext(
            mode="embedded",
            workspace_root=pwd,
            studiolocal_root=studiolocal_root,
            credential_strategy="inherit",
            env_files_priority=[
                pwd / ".envmk",
                pwd / ".env",
                Path.home() / ".studiolocal" / ".env",
            ],
        )

    return WorkspaceContext(
        mode="standalone",
        workspace_root=pwd,
        studiolocal_root=studiolocal_root,
        credential_strategy="own",
        env_files_priority=[studiolocal_root / ".env"],
    )
