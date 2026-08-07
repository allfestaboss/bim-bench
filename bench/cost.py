"""腕のコストを扱う。

点数と並べてトークン数と所要時間を出す。jiban-bench でも kikai-bench でも、
腕が揃って満点になることがあり、そのとき点数はもう軸を映していない。
実務に効く差は単価と到達範囲のほうに出る。

測定値は attempts/<TASK>/cost.json に置く。形は:

    {
      "_meta": {"round": 2, "note": "..."},
      "armA": {"tokens": 205973, "duration_ms": 882162, "tool_uses": 16}
    }

この数字は腕を走らせた側が記録する。ベンチが自分で測れるものではないので、
無ければ表では "-" になるだけで、採点は通る。
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Cost:
    tokens: int | None = None
    duration_ms: int | None = None
    tool_uses: int | None = None

    @property
    def seconds(self) -> float | None:
        return None if self.duration_ms is None else self.duration_ms / 1000

    def per_unit(self, units: int) -> float | None:
        """仕事量1単位あたりのトークン。units は幾何公差の件数。"""
        if self.tokens is None or not units:
            return None
        return self.tokens / units


def load(task_id: str) -> dict[str, Cost]:
    path = ROOT / "attempts" / task_id / "cost.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        k: Cost(**{f: v.get(f) for f in ("tokens", "duration_ms", "tool_uses")})
        for k, v in raw.items()
        if not k.startswith("_")
    }


def meta(task_id: str) -> dict:
    path = ROOT / "attempts" / task_id / "cost.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("_meta", {})


def workload(task_id: str) -> dict[str, int]:
    """課題の仕事量。参照解から数える。"""
    ref_path = ROOT / "reference" / f"{task_id}.json"
    if not ref_path.exists():
        return {"files": 0, "tolerances": 0, "datums": 0}
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    s = ref.get("summary", {})
    return {
        "files": s.get("n_file", len(ref.get("results", []))),
        "tolerances": s.get("n_tolerance", 0),
        "datums": s.get("n_datum", 0),
    }


def fmt_seconds(sec: float | None) -> str:
    if sec is None:
        return "-"
    m, s = divmod(int(round(sec)), 60)
    return f"{m}分{s:02d}秒" if m else f"{s}秒"


def fmt_tokens(tok: int | None) -> str:
    if tok is None:
        return "-"
    if tok >= 10000:
        return f"{tok / 1000:.0f}k"
    return f"{tok / 1000:.1f}k"


def width(s: str) -> int:
    """端末上の表示幅。全角は2で数える。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def ljust(s: str, w: int) -> str:
    return s + " " * max(0, w - width(s))


def rjust(s: str, w: int) -> str:
    return " " * max(0, w - width(s)) + s
