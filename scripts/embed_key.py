"""Generates the modules that only exist during the build (build.ps1 deletes them when it finishes):

- ownhost/_build.py: identifier of this build. The app compares it with the one of this PC's agent
  to restart the agent if it is from an older version.
- ownhost/_embedded.py: the obfuscated CurseForge key, if the CURSEFORGE_API_KEY variable or the
  `curseforge.key` file at the project root exists. Note: this is obfuscation, not encryption; someone
  with time could extract it from the exe.

Usage:  python scripts/embed_key.py          -> generates the modules
        python scripts/embed_key.py --clean  -> deletes them
"""

import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "ownhost" / "_embedded.py"
BUILD_FILE = ROOT / "ownhost" / "_build.py"
KEY_FILE = ROOT / "curseforge.key"


def main() -> None:
    if "--clean" in sys.argv:
        TARGET.unlink(missing_ok=True)
        BUILD_FILE.unlink(missing_ok=True)
        return
    build = os.environ.get("OWNHOST_BUILD") or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    BUILD_FILE.write_text(f'# Generated at build time by scripts/embed_key.py.\nBUILD = "{build}"\n', encoding="utf-8")
    print(f"Build {build}")

    key = os.environ.get("CURSEFORGE_API_KEY") or (KEY_FILE.read_text(encoding="utf-8").strip()
                                                   if KEY_FILE.exists() else "")
    if not key:
        print("No CurseForge key: the exe will be built without it.")
        TARGET.unlink(missing_ok=True)
        return
    data = key.encode()
    mask = secrets.token_bytes(len(data))
    hidden = bytes(a ^ b for a, b in zip(data, mask))
    TARGET.write_text(
        "# Generated at build time by scripts/embed_key.py. Do not edit or commit to git.\n"
        f"_A = {list(hidden)!r}\n_B = {list(mask)!r}\n\n\n"
        "def curseforge_key() -> str:\n"
        "    return bytes(a ^ b for a, b in zip(_A, _B)).decode()\n",
        encoding="utf-8",
    )
    print("CurseForge key included (obfuscated) in the exe.")


if __name__ == "__main__":
    main()
