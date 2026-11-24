import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ReactQuestion as ReactQuestionModel } from '@/core/learning/choice-activity'
import type {
  ReactQuestionDraft,
  ReactQuestionDraftKey,
  ReactQuestionDraftStore,
} from '@/core/learning/react-question-draft/react-question-draft-store'
import { type ReactQuestionProps, useReactQuestion } from '../use-react-question'
import { IndexedDbReactQuestionDraftStore } from '@/provision/learning/indexed-db-react-question-draft-store'

const QUESTION: ReactQuestionModel = {
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
  additionalFilePolicy: null,
  criteria: [{ key: 'complete', name: 'Completude', weightPercentage: 100 }],
}
function createDraftStore(overrides: Partial<ReactQuestionDraftStore> = {}) {
  function keyOf(key: ReactQuestionDraftKey) {
    return JSON.stringify(Object.entries(key).sort())
  }
  const records = new Map<string, ReactQuestionDraft>()
  const listeners = new Set<
    (event: { generation: number; tombstone: boolean; accountRevoked?: boolean }) => void
  >()
  const store: ReactQuestionDraftStore = {
    read: vi.fn(async (key) => records.get(keyOf(key)) ?? null),
    write: vi.fn(
      async (
        key: ReactQuestionDraftKey,
        files: ReactQuestionDraft['files'],
        expectedGeneration: number,
      ) => {
        const current = records.get(keyOf(key))
        if (current?.tombstone || (current?.generation ?? 0) !== expectedGeneration)
          return 0
        const generation = expectedGeneration + 1
        records.set(keyOf(key), {
          ...key,
          schemaVersion: 1,
          generation,
          savedAt: 1,
          tombstone: false,
          files: files.map((file) => ({ ...file })),
        })
        return generation
      },
    ),
    tombstone: vi.fn(async () => 1),
    clearTombstone: vi.fn(async () => 2),
    tombstoneActivity: vi.fn(async () => undefined),
    tombstoneStaleActivity: vi.fn(async () => undefined),
    validateAccountCapability: vi.fn(async () => 'active' as const),
    revokeAccount: vi.fn(async () => undefined),
    subscribe: vi.fn((_key, listener) => {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    }),
    ...overrides,
  }
  function publish(
    key: ReactQuestionDraftKey,
    files: ReactQuestionDraft['files'],
    generation: number,
    tombstone = false,
  ) {
    records.set(keyOf(key), {
      ...key,
      schemaVersion: 1,
      files,
      generation,
      savedAt: 1,
      tombstone,
    })
    for (const listener of listeners) listener({ generation, tombstone })
  }
  function publishAccountRevoked() {
    for (const listener of listeners)
      listener({ generation: 0, tombstone: true, accountRevoked: true })
  }
  return { store, publish, publishAccountRevoked }
}
function createProps(
  draftStore: ReactQuestionDraftStore,
  overrides: Partial<ReactQuestionProps> = {},
): ReactQuestionProps {
  return {
    draftStore,
    question: QUESTION,
    accountId: 'account-1',
    goalId: 'goal-1',
    skillId: 'skill-1',
    competencyId: 'competency-1',
    activityId: 'activity-1',
    activityRevision: 'revision-1',
    activeQuestionKeys: ['react-1'],
    isOnlineAuthority: true,
    questionNumber: 1,
    totalQuestions: 1,
    ...overrides,
  }
}
function keyFrom(props: ReactQuestionProps): ReactQuestionDraftKey {
  return {
    accountId: props.accountId ?? '',
    goalId: props.goalId ?? '',
    skillId: props.skillId ?? '',
    competencyId: props.competencyId ?? '',
    activityId: props.activityId,
    activityRevision: props.activityRevision ?? '',
    questionKey: props.question.key,
  }
}
function deferred<T>() {
  let resolve: (value: T) => void = () => undefined
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise
  })
  return { promise, resolve }
}

function createRunner() {
  return {
    start: vi.fn(async () => undefined),
    updateFile: vi.fn(async () => undefined),
    addFile: vi.fn(async () => undefined),
    subscribe: vi.fn(() => vi.fn()),
    dispose: vi.fn(),
  }
}

