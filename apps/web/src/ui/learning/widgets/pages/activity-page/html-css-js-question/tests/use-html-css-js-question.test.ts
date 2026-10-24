import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { WebContainer } from '@webcontainer/api'
import { HtmlCssJsWebContainerPracticeRunner } from '@/provision/learning/html-css-js-webcontainer-practice-runner'
import type { HtmlCssJsQuestion as HtmlQuestion } from '@/core/learning/choice-activity'
import type {
  HtmlCssJsPracticeEvent,
  HtmlCssJsPracticeRunner,
} from '@/core/learning/html-css-js-practice-runner'
import type {
  ReactQuestionDraft,
  ReactQuestionDraftKey,
  ReactQuestionDraftStore,
} from '@/core/learning/react-question-draft/react-question-draft-store'
import {
  useHtmlCssJsQuestion,
  type HtmlCssJsQuestionProps,
} from '../use-html-css-js-question'

const { bootWebContainer } = vi.hoisted(() => ({ bootWebContainer: vi.fn() }))
vi.mock('@webcontainer/api', () => ({
  WebContainer: { boot: bootWebContainer },
}))

const QUESTION: HtmlQuestion = {
  key: 'web-1',
  kind: 'html_css_js',
  prompt: 'Crie uma página acessível.',
  initialFiles: [
    { path: 'index.html', content: '<main>inicial</main>', editable: true },
    { path: 'vite.config.js', content: 'export default {}', editable: false },
  ],
  entrypoint: 'index.html',
  editablePaths: ['index.html'],
  fixedDependencies: [{ name: 'vite', version: '7.0.0' }],
  permittedCommands: [{ id: 'dev', executable: 'npm', arguments: ['run', 'dev'] }],
  criteria: [{ key: 'semantic', name: 'HTML semântico', weightPercentage: 100 }],
}

function createDraft(
  files: ReactQuestionDraft['files'],
  generation = 2,
  tombstone = false,
): ReactQuestionDraft {
  return {
    accountId: 'account-1',
    goalId: 'goal-1',
    skillId: 'skill-1',
    competencyId: 'competency-1',
    activityId: 'activity-1',
    questionKey: 'web-1',
    activityRevision: 'revision-1',
    schemaVersion: 1,
    files,
    generation,
    savedAt: Date.now(),
    tombstone,
  }
}

function createRunner() {
  let listener: ((event: HtmlCssJsPracticeEvent) => void) | null = null
  const runner: HtmlCssJsPracticeRunner = {
    start: vi.fn(async () => {
      listener?.({
        status: 'ready',
        previewUrl: 'https://preview.webcontainer-api.io/',
        terminalText: 'Prévia pronta',
      })
    }),
    updateFile: vi.fn(async () => undefined),
    subscribe: vi.fn((nextListener) => {
      listener = nextListener
      nextListener({ status: 'booting', previewUrl: null, terminalText: '' })
      return () => {
        listener = null
      }
    }),
    dispose: vi.fn(),
  }
  return runner
}

function createStore(
  overrides: Partial<ReactQuestionDraftStore> = {},
): ReactQuestionDraftStore {
  return {
    read: vi.fn(async () => null),
    write: vi.fn(async () => 1),
    tombstone: vi.fn(async () => 1),
    clearTombstone: vi.fn(async () => 2),
    tombstoneActivity: vi.fn(async () => undefined),
    tombstoneStaleActivity: vi.fn(async () => undefined),
    subscribe: vi.fn(() => () => undefined),
    ...overrides,
  }
}

function createProps(
  overrides: Partial<HtmlCssJsQuestionProps> = {},
): HtmlCssJsQuestionProps {
  return {
    question: QUESTION,
    accountId: 'account-1',
    goalId: 'goal-1',
    skillId: 'skill-1',
    competencyId: 'competency-1',
    activityId: 'activity-1',
    activityRevision: 'revision-1',
    activeQuestionKeys: ['web-1'],
    isOnlineAuthority: true,
    questionNumber: 1,
    totalQuestions: 2,
    draftStore: createStore(),
    runnerFactory: createRunner,
    onFilesChange: vi.fn(),
    onAnswerValidityChange: vi.fn(),
    onAssess: vi.fn(),
    ...overrides,
  }
}

