"""Entorno limpio para lanzar otros programas desde la app empaquetada.

En Linux, PyInstaller cambia LD_LIBRARY_PATH para que la app use sus propias bibliotecas (las de
Ubuntu 22.04, donde se compila). Si ese valor se hereda, los programas del sistema (/bin/sh, Java,
el servidor de Bedrock...) cargan bibliotecas que no son las suyas y fallan, por ejemplo:
    /bin/sh: symbol lookup error: undefined symbol: rl_trim_arg_from_keyseq
PyInstaller guarda el valor original en LD_LIBRARY_PATH_ORIG: aquí se restaura.
"""

import os
import sys

_LIB_VARS = ("LD_LIBRARY_PATH",)


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    if getattr(sys, "frozen", False) and sys.platform.startswith("linux"):
        for var in _LIB_VARS:
            original = env.pop(f"{var}_ORIG", None)
            if original:
                env[var] = original
            else:
                env.pop(var, None)
    if extra:
        env.update(extra)
    return env
