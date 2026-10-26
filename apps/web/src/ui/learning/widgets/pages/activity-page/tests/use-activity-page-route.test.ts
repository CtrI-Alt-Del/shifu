import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
} from '@tanstack/react-router'
import { createElement } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RestResponse } from '@/core/shared/responses/rest-response'
import { Route as activityRoute } from '@/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId'
import { learningActivityPath } from '@/constants/routes'
import type { CodeEditorProps } from '@/ui/learning/widgets/components/code-editor'
import { installDraftBrowserStorage } from './draft-browser-storage'
import type { ReactQuestionDraft } from '@/core/learning/react-question-draft/react-question-draft-store'
import {
  clearDiagnosticRun,
  setDiagnosticRun,
} from '@/ui/learning/diagnostic-run-session'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  access: vi.fn(),
  boot: vi.fn(),
  mount: vi.fn(),
  spawn: vi.fn(),
  writeFile: vi.fn(),
  mkdir: vi.fn(),
  teardown: vi.fn(),
  kill: vi.fn(),
  serverReady: undefined as undefined | ((port: number, url: string) => void),
}))
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('@tanstack/react-start', () => ({
  createStart: () => ({}),
  createMiddleware: () => ({ server: (handler: unknown) => handler }),
  createServerFn: () => {
    let validate: (data: unknown) => unknown = (data) => data
    const builder = {
      middleware: () => builder,
      validator: (validator: (data: unknown) => unknown) => {
        validate = validator
        return builder
      },
      handler:
        (handler: (context: { data: unknown }) => unknown) =>
        (context: { data: unknown }) =>
          handler({
            data: validate(context.data),
            context: { requestId: 'test-request-id' },
          } as never),
    }
    return builder
  },
}))
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://shifu.test'),
}))
vi.mock('@/middlewares/require-auth-middleware', () => ({
  requireAuthMiddleware: vi.fn(async () => ({
    displayName: 'Aluno',
    email: 'student@example.test',
  })),
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.access }),
}))
vi.mock('@/provision/auth/better-auth/better-auth-config', () => ({
  BetterAuthConfig: () => ({ identityURL: 'http://shifu.test' }),
}))
vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: () => ({ get: mocks.get, post: mocks.post }),
}))
vi.mock('@webcontainer/api', () => ({ WebContainer: { boot: mocks.boot } }))
vi.mock('@/ui/learning/widgets/components/code-editor', () => ({
  CodeEditor: ({
    files,
    selectedPath,
    editablePaths,
    onFileChange,
    readOnly,
  }: CodeEditorProps) => {
    const file = files.find(({ path }) => path === selectedPath) ?? files[0]
    return createElement('textarea', {
      'aria-label': 'Código em edição',
      value: file?.content ?? '',
      readOnly: readOnly || !editablePaths?.includes(file?.path ?? ''),
      onChange: (event: { target: { value: string } }) =>
        file && onFileChange?.(file.path, event.target.value),
    })
  },
}))

