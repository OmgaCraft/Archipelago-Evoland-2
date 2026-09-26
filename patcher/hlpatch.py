"""Petite boîte à outils pour modifier du bytecode HashLink avec crashlink.

- `Patcher` retrouve fonctions, types, globales et champs par leur nom.
- `FnBuilder` écrit du code HashLink lisible (étiquettes, registres nommés), puis
  l'ajoute comme nouvelle fonction ou l'insère dans une fonction existante.

Les sauts HashLink sont relatifs : offset = cible - (position du saut + 1).
Quand on insère des opcodes dans une fonction existante, tous les sauts qui
traversent le point d'insertion sont recalculés.
"""
from __future__ import annotations

from typing import Any, Optional, Union

from crashlink import (
    Bytecode, Enum, Fun, Function, InlineBool, Native, Obj, Opcode, Reg, Regs, Type,
    Virtual, VarInt, VarInts,
)
from crashlink.core import DebugInfo, fIndex, fieldRef, fileRef, gIndex, intRef, strRef, tIndex
from crashlink.opcodes import opcodes as OPCODE_SCHEMA

PRIMITIVES = {
    "void": 0, "u8": 1, "u16": 2, "i32": 3, "i64": 4, "f32": 5, "f64": 6, "bool": 7,
    "bytes": 8, "dynamic": 9, "array": 12, "type": 13, "dynobj": 16,
}

JUMP_OPS = {name for name, schema in OPCODE_SCHEMA.items() if "offset" in schema}

TypeRef = Union[int, str]


