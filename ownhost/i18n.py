"""Translations (Spanish and English).

The code is written with the Spanish texts, which are also the keys of the English catalog
(ownhost/locale/en_*.py). Use ``tr("Texto con {nombre}", nombre=valor)`` for every text a person sees.

- The app picks one language per run (Settings → Language).
- The agent answers each request in the language the app asks for (``X-Ownhost-Language`` header) and
  writes console lines and notices in its own language (the system's, or the one the app sets).
"""

import contextvars
import importlib
import locale
import os
import pkgutil

LANGUAGES = {"es": "Español (España)", "en": "English"}
HEADER = "X-Ownhost-Language"

_default = "es"
_current: contextvars.ContextVar[str | None] = contextvars.ContextVar("ownhost_language", default=None)
_catalog: dict[str, str] | None = None


def _english() -> dict[str, str]:
    global _catalog
    if _catalog is None:
        import ownhost.locale as package

        catalog: dict[str, str] = {}
        for module in pkgutil.iter_modules(package.__path__):
            if module.name.startswith("en_"):
                catalog.update(importlib.import_module(f"ownhost.locale.{module.name}").STRINGS)
        _catalog = catalog
    return _catalog


def system_language() -> str:
    """Spanish if the system is in Spanish; English otherwise."""
    for name in (os.environ.get("LC_ALL"), os.environ.get("LANG"), (locale.getlocale()[0] or "")):
        if name:
            low = name.lower()
            return "es" if low.startswith("es") or low.startswith("spanish") else "en"
    return "en"


def normalize(lang: str | None) -> str | None:
    lang = (lang or "").strip().lower()[:2]
    return lang if lang in LANGUAGES else None


def set_language(lang: str | None) -> None:
    """Default language of this process (the app's choice, or the agent's own)."""
    global _default
    _default = normalize(lang) or system_language()


def language() -> str:
    return _current.get() or _default


def use_language(lang: str | None) -> contextvars.Token:
    """Language for the current request (the agent sets it from the app's header)."""
    return _current.set(normalize(lang))


def reset_language(token: contextvars.Token) -> None:
    _current.reset(token)


def decimal(number: str) -> str:
    """A number written with a dot ("3.5"), with the decimal comma in Spanish ("3,5")."""
    return number.replace(".", ",") if language() == "es" else number


def tr(text: str, /, **values) -> str:
    if language() == "en":
        text = _english().get(text, text)
    return text.format(**values) if values else text
