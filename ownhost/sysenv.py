"""Clean environment for launching other programs from the packaged app.

On Linux, PyInstaller changes LD_LIBRARY_PATH so the app uses its own libraries (those of
Ubuntu 22.04, where it is built). If that value is inherited, system programs (/bin/sh, Java,
the Bedrock server...) load libraries that are not theirs and fail, for example:
    /bin/sh: symbol lookup error: undefined symbol: rl_trim_arg_from_keyseq
PyInstaller keeps the original value in LD_LIBRARY_PATH_ORIG: it is restored here.
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