describe('useHtmlCssJsQuestion', () => {
  it('opens the curricular entrypoint when it is nested under the project root', async () => {
    const previousSecureContext = Object.getOwnPropertyDescriptor(
      window,
      'isSecureContext',
    )
    const previousCrossOriginIsolated = Object.getOwnPropertyDescriptor(
      window,
      'crossOriginIsolated',
    )
    Object.defineProperty(window, 'isSecureContext', {
      configurable: true,
      value: true,
    })
    Object.defineProperty(window, 'crossOriginIsolated', {
      configurable: true,
      value: true,
    })

    let onServerReady: ((port: number, url: string) => void) | null = null
    const serverProcess = {
      output: new ReadableStream<string>({ start: (controller) => controller.close() }),
      exit: new Promise<number>(() => undefined),
      kill: vi.fn(),
    }
    const container = {
      mount: vi.fn(async () => undefined),
      spawn: vi
        .fn()
        .mockResolvedValueOnce({ exit: Promise.resolve(0) })
        .mockImplementationOnce(async () => {
          onServerReady?.(5173, 'https://preview.webcontainer-api.io/')
          return serverProcess
        }),
      on: vi.fn((_event, listener) => {
        onServerReady = listener
      }),
      fs: { mkdir: vi.fn(), writeFile: vi.fn() },
      teardown: vi.fn(),
    } as unknown as WebContainer
    bootWebContainer.mockResolvedValueOnce(container)

    try {
      const runner = HtmlCssJsWebContainerPracticeRunner()
      const events: HtmlCssJsPracticeEvent[] = []
      runner.subscribe((event) => events.push(event))
      await runner.start({
        files: [
          { path: 'src/pages/index.html', content: '<main>page</main>' },
          { path: 'src/styles.css', content: 'main { color: black; }' },
        ],
        entrypoint: 'src/pages/index.html',
        fixedDependencies: [{ name: 'vite', version: '7.0.0' }],
        permittedCommands: [{ id: 'dev', executable: 'npm', arguments: ['run', 'dev'] }],
      })

      expect(events.at(-1)).toMatchObject({
        status: 'ready',
        previewUrl: 'https://preview.webcontainer-api.io/src/pages/index.html',
      })
      runner.dispose()
    } finally {
      if (previousSecureContext)
        Object.defineProperty(window, 'isSecureContext', previousSecureContext)
      else Reflect.deleteProperty(window, 'isSecureContext')
      if (previousCrossOriginIsolated)
        Object.defineProperty(window, 'crossOriginIsolated', previousCrossOriginIsolated)
      else Reflect.deleteProperty(window, 'crossOriginIsolated')
    }
  })

  it('restores the account and revision scoped editable draft and starts isolated practice', async () => {
    const runner = createRunner()
    const draftStore = createStore({
      read: vi.fn(async () =>
        createDraft([{ path: 'index.html', content: '<main>salvo</main>' }], 4),
      ),
    })
    const { result } = renderHook(() =>
      useHtmlCssJsQuestion(
        createProps({
          draftStore,
          runnerFactory: () => runner,
        }),
      ),
    )

    await waitFor(() =>
      expect(result.current.displayFiles[0]?.content).toBe('<main>salvo</main>'),
    )
    expect(result.current.generation).toBe(4)
    expect(runner.start).toHaveBeenCalledWith(
      expect.objectContaining({
        files: [
          { path: 'index.html', content: '<main>salvo</main>' },
          { path: 'vite.config.js', content: 'export default {}' },
        ],
      }),
    )
    expect(result.current.practiceStatus).toBe('ready')
    expect(result.current.previewUrl).toBe('https://preview.webcontainer-api.io/')
  })

  it('saves exact editable files with the current generation and propagates edits to practice', async () => {
    const runner = createRunner()
    const write = vi.fn(async () => 3)
    const draftStore = createStore({ write })
    const props = createProps({ draftStore, runnerFactory: () => runner })
    const { result } = renderHook(() => useHtmlCssJsQuestion(props))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))

    act(() => result.current.handleFileChange('index.html', '<main>novo</main>'))
    expect(runner.updateFile).toHaveBeenCalledWith('index.html', '<main>novo</main>')
    await waitFor(
      () =>
        expect(write).toHaveBeenCalledWith(
          expect.objectContaining({
            questionKey: 'web-1',
            activityRevision: 'revision-1',
          }),
          [{ path: 'index.html', content: '<main>novo</main>' }],
          0,
        ),
      { timeout: 1500 },
    )
    expect(result.current.generation).toBe(3)
  })

  it('adopts a newer saved cross-tab generation without allowing extra files', async () => {
    let changed: ((event: { generation: number; tombstone: boolean }) => void) | null =
      null
    const latest = createDraft(
      [{ path: 'index.html', content: '<main>outra aba</main>' }],
      5,
    )
    const read = vi.fn().mockResolvedValueOnce(null).mockResolvedValueOnce(latest)
    const draftStore = createStore({
      read,
      subscribe: vi.fn((_key: ReactQuestionDraftKey, listener) => {
        changed = listener
        return () => {
          changed = null
        }
      }),
    })
    const { result } = renderHook(() => useHtmlCssJsQuestion(createProps({ draftStore })))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))

    act(() => changed?.({ generation: 5, tombstone: false }))
    await waitFor(() =>
      expect(result.current.displayFiles[0]?.content).toBe('<main>outra aba</main>'),
    )
    expect(result.current.generation).toBe(5)
    expect(result.current.displayFiles).toHaveLength(2)
  })

  it('freezes the response when another tab invalidates its draft', async () => {
    let changed: ((event: { generation: number; tombstone: boolean }) => void) | null =
      null
    const tombstone = createDraft(
      [{ path: 'index.html', content: '<main>rascunho invalidado</main>' }],
      6,
      true,
    )
    const read = vi.fn().mockResolvedValueOnce(null).mockResolvedValueOnce(tombstone)
    const draftStore = createStore({
      read,
      subscribe: vi.fn((_key: ReactQuestionDraftKey, listener) => {
        changed = listener
        return () => {
          changed = null
        }
      }),
    })
    const { result } = renderHook(() => useHtmlCssJsQuestion(createProps({ draftStore })))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))

    act(() => changed?.({ generation: 6, tombstone: true }))
    await waitFor(() => expect(result.current.isDraftInvalidated).toBe(true))
    expect(result.current.isFrozen).toBe(true)
    act(() => result.current.handleFileChange('index.html', '<main>edição local</main>'))
    expect(result.current.displayFiles[0]?.content).toBe('<main>inicial</main>')
  })
})
