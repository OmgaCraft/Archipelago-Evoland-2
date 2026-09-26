"""Copie les fichiers d'Evoland 2 dans le dépôt GitHub (Archipelago-Evoland-2).

Seul notre code est copié : aucun fichier du jeu (hlboot.dat, .pak, data.cdb, scripts extraits).
Le README et le .gitignore sont écrits directement dans le dépôt.

Usage : python tools/evo2_sync_repo.py [dossier du dépôt]
"""
import os
import shutil
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_REPO = os.path.join(ROOT, "..", "Archipelago-Evoland-2")

FOLDERS = ["apworld/evoland2"]
FILES = [
    "patcher/hlpatch.py",
    "patcher/evoland2_patch.py",
    "patcher/build_all.py",
    "tools/pak.py",
    "tools/hl.sh",
    "tools/evo2_catalog.py",
    "tools/evo2_build_locations.py",
    "tools/evo2_build_apworld.py",
    "tools/evo2_loopback.py",
    "tools/evo2_item_usage.py",
    "tools/evo2_code_refs.py",
    "tools/evo2_sync_repo.py",
    "docs/NOTES_EVOLAND2.md",
]


def ignore(folder, names):
    return [n for n in names if n == "__pycache__" or n.endswith(".pyc")]


if __name__ == "__main__":
    repo = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_REPO)
    if not os.path.isdir(os.path.join(repo, ".git")):
        sys.exit(f"Pas un dépôt git : {repo}")
    for folder in FOLDERS:
        source, target = os.path.join(ROOT, folder), os.path.join(repo, folder)
        # mise à jour sur place (OneDrive peut verrouiller un dossier qu'on tenterait de supprimer)
        shutil.copytree(source, target, ignore=ignore, dirs_exist_ok=True)
        for current, dirs, files in os.walk(target):
            for file in files:
                path = os.path.join(current, file)
                if not os.path.exists(os.path.join(source, os.path.relpath(path, target))):
                    os.remove(path)
    for file in FILES:
        target = os.path.join(repo, file)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copy2(os.path.join(ROOT, file), target)
    print("Fichiers copiés dans", repo)
