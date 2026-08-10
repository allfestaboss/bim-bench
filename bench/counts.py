"""数え上げ課題（T005 / T006）の参照解を作る。

    python3 -m bench.counts          # 両方
    python3 -m bench.counts T006     # 片方だけ

**T004 が壊れた理由を、設計で消す。**

T004 は「規格が2通りに読める箇所を自分で挙げ、その影響を数えよ」という形だった。
自由記述なので、答案と参照解の対応を**実体番号の重なり**で取るしかなかった。
そこが致命傷になった。

  * `#13` は17ファイル全部の IfcProject なので、`#13` に触れる問いなら何でも
    「IfcProject を空間に数えるか」に吸着した。**別の問いの答えと突き合わせていた。**
  * 実体を広く並べるほど当たりやすいので、corpus の全実体を並べて差だけ合わせた
    **中身ゼロの答案が 100.0/100 を取った。**

T005 は同じ失敗をしない。**こちらが箇所を名指しし、数だけを訊く。**
対応づけが発生しないので吸着しない。実体番号を書かせないので水増しもできない。

**規格が2通りに読めるか、という論点も外した。** T004 はそこを
「2つの独立実装が食い違う」で担保しようとしたが、食い違いは
(a)規格が決めていない (b)片方が規格違反 (c)規格の管轄外 のどれでも起きるので、
非演繹だった。T005 の各設問は**規格の解釈ではなく、こちらが定めた数え方**である。
どちらが正しいかを問わない。**定められた規則どおりに17ファイルを数え切れるか**だけを問う。

答えは全て参照解から計算する。**主張しない。**

----

**T006 は T005 の課題文の欠陥を1件だけ直したものである。**

T005 の性能仕様2問（`property_all` / `property_merged`）は、性能仕様が付く先が
物理要素とは限らないのに、**どの所有者まで数えるかを課題文が決めていなかった。**
物理要素に限れば 308/306、所有者を問わなければ 324/322 で、どちらも規則から導ける。
T005 の6走中5走が独立にこれを申告している。

**T005 は直さない。**答案を見てから課題文を書き換えるのは、T004 を撤回に追い込んだ
失敗そのものだからである。欠陥は T005 に保存し、T006 で設問を割る。

T006 が測るのは腕の優劣ではなく、**この欠陥の診断が正しかったか**である。
欠陥が課題文だけの問題だったなら、両腕とも 13/13 に達するはずで、達しなければ
診断が間違っていたことになる。走らせる前に凍結してあるので、後から動かせない。

各設問には `pins` を持たせた。「この設問はどの解釈で固定されているか」の宣言で、
`bench/probe.py` が**答えが動く設問に宣言があるか**を機械照合する。T005 の欠陥は
この照合を通らない（実際に落ちることを probe 自身が確かめている）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = "T002"   # 同じ17ファイルの抽出結果を土台にする
CORPUS = ROOT / "corpus" / "buildingsmart"

# 物理要素ではない型。task.json の規則と同じ語彙。
NON_PHYSICAL = {
    "IFCZONE", "IFCGROUP", "IFCSYSTEM", "IFCDISTRIBUTIONSYSTEM",
    "IFCANNOTATION", "IFCGRID", "IFCDISTRIBUTIONPORT",
}


def _is_physical(t: str, spatial_types: frozenset[str]) -> bool:
    """規則の「物理要素」に当たるか。空間構造の実体と非物理型と ***TYPE を外す。"""
    return (t not in spatial_types and t not in NON_PHYSICAL
            and not t.endswith("TYPE"))


def owner_types(ref: dict) -> dict[tuple[str, int], str]:
    """性能仕様が付く先の型を (ファイル, 実体番号) -> 型名 で引けるようにする。

    T002 の抽出は所有者の**番号**しか持っていない。型は原本を読んで解決する。
    `reference/T002.json` は凍結済みなので触らない。
    """
    from .step import load

    out: dict[tuple[str, int], str] = {}
    for x in ref["results"]:
        want = {p["element"] for p in x["properties"] if p.get("element") is not None}
        if not want:
            continue
        model = load(CORPUS / x["file"])
        for eid in want:
            ent = model.get(eid)
            out[(x["file"], eid)] = ent.type if ent else "??"
    return out


def _property_rows(ref: dict) -> list[tuple[str, int, str, str, str]]:
    """性能仕様を (ファイル, 要素番号, 所有者の型, Pset名, 属性名) にならす。"""
    types = owner_types(ref)
    return [(x["file"], p["element"], types.get((x["file"], p["element"]), "??"),
             p["pset_name"], p["name"])
            for x in ref["results"] for p in x["properties"]]


def _split_merged(rows) -> tuple[int, int]:
    """(そのままの行数, 同じファイル・要素・Pset名・属性名をまとめた行数)。"""
    return len(rows), len({(f, e, ps, nm) for f, e, t, ps, nm in rows})


def _common(ref: dict) -> dict:
    """T005 / T006 が共有する、性能仕様以外の数え上げ。"""
    sp = [s for x in ref["results"] for s in x["spatials"]]
    el = [e for x in ref["results"] for e in x["elements"]]
    qt = [q for x in ref["results"] for q in x["quantities"]]

    via: dict = {}
    for e in el:
        via[e.get("container_via")] = via.get(e.get("container_via"), 0) + 1

    return {
        "n_sp": len(sp),
        "n_el": len(el),
        "n_qt": len(qt),
        "n_proj": sum(1 for s in sp if s["type"] == "IFCPROJECT"),
        "n_contained": sum(1 for s in sp if s.get("parent_via") == "contained"),
        "n_depth0": sum(1 for s in sp if s.get("depth") == 0),
        "n_feature": sum(1 for e in el if e["type"] == "IFCSURFACEFEATURE"),
        "via": via,
    }


def _shared_questions(c: dict) -> list[dict]:
    """性能仕様以外の9問。T005 と T006 で共通、文面も同一。"""
    return [
        {"id": "spatial_all", "answer": c["n_sp"],
         "ask": "IFCPROJECT を含め、空間構造の実体を全て数えたときの行数"},
        {"id": "spatial_no_project", "answer": c["n_sp"] - c["n_proj"],
         "ask": "同上から IFCPROJECT を除いた行数"},
        {"id": "spatial_depth0", "answer": c["n_depth0"],
         "ask": "親を持たない空間（深さ0）の行数。"
                "包含関係で他の空間の下に置かれている空間は、置かれ先を親として扱う"},
        {"id": "spatial_depth0_aggregate_only", "answer": c["n_depth0"] + c["n_contained"],
         "ask": "同上だが、親は集約関係（IFCRELAGGREGATES）でのみ決まるとしたときの行数"},
        {"id": "element_all", "answer": c["n_el"],
         "ask": "物理要素の行数。集約の親も部品も、付着している要素も、全て1行として数える"},
        {"id": "element_direct_only", "answer": c["via"].get("direct", 0),
         "ask": "同上のうち、IFCRELCONTAINEDINSPATIALSTRUCTURE で直接ある空間に"
                "載っているものだけを数えた行数"},
        {"id": "element_no_adheres", "answer": c["n_el"] - c["via"].get("adheres", 0),
         "ask": "物理要素の行数から、付着関係（IFCRELADHERESTOELEMENT）でしか"
                "空間に繋がっていないものを除いた行数"},
        {"id": "element_no_feature", "answer": c["n_el"] - c["n_feature"],
         "ask": "物理要素の行数から IFCSURFACEFEATURE を除いた行数"},
    ]


# --------------------------------------------------------------------------
# T005 — 凍結済み。**この関数の出力を変えてはいけない。**
# --------------------------------------------------------------------------

def questions_t005(ref: dict) -> list[dict]:
    """T005 の設問。走行後に凍結したので、文面も答えも変えない。

    性能仕様の2問には所有者の範囲が書かれていない。**それが欠陥である。**
    直さずに残す。T006 が直したものを持つ。
    """
    c = _common(ref)
    pr = [(x["file"], p) for x in ref["results"] for p in x["properties"]]
    n_pr = len(pr)
    dup: dict[tuple, int] = {}
    for f, p in pr:
        k = (f, p["element"], p["pset_name"], p["name"])
        dup[k] = dup.get(k, 0) + 1
    n_collapse = sum(v - 1 for v in dup.values() if v > 1)

    qs = _shared_questions(c)
    qs += [
        {"id": "property_all", "answer": n_pr,
         "ask": "性能仕様の行数。直接付いたものと型経由で付いたものを別の行として数える"},
        {"id": "property_merged", "answer": n_pr - n_collapse,
         "ask": "同上だが、同じファイル・同じ要素・同じ Pset 名・同じ属性名のものを"
                "1行にまとめたときの行数"},
        {"id": "quantity_all", "answer": c["n_qt"],
         "ask": "数量（IfcQuantity*）の行数"},
    ]
    return qs


# --------------------------------------------------------------------------
# T006 — 性能仕様の2問を、所有者の範囲ごとに4問へ割る
# --------------------------------------------------------------------------

def questions_t006(ref: dict) -> list[dict]:
    """T006 の設問。T005 との差は性能仕様の2問 -> 4問だけである。

    `pins` は「この設問がどの解釈で固定されているか」の宣言。
    `bench/probe.py` が、答えが動く設問にこの宣言があるかを機械照合する。
    """
    from .ifc import SPATIAL_TYPES

    c = _common(ref)
    st = frozenset(SPATIAL_TYPES)
    rows = _property_rows(ref)
    phys = [r for r in rows if _is_physical(r[2], st)]

    any_split, any_merged = _split_merged(rows)
    ph_split, ph_merged = _split_merged(phys)

    qs = _shared_questions(c)
    for q in qs:
        q.setdefault("pins", {})
    # 既に文面で解釈を名指ししている設問は、それを宣言として書き出す。
    by_id = {q["id"]: q for q in qs}
    by_id["spatial_all"]["pins"] = {"project_as_spatial": "include"}
    by_id["spatial_no_project"]["pins"] = {"project_as_spatial": "exclude"}
    by_id["spatial_depth0"]["pins"] = {"zone_parent": "containment"}
    by_id["spatial_depth0_aggregate_only"]["pins"] = {"zone_parent": "aggregate_only"}
    by_id["element_all"]["pins"] = {"adheres_container": "count"}
    by_id["element_no_adheres"]["pins"] = {"adheres_container": "drop"}

    qs += [
        {"id": "property_owner_physical_split", "answer": ph_split,
         "pins": {"property_owner": "physical"},
         "ask": "**物理要素に付いた**性能仕様の行数。"
                "直接付いたものと型経由で付いたものを別の行として数える"},
        {"id": "property_owner_physical_merged", "answer": ph_merged,
         "pins": {"property_owner": "physical"},
         "ask": "**物理要素に付いた**性能仕様のうち、同じファイル・同じ要素・"
                "同じ Pset 名・同じ属性名のものを1行にまとめたときの行数"},
        {"id": "property_owner_any_split", "answer": any_split,
         "pins": {"property_owner": "any"},
         "ask": "**所有者の種類を問わず**、全ての性能仕様の行数。"
                "直接付いたものと型経由で付いたものを別の行として数える"},
        {"id": "property_owner_any_merged", "answer": any_merged,
         "pins": {"property_owner": "any"},
         "ask": "**所有者の種類を問わず**、全ての性能仕様のうち、同じファイル・"
                "同じ要素・同じ Pset 名・同じ属性名のものを1行にまとめたときの行数"},
        {"id": "quantity_all", "answer": c["n_qt"], "pins": {},
         "ask": "数量（IfcQuantity*）の行数。"
                "**所有者の種類を問わず**、17ファイル全体で数える"},
    ]
    return qs


BUILDERS = {
    "T005": (questions_t005,
             "答えは全て参照解から計算した値。設問はこちらが定めた数え方であり、"
             "規格の解釈を問うものではない。"),
    "T006": (questions_t006,
             "答えは全て参照解から計算した値。設問はこちらが定めた数え方であり、"
             "規格の解釈を問うものではない。T005 との差は、性能仕様を"
             "「物理要素に付いたものだけ」と「所有者を問わず全て」に割った点のみ。"),
    # T007 は T006 の再出題。**設問は一字一句同じ。**違うのは課題文の説明文だけで、
    # T006 はそこに4問の答えを印字していた。腕の3走すべてが独立に申告した。
    "T007": (questions_t006,
             "答えは全て参照解から計算した値。設問は T006 と一字一句同一で、"
             "違いは課題文の説明文から数値を全て外した点のみ。"),
}


def build(task: str = "T005") -> dict:
    fn, note = BUILDERS[task]
    ref = json.loads((ROOT / "reference" / f"{SRC}.json").read_text(encoding="utf-8"))
    return {"task": task, "from": SRC, "note": note, "questions": fn(ref)}


def main() -> int:
    tasks = sys.argv[1:] or ["T005", "T006"]
    for task in tasks:
        doc = build(task)
        out = ROOT / "reference" / f"{task}.json"
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{out.relative_to(ROOT)}: 設問 {len(doc['questions'])}問")
        for q in doc["questions"]:
            print(f"  {q['id']:<32} {q['answer']:>5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
