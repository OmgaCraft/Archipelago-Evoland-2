"""Patch Archipelago pour la partie Evoland 2 d'Evoland Legendary Edition.

Protocole par fichiers, dans le dossier `archipelago2/` du jeu (créé par le client) :

- `archipelago2/config.txt` (client -> jeu) :
      8 chiffres = identifiant de la partie Archipelago, puis éventuellement ",stars=N" (étoiles
      exigées pour franchir le portail du boss final), puis ",clé1,clé2,...,clén," = liste des
      locations dont le contenu est mélangé. Une location absente de la liste garde son contenu
      d'origine. Sans ce fichier, le jeu se comporte normalement.
- `archipelago2/checks/<clé>.txt` (jeu -> client) : un fichier vide par location vérifiée.
      c<époque>_<niveau>_<uid>          coffre (uid = x + y * largeur du niveau)
      s<époque>_<niveau>_<quoi>_<n>     autre source (script, objet au sol…) ; quoi = objet ou
                                        card:<carte> ; n = n-ième fois dans cette sauvegarde
      goal                              générique de fin
      mismatch                          la sauvegarde appartient à une autre partie Archipelago
- `archipelago2/items.txt` (client -> jeu) : tous les items reçus, dans l'ordre, un par ligne :
      i:<objet>   c:<carte>   g:<or>
      Le nombre d'items déjà appliqués est stocké dans la sauvegarde (state.globalFlags).

Pièges du JIT de cette version de HashLink (« JIT ERROR 0 (jit.c line 524) » au lancement) :
- pas de variable globale de type bool (utiliser un i32 0/1) ;
- pas de ToDyn sur un null<i32> (le convertir d'abord en i32 avec SafeCast).

Usage : python evoland2_patch.py <hlboot.dat> <hlboot.dat patché>
        (build_all.py applique les patchs d'Evoland 1 et d'Evoland 2 ensemble)
"""
import sys

from crashlink import Bytecode

from hlpatch import FnBuilder, Patcher

AP_DIR = "archipelago2/"
POLL_FRAMES = 30
SESSION_DIGITS = 8
FLAG_SESSION = "ap2.session"
FLAG_APPLIED = "ap2.applied"
FLAG_COUNTER = "ap2.n."
SENT_MESSAGE = "Objet envoyé dans le multiworld Archipelago !"
SPECIAL_MODES = ("inTactics", "inLaboMode", "inOldGame", "inDDR")
FINAL_LEVEL = "ZFinalBoss"
PORTAL_LEVEL = "Glitch"  # le portail du boss final est dans l'Anomalie
STARS_TAG = ",stars="
TRAP_LEVEL = "MagiIsland"  # Magilith passé -> présent de l'Île Maudite (voir build_trap_gate)
TRAP_MESSAGE = ("Le Magilith reste silencieux... Il faut Velvet dans l'équipe ou le Terminal de contrôle "
                "pour revenir de l'autre côté.")

ALL_PARTS = ("base", "session", "getitem", "chest", "poll", "credits", "final", "trap")


