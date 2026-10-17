// 화면 계층(node) — pane·탭·workspace 는 scripts/screen 을 불러 다룬다(herdr 를 직접 부르지 않는다).
// 계약·백엔드 고르기는 파이썬 쪽 정본 scripts/lib/screen.py 에 있다 — 여기는 부르고 JSON 을 읽기만 한다.
//   await screen(['pane', 'list'])                → { panes: [...] } · 실패면 null (바꾸는 동작은 성공하면 {})
//   screenSync(['pane', 'current'])               → { pane: {...} } · 실패면 예외
import { execFile, execFileSync } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const SCREEN = join(dirname(fileURLToPath(import.meta.url)), '..', 'screen')

const parse = (stdout) => (stdout.trim() ? JSON.parse(stdout) : {})

export const screen = (args, options = {}) =>
  new Promise((resolve) => {
    execFile(SCREEN, args, { encoding: 'utf8', timeout: 5000, maxBuffer: 16 * 1024 * 1024, ...options }, (error, stdout) => {
      if (error) return resolve(null)
      try {
        resolve(parse(stdout))
      } catch {
        resolve(null)
      }
    })
  })

export const screenSync = (args, options = {}) => parse(execFileSync(SCREEN, args, { encoding: 'utf8', ...options }))
