"""Búsqueda e instalación de mods/plugins desde Modrinth y CurseForge."""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import httpx

from ownhost.agent.downloads import USER_AGENT, Log, download
from ownhost.agent.errors import UserError

MODRINTH = "https://api.modrinth.com/v2"
CURSEFORGE = "https://api.curseforge.com/v1"
CF_MINECRAFT = 432
CF_REQUIRED = 3  # relationType de una dependencia obligatoria
MAX_DEPENDENCY_DEPTH = 4
METADATA_FILE = ".ownhost-mods.json"


@dataclass
class ModTarget:
    """Qué tipo de mods acepta un servidor y dónde se guardan."""
    folder: str                  # "mods" o "plugins"
    label: str                   # texto para la interfaz
    modrinth_type: str           # project_type en Modrinth
    modrinth_loaders: list[str]
    cf_class: int | str | None   # classId en CurseForge (6 = mods, 5 = plugins Bukkit) o su slug
    cf_loader: int | None = None  # modLoaderType en CurseForge (4 = Fabric)
    server_side_only: bool = False  # descartar mods que solo funcionan en el cliente
    cf_game: int | str = CF_MINECRAFT  # id del juego en CurseForge, o su slug («hytale»)
    match_version: bool = True   # filtrar por la versión del juego (Hytale no tiene versiones fijas)
    sources: tuple[str, ...] = ("modrinth", "curseforge")
    extensions: tuple[str, ...] = (".jar",)

    def is_mod_file(self, name: str) -> bool:
        return name.removesuffix(".disabled").endswith(self.extensions)


def _client(cf_key: str | None = None) -> httpx.Client:
    headers = {"User-Agent": USER_AGENT}
    if cf_key:
        headers["x-api-key"] = cf_key
    return httpx.Client(timeout=30, follow_redirects=True, headers=headers)


def _get(url: str, cf_key: str | None = None, **params):
    with _client(cf_key) as c:
        r = c.get(url, params=params)
    if r.status_code in (401, 403) and url.startswith(CURSEFORGE):
        raise UserError("CurseForge ha rechazado la clave de API. Revísala en Ajustes.")
    r.raise_for_status()
    return r.json()


@lru_cache(maxsize=8)
def _cf_ids(cf_key: str, game: int | str, cls: int | str | None) -> tuple[int, int | None]:
    """Ids numéricos del juego y de la clase en CurseForge (los de Hytale se buscan por su nombre)."""
    if isinstance(game, int):
        game_id = game
    else:
        games = _get(f"{CURSEFORGE}/games", cf_key, pageSize=50)["data"]
        game_id = next((g["id"] for g in games if g["slug"] == game), None)
        if game_id is None:
            raise UserError(f"CurseForge no tiene mods de {game} para tu clave de API")
    if cls is None or isinstance(cls, int):
        return game_id, cls
    classes = _get(f"{CURSEFORGE}/categories", cf_key, gameId=game_id, classesOnly="true")["data"]
    return game_id, next((c["id"] for c in classes if c["slug"] == cls), None)


def _require_cf_key(cf_key: str | None) -> str:
    if not cf_key:
        raise UserError("Para usar CurseForge necesitas una clave de API gratuita. "
                        "Consíguela en console.curseforge.com y ponla en Ajustes.")
    return cf_key


# ---------- búsqueda ----------

def search(source: str, target: ModTarget, game_version: str, query: str,
           cf_key: str | None, offset: int = 0) -> list[dict]:
    if source not in target.sources:
        raise UserError(f"Este servidor no admite mods de {source}")
    if source == "modrinth":
        return _search_modrinth(target, game_version, query, offset)
    if source == "curseforge":
        return _search_curseforge(target, game_version, query, _require_cf_key(cf_key), offset)
    raise UserError(f"Origen desconocido: {source}")


def _search_modrinth(target: ModTarget, game_version: str, query: str, offset: int) -> list[dict]:
    facets = [
        [f"project_type:{target.modrinth_type}"],
        [f"categories:{loader}" for loader in target.modrinth_loaders],
        [f"versions:{game_version}"],
    ]
    if target.server_side_only:
        facets.append(["server_side:required", "server_side:optional"])
    data = _get(f"{MODRINTH}/search", query=query, facets=json.dumps(facets), limit=25, offset=offset,
                index="relevance" if query else "downloads")
    return [{
        "id": h["project_id"],
        "title": h["title"],
        "description": h["description"],
        "author": h["author"],
        "downloads": h["downloads"],
        "url": f"https://modrinth.com/{h['project_type']}/{h['slug']}",
    } for h in data["hits"]]


