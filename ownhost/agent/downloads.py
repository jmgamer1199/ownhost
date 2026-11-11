import hashlib
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable

import httpx

from ownhost.i18n import tr

Log = Callable[[str], None]

USER_AGENT = "ownhost/0.1 (+https://github.com/)"
# No file Ownhost downloads (Java, servers, mods, modpacks) is bigger than this: it stops a bad host from filling the disk.
MAX_DOWNLOAD = 3 << 30


def http() -> httpx.Client:
    return httpx.Client(follow_redirects=True, timeout=60, headers={"User-Agent": USER_AGENT})


def get_json(url: str, **params):
    with http() as c:
        r = c.get(url, params=params or None)
        r.raise_for_status()
        return r.json()


def get_json_quick(url: str, timeout: float = 6):
    """For lookups the user is waiting for: gives up after a few seconds."""
    with httpx.Client(follow_redirects=True, timeout=timeout, headers={"User-Agent": USER_AGENT}) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.json()


def safe_name(name: str) -> str:
    """A file name that came from a remote service, reduced to the name alone: no folders, no '..'."""
    clean = PurePosixPath(str(name).replace("\\", "/")).name
    if clean in ("", ".", ".."):
        raise ValueError(tr("Nombre de archivo no válido: {name}", name=name))
    return clean


def download(url: str, dest: Path, log: Log, user_agent: str | None = None, *,
             sha256: str | None = None, sha1: str | None = None) -> Path:
    """Downloads `url` to `dest`, reporting progress every 10 %.

    If the publisher gives a checksum (`sha256` or `sha1`), the file is checked and discarded if it doesn't match."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    log(tr("Descargando {url}", url=url))
    headers = {"User-Agent": user_agent} if user_agent else None
    sums = [(name, hashlib.new(name), value.lower()) for name, value in (("sha256", sha256), ("sha1", sha1)) if value]
    try:
        with http() as c, c.stream("GET", url, headers=headers) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length") or 0)
            if total > MAX_DOWNLOAD:
                raise RuntimeError(tr("La descarga es demasiado grande"))
            done, next_report = 0, 10
            with open(tmp, "wb") as f:
                for chunk in r.iter_bytes(1 << 16):
                    f.write(chunk)
                    for _, digest, _ in sums:
                        digest.update(chunk)
                    done += len(chunk)
                    if done > MAX_DOWNLOAD:
                        raise RuntimeError(tr("La descarga es demasiado grande"))
                    if total and done * 100 // total >= next_report:
                        log(f"  {next_report}% ({done // (1 << 20)} MB)")
                        next_report += 10
        for name, digest, expected in sums:
            if digest.hexdigest() != expected:
                raise RuntimeError(tr("La descarga no coincide con su huella {name}; se ha descartado", name=name.upper()))
        tmp.replace(dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return dest


def extract(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            z.extractall(dest)
    else:
        with tarfile.open(archive) as t:
            t.extractall(dest, filter="data")
