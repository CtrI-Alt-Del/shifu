import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ReactQuestion as ReactQuestionModel } from '@/core/learning/choice-activity'

import { ReactQuestion } from '..'
import {
  ReactQuestionDraftStore,
  isValidReactQuestionDraft,
  nextReactQuestionDraftGeneration,
  validateReactAdditionalFile,
  type ReactQuestionDraftKey,
} from '@/core/learning/react-question-draft/react-question-draft-store'
import { useReactQuestion } from '../use-react-question'

vi.mock('../use-react-question', () => ({
  useReactQuestion: vi.fn(),
}))
vi.mock('@/ui/learning/widgets/components/code-editor', () => ({
  CodeEditor: () => <div>Editor</div>,
}))
vi.mock('@/ui/learning/widgets/components/code-file-tree', () => ({
  CodeFileTree: () => <div>Arquivos</div>,
}))

const question: ReactQuestionModel = {
  key: 'react-1',
  kind: 'react',
  prompt: 'Monte uma tela de boas-vindas.',
  initialFiles: [
    { path: 'src/App.tsx', content: 'export default function App() {}', editable: true },
  ],
  entrypoint: 'src/main.tsx',
  editablePaths: ['src/App.tsx'],
  fixedDependencies: [{ name: 'react', version: '19.0.0' }],
  permittedCommands: [],
  additionalFilePolicy: {
    allowedDirectories: ['src'],
    allowedExtensions: ['.tsx'],
    maxFiles: 2,
  },
  criteria: [{ key: 'complete', name: 'Completude', weightPercentage: 100 }],
}

const hookState = {
  files: [{ path: 'src/App.tsx', content: 'export default function App() {}' }],
  displayFiles: question.initialFiles.map(({ path, content }) => ({ path, content })),
  selectedPath: 'src/App.tsx',
  editablePaths: ['src/App.tsx'],
  editorEditablePaths: ['src/App.tsx'],
  additionalFilesCount: 0,
  draftLoaded: true,
  draftGeneration: 1,
  isSaving: false,
  hasSaveError: false,
  isAssessing: false,
  hasAssessError: false,
  status: 'ready' as const,
  previewUrl: 'https://preview-abc.webcontainer.io/',
  terminalText: '',
  newFilePath: '',
  hasFileError: false,
  isDraftInvalidated: false,
  isActivityLocked: false,
  totalSourceBytes: 32,
  isFrozen: false,
  handleAddFile: vi.fn(),
  handleAssess: vi.fn(),
  handleFileChange: vi.fn(),
  handleSelectFile: vi.fn(),
  handleNewFilePathChange: vi.fn(),
}

const draftRecords = new Map<IDBValidKey, unknown>()
type FakeRequest = {
  result: unknown
  error: DOMException | null
  onsuccess: ((event: Event) => void) | null
  onerror: ((event: Event) => void) | null
  onupgradeneeded: ((event: IDBVersionChangeEvent) => void) | null
}

function fakeRequest(): FakeRequest {
  return {
    result: undefined,
    error: null,
    onsuccess: null,
    onerror: null,
    onupgradeneeded: null,
  }
}

class FakeBroadcastChannel {
  static channels = new Set<FakeBroadcastChannel>()
  onmessage: ((event: MessageEvent<unknown>) => void) | null = null

  constructor(_name: string) {
    FakeBroadcastChannel.channels.add(this)
  }

  postMessage(data: unknown) {
    const crossTabMessage =
      data && typeof data === 'object' ? { ...data, sender: 'other-tab' } : data
    for (const channel of FakeBroadcastChannel.channels) {
      if (channel !== this)
        queueMicrotask(() =>
          channel.onmessage?.({ data: crossTabMessage } as MessageEvent<unknown>),
        )
    }
  }

  close() {
    FakeBroadcastChannel.channels.delete(this)
  }
}

