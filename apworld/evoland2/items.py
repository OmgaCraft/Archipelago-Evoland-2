"""Objets d'Evoland 2.

Les objets du pool sont exactement les contenus d'origine des locations (location_data.py).
Chaque objet est envoyé au jeu sous forme d'un enregistrement « i:<objet> » ou « c:<carte> »
(voir patcher/evoland2_patch.py), que le client écrit dans archipelago2/items.txt.
"""
import zlib

from BaseClasses import Item, ItemClassification

from .location_data import LOCATIONS

GAME_NAME = "Evoland 2"
BASE_ID = 73_320_000

PROG = ItemClassification.progression
USEFUL = ItemClassification.useful
FILLER = ItemClassification.filler

# identifiant interne du jeu -> nom affiché dans Archipelago
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

# Objets qui débloquent de la progression (voir location_data.py et regions.py).
PROGRESSION_IDS = {
    "Sword", "VillageKey", "SewersKey", "SewersGem", "Bonbon", "Badge", "Pass", "LibKey", "Book", "Catakey",
    "Bombs", "SuperBombs", "MissingRail", "TimeStone", "Boat", "ChildKey", "NESPad", "LoveLetter", "LoveProof",
    "PirateFlag", "MagiKey1", "IceBook", "MagiKey2", "MagiKey3", "SylveTear", "MagiKey4", "MagiKey5",
    "DalkinKey", "DalkinMedal", "MagusKey", "IngrA", "IngrB", "IngrC", "Energy", "WingBroken", "WingTravel",
}
FILLER_IDS = {"GreenGoo", "RedGoo", "Gravity"}
FRAGMENTS = ["Fragment of Fire", "Fragment of Ice", "Fragment of Nature", "Fragment of Earth", "Fragment of Time"]


class Evoland2Item(Item):
    game = GAME_NAME


def name_of_record(record: str) -> str:
    """« i:VillageKey » -> « Old House Key » ; « c:manimal » -> « Manimal Card »."""
    kind, value = record.split(":", 1)
    if kind == "c":
        return f"{value[:1].upper()}{value[1:]} Card"
    return ITEM_NAMES.get(value, value)


def name_of_id(internal_id: str) -> str:
    return ITEM_NAMES.get(internal_id, internal_id)


def classification_of(record: str) -> ItemClassification:
    kind, value = record.split(":", 1)
    if kind == "c":
        return USEFUL
    if value in PROGRESSION_IDS:
        return PROG
    if value in FILLER_IDS:
        return FILLER
    return USEFUL


# nom -> enregistrement envoyé au jeu, pour tous les contenus possibles
item_records: dict[str, str] = {}
for _name, _key, _region, _record, _req in LOCATIONS:
    item_records[name_of_record(_record)] = _record


def _item_id(name: str) -> int:
    return BASE_ID + zlib.crc32(name.encode()) % 1_000_000


item_name_to_id = {name: _item_id(name) for name in item_records}
assert len(set(item_name_to_id.values())) == len(item_name_to_id), "collision d'identifiants d'objets"
item_id_to_record = {item_name_to_id[name]: record for name, record in item_records.items()}

item_name_groups = {
    "Fragments": set(FRAGMENTS),
    "Cards": {name for name, record in item_records.items() if record.startswith("c:")},
    "Keys": {"Old House Key", "Sewers Key", "Library Key", "Children's Key", "Dalkin's House Key", "Magus's Key"},
}
