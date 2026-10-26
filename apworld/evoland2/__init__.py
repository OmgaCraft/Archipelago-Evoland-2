"""Evoland 2 — monde Archipelago.

Toutes les locations (coffres, récompenses de quête, objets au sol) ont leur contenu mélangé,
y compris les objets d'histoire. Le jeu patché (patcher/evoland2_patch.py) et le client
(client.py) échangent par fichiers dans le dossier `archipelago2/` du jeu.
"""
from typing import Any

from BaseClasses import ItemClassification, Tutorial
from worlds.AutoWorld import WebWorld, World
from worlds.LauncherComponents import Component, Type, components, launch_subprocess

from .items import (
    GAME_NAME, Evoland2Item, classification_of, item_name_groups, item_name_to_id, item_records,
    name_of_record,
)
from .location_data import LOCATIONS
from .locations import location_name_groups, location_name_to_id
from .options import Evoland2Options, evoland2_option_groups
from .regions import create_regions

APWORLD_VERSION = "0.1.3"

# Locations dont le contenu reste celui d'origine (le check est quand même envoyé) :
# la sortie de Nibiru exige d'ouvrir la vieille maison, donc la clé doit venir du pêcheur.
LOCKED_VANILLA = {"Nibiru (Present) - Old Pol's Reward"}


def launch_client(*args: str) -> None:
    from .client import launch
    launch_subprocess(launch, name="Evoland2Client", args=args)


components.append(Component("Evoland 2 Client", func=launch_client, component_type=Type.CLIENT))


class Evoland2Web(WebWorld):
    theme = "grass"
    option_groups = evoland2_option_groups
    tutorials = [
        Tutorial("Multiworld Setup Guide", "A guide to setting up Evoland 2 for Archipelago.",
                 "English", "setup_en.md", "setup/en", ["OmgaCraft"]),
        Tutorial("Guide d'installation Multiworld", "Un guide pour configurer Evoland 2 avec Archipelago.",
                 "Français", "setup_fr.md", "setup/fr", ["OmgaCraft"]),
    ]


class Evoland2World(World):
    """
    Evoland 2 is an adventure through time and through the history of video games: Zelda-like
    dungeons, platforming, shoot 'em up, fighting games and more, across the past, present and
    future. In this randomizer, every chest and quest reward can hold an item from the multiworld.
    """
    game = GAME_NAME
    web = Evoland2Web()
    options_dataclass = Evoland2Options
    options: Evoland2Options

    item_name_to_id = item_name_to_id
    location_name_to_id = location_name_to_id
    item_name_groups = item_name_groups
    location_name_groups = location_name_groups

    stars_required: int = 0

    def generate_early(self) -> None:
        if self.options.goal == self.options.goal.option_final_boss_and_stars:
            self.stars_required = self.options.stars_required.value
        # L'épée est indispensable pour quitter Nibiru : elle est placée tôt, dans ce monde.
        self.multiworld.local_early_items[self.player]["Old Sword"] = 1

    def create_regions(self) -> None:
        create_regions(self)
        self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)

    def create_items(self) -> None:
        pool = []
        for name, _key, _region, record, _req in LOCATIONS:
            item = self.create_item(name_of_record(record))
            if name in LOCKED_VANILLA:
                self.get_location(name).place_locked_item(item)
            else:
                pool.append(item)
        self.multiworld.itempool += pool

    def create_item(self, name: str) -> Evoland2Item:
        classification = classification_of(item_records[name])
        if name == "Star" and self.stars_required:
            classification = ItemClassification.progression_skip_balancing
        return Evoland2Item(name, classification, item_name_to_id[name], self.player)

    def get_filler_item_name(self) -> str:
        return "Green Goo"

    def fill_slot_data(self) -> dict[str, Any]:
        return {
            "apworld_version": APWORLD_VERSION,
            "location_keys": [key for _name, key, _region, _record, _req in LOCATIONS],
            "stars_required": self.stars_required,
        }
