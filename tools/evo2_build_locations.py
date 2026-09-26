"""Génère apworld/evoland2/location_data.py à partir du catalogue (extracted/evo2/catalog.json).

Chaque location reçoit : sa clé en jeu (voir patcher/evoland2_patch.py), un nom anglais, son contenu
d'origine, sa région (chapitre de l'histoire) et ses prérequis propres.
Règle de prudence : en cas de doute, une location est placée dans une région plus tardive.
"""
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..")
CATALOG = os.path.join(ROOT, "extracted", "evo2", "catalog.json")
OUT = os.path.join(ROOT, "apworld", "evoland2", "location_data.py")
TIME_INDEX = {"Past": 0, "Present": 1, "Futur": 2, "Antik": 3}
TIME_NAME = {"Past": "Past", "Present": "Present", "Futur": "Future", "Antik": "Magi Era"}

AREA = {
    "FirstVillage": "Nibiru", "FirstVillageInterior": "Nibiru Old House", "Forest": "Spelbuk Forest",
    "MountainPass": "Grizzly Pass", "Jail": "Imperial Prison", "Sewers": "Genova Sewers",
    "Capital": "Genova", "CapitalInterior": "Genova Houses", "GhostForest": "Haunted Forest",
    "GhostForestCave": "Haunted Forest Cave", "Catacombs": "Jatai's Lair", "Library": "Great Library",
    "Pyramid": "Pyramid of the Prophet", "WindvalleyClimb": "Windy Valley Caverns",
    "Windvalley2": "Windy Valley", "WindvalleyInterior": "Windy Valley Houses", "MountAlpha": "Mount Alpha",
    "Harbor": "Seera Harbor", "MagiIsland": "Cursed Isle", "Mine": "Mine", "LaboEntrance": "Laboratory Entrance",
    "Labo": "Giro's Laboratory", "WeaponHearth": "Eye of the Storm", "Glitch": "Anomaly",
    "IcyCavern": "Frozen Cavern", "VikingVillage": "Viking Village", "VikingInterior": "Viking Village Hall",
    "NorthCavern": "Mines of Noria", "Demonia2": "Demonia Campaign (River Kawai)",
    "Demonia4": "Demonia Campaign (Ambush)", "Demonia9": "Demonia Campaign (Castle)",
    "Demonia31": "Demonia Campaign (Hidden Camp)", "DemoniaEnd": "Demonia Campaign (Magus)",
    "Foreland": "The Bluff", "Sylves": "Sylph Forest", "SylvesForest": "Sylph Sanctuary",
    "ChickenIsland": "Isle of Cluckkety", "Nakomi": "Nakomi Forest", "MenosIslandInterior": "Lost Isle",
    "Meadow": "Grass Cutting Field", "WorldMap": "World Map", "PirateHideout": "Pirates' Lair",
}

