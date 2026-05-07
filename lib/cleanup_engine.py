"""Cleanup engine — determina candidatos para remoção e executa em modos safe ou review.

Regras (do DESIGN.md):

| Categoria              | Idade min | --safe        | review (manual) |
|------------------------|-----------|---------------|-----------------|
| _tmp/ files            |        0  | remove        | remove          |
| failed generations     |        0  | remove arq.   | remove tudo     |
| drafts não promovidos  |  >30 dias | preserva      | candidato       |
| discarded              |   >7 dias | preserva      | candidato       |
| sessions abandonadas   |       —   | fecha         | fecha           |
| workflows não usados   |  >90 dias | preserva      | flag p/ review  |
| library                |   nunca   | NUNCA toca    | NUNCA toca      |
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .tracker import Tracker


@dataclass
class CleanupCandidate:
    category: str
    label: str
    paths: list[Path]
    db_action: str  # "delete_assets" | "wipe_files" | "close_session" | "flag" | ""
    db_ids: list[int]
    bytes_size: int

    def total_files(self) -> int:
        return len(self.paths)


class CleanupEngine:
    def __init__(self, tracker: Tracker, studiolocal_root: Path, idle_minutes: int = 60):
        self.tracker = tracker
        self.root = studiolocal_root
        self.idle_minutes = idle_minutes

    # --- scan ---------------------------------------------------------------

    def scan(self, safe: bool) -> list[CleanupCandidate]:
        cands: list[CleanupCandidate] = []
        cands.append(self._scan_tmp())
        cands.append(self._scan_failed_generations())
        cands.append(self._scan_abandoned_sessions())
        if not safe:
            cands.append(self._scan_old_drafts(age_days=30))
            cands.append(self._scan_old_discarded(age_days=7))
            cands.append(self._scan_unused_workflows(age_days=90))
        return [c for c in cands if c.total_files() > 0 or c.db_ids]

    # --- helpers --------------------------------------------------------------

    def _bytes_of(self, paths: list[Path]) -> int:
        total = 0
        for p in paths:
            try:
                if p.is_file():
                    total += p.stat().st_size
                elif p.is_dir():
                    for f in p.rglob("*"):
                        if f.is_file():
                            total += f.stat().st_size
            except OSError:
                pass
        return total

    def _scan_tmp(self) -> CleanupCandidate:
        paths: list[Path] = []
        if (self.root / "_tmp").exists():
            paths.extend(p for p in (self.root / "_tmp").iterdir())
        for proj_tmp in (self.root / "projects").glob("*/_tmp"):
            for p in proj_tmp.iterdir():
                if p.name == "discarded":
                    continue
                paths.append(p)
        return CleanupCandidate(
            category="_tmp_files",
            label="Arquivos em _tmp/",
            paths=paths,
            db_action="",
            db_ids=[],
            bytes_size=self._bytes_of(paths),
        )

    def _scan_failed_generations(self) -> CleanupCandidate:
        rows = self.tracker.query("SELECT id FROM generations WHERE status='failed'")
        return CleanupCandidate(
            category="failed_generations",
            label="Generations com status=failed",
            paths=[],
            db_action="wipe_files",
            db_ids=[r["id"] for r in rows],
            bytes_size=0,
        )

    def _scan_abandoned_sessions(self) -> CleanupCandidate:
        rows = self.tracker.find_abandoned_sessions(self.idle_minutes)
        return CleanupCandidate(
            category="abandoned_sessions",
            label=f"Sessions inativas há >{self.idle_minutes}min (será fechada, não deletada)",
            paths=[],
            db_action="close_session",
            db_ids=[r["id"] for r in rows],
            bytes_size=0,
        )

    def _scan_old_drafts(self, age_days: int) -> CleanupCandidate:
        cutoff = (datetime.utcnow() - timedelta(days=age_days)).isoformat(sep=" ")
        rows = self.tracker.query(
            "SELECT id, file_path FROM assets WHERE status='draft' AND created_at < ?",
            (cutoff,),
        )
        paths = [self.root / r["file_path"] for r in rows]
        return CleanupCandidate(
            category="old_drafts",
            label=f"Drafts não promovidos (>{age_days}d)",
            paths=paths,
            db_action="delete_assets",
            db_ids=[r["id"] for r in rows],
            bytes_size=self._bytes_of(paths),
        )

    def _scan_old_discarded(self, age_days: int) -> CleanupCandidate:
        cutoff = (datetime.utcnow() - timedelta(days=age_days)).isoformat(sep=" ")
        rows = self.tracker.query(
            "SELECT id, file_path FROM assets WHERE status='discarded' "
            "AND discarded_at IS NOT NULL AND discarded_at < ?",
            (cutoff,),
        )
        paths = [self.root / r["file_path"] for r in rows]
        return CleanupCandidate(
            category="old_discarded",
            label=f"Descartados (>{age_days}d)",
            paths=paths,
            db_action="delete_assets",
            db_ids=[r["id"] for r in rows],
            bytes_size=self._bytes_of(paths),
        )

    def _scan_unused_workflows(self, age_days: int) -> CleanupCandidate:
        cutoff = (datetime.utcnow() - timedelta(days=age_days)).isoformat(sep=" ")
        rows = self.tracker.query(
            "SELECT w.id, w.slug, w.yaml_path FROM workflows w "
            "WHERE w.created_at < ? "
            "AND NOT EXISTS (SELECT 1 FROM runs r WHERE r.workflow_id = w.id)",
            (cutoff,),
        )
        return CleanupCandidate(
            category="unused_workflows",
            label=f"Workflows nunca usados (>{age_days}d) — flag para review",
            paths=[],
            db_action="flag",
            db_ids=[r["id"] for r in rows],
            bytes_size=0,
        )

    # --- execute ------------------------------------------------------------

    def execute(self, candidates: list[CleanupCandidate]) -> dict[str, int]:
        stats = {"files": 0, "bytes": 0, "db_rows": 0, "sessions_closed": 0}
        for c in candidates:
            for p in c.paths:
                try:
                    if p.is_file():
                        size = p.stat().st_size
                        p.unlink()
                        stats["files"] += 1
                        stats["bytes"] += size
                    elif p.is_dir():
                        for f in p.rglob("*"):
                            if f.is_file():
                                stats["bytes"] += f.stat().st_size
                                stats["files"] += 1
                        import shutil
                        shutil.rmtree(p)
                except OSError:
                    pass

            if c.db_action == "delete_assets":
                for aid in c.db_ids:
                    with self.tracker.transaction() as conn:
                        conn.execute("DELETE FROM assets WHERE id = ?", (aid,))
                    stats["db_rows"] += 1
            elif c.db_action == "close_session":
                for sid in c.db_ids:
                    self.tracker.close_session(sid)
                    stats["sessions_closed"] += 1
            # "wipe_files" e "flag" não tocam DB (mantém audit trail)

        self._log(stats, candidates)
        return stats

    def _log(self, stats: dict[str, int], candidates: list[CleanupCandidate]) -> None:
        log_dir = self.root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "at": datetime.utcnow().isoformat() + "Z",
            "stats": stats,
            "categories": [
                {"name": c.category, "files": c.total_files(), "bytes": c.bytes_size}
                for c in candidates
            ],
        }
        with (log_dir / "cleanup-history.jsonl").open("a") as f:
            f.write(json.dumps(entry) + "\n")