function installDraftStorage() {
  draftRecords.clear()
  FakeBroadcastChannel.channels.clear()
  const database = {
    createObjectStore: vi.fn(),
    close: vi.fn(),
    transaction: vi.fn(() => {
      const transaction = {
        oncomplete: null as ((event: Event) => void) | null,
        onerror: null as ((event: Event) => void) | null,
        onabort: null as ((event: Event) => void) | null,
        error: null as DOMException | null,
        objectStore: vi.fn(() => ({
          get(key: IDBValidKey) {
            const request = fakeRequest()
            queueMicrotask(() => {
              request.result = draftRecords.get(key)
              request.onsuccess?.(new Event('success'))
              setTimeout(() => transaction.oncomplete?.(new Event('complete')), 0)
            })
            return request
          },
          put(value: unknown, key: IDBValidKey) {
            draftRecords.set(key, value)
            setTimeout(() => transaction.oncomplete?.(new Event('complete')), 0)
            return {}
          },
        })),
      }
      return transaction
    }),
  }
  const indexedDBMock = {
    open: vi.fn(() => {
      const request = fakeRequest()
      request.result = database
      queueMicrotask(() => {
        request.onupgradeneeded?.(new Event('upgradeneeded') as IDBVersionChangeEvent)
        request.onsuccess?.(new Event('success'))
      })
      return request
    }),
  }
  vi.stubGlobal('indexedDB', indexedDBMock)
  vi.stubGlobal('BroadcastChannel', FakeBroadcastChannel)
}

const draftKey: ReactQuestionDraftKey = {
  accountId: 'account-1',
  goalId: 'goal-1',
  skillId: 'skill-1',
  competencyId: 'competency-1',
  activityId: 'activity-1',
  questionKey: 'react-1',
  activityRevision: 'revision-1',
}

