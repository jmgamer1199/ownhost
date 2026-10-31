import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from ownhost.agent.downloads import download, get_json, http
from ownhost.agent.games.base import (
    Flavor, GameAdapter, InstallContext, read_properties, run_logged, write_properties,
)
from ownhost.agent.models import ServerMeta
from ownhost.agent.mods import ModTarget

MOJANG_MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
PAPER_API = "https://fill.papermc.io/v3/projects/paper"
FABRIC_META = "https://meta.fabricmc.net/v2"
FORGE_PROMOS = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
FORGE_MAVEN = "https://maven.minecraftforge.net/net/minecraftforge/forge"
NEOFORGE_MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge"

CACHE_SECONDS = 600
LOADERS = ("forge", "neoforge")


def version_key(version: str) -> tuple[int, ...]:
    """'1.21.1' -> (1, 21, 1); ignora sufijos como '-beta'."""
    return tuple(int(p) for p in re.findall(r"\d+", version.split("-")[0]))


def neoforge_mc_version(neo: str) -> str:
    """Versión de Minecraft a la que corresponde una versión de NeoForge.

    Antiguo: 21.1.77 -> 1.21.1, 21.0.5 -> 1.21.  Nuevo (desde MC 26): 26.1.2.123 -> 26.1.2, 26.3.0.99 -> 26.3.
    """
    parts = version_key(neo) + (0, 0, 0)
    if parts[0] >= 25:
        major, minor, patch = parts[0], parts[1], parts[2]
        return f"{major}.{minor}" + (f".{patch}" if patch else "")
    major, minor = parts[0], parts[1]
    return f"1.{major}" + (f".{minor}" if minor else "")