# Régions (chapitres) : voir apworld/evoland2/regions.py pour les connexions.
REGION_BY_LEVEL = {
    ("Present", "FirstVillage"): "Nibiru",
    ("Present", "FirstVillageInterior"): "Nibiru",
    ("Present", "Forest"): "Spelbuk Forest",
    ("Past", "Forest"): "Spelbuk Forest",
    ("Past", "FirstVillage"): "Early Past",
    ("Past", "MountainPass"): "Early Past",
    ("Past", "Jail"): "Imperial Prison",
    ("Past", "Sewers"): "Genova Sewers",
    ("Past", "Capital"): "Genova (Past)",
    ("Past", "CapitalInterior"): "Genova (Past)",
    ("Past", "Harbor"): "Past Overworld",
    ("Past", "Meadow"): "Past Overworld",
    ("Past", "Mine"): "Past Overworld",
    ("Past", "GhostForest"): "Haunted Forest",
    ("Past", "GhostForestCave"): "Haunted Forest",
    ("Futur", "Catacombs"): "Jatai's Lair",
    ("Futur", "Capital"): "Genova (Future)",
    ("Futur", "CapitalInterior"): "Genova (Future)",
    ("Futur", "Library"): "Great Library",
    ("Futur", "WindvalleyClimb"): "Windy Valley Caverns",
    ("Futur", "Pyramid"): "Pyramid of the Prophet",
    ("Present", "MagiIsland"): "Cursed Isle",
    ("Present", "Harbor"): "Present World",
    ("Present", "Capital"): "Genova (Present)",
    ("Present", "CapitalInterior"): "Genova (Present)",
    ("Present", "Mine"): "Mine",
    ("Present", "LaboEntrance"): "Laboratory",
    ("Present", "Labo"): "Laboratory",
    ("Futur", "WeaponHearth"): "Eye of the Storm",
    ("Futur", "Windvalley2"): "Time Fragment Quest",
    ("Futur", "WindvalleyInterior"): "Time Fragment Quest",
    ("Futur", "Glitch"): "Anomaly",
    ("Futur", "WorldMap"): "Anomaly",
    ("Futur", "ChickenIsland"): "Skies",
    ("Past", "Nakomi"): "Skies",
    ("Futur", "MountAlpha"): "Skies",
    ("Past", "MagiIsland"): "Fire Fragment Quest",
    ("Present", "PirateHideout"): "Fire Fragment Quest",
    ("Futur", "IcyCavern"): "Ice Fragment Quest",
    ("Past", "VikingVillage"): "Ice Fragment Quest",
    ("Past", "VikingInterior"): "Ice Fragment Quest",
    ("Past", "NorthCavern"): "Ice Fragment Quest",
    ("Past", "Demonia2"): "Earth Fragment Quest",
    ("Past", "Demonia4"): "Earth Fragment Quest",
    ("Past", "Demonia9"): "Earth Fragment Quest",
    ("Past", "Demonia31"): "Earth Fragment Quest",
    ("Past", "DemoniaEnd"): "Earth Fragment Quest",
    ("Present", "Foreland"): "Nature Fragment Quest",
    ("Present", "Sylves"): "Nature Fragment Quest",
    ("Present", "SylvesForest"): "Nature Fragment Quest",
    ("Past", "SylvesForest"): "Nature Fragment Quest",
    ("Futur", "SylvesForest"): "Nature Fragment Quest",
    ("Present", "GhostForest"): "Free Time Travel",
    ("Present", "GhostForestCave"): "Free Time Travel",
    ("Present", "Jail"): "Free Time Travel",
    ("Futur", "FirstVillage"): "Free Time Travel",
    ("Past", "MenosIslandInterior"): "Skies",
}

# Locations exclues : comportement d'origine conservé (voir docs/NOTES_EVOLAND2.md).
EXCLUDED = {
    ("Past", "Jail", "Sword"),  # rend l'arme confisquée à la capture : ne pas la mélanger
    ("Past", "Sewers", "__lembrouil_gold"),  # dépôt d'or de Mr Mudwell
    ("Past", "CapitalInterior", "act_game_waiter"),  # porte-bonheur redonné après un pari perdu
}

FRAGMENT_IDS = {f"MagiKey{i}": 1 for i in range(1, 6)}

