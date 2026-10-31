"""Player statistics: time played, number of sessions and last time they joined.

They are recorded from the joins and leaves the server writes to the console, and saved in
data_dir/stats/<server>.json so they survive agent restarts.
"""

import json
import threading
import time
from pathlib import Path


class PlayerStats:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.players: dict[str, dict] = {}
        self.open: dict[str, float] = {}  # sessions in progress: player -> join time
        if path.exists():
            try:
                self.players = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                self.players = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.players, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def joined(self, name: str, now: float | None = None) -> None:
        now = now or time.time()
        with self.lock:
            p = self.players.setdefault(name, {"seconds": 0, "sessions": 0, "first_seen": now, "last_seen": now})
            p["sessions"] += 1
            p["last_seen"] = now
            self.open[name] = now
            self._save()

    def left(self, name: str, now: float | None = None) -> None:
        now = now or time.time()
        with self.lock:
            self._close(name, now)
            self._save()

    def all_left(self) -> None:
        """The server has stopped: open sessions are closed."""
        now = time.time()
        with self.lock:
            if not self.open:
                return
            for name in list(self.open):
                self._close(name, now)
            self._save()

    def _close(self, name: str, now: float) -> None:
        start = self.open.pop(name, None)
        p = self.players.get(name)
        if p is None or start is None:
            return
        p["seconds"] += int(now - start)
        p["last_seen"] = now

    def summary(self) -> list[dict]:
        """Players sorted by time played (including the session in progress)."""
        now = time.time()
        with self.lock:
            rows = []
            for name, p in self.players.items():
                online = name in self.open
                rows.append({"name": name, "seconds": p["seconds"] + (int(now - self.open[name]) if online else 0),
                             "sessions": p["sessions"], "first_seen": p["first_seen"],
                             "last_seen": now if online else p["last_seen"], "online": online})
        return sorted(rows, key=lambda r: r["seconds"], reverse=True)
