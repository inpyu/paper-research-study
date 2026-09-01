#!/usr/bin/env bash
# cron 진입점. 중복 실행을 막고, 전체에 타임아웃을 걸고, 로그를 남긴다.
#   crontab:  0 6 * * * /home/cau/paper-research-study/routine/routine.sh
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/logs/routine.log"
mkdir -p "$ROOT/logs"

exec 9>"$ROOT/logs/.lock"
flock -n 9 || { echo "$(date -Is) 이미 실행 중 — 건너뜀" >>"$LOG"; exit 0; }

run() {
  echo "--- $(date -Is) $*" >>"$LOG"
  timeout 300 "$@" >>"$LOG" 2>&1 || { echo "실패($?): $*" >>"$LOG"; return 1; }
}

{
  echo "=== $(date -Is) 루틴 시작"
  # 0. 대상 레포 갱신
  git -C "${TARGET_REPO:-$HOME/work/prefill-opt}" pull --ff-only -q || echo "pull 실패(계속)"
  PY="$ROOT/.venv/bin/python3"; [ -x "$PY" ] || PY=python3

  # 1) 파싱·인덱싱·갭 — LLM 미사용. 항상 성공해야 한다.
  run "$PY" "$ROOT/routine/parse_notes.py" &&
  run "$PY" "$ROOT/routine/index_code.py" &&
  run "$PY" "$ROOT/routine/gaps.py" --top 10 &&
  run "$PY" "$ROOT/routine/trace.py" || echo "!! 파싱 단계 실패 — 배포 중단"

  # 2) 논문 수집·브리핑 — 실패해도 배포는 계속한다(직전 브리핑 유지).
  run "$PY" "$ROOT/routine/arxiv.py" --days 3 --top 8 || echo "arXiv 수집 실패(계속)"
  timeout 600 "$PY" "$ROOT/routine/generate.py" --top 8 --keep 3 >>"$LOG" 2>&1 \
    || echo "브리핑 생성 실패(계속) — 직전 산출물 유지"

  # 3) 빌드·배포·알림
  run "$PY" "$ROOT/routine/build.py" &&
  run "$PY" "$ROOT/routine/publish.py"
  run "$PY" "$ROOT/routine/notify.py"
  echo "=== $(date -Is) 루틴 끝"
} >>"$LOG" 2>&1

tail -40 "$LOG"