class Evoland2Patch:
    def __init__(self, bc: Bytecode) -> None:
        self.bc = bc
        self.p = p = Patcher(bc)
        self.get_item = p.fn("logic.Logic.getItem")
        self.on_end_type = p.fn_type(self.get_item).args[2].value
        self.null_int = p.null_of("i32")
        self.g_timer = p.add_global("i32")
        self.g_granting = p.add_global("i32")  # 0/1 : le JIT refuse les globales bool
        self.g_chest = p.add_global("String")

    # --- petits outils de génération ----------------------------------------------------
    def concat(self, b: FnBuilder, *pieces: int) -> int:
        acc = pieces[0]
        for piece in pieces[1:]:
            acc = b.call("$String.__add__", acc, piece)
        return acc

    def to_string(self, b: FnBuilder, reg: int) -> int:
        """Entier (i32 ou null<i32>) -> String, via Std.string(dynamic)."""
        if b.regs[reg] == self.null_int:
            plain = b.reg("i32")
            b.op("SafeCast", dst=plain, src=reg)
            reg = plain
        return b.call("$Std.string", self.boxed(b, reg))

    @staticmethod
    def boxed(b: FnBuilder, reg: int) -> int:
        dyn = b.reg("dynamic")
        b.op("ToDyn", dst=dyn, src=reg)
        return dyn

    @staticmethod
    def set_global(b: FnBuilder, gindex: int, src: int) -> None:
        b.op("SetGlobal", src=src, **{"global": gindex})

    def location_prefix(self, b: FnBuilder, letter: str, state: int) -> int:
        """« <lettre><époque>_<niveau>_ » à partir de l'état du jeu."""
        return self.concat(b, b.string(letter), self.to_string(b, b.field(state, "currentTime")),
                           b.string("_"), b.field(state, "currentLevel"), b.string("_"))

    # --- fonctions ajoutées ---------------------------------------------------------------
    def build_base(self) -> None:
        p = self.p
        # ap2_noop() : fonction vide, passée comme onEnd à getItem
        b = FnBuilder(p, "ap2.noop", [], "void")
        b.ret_void()
        self.noop = p.add_function(b)

        # ap2_read(path) -> String ou null (fonctions natives : aucune exception)
        b = FnBuilder(p, "ap2.read", ["String"], "String")
        raw = b.call("std.file_contents", b.call("$Sys.getPath", 0), b.null(p.ref_of("i32")))
        b.op("JNull", reg=raw, offset="absent")
        b.ret(b.call("$String.fromUTF8", raw))
        b.label("absent")
        b.ret(b.null("String"))
        self.read = p.add_function(b)

        # ap2_send(key) : crée archipelago2/checks/<key>.txt (fichier vide)
        b = FnBuilder(p, "ap2.send", ["String"], "void")
        path = self.concat(b, b.string(AP_DIR + "checks/"), 0, b.string(".txt"))
        fd = b.call("std.file_open", b.call("$Sys.getPath", path), b.int(1), b.bool(True))
        b.op("JNull", reg=fd, offset="fin")
        b.call("std.file_close", fd)
        b.label("fin")
        b.ret_void()
        self.send = p.add_function(b)

    def build_session(self) -> None:
        p = self.p
        # ap2_session_ok(game, config) -> bool : la sauvegarde retient l'identifiant de partie
        b = FnBuilder(p, "ap2.sessionOk", ["Game", "String"], "bool")
        b.op("JSLt", a=b.field(1, "length"), b=b.int(SESSION_DIGITS), offset="ok")
        digits = b.reg(self.null_int)
        b.op("ToDyn", dst=digits, src=b.int(SESSION_DIGITS))
        parsed = b.call("$Std.parseInt", b.call("String.substr", 1, b.int(0), digits))
        b.op("JNull", reg=parsed, offset="ok")
        session = b.reg("i32")
        b.op("SafeCast", dst=session, src=parsed)
        flags = b.field(b.field(0, "state"), "globalFlags")
        key = b.string(FLAG_SESSION)
        stored = b.call("haxe.ds.StringMap.get", flags, key)
        b.op("JNotNull", reg=stored, offset="comparer")
        b.call("haxe.ds.StringMap.set", flags, key, self.boxed(b, session))
        b.op("JAlways", offset="ok")
        b.label("comparer")
        known = b.reg("i32")
        b.op("SafeCast", dst=known, src=stored)
        b.op("JEq", a=known, b=session, offset="ok")
        b.call(self.send, b.string("mismatch"))
        b.ret(b.bool(False))
        b.label("ok")
        b.ret(b.bool(True))
        self.session_ok = p.add_function(b)

        # ap2_contains(config, key) -> bool : ",key," présent dans la config ?
        b = FnBuilder(p, "ap2.contains", ["String", "String"], "bool")
        needle = self.concat(b, b.string(","), 1, b.string(","))
        index = b.call("String.indexOf", 0, needle, b.null(self.null_int))
        b.op("JSLt", a=index, b=b.int(0), offset="non")
        b.ret(b.bool(True))
        b.label("non")
        b.ret(b.bool(False))
        self.contains = p.add_function(b)

    def build_on_get_item(self) -> None:
        """ap2_on_get_item(logic, item, onEnd, silent, card) -> bool
        true = l'objet d'origine est remplacé par un check Archipelago."""
        p = self.p
        b = FnBuilder(p, "ap2.onGetItem",
                      ["logic.Logic", "String", self.on_end_type, p.ref_of("bool"), "String"], "bool")
        logic, item, on_end, card = 0, 1, 2, 4
        b.op("JNotEq", a=b.get_global(self.g_granting), b=b.int(0), offset="vanilla")  # item reçu
        game = b.field(logic, "game")
        cfg = b.call(self.read, b.string(AP_DIR + "config.txt"))
        b.op("JNull", reg=cfg, offset="vanilla")
        b.op("JFalse", cond=b.call(self.session_ok, game, cfg), offset="vanilla")
        key = b.get_global(self.g_chest)
        self.set_global(b, self.g_chest, b.null("String"))
        b.op("JNotNull", reg=key, offset="envoyer")
        # source autre qu'un coffre : s<époque>_<niveau>_<quoi>_<n>
        state = b.field(game, "state")
        what = b.reg("String")
        b.op("JNull", reg=card, offset="objet")
        b.op("Mov", dst=what, src=self.concat(b, b.string("card:"), card))
        b.op("JAlways", offset="quoi_ok")
        b.label("objet")
        b.op("Mov", dst=what, src=item)
        b.label("quoi_ok")
        base = self.concat(b, self.location_prefix(b, "s", state), what)
        flags = b.field(state, "globalFlags")
        counter_key = self.concat(b, b.string(FLAG_COUNTER), base)
        count = b.int(0)
        stored = b.call("haxe.ds.StringMap.get", flags, counter_key)
        b.op("JNull", reg=stored, offset="compte_lu")
        b.op("SafeCast", dst=count, src=stored)
        b.label("compte_lu")
        b.op("Incr", dst=count)
        b.call("haxe.ds.StringMap.set", flags, counter_key, self.boxed(b, count))
        b.op("Mov", dst=key, src=self.concat(b, base, b.string("_"), self.to_string(b, count)))
        b.label("envoyer")
        b.call(self.send, key)
        b.op("JFalse", cond=b.call(self.contains, cfg, key), offset="vanilla")
        # contenu mélangé : pas d'objet, un message, puis la suite normale (onEnd)
        callback = b.reg(self.on_end_type)
        b.op("Mov", dst=callback, src=on_end)
        b.op("JNotNull", reg=callback, offset="annonce")
        b.op("StaticClosure", dst=callback, fun=self.noop)
        b.label("annonce")
        b.call("logic.Logic.announce", logic, b.string(SENT_MESSAGE), callback)
        b.ret(b.bool(True))
        b.label("vanilla")
        b.ret(b.bool(False))
        self.on_get_item = p.add_function(b)

    def build_poll(self) -> None:
        """ap2_poll(game) : appelé à chaque image par Game.update, applique les items reçus."""
        p = self.p
        b = FnBuilder(p, "ap2.poll", ["Game"], "void")
        game = 0
        timer = b.get_global(self.g_timer)
        b.op("Incr", dst=timer)
        self.set_global(b, self.g_timer, timer)
        b.op("JSLt", a=timer, b=b.int(POLL_FRAMES), offset="fin")
        self.set_global(b, self.g_timer, b.int(0))
        # uniquement quand le héros est libre, hors modes spéciaux
        logic = b.field(game, "logic")
        b.op("JNull", reg=logic, offset="fin")
        b.op("JNull", reg=b.field(game, "hero"), offset="fin")
        api = b.field(game, "heroApi")
        b.op("JNull", reg=api, offset="fin")
        locked = b.reg("bool")
        b.op("CallMethod", dst=locked, field=p.field(b.regs[api], "isLocked"), args=[api])
        b.op("JTrue", cond=locked, offset="fin")
        for mode in SPECIAL_MODES:
            b.op("JTrue", cond=b.field(game, mode), offset="fin")
        cfg = b.call(self.read, b.string(AP_DIR + "config.txt"))
        b.op("JNull", reg=cfg, offset="fin")
        b.op("JFalse", cond=b.call(self.session_ok, game, cfg), offset="fin")
        items = b.call(self.read, b.string(AP_DIR + "items.txt"))
        b.op("JNull", reg=items, offset="fin")
        b.op("JSLt", a=b.field(items, "length"), b=b.int(3), offset="fin")
        lines = b.call("String.split", items, b.string("\n"))
        flags = b.field(b.field(game, "state"), "globalFlags")
        applied_key = b.string(FLAG_APPLIED)
        applied = b.int(0)
        stored = b.call("haxe.ds.StringMap.get", flags, applied_key)
        b.op("JNull", reg=stored, offset="compte_lu")
        b.op("SafeCast", dst=applied, src=stored)
        b.label("compte_lu")
        b.op("JSGte", a=applied, b=b.field(lines, "length"), offset="fin")
        elem = b.reg("dynamic")
        b.op("GetArray", dst=elem, array=b.field(lines, "array"), index=applied)
        record = b.reg("String")
        b.op("UnsafeCast", dst=record, src=elem)
        b.call("haxe.ds.StringMap.set", flags, applied_key, self.boxed(b, b.binop("Add", applied, b.int(1))))
        b.op("JNull", reg=record, offset="fin")
        b.op("JSLt", a=b.field(record, "length"), b=b.int(3), offset="fin")
        kind = b.reg("i32")
        b.op("GetI16", dst=kind, bytes=b.field(record, "bytes"), index=b.int(0))
        value = b.call("String.substr", record, b.int(2), b.null(self.null_int))
        self.set_global(b, self.g_granting, b.int(1))
        end = b.reg(self.on_end_type)
        b.op("StaticClosure", dst=end, fun=self.noop)
        no_silent = b.null(p.ref_of("bool"))
        b.op("JNotEq", a=kind, b=b.int(ord("i")), offset="pas_objet")
        b.call(self.get_item, logic, value, end, no_silent, b.null("String"))
        b.op("JAlways", offset="donne")
        b.label("pas_objet")
        b.op("JNotEq", a=kind, b=b.int(ord("c")), offset="pas_carte")
        b.call(self.get_item, logic, b.null("String"), end, no_silent, value)
        b.op("JAlways", offset="donne")
        b.label("pas_carte")
        b.op("JNotEq", a=kind, b=b.int(ord("g")), offset="donne")
        amount = b.call("$Std.parseInt", value)
        b.op("JNull", reg=amount, offset="donne")
        gold = b.reg("i32")
        b.op("SafeCast", dst=gold, src=amount)
        b.call("Game.addGold", game, gold)
        b.label("donne")
        self.set_global(b, self.g_granting, b.int(0))
        b.label("fin")
        b.ret_void()
        self.poll = p.add_function(b)

    def build_final_gate(self) -> None:
        """ap2_final_gate(scriptGlobals, level) -> bool : true = bloquer le passage vers le boss final.

        Uniquement depuis l'Anomalie : les phases du combat final repassent aussi par ZFinalBoss."""
        p = self.p
        b = FnBuilder(p, "ap2.finalGate", ["logic.ScriptGlobals", "String"], "bool")
        level = 1
        b.op("JNull", reg=level, offset="ok")
        b.op("JSLt", a=b.call("String.indexOf", level, b.string(FINAL_LEVEL), b.null(self.null_int)),
             b=b.int(0), offset="ok")
        game = b.field(0, "game")
        current = b.field(b.field(game, "state"), "currentLevel")
        b.op("JNull", reg=current, offset="ok")
        b.op("JSLt", a=b.call("String.indexOf", current, b.string(PORTAL_LEVEL), b.null(self.null_int)),
             b=b.int(0), offset="ok")
        cfg = b.call(self.read, b.string(AP_DIR + "config.txt"))
        b.op("JNull", reg=cfg, offset="ok")
        pos = b.call("String.indexOf", cfg, b.string(STARS_TAG), b.null(self.null_int))
        b.op("JSLt", a=pos, b=b.int(0), offset="ok")
        start = b.binop("Add", pos, b.int(len(STARS_TAG)))
        parsed = b.call("$Std.parseInt", b.call("String.substr", cfg, start, b.null(self.null_int)))
        b.op("JNull", reg=parsed, offset="ok")
        need = b.reg("i32")
        b.op("SafeCast", dst=need, src=parsed)
        logic = b.field(game, "logic")
        have = b.call("logic.Logic.itemCount", logic, b.string("Star"))
        b.op("JSGte", a=have, b=need, offset="ok")
        message = self.concat(b, b.string("Il vous faut "), self.to_string(b, need),
                              b.string(" étoiles pour ouvrir ce portail (vous en avez "),
                              self.to_string(b, have), b.string(")."))
        callback = b.reg(self.on_end_type)
        b.op("StaticClosure", dst=callback, fun=self.noop)
        b.call("logic.Logic.announce", logic, message, callback)
        b.ret(b.bool(True))
        b.label("ok")
        b.ret(b.bool(False))
        self.final_gate = p.add_function(b)

    def build_trap_gate(self) -> None:
        """ap2_trap_gate(scriptGlobals, level, time) -> bool : true = bloquer un Magilith piège.

        Le Magilith de l'Île Maudite du passé (past/MagiIsland.js, act_mag, sans condition) mène au
        présent, derrière une porte que seule la glace de Velvet affaiblit ; le Magilith du présent
        exige le Terminal de contrôle. Normalement on n'y arrive qu'à l'acte 2, mais avec le Bateau
        reçu tôt on peut y aller avant que Velvet ait rejoint l'équipe : blocage définitif."""
        p = self.p
        b = FnBuilder(p, "ap2.trapGate", ["logic.ScriptGlobals", "String", "String"], "bool")
        level, time = 1, 2
        b.op("JNull", reg=level, offset="ok")
        b.op("JNull", reg=time, offset="ok")
        b.op("JSLt", a=b.call("String.indexOf", level, b.string(TRAP_LEVEL), b.null(self.null_int)),
             b=b.int(0), offset="ok")
        b.op("JSLt", a=b.call("String.indexOf", time, b.string("present"), b.null(self.null_int)),
             b=b.int(0), offset="ok")
        state = b.field(b.field(0, "game"), "state")
        current = b.field(state, "currentLevel")
        b.op("JNull", reg=current, offset="ok")
        b.op("JSLt", a=b.call("String.indexOf", current, b.string(TRAP_LEVEL), b.null(self.null_int)),
             b=b.int(0), offset="ok")
        era = b.field(state, "currentTime")
        b.op("JNull", reg=era, offset="ok")
        plain = b.reg("i32")
        b.op("SafeCast", dst=plain, src=era)
        b.op("JNotEq", a=plain, b=b.int(0), offset="ok")  # seulement depuis le passé
        b.op("JTrue", cond=b.call("logic.ScriptGlobals.hasTeam", 0, b.string("Velvet")), offset="ok")
        b.op("JTrue", cond=b.call("logic.ScriptGlobals.hasItem", 0, b.string("NESPad"), b.null(self.null_int)),
             offset="ok")
        callback = b.reg(self.on_end_type)
        b.op("StaticClosure", dst=callback, fun=self.noop)
        b.call("logic.Logic.announce", b.field(b.field(0, "game"), "logic"), b.string(TRAP_MESSAGE), callback)
        b.ret(b.bool(True))
        b.label("ok")
        b.ret(b.bool(False))
        self.trap_gate = p.add_function(b)

    # --- accroches dans le code du jeu ---------------------------------------------------
    def hook_final_gate(self) -> None:
        """ScriptGlobals.goto : refuse le portail du boss final s'il manque des étoiles."""
        goto = self.p.fn("logic.ScriptGlobals.goto")
        ins = FnBuilder.for_function(self.p, goto)
        blocked = ins.reg("bool")
        ins.op("Call2", dst=blocked, fun=self.final_gate, arg0=0, arg1=1)
        ins.op("JFalse", cond=blocked, offset="@0")
        ins.ret_void()
        self.p.insert_code(goto, 0, ins)

    def hook_trap_gate(self) -> None:
        """ScriptGlobals.goto(level, anchor, time) : refuse le Magilith piège de l'Île Maudite."""
        goto = self.p.fn("logic.ScriptGlobals.goto")
        ins = FnBuilder.for_function(self.p, goto)
        blocked = ins.reg("bool")
        ins.op("Call3", dst=blocked, fun=self.trap_gate, arg0=0, arg1=1, arg2=3)
        ins.op("JFalse", cond=blocked, offset="@0")
        ins.ret_void()
        self.p.insert_code(goto, 0, ins)

    def hook_get_item(self) -> None:
        """getItem : les objets mélangés deviennent des checks."""
        ins = FnBuilder.for_function(self.p, self.get_item)
        handled = ins.reg("bool")
        ins.op("CallN", dst=handled, fun=self.on_get_item, args=[0, 1, 2, 3, 4])
        ins.op("JFalse", cond=handled, offset="@0")
        ins.op("Ret", ret=handled)
        self.p.insert_code(self.get_item, 0, ins)

    def hook_chests(self) -> None:
        """Juste avant chaque appel à getItem dans la closure d'ouverture d'un coffre, on mémorise
        la clé du coffre (c<époque>_<niveau>_<uid>) pour ap2.onGetItem."""
        bc, p = self.bc, self.p
        chest_open = next(f.findex.value for f in bc.functions if self._is_chest_closure(f))
        func = bc.fn(chest_open)
        first = func.ops[0]  # EnumField regX = (reg0 as _).1  -> le coffre
        capture_construct = first.df["construct"].value
        chest_type = func.regs[first.df["dst"].value].value
        calls = [i for i, op in enumerate(func.ops) if op.op == "CallN" and op.df["fun"].value == self.get_item]
        for at in reversed(calls):
            ins = FnBuilder.for_function(p, chest_open)
            chest = ins.reg(chest_type)
            ins.op("EnumField", dst=chest, value=0, construct=capture_construct, field=1)
            state = ins.field(ins.field(chest, "game"), "state")
            key = self.concat(ins, self.location_prefix(ins, "c", state), self.to_string(ins, ins.field(chest, "uid")))
            self.set_global(ins, self.g_chest, key)
            p.insert_code(chest_open, at, ins)

    def hook_update(self) -> None:
        """Game.update : réception des items."""
        update = self.p.fn("Game.update")
        ins = FnBuilder.for_function(self.p, update)
        ins.op("Call1", dst=ins.reg("void"), fun=self.poll, arg0=0)
        self.p.insert_code(update, 0, ins)

    def hook_credits(self) -> None:
        """Générique de fin : objectif atteint."""
        credits = self.p.fn("logic.ScriptGlobals.setCredits")
        ins = FnBuilder.for_function(self.p, credits)
        ins.op("Call1", dst=ins.reg("void"), fun=self.send, arg0=ins.string("goal"))
        self.p.insert_code(credits, 0, ins)

    def _is_chest_closure(self, func) -> bool:
        """Closure anonyme de ent/active/Chest.hx qui appelle getItem (ouverture du coffre)."""
        bc = self.bc
        if bc.full_func_name(func) != "<none>" or not func.debuginfo or not func.debuginfo.value:
            return False
        try:
            if not func.debuginfo.value[0].resolve(bc).endswith("ent/active/Chest.hx"):
                return False
        except Exception:
            return False
        return any(op.op == "CallN" and op.df["fun"].value == self.get_item for op in func.ops)


def build(bc: Bytecode, parts: tuple = ALL_PARTS) -> None:
    """Applique le patch. `parts` permet de n'en appliquer qu'une partie (diagnostic du JIT)."""
    patch = Evoland2Patch(bc)
    patch.build_base()
    if "session" in parts:
        patch.build_session()
    if "getitem" in parts:
        patch.build_on_get_item()
        patch.hook_get_item()
        if "chest" in parts:
            patch.hook_chests()
    if "poll" in parts:
        patch.build_poll()
        patch.hook_update()
    if "credits" in parts:
        patch.hook_credits()
    if "final" in parts:
        patch.build_final_gate()
        patch.hook_final_gate()
    if "trap" in parts:
        patch.build_trap_gate()
        patch.hook_trap_gate()


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    bytecode = Bytecode.from_path(src)
    build(bytecode)
    with open(dst, "wb") as f:
        f.write(bytecode.serialise())
    print("Patch Evoland 2 écrit :", dst)
