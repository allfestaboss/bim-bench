"""数え上げ課題の設問が、答えの決まる範囲を課題文で固定できているかを機械照合する。

    python3 -m bench.probe            # T005 と T006
    python3 -m bench.probe T006

**なぜ要るか。**

採点器・較正・敵対テストはすべて参照解の関数なので、参照解の中の誤りは検出できない。
**さらに課題文は参照解の関数ではない。**ベンチの中で唯一、参照解と独立に書かれる。
だから同じ理屈で、3つの検査は**参照解と課題文の食い違い**を検出できない。
内部整合性が完璧なまま、聞いていない問いの答えを採点し続けられる。

T005 で実際に起きた。性能仕様は物理要素だけでなく IFCSPACE / IFCBUILDING / IFCZONE
にも付いているのに、**どこまでを数えるかを課題文が決めていなかった。**
物理要素に限れば 308/306、所有者を問わなければ 324/322。どちらも規則から導ける。
較正も外部検算も敵対テストも通り、6走中5走が独立に申告するまで気づかなかった。

**この検査は、その1件を機械で捕まえる。**

  1. 所有者の範囲（物理要素だけか、種類を問わないか）を実際に切り替えて数え直す
  2. 答えが動いた設問について、その設問の文面が範囲を名指ししているかを見る
  3. 動いたのに名指ししていない設問を欠陥として報告する

**この検査の限界。** 見ているのは「所有者の範囲」という1つの軸だけである。
性能仕様と数量は行が実体にぶら下がるので、どの実体までを母集団にするかが
設問と直交して決まる——そこだけを見ている。空間や要素の設問は母集団の定義が
規則本文で型により固定されているので対象外。**他の軸の欠陥は捕まえられない。**
軸を増やすには、規則が決めていない箇所を新たに見つけるしかない。

**この検査自身の較正:** T005 に当てると必ず落ちる（既知の欠陥2件）。
落ちなくなったら、検査のほうが壊れている。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .counts import _is_physical, _property_rows, _split_merged
from .ifc import SPATIAL_TYPES

ROOT = Path(__file__).resolve().parent.parent
SRC = "T002"

# 設問の文面がこれらの語を含んでいれば、所有者の範囲を名指ししているとみなす。
DISCRIMINATORS = ("物理要素", "所有者")

# この検査が落とすことを期待する既知の欠陥。ここが落ちなくなったら検査が壊れている。
KNOWN_DEFECTS = {"T005": {"property_all", "property_merged"}}


def _quantity_rows(ref: dict) -> list[tuple[str, int, str]]:
    """数量を (ファイル, 所有者番号, 所有者の型) にならす。"""
    from .step import load

    corpus = ROOT / "corpus" / "buildingsmart"
    out = []
    for x in ref["results"]:
        want = {q["element"] for q in x["quantities"] if q.get("element") is not None}
        model = load(corpus / x["file"]) if want else None
        types = {e: (model.get(e).type if model.get(e) else "??") for e in want}
        for q in x["quantities"]:
            out.append((x["file"], q["element"], types.get(q["element"], "??")))
    return out


def scopes(ref: dict) -> dict[str, dict[str, int]]:
    """所有者の範囲を切り替えたときの、各集計の値。"""
    st = frozenset(SPATIAL_TYPES)
    pr = _property_rows(ref)
    qt = _quantity_rows(ref)

    pr_phys = [r for r in pr if _is_physical(r[2], st)]
    qt_phys = [r for r in qt if _is_physical(r[2], st)]

    p_any_s, p_any_m = _split_merged(pr)
    p_ph_s, p_ph_m = _split_merged(pr_phys)

    return {
        "property_split": {"any": p_any_s, "physical": p_ph_s},
        "property_merged": {"any": p_any_m, "physical": p_ph_m},
        "quantity": {"any": len(qt), "physical": len(qt_phys)},
    }


def family(qid: str) -> str | None:
    """設問がどの集計に当たるか。所有者の範囲が効きうるものだけを返す。"""
    if qid.startswith("property") and "merged" in qid:
        return "property_merged"
    if qid.startswith("property"):
        return "property_split"
    if qid.startswith("quantity"):
        return "quantity"
    return None


def check(task: str) -> int:
    ref = json.loads((ROOT / "reference" / f"{SRC}.json").read_text(encoding="utf-8"))
    doc = json.loads((ROOT / "reference" / f"{task}.json").read_text(encoding="utf-8"))
    sc = scopes(ref)

    print(f"=== {task} 所有者の範囲による揺れ ===")
    flagged: list[str] = []
    for q in doc["questions"]:
        fam = family(q["id"])
        if fam is None:
            continue
        vals = sc[fam]
        moves = len(set(vals.values())) > 1
        pinned = any(d in q["ask"] for d in DISCRIMINATORS)
        if not moves:
            verdict, mark = "不変（範囲を問わず同じ）", "OK"
        elif pinned:
            verdict, mark = "動くが文面が範囲を名指ししている", "OK"
        else:
            verdict, mark = "**動くのに文面が範囲を決めていない**", "NG"
            flagged.append(q["id"])
        span = " / ".join(f"{k}={v}" for k, v in vals.items())
        print(f"[{mark}] {q['id']:<32} 答={q['answer']:>4}  ({span})  {verdict}")

    expected = KNOWN_DEFECTS.get(task, set())
    print()
    if expected:
        if set(flagged) == expected:
            print(f"既知の欠陥 {len(expected)}件を検出（この検査自身の較正）: "
                  + " / ".join(sorted(expected)))
            return 0
        print(f"**較正に失敗。** 期待 {sorted(expected)} / 実際 {sorted(flagged)}")
        return 1
    if flagged:
        print(f"**欠陥 {len(flagged)}件。** 設問が答えの決まる範囲を固定していない: "
              + " / ".join(flagged))
        return 1
    print("欠陥なし。範囲が動く設問は全て文面で名指ししている。")
    return 0


def main() -> int:
    tasks = sys.argv[1:] or ["T005", "T006"]
    bad = 0
    for i, t in enumerate(tasks):
        if i:
            print()
        bad += check(t)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
