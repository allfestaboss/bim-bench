"""欠陥を仕込んだ IFC を作る。

    python3 -m bench.inject

buildingSMART の原本（corpus/buildingsmart/）から派生ファイルを作り、
corpus/injected/ に書く。何をどこに仕込んだかは MANIFEST.json に残る。

**なぜ自作の欠陥なら参照解にしてよいか。**
このリポジトリの原則は「参照解は外部の権威に持たせる」である。自分で解いた答えは
自分では検査できないからだ。仕込んだ欠陥はその例外にあたる。**答えは解いて得たものでは
なく、こちらが構成した事実**であり、注入前後の差分がそのまま証拠になる。
加えて、注入後に検出器を回し「仕込んだもの＋原本に元からあるもの」と一致するかを
毎回確かめる（`verify()`）。一致しなければファイルを書かない。

**仕込むのは実在する照査項目だけにする。** ありえない壊し方をしても、
実務で起きない欠陥を見つける腕を測ることにしかならない。

    duplicate_global_id 別々の実体が同じ GlobalId を名乗る
                        書き出しツールの取り違えで実際に起きる。差分管理が壊れる
    orphan_element      要素がどの空間にも載っていない
                        数量拾いから静かに漏れる。積算が合わない典型
    double_containment  要素が複数の空間に載る
                        二重計上になる。逆向きの典型
    dangling_reference  存在しない実体を参照する
                        部分的な書き出しや手編集で起きる
    quantity_mismatch   体積 != 面積 x 厚さ
                        幾何を直して数量を更新し忘れた形
    property_conflict   同名 Pset の同じ属性が経路違いで食い違う
                        原本にも2件ある。型と個体のどちらを正とするかの問題
    multi_parent        空間が複数の親から集約される
                        階層が木でなくなる
    aggregation_cycle   集約が循環する
                        根にたどり着かない。無限ループを踏む

原本は CC BY 4.0。派生物の作成は許諾されており、変更した旨を示す義務がある。
corpus/injected/NOTICE.md に明記する。**ファイル本体には書かない**——
どこを変えたかが答えなので、ファイルを見れば分かる形にはしない。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .ifc import extract
from .step import load

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "corpus" / "buildingsmart"
DST = ROOT / "corpus" / "injected"


def _stmt(text: str, eid: int) -> tuple[int, int, str]:
    """実体 #eid の宣言全体（`#12=IFC…;`）の範囲と中身を返す。"""
    m = re.search(rf"#{eid}\s*=\s*.*?;", text, re.S)
    if not m:
        raise LookupError(f"#{eid} が見つからない")
    return m.start(), m.end(), m.group(0)


def _replace(text: str, eid: int, new: str) -> str:
    a, b, _ = _stmt(text, eid)
    return text[:a] + new + text[b:]


def _next_id(model) -> int:
    return max(model.entities) + 1


# ---- 仕込み方。どれも (text, model) を受け取り (text, Anomaly の鍵) を返す ----

def dup_global_id(text, model, kind_of: str):
    """同じ型の実体2つを選び、後ろの GlobalId を前のものに書き換える。"""
    xs = sorted((e for e in model.of(kind_of)), key=lambda e: e.id)
    if len(xs) < 2:
        raise LookupError(f"{kind_of} が2つ未満")
    keep, victim = xs[0], xs[1]
    gid = keep.args[0]
    _, _, s = _stmt(text, victim.id)
    new = re.sub(r"'[^']*'", f"'{gid}'", s, count=1)
    return _replace(text, victim.id, new), ("duplicate_global_id", (keep.id, victim.id))


def orphan(text, model):
    """包含関係の要素リストから1件だけ抜く。要素は残るが、どこにも載らなくなる。"""
    for r in sorted(model.of("IFCRELCONTAINEDINSPATIALSTRUCTURE"), key=lambda e: e.id):
        items = r.args[4] if len(r.args) > 4 else None
        if not isinstance(items, list) or len(items) < 2:
            continue
        target = sorted(int(i) for i in items)[-1]
        _, _, s = _stmt(text, r.id)
        new = re.sub(rf"(\(|,)#{target}(,|\))",
                     lambda m: m.group(1) if m.group(2) == "," else m.group(2), s, count=1)
        if new == s:
            continue
        return _replace(text, r.id, new), ("orphan_element", (target,))
    raise LookupError("抜ける要素が無い")


def double_contain(text, model):
    """既に載っている要素を、別の包含関係にも足す。"""
    rels = sorted(model.of("IFCRELCONTAINEDINSPATIALSTRUCTURE"), key=lambda e: e.id)
    if len(rels) < 2:
        raise LookupError("包含関係が2つ未満")
    src, dst = rels[0], rels[1]
    items = src.args[4]
    target = sorted(int(i) for i in items)[0]
    _, _, s = _stmt(text, dst.id)
    new = re.sub(r"\((#\d+(?:,#\d+)*)\)", rf"(\1,#{target})", s, count=1)
    if new == s:
        raise LookupError("足せなかった")
    return _replace(text, dst.id, new), ("double_containment", (target,))