# Prérequis propres à certaines locations (en plus de ceux de leur région).
# Clé : (époque, niveau, étiquette) -> items requis ({"item": nombre}). Étiquettes, de la plus générale
# à la plus précise (la dernière trouvée l'emporte) : "*", contenu d'origine (ou "card:<id>"),
# "#<uid>" pour un coffre précis, fonction de script, "fonction:argument".
# Sources : scripts du jeu (extracted/evo2/extra/script), soluce Steam, tableur communautaire
# « Evoland 2 Items, Flags and Logic ».
EXTRA_REQS = {
    ("Present", "FirstVillageInterior", "*"): {"VillageKey": 1},
    # coffre « secondChest » : retiré tant que l'acte 3 n'a pas commencé (5 fragments posés)
    ("Present", "FirstVillageInterior", "Star"): {"VillageKey": 1, **FRAGMENT_IDS},
    # égouts : la fuite ne demande que les 2 clés ; les 4 gemmes ouvrent la grille de la carte
    ("Past", "Sewers", "card:blacksmith"): {"SewersGem": 4},
    ("Past", "Capital", "act_passeur"): {},
    ("Past", "Capital", "Star"): {"SewersKey": 3},  # mur extérieur : accessible une fois sorti de Genova
    ("Past", "CapitalInterior", "act_nchest0"): {"Bonbon": 1},
    ("Past", "CapitalInterior", "on_startDDR"): {"MagusKey": 1},  # salle de Magus + mode rythme (Demonia)
    ("Past", "Harbor", "act_girl"): {"NESPad": 1, "LoveLetter": 1},
    ("Futur", "Catacombs", "onBossTalk"): {"Catakey": 2},
    ("Futur", "Capital", "act_gb3"): {"Book": 1, "LibKey": 1},
    ("Futur", "CapitalInterior", "act_merchant"): {"Badge": 1},
    ("Present", "Capital", "on_checkDD"): {"PirateFlag": 1},  # Colisée : ouvert après le repaire des pirates
    ("Present", "CapitalInterior", "act_getMedal"): {"DalkinKey": 1},
    ("Present", "CapitalInterior", "Star"): {"DalkinKey": 1},  # coffre de Dalkin : après la campagne
    ("Present", "CapitalInterior", "act_wok"): {"IngrA": 1, "IngrB": 1, "IngrC": 1},
    ("Present", "Mine", "*"): {"Bombs": 1},
    ("Present", "Mine", "getBombs"): {},
    ("Present", "Mine", "ChildKey"): {},
    ("Present", "Mine", "SuperBombs"): {"Bombs": 1, "MissingRail": 3},
    ("Present", "Mine", "card:largo"): {},  # acte 2 (région), bombes déjà requises par la région
    ("Present", "Mine", "card:menos"): {},  # mur cassé par Menos : acte 2 (région)
    ("Past", "MagiIsland", "act_roberts:PirateFlag"): {"LoveLetter": 1, "LoveProof": 1},
    ("Present", "PirateHideout", "wonBoss"): {"PirateFlag": 1},
    ("Past", "VikingVillage", "act_anar"): {"IceBook": 1},
    # bosquet sacré : entrée fermée sans la Larme de Sylphe (Sylves.js, init)
    ("Present", "SylvesForest", "*"): {"SylveTear": 1},
    ("Past", "SylvesForest", "*"): {"SylveTear": 1},
    ("Futur", "SylvesForest", "*"): {"SylveTear": 1},
    # garde de Windy Valley : levé quand Sid a reçu le Prototype X-01 (Windvalley2.js, locker)
    ("Futur", "Windvalley2", "Energy"): {"WingBroken": 1},
    ("Futur", "Windvalley2", "on_postShoot"): {"Flying Machine": 1},
    # le Gardien ailé n'apparaît qu'à l'acte 3 (WorldMap.js, on_guardian)
    ("Futur", "WorldMap", "on_dropItemPos"): {"Flying Machine": 1, **FRAGMENT_IDS},
    # Nibiru (futur) : chemin ouvert à l'acte 3 (WorldMap.js futur, Line001)
    ("Futur", "FirstVillage", "*"): dict(FRAGMENT_IDS),
    # îles du passé : voler dans une autre époque demande le Module temporel
    ("Past", "Nakomi", "*"): {"WingTravel": 1},
    ("Past", "MenosIslandInterior", "*"): {"WingTravel": 1},
}

# Région différente de celle du niveau pour certaines locations (mêmes étiquettes que EXTRA_REQS).
REGION_OVERRIDE = {
    # l'éboulement vers Nibiru/Spelbuk (présent) ne disparaît qu'à l'acte 2 ; glace de Velvet requise
    ("Present", "FirstVillage", "Energy"): "Free Time Travel",
    ("Present", "FirstVillage", "Mineral"): "Free Time Travel",
    ("Present", "FirstVillageInterior", "Star"): "Free Time Travel",
    ("Present", "Forest", "#6785"): "Free Time Travel",  # eau à geler à gauche du Magilith
    ("Past", "FirstVillage", "card:manimal"): "Free Time Travel",  # glace de Velvet
    # partie « maison aux poules » des égouts, entrée depuis Genova
    ("Past", "Sewers", "SewersGem"): "Genova (Past)",
    ("Past", "Sewers", "card:blacksmith"): "Genova (Past)",
    ("Past", "Sewers", "#57931"): "Genova (Past)",
    ("Past", "CapitalInterior", "on_startDDR"): "Earth Fragment Quest",
    ("Present", "Capital", "on_checkDD"): "Fire Fragment Quest",
    ("Present", "CapitalInterior", "Star"): "Earth Fragment Quest",
    ("Present", "Mine", "card:largo"): "Free Time Travel",
    ("Present", "Mine", "card:menos"): "Free Time Travel",
    # le prototype ne se prend qu'après avoir parlé à Sid (Windy Valley présent, acte 2)
    ("Futur", "Pyramid", "act_proto"): "Free Time Travel",
}

