"""課題を凍結し、答案が書かれたあとに動いていないことを機械で確かめる。

    python3 -m bench.freeze T006 --stamp   # 凍結する（答案が無いときだけ）
    python3 -m bench.freeze T006           # 凍結が守られているか検算する

**なぜ要るか。**

T004 は、答案を読んだあとに課題文と採点器の両方を書き換えていた。
改訂が動かした点数（+52.6）が、示したとされる腕間差（35.7）より大きく、
測定として成立しなかった。撤回した。

「走らせる前に凍結する」を人の記憶で守るのは無理である。**鍵を取って照合する。**

**凍結が破れるのは、答案が存在したあとに動いたときだけ。**
答案が1つも無いうちは何度でも作り直してよい（それは設計であって改訂ではない）。
だから `--stamp` は答案があると拒否し、検算は答案があるときだけ厳密に落とす。

凍結の対象は「点数を動かしうるもの」全て。課題文と参照解だけでは足りない。
採点器・敵対テスト・参照解の生成器・較正・課題文の照合まで入れる。
T004 で動いたのは採点器のほうだった。

**ただし2層に分ける。**

  硬  tasks/<T>/task.json と reference/<T>.json
      答案が存在したあとに動いたら、その課題の点数は測定ではない。**落とす。**

  軟  採点器・生成器・敵対テスト・較正・課題文の照合
      次の課題を足せば必ず動く共有コードである。動いたこと自体は罪ではない。
      罪なのは**動いた結果として参照解や点数が変わること**で、それは硬の層と
      `out/<T>.json` の差分が捕まえる。ここでは報告だけして止めない。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 硬 — 答案が存在したあとに動いたら、その課題の点数は測定として使えない。
# **腕に渡すプロンプトも入れる。**課題文と同じく、腕が読むものだからである。
HARD_PATHS = [
    "tasks/{task}/task.json",
    "reference/{task}.json",
    "arms/{task}.md",
]

# 軟 — 共有コード。動いたら報告するが、それ自体では落とさない。
SOFT_PATHS = [
    "bench/check.py",
    "bench/counts.py",
    "bench/probe.py",
    "bench/selfcheck.py",
    "checker/adversarial_counts.py",
]


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def targets(task: str, paths: list[str]) -> list[Path]:
    return [ROOT / s.format(task=task) for s in paths]


def answers(task: str) -> list[Path]:
    """腕の答案。cost.json は測定の記録であって答案ではない。"""
    d = ROOT / "attempts" / task
    return sorted(p for p in d.glob("*.json") if p.name != "cost.json") if d.is_dir() else []


def stamp(task: str) -> int:
    have = answers(task)
    if have:
        print(f"**凍結できない。**{task} には既に答案が {len(have)}本ある: "
              + ", ".join(p.name for p in have))
        print("答案を見たあとに凍結し直すのは、T004 を撤回に追い込んだ改訂と同じである。")
        return 1
    doc = {
        "task": task,
        "note": ("腕を走らせる前に凍結した。硬の鍵が動いたら、"
                 "答案の点数は測定ではなく改訂の産物である。"),
        "hard": {},
        "soft": {},
    }
    for tier, paths in (("hard", HARD_PATHS), ("soft", SOFT_PATHS)):
        for p in targets(task, paths):
            if not p.exists():
                print(f"**凍結できない。**{p.relative_to(ROOT)} が無い。")
                return 1
            doc[tier][str(p.relative_to(ROOT))] = digest(p)
    out = ROOT / "tasks" / task / "FROZEN.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out.relative_to(ROOT)} に "
          f"硬{len(doc['hard'])}件 / 軟{len(doc['soft'])}件を凍結した。")
    for tier in ("hard", "soft"):
        for k, v in doc[tier].items():
            print(f"  [{tier}] {k:<38} {v[:16]}")
    return 0


def verify(task: str) -> int:
    f = ROOT / "tasks" / task / "FROZEN.json"
    if not f.exists():
        print(f"[--] {task}: 凍結の記録が無い（--stamp で作る）")
        return 0
    doc = json.loads(f.read_text(encoding="utf-8"))
    have = answers(task)

    def drift(tier: str) -> list[tuple[str, str, str]]:
        out = []
        for rel, want in (doc.get(tier) or {}).items():
            p = ROOT / rel
            got = digest(p) if p.exists() else "(無い)"
            if got != want:
                out.append((rel, want, got))
        return out

    hard, soft = drift("hard"), drift("soft")
    n = len(doc.get("hard") or {}) + len(doc.get("soft") or {})

    if not hard and not soft:
        print(f"[OK] {task}: 凍結の {n}件は動いていない（答案 {len(have)}本）")
        return 0

    for rel, want, got in soft:
        print(f"[--] {task}: 共有コードが動いた {rel}"
              f"  凍結={want[:16]} 現在={got[:16]}")
    if soft and not hard:
        print(f"     課題文と参照解は動いていないので、点数は測定のままである。")

    if not hard:
        return 0
    print(f"[NG] {task}: **課題文か参照解が動いている**")
    for rel, want, got in hard:
        print(f"     {rel:<38} 凍結={want[:16]} 現在={got[:16]}")
    if not have:
        print("     答案がまだ無いので、これは改訂ではなく設計である。"
              "--stamp で凍結し直すこと。")
        return 0
    print("     **答案が存在したあとに動いている。この課題の点数は測定として使えない。**")
    return 1


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--stamp" in sys.argv:
        if not args:
            print("課題を指定すること: python3 -m bench.freeze T006 --stamp")
            return 1
        return sum(stamp(t) for t in args)
    tasks = args or [d.name for d in sorted((ROOT / "tasks").iterdir()) if d.is_dir()]
    return 1 if sum(verify(t) for t in tasks) else 0


if __name__ == "__main__":
    sys.exit(main())