class Patcher:
    def __init__(self, bc: Bytecode) -> None:
        self.bc = bc
        self._fn_by_name: dict[str, int] = {}
        for func in list(bc.functions) + list(bc.natives):
            name = bc.full_func_name(func)
            self._fn_by_name.setdefault(name, func.findex.value)
        self._type_by_name: dict[str, int] = {}
        for i, t in enumerate(bc.types):
            d = t.definition
            if isinstance(d, (Obj, Enum)):
                self._type_by_name.setdefault(d.name.resolve(bc), i)
        self._file_ref = fileRef(bc.debugfiles.find_or_add("archipelago/Patch.hx"), 1) \
            if bc.debugfiles else None

    # --- recherche par nom -----------------------------------------------------------
    def fn(self, name: str) -> int:
        """Index d'une fonction, ex. 'sys.io.$File.saveContent' ou 'evo1.Game.unlock'."""
        try:
            return self._fn_by_name[name]
        except KeyError:
            raise KeyError(f"Fonction introuvable : {name}") from None

    def ty(self, ref: TypeRef) -> int:
        """Index d'un type : index direct, primitive ('i32', 'bool'…) ou nom de classe/enum."""
        if isinstance(ref, int):
            return ref
        if ref in PRIMITIVES:
            return self.bc.find_prim_type(Type.Kind(PRIMITIVES[ref])).value
        try:
            return self._type_by_name[ref]
        except KeyError:
            raise KeyError(f"Type introuvable : {ref}") from None

    def null_of(self, ref: TypeRef) -> int:
        """Type null<T> (ex. null<i32>)."""
        inner = self.ty(ref)
        for i, t in enumerate(self.bc.types):
            if t.kind.value == Type.Kind.NULL.value and t.definition.type.value == inner:
                return i
        raise KeyError(f"Type null<{ref}> introuvable")

    def fun_type(self, args: list[TypeRef], ret: TypeRef) -> int:
        """Type fonction (args) -> ret : réutilise un type existant ou en crée un."""
        arg_idx = [self.ty(a) for a in args]
        ret_idx = self.ty(ret)
        for i, t in enumerate(self.bc.types):
            d = t.definition
            if t.kind.value == Type.Kind.FUN.value and isinstance(d, Fun) \
                    and [a.value for a in d.args] == arg_idx and d.ret.value == ret_idx:
                return i
        fun = Fun()
        fun.args = [tIndex(a) for a in arg_idx]
        fun.nargs = VarInt(len(arg_idx))
        fun.ret = tIndex(ret_idx)
        typ = Type()
        typ.kind.value = Type.Kind.FUN.value
        typ.definition = fun
        return self.bc.add_type(typ).value

    def global_of(self, ref: TypeRef) -> int:
        """Globale qui contient l'objet statique d'une classe (ex. 'evo1.$State')."""
        return self._find_global(self.ty(ref))

    def _find_global(self, type_idx: int) -> int:
        for gi, gt in enumerate(self.bc.global_types):
            if gt.value == type_idx:
                return gi
        raise KeyError(f"Aucune globale de type {type_idx}")

    def field(self, ref: TypeRef, name: str) -> int:
        """Index d'un champ dans une classe (champs hérités compris) ou un type virtual."""
        d = self.bc.types[self.ty(ref)].definition
        assert isinstance(d, (Obj, Virtual)), ref
        for i, f in enumerate(d.resolve_fields(self.bc)):
            if f.name.resolve(self.bc) == name:
                return i
        raise KeyError(f"Champ {name} introuvable dans {ref}")

    def field_type(self, ref: TypeRef, name: str) -> int:
        d = self.bc.types[self.ty(ref)].definition
        return d.resolve_fields(self.bc)[self.field(ref, name)].type.value

    def ref_of(self, ref: TypeRef) -> int:
        """Type ref<T> (ex. ref<i32>)."""
        inner = self.ty(ref)
        for i, t in enumerate(self.bc.types):
            if t.kind.value == Type.Kind.REF.value and t.definition.type.value == inner:
                return i
        raise KeyError(f"Type ref<{ref}> introuvable")

    def fn_type(self, findex: int) -> Fun:
        func = self.bc.fn(findex)
        d = func.type.resolve(self.bc).definition
        assert isinstance(d, Fun)
        return d

    def add_global(self, ref: TypeRef) -> int:
        """Ajoute une variable globale (initialisée à 0/null par la VM)."""
        self.bc.global_types.append(tIndex(self.ty(ref)))
        return len(self.bc.global_types) - 1

    def global_type(self, gindex: int) -> int:
        return self.bc.global_types[gindex].value

    def string(self, s: str) -> int:
        return self.bc.add_string(s).value

    def int_const(self, value: int) -> int:
        for i, v in enumerate(self.bc.ints):
            if v.value == value & 0xFFFFFFFF:
                return i
        return self.bc.add_i32(value).value

    def enum_construct(self, enum: TypeRef, name: str) -> int:
        d = self.bc.types[self.ty(enum)].definition
        assert isinstance(d, Enum)
        for i, c in enumerate(d.constructs):
            if c.name.resolve(self.bc) == name:
                return i
        raise KeyError(f"{name} introuvable dans {enum}")

    # --- ajout / insertion de code ---------------------------------------------------
    def add_function(self, builder: "FnBuilder") -> int:
        func = Function()
        func.type = tIndex(self.fun_type(builder.args, builder.ret_type))
        func.findex = self.bc.next_free_findex()
        func.regs = [tIndex(r) for r in builder.regs]
        func.ops = builder.assemble()
        func.has_debug = self.bc.has_debug_info
        func.version = self.bc.version.value if hasattr(self.bc.version, "value") else self.bc.version
        if func.has_debug:
            func.debuginfo = DebugInfo()
            func.debuginfo.value = [self._file_ref] * len(func.ops)
            func.assigns = []
            func.nassigns = VarInt(0)
        func.calls = [op.df["fun"] for op in func.ops if "fun" in op.df and op.op != "CallClosure"]
        self.bc.functions.append(func)
        self.bc.invalidate_findex_cache()
        self._fn_by_name[builder.name] = func.findex.value
        return func.findex.value

    def insert_code(self, findex: int, at: int, builder: "FnBuilder") -> None:
        """Insère le code de `builder` avant l'opcode n°`at` d'une fonction existante.

        Le builder utilise les registres de la fonction (voir `FnBuilder.for_function`) ;
        les nouveaux registres éventuels sont ajoutés à la fin. Une étiquette spéciale
        `@N` saute vers l'opcode n°N de la fonction d'origine (numérotation d'avant l'insertion).
        """
        func = self.bc.fn(findex)
        assert isinstance(func, Function)
        new_ops = builder.assemble(base_index=at)
        n = len(new_ops)

        # 1) recalcul des sauts existants qui traversent le point d'insertion
        for i, op in enumerate(func.ops):
            for key, target in _jump_targets(op, i):
                new_i = i + n if i >= at else i
                new_target = target + n if target >= at else target
                _set_jump(op, key, new_target - (new_i + 1))
        # 2) insertion
        func.ops[at:at] = new_ops
        func.regs = [tIndex(r) for r in builder.regs]
        if func.debuginfo:
            ref = func.debuginfo.value[at] if at < len(func.debuginfo.value) else self._file_ref
            func.debuginfo.value[at:at] = [ref] * n
        if func.assigns:
            func.assigns = [(name, VarInt(pos.value + n if pos.value >= at else pos.value))
                            for name, pos in func.assigns]
        func.calls = [op.df["fun"] for op in func.ops if "fun" in op.df and op.op != "CallClosure"]


