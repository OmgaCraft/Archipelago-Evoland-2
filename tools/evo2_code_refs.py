"""Cherche les fonctions du code (bytecode) qui utilisent une chaîne donnée (ex. un nom d'objet).

Les chaînes littérales Haxe sont des globales initialisées par la table des constantes.
Usage : python tools/evo2_code_refs.py Gravity Bombs Boat ...
"""
import sys

from crashlink import Bytecode

bc = Bytecode.from_path("extracted/hlboot.dat")
wanted = set(sys.argv[1:])

# globale -> texte, pour les constantes de type String
string_globals = {}
for const in bc.constants:
    if len(const.fields) >= 1:
        try:
            text = bc.strings.value[const.fields[0].value]
        except (IndexError, AttributeError):
            continue
        if text in wanted:
            string_globals[const._global.value] = text

found = {w: [] for w in wanted}
for func in bc.functions:
    for i, op in enumerate(func.ops):
        g = None
        if op.op == "GetGlobal":
            g = op.df["global"].value
            text = string_globals.get(g)
        elif op.op == "String":
            text = bc.strings.value[op.df["ptr"].value]
            text = text if text in wanted else None
        else:
            continue
        if text:
            found[text].append(f"{bc.full_func_name(func)}@{func.findex.value} op{i}")
for w in sorted(found):
    print(f"== {w} ({len(found[w])})")
    for f in sorted(set(found[w]))[:25]:
        print("   ", f)
