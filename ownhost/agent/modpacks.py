"""Importar modpacks: .mrpack de Modrinth y .zip de CurseForge.

Un modpack trae la versión de Minecraft, el loader (Fabric, Forge o NeoForge) y su versión, la lista de
mods (con su enlace o su id de CurseForge) y una carpeta «overrides» con la configuración. Aquí se lee
todo eso, se descargan los mods que hacen falta en un servidor (los de solo cliente se descartan) y se
copian los overrides.
"""

import hashlib
import json
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from ownhost.agent.downloads import Log, download
from ownhost.agent.errors import UserError
from ownhost.agent.mods import CURSEFORGE, _client, _require_cf_key, load_metadata, save_metadata

CF_SERVER_TAG = "Server"
CF_CLIENT_TAG = "Client"
# Dominios desde los que un .mrpack puede descargar archivos (lo exige el formato de Modrinth).
MRPACK_HOSTS = ("cdn.modrinth.com", "github.com", "raw.githubusercontent.com", "gitlab.com")


@dataclass
class PackFile:
    path: str               # ruta dentro del servidor, p. ej. "mods/sodium.jar"
    url: str | None = None
    sha1: str | None = None
    size: int = 0
    cf_project: int | None = None
    cf_file: int | None = None
    title: str = ""
    version: str = ""


@dataclass
class Pack:
    kind: str                # "modrinth" o "curseforge"
    name: str
    version: str             # versión del modpack
    minecraft: str
    flavor: str              # fabric, forge o neoforge
    loader_version: str
    files: list[PackFile] = field(default_factory=list)
    overrides: list[str] = field(default_factory=list)  # carpetas dentro del zip, en orden


