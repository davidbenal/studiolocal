"""SQLite wrapper. Toda escrita ao tracker.db passa por aqui.

Convenções:
- Todas as operações que tocam múltiplas tabelas usam transação explícita.
- Ids retornados são `lastrowid` da connection.
- Datas são strings ISO no fuso local do SQLite (`datetime('now')`).
- Tags são armazenadas como JSON array; `tags_filter()` faz LIKE-match.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


class Tracker:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    # --- migrations -----------------------------------------------------------

    def current_schema_version(self) -> int:
        try:
            row = self._conn.execute(
                "SELECT MAX(version) v FROM schema_version"
            ).fetchone()
            return row["v"] or 0
        except sqlite3.OperationalError:
            return 0

    def apply_migrations(self) -> list[int]:
        """Aplica migrations 001_, 002_, ... ainda não registradas."""
        applied: list[int] = []
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            version = int(sql_file.stem.split("_")[0])
            if version <= self.current_schema_version():
                continue
            with self.transaction() as conn:
                conn.executescript(sql_file.read_text())
            applied.append(version)
        return applied

    # --- transactions ---------------------------------------------------------

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    # --- projects -------------------------------------------------------------

    def create_project(
        self,
        slug: str,
        name: str,
        tags: list[str] | None = None,
        budget_brl: float | None = None,
    ) -> int:
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO projects (slug, name, tags, budget_brl) VALUES (?,?,?,?)",
                (slug, name, json.dumps(tags or []), budget_brl),
            )
            return cur.lastrowid

    def get_project_by_slug(self, slug: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM projects WHERE slug = ?", (slug,)
        ).fetchone()

    def list_projects(self, status: str | None = None) -> list[sqlite3.Row]:
        if status:
            return self._conn.execute(
                "SELECT * FROM projects WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        return self._conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()

    def archive_project(self, project_id: int) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE projects SET status='archived', archived_at=datetime('now') "
                "WHERE id = ?",
                (project_id,),
            )

    # --- sessions -------------------------------------------------------------

    def open_session(self, project_id: int | None = None) -> int:
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO sessions (project_id) VALUES (?)", (project_id,)
            )
            return cur.lastrowid

    def touch_session(self, session_id: int) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE sessions SET last_activity_at=datetime('now') WHERE id = ?",
                (session_id,),
            )

    def close_session(self, session_id: int) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE sessions SET closed_at=datetime('now') WHERE id = ? "
                "AND closed_at IS NULL",
                (session_id,),
            )

    def find_active_session(self, project_id: int | None = None) -> sqlite3.Row | None:
        if project_id is None:
            return self._conn.execute(
                "SELECT * FROM sessions WHERE closed_at IS NULL "
                "ORDER BY last_activity_at DESC LIMIT 1"
            ).fetchone()
        return self._conn.execute(
            "SELECT * FROM sessions WHERE closed_at IS NULL AND project_id = ? "
            "ORDER BY last_activity_at DESC LIMIT 1",
            (project_id,),
        ).fetchone()

    def find_abandoned_sessions(self, idle_minutes: int = 60) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM sessions WHERE closed_at IS NULL "
            f"AND last_activity_at < datetime('now', '-{int(idle_minutes)} minutes')"
        ).fetchall()

    # --- generations + assets -------------------------------------------------

    def create_generation(
        self,
        project_id: int,
        session_id: int,
        model: str,
        kind: str,
        prompt: str | None,
        params: dict[str, Any],
        run_id: int | None = None,
        step_index: int | None = None,
    ) -> int:
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO generations "
                "(project_id, session_id, run_id, step_index, model, kind, prompt, params, status) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    project_id,
                    session_id,
                    run_id,
                    step_index,
                    model,
                    kind,
                    prompt,
                    json.dumps(params or {}),
                    "pending",
                ),
            )
            return cur.lastrowid

    def finish_generation(
        self,
        generation_id: int,
        status: str,
        cost_brl: float = 0.0,
        fal_request_id: str | None = None,
        error: str | None = None,
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE generations SET status=?, cost_brl=?, fal_request_id=?, "
                "error=?, finished_at=datetime('now') WHERE id = ?",
                (status, cost_brl, fal_request_id, error, generation_id),
            )

    def create_asset(
        self,
        generation_id: int,
        project_id: int,
        kind: str,
        file_path: str,
        parent_asset_id: int | None = None,
        width: int | None = None,
        height: int | None = None,
        duration_s: float | None = None,
        bytes_size: int | None = None,
    ) -> int:
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO assets "
                "(generation_id, project_id, parent_asset_id, kind, file_path, "
                "width, height, duration_s, bytes) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    generation_id,
                    project_id,
                    parent_asset_id,
                    kind,
                    file_path,
                    width,
                    height,
                    duration_s,
                    bytes_size,
                ),
            )
            return cur.lastrowid

    def promote_asset(self, asset_id: int, new_path: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE assets SET status='library', file_path=?, "
                "promoted_at=datetime('now') WHERE id = ?",
                (new_path, asset_id),
            )

    def discard_asset(self, asset_id: int, new_path: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE assets SET status='discarded', file_path=?, "
                "discarded_at=datetime('now') WHERE id = ?",
                (new_path, asset_id),
            )

    # --- workflows + runs -----------------------------------------------------

    def create_workflow(
        self,
        slug: str,
        name: str,
        yaml_path: str,
        source_session_id: int | None = None,
        description: str | None = None,
    ) -> int:
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO workflows (slug, name, yaml_path, source_session_id, description) "
                "VALUES (?,?,?,?,?)",
                (slug, name, yaml_path, source_session_id, description),
            )
            return cur.lastrowid

    def get_workflow_by_slug(self, slug: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM workflows WHERE slug = ?", (slug,)
        ).fetchone()

    def create_run(
        self,
        workflow_id: int,
        project_id: int,
        session_id: int | None,
        inputs: dict[str, Any],
    ) -> int:
        with self.transaction() as conn:
            cur = conn.execute(
                "INSERT INTO runs (workflow_id, project_id, session_id, inputs) "
                "VALUES (?,?,?,?)",
                (workflow_id, project_id, session_id, json.dumps(inputs or {})),
            )
            return cur.lastrowid

    def update_run(
        self,
        run_id: int,
        status: str | None = None,
        cost_brl: float | None = None,
        state: dict[str, Any] | None = None,
        finished: bool = False,
    ) -> None:
        sets = []
        vals: list[Any] = []
        if status is not None:
            sets.append("status = ?")
            vals.append(status)
        if cost_brl is not None:
            sets.append("cost_brl = ?")
            vals.append(cost_brl)
        if state is not None:
            sets.append("state = ?")
            vals.append(json.dumps(state))
        if finished:
            sets.append("finished_at = datetime('now')")
        if not sets:
            return
        vals.append(run_id)
        with self.transaction() as conn:
            conn.execute(f"UPDATE runs SET {', '.join(sets)} WHERE id = ?", vals)

    # --- queries de leitura (suporte a reports) -------------------------------

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self._conn.execute(sql, params).fetchall()

    def close(self) -> None:
        self._conn.close()
