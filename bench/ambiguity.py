"""規格が2通りに読める箇所を、実装同士の食い違いから構成する。

    python3 -m bench.ambiguity

T001/T002/T003 は3課題続けて両腕とも到達範囲で並んだ。**測る軸を変える。**
測るのは「正しく読めるか」ではなく、**正解が1つに決まらない箇所に気づき、
どちらを採るかを決め、その選択で何件動くかを言えるか**である。

**正解が無いものを、どうやって機械採点するか。**
参照解を「正しい読み方」にはできない。正しい読み方が無いのが前提だからだ。
代わりに **「決まらない箇所の集合」を参照解にする。** これは客観的に構成できる。

**その集合を、こちらの意見にしないための錨。**
このリポジトリの原則は「参照解は外部の権威に持たせる」。ここでの権威は
**2つの独立実装が実際に食い違っている、という事実**である。
こちらの生実体たどりと ifcopenshell の util.element API が違う答えを返し、
かつどちらも規格上あり得る——その4箇所だけを採る。好みで足さない。
4箇所はいずれも bench/crosscheck.py に「定義の差であって、どちらかが
間違っているわけではない」と、この課題を作る前から書いてあったものである。

影響件数は主張しない。**もう一方の読み方を実際に適用して数える。**
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sites(ref: dict) -> list[dict]:
    """参照解から、決まらない箇所とその影響を計算する。"""
    sp = [(x["file"], s) for x in ref["results"] for s in x["spatials"]]
    el = [(x["file"], e) for x in ref["results"] for e in x["elements"]]
    pr = [(x["file"], p) for x in ref["results"] for p in x["properties"]]

    out: list[dict] = []

    # 1. IfcProject を空間として数えるか
    #    こちら: 集約ツリーの根なので空間に含める / ifcopenshell: IfcContext であって
    #    IfcSpatialElement ではない。**腕2本が独立に「含めない」を選んだ箇所。**
    ids = [s["id"] for _, s in sp if s["type"] == "IFCPROJECT"]
    out.append({
        "id": "project_as_spatial",
        "entities": sorted(ids),
        "reading_a": "IfcProject を空間の一員として数える（深さ0の根）",
        "reading_b": "IfcProject は IfcContext であって空間ではないので数えない",
        "moves": "空間の行数",
        "affected": len(ids),
        "count_a": len(sp),
        "count_b": len(sp) - len(ids),
    })

    # 2. 集約の親を持たない空間を、包含関係で置かれた先の下に置くか
    #    こちら: 置かれ先を親にする / ifcopenshell: get_aggregate() は集約しか見ず None
    ids = [s["id"] for _, s in sp if s.get("parent_via") == "contained"]
    out.append({
        "id": "zone_parent_via_containment",
        "entities": sorted(ids),
        "reading_a": "包含関係で置かれた空間は、置かれ先を親とする",
        "reading_b": "集約以外で親は決まらない。親なし（根と同列）とする",
        "moves": "深さ0（親を持たない）空間の行数",
        "affected": len(ids),
        "count_a": sum(1 for _, s in sp if s.get("depth") == 0),
        "count_b": sum(1 for _, s in sp if s.get("depth") == 0) + len(ids),
    })

    # 3. 母体に貼り付いた要素が、母体の所属を継ぐか
    #    こちら: 継ぐ / ifcopenshell: get_container() は None を返す
    ids = [e["id"] for _, e in el if e.get("container_via") == "adheres"]
    out.append({
        "id": "adheres_container",
        "entities": sorted(ids),
        "reading_a": "付着関係の要素は母体の所属を継ぐ（物理的にそこにある）",
        "reading_b": "包含関係に無いのだから、どの空間にも載っていない",
        "moves": "所属を持つ要素の行数",
        "affected": len(ids),
        "count_a": sum(1 for _, e in el if e.get("container") is not None),
        "count_b": sum(1 for _, e in el if e.get("container") is not None) - len(ids),
    })

    # 4. 型経由の性能仕様を別行として持つか、直接の値で上書きするか
    #    こちら: 経路ごとに別行 / ifcopenshell: get_psets() の既定は直接が型を上書き
    #    **上書きすると耐火等級の食い違いが見えなくなる。**
    key: dict[tuple, list] = {}
    for f, p in pr:
        key.setdefault((f, p["element"], p["pset_name"], p["name"]), []).append(p)
    collided = sorted({k[1] for k, v in key.items() if len(v) > 1})
    merged = len(pr) - sum(len(v) - 1 for v in key.values() if len(v) > 1)
    out.append({
        "id": "type_property_precedence",
        "entities": collided,
        "reading_a": "直接と型経由を別の行として両方報告する",
        "reading_b": "同じ属性は1つ。直接の値が型の値を上書きする",
        "moves": "性能仕様の行数",
        "affected": len(collided),
        "count_a": len(pr),
        "count_b": merged,
    })

    return out


def build(task_id: str = "T002") -> dict:
    ref = json.loads((ROOT / "reference" / f"{task_id}.json").read_text(encoding="utf-8"))
    return {
        "from": task_id,
        "anchor": ("2つの独立実装（生実体たどり / ifcopenshell util.element）が"
                   "実際に食い違い、かつ規格上どちらもあり得る箇所だけを採る"),
        "sites": sites(ref),
    }


def main() -> int:
    doc = build(sys.argv[1] if len(sys.argv) > 1 else "T002")
    out = ROOT / "reference" / "T004.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out.relative_to(ROOT)}: 決まらない箇所 {len(doc['sites'])}件")
    for s in doc["sites"]:
        print(f"  {s['id']:<28} 実体{s['affected']:>3}件  "
              f"{s['moves']} {s['count_a']} -> {s['count_b']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
