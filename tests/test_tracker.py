"""Testes do tracker — CRUD básico, migrations, transações."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.tracker import Tracker


@pytest.fixture
def tracker(tmp_path: Path) -> Tracker:
    t = Tracker(tmp_path / "tracker.db")
    t.apply_migrations()
    return t


def test_migrations_aplicadas(tracker: Tracker) -> None:
    assert tracker.current_schema_version() >= 2


def test_create_e_get_project(tracker: Tracker) -> None:
    pid = tracker.create_project("teste", "Teste", ["client:x"], 100.0)
    p = tracker.get_project_by_slug("teste")
    assert p is not None
    assert p["id"] == pid
    assert p["name"] == "Teste"
    assert json.loads(p["tags"]) == ["client:x"]
    assert p["budget_brl"] == 100.0
    assert p["status"] == "active"


def test_archive_project(tracker: Tracker) -> None:
    pid = tracker.create_project("arch", "Archived", [], None)
    tracker.archive_project(pid)
    p = tracker.get_project_by_slug("arch")
    assert p["status"] == "archived"
    assert p["archived_at"] is not None


def test_session_lifecycle(tracker: Tracker) -> None:
    pid = tracker.create_project("s", "S", [], None)
    sid = tracker.open_session(pid)
    assert tracker.find_active_session(pid) is not None
    tracker.close_session(sid)
    assert tracker.find_active_session(pid) is None


def test_generation_e_asset(tracker: Tracker) -> None:
    pid = tracker.create_project("g", "G", [], None)
    sid = tracker.open_session(pid)
    gid = tracker.create_generation(
        pid, sid, "nano-banana-pro", "image", "prompt aqui", {"num_outputs": 2}
    )
    aid = tracker.create_asset(gid, pid, "image", "projects/g/drafts/test/01.png")
    tracker.finish_generation(gid, "done", cost_brl=0.64)

    rows = tracker.query("SELECT * FROM generations WHERE id = ?", (gid,))
    assert rows[0]["status"] == "done"
    assert rows[0]["cost_brl"] == 0.64
    rows = tracker.query("SELECT * FROM assets WHERE id = ?", (aid,))
    assert rows[0]["status"] == "draft"


def test_promote_asset(tracker: Tracker) -> None:
    pid = tracker.create_project("p", "P", [], None)
    sid = tracker.open_session(pid)
    gid = tracker.create_generation(pid, sid, "m", "image", "p", {})
    aid = tracker.create_asset(gid, pid, "image", "drafts/old/01.png")
    tracker.promote_asset(aid, "library/01.png")
    row = tracker.query("SELECT * FROM assets WHERE id = ?", (aid,))[0]
    assert row["status"] == "library"
    assert row["promoted_at"] is not None
    assert row["file_path"] == "library/01.png"


def test_transacoes_rollback_em_falha(tracker: Tracker) -> None:
    """Tenta inserir row com FK inválida — deve falhar e não deixar lixo."""
    with pytest.raises(Exception):
        with tracker.transaction() as conn:
            conn.execute(
                "INSERT INTO assets (generation_id, project_id, kind, file_path) "
                "VALUES (99999, 99999, 'image', 'fake')"
            )
    rows = tracker.query("SELECT COUNT(*) n FROM assets")
    assert rows[0]["n"] == 0
