"""参照解の較正。

IFC 抽出器を、生の IFC テキストを手で追った結果と突き合わせる。
手側は step.py も ifc.py も呼ばない。同じコードを呼んで比べても検査にならない。

kikai-bench で「較正は1ファイルでは足りない」を踏んだので、
最初から建築系とインフラ系の両方で取る。IFC4.3 でインフラが入り、
IFCBRIDGE / IFCBRIDGEPART という別系統の空間型が加わっている。

    python -m bench.selfcheck
"""

from __future__ import annotations

import sys
from pathlib import Path

from .ifc import extract
from .step import load

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus" / "buildingsmart" / "ifc4x3"


def hand_slab_quantity() -> dict:
    """Building-Architecture の床スラブと、その面積。

    ファイルから直接読んだ行:

        #49=IFCSLAB('3zR0BOEcLADRKln4HYporH',#1,'floor','A solid, site-cast …',
                    'slab on grade',#60,#70,'4544…',$);
        #57=IFCELEMENTQUANTITY('2zWnAWnhD7EP2Z8GV8Oj9L',#1,'Qto_SlabBaseQuantities',
                               $,'BaseQuantities',(#54,#55,#56));
        #56=IFCQUANTITYAREA('NetArea',$,$,25.749999999991743,$);
        #59=IFCRELCONTAINEDINSPATIALSTRUCTURE('0QJ56olXz8X94dIhU_jyvm',#1,$,$,
                                              (#49,#234,#258,#277,#296,#302,#310),#40);

    IfcRoot の共通引数は (GlobalId, OwnerHistory, Name, Description) なので
    第1引数が GlobalId、第3引数が Name。
    IFCQUANTITYAREA は (Name, Description, Unit, AreaValue, Formula) で第4引数が値。
    所属は IFCRELCONTAINEDINSPATIALSTRUCTURE の第5引数が要素リスト、第6引数が空間。
    """
    return {
        "file": "Building-Architecture.ifc",
        "element_id": 49,
        "element_type": "IFCSLAB",
        "element_global_id": "3zR0BOEcLADRKln4HYporH",
        "element_name": "floor",
        "container_id": 40,
        "quantity_id": 56,
        "quantity_kind": "IFCQUANTITYAREA",
        "quantity_name": "NetArea",
        "quantity_value": 25.749999999991743,
    }


def hand_bridge_hierarchy() -> dict:
    """Infra-Bridge の空間階層。IFC4.3 のインフラ系。

    IFCRELAGGREGATES('id',$,$,$,#親,(#子,…)) で親子が付く。
    実際にたどった最深の連鎖:

        #13  IFCPROJECT     'ifc silly sample scene - project'      深さ0
        #20  IFCSITE        'environment - site'                    深さ1
        #679 IFCSITE        'road rail bridge - site'               深さ2
        #685 IFCBRIDGE      'rail bridge'                           深さ3
        #692 IFCBRIDGEPART  'rail bridge - substructure'            深さ4
        #726 IFCBRIDGEPART  'rail bridge - pier'                    深さ5

    **IFCBRIDGEPART は IFCBRIDGEPART の中に入れ子になる**（下部構造 -> 橋脚）。
    敷地も敷地の中に入る。建築の「建物 -> 階」という2段の型で考えると読み違える。
    最初この値を4と書いて較正が落ちた。抽出器が正しく、手読みが浅かった。
    """
    return {
        "file": "Infra-Bridge.ifc",
        "spatial_counts": {
            "IFCPROJECT": 1, "IFCSITE": 6, "IFCBRIDGE": 3, "IFCBRIDGEPART": 18,
        },
        "max_depth": 5,
    }