SCRIPT_NAMES = {
    ("Present", "FirstVillage", "act_fisher"): "Old Pol's Reward",
    ("Past", "Capital", "act_passeur:SewersKey"): "Mr Mudwell's Sewers Key",
    ("Past", "Capital", "act_passeur:Badge"): "Mr Mudwell's Loyalty Badge",
    ("Past", "CapitalInterior", "act_weird"): "Candy from the Inn Customer",
    ("Past", "CapitalInterior", "act_nchest0"): "Noble's Secret Chest",
    ("Past", "CapitalInterior", "on_startDDR"): "Rhythm Game Card",
    ("Past", "DemoniaEnd", "getKey"): "Magus's Robe",
    ("Past", "Harbor", "act_girl"): "Tinder Profile",
    ("Past", "MagiIsland", "act_roberts:PirateFlag"): "Pirate Roberts's Flag",
    ("Past", "MagiIsland", "act_roberts:LoveLetter"): "Pirate Roberts's Love Letter",
    ("Past", "Meadow", "initBushes"): "Grass Cutting Game",
    ("Past", "VikingInterior", "act_boss"): "Viking Chief's Book",
    ("Past", "VikingVillage", "act_anar"): "Fragment of Ice",
    ("Present", "Capital", "act_c1"): "Child Key (Blond Girl)",
    ("Present", "Capital", "act_mailbox"): "Child Key (Mailbox)",
    ("Present", "Capital", "act_c3"): "Child Key (Library Girl)",
    ("Present", "Capital", "on_checkDD"): "Beat 'em All Card",
    ("Present", "CapitalInterior", "act_findKey"): "Child Key (Barracks)",
    ("Present", "CapitalInterior", "act_getMedal"): "Dalkin's Medal",
    ("Present", "CapitalInterior", "act_center"): "Card Game Starter Card",
    ("Present", "CapitalInterior", "act_wok"): "Legendary Cook's Maana",
    ("Present", "Foreland", "act_spark"): "Sylph's Tear",
    ("Present", "Labo", "act_c19"): "Cyborg Pod",
    ("Present", "MagiIsland", "act_boat"): "Boat",
    ("Present", "Mine", "getBombs"): "Plum's Bombs",
    ("Present", "PirateHideout", "wonBoss"): "Fragment of Fire",
    ("Present", "SylvesForest", "act_manaTree"): "Mana Tree Card",
    ("Present", "SylvesForest", "rtc_meetManaTree"): "Fragment of Nature",
    ("Futur", "Capital", "act_gb3"): "Girls' Reward",
    ("Futur", "Capital", "buy"): "House Purchase",
    ("Futur", "CapitalInterior", "act_merchant"): "Mudwell Jr's Pass",
    ("Futur", "Catacombs", "onBossTalk"): "Jatai's Maana",
    ("Futur", "FirstVillage", "act_last"): "Final Visit Star",
    ("Futur", "Library", "act_old"): "Researchers' Star",
    ("Futur", "Library", "act_archivist"): "Archivist's Book",
    ("Futur", "Pyramid", "act_timeStone"): "Stone of Time",
    ("Futur", "Pyramid", "act_proto"): "Prototype X-01",
    ("Futur", "WeaponHearth", "act_hybrid"): "Control Terminal",
    ("Futur", "Windvalley2", "on_postShoot"): "Shoot 'em Up Rematch Card",
    ("Futur", "WorldMap", "on_dropItemPos"): "Time Module",
}

ITEM_NAMES = {
    "Star": "Star", "Mineral": "Orikon Ore", "Energy": "Maana", "GreenGoo": "Green Goo", "RedGoo": "Red Goo",
    "Sword": "Old Sword", "VillageKey": "Old House Key", "Gravity": "Gravity", "SewersKey": "Sewers Key",
    "SewersGem": "Strange Gem", "Bonbon": "Licked Candy", "LuckyCharm": "Lucky Charm", "Badge": "Loyalty Badge",
    "Pass": "Pass", "LibKey": "Library Key", "Book": "50 Drinking Games", "Catakey": "Jatai's Gem",
    "Bombs": "Bombs", "SuperBombs": "Super Bombs", "MissingRail": "Missing Rail", "TimeStone": "Stone of Time",
    "Boat": "Boat", "ChildKey": "Children's Key", "NESPad": "Control Terminal", "LoveLetter": "Love Letter",
    "LoveProof": "Tinder Profile", "PirateFlag": "Pirate Flag", "MagiKey1": "Fragment of Fire",
    "IceBook": "Book of Boreas", "MagiKey2": "Fragment of Ice", "MagiKey3": "Fragment of Nature",
    "SylveTear": "Sylph's Tear", "WingBroken": "Prototype X-01", "MagiKey4": "Fragment of Earth",
    "MagiKey5": "Fragment of Time", "DalkinKey": "Dalkin's House Key", "DalkinMedal": "Dalkin's Medal",
    "WingTravel": "Time Module", "MagusKey": "Magus's Key", "IngrA": "Golden Apple",
    "IngrB": "Cheeseless Pizza", "IngrC": "Mammoth Steak",
}


