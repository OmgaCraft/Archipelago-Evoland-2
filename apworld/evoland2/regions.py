"""Régions d'Evoland 2 (chapitres de l'histoire) et règles d'accès.

Les passages entre régions suivent l'ordre de l'histoire (voir la soluce et les sauvegardes de
chapitres des développeurs, `$State.get`). Les prérequis d'objets viennent de l'analyse des scripts
(`docs/evo2_item_usage.md`), des portes des niveaux et du tableur communautaire « Evoland 2 Items,
Flags and Logic ». En cas de doute, la logique demande plus que nécessaire plutôt que moins.
"""
from typing import TYPE_CHECKING, Callable

from BaseClasses import CollectionState, ItemClassification, Region

from .items import FRAGMENTS, Evoland2Item, name_of_id
from .location_data import LOCATIONS
from .locations import Evoland2Location, location_name_to_id

if TYPE_CHECKING:
    from . import Evoland2World

Rule = Callable[[CollectionState], bool]
Requirements = dict[str, int]  # nom d'objet (ou d'événement) -> nombre

# (origine, destination, prérequis avec les noms Archipelago)
CONNECTIONS: list[tuple[str, str, Requirements]] = [
    ("Menu", "Nibiru", {}),
    # Le garde de Nibiru bloque la forêt tant que le coffre de la vieille maison (fermée à clé)
    # n'a pas été ouvert (FirstVillage.js, on_lockSword / drapeau foundSword).
    ("Nibiru", "Spelbuk Forest", {"Old Sword": 1, "Old House Key": 1}),
    ("Spelbuk Forest", "Early Past", {}),
    ("Early Past", "Imperial Prison", {}),
    ("Imperial Prison", "Genova Sewers", {}),
    # Fuite par les égouts : deux portes à clé (les gemmes servent à la partie « maison aux poules »)
    ("Genova Sewers", "Genova (Past)", {"Sewers Key": 2}),
    ("Genova (Past)", "Past Overworld", {"Sewers Key": 3}),
    ("Past Overworld", "Haunted Forest", {}),
    ("Haunted Forest", "Jatai's Lair", {}),
    # Menos niveau 2 (1 Maana chez Bibi) pour casser le rocher du pont de Mayenne
    ("Jatai's Lair", "Genova (Future)", {"Maana": 1}),
    ("Genova (Future)", "Great Library", {"Library Key": 1}),
    ("Great Library", "Windy Valley Caverns", {}),
    ("Windy Valley Caverns", "Pyramid of the Prophet", {}),
    ("Pyramid of the Prophet", "Cursed Isle", {"Pass": 1, "Stone of Time": 1}),
    ("Cursed Isle", "Present World", {"Boat": 1}),
    ("Present World", "Genova (Present)", {}),
    ("Genova (Present)", "Mine", {"Children's Key": 5}),
    ("Mine", "Laboratory", {"Bombs": 1, "Super Bombs": 1, "Missing Rail": 3}),
    ("Laboratory", "Eye of the Storm", {}),
    # Terminal de contrôle : voyage libre dans le temps (acte 2)
    ("Eye of the Storm", "Free Time Travel", {"Control Terminal": 1, "Maana": 2}),
    ("Free Time Travel", "Time Fragment Quest", {}),
    # Le garde de Windy Valley (futur) bloque le Magilith antique tant que Sid n'a pas reçu le
    # Prototype X-01 (Windvalley2.js, locker ; present/Windvalley.js, act_inv)
    ("Time Fragment Quest", "Anomaly", {"Prototype X-01": 1}),
    ("Free Time Travel", "Skies", {"Flying Machine": 1}),
    ("Free Time Travel", "Fire Fragment Quest", {"Boat": 1}),
    ("Free Time Travel", "Ice Fragment Quest", {}),
    ("Free Time Travel", "Earth Fragment Quest", {"Dalkin's Medal": 1}),
    ("Free Time Travel", "Nature Fragment Quest", {}),
    # Acte 3 (5 fragments), Gardien ailé vaincu en machine volante, puis le portail du boss final
    # s'ouvre en posant la Pierre du Temps (Glitch.js, on_finalInit)
    ("Free Time Travel", "Final Battle",
     {"Stone of Time": 1, "Flying Machine": 1, **{name: 1 for name in FRAGMENTS}}),
]

# Événements (pas des checks) : (région, nom, prérequis)
EVENTS: list[tuple[str, str, Requirements]] = [
    # La machine volante de l'Anomalie ne se prend qu'avec le Fragment du Temps (Glitch.js, act_wing)
    ("Anomaly", "Flying Machine", {"Fragment of Time": 1}),
    ("Final Battle", "Victory", {}),
]


def rule_for(requirements: Requirements, player: int) -> Rule:
    if not requirements:
        return lambda state: True
    items = dict(requirements)
    return lambda state: all(state.has(name, player, count) for name, count in items.items())


def translate(requirements: dict[str, int]) -> Requirements:
    """Prérequis de location_data (identifiants du jeu) -> noms Archipelago."""
    return {name_of_id(item): count for item, count in requirements.items()}


def create_regions(world: "Evoland2World") -> None:
    player = world.player
    multiworld = world.multiworld
    names = {"Menu"} | {dest for _, dest, _ in CONNECTIONS}
    regions = {name: Region(name, player, multiworld) for name in names}

    for name, _key, region_name, _record, requirements in LOCATIONS:
        region = regions[region_name]
        location = Evoland2Location(player, name, location_name_to_id[name], region)
        location.access_rule = rule_for(translate(requirements), player)
        region.locations.append(location)

    for region_name, event, requirements in EVENTS:
        region = regions[region_name]
        location = Evoland2Location(player, event, None, region)
        location.access_rule = rule_for(requirements, player)
        location.place_locked_item(Evoland2Item(event, ItemClassification.progression, None, player))
        region.locations.append(location)

    for origin, dest, requirements in CONNECTIONS:
        if dest == "Final Battle" and world.stars_required:
            requirements = {**requirements, "Star": world.stars_required}
        regions[origin].connect(regions[dest], f"{origin} -> {dest}", rule_for(requirements, player))

    multiworld.regions += regions.values()