def _example_provenance() -> bool:
    """課題文の答案例が、名乗ったファイルに**実在する**行だけで出来ているか。

    ここを見ていなかったせいで同じ失敗を4回した。
    1回目 手で書いた GlobalId が実データと違う
    2回目 depth の例が規則と食い違う
    3回目 anomalies の例に答え（測りたい矛盾）そのものを書いていた
    4回目 3回目を直したとき、別ファイルの属性を元のファイル名の下に置いた

    機械生成にしただけでは足りない。**生成したものを参照解に照合し直す。**
    """
    import json as _json
    good = True
    print()
    print("=== 課題文の例の出どころ ===")
    for tdir in sorted((ROOT / "tasks").iterdir()):
        tf = tdir / "task.json"
        if not tf.exists():
            continue
        task = _json.loads(tf.read_text(encoding="utf-8"))
        rf = ROOT / "reference" / f"{tdir.name}.json"
        if not rf.exists():
            continue
        ref = _json.loads(rf.read_text(encoding="utf-8"))
        for ex in (task.get("answer_format", {}).get("results") or []):
            fname = ex.get("file")
            rec = next((x for x in ref["results"] if x["file"] == fname), None)
            if rec is None:
                print(f"  [{tdir.name}] {fname} は参照解に無い <-- NG")
                good = False
                continue
            bad = []
            for key, ident in (("spatials", lambda t: t.get("id")),
                               ("elements", lambda t: t.get("id")),
                               ("quantities", lambda t: t.get("id")),
                               ("properties", lambda t: (t.get("element"), t.get("pset_name"),
                                                         t.get("name"), t.get("via")))):
                have = {ident(t) for t in (rec.get(key) or [])}
                for t in (ex.get(key) or []):
                    if ident(t) not in have:
                        bad.append(f"{key}:{ident(t)}")
            # 答え（矛盾）を例に書いていないか
            leaked = [a for a in (ex.get("anomalies") or []) if a in (rec.get("anomalies") or [])]
            mark = "OK" if not bad and not leaked else "<-- NG"
            print(f"  [{tdir.name}] {fname:<38} {mark}")
            if bad:
                print(f"      そのファイルに無い行: {bad[:6]}")
                good = False
            if leaked:
                print(f"      答えを例に書いている: {leaked[:2]}")
                good = False
    return good


def main() -> int:
    ok = True
    print("=== 較正 ===")

    h = hand_slab_quantity()
    x = extract(load(CORPUS / h["file"]))
    print(f"\n[{h['file']}] 空間{len(x.spatials)} 要素{len(x.elements)} 数量{len(x.quantities)}")

    el = next((e for e in x.elements if e.id == h["element_id"]), None)
    q = next((a for a in x.quantities if a.id == h["quantity_id"]), None)
    rows = []
    if el is None:
        rows.append(("要素", "存在", "無し", False))
        ok = False
    else:
        for key, got in (("type", el.type), ("global_id", el.global_id),
                         ("name", el.name), ("container", el.container)):
            want = h[{"type": "element_type", "global_id": "element_global_id",
                      "name": "element_name", "container": "container_id"}[key]]
            rows.append((f"要素.{key}", want, got, want == got))
    if q is None:
        rows.append(("数量", "存在", "無し", False))
        ok = False
    else:
        rows.append(("数量.kind", h["quantity_kind"], q.kind, h["quantity_kind"] == q.kind))
        rows.append(("数量.name", h["quantity_name"], q.name, h["quantity_name"] == q.name))
        same = q.value is not None and abs(q.value - h["quantity_value"]) < 1e-12
        rows.append(("数量.value", h["quantity_value"], q.value, same))
        rows.append(("数量.element", h["element_id"], q.element, q.element == h["element_id"]))
    for label, want, got, good in rows:
        ok = ok and good
        print(f"  {label:<16} 手={want!s:<26} 抽出={got!s:<26} {'' if good else '<-- NG'}")

    b = hand_bridge_hierarchy()
    y = extract(load(CORPUS / b["file"]))
    print(f"\n[{b['file']}] 空間{len(y.spatials)} 要素{len(y.elements)} 数量{len(y.quantities)}")
    got_counts = {k: v for k, v in y.spatial_counts().items() if k in b["spatial_counts"]}
    good = got_counts == b["spatial_counts"]
    ok = ok and good
    print(f"  {'空間の内訳':<16} 手={b['spatial_counts']}")
    print(f"  {'':<16} 抽出={got_counts} {'' if good else '<-- NG'}")
    got_depth = max((s.depth for s in y.spatials), default=0)
    good = got_depth == b["max_depth"]
    ok = ok and good
    print(f"  {'最大の深さ':<16} 手={b['max_depth']:<26} 抽出={got_depth:<26} {'' if good else '<-- NG'}")

    ok = _example_provenance() and ok

    print()
    print("較正:", "OK（手読みと一致）" if ok else "NG（不一致あり）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
