"""課題を凍結し、答案が書かれたあとに動いていないことを機械で確かめる。

    python3 -m bench.freeze T006 --stamp      # 凍結する（**答案がまだ無いときだけ**）
    python3 -m bench.freeze T001 --baseline   # 事後記録（答案が既にあるとき）
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
    "bench/leak.py",
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


def record(task: str, mode: str) -> int:
    """mode="stamp" は凍結、mode="baseline" は事後記録。

    **この2つは違うものである。**凍結は答案より前に押すので、点数が測定である
    ことを保証する。事後記録は答案を見たあとに押すので、**過去について何も
    保証しない。**これから先の改変を検出できるようにするだけである。
    区別はファイル名（`FROZEN.json` / `BASELINE.json`）と `kind` に書く。
    """
    have = answers(task)
    if mode == "stamp" and have:
        print(f"**凍結できない。**{task} には既に答案が {len(have)}本ある: "
              + ", ".join(p.name for p in have))
        print("答案を見たあとに凍結し直すのは、T004 を撤回に追い込んだ改訂と同じである。")
        print("既に走り終えた課題には --baseline を使うこと（凍結ではなく事後記録）。")
        return 1
    if mode == "baseline" and not have:
        print(f"{task} にはまだ答案が無い。--stamp で本当の凍結ができる。")
        return 1
    doc = {
        "task": task,
        "kind": ("腕を走らせる前に凍結した" if mode == "stamp" else
                 "**事後記録であって凍結ではない。**過去を保証しない。"
                 "これから先の改変を検出できるようにするだけである"),
        "note": ("腕を走らせる前に凍結した。硬の鍵が動いたら、"
                 "答案の点数は測定ではなく改訂の産物である。"
                 if mode == "stamp" else
                 "答案が既にある状態で押した。**この記録は点数が測定であることを"
                 "証明しない。**今後この課題が黙って書き換わることだけを防ぐ。"),
        "answers_at_record": [q.name for q in have],
        "hard": {},
        "soft": {},
    }
    missing = []
    for tier, paths in (("hard", HARD_PATHS), ("soft", SOFT_PATHS)):
        for p in targets(task, paths):
            if not p.exists():
                if mode == "stamp":
                    print(f"**凍結できない。**{p.relative_to(ROOT)} が無い。")
                    return 1
                # 事後記録では拒否しない。**無いことを記録する。**
                # T001-T005 は arms/ を残す前に走っており（論文 §4.2.6）、
                # 拒否すると「記録が無い」状態がそのまま続いてしまう。
                missing.append(str(p.relative_to(ROOT)))
                continue
            doc[tier][str(p.relative_to(ROOT))] = digest(p)
    doc["missing_at_record"] = missing
    doc["arms_prompt_recorded"] = not any(m.startswith("arms/") for m in missing)
    out = ROOT / "tasks" / task / ("FROZEN.json" if mode == "stamp" else "BASELINE.json")
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out.relative_to(ROOT)} に "
          f"硬{len(doc['hard'])}件 / 軟{len(doc['soft'])}件を"
          f"{'凍結した' if mode == 'stamp' else '事後記録した'}。"
          + (f"  ※記録できなかった: {', '.join(missing)}" if missing else ""))
    for tier in ("hard", "soft"):
        for k, v in doc[tier].items():
            print(f"  [{tier}] {k:<38} {v[:16]}")
    return 0


def verify(task: str) -> int:
    d = ROOT / "tasks" / task
    f = next((d / n for n in ("FROZEN.json", "BASELINE.json") if (d / n).exists()), None)
    if f is None:
        print(f"[--] {task}: 記録が無い（--stamp / --baseline で作る）")
        return 0
    doc = json.loads(f.read_text(encoding="utf-8"))
    frozen = f.name == "FROZEN.json"
    label = "凍結" if frozen else "事後記録"
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
        print(f"[OK] {task}: {label}の {n}件は動いていない（答案 {len(have)}本）")
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
    for flag, mode in (("--stamp", "stamp"), ("--baseline", "baseline")):
        if flag in sys.argv:
            if not args:
                print(f"課題を指定すること: python3 -m bench.freeze T006 {flag}")
                return 1
            return sum(record(t, mode) for t in args)
    tasks = args or [d.name for d in sorted((ROOT / "tasks").iterdir()) if d.is_dir()]
    return 1 if sum(verify(t) for t in tasks) else 0


if __name__ == "__main__":
    sys.exit(main())
