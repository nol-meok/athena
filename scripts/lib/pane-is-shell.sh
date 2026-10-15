#!/usr/bin/env bash
# pane 이 빈 셸(프롬프트에서 대기 — 안에서 도는 프로그램 없음)이면 0, 뭔가 돌고 있으면 1.
# herdr 를 다시 켜면 pane 자리·이름은 복원되지만 안의 프로그램은 빈 셸로 돌아온다 — 이름만 보고 "떠 있다" 고 치면 빈 자리로 남는다.
# 사용: scripts/lib/pane-is-shell.sh <pane id>   (확인 못 하면 1 — 돌고 있는 것을 건드리지 않는 쪽으로)
set -uo pipefail
[ -n "${1:-}" ] || exit 1
herdr pane process-info --pane "$1" 2>/dev/null | python3 -c '
import sys, json
try:
    info = json.load(sys.stdin)["result"]["process_info"]
except Exception:
    sys.exit(1)
sys.exit(0 if info.get("foreground_process_group_id") == info.get("shell_pid") else 1)
'
