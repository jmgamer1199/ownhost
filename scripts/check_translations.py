"""Checks the translations: every tr("...") text in the code must be in an English catalog, with the
same {placeholders}. Also lists catalog entries that are no longer used.

Usage: python scripts/check_translations.py [files...]   (default: the whole ownhost package)
Exits with code 1 if something is missing or wrong.
"""

import ast
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def used_texts(paths: list[Path]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr"
                    and node.args):
                arg = node.args[0]
                where = f"{path.relative_to(ROOT)}:{node.lineno}"
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    found.setdefault(arg.value, []).append(where)
                elif isinstance(arg, ast.JoinedStr):
                    found.setdefault(f"<f-string in {where}>", []).append(where)
    return found


def main() -> int:
    from ownhost import i18n

    catalog = i18n._english()
    paths = [Path(p).resolve() for p in sys.argv[1:]] or [
        p for p in (ROOT / "ownhost").rglob("*.py") if "locale" not in p.parts]
    used = used_texts(paths)
    problems = 0
    for text, places in sorted(used.items()):
        if text.startswith("<f-string"):
            print(f"f-string inside tr() (use placeholders): {places[0]}")
            problems += 1
        elif text not in catalog:
            print(f"Missing translation: {text!r}  ({places[0]})")
            problems += 1
        elif placeholders(text) != placeholders(catalog[text]):
            print(f"Different placeholders: {text!r} -> {catalog[text]!r}")
            problems += 1
    if not sys.argv[1:]:
        unused = sorted(set(catalog) - set(used))
        if unused:
            print(f"{len(unused)} catalog entries are not used in the code (can be removed):")
            for text in unused[:20]:
                print(f"  {text!r}")
    print(f"{len(used)} texts checked, {problems} problems.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
