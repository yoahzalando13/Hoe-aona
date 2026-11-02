"""Vérifie que chaque texte traduit de l'interface a sa version anglaise et malgache.

    python scripts/check_i18n.py

Les clés sont les textes français passés à `| t`, `| plural`, `t(...)` et `plural(...)` dans frontend/src/app.
Code de sortie 1 si une traduction manque (utilisable en intégration continue).
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "frontend/src/app"
LIT = r"'((?:[^'\\]|\\.)*)'"


def used_keys() -> set[str]:
    keys: set[str] = set()
    for p in APP.rglob("*"):
        if p.suffix not in (".html", ".ts") or "i18n" in p.parts:
            continue
        s = p.read_text(encoding="utf-8")
        keys |= set(re.findall(LIT + r"\s*\|\s*t\b", s))
        keys |= set(re.findall(r"(?<![\w.])t\(\s*" + LIT, s))
        for m in re.finditer(r"\|\s*plural\s*:\s*" + LIT + r"\s*:\s*" + LIT, s):
            keys |= {m.group(1), m.group(2)}
        for m in re.finditer(r"(?<![\w.])plural\([^,]+,\s*" + LIT + r"\s*,\s*" + LIT, s):
            keys |= {m.group(1), m.group(2)}
    return keys


def dictionary(name: str) -> dict[str, str]:
    src = (APP / "i18n" / f"{name}.ts").read_text(encoding="utf-8")
    body = src[src.index("{"):src.rindex("}") + 1]
    return json.loads(re.sub(r",\s*}$", "}", body))


def main() -> int:
    keys = used_keys()
    failed = False
    for name in ("en", "mg"):
        d = dictionary(name)
        missing = sorted(k for k in keys if k not in d)
        placeholders = [k for k in keys & d.keys() if set(re.findall(r"\{\w+\}", k)) != set(re.findall(r"\{\w+\}", d[k]))]
        print(f"{name} : {len(keys) - len(missing)}/{len(keys)} clés traduites")
        for k in missing:
            print(f"  manquante : {k!r}")
        for k in placeholders:
            print(f"  paramètres différents : {k!r} -> {d[k]!r}")
        failed |= bool(missing or placeholders)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
