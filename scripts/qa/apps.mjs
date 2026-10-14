/**
 * QA 대상 앱 — 팩에 등록한 레포에서 뽑는다(코어에 앱 이름·포트·쿠키를 적지 않는다).
 *   단일 레포(kind single)  = 앱 하나 — 이름은 레포 이름(repo.qaApp 으로 바꿀 수 있다), 앱 폴더는 레포 루트
 *   모노레포(kind monorepo) = 앱마다 — 앱 폴더 apps/<앱>(apps.<앱>.dir 로 바꿀 수 있다)
 *   발행 패키지(kind packages)·백엔드(layer be)는 화면이 없어 뺀다
 * 앱마다 QA 설정(띄우는 명령·포트·로그인 쿠키·준비 단계·화면 목록)은 scripts/qa/routes/<앱>.json(팩 qa/routes 링크).
 * 그 파일이 없으면 "설정 전" — /setup 이 scripts/qa/init-app.mjs 로 초안을 만든다.
 * 화면에 보일 이름은 팩 qa.apps.<앱>(문자열)이 있으면 그것, 없으면 앱 이름.
 */
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const QA_DIR = dirname(fileURLToPath(import.meta.url))
export const ROUTES_DIR = join(QA_DIR, 'routes')

// 등록된 레포 → QA 대상 앱 목록 [{ app, label, repo, dir, branch, prBase, agents, configured }] — branch 는 운영 기준(문서·초안), prBase 는 작업 base(영향 비교·전체 검수)
export function listQaApps(config) {
  const labels = config.qa?.apps ?? {}
  const labelOf = (app) => (typeof labels[app] === 'string' ? labels[app] : labels[app]?.label) || app
  const apps = []
  for (const repo of config.repos ?? []) {
    if (repo.kind === 'packages' || repo.layer === 'be') continue
    if (repo.kind === 'monorepo') {
      for (const [app, settings] of Object.entries(repo.apps ?? {})) {
        apps.push({ app, repo: repo.name, dir: settings.dir ?? `apps/${app}`, branch: settings.branch ?? repo.branch, prBase: settings.prBase ?? repo.prBase ?? 'dev', agents: settings.agent ? [settings.agent] : [] })
      }
      continue
    }
    apps.push({ app: repo.qaApp ?? repo.name, repo: repo.name, dir: '', branch: repo.branch, prBase: repo.prBase ?? 'dev', agents: repo.agents ?? [] })
  }
  return apps.map((entry) => ({ ...entry, label: labelOf(entry.app), configured: existsSync(join(ROUTES_DIR, `${entry.app}.json`)) }))
}

export const findQaApp = (config, app) => listQaApps(config).find((entry) => entry.app === app) ?? null
export const appOfAgent = (config, agent) => listQaApps(config).find((entry) => entry.agents.includes(agent)) ?? null

// --app 을 안 줬을 때 — 설정(routes)이 있는 앱이 하나뿐이면 그것. 여럿이거나 없으면 null(고르게 한다)
export function defaultQaApp(config) {
  const configured = listQaApps(config).filter((entry) => entry.configured)
  return configured.length === 1 ? configured[0].app : null
}

export const readRoutes = (app) => {
  const file = join(ROUTES_DIR, `${app}.json`)
  return /^[\w.-]+$/.test(app) && existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')) : null
}

// 앱 폴더 안 상대 경로 — 단일 레포는 dir 이 '' 이라 그대로
export const inApp = (dir, path) => (dir ? `${dir}/${path}` : path)

// 라우터 폴더(앱 폴더 기준) — app/ 이 있으면 App Router, 아니면 pages/. src/ 아래도 본다. Next 화면 앱이 아니면 null
export const routerDirOf = (appAbs) => ['app', 'src/app', 'pages', 'src/pages'].find((dir) => existsSync(join(appAbs, dir))) ?? null

