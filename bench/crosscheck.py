"""抽出器を ifcopenshell で外から検算する。

    .venv/bin/python -m bench.crosscheck

較正（bench/selfcheck.py）は自分の手読みとの突き合わせなので、
こちらが同じ思い込みをしていれば一緒に間違える。
ifcopenshell は IFC の独立した実装なので、その思い込みごと検査できる。

**同じ経路を再実装しない。** ifcopenshell 自身の API を使って取り直す。

    空間の親    ifcopenshell.util.element.get_aggregate(e)
    要素の所属  ifcopenshell.util.element.get_container(e)
    数量        ifcopenshell.util.element.get_psets(e, qtos_only=True)
    性能仕様    get_psets(e, should_inherit=False) と get_psets(get_type(e))

こちらは IFCRELAGGREGATES / IFCRELCONTAINEDINSPATIALSTRUCTURE / IFCELEMENTQUANTITY を
生の実体からたどっている。到達経路が違うので、一致すれば意味がある。

**性能仕様だけは向こうの既定 API をそのまま使えない。**
get_psets(e) は既定で型の値を直接の値で上書きして1つの辞書に潰す。

    #52 IfcSlab   get_psets(e)                -> FireRating = 'REI30'
                  get_psets(e, 継承なし)       -> FireRating = 'REI30'
                  get_psets(型 #50)           -> FireRating = 'REI60'

つまり **既定のまま読むと REI60 は消え、耐火等級の矛盾は見えない。**
照査で拾いたいのは当のその矛盾なので、2経路を別々に取って比べる。

ifcopenshell は corpus に同梱していない（venv に入れる）。
検算の道具であって、参照解の一部ではない。
"""

from __future__ import annotations

import sys
from pathlib import Path

from .ifc import extract
from .step import load as load_step

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus" / "buildingsmart"


def _norm(v) -> str:
    """ifcopenshell 側の値をこちら側の書き方に寄せる。

    向こうは Python の型に直して返す（True / False / ['UNSET'] / 45.0）。
    こちらは Part21 の書式のまま持っている（.T. / .F. / UNSET / 45.）。
    **読み取れているかを見たいのであって、表記の差を咎めたいのではない。**
    """
    if isinstance(v, bool):
        return "T" if v else "F"
    if isinstance(v, (list, tuple)):
        return ",".join(_norm(x) for x in v)
    s = str(v).strip().strip(".") if not isinstance(v, float) else repr(v)
    # Part21 は 45. と書き、ifcopenshell は 45.0 と読む。同じ数である。
    try:
        return repr(float(s))
    except ValueError:
        return s


def _oshell_view(path: Path) -> dict:
    """ifcopenshell 側から見た姿を作る。"""
    import ifcopenshell
    import ifcopenshell.util.element as ue

    f = ifcopenshell.open(str(path))

    spatial_parent: dict[int, int | None] = {}
    for e in f.by_type("IfcObjectDefinition"):
        # IfcProject は IfcContext であって IfcSpatialElement ではない。
        # こちらは階層の根として空間に含めているので、向こう側でも拾って揃える。
        # 定義の差であって、どちらかが間違っているわけではない。
        if not (e.is_a("IfcSpatialElement") or e.is_a("IfcSpatialStructureElement")
                or e.is_a("IfcProject")):
            continue
        parent = ue.get_aggregate(e)
        spatial_parent[e.id()] = parent.id() if parent else None

    container: dict[int, int | None] = {}
    for e in f.by_type("IfcElement"):
        c = ue.get_container(e)
        if c is not None:
            container[e.id()] = c.id()

    quantities: dict[int, dict[str, float]] = {}  # element id -> {name: value}
    for e in f.by_type("IfcObject"):
        try:
            qs = ue.get_psets(e, qtos_only=True)
        except Exception:
            continue
        flat: dict[str, float] = {}
        for _, body in (qs or {}).items():
            for k, v in body.items():
                if k == "id":
                    continue
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    flat[k] = float(v)
        if flat:
            quantities[e.id()] = flat

    # 性能仕様。直接と型経由を**別々に**取る。既定の get_psets(e) は
    # 型の値を直接の値で上書きするので、そのまま使うと矛盾が消える。
    props: dict[tuple, str] = {}  # (要素, Pset名, 属性名, 付き方) -> 値
    for e in f.by_type("IfcObject"):
        pairs = [("direct", ue.get_psets(e, psets_only=True, should_inherit=False))]
        t = ue.get_type(e)
        if t is not None and t.id() != e.id():
            pairs.append(("type", ue.get_psets(t, psets_only=True)))
        for via, psets in pairs:
            for pname, body in (psets or {}).items():
                for k, v in (body or {}).items():
                    if k == "id" or v is None:
                        continue
                    props[(e.id(), pname, k, via)] = _norm(v)

    return {"schema": f.schema, "spatial_parent": spatial_parent,
            "container": container, "quantities": quantities, "properties": props}


