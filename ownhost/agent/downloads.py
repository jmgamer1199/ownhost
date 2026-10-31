import tarfile
import zipfile
from pathlib import Path
from typing import Callable

import httpx

from ownhost.i18n import tr

Log = Callable[[str], None]

USER_AGENT = "ownhost/0.1 (+https://github.com/)"


def http() -> httpx.Client:
    return httpx.Client(follow_redirects=True, timeout=60, headers={"User-Agent": USER_AGENT})


def get_json(url: str, **params):
    with http() as c:
        r = c.get(url, params=params or None)
        r.raise_for_status()
        return r.json()


def download(url: str, dest: Path, log: Log, user_agent: str | None = None) -> Path:
    """Downloads `url` to `dest`, reporting progress every 10 %."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    log(tr("Descargando {url}", url=url))
    headers = {"User-Agent": user_agent} if user_agent else None
    with http() as c, c.stream("GET", url, headers=headers) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length") or 0)
        done, next_report = 0, 10
        with open(tmp, "wb") as f:
            for chunk in r.iter_bytes(1 << 16):
                f.write(chunk)
                done += len(chunk)
                if total and done * 100 // total >= next_report:
                    log(f"  {next_report}% ({done // (1 << 20)} MB)")
                    next_report += 10
    tmp.replace(dest)
    return dest


def extract(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)
    else:
        with tarfile.open(archive) as t:
            t.extractall(dest, filter="data")
