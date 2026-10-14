#!/usr/bin/env bash
# 사이드바 Explorer 를 지정한 탭마다 다시 띄운다 (이미 있으면 건너뜀).
#   redeploy(패치판 교체 뒤 새 빌드로 다시 띄우기)는 모든 workspace 의 Explorer 를 닫고 지금 탭에만 다시 띄운다
#   — 다른 workspace 는 "다음 포커스 때" 라지만 실제로는 안 돌아온다. athena-up 이 redeploy 전에 Explorer 가 있던 탭을 적어 두고 이걸 부른다.
# 사용: scripts/herdr-sidebar-reopen.sh <탭 id...>   (인자가 없으면 모든 탭)
# 방식은 플러그인 ensure-sidebar.sh 와 같다 — 그 탭의 기준 pane 옆을 나눠 herdr-sidebar 를 띄우고 "Explorer" 이름을 붙인다.
# Explorer 는 기준 pane 의 폴더(에이전트 pane 이면 그 워크트리)를 보여 준다.
set -uo pipefail
command -v herdr >/dev/null 2>&1 || exit 0
ROOT="$(herdr plugin list --json 2>/dev/null | python3 -c "import sys,json;print(next((p.get('plugin_root','') for p in json.load(sys.stdin)['result']['plugins'] if p.get('plugin_id')=='herdr-sidebar'),''))" 2>/dev/null)"
BIN_DIR="$ROOT/target/release"; BIN="$BIN_DIR/herdr-sidebar"
[ -n "$ROOT" ] && [ -x "$BIN" ] || { echo "· herdr-sidebar 가 없어 건너뜀"; exit 0; }

tabs=("$@")
[ "${#tabs[@]}" -gt 0 ] || while read -r t; do tabs+=("$t"); done < <(herdr tab list 2>/dev/null | python3 -c "import sys,json;[print(t['tab_id']) for t in json.load(sys.stdin)['result']['tabs']]")

for tab in "${tabs[@]}"; do
  # 기준 pane: 그 탭에서 포커스됐던 pane → 없으면 도구·미리보기가 아닌 첫 pane. Explorer 가 이미 있으면 건너뜀
  read -r has pane cwd <<<"$(herdr pane list 2>/dev/null | python3 -c "
import sys, json
ps = [p for p in json.load(sys.stdin)['result']['panes'] if p['tab_id'] == '$tab']
if any(p.get('label') == 'Explorer' for p in ps):
    print('yes - -'); sys.exit()
skip = ('Explorer', '가이드 메뉴', '🛰 에이전트 모니터', '📋 현황판', '📚 배우기 검토')
cand = [p for p in ps if p.get('label') not in skip and not (p.get('label') or '').endswith('· preview')]
cand.sort(key=lambda p: not p.get('focused'))
p = cand[0] if cand else None
print('no', p['pane_id'], p.get('foreground_cwd') or p.get('cwd') or '-') if p else print('yes - -')
")"
  [ "$has" = no ] || continue
  target="$pane"; ratio="0.75"; needs_swap="false"
  plan="$(herdr pane layout --pane "$pane" 2>/dev/null | "$BIN" --open-plan 2>/dev/null || true)"
  [ -n "$plan" ] && IFS=$'\t' read -r target ratio needs_swap <<<"$plan"
  args=(pane split "$target" --direction right --ratio "$ratio" --no-focus --env "PATH=$BIN_DIR${PATH:+:$PATH}")
  [ "$cwd" != "-" ] && args+=(--cwd "$cwd")
  np="$(herdr "${args[@]}" 2>/dev/null | sed -n 's/.*"pane_id":"\([^"]*\)".*/\1/p' | head -n1)"
  [ -n "$np" ] || { echo "✖ $tab Explorer 못 띄움"; continue; }
  [ "$needs_swap" = true ] && herdr pane swap --source-pane "$np" --target-pane "$target" >/dev/null 2>&1
  herdr pane run "$np" "herdr-sidebar" >/dev/null 2>&1
  herdr pane rename "$np" Explorer >/dev/null 2>&1
  echo "✔ $tab Explorer ($cwd)"
done
exit 0
