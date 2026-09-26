"""Catalogue de toutes les sources d'objets d'Evoland 2.

- coffres et objets actifs porteurs d'un contenu (data.cdb, levelData.actives) ;
- récompenses des scripts de zone (extra/script/<époque>/<Niveau>.js).

Sortie : extracted/evo2/catalog.json et un résumé à l'écran.
"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..", "extracted", "evo2")
TIMES = ["Past", "Present", "Futur", "Antik"]
SCRIPT_TIMES = {"past": "Past", "present": "Present", "futur": "Futur", "antik": "Antik"}
IGNORED_LEVEL = re.compile(r"^(_|Reboss|Allcomplete)")
ITEM_ACTIVES = {"Chest", "MagiChest", "Sparkling", "SewersGem", "MissingRail"}

GIVE_CALL = re.compile(r"\b(getItem|getCard|quickAddItem|quickAddCard)\(\s*([^)]*?)\s*\)")
FUNCTION = re.compile(r"^\s*function\s+(\w+)\s*\(")


def load_db():
    with open(os.path.join(ROOT, "data.cdb"), encoding="utf-8") as f:
        db = json.load(f)
    return {s["name"]: s for s in db["sheets"]}


def normalize_content(value, cards: set[str]):
    """Même règle que ent.active.Chest : minuscule + carte existante -> carte, sinon objet."""
    if not isinstance(value, str):
        return None
    if value[:1].islower() and value in cards:
        return {"card": value}
    return {"item": value[:1].upper() + value[1:]}


def chests(sheets):
    cards = {c["id"] for c in sheets["card"]["lines"]}
    result = []
    for level in sheets["levelData"]["lines"]:
        name = level.get("level")
        if not name or IGNORED_LEVEL.match(name):
            continue
        time = TIMES[level.get("time", 0)]
        for a in level.get("actives", []):
            if a.get("type") not in ITEM_ACTIVES:
                continue
            result.append({
                "level": name, "time": time, "type": a["type"], "x": a["x"], "y": a["y"],
                "uid": a["x"] + a["y"] * level["width"], "id": a.get("id"),
                "raw": a.get("value"), "content": normalize_content(a.get("value"), cards),
            })
    return result


def script_rewards():
    result = []
    base = os.path.join(ROOT, "extra", "script")
    for folder in sorted(os.listdir(base)):
        for file in sorted(os.listdir(os.path.join(base, folder))):
            if not file.endswith(".js"):
                continue
            function = None
            with open(os.path.join(base, folder, file), encoding="utf-8", errors="replace") as f:
                for n, line in enumerate(f, 1):
                    m = FUNCTION.match(line)
                    if m:
                        function = m.group(1)
                    for call in GIVE_CALL.finditer(line):
                        arg = call.group(2)
                        literal = re.fullmatch(r'"([^"]*)"(?:\s*,.*)?', arg)
                        result.append({
                            "level": file[:-3], "time": SCRIPT_TIMES.get(folder, folder),
                            "call": call.group(1), "function": function, "line": n,
                            "arg": literal.group(1) if literal else arg,
                            "dynamic": literal is None,
                        })
    return result


if __name__ == "__main__":
    sheets = load_db()
    catalog = {"chests": chests(sheets), "scripts": script_rewards()}
    with open(os.path.join(ROOT, "catalog.json"), "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=1, ensure_ascii=False)
    from collections import Counter
    print("objets actifs porteurs de contenu :", Counter(c["type"] for c in catalog["chests"]))
    print("contenus :", Counter((c["content"] or {}).get("item") or (c["content"] or {}).get("card", "-")
                                for c in catalog["chests"]).most_common(60))
    print("appels de scripts :", Counter(s["call"] for s in catalog["scripts"]))