describe('ReactQuestion', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('isolates the preview in a distinct HTTPS WebContainer origin', () => {
    vi.mocked(useReactQuestion).mockReturnValue({
      ...hookState,
      previewUrl: 'https://preview-abc.local-corp.webcontainer-api.io/',
    })
    render(
      <ReactQuestion
        question={question}
        accountId='account-1'
        goalId='goal-1'
        skillId='skill-1'
        competencyId='competency-1'
        activityId='activity-1'
        activityRevision='revision-1'
        activeQuestionKeys={['react-1']}
        isOnlineAuthority
        questionNumber={1}
        totalQuestions={1}
      />,
    )

    const preview = screen.getByTitle('Prévia isolada da aplicação React')
    const previewUrl = new URL(preview.getAttribute('src') ?? '')
    expect(preview.getAttribute('sandbox')).toBe('allow-scripts')
    expect(previewUrl.protocol).toBe('https:')
    expect(previewUrl.hostname).toMatch(/\.webcontainer-api\.io$/)
    expect(previewUrl.origin).not.toBe(window.location.origin)
  })

  it('enforces allowed paths, extensions, file counts, and collision rules', () => {
    const policy = question.additionalFilePolicy
    const currentFiles = [{ path: 'src/App.tsx' }]
    const initialPaths = ['src/App.tsx']
    expect(
      validateReactAdditionalFile(
        'src/components/Header.tsx',
        currentFiles,
        policy,
        initialPaths,
      ),
    ).toBe(true)
    expect(
      validateReactAdditionalFile('src/package.json', currentFiles, policy, initialPaths),
    ).toBe(false)
    expect(
      validateReactAdditionalFile(
        'src/../Escape.tsx',
        currentFiles,
        policy,
        initialPaths,
      ),
    ).toBe(false)
    expect(
      validateReactAdditionalFile(
        'src/App.tsx/Child.tsx',
        currentFiles,
        policy,
        initialPaths,
      ),
    ).toBe(false)
    expect(
      validateReactAdditionalFile(
        'src/components/Readme.md',
        currentFiles,
        policy,
        initialPaths,
      ),
    ).toBe(false)
    expect(
      validateReactAdditionalFile(
        'src/components/Second.tsx',
        [...currentFiles, { path: 'src/Header.tsx' }, { path: 'src/Footer.tsx' }],
        policy,
        initialPaths,
      ),
    ).toBe(false)
  })

  it('accepts only versioned drafts that match the account and activity key', () => {
    const key = {
      accountId: 'account-1',
      goalId: 'goal-1',
      skillId: 'skill-1',
      competencyId: 'competency-1',
      activityId: 'activity-1',
      questionKey: 'react-1',
      activityRevision: 'revision-1',
    }
    const draft = {
      ...key,
      schemaVersion: 1,
      files: [{ path: 'src/App.tsx', content: 'export default function App() {}' }],
      generation: 2,
      savedAt: Date.now(),
      tombstone: false,
    }
    expect(isValidReactQuestionDraft(draft, key)).toBe(true)
    expect(isValidReactQuestionDraft({ ...draft, schemaVersion: 2 }, key)).toBe(false)
    expect(isValidReactQuestionDraft(draft, { ...key, accountId: 'other-account' })).toBe(
      false,
    )
    expect(isValidReactQuestionDraft({ ...draft, generation: 0 }, key)).toBe(false)
    expect(
      isValidReactQuestionDraft(
        { ...draft, files: [{ path: '../secret', content: 3 }] },
        key,
      ),
    ).toBe(false)
  })

  it('recovers from corrupt stored generation values when creating a tombstone', () => {
    expect(nextReactQuestionDraftGeneration(4)).toBe(5)
    expect(nextReactQuestionDraftGeneration('corrupt')).toBe(1)
    expect(nextReactQuestionDraftGeneration(Number.MAX_SAFE_INTEGER + 1)).toBe(1)
  })

  it('orders local writes, isolates accounts, and broadcasts invalidation tombstones', async () => {
    installDraftStorage()
    const changes: { generation: number; tombstone: boolean }[] = []
    const unsubscribe = ReactQuestionDraftStore.subscribe(draftKey, (change) =>
      changes.push(change),
    )
    const first = [{ path: 'src/App.tsx', content: 'first' }]
    const second = [{ path: 'src/App.tsx', content: 'second' }]
    expect(await ReactQuestionDraftStore.write(draftKey, first, 0)).toBe(1)
    expect(await ReactQuestionDraftStore.write(draftKey, second, 0)).toBe(0)
    expect((await ReactQuestionDraftStore.read(draftKey))?.files).toEqual(first)
    expect(
      await ReactQuestionDraftStore.read({ ...draftKey, accountId: 'other' }),
    ).toBeNull()

    const tombstoneGeneration = await ReactQuestionDraftStore.tombstone(draftKey)
    expect(tombstoneGeneration).toBe(2)
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(changes).toContainEqual({ generation: 2, tombstone: true })
    expect((await ReactQuestionDraftStore.read(draftKey))?.tombstone).toBe(true)
    expect(
      await ReactQuestionDraftStore.write(draftKey, second, tombstoneGeneration),
    ).toBe(0)
    const restoredGeneration = await ReactQuestionDraftStore.clearTombstone(
      draftKey,
      first,
      tombstoneGeneration,
    )
    expect(restoredGeneration).toBe(3)
    expect((await ReactQuestionDraftStore.read(draftKey))?.files).toEqual(first)
    unsubscribe()
  })

  it('surfaces IndexedDB failures so the widget can keep the answer unsaved', async () => {
    const failingIndexedDB = {
      open: vi.fn(() => {
        const request = fakeRequest()
        queueMicrotask(() => {
          request.error = new DOMException('storage unavailable')
          request.onerror?.(new Event('error'))
        })
        return request
      }),
    }
    vi.stubGlobal('indexedDB', failingIndexedDB)
    await expect(ReactQuestionDraftStore.read(draftKey)).rejects.toThrow(
      'storage unavailable',
    )
  })
})
