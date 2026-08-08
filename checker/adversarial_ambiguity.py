#!/usr/bin/env python3
"""「決まらない箇所」の採点器が騙されないかを試す。

この課題は正解が1つに決まらない。だからこそ採点器が甘くなりやすい。
**「曖昧だ」と言うだけの答案が高得点になったら、その採点器は壊れている。**

  no_counts        箇所は当てるが、何件動くかを書かない
  wrong_counts     数を書くが違う
  one_bucket       全部の実体を1つの箇所にまとめて出す（雑な一括指摘）
  flood            実体をでっち上げて箇所を水増しする
  biggest_only     一番大きい箇所だけ挙げる
  swapped_counts   count_a と count_b を逆に書く（どちらの読みか分かっていない）

使い方: adversarial_ambiguity.py
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / "out"


def _full(ref: dict) -> dict:
    return {"task": "T004", "sites": [
        {"entities": list(s["entities"]), "count_a": s["count_a"], "count_b": s["count_b"]}
        for s in ref["sites"]]}


def no_counts(ref):
    s = _full(ref)
    for x in s["sites"]:
        x.pop("count_a", None)
        x.pop("count_b", None)
    return s


def wrong_counts(ref):
    s = _full(ref)
    for x in s["sites"]:
        x["count_a"] += 1
        x["count_b"] += 1
    return s


def swapped_counts(ref):
    s = _full(ref)
    for x in s["sites"]:
        x["count_a"], x["count_b"] = x["count_b"], x["count_a"]
    return s


def one_bucket(ref):
    every = sorted({e for y in ref["sites"] for e in y["entities"]})
    return {"task": "T004", "sites": [{"entities": every, "count_a": 0, "count_b": 0}]}


def flood(ref):
    s = _full(ref)
    for i in range(8):
        s["sites"].append({"entities": [900000 + i], "count_a": 1, "count_b": 2})
    return s


def biggest_only(ref):
    s = _full(ref)
    s["sites"] = [max(s["sites"], key=lambda x: len(x["entities"]))]
    return s


EVIL = [
    ("no_counts", no_counts, "Q9"),
    ("wrong_counts", wrong_counts, "Q9"),
    ("swapped_counts", swapped_counts, "Q9"),
    ("one_bucket", one_bucket, "Q8"),
    ("flood", flood, "Q8"),
    ("biggest_only", biggest_only, "Q8"),
]


def main() -> int:
    ref_path = ROOT / "reference" / "T004.json"
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    task = ROOT / "tasks" / "T004" / "task.json"
    TMP.mkdir(exist_ok=True)

    def score(name: str, payload) -> dict:
        p = TMP / f"{name}.json"
        p.write_text(payload if isinstance(payload, str)
                     else json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(ROOT / "bench" / "check.py"), str(task), str(ref_path), str(p)],
            capture_output=True, text=True)
        return json.loads(r.stdout)[0]

    failures = 0

    base = score("_calib_t004", _full(ref))
    ok = abs(base["score"] - base["max"]) < 1e-9 and not base["fatal"]
    print(f"[{'OK' if ok else 'NG'}] 較正: 参照解 {base['score']:.1f}/{base['max']:.0f}")
    failures += 0 if ok else 1

    broken = json.dumps(_full(ref), ensure_ascii=False, separators=(",", ":"))
    assert "},{" in broken
    r = score("evil_malformed_t004", broken.replace("},{", "}{", 1))
    ok = bool(r["fatal"]) and r["score"] == 0.0
    print(f"[{'OK' if ok else 'NG'}] malformed: {r['score']:.1f}  ← 失格になるべき")
    failures += 0 if ok else 1

    for name, fn, expect in EVIL:
        r = score(name, fn(copy.deepcopy(ref)))
        lost = [c["level"] for c in r["checks"] if not c["ok"] and c["max"]]
        ok = r["score"] < r["max"] - 1e-9 and expect in lost
        print(f"[{'OK' if ok else 'NG'}] {name}: {r['score']:.1f}/100  "
              f"失点={sorted(set(lost)) or '無し'}  期待={expect}")
        failures += 0 if ok else 1

    total = len(EVIL) + 2
    print()
    print(f"敵対テスト: {total - failures}/{total} 通過")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
