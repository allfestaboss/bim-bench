#!/usr/bin/env bash
# 使い方: ./run.sh [T001 ...]   引数なしで全課題
#
# 採点の前に必ず (1)較正 (2)外部検算 (3)敵対テスト を通す。
# どれか落ちたら数字を出さない。
# 外部検算は ifcopenshell を使うので .venv があればそちらで走らせる。
set -euo pipefail
cd "$(dirname "$0")"
PY=python3
VPY=".venv/bin/python"; [ -x "$VPY" ] || VPY="$PY"
TASKS=("$@")
if [ ${#TASKS[@]} -eq 0 ]; then
  TASKS=(); for d in tasks/*/; do TASKS+=("$(basename "$d")"); done
fi
mkdir -p out

for T in "${TASKS[@]}"; do
  # T004 は「決まらない箇所」の課題。参照解の作り方が違う。
  if [ "$T" = "T005" ]; then $PY -m bench.counts >/dev/null
  elif [ "$T" = "T004" ]; then $PY -m bench.ambiguity >/dev/null
  else $PY -m bench.build_ref "$T" >/dev/null; fi
done

$PY -m bench.selfcheck > out/_selfcheck.txt || {
  echo "較正に失敗。out/_selfcheck.txt を見ること。"; exit 1; }
echo "較正OK: $(grep '較正:' out/_selfcheck.txt)"

if "$VPY" -c "import ifcopenshell" 2>/dev/null; then
  "$VPY" -m bench.crosscheck > out/_crosscheck.txt || {
    echo "外部検算に失敗。out/_crosscheck.txt を見ること。"; exit 1; }
  echo "外部検算OK: $(grep '突き合わせ:' out/_crosscheck.txt)"
else
  echo "外部検算: ifcopenshell が無いので飛ばした（.venv を作ること）"
fi

for T in "${TASKS[@]}"; do
  ADV=checker/adversarial.py
  [ "$T" = "T004" ] && ADV=checker/adversarial_ambiguity.py
  [ "$T" = "T005" ] && ADV=checker/adversarial_counts.py
  $PY "$ADV" "$T" > "out/${T}_adversarial.txt" || {
    echo "敵対テストに失敗。out/${T}_adversarial.txt を見ること。"; exit 1; }
  echo "敵対OK($T): $(grep -c '^\[OK' "out/${T}_adversarial.txt") ケース"

  FILES=("out/_calib_$(echo "$T" | tr 'A-Z' 'a-z').json")
  for f in attempts/$T/*.json; do
    case "$(basename "$f")" in cost.json) continue ;; esac
    [ -e "$f" ] && FILES+=("$f")
  done
  $PY bench/check.py "tasks/$T/task.json" "reference/$T.json" "${FILES[@]}" > "out/${T}.json"
  $PY -m bench.summary "$T"
done
echo
echo "詳細: out/<TASK>.json  敵対: out/<TASK>_adversarial.txt"
