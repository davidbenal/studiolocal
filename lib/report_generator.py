"""Gera relatórios markdown a partir do tracker.db.

Filtros suportados: período (mês ou intervalo), tag, modelo, project.
"""

from __future__ import annotations

from .tracker import Tracker


def _money(v: float | None) -> str:
    if v is None:
        return "R$ 0,00"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ReportGenerator:
    def __init__(self, tracker: Tracker):
        self.tracker = tracker

    def cost_summary(
        self,
        month: str | None = None,
        tag: str | None = None,
        project_slug: str | None = None,
    ) -> str:
        where: list[str] = ["g.status = 'done'"]
        params: list[object] = []
        if month:
            where.append("strftime('%Y-%m', g.created_at) = ?")
            params.append(month)
        if project_slug:
            where.append("p.slug = ?")
            params.append(project_slug)
        if tag:
            where.append("p.tags LIKE ?")
            params.append(f'%"{tag}"%')

        wsql = " AND ".join(where)

        total = self.tracker.query(
            f"SELECT SUM(g.cost_brl) v, COUNT(*) n FROM generations g "
            f"JOIN projects p ON p.id=g.project_id WHERE {wsql}",
            tuple(params),
        )[0]
        failed = self.tracker.query(
            f"SELECT COUNT(*) n FROM generations g JOIN projects p ON p.id=g.project_id "
            f"WHERE p.id=g.project_id AND g.status='failed'"
            + (f" AND strftime('%Y-%m', g.created_at) = ?" if month else "")
            + (f" AND p.slug = ?" if project_slug else "")
            + (f" AND p.tags LIKE ?" if tag else ""),
            tuple(params),
        )[0]

        by_model = self.tracker.query(
            f"SELECT g.model m, COUNT(*) n, SUM(g.cost_brl) v FROM generations g "
            f"JOIN projects p ON p.id=g.project_id WHERE {wsql} "
            f"GROUP BY g.model ORDER BY v DESC",
            tuple(params),
        )

        by_project = self.tracker.query(
            f"SELECT p.slug s, p.name n, SUM(g.cost_brl) v FROM generations g "
            f"JOIN projects p ON p.id=g.project_id WHERE {wsql} "
            f"GROUP BY p.id ORDER BY v DESC",
            tuple(params),
        )

        lines: list[str] = []
        title_parts = []
        if month:
            title_parts.append(f"mês {month}")
        if tag:
            title_parts.append(f"tag `{tag}`")
        if project_slug:
            title_parts.append(f"project `{project_slug}`")
        title = "Relatório de custos" + (" — " + ", ".join(title_parts) if title_parts else "")

        lines.append(f"## {title}\n")
        lines.append(
            f"**Total:** {_money(total['v'])}  "
            f"|  **Generations:** {total['n']} done, {failed['n']} failed\n"
        )

        if by_model:
            lines.append("### Por modelo\n")
            lines.append("| Modelo | Calls | Total |")
            lines.append("|---|---:|---:|")
            for r in by_model:
                lines.append(f"| `{r['m']}` | {r['n']} | {_money(r['v'])} |")
            lines.append("")

        if by_project and not project_slug:
            lines.append("### Por project\n")
            lines.append("| Project | Total |")
            lines.append("|---|---:|")
            for r in by_project:
                lines.append(f"| {r['n']} (`{r['s']}`) | {_money(r['v'])} |")
            lines.append("")

        return "\n".join(lines)

    def project_status(self, project_slug: str) -> str:
        proj = self.tracker.get_project_by_slug(project_slug)
        if not proj:
            return f"Project `{project_slug}` não encontrado."

        lib_count = self.tracker.query(
            "SELECT COUNT(*) n FROM assets WHERE project_id=? AND status='library'",
            (proj["id"],),
        )[0]["n"]
        draft_count = self.tracker.query(
            "SELECT COUNT(*) n FROM assets WHERE project_id=? AND status='draft'",
            (proj["id"],),
        )[0]["n"]
        total_cost = self.tracker.query(
            "SELECT SUM(cost_brl) v FROM generations WHERE project_id=? AND status='done'",
            (proj["id"],),
        )[0]["v"] or 0.0

        lines = [
            f"## Project: {proj['name']}",
            f"- slug: `{proj['slug']}`",
            f"- status: {proj['status']}",
            f"- tags: {proj['tags']}",
            f"- budget: {_money(proj['budget_brl']) if proj['budget_brl'] else '—'}",
            f"- gasto: {_money(total_cost)}",
            f"- library: {lib_count} assets",
            f"- drafts: {draft_count} assets",
        ]
        return "\n".join(lines)
