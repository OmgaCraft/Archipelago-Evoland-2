"""Client Archipelago pour Evoland 2 (Evoland Legendary Edition).

Le jeu patché échange avec ce client par des fichiers dans <dossier du jeu>/archipelago2/ :
- config.txt : identifiant de partie (8 chiffres), étoiles exigées pour le boss final (stars=N),
  puis la liste des locations mélangées ;
- items.txt  : tous les items reçus, dans l'ordre, un par ligne (i:<objet>, c:<carte>) ;
- checks/    : un fichier vide par location vérifiée (écrit par le jeu) ;
- seed.txt   : la partie Archipelago associée (pour repartir de zéro avec une nouvelle partie).
"""
import asyncio
import hashlib
import os
import re
import sys
import time
from typing import Optional

import Utils
from CommonClient import (
    ClientCommandProcessor, CommonContext, get_base_parser, gui_enabled, handle_url_arg, logger,
    server_loop,
)
from NetUtils import ClientStatus

from .items import item_id_to_record
from .locations import location_key_to_id

GAME_FOLDER_NAME = "Evoland Legendary Edition"
EXCHANGE_FOLDER = "archipelago2"
PATCH_MARKER = b"archipelago2/checks/"
STORE_KEY = "evoland2"


def session_id(seed_name: str, slot: int) -> int:
    """Identifiant de partie sur 8 chiffres, retenu par la sauvegarde du jeu."""
    digest = hashlib.sha1(f"evoland2/{seed_name}/{slot}".encode()).hexdigest()
    return int(digest, 16) % 10**8 or 1


def is_game_dir(path: Optional[str]) -> bool:
    return bool(path) and os.path.isfile(os.path.join(path, "hlboot.dat"))


def find_steam_game_dir() -> Optional[str]:
    """Cherche le jeu dans les bibliothèques Steam."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as reg:
            steam_path = winreg.QueryValueEx(reg, "SteamPath")[0]
    except OSError:
        return None
    libraries = [steam_path]
    vdf = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")
    if os.path.isfile(vdf):
        with open(vdf, encoding="utf-8", errors="replace") as f:
            libraries += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', f.read())]
    for library in libraries:
        candidate = os.path.join(library, "steamapps", "common", GAME_FOLDER_NAME)
        if is_game_dir(candidate):
            return candidate
    return None


def saved_game_dir() -> Optional[str]:
    """Dossier choisi précédemment avec /gamedir (mémorisé par Archipelago)."""
    return Utils.persistent_load().get(STORE_KEY, {}).get("game_directory")


class Evoland2CommandProcessor(ClientCommandProcessor):
    ctx: "Evoland2Context"

    def _cmd_gamedir(self, path: str = "") -> None:
        """Affiche ou change le dossier du jeu (celui qui contient hlboot.dat)."""
        if path:
            if not is_game_dir(path):
                logger.error(f"Pas de hlboot.dat dans « {path} ».")
                return
            self.ctx.game_dir = path
            Utils.persistent_store(STORE_KEY, "game_directory", path)
            self.ctx.on_game_dir_changed()
        logger.info(f"Dossier du jeu : {self.ctx.game_dir or 'introuvable'}")

    def _cmd_status(self) -> None:
        """Affiche l'état de la liaison avec le jeu."""
        ctx = self.ctx
        logger.info(f"Dossier du jeu : {ctx.game_dir or 'introuvable'}")
        logger.info(f"Jeu patché pour Evoland 2 : {'oui' if ctx.game_is_patched() else 'NON'}")
        logger.info(f"Items reçus : {len(ctx.items_received)} ; checks trouvés : {len(ctx.found_keys)}")


