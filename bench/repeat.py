"""同じ課題を何度も回した結果をまとめる。

    python3 -m bench.repeat T004

**平均だけでは意味が薄い。** n=3 で標準偏差を出しても精度は無い。
見るべきは3つで、どれも小さい n で意味を持つ。

  1. 順位が保たれるか   armC > armB が毎回成立するか。1回でも逆転したら結論が弱まる
  2. ばらつきの幅       最小〜最大。n が小さいときは範囲のほうが正直
  3. 箇所ごとの発見率   **ここが一番効く。**「毎回落とす」のか「たまたま1回落とした」のかで
                        結論の強さが変わる。腕ごと・箇所ごとに何回見つけたかを出す

答案は attempts/<TASK>/<腕>_r<N>.json という名前で置く。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _ents(t) -> frozenset:
    out = set()
    for e in (t.get("entities") or []):
        try:
            out.add(int(e))
        except (TypeError, ValueError):
            pass
    return frozenset(out)


def runs(task_id: str) -> dict[str, list[Path]]:
    """腕ごとの答案を集める。r1, r2, … の順に並べる。"""
    out: dict[str, list[Path]] = {}
    d = ROOT / "attempts" / task_id
    for p in sorted(d.glob("arm*_r*.json")):
        arm = p.stem.split("_r")[0]
        out.setdefault(arm, []).append(p)
    return out


def score(task_id: str, path: Path) -> dict:
    r = subprocess.run(
        [sys.executable, str(ROOT / "bench" / "check.py"),
         str(ROOT / "tasks" / task_id / "task.json"),
         str(ROOT / "reference" / f"{task_id}.json"), str(path)],
        capture_output=True, text=True)
    return json.loads(r.stdout)[0]


def main() -> int:
    task_id = sys.argv[1] if len(sys.argv) > 1 else "T004"
    ref = json.loads((ROOT / "reference" / f"{task_id}.json").read_text(encoding="utf-8"))
    sites = ref.get("sites") or []
    by_arm = runs(task_id)
    if not by_arm:
        print(f"attempts/{task_id}/ に <腕>_r<N>.json が無い。")
        return 2

    print(f"== {task_id} 反復 ==  参照解の箇所 {len(sites)}件")
    print()
    print(f"{'腕':<8}{'n':>3}{'最小':>8}{'最大':>8}{'中央':>8}{'幅':>7}   各回")
    print("-" * 78)
    results: dict[str, list[float]] = {}
    detail: dict[str, list[dict]] = {}
    for arm, paths in sorted(by_arm.items()):
        ss = []
        ds = []
        for p in paths:
            r = score(task_id, p)
            ss.append(r["score"])
            ds.append(r)
        results[arm] = ss
        detail[arm] = ds
        srt = sorted(ss)
        mid = srt[len(srt) // 2] if len(srt) % 2 else (srt[len(srt) // 2 - 1] + srt[len(srt) // 2]) / 2
        print(f"{arm:<8}{len(ss):>3}{min(ss):>8.1f}{max(ss):>8.1f}{mid:>8.1f}"
              f"{max(ss) - min(ss):>7.1f}   "
              + "  ".join(f"{x:.1f}" for x in ss))

    # ---- 順位が保たれるか ----
    arms = sorted(results)
    if len(arms) == 2:
        a, b = arms
        print()
        n = min(len(results[a]), len(results[b]))
        wins = sum(1 for i in range(n) if results[a][i] > results[b][i])
        ties = sum(1 for i in range(n) if abs(results[a][i] - results[b][i]) < 1e-9)
        print(f"順位: {a} が {b} を上回った回 {wins}/{n}"
              + (f"（同点 {ties}回）" if ties else ""))
        if min(results[b]) > max(results[a]):
            print(f"      **{b} の最小値が {a} の最大値を上回る。範囲が重ならない。**")
        elif min(results[a]) > max(results[b]):
            print(f"      **{a} の最小値が {b} の最大値を上回る。範囲が重ならない。**")
        else:
            print("      範囲が重なっている。順位は確定できない。")

    # ---- 箇所ごとの発見率 ----
    print()
    print("=== 箇所ごとに、何回見つけたか ===")
    hdr = f"{'決まらない箇所':<26}"
    for arm in arms:
        hdr += f"{arm:>10}"
    print(hdr)
    print("-" * (30 + 10 * len(arms)))
    for s in sites:
        rs = set(s["entities"])
        row = f"{s['id']:<26}"
        for arm in arms:
            hit = 0
            for p in by_arm[arm]:
                sub = json.loads(p.read_text(encoding="utf-8"))
                found = any(rs & _ents(t) for t in (sub.get("sites") or []))
                hit += 1 if found else 0
            row += f"{f'{hit}/{len(by_arm[arm])}':>10}"
        print(row)

    # ---- 影響の計算が当たったか ----
    print()
    print("=== 影響の計算（count_a が実在する値 かつ 差が件数と一致）===")
    totals = set(ref.get("totals") or [])
    for arm in arms:
        ok_per_run = []
        for p in by_arm[arm]:
            sub = json.loads(p.read_text(encoding="utf-8"))
            good = 0
            for s in sites:
                rs = set(s["entities"])
                n = int(s.get("affected") or len(rs))
                for t in (sub.get("sites") or []):
                    if not (rs & _ents(t)):
                        continue
                    try:
                        a_, b_ = float(t.get("count_a")), float(t.get("count_b"))
                    except (TypeError, ValueError):
                        continue
                    if int(a_) in totals and abs(a_ - b_) == n:
                        good += 1
                    break
            ok_per_run.append(good)
        print(f"  {arm:<8} {'  '.join(f'{g}/{len(sites)}' for g in ok_per_run)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
