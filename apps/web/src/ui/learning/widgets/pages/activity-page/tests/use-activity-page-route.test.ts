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
vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => {
    let validate: (data: unknown) => unknown = (data) => data
    const builder = {
      validator: (validator: (data: unknown) => unknown) => {
        validate = validator
        return builder
      },
      handler:
        (handler: (context: { data: unknown }) => unknown) =>
        (context: { data: unknown }) =>
          handler({ data: validate(context.data) }),
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
  CodeEditor: ({ files, selectedPath, onFileChange, readOnly }: CodeEditorProps) => {
    const file = files.find(({ path }) => path === selectedPath) ?? files[0]
    return createElement('textarea', {
      'aria-label': 'Código em edição',
      value: file?.content ?? '',
      readOnly,
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
    const never = new Promise<number>(() => undefined)
    mocks.spawn.mockImplementation(async (_command: string, args: readonly string[]) =>
      args[0] === 'install'
        ? { exit: Promise.resolve(0), kill: mocks.kill }
        : {
            exit: never,
            kill: mocks.kill,
            output: new ReadableStream<string>({
              start(controller) {
                controller.close()
              },
            }),
          },
    )
    mocks.boot.mockResolvedValue({
      mount: mocks.mount,
      spawn: mocks.spawn,
      fs: { mkdir: mocks.mkdir, writeFile: mocks.writeFile },
      teardown: mocks.teardown,
      on: (_event: string, handler: (port: number, url: string) => void) => {
        mocks.serverReady = handler
      },
    })
    vi.stubGlobal('isSecureContext', true)
    vi.stubGlobal('crossOriginIsolated', true)
    storage = installDraftBrowserStorage()
    vi.stubGlobal('scrollTo', vi.fn())
    vi.stubGlobal('matchMedia', () => ({ matches: true }))
    HTMLElement.prototype.scrollIntoView = vi.fn()
  })
  afterEach(() => {
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
        ? { exit: Promise.resolve(0), kill: mocks.kill }
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
})
