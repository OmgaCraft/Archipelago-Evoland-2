"""Construit evoland2.apworld et l'installe dans le dossier custom_worlds d'Archipelago.

Usage : python tools/evo2_build_apworld.py [--no-install]
"""
import os
import shutil
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SOURCE = os.path.join(ROOT, "apworld", "evoland2")
BUILD = os.path.join(ROOT, "build", "evoland2.apworld")
CUSTOM_WORLDS = r"C:\ProgramData\Archipelago\custom_worlds"

if __name__ == "__main__":
    os.makedirs(os.path.dirname(BUILD), exist_ok=True)
    with zipfile.ZipFile(BUILD, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder, dirs, files in os.walk(SOURCE):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                path = os.path.join(folder, file)
                zf.write(path, os.path.join("evoland2", os.path.relpath(path, SOURCE)))
    print("Construit :", BUILD)
    if "--no-install" not in sys.argv:
        shutil.copy2(BUILD, CUSTOM_WORLDS)
        print("Installé dans :", CUSTOM_WORLDS)
