"""IFC から空間構造・要素・数量を取り出して正規化する。

実物（buildingSMART の PCERT サンプル8ファイル）で確認した経路だけを実装している。
仕様書からの推測では書かない。

  空間構造  IFCRELAGGREGATES('id',$,$,$,#親,(#子,…))
            プロジェクト -> 敷地 -> 建物/橋/道路/鉄道 -> 階/部分
            IFC4.3 でインフラが入り、IFCBRIDGE / IFCROAD / IFCRAILWAY と
            IFCBRIDGEPART / IFCFACILITYPART が加わった

  要素の所属 IFCRELCONTAINEDINSPATIALSTRUCTURE('id',$,$,$,(#要素,…),#空間)
            「どの要素がどの空間に載っているか」。国交省の BIM/CIM 照査で
            人がチェックシートを見ながら確認しているのがここ。

            **直載せだけでは足りない。** 集合体（IFCRELAGGREGATES）の中に
            入れ子になった要素は、親をたどって初めて所属が決まる。
            例: IfcRoof の中の IfcSlab は、屋根が建物に載っているので建物に属する。
            ifcopenshell との突き合わせで、これを落としていたことが分かった。

  付着物    IFCRELADHERESTOELEMENT('id',$,$,$,#母体,(#表面形状,…))
            路面標示のように「母体に貼り付いている」要素。母体が空間に載って
            いるので、そこにあることになる。ただし IFC の厳密な包含関係
            （IFCRELCONTAINEDINSPATIALSTRUCTURE）ではないので、
            **ifcopenshell の get_container() も None を返す。**
            腕（armC）がこれを見つけた。独立実装との一致だけでは届かなかった。
            本ベンチは母体の所属を継承させ、container_via に経路を残す。

  性能仕様  IFCPROPERTYSET('id',$,'Pset_SlabCommon',$,(#属性,…))
            IFCPROPERTYSINGLEVALUE('FireRating',$,IFCLABEL('REI60'),$)  第3引数が値
            要素への付き方が2通りある:
              直接  IFCRELDEFINESBYPROPERTIES('id',$,$,$,(#要素…),#Pset)
              型経由 IFCRELDEFINESBYTYPE('id',$,$,$,(#要素…),#型)
                     -> 型の第6引数 HasPropertySets が Pset のリスト
            **同じ要素に、同じ名前の Pset が両経路から付き、値が食い違うことがある。**
            実物では床スラブ #49 に Pset_SlabCommon が2つ付き、
            FireRating が型経由 REI60 / 直接 REI30 と矛盾していた。
            腕(armB)がこれを見つけた。耐火等級の食い違いは BIM 照査が
            捕まえるべきものの典型である。

  数量      IFCELEMENTQUANTITY('id',$,名前,$,単位,(#数量,…))
            IFCQUANTITYLENGTH / AREA / VOLUME('名前',説明,単位,値,式)
            **単位系が量ごとに違う。** 本 corpus は長さが MILLI.METRE、
            面積が SQUARE_METRE、体積が CUBIC_METRE で宣言されている。
            値だけ見ても意味が決まらないので、宣言された単位を併記する。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .step import Entity, Model, Ref

# 空間を表す型。IFC4.3 でインフラ系が加わっている。
SPATIAL_TYPES = {
    "IFCPROJECT", "IFCSITE", "IFCBUILDING", "IFCBUILDINGSTOREY", "IFCSPACE",
    "IFCSPATIALZONE", "IFCFACILITY", "IFCFACILITYPART", "IFCBRIDGE",
    "IFCBRIDGEPART", "IFCROAD", "IFCROADPART", "IFCRAILWAY", "IFCRAILWAYPART",
    "IFCMARINEFACILITY", "IFCMARINEPART",
}

QUANTITY_TYPES = {
    "IFCQUANTITYLENGTH": "長さ",
    "IFCQUANTITYAREA": "面積",
    "IFCQUANTITYVOLUME": "体積",
    "IFCQUANTITYCOUNT": "個数",
    "IFCQUANTITYWEIGHT": "質量",
    "IFCQUANTITYTIME": "時間",
}


def _s(v) -> str:
    return "" if v is None else str(v)


@dataclass
class Spatial:
    """空間要素1件。"""

    id: int
    type: str  # IFCBUILDINGSTOREY など
    global_id: str
    name: str
    parent: int | None = None  # 親空間の実体ID
    parent_via: str = ""  # 'aggregate' / 'contained'。集約以外で置かれていれば経路を残す
    depth: int = 0  # プロジェクトからの深さ


@dataclass
class Element:
    """物理要素1件。どの空間に載っているかを持つ。"""

    id: int
    type: str  # IFCWALL など
    global_id: str
    name: str
    container: int | None = None  # 載っている空間の実体ID
    container_via: str = ""  # 'direct' / 'aggregate' / 'adheres'。間接なら経路を残す


@dataclass
class Quantity:
    """数量1件。"""

    id: int
    kind: str  # IFCQUANTITYVOLUME など
    label: str  # 体積 など
    name: str  # 'NetVolume' など
    value: float | None
    unit: str = ""  # ファイルが宣言している単位（MILLI.METRE / SQUARE_METRE など）
    owner: int | None = None  # 属する IFCELEMENTQUANTITY
    element: int | None = None  # 数量が付く要素


@dataclass
class Property:
    """性能仕様の属性1件。"""

    id: int
    pset_id: int
    pset_name: str
    name: str
    value: str
    element: int | None = None
    via: str = ""  # 'direct' / 'type'


@dataclass
class Extract:
    schema: str
    spatials: list[Spatial] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    quantities: list[Quantity] = field(default_factory=list)
    properties: list[Property] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.elements:
            out[e.type] = out.get(e.type, 0) + 1
        return dict(sorted(out.items()))

    def spatial_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for s in self.spatials:
            out[s.type] = out.get(s.type, 0) + 1
        return dict(sorted(out.items()))


_TYPED = None


def _unwrap(v) -> str:
    """IFCLABEL('REI60') のような型付き値から中身を取る。"""
    import re as _re
    if v is None:
        return ""
    t = str(v)
    m = _re.fullmatch(r"[A-Z_0-9]+\((.*)\)", t.strip(), _re.S)
    if m:
        inner = m.group(1).strip()
        if inner.startswith("'") and inner.endswith("'"):
            return inner[1:-1]
        return inner
    return t


def _rooted(entity: Entity) -> tuple[str, str]:
    """IfcRoot の共通引数 (GlobalId, OwnerHistory, Name, Description) から取る。"""
    gid = _s(entity.args[0]) if entity.args else ""
    name = _s(entity.args[2]) if len(entity.args) > 2 else ""
    return gid, name


def extract(model: Model) -> Extract:
    out = Extract(schema=model.schema)

    # ---- 空間要素 ----
    by_id: dict[int, Spatial] = {}
    for t in SPATIAL_TYPES:
        for e in model.of(t):
            gid, name = _rooted(e)
            by_id[e.id] = Spatial(id=e.id, type=e.type, global_id=gid, name=name)

    # ---- 親子関係。IFCRELAGGREGATES の第5引数が親、第6引数が子のリスト ----
    for r in model.of("IFCRELAGGREGATES"):
        if len(r.args) < 6:
            continue
        parent = model.get(r.args[4])
        kids = r.args[5]
        if parent is None or not isinstance(kids, list):
            continue
        for k in kids:
            child = model.get(k)
            if child is None or child.id not in by_id:
                continue
            if by_id[child.id].parent is not None:
                out.anomalies.append(
                    f"#{child.id} ({child.type}) が複数の親から集約されている"
                )
            by_id[child.id].parent = parent.id if parent.id in by_id else None
            by_id[child.id].parent_via = "aggregate"

    # 集約の親を持たない空間が、包含関係で空間の下に置かれていることがある。
    # IFCSPATIALZONE は IfcSpatialStructureElement ではないので、
    # IFCRELCONTAINEDINSPATIALSTRUCTURE の被参照側に出てよい（IFC4.3 で合法）。
    # 集約だけ見ていると根に取り残され、プロジェクトと同列になってしまう。
    # 腕2本がこれを指摘した。
    for r in model.of("IFCRELCONTAINEDINSPATIALSTRUCTURE"):
        if len(r.args) < 6:
            continue
        items = r.args[4]
        space = model.get(r.args[5])
        if space is None or space.id not in by_id or not isinstance(items, list):
            continue
        for i in items:
            c = model.get(i)
            if c is None or c.id not in by_id or by_id[c.id].parent is not None:
                continue
            by_id[c.id].parent = space.id
            by_id[c.id].parent_via = "contained"

    # 深さを付ける。親をたどるだけ。循環していたら報告する。
    for s in by_id.values():
        seen: set[int] = set()
        cur, d = s.parent, 0
        while cur is not None and cur in by_id:
            if cur in seen:
                out.anomalies.append(f"#{s.id} の空間階層が循環している")
                break
            seen.add(cur)
            d += 1
            cur = by_id[cur].parent
        s.depth = d
    out.spatials = sorted(by_id.values(), key=lambda x: (x.depth, x.type, x.global_id))

    # ---- 要素の所属 ----
    # 集合体の親子。空間の集約とは別に、要素が要素を束ねる形がある
    # （IfcRoof が IfcSlab を束ねるなど）。
    aggregate_parent: dict[int, int] = {}
    for r in model.of("IFCRELAGGREGATES"):
        if len(r.args) < 6:
            continue
        parent = model.get(r.args[4])
        kids = r.args[5]
        if parent is None or not isinstance(kids, list):
            continue
        for k in kids:
            child = model.get(k)
            if child is not None and child.id not in by_id:  # 空間でない子だけ
                aggregate_parent[child.id] = parent.id

    elements: dict[int, Element] = {}
    direct: dict[int, int | None] = {}
    for r in model.of("IFCRELCONTAINEDINSPATIALSTRUCTURE"):
        if len(r.args) < 6:
            continue
        items = r.args[4]
        space = model.get(r.args[5])
        if not isinstance(items, list):
            continue
        for i in items:
            e = model.get(i)
            if e is None:
                out.anomalies.append(f"空間への所属が存在しない実体 {i} を指している")
                continue
            if e.id in by_id:
                # 空間そのものが包含関係に出てくることがある（IfcSpatialZone など）。
                # 空間は空間として扱い、物理要素として二重に数えない。
                continue
            gid, name = _rooted(e)
            if e.id in elements:
                out.anomalies.append(f"#{e.id} ({e.type}) が複数の空間に載っている")
            direct[e.id] = space.id if space else None
            elements[e.id] = Element(id=e.id, type=e.type, global_id=gid, name=name,
                                     container=space.id if space else None,
                                     container_via="direct")

    # 集合体の中に入れ子になった要素。親をたどって所属を継承する。
    for child, parent in aggregate_parent.items():
        if child in elements:
            continue
        e = model.get(child)
        if e is None or e.id in by_id:
            continue
        cur, seen = parent, {child}
        while cur is not None and cur not in seen:
            seen.add(cur)
            if cur in direct:
                gid, name = _rooted(e)
                elements[child] = Element(id=child, type=e.type, global_id=gid,
                                          name=name, container=direct[cur],
                                          container_via="aggregate")
                break
            cur = aggregate_parent.get(cur)

    # 母体に貼り付いている要素（路面標示など）。母体の所属を継承する。
    for r in model.of("IFCRELADHERESTOELEMENT"):
        if len(r.args) < 6:
            continue
        host = model.get(r.args[4])
        feats = r.args[5]
        if host is None or not isinstance(feats, list):
            continue
        host_container = None
        if host.id in elements:
            host_container = elements[host.id].container
        elif host.id in direct:
            host_container = direct[host.id]
        for i in feats:
            e = model.get(i)
            if e is None or e.id in by_id or e.id in elements:
                continue
            gid, name = _rooted(e)
            elements[e.id] = Element(id=e.id, type=e.type, global_id=gid, name=name,
                                     container=host_container, container_via="adheres")

    out.elements = sorted(elements.values(), key=lambda x: (x.type, x.global_id))

    # ---- 数量 ----
    # IFCELEMENTQUANTITY -> (IFCQUANTITY*) 、それを IFCRELDEFINESBYPROPERTIES が要素に結ぶ
    owner_of: dict[int, int] = {}
    for q in model.of("IFCELEMENTQUANTITY"):
        lst = q.args[5] if len(q.args) > 5 else None
        for i in (lst if isinstance(lst, list) else []):
            e = model.get(i)
            if e is not None:
                owner_of[e.id] = q.id

    attached: dict[int, int] = {}  # IFCELEMENTQUANTITY -> 要素
    for r in model.of("IFCRELDEFINESBYPROPERTIES"):
        if len(r.args) < 6:
            continue
        objs = r.args[4]
        pdef = model.get(r.args[5])
        if pdef is None or pdef.type != "IFCELEMENTQUANTITY":
            continue
        for o in (objs if isinstance(objs, list) else []):
            e = model.get(o)
            if e is not None:
                attached[pdef.id] = e.id
                break

    # ファイルが宣言している単位。量の種類ごとに違う（長さmm・面積m2 など）。
    unit_of: dict[str, str] = {}
    for u in model.of("IFCSIUNIT"):
        args = u.args
        if len(args) < 4:
            continue
        utype = _s(args[1])
        prefix = _s(args[2])
        uname = _s(args[3])
        unit_of[utype] = f"{prefix + '.' if prefix else ''}{uname}"
    KIND_UNIT = {"IFCQUANTITYLENGTH": "LENGTHUNIT", "IFCQUANTITYAREA": "AREAUNIT",
                 "IFCQUANTITYVOLUME": "VOLUMEUNIT", "IFCQUANTITYWEIGHT": "MASSUNIT",
                 "IFCQUANTITYTIME": "TIMEUNIT"}

    for kind, label in QUANTITY_TYPES.items():
        for e in model.of(kind):
            name = _s(e.args[0]) if e.args else ""
            val = None
            if len(e.args) > 3:
                try:
                    val = float(e.args[3])
                except (TypeError, ValueError):
                    val = None
            owner = owner_of.get(e.id)
            out.quantities.append(
                Quantity(id=e.id, kind=kind, label=label, name=name, value=val,
                         unit=unit_of.get(KIND_UNIT.get(kind, ""), ""),
                         owner=owner, element=attached.get(owner) if owner else None)
            )
    out.quantities.sort(key=lambda q: (q.kind, q.name, q.id))

    # ---- 性能仕様 ----
    # Pset -> 属性
    pset_props: dict[int, list[Entity]] = {}
    pset_name: dict[int, str] = {}
    for ps in model.of("IFCPROPERTYSET"):
        pset_name[ps.id] = _s(ps.args[2]) if len(ps.args) > 2 else ""
        lst = ps.args[4] if len(ps.args) > 4 else None
        items = []
        for i in (lst if isinstance(lst, list) else []):
            e = model.get(i)
            if e is not None and e.type == "IFCPROPERTYSINGLEVALUE":
                items.append(e)
        pset_props[ps.id] = items

    # 要素 -> [(Pset, 経路)]
    attach: list[tuple[int, int, str]] = []  # (element, pset, via)
    for r in model.of("IFCRELDEFINESBYPROPERTIES"):
        if len(r.args) < 6:
            continue
        pdef = model.get(r.args[5])
        if pdef is None or pdef.type != "IFCPROPERTYSET":
            continue
        for o in (r.args[4] if isinstance(r.args[4], list) else []):
            e = model.get(o)
            if e is not None:
                attach.append((e.id, pdef.id, "direct"))
    for r in model.of("IFCRELDEFINESBYTYPE"):
        if len(r.args) < 6:
            continue
        ty = model.get(r.args[5])
        if ty is None:
            continue
        owned = ty.args[5] if len(ty.args) > 5 else None
        for i in (owned if isinstance(owned, list) else []):
            ps = model.get(i)
            if ps is None or ps.type != "IFCPROPERTYSET":
                continue
            for o in (r.args[4] if isinstance(r.args[4], list) else []):
                e = model.get(o)
                if e is not None:
                    attach.append((e.id, ps.id, "type"))

    for elem, ps, via in attach:
        for pr in pset_props.get(ps, []):
            name = _s(pr.args[0]) if pr.args else ""
            raw = pr.args[2] if len(pr.args) > 2 else None
            out.properties.append(Property(
                id=pr.id, pset_id=ps, pset_name=pset_name.get(ps, ""),
                name=name, value=_unwrap(raw), element=elem, via=via))
    out.properties.sort(key=lambda x: (x.element or 0, x.pset_name, x.name, x.id))

    # 同じ要素・同じPset名・同じ属性名で値が食い違うものを矛盾として挙げる
    seen: dict[tuple, list[Property]] = {}
    for pr in out.properties:
        seen.setdefault((pr.element, pr.pset_name, pr.name), []).append(pr)
    for (elem, psn, nm), group in sorted(seen.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1], kv[0][2])):
        vals = {p.value for p in group}
        if len(vals) > 1:
            detail = ", ".join(f"{p.value}({p.via})" for p in group)
            out.anomalies.append(
                f"#{elem} に同名の {psn} が複数付き、{nm} が食い違う: {detail}")

    return out