def check_file(path: Path) -> list[str]:
    """1ファイル分。食い違いを文字列で返す。"""
    mine = extract(load_step(path))
    theirs = _oshell_view(path)
    bad: list[str] = []

    # ---- 空間の集合と親 ----
    my_sp = {s.id: s for s in mine.spatials}
    th_sp = theirs["spatial_parent"]
    only_mine = set(my_sp) - set(th_sp)
    only_theirs = set(th_sp) - set(my_sp)
    if only_mine:
        bad.append(f"空間: こちらだけにある {sorted(only_mine)[:6]}")
    if only_theirs:
        bad.append(f"空間: ifcopenshell だけにある {sorted(only_theirs)[:6]}")
    contained_placed = 0
    for i in set(my_sp) & set(th_sp):
        if my_sp[i].parent == th_sp[i]:
            continue
        # 集約の親を持たず包含関係で置かれている空間（IFCSPATIALZONE など）は、
        # ifcopenshell の get_aggregate() が None を返す。こちらは置かれ先を
        # 親にしている。**定義の差**なので比較から外す。腕2本が指摘した箇所。
        if my_sp[i].parent_via == "contained" and th_sp[i] is None:
            contained_placed += 1
            continue
        bad.append(f"空間 #{i} の親: こちら={my_sp[i].parent} ifcopenshell={th_sp[i]}")
    if contained_placed:
        bad.append(f"（参考）包含で置かれた空間 {contained_placed}件は比較対象外。"
                   "ifcopenshell の get_aggregate() は集約しか見ない")

    # ---- 要素の所属 ----
    # IFCRELADHERESTOELEMENT で母体に貼り付いている要素（路面標示など）は、
    # ifcopenshell の get_container() が None を返す。こちらは母体の所属を
    # 継承させている。**定義の差**なので比較から外す。
    # この関係の存在は腕(armC)が見つけた。独立実装との一致だけでは届かなかった。
    my_el = {e.id: e.container for e in mine.elements if e.container_via != "adheres"}
    adheres = sum(1 for e in mine.elements if e.container_via == "adheres")
    th_el = theirs["container"]
    only_mine = set(my_el) - set(th_el)
    only_theirs = set(th_el) - set(my_el)
    if only_mine:
        bad.append(f"要素: こちらだけにある {sorted(only_mine)[:6]}")
    if only_theirs:
        bad.append(f"要素: ifcopenshell だけにある {sorted(only_theirs)[:6]}")
    for i in set(my_el) & set(th_el):
        if my_el[i] != th_el[i]:
            bad.append(f"要素 #{i} の所属: こちら={my_el[i]} ifcopenshell={th_el[i]}")

    # ---- 数量 ----
    my_q: dict[int, dict[str, float]] = {}
    for q in mine.quantities:
        if q.element is None or q.value is None:
            continue
        my_q.setdefault(q.element, {})[q.name] = q.value
    th_q = theirs["quantities"]
    for i in set(my_q) | set(th_q):
        a, b = my_q.get(i, {}), th_q.get(i, {})
        for name in set(a) | set(b):
            va, vb = a.get(name), b.get(name)
            if va is None or vb is None:
                bad.append(f"数量 #{i}/{name}: こちら={va} ifcopenshell={vb}")
            elif abs(va - vb) > max(abs(vb) * 1e-9, 1e-12):
                bad.append(f"数量 #{i}/{name}: こちら={va} ifcopenshell={vb}")
    # ---- 性能仕様 ----
    my_p = {(p.element, p.pset_name, p.name, p.via): p.value
            for p in mine.properties if p.element is not None}
    th_p = theirs["properties"]
    only_mine = set(my_p) - set(th_p)
    only_theirs = set(th_p) - set(my_p)
    for k in sorted(only_mine)[:6]:
        bad.append(f"性能仕様 こちらだけにある {k}")
    for k in sorted(only_theirs)[:6]:
        bad.append(f"性能仕様 ifcopenshell だけにある {k}")
    for k in sorted(set(my_p) & set(th_p)):
        a, b = _norm(my_p[k]), th_p[k]
        if a != b:
            bad.append(f"性能仕様 {k}: こちら={my_p[k]!r} ifcopenshell={b!r}")

    if adheres:
        bad.append(f"（参考）付着による所属 {adheres}件は比較対象外。ifcopenshell は解決しない")
    return bad