def _safe_path(rel: str) -> str:
    """Ruta relativa sin trucos (../, absolutas, unidades de Windows)."""
    p = PurePosixPath(rel.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or not p.parts or ":" in p.parts[0]:
        raise UserError(f"El modpack tiene una ruta no válida: {rel}")
    return str(p)


def read(archive: Path) -> Pack:
    try:
        z = zipfile.ZipFile(archive)
    except zipfile.BadZipFile:
        raise UserError("El archivo no es un modpack (.mrpack o .zip de CurseForge)") from None
    with z:
        names = set(z.namelist())
        if "modrinth.index.json" in names:
            return _read_mrpack(json.loads(z.read("modrinth.index.json")))
        if "manifest.json" in names:
            return _read_curseforge(json.loads(z.read("manifest.json")))
    raise UserError("No encuentro la descripción del modpack (modrinth.index.json o manifest.json). "
                    "Si es de CurseForge, descarga el modpack completo, no solo el servidor.")


def _read_mrpack(index: dict) -> Pack:
    if index.get("game") != "minecraft":
        raise UserError("El modpack no es de Minecraft")
    deps = index.get("dependencies", {})
    for key, flavor in (("fabric-loader", "fabric"), ("neoforge", "neoforge"), ("forge", "forge")):
        if key in deps:
            break
    else:
        if "quilt-loader" in deps:
            raise UserError("Los modpacks de Quilt no están soportados (solo Fabric, Forge y NeoForge)")
        raise UserError("El modpack no indica Fabric, Forge ni NeoForge")
    pack = Pack(kind="modrinth", name=index.get("name") or "Modpack", version=index.get("versionId", ""),
                minecraft=deps["minecraft"], flavor=flavor, loader_version=deps[key],
                overrides=["overrides", "server-overrides"])
    for f in index.get("files", []):
        if (f.get("env") or {}).get("server") == "unsupported":
            continue  # solo cliente (shaders, minimapas...)
        urls = [u for u in f.get("downloads", []) if u.split("/")[2] in MRPACK_HOSTS]
        if not urls:
            continue
        pack.files.append(PackFile(path=_safe_path(f["path"]), url=urls[0], sha1=f.get("hashes", {}).get("sha1"),
                                   size=f.get("fileSize", 0)))
    return pack


def _read_curseforge(manifest: dict) -> Pack:
    mc = manifest.get("minecraft") or {}
    loaders = mc.get("modLoaders") or []
    loader = next((l["id"] for l in loaders if l.get("primary")), loaders[0]["id"] if loaders else "")
    kind, _, version = loader.partition("-")
    if kind not in ("fabric", "forge", "neoforge"):
        raise UserError(f"Loader no soportado en el modpack: {loader or 'ninguno'}")
    pack = Pack(kind="curseforge", name=manifest.get("name") or "Modpack", version=manifest.get("version", ""),
                minecraft=mc.get("version", ""), flavor=kind, loader_version=version,
                overrides=[manifest.get("overrides") or "overrides"])
    for f in manifest.get("files", []):
        if f.get("required", True):
            pack.files.append(PackFile(path="", cf_project=f["projectID"], cf_file=f["fileID"]))
    return pack


def install(pack: Pack, archive: Path, server_dir: Path, cf_key: str | None, log: Log) -> list[str]:
    """Descarga los mods y copia los overrides. Devuelve los mods que hay que bajar a mano."""
    manual: list[str] = []
    if pack.kind == "curseforge" and pack.files:
        _resolve_curseforge(pack, _require_cf_key(cf_key), manual, log)
    files = [f for f in pack.files if f.url]
    for i, f in enumerate(files, 1):
        dest = server_dir / f.path
        dest.parent.mkdir(parents=True, exist_ok=True)
        log(f"[{i}/{len(files)}] {PurePosixPath(f.path).name}")
        download(f.url, dest, lambda _msg: None)
        if f.sha1 and hashlib.sha1(dest.read_bytes()).hexdigest() != f.sha1:
            dest.unlink(missing_ok=True)
            raise UserError(f"El archivo {f.path} no coincide con el del modpack (descarga corrupta). "
                            "Vuelve a intentarlo.")

    # Los de CurseForge se apuntan con su proyecto, para poder buscarles actualizaciones luego.
    # (Los de Modrinth no hace falta: se reconocen por su hash.)
    mods_dir = server_dir / "mods"
    meta = load_metadata(mods_dir) if mods_dir.exists() else {}
    for f in files:
        if not f.path.startswith("mods/"):
            continue
        name = PurePosixPath(f.path).name
        if f.cf_project:
            meta[name] = {"source": "curseforge", "project_id": str(f.cf_project), "title": f.title,
                          "version": f.version}
        else:
            meta[name] = {"source": "modpack"}
    if meta:
        save_metadata(mods_dir, meta)

    log("Copiando la configuración del modpack...")
    with zipfile.ZipFile(archive) as z:
        for prefix in pack.overrides:
            for info in z.infolist():
                if info.is_dir() or not info.filename.startswith(prefix + "/"):
                    continue
                rel = _safe_path(info.filename[len(prefix) + 1:])
                dest = server_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
    return manual


def _resolve_curseforge(pack: Pack, cf_key: str, manual: list[str], log: Log) -> None:
    """Convierte los ids de CurseForge en enlaces de descarga y descarta los mods de solo cliente."""
    log(f"Consultando {len(pack.files)} mods en CurseForge...")
    ids = [f.cf_file for f in pack.files]
    with _client(cf_key) as c:
        r = c.post(f"{CURSEFORGE}/mods/files", json={"fileIds": ids})
        if r.status_code in (401, 403):
            raise UserError("CurseForge ha rechazado la clave de API. Revísala en Ajustes.")
        r.raise_for_status()
        files = {f["id"]: f for f in r.json()["data"]}
        r = c.post(f"{CURSEFORGE}/mods", json={"modIds": list({f.cf_project for f in pack.files})})
        r.raise_for_status()
        mods = {m["id"]: m for m in r.json()["data"]}
    kept = []
    for f in pack.files:
        info = files.get(f.cf_file)
        mod = mods.get(f.cf_project, {})
        if not info:
            manual.append(mod.get("name") or str(f.cf_project))
            continue
        tags = set(info.get("gameVersions") or [])
        if CF_CLIENT_TAG in tags and CF_SERVER_TAG not in tags:
            continue  # solo cliente
        # Paquetes de recursos y shaders van en otras carpetas y no los usa el servidor
        folder = {12: "resourcepacks", 6552: "shaderpacks"}.get(mod.get("classId"), "mods")
        if folder != "mods":
            continue
        if not info.get("downloadUrl"):
            # El autor no deja descargarlo desde otras apps: hay que bajarlo a mano.
            link = (mod.get("links") or {}).get("websiteUrl", "")
            manual.append(f"{mod.get('name', info['fileName'])} ({link}/files/{f.cf_file})")
            continue
        sha1 = next((h["value"] for h in info.get("hashes", []) if h.get("algo") == 1), None)
        kept.append(PackFile(path=f"mods/{_safe_path(info['fileName'])}", url=info["downloadUrl"], sha1=sha1,
                             cf_project=f.cf_project, cf_file=f.cf_file, title=mod.get("name", ""),
                             version=info.get("displayName", "")))
    pack.files = kept
