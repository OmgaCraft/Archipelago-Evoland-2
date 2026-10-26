"""Répare une sauvegarde d'Evoland 2 abîmée par le bug des fins de ligne du client 0.1.0.

Le client 0.1.0 écrivait items.txt avec « \\r\\n » : le jeu a ajouté à l'inventaire des objets
« Objet\\r » inconnus, et le menu plante (« Null access » dans ui.MenuItems). Cet outil retire le
« \\r », fusionne les doublons (le jeu ne lit que la première ligne d'un objet) et recalcule la somme
de contrôle de la sauvegarde (hxd.Save : sérialisation Haxe + « # » + CRC).

Option --move <niveau>:<époque>:<ancre> : replace le héros sur une ancre d'un niveau (pour sortir d'un
blocage), par ex. --move MagiIsland:past:magFront. Époques : past, present, futur, antik.

Usage : python tools/evo2_save_fix.py <slotN.sav> [fichier de sortie] [--move niveau:époque:ancre]
Sans fichier de sortie, n'écrit rien et affiche seulement ce qui serait corrigé.
"""
import hashlib
import re
import sys
from urllib.parse import quote, unquote

SALT = "s*al!t"  # sel par défaut de hxd.Save (vérifié sur une sauvegarde vide du jeu)


def make_crc(data: str) -> str:
    inner = hashlib.sha1((data + SALT).encode("utf-8")).hexdigest()
    return hashlib.sha1((data + inner).encode("utf-8")).hexdigest()[4:36]


def url_encode(text: str) -> str:
    return quote(text, safe="-_.~!*'()")


class Parser:
    """Désérialiseur Haxe minimal : garde les nombres tels quels pour un aller-retour exact."""

    NUMBER = re.compile(r"-?[0-9.eE+\-]+")

    def __init__(self, text: str):
        self.text, self.pos, self.strings = text, 0, []

    def peek(self) -> str:
        return self.text[self.pos]

    def take(self) -> str:
        c = self.text[self.pos]
        self.pos += 1
        return c

    def number(self) -> str:
        m = self.NUMBER.match(self.text, self.pos)
        self.pos = m.end()
        return m.group()

    def parse(self):
        c = self.take()
        if c in "ntfzkmp":
            return (c,)
        if c in "idr":
            return (c, self.number())
        if c == "y":
            length = int(self.number())
            assert self.take() == ":"
            raw = self.text[self.pos:self.pos + length]
            self.pos += length
            value = unquote(raw)
            assert url_encode(value) == raw, f"encodage inattendu : {raw!r}"
            self.strings.append(value)
            return ("s", value)
        if c == "R":
            return ("s", self.strings[int(self.number())])
        if c in "oc":
            name = self.parse()[1] if c == "c" else None
            fields = []
            while self.peek() != "g":
                key = self.parse()
                fields.append((key[1], self.parse()))
            self.take()
            return (c, fields, name)
        if c in "wj":
            name = self.parse()[1]
            if c == "w":
                tag = self.parse()[1]
            else:
                assert self.take() == ":"
                tag = self.number()
            assert self.take() == ":"
            args = [self.parse() for _ in range(int(self.number()))]
            return (c, name, tag, args)
        if c in "alb":
            items = []
            while self.peek() != "h":
                if c == "a" and self.peek() == "u":
                    self.take()
                    items.append(("u", self.number()))
                elif c == "b":
                    key = self.parse()
                    items.append((key[1], self.parse()))
                else:
                    items.append(self.parse())
            self.take()
            return (c, items)
        if c == "q":
            items = []
            while self.peek() != "h":
                assert self.take() == ":"
                items.append((self.number(), self.parse()))
            self.take()
            return ("q", items)
        raise ValueError(f"type de donnée non géré {c!r} à la position {self.pos - 1}")


class Serializer:
    def __init__(self):
        self.out, self.cache = [], {}

    def string(self, value: str) -> None:
        if value in self.cache:
            self.out.append(f"R{self.cache[value]}")
        else:
            self.cache[value] = len(self.cache)
            raw = url_encode(value)
            self.out.append(f"y{len(raw)}:{raw}")

    def write(self, node) -> str:
        kind = node[0]
        if kind in "ntfzkmp":
            self.out.append(kind)
        elif kind in "idr":
            self.out.append(kind + node[1])
        elif kind == "s":
            self.string(node[1])
        elif kind in "oc":
            self.out.append(kind)
            if kind == "c":
                self.string(node[2])
            for key, value in node[1]:
                self.string(key)
                self.write(value)
            self.out.append("g")
        elif kind in "alb":
            self.out.append(kind)
            for item in node[1]:
                if kind == "b":
                    self.string(item[0])
                    self.write(item[1])
                elif item[0] == "u":
                    self.out.append("u" + item[1])
                else:
                    self.write(item)
            self.out.append("h")
        elif kind == "q":
            self.out.append("q")
            for key, value in node[1]:
                self.out.append(":" + key)
                self.write(value)
            self.out.append("h")
        elif kind in "wj":
            self.out.append(kind)
            self.string(node[1])
            if kind == "w":
                self.string(node[2])
            else:
                self.out.append(":" + node[2])
            self.out.append(f":{len(node[3])}")
            for arg in node[3]:
                self.write(arg)
        return "".join(self.out)


