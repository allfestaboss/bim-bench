#!/usr/bin/env python3
"""採点器が騙されないかを試す。

参照解から意図的に壊した答案を作り、採点器が落とすことを確認する。
落とせなければ採点器が壊れているので、腕の点数を出してはいけない。

**このベンチで実際に起きた失敗を、そのまま敵対ケースにしてある。**

  evil_depth_naive     空間階層を「建物→階」の2段と決め打ちして深さを1つ浅く数える。
                       こちらが課題文の例で実際にやった誤り。腕2本が指摘した。
  evil_drop_adheres    IFCRELADHERESTOELEMENT の付着要素20件を落とす。
                       armB が実際に落とし、ifcopenshell も解決しない。
  evil_zero_depth      深さ0（IfcProject）を null にする。0 は有効な値である。
  evil_container_null  所属を全て null にする。「載っていない」と「答えていない」の区別。
  evil_quantity_scale  数量を1000倍する。長さが mm、面積が m2 という
                       単位系の不統一を取り違えた場合に出る形。
  evil_malformed       オブジェクト間のカンマ落ち。kikai-bench の armB が実際にこれで壊れた。

使い方: adversarial.py T001
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(task_id: str) -> dict:
    return json.loads((ROOT / "reference" / f"{task_id}.json").read_text(encoding="utf-8"))


def _sub(ref: dict) -> dict:
    return {"task": ref["task"], "results": copy.deepcopy(ref["results"])}


def _each(sub: dict, key: str):
    for r in sub["results"]:
        for t in (r.get(key) or []):
            yield r, t


def evil_drop_file(ref):
    """ファイルを1つ落とす（部分提出）。"""
    s = _sub(ref)
    s["results"] = s["results"][:-1] if len(s["results"]) > 1 else s["results"]
    return s


def evil_invent_elements(ref):
    """要素を捏造して水増しする。"""
    s = _sub(ref)
    r = s["results"][0]
    base = dict((r.get("elements") or [{}])[0])
    for k in range(10):
        fake = dict(base)
        fake["id"] = 900000 + k
        fake["name"] = f"Invented.{k}"
        r.setdefault("elements", []).append(fake)
    return s


def evil_depth_naive(ref):
    """空間の深さを1つ浅く数える。

    「プロジェクト→敷地→建物→階」の4段と決め打ちすると、敷地が敷地に
    入れ子になっている分を見落として全部1つ浅くなる。
    こちらが課題文の例で実際にやった誤りで、腕2本がそれを指摘した。
    """
    s = _sub(ref)
    for _, t in _each(s, "spatials"):
        d = t.get("depth")
        if isinstance(d, int) and d > 0:
            t["depth"] = d - 1
    return s


def evil_zero_depth(ref):
    """深さ0（IfcProject）を null にする。0 は有効な値である。"""
    s = _sub(ref)
    for _, t in _each(s, "spatials"):
        if t.get("depth") == 0:
            t["depth"] = None
    return s


def evil_drop_adheres(ref):
    """付着関係で所属している要素を落とす。

    armB が実際に落とした20件。ifcopenshell の get_container() も
    これを解決しないので、独立実装との突き合わせでは出てこない。
    """
    s = _sub(ref)
    for r in s["results"]:
        r["elements"] = [e for e in (r.get("elements") or [])
                         if e.get("container_via") != "adheres"]
    return s


def evil_container_null(ref):
    """所属を全て null にする。「載っていない」と「答えていない」の区別。"""
    s = _sub(ref)
    for _, t in _each(s, "elements"):
        t["container"] = None
    return s


def evil_container_root(ref):
    """所属を全てプロジェクト直下にする（階層を潰した答案）。"""
    s = _sub(ref)
    for r in s["results"]:
        root = next((x["id"] for x in (r.get("spatials") or []) if x.get("depth") == 0), None)
        for t in (r.get("elements") or []):
            t["container"] = root
    return s


def evil_quantity_scale(ref):
    """数量を1000倍する。長さmm・面積m2 の取り違えで出る形。"""
    s = _sub(ref)
    for _, t in _each(s, "quantities"):
        if isinstance(t.get("value"), (int, float)):
            t["value"] = t["value"] * 1000
    return s


def evil_drop_unit(ref):
    """数量の単位を落とす。値だけでは意味が決まらない。"""
    s = _sub(ref)
    for _, t in _each(s, "quantities"):
        t["unit"] = ""
    return s


def evil_parent_flip(ref):
    """空間の親をプロジェクトに付け替える（階層を平らにした答案）。"""
    s = _sub(ref)
    for r in s["results"]:
        root = next((x["id"] for x in (r.get("spatials") or []) if x.get("depth") == 0), None)
        for t in (r.get("spatials") or []):
            if t.get("depth"):
                t["parent"] = root
    return s


def evil_drop_type_properties(ref):
    """型経由で付いた性能仕様を落とす。

    直接付いたものだけ見ると、床スラブの FireRating は REI30 の1つに見え、
    型経由の REI60 との矛盾が消える。**矛盾が見えなくなること自体が失点**である。
    """
    s = _sub(ref)
    for r in s["results"]:
        r["properties"] = [p for p in (r.get("properties") or []) if p.get("via") != "type"]
    return s


def evil_merge_conflict(ref):
    """食い違う性能仕様を片方の値に揃える（矛盾を握りつぶした答案）。"""
    s = _sub(ref)
    for r in s["results"]:
        first: dict = {}
        for p in (r.get("properties") or []):
            k = (p.get("element"), p.get("pset_name"), p.get("name"))
            if k in first:
                p["value"] = first[k]
            else:
                first[k] = p.get("value")
    return s


def evil_keep_typed_value(ref):
    """属性値を IFCLABEL('REI60') のまま報告する（中身を取り出していない）。"""
    s = _sub(ref)
    for r in s["results"]:
        for p in (r.get("properties") or []):
            if p.get("value"):
                p["value"] = f"IFCLABEL('{p['value']}')"
    return s


def evil_no_anomalies(ref):
    """「異常なし」と書く。照査で最も高くつく答案。"""
    s = _sub(ref)
    for r in s["results"]:
        r["anomalies"] = []
    return s


def evil_flood_anomalies(ref):
    """全部の要素を怪しいと書く。**見落としゼロだが役に立たない。**

    再現率だけで採ると満点になってしまうので、F1 で採っていることの確認。
    """
    s = _sub(ref)
    for r in s["results"]:
        a = list(r.get("anomalies") or [])
        for i in range(30):
            a.append({"kind": "orphan_element", "entities": [900000 + i],
                      "detail": "怪しい"})
        r["anomalies"] = a
    return s


def evil_wrong_kind(ref):
    """欠陥の場所は当てているが、種別を取り違えている。"""
    s = _sub(ref)
    for r in s["results"]:
        for a in (r.get("anomalies") or []):
            a["kind"] = "orphan_element" if a["kind"] != "orphan_element" else "multi_parent"
    return s


def evil_cycle_cascade(ref):
    """循環を、輪に入っている空間ごとに1件ずつ挙げる（同じ壊れ方を水増し）。"""
    s = _sub(ref)
    for r in s["results"]:
        out = []
        for a in (r.get("anomalies") or []):
            if a["kind"] == "aggregation_cycle" and len(a.get("entities") or []) > 1:
                out.extend({"kind": "aggregation_cycle", "entities": [e],
                            "detail": a.get("detail", "")} for e in a["entities"])
            else:
                out.append(a)
        r["anomalies"] = out
    return s


def benign_rounded(ref):
    """有効数字12桁に丸めただけ。これは通ってよい（許容の境界確認）。"""
    s = _sub(ref)
    for _, t in _each(s, "quantities"):
        if isinstance(t.get("value"), float):
            t["value"] = float(f"{t['value']:.12g}")
    return s


def _has(ref, key, pred) -> bool:
    return any(pred(t) for r in ref["results"] for t in (r.get(key) or []))


EVIL = [
    ("evil_drop_file", evil_drop_file, "Q1", lambda r: len(r["results"]) > 1),
    ("evil_invent_elements", evil_invent_elements, "Q3", lambda r: True),
    ("evil_depth_naive", evil_depth_naive, "Q2",
     lambda r: _has(r, "spatials", lambda t: (t.get("depth") or 0) > 0)),
    ("evil_zero_depth", evil_zero_depth, "Q2",
     lambda r: _has(r, "spatials", lambda t: t.get("depth") == 0)),
    ("evil_parent_flip", evil_parent_flip, "Q2",
     lambda r: _has(r, "spatials", lambda t: (t.get("depth") or 0) > 1)),
    ("evil_drop_adheres", evil_drop_adheres, "Q3",
     lambda r: _has(r, "elements", lambda t: t.get("container_via") == "adheres")),
    ("evil_container_null", evil_container_null, "Q4",
     lambda r: _has(r, "elements", lambda t: t.get("container") is not None)),
    ("evil_container_root", evil_container_root, "Q4",
     lambda r: _has(r, "elements", lambda t: t.get("container") is not None)),
    ("evil_quantity_scale", evil_quantity_scale, "Q5",
     lambda r: _has(r, "quantities", lambda t: t.get("value"))),
    ("evil_drop_type_properties", evil_drop_type_properties, "Q6",
     lambda r: any(p.get("via") == "type" for x in r["results"] for p in (x.get("properties") or []))),
    ("evil_merge_conflict", evil_merge_conflict, "Q6",
     lambda r: any(x.get("anomalies") for x in r["results"])),
    ("evil_keep_typed_value", evil_keep_typed_value, "Q6",
     lambda r: any(p.get("value") for x in r["results"] for p in (x.get("properties") or []))),
    ("evil_no_anomalies", evil_no_anomalies, "Q7",
     lambda r: any(x.get("anomalies") for x in r["results"])),
    ("evil_flood_anomalies", evil_flood_anomalies, "Q7", lambda r: True),
    ("evil_wrong_kind", evil_wrong_kind, "Q7",
     lambda r: any(x.get("anomalies") for x in r["results"])),
    ("evil_cycle_cascade", evil_cycle_cascade, "Q7",
     lambda r: any(a["kind"] == "aggregation_cycle" and len(a.get("entities") or []) > 1
                   for x in r["results"] for a in (x.get("anomalies") or []))),
    ("evil_drop_unit", evil_drop_unit, "Q5",
     lambda r: _has(r, "quantities", lambda t: t.get("unit"))),
]


def main() -> int:
    task_id = sys.argv[1] if len(sys.argv) > 1 else "T001"
    ref = _load(task_id)
    out_dir = ROOT / "out"
    out_dir.mkdir(exist_ok=True)
    task = ROOT / "tasks" / task_id / "task.json"
    ref_path = ROOT / "reference" / f"{task_id}.json"

    def score(name: str, payload) -> dict:
        p = out_dir / f"{name}.json"
        if isinstance(payload, str):
            p.write_text(payload, encoding="utf-8")
        else:
            p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(ROOT / "bench" / "check.py"), str(task), str(ref_path), str(p)],
            capture_output=True, text=True)
        return json.loads(r.stdout)[0]

    failures = 0

    base = score(f"_calib_{task_id.lower()}", _sub(ref))
    full = abs(base["score"] - base["max"]) < 1e-9 and not base["fatal"]
    print(f"[{'OK' if full else 'NG'}] 較正: 参照解 {base['score']:.1f}/{base['max']:.0f}")
    if not full:
        for c in base["checks"]:
            if not c["ok"] and c["max"]:
                print(f"       [{c['level']}] {c['name']}: {c['detail'][:200]}")
        failures += 1

    r = score("benign_rounded", benign_rounded(ref))
    ok = abs(r["score"] - r["max"]) < 1e-9
    print(f"[{'OK' if ok else 'NG'}] benign_rounded: {r['score']:.1f}/{r['max']:.0f}  ← 丸めは通るべき")
    if not ok:
        failures += 1

    broken = json.dumps(_sub(ref), ensure_ascii=False, separators=(",", ":"))
    assert "},{" in broken, "壊す対象が見つからない"
    r = score("evil_malformed", broken.replace("},{", "}{", 1))
    ok = bool(r["fatal"]) and r["score"] == 0.0
    print(f"[{'OK' if ok else 'NG'}] evil_malformed: {r['score']:.1f}/{r['max']:.0f}"
          + (f"  失格" if r["fatal"] else "  ← 失格になるべき"))
    if not ok:
        failures += 1

    graded = json.loads(task.read_text(encoding="utf-8")).get("grade_levels")
    ran = 0
    for name, fn, expect, applies in EVIL:
        if graded is not None and expect not in graded:
            print(f"[--] {name}: この課題は {expect} を採点しないので飛ばす")
            continue
        if not applies(ref):
            print(f"[--] {name}: この課題には該当する対象が無いので飛ばす")
            continue
        ran += 1
        r = score(name, fn(ref))
        caught = r["score"] < r["max"] - 1e-9 or r["fatal"]
        lost = [c["level"] for c in r["checks"] if not c["ok"] and c["max"]]
        ok = caught and (expect in lost or r["fatal"])
        print(f"[{'OK' if ok else 'NG'}] {name}: {r['score']:.1f}/{r['max']:.0f}"
              f"  失点={sorted(set(lost)) or '無し'}  期待={expect}")
        if not ok:
            failures += 1

    total = ran + 3
    print()
    print(f"敵対テスト: {total - failures}/{total} 通過")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