def dangling(text, model):
    """包含関係の要素リストに、存在しない番号を1つ**足す**。

    既にある番号を差し替えると、その要素がどこにも載らなくなって
    orphan_element も同時に生える。**1回の編集で欠陥を1つだけ作る。**
    """
    ghost = _next_id(model) + 1000
    for r in sorted(model.of("IFCRELCONTAINEDINSPATIALSTRUCTURE"), key=lambda e: e.id):
        items = r.args[4] if len(r.args) > 4 else None
        if not isinstance(items, list) or len(items) < 1:
            continue
        _, _, s = _stmt(text, r.id)
        new = re.sub(r"\((#\d+(?:,#\d+)*)\)", rf"(\1,#{ghost})", s, count=1)
        if new == s:
            continue
        return _replace(text, r.id, new), ("dangling_reference", (ghost,))
    raise LookupError("足せる包含関係が無い")


def bad_quantity(text, model):
    """体積を書き換えて、面積 x 厚さ と合わなくする。"""
    x = extract(model)
    per: dict[int, dict[str, object]] = {}
    for q in x.quantities:
        if q.element is not None:
            per.setdefault(q.element, {})[q.name] = q
    for elem in sorted(per):
        qs = per[elem]
        if not {"NetArea", "Depth", "NetVolume"} <= set(qs):
            continue
        q = qs["NetVolume"]
        _, _, s = _stmt(text, q.id)
        v = q.value
        new = s.replace(repr(v), repr(round(v * 1.5, 9)), 1)
        if new == s:  # 12. のような書式で repr と一致しないとき
            new = re.sub(r",(-?\d+\.\d*(?:[eE][-+]?\d+)?),",
                         f",{round(v * 1.5, 9)},", s, count=1)
        if new == s:
            continue
        return _replace(text, q.id, new), ("quantity_mismatch", (elem,))
    raise LookupError("三つ組が無い")


def prop_conflict(text, model):
    """既にある属性と同名・別値の Pset をもう1つ付ける。

    型経由の Pset がある要素とは限らないので、**経路を問わず**既存の属性を選ぶ。
    同じ要素・同じ Pset 名・同じ属性名で値が割れれば矛盾になる。
    """
    x = extract(model)
    cand = [p for p in x.properties if p.element is not None and p.value]
    if not cand:
        raise LookupError("属性が無い")
    p = sorted(cand, key=lambda t: (t.element or 0, t.pset_name, t.name))[0]
    nid = _next_id(model)
    owner = model.of("IFCOWNERHISTORY")[0].id
    gid = "3zZ$Injected000000000A"
    add = (f"\n#{nid}=IFCPROPERTYSINGLEVALUE('{p.name}',$,IFCLABEL('INJECTED'),$);"
           f"\n#{nid+1}=IFCPROPERTYSET('{gid}',#{owner},'{p.pset_name}',$,(#{nid}));"
           f"\n#{nid+2}=IFCRELDEFINESBYPROPERTIES('{gid[:-1]}B',#{owner},$,$,(#{p.element}),#{nid+1});")
    text = text.replace("ENDSEC;\nEND-ISO-10303-21;", add + "\nENDSEC;\nEND-ISO-10303-21;", 1)
    return text, ("property_conflict", (p.element,))


def multi_parent(text, model):
    """既に親を持つ空間を、別の集約の子にも足す。"""
    x = extract(model)
    depth2 = sorted(s.id for s in x.spatials if s.depth and s.depth >= 2)
    rels = sorted(model.of("IFCRELAGGREGATES"), key=lambda e: e.id)
    for target in depth2:
        for r in rels:
            kids = r.args[5] if len(r.args) > 5 else None
            if not isinstance(kids, list) or target in [int(k) for k in kids]:
                continue
            if int(r.args[4]) == target:
                continue
            _, _, s = _stmt(text, r.id)
            new = re.sub(r"\((#\d+(?:,#\d+)*)\)", rf"(\1,#{target})", s, count=1)
            if new == s:
                continue
            return _replace(text, r.id, new), ("multi_parent", (target,))
    raise LookupError("足せる空間が無い")


