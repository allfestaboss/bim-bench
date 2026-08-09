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

**`_env` は後から復元できない。** どのモデルで測ったのかを書かずに走らせると、
トークン数だけが残って比較に使えなくなる。`require_env()` は `_env` が無ければ
例外を投げる。コストを表に出す経路はこれを通すこと。
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

# _env に必ず入っていてほしい項目。source は recorded / reconstructed のどちらか。
ENV_FIELDS = ("model", "sampling", "harness", "run_date", "source")


def env(task_id: str) -> dict:
    path = ROOT / "attempts" / task_id / "cost.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("_env", {})


def require_env(task_id: str) -> dict:
    """コストを報告してよいかを判定する。

    測定環境が書かれていないコストは、単位の無い数値と同じで比較に使えない。
    足りない項目を並べて落とす。黙って "-" にはしない —— 欠測と未記録は別物で、
    後者は測り直せば直るのに、表の上では見分けがつかなくなる。
    """
    e = env(task_id)
    if not e:
        raise ValueError(
            f"{task_id}: cost.json に _env が無い。どのモデルで測ったか記録されていない。\n"
            f"  必要な項目: {', '.join(ENV_FIELDS)}\n"
            f"  事後に思い出して書くなら source を 'reconstructed' にすること。"
        )
    missing = [f for f in ENV_FIELDS if not e.get(f)]
    if missing:
        raise ValueError(f"{task_id}: _env に不足がある: {', '.join(missing)}")
    if e["source"] not in ("recorded", "reconstructed"):
        raise ValueError(
            f"{task_id}: _env.source は recorded か reconstructed。"
            f"実際の値: {e['source']!r}"
        )
    return e




def workload(task_id: str) -> dict[str, int]:
    """課題の仕事量。参照解から数える。"""
    ref_path = ROOT / "reference" / f"{task_id}.json"
    if not ref_path.exists():
        return {"files": 0, "tolerances": 0, "spatials": 0,
                "quantities": 0, "properties": 0, "anomalies": 0}
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    if "sites" in ref:  # 「決まらない箇所」の課題は形が違う
        return {"files": 0, "tolerances": len(ref["sites"]), "spatials": 0,
                "quantities": 0, "properties": 0, "anomalies": 0}
    s = ref.get("summary", {})
    return {
        "files": s.get("n_file", len(ref.get("results", []))),
        "tolerances": s.get("n_element", 0),   # 単価の分母は要素数
        "spatials": s.get("n_spatial", 0),
        "quantities": s.get("n_quantity", 0),
        "properties": s.get("n_property", 0),
        "anomalies": s.get("n_anomaly", 0),
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
