"""StudioLocal CLI — entrypoint para skills e usuários técnicos.

Cada subcomando tem responsabilidade única. Skills disparam estes via Bash.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .asset_store import AssetStore, slugify
from .cleanup_engine import CleanupEngine
from .env_loader import load_fal_key, MissingCredential
from .fal_client import FalClient, FalError
from .models_registry import ModelsRegistry
from .report_generator import ReportGenerator
from .session_manager import SessionManager
from .tracker import Tracker
from .workflow_runner import WorkflowRunner, WorkflowSpec, WorkflowPaused, WorkflowError
from .workspace_detector import detect

console = Console()


def _ctx(pwd: Path | None = None) -> tuple[Tracker, AssetStore, ModelsRegistry, SessionManager]:
    wctx = detect(pwd)
    if not wctx.studiolocal_root.exists():
        click.echo(
            f"StudioLocal não instalado em {wctx.workspace_root}. "
            "Rode `/studiolocal-install` primeiro.",
            err=True,
        )
        sys.exit(1)
    tracker = Tracker(wctx.studiolocal_root / "tracker.db")
    store = AssetStore(wctx.studiolocal_root)
    registry = ModelsRegistry()
    sm = SessionManager(tracker)
    return tracker, store, registry, sm


def _fal(tracker: Tracker, registry: ModelsRegistry) -> FalClient:
    wctx = detect()
    try:
        key = load_fal_key(wctx)
    except MissingCredential as e:
        click.echo(str(e), err=True)
        sys.exit(2)
    return FalClient(key, registry)


@click.group()
@click.version_option(__version__)
def main() -> None:
    """StudioLocal — geração via Fal.ai operada conversacionalmente."""


# --- install --------------------------------------------------------------


@main.command()
@click.option("--force", is_flag=True, help="Reinstala mesmo se .studiolocal/ existe")
def install(force: bool) -> None:
    """Setup do workspace atual: detecta modo, cria .studiolocal/, edita CLAUDE.md."""
    wctx = detect()
    target = wctx.studiolocal_root

    if target.exists() and not force:
        click.echo(f"Já instalado em {target}. Use --force para reinstalar.")
        return

    target.mkdir(parents=True, exist_ok=True)
    for sub in ("projects", "workflows", "_tmp", "archive", "logs"):
        (target / sub).mkdir(exist_ok=True)

    tracker = Tracker(target / "tracker.db")
    applied = tracker.apply_migrations()
    click.echo(f"✓ tracker.db schema v{tracker.current_schema_version()} ({len(applied)} migrations)")

    if wctx.mode == "standalone":
        env_file = target / ".env"
        if not env_file.exists():
            tmpl = (Path(__file__).parent.parent / "templates" / "env.tmpl").read_text()
            env_file.write_text(tmpl)
            click.echo(f"✓ {env_file} criado (preencha FAL_KEY)")

    config = target / "config.yaml"
    if not config.exists():
        config.write_text(
            f"mode: {wctx.mode}\n"
            f"workspace_root: {wctx.workspace_root}\n"
            "idle_timeout_min: 60\n"
            "default_image: nano-banana-pro\n"
            "default_video: seedance-2\n"
            "default_upscale: clarity\n"
        )

    _patch_claude_md(wctx.workspace_root, wctx.mode)

    click.echo(f"\n✓ StudioLocal instalado em modo {wctx.mode.upper()}")
    click.echo(f"  workspace: {wctx.workspace_root}")
    click.echo(f"  data:      {target}")


def _patch_claude_md(workspace_root: Path, mode: str) -> None:
    md = workspace_root / "CLAUDE.md"
    block = (
        "<!-- studiolocal:start -->\n"
        "## StudioLocal\n\n"
        "Geração de imagem/vídeo via Fal.ai. Skills: "
        "`/studio-{project,image,video,upscale,promote,discard,workflow,run,cleanup,report,status}`.\n"
        f"Tracker em `.studiolocal/tracker.db`. Modo: **{mode}** "
        + (
            "(FAL_KEY herdado do workspace pai)."
            if mode == "embedded"
            else "(FAL_KEY em `.studiolocal/.env`)."
        )
        + "\n\nAo `/end-session` deste workspace, rode antes do commit: `studiolocal cleanup --safe`.\n"
        "<!-- studiolocal:end -->\n"
    )
    if not md.exists():
        md.write_text(block)
        return
    content = md.read_text()
    if "<!-- studiolocal:start -->" in content:
        import re
        new = re.sub(
            r"<!-- studiolocal:start -->.*?<!-- studiolocal:end -->\n?",
            block,
            content,
            flags=re.DOTALL,
        )
        md.write_text(new)
    else:
        md.write_text(content.rstrip() + "\n\n" + block)


# --- project ---------------------------------------------------------------


@main.group()
def project() -> None:
    """CRUD de projects."""


@project.command("new")
@click.argument("name")
@click.option("--tag", "tags", multiple=True, help="Tags (repetir): --tag client:X --tag type:Y")
@click.option("--budget", type=float, help="Budget em BRL")
def project_new(name: str, tags: tuple[str, ...], budget: float | None) -> None:
    tracker, store, _, _ = _ctx()
    slug = slugify(name)
    if tracker.get_project_by_slug(slug):
        click.echo(f"Project `{slug}` já existe.", err=True)
        sys.exit(1)
    pid = tracker.create_project(slug, name, list(tags), budget)
    proj_dir = store.project_dir(slug)
    # cria README do project
    tmpl = (Path(__file__).parent.parent / "templates" / "project_README.md.tmpl").read_text()
    readme_text = (
        tmpl.replace("{{ name }}", name)
        .replace("{{ slug }}", slug)
        .replace("{{ status }}", "active")
        .replace("{{ tags }}", ", ".join(tags) or "—")
        .replace("{{ budget }}", f"R$ {budget:.2f}" if budget else "—")
        .replace("{{ created_at }}", "")
    )
    (proj_dir / "README.md").write_text(readme_text)
    click.echo(f"✓ Project `{slug}` (#{pid}) criado em {proj_dir}")


@project.command("list")
@click.option("--archived", is_flag=True)
def project_list(archived: bool) -> None:
    tracker, _, _, _ = _ctx()
    rows = tracker.list_projects(status="archived" if archived else "active")
    if not rows:
        click.echo("Sem projects.")
        return
    table = Table(title="Projects")
    table.add_column("slug")
    table.add_column("nome")
    table.add_column("tags")
    table.add_column("budget", justify="right")
    table.add_column("criado")
    for r in rows:
        tags = ", ".join(json.loads(r["tags"] or "[]"))
        budget = f"R$ {r['budget_brl']:.2f}" if r["budget_brl"] else "—"
        table.add_row(r["slug"], r["name"], tags or "—", budget, r["created_at"][:10])
    console.print(table)


@project.command("archive")
@click.argument("slug")
def project_archive(slug: str) -> None:
    tracker, _, _, _ = _ctx()
    proj = tracker.get_project_by_slug(slug)
    if not proj:
        click.echo(f"Project `{slug}` não encontrado.", err=True)
        sys.exit(1)
    tracker.archive_project(proj["id"])
    click.echo(f"✓ Project `{slug}` arquivado")


# --- generate (image/video/upscale) ---------------------------------------


@main.command("gen")
@click.option("--project", "project_slug", required=True)
@click.option("--kind", type=click.Choice(["image", "video", "upscale"]), required=True)
@click.option("--model", help="Override do modelo default")
@click.option("--prompt", help="Prompt textual")
@click.option("--params", help='JSON com params extras: \'{"num_outputs":4}\'')
@click.option("--input-asset", "input_asset_id", type=int, help="ID de asset (para upscale/video-from-image)")
@click.option("--yes", is_flag=True, help="Pula confirmação de custo")
def gen(
    project_slug: str,
    kind: str,
    model: str | None,
    prompt: str | None,
    params: str | None,
    input_asset_id: int | None,
    yes: bool,
) -> None:
    tracker, store, registry, sm = _ctx()
    proj = tracker.get_project_by_slug(project_slug)
    if not proj:
        click.echo(f"Project `{project_slug}` não encontrado.", err=True)
        sys.exit(1)

    model = model or registry.defaults[kind]
    p_dict: dict = json.loads(params) if params else {}
    if prompt:
        p_dict.setdefault("prompt", prompt)
    if input_asset_id:
        row = tracker.query("SELECT * FROM assets WHERE id = ?", (input_asset_id,))
        if not row:
            click.echo(f"Asset {input_asset_id} não encontrado.", err=True)
            sys.exit(1)
        full_path = store.root / row[0]["file_path"]
        if kind == "upscale":
            p_dict.setdefault("input_asset", str(full_path))
        else:
            p_dict.setdefault("input_image", str(full_path))

    cost = registry.estimate_cost(model, p_dict)
    if not yes:
        click.echo(f"Modelo: {model} | custo estimado: R$ {cost:.2f}")
        if not click.confirm("Confirmar?", default=True):
            click.echo("Cancelado.")
            return

    session_id = sm.ensure_session(proj["id"])
    fal = _fal(tracker, registry)
    gen_id = tracker.create_generation(
        project_id=proj["id"],
        session_id=session_id,
        model=model,
        kind=kind,
        prompt=p_dict.get("prompt"),
        params=p_dict,
    )

    try:
        result = fal.call(model, p_dict)
    except FalError as e:
        tracker.finish_generation(gen_id, status="failed", error=str(e))
        click.echo(f"✗ Falhou: {e}", err=True)
        sys.exit(2)

    draft_dir = store.new_draft_dir(proj["slug"], topic_hint=p_dict.get("prompt", kind))
    ext = {"image": "png", "video": "mp4", "upscale": "png"}.get(kind, "bin")
    asset_kind = "video" if kind == "video" else "image"
    asset_ids: list[int] = []
    for i, url in enumerate(result.output_urls):
        file_path = draft_dir / f"{i + 1:02d}.{ext}"
        size = FalClient.download(url, file_path)
        aid = tracker.create_asset(
            generation_id=gen_id,
            project_id=proj["id"],
            kind=asset_kind,
            file_path=store.relpath(file_path),
            parent_asset_id=input_asset_id if kind in ("upscale", "video") else None,
            bytes_size=size,
        )
        asset_ids.append(aid)
    tracker.finish_generation(gen_id, status="done", cost_brl=cost, fal_request_id=result.request_id)

    click.echo(f"\n✓ {len(asset_ids)} asset(s) em {draft_dir.relative_to(store.root)}")
    click.echo(f"  IDs: {asset_ids}  |  custo: R$ {cost:.2f}  |  request_id: {result.request_id}")


# --- promote / discard ----------------------------------------------------


@main.command()
@click.argument("asset_id", type=int)
def promote(asset_id: int) -> None:
    tracker, store, _, _ = _ctx()
    rows = tracker.query("SELECT * FROM assets WHERE id = ?", (asset_id,))
    if not rows:
        click.echo(f"Asset {asset_id} não encontrado.", err=True)
        sys.exit(1)
    a = rows[0]
    proj = tracker.query("SELECT slug FROM projects WHERE id = ?", (a["project_id"],))[0]
    src = store.root / a["file_path"]
    new = store.promote(src, proj["slug"])
    tracker.promote_asset(asset_id, store.relpath(new))
    click.echo(f"✓ Asset {asset_id} promovido para {new.relative_to(store.root)}")


@main.command()
@click.argument("asset_id", type=int)
def discard(asset_id: int) -> None:
    tracker, store, _, _ = _ctx()
    rows = tracker.query("SELECT * FROM assets WHERE id = ?", (asset_id,))
    if not rows:
        click.echo(f"Asset {asset_id} não encontrado.", err=True)
        sys.exit(1)
    a = rows[0]
    proj = tracker.query("SELECT slug FROM projects WHERE id = ?", (a["project_id"],))[0]
    src = store.root / a["file_path"]
    new = store.discard(src, proj["slug"])
    tracker.discard_asset(asset_id, store.relpath(new))
    click.echo(f"✓ Asset {asset_id} descartado")


# --- workflow / run --------------------------------------------------------


@main.group()
def workflow() -> None:
    """CRUD de workflows."""


@workflow.command("list")
def workflow_list() -> None:
    tracker, _, _, _ = _ctx()
    rows = tracker.query("SELECT * FROM workflows ORDER BY created_at DESC")
    if not rows:
        click.echo("Nenhum workflow salvo ainda.")
        return
    table = Table(title="Workflows")
    table.add_column("slug")
    table.add_column("nome")
    table.add_column("yaml")
    for r in rows:
        table.add_row(r["slug"], r["name"], r["yaml_path"])
    console.print(table)


@workflow.command("save")
@click.option("--name", required=True, help="Nome legível: 'Hero Fashion Light'")
@click.option("--from-yaml", "from_yaml", required=True, help="Path do YAML pronto")
@click.option("--description", default="")
def workflow_save(name: str, from_yaml: str, description: str) -> None:
    tracker, store, _, _ = _ctx()
    src = Path(from_yaml).resolve()
    if not src.exists():
        click.echo(f"Arquivo {src} não existe.", err=True)
        sys.exit(1)
    slug = slugify(name)
    target = store.root / "workflows" / f"{slug}.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(src.read_text())
    sid = (tracker.find_active_session() or {}).get("id") if tracker.find_active_session() else None
    wid = tracker.create_workflow(
        slug=slug,
        name=name,
        yaml_path=str(target.relative_to(store.root)),
        source_session_id=sid,
        description=description,
    )
    click.echo(f"✓ Workflow `{slug}` (#{wid}) salvo em {target}")


@main.command("run")
@click.argument("workflow_slug")
@click.option("--project", "project_slug", required=True)
@click.option("--inputs", help='JSON: \'{"prompt":"X"}\'')
@click.option("--resume", "resume_run_id", type=int, help="Resume run pausada")
@click.option("--selected", help='Para human_pick: \'{"selected": <asset_id>}\'')
def run_cmd(
    workflow_slug: str,
    project_slug: str,
    inputs: str | None,
    resume_run_id: int | None,
    selected: str | None,
) -> None:
    tracker, store, registry, sm = _ctx()
    proj = tracker.get_project_by_slug(project_slug)
    if not proj:
        click.echo(f"Project `{project_slug}` não encontrado.", err=True)
        sys.exit(1)
    wrow = tracker.get_workflow_by_slug(workflow_slug)
    if not wrow:
        click.echo(f"Workflow `{workflow_slug}` não encontrado.", err=True)
        sys.exit(1)
    spec = WorkflowSpec.from_yaml(store.root / wrow["yaml_path"])
    fal = _fal(tracker, registry)
    runner = WorkflowRunner(tracker, registry, fal, store)

    try:
        if resume_run_id:
            user_input = json.loads(selected) if selected else {}
            runner.resume(spec, resume_run_id, proj["id"], proj["slug"], None, user_input)
            click.echo(f"✓ Run #{resume_run_id} retomada e concluída")
        else:
            session_id = sm.ensure_session(proj["id"])
            inp = json.loads(inputs) if inputs else {}
            run_id = runner.start(
                spec, proj["id"], proj["slug"], session_id, inp, wrow["id"]
            )
            click.echo(f"✓ Run #{run_id} concluída")
    except WorkflowPaused as p:
        click.echo(f"\n⏸ Run #{p.run_id} pausada no step '{p.step_id}'")
        click.echo(f"  {p.prompt_to_user}")
        click.echo(f"  Opções (asset IDs): {p.options}")
        click.echo(
            f"\n  Para continuar:\n"
            f"    studiolocal run {workflow_slug} --project {project_slug} "
            f"--resume {p.run_id} --selected '{{\"selected\": <id>}}'"
        )
    except WorkflowError as e:
        click.echo(f"✗ {e}", err=True)
        sys.exit(2)


# --- cleanup --------------------------------------------------------------


@main.command()
@click.option("--safe", is_flag=True, help="Modo safe (auto end-session)")
@click.option("--quiet", is_flag=True)
@click.option("--yes", is_flag=True, help="Pula confirmação")
def cleanup(safe: bool, quiet: bool, yes: bool) -> None:
    tracker, store, _, _ = _ctx()
    engine = CleanupEngine(tracker, store.root)
    cands = engine.scan(safe=safe)

    if not cands:
        if not quiet:
            click.echo("✓ Nada a limpar.")
        return

    if not quiet:
        table = Table(title=f"Cleanup ({'SAFE' if safe else 'review'})")
        table.add_column("Categoria")
        table.add_column("Itens", justify="right")
        table.add_column("Tamanho", justify="right")
        for c in cands:
            mb = c.bytes_size / 1024 / 1024
            size = f"{mb:.1f} MB" if mb >= 1 else f"{c.bytes_size} B"
            table.add_row(c.label, str(c.total_files() or len(c.db_ids)), size)
        console.print(table)

    if not (safe or yes):
        if not click.confirm("Apagar tudo acima?", default=False):
            click.echo("Cancelado.")
            return

    stats = engine.execute(cands)
    if not quiet:
        mb = stats["bytes"] / 1024 / 1024
        click.echo(
            f"\n✓ Removido: {stats['files']} arquivos, {mb:.1f} MB, "
            f"{stats['db_rows']} rows DB, {stats['sessions_closed']} sessions fechadas"
        )


# --- report / status ------------------------------------------------------


@main.command()
@click.option("--month", help="YYYY-MM")
@click.option("--tag", help="Filtra por tag literal: client:petrobras")
@click.option("--project", "project_slug", help="Filtra por slug")
def report(month: str | None, tag: str | None, project_slug: str | None) -> None:
    tracker, _, _, _ = _ctx()
    rg = ReportGenerator(tracker)
    click.echo(rg.cost_summary(month=month, tag=tag, project_slug=project_slug))


@main.command()
def status() -> None:
    tracker, _, registry, sm = _ctx()
    rg = ReportGenerator(tracker)
    active = tracker.find_active_session()
    proj_name = "—"
    if active and active["project_id"]:
        p = tracker.query("SELECT name, slug FROM projects WHERE id = ?", (active["project_id"],))[0]
        proj_name = f"{p['name']} (`{p['slug']}`)"

    click.echo(f"## Status\n")
    click.echo(f"- Project ativo: {proj_name}")
    click.echo(f"- Session ativa: #{active['id'] if active else '—'}")
    click.echo(f"- Modelos default: {registry.defaults}")
    click.echo(f"- Calibração `models.yaml`: {registry.calibrated_at}")
    from datetime import date
    month = date.today().strftime("%Y-%m")
    click.echo("\n" + rg.cost_summary(month=month))


# --- db utility ------------------------------------------------------------


@main.group()
def db() -> None:
    """Operações de banco."""


@db.command("migrate")
def db_migrate() -> None:
    tracker, _, _, _ = _ctx()
    applied = tracker.apply_migrations()
    if applied:
        click.echo(f"✓ Aplicadas migrations: {applied}")
    else:
        click.echo(f"✓ Schema atual: v{tracker.current_schema_version()}")


if __name__ == "__main__":
    main()
