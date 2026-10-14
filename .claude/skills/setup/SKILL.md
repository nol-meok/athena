---
name: setup
description: 새 회사 첫 실행 — 레포를 찾아 회사 팩을 만들고(athena init) 레포마다 에이전트·지식 뼈대·검증 스크립트를 만든 뒤(athena scaffold) 레포 코드를 읽어 뼈대와 서비스 문서를 채우고 QA 초안(앱별 routes·TC)·검증·지문 기준선·레포별 다이어그램까지 잡습니다. 팩이 없을 때 세션 시작 훅이 안내합니다.
argument-hint: "(선택) 레포 폴더 — 비우면 athena.config.json reposRoot 또는 상위 폴더"
---

# 새 회사 첫 실행

레포 폴더: $ARGUMENTS (비우면 `reposRoot`, 없으면 `..`)

기계적인 일은 `bin/athena` 가, 코드를 읽고 판단하는 일은 아테나(와 작업자)가 한다. 환경 설정이라 계획서 없이 진행하고, 끝에 보고한다. **레포는 읽기만 한다**(fetch·체크아웃·설치도 사용자에게 묻고). 비밀값은 출력하지 않는다.

## 0. 이미 팩이 있는 회사인가
AskUserQuestion — "회사 팩 레포가 이미 있나요?" · 선택지 `있다 — 주소 입력`(Other 에 clone 주소) / `없다 — 새로 만든다`.
- 있다: `git clone <주소> packs/<회사>` → `athena.config.json` 에 `{ "pack": "packs/<회사>", "reposRoot": ".." }` → `bin/athena pack link` → `scripts/setup.sh`(repos/ 링크) → 끝. 6단계(검증)만 돌려 보고한다

## 1. 레포 찾기
`bin/athena init --scan [--root <폴더>]` — 표를 그대로 보여 준다. 추정(종류 single·monorepo·packages · 층 fe·be · 기준 브랜치 · 작업 base · 앱별 브랜치 · GitHub 조직)이다.

## 2. 사용자 확인 (AskUserQuestion, 한 번에 최대 4문항)
- **넣을 레포**(multiSelect) — 아테나 자신·다른 아테나 복사본·연구용 레포는 기본으로 빼서 보여 준다
- **회사 이름**(팩 폴더 이름, 영문 소문자) · **회사를 가리키는 말**(names — 서비스·브랜드 이름, `pack check` 가 코어에서 찾는다)
- **추정이 틀린 레포** — 기준 브랜치(운영 반영분)·작업 base(PR 대상)·종류·층. 고칠 게 있으면 그 레포만 다시 묻는다
- **에이전트 이름** — 기본은 `<레포>-fe|be`, 모노레포는 `<앱>-fe` + `<레포>-packages-fe`. 바꾸려면 `--agent <레포>=<이름>` · `--agent <레포>/<앱>=<이름>`

## 3. 팩 만들기
`bin/athena init --pack <회사> --repos <a,b,…> [--names <x,y>] [--org <조직>] [--agent …]` → `packs/<회사>/pack.json`·`ROUTING.md`·`athena.config.json`·링크. 추정을 고쳤으면 `packs/<회사>/pack.json` 해당 레포를 직접 고친다(형식 `docs/pack.md`). 그다음 `scripts/setup.sh`(repos/ 링크).

## 4. 뼈대
`bin/athena scaffold` — 레포마다 `agents/<에이전트>.md` · `knowledge/<레포>/{rules,structure,gotchas}.md` · `verify/<레포>.sh`(코어 `_generic.sh` 호출), 팩 하나에 `docs/services.md`(서비스 소개 · 스택 표 자리) · `diagrams/SERVICES.md`(/diagram 서비스 표) · `diagrams/index.json`(다이어그램 목록 카드). 있는 파일은 건드리지 않는다.

