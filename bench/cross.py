"""同じパーサで、土木・機械・建築の3業界を読む。

    python3 -m bench.cross [土木のP21ディレクトリ] [機械のSTEPディレクトリ]

CAD横断シリーズは「業界ごとに形式が違う」という前提で始めた。**それは誤りだった。**

    土木  SXF (P21形式)  = ISO 10303-21 / AP202 ASSOCIATIVE_DRAUGHTING
    機械  STEP AP242     = ISO 10303-21 / AP242
    建築  IFC            = ISO 10303-21 / IFC4, IFC4X3

3つとも同じ器に入っている。これを主張ではなく実証にするため、
**bim-bench が IFC のために書いたパーサ（bench/step.py）を1文字も変えずに**
他2業界のファイルへ当てる。読めれば、器が同じであることの証明になる。

同時に語彙の重なりを数える。器が同じでも語彙が重ならないなら、
業界の壁は形式ではなく別のところにある——それが何かも、数えれば出る。

他リポのデータを参照するので、隣に置かれている前提で既定パスを引く。
無ければ引数で渡す。
"""

from __future__ import annotations

import sys
from pathlib import Path

from .step import load

ROOT = Path(__file__).resolve().parent.parent

# (表示名, 既定パス, 拡張子)
INDUSTRIES = [
    ("土木 SXF-P21", ROOT.parent / "doboku-bench" / "samples", ("*.P21", "*.p21")),
    ("機械 STEP AP242", ROOT.parent / "kikai-bench" / "corpus", ("*.stp", "*.step")),
    ("建築 IFC", ROOT / "corpus" / "buildingsmart", ("*.ifc",)),
]


def _concept(t: str) -> str:
    """型名から業界ごとの飾りを落として、概念名だけにする。

    IFC は全ての型に IFC を付け、下線を使わない。AP202/AP242 は付けず下線を使う。
    `IFCCARTESIANPOINT` と `CARTESIAN_POINT` は**同じ概念の別名**である。
    """
    x = t[3:] if t.startswith("IFC") else t
    return x.replace("_", "")


def scan(path: Path, globs) -> tuple[list[Path], set[str], int, set[str]]:
    files: list[Path] = []
    for g in globs:
        files.extend(sorted(path.rglob(g)))
    kinds: set[str] = set()
    schemas: set[str] = set()
    n = 0
    for f in sorted(set(files)):
        m = load(f)
        kinds |= {e.type for e in m.entities.values()}
        schemas.add((m.schema or "").split("{")[0].strip())
        n += len(m.entities)
    return sorted(set(files)), kinds, n, schemas


def main() -> int:
    args = sys.argv[1:]
    spec = list(INDUSTRIES)
    for i, a in enumerate(args[:2]):
        spec[i] = (spec[i][0], Path(a), spec[i][2])

    print("=== 同じパーサ（bench/step.py、IFC のために書いたもの）で3業界を読む ===")
    print()
    vocab: dict[str, set[str]] = {}
    total = 0
    missing = []
    for name, path, globs in spec:
        if not path.exists():
            missing.append(f"{name}: {path} が無い")
            continue
        files, kinds, n, schemas = scan(path, globs)
        if not files:
            missing.append(f"{name}: {path} に対象ファイルが無い")
            continue
        vocab[name] = kinds
        total += n
        print(f"  {name}")
        print(f"      ファイル {len(files):>2}本 / 実体 {n:>7,}件 / 型 {len(kinds):>3}種")
        print(f"      schema  {', '.join(sorted(s for s in schemas if s))[:70]}")
    for m in missing:
        print(f"  [飛ばした] {m}")
    if len(vocab) < 2:
        print("\n2業界そろわないので比較できない。パスを引数で渡すこと。")
        return 2

    print()
    print(f"  **1つのパーサが、{len(vocab)}業界・実体 {total:,}件を読んだ。**")
    print()
    print("=== 語彙は重なるか ===")
    names = list(vocab)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = vocab[names[i]], vocab[names[j]]
            ca = {_concept(x) for x in a}
            cb = {_concept(x) for x in b}
            print(f"  {names[i]:<16} ∩ {names[j]:<16}"
                  f"  型名で {len(a & b):>3}種 / 概念で {len(ca & cb):>3}種")
    all_named = set.intersection(*vocab.values())
    all_concept = set.intersection(*({_concept(x) for x in v} for v in vocab.values()))
    print()
    print(f"  全業界に共通する**型名**   : {len(all_named)}種 {sorted(all_named)[:6]}")
    print(f"  全業界に共通する**概念**   : {len(all_concept)}種 {sorted(all_concept)}")

    if all_concept and not all_named:
        print()
        print("  型名では1つも重ならないのに、概念では重なる。**違うのは名前だけ。**")
        print()
        for c in sorted(all_concept)[:5]:
            row = []
            for nm in names:
                hit = [t for t in vocab[nm] if _concept(t) == c]
                row.append(f"{nm.split()[0]}={hit[0] if hit else '—'}")
            print("      " + "  ".join(row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
