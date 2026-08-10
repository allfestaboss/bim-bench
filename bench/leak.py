"""課題文に答えが書いていないかを機械照合する。

    python3 -m bench.leak          # 数え上げ課題を全部
    python3 -m bench.leak T007

**なぜ要るか。**

T006 でやった。T005 の欠陥（性能仕様2問の所有者範囲が未確定）を説明するために、
課題文の `note` に「物理要素に限れば 308/306、所有者を問わなければ 324/322」と
書いた。**その4つが、そのまま T006 の4問の答えである。**
出題側の欠陥を直す文章が、直した先の答えを漏らしていた。

漏れは5つの検査を全部すり抜けた。

    較正            参照解の関数。課題文を見ない
    外部検算        参照解の関数。課題文を見ない
    敵対テスト      参照解の関数。課題文を見ない
    bench/probe     課題文を見るが、**範囲の名指しだけ**を見る
    bench/freeze    改変を見る。中身は見ない

`bench/selfcheck.py` には「答えを例に書いていないか」の検査が既にあった
（`_example_provenance`）。**思想はあったが、届いていなかった。**
あれは `answer_format.results` の記入例しか見ておらず、数え上げ課題には
`results` が無いので、黙って何も検査せずに通っていた。

見つけたのは腕である。armC_r2 が答案とは別に「課題文の note 自体が
性能仕様4問の答えを明記しており、本文を読むだけで答えられる」と申告した。

**この検査は、その1件を機械で捕まえる。**

数詞（17ファイル、13問、6走 など）は答えではないので落とす。
落としたうえで課題文に残る数が参照解の答えと一致したら、漏れとして報告する。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 数詞。この後ろに付く数は「量の説明」であって答えではない。
COUNTERS = ("ファイル", "問", "本", "件", "走", "回", "点", "通り", "つ", "度", "版", "年", "行目")

# 課題文のうち、腕が読む部分。answer_format の 0 は答えではないので外す。
FIELDS = ("title", "note", "asked", "rules", "questions")

# この検査が落とすことを期待する既知の欠陥。落ちなくなったら検査が壊れている。
KNOWN_LEAKS = {"T006": {"property_owner_physical_split", "property_owner_physical_merged",
                        "property_owner_any_split", "property_owner_any_merged"}}


def statement(task: dict, task_id: str = "") -> str:
    """腕が読む文面を1本の文字列にする。

    **課題文だけでは足りない。**腕はプロンプトも読む。T006 の漏れは note にあったが、
    同じ数字をプロンプトに書いていれば同じことになる。腕が読むものは全部入れる。
    """
    parts = []
    for k in FIELDS:
        v = task.get(k)
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            for x in v:
                parts.append(x if isinstance(x, str)
                             else " ".join(str(y) for y in x.values()))
    prompt = ROOT / "arms" / f"{task_id}.md"
    if task_id and prompt.exists():
        parts.append(prompt.read_text(encoding="utf-8"))
    return "\n".join(parts)


def bare_numbers(text: str) -> set[str]:
    """数詞に付いた数を落として、裸の数だけ残す。"""
    text = re.sub(r"\d+(?=(" + "|".join(COUNTERS) + r"))", "", text)
    return set(re.findall(r"\d+", text))


def check(task_id: str) -> int:
    tf = ROOT / "tasks" / task_id / "task.json"
    rf = ROOT / "reference" / f"{task_id}.json"
    if not tf.exists() or not rf.exists():
        return 0
    task = json.loads(tf.read_text(encoding="utf-8"))
    ref = json.loads(rf.read_text(encoding="utf-8"))
    if "questions" not in ref:
        return 0

    nums = bare_numbers(statement(task, task_id))
    leaked = [q["id"] for q in ref["questions"] if str(q["answer"]) in nums]

    print(f"=== {task_id} 課題文に答えが書いていないか ===")
    for q in ref["questions"]:
        hit = str(q["answer"]) in nums
        print(f"[{'NG' if hit else 'OK'}] {q['id']:<32} 答={q['answer']:>5}"
              + ("  **課題文に書いてある**" if hit else ""))

    expected = KNOWN_LEAKS.get(task_id, set())
    print()
    if expected:
        if set(leaked) == expected:
            print(f"既知の漏れ {len(expected)}件を検出（この検査自身の較正）")
            return 0
        print(f"**較正に失敗。** 期待 {sorted(expected)} / 実際 {sorted(leaked)}")
        return 1
    if leaked:
        print(f"**漏れ {len(leaked)}件。** 課題文を読むだけで答えられる: " + " / ".join(leaked))
        return 1
    print("漏れなし。")
    return 0


def main() -> int:
    tasks = sys.argv[1:] or [d.name for d in sorted((ROOT / "tasks").iterdir()) if d.is_dir()]
    bad = 0
    for i, t in enumerate(tasks):
        if i:
            print()
        bad += check(t)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
