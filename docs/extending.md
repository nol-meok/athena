# Athena 확장 가이드

스킬(슬래시 커맨드)과 에이전트는 파일 하나로 추가된다. 추가한 뒤에는 문서 몇 곳을 같이 손봐야 한다.

## 스킬 추가
- `.claude/skills/<이름>/SKILL.md` 하나 만들면 `/<이름>`으로 바로 뜬다
- frontmatter에 `name`, `description`, 필요하면 `argument-hint`를 둔다
- 본문에서 `$ARGUMENTS`로 인자를 받는다
- 기존 `.claude/skills/call/SKILL.md`를 복사해서 고치는 게 가장 빠르다

```yaml
---
name: 이름
description: 어떤 요청이면 이 스킬인지 한 문장
argument-hint: "인자 예시"
---
```

## 학습으로 스킬 만들기 (learn 이슈 `target: skill:<이름>`)
에이전트가 같은 절차를 반복하면 스킬 후보가 현황판 [학습] 탭에 쌓인다(`AGENTS.md` 6절 "📚 배운 것"). 사용자가 [아테나에게 맡기기]를 누르면 아테나가 아래 틀로 만든다.
- 이름은 **절차의 종류**로 짓는다 — PR 번호·오류 문구·`fix-…` 같은 일회성 이름 금지. 소문자·숫자·`-`
- 먼저 **기존 스킬을 고쳐 넣을 수 있는지** 본다 — 비슷한 스킬이 있으면 새로 만들지 않고 그 스킬에 절을 더한다
- `description` 은 **첫 60자 안에 "어떤 요청이면 이 스킬"** 이 보이게(스킬 목록에서 잘려 보인다)
- 본문 순서: **언제 쓰나 → 절차 → 함정 → 확인 방법**. learn 이슈의 `## 절차`·근거를 옮기고, 계획서 번호·날짜는 넣지 않는다
- 만든 뒤 아래 "같이 갱신할 곳" 표를 고친다. 30일 넘게 안 쓰면 `scripts/learn-curator.mjs` 가 정리 후보로 올린다 — 정리하면 지우지 않고 `.claude/skills/.archive/<이름>/` 로 옮긴다

```markdown
---
name: <이름>
description: <60자 안에 언제 쓰는지> — <덧붙일 설명>
argument-hint: "<인자 예시>"
---

## 언제 쓰나
## 절차
1. …
## 함정
- …
## 확인 방법
- …
```

## 에이전트 추가
- `.claude/agents/<이름>.md` 하나 만들면 된다
- frontmatter의 `description`이 아테나가 라우팅할 때 읽는 문장이다. "어떤 요청이면 이 에이전트"를 구체적으로 적는다
- description 안에 콜론+공백(`: `)이 들어가면 YAML이 깨진다
- 담당 레포가 있으면 `tools`와 본문에 레포 절대경로·검증 명령을 적는다 (기존 `.claude/agents/*.md` 참고)
- `tools` 에는 기존 FE 에이전트와 같은 **Atlassian 읽기 전용 도구 목록**을 그대로 붙인다(Jira·Confluence 읽기 — 와일드카드 `mcp__claude_ai_Atlassian__*` 는 쓰기까지 열리므로 쓰지 않는다)

## 같이 갱신할 곳
| 파일 | 고칠 곳 |
|---|---|
| `AGENTS.md` | 담당 레포 표, 라우팅 기준 (도구 무관 공통 문서) |
| `CLAUDE.md` | 서브에이전트 표, Skills 표 |
| `README.md` | 팀 표, 사용 목록, 구조 |
| `docs/playbook.html` | 팀 구성·슬래시 커맨드·폴더 구조 섹션, 헤더의 `agents N · skills N` |

`/sync`는 레포 쪽 변화만 반영하고 athena 자체 구조 변화는 잡지 않는다. 스킬이나 에이전트를 추가했으면 아테나에게 **"방금 추가한 스킬 문서에도 반영해줘"**라고 하면 위 세 곳을 갱신한다.

## 보는 방법
- 터미널: `/guide` (오른쪽 pane에 **선택형 메뉴** — 확장 가이드도 메뉴에 있다), `/guide <파일>` (오른쪽 pane에 파일을 뷰어로), `/guide 열기` (플레이북 HTML을 브라우저로). 이 문서를 채팅에서 보려면 아테나에게 "확장 가이드 보여줘"
- 메뉴(`scripts/guide-menu.sh`): 항목을 **마우스로 클릭**하거나 ↑/↓·휠·숫자로 고르고 Enter로 실행, `q`로 종료. 7개 항목이 두 그룹으로 나뉜다
  - **📘 문서** — ① 아테나 구조 설명 ② 시작하기 ③ 플레이북 ④ 서비스 다이어그램 ⑤ 확장 가이드
  - **⚡ 실행 · 확인** — ⑥ **스킬 목록 · 실행** ⑦ 에이전트 · 담당 레포 · 라우팅