def _search_curseforge(target: ModTarget, game_version: str, query: str, cf_key: str,
                       offset: int) -> list[dict]:
    game_id, class_id = _cf_ids(cf_key, target.cf_game, target.cf_class)
    params = {"gameId": game_id, "searchFilter": query, "sortField": 2, "sortOrder": "desc",
              "pageSize": 25, "index": offset}
    if class_id is not None:
        params["classId"] = class_id
    if target.match_version:
        params["gameVersion"] = game_version
    if target.cf_loader is not None:
        params["modLoaderType"] = target.cf_loader
    data = _get(f"{CURSEFORGE}/mods/search", cf_key, **params)
    return [{
        "id": str(m["id"]),
        "title": m["name"],
        "description": m["summary"],
        "author": m["authors"][0]["name"] if m.get("authors") else "",
        "downloads": int(m.get("downloadCount", 0)),
        "url": (m.get("links") or {}).get("websiteUrl") or "",
    } for m in data["data"]]


# ---------- instalación ----------

def load_metadata(folder: Path) -> dict[str, dict]:
    path = folder / METADATA_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_metadata(folder: Path, meta: dict[str, dict]) -> None:
    (folder / METADATA_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def install(source: str, project_id: str, target: ModTarget, game_version: str, folder: Path,
            cf_key: str | None, log: Log) -> list[str]:
    """Instala el proyecto y sus dependencias obligatorias. Devuelve los archivos añadidos."""
    folder.mkdir(parents=True, exist_ok=True)
    meta = load_metadata(folder)
    installed_ids = {(m["source"], m["project_id"]) for m in meta.values()}
    added: list[str] = []
    if source == "curseforge":
        cf_key = _require_cf_key(cf_key)

    def visit(pid: str, depth: int) -> None:
        if (source, pid) in installed_ids or depth > MAX_DEPENDENCY_DEPTH:
            return
        installed_ids.add((source, pid))
        if source == "modrinth":
            info = _modrinth_file(pid, target, game_version)
        else:
            info = _curseforge_file(pid, target, game_version, cf_key)
        dest = folder / info["filename"]
        download(info["url"], dest, log)
        meta[info["filename"]] = {"source": source, "project_id": pid, "title": info["title"],
                                  "version": info["version"]}
        save_metadata(folder, meta)
        added.append(info["filename"])
        for dep in info["dependencies"]:
            log(f"Instalando dependencia de {info['title']}...")
            try:
                visit(dep, depth + 1)
            except UserError as e:
                log(f"AVISO: no se pudo instalar una dependencia: {e}")

    visit(project_id, 0)
    return added


def _modrinth_file(project_id: str, target: ModTarget, game_version: str) -> dict:
    versions = _get(f"{MODRINTH}/project/{project_id}/version",
                    loaders=json.dumps(target.modrinth_loaders), game_versions=json.dumps([game_version]))
    if not versions:
        raise UserError(f"No hay una versión de este proyecto para {game_version}")
    version = next((v for v in versions if v["version_type"] == "release"), versions[0])
    file = next((f for f in version["files"] if f["primary"]), version["files"][0])
    project = _get(f"{MODRINTH}/project/{project_id}")
    return {
        "filename": file["filename"],
        "url": file["url"],
        "title": project["title"],
        "version": version["version_number"],
        "dependencies": [d["project_id"] for d in version["dependencies"]
                         if d["dependency_type"] == "required" and d.get("project_id")],
    }


def _curseforge_file(mod_id: str, target: ModTarget, game_version: str, cf_key: str) -> dict:
    params = {"pageSize": 50}
    if target.match_version:
        params["gameVersion"] = game_version
    if target.cf_loader is not None:
        params["modLoaderType"] = target.cf_loader
    files = _get(f"{CURSEFORGE}/mods/{mod_id}/files", cf_key, **params)["data"]
    if not files:
        raise UserError(f"No hay una versión de este proyecto para {game_version}" if target.match_version
                        else "Este proyecto no tiene archivos para descargar")
    files.sort(key=lambda f: f["fileDate"], reverse=True)
    file = next((f for f in files if f["releaseType"] == 1), files[0])
    mod = _get(f"{CURSEFORGE}/mods/{mod_id}", cf_key)["data"]
    if not file.get("downloadUrl"):
        # El autor ha desactivado las descargas desde apps de terceros.
        raise UserError(f"El autor de «{mod['name']}» no permite descargarlo desde otras apps. "
                        f"Descárgalo desde su página: {(mod.get('links') or {}).get('websiteUrl', '')}")
    return {
        "filename": file["fileName"],
        "url": file["downloadUrl"],
        "title": mod["name"],
        "version": file["displayName"],
        "dependencies": [str(d["modId"]) for d in file.get("dependencies", [])
                         if d["relationType"] == CF_REQUIRED],
    }


# ---------- listar / borrar ----------

def list_installed(folder: Path, target: ModTarget) -> list[dict]:
    if not folder.exists():
        return []
    meta = load_metadata(folder)
    result = []
    for f in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
        if not f.is_file() or not target.is_mod_file(f.name):
            continue
        name = f.name.removesuffix(".disabled")
        info = meta.get(name, {})
        result.append({
            "filename": name,
            "enabled": not f.name.endswith(".disabled"),
            "title": info.get("title") or name,
            "version": info.get("version", ""),
            "source": info.get("source", "manual"),
            "size_kb": f.stat().st_size // 1024,
        })
    return result


def _mod_path(folder: Path, filename: str) -> Path:
    path = (folder / filename).resolve()
    if path.parent != folder.resolve():
        raise UserError("Nombre de archivo no válido")
    return path


def remove(folder: Path, filename: str) -> None:
    for candidate in (filename, filename + ".disabled"):
        path = _mod_path(folder, candidate)
        if path.exists():
            path.unlink()
    meta = load_metadata(folder)
    if meta.pop(filename, None) is not None:
        save_metadata(folder, meta)


def set_enabled(folder: Path, filename: str, enabled: bool) -> None:
    on, off = _mod_path(folder, filename), _mod_path(folder, filename + ".disabled")
    if enabled and off.exists():
        off.rename(on)
    elif not enabled and on.exists():
        on.rename(off)


# ---------- actualizaciones ----------

def _mod_files(folder: Path, target: ModTarget) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and target.is_mod_file(p.name))


