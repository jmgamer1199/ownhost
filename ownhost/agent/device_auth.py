"""Detecta en la consola los inicios de sesión por código (OAuth device flow).

Hytale muestra algo como:
    Visit: https://oauth.accounts.hytale.com/oauth2/device/verify
    Enter code: AbCd1234
y al terminar "Authentication successful!". El formato exacto ha cambiado entre
versiones, así que las expresiones son deliberadamente tolerantes.
"""

import re

# Hytale y la cuenta de Microsoft de la extensión MCXboxBroadcast («...open the page
# https://www.microsoft.com/link and enter the code XXXXXXXX to authenticate.»).
URL_RE = re.compile(r"https?://[^\s\"'<>]*(?:hytale|microsoft\.com/link|microsoft\.com/devicelogin)[^\s\"'<>]*",
                    re.IGNORECASE)
CODE_RE = re.compile(r"(?:code\s*[:=]|enter the code)\s*([A-Za-z0-9]{4,}(?:-[A-Za-z0-9]{2,})*)", re.IGNORECASE)
URL_CODE_RE = re.compile(r"user_code=([A-Za-z0-9-]+)")
SUCCESS_RE = re.compile(r"authentication successful|successfully (?:authenticated|logged in)|"
                        r"authenticated successfully|login successful", re.IGNORECASE)
FAILURE_RE = re.compile(r"(?:authentication|authorization|login) (?:failed|expired|timed out|cancel)|"
                        r"failed to get/refresh auth token", re.IGNORECASE)
AUTH_URL_HINTS = ("device", "verify", "activate", "oauth", "login", "auth", "link")


class DeviceAuthWatcher:
    def __init__(self):
        self.pending: dict | None = None

    def feed(self, line: str) -> str | None:
        """Procesa una línea. Devuelve 'pending', 'success', 'failed' o None."""
        event = None
        url = URL_RE.search(line)
        if url and any(h in url.group(0).lower() for h in AUTH_URL_HINTS):
            link = url.group(0).rstrip(".,);")
            code = URL_CODE_RE.search(link)
            self.pending = {"url": link, "code": code.group(1) if code else None}
            event = "pending"
        if self.pending:
            code = CODE_RE.search(line)
            if code and code.group(1).lower() not in ("http", "https"):
                self.pending["code"] = code.group(1)
                event = "pending"
            if SUCCESS_RE.search(line):
                self.pending = None
                return "success"
            if FAILURE_RE.search(line):
                self.pending = None
                return "failed"
        elif SUCCESS_RE.search(line):
            return "success"
        return event

    def reset(self) -> None:
        self.pending = None
