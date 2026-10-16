"""화면 계층 — 아테나가 pane·탭·workspace 를 다루는 곳은 여기 하나다(scripts/screen CLI · node 쪽 scripts/lib/screen.mjs 가 이걸 부른다).

지금 화면 백엔드는 herdr 하나다. 다음 단계(③ Studio)가 같은 계약(아래 동작 · 납작한 JSON)을 구현하면 아테나 스크립트는 그대로 쓴다.
아테나 코드는 herdr 를 직접 부르지 않는다 — herdr 명령·HERDR_* 환경 변수·herdr JSON 모양을 아는 건 HerdrBackend 뿐이다
(예외: herdr 플러그인 자체를 다루는 scripts/herdr-sidebar-*.sh — scripts/screen-lint.sh 허용 목록).

백엔드 고르기 — ATHENA_SCREEN=herdr|studio|none, 없거나 auto 면:
  HERDR_ENV=1 이거나 HERDR_PANE_ID 가 있거나 herdr 명령이 있으면 herdr, 아니면 none.
  herdr pane 밖이어도 herdr 명령이 있으면 herdr 다 — 원래 스크립트가 그 자리에서 herdr 를 바로 불렀다(plan-html 의 pane current ·
  현황판의 pane list). "pane 안인가" 는 inside() 가 따로 답한다(HERDR_ENV=1 + herdr 명령 — 원래 10곳의 검사 그대로).
  studio 는 아직 없다 — 모든 동작이 unsupported 로 실패한다(③ 에서 채운다).

납작한 JSON(백엔드 모양을 감춘다 — id 는 불투명한 문자열, 부르는 쪽이 id 를 쪼개 읽지 않는다):
  Pane      {id, tab_id, workspace_id, label, cwd, foreground_cwd, focused, agent, agent_status, title}
  Tab       {id, workspace_id, label}
  Workspace {id, label, active_tab_id, focused}
  Layout    {area:{x,y,width,height}, panes:[{id, rect:{x,y,width,height}}]}
  Self      {inside, backend, pane_id, tab_id, workspace_id}
실패: 종료 코드 1 이상. 화면 계층이 낸 오류는 표준오류에 {"error": "<code>", "message": "…"}.
      백엔드(herdr)가 실패하면 그 출력·종료 코드를 그대로 흘려보낸다 — 원래 스크립트가 오류 안내에 넣던 글자가 그대로 남게

bash 에서:  "$ATHENA_DIR/scripts/screen" pane list --label "📋 현황판" --format id
파이썬에서: sys.path.insert(0, ATHENA_DIR + '/scripts/lib'); import screen
            me = screen.self_info(); panes = screen.list_panes(timeout=3)
"""
import json
import os
import shlex
import shutil
import subprocess
import sys

FEATURES_HERDR = ['agent-status', 'process-info', 'layout-geometry', 'pane-move', 'workspaces', 'herdr-sidebar']


class ScreenError(Exception):
    """code: usage · not_inside · unsupported · unavailable · backend.
    backend 오류는 백엔드가 낸 출력(stdout · stderr · 종료 코드)을 그대로 들고 있다 — CLI 가 그대로 흘려보낸다(원래 스크립트가 받던 그 글자)."""

    def __init__(self, code, message, stdout='', stderr='', returncode=1):
        super().__init__(message)
        self.code, self.message = code, message
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode or 1


def _realpath(path):
    return os.path.realpath(path) if path else ''


class Backend:
    """동작 계약. 백엔드가 못 하는 동작은 refusal() 오류로 실패한다(조용히 넘어가지 않는다)."""
    name = 'none'

    def refusal(self):
        return ScreenError('unsupported', f'{self.name} 화면 백엔드는 이 동작을 지원하지 않는다')

    def _no(self, *_args, **_kwargs):
        raise self.refusal()

    def features(self):
        return []

    def inside(self):
        return False

    def self_info(self):
        return {'inside': False, 'backend': self.name, 'pane_id': '', 'tab_id': '', 'workspace_id': ''}

    pane_current = list_panes = get_pane = layout = is_shell = read = wait_output = _no
    list_tabs = get_tab = rename_tab = close_tab = list_workspaces = get_workspace = create_workspace = _no
    split = run = send_text = send_keys = rename = swap = move = close = _no