def card_name(card_id: str) -> str:
    return f"{card_id[:1].upper()}{card_id[1:]} Card"


def item_name(record: str) -> str:
    kind, value = record.split(":", 1)
    return card_name(value) if kind == "c" else ITEM_NAMES.get(value, value)


def lookup(table, time, level, tags, default):
    value = table.get((time, level, "*"), default)
    for tag in tags:
        value = table.get((time, level, tag), value)
    return value


def reqs_for(time, level, *tags):
    return dict(lookup(EXTRA_REQS, time, level, tags, {}))


def region_for(time, level, *tags):
    return lookup(REGION_OVERRIDE, time, level, tags, REGION_BY_LEVEL[(time, level)])


def build():
    catalog = json.load(open(CATALOG, encoding="utf-8"))
    entries = []
    # coffres et objets au sol
    grouped = defaultdict(list)
    for c in catalog["chests"]:
        content = c["content"]
        if not content and c["type"] in ("SewersGem", "MissingRail"):
            content = {"item": c["type"]}  # objet fixé par le code (ent.active.SewersGem / MissingRail)
            c = {**c, "content": content}
        if not content or (c["time"], c["level"], content.get("item")) in EXCLUDED:
            continue
        if c["type"] not in ("Chest", "SewersGem", "MissingRail", "Sparkling"):
            continue
        grouped[(c["time"], c["level"])].append(c)
    for (time, level), chests in grouped.items():
        counters = Counter()
        for c in sorted(chests, key=lambda c: (c["y"], c["x"])):
            content = c["content"]
            record = f"c:{content['card']}" if "card" in content else f"i:{content['item']}"
            tag = f"card:{content['card']}" if "card" in content else content["item"]
            if c["type"] == "Chest":
                key = f"c{TIME_INDEX[time]}_{level}_{c['uid']}"
            else:
                counters[tag] += 1
                key = f"s{TIME_INDEX[time]}_{level}_{tag}_{counters[tag]}"
            label = "Chest" if c["type"] == "Chest" else "Pickup"
            tags = (tag, f"#{c['uid']}")
            entries.append(dict(time=time, level=level, key=key, record=record,
                                base=f"{AREA[level]} ({TIME_NAME[time]}) - {item_name(record)} {label}",
                                req=reqs_for(time, level, *tags), region=region_for(time, level, *tags)))
    # récompenses de scripts
    counters = Counter()
    for s in catalog["scripts"]:
        if s["dynamic"] or s["call"].startswith("quick"):
            continue
        if (s["time"], s["level"], s["function"]) in EXCLUDED:
            continue
        time, level = s["time"], s["level"]
        tag = f"card:{s['arg']}" if s["call"] == "getCard" else s["arg"]
        record = f"c:{s['arg']}" if s["call"] == "getCard" else f"i:{s['arg']}"
        counters[(time, level, tag)] += 1
        key = f"s{TIME_INDEX[time]}_{level}_{tag}_{counters[(time, level, tag)]}"
        label = SCRIPT_NAMES.get((time, level, f"{s['function']}:{s['arg']}")) \
            or SCRIPT_NAMES.get((time, level, s["function"])) or s["function"]
        tags = (tag, s["function"], f"{s['function']}:{s['arg']}")
        entries.append(dict(time=time, level=level, key=key, record=record,
                            base=f"{AREA[level]} ({TIME_NAME[time]}) - {label}",
                            req=reqs_for(time, level, *tags), region=region_for(time, level, *tags)))
    # noms uniques (#2, #3… pour les doublons)
    seen = Counter(e["base"] for e in entries)
    index = Counter()
    for e in entries:
        if seen[e["base"]] > 1:
            index[e["base"]] += 1
            e["name"] = f"{e['base']} #{index[e['base']]}"
        else:
            e["name"] = e["base"]
    return entries


def write(entries):
    lines = [
        '"""Locations d\'Evoland 2 — fichier généré par tools/evo2_build_locations.py (ne pas modifier à la main)."""',
        "",
        "# (nom, clé en jeu, région, contenu d'origine, prérequis {objet: nombre})",
        "LOCATIONS = [",
    ]
    for e in sorted(entries, key=lambda e: (e["region"], e["name"])):
        lines.append(f"    ({e['name']!r}, {e['key']!r}, {e['region']!r}, {e['record']!r}, {e['req']!r}),")
    lines.append("]")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    data = build()
    write(data)
    print(len(data), "locations ->", OUT)
    print(Counter(e["region"] for e in data))
    print(Counter(item_name(e["record"]) for e in data).most_common())
