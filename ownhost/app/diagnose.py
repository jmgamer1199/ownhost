"""What to tell the user when the app can't connect to a computer, and what to try there.

The cause is told apart from what the computer did: it answered "no" (token or permission), it refused the
connection (the agent isn't running), it didn't answer at all (off, other network or firewall), or something
else broke. The advice depends on the computer's system, which comes from what the agent says about itself
(`/api/hello`, no token needed) or, if it doesn't answer, from the ping's TTL (Linux and macOS start at 64,
Windows at 128: only a guess).
"""

from ownhost.app.client import AgentClient, ApiError, fetch_hello
from ownhost.app.hosts import Host
from ownhost.i18n import tr
from ownhost.net import ping_system

SHOW_TOKEN = "sudo -u ownhost env OWNHOST_DATA_DIR=/var/lib/ownhost /opt/ownhost/Ownhost --agent --show-token"
SERVICE = "sudo systemctl status ownhost-agent\njournalctl -u ownhost-agent -n 50"
FIREWALL = "sudo ufw status\nsudo firewall-cmd --list-all"


def try_connect(host: Host) -> dict:
    """Tries to talk to the agent. {"ok": True}, or what went wrong and what is known about that computer."""
    client = AgentClient(host)
    try:
        client.info()
        return {"ok": True}
    except ApiError as e:
        kind, message = e.kind, str(e)
    except Exception as e:  # noqa: BLE001 - anything else is shown as it is
        kind, message = "other", str(e)
    finally:
        client.close()
    hello = fetch_hello(host) if kind in ("token", "forbidden", "other") else None
    reachable, guess = False, None
    if kind in ("refused", "silent"):
        reachable, guess = ping_system(host.address)
    return {"ok": False, "kind": kind, "message": message, "hello": hello, "reachable": reachable or kind == "refused",
            "system": ((hello or {}).get("os") or guess or "").lower(),
            "headless": (hello or {}).get("headless")}


def explain(result: dict, host: Host) -> str:
    """The text for the user, for a failed `try_connect`."""
    kind, system, headless = result["kind"], result.get("system", ""), result.get("headless")
    address, port = host.address, host.port
    linux = system == "linux"
    if kind == "token":
        if host.token:
            return tr("Token incorrecto")
        text = tr("El equipo {address} responde, pero no te deja entrar sin el token. Escríbelo en «Token o código» "
                  "(o entra desde un PC con tu misma cuenta de Tailscale).", address=address)
        if linux and headless:
            return text + "\n\n" + tr("Para ver el token en ese equipo, ejecuta:") + "\n" + SHOW_TOKEN
        if linux and headless is None:
            return (text + "\n\n" + tr("En ese equipo: abre Ownhost y pulsa «Copiar token» en la ficha «Este PC»; si no "
                                       "tiene pantalla, ejecuta:") + "\n" + SHOW_TOKEN)
        return text + "\n\n" + tr("En ese equipo, abre Ownhost y pulsa «Copiar token» en la ficha «Este PC».")
    if kind == "refused":
        text = tr("El equipo {address} está encendido, pero el Ownhost no responde en el puerto {port}: el agente no "
                  "está en marcha o usa otro puerto.", address=address, port=port)
        if linux and headless is not False:
            return text + "\n\n" + tr("En ese equipo (Linux), comprueba el servicio:") + "\n" + SERVICE
        return text + "\n\n" + tr("En ese equipo, abre Ownhost y comprueba que «Este PC» funciona como servidor.")
    if kind == "silent":
        if not result.get("reachable"):
            return tr("No hay respuesta de {address}: puede estar apagado, sin conexión o en otra red. Si es por "
                      "Tailscale, comprueba que los dos equipos están conectados.", address=address)
        text = tr("El equipo {address} está encendido y responde al ping, pero el Ownhost no contesta (puerto {port}). "
                  "Casi seguro es su cortafuegos.", address=address, port=port)
        if system == "windows":
            return text + "\n\n" + tr("En ese equipo, permite Ownhost en el Firewall de Windows (solo en redes privadas).")
        if linux:
            text += "\n\n" + tr("En ese equipo (Linux), mira el cortafuegos y permite el puerto {port} solo para tu red "
                                "de casa y Tailscale (install-agent-service.sh lo hace al instalar):", port=port)
            text += "\n" + FIREWALL
            if headless is not True:
                text += "\n\n" + tr("Si tiene pantalla, abre Ownhost y pulsa «Abrir puertos del cortafuegos» en la "
                                    "ficha «Este PC».")
            return text
        return text + "\n\n" + tr("En ese equipo, abre los puertos del cortafuegos: en Linux, «Abrir puertos del "
                                  "cortafuegos» en la ficha «Este PC»; en Windows, permite Ownhost en el Firewall.")
    return result["message"] if kind == "forbidden" else tr("No se pudo completar la conexión: {message}",
                                                           message=result["message"])