function installIndexedDB() {
  const records = new Map<IDBValidKey, unknown>()
  const capabilityRecords = new Map<IDBValidKey, unknown>()
  const objectStoreNames = new Set<string>()
  const database = {
    objectStoreNames: { contains: (name: string) => objectStoreNames.has(name) },
    createObjectStore: vi.fn((name: string) => {
      objectStoreNames.add(name)
      return {}
    }),
    close: vi.fn(),
    transaction: vi.fn((_storeNames: string | string[]) => {
      const transaction = {
        oncomplete: null as (() => void) | null,
        onerror: null as (() => void) | null,
        onabort: null as (() => void) | null,
        objectStore: (name: string) => {
          const storeRecords =
            name === 'account-capabilities' ? capabilityRecords : records
          return {
            get(key: IDBValidKey) {
              const request = {
                result: undefined as unknown,
                onsuccess: null as (() => void) | null,
                onerror: null as (() => void) | null,
              }
              queueMicrotask(() => {
                request.result = storeRecords.get(key)
                request.onsuccess?.()
                setTimeout(() => transaction.oncomplete?.(), 0)
              })
              return request
            },
            put(value: unknown, key?: IDBValidKey) {
              const accountId = (value as { accountId?: string }).accountId
              const recordKey = key ?? accountId
              if (recordKey !== undefined) storeRecords.set(recordKey, value)
              setTimeout(() => transaction.oncomplete?.(), 0)
              return {}
            },
            openCursor() {
              const entries = [...storeRecords.entries()]
              let index = 0
              const request = {
                result: null as null | {
                  value: unknown
                  delete: () => void
                  update: (value: unknown) => void
                  continue: () => void
                },
                onsuccess: null as (() => void) | null,
              }
              function next() {
                queueMicrotask(() => {
                  const entry = entries[index++]
                  request.result = entry
                    ? {
                        value: entry[1],
                        delete: () => storeRecords.delete(entry[0]),
                        update: (value) =>
                          storeRecords.set(entry[0], structuredClone(value)),
                        continue: next,
                      }
                    : null
                  request.onsuccess?.()
                  if (!entry) setTimeout(() => transaction.oncomplete?.(), 0)
                })
              }
              next()
              return request
            },
          }
        },
      }
      return transaction
    }),
  }
  vi.stubGlobal('BroadcastChannel', undefined)
  vi.stubGlobal('indexedDB', {
    open: vi.fn(() => {
      const request = {
        result: database,
        onsuccess: null as (() => void) | null,
        onerror: null as (() => void) | null,
        onupgradeneeded: null as (() => void) | null,
      }
      queueMicrotask(() => {
        request.onupgradeneeded?.()
        request.onsuccess?.()
      })
      return request
    }),
  })
  return records
}

function createBrowserCapabilityClient() {
  return {
    issueBrowserDataCapability: vi.fn(async () => 'test-browser-capability'),
    validateBrowserDataCapability: vi.fn(async () => 'active' as const),
  }
}

