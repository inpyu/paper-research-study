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
  # 1~3. 파싱·인덱싱·갭 (LLM 미사용 — 항상 성공해야 한다)
  run python3 "$ROOT/routine/parse_notes.py" &&
  run python3 "$ROOT/routine/index_code.py" &&
  run python3 "$ROOT/routine/gaps.py" --top 10
  echo "=== $(date -Is) 루틴 끝"
} >>"$LOG" 2>&1

tail -40 "$LOG"
