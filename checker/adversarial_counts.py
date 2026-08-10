#!/usr/bin/env python3
"""数え上げ課題（T005 / T006）の採点器を試す。

    python3 checker/adversarial_counts.py T006

T004 は「中身ゼロの答案が満点を取る」ことに公開直前まで気づかなかった。
原因は、敵対テストの全ケースが**参照解を摂動して**作られていたこと。
参照解の近傍しか探索しないので、参照解から遠い答案は設計上テストされない。

**ここでは逆から作る。** まず「何も読まずに書ける答案」を並べ、
それが低い点にとどまることを確かめる。そのあとで惜しい答案を見る。

  void_zero      全部 0
  void_empty     空の答案
  void_mode      全部を同じ値（コーパスで一番大きい数）にする
  void_plausible 桁だけ合わせた、それらしい値
  near_miss      1問だけ 1 ずれる（完全一致のみなので落ちるべき）
  half           半分だけ答える
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASK_ID = sys.argv[1] if len(sys.argv) > 1 else "T005"
TASK = ROOT / "tasks" / TASK_ID / "task.json"
REF = ROOT / "reference" / f"{TASK_ID}.json"


def score(name: str, payload) -> dict:
    p = ROOT / "out" / f"{name}.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(payload if isinstance(payload, str)
                 else json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "bench" / "check.py"),
                        str(TASK), str(REF), str(p)], capture_output=True, text=True)
    return json.loads(r.stdout)[0]


def main() -> int:
    ref = json.loads(REF.read_text(encoding="utf-8"))
    qs = ref["questions"]
    ids = [q["id"] for q in qs]
    full = {q["id"]: q["answer"] for q in qs}
    failures = 0

    lo = TASK_ID.lower()
    r = score(f"_calib_{lo}", {"task": TASK_ID, "answers": full})
    ok = abs(r["score"] - 100.0) < 1e-9
    print(f"[{'OK' if ok else 'NG'}] 較正: 参照解 {r['score']:.1f}/100")
    failures += 0 if ok else 1

    broken = json.dumps({"task": TASK_ID, "answers": full}, ensure_ascii=False)
    r = score(f"evil_malformed_{lo}", broken.replace(",", "", 1))
    ok = r["score"] < 100.0
    print(f"[{'OK' if ok else 'NG'}] malformed: {r['score']:.1f}  ← 満点になってはいけない")
    failures += 0 if ok else 1

    # **何も読まずに書ける答案は、10点未満でなければならない。**
    biggest = max(q["answer"] for q in qs)
    voids = {
        f"void_zero_{lo}": {i: 0 for i in ids},
        f"void_empty_{lo}": {},
        f"void_mode_{lo}": {i: biggest for i in ids},
        f"void_plausible_{lo}": {i: 200 for i in ids},
    }
    for name, ans in voids.items():
        r = score(name, {"task": TASK_ID, "answers": ans})
        ok = r["score"] < 10.0
        print(f"[{'OK' if ok else 'NG'}] {name}: {r['score']:.1f}/100  ← 10点未満であるべき")
        failures += 0 if ok else 1

    near = dict(full)
    near[ids[0]] = full[ids[0]] + 1
    r = score(f"near_miss_{lo}", {"task": TASK_ID, "answers": near})
    ok = r["score"] < 100.0
    print(f"[{'OK' if ok else 'NG'}] near_miss(1ずれ): {r['score']:.1f}/100  ← 満点は不可")
    failures += 0 if ok else 1

    half = {i: full[i] for i in ids[: len(ids) // 2]}
    r = score(f"half_{lo}", {"task": TASK_ID, "answers": half})
    ok = 0.0 < r["score"] < 100.0
    print(f"[{'OK' if ok else 'NG'}] half(半分だけ): {r['score']:.1f}/100  ← 部分点であるべき")
    failures += 0 if ok else 1

    total = 8
    print()
    print(f"敵対テスト({TASK_ID}): {total - failures}/{total} 通過")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