class Evoland2Context(CommonContext):
    game = "Evoland 2"
    items_handling = 0b111  # tous les items, y compris ceux trouvés dans notre propre monde
    command_processor = Evoland2CommandProcessor

    def __init__(self, server_address: Optional[str], password: Optional[str]) -> None:
        super().__init__(server_address, password)
        self.game_dir: Optional[str] = None
        for candidate in (saved_game_dir(), find_steam_game_dir()):
            if is_game_dir(candidate):
                self.game_dir = candidate
                break
        self.location_keys: Optional[list[str]] = None
        self.stars_required = 0
        self.found_keys: set[str] = set()
        self.goal_sent = False
        self.mismatch_reported = False

    @property
    def ap_dir(self) -> str:
        return os.path.join(self.game_dir, EXCHANGE_FOLDER)

    def game_is_patched(self) -> bool:
        if not self.game_dir:
            return False
        try:
            with open(os.path.join(self.game_dir, "hlboot.dat"), "rb") as f:
                return PATCH_MARKER in f.read()
        except OSError:
            return False

    def on_game_dir_changed(self) -> None:
        if not self.game_is_patched():
            logger.warning("Le jeu n'est pas patché pour Evoland 2 : les coffres ne seront pas détectés.")
        if self.location_keys is not None:
            self.prepare_game_folder()

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        if cmd == "Connected":
            self.location_keys = args["slot_data"]["location_keys"]
            self.stars_required = args["slot_data"].get("stars_required", 0)
            self.goal_sent = False
            if not self.game_dir:
                logger.error("Dossier du jeu introuvable : utilisez /gamedir <dossier du jeu>.")
            else:
                self.on_game_dir_changed()
        elif cmd == "ReceivedItems":
            self.write_items()

    def prepare_game_folder(self) -> None:
        """Crée le dossier d'échange et repart de zéro si c'est une nouvelle partie Archipelago."""
        os.makedirs(os.path.join(self.ap_dir, "checks"), exist_ok=True)
        seed_id = f"{self.seed_name}/{self.slot}"
        seed_file = os.path.join(self.ap_dir, "seed.txt")
        previous = open(seed_file).read().strip() if os.path.isfile(seed_file) else None
        if previous != seed_id:
            if previous:
                logger.info("Nouvelle partie Archipelago : commencez une nouvelle sauvegarde d'Evoland 2.")
            for name in os.listdir(os.path.join(self.ap_dir, "checks")):
                os.remove(os.path.join(self.ap_dir, "checks", name))
            self.found_keys.clear()
            with open(seed_file, "w") as f:
                f.write(seed_id)
        config = f"{session_id(self.seed_name, self.slot):08d},"
        if self.stars_required:
            config += f"stars={self.stars_required},"  # portail du boss final bloqué sans ces étoiles
        config += ",".join(self.location_keys) + ","
        with open(os.path.join(self.ap_dir, "config.txt"), "w", encoding="utf-8") as f:
            f.write(config)
        self.write_items()

    def write_items(self) -> None:
        if not self.game_dir or self.location_keys is None:
            return
        records = []
        for network_item in self.items_received:
            record = item_id_to_record.get(network_item.item)
            if record is None:
                logger.warning(f"Item inconnu reçu : {network_item.item}")
                continue
            records.append(record)
        content = "\n".join(records)
        # Écriture directe : le jeu ignore une ligne incomplète et relit le fichier régulièrement.
        for _ in range(10):
            try:
                with open(os.path.join(self.ap_dir, "items.txt"), "w", encoding="utf-8") as f:
                    f.write(content)
                return
            except PermissionError:
                time.sleep(0.05)
        logger.error("Impossible d'écrire items.txt (fichier verrouillé).")

    def run_gui(self) -> None:
        from kvui import GameManager

        class Evoland2Manager(GameManager):
            logging_pairs = [("Client", "Archipelago")]
            base_title = "Archipelago Evoland 2 Client"

        self.ui = Evoland2Manager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")


async def game_watcher(ctx: Evoland2Context) -> None:
    """Surveille les checks écrits par le jeu et les envoie au serveur."""
    while not ctx.exit_event.is_set():
        await asyncio.sleep(0.5)
        if not ctx.game_dir or ctx.location_keys is None or not ctx.slot:
            continue
        checks_dir = os.path.join(ctx.ap_dir, "checks")
        if not os.path.isdir(checks_dir):
            continue
        new_ids = set()
        for name in os.listdir(checks_dir):
            if not name.endswith(".txt"):
                continue
            key = name[:-4]
            if key in ctx.found_keys:
                continue
            ctx.found_keys.add(key)
            if key == "mismatch":
                if not ctx.mismatch_reported:
                    ctx.mismatch_reported = True
                    logger.error("Cette sauvegarde d'Evoland 2 appartient à une autre partie Archipelago : "
                                 "rien ne sera envoyé ni reçu. Commencez une nouvelle sauvegarde.")
                os.remove(os.path.join(checks_dir, name))
                continue
            location_id = location_key_to_id.get(key)
            if location_id is not None and location_id in ctx.server_locations:
                new_ids.add(location_id)
        if new_ids:
            await ctx.check_locations(new_ids)
        if "goal" in ctx.found_keys and not ctx.goal_sent:
            ctx.goal_sent = True
            await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
            ctx.finished_game = True


def launch(*args: str) -> None:
    parser = get_base_parser(description="Evoland 2 Archipelago Client")
    parser.add_argument("--name", default=None, help="Nom du slot à utiliser.")
    parser.add_argument("--gamedir", default=None, help="Dossier du jeu (contenant hlboot.dat).")
    parser.add_argument("url", nargs="?", help="Lien de connexion archipelago://")
    parsed = handle_url_arg(parser.parse_args(args), parser=parser)

    async def main() -> None:
        ctx = Evoland2Context(parsed.connect, parsed.password)
        ctx.auth = parsed.name
        if parsed.gamedir:
            ctx.game_dir = parsed.gamedir
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")
        watcher = asyncio.create_task(game_watcher(ctx), name="Evoland2GameWatcher")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        if ctx.game_dir:
            logger.info(f"Dossier du jeu : {ctx.game_dir}")
            if not ctx.game_is_patched():
                logger.warning("Le jeu n'est pas patché pour Evoland 2.")
        else:
            logger.warning("Dossier du jeu introuvable : utilisez /gamedir <dossier du jeu>.")
        await ctx.exit_event.wait()
        await ctx.shutdown()
        watcher.cancel()

    Utils.init_logging("Evoland2Client", exception_logger="Client")
    asyncio.run(main())