class NoneBackend(Backend):
    """화면 계층 밖 — 터미널 하나뿐. 부르는 쪽이 원래 하던 대체 동작(nohup · 새 창 · 직접 실행 안내)을 한다."""
    name = 'none'

    def refusal(self):
        return ScreenError('not_inside', '화면 계층 밖이다(ATHENA_SCREEN=none · herdr 없음)')


class StudioBackend(Backend):
    """③ Studio 자리 — 아직 없다. 조용히 넘어가지 않고 unsupported 로 실패한다(부르는 쪽 대체 동작이 돌게)."""
    name = 'studio'

    def refusal(self):
        return ScreenError('unsupported', 'studio 화면 백엔드는 아직 없다(③ Studio 에서 구현) — ATHENA_SCREEN 을 비우면 herdr 를 쓴다')


def _pane(raw):
    # label ← label || name || title — 현황판·board.sh 가 name 까지 보던 것(herdr 0.9 는 label 만 준다)
    return {
        'id': raw.get('pane_id'), 'tab_id': raw.get('tab_id'), 'workspace_id': raw.get('workspace_id'),
        'label': raw.get('label') or raw.get('name') or raw.get('title') or None,
        'cwd': raw.get('cwd'), 'foreground_cwd': raw.get('foreground_cwd'), 'focused': bool(raw.get('focused')),
        'agent': raw.get('agent') or None, 'agent_status': raw.get('agent_status') or None,
        'title': raw.get('terminal_title_stripped') or None,
    }


def _workspace(raw):
    return {'id': raw.get('workspace_id'), 'label': raw.get('label'), 'active_tab_id': raw.get('active_tab_id'), 'focused': bool(raw.get('focused'))}