class MinecraftAdapter(GameAdapter):
    id = "minecraft"
    name = "Minecraft (Java)"
    default_port = 25565
    needs_eula = True
    flavors = [
        Flavor("vanilla", "Vanilla"),
        Flavor("paper", "Paper (plugins)"),
        Flavor("fabric", "Fabric (mods)"),
        Flavor("forge", "Forge (mods)"),
        Flavor("neoforge", "NeoForge (mods)"),
    ]
    ready_pattern = re.compile(r"Done \([\d.,]+s\)! For help")
    properties_file = "server.properties"
    backup_pre_commands = ["save-off", "save-all flush"]
    backup_post_commands = ["save-on"]

    def __init__(self):
        self._cache: dict[str, tuple[float, object]] = {}

    def _cached(self, key: str, fetch):
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < CACHE_SECONDS:
            return hit[1]
        value = fetch()
        self._cache[key] = (time.time(), value)
        return value

    def _manifest(self) -> dict:
        return self._cached("manifest", lambda: get_json(MOJANG_MANIFEST))

    def _version_json(self, version: str) -> dict:
        def fetch():
            for v in self._manifest()["versions"]:
                if v["id"] == version:
                    return get_json(v["url"])
            raise ValueError(f"Versión de Minecraft desconocida: {version}")
        return self._cached(f"version:{version}", fetch)

    def _forge_promos(self) -> dict[str, str]:
        return self._cached("forge", lambda: get_json(FORGE_PROMOS)["promos"])

    def _neoforge_versions(self) -> list[str]:
        def fetch():
            with http() as c:
                r = c.get(f"{NEOFORGE_MAVEN}/maven-metadata.xml")
                r.raise_for_status()
            return [v.text for v in ET.fromstring(r.text).iter("version")]
        return self._cached("neoforge", fetch)

    def versions(self, flavor: str) -> list[str]:
        if flavor == "vanilla":
            return [v["id"] for v in self._manifest()["versions"] if v["type"] == "release"]
        if flavor == "paper":
            groups = self._cached("paper", lambda: get_json(PAPER_API))["versions"]
            # Solo versiones estables (sin -rc, -pre...).
            return [v for group in groups.values() for v in group if "-" not in v]
        if flavor == "fabric":
            games = self._cached("fabric", lambda: get_json(f"{FABRIC_META}/versions/game"))
            return [g["version"] for g in games if g["stable"]]
        if flavor in LOADERS:
            if flavor == "forge":
                mcs = {key.rsplit("-", 1)[0] for key in self._forge_promos()}
            else:
                mcs = {neoforge_mc_version(v) for v in self._neoforge_versions()}
            # Descarta versiones raras (snapshots, bromas de abril...) que no son releases de Mojang.
            releases = set(self.versions("vanilla"))
            return sorted(mcs & releases, key=version_key, reverse=True)
        raise ValueError(f"Tipo desconocido: {flavor}")

    def java_major(self, flavor: str, version: str) -> int:
        return self._version_json(version).get("javaVersion", {}).get("majorVersion", 8)

    def _loader_version(self, flavor: str, mc: str) -> str:
        """Última versión del loader (estable si la hay) para una versión de Minecraft."""
        if flavor == "forge":
            promos = self._forge_promos()
            version = promos.get(f"{mc}-recommended") or promos.get(f"{mc}-latest")
            if not version:
                raise ValueError(f"No hay Forge para Minecraft {mc}")
            return version
        candidates = [v for v in self._neoforge_versions() if neoforge_mc_version(v) == mc]
        if not candidates:
            raise ValueError(f"No hay NeoForge para Minecraft {mc}")
        stable = [v for v in candidates if "beta" not in v and "alpha" not in v]
        return max(stable or candidates, key=version_key)

    def available_update(self, meta: ServerMeta, tools_dir: Path) -> str | None:
        # Solo builds nuevas de la MISMA versión de Minecraft: cambiar de versión puede romper
        # mundos y mods, así que eso se hace a mano con «Actualizar...».
        if meta.extra.get("loader_version"):
            return None  # modpack: se queda con el loader que pide el modpack
        if meta.flavor == "paper":
            latest = str(get_json(f"{PAPER_API}/versions/{meta.version}/builds/latest")["id"])
            return f"Paper build {latest}" if latest != meta.build else None
        if meta.flavor == "fabric":
            loader = next(l["version"] for l in get_json(f"{FABRIC_META}/versions/loader") if l["stable"])
            return f"Fabric loader {loader}" if f"loader {loader}" != meta.build else None
        if meta.flavor in LOADERS:
            loader = self._loader_version(meta.flavor, meta.version)
            return f"{meta.flavor} {loader}" if loader != meta.build else None
        return None  # Vanilla: cada versión de Minecraft tiene un único servidor

    def install(self, ctx: InstallContext) -> None:
        meta = ctx.meta
        if meta.flavor in LOADERS:
            self._install_loader(ctx)
        else:
            if meta.flavor == "vanilla":
                url = self._version_json(meta.version)["downloads"]["server"]["url"]
                meta.build = None
            elif meta.flavor == "paper":
                build = get_json(f"{PAPER_API}/versions/{meta.version}/builds/latest")
                url = build["downloads"]["server:default"]["url"]
                meta.build = str(build["id"])
            elif meta.flavor == "fabric":
                loader = meta.extra.get("loader_version") or                     next(l["version"] for l in get_json(f"{FABRIC_META}/versions/loader") if l["stable"])
                installer = next(i["version"] for i in get_json(f"{FABRIC_META}/versions/installer") if i["stable"])
                url = f"{FABRIC_META}/versions/loader/{meta.version}/{loader}/{installer}/server/jar"
                meta.build = f"loader {loader}"
            else:
                raise ValueError(f"Tipo desconocido: {meta.flavor}")
            download(url, ctx.server_dir / "server.jar", ctx.log)

        if ctx.first_install:
            # La app solo crea el servidor si el usuario ha aceptado el EULA.
            (ctx.server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
        self.apply_settings(meta, ctx.server_dir)

    def _install_loader(self, ctx: InstallContext) -> None:
        """Forge y NeoForge se instalan ejecutando su instalador oficial en modo servidor."""
        meta = ctx.meta
        loader = meta.extra.get("loader_version") or self._loader_version(meta.flavor, meta.version)
        if meta.flavor == "forge":
            full = f"{meta.version}-{loader}"
            url = f"{FORGE_MAVEN}/{full}/forge-{full}-installer.jar"
        else:
            url = f"{NEOFORGE_MAVEN}/{loader}/neoforge-{loader}-installer.jar"
        installer = ctx.server_dir / "installer.jar"
        download(url, installer, ctx.log)
        ctx.log(f"Ejecutando el instalador de {meta.flavor} {loader} (puede tardar unos minutos)...")
        try:
            run_logged([str(ctx.java), "-jar", installer.name, "--installServer"], ctx.server_dir, ctx.log)
        finally:
            installer.unlink(missing_ok=True)
            for leftover in ctx.server_dir.glob("installer.jar.log"):
                leftover.unlink()
        meta.build = loader

    def apply_settings(self, meta: ServerMeta, server_dir: Path) -> None:
        path = server_dir / self.properties_file
        updates = {"server-port": str(meta.port)}
        if "motd" not in read_properties(path):
            updates["motd"] = meta.name
        write_properties(path, updates)

    supports_world_import = True

    def world_dirs(self, server_dir: Path) -> list[str]:
        level = read_properties(server_dir / self.properties_file).get("level-name") or "world"
        # Paper/Spigot guardan el Nether y el End en carpetas aparte.
        return [level, f"{level}_nether", f"{level}_the_end"]

    def mod_target(self, meta: ServerMeta) -> ModTarget | None:
        if meta.flavor == "paper":
            return ModTarget(folder="plugins", label="Plugins", modrinth_type="plugin",
                             modrinth_loaders=["paper", "spigot", "bukkit"], cf_class=5)
        if meta.flavor == "fabric":
            return ModTarget(folder="mods", label="Mods", modrinth_type="mod", modrinth_loaders=["fabric"],
                             cf_class=6, cf_loader=4, server_side_only=True)
        if meta.flavor == "forge":
            return ModTarget(folder="mods", label="Mods", modrinth_type="mod", modrinth_loaders=["forge"],
                             cf_class=6, cf_loader=1, server_side_only=True)
        if meta.flavor == "neoforge":
            return ModTarget(folder="mods", label="Mods", modrinth_type="mod", modrinth_loaders=["neoforge"],
                             cf_class=6, cf_loader=6, server_side_only=True)
        return None

    def command(self, meta: ServerMeta, server_dir: Path, java: Path) -> list[str]:
        memory = [f"-Xms{min(1024, meta.memory_mb)}M", f"-Xmx{meta.memory_mb}M"]
        if meta.flavor in LOADERS:
            return [str(java), *memory, *self._loader_launch(meta, server_dir), "nogui"]
        return [str(java), *memory, "-jar", "server.jar", "nogui"]

    @staticmethod
    def _loader_launch(meta: ServerMeta, server_dir: Path) -> list[str]:
        # Forge 1.17+ y NeoForge dejan un archivo con los argumentos de Java en libraries/.
        args_name = "win_args.txt" if sys.platform == "win32" else "unix_args.txt"
        if meta.flavor == "neoforge":
            base = server_dir / "libraries" / "net" / "neoforged" / "neoforge" / (meta.build or "")
        else:
            base = server_dir / "libraries" / "net" / "minecraftforge" / "forge" / f"{meta.version}-{meta.build}"
        args_file = base / args_name
        if args_file.exists():
            return [f"@{args_file.relative_to(server_dir).as_posix()}"]
        # Forge antiguo (1.16 y anteriores) genera un jar ejecutable.
        jars = [p for p in server_dir.glob("forge-*.jar") if "installer" not in p.name]
        if jars:
            return ["-jar", max(jars, key=lambda p: p.stat().st_mtime).name]
        raise RuntimeError("No se encuentran los archivos de arranque de Forge/NeoForge; "
                           "prueba a actualizar el servidor")