def _jump_targets(op: Opcode, index: int) -> list[tuple[Any, int]]:
    res = []
    if op.op in JUMP_OPS:
        res.append(("offset", index + 1 + op.df["offset"].value))
    elif op.op == "Switch":
        for k, off in enumerate(op.df["offsets"].value):
            res.append((("offsets", k), index + 1 + off.value))
        res.append(("end", index + 1 + op.df["end"].value))
    return res


def _set_jump(op: Opcode, key: Any, value: int) -> None:
    if isinstance(key, tuple):
        op.df["offsets"].value[key[1]] = VarInt(value)
    else:
        op.df[key] = VarInt(value)


class FnBuilder:
    """Écrit une fonction HashLink de façon lisible.

    Exemple :
        b = FnBuilder(p, "ap.hello", args=[], ret="void")
        s = b.reg("String")
        b.op("String", dst=s, ptr=p.string("hello"))
        b.label("fin")
        b.op("Ret", ret=b.reg("void"))
    Les opérandes de saut prennent un nom d'étiquette ; ceux de registre un index.
    """

    def __init__(self, patcher: Patcher, name: str, args: list[TypeRef], ret: TypeRef) -> None:
        self.p = patcher
        self.name = name
        self.args = [patcher.ty(a) for a in args]
        self.ret_type = patcher.ty(ret)
        self.regs: list[int] = list(self.args)
        self.ops: list[tuple[str, dict[str, Any]]] = []
        self.labels: dict[str, int] = {}

    @classmethod
    def for_function(cls, patcher: Patcher, findex: int) -> "FnBuilder":
        """Builder qui partage les registres d'une fonction existante (pour insert_code)."""
        func = patcher.bc.fn(findex)
        b = cls.__new__(cls)
        b.p = patcher
        b.name = f"insert@{findex}"
        b.args = []
        b.ret_type = 0
        b.regs = [r.value for r in func.regs]
        b.ops = []
        b.labels = {}
        return b

    def reg(self, ref: TypeRef) -> int:
        self.regs.append(self.p.ty(ref))
        return len(self.regs) - 1

    def string(self, text: str) -> int:
        """Crée un vrai objet String Haxe (l'opcode `String` seul ne donne que des octets UTF-16)."""
        raw, length, result = self.reg("bytes"), self.reg("i32"), self.reg("String")
        self.op("String", dst=raw, ptr=self.p.string(text))
        self.op("Int", dst=length, ptr=self.p.int_const(len(text.encode("utf-16-le")) // 2))
        self.op("Call2", dst=result, fun=self.p.fn("$String.__alloc__"), arg0=raw, arg1=length)
        return result

    # --- raccourcis ------------------------------------------------------------------
    def int(self, value: int) -> int:
        r = self.reg("i32")
        self.op("Int", dst=r, ptr=self.p.int_const(value))
        return r

    def bool(self, value: bool) -> int:
        r = self.reg("bool")
        self.op("Bool", dst=r, value=value)
        return r

    def null(self, ref: TypeRef) -> int:
        r = self.reg(ref)
        self.op("Null", dst=r)
        return r

    def call(self, fn: Union[str, int], *args: int) -> int:
        """Appelle une fonction statique ; renvoie le registre résultat."""
        fidx = self.p.fn(fn) if isinstance(fn, str) else fn
        dst = self.reg(self.p.fn_type(fidx).ret.value)
        if len(args) <= 4:
            operands = {f"arg{i}": a for i, a in enumerate(args)}
            self.op(f"Call{len(args)}", dst=dst, fun=fidx, **operands)
        else:
            self.op("CallN", dst=dst, fun=fidx, args=list(args))
        return dst

    def field(self, obj: int, name: str) -> int:
        t = self.regs[obj]
        dst = self.reg(self.p.field_type(t, name))
        self.op("Field", dst=dst, obj=obj, field=self.p.field(t, name))
        return dst

    def set_field(self, obj: int, name: str, src: int) -> None:
        self.op("SetField", obj=obj, field=self.p.field(self.regs[obj], name), src=src)

    def get_global(self, gindex: int) -> int:
        dst = self.reg(self.p.global_type(gindex))
        self.op("GetGlobal", dst=dst, **{"global": gindex})
        return dst

    def binop(self, name: str, a: int, b: int) -> int:
        dst = self.reg(self.regs[a])
        self.op(name, dst=dst, a=a, b=b)
        return dst

    def ret(self, r: int) -> None:
        self.op("Ret", ret=r)

    def ret_void(self) -> None:
        self.op("Ret", ret=self.reg("void"))

    def label(self, name: str) -> None:
        assert name not in self.labels, f"étiquette en double : {name}"
        self.labels[name] = len(self.ops)

    def op(self, name: str, **operands: Any) -> None:
        assert name in OPCODE_SCHEMA, f"opcode inconnu : {name}"
        expected = set(OPCODE_SCHEMA[name])
        assert set(operands) == expected, f"{name} attend {sorted(expected)}, reçu {sorted(operands)}"
        self.ops.append((name, operands))

    def assemble(self, base_index: int = 0) -> list[Opcode]:
        result = []
        n = len(self.ops)
        for i, (name, operands) in enumerate(self.ops):
            df: dict[str, Any] = {}
            for key, kind in OPCODE_SCHEMA[name].items():
                v = operands[key]
                if kind == "JumpOffset":
                    if isinstance(v, str) and v.startswith("@"):
                        # opcode d'origine n°N : décalé de n s'il est après le point d'insertion
                        orig = int(v[1:])
                        target = (orig + n if orig >= base_index else orig) - base_index
                    else:
                        target = self.labels[v]
                    df[key] = VarInt(target - (i + 1))
                elif kind == "JumpOffsets":
                    vi = VarInts()
                    vi.value = [VarInt(self.labels[x] - (i + 1)) for x in v]
                    df[key] = vi
                elif kind == "Reg":
                    df[key] = Reg(v)
                elif kind == "Regs":
                    r = Regs()
                    r.value = [Reg(x) for x in v]
                    df[key] = r
                elif kind == "RefInt":
                    df[key] = intRef(v)
                elif kind == "RefString":
                    df[key] = strRef(v)
                elif kind == "RefFun":
                    df[key] = fIndex(v)
                elif kind == "RefField":
                    df[key] = fieldRef(v)
                elif kind == "RefGlobal":
                    df[key] = gIndex(v)
                elif kind == "RefType":
                    df[key] = tIndex(v)
                elif kind == "InlineBool":
                    b = InlineBool()
                    b.value = bool(v)
                    df[key] = b
                else:  # InlineInt, RefEnumConstruct, RefFloat, RefBytes…
                    df[key] = VarInt(v)
            result.append(Opcode(name, df))
        return result
