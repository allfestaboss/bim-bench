"""タスクから参照解を生成する。

    python -m bench.build_ref T001
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

from .ifc import extract
from .step import load

ROOT = Path(__file__).resolve().parent.parent


def build(task_id: str) -> dict:
    task = json.loads((ROOT / "tasks" / task_id / "task.json").read_text(encoding="utf-8"))
    results = []
    for f in task["files"]:
        x = extract(load(ROOT / f["path"]))
        results.append({
            "file": str(Path(f["path"]).relative_to("corpus/buildingsmart")),
            "schema": x.schema,
            "spatials": [dataclasses.asdict(s) for s in x.spatials],
            "elements": [dataclasses.asdict(e) for e in x.elements],
            "quantities": [dataclasses.asdict(q) for q in x.quantities],
            "anomalies": x.anomalies,
            "counts": x.counts(),
            "spatial_counts": x.spatial_counts(),
        })
    return {
        "task": task_id,
        "standard": "ISO 16739 (IFC) / ISO 10303-21",
        "results": results,
        "summary": {
            "n_file": len(results),
            "n_spatial": sum(len(r["spatials"]) for r in results),
            "n_element": sum(len(r["elements"]) for r in results),
            "n_quantity": sum(len(r["quantities"]) for r in results),
        },
    }


def main() -> int:
    task_id = sys.argv[1] if len(sys.argv) > 1 else "T001"
    ref = build(task_id)
    out = ROOT / "reference" / f"{task_id}.json"
    out.write_text(json.dumps(ref, ensure_ascii=False, indent=1), encoding="utf-8")
    s = ref["summary"]
    print(f"{out.relative_to(ROOT)}: {s['n_file']}ファイル / 空間 {s['n_spatial']} / "
          f"要素 {s['n_element']} / 数量 {s['n_quantity']}")
    for r in ref["results"]:
        print(f"    {r['file']:<28} 空間{len(r['spatials']):>3} 要素{len(r['elements']):>3} "
              f"数量{len(r['quantities']):>3}  {r['schema']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
