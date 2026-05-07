"""Gerencia o filesystem de assets dentro de $workspace/.studiolocal/projects/{slug}/.

Convenções:
- Drafts ficam em projects/{slug}/drafts/YYYY-MM-DD_<topic>/NN.<ext>
- Library promove para projects/{slug}/library/<promoted_name>.<ext>
- Discarded vai para projects/{slug}/_tmp/discarded/<original_name>
"""

from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path


def slugify(text: str, max_len: int = 60) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len] or "untitled"


class AssetStore:
    def __init__(self, studiolocal_root: Path):
        self.root = studiolocal_root

    def project_dir(self, project_slug: str) -> Path:
        d = self.root / "projects" / project_slug
        for sub in ("drafts", "library", "_tmp", "_tmp/discarded"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        return d

    def new_draft_dir(self, project_slug: str, topic_hint: str | None = None) -> Path:
        topic = slugify(topic_hint or "gen", max_len=40)
        stamp = date.today().isoformat()
        base = self.project_dir(project_slug) / "drafts" / f"{stamp}_{topic}"
        # se já existe (mesmo dia + topic), encontra próximo sufixo
        n = 1
        d = base
        while d.exists():
            n += 1
            d = base.parent / f"{base.name}-{n:02d}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def promote(self, src: Path, project_slug: str, target_name: str | None = None) -> Path:
        target_name = target_name or src.name
        dest = self.project_dir(project_slug) / "library" / target_name
        if dest.exists():
            stem, ext = dest.stem, dest.suffix
            n = 2
            while dest.exists():
                dest = dest.with_name(f"{stem}-{n:02d}{ext}")
                n += 1
        shutil.move(str(src), str(dest))
        return dest

    def discard(self, src: Path, project_slug: str) -> Path:
        dest = self.project_dir(project_slug) / "_tmp" / "discarded" / src.name
        if dest.exists():
            stem, ext = dest.stem, dest.suffix
            n = 2
            while dest.exists():
                dest = dest.with_name(f"{stem}-{n:02d}{ext}")
                n += 1
        shutil.move(str(src), str(dest))
        return dest

    def relpath(self, absolute: Path) -> str:
        """Retorna path relativo a self.root para registro no DB."""
        try:
            return str(absolute.relative_to(self.root))
        except ValueError:
            return str(absolute)
