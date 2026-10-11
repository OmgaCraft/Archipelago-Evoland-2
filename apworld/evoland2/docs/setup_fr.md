# Guide d'installation d'Evoland 2

> **Version 0.1.2 (test).** Evoland 2 dans Evoland Legendary Edition (Steam).

## Installation

1. Copier `evoland2.apworld` dans le dossier `custom_worlds` d'Archipelago, puis relancer le Launcher.
2. Patcher le jeu : construire un `hlboot.dat` patché à partir de **votre** `hlboot.dat` d'origine
   avec `patcher/build_all.py` (voir le README du dépôt
   https://github.com/OmgaCraft/Archipelago-Evoland-2), garder une copie de l'original, puis remplacer
   `hlboot.dat` dans le dossier du jeu. Si vous jouez aussi à Evoland 1 avec Archipelago, le fichier doit
   contenir les patchs des deux jeux.

## Jouer

1. Générer et héberger la partie (archipelago.gg ou serveur local).
2. Dans le Launcher, ouvrir **Evoland 2 Client** et se connecter avec son nom de slot. Le dossier du
   jeu est trouvé dans Steam ; sinon : `/gamedir <dossier du jeu>`.
3. Lancer le jeu depuis Steam, choisir **Evoland 2** et **commencer une nouvelle sauvegarde**
   (une sauvegarde par partie Archipelago).
4. Garder le client ouvert pendant la partie.

## Ce qui est mélangé

Tous les coffres, récompenses de quête et objets ramassés au sol (143 locations) : étoiles, minerais
d'Orikon, Maana, cartes, mais aussi les objets d'histoire (clés, Bombes, Pierre du Temps, Bateau,
Terminal de contrôle, les 5 fragments de la Clé Magi…).

Exceptions (comportement normal) : le coffre de la prison qui rend l'arme confisquée, le dépôt d'or
de Mr Mudwell et les achats en boutique. La récompense du pêcheur de Nibiru donne toujours la Clé de
la vieille maison : la sortie du village exige d'ouvrir le coffre de cette maison.

## Commandes du client

- `/gamedir [dossier]` : affiche ou change le dossier du jeu.
- `/status` : état de la liaison avec le jeu.
