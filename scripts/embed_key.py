"""Genera los módulos que solo existen durante la compilación (crear-exe.ps1 los borra al terminar):

- ownhost/_build.py: identificador de esta compilación. La app lo compara con el del agente de este
  PC para reiniciarlo si es de una versión anterior.
- ownhost/_embedded.py: la clave de CurseForge ofuscada, si existe la variable CURSEFORGE_API_KEY o el
  archivo `curseforge.key` en la raíz del proyecto. Ojo: es ofuscación, no cifrado; alguien con
  tiempo podría extraerla del exe.

Uso:  python scripts/embed_key.py          -> genera los módulos
      python scripts/embed_key.py --clean  -> los borra
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
    BUILD_FILE.write_text(f'# Generado al compilar por scripts/embed_key.py.\nBUILD = "{build}"\n', encoding="utf-8")
    print(f"Compilación {build}")

    key = os.environ.get("CURSEFORGE_API_KEY") or (KEY_FILE.read_text(encoding="utf-8").strip()
                                                   if KEY_FILE.exists() else "")
    if not key:
        print("Sin clave de CurseForge: el exe se generará sin ella.")
        TARGET.unlink(missing_ok=True)
        return
    data = key.encode()
    mask = secrets.token_bytes(len(data))
    hidden = bytes(a ^ b for a, b in zip(data, mask))
    TARGET.write_text(
        "# Generado al compilar por scripts/embed_key.py. No editar ni subir a git.\n"
        f"_A = {list(hidden)!r}\n_B = {list(mask)!r}\n\n\n"
        "def curseforge_key() -> str:\n"
        "    return bytes(a ^ b for a, b in zip(_A, _B)).decode()\n",
        encoding="utf-8",
    )
    print("Clave de CurseForge incluida (ofuscada) en el exe.")


if __name__ == "__main__":
    main()
