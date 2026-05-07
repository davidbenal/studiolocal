"""Gerencia auto-open / auto-close de Sessions.

Regras:
- 1ª Generation no project ativa abre uma Session se não houver uma ativa.
- Cada Generation atualiza last_activity_at da Session ativa.
- Sessions com last_activity_at > idle_minutes (default 60) são auto-fechadas
  no próximo touch ou via cleanup --safe.
"""

from __future__ import annotations

from .tracker import Tracker


class SessionManager:
    def __init__(self, tracker: Tracker, idle_minutes: int = 60):
        self.tracker = tracker
        self.idle_minutes = idle_minutes

    def ensure_session(self, project_id: int) -> int:
        # fecha sessions abandonadas globalmente antes de abrir nova
        for s in self.tracker.find_abandoned_sessions(self.idle_minutes):
            self.tracker.close_session(s["id"])

        active = self.tracker.find_active_session(project_id=project_id)
        if active:
            self.tracker.touch_session(active["id"])
            return active["id"]
        return self.tracker.open_session(project_id=project_id)

    def auto_close_idle(self) -> int:
        count = 0
        for s in self.tracker.find_abandoned_sessions(self.idle_minutes):
            self.tracker.close_session(s["id"])
            count += 1
        return count
