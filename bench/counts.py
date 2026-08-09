"""数え上げ課題（T005）の参照解を作る。

    python3 -m bench.counts

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
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = "T002"   # 同じ17ファイルの抽出結果を土台にする


def questions(ref: dict) -> list[dict]:
    sp = [s for x in ref["results"] for s in x["spatials"]]
    el = [e for x in ref["results"] for e in x["elements"]]
    pr = [(x["file"], p) for x in ref["results"] for p in x["properties"]]
    qt = [q for x in ref["results"] for q in x["quantities"]]

    n_sp, n_el, n_pr, n_qt = len(sp), len(el), len(pr), len(qt)
    n_proj = sum(1 for s in sp if s["type"] == "IFCPROJECT")
    n_contained = sum(1 for s in sp if s.get("parent_via") == "contained")
    n_depth0 = sum(1 for s in sp if s.get("depth") == 0)
    via = {}
    for e in el:
        via[e.get("container_via")] = via.get(e.get("container_via"), 0) + 1
    n_feature = sum(1 for e in el if e["type"] == "IFCSURFACEFEATURE")

    dup: dict[tuple, int] = {}
    for f, p in pr:
        k = (f, p["element"], p["pset_name"], p["name"])
        dup[k] = dup.get(k, 0) + 1
    n_collapse = sum(v - 1 for v in dup.values() if v > 1)

    return [
        {"id": "spatial_all", "answer": n_sp,
         "ask": "IFCPROJECT を含め、空間構造の実体を全て数えたときの行数"},
        {"id": "spatial_no_project", "answer": n_sp - n_proj,
         "ask": "同上から IFCPROJECT を除いた行数"},
        {"id": "spatial_depth0", "answer": n_depth0,
         "ask": "親を持たない空間（深さ0）の行数。"
                "包含関係で他の空間の下に置かれている空間は、置かれ先を親として扱う"},
        {"id": "spatial_depth0_aggregate_only", "answer": n_depth0 + n_contained,
         "ask": "同上だが、親は集約関係（IFCRELAGGREGATES）でのみ決まるとしたときの行数"},
        {"id": "element_all", "answer": n_el,
         "ask": "物理要素の行数。集約の親も部品も、付着している要素も、全て1行として数える"},
        {"id": "element_direct_only", "answer": via.get("direct", 0),
         "ask": "同上のうち、IFCRELCONTAINEDINSPATIALSTRUCTURE で直接ある空間に"
                "載っているものだけを数えた行数"},
        {"id": "element_no_adheres", "answer": n_el - via.get("adheres", 0),
         "ask": "物理要素の行数から、付着関係（IFCRELADHERESTOELEMENT）でしか"
                "空間に繋がっていないものを除いた行数"},
        {"id": "element_no_feature", "answer": n_el - n_feature,
         "ask": "物理要素の行数から IFCSURFACEFEATURE を除いた行数"},
        {"id": "property_all", "answer": n_pr,
         "ask": "性能仕様の行数。直接付いたものと型経由で付いたものを別の行として数える"},
        {"id": "property_merged", "answer": n_pr - n_collapse,
         "ask": "同上だが、同じファイル・同じ要素・同じ Pset 名・同じ属性名のものを"
                "1行にまとめたときの行数"},
        {"id": "quantity_all", "answer": n_qt,
         "ask": "数量（IfcQuantity*）の行数"},
    ]


def build() -> dict:
    ref = json.loads((ROOT / "reference" / f"{SRC}.json").read_text(encoding="utf-8"))
    return {
        "task": "T005",
        "from": SRC,
        "note": ("答えは全て参照解から計算した値。設問はこちらが定めた数え方であり、"
                 "規格の解釈を問うものではない。"),
        "questions": questions(ref),
    }


def main() -> int:
    doc = build()
    out = ROOT / "reference" / "T005.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out.relative_to(ROOT)}: 設問 {len(doc['questions'])}問")
    for q in doc["questions"]:
        print(f"  {q['id']:<32} {q['answer']:>5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
