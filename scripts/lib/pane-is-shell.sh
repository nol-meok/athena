#!/usr/bin/env bash
# pane 이 빈 셸(프롬프트에서 대기 — 안에서 도는 프로그램 없음)이면 0, 뭔가 돌고 있으면 1.
# herdr 를 다시 켜면 pane 자리·이름은 복원되지만 안의 프로그램은 빈 셸로 돌아온다 — 이름만 보고 "떠 있다" 고 치면 빈 자리로 남는다.
# 사용: scripts/lib/pane-is-shell.sh <pane id>   (확인 못 하면 1 — 돌고 있는 것을 건드리지 않는 쪽으로)
# 화면 계층으로 옮겼다 — scripts/screen pane is-shell 을 그대로 부른다(옛 경로를 부르는 곳을 위해 남겨 둔다)
exec "$(dirname "$0")/../screen" pane is-shell "${1:-}"
