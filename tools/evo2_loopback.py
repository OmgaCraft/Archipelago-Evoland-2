"""Client de test « en boucle » pour Evoland 2 : chaque check renvoie le contenu d'origine.

coffre / récompense -> archipelago2/checks/<clé>.txt -> ce script -> archipelago2/items.txt -> le jeu.
Journal : extracted/evo2_loopback.log

Usage : python tools/evo2_loopback.py [dossier du jeu]
"""
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAME = sys.argv[1] if len(sys.argv) > 1 else r"D:\steamapp\steamapps\common\Evoland Legendary Edition"
AP = os.path.join(GAME, "archipelago2")
LOG = os.path.join(ROOT, "extracted", "evo2_loopback.log")
TIME_INDEX = {"Past": 0, "Present": 1, "Futur": 2, "Antik": 3}
SESSION = "00000042"

catalog = json.load(open(os.path.join(ROOT, "extracted", "evo2", "catalog.json"), encoding="utf-8"))

# clé -> ligne d'item à renvoyer (contenu d'origine)
vanilla: dict[str, str] = {}
for c in catalog["chests"]:
    content = c["content"]
    if not content:
        continue
    record = f"c:{content['card']}" if "card" in content else f"i:{content['item']}"
    if c["type"] == "Chest":
        vanilla[f"c{TIME_INDEX[c['time']]}_{c['level']}_{c['uid']}"] = record
    else:
        what = f"card:{content['card']}" if "card" in content else content["item"]
        for n in range(1, 5):
            vanilla[f"s{TIME_INDEX[c['time']]}_{c['level']}_{what}_{n}"] = record
for s in catalog["scripts"]:
    if s["dynamic"] or s["call"].startswith("quick"):
        continue
    what = f"card:{s['arg']}" if s["call"] == "getCard" else s["arg"]
    record = f"c:{s['arg']}" if s["call"] == "getCard" else f"i:{s['arg']}"
    for n in range(1, 5):
        vanilla[f"s{TIME_INDEX[s['time']]}_{s['level']}_{what}_{n}"] = record


def log(msg: str) -> None:
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    os.makedirs(os.path.join(AP, "checks"), exist_ok=True)
    with open(os.path.join(AP, "config.txt"), "w", encoding="utf-8") as f:
        f.write(SESSION + "," + ",".join(sorted(vanilla)) + ",")
    items_path = os.path.join(AP, "items.txt")
    items = open(items_path, encoding="utf-8").read().split("\n") if os.path.exists(items_path) else []
    items = [i for i in items if i]
    seen = set(os.listdir(os.path.join(AP, "checks")))
    log(f"Démarrage : {len(vanilla)} clés connues, {len(items)} items déjà envoyés, {len(seen)} checks existants.")
    while True:
        for name in sorted(os.listdir(os.path.join(AP, "checks"))):
            if name in seen:
                continue
            seen.add(name)
            key = name[:-4]
            record = vanilla.get(key)
            log(f"CHECK {key} -> {record or 'inconnu (contenu d origine gardé par le jeu)'}")
            if record:
                items.append(record)
                with open(items_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(items))
                log(f"  -> renvoyé ({len(items)} au total)")
        time.sleep(0.3)


if __name__ == "__main__":
    main()