def check_injected() -> list[str]:
    """仕込んだ欠陥を ifcopenshell から独立に確認する。

    仕込みの正しさは注入前後の差分で保証されるが、**それはこちらの道具だけで
    閉じた証明**である。外の実装が同じものを見ているかを別に確かめる。

    ifcopenshell の API で直に取れるのは次の2種類だけ。残りは構成による保証と、
    原本（buildingSMART 側）に元からある2件が支える。

        duplicate_global_id  by_type("IfcRoot") の GlobalId を数える
        orphan_element       get_container() も get_aggregate() も None
    """
    import json

    import ifcopenshell
    import ifcopenshell.util.element as ue

    inj = ROOT / "corpus" / "injected"
    man = json.loads((inj / "MANIFEST.json").read_text(encoding="utf-8"))
    bad: list[str] = []
    for name, d in sorted(man.items()):
        planted = {(a["kind"], tuple(sorted(a["entities"]))) for a in d["planted"]}
        f = ifcopenshell.open(str(inj / name))

        seen: dict[str, list[int]] = {}
        for e in f.by_type("IfcRoot"):
            if e.GlobalId:
                seen.setdefault(e.GlobalId, []).append(e.id())
        dup = {("duplicate_global_id", tuple(sorted(v))) for v in seen.values() if len(v) > 1}

        # 付着関係(IFCRELADHERESTOELEMENT)で母体に貼り付いている要素は、
        # ifcopenshell から見ると容器が無い。**欠陥ではない**ので除く。
        mine = extract(load_step(inj / name))
        adheres = {e.id for e in mine.elements if e.container_via == "adheres"}
        orph = {("orphan_element", (e.id(),)) for e in f.by_type("IfcElement")
                if ue.get_container(e) is None and ue.get_aggregate(e) is None
                and e.id() not in adheres}

        for kind, found in (("duplicate_global_id", dup), ("orphan_element", orph)):
            want = {k for k in planted if k[0] == kind}
            if found != want:
                for k in sorted(want - found):
                    bad.append(f"{name}: 仕込んだ {k} を ifcopenshell が見ていない")
                for k in sorted(found - want):
                    bad.append(f"{name}: 仕込んでいない {k} を ifcopenshell が見ている")
        n = len({k for k in planted if k[0] in ("duplicate_global_id", "orphan_element")})
        print(f"  {name:<38} 外から確認できた仕込み {n}件")
    return bad


def main() -> int:
    try:
        import ifcopenshell  # noqa: F401
    except ImportError:
        print("ifcopenshell が無い。.venv/bin/python -m bench.crosscheck で走らせること。")
        return 2

    print("=== ifcopenshell との突き合わせ ===")
    print("こちらは生の実体から、向こうは util.element の API から取っている。")
    print()
    total = 0
    for f in sorted(CORPUS.rglob("*.ifc")):
        bad = check_file(f)
        notes = [b for b in bad if b.startswith("（参考）")]
        bad = [b for b in bad if not b.startswith("（参考）")]
        total += len(bad)
        for n in notes:
            print(f"  {str(f.relative_to(CORPUS)):<38} {n}")
        mark = "OK" if not bad else f"不一致 {len(bad)}件"
        print(f"  {str(f.relative_to(CORPUS)):<38} {mark}")
        for b in bad[:8]:
            print(f"      {b}")
        if len(bad) > 8:
            print(f"      … 他 {len(bad) - 8}件")
    if (ROOT / "corpus" / "injected" / "MANIFEST.json").exists():
        print()
        print("=== 仕込んだ欠陥を外から確認 ===")
        bad = check_injected()
        total += len(bad)
        for b in bad:
            print(f"      {b}")

    print()
    print(f"突き合わせ: {'全ファイル一致' if total == 0 else f'計 {total}件の食い違い'}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
