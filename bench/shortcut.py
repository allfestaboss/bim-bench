"""設問が、想定より浅い経路で解けてしまわないかを見る。**助言であって関門ではない。**

    python3 -m bench.shortcut          # 数え上げ課題を全部
    python3 -m bench.shortcut T007

**なぜ要るか。**

T007 でやった。`property_owner_any_split` は「所有者の種類を問わず、全ての性能仕様の
行数」を訊く設問で、答えは 324。ところが規則が性能仕様を
「IFCPROPERTYSINGLEVALUE と IFCPROPERTYENUMERATEDVALUE」と型で定義しているので、
**その2型を grep で数えるだけで 324 が出る。**所有関係を一切たどらない。

漏れ（`bench/leak.py`）とは違う。答えは課題文に書いていないし、答案も正当である。
壊れているのは**設問が測っているつもりの能力**のほうで、
所有関係をたどれるかを訊いたつもりが、型名を知っているかを訊いていた。

見つけたのは腕である。armC_r2 が「この1問は所有関係を一切辿らず grep 2回で解ける」と
申告し、こちらで検算して一致した。

**なぜ関門にしないか。**

最初は落とす検査として書いた。型の組を3つまで見たところ、T007 で
`spatial_depth0`(17) が `IFCPROJECT + IFCFACILITY + IFC4` に、
`spatial_depth0_aggregate_only`(19) が `IFCPROJECT + IFCRAILWAY` に一致した。
**後者は意味の無い組み合わせである。**答えが小さいと、型の足し算はいくらでも当たる。

落とす検査にすると、この手の当たりを毎回手で振り払うことになり、
**振り払う癖がついた検査は、本物が来ても振り払う。**だから助言にした。
出すのは手がかりであって判定ではない。人が読んで決める。

  強い手がかり  答えが**単独の型**の実体数と一致する
  弱い手がかり  答えが**2型の和**と一致する。小さい答えでは偶然が多い

**この検査の限界。**見ているのは型の出現数の和だけで、一段でも加工が入る経路
（引き算、重複除去）は捕まえられない。また一致は**近道の存在**を示すだけで、
腕がそれを使ったことは示さない。T007 の3走はいずれも所有関係をたどったうえで
この値に到達している。
"""

from __future__ import annotations

import json
import re
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 課題文に出てくる型名を拾う。IFC で始まる大文字の語。
# 'IFC4' のようなスキーマ名は型ではないので落とす（数字で終わるものを除く）。
TYPE_RE = re.compile(r"\bIFC[A-Z]{3,}\b")


def corpus_counts(task: dict) -> dict[str, int]:
    """課題の対象17ファイルで、型ごとの実体定義の数を数える。"""
    pat = re.compile(r"^#\d+\s*=\s*([A-Z0-9_]+)", re.MULTILINE)
    counts: dict[str, int] = {}
    for f in task["files"]:
        text = (ROOT / f["path"]).read_text(encoding="utf-8", errors="replace")
        for t in pat.findall(text.upper()):
            counts[t] = counts.get(t, 0) + 1
    return counts


def named_types(task: dict) -> set[str]:
    """課題文が名前を出している型のうち、コーパスに実在するもの。"""
    blob = " ".join(
        [task.get("note", "")]
        + list(task.get("rules") or [])
        + [q["ask"] for q in (task.get("questions") or [])]
    )
    return set(TYPE_RE.findall(blob))


def check(task_id: str) -> None:
    tf = ROOT / "tasks" / task_id / "task.json"
    rf = ROOT / "reference" / f"{task_id}.json"
    if not tf.exists() or not rf.exists():
        return
    task = json.loads(tf.read_text(encoding="utf-8"))
    ref = json.loads(rf.read_text(encoding="utf-8"))
    if "questions" not in ref:
        return

    counts = corpus_counts(task)
    live = sorted(t for t in named_types(task) if counts.get(t))

    single = {counts[t]: (t,) for t in live}
    pair = {}
    for a, b in combinations(live, 2):
        s = counts[a] + counts[b]
        pair.setdefault(s, (a, b))

    print(f"=== {task_id} 素の数え上げで届くか（助言） ===")
    strong, weak = [], []
    for q in ref["questions"]:
        a = q["answer"]
        if a in single:
            strong.append(q["id"])
            print(f"[強] {q['id']:<32} 答={a:>5}  ← {single[a][0]} の実体数と一致")
        elif a in pair:
            weak.append(q["id"])
            print(f"[弱] {q['id']:<32} 答={a:>5}  ← {' + '.join(pair[a])} の和と一致")
        else:
            print(f"[  ] {q['id']:<32} 答={a:>5}")

    print()
    if not strong and not weak:
        print("素の数え上げで届く設問は無い。")
        return
    print(f"強い手がかり {len(strong)}件 / 弱い手がかり {len(weak)}件。"
          " **判定ではない。**弱いほうは型の足し算がたまたま当たっただけのことが多い。"
          "設問が測るつもりの能力を測っているかは、人が読んで決めること。")


def main() -> int:
    tasks = sys.argv[1:] or [d.name for d in sorted((ROOT / "tasks").iterdir()) if d.is_dir()]
    for i, t in enumerate(tasks):
        if i:
            print()
        check(t)
    return 0   # **助言なので、落とさない。**


if __name__ == "__main__":
    sys.exit(main())
