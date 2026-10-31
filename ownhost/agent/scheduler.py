"""Tareas programadas: copias de seguridad automáticas y reinicio diario."""

import logging
import threading
import time
from datetime import datetime

log = logging.getLogger("ownhost.agent")

CHECK_SECONDS = 30
# Valores por defecto para servidores que nunca han cambiado su programación:
# copia diaria guardando las 7 últimas, sin reinicio programado.
DEFAULT_SCHEDULE = {"backup_hours": 24, "keep_backups": 7, "restart_at": None}


def schedule_of(meta) -> dict:
    return {**DEFAULT_SCHEDULE, **(meta.extra.get("schedule") or {})}


class Scheduler(threading.Thread):
    def __init__(self, manager):
        super().__init__(daemon=True, name="scheduler")
        self.manager = manager
        self._restarted_on: dict[str, str] = {}  # servidor -> día del último reinicio programado

    def run(self) -> None:
        while True:
            time.sleep(CHECK_SECONDS)
            for s in list(self.manager.servers.values()):
                try:
                    self._check(s)
                except Exception:  # noqa: BLE001 - un fallo en un servidor no para a los demás
                    log.exception("Error en las tareas programadas de %s", s.meta.name)

    def _check(self, s) -> None:
        if s.task or s.state in ("starting", "stopping") or not s.server_dir.exists():
            return
        sched = schedule_of(s.meta)

        # Copia automática: cada `backup_hours`, solo si el servidor ha estado encendido desde la última
        # (si lleva días apagado, la copia sería idéntica a la anterior).
        hours = sched.get("backup_hours") or 0
        if hours:
            last = self.manager.last_backup_time(s.meta.id)
            used_since = s.running or (s.meta.extra.get("last_stopped", 0) > (last or 0))
            if used_since and (last is None or time.time() - last >= hours * 3600):
                self.manager.auto_backup(s, int(sched.get("keep_backups") or 7))
                return

        # Reinicio diario a la hora indicada ("HH:MM"), con aviso a los jugadores.
        at = sched.get("restart_at")
        today = datetime.now().strftime("%Y-%m-%d")
        if at and s.state == "running" and datetime.now().strftime("%H:%M") == at \
                and self._restarted_on.get(s.meta.id) != today:
            self._restarted_on[s.meta.id] = today
            self.manager.scheduled_restart(s)
