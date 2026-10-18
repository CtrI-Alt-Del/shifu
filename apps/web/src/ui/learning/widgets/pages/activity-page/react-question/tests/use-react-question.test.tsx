import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ReactQuestion as ReactQuestionModel } from '@/core/learning/choice-activity'
import { ReactQuestionDraftStore } from '@/core/learning/react-question-draft/react-question-draft-store'

import { useReactQuestion } from '../use-react-question'

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
  additionalFilePolicy: null,
  criteria: [{ key: 'complete', name: 'Completude', weightPercentage: 100 }],
}

function installIndexedDB() {
  const records = new Map<IDBValidKey, unknown>()
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
            const request = {
              result: undefined as unknown,
              error: null as DOMException | null,
              onsuccess: null as ((event: Event) => void) | null,
              onerror: null as ((event: Event) => void) | null,
            }
            queueMicrotask(() => {
              request.result = records.get(key)
              request.onsuccess?.(new Event('success'))
              setTimeout(() => transaction.oncomplete?.(new Event('complete')), 0)
            })
            return request
          },
          put(value: unknown, key: IDBValidKey) {
            records.set(key, value)
            setTimeout(() => transaction.oncomplete?.(new Event('complete')), 0)
            return {}
          },
          openCursor() {
            const request = {
              result: null as { continue: () => void } | null,
              onsuccess: null as ((event: Event) => void) | null,
              onerror: null as ((event: Event) => void) | null,
            }
            queueMicrotask(() => {
              request.onsuccess?.(new Event('success'))
              setTimeout(() => transaction.oncomplete?.(new Event('complete')), 0)
            })
            return request
          },
        })),
      }
      return transaction
    }),
  }
  const indexedDBMock = {
    open: vi.fn(() => {
      const request = {
        result: database,
        error: null as DOMException | null,
        onsuccess: null as ((event: Event) => void) | null,
        onerror: null as ((event: Event) => void) | null,
        onupgradeneeded: null as ((event: IDBVersionChangeEvent) => void) | null,
      }
      queueMicrotask(() => {
        request.onupgradeneeded?.(new Event('upgradeneeded') as IDBVersionChangeEvent)
        request.onsuccess?.(new Event('success'))
      })
      return request
    }),
  }
  vi.stubGlobal('indexedDB', indexedDBMock)
  return () => records
}

describe('useReactQuestion draft lifecycle', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('flushes the current draft before preliminary assessment', async () => {
    installIndexedDB()
    const onAssess = vi.fn(async () => {
      const saved = await ReactQuestionDraftStore.read({
        accountId: 'account-1',
        goalId: 'goal-1',
        skillId: 'skill-1',
        competencyId: 'competency-1',
        activityId: 'activity-1',
        questionKey: 'react-1',
        activityRevision: 'revision-1',
      })
      expect(saved?.files).toEqual([
        { path: 'src/App.tsx', content: 'export default function App() {}' },
      ])
    })
    const { result } = renderHook(() =>
      useReactQuestion({
        question,
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
        onAssess,
      }),
    )
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    await act(async () => result.current.handleAssess())

    expect(onAssess).toHaveBeenCalledOnce()
    expect(result.current.hasAssessError).toBe(false)
  })

  it('does not assess when a draft cannot be saved', async () => {
    installIndexedDB()
    const onAssess = vi.fn()
    const { result } = renderHook(() =>
      useReactQuestion({
        question,
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
        onAssess,
      }),
    )
    await waitFor(() => expect(result.current.draftLoaded).toBe(true))
    vi.stubGlobal('indexedDB', {
      open: () => {
        throw new DOMException('storage unavailable')
      },
    })
    await act(async () => result.current.handleAssess())

    expect(onAssess).not.toHaveBeenCalled()
    expect(result.current.hasAssessError).toBe(true)
    expect(result.current.hasSaveError).toBe(true)
  })

  it('assesses and restores a draft containing an allowed additional file', async () => {
    installIndexedDB()
    const questionWithAdditionalFile: ReactQuestionModel = {
      ...question,
      additionalFilePolicy: {
        allowedDirectories: ['src/components'],
        allowedExtensions: ['.tsx'],
        maxFiles: 1,
      },
    }
    const onAssess = vi.fn()
    const props = {
      question: questionWithAdditionalFile,
      accountId: 'account-additional',
      goalId: 'goal-1',
      skillId: 'skill-1',
      competencyId: 'competency-1',
      activityId: 'activity-1',
      activityRevision: 'revision-1',
      activeQuestionKeys: ['react-1'],
      isOnlineAuthority: true,
      questionNumber: 1,
      totalQuestions: 1,
      onAssess,
    }
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
    expect(onAssess).toHaveBeenCalledWith([
      { path: 'src/App.tsx', content: 'export default function App() {}' },
      { path: 'src/components/Badge.tsx', content: 'export const Badge = () => null' },
    ])
    expect(first.result.current.hasAssessError).toBe(false)
    first.unmount()

    const second = renderHook(() => useReactQuestion(props))
    await waitFor(() => expect(second.result.current.draftLoaded).toBe(true))
    expect(second.result.current.files).toEqual([
      { path: 'src/App.tsx', content: 'export default function App() {}' },
      { path: 'src/components/Badge.tsx', content: 'export const Badge = () => null' },
    ])
    expect(second.result.current.isDraftInvalidated).toBe(false)
  })
})