def load(text: str):
    parser = Parser(text)
    node = parser.parse()
    assert parser.pos == len(text), "données en trop après la sauvegarde"
    assert Serializer().write(node) == text, "l'aller-retour ne redonne pas le même texte"
    return node


def fix_inventory(inventory, log) -> bool:
    """Retire les « \\r » et fusionne les doublons ; renvoie True si quelque chose a changé."""
    merged, changed = {}, False
    result = []
    for entry in inventory[1]:
        fields = dict(entry[1])
        kind = fields["kind"][1]
        clean = kind.rstrip("\r\n")
        qty = int(fields["qty"][1]) if fields["qty"][0] == "i" else 0
        if clean != kind:
            log(f"  objet invalide {kind!r} -> {clean!r}")
            changed = True
        if clean in merged:
            target = merged[clean]
            total = int(target["qty"][1]) + qty if target["qty"][0] == "i" else qty
            target["qty"] = ("i", str(total))
            log(f"  doublon {clean!r} fusionné (quantité {total})")
            changed = True
            continue
        fields["kind"] = ("s", clean)
        merged[clean] = fields
        result.append(fields)
    # on garde l'ordre des champs d'origine (qty puis kind, ou l'inverse)
    order = [key for key, _ in inventory[1][0][1]] if inventory[1] else []
    inventory[1][:] = [("o", [(key, fields[key]) for key in order], None) for fields in result]
    return changed


def walk(node, log) -> bool:
    """Corrige tous les inventaires, y compris dans les états sérialisés imbriqués (chaînes)."""
    changed = False
    kind = node[0]
    if kind in "oc":
        for i, (key, value) in enumerate(node[1]):
            if key == "inventory" and value[0] == "a":
                changed |= fix_inventory(value, log)
            elif value[0] == "s" and "inventory" in value[1] and value[1][:1] in "oc":
                inner = load(value[1])
                if walk(inner, log):
                    node[1][i] = (key, ("s", Serializer().write(inner)))
                    changed = True
            else:
                changed |= walk(value, log)
    elif kind in "alb":
        for item in node[1]:
            if kind == "b":
                changed |= walk(item[1], log)
            elif item[0] != "u":
                changed |= walk(item, log)
    elif kind == "q":
        for _key, value in node[1]:
            changed |= walk(value, log)
    elif kind in "wj":
        for arg in node[3]:
            changed |= walk(arg, log)
    return changed


TIMES = {"past": 0, "present": 1, "futur": 2, "antik": 3}


def move_hero(root, target: str, log) -> None:
    """Place le héros sur une ancre (Game.hx : une ancre définie l'emporte sur heroX/heroY)."""
    level, time, anchor = target.split(":")
    state = dict(root[1])["data"]
    fields = state[1]
    index = {key: i for i, (key, _) in enumerate(fields)}
    old = dict(fields)
    log(f"  héros : {old['currentLevel'][1]} (époque {old['currentTime']}) -> {level} ({time}), ancre {anchor}")
    number = TIMES[time]
    fields[index["currentLevel"]] = ("currentLevel", ("s", level))
    fields[index["currentTime"]] = ("currentTime", ("z",) if number == 0 else ("i", str(number)))
    fields[index["startAnchor"]] = ("startAnchor", ("s", anchor))
    # le dernier point de passage appartient à l'ancien niveau : on le vide (valeur d'une partie neuve)
    fields[index["lastCheckPoint"]] = ("lastCheckPoint", ("n",))


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--move")]
    move = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--move=")), None)
    if "--move" in sys.argv:
        move = sys.argv[sys.argv.index("--move") + 1]
        args.remove(move)
    source = args[0]
    text = open(source, encoding="utf-8", newline="").read()
    data, _, crc = text.rpartition("#")
    assert make_crc(data) == crc, "somme de contrôle de la sauvegarde invalide"
    root = load(data)
    changed = walk(root, print)
    if move:
        move_hero(root, move, print)
        changed = True
    if not changed:
        print("Rien à corriger.")
        return
    fixed = Serializer().write(root)
    load(fixed)  # relecture de contrôle
    if len(args) > 1:
        with open(args[1], "w", encoding="utf-8", newline="") as f:
            f.write(fixed + "#" + make_crc(fixed))
        print("Sauvegarde corrigée écrite :", args[1])
    else:
        print("(simulation : aucun fichier écrit)")


if __name__ == "__main__":
    main()
