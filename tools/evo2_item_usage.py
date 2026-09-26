"""Pour chaque objet d'Evoland 2 : où les scripts le donnent, le testent ou le consomment.

Usage : python tools/evo2_item_usage.py [objet ...]   (sans argument : tous les objets clés)
Sortie : docs/evo2_item_usage.md
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPTS = os.path.join(ROOT, "extracted", "evo2", "extra", "script")
OUT = os.path.join(ROOT, "docs", "evo2_item_usage.md")

KEY_ITEMS = [
    "Sword", "VillageKey", "Gravity", "SewersKey", "SewersGem", "Bonbon", "LuckyCharm", "Badge", "Pass",
    "LibKey", "Book", "Catakey", "Bombs", "SuperBombs", "MissingRail", "TimeStone", "Boat", "ChildKey",
    "NESPad", "LoveLetter", "LoveProof", "PirateFlag", "MagiKey1", "IceBook", "MagiKey2", "MagiKey3",
    "SylveTear", "Wing", "Radar", "WingBroken", "MagiKey4", "MagiKey5", "Whisky", "Tea", "Sugar",
    "DalkinKey", "DalkinMedal", "Energy", "WingTravel", "MagusKey", "IngrA", "IngrB", "IngrC", "Mineral",
]
CALL = re.compile(r'\b(getItem|quickAddItem|hasItem|useItem|itemCount|removeItem)\(\s*"(\w+)"([^)]*)\)')
FUNCTION = re.compile(r"^\s*function\s+(\w+)\s*\(")


def scan():
    uses = {}
    for folder in sorted(os.listdir(SCRIPTS)):
        for file in sorted(os.listdir(os.path.join(SCRIPTS, folder))):
            function = None
            path = os.path.join(SCRIPTS, folder, file)
            with open(path, encoding="utf-8", errors="replace") as f:
                for n, line in enumerate(f, 1):
                    m = FUNCTION.match(line)
                    if m:
                        function = m.group(1)
                    for call in CALL.finditer(line):
                        uses.setdefault(call.group(2), []).append(
                            (folder, file[:-3], function, n, call.group(1), call.group(3).strip(", "), line.strip()))
    return uses


if __name__ == "__main__":
    wanted = sys.argv[1:] or KEY_ITEMS
    uses = scan()
    lines = ["# Utilisation des objets dans les scripts d'Evoland 2", "",
             "Généré par `tools/evo2_item_usage.py`.", ""]
    for item in wanted:
        lines.append(f"## {item}")
        lines.append("")
        for folder, level, function, n, call, extra, text in uses.get(item, []):
            lines.append(f"- `{call}` {folder}/{level}.js:{n} dans `{function}`"
                         + (f" (args: {extra})" if extra else "") + f" — `{text[:90]}`")
        if item not in uses:
            lines.append("- (aucune utilisation dans les scripts)")
        lines.append("")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