class HerdrBackend(Backend):
    name = 'herdr'

    def features(self):
        return list(FEATURES_HERDR)

    def inside(self):
        return os.environ.get('HERDR_ENV') == '1' and shutil.which('herdr') is not None

    def self_info(self):
        pane = os.environ.get('HERDR_PANE_ID', '')
        # herdr id 는 "<workspace>:<pane>" — 쪼개 읽는 건 백엔드 몫이다(monitor-pane 이 하던 그대로: ':' 가 없으면 비움)
        return {'inside': self.inside(), 'backend': 'herdr', 'pane_id': pane, 'tab_id': os.environ.get('HERDR_TAB_ID', ''),
                'workspace_id': pane.split(':')[0] if ':' in pane else ''}

    def _call(self, args, timeout=None, parse=True):
        try:
            done = subprocess.run(['herdr', *args], capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            raise ScreenError('unavailable', 'herdr 명령을 찾지 못했다')
        if done.returncode != 0:
            raise ScreenError('backend', f'herdr {" ".join(args[:2])} 실패', done.stdout, done.stderr, done.returncode)
        if not parse:
            return done.stdout
        try:
            return json.loads(done.stdout)['result']
        except (ValueError, KeyError, TypeError):
            raise ScreenError('backend', f'herdr {" ".join(args[:2])} 응답을 읽지 못했다', done.stdout, done.stderr)

    # 조회
    def pane_current(self):
        return _pane(self._call(['pane', 'current'])['pane'])

    def list_panes(self, timeout=None):
        return [_pane(raw) for raw in self._call(['pane', 'list'], timeout=timeout)['panes']]

    def get_pane(self, pane):
        return _pane(self._call(['pane', 'get', pane])['pane'])

    def layout(self, pane):
        lay = self._call(['pane', 'layout', '--pane', pane])['layout']
        return {'area': lay['area'], 'panes': [{'id': rect['pane_id'], 'rect': rect['rect']} for rect in lay['panes']]}

    def is_shell(self, pane):
        # 빈 셸(프롬프트에서 대기 — 안에서 도는 프로그램 없음)이면 True. 확인 못 하면 False — 돌고 있는 것을 건드리지 않는 쪽으로
        if not pane:
            return False
        try:
            info = self._call(['pane', 'process-info', '--pane', pane])['process_info']
        except (ScreenError, KeyError, TypeError):
            return False
        return info.get('foreground_process_group_id') == info.get('shell_pid')

    def read(self, pane, options):
        return self._call(['pane', 'read', *options, pane], parse=False)

    def wait_output(self, pane, options):
        return self._call(['pane', 'wait-output', *options, pane], parse=False)

    def list_tabs(self, workspace=None):
        tabs = [{'id': raw.get('tab_id'), 'workspace_id': raw.get('workspace_id'), 'label': raw.get('label')} for raw in self._call(['tab', 'list'])['tabs']]
        return [tab for tab in tabs if workspace is None or tab['workspace_id'] == workspace]

    def get_tab(self, tab):
        # herdr 탭 id 는 "<workspace>:<tab>" — 서버에 묻지 않고 id 에서 읽는다(athena-layout 이 하던 ${TAB%%:*} 그대로 · herdr 를 더 부르지 않게)
        return {'id': tab, 'workspace_id': tab.split(':', 1)[0], 'label': None}

    def rename_tab(self, tab, label):
        self._call(['tab', 'rename', tab, label], parse=False)

    def close_tab(self, tab):
        self._call(['tab', 'close', tab], parse=False)

    def list_workspaces(self):
        return [_workspace(raw) for raw in self._call(['workspace', 'list'])['workspaces']]

    def get_workspace(self, workspace):
        return _workspace(self._call(['workspace', 'get', workspace])['workspace'])

    def create_workspace(self, label, cwd, focus=None):
        args = ['workspace', 'create', '--label', label, '--cwd', cwd]
        if focus is not None:
            args.append('--focus' if focus else '--no-focus')
        return _workspace(self._call(args)['workspace'])

    # 바꾸기
    def split(self, target, direction, ratio=None, cwd=None, env=(), focus=None):
        # target: self = 부른 pane(모르면 포커스된 pane) · focused = 포커스된 pane · 그 밖 = pane id.
        # herdr 인자는 원래 스크립트가 쓰던 그대로 — self 는 --pane <id>, id 는 자리 인자(둘 다 herdr 에서 같은 뜻)
        if target == 'self':
            pane = os.environ.get('HERDR_PANE_ID', '')
            where = ['--pane', pane] if pane else ['--current']
        elif target == 'focused':
            where = ['--current']
        else:
            where = [target]
        args = ['pane', 'split', *where, '--direction', direction]
        if ratio is not None:
            args += ['--ratio', ratio]
        if cwd is not None:
            args += ['--cwd', cwd]
        for pair in env:
            args += ['--env', pair]
        if focus is not None:
            args.append('--focus' if focus else '--no-focus')
        return _pane(self._call(args)['pane'])

    def run(self, pane, words):
        # herdr 는 단어를 따옴표 없이 공백으로 이어 붙여 그 pane 의 셸에 한 줄로 친다 — 계약 그대로 둔다(따옴표가 필요하면 부르는 쪽이 한 줄로 만들어 넘긴다)
        self._call(['pane', 'run', pane, *words], parse=False)

    def send_text(self, pane, text):
        self._call(['pane', 'send-text', pane, text], parse=False)

    def send_keys(self, pane, keys):
        self._call(['pane', 'send-keys', pane, *keys], parse=False)

    def rename(self, pane, label):
        self._call(['pane', 'rename', pane, label], parse=False)

    def swap(self, source, target):
        self._call(['pane', 'swap', '--source-pane', source, '--target-pane', target], parse=False)

    def move(self, pane, new_tab=False, tab=None, target=None, split=None, ratio=None, focus=None):
        # 옮기면 pane id 가 바뀐다(herdr) — 돌려준 id 를 쓴다. herdr 는 같은 탭 안 이동을 못 한다(reason same_tab)
        args = ['pane', 'move', pane]
        if new_tab:
            args.append('--new-tab')
        else:
            args += ['--tab', tab, '--target-pane', target, '--split', split]
            if ratio is not None:
                args += ['--ratio', ratio]
        if focus is not None:
            args.append('--focus' if focus else '--no-focus')
        return _pane(self._call(args)['move_result']['pane'])

    def close(self, pane):
        self._call(['pane', 'close', pane], parse=False)


BACKENDS = {'herdr': HerdrBackend, 'studio': StudioBackend, 'none': NoneBackend}


def backend_name():
    name = os.environ.get('ATHENA_SCREEN', '') or 'auto'
    if name != 'auto':
        return name
    if os.environ.get('HERDR_ENV') == '1' or os.environ.get('HERDR_PANE_ID') or shutil.which('herdr'):
        return 'herdr'
    return 'none'


def get_backend():
    name = backend_name()
    if name not in BACKENDS:
        raise ScreenError('usage', f'모르는 화면 백엔드: ATHENA_SCREEN={name} (herdr · studio · none)')
    return BACKENDS[name]()


# 파이썬 훅용 짧은 이름
def self_info():
    return get_backend().self_info()


def inside():
    return get_backend().inside()


def list_panes(timeout=None):
    return get_backend().list_panes(timeout=timeout)


# ── CLI (scripts/screen) ────────────────────────────────────────────────
USAGE = """사용: scripts/screen <동작> …   (결과는 납작한 JSON · 실패면 종료 코드 1 이상)
  self [--format json|sh]                      부른 pane(환경에서 — 서버에 묻지 않음) · sh 는 eval 용 SCREEN_* 변수
  inside                                       화면 pane 안이면 0
  capabilities [--has <기능>[,<기능>…]]          백엔드 기능 목록 · --has 는 다 있으면 0
  pane current                                 서버가 정한 지금 pane(self 와 다르다 — 환경이 없으면 포커스된 pane)
  pane list [--tab T] [--workspace W] [--label L] [--cwd D] [--agent-only] [--prefer-tab T] [--prefer-workspace W]
                                               (T·W 에 self 를 쓰면 부른 pane 의 탭·workspace) · --cwd 는 cwd 나 foreground_cwd 의 실제 경로가 D 인 것
  pane get <pane> · pane layout --pane <pane> · pane is-shell <pane>(빈 셸이면 0)
  pane read <pane> [--lines N] [--source S]    출력 그대로(글자)
  pane wait-output <pane> (--match T | --regex R) [--timeout MS] [--lines N] [--source S]
  pane split --target <id|self|focused> --direction right|down [--ratio R] [--cwd D] [--env K=V]… [--focus|--no-focus]
  pane run <pane> <단어>…                      단어를 공백으로 이어 붙인 한 줄을 그 pane 셸에 친다(따옴표 없음 — herdr 계약 그대로)
  pane send-text <pane> <글> · pane send-keys <pane> <키>… (Enter · C-c) · pane rename <pane> <이름> · pane close <pane>
  pane swap <pane> <pane> · pane move <pane> (--new-tab | --tab T --target P --split right|down [--ratio R]) [--focus|--no-focus]
  tab list [--workspace W] · tab get <tab> · tab rename <tab> <이름> · tab close <tab>
  workspace list · workspace get <w> · workspace create --label L --cwd D [--focus|--no-focus]
  공통: --format json(기본) | id(첫 대상의 id 한 줄) | ids(한 줄에 하나)
  백엔드: ATHENA_SCREEN=herdr|studio|none (기본 auto)"""

VALUE_FLAGS = {'--format', '--has', '--tab', '--workspace', '--label', '--cwd', '--prefer-tab', '--prefer-workspace', '--pane',
               '--target', '--direction', '--ratio', '--env', '--split', '--lines', '--source', '--match', '--regex', '--timeout'}
BOOL_FLAGS = {'--agent-only', '--focus', '--no-focus', '--new-tab'}


def _parse(args):
    """--플래그 값 · 자리 인자. --env 는 여러 번. pane run · send-text 는 부르는 쪽에서 나눠 받는다(단어에 - 가 있어도 그대로)"""
    flags, positional, index = {}, [], 0
    while index < len(args):
        arg = args[index]
        if arg in VALUE_FLAGS:
            if index + 1 >= len(args):
                raise ScreenError('usage', f'{arg} 에 값이 없다')
            if arg == '--env':
                flags.setdefault('--env', []).append(args[index + 1])
            else:
                flags[arg] = args[index + 1]
            index += 2
        elif arg in BOOL_FLAGS:
            flags[arg] = True
            index += 1
        elif arg.startswith('--'):
            raise ScreenError('usage', f'모르는 옵션: {arg}')
        else:
            positional.append(arg)
            index += 1
    return flags, positional


def _focus(flags):
    if flags.get('--focus'):
        return True
    if flags.get('--no-focus'):
        return False
    return None


def _need(positional, count, what):
    if len(positional) < count:
        raise ScreenError('usage', f'{what} 가 없다')
    return positional


def _filter_panes(screen, panes, flags):
    me = screen.self_info()
    resolve = lambda value, key: me[key] if value == 'self' else value  # noqa: E731
    if '--tab' in flags:
        panes = [p for p in panes if p['tab_id'] == resolve(flags['--tab'], 'tab_id')]
    if '--workspace' in flags:
        panes = [p for p in panes if p['workspace_id'] == resolve(flags['--workspace'], 'workspace_id')]
    if '--label' in flags:
        panes = [p for p in panes if p['label'] == flags['--label']]
    if '--cwd' in flags:
        root = _realpath(flags['--cwd'])
        panes = [p for p in panes if (p['cwd'] and _realpath(p['cwd']) == root) or (p['foreground_cwd'] and _realpath(p['foreground_cwd']) == root)]
    if flags.get('--agent-only'):
        panes = [p for p in panes if p['agent']]
    # 우선순위는 정렬로(안정 정렬 — 같은 순위 안에서는 백엔드가 준 순서 그대로)
    if flags.get('--prefer-workspace') and resolve(flags['--prefer-workspace'], 'workspace_id'):
        want = resolve(flags['--prefer-workspace'], 'workspace_id')
        panes = sorted(panes, key=lambda p: p['workspace_id'] != want)
    if flags.get('--prefer-tab') and resolve(flags['--prefer-tab'], 'tab_id'):
        want = resolve(flags['--prefer-tab'], 'tab_id')
        panes = sorted(panes, key=lambda p: p['tab_id'] != want)
    return panes


def _dispatch(screen, words, flags, positional, raw_rest):
    """→ (출력 객체 | None, 종료 코드)"""
    op = ' '.join(words)
    if op == 'self':
        return screen.self_info(), 0
    if op == 'inside':
        return None, 0 if screen.inside() else 1
    if op == 'capabilities':
        features = screen.features()
        if '--has' in flags:
            return None, 0 if all(f in features for f in flags['--has'].split(',') if f) else 1
        return {'backend': screen.name, 'features': features}, 0
    if op == 'pane current':
        return {'pane': screen.pane_current()}, 0
    if op == 'pane list':
        return {'panes': _filter_panes(screen, screen.list_panes(), flags)}, 0
    if op == 'pane get':
        return {'pane': screen.get_pane(_need(positional, 1, 'pane')[0])}, 0
    if op == 'pane layout':
        if '--pane' not in flags:
            raise ScreenError('usage', 'pane layout --pane <pane>')
        return screen.layout(flags['--pane']), 0
    if op == 'pane is-shell':
        try:
            return None, 0 if screen.is_shell(positional[0] if positional else '') else 1
        except ScreenError:
            return None, 1   # 확인 못 하면 1 — 돌고 있는 것을 건드리지 않는 쪽으로
    if op in ('pane read', 'pane wait-output'):
        pane = _need(positional, 1, 'pane')[0]
        options = [item for key in ('--source', '--lines', '--match', '--regex', '--timeout') if key in flags for item in (key, flags[key])]
        text = (screen.read if op == 'pane read' else screen.wait_output)(pane, options)
        return {'text': text}, 0
    if op == 'pane split':
        if '--target' not in flags or '--direction' not in flags:
            raise ScreenError('usage', 'pane split --target <id|self|focused> --direction right|down')
        return {'pane': screen.split(flags['--target'], flags['--direction'], flags.get('--ratio'), flags.get('--cwd'), flags.get('--env', []), _focus(flags))}, 0
    if op == 'pane run':
        _need(raw_rest, 2, 'pane 과 명령')
        screen.run(raw_rest[0], raw_rest[1:])
        return None, 0
    if op == 'pane send-text':
        _need(raw_rest, 2, 'pane 과 글')
        screen.send_text(raw_rest[0], raw_rest[1])
        return None, 0
    if op == 'pane send-keys':
        _need(raw_rest, 2, 'pane 과 키')
        screen.send_keys(raw_rest[0], raw_rest[1:])
        return None, 0
    if op == 'pane rename':
        _need(raw_rest, 2, 'pane 과 이름')
        screen.rename(raw_rest[0], raw_rest[1])
        return None, 0
    if op == 'pane swap':
        _need(positional, 2, '두 pane')
        screen.swap(positional[0], positional[1])
        return None, 0
    if op == 'pane move':
        pane = _need(positional, 1, 'pane')[0]
        if flags.get('--new-tab'):
            return {'pane': screen.move(pane, new_tab=True, focus=_focus(flags))}, 0
        if not all(key in flags for key in ('--tab', '--target', '--split')):
            raise ScreenError('usage', 'pane move <pane> (--new-tab | --tab T --target P --split right|down [--ratio R])')
        return {'pane': screen.move(pane, tab=flags['--tab'], target=flags['--target'], split=flags['--split'], ratio=flags.get('--ratio'), focus=_focus(flags))}, 0
    if op == 'pane close':
        screen.close(_need(positional, 1, 'pane')[0])
        return None, 0
    if op == 'tab list':
        return {'tabs': screen.list_tabs(flags.get('--workspace'))}, 0
    if op == 'tab get':
        return {'tab': screen.get_tab(_need(positional, 1, 'tab')[0])}, 0
    if op == 'tab rename':
        _need(raw_rest, 2, 'tab 과 이름')
        screen.rename_tab(raw_rest[0], raw_rest[1])
        return None, 0
    if op == 'tab close':
        screen.close_tab(_need(positional, 1, 'tab')[0])
        return None, 0
    if op == 'workspace list':
        return {'workspaces': screen.list_workspaces()}, 0
    if op == 'workspace get':
        return {'workspace': screen.get_workspace(_need(positional, 1, 'workspace')[0])}, 0
    if op == 'workspace create':
        if '--label' not in flags or '--cwd' not in flags:
            raise ScreenError('usage', 'workspace create --label L --cwd D')
        return {'workspace': screen.create_workspace(flags['--label'], flags['--cwd'], _focus(flags))}, 0
    raise ScreenError('usage', f'모르는 동작: {op or "(없음)"} — scripts/screen --help')


def _print(result, fmt):
    if result is None:
        return
    if fmt == 'sh':
        sys.stdout.write(''.join(f'SCREEN_{key.upper()}={shlex.quote(str(int(value)) if isinstance(value, bool) else str(value or ""))}\n' for key, value in result.items()))
    elif fmt in ('id', 'ids'):
        if 'text' in result:
            sys.stdout.write(result['text'])
            return
        items = next((value for value in result.values() if isinstance(value, list)), None)
        if items is None:
            items = [next(iter(result.values()))] if result else []
        ids = [item.get('id') or '' for item in items if isinstance(item, dict)]
        sys.stdout.write((ids[0] if ids else '') + '\n' if fmt == 'id' else ''.join(f'{value}\n' for value in ids))
    elif 'text' in result:
        sys.stdout.write(result['text'])   # read · wait-output 은 사람·에이전트가 읽는 글자 그대로
    else:
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + '\n')


