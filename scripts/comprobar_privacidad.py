"""Comprueba que un exe/binario de PyInstaller no contiene datos de quien lo compila.

Busca (descomprimiendo el contenido) el nombre de usuario, el nombre del equipo, la carpeta
personal y las IPs de este PC. Lo ejecuta crear-exe.ps1 después de compilar.

Uso: python scripts/comprobar_privacidad.py dist/Ownhost.exe [más binarios...]
Sale con código 1 si encuentra algo.
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

# Lo único que se permite: la dirección pública del repositorio (de ahí se descargan las versiones
# nuevas). Si el nombre de la cuenta contiene el usuario de este PC, no cuenta como dato personal.
ALLOWED = [REPO.lower().encode()]

# Bibliotecas de terceros: sus textos no dependen de quién compila (evita falsos positivos
# como palabras cortas que aparecen dentro de las DLL de Qt).
THIRD_PARTY = (".dll", ".so", ".pyd", ".dylib")


def personal_strings() -> list[str]:
    found = {getpass.getuser(), socket.gethostname(), str(Path.home())}
    found |= {ip for ip in own_ips() if not ip.startswith("127.")}
    for var in ("USERNAME", "COMPUTERNAME", "USERDOMAIN", "OneDrive"):
        if os.environ.get(var):
            found.add(os.environ[var])
    return sorted(s for s in found if len(s) >= 4)


def contents(path: str):
    """Recorre todo lo empaquetado: archivos y cada módulo de Python del PYZ."""
    archive = CArchiveReader(path)
    for name in archive.toc:
        try:
            data = archive.extract(name)
        except Exception:  # noqa: BLE001 - entradas especiales sin contenido
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
                    print(f"  ¡{Path(binary).name}: «{n}» aparece en {name}!")
                    problems += 1
    if problems:
        print("AVISO: el binario contiene datos de este equipo. No lo compartas.")
        return 1
    print(f"Privacidad OK: {len(sys.argv) - 1} binario(s) sin datos de este equipo "
          f"(revisados {len(needles)} datos: usuario, equipo, carpeta personal, IPs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
