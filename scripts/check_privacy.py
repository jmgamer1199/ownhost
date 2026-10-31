"""Checks that a PyInstaller exe/binary contains no data about whoever built it.

Searches (decompressing the contents) for this PC's username, computer name, home folder
and IPs. build.ps1 runs it after building.

Usage: python scripts/check_privacy.py dist/Ownhost.exe [more binaries...]
Exits with code 1 if it finds anything.
"""

import getpass
import marshal
import os
import socket
import sys
import tempfile
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ownhost.net import own_ips  # noqa: E402
from ownhost.updates import REPO  # noqa: E402

# The only thing allowed: the repository's public address (new versions are downloaded from there).
# If the account name contains this PC's username, it doesn't count as personal data.
ALLOWED = [REPO.lower().encode()]

# Third-party libraries: their contents don't depend on who builds (avoids false positives
# such as short words that appear inside the Qt DLLs).
THIRD_PARTY = (".dll", ".so", ".pyd", ".dylib")


def personal_strings() -> list[str]:
    found = {getpass.getuser(), socket.gethostname(), str(Path.home())}
    found |= {ip for ip in own_ips() if not ip.startswith("127.")}
    for var in ("USERNAME", "COMPUTERNAME", "USERDOMAIN", "OneDrive"):
        if os.environ.get(var):
            found.add(os.environ[var])
    return sorted(s for s in found if len(s) >= 4)


def contents(path: str):
    """Walks through everything packaged: files and every Python module in the PYZ."""
    archive = CArchiveReader(path)
    for name in archive.toc:
        try:
            data = archive.extract(name)
        except Exception:  # noqa: BLE001 - special entries with no content
            continue
        if not data:
            continue
        if name.startswith("PYZ"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pyz") as f:
                f.write(data)
            pyz = ZlibArchiveReader(f.name)
            for module in pyz.toc:
                code = pyz.extract(module)
                yield f"{name}:{module}", code if isinstance(code, bytes) else marshal.dumps(code)
            os.unlink(f.name)
        else:
            yield name, data


def main() -> int:
    needles = personal_strings()
    problems = 0
    for binary in sys.argv[1:]:
        for name, data in contents(binary):
            if name.lower().endswith(THIRD_PARTY):
                continue
            low = data.lower()
            for allowed in ALLOWED:
                low = low.replace(allowed, b"")
            for n in needles:
                if n.lower().encode() in low:
                    print(f"  {Path(binary).name}: '{n}' appears in {name}!")
                    problems += 1
    if problems:
        print("WARNING: the binary contains data from this computer. Don't share it.")
        return 1
    print(f"Privacy OK: {len(sys.argv) - 1} binary(ies) with no data from this computer "
          f"(checked {len(needles)} items: username, computer name, home folder, IPs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
