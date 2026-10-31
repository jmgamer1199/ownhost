"""Historial de rendimiento: CPU, RAM y jugadores de cada servidor, y uso de disco.

Se toma una muestra por minuto de cada servidor encendido y se guardan las últimas 24 horas.
El historial se escribe a disco de vez en cuando para que sobreviva a un reinicio del agente.
"""

import json
import logging
import shutil
import threading
import time
from collections import deque
from pathlib import Path

log = logging.getLogger("ownhost.agent")

SAMPLE_SECONDS = 60
KEEP_SECONDS = 24 * 3600
SAVE_EVERY = 10  # muestras entre guardados
DISK_CACHE_SECONDS = 300


def folder_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for p in path.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            pass
    return total


class Metrics(threading.Thread):
    def __init__(self, manager):
        super().__init__(daemon=True, name="metrics")
        self.manager = manager
        self.folder = manager.data_dir / "metrics"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.history: dict[str, deque] = {}
        self._disk: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()

    # ---------- historial ----------

    def _series(self, server_id: str) -> deque:
        if server_id not in self.history:
            points = deque(maxlen=KEEP_SECONDS // SAMPLE_SECONDS + 10)
            try:
                saved = json.loads((self.folder / f"{server_id}.json").read_text(encoding="utf-8"))
                cutoff = time.time() - KEEP_SECONDS
                points.extend(p for p in saved if p[0] >= cutoff)
            except (OSError, ValueError):
                pass
            self.history[server_id] = points
        return self.history[server_id]

    def run(self) -> None:
        count = 0
        while True:
            time.sleep(SAMPLE_SECONDS)
            now = int(time.time())
            with self._lock:
                for s in list(self.manager.servers.values()):
                    if s.state != "running":
                        continue
                    st = s.stats()
                    if st:
                        self._series(s.meta.id).append([now, st["cpu_percent"], st["memory_mb"], len(s.online)])
            count += 1
            if count % SAVE_EVERY == 0:
                self.save()

    def save(self) -> None:
        with self._lock:
            for sid, points in self.history.items():
                if sid not in self.manager.servers:
                    continue
                try:
                    (self.folder / f"{sid}.json").write_text(json.dumps(list(points)), encoding="utf-8")
                except OSError:
                    log.exception("No se pudo guardar el historial de %s", sid)

    def forget(self, server_id: str) -> None:
        with self._lock:
            self.history.pop(server_id, None)
            self._disk.pop(server_id, None)
            (self.folder / f"{server_id}.json").unlink(missing_ok=True)

    def points(self, server_id: str, hours: float) -> list:
        cutoff = time.time() - hours * 3600
        with self._lock:
            return [p for p in self._series(server_id) if p[0] >= cutoff]

    # ---------- disco ----------

    def disk(self, s) -> dict:
        """Tamaño del servidor y de sus copias, y espacio del disco. Recorrer un mundo grande es lento:
        se guarda unos minutos."""
        cached = self._disk.get(s.meta.id)
        if cached and time.time() - cached[0] < DISK_CACHE_SECONDS:
            return cached[1]
        usage = shutil.disk_usage(self.manager.data_dir)
        info = {"server_bytes": folder_size(s.server_dir),
                "backups_bytes": folder_size(self.manager.backups_dir / s.meta.id),
                "disk_total": usage.total, "disk_free": usage.free}
        self._disk[s.meta.id] = (time.time(), info)
        return info
