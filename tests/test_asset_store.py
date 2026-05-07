"""Testes do asset_store — slugify, draft dirs, promote, discard."""

from __future__ import annotations

from pathlib import Path

from lib.asset_store import AssetStore, slugify


def test_slugify_basico() -> None:
    assert slugify("Hero Fashion Q2") == "hero-fashion-q2"
    assert slugify("Petrobras  Tanque   Algas") == "petrobras-tanque-algas"


def test_slugify_remove_acentos_e_simbolos() -> None:
    assert slugify("Camisão Áureo!") == "camis-o-ureo"


def test_slugify_max_len() -> None:
    s = slugify("a" * 100, max_len=20)
    assert len(s) <= 20


def test_slugify_vazio_default() -> None:
    assert slugify("...") == "untitled"
    assert slugify("") == "untitled"


def test_project_dir_cria_subpastas(tmp_path: Path) -> None:
    store = AssetStore(tmp_path)
    d = store.project_dir("hero")
    assert (d / "drafts").is_dir()
    assert (d / "library").is_dir()
    assert (d / "_tmp" / "discarded").is_dir()


def test_new_draft_dir_evita_colisao(tmp_path: Path) -> None:
    store = AssetStore(tmp_path)
    d1 = store.new_draft_dir("hero", topic_hint="hero")
    d2 = store.new_draft_dir("hero", topic_hint="hero")
    assert d1 != d2


def test_promote_e_discard(tmp_path: Path) -> None:
    store = AssetStore(tmp_path)
    d = store.new_draft_dir("hero", "test")
    src = d / "01.png"
    src.write_bytes(b"fake")

    promoted = store.promote(src, "hero", target_name="final.png")
    assert promoted.exists()
    assert promoted.parent.name == "library"
    assert not src.exists()

    src2 = d / "02.png"
    src2.write_bytes(b"fake")
    discarded = store.discard(src2, "hero")
    assert discarded.exists()
    assert discarded.parent.name == "discarded"


def test_relpath(tmp_path: Path) -> None:
    store = AssetStore(tmp_path)
    abs_path = tmp_path / "projects" / "x" / "drafts" / "01.png"
    abs_path.parent.mkdir(parents=True)
    abs_path.write_bytes(b"")
    rel = store.relpath(abs_path)
    assert rel == "projects/x/drafts/01.png"
