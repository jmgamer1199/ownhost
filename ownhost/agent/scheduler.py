"""Scheduled tasks: automatic backups and daily restart."""

import logging
import threading
import time
from datetime import datetime

from ownhost.i18n import tr

log = logging.getLogger("ownhost.agent")

CHECK_SECONDS = 30
# Defaults for servers that never changed their schedule:
# daily backup keeping the last 7, no scheduled restart.
DEFAULT_SCHEDULE = {"backup_hours": 24, "keep_backups": 7, "restart_at": None, "idle_stop_minutes": 0}
# Only in these games is it known who is online (from the console).
TRACKS_PLAYERS = ("minecraft", "bedrock")


def schedule_of(meta) -> dict:
    return {**DEFAULT_SCHEDULE, **(meta.extra.get("schedule") or {})}


class Scheduler(threading.Thread):
    def __init__(self, manager):
        super().__init__(daemon=True, name="scheduler")
        self.manager = manager
        self._restarted_on: dict[str, str] = {}  # server -> day of the last scheduled restart

    def run(self) -> None:
        while True:
            time.sleep(CHECK_SECONDS)
            for s in list(self.manager.servers.values()):
                try:
                    self._check(s)
                except Exception:  # noqa: BLE001 - a failure in one server does not stop the others
                    log.exception("Error in the scheduled tasks of %s", s.meta.name)

    def _check(self, s) -> None:
        if s.task or s.state in ("starting", "stopping") or not s.server_dir.exists():
            return
        sched = schedule_of(s.meta)

        # Automatic backup: every `backup_hours`, only if the server has been running since the last one
        # (if it has been stopped for days, the backup would be identical to the previous one).
        hours = sched.get("backup_hours") or 0
        if hours:
            last = self.manager.last_backup_time(s.meta.id)
            used_since = s.running or (s.meta.extra.get("last_stopped", 0) > (last or 0))
            if used_since and (last is None or time.time() - last >= hours * 3600):
                self.manager.auto_backup(s, int(sched.get("keep_backups") or 7))
                return

        # Stop if nobody plays for `idle_stop_minutes` (saves power and memory).
        idle = sched.get("idle_stop_minutes") or 0
        if s.state != "running" or s.online or not idle or s.meta.game not in TRACKS_PLAYERS:
            s.empty_since = None
        elif s.empty_since is None:
            s.empty_since = time.time()
        elif time.time() - s.empty_since >= idle * 60:
            s.empty_since = None
            s.log(tr("Nadie ha jugado en {minutes} minutos: se apaga el servidor.", minutes=idle))
            s.event("idle", tr("«{name}» se ha apagado porque nadie jugaba.", name=s.meta.name))
            self.manager.stop(s.meta.id)
            return

        # Daily restart at the given time ("HH:MM"), warning the players.
        at = sched.get("restart_at")
        today = datetime.now().strftime("%Y-%m-%d")
        if at and s.state == "running" and datetime.now().strftime("%H:%M") == at \
                and self._restarted_on.get(s.meta.id) != today:
            self._restarted_on[s.meta.id] = today
            self.manager.scheduled_restart(s)
