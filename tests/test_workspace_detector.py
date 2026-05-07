"""Testes do workspace_detector."""

from __future__ import annotations

from pathlib import Path

from lib.workspace_detector import detect


def test_standalone_em_pasta_vazia(tmp_path: Path) -> None:
    ctx = detect(tmp_path)
    assert ctx.mode == "standalone"
    assert ctx.credential_strategy == "own"
    assert ctx.studiolocal_root == tmp_path / ".studiolocal"
    assert ctx.env_files_priority == [tmp_path / ".studiolocal" / ".env"]


def test_embedded_quando_envmk_existe(tmp_path: Path) -> None:
    (tmp_path / ".envmk").write_text("FAL_KEY=fake\n")
    ctx = detect(tmp_path)
    assert ctx.mode == "embedded"
    assert ctx.credential_strategy == "inherit"
    assert (tmp_path / ".envmk") in ctx.env_files_priority
    # ordem: .envmk > .env > global
    assert ctx.env_files_priority[0] == tmp_path / ".envmk"


def test_embedded_quando_claude_md_existe(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# project\n")
    ctx = detect(tmp_path)
    assert ctx.mode == "embedded"


def test_embedded_quando_env_existe(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("FOO=bar\n")
    ctx = detect(tmp_path)
    assert ctx.mode == "embedded"


def test_studiolocal_root_sempre_em_pwd(tmp_path: Path) -> None:
    ctx = detect(tmp_path)
    assert ctx.studiolocal_root == tmp_path / ".studiolocal"