// 화면 파일 규칙 — 화면 폴더(pages/·app/) 안 경로로 본다. impact.mjs(영향 분석)와 init-app.mjs(초안)가 같이 쓴다
const SPECIAL_PAGES = new Set(['_app', '_document', '_error'])
const CODE_FILE = /\.(tsx|ts|jsx|js)$/
// 라우트 그룹 (x)·병렬 슬롯 @x 는 주소에 안 나온다
const urlSegments = (inside) => inside.split('/').filter((segment) => segment && !/^\(.*\)$/.test(segment) && !segment.startsWith('@'))
export function isScreenPath(inside, router) {
  if (!CODE_FILE.test(inside)) return false
  const baseName = inside.split('/').pop().replace(/\.\w+$/, '')
  if (router === 'app') return baseName === 'page' && !inside.split('/').some((segment) => segment.startsWith('@') || segment.startsWith('(.'))
  if (inside.startsWith('api/')) return false
  return !SPECIAL_PAGES.has(baseName)
}
export function routeOfPath(inside, router) {
  const trimmed = inside.replace(CODE_FILE, '')
  // App Router: (authenticated)/chat/[id]/page.tsx → /chat/[id]
  if (router === 'app') return `/${urlSegments(trimmed.replace(/(^|\/)page$/, '')).join('/')}`
  // Pages Router: help/faq/index.tsx → /help/faq
  return `/${trimmed}`.replace(/\/index$/, '') || '/'
}

// 패키지 관리자 — 레포 루트의 lockfile 로 고른다(없으면 npm)
export function packageManager(root) {
  if (existsSync(join(root, 'pnpm-lock.yaml'))) return { name: 'pnpm', install: ['pnpm', 'install', '--frozen-lockfile', '--prefer-offline'], exec: ['pnpm', 'exec'], run: ['pnpm', 'run'] }
  if (existsSync(join(root, 'yarn.lock'))) return { name: 'yarn', install: ['yarn', 'install', '--frozen-lockfile'], exec: ['yarn'], run: ['yarn', 'run'] }
  return { name: 'npm', install: existsSync(join(root, 'package-lock.json')) ? ['npm', 'ci'] : ['npm', 'install'], exec: ['npx', '--no-install'], run: ['npm', 'run'] }
}

/**
 * 로컬 서버 설정 — routes/<앱>.json 의 server 블록. 없는 값은 기본값.
 *   port        작업(head) 서버 포트 — 기본 3291
 *   basePort    기준(base) 서버 포트 — 기본 port + 1
 *   localPorts  사람이 따로 띄워 둔 dev 서버 포트 — 현황판 [로그인] 이 port 다음으로 찾아 본다
 *   dev         띄우는 명령(앱 폴더에서, {port} 를 바꿔 넣는다) — 기본 ["<pm exec>", "next", "dev", "-p", "{port}"]
 *   prepare     dev 전에 돌릴 package.json 스크립트 — "gen:relay" 또는 { "script": "gen:env", "unless": ".env" }(그 파일이 앱 폴더에 있으면 건너뜀). 기본 없음
 *   tokenCookie 로그인했으면 생기는 쿠키 이름(앞부분) — 세션이 살아 있나·만료 시각을 이걸로 본다. 없으면 세션 파일이 있으면 살아 있다고 본다
 */
export function serverSettings(routes) {
  const server = routes?.server ?? {}
  const port = Number(server.port) || 3291
  return {
    port,
    basePort: Number(server.basePort) || port + 1,
    localPorts: (server.localPorts ?? []).map(Number).filter(Boolean),
    dev: Array.isArray(server.dev) && server.dev.length ? server.dev : null,
    prepare: (server.prepare ?? []).map((step) => (typeof step === 'string' ? { script: step } : step)).filter((step) => step?.script),
    tokenCookie: server.tokenCookie || ''
  }
}

// 띄우는 명령 — [명령, ...인자]
export const devCommand = (settings, manager, port) =>
  (settings.dev ?? [...manager.exec, 'next', 'dev', '-p', '{port}']).map((part) => String(part).replaceAll('{port}', String(port)))

// 저장한 세션의 로그인 토큰 쿠키(tokenCookie 로 시작하고 만료 시각이 있는 것) — 쿠키 값은 보지 않는다
export const sessionToken = (cookies, settings) =>
  settings.tokenCookie ? (cookies ?? []).find((cookie) => cookie.name.startsWith(settings.tokenCookie) && cookie.expires > 0) ?? null : null
// 브라우저 컨텍스트에 로그인 쿠키가 있나 — tokenCookie 가 없으면 쿠키가 하나라도 있으면
export const hasLoginCookie = (cookies, settings) =>
  (cookies ?? []).some((cookie) => cookie.value && (!settings.tokenCookie || cookie.name.startsWith(settings.tokenCookie)))