def cycle(text, model):
    """集約を循環させる。**足すのではなく付け替える。**

    「子が親を集約する」関係を新たに足すだけだと、親が2つの親を持つことになり
    multi_parent が同時に生える。親を元の祖父から外し、子に付け替えることで
    親と子だけの輪にする。1回の編集で欠陥を1つだけ作る。
    """
    x = extract(model)
    by_id = {s.id: s for s in x.spatials}
    for s in sorted(x.spatials, key=lambda t: t.id):
        if s.parent_via != "aggregate" or not s.depth or s.depth < 2:
            continue
        kids = [t for t in x.spatials if t.parent == s.id and t.parent_via == "aggregate"]
        if not kids or s.parent not in by_id:
            continue
        parent, child = s.id, sorted(k.id for k in kids)[0]
        # 祖父の子リストから親を外す
        for r in sorted(model.of("IFCRELAGGREGATES"), key=lambda e: e.id):
            kk = r.args[5] if len(r.args) > 5 else None
            if not isinstance(kk, list) or parent not in [int(i) for i in kk]:
                continue
            _, _, st = _stmt(text, r.id)
            new = re.sub(rf"(\(|,)#{parent}(,|\))",
                         lambda m: m.group(1) if m.group(2) == "," else m.group(2),
                         st, count=1)
            if new == st:
                continue
            text = _replace(text, r.id, new)
            break
        else:
            continue
        nid = _next_id(model)
        owner = model.of("IFCOWNERHISTORY")[0].id
        add = (f"\n#{nid}=IFCRELAGGREGATES('3zZ$Injected000000000C',#{owner},$,$,"
               f"#{child},(#{parent}));")
        text = text.replace("ENDSEC;\nEND-ISO-10303-21;",
                            add + "\nENDSEC;\nEND-ISO-10303-21;", 1)
        return text, ("aggregation_cycle", (parent, child))
    raise LookupError("循環させられる対が無い")


# ---- 何をどのファイルに仕込むか ----
# **1ファイルに1種類だけ**とはしない。実物は複数の欠陥が同時に出る。
PLAN: list[tuple[str, str, list]] = [
    ("ifc4x3/Building-Architecture.ifc", "A", [orphan, bad_quantity]),
    ("ifc4x3/Infra-Bridge.ifc", "B", [multi_parent, (dup_global_id, "IFCBRIDGEPART")]),
    ("ifc4x3/Infra-Road.ifc", "C", [double_contain, dangling]),
    ("ifc4/Building-Structural.ifc", "D", [orphan, (dup_global_id, "IFCWALL")]),
    ("ifc4/Infra-Landscaping.ifc", "E", [orphan, prop_conflict]),
    ("ifc4/Building-Architecture.ifc", "F", [cycle, double_contain]),
]


def build() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, list] = {}
    bad = 0

    for rel, tag, steps in PLAN:
        src = SRC / rel
        text = src.read_text(encoding="utf-8", errors="replace")
        before = {a.key() for a in extract(load(src)).anomalies}
        planted: list[tuple] = []

        try:
            for step in steps:
                model = load_text(text)
                fn, args = (step, ()) if callable(step) else (step[0], tuple(step[1:]))
                text, key = fn(text, model, *args)
                planted.append(key)
        except LookupError as e:
            print(f"  [NG] {tag}-{Path(rel).name}: 仕込めなかった: {e}")
            bad += 1
            continue

        out = DST / f"{tag}-{Path(rel).name}"
        tmp = out.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        got = {a.key() for a in extract(load(tmp)).anomalies}
        want = before | {(k, tuple(sorted(e))) for k, e in planted}

        if got != want:
            print(f"  [NG] {out.name}")
            for k in sorted(want - got):
                print(f"        仕込んだのに出ない: {k}")
            for k in sorted(got - want):
                print(f"        仕込んでいないのに出る: {k}")
            tmp.unlink()
            bad += 1
            continue

        tmp.replace(out)
        manifest[out.name] = {
            "source": rel,
            "planted": [{"kind": k, "entities": sorted(e)} for k, e in planted],
            "pre_existing": [{"kind": k, "entities": list(e)} for k, e in sorted(before)],
        }
        print(f"  [OK] {out.name:<38} 仕込み{len(planted)}件 元から{len(before)}件")

    (DST / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    (DST / "NOTICE.md").write_text(NOTICE, encoding="utf-8")
    print()
    print(f"仕込み: {'全ファイル検証OK' if not bad else f'{bad}ファイルで不一致'}")
    return 1 if bad else 0


def load_text(text: str):
    """文字列から Model を作る（一時ファイル経由）。"""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".ifc", delete=False,
                                     encoding="utf-8") as f:
        f.write(text)
        p = Path(f.name)
    try:
        return load(p)
    finally:
        p.unlink()


NOTICE = """# 出どころと改変の明示

このディレクトリのファイルは buildingSMART International の
[Sample-Test-Files](https://github.com/buildingSMART/Sample-Test-Files) を
**改変した派生物**である。原本は CC BY 4.0。

改変内容: 照査で問題になる欠陥を意図的に仕込んである。
何をどこに仕込んだかは `MANIFEST.json` にある。

原本は `corpus/buildingsmart/` に無改変で置いてある。
"""


if __name__ == "__main__":
    sys.exit(build())
