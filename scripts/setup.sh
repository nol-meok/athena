#!/usr/bin/env bash
# 팀원 최초 설정: athena.config.json 의 레포들을 repos/<name> 심볼릭 링크로 연결하고 도구를 점검한다.
# 사용: scripts/setup.sh [--root <레포들이 있는 폴더>]   (기본: athena.config.json 의 reposRoot, 보통 hermes 상위 폴더)
set -uo pipefail
ATHENA_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ATHENA_DIR"
ROOT_OVERRIDE=""
[ "${1:-}" = "--root" ] && ROOT_OVERRIDE="${2:-}"

CONFIG_ROOT="$(python3 -c 'import sys; sys.path.insert(0, "scripts/lib"); from athena_config import load; print(load(".")["reposRoot"])')"
REPOS_ROOT="${ROOT_OVERRIDE:-$CONFIG_ROOT}"
case "$REPOS_ROOT" in /*) ;; *) REPOS_ROOT="$ATHENA_DIR/$REPOS_ROOT" ;; esac
REPOS_ROOT="$(cd "$REPOS_ROOT" 2>/dev/null && pwd)" || { echo "❌ 레포 루트가 없습니다: ${ROOT_OVERRIDE:-$CONFIG_ROOT}"; exit 1; }

mkdir -p repos
echo "레포 루트: $REPOS_ROOT"
missing=0
for name in $(python3 -c 'import sys; sys.path.insert(0, "scripts/lib"); from athena_config import load; print(" ".join(r["name"] for r in load(".")["repos"]))'); do
  target="$REPOS_ROOT/$name"
  link="repos/$name"
  if [ -d "$target/.git" ] || [ -f "$target/.git" ]; then
    [ -L "$link" ] && rm "$link"
    ln -s "$target" "$link"
    printf '  ✔ %-22s → %s\n' "$name" "$target"
  else
    printf '  ✖ %-22s 없음 (%s) — clone 후 다시 실행\n' "$name" "$target"
    missing=$((missing+1))
  fi
done

echo
echo "도구 점검:"
for tool in git node pnpm claude herdr; do
  if command -v "$tool" >/dev/null 2>&1; then
    ver="$("$tool" --version 2>/dev/null | head -1)"
    printf '  ✔ %-7s %s\n' "$tool" "$ver"
  else
    if [ "$tool" = herdr ]; then printf '  · %-7s 없음 (선택 — /guide pane 은 새 창으로 대체됨)\n' "$tool"
    else printf '  ✖ %-7s 없음\n' "$tool"; fi
  fi
done

echo
echo "herdr-sidebar 패치 (Explorer 에서 바뀐 파일 클릭 → diff · patches/herdr-sidebar):"
"$ATHENA_DIR/scripts/herdr-sidebar-patch.sh"

echo
echo "QA 시뮬레이션 도구 (scripts/qa — Playwright·dependency-cruiser):"
if [ -d "$ATHENA_DIR/scripts/qa/node_modules" ]; then
  echo "  ✔ 의존성 있음"
elif command -v npm >/dev/null 2>&1 && (cd "$ATHENA_DIR/scripts/qa" && npm ci --silent >/dev/null 2>&1); then
  echo "  ✔ 의존성 설치 (npm ci)"
else
  echo "  ✖ 설치 실패 — cd scripts/qa && npm ci"
fi
if [ -d "$ATHENA_DIR/scripts/qa/node_modules/playwright" ]; then
  if (cd "$ATHENA_DIR/scripts/qa" && npx --no-install playwright install chromium >/dev/null 2>&1); then echo "  ✔ Chromium 준비"
  else echo "  ✖ Chromium 설치 실패 — cd scripts/qa && npx playwright install chromium"; fi
fi
echo "  · 로그인 세션은 각자 한 번: node scripts/qa/login.mjs (이메일 로그인 — docs/knowledge/common/verify.md \"QA 시뮬레이션\")"

echo
if [ "$missing" -gt 0 ]; then echo "⚠️  레포 $missing 개가 연결되지 않았습니다. 해당 에이전트는 동작하지 않습니다."; else echo "✅ 준비 완료. athena 폴더에서 claude 를 실행하세요."; fi
