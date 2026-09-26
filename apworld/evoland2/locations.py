"""Locations d'Evoland 2 (table générée dans location_data.py)."""
import zlib

from BaseClasses import Location

from .items import GAME_NAME
from .location_data import LOCATIONS

BASE_ID = 74_320_000


class Evoland2Location(Location):
    game = GAME_NAME


def _location_id(key: str) -> int:
    # identifiant stable dérivé de la clé en jeu (ne change pas si on ajoute des locations)
    return BASE_ID + zlib.crc32(key.encode()) % 1_000_000


location_name_to_id = {name: _location_id(key) for name, key, _region, _record, _req in LOCATIONS}
assert len(set(location_name_to_id.values())) == len(location_name_to_id), "collision d'identifiants"
assert len(location_name_to_id) == len(LOCATIONS), "noms de locations en double"
location_key_to_id = {key: _location_id(key) for _name, key, _region, _record, _req in LOCATIONS}

location_name_groups: dict[str, set[str]] = {}
for _name, _key, _region, _record, _req in LOCATIONS:
    location_name_groups.setdefault(_region, set()).add(_name)