describe('useReactQuestion', () => {
  afterEach(() => {
    cleanup()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })
  it('flushes the current draft before preliminary assessment', async () => {
    const { store } = createDraftStore()
    const props = createProps(store)
    const onAssess = vi.fn(async (files) => {
      expect((await store.read(keyFrom(props)))?.files).toEqual(files)
    })
    const { result } = renderHook(() => useReactQuestion({ ...props, onAssess }))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    act(() => result.current.handleFileChange('src/App.tsx', 'edited'))
    await act(async () => result.current.handleAssess())
    expect(onAssess).toHaveBeenCalledWith([{ path: 'src/App.tsx', content: 'edited' }])
    expect(result.current.hasAssessError).toBe(false)
  })
  it('does not assess when the draft cannot be saved', async () => {
    const { store } = createDraftStore()
    const onAssess = vi.fn()
    const { result } = renderHook(() =>
      useReactQuestion(createProps(store, { onAssess })),
    )
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    vi.mocked(store.write).mockRejectedValue(new DOMException('storage unavailable'))
    await act(async () => result.current.handleAssess())
    expect(onAssess).not.toHaveBeenCalled()
    expect(result.current.hasAssessError).toBe(true)
    expect(result.current.hasSaveError).toBe(true)
  })
  it('reports a stale-draft cleanup failure without rejecting outside the consumer', async () => {
    const { store } = createDraftStore()
    vi.mocked(store.tombstoneStaleActivity).mockRejectedValue(
      new DOMException('storage unavailable'),
    )
    const { result } = renderHook(() => useReactQuestion(createProps(store)))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    await waitFor(() => expect(result.current.hasSaveError).toBe(true))
    expect(result.current.files).toEqual([
      { path: 'src/App.tsx', content: 'export default function App() {}' },
    ])
  })
  it('restores permitted additional files after remount', async () => {
    const { store } = createDraftStore()
    const props = createProps(store, {
      question: {
        ...QUESTION,
        additionalFilePolicy: {
          allowedDirectories: ['src/components'],
          allowedExtensions: ['.tsx'],
          maxFiles: 1,
        },
      },
      onAssess: vi.fn(),
    })
    const first = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(first.result.current.draftLoaded).toBe(true))
    act(() => first.result.current.handleNewFilePathChange('src/components/Badge.tsx'))
    act(() => first.result.current.handleAddFile())
    act(() =>
      first.result.current.handleFileChange(
        'src/components/Badge.tsx',
        'export const Badge = () => null',
      ),
    )
    await act(async () => first.result.current.handleAssess())
    first.unmount()
    const second = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(second.result.current.draftLoaded).toBe(true))
    expect(second.result.current.files).toEqual([
      { path: 'src/App.tsx', content: 'export default function App() {}' },
      { path: 'src/components/Badge.tsx', content: 'export const Badge = () => null' },
    ])
  })

  it.each([
    'src/package.json',
    'src/../Escape.tsx',
    'src/App.tsx/Child.tsx',
    'src/Readme.md',
  ])('rejects an additional file outside the curricular policy: %s', async (path) => {
    const { store } = createDraftStore()
    const props = createProps(store, {
      question: {
        ...QUESTION,
        additionalFilePolicy: {
          allowedDirectories: ['src'],
          allowedExtensions: ['.tsx'],
          maxFiles: 1,
        },
      },
    })
    const { result } = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    act(() => result.current.handleNewFilePathChange(path))
    act(() => result.current.handleAddFile())
    expect(result.current.hasFileError).toBe(true)
    expect(result.current.files.map((file) => file.path)).toEqual(['src/App.tsx'])
  })

  it('rejects extra files beyond the curricular count limit', async () => {
    const { store } = createDraftStore()
    const props = createProps(store, {
      question: {
        ...QUESTION,
        additionalFilePolicy: {
          allowedDirectories: ['src'],
          allowedExtensions: ['.tsx'],
          maxFiles: 1,
        },
      },
    })
    const { result } = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    act(() => result.current.handleNewFilePathChange('src/First.tsx'))
    act(() => result.current.handleAddFile())
    act(() => result.current.handleNewFilePathChange('src/Second.tsx'))
    act(() => result.current.handleAddFile())
    expect(result.current.hasFileError).toBe(true)
    expect(result.current.additionalFilesCount).toBe(1)
    expect(result.current.files.map((file) => file.path)).toEqual([
      'src/App.tsx',
      'src/First.tsx',
    ])
  })
  it('preserves unsaved edits and runner through equivalent activity refreshes', async () => {
    const { store } = createDraftStore()
    const runner = {
      start: vi.fn(async () => undefined),
      updateFile: vi.fn(async () => undefined),
      addFile: vi.fn(async () => undefined),
      subscribe: vi.fn(() => vi.fn()),
      dispose: vi.fn(),
    }
    const runnerFactory = vi.fn(() => runner)
    const props = createProps(store, { runnerFactory })
    const { result, rerender } = renderHook(
      (currentProps) => useReactQuestion(currentProps),
      { initialProps: props },
    )
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    act(() => result.current.handleFileChange('src/App.tsx', 'unsaved'))
    rerender({ ...props, question: structuredClone(QUESTION) })
    expect(result.current.files).toEqual([{ path: 'src/App.tsx', content: 'unsaved' }])
    expect(store.read).toHaveBeenCalledOnce()
    expect(runnerFactory).toHaveBeenCalledOnce()
    rerender({ ...props, isOnlineAuthority: false })
    rerender({ ...props, isOnlineAuthority: true, question: structuredClone(QUESTION) })
    expect(result.current.files[0]?.content).toBe('unsaved')
    expect(store.read).toHaveBeenCalledOnce()
  })
  it('preserves frozen files across remote updates but still reacts to deletion', async () => {
    const { store, publish } = createDraftStore()
    const onFilesChange = vi.fn()
    const onAnswerValidityChange = vi.fn()
    const runner = createRunner()
    const runnerFactory = vi.fn(() => runner)
    const props = createProps(store, {
      onFilesChange,
      onAnswerValidityChange,
      runnerFactory,
    })
    const { result, rerender } = renderHook(
      (currentProps) => useReactQuestion(currentProps),
      { initialProps: props },
    )
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    act(() => result.current.handleFileChange('src/App.tsx', 'assessed'))
    rerender({ ...props, readOnly: true })
    onFilesChange.mockClear()
    await act(async () =>
      publish(keyFrom(props), [{ path: 'src/App.tsx', content: 'remote' }], 3),
    )
    expect(result.current.files[0]?.content).toBe('assessed')
    expect(onFilesChange).not.toHaveBeenCalled()
    expect(runner.start).toHaveBeenCalledOnce()
    await act(async () => publish(keyFrom(props), [], 4, true))
    expect(result.current.isDraftInvalidated).toBe(true)
    expect(onAnswerValidityChange).toHaveBeenLastCalledWith(false)
    expect(runner.dispose).toHaveBeenCalledOnce()
    expect(result.current.status).toBe('unavailable')
  })

  it.each(['broadcast', 'save conflict'] as const)(
    'restarts the preview from the full accepted remote project after %s',
    async (source) => {
      const { store, publish } = createDraftStore()
      const runner = createRunner()
      const restartedRunner = createRunner()
      const runnerFactory = vi.fn(() => restartedRunner).mockReturnValueOnce(runner)
      const props = createProps(store, {
        runnerFactory,
        question: {
          ...QUESTION,
          initialFiles: [
            ...QUESTION.initialFiles,
            { path: 'src/main.tsx', content: 'fixed bootstrap', editable: false },
          ],
          additionalFilePolicy: {
            allowedDirectories: ['src/components'],
            allowedExtensions: ['.tsx'],
            maxFiles: 2,
          },
        },
      })
      const { result } = renderHook(() => useReactQuestion(props))
      await waitFor(() => expect(result.current.draftLoaded).toBe(true))
      vi.useFakeTimers()
      act(() => result.current.handleNewFilePathChange('src/components/Local.tsx'))
      act(() => result.current.handleAddFile())
      const remoteFiles = [
        { path: 'src/App.tsx', content: 'import Badge from "./components/Badge"' },
        {
          path: 'src/components/Badge.tsx',
          content: 'export default () => <b>Badge</b>',
        },
      ]
      if (source === 'broadcast') {
        await act(async () => publish(keyFrom(props), remoteFiles, 3))
      } else {
        vi.mocked(store.write).mockResolvedValueOnce(0)
        vi.mocked(store.read).mockResolvedValueOnce({
          ...keyFrom(props),
          schemaVersion: 1,
          generation: 3,
          savedAt: 1,
          tombstone: false,
          files: remoteFiles,
        })
        await act(async () => vi.advanceTimersByTimeAsync(350))
      }
      expect(result.current.files).toEqual(remoteFiles)
      expect(runner.dispose).toHaveBeenCalledOnce()
      expect(runnerFactory).toHaveBeenCalledTimes(2)
      expect(runner.start).toHaveBeenCalledOnce()
      expect(restartedRunner.start).toHaveBeenCalledOnce()
      expect(restartedRunner.start).toHaveBeenCalledWith({
        files: [
          remoteFiles[0],
          { path: 'src/main.tsx', content: 'fixed bootstrap' },
          remoteFiles[1],
        ],
        entrypoint: QUESTION.entrypoint,
        fixedDependencies: QUESTION.fixedDependencies,
        permittedCommands: [],
        additionalFilePolicy: props.question.additionalFilePolicy,
      })
      expect(
        result.current.displayFiles.some((file) => file.path.endsWith('Local.tsx')),
      ).toBe(false)
    },
  )

  it('clears the previous account source before a different account is authorized', async () => {
    const { store } = createDraftStore()
    const props = createProps(store)
    const { result, rerender } = renderHook(
      (currentProps) => useReactQuestion(currentProps),
      { initialProps: props },
    )
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    act(() =>
      result.current.handleFileChange('src/App.tsx', 'previous account private source'),
    )
    rerender({ ...props, accountId: 'account-2', isOnlineAuthority: false })
    expect(result.current.files[0]?.content).toBe(QUESTION.initialFiles[0]?.content)
    expect(result.current.draftLoaded).toBe(false)
    rerender(props)
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    expect(store.read).toHaveBeenCalledTimes(2)
  })
  it('serializes an in-flight autosave and assessment flush without losing newer edits', async () => {
    const { store } = createDraftStore()
    const props = createProps(store, { onAssess: vi.fn() })
    const { result } = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    vi.useFakeTimers()
    const firstWrite = deferred<void>()
    const write = vi.mocked(store.write)
    const normalWrite = write.getMockImplementation()
    if (!normalWrite) throw new Error('Expected the draft write implementation')
    write.mockImplementationOnce(async (...args) => {
      await firstWrite.promise
      return normalWrite(...args)
    })
    act(() => result.current.handleFileChange('src/App.tsx', 'older'))
    await act(async () => vi.advanceTimersByTimeAsync(350))
    expect(write).toHaveBeenCalledTimes(1)
    act(() => result.current.handleFileChange('src/App.tsx', 'newest'))
    await act(async () => vi.advanceTimersByTimeAsync(350))
    expect(write).toHaveBeenCalledTimes(1)
    let assessment: Promise<void> = Promise.resolve()
    act(() => {
      assessment = result.current.handleAssess()
    })
    await act(async () => {
      firstWrite.resolve()
      await assessment
    })
    expect(write.mock.calls.map((call) => call[2])).toEqual([0, 1, 2])
    expect((await store.read(keyFrom(props)))?.files[0]?.content).toBe('newest')
    expect(result.current.files[0]?.content).toBe('newest')
    expect(props.onAssess).toHaveBeenCalledWith([
      { path: 'src/App.tsx', content: 'newest' },
    ])
  })
  it('rejects invalid stored files after a conflicting save', async () => {
    const { store } = createDraftStore()
    const props = createProps(store, { onAssess: vi.fn() })
    const { result } = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    vi.mocked(store.write).mockResolvedValue(0)
    vi.mocked(store.read).mockResolvedValue({
      ...keyFrom(props),
      schemaVersion: 1,
      generation: 2,
      savedAt: 1,
      tombstone: false,
      files: [{ path: '../secret.tsx', content: 'invalid' }],
    })
    await act(async () => result.current.handleAssess())
    expect(result.current.isDraftInvalidated).toBe(true)
    expect(props.onAssess).not.toHaveBeenCalled()
    expect(result.current.files[0]?.path).toBe('src/App.tsx')
  })

  it('blocks assessment queued behind an autosave that conflicts with another tab', async () => {
    const { store } = createDraftStore()
    const props = createProps(store, { onAssess: vi.fn() })
    const { result } = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    vi.useFakeTimers()
    const firstWrite = deferred<number>()
    vi.mocked(store.write).mockImplementationOnce(() => firstWrite.promise)
    act(() => result.current.handleFileChange('src/App.tsx', 'older local edit'))
    await act(async () => vi.advanceTimersByTimeAsync(350))
    act(() => result.current.handleFileChange('src/App.tsx', 'newer local edit'))
    let assessment: Promise<void> = Promise.resolve()
    act(() => {
      assessment = result.current.handleAssess()
    })
    vi.mocked(store.read).mockResolvedValueOnce({
      ...keyFrom(props),
      schemaVersion: 1,
      generation: 2,
      savedAt: 1,
      tombstone: false,
      files: [{ path: 'src/App.tsx', content: 'remote stored answer' }],
    })
    await act(async () => {
      firstWrite.resolve(0)
      await assessment
    })
    expect(result.current.isDraftInvalidated).toBe(true)
    expect(result.current.hasAssessError).toBe(true)
    expect(props.onAssess).not.toHaveBeenCalled()
    expect(store.write).toHaveBeenCalledOnce()
    await act(async () => result.current.handleAssess())
    expect(store.write).toHaveBeenCalledOnce()
    expect(props.onAssess).not.toHaveBeenCalled()
  })

  it('discards a queued autosave superseded by another tab while an older write completes', async () => {
    const { store, publish } = createDraftStore()
    const props = createProps(store)
    const { result } = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    vi.useFakeTimers()
    const firstReply = deferred<void>()
    const write = vi.mocked(store.write)
    const normalWrite = write.getMockImplementation()
    if (!normalWrite) throw new Error('Expected the draft write implementation')
    write.mockImplementationOnce(async (...args) => {
      const generation = await normalWrite(...args)
      await firstReply.promise
      return generation
    })
    act(() => result.current.handleFileChange('src/App.tsx', 'first local edit'))
    await act(async () => vi.advanceTimersByTimeAsync(350))
    act(() => result.current.handleFileChange('src/App.tsx', 'queued local edit'))
    await act(async () => vi.advanceTimersByTimeAsync(350))
    expect(write).toHaveBeenCalledTimes(1)
    await act(async () =>
      publish(keyFrom(props), [{ path: 'src/App.tsx', content: 'remote edit' }], 2),
    )
    expect(result.current.files[0]?.content).toBe('remote edit')
    await act(async () => {
      firstReply.resolve()
    })
    expect(write).toHaveBeenCalledTimes(1)
    expect((await store.read(keyFrom(props)))?.files[0]?.content).toBe('remote edit')
    act(() =>
      result.current.handleFileChange('src/App.tsx', 'edit after remote adoption'),
    )
    await act(async () => vi.advanceTimersByTimeAsync(350))
    expect(write.mock.calls.map((call) => call[2])).toEqual([0, 2])
    expect((await store.read(keyFrom(props)))?.files[0]?.content).toBe(
      'edit after remote adoption',
    )
  })

  it('restores browser-persisted work only for the same authenticated account', async () => {
    installIndexedDB()
    const props = createProps(
      IndexedDbReactQuestionDraftStore(createBrowserCapabilityClient()),
      { onAssess: vi.fn() },
    )
    const first = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(first.result.current.draftLoaded).toBe(true))
    act(() =>
      first.result.current.handleFileChange('src/App.tsx', 'private saved source'),
    )
    await act(async () => first.result.current.handleAssess())
    expect(first.result.current.hasAssessError).toBe(false)
    first.unmount()
    const second = renderHook(() =>
      useReactQuestion({
        ...props,
        draftStore: IndexedDbReactQuestionDraftStore(createBrowserCapabilityClient()),
      }),
    )
    await waitFor(() => expect(second.result.current.draftLoaded).toBe(true))
    expect(second.result.current.files[0]?.content).toBe('private saved source')
    second.unmount()
    const other = renderHook(() =>
      useReactQuestion({
        ...props,
        accountId: 'account-2',
        draftStore: IndexedDbReactQuestionDraftStore(createBrowserCapabilityClient()),
      }),
    )
    await waitFor(() => expect(other.result.current.draftLoaded).toBe(true))
    expect(other.result.current.files[0]?.content).toBe(QUESTION.initialFiles[0]?.content)
  })

  it('keeps legacy source local and blocks restore until capability validation recovers', async () => {
    const { store } = createDraftStore()
    const props = createProps(store, { onAssess: vi.fn() })
    const key = keyFrom(props)
    const existing = {
      ...key,
      schemaVersion: 1 as const,
      files: [{ path: 'src/App.tsx', content: 'legacy private source' }],
      generation: 3,
      savedAt: 1,
      tombstone: false,
    }
    const read = vi.mocked(store.read)
    const validate = vi.mocked(store.validateAccountCapability)
    read.mockResolvedValue(existing)
    validate
      .mockRejectedValueOnce(new Error('identity unavailable'))
      .mockResolvedValue('active')
    const { result } = renderHook(() => useReactQuestion(props))

    await waitFor(() => expect(result.current.hasSaveError).toBe(true))
    expect(result.current.draftLoaded).toBe(false)
    expect(read).not.toHaveBeenCalled()
    await act(async () => result.current.handleAssess())
    expect(props.onAssess).not.toHaveBeenCalled()

    await act(async () => window.dispatchEvent(new Event('online')))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    expect(result.current.files[0]?.content).toBe('legacy private source')
    expect(validate).toHaveBeenCalledTimes(2)
  })

  it('clears in-memory code and blocks assessment when another tab revokes the account', async () => {
    const { store, publishAccountRevoked } = createDraftStore()
    const onAnswerValidityChange = vi.fn()
    const props = createProps(store, { onAnswerValidityChange, onAssess: vi.fn() })
    const key = keyFrom(props)
    vi.mocked(store.read).mockResolvedValue({
      ...key,
      schemaVersion: 1,
      files: [{ path: 'src/App.tsx', content: 'private answer' }],
      generation: 2,
      savedAt: 1,
      tombstone: false,
    })
    const { result } = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(result.current.files[0]?.content).toBe('private answer'))

    act(() => publishAccountRevoked())

    expect(result.current.files[0]?.content).toBe(QUESTION.initialFiles[0]?.content)
    expect(result.current.draftLoaded).toBe(true)
    expect(result.current.isDraftInvalidated).toBe(true)
    expect(onAnswerValidityChange).toHaveBeenLastCalledWith(false)
    await act(async () => result.current.handleAssess())
    expect(props.onAssess).not.toHaveBeenCalled()
    expect(store.clearTombstone).not.toHaveBeenCalled()
  })

  it('clears in-memory code when capability validation reports revocation', async () => {
    const { store } = createDraftStore({
      validateAccountCapability: vi.fn(async () => 'revoked' as const),
    })
    const onAssess = vi.fn()
    const props = createProps(store, { onAssess })
    const { result } = renderHook(() => useReactQuestion(props))

    await waitFor(() => expect(result.current.isDraftInvalidated).toBe(true))

    expect(result.current.draftLoaded).toBe(true)
    expect(result.current.files).toEqual([
      { path: 'src/App.tsx', content: QUESTION.initialFiles[0]?.content ?? '' },
    ])
    expect(store.read).not.toHaveBeenCalled()
    await act(async () => result.current.handleAssess())
    expect(onAssess).not.toHaveBeenCalled()
  })

  it('blocks a stale tab assessment instead of overwriting another tab stored answer', async () => {
    installIndexedDB()
    const props = createProps(
      IndexedDbReactQuestionDraftStore(createBrowserCapabilityClient()),
      { onAssess: vi.fn() },
    )
    const first = renderHook(() => useReactQuestion(props))
    const otherProps = {
      ...props,
      draftStore: IndexedDbReactQuestionDraftStore(createBrowserCapabilityClient()),
      onAssess: vi.fn(),
    }
    const other = renderHook(() => useReactQuestion(otherProps))
    await waitFor(() =>
      expect(first.result.current.draftLoaded && other.result.current.draftLoaded).toBe(
        true,
      ),
    )
    act(() => first.result.current.handleFileChange('src/App.tsx', 'first tab answer'))
    await act(async () => first.result.current.handleAssess())
    act(() => other.result.current.handleFileChange('src/App.tsx', 'stale tab answer'))
    await act(async () => other.result.current.handleAssess())
    expect(otherProps.onAssess).not.toHaveBeenCalled()
    expect(other.result.current.hasAssessError).toBe(true)
    expect(other.result.current.isDraftInvalidated).toBe(true)
    await act(async () => other.result.current.handleAssess())
    expect(otherProps.onAssess).not.toHaveBeenCalled()
    first.unmount()
    other.unmount()
    const restored = renderHook(() =>
      useReactQuestion({
        ...props,
        draftStore: IndexedDbReactQuestionDraftStore(createBrowserCapabilityClient()),
      }),
    )
    await waitFor(() => expect(restored.result.current.draftLoaded).toBe(true))
    expect(restored.result.current.files[0]?.content).toBe('first tab answer')
  })

  it('recovers a corrupt browser draft without exposing its invalid source', async () => {
    const records = installIndexedDB()
    records.set(
      'account-1\u001fgoal-1\u001fskill-1\u001fcompetency-1\u001factivity-1\u001freact-1\u001frevision-1',
      { generation: 'corrupt', files: [{ path: '../secret', content: 'untrusted' }] },
    )
    const props = createProps(
      IndexedDbReactQuestionDraftStore(createBrowserCapabilityClient()),
      { onAssess: vi.fn() },
    )
    const { result } = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    expect(result.current.files[0]?.content).toBe(QUESTION.initialFiles[0]?.content)
    expect(result.current.isDraftInvalidated).toBe(false)
    await act(async () => result.current.handleAssess())
    expect(props.onAssess).toHaveBeenCalledWith([
      { path: 'src/App.tsx', content: QUESTION.initialFiles[0]?.content },
    ])
  })
})
