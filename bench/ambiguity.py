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


def totals(ref: dict) -> list[int]:
    """コーパスから実際に数えられる集計値の集合。

    **どの読み方を採るかで「何の行を数えるか」自体が変わる。**
    こちらが「深さ0の空間の行数」を数えても、腕が「空間の行数」を数えるのは
    規則が許している（`moves` に何を数えたか書かせている）。
    どちらの土台で数えたかを咎めず、**その土台が実在するか**だけを見る。

    表ごとの総数と、分類ごとの内訳と、総数から内訳を引いた数を集める。
    228 や 629 や 324 は、17ファイルを最後まで数えないと出てこない。
    **当てずっぽうでは当たらない。** そこが測りたいところである。
    """
    got: set[int] = set()
    tables = {
        "spatials": ("type", "parent_via", "depth"),
        "elements": ("type", "container_via"),
        "quantities": ("kind", "unit"),
        "properties": ("via", "pset_name"),
    }
    for name, fields in tables.items():
        rows = [r for x in ref["results"] for r in x[name]]
        got.add(len(rows))
        for f in fields:
            groups: dict = {}
            for r in rows:
                groups[r.get(f)] = groups.get(r.get(f), 0) + 1
            for n in groups.values():
                got.add(n)
                got.add(len(rows) - n)
        # 値が埋まっている行の数（所属あり・親ありなど）も土台になりうる
        for f in ("container", "parent", "element"):
            if rows and f in rows[0]:
                n = sum(1 for r in rows if r.get(f) is not None)
                got.add(n)
                got.add(len(rows) - n)
    return sorted(x for x in got if x > 0)


def real_ids(task_id: str) -> list[int]:
    """課題の全ファイルに実在する実体番号の和集合。

    **参照解に無い箇所を挙げたこと自体は咎めない。** こちらの参照解は
    「2実装が実際に食い違う4箇所」に絞った**下限**であって、上限ではない。
    腕がそれ以外の本物の分かれ目を見つけたなら、それは減点する理由にならない。
    落とすのは**実在しない実体を並べた答案**だけにする。
    """
    from .step import load
    task = json.loads((ROOT / "tasks" / task_id / "task.json").read_text(encoding="utf-8"))
    out: set[int] = set()
    for f in task["files"]:
        out |= set(load(ROOT / f["path"]).entities)
    return sorted(out)


def build(task_id: str = "T002") -> dict:
    ref = json.loads((ROOT / "reference" / f"{task_id}.json").read_text(encoding="utf-8"))
    return {
        "from": task_id,
        "anchor": ("2つの独立実装（生実体たどり / ifcopenshell util.element）が"
                   "実際に食い違い、かつ規格上どちらもあり得る箇所だけを採る"),
        "sites": sites(ref),
        "totals": totals(ref),
        # 実在する実体番号。でっち上げの箇所を落とすためだけに使う。
        "real_ids": real_ids(task_id),
    }


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else "T002"
    doc = build(src)
    out = ROOT / "reference" / "T004.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out.relative_to(ROOT)}: 決まらない箇所 {len(doc['sites'])}件 / "
          f"実在する集計値 {len(doc['totals'])}種 / 実在する実体 {len(doc['real_ids'])}件")
    for s in doc["sites"]:
        print(f"  {s['id']:<28} 実体{s['affected']:>3}件  "
              f"{s['moves']} {s['count_a']} -> {s['count_b']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
