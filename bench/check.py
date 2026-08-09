#!/usr/bin/env python3
"""IFC 読解の機械採点器。参照解だけを真として採点する。

  Q0 形式（JSONとして読めるか・ファイルが揃っているか）  ※失格判定のみ、配点なし
  Q1 空間の網羅（取りこぼしと捏造の両方）                15点
  Q2 空間の親と深さ                                    20点
  Q3 要素の網羅（取りこぼしと捏造の両方）                20点
  Q4 要素の所属                                        25点
  Q5 数量（値と単位）                                   17点
  Q6 性能仕様（Pset名・属性名・値・付き方）               17点
  Q7 欠陥の指摘（種別と実体番号）                        25点
  Q8 規格が2通りに読める箇所への気づき（実体集合）        40点
  Q9 その選択で何件動くかの計算                          60点

**Q4 が最も重い。** 「どの要素がどの空間に載っているか」は、国交省の BIM/CIM 照査で
人が Word のチェックシートを見ながら確認している当のものだからである。
このベンチが測る意味の中心がそこにある。

この採点器を書くまでに実際に踏んだ罠を、そのまま設計に入れてある。

  * **0 は有効な値である。** 深さ 0 は IfcProject（階層の根）、
    数量 0.0 もありうる。`x or -1` のような falsy 既定値を書くと化ける。
    kikai-bench で最大実体公差方式のゼロ位置度を取り違えた。
  * **所属が無いことと、答えていないことは違う。** container が None なのは
    「空間に載っていない」という答えであって、欠測ではない。区別する。
  * 手書きの答案は JSON として壊れる（kikai-bench の armB の実例）。壊れた提出は失格。
  * 部分提出は実際に出る。未提出のファイルはその分を0点にし、提出済みは正しく採点する。
  * 網羅は F1。20件しか読めない答案と、8件でっち上げて水増しした答案を同点にしない。

使い方: check.py <task.json> <reference.json> <submission.json ...>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

REL_TOL = 1e-9
ABS_FLOOR = 1e-12

POINTS = {"Q1": 12.0, "Q2": 16.0, "Q3": 16.0, "Q4": 22.0, "Q5": 17.0, "Q6": 17.0,
          "Q7": 25.0, "Q8": 40.0, "Q9": 60.0}
LEVEL_NAME = {
    "Q1": "空間の網羅",
    "Q2": "空間の親と深さ",
    "Q3": "要素の網羅",
    "Q4": "要素の所属",
    "Q5": "数量（値と単位）",
    "Q6": "性能仕様",
    "Q7": "欠陥の指摘",
    "Q8": "分かれ目への気づき",
    "Q9": "影響の計算",
}

MISSING = object()  # 「答えていない」を None（＝所属なし）と区別するための番兵


def num(v) -> float | None:
    """数値に正規化する。**0 を falsy で潰さない。**"""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def close(got, want) -> bool:
    g, w = num(got), num(want)
    if g is None or w is None:
        return g is None and w is None
    return abs(g - w) <= max(abs(w) * REL_TOL, ABS_FLOOR)


def _ref_or_none(v):
    """実体参照。None は「所属なし」という答えで、欠測ではない。"""
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return MISSING


def _val(v) -> str:
    """性能仕様の値を比べる形にそろえる。

    Part21 は 45. と書き、JSON の数値として 45.0 と書く答案もある。**同じ数である。**
    単位名の点を落として比べるのと同じ理屈で、書式の差は読み取り能力の差ではない。
    """
    if isinstance(v, bool):
        return ".T." if v else ".F."
    s = "" if v is None else str(v).strip()
    try:
        return repr(float(s))
    except ValueError:
        return s


def _f1(hit: int, want: int, extra: int) -> float:
    recall = hit / want if want else 0.0
    precision = hit / (hit + extra) if (hit + extra) else 0.0
    return (2 * recall * precision / (recall + precision)) if (recall + precision) else 0.0


def _files(doc: dict) -> dict[str, dict]:
    """答案・参照解をファイル名で引けるようにする。

    同じ基底名が複数のスキーマ版に存在する（ifc4/Building-Architecture.ifc と
    ifc4x3/Building-Architecture.ifc）。基底名で引くと衝突するので相対パスで持つ。

    ただし**衝突が無いなら基底名でも引けるようにする。** T001 は corpus が
    ifc4x3 だけだった頃の課題で、当時はディレクトリ名を要求していなかった。
    後から ifc4/ を足して参照解側の名前を変えたせいで、こちらの都合で
    古い答案が全問0点になっていた。**腕の答案は当時の課題文に対して正しい。**
    """
    out: dict[str, dict] = {}
    base: dict[str, list[dict]] = {}
    for r in doc.get("results") or []:
        name = str(r.get("file", "")).strip().lstrip("./")
        if not name:
            continue
        out[name] = r
        base.setdefault(name.rsplit("/", 1)[-1], []).append(r)
    for b, rows in base.items():
        if len(rows) == 1 and b not in out:
            out[b] = rows[0]
    return out


def _index(rec: dict | None, key: str) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for t in ((rec or {}).get(key) or []):
        try:
            out[int(t["id"])] = t
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _ents(t) -> frozenset:
    out = set()
    for e in (t.get("entities") or []):
        try:
            out.add(int(e))
        except (TypeError, ValueError):
            pass
    return frozenset(out)


def grade_ambiguity(ref_doc: dict, sub_doc: dict, levels: list[str] | None = None) -> dict:
    """「決まらない箇所」の課題を採点する。

    **語彙で照合しない。** こちらが site の名前を課題文に並べれば、腕はそれを
    引き写すだけになり、気づいたかを測ったことにならない。名前は自由に書かせ、
    **実体番号の集合の重なり**で対応を取る。集合は客観的で、共通語彙が要らない。

    Q8 気づき   参照側の各箇所について、最もよく重なる答案の項目との Jaccard。
                拾えないのと、無い箇所をでっち上げるのを F1 で同じだけ嫌う。
    Q9 影響     対応が取れた箇所について、もう一方の読み方を採ったときの行数が
                合っているか。**「曖昧だ」と言うのは安い。「322件になる」は
                両方の読み方を実際に適用しないと言えない。** ここが分離点。
    """
    active = [l for l in ("Q8", "Q9") if levels is None or l in levels]
    ref_sites = ref_doc.get("sites") or []
    sub_sites = [t for t in (sub_doc.get("sites") or []) if isinstance(t, dict)]

    checks: list[dict] = []
    fatal = None if sub_sites else "sites が無いか、形が違う"

    # **Jaccard では採らない。** 参照側は要素番号だけを挙げ、答案は型や Pset まで
    # 挙げる——どちらも「扱いが変わる実体を全部」という規則を満たす。
    # 粒度の流儀で減点すると、読解でなく書き方の癖を測ることになる。
    # 参照側の実体をどれだけ覆えたか（包含）で採る。
    pairs: list[tuple[dict, dict | None, float]] = []
    used: set[int] = set()
    for r in ref_sites:
        rs = _ents(r)
        best, best_c, best_i = None, 0.0, -1
        for i, t in enumerate(sub_sites):
            if i in used:
                continue
            cov = len(rs & _ents(t)) / len(rs) if rs else 0.0
            if cov > best_c:
                best, best_c, best_i = t, cov, i
        if best_i >= 0:
            used.add(best_i)
        pairs.append((r, best, best_c))

    if "Q8" in active:
        recall = sum(j for _, _, j in pairs) / len(ref_sites) if ref_sites else 0.0
        # **参照解に無い箇所を挙げたことは咎めない。** こちらの4箇所は
        # 「2実装が実際に食い違う」に絞った下限であって、上限ではない。
        # 落とすのは実在しない実体を並べた箇所だけ。
        real = set(ref_doc.get("real_ids") or [])
        bogus = [t for t in sub_sites
                 if real and _ents(t) and not (_ents(t) & real)]
        precision = 1.0 - len(bogus) / len(sub_sites) if sub_sites else 0.0
        f1 = (2 * recall * precision / (recall + precision)) if (recall + precision) else 0.0
        miss = [r["id"] for r, _, j in pairs if j == 0.0]
        matched = len(sub_sites) - len(bogus)
        checks.append({
            "level": "Q8", "name": LEVEL_NAME["Q8"],
            "ok": abs(f1 - 1.0) < 1e-9, "points": POINTS["Q8"] * f1, "max": POINTS["Q8"],
            "detail": ("OK" if abs(f1 - 1.0) < 1e-9 else
                       f"覆えた割合 {recall:.2f} / 実在する箇所の割合 {precision:.2f}"
                       + (f"  気づいていない: {miss}" if miss else "")
                       + (f"  実在しない実体を挙げた箇所 {len(bogus)}件" if bogus else "")),
        })

    if "Q9" in active:
        good, bad = 0.0, []
        for r, t, j in pairs:
            if t is None or j == 0.0:
                bad.append(f"{r['id']}(気づいていない)")
                continue
            # **何を数えるかは腕が選んでよい**（規則がそう書いてある）。
            # こちらが「深さ0の空間」を数え、腕が「空間」を数えるのは、どちらも正しい。
            # 咎めるべきはそこではないので、次の2点だけを見る。
            #   1. count_a が**コーパスから実際に数えられる値**か
            #      228 や 629 や 324 は17ファイルを最後まで数えないと出てこない
            #   2. 差が、その箇所で扱いが変わる実体の数と合っているか
            a, b = num(t.get("count_a")), num(t.get("count_b"))
            totals = set(ref_doc.get("totals") or [])
            # **実体番号は集合にすると潰れる。** #13 は17ファイル全部の IFCPROJECT で、
            # 集合にすると1件になってしまう。armC が「番号だけでは箇所が一意に
            # 決まらない」と指摘した箇所そのもの。件数は参照側が持っている値を使う。
            n = int(r.get("affected") or len(_ents(r)))
            # **どちらの読みを a と呼ぶかは規則で決めていない。**
            # こちらは「含める」側を a にしたが、腕が「統合する」側を a に置くのも
            # 規則に反しない。実際 armC が 322->324 と書いてきた（こちらは 324->322）。
            # 順番で減点すると、読解ではなく並べ方の癖を測ることになる。
            # **どちらかがコーパスから実際に数えられる値であればよい**とする。
            base_ok = (a is not None and int(a) in totals) or \
                      (b is not None and int(b) in totals)
            delta_ok = a is not None and b is not None and abs(a - b) == n
            if base_ok and delta_ok:
                good += 1.0
            else:
                why = []
                if not base_ok:
                    why.append(f"count_a={a} / count_b={b} のどちらも実際には数えられない値")
                if not delta_ok:
                    why.append(f"差が {abs(a - b) if a is not None and b is not None else '?'}"
                               f" で、扱いが変わる実体 {n}件と合わない")
                bad.append(f"{r['id']}({' / '.join(why)})")
        score = good / len(ref_sites) if ref_sites else 0.0
        checks.append({
            "level": "Q9", "name": LEVEL_NAME["Q9"],
            "ok": abs(score - 1.0) < 1e-9, "points": POINTS["Q9"] * score,
            "max": POINTS["Q9"],
            "detail": "OK" if not bad else " / ".join(bad[:4]),
        })

    total = 0.0 if fatal else sum(c["points"] for c in checks)
    mx = sum(POINTS[l] for l in active)
    if mx and abs(mx - 100.0) > 1e-9:
        total = total * 100.0 / mx
    return {"file": sub_doc.get("_file", "?"), "score": total, "max": 100.0,
            "fatal": fatal, "checks": checks}


def grade(ref_doc: dict, sub_doc: dict, levels: list[str] | None = None) -> dict:
    active = [l for l in POINTS if levels is None or l in levels]
    ref_files = _files(ref_doc)
    sub_files = _files(sub_doc)

    checks: list[dict] = []
    fatal = None if sub_files else "results が無いか、file 名が付いていない"

    def _pick(fname: str) -> dict | None:
        return sub_files.get(fname) or sub_files.get(fname.rsplit("/", 1)[-1])

    missing_files = [f for f in ref_files if _pick(f) is None]
    checks.append({
        "level": "Q0", "name": "対象ファイルが揃っている",
        "ok": not missing_files, "points": 0.0, "max": 0.0,
        "detail": "OK" if not missing_files else f"未提出 {len(missing_files)}件: {missing_files}",
    })

    tally = {k: [0.0, 0.0] for k in active}
    details: dict[str, list[str]] = {k: [] for k in active}

    for fname, ref_rec in ref_files.items():
        if "/" not in fname and fname.rsplit("/", 1)[-1] in ref_files and \
                any("/" in k for k in ref_files):
            continue  # 基底名の別名は二重に採点しない
        sub_rec = _pick(fname)
        rs, ss = _index(ref_rec, "spatials"), _index(sub_rec, "spatials")
        re_, se = _index(ref_rec, "elements"), _index(sub_rec, "elements")
        rq, sq = _index(ref_rec, "quantities"), _index(sub_rec, "quantities")
        # 性能仕様は同じ属性実体が複数の要素に付くので id では引けない。
        # (要素, Pset名, 属性名, 付き方) を鍵にする。
        def _pkey(t):
            return (t.get("element"), str(t.get("pset_name") or ""),
                    str(t.get("name") or ""), str(t.get("via") or ""))
        rp = {_pkey(t): t for t in (ref_rec.get("properties") or [])}
        sp = {_pkey(t): t for t in ((sub_rec or {}).get("properties") or [])}

        # ---- Q1 / Q3 網羅 ----
        for level, r_idx, s_idx, what in (("Q1", rs, ss, "空間"), ("Q3", re_, se, "要素")):
            if level not in active or not r_idx:
                continue
            hit = len(set(r_idx) & set(s_idx))
            extra = len(set(s_idx) - set(r_idx))
            f1 = _f1(hit, len(r_idx), extra)
            tally[level][0] += f1
            tally[level][1] += 1
            if f1 < 1.0:
                details[level].append(
                    f"{fname}: {what} 一致{hit}/{len(r_idx)}"
                    + (f" 捏造{extra}件" if extra else "")
                    + (" 未提出" if sub_rec is None else ""))

        # ---- Q2 空間の親と深さ ----
        if "Q2" in active and rs:
            good, bad = 0, []
            for i, r in rs.items():
                s = ss.get(i)
                if s is None:
                    bad.append(f"#{i}(未提出)")
                    continue
                p_ok = _ref_or_none(s.get("parent")) == _ref_or_none(r.get("parent"))
                d_ok = num(s.get("depth")) is not None and num(s.get("depth")) == num(r.get("depth"))
                if p_ok and d_ok:
                    good += 1
                else:
                    bad.append(f"#{i}" + ("(親)" if not p_ok else "") + ("(深さ)" if not d_ok else ""))
            tally["Q2"][0] += good
            tally["Q2"][1] += len(rs)
            if bad:
                details["Q2"].append(f"{fname}: {good}/{len(rs)}  誤り {', '.join(bad[:6])}"
                                     + (" …" if len(bad) > 6 else ""))

        # ---- Q4 要素の所属 ----
        if "Q4" in active and re_:
            good, bad = 0, []
            for i, r in re_.items():
                s = se.get(i)
                if s is None:
                    bad.append(f"#{i}(未提出)")
                    continue
                # container が無い（None）のと、キー自体が無いのは別。
                got = _ref_or_none(s.get("container")) if "container" in s else MISSING
                if got is not MISSING and got == _ref_or_none(r.get("container")):
                    good += 1
                else:
                    bad.append(f"#{i}")
            tally["Q4"][0] += good
            tally["Q4"][1] += len(re_)
            if bad:
                details["Q4"].append(f"{fname}: {good}/{len(re_)}  誤り {', '.join(bad[:6])}"
                                     + (" …" if len(bad) > 6 else ""))

        # ---- Q6 性能仕様 ----
        if "Q6" in active and rp:
            good, bad = 0, []
            for k, r in rp.items():
                t = sp.get(k)
                if t is None:
                    bad.append(f"{k[1]}/{k[2]}(未提出)")
                elif _val(t.get("value")) == _val(r.get("value")):
                    good += 1
                else:
                    bad.append(f"{k[1]}/{k[2]}(値)")
            extra = len(set(sp) - set(rp))
            # 捏造も減点する。網羅と同じ扱い。
            score = good / (len(rp) + extra) if (len(rp) + extra) else 0.0
            tally["Q6"][0] += score * len(rp)
            tally["Q6"][1] += len(rp)
            if bad or extra:
                details["Q6"].append(
                    f"{fname}: {good}/{len(rp)}"
                    + (f" 捏造{extra}件" if extra else "")
                    + (f"  誤り {', '.join(bad[:5])}" if bad else ""))

        # ---- Q7 欠陥の指摘 ----
        # 自由文では機械採点できないので (種別, 実体番号の組) を鍵にする。
        # **F1 で採る。** 拾えないのと、無いものを挙げるのを、同じだけ嫌う。
        # 照査で「異常なし」と書くのと「全部が異常」と書くのは、どちらも役に立たない。
        if "Q7" in active:
            def _akey(t):
                ents = t.get("entities")
                ents = ents if isinstance(ents, list) else []
                out = []
                for e in ents:
                    try:
                        out.append(int(e))
                    except (TypeError, ValueError):
                        pass
                return (str(t.get("kind") or "").strip().lower(), tuple(sorted(out)))
            ra = {_akey(t) for t in (ref_rec.get("anomalies") or [])}
            # kind 'other' は語彙に無い壊れ方の受け皿で、課題文が「採点対象外だが読む」と
            # 約束している。**約束した以上、誤指摘として数えてはいけない。**
            # 実際にこれで armC が減点された。語彙に無い欠陥を正直に挙げたほうが
            # 損をする採点器は、正直さを罰している。
            sa = {_akey(t) for t in ((sub_rec or {}).get("anomalies") or [])
                  if str(t.get("kind") or "").strip().lower() != "other"}
            hit = len(ra & sa)
            extra = len(sa - ra)
            # 欠陥が無いファイルは、何も挙げなければ満点。挙げたら減点。
            if not ra:
                f1 = 0.0 if extra else 1.0
            else:
                f1 = _f1(hit, len(ra), extra)
            tally["Q7"][0] += f1
            tally["Q7"][1] += 1
            if f1 < 1.0:
                miss = sorted(ra - sa)
                inv = sorted(sa - ra)
                details["Q7"].append(
                    f"{fname}: {hit}/{len(ra)}"
                    + (f" 見落とし {miss[:3]}" if miss else "")
                    + (f" 誤指摘 {inv[:3]}" if inv else ""))

        # ---- Q5 数量 ----
        if "Q5" in active and rq:
            good, bad = 0, []
            for i, r in rq.items():
                s = sq.get(i)
                if s is None:
                    bad.append(f"#{i}(未提出)")
                    continue
                v_ok = close(s.get("value"), r.get("value"))
                # 単位は答案が出していれば見る。出していなければ値だけで判定しない。
                u_want = str(r.get("unit") or "")
                u_got = str(s.get("unit") or "")
                # 単位名の区切りは書式の問題であって読み取り能力の差ではない。
                # こちらは接頭語と名前を '.' で繋いで MILLI.METRE と持つが、
                # MILLIMETRE と書くのも同じ意味。点を全部落として比べる。
                u_ok = (not u_want) or (
                    u_got.replace(".", "").upper() == u_want.replace(".", "").upper())
                e_ok = _ref_or_none(s.get("element")) == _ref_or_none(r.get("element"))
                if v_ok and u_ok and e_ok:
                    good += 1
                else:
                    bad.append(f"#{i}" + ("(値)" if not v_ok else "")
                               + ("(単位)" if not u_ok else "") + ("(要素)" if not e_ok else ""))
            tally["Q5"][0] += good
            tally["Q5"][1] += len(rq)
            if bad:
                details["Q5"].append(f"{fname}: {good}/{len(rq)}  誤り {', '.join(bad[:6])}"
                                     + (" …" if len(bad) > 6 else ""))

    for level, (got, mx) in tally.items():
        checks.append({
            "level": level, "name": LEVEL_NAME[level],
            "ok": mx > 0 and abs(got - mx) < 1e-9,
            "points": POINTS[level] * (got / mx) if mx else 0.0,
            "max": POINTS[level],
            "detail": " / ".join(details[level]) if details[level] else "OK",
        })

    score = 0.0 if fatal else sum(c["points"] for c in checks)
    total_max = sum(POINTS[l] for l in active)
    if total_max and abs(total_max - 100.0) > 1e-9:
        score = score * 100.0 / total_max
    return {"file": sub_doc.get("_file", "?"), "score": score, "max": 100.0,
            "fatal": fatal, "checks": checks}


def main() -> int:
    task_path, ref_path, *subs = sys.argv[1:]
    task = json.loads(Path(task_path).read_text(encoding="utf-8"))
    levels = task.get("grade_levels")
    ref = json.loads(Path(ref_path).read_text(encoding="utf-8"))
    out = []
    for s in subs:
        try:
            sub = json.loads(Path(s).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            out.append({"file": s, "score": 0.0, "max": 100.0,
                        "fatal": f"JSONとして読めない: {e}", "checks": []})
            continue
        sub["_file"] = s
        # 「決まらない箇所」の課題は形が違うので採点器を分ける。
        if "sites" in ref:
            out.append(grade_ambiguity(ref, sub, levels))
        else:
            out.append(grade(ref, sub, levels))
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