const ids = {
  goalId: '01J00000000000000000000001',
  skillId: '01J00000000000000000000002',
  competencyId: '01J00000000000000000000003',
  activityId: '01J00000000000000000000004',
}
const diagnosticRunId = '12345678-1234-4123-8123-123456789012'
const initialFiles = [
  { path: 'src/main.tsx', content: 'import App from "./App"', editable: false },
  {
    path: 'src/App.tsx',
    content: 'export default function App() { return <h1>Inicial</h1> }',
    editable: true,
  },
]
let storage: ReturnType<typeof installDraftBrowserStorage>
function draft(overrides: Partial<ReactQuestionDraft> = {}): ReactQuestionDraft {
  return {
    ...ids,
    accountId: 'route-account',
    questionKey: 'react-route',
    activityRevision: 'revision-route',
    schemaVersion: 1,
    generation: 1,
    savedAt: 1,
    tombstone: false,
    files: [{ path: 'src/App.tsx', content: 'saved source' }],
    ...overrides,
  }
}
function storeDraft(value: ReactQuestionDraft) {
  const key = [
    value.accountId,
    value.goalId,
    value.skillId,
    value.competencyId,
    value.activityId,
    value.questionKey,
    value.activityRevision,
  ].join('\u001f')
  storage.records.set(key, value)
  return key
}
function activity() {
  return {
    activity_id: ids.activityId,
    activity_revision: 'revision-route',
    title: 'Aplicação React',
    difficulty: 'easy',
    can_submit: true,
    questions: [
      {
        key: 'react-route',
        kind: 'react',
        prompt: 'Implemente uma tela.',
        initial_files: initialFiles.map((file) => ({ ...file })),
        editable_paths: ['src/App.tsx'],
        entrypoint: 'src/main.tsx',
        fixed_dependencies: [
          { name: 'react', version: '19.0.0' },
          { name: 'react-dom', version: '19.0.0' },
          { name: 'vite', version: '6.0.0' },
        ],
        permitted_commands: [{ id: 'dev', executable: 'npm', arguments: ['run', 'dev'] }],
        additional_file_policy: {
          allowed_directories: ['src'],
          allowed_extensions: ['.tsx'],
          max_files: 2,
        },
        criteria: [{ key: 'ui', name: 'Interface', weight_percentage: 100 }],
      },
    ],
  }
}
function integratedActivity() {
  const base = activity()
  const question = base.questions[0]
  if (!question) throw new Error('Expected a fixture question')
  return {
    ...base,
    title: 'Projeto React + Fastify',
    questions: [
      {
        ...question,
        kind: 'react_fastify',
        initial_files: [
          ...question.initial_files,
          { path: 'server.js', content: 'console.log("API")', editable: true },
          { path: 'index.html', content: '<div id="root"></div>', editable: false },
        ],
        editable_paths: ['src/App.tsx', 'server.js'],
        frontend_entrypoint: 'src/main.tsx',
        api_entrypoint: 'server.js',
        frontend_command_id: 'web',
        api_command_id: 'api',
        fixed_dependencies: [
          ...question.fixed_dependencies,
          { name: 'fastify', version: '5.8.4' },
        ],
        permitted_commands: [
          { id: 'web', executable: 'npm', arguments: ['run', 'dev:web'] },
          { id: 'api', executable: 'npm', arguments: ['run', 'dev:api'] },
        ],
        http_examples: [
          {
            key: 'list',
            title: 'Listar tarefas',
            method: 'GET',
            path: '/api/tasks',
            body: null,
          },
        ],
      },
    ],
  }
}
function setup() {
  const root = createRootRoute({ component: Outlet })
  Object.assign(activityRoute.options, {
    getParentRoute: () => root,
    path: '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/',
  })
  const destination = createRoute({
    getParentRoute: () => root,
    path: '/elsewhere',
    component: () => createElement('h1', null, 'Outra página'),
  })
  const login = createRoute({
    getParentRoute: () => root,
    path: '/login',
    component: () => createElement('h1', null, 'Entrar'),
  })
  const attempt = createRoute({
    getParentRoute: () => root,
    path: '/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/attempts/$attemptId',
    component: () => createElement('h1', null, 'Tentativa enviada'),
  })
  const skill = createRoute({
    getParentRoute: () => root,
    path: '/learning/goals/$goalId/skills/$skillId',
    component: () => createElement('h1', null, 'Habilidade do diagnóstico'),
  })
  const result = createRoute({
    getParentRoute: () => root,
    path: '/learning/goals/$goalId/skills/$skillId/diagnostic/result',
    component: () => createElement('h1', null, 'Resultado do diagnóstico'),
  })
  const router = createRouter({
    routeTree: root.addChildren([
      activityRoute,
      destination,
      login,
      attempt,
      skill,
      result,
    ]),
    history: createMemoryHistory({ initialEntries: [learningActivityPath(ids)] }),
  })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const view = render(
    createElement(
      QueryClientProvider,
      { client },
      createElement(RouterProvider, { router }),
    ),
  )
  return { router, ...view }
}
function selectIntegratedTab(name: string) {
  const tab = screen.getByRole('tab', { name })
  fireEvent.mouseDown(tab, { button: 0, ctrlKey: false })
  fireEvent.click(tab)
}
function httpProcess(response: unknown) {
  return {
    exit: Promise.resolve(0),
    kill: vi.fn(),
    output: new ReadableStream<string>({
      start(controller) {
        controller.enqueue(JSON.stringify(response))
        controller.close()
      },
    }),
  }
}
async function setupIntegratedPractice(
  options: {
    response?: unknown
    nodeSpawn?: (args: readonly string[]) => Promise<ReturnType<typeof httpProcess>>
  } = {},
) {
  mocks.get.mockResolvedValue(
    new RestResponse({ statusCode: 200, body: integratedActivity() }),
  )
  const normalSpawn = mocks.spawn.getMockImplementation()
  mocks.spawn.mockImplementation(async (command: string, args: readonly string[]) =>
    isHttpClientSpawn(command, args)
      ? options.nodeSpawn
        ? options.nodeSpawn(args)
        : httpProcess(
            options.response ?? {
              status: 200,
              headers: [
                { name: 'Content-Type', value: 'application/json' },
                { name: 'Set-Cookie', value: 'private' },
              ],
              body: 'response body',
              truncated: false,
            },
          )
      : normalSpawn?.(command, args),
  )
  const view = setup()
  await screen.findByRole('region', { name: 'Questão React + Fastify' })
  await waitFor(() =>
    expect(mocks.spawn).toHaveBeenCalledWith('node', [
      'node_modules/vite/bin/vite.js',
      '--host',
      '0.0.0.0',
      '--port',
      '5173',
      '--strictPort',
    ]),
  )
  act(() => {
    mocks.serverReady?.(3000, 'https://api.local.webcontainer-api.io/')
    mocks.serverReady?.(5173, 'https://frontend.local.webcontainer-api.io/')
  })
  await screen.findByTitle('Prévia isolada React + Fastify')
  return view
}
function isHttpClientSpawn(command: string, args: readonly string[]) {
  return command === 'node' && args[0] === '--input-type=module' && args.length === 4
}
function decodeHttpRequestArgument(argument: string | undefined): {
  method: string
  path: string
  body?: string
} {
  if (!argument) throw new Error('Expected the HTTP request argument')
  return JSON.parse(Buffer.from(argument, 'base64').toString('utf8'))
}
function httpCalls() {
  return mocks.spawn.mock.calls.filter(([command, args]) =>
    isHttpClientSpawn(command, args),
  )
}
describe('ActivityPage routed React composition', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.serverReady = undefined
    mocks.access.mockResolvedValue({
      accountId: 'route-account',
      accessToken: 'route-token',
    })
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 200, body: activity() }))
    mocks.mount.mockResolvedValue(undefined)
    mocks.mkdir.mockResolvedValue(undefined)
    mocks.writeFile.mockResolvedValue(undefined)
    mocks.spawn.mockImplementation(async (_command: string, args: readonly string[]) => {
      if (_command === 'node' && args[0] === '--input-type=module' && args.length === 3)
        return { exit: Promise.resolve(0), kill: vi.fn() }
      if (args[0] === 'install')
        return {
          exit: Promise.resolve(0),
          kill: mocks.kill,
          output: new ReadableStream<string>({
            start(controller) {
              controller.close()
            },
          }),
        }
      let finish: (code: number) => void = () => undefined
      const exit = new Promise<number>((resolve) => {
        finish = resolve
      })
      return {
        exit,
        kill: () => {
          mocks.kill()
          finish(0)
        },
        output: new ReadableStream<string>({
          start(controller) {
            controller.close()
          },
        }),
      }
    })
    mocks.boot.mockResolvedValue({
      mount: mocks.mount,
      spawn: mocks.spawn,
      fs: { mkdir: mocks.mkdir, writeFile: mocks.writeFile },
      teardown: mocks.teardown,
      on: (_event: string, handler: (port: number, url: string) => void) => {
        if (_event === 'server-ready') mocks.serverReady = handler
        return () => undefined
      },
    })
    vi.stubGlobal('isSecureContext', true)
    vi.stubGlobal('crossOriginIsolated', true)
    storage = installDraftBrowserStorage()
    vi.stubGlobal('scrollTo', vi.fn())
    vi.stubGlobal('matchMedia', () => ({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
    HTMLElement.prototype.scrollIntoView = vi.fn()
  })
  afterEach(() => {
    vi.useRealTimers()
    cleanup()
    clearDiagnosticRun(ids.goalId, ids.skillId)
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('loads the actual route and starts isolated React practice with fixed dependencies', async () => {
    const { unmount, router } = setup()
    await screen.findByRole('region', { name: 'Questão React' })
    await waitFor(() => expect(mocks.spawn).toHaveBeenCalledWith('npm', ['run', 'dev']))
    expect(router.state.location.pathname).toContain(ids.activityId)
    expect(mocks.get).toHaveBeenCalledWith(learningActivityPath(ids), {
      headers: { Authorization: 'Bearer route-token' },
    })
    expect(mocks.mount).toHaveBeenCalledWith(
      expect.objectContaining({
        'package.json': {
          file: { contents: expect.stringContaining('"react":"19.0.0"') },
        },
        'index.html': { file: { contents: expect.stringContaining('/src/main.tsx') } },
      }),
    )
    act(() => mocks.serverReady?.(5173, 'https://preview.local.webcontainer-api.io/'))
    expect(await screen.findByTitle('Prévia isolada da aplicação React')).toHaveAttribute(
      'src',
      'https://preview.local.webcontainer-api.io/',
    )
    fireEvent.click(screen.getByRole('treeitem', { name: 'App.tsx' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Código em edição' }), {
      target: { value: 'export default function App() { return <h1>Alterado</h1> }' },
    })
    await waitFor(() =>
      expect(mocks.writeFile).toHaveBeenCalledWith(
        'src/App.tsx',
        expect.stringContaining('Alterado'),
      ),
    )
    fireEvent.change(screen.getByRole('textbox', { name: 'Caminho do novo arquivo' }), {
      target: { value: 'src/Badge.tsx' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Criar' }))
    await waitFor(() => expect(mocks.writeFile).toHaveBeenCalledWith('src/Badge.tsx', ''))
    unmount()
    expect(mocks.kill).toHaveBeenCalled()
    expect(mocks.teardown).toHaveBeenCalledOnce()
  })

  it.each([
    'http://preview.webcontainer-api.io/',
    'https://untrusted.example/',
    'http://localhost:3000/',
    'not-a-url',
  ])('keeps an unsafe preview origin out of the page: %s', async (url) => {
    setup()
    await waitFor(() => expect(mocks.serverReady).toBeTypeOf('function'))
    act(() => mocks.serverReady?.(5173, url))
    await waitFor(() =>
      expect(
        screen.queryByTitle('Prévia isolada da aplicação React'),
      ).not.toBeInTheDocument(),
    )
    fireEvent.click(screen.getByRole('treeitem', { name: 'App.tsx' }))
    expect(screen.getByRole('textbox', { name: 'Código em edição' })).not.toHaveAttribute(
      'readonly',
    )
  })

  it('keeps editing available when the browser cannot isolate a practice runtime', async () => {
    vi.stubGlobal('crossOriginIsolated', false)
    setup()
    await screen.findByRole('textbox', { name: 'Código em edição' })
    await waitFor(() =>
      expect(screen.getByText(/Prévia indisponível neste navegador/)).toBeVisible(),
    )
    expect(mocks.boot).not.toHaveBeenCalled()
  })

  it('keeps the activity available when dependency installation fails', async () => {
    mocks.spawn.mockResolvedValue({ exit: Promise.resolve(1), kill: mocks.kill })
    setup()
    await waitFor(() => expect(mocks.teardown).toHaveBeenCalledOnce())
    expect(screen.getByRole('textbox', { name: 'Código em edição' })).toBeVisible()
    expect(
      screen.queryByTitle('Prévia isolada da aplicação React'),
    ).not.toBeInTheDocument()
  })

  it('does not start a practice server after leaving while dependency installation is pending', async () => {
    let finishInstall: (exitCode: number) => void = () => undefined
    mocks.spawn.mockImplementation(async (_command: string, args: readonly string[]) =>
      args[0] === 'install'
        ? {
            exit: new Promise<number>((resolve) => {
              finishInstall = resolve
            }),
            kill: mocks.kill,
          }
        : { exit: new Promise<number>(() => undefined), kill: mocks.kill },
    )

    const { unmount } = setup()
    await waitFor(() =>
      expect(mocks.spawn).toHaveBeenCalledWith(
        'npm',
        ['install', '--ignore-scripts', '--no-audit', '--no-fund'],
        { output: false },
      ),
    )
    unmount()
    expect(mocks.teardown).toHaveBeenCalledOnce()

    await act(async () => finishInstall(0))

    expect(mocks.spawn).toHaveBeenCalledTimes(1)
    expect(mocks.serverReady).toBeUndefined()
  })

  it('confirms unsent navigation and preserves the current route after cancelling', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { router } = setup()
    await screen.findByRole('textbox', { name: 'Código em edição' })
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled(),
    )
    fireEvent.click(screen.getByRole('treeitem', { name: 'App.tsx' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Código em edição' }), {
      target: { value: 'unsent source' },
    })
    act(() => {
      void router.navigate({ to: '/elsewhere' as never })
    })
    await waitFor(() =>
      expect(confirm).toHaveBeenCalledWith(
        'Suas respostas não foram enviadas. Deseja sair desta Atividade?',
      ),
    )
    expect(router.state.location.pathname).toContain(ids.activityId)
    confirm.mockReturnValue(true)
    act(() => {
      void router.navigate({ to: '/elsewhere' as never })
    })
    expect(await screen.findByRole('heading', { name: 'Outra página' })).toBeVisible()
    expect(router.state.location.pathname).toBe('/elsewhere')
  })

  it('returns to login when the authenticated session has expired before loading', async () => {
    mocks.access.mockResolvedValue(null)
    const { router } = setup()
    expect(await screen.findByRole('heading', { name: 'Entrar' })).toBeVisible()
    expect(router.state.location.pathname).toBe('/login')
    expect(mocks.post).not.toHaveBeenCalled()
  })

  it('returns a diagnostic attempt to its Skill when the activity reports an unresolved attempt', async () => {
    setDiagnosticRun(ids.goalId, ids.skillId, diagnosticRunId)
    mocks.get.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 200,
          body: path.endsWith('/diagnostic')
            ? { status: 'diagnosing', runState: 'active', activitySequence: [] }
            : {
                ...activity(),
                is_diagnostic: true,
                unresolved_attempt_id: ids.activityId,
              },
        }),
    )

    const { router } = setup()

    expect(
      await screen.findByRole('heading', { name: 'Habilidade do diagnóstico' }),
    ).toBeVisible()
    expect(router.state.location.pathname).toBe(
      `/learning/goals/${ids.goalId}/skills/${ids.skillId}`,
    )
    expect(mocks.get).toHaveBeenCalledWith(learningActivityPath(ids), {
      headers: {
        Authorization: 'Bearer route-token',
        'X-Diagnostic-Run-Id': diagnosticRunId,
      },
    })
  })

  it('opens the consolidated result when the authoritative diagnostic is complete', async () => {
    setDiagnosticRun(ids.goalId, ids.skillId, diagnosticRunId)
    mocks.get.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 200,
          body: path.endsWith('/diagnostic')
            ? { status: 'completed', runState: 'completed', activitySequence: [] }
            : { ...activity(), is_diagnostic: true },
        }),
    )

    const { router } = setup()

    expect(
      await screen.findByRole('heading', { name: 'Resultado do diagnóstico' }),
    ).toBeVisible()
    expect(router.state.location.pathname).toContain('/diagnostic/result')
  })

  it('navigates to the persisted attempt after assessing and submitting the frozen React answer', async () => {
    mocks.post.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 200,
          body: path.includes('preliminary-evaluations')
            ? {
                status: 'conclusive',
                score: 100,
                criteria: [
                  {
                    key: 'ui',
                    weight_percentage: 100,
                    level: '100',
                    comment_id: 'correct',
                    comment: 'Interface correta',
                  },
                ],
              }
            : {
                attempt_id: '01J00000000000000000000005',
                status: 'pending',
                result_url: '/result',
              },
        }),
    )
    const { router } = setup()
    await screen.findByRole('textbox', { name: 'Código em edição' })
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled(),
    )
    fireEvent.click(screen.getByRole('button', { name: 'Avaliar questão' }))
    await screen.findByText('Interface correta')
    expect(screen.getByRole('textbox', { name: 'Código em edição' })).toHaveAttribute(
      'readonly',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Enviar atividade' }))
    expect(
      await screen.findByRole('heading', { name: 'Tentativa enviada' }),
    ).toBeVisible()
    expect(router.state.location.pathname).toContain('01J00000000000000000000005')
    expect(mocks.post.mock.calls[1]?.[1]).toMatchObject({
      activity_revision: 'revision-route',
      answers: [{ kind: 'react', question_key: 'react-route' }],
    })
  })

  it('restores the account draft and synchronizes a later remote edit into a fresh isolated preview', async () => {
    const key = storeDraft(draft())
    setup()
    await waitFor(() =>
      expect(screen.getByRole('textbox', { name: 'Código em edição' })).toHaveValue(
        'saved source',
      ),
    )
    await waitFor(() => expect(mocks.boot).toHaveBeenCalledOnce())
    const remote = draft({
      generation: 20,
      files: [{ path: 'src/App.tsx', content: 'remote source' }],
    })
    storage.records.set(key, remote)
    act(() =>
      storage.publish({ key, generation: 20, tombstone: false, sender: 'remote-tab' }),
    )
    await waitFor(() =>
      expect(screen.getByRole('textbox', { name: 'Código em edição' })).toHaveValue(
        'remote source',
      ),
    )
    await waitFor(() => expect(mocks.boot).toHaveBeenCalledTimes(2))
    expect(mocks.teardown).toHaveBeenCalledOnce()
    expect(mocks.mount.mock.calls.at(-1)?.[0]).toMatchObject({
      src: { directory: { 'App.tsx': { file: { contents: 'remote source' } } } },
    })
  })

  it('invalidates a deleted activity draft received from another tab', async () => {
    const key = storeDraft(draft())
    setup()
    await waitFor(() => expect(mocks.boot).toHaveBeenCalledOnce())
    storage.records.set(key, draft({ generation: 20, tombstone: true, files: [] }))
    act(() =>
      storage.publish({ key, generation: 20, tombstone: true, sender: 'remote-tab' }),
    )
    expect(
      await screen.findByText(
        'Rascunho invalidado. Atualize a Atividade para validar novamente.',
      ),
    ).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeDisabled()
    expect(screen.getByRole('textbox', { name: 'Código em edição' })).toHaveAttribute(
      'readonly',
    )
    await waitFor(() => expect(mocks.teardown).toHaveBeenCalledOnce())
  })

  it('purges obsolete revisions and removed questions while preserving other accounts', async () => {
    const oldKey = storeDraft(draft({ activityRevision: 'old-revision' }))
    const removedKey = storeDraft(draft({ questionKey: 'removed-question' }))
    const other = draft({ accountId: 'other-account' })
    const otherKey = storeDraft(other)
    setup()
    await waitFor(() =>
      expect(storage.records.get(oldKey)).toMatchObject({
        tombstone: true,
        files: [],
        generation: 2,
      }),
    )
    expect(storage.records.get(removedKey)).toMatchObject({
      tombstone: true,
      files: [],
      generation: 2,
    })
    expect(storage.records.get(otherKey)).toEqual(other)
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
  })

  it('invalidates every draft for an activity when the authenticated request returns private absence', async () => {
    const activeKey = storeDraft(draft())
    const oldRevisionKey = storeDraft(draft({ activityRevision: 'old-revision' }))
    const otherKey = storeDraft(draft({ accountId: 'another-account' }))
    mocks.get.mockResolvedValue(
      new RestResponse({ statusCode: 404, errorMessage: 'Atividade indisponível' }),
    )

    setup()

    expect(
      await screen.findByRole('heading', { name: 'Atividade não encontrada' }),
    ).toBeVisible()
    await waitFor(() =>
      expect(storage.records.get(activeKey)).toMatchObject({
        tombstone: true,
        generation: 2,
        files: [],
      }),
    )
    expect(storage.records.get(oldRevisionKey)).toMatchObject({
      tombstone: true,
      generation: 2,
      files: [],
    })
    expect(storage.records.get(otherKey)).toEqual(draft({ accountId: 'another-account' }))
    expect(mocks.boot).not.toHaveBeenCalled()
  })

  it('keeps the activity editor available when its signed React project lacks an authorized dev command', async () => {
    const unavailable = activity()
    unavailable.questions[0].permitted_commands = [
      { id: 'build', executable: 'npm', arguments: ['run', 'build'] },
    ]
    mocks.get.mockResolvedValue(new RestResponse({ statusCode: 200, body: unavailable }))

    setup()

    expect(await screen.findByRole('textbox', { name: 'Código em edição' })).toBeVisible()
    await waitFor(() =>
      expect(screen.getByRole('log')).toHaveTextContent(
        'Prévia indisponível: o comando de desenvolvimento não foi autorizado.',
      ),
    )
    expect(mocks.boot).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
  })

  it.each([
    {
      reason: 'a traversal path',
      change: (question: ReturnType<typeof activity>['questions'][number]) => {
        question.initial_files[1].path = 'src/../Secrets.tsx'
      },
    },
    {
      reason: 'a duplicate path',
      change: (question: ReturnType<typeof activity>['questions'][number]) => {
        question.initial_files.push({
          path: 'src/App.tsx',
          content: 'duplicate source',
          editable: true,
        })
      },
    },
    {
      reason: 'a missing entrypoint',
      change: (question: ReturnType<typeof activity>['questions'][number]) => {
        question.entrypoint = 'src/Missing.tsx'
      },
    },
    {
      reason: 'a source larger than the local sandbox limit',
      change: (question: ReturnType<typeof activity>['questions'][number]) => {
        question.initial_files[1].content = 'x'.repeat(256 * 1024 + 1)
      },
    },
    {
      reason: 'a missing React dependency',
      change: (question: ReturnType<typeof activity>['questions'][number]) => {
        question.fixed_dependencies = question.fixed_dependencies.filter(
          ({ name }) => name !== 'react',
        )
      },
    },
    {
      reason: 'an invalid additional-file policy',
      change: (question: ReturnType<typeof activity>['questions'][number]) => {
        question.additional_file_policy.max_files = 0
      },
    },
  ])('does not boot an invalid signed React project with $reason', async ({ change }) => {
    const invalidActivity = activity()
    change(invalidActivity.questions[0])
    mocks.get.mockResolvedValue(
      new RestResponse({ statusCode: 200, body: invalidActivity }),
    )

    setup()

    await waitFor(() =>
      expect(screen.getByRole('log')).toHaveTextContent(
        'A prévia está indisponível. Continue editando e avaliando.',
      ),
    )
    expect(mocks.boot).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
  })

  it('keeps assessment available after a sandbox boot error', async () => {
    mocks.boot.mockRejectedValueOnce(new Error('WebContainer unavailable'))

    setup()

    await waitFor(() =>
      expect(screen.getByRole('log')).toHaveTextContent(
        'A prévia está indisponível. Continue editando e avaliando.',
      ),
    )
    expect(screen.getByRole('textbox', { name: 'Código em edição' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
  })

  it.each(['transaction-error', 'abort'] as const)(
    'reports a local save failure after an IndexedDB %s while retaining the answer',
    async (event) => {
      setup()
      await screen.findByRole('textbox', { name: 'Código em edição' })
      await waitFor(() =>
        expect(screen.getByText('Rascunho salvo neste navegador')).toBeVisible(),
      )
      storage.rejectNext('readwrite', 'get', event)
      fireEvent.click(screen.getByRole('treeitem', { name: 'App.tsx' }))
      fireEvent.change(screen.getByRole('textbox', { name: 'Código em edição' }), {
        target: { value: 'A resposta permanece visível após falha local' },
      })

      expect(
        await screen.findByText(
          'Não foi possível salvar localmente. Sua resposta não foi enviada.',
        ),
      ).toBeVisible()
      expect(screen.getByRole('textbox', { name: 'Código em edição' })).toHaveValue(
        'A resposta permanece visível após falha local',
      )
    },
  )

  it('keeps assessment available when the browser cannot open the draft database', async () => {
    storage.rejectNext('open', 'open', 'request-error')

    setup()

    expect(await screen.findByRole('textbox', { name: 'Código em edição' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
    expect(
      await screen.findByText(
        'Não foi possível salvar localmente. Sua resposta não foi enviada.',
      ),
    ).toBeVisible()
  })

  it('preserves an authorized activity when stale-draft cleanup aborts locally', async () => {
    storage.rejectNext('readwrite', 'cursor', 'abort')

    setup()

    expect(await screen.findByRole('textbox', { name: 'Código em edição' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
    expect(
      await screen.findByText(
        'Não foi possível salvar localmente. Sua resposta não foi enviada.',
      ),
    ).toBeVisible()
  })

  it('does not restore a tombstoned answer when clearing its local marker aborts', async () => {
    storeDraft(draft({ tombstone: true, files: [] }))
    storage.rejectNext('readwrite', 'get', 'abort')

    setup()

    expect(
      await screen.findByRole('textbox', { name: 'Código em edição' }),
    ).not.toHaveValue('saved source')
    expect(
      await screen.findByText(
        'Rascunho invalidado. Atualize a Atividade para validar novamente.',
      ),
    ).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeDisabled()
  })

  it('keeps private absence authoritative when invalidating its local drafts fails', async () => {
    storeDraft(draft())
    storage.rejectNext('readwrite', 'cursor', 'transaction-error')
    mocks.get.mockResolvedValue(
      new RestResponse({ statusCode: 404, errorMessage: 'Atividade indisponível' }),
    )

    setup()

    expect(
      await screen.findByRole('heading', { name: 'Atividade não encontrada' }),
    ).toBeVisible()
    expect(mocks.boot).not.toHaveBeenCalled()
  })

  it('removes the preview and explains when the isolated development server exits', async () => {
    let finishServer: (exitCode: number) => void = () => undefined
    mocks.spawn.mockImplementation(async (_command: string, args: readonly string[]) =>
      args[0] === 'install'
        ? {
            exit: Promise.resolve(0),
            kill: mocks.kill,
            output: new ReadableStream<string>({
              start(controller) {
                controller.close()
              },
            }),
          }
        : {
            exit: new Promise<number>((resolve) => {
              finishServer = resolve
            }),
            kill: mocks.kill,
            output: new ReadableStream<string>({
              start(controller) {
                controller.enqueue('Servidor iniciado.\n')
                controller.close()
              },
            }),
          },
    )

    setup()
    await waitFor(() => expect(mocks.serverReady).toBeTypeOf('function'))
    act(() => mocks.serverReady?.(5173, 'https://preview.local.webcontainer-api.io/'))
    expect(await screen.findByTitle('Prévia isolada da aplicação React')).toBeVisible()
    expect(screen.getByRole('log')).toHaveTextContent('Servidor iniciado.')

    act(() => finishServer(1))

    await waitFor(() =>
      expect(
        screen.queryByTitle('Prévia isolada da aplicação React'),
      ).not.toBeInTheDocument(),
    )
    expect(screen.getByRole('log')).toHaveTextContent(
      'Servidor de prática encerrado (código 1).',
    )
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
  })

  it.each(['invalid-file', 'corrupt-record', 'tombstone'])(
    'reopens the current authorized question without restoring a %s draft',
    async (kind) => {
      const value = draft(
        kind === 'invalid-file'
          ? { files: [{ path: 'package.json', content: 'unsafe source' }] }
          : kind === 'tombstone'
            ? { tombstone: true, files: [] }
            : { schemaVersion: 0 as 1 },
      )
      const key = storeDraft(value)
      setup()
      await waitFor(() =>
        expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled(),
      )
      expect(storage.records.get(key)).toMatchObject({
        tombstone: false,
        generation: kind === 'tombstone' ? 2 : 3,
      })
      expect(screen.getByRole('textbox', { name: 'Código em edição' })).not.toHaveValue(
        'unsafe source',
      )
      expect(
        screen.getByText(/Rascunho salvo neste navegador|Salvando neste navegador/),
      ).toBeVisible()
    },
  )
  it('runs the integrated routed composition with separate API/React readiness, manual HTTP and editable files', async () => {
    mocks.get.mockResolvedValue(
      new RestResponse({ statusCode: 200, body: integratedActivity() }),
    )
    const normalSpawn = mocks.spawn.getMockImplementation()
    mocks.spawn.mockImplementation(async (command: string, args: readonly string[]) => {
      if (isHttpClientSpawn(command, args))
        return {
          exit: Promise.resolve(0),
          kill: mocks.kill,
          output: new ReadableStream<string>({
            start(controller) {
              controller.enqueue(
                JSON.stringify({
                  status: 200,
                  headers: [
                    { name: 'Content-Type', value: 'application/json' },
                    { name: 'Set-Cookie', value: 'private' },
                  ],
                  body: '[{"id":1}]',
                  truncated: false,
                }),
              )
              controller.close()
            },
          }),
        }
      return normalSpawn?.(command, args)
    })
    const { unmount, router } = setup()
    await screen.findByRole('region', { name: 'Questão React + Fastify' })
    await waitFor(() =>
      expect(mocks.spawn).toHaveBeenCalledWith('node', [
        'node_modules/vite/bin/vite.js',
        '--host',
        '0.0.0.0',
        '--port',
        '5173',
        '--strictPort',
      ]),
    )
    expect(mocks.spawn).toHaveBeenCalledWith('node', ['--watch', './server.js'])
    expect(mocks.spawn).toHaveBeenCalledWith('npm', [
      'install',
      '--ignore-scripts',
      '--no-audit',
      '--no-fund',
    ])
    expect(mocks.mount).toHaveBeenCalledWith(
      expect.objectContaining({
        'package.json': { file: { contents: expect.stringContaining('fastify') } },
        'index.html': { file: { contents: expect.stringContaining('root') } },
      }),
    )
    act(() => mocks.serverReady?.(3000, 'https://api.local.webcontainer-api.io/'))
    expect(screen.queryByTitle('Prévia isolada React + Fastify')).not.toBeInTheDocument()
    act(() => mocks.serverReady?.(5173, 'https://frontend.local.webcontainer-api.io/'))
    const preview = await screen.findByTitle('Prévia isolada React + Fastify')
    expect(preview).toHaveAttribute('src', 'https://frontend.local.webcontainer-api.io/')
    expect(preview).toHaveAttribute('sandbox', 'allow-scripts allow-same-origin')
    expect(preview).toHaveAttribute('referrerpolicy', 'no-referrer')
    fireEvent.mouseDown(screen.getByRole('tab', { name: 'HTTP' }), {
      button: 0,
      ctrlKey: false,
    })
    fireEvent.click(screen.getByRole('tab', { name: 'HTTP' }))
    expect(httpCalls()).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' }))
    await screen.findByText('Status HTTP 200')
    expect(screen.getByText('[{"id":1}]')).toBeVisible()
    const httpCall = httpCalls()[0]
    expect(decodeHttpRequestArgument(httpCall?.[1]?.at(-1))).toEqual({
      method: 'GET',
      path: '/api/tasks',
    })
    fireEvent.mouseDown(screen.getByRole('tab', { name: 'Arquivos' }), {
      button: 0,
      ctrlKey: false,
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Arquivos' }))
    fireEvent.click(screen.getByRole('treeitem', { name: 'App.tsx' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Código em edição' }), {
      target: { value: 'frontend edited' },
    })
    await waitFor(() =>
      expect(mocks.writeFile).toHaveBeenCalledWith('src/App.tsx', 'frontend edited'),
    )
    expect(httpCalls()).toHaveLength(1)
    fireEvent.change(screen.getByRole('textbox', { name: 'Caminho do novo arquivo' }), {
      target: { value: 'src/Badge.tsx' },
    })
    expect(screen.getAllByRole('button', { name: 'Novo arquivo' })).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: 'Novo arquivo' }))
    await waitFor(() => expect(mocks.writeFile).toHaveBeenCalledWith('src/Badge.tsx', ''))
    fireEvent.change(screen.getByRole('textbox', { name: 'Caminho do novo arquivo' }), {
      target: { value: 'package.json' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Novo arquivo' }))
    expect(screen.getByRole('alert')).toHaveTextContent('fora da política')
    expect(mocks.writeFile).not.toHaveBeenCalledWith('package.json', expect.anything())
    expect(router.state.location.pathname).toContain(ids.activityId)
    unmount()
    expect(mocks.kill).toHaveBeenCalled()
    expect(mocks.teardown).toHaveBeenCalledOnce()
  })

  it('preserves an integrated preliminary snapshot on inconclusive retry and submits the same files', async () => {
    mocks.get.mockResolvedValue(
      new RestResponse({ statusCode: 200, body: integratedActivity() }),
    )
    let preliminaryCalls = 0
    mocks.post.mockImplementation(
      async (path: string) =>
        new RestResponse({
          statusCode: 200,
          body: path.includes('preliminary-evaluations')
            ? {
                status: ++preliminaryCalls === 1 ? 'inconclusive' : 'conclusive',
                score: preliminaryCalls === 1 ? null : 100,
                criteria: [
                  {
                    key: 'ui',
                    weight_percentage: 100,
                    level: '100',
                    comment_id: 'correct',
                    comment: 'Integração correta',
                  },
                ],
              }
            : {
                attempt_id: '01J00000000000000000000005',
                status: 'pending',
                result_url: '/result',
              },
        }),
    )
    const { router } = setup()
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled(),
    )
    fireEvent.mouseDown(screen.getByRole('tab', { name: 'Arquivos' }), {
      button: 0,
      ctrlKey: false,
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Arquivos' }))
    fireEvent.click(screen.getByRole('treeitem', { name: 'App.tsx' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Código em edição' }), {
      target: { value: 'frozen frontend' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Avaliar questão' }))
    await screen.findByRole('button', { name: 'Reavaliar resposta' })
    const first = mocks.post.mock.calls[0]?.[1]
    expect(first).toMatchObject({
      answer: {
        kind: 'react_fastify',
        files: expect.arrayContaining([
          { path: 'src/App.tsx', content: 'frozen frontend' },
          { path: 'server.js', content: 'console.log("API")' },
        ]),
      },
    })
    expect(screen.getByRole('textbox', { name: 'Código em edição' })).toHaveAttribute(
      'readonly',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Reavaliar resposta' }))
    await screen.findByRole('button', { name: 'Enviar atividade' })
    expect(mocks.post.mock.calls[1]?.[1]).toEqual(first)
    fireEvent.click(screen.getByRole('button', { name: 'Enviar atividade' }))
    await screen.findByRole('heading', { name: 'Tentativa enviada' })
    expect(mocks.post.mock.calls[2]?.[1]).toMatchObject({
      answers: [expect.objectContaining({ kind: 'react_fastify' })],
    })
    expect(router.state.location.pathname).toContain('01J00000000000000000000005')
  })
  it.each(['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'] as const)(
    'sends only an explicit %s request and preserves the generated client isolation',
    async (method) => {
      await setupIntegratedPractice()
      selectIntegratedTab('HTTP')
      fireEvent.click(screen.getByRole('button', { name: method }))
      if (method !== 'GET' && method !== 'HEAD')
        fireEvent.change(screen.getByRole('textbox', { name: 'Corpo da requisição' }), {
          target: { value: '{"done":true}' },
        })
      expect(httpCalls()).toHaveLength(0)
      fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' }))
      await screen.findByText('Status HTTP 200')
      expect(httpCalls()).toHaveLength(1)
      const args = httpCalls()[0]?.[1]
      expect(decodeHttpRequestArgument(args?.at(-1))).toEqual({
        method,
        path: '/api/tasks',
        ...(method === 'GET' || method === 'HEAD' ? {} : { body: '{"done":true}' }),
      })
      expect(args?.[2]).toContain("hostname: '127.0.0.1', port: 3000, path: request.path")
      expect(args?.[2]).toContain('method: request.method, headers, agent: false')
      expect(args?.[2]).toContain(
        "headers['content-length'] = Buffer.byteLength(request.body, 'utf8')",
      )
      expect(JSON.stringify(decodeHttpRequestArgument(args?.at(-1)))).not.toContain(
        'route-token',
      )
      expect(screen.queryByText('private')).not.toBeInTheDocument()
    },
  )
  it.each(['GET', 'HEAD'] as const)(
    'omits a previously entered body when switching to %s',
    async (method) => {
      await setupIntegratedPractice()
      selectIntegratedTab('HTTP')
      fireEvent.click(screen.getByRole('button', { name: 'PATCH' }))
      fireEvent.change(screen.getByRole('textbox', { name: 'Corpo da requisição' }), {
        target: { value: 'must not be sent' },
      })
      fireEvent.click(screen.getByRole('button', { name: method }))
      expect(
        screen.queryByRole('textbox', { name: 'Corpo da requisição' }),
      ).not.toBeInTheDocument()
      fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' }))
      await screen.findByText('Status HTTP 200')
      expect(decodeHttpRequestArgument(httpCalls()[0]?.[1]?.at(-1))).toEqual({
        method,
        path: '/api/tasks',
      })
    },
  )
  it.each([
    '/learning',
    'https://shifu.test/api/tasks',
    '//outside.test/api/tasks',
    '/api/../learning',
    '/api/%2e%2e/learning',
    '/api/%252e%252e/learning',
    '/api/%25252e%25252e/learning',
    '/api/tasks#secret',
    '/api/\\outside',
    '/api/tasks%00',
    '/api/tasks%0a',
    '/apix/tasks',
  ])('rejects an HTTP target outside the project boundary: %s', async (path) => {
    await setupIntegratedPractice()
    selectIntegratedTab('HTTP')
    fireEvent.change(screen.getByRole('textbox', { name: 'Rota da API' }), {
      target: { value: path },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' }))
    await screen.findByRole('alert')
    expect(httpCalls()).toHaveLength(0)
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
  })
  it.each([
    { size: 65536, accepted: true },
    { size: 65537, accepted: false },
  ])(
    'enforces the exact 64 KiB request boundary at $size bytes',
    async ({ size, accepted }) => {
      await setupIntegratedPractice()
      selectIntegratedTab('HTTP')
      fireEvent.click(screen.getByRole('button', { name: 'PATCH' }))
      fireEvent.change(screen.getByRole('textbox', { name: 'Corpo da requisição' }), {
        target: { value: 'a'.repeat(size) },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' }))
      if (accepted) {
        await screen.findByText('Status HTTP 200')
        expect(decodeHttpRequestArgument(httpCalls()[0]?.[1]?.at(-1)).body).toHaveLength(
          size,
        )
      } else {
        await screen.findByRole('alert')
        expect(httpCalls()).toHaveLength(0)
      }
    },
  )
  it.each([
    { size: 1048576, truncated: false },
    { size: 1048577, truncated: true },
  ])('caps and labels an API response of $size bytes', async ({ size, truncated }) => {
    await setupIntegratedPractice({
      response: {
        status: 200,
        headers: [{ name: 'Set-Cookie', value: 'private' }],
        body: 'a'.repeat(size),
        truncated: false,
      },
    })
    selectIntegratedTab('HTTP')
    fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' }))
    await screen.findByText('Status HTTP 200')
    const panel = screen.getByRole('region', { name: 'Requisições HTTP' })
    expect(panel.querySelector('pre')?.textContent).toHaveLength(1048576)
    if (truncated)
      expect(screen.getByText('Resposta truncada no limite de 1 MB.')).toBeVisible()
    else
      expect(
        screen.queryByText('Resposta truncada no limite de 1 MB.'),
      ).not.toBeInTheDocument()
    expect(panel).not.toHaveTextContent('private')
  })
  it('returns a redirect status without another API request or credential destination', async () => {
    await setupIntegratedPractice({
      response: {
        status: 302,
        headers: [
          { name: 'Location', value: 'https://shifu.test/private' },
          { name: 'Set-Cookie', value: 'private' },
        ],
        body: 'redirect',
        truncated: false,
      },
    })
    selectIntegratedTab('HTTP')
    fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' }))
    await screen.findByText('Status HTTP 302')
    expect(httpCalls()).toHaveLength(1)
    expect(httpCalls()[0]?.[1]?.[2]?.match(/requestHttp\(\{/g)).toHaveLength(1)
    expect(httpCalls()[0]?.[1]?.[2]).not.toContain('response.headers.location')
    expect(
      screen.getByRole('region', { name: 'Requisições HTTP' }),
    ).not.toHaveTextContent('https://shifu.test/private')
  })
  it('kills a late spawned request after cancellation and never renders its stale result', async () => {
    let resolveSpawn: (process: ReturnType<typeof httpProcess>) => void = () => undefined
    await setupIntegratedPractice({
      nodeSpawn: () =>
        new Promise((resolve) => {
          resolveSpawn = resolve
        }),
    })
    selectIntegratedTab('HTTP')
    fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' }))
    await waitFor(() => expect(httpCalls()).toHaveLength(1))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar requisição' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Requisição cancelada')
    const process = httpProcess({
      status: 200,
      headers: [],
      body: 'stale result',
      truncated: false,
    })
    await act(async () => resolveSpawn(process))
    expect(process.kill).toHaveBeenCalled()
    expect(screen.queryByText('stale result')).not.toBeInTheDocument()
  })
  it('times out a pending spawn at ten seconds, preserving the answer and rejecting late output', async () => {
    let resolveSpawn: (process: ReturnType<typeof httpProcess>) => void = () => undefined
    await setupIntegratedPractice({
      nodeSpawn: () =>
        new Promise((resolve) => {
          resolveSpawn = resolve
        }),
    })
    selectIntegratedTab('HTTP')
    vi.useFakeTimers()
    await act(async () =>
      fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' })),
    )
    expect(httpCalls()).toHaveLength(1)
    await act(async () => vi.advanceTimersByTimeAsync(10000))
    expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível enviar')
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
    const process = httpProcess({
      status: 200,
      headers: [],
      body: 'late result',
      truncated: false,
    })
    await act(async () => resolveSpawn(process))
    expect(process.kill).toHaveBeenCalled()
    expect(screen.queryByText('late result')).not.toBeInTheDocument()
  })
  it('disposes a pending request and ignores an old readiness callback after route unmount', async () => {
    let resolveSpawn: (process: ReturnType<typeof httpProcess>) => void = () => undefined
    const { unmount } = await setupIntegratedPractice({
      nodeSpawn: () =>
        new Promise((resolve) => {
          resolveSpawn = resolve
        }),
    })
    selectIntegratedTab('HTTP')
    fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' }))
    await waitFor(() => expect(httpCalls()).toHaveLength(1))
    const oldReady = mocks.serverReady
    unmount()
    const process = httpProcess({
      status: 200,
      headers: [],
      body: 'disposed result',
      truncated: false,
    })
    await act(async () => {
      resolveSpawn(process)
      oldReady?.(5173, 'https://stale.webcontainer.io/')
    })
    expect(process.kill).toHaveBeenCalled()
    expect(mocks.teardown).toHaveBeenCalledOnce()
    expect(screen.queryByTitle('Prévia isolada React + Fastify')).not.toBeInTheDocument()
  })
  it('replaces only the explicitly requested API process through the permitted terminal command', async () => {
    await setupIntegratedPractice()
    selectIntegratedTab('Terminal')
    fireEvent.change(screen.getByRole('textbox', { name: 'Comando permitido' }), {
      target: { value: 'npm run dev:api' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar comando' }))
    await waitFor(() =>
      expect(
        mocks.spawn.mock.calls.filter(([, args]) => args[0] === '--watch'),
      ).toHaveLength(2),
    )
    expect(
      mocks.spawn.mock.calls.filter(
        ([, args]) => args[0] === 'node_modules/vite/bin/vite.js',
      ),
    ).toHaveLength(1)
    expect(mocks.kill).toHaveBeenCalledOnce()
    expect(httpCalls()).toHaveLength(0)
  })
  it('accepts CORS only from its confirmed isolated preview origin', async () => {
    await setupIntegratedPractice()
    const source = mocks.mount.mock.calls[0]?.[0]?.['vite.config.js']?.file?.contents
    expect(typeof source).toBe('string')
    let originRecord = 'null'
    const middleware = vi.fn()
    const proxyEvents = new Map<string, (...args: unknown[]) => void>()
    type PracticeRequest = {
      headers: Record<string, string>
      method: string
      url: string
    }
    type PracticeResponse = {
      setHeader: ReturnType<typeof vi.fn>
      end: ReturnType<typeof vi.fn>
      statusCode: number
    }
    type Configuration = {
      plugins: {
        configureServer(server: { middlewares: { use: typeof middleware } }): void
      }[]
      server: {
        cors: boolean
        proxy: Record<
          string,
          {
            configure(proxy: {
              on(event: string, listener: (...args: unknown[]) => void): void
            }): void
          }
        >
      }
    }
    const createConfiguration = new Function(
      'readFileSync',
      String(source)
        .replace("import { readFileSync } from 'node:fs';", '')
        .replace('export default', 'return'),
    ) as (read: () => string) => Configuration
    const configuration = createConfiguration(() => originRecord)
    configuration.plugins[0]?.configureServer({ middlewares: { use: middleware } })
    configuration.server.proxy['/api']?.configure({
      on(event, listener) {
        proxyEvents.set(event, listener)
      },
    })
    expect(configuration.server.cors).toBe(false)
    const handleRequest = middleware.mock.calls[0]?.[0] as (
      request: PracticeRequest,
      response: PracticeResponse,
      next: () => void,
    ) => void
    const confirmedOrigin = 'https://frontend.local.webcontainer-api.io'
    for (const storedOrigin of ['null', JSON.stringify(confirmedOrigin)]) {
      originRecord = storedOrigin
      for (const origin of [
        confirmedOrigin,
        'null',
        window.location.origin,
        'https://another.webcontainer-api.io',
      ]) {
        const request = {
          headers: { origin, cookie: 'private', authorization: 'private' },
          method: 'GET',
          url: '/api/tasks',
        }
        const response = { setHeader: vi.fn(), end: vi.fn(), statusCode: 200 }
        const next = vi.fn()
        handleRequest(request, response, next)
        const isAllowed = storedOrigin !== 'null' && origin === confirmedOrigin
        if (isAllowed)
          expect(response.setHeader).toHaveBeenCalledWith(
            'Access-Control-Allow-Origin',
            confirmedOrigin,
          )
        else
          expect(response.setHeader).not.toHaveBeenCalledWith(
            'Access-Control-Allow-Origin',
            expect.anything(),
          )
        expect(request.headers).not.toHaveProperty('cookie')
        expect(request.headers).not.toHaveProperty('authorization')
        expect(next).toHaveBeenCalledOnce()
        const upstream = {
          headers: {
            'set-cookie': 'private',
            'access-control-allow-credentials': 'true',
            'access-control-allow-origin': '*',
          },
        }
        proxyEvents.get('proxyRes')?.(upstream, request)
        expect(upstream.headers).not.toHaveProperty('set-cookie')
        expect(upstream.headers).not.toHaveProperty('access-control-allow-credentials')
        if (isAllowed)
          expect(upstream.headers).toHaveProperty(
            'access-control-allow-origin',
            confirmedOrigin,
          )
        else expect(upstream.headers).not.toHaveProperty('access-control-allow-origin')
      }
    }
    const preflight = { setHeader: vi.fn(), end: vi.fn(), statusCode: 0 }
    handleRequest(
      { headers: { origin: confirmedOrigin }, method: 'OPTIONS', url: '/api/tasks/1' },
      preflight,
      vi.fn(),
    )
    expect(preflight.statusCode).toBe(204)
    expect(preflight.setHeader).toHaveBeenCalledWith(
      'Access-Control-Allow-Headers',
      'Content-Type',
    )
    expect(preflight.setHeader).not.toHaveBeenCalledWith(
      'Access-Control-Allow-Credentials',
      expect.anything(),
    )
  })
  it('keeps generated configuration and fixed project files immutable in the editor and explorer', async () => {
    await setupIntegratedPractice()
    selectIntegratedTab('Arquivos')
    fireEvent.click(screen.getByRole('treeitem', { name: 'index.html' }))
    expect(screen.getByRole('textbox', { name: 'Código em edição' })).toHaveAttribute(
      'readonly',
    )
    expect(
      screen.queryByRole('treeitem', { name: 'package.json' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('treeitem', { name: 'vite.config.js' }),
    ).not.toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox', { name: 'Caminho do novo arquivo' }), {
      target: { value: 'src/vite.config.js' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Novo arquivo' }))
    expect(screen.getByRole('alert')).toHaveTextContent('fora da política')
    expect(
      mocks.writeFile.mock.calls.some(
        ([path]) =>
          path === 'index.html' ||
          path.endsWith('vite.config.js') ||
          path === 'package.json',
      ),
    ).toBe(false)
    expect(mocks.mount.mock.calls[0]?.[0]?.['vite.config.js']?.file?.contents).toContain(
      '127.0.0.1:3000',
    )
  })
  it.each(
    [3000, 5173].flatMap((port) =>
      [
        'https://untrusted.example/',
        'http://unsafe.webcontainer.io/',
        'https://name:secret@preview.webcontainer.io/',
        'https://preview.webcontainer-api.io:8443/',
        'https://preview.webcontainer.io.attacker.example/',
        'not-a-url',
      ].map((url) => ({ port, url })),
    ),
  )(
    'rejects an invalid preview origin independently for port $port: $url',
    async ({ port, url }) => {
      await setupIntegratedPractice()
      act(() => mocks.serverReady?.(port, url))
      selectIntegratedTab('HTTP')
      if (port === 3000)
        expect(screen.getByRole('button', { name: 'Enviar requisição' })).toBeDisabled()
      else expect(screen.getByRole('button', { name: 'Enviar requisição' })).toBeEnabled()
      selectIntegratedTab('Prévia')
      expect(screen.queryByTitle('Prévia isolada React + Fastify')).not.toHaveAttribute(
        'src',
        url,
      )
      selectIntegratedTab('Arquivos')
      fireEvent.click(screen.getByRole('treeitem', { name: 'App.tsx' }))
      expect(
        screen.getByRole('textbox', { name: 'Código em edição' }),
      ).not.toHaveAttribute('readonly')
    },
  )
  it('cancels a pending HTTP operation before a terminal restart and kills its late process', async () => {
    let resolveSpawn: (process: ReturnType<typeof httpProcess>) => void = () => undefined
    await setupIntegratedPractice({
      nodeSpawn: () =>
        new Promise((resolve) => {
          resolveSpawn = resolve
        }),
    })
    selectIntegratedTab('HTTP')
    fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' }))
    await waitFor(() => expect(httpCalls()).toHaveLength(1))
    selectIntegratedTab('Terminal')
    fireEvent.change(screen.getByRole('textbox', { name: 'Comando permitido' }), {
      target: { value: 'npm run dev:api' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar comando' }))
    await waitFor(() =>
      expect(
        mocks.spawn.mock.calls.filter(([, args]) => args[0] === '--watch'),
      ).toHaveLength(2),
    )
    const process = httpProcess({
      status: 200,
      headers: [],
      body: 'old API response',
      truncated: false,
    })
    await act(async () => resolveSpawn(process))
    expect(process.kill).toHaveBeenCalled()
    selectIntegratedTab('HTTP')
    expect(screen.queryByText('old API response')).not.toBeInTheDocument()
    expect(httpCalls()).toHaveLength(1)
  })
  it('updates multiple files through watchers without killing or awaiting a persistent process exit', async () => {
    const normalSpawn = mocks.spawn.getMockImplementation()
    mocks.spawn.mockImplementation(async (command: string, args: readonly string[]) => {
      const process = await normalSpawn?.(command, args)
      if (
        command === 'node' &&
        (args[0] === '--watch' || args[0] === 'node_modules/vite/bin/vite.js')
      )
        return { ...process, kill: vi.fn(), exit: new Promise<number>(() => undefined) }
      return process
    })
    await setupIntegratedPractice()
    selectIntegratedTab('Arquivos')
    fireEvent.click(screen.getByRole('treeitem', { name: 'App.tsx' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Código em edição' }), {
      target: { value: 'first update' },
    })
    await waitFor(() =>
      expect(mocks.writeFile).toHaveBeenCalledWith('src/App.tsx', 'first update'),
    )
    fireEvent.change(screen.getByRole('textbox', { name: 'Código em edição' }), {
      target: { value: 'second update' },
    })
    await waitFor(() =>
      expect(mocks.writeFile).toHaveBeenCalledWith('src/App.tsx', 'second update'),
    )
    expect(
      mocks.spawn.mock.calls.filter(([, args]) => args[0] === '--watch'),
    ).toHaveLength(1)
    expect(
      mocks.spawn.mock.calls.filter(
        ([, args]) => args[0] === 'node_modules/vite/bin/vite.js',
      ),
    ).toHaveLength(1)
    await waitFor(() =>
      expect(
        mocks.spawn.mock.calls.filter(
          ([command, args]) =>
            command === 'node' && args[0] === '--input-type=module' && args.length === 3,
        ),
      ).toHaveLength(2),
    )
    expect(httpCalls()).toHaveLength(0)
    selectIntegratedTab('Prévia')
    expect(await screen.findByTitle('Prévia isolada React + Fastify')).toHaveAttribute(
      'src',
      expect.stringContaining('_practiceRevision='),
    )
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
  })
  it('round-trips quoted Unicode and multiline HTTP bodies through a UTF-8 base64 process argument', async () => {
    const body = JSON.stringify(
      { title: 'Ação "rápida"', detail: 'linha 1\nlinha 2', symbol: '🧠' },
      null,
      2,
    )
    await setupIntegratedPractice({
      nodeSpawn: async (args) =>
        httpProcess({
          status: 200,
          headers: [{ name: 'Content-Type', value: 'application/json' }],
          body: decodeHttpRequestArgument(args.at(-1)).body,
          truncated: false,
        }),
    })
    selectIntegratedTab('HTTP')
    fireEvent.click(screen.getByRole('button', { name: 'PATCH' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Corpo da requisição' }), {
      target: { value: body },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar requisição' }))
    await screen.findByText('Status HTTP 200')
    const args = httpCalls()[0]?.[1]
    expect(decodeHttpRequestArgument(args?.at(-1))).toEqual({
      method: 'PATCH',
      path: '/api/tasks',
      body,
    })
    expect(args?.at(-1)).toMatch(/^[A-Za-z0-9+/]+={0,2}$/)
    expect(args?.[2]).toContain("Buffer.from(process.argv[1], 'base64').toString('utf8')")
    expect(new TextEncoder().encode(body).length).toBeGreaterThan(body.length)
    expect(
      screen.getByRole('region', { name: 'Requisições HTTP' }).querySelector('pre')
        ?.textContent,
    ).toBe(body)
  })
})
