"""STEP Part21 (ISO 10303-21) を読む。

**kikai-bench から持ってきたものをそのまま使っている。**

CAD横断シリーズを進めて分かったのは、「業界ごとに形式が違う」という
見立てが半分しか当たっていなかったことである。

    doboku-bench  SXF   -> ISO 10303-21 の器に SXF フィーチャ
    kikai-bench   AP242 -> ISO 10303-21
    bim-bench     IFC   -> ISO 10303-21

**3業界とも器は同じ ISO 10303-21 で、違うのはスキーマだった。**
だからパーサは共有できる。IFC ファイルの1行目は ISO-10303-21; である。

違うのは語彙のほう。AP242 は GEOMETRIC_TOLERANCE、IFC は IFCWALL。
測る対象は器ではなくスキーマの読解になる。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# 実体1件。 #107=PERPENDICULARITY_TOLERANCE('Perpendicularity.1','',#10003,#993,(#331));
#
# 先読みに \Z を入れてあるのは、DATA セクションの**最後の実体**を落とさないため。
# body は ENDSEC の手前で切っているので、末尾には次の #id= も ENDSEC も来ない。
# これを入れ忘れると全ファイルで最後の1実体が黙って消える（実際に踏んだ。
# nist_stc_07 の最後の実体が幾何公差で、宣言22件に対し21件しか取れていなかった）。
_ENTITY = re.compile(r"#(\d+)\s*=\s*(.*?);\s*(?=#\d+\s*=|ENDSEC|\Z)", re.S)
_SIMPLE = re.compile(r"^([A-Z_0-9]+)\s*\((.*)\)$", re.S)
_COMPLEX_PART = re.compile(r"([A-Z_0-9]+)\s*\(")


class Ref(int):
    """#123 への参照。int を継承しているので id としてそのまま使える。"""

    def __repr__(self) -> str:
        return f"#{int(self)}"


@dataclass
class Entity:
    id: int
    type: str  # 複合実体のときは最初の型
    types: tuple[str, ...]  # 複合実体の全ての型
    args: list  # 単純実体の引数。複合実体は parts を見る
    parts: dict[str, list] = field(default_factory=dict)

    def arg(self, i: int, of_type: str | None = None):
        """引数を取る。of_type を指定すると複合実体のその型から取る。"""
        src = self.parts[of_type] if of_type else self.args
        return src[i] if i < len(src) else None


def _split_args(s: str) -> list:
    """引数リストを分解する。文字列・入れ子リスト・参照・列挙・数値を扱う。"""
    out: list = []
    buf: list[str] = []
    depth = 0
    in_str = False
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if in_str:
            if c == "'":
                # '' は文字列中のシングルクォート
                if i + 1 < n and s[i + 1] == "'":
                    buf.append("'")
                    i += 2
                    continue
                in_str = False
            buf.append(c)
        elif c == "'":
            in_str = True
            buf.append(c)
        elif c == "(":
            depth += 1
            buf.append(c)
        elif c == ")":
            depth -= 1
            buf.append(c)
        elif c == "," and depth == 0:
            out.append(_value("".join(buf)))
            buf = []
        else:
            buf.append(c)
        i += 1
    tail = "".join(buf).strip()
    if tail or out:
        out.append(_value(tail))
    return out


def _value(raw: str):
    t = raw.strip()
    if not t:
        return None
    if t == "$":
        return None
    if t == "*":
        return "*"
    if t.startswith("#"):
        try:
            return Ref(int(t[1:]))
        except ValueError:
            return t
    if t.startswith("'") and t.endswith("'"):
        return t[1:-1]
    if t.startswith(".") and t.endswith("."):
        return t[1:-1]  # 列挙値 .T. -> 'T'
    if t.startswith("("):
        return _split_args(t[1:-1])
    try:
        return int(t) if re.fullmatch(r"[+-]?\d+", t) else float(t)
    except ValueError:
        return t


def _parse_complex(body: str) -> tuple[tuple[str, ...], dict[str, list]]:
    """(TYPE1(...)TYPE2(...)) 形式をほどく。"""
    inner = body.strip()[1:-1]
    parts: dict[str, list] = {}
    order: list[str] = []
    i = 0
    while i < len(inner):
        m = _COMPLEX_PART.match(inner, i)
        if not m:
            i += 1
            continue
        name = m.group(1)
        j = m.end()  # '(' の次
        depth = 1
        in_str = False
        while j < len(inner) and depth:
            c = inner[j]
            if in_str:
                if c == "'":
                    if j + 1 < len(inner) and inner[j + 1] == "'":
                        j += 2
                        continue
                    in_str = False
            elif c == "'":
                in_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            j += 1
        parts[name] = _split_args(inner[m.end() : j - 1])
        order.append(name)
        i = j
    return tuple(order), parts


@dataclass
class Model:
    header: dict[str, list]
    entities: dict[int, Entity]
    by_type: dict[str, list[Entity]]

    def get(self, ref) -> Entity | None:
        """参照から実体を引く。参照でないものが来たら None を返す。

        引数には COMMON_DATUM_LIST((#76,#77)) のような型付き値も混ざるので、
        呼び出し側でいちいち型を見なくて済むようにここで吸収する。
        """
        if ref is None or isinstance(ref, (list, str)):
            return None
        try:
            return self.entities.get(int(ref))
        except (TypeError, ValueError):
            return None

    def of(self, *types: str) -> list[Entity]:
        out: list[Entity] = []
        for t in types:
            out.extend(self.by_type.get(t, []))
        return out

    @property
    def schema(self) -> str:
        h = self.header.get("FILE_SCHEMA")
        if not h:
            return ""
        v = h[0]
        return (v[0] if isinstance(v, list) and v else v) or ""


def load(path: Path) -> Model:
    text = path.read_text(encoding="utf-8", errors="replace")

    header: dict[str, list] = {}
    hm = re.search(r"HEADER;(.*?)ENDSEC;", text, re.S)
    if hm:
        for m in re.finditer(r"([A-Z_]+)\s*\((.*?)\)\s*;", hm.group(1), re.S):
            header[m.group(1)] = _split_args(m.group(2))

    dm = re.search(r"\bDATA;(.*)ENDSEC;", text, re.S)
    body = dm.group(1) if dm else text

    entities: dict[int, Entity] = {}
    by_type: dict[str, list[Entity]] = {}
    for m in _ENTITY.finditer(body):
        eid = int(m.group(1))
        raw = m.group(2).strip()
        if raw.startswith("("):
            types, parts = _parse_complex(raw)
            e = Entity(id=eid, type=types[0] if types else "", types=types, args=[], parts=parts)
        else:
            sm = _SIMPLE.match(raw)
            if not sm:
                continue
            name = sm.group(1)
            e = Entity(id=eid, type=name, types=(name,), args=_split_args(sm.group(2)))
        entities[eid] = e
        for t in e.types:
            by_type.setdefault(t, []).append(e)

    return Model(header=header, entities=entities, by_type=by_type)
