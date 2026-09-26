"""Construit le hlboot.dat final avec les patchs d'Evoland 1 ET d'Evoland 2.

Les deux jeux sont dans le même hlboot.dat : il faut toujours partir du fichier d'origine
et appliquer les deux patchs, sinon l'installation de l'un efface l'autre.
Si le patch d'Evoland 1 (evoland_patch.py) est absent, seul celui d'Evoland 2 est appliqué.

Usage : python build_all.py <hlboot.dat d'origine> <hlboot.dat patché>
"""
import sys

from crashlink import Bytecode

import evoland2_patch

try:
    import evoland_patch
except ImportError:
    evoland_patch = None

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bytecode = Bytecode.from_path(src)
    if evoland_patch is not None:
        evoland_patch.build(bytecode)
    evoland2_patch.build(bytecode)
    with open(dst, "wb") as f:
        f.write(bytecode.serialise())
    games = "Evoland 1 + Evoland 2" if evoland_patch is not None else "Evoland 2"
    print(f"hlboot.dat ({games}) écrit :", dst)
