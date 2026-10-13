import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useMentorContextProvider } from '../use-mentor-context-provider'

const ports = vi.hoisted(() => ({
  create: vi.fn(),
  list: vi.fn(),
  detail: vi.fn(),
  submit: vi.fn(),
  reset: vi.fn(),
  navigate: vi.fn(),
  remove: vi.fn(),
  location: { pathname: '/intelligence', search: {} },
  submitting: false,
  localRecognition: false,
}))
// Optional local-mode regressions select the shared hook's real local implementation.
vi.mock('@/ui/shared/hooks/use-speech-recognition', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('@/ui/shared/hooks/use-speech-recognition')>()
  return {
    ...actual,
    useSpeechRecognition: (language: string, processLocally: boolean) =>
      actual.useSpeechRecognition(language, ports.localRecognition || processLocally),
  }
})
vi.mock('@tanstack/react-router', () => ({
  useLocation: () => ports.location,
  useNavigate: () => ports.navigate,
}))
vi.mock('@/ui/intelligence/hooks/use-create-mentor-session-action', () => ({
  useCreateMentorSessionAction: () => ({
    createMentorSession: ports.create,
    isCreatingMentorSession: ports.submitting,
    resetCreateMentorSession: ports.reset,
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-mentor-sessions-query', () => ({
  useMentorSessionsQuery: () => ({ readMentorSessions: ports.list }),
}))
vi.mock('@/ui/intelligence/hooks/use-mentor-session-query', () => ({
  useMentorSessionQuery: () => ({ readMentorSession: ports.detail }),
}))
vi.mock('@/ui/intelligence/hooks/use-submit-mentor-message-action', () => ({
  useSubmitMentorMessageAction: () => ({
    submitMentorMessage: ports.submit,
    isPending: ports.submitting,
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-cancel-mentor-response-action', () => ({
  useCancelMentorResponseAction: () => ({
    cancelMentorResponse: vi.fn(),
    isPending: false,
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-retry-mentor-response-action', () => ({
  useRetryMentorResponseAction: () => ({
    retryMentorResponse: vi.fn(),
    isPending: false,
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-remove-mentor-session-action', () => ({
  useRemoveMentorSessionAction: () => ({
    removeMentorSession: ports.remove,
    isRemovingMentorSession: false,
    resetRemoveMentorSession: ports.reset,
  }),
}))
vi.mock('@/ui/intelligence/hooks/use-rename-mentor-session-action', () => ({
  useRenameMentorSessionAction: () => ({
    renameMentorSession: vi.fn(),
    isRenamingMentorSession: false,
    resetRenameMentorSession: ports.reset,
  }),
}))

type ResultEvent = {
  resultIndex: number
  results: Array<{ isFinal: boolean; 0: { transcript: string } }>
}
class BrowserRecognition {
  static instances: BrowserRecognition[] = []
  static available = vi.fn()
  static install = vi.fn()
  processLocally = false
  lang = ''
  continuous = false
  interimResults = true
  maxAlternatives = 0
  onstart: (() => void) | null = null
  onend: (() => void) | null = null
  onerror: ((event: { error: string }) => void) | null = null
  onresult: ((event: ResultEvent) => void) | null = null
  onnomatch: (() => void) | null = null
  start = vi.fn()
  stop = vi.fn()
  abort = vi.fn()
  constructor() {
    BrowserRecognition.instances.push(this)
  }
  results(...transcripts: string[]) {
    this.onresult?.({
      resultIndex: 0,
      results: transcripts.map((transcript) => ({ isFinal: true, 0: { transcript } })),
    })
  }
}
const session = {
  session: {
    id: 'session-a',
    title: 'Dúvida',
    createdAt: 'now',
    updatedAt: 'now',
    lastActivityAt: 'now',
  },
  messages: { items: [], nextCursor: null },
  pendingLearnerMessageId: null,
}
async function openProvider() {
  const value = renderHook(({ email }) => useMentorContextProvider(email), {
    initialProps: { email: 'learner@example.com' },
  })
  await waitFor(() => expect(value.result.current.isValidatingScope).toBe(false))
  await waitFor(() =>
    expect(value.result.current.dictationLanguageAvailability).toBe('available'),
  )
  return value
}
async function start(
  value: Awaited<ReturnType<typeof openProvider>>,
  surface: 'page' | 'fab' = 'page',
) {
  await act(async () => {
    void value.result.current.startDictation(surface)
  })
  const recognition = [...BrowserRecognition.instances]
    .reverse()
    .find((instance) => instance.start.mock.calls.length > 0)
  if (!recognition) throw new Error('Expected an explicitly started native recognition')
  return recognition
}
function finish(
  value: Awaited<ReturnType<typeof openProvider>>,
  recognition: BrowserRecognition,
  text = 'texto reconhecido',
) {
  act(() => {
    recognition.onstart?.()
    value.result.current.finishDictation()
    recognition.results(text)
    recognition.onend?.()
  })
}
beforeEach(() => {
  vi.clearAllMocks()
  BrowserRecognition.instances = []
  BrowserRecognition.available.mockResolvedValue('available')
  BrowserRecognition.install.mockResolvedValue(true)
  vi.stubGlobal('SpeechRecognition', BrowserRecognition)
  ports.submitting = false
  ports.localRecognition = false
  ports.location = { pathname: '/intelligence', search: {} }
  ports.list.mockResolvedValue({ items: [], nextCursor: null })
  ports.detail.mockResolvedValue(session)
  ports.create.mockResolvedValue(session)
  ports.submit.mockResolvedValue(session)
  ports.remove.mockResolvedValue(undefined)
})
afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('Mentor native dictation consumer', () => {
  it.each(['page', 'fab'] as const)(
    'starts native recognition only on an explicit gesture on %s',
    async (surface) => {
      const value = await openProvider()
      expect(
        BrowserRecognition.instances.every(
          (instance) => instance.start.mock.calls.length === 0,
        ),
      ).toBe(true)
      const recognition = await start(value, surface)
      expect(recognition.start).toHaveBeenCalledOnce()
      expect(recognition.lang).toBe('pt-BR')
      expect(recognition.processLocally).toBe(false)
    },
  )
  it('stops recognition and awaits finalization', async () => {
    const value = await openProvider()
    const recognition = await start(value)
    act(() => recognition.onstart?.())
    act(() => value.result.current.finishDictation())
    expect(recognition.stop).toHaveBeenCalledOnce()
    expect(value.result.current.dictationStatus).toBe('transcribing')
    expect(value.result.current.draft).toBe('')
    act(() => {
      recognition.results('resultado')
      recognition.onend?.()
    })
    await waitFor(() => expect(value.result.current.draft).toBe('resultado'))
  })
  it.each(['', '  Texto anterior\ncom detalhes  '])(
    'appends final text without changing the existing draft %j',
    async (original) => {
      const value = await openProvider()
      act(() => value.result.current.setDraft(original))
      const recognition = await start(value)
      finish(value, recognition, '  resultado  ')
      await waitFor(() =>
        expect(value.result.current.draft).toBe(
          original + (original ? '\n' : '') + 'resultado',
        ),
      )
    },
  )
  it('sends only the explicitly reviewed text', async () => {
    const value = await openProvider()
    const recognition = await start(value)
    finish(value, recognition, 'transcrito')
    await waitFor(() => expect(value.result.current.draft).toBe('transcrito'))
    expect(ports.create).not.toHaveBeenCalled()
    act(() => value.result.current.setDraft('Texto revisado pelo aprendiz'))
    await act(async () => value.result.current.sendFirstMessage('page'))
    expect(ports.create).toHaveBeenCalledWith(
      expect.objectContaining({ firstMessage: 'Texto revisado pelo aprendiz' }),
    )
    expect(value.result.current.draft).toBe('')
  })
  it('creates no message during dictation', async () => {
    const value = await openProvider()
    const recognition = await start(value)
    act(() => {
      recognition.onstart?.()
      recognition.results('ainda não enviado')
    })
    expect(value.result.current.draft).toBe('')
    expect(value.result.current.selectedSessionId).toBeNull()
    expect(ports.create).not.toHaveBeenCalled()
    expect(ports.submit).not.toHaveBeenCalled()
    act(() => value.result.current.cancelDictation())
    expect(ports.create).not.toHaveBeenCalled()
  })
  it.each(['validating', 'submitting', 'response', 'message'])(
    'guards dictation while conversation access or response is pending: %s',
    async (guard) => {
      const value = await openProvider()
      if (guard === 'validating') {
        ports.list.mockReturnValue(new Promise(() => {}))
        act(() => {
          void value.result.current.refresh()
        })
      } else if (guard === 'submitting') {
        ports.submitting = true
        value.rerender({ email: 'learner@example.com' })
      } else {
        ports.detail.mockResolvedValue({
          ...session,
          pendingLearnerMessageId: 'pending',
          ...(guard === 'response'
            ? { response: { status: 'processing', blocks: [], consultations: [] } }
            : {}),
        })
        await act(async () => value.result.current.selectSession('session-a'))
      }
      await act(async () => value.result.current.startDictation('page'))
      expect(
        BrowserRecognition.instances.every(
          (instance) => instance.start.mock.calls.length === 0,
        ),
      ).toBe(true)
    },
  )
  it.each(['preparing', 'recording', 'transcribing'])(
    'cancels every active stage without changing the draft: %s',
    async (stage) => {
      const value = await openProvider()
      act(() => value.result.current.setDraft('preservado'))
      const recognition = await start(value)
      if (stage !== 'preparing') act(() => recognition.onstart?.())
      if (stage === 'transcribing') act(() => value.result.current.finishDictation())
      act(() => {
        recognition.results('descartar')
        value.result.current.cancelDictation()
      })
      expect(recognition.abort).toHaveBeenCalledOnce()
      expect(value.result.current.draft).toBe('preservado')
      expect(value.result.current.dictationStatus).toBe('idle')
    },
  )
  it.each(['not-allowed', 'service-not-allowed'])(
    'preserves the draft on permission denial: %s',
    async (error) => {
      const value = await openProvider()
      act(() => value.result.current.setDraft('preservado'))
      const recognition = await start(value)
      act(() => recognition.onerror?.({ error }))
      expect(value.result.current.dictationError).toBe(
        'Permissão do microfone negada. Você pode continuar digitando.',
      )
      expect(value.result.current.draft).toBe('preservado')
    },
  )
  it('preserves the draft on microphone failure', async () => {
    const value = await openProvider()
    act(() => value.result.current.setDraft('preservado'))
    const recognition = await start(value)
    act(() => recognition.onerror?.({ error: 'audio-capture' }))
    expect(value.result.current.dictationError).toBe(
      'Não foi possível usar o microfone. Tente novamente ou continue digitando.',
    )
    expect(value.result.current.draft).toBe('preservado')
  })
  it.each(['no-speech', 'network', 'nomatch', 'empty'])(
    'rejects empty or failed recognition without partial text: %s',
    async (error) => {
      const value = await openProvider()
      act(() => value.result.current.setDraft('preservado'))
      const recognition = await start(value)
      act(() => {
        if (error === 'nomatch') recognition.onnomatch?.()
        else if (error === 'empty') {
          recognition.results('   ')
          recognition.onend?.()
        } else {
          recognition.results('parcial')
          recognition.onerror?.({ error })
        }
      })
      expect(value.result.current.dictationError).toBe(
        'Não foi possível reconhecer o ditado. Tente novamente ou continue digitando.',
      )
      expect(value.result.current.draft).toBe('preservado')
    },
  )
  it('times out preparation after thirty seconds', async () => {
    const value = await openProvider()
    vi.useFakeTimers()
    const recognition = await start(value)
    act(() => vi.advanceTimersByTime(29_999))
    expect(value.result.current.dictationStatus).toBe('preparing')
    act(() => vi.advanceTimersByTime(1))
    expect(value.result.current.dictationError).toBe(
      'Não foi possível iniciar o ditado. Tente novamente ou continue digitando.',
    )
    expect(recognition.abort).toHaveBeenCalledOnce()
  })
  it('times out finalization after ten seconds', async () => {
    const value = await openProvider()
    vi.useFakeTimers()
    const recognition = await start(value)
    act(() => {
      recognition.onstart?.()
      value.result.current.finishDictation()
    })
    act(() => vi.advanceTimersByTime(9_999))
    expect(value.result.current.dictationStatus).toBe('transcribing')
    act(() => vi.advanceTimersByTime(1))
    expect(value.result.current.dictationError).toBe(
      'Não foi possível concluir o ditado. Tente novamente ou continue digitando.',
    )
    expect(recognition.abort).toHaveBeenCalledOnce()
  })
  it('reviews a natural end without automatically restarting', async () => {
    const value = await openProvider()
    const recognition = await start(value)
    act(() => {
      recognition.onstart?.()
      recognition.results('fim natural')
      recognition.onend?.()
    })
    await waitFor(() => expect(value.result.current.draft).toBe('fim natural'))
    expect(value.result.current.dictationStatus).toBe('review')
    expect(recognition.start).toHaveBeenCalledOnce()
  })
  it.each(['close', 'select', 'new', 'delete', 'navigation', 'unmount', 'account'])(
    'aborts dictation when its owning scope is abandoned: %s',
    async (action) => {
      const value = await openProvider()
      if (action === 'delete')
        await act(async () => value.result.current.selectSession('session-a'))
      const recognition = await start(value, 'fab')
      act(() => recognition.onstart?.())
      if (action === 'select')
        await act(async () => value.result.current.selectSession('session-b'))
      else if (action === 'delete') {
        act(() => value.result.current.openRemoveDialog('session-a'))
        await act(async () => value.result.current.removeSession())
      } else if (action === 'new') act(() => value.result.current.startNewConversation())
      else if (action === 'navigation') {
        ports.location = { pathname: '/', search: {} }
        value.rerender({ email: 'learner@example.com' })
      } else if (action === 'account') value.rerender({ email: 'other@example.com' })
      else if (action === 'unmount') value.unmount()
      else act(() => value.result.current.closePanel())
      expect(recognition.abort).toHaveBeenCalledOnce()
      expect(recognition.onresult).toBeNull()
    },
  )
  it('rejects stale callbacks from an earlier operation', async () => {
    const value = await openProvider()
    const old = await start(value)
    const lateResult = old.onresult
    const lateEnd = old.onend
    act(() => value.result.current.cancelDictation())
    const fresh = await start(value)
    act(() => {
      lateResult?.({
        resultIndex: 0,
        results: [{ isFinal: true, 0: { transcript: 'antigo' } }],
      })
      lateEnd?.()
    })
    expect(value.result.current.draft).toBe('')
    finish(value, fresh, 'novo')
    await waitFor(() => expect(value.result.current.draft).toBe('novo'))
  })
  it('rejects recognition after the draft revision changes', async () => {
    const value = await openProvider()
    act(() => value.result.current.setDraft('original'))
    const recognition = await start(value)
    act(() => {
      value.result.current.setDraft('editado')
      recognition.results('ditado')
      recognition.onend?.()
    })
    await waitFor(() =>
      expect(value.result.current.dictationError).toBe(
        'Seu rascunho mudou. O ditado não foi aplicado.',
      ),
    )
    expect(value.result.current.draft).toBe('editado')
  })
  it('applies repeated final results only once in index order', async () => {
    const value = await openProvider()
    const recognition = await start(value)
    const end = recognition.onend
    act(() => {
      recognition.results('primeiro', 'segundo')
      recognition.results('primeiro', 'segundo')
      end?.()
      end?.()
    })
    await waitFor(() => expect(value.result.current.draft).toBe('primeiro segundo'))
  })
  it('cleans native handlers and timers at termination', async () => {
    const value = await openProvider()
    vi.useFakeTimers()
    const recognition = await start(value)
    finish(value, recognition)
    expect(recognition.onstart).toBeNull()
    expect(recognition.onresult).toBeNull()
    expect(recognition.onend).toBeNull()
    expect(recognition.onerror).toBeNull()
    expect(vi.getTimerCount()).toBe(0)
  })
  it('makes no transcription or audio transport calls', async () => {
    const fetch = vi.fn()
    vi.stubGlobal('fetch', fetch)
    const value = await openProvider()
    const recognition = await start(value)
    finish(value, recognition)
    expect(fetch).not.toHaveBeenCalled()
    expect(ports.create).not.toHaveBeenCalled()
    expect(ports.submit).not.toHaveBeenCalled()
  })
  it('creates no audio files or blobs', async () => {
    const blob = vi.spyOn(globalThis, 'Blob')
    const file = vi.spyOn(globalThis, 'File')
    const value = await openProvider()
    const recognition = await start(value)
    finish(value, recognition)
    expect(blob).not.toHaveBeenCalled()
    expect(file).not.toHaveBeenCalled()
    blob.mockRestore()
    file.mockRestore()
  })
  it('still requires real local processing support when explicitly selected', async () => {
    ports.localRecognition = true
    class RemoteRecognition extends BrowserRecognition {
      constructor() {
        super()
        delete (this as { processLocally?: boolean }).processLocally
      }
    }
    vi.stubGlobal('SpeechRecognition', RemoteRecognition)
    const value = renderHook(() => useMentorContextProvider('learner@example.com'))
    await waitFor(() =>
      expect(value.result.current.dictationLanguageAvailability).toBe('unavailable'),
    )
    await act(async () => value.result.current.startDictation())
    expect(
      BrowserRecognition.instances.every((instance) => !instance.start.mock.calls.length),
    ).toBe(true)
  })
  it('never installs in browser-managed mode even on an installation call', async () => {
    const value = await openProvider()
    await act(async () => value.result.current.installDictationLanguage())
    expect(BrowserRecognition.install).not.toHaveBeenCalled()
    expect(value.result.current.canInstallDictationLanguage).toBe(false)
    expect(value.result.current.dictationInstallationStatus).toBe('idle')
  })
  it('starts browser-managed recognition without local processing support', async () => {
    class RemoteRecognition extends BrowserRecognition {
      constructor() {
        super()
        delete (this as { processLocally?: boolean }).processLocally
      }
    }
    BrowserRecognition.available.mockImplementation(async ({ processLocally }) =>
      processLocally ? 'unavailable' : 'available',
    )
    vi.stubGlobal('SpeechRecognition', RemoteRecognition)
    const value = await openProvider()
    const recognition = await start(value)
    expect(recognition.start).toHaveBeenCalledOnce()
    expect(BrowserRecognition.available).toHaveBeenCalledWith({
      langs: ['pt-BR'],
      processLocally: false,
      quality: 'dictation',
    })
    expect(BrowserRecognition.install).not.toHaveBeenCalled()
    expect(value.result.current.canInstallDictationLanguage).toBe(false)
  })
  it('supports legacy browser recognition without static language APIs', async () => {
    class LegacyRecognition extends BrowserRecognition {}
    Object.defineProperty(LegacyRecognition, 'available', { value: undefined })
    Object.defineProperty(LegacyRecognition, 'install', { value: undefined })
    vi.stubGlobal('SpeechRecognition', undefined)
    vi.stubGlobal('webkitSpeechRecognition', LegacyRecognition)
    const value = await openProvider()
    const recognition = await start(value)
    expect(recognition.start).toHaveBeenCalledOnce()
    expect(recognition.processLocally).toBe(false)
    expect(recognition.lang).toBe('pt-BR')
    expect(value.result.current.canInstallDictationLanguage).toBe(false)
  })
  it.each(['unsupported', 'unavailable'])(
    'preserves typing when browser recognition is unavailable: %s',
    async (reason) => {
      if (reason === 'unsupported') vi.stubGlobal('SpeechRecognition', undefined)
      else BrowserRecognition.available.mockResolvedValue('unavailable')
      const value = renderHook(() => useMentorContextProvider('learner@example.com'))
      await waitFor(() =>
        expect(value.result.current.dictationLanguageAvailability).toBe('unavailable'),
      )
      act(() => value.result.current.setDraft('texto digitado'))
      await act(async () => value.result.current.sendFirstMessage())
      expect(ports.create).toHaveBeenCalledWith(
        expect.objectContaining({ firstMessage: 'texto digitado' }),
      )
      expect(BrowserRecognition.install).not.toHaveBeenCalled()
    },
  )
  it('installs Portuguese only on an explicit action', async () => {
    ports.localRecognition = true
    BrowserRecognition.available.mockResolvedValue('downloadable')
    const value = renderHook(() => useMentorContextProvider('learner@example.com'))
    await waitFor(() =>
      expect(value.result.current.canInstallDictationLanguage).toBe(true),
    )
    expect(BrowserRecognition.install).not.toHaveBeenCalled()
    BrowserRecognition.available.mockResolvedValue('available')
    await act(async () => value.result.current.installDictationLanguage())
    expect(BrowserRecognition.install).toHaveBeenCalledWith(
      expect.objectContaining({ langs: ['pt-BR'] }),
    )
    expect(
      BrowserRecognition.instances.every(
        (instance) => instance.start.mock.calls.length === 0,
      ),
    ).toBe(true)
  })
  it.each([false, 'throws'])(
    'preserves the draft when installation fails: %s',
    async (failure) => {
      ports.localRecognition = true
      const value = await openProvider()
      act(() => value.result.current.setDraft('preservado'))
      if (failure === false) BrowserRecognition.install.mockResolvedValue(false)
      else BrowserRecognition.install.mockRejectedValue(new DOMException('blocked'))
      await act(async () => value.result.current.installDictationLanguage())
      expect(value.result.current.dictationInstallationError).toBe(
        'Não foi possível instalar o pacote de idioma. Tente novamente ou continue digitando.',
      )
      expect(value.result.current.draft).toBe('preservado')
    },
  )
  it('announces installation success without starting recognition', async () => {
    ports.localRecognition = true
    const value = await openProvider()
    await act(async () => value.result.current.installDictationLanguage())
    expect(value.result.current.dictationInstallationStatus).toBe('installed')
    expect(
      BrowserRecognition.instances.every(
        (instance) => instance.start.mock.calls.length === 0,
      ),
    ).toBe(true)
  })
  it('never installs a language pack automatically', async () => {
    ports.localRecognition = true
    BrowserRecognition.available.mockResolvedValue('downloadable')
    const value = renderHook(() => useMentorContextProvider('learner@example.com'))
    await waitFor(() =>
      expect(value.result.current.dictationLanguageAvailability).toBe('downloadable'),
    )
    await act(async () => value.result.current.startDictation())
    expect(BrowserRecognition.install).not.toHaveBeenCalled()
    expect(
      BrowserRecognition.instances.every(
        (instance) => instance.start.mock.calls.length === 0,
      ),
    ).toBe(true)
  })
  it('sends only the explicitly reviewed text in an existing conversation', async () => {
    const value = await openProvider()
    await act(async () => value.result.current.selectSession('session-a'))
    act(() => value.result.current.setDraft('Original'))
    const recognition = await start(value)
    finish(value, recognition, 'Ditado')
    await waitFor(() => expect(value.result.current.draft).toBe('Original\nDitado'))
    expect(ports.submit).not.toHaveBeenCalled()
    act(() => value.result.current.setDraft('Revisão final'))
    await act(async () => value.result.current.sendFirstMessage('page'))
    expect(ports.create).not.toHaveBeenCalled()
    expect(ports.submit).toHaveBeenCalledWith(
      expect.objectContaining({ content: 'Revisão final', sessionId: 'session-a' }),
    )
  })
  it.each(['select', 'account'])(
    'rejects stale callbacks after scope change: %s',
    async (scope) => {
      const value = await openProvider()
      const recognition = await start(value)
      const onend = recognition.onend
      const onresult = recognition.onresult
      if (scope === 'select')
        await act(async () => value.result.current.selectSession('session-a'))
      else value.rerender({ email: 'other@example.com' })
      act(() => value.result.current.setDraft('Novo escopo'))
      act(() => {
        onresult?.({
          resultIndex: 0,
          results: [{ isFinal: true, 0: { transcript: 'Texto antigo' } }],
        })
        onend?.()
      })
      expect(value.result.current.draft).toBe('Novo escopo')
      expect(recognition.abort).toHaveBeenCalledOnce()
    },
  )
  it('cancels dictation when existing access validation rejects the account', async () => {
    const value = await openProvider()
    const recognition = await start(value)
    ports.list.mockRejectedValue(new Error('A sessão da conta mudou'))
    await act(async () => value.result.current.refresh())
    expect(recognition.abort).toHaveBeenCalledOnce()
    expect(value.result.current.dictationStatus).toBe('idle')
    expect(value.result.current.scopeError).toBeTruthy()
  })
  it('does not announce installation success when the language is still unavailable', async () => {
    ports.localRecognition = true
    BrowserRecognition.available.mockResolvedValue('downloadable')
    const value = renderHook(() => useMentorContextProvider('learner@example.com'))
    await waitFor(() =>
      expect(value.result.current.canInstallDictationLanguage).toBe(true),
    )
    BrowserRecognition.available.mockResolvedValue('unavailable')
    await act(async () => value.result.current.installDictationLanguage())
    expect(value.result.current.dictationInstallationStatus).toBe('failed')
    expect(value.result.current.canStartDictation).toBe(false)
    expect(
      BrowserRecognition.instances.every((instance) => !instance.start.mock.calls.length),
    ).toBe(true)
  })
  it('blocks dictation for an active response even without a pending message identifier', async () => {
    const value = await openProvider()
    ports.detail.mockResolvedValue({
      ...session,
      pendingLearnerMessageId: null,
      response: { status: 'processing', blocks: [], consultations: [] },
    })
    await act(async () => value.result.current.selectSession('session-a'))
    expect(value.result.current.canStartDictation).toBe(false)
    await act(async () => value.result.current.startDictation())
    expect(
      BrowserRecognition.instances.every((instance) => !instance.start.mock.calls.length),
    ).toBe(true)
  })
  it.each(['close', 'navigation', 'surface'])(
    'stops observing language installation after abandoning the flow: %s',
    async (scope) => {
      ports.localRecognition = true
      BrowserRecognition.available.mockResolvedValue('downloadable')
      let complete: (installed: boolean) => void = () => undefined
      BrowserRecognition.install.mockReturnValue(
        new Promise<boolean>((resolve) => {
          complete = resolve
        }),
      )
      const value = renderHook(() => useMentorContextProvider('learner@example.com'))
      await waitFor(() =>
        expect(value.result.current.canInstallDictationLanguage).toBe(true),
      )
      act(() => {
        value.result.current.setDraft('Preservado')
        void value.result.current.installDictationLanguage('fab')
      })
      expect(value.result.current.dictationInstallationStatus).toBe('installing')
      if (scope === 'navigation') {
        ports.location.pathname = '/gamification'
        value.rerender()
      } else
        act(() =>
          scope === 'close'
            ? value.result.current.closePanel()
            : value.result.current.releaseDictationSurface('fab'),
        )
      await act(async () => {
        complete(true)
      })
      expect(value.result.current.dictationInstallationStatus).toBe('idle')
      expect(value.result.current.dictationInstallationError).toBeNull()
      expect(value.result.current.draft).toBe('Preservado')
      expect(
        BrowserRecognition.instances.every(
          (instance) => !instance.start.mock.calls.length,
        ),
      ).toBe(true)
    },
  )
})
