#!/usr/bin/env python3
"""athena workspace 고정 배치 훅 (Claude Code SessionStart) — 아테나 세션이 켜지면 scripts/athena-up.sh 를 뒤에서 돌린다.

도구 pane(현황판·에이전트 모니터·배우기 검토·가이드 메뉴)을 없는 것만 띄우고 정해진 자리로 정리한다.
아테나 세션만 — FE 에이전트(claude --agent)·reviewer, athena 루트가 아닌 cwd, herdr 밖,
도구 pane 안에서 뜬 claude(배우기 검토의 claude -p 등)는 건너뛴다. 세션 시작을 막거나 늦추지 않는다(항상 exit 0).
"""
import json
import os
import subprocess
import sys

try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}

ATHENA_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
TOOL_LABELS = {'📋 현황판', '🛰 에이전트 모니터', '📚 배우기 검토', '가이드 메뉴', 'Explorer'}


def main() -> None:
    if payload.get('agent_type') or os.environ.get('ATHENA_AGENT'):
        return
    if os.path.realpath(payload.get('cwd') or os.getcwd()) != ATHENA_DIR:
        return
    if os.environ.get('HERDR_ENV') != '1' or not os.environ.get('HERDR_PANE_ID'):
        return
    # 도구 pane 안에서 뜬 claude 는 건너뛴다
    try:
        out = subprocess.run(['herdr', 'pane', 'list'], capture_output=True, text=True, timeout=3).stdout
        me = next((p for p in json.loads(out)['result']['panes'] if p['pane_id'] == os.environ['HERDR_PANE_ID']), {})
        if me.get('label') in TOOL_LABELS:
            return
    except Exception:
        return
    subprocess.Popen(
        [os.path.join(ATHENA_DIR, 'scripts', 'athena-up.sh')],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


try:
    main()
except Exception:
    pass
sys.exit(0)
