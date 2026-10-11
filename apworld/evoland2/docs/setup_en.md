# Evoland 2 Setup Guide

> **Version 0.1.2 (test).** Evoland 2 inside Evoland Legendary Edition (Steam).

## Installation

1. Copy `evoland2.apworld` into the `custom_worlds` folder of Archipelago and restart the Launcher.
2. Patch the game: build a patched `hlboot.dat` from **your own** original `hlboot.dat` with
   `patcher/build_all.py` (see the README of https://github.com/OmgaCraft/Archipelago-Evoland-2),
   keep a copy of the original, then replace `hlboot.dat` in the game folder. If you also play
   Evoland 1 with Archipelago, the file must contain the patches of both games.

## Playing

1. Generate and host the game (archipelago.gg or the local server).
2. In the Launcher, open **Evoland 2 Client** and connect with your slot name. The game folder is
   found in your Steam libraries; otherwise use `/gamedir <game folder>`.
3. Start the game from Steam, choose **Evoland 2** and **start a new save file**
   (one save file per Archipelago game).
4. Keep the client open while playing.

## Client commands

- `/gamedir [folder]`: show or change the game folder.
- `/status`: show the link state with the game.