## 5. 뼈대 채우기 (레포마다 작업자 하나 — Agent 도구 `general-purpose`, 백그라운드, 한 번에 최대 5개 · `/monitor` 로 보이게)
작업자 지시(레포마다 같은 틀):
- 대상: `repos/<레포>`(모노레포 앱은 `apps/<앱>`)를 **운영 기준 ref**(`git show origin/<branch>:<경로>` · `git ls-tree`)로 읽는다. 메인 체크아웃은 브랜치가 제각각이라 읽지 않는다. 쓰지 않는다
- 채울 것: 에이전트 `description`(어떤 요청이면 이 에이전트인지 — 화면·도메인 키워드 한 문장, **콜론+공백 금지**) · `rules.md` "필수"(금지·용어·생성물) · `structure.md`(스택·디렉토리·라우트·스크립트) · 레포 원문(`README`·`CLAUDE.md`·`AGENTS.md`) 요약. **확인 안 된 것은 "확인 필요"로 남긴다** — 추측을 사실로 쓰지 않는다
- `patterns.md`·`workflows.md` 는 만들지 않는다(그 레포를 처음 작업할 때 채운다)
- 레포 고유 검증이 필요하면(`_generic.sh` 로 부족) `verify/<레포>.sh` 를 `_lib.sh` 로 다시 쓴다
- 보고: 채운 파일 · "확인 필요" 목록 · **서비스 소개**(서비스(앱)마다 "무엇을 하나" 한 줄 · 주요 화면·API 3~5개와 근거 파일) — services.md 는 작업자가 쓰지 않는다(여럿이 한 파일을 덮지 않게)
그다음 아테나가
- `ROUTING.md` "어느 레포인지 고르기"(요청 말 → 레포)를 채운다. 같은 말이 여러 레포를 가리키면 "되묻는다"로 적는다
- `docs/services.md` "서비스 소개" 표의 "확인 필요" 칸을 작업자 보고로 채운다(근거 없는 칸은 그대로). "스택 (자동)" 구간은 손대지 않는다 — 7단계 `build-derived` 가 채운다

## 5-1. QA 초안
`node scripts/qa/init-app.mjs --all` — 등록한 화면 레포의 앱마다(단일 레포 = 앱 하나, 모노레포 = 앱마다, 백엔드·패키지·Next 아닌 앱은 건너뜀) 운영 기준 ref 의 화면 목록을 읽어 팩 `qa/routes/<앱>.json`(QA 설정 초안)과 `qa/docs/tc/<앱>.md`(화면마다 스모크 TC)를 만들고 링크한다. 있는 파일은 덮지 않는다. 출력의 "확인 필요"(로그인 쿠키 `server.tokenCookie` · `devUrl` · 로그인 경로 · dev 전 준비 스크립트 · 동적 화면 samples)는 5단계 작업자가 읽은 코드로 채울 수 있으면 채우고(근거 파일을 적는다), 아니면 그대로 보고에 남긴다 — 형식 `docs/knowledge/common/verify.md` "앱 설정"

## 6. 검증 한 번
레포마다 `scripts/verify/<레포>.sh [<앱>]`(무거우니 `heavy.sh` 가 줄 세운다) — 결과 표를 그대로 모아 보여 준다. ❌·⏭ 은 통과로 치지 않고 "확인 필요"(설치 안 됨·스크립트 없음 등)로 남긴다. 설치는 사용자에게 묻고 한다.

## 7. 지문 기준선
`node scripts/sync-fingerprint.mjs`(fetch 한다 — 사용자에게 한 줄 알린다) → 리포트 확인 → `node scripts/sync-fingerprint.mjs --accept` → `node scripts/build-derived.mjs`(`docs/services.md` 스택 표가 채워진다). 이후는 평소 `/sync`.

## 7-1. 레포별 다이어그램
AskUserQuestion — "서비스 다이어그램(구조 · 화면 맵 · 요청 흐름)을 지금 그릴까요?" · 선택지 `지금 그린다 (추천)`(description: 서비스 N개 · 작업자 5개씩 · 서비스마다 수 분~수십 분(추측)) / `나중에`(description: 언제든 /diagram).
- 지금: `/diagram` 절차(`.claude/skills/diagram/SKILL.md`)를 전체 대상으로 그대로 돈다 — 서비스 표는 4단계가 만든 `docs/diagrams/SERVICES.md`, 가이드(`guides/<서비스>.md`)는 작업자가 처음 그리며 만든다. 끝나면 `node scripts/build-diagram-index.mjs`
- 나중에: 보고의 "다음" 에 `/diagram` 을 적는다

## 8. 마무리 보고
- 만든 것: 팩 경로 · 레포·에이전트 표 · 파일 수 · 서비스 문서(`docs/services.md` — 채운 칸·남은 "확인 필요") · 다이어그램(그린 서비스·장 수, 미뤘으면 미룸)
- 검증 표 · "확인 필요" 목록(레포별) · QA 초안(앱별 화면 수 · 남은 `$todo`)
- 다음: `bin/athena pack check`(코어에 회사 이름이 새지 않았는지) · 팩을 팀과 나누려면 `packs/<회사>` 를 별도 레포로 push(사용자가) · 첫 작업은 평소처럼 말로
