# Archipelago – Evoland 2

Monde [Archipelago](https://archipelago.gg) (randomizer multi-jeux) pour **Evoland 2**, dans
**Evoland Legendary Edition** (version Steam).

*English version below.*

**Version 0.1.0** : première version jouable, en test.

## Ce qui est mélangé

- **143 locations** : tous les coffres, les récompenses de quête et les objets ramassés au sol.
- Leur contenu est mélangé avec le reste du multiworld, **y compris les objets d'histoire** (clés,
  Bombes, Pierre du Temps, Bateau, Terminal de contrôle, les 5 fragments de la Clé Magi…).
- Exceptions (comportement normal) : le coffre de la prison qui rend l'arme confisquée, le dépôt d'or
  de Mr Mudwell et les achats en boutique. Le pêcheur de Nibiru donne toujours la Clé de la vieille
  maison (la sortie du village exige d'ouvrir le coffre de cette maison).

## Objectif (option `goal`)

- `final_boss` : vaincre le boss final.
- `final_boss_and_stars` : vaincre le boss final, mais son portail reste **fermé en jeu** tant que vous
  n'avez pas le nombre d'étoiles demandé (option `stars_required`, de 1 à 30).

## Installation

Il faut votre propre copie d'Evoland Legendary Edition (Steam) et Archipelago 0.6.4 ou plus récent.
Ce dépôt ne contient **aucun fichier du jeu**.

1. **Monde Archipelago** : copier `evoland2.apworld` (page *Releases*, ou à construire avec
   `python tools/evo2_build_apworld.py --no-install`, résultat dans `build/`) dans le dossier
   `custom_worlds` d'Archipelago, puis relancer le Launcher.
2. **Patch du jeu** (Python 3.10+ et [crashlink](https://pypi.org/project/crashlink/) 0.0.9 :
   `pip install crashlink==0.0.9`) :
   ```
   cd patcher
   python build_all.py "<dossier du jeu>/hlboot.dat" hlboot_patche.dat
   ```
   Gardez une copie de l'`hlboot.dat` d'origine, puis remplacez-le par `hlboot_patche.dat`.
   Partez **toujours** du fichier d'origine (Evoland 1 et 2 partagent ce fichier : si vous jouez aussi
   à Evoland 1 avec Archipelago, il faut un `hlboot.dat` qui contient les deux patchs).

## Jouer

1. Générer et héberger la partie (archipelago.gg ou serveur local).
2. Dans le Launcher, ouvrir **Evoland 2 Client** et se connecter. Le dossier du jeu est trouvé dans
   Steam ; sinon : `/gamedir <dossier du jeu>`.
3. Lancer le jeu, choisir **Evoland 2** et commencer **une nouvelle sauvegarde** par partie.
4. Garder le client ouvert pendant la partie.

Le jeu et le client échangent par fichiers dans le dossier `archipelago2/` du jeu.

## Logique

La logique suit l'histoire (actes 1 à 3) et les prérequis vérifiés dans les scripts du jeu : glace de
Velvet, éboulement vers Nibiru levé à l'acte 2, coffres qui n'apparaissent qu'à l'acte 3, garde de
Windy Valley (Prototype X-01), Colisée ouvert après le repaire des pirates, etc.
Voir `apworld/evoland2/regions.py` et `tools/evo2_build_locations.py`.

## Organisation du dépôt

| Dossier | Contenu |
| --- | --- |
| `apworld/evoland2/` | le monde Archipelago (objets, locations, régions, options, client) |
| `patcher/` | le patch du bytecode HashLink du jeu (`evoland2_patch.py`), la boîte à outils `hlpatch.py` |
| `tools/` | extraction des données (`pak.py`), catalogue des locations, génération de `location_data.py`, construction de l'apworld, client de test « loopback » |
| `docs/` | notes techniques |

Pour régénérer les données : extraire `evo2.pak` du jeu avec `tools/pak.py` vers `extracted/evo2/`,
puis lancer `tools/evo2_catalog.py`, `tools/evo2_build_locations.py` et `tools/evo2_build_apworld.py`.

## Limites connues

- Le verrou d'étoiles du boss final n'a pas encore été testé en jeu.
- Les noms des cartes reprennent leurs identifiants internes (ex. « Shooter1 Card »).
- Boutiques, mini-jeux de cartes et défis de duel ne sont pas mélangés.

## Crédits

- Evoland 2 : Shiro Games. Ce projet n'est ni affilié ni approuvé par Shiro Games.
- Références de logique : le guide Steam d'Evoland 2 et le tableur communautaire
  [Evoland 2 Items, Flags and Logic](https://docs.google.com/spreadsheets/d/1z8olt25UQ6uwJfjUcqqZWrySkZK8X4EECW4i_wOoP7k).
- Outils : [crashlink](https://pypi.org/project/crashlink/), [hlbc](https://github.com/Gui-Yom/hlbc).

---

# Archipelago – Evoland 2 (English)

[Archipelago](https://archipelago.gg) world for **Evoland 2** in **Evoland Legendary Edition** (Steam).
**Version 0.1.0**, first playable test version.

- **143 locations** (every chest, quest reward and ground pickup), shuffled with the whole multiworld,
  story items included. Exceptions: the prison chest returning your weapon, Mr Mudwell's gold deposit,
  shop purchases; Old Pol always gives the Old House Key.
- **Goal**: `final_boss`, or `final_boss_and_stars` (the final boss portal stays closed in game until
  you have `stars_required` Stars).

**Install**: put `evoland2.apworld` in Archipelago's `custom_worlds` folder. Patch the game with
`python patcher/build_all.py "<game folder>/hlboot.dat" patched.dat` (needs Python 3.10+ and
`crashlink==0.0.9`), keep a backup of the original `hlboot.dat` and replace it with the patched file.
Always start from the original file. No game files are included in this repository.

**Play**: open **Evoland 2 Client** from the Launcher, connect, start the game, pick Evoland 2 and
start a new save for each Archipelago game. Keep the client running.
