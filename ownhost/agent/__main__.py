"""Agent: runs on every PC that hosts servers.

    python -m ownhost.agent            # starts the agent
    python -m ownhost.agent --show-token
"""

import argparse
import logging
import socket
import sys
import time
from pathlib import Path

import uvicorn

from ownhost import i18n, updates
from ownhost.agent.api import create_app
from ownhost.agent.config import AgentConfig
from ownhost.agent.manager import ServerManager
from ownhost.i18n import tr
from ownhost.paths import default_data_dir


def main(argv: list[str] | None = None) -> None:
    i18n.set_language(None)  # the system's language for the help text; the saved one is applied below
    parser = argparse.ArgumentParser(prog="ownhost-agent", description=tr("Agente de Ownhost"))
    parser.add_argument("--data-dir", type=Path, default=default_data_dir(),
                        help=tr("carpeta donde se guardan servidores, Java y copias"))
    parser.add_argument("--port", type=int, help=tr("puerto de la API (por defecto 8765)"))
    parser.add_argument("--bind", help=tr("interfaz de red (por defecto 0.0.0.0 = toda la red local)"))
    parser.add_argument("--name", help=tr("nombre de este equipo en la app"))
    parser.add_argument("--show-token", action="store_true", help=tr("muestra el token y sale"))
    args = parser.parse_args(argv)

    data_dir: Path = args.data_dir
    config = AgentConfig.load_or_create(data_dir)
    i18n.set_language(config.language)
    changed = False
    for key in ("port", "bind", "name"):
        value = getattr(args, key)
        if value is not None and value != getattr(config, key):
            setattr(config, key, value)
            changed = True
    if changed:
        config.save(data_dir)

    if args.show_token:
        print(config.token)
        return

    if sys.stderr is None:
        # Inside the console-less .exe there is no stdout/stderr: send it to a file.
        data_dir.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(data_dir / "agent.log", "a", encoding="utf-8", buffering=1)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    print(tr("Agente '{name}' escuchando en {bind}:{port}", name=config.name, bind=config.bind, port=config.port))
    print(tr("Datos en: {folder}", folder=data_dir))
    print(tr("Token para añadir este equipo en la app: {token}", token=config.token))

    wait_for_port(config.bind, config.port)
    updates.cleanup_old()  # Windows: the previous version's .exe, renamed when updating
    app = create_app(config, ServerManager(data_dir))
    uvicorn.run(app, host=config.bind, port=config.port, log_level="warning")


def wait_for_port(host: str, port: int, seconds: float = 60) -> None:
    """After an update the new agent may start before the old one has let go of the port: it waits
    (instead of failing with "address already in use") until it's free."""
    deadline = time.monotonic() + seconds
    warned = False
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if sys.platform != "win32":
                # As uvicorn does: a port left in TIME_WAIT counts as free (on Windows this option
                # would let two programs share it, so it isn't used there).
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
                return
            except OSError:
                if time.monotonic() > deadline:
                    return  # uvicorn will report the error
        if not warned:
            print(tr("El puerto {port} está ocupado; esperando a que se libere...", port=port))
            warned = True
        time.sleep(0.5)


if __name__ == "__main__":
    main()