def main(argv):
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(USAGE)
        return 0 if argv else 2
    # 동작 이름(한두 단어) — pane run · send-text · rename 뒤는 손대지 않고 그대로 넘긴다(단어가 - 로 시작해도)
    count = 1 if argv[0] in ('self', 'inside', 'capabilities') else 2
    words, rest = argv[:count], argv[count:]
    raw_ops = ('pane run', 'pane send-text', 'pane send-keys', 'pane rename', 'tab rename')
    fmt = 'json'
    try:
        if ' '.join(words) in raw_ops:
            flags, positional, raw_rest = {}, [], rest
        else:
            flags, positional = _parse(rest)
            raw_rest = positional
            fmt = flags.get('--format', 'json')
            if fmt not in ('json', 'id', 'ids', 'sh'):
                raise ScreenError('usage', f'--format 은 json · id · ids · sh: {fmt}')
        screen = get_backend()
        result, code = _dispatch(screen, words, flags, positional, raw_rest)
    except ScreenError as error:
        if error.code == 'backend':
            # 백엔드가 낸 글자를 그대로 — 원래 스크립트가 받던 출력(json 일 때만 표준출력. id 는 비워 둔다 — 부르는 쪽이 오류 글을 id 로 읽지 않게)
            (sys.stdout if fmt == 'json' else sys.stderr).write(error.stdout)
            sys.stderr.write(error.stderr)
            return error.returncode
        sys.stderr.write(json.dumps({'error': error.code, 'message': error.message}, ensure_ascii=False) + '\n')
        return 2 if error.code == 'usage' else 1
    except subprocess.TimeoutExpired:
        sys.stderr.write(json.dumps({'error': 'timeout', 'message': '화면 백엔드가 제때 답하지 않았다'}, ensure_ascii=False) + '\n')
        return 1
    _print(result, fmt)
    return code
