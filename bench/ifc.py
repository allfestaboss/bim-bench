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

  数量      IFCELEMENTQUANTITY('id',$,名前,$,単位,(#数量,…))
            IFCQUANTITYLENGTH / AREA / VOLUME('名前',説明,単位,値,式)
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
    depth: int = 0  # プロジェクトからの深さ


@dataclass
class Element:
    """物理要素1件。どの空間に載っているかを持つ。"""

    id: int
    type: str  # IFCWALL など
    global_id: str
    name: str
    container: int | None = None  # 載っている空間の実体ID


@dataclass
class Quantity:
    """数量1件。"""

    id: int
    kind: str  # IFCQUANTITYVOLUME など
    label: str  # 体積 など
    name: str  # 'NetVolume' など
    value: float | None
    owner: int | None = None  # 属する IFCELEMENTQUANTITY
    element: int | None = None  # 数量が付く要素


@dataclass
class Extract:
    schema: str
    spatials: list[Spatial] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    quantities: list[Quantity] = field(default_factory=list)
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
                                     container=space.id if space else None)

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
                                          name=name, container=direct[cur])
                break
            cur = aggregate_parent.get(cur)

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
                         owner=owner, element=attached.get(owner) if owner else None)
            )
    out.quantities.sort(key=lambda q: (q.kind, q.name, q.id))
    return out