def check_updates(folder: Path, target: ModTarget, game_version: str, cf_key: str | None) -> list[dict]:
    """Mods con una versión más nueva para esta versión de Minecraft y este loader.

    Los de Modrinth se reconocen por su hash, aunque no se instalaran desde la app (p. ej. los de un
    modpack o copiados a mano). Los de CurseForge, por lo que apuntó la app al instalarlos.
    """
    if not folder.exists():
        return []
    meta = load_metadata(folder)
    jars = _mod_files(folder, target) if "modrinth" in target.sources else []
    by_hash = {hashlib.sha1(p.read_bytes()).hexdigest(): p for p in jars}
    updates: list[dict] = []
    seen: set[str] = set()

    if by_hash:
        with _client() as c:
            r = c.post(f"{MODRINTH}/version_files/update",
                       json={"hashes": list(by_hash), "algorithm": "sha1", "loaders": target.modrinth_loaders,
                             "game_versions": [game_version]})
        latest = r.json() if r.status_code == 200 else {}
        found = {h: v for h, v in latest.items() if h in by_hash}
        titles = {}
        if found:
            ids = list({v["project_id"] for v in found.values()})
            projects = _get(f"{MODRINTH}/projects", ids=json.dumps(ids))
            titles = {p["id"]: p["title"] for p in projects}
        for h, version in found.items():
            path = by_hash[h]
            name = path.name.removesuffix(".disabled")
            seen.add(name)
            file = next((f for f in version["files"] if f["primary"]), version["files"][0])
            if file["hashes"].get("sha1") == h:
                continue  # ya es la última
            updates.append({"filename": name, "title": titles.get(version["project_id"], name),
                            "current": meta.get(name, {}).get("version", ""), "latest": version["version_number"],
                            "source": "modrinth", "project_id": version["project_id"],
                            "new_filename": file["filename"], "url": file["url"]})

    if cf_key:
        for name, info in meta.items():
            if info.get("source") != "curseforge" or name in seen or not (folder / name).exists() \
                    and not (folder / (name + ".disabled")).exists():
                continue
            try:
                new = _curseforge_file(info["project_id"], target, game_version, cf_key)
            except (UserError, httpx.HTTPError):
                continue
            if new["filename"] != name:
                updates.append({"filename": name, "title": info.get("title") or name,
                                "current": info.get("version", ""), "latest": new["version"],
                                "source": "curseforge", "project_id": info["project_id"],
                                "new_filename": new["filename"], "url": new["url"]})
    return sorted(updates, key=lambda u: u["title"].lower())


def apply_update(folder: Path, update: dict) -> None:
    """Cambia un mod por su versión nueva, conservando si estaba desactivado."""
    old = _mod_path(folder, update["filename"])
    disabled = not old.exists() and _mod_path(folder, update["filename"] + ".disabled").exists()
    new_name = _mod_path(folder, update["new_filename"]).name
    tmp = folder / (new_name + ".part-update")
    download(update["url"], tmp, lambda _msg: None)
    remove(folder, update["filename"])
    tmp.rename(folder / (new_name + (".disabled" if disabled else "")))
    meta = load_metadata(folder)
    meta[new_name] = {"source": update["source"], "project_id": update["project_id"],
                      "title": update["title"], "version": update["latest"]}
    save_metadata(folder, meta)
