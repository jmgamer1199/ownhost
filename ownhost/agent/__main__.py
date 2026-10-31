"""Agente: se ejecuta en cada PC que hospeda servidores.

    python -m ownhost.agent            # arranca el agente
    python -m ownhost.agent --show-token
"""

import argparse
import logging
import sys
from pathlib import Path

import uvicorn

from ownhost.agent.api import create_app
from ownhost.agent.config import AgentConfig
from ownhost.agent.manager import ServerManager
from ownhost.paths import default_data_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ownhost-agent", description="Agente de Ownhost")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir(),
                        help="carpeta donde se guardan servidores, Java y copias")
    parser.add_argument("--port", type=int, help="puerto de la API (por defecto 8765)")
    parser.add_argument("--bind", help="interfaz de red (por defecto 0.0.0.0 = toda la red local)")
    parser.add_argument("--name", help="nombre de este equipo en la app")
    parser.add_argument("--show-token", action="store_true", help="muestra el token y sale")
    args = parser.parse_args(argv)

    data_dir: Path = args.data_dir
    config = AgentConfig.load_or_create(data_dir)
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
        # Dentro del .exe sin consola no hay stdout/stderr: lo mandamos a un archivo.
        data_dir.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(data_dir / "agent.log", "a", encoding="utf-8", buffering=1)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    print(f"Agente '{config.name}' escuchando en {config.bind}:{config.port}")
    print(f"Datos en: {data_dir}")
    print(f"Token para añadir este equipo en la app: {config.token}")

    app = create_app(config, ServerManager(data_dir))
    uvicorn.run(app, host=config.bind, port=config.port, log_level="warning")


if __name__ == "__main__":
    main()
