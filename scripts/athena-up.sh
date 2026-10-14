#!/usr/bin/env bash
# athena workspace 를 늘 같은 모양으로 — 도구 pane 을 (없는 것만) 띄우고 고정 배치로 정리한다.
#   오른쪽 끝: Explorer(사이드바 플러그인이 띄움) · 가이드 메뉴 / 하단 한 줄: 🛰 에이전트 모니터 | 📋 현황판 | 📚 배우기 검토
#   + herdr-sidebar 패치판(scripts/herdr-sidebar-patch.sh — 없으면 고정 버전 설치 + 미리 빌드한 패치판 실행 파일, Rust 필요 없음)
# 아테나 세션이 켜질 때 SessionStart 훅(scripts/hooks/workspace-up.py)이 뒤에서 부른다. 손으로: scripts/athena-up.sh
# 조건은 "athena 폴더에서 켠 아테나 claude" 하나 — workspace 이름은 보지 않는다(훅이 cwd·에이전트 여부를 거른다)
# 각 도구 스크립트는 같은 이름의 pane 이 있으면 새로 만들지 않는다 — 다시 돌려도 안전.
set -uo pipefail
ATHENA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
[ "${HERDR_ENV:-}" = 1 ] && command -v herdr >/dev/null 2>&1 || exit 0
TAB="${HERDR_TAB_ID:-}"; [ -n "$TAB" ] || exit 0

# 현황판을 먼저 — 본 영역 아래를 통째로 차지해 하단 줄의 기준 칸이 된다. 세션 시작 때는 브라우저를 새로 열지 않는다
ATHENA_BOARD_NO_BROWSER=1 "$ATHENA_DIR/scripts/board.sh" >/dev/null 2>&1
"$ATHENA_DIR/scripts/monitor-pane.sh" >/dev/null 2>&1
"$ATHENA_DIR/scripts/learn-review-pane.sh" >/dev/null 2>&1
"$ATHENA_DIR/scripts/guide-pane.sh" >/dev/null 2>&1
"$ATHENA_DIR/scripts/athena-layout.sh" "$TAB" >/dev/null 2>&1

# 사이드바 패치판(Explorer 에서 바뀐 파일 클릭 → diff) — 없으면 고정 버전 설치 + 미리 빌드한 실행 파일, 최신이면 바로 끝난다.
# 실행 파일을 바꿨으면 열린 사이드바를 새 빌드로 다시 띄우고 배치를 한 번 더 맞춘다
out="$("$ATHENA_DIR/scripts/herdr-sidebar-patch.sh" 2>&1)"
printf '%s  %s\n' "$(date '+%F %T')" "$out" >> "${TMPDIR:-/tmp}/hermes-up.log"   # 뒤에서 도니 결과는 여기 남긴다
if grep -q '패치판 교체' <<<"$out"; then
  # redeploy 는 모든 workspace 의 Explorer 를 닫는다 — 있던 탭을 적어 두고 새 빌드로 전부 다시 띄운다
  had="$(herdr pane list 2>/dev/null | python3 -c "import sys,json;print(' '.join(sorted({p['tab_id'] for p in json.load(sys.stdin)['result']['panes'] if p.get('label')=='Explorer'} | {'$TAB'})))")"
  herdr plugin action invoke redeploy --plugin herdr-sidebar >/dev/null 2>&1
  sleep 3
  # shellcheck disable=SC2086
  "$ATHENA_DIR/scripts/herdr-sidebar-reopen.sh" $had >> "${TMPDIR:-/tmp}/hermes-up.log" 2>&1
  sleep 2
  "$ATHENA_DIR/scripts/athena-layout.sh" "$TAB" >/dev/null 2>&1
fi
exit 0