- **스킬 목록**은 `.claude/skills/*/SKILL.md`의 frontmatter(`name`·`argument-hint`·`description`)를 그때그때 읽어 만든다. 스킬을 추가하면 메뉴에 자동으로 나온다. 번호를 고르면 `⏎`로 인자를 입력해 **아래에 새 pane을 열어 별도 아테나 세션**으로 `/<스킬>`을 실행하거나(기존 Claude Code pane은 건드리지 않는다. herdr 안에서만 동작, 아니면 프롬프트를 화면에 표시), `v`로 SKILL.md 본문을 볼 수 있다
- **에이전트 목록**도 `.claude/agents/*.md`에서 `name`·`description`·`- 레포:`를 읽어 만들고, 그 아래에 `AGENTS.md`의 "어느 레포인지 고르기" 라우팅 기준을 붙인다
- 문서 항목은 **마크다운 뷰어**로 열린다. `glow`가 설치돼 있으면 glow, 없으면 내장 렌더러 `scripts/mdview.py`(의존성 없음, 제목·목록·표·코드·굵게 서식). 특정 파일을 직접 보려면 `/guide <파일>`을 쓴다
- 스크립트 단독: `scripts/guide-pane.sh [파일]`. `.md`를 주면 뷰어로, 그 외는 less로 띄운다. 화면 pane 안이면(herdr) `scripts/screen pane split`, tmux면 `split-window`, 둘 다 아니면 새 Ghostty 창으로 대체된다
- 플레이북: `docs/playbook.html` "확장하기" 절(`/guide 열기`)

## 화면 계층 (scripts/screen)
아테나 스크립트·훅·지시문은 pane·탭·workspace 를 **`scripts/screen` 으로만** 다룬다. herdr 명령·`HERDR_*` 환경 변수·herdr JSON 모양을 아는 곳은 `scripts/lib/screen.py`(herdr 백엔드) 하나다 — 화면 백엔드가 바뀌어도(③ Studio) 같은 계약만 구현하면 스크립트는 그대로 돈다.
- 입구: bash·node 는 `scripts/screen <동작>`(node 는 `scripts/lib/screen.mjs` 의 `screen()`·`screenSync()`), 파이썬 훅은 `scripts/lib/screen.py` 를 바로 불러 쓴다(`config.mjs ↔ athena_config.py` 와 같은 짝). 결과는 납작한 JSON, 실패면 종료 코드 1 이상
- 동작(`scripts/screen --help`)

  | 묶음 | 동작 |
  |---|---|
  | 지금 자리 | `self`(부른 pane — 환경에서, `--format sh` 는 eval 용 `SCREEN_*`) · `inside`(pane 안이면 0) · `pane current`(서버가 정한 지금 pane — self 와 다르다) · `capabilities [--has …]` |
  | 보기 | `pane list`(`--tab`·`--workspace`·`--label`(이름표만)·`--label-or-name`·`--cwd`·`--agent-only`·`--prefer-tab`·`--prefer-workspace`, `self` 를 값으로) · `pane get` · `pane layout --pane` · `pane is-shell` · `pane read`·`pane wait-output`(herdr 읽기 옵션 그대로 — 출력 형식은 `--read-format`) · `tab list`·`tab get` · `workspace list`·`workspace get` |
  | 바꾸기 | `pane split --target <id\|self\|focused>` · `pane run` · `pane send-text` · `pane send-keys` · `pane rename` · `pane swap` · `pane move`(id 가 바뀐다) · `pane close` · `tab rename`·`tab close` · `workspace create` |

- `pane run` 은 단어를 **따옴표 없이 공백으로 이어 붙인 한 줄**을 그 pane 셸에 친다(herdr 계약 그대로). 따옴표가 필요한 명령은 실행기 파일을 만들어 그 경로 하나만 넘긴다(`delegate.sh` 방식)
- `--target self` 는 부른 pane(모르면 포커스된 pane), `focused` 는 포커스된 pane. 뒤에서 도는 스크립트는 self 를 쓴다 — 포커스된 pane 은 사용자가 보고 있는 엉뚱한 곳일 수 있다
- 출력 형식: `--format json`(기본) · `id`(첫 대상의 id 한 줄) · `ids`(한 줄에 하나). id 는 불투명한 문자열 — 쪼개 읽지 않는다(workspace 는 `workspace_id`·`tab get` 으로)
- 백엔드: `ATHENA_SCREEN=herdr|studio|none`(기본 auto — herdr 표시·명령이 있으면 herdr, 아니면 none). none 이면 바꾸는 동작이 실패하고 부르는 쪽이 원래 대체 동작(nohup · 새 창 · 직접 실행 안내)을 한다. studio 는 아직 없다(unsupported)
- 백엔드 기능(`capabilities`): `agent-status` · `process-info` · `layout-geometry` · `pane-move` · `workspaces` · `herdr-sidebar` — 고정 배치(`athena-layout.sh`)는 자리·옮기기가 있을 때만, 사이드바 단계(`athena-up.sh`)는 `herdr-sidebar` 가 있을 때만 돈다
- herdr 플러그인 자체(사이드바 Explorer 설치·실행 파일·redeploy)는 `scripts/herdr-sidebar-*.sh` 가 herdr 를 직접 부른다 — 허용 목록
- 지킴이: `scripts/screen-lint.sh` — `scripts`·`bin`·`.claude`·`.codex` 에서 허용 목록 밖의 herdr 명령·`HERDR_*` 를 찾으면 1. 스크립트를 고치거나 더하면 돌린다
- 회귀 검사: `scripts/screen-check/check.sh` — 가짜 herdr 로 각 스크립트가 부르는 인자·순서·출력을 golden 과 비교한다(진짜 herdr·현황판은 건드리지 않는다). 화면 동작을 일부러 바꿨으면 그 시나리오만 `--record`
