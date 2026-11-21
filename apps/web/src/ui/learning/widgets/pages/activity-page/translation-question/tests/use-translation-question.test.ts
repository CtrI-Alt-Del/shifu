import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { TranslationQuestion } from '@/core/learning/choice-activity'
import { useSpeechRecognition } from '@/ui/shared/hooks/use-speech-recognition'

import { useTranslationQuestion } from '../use-translation-question'

vi.mock('@/ui/shared/hooks/use-speech-recognition', () => ({
  useSpeechRecognition: vi.fn(),
}))

const useSpeechRecognitionMock = vi.mocked(useSpeechRecognition)

const QUESTION: TranslationQuestion = {
  key: 'translation-1',
  kind: 'translation',
  prompt: 'Traduza o texto abaixo para o inglês.',
  sourceLanguage: 'Português',
  targetLanguage: 'Inglês',
  sourceText: 'Bom dia, como você está?',
  criteria: [
    { key: 'semantic_preservation', name: 'Preservação semântica', weightPercentage: 70 },
    { key: 'grammatical_adequacy', name: 'Adequação gramatical', weightPercentage: 30 },
  ],
}
const OTHER_QUESTION: TranslationQuestion = { ...QUESTION, key: 'translation-2' }

function speechRecognitionPorts(
  overrides: Partial<ReturnType<typeof useSpeechRecognition>> = {},
) {
  return {
    status: 'idle',
    error: null,
    elapsedSeconds: 0,
    languageAvailability: 'available',
    installationStatus: 'idle',
    installationError: null,
    canInstallLanguage: false,
    startRecognition: vi.fn().mockResolvedValue(null),
    finishRecognition: vi.fn(),
    cancelRecognition: vi.fn(),
    installLanguagePack: vi.fn(),
    ...overrides,
  } as unknown as ReturnType<typeof useSpeechRecognition>
}

describe('useTranslationQuestion', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it.each([
    ['en-US', 'pt-BR', 'Inglês (Estados Unidos)', 'Português (Brasil)'],
    ['Português', 'Inglês', 'Português', 'Inglês'],
  ])(
    'shows the languages %s and %s as pt-BR labels, keeping authored names as they are',
    (sourceLanguage, targetLanguage, sourceLabel, targetLabel) => {
      useSpeechRecognitionMock.mockReturnValue(speechRecognitionPorts())
      const { result } = renderHook(() =>
        useTranslationQuestion({
          onChange: vi.fn(),
          question: { ...QUESTION, sourceLanguage, targetLanguage },
          questionNumber: 1,
          totalQuestions: 1,
          value: '',
        }),
      )

      expect(result.current.sourceLanguageLabel).toBe(sourceLabel)
      expect(result.current.targetLanguageLabel).toBe(targetLabel)
    },
  )

  it('reports typed text directly through onChange', () => {
    const onChangeMock = vi.fn()
    useSpeechRecognitionMock.mockReturnValue(speechRecognitionPorts())
    const { result } = renderHook(() =>
      useTranslationQuestion({
        onChange: onChangeMock,
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        value: '',
      }),
    )

    act(() => result.current.handleChangeText('Novo texto'))

    expect(onChangeMock).toHaveBeenCalledWith('Novo texto')
  })

  it.each([
    ['en-US', 'en-US'],
    ['Inglês', 'en-US'],
    ['Português', 'pt-BR'],
  ])('dictates in the target language %s as %s', (targetLanguage, expected) => {
    useSpeechRecognitionMock.mockReturnValue(speechRecognitionPorts())

    renderHook(() =>
      useTranslationQuestion({
        onChange: vi.fn(),
        question: { ...QUESTION, targetLanguage },
        questionNumber: 1,
        totalQuestions: 1,
        value: '',
      }),
    )

    expect(useSpeechRecognitionMock).toHaveBeenCalledWith(expected)
  })

  it('treats dictation as unavailable when the target language cannot be resolved', async () => {
    const startRecognitionMock = vi.fn().mockResolvedValue('texto')
    const onChangeMock = vi.fn()
    useSpeechRecognitionMock.mockReturnValue(
      speechRecognitionPorts({ startRecognition: startRecognitionMock }),
    )
    const { result } = renderHook(() =>
      useTranslationQuestion({
        onChange: onChangeMock,
        question: { ...QUESTION, targetLanguage: 'Klingon' },
        questionNumber: 1,
        totalQuestions: 1,
        value: '',
      }),
    )

    await act(async () => result.current.handleStartDictation())

    expect(result.current.languageAvailability).toBe('unavailable')
    expect(startRecognitionMock).not.toHaveBeenCalled()
    expect(onChangeMock).not.toHaveBeenCalled()
  })

  it('blocks typed changes while disabled', () => {
    const onChangeMock = vi.fn()
    useSpeechRecognitionMock.mockReturnValue(speechRecognitionPorts())
    const { result } = renderHook(() =>
      useTranslationQuestion({
        disabled: true,
        onChange: onChangeMock,
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        value: '',
      }),
    )

    act(() => result.current.handleChangeText('Novo texto'))

    expect(onChangeMock).not.toHaveBeenCalled()
  })

  it('applies a dictated transcript immediately when there is no existing text', async () => {
    const onChangeMock = vi.fn()
    let resolveTranscript: (value: string | null) => void = () => undefined
    const startRecognitionMock = vi.fn(
      () =>
        new Promise<string | null>((resolve) => {
          resolveTranscript = resolve
        }),
    )
    useSpeechRecognitionMock.mockReturnValue(
      speechRecognitionPorts({ startRecognition: startRecognitionMock }),
    )
    const { result } = renderHook(() =>
      useTranslationQuestion({
        onChange: onChangeMock,
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        value: '',
      }),
    )

    let started: Promise<void> = Promise.resolve()
    act(() => {
      started = result.current.handleStartDictation()
    })
    await act(async () => {
      resolveTranscript('Texto ditado')
      await started
    })

    expect(onChangeMock).toHaveBeenCalledWith('Texto ditado')
    expect(result.current.pendingTranscript).toBeNull()
  })

  it('asks for confirmation before replacing existing text', async () => {
    const onChangeMock = vi.fn()
    let resolveTranscript: (value: string | null) => void = () => undefined
    const startRecognitionMock = vi.fn(
      () =>
        new Promise<string | null>((resolve) => {
          resolveTranscript = resolve
        }),
    )
    useSpeechRecognitionMock.mockReturnValue(
      speechRecognitionPorts({ startRecognition: startRecognitionMock }),
    )
    const { result } = renderHook(() =>
      useTranslationQuestion({
        onChange: onChangeMock,
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        value: 'Texto existente',
      }),
    )

    let started: Promise<void> = Promise.resolve()
    act(() => {
      started = result.current.handleStartDictation()
    })
    await act(async () => {
      resolveTranscript('Texto ditado')
      await started
    })

    expect(onChangeMock).not.toHaveBeenCalled()
    expect(result.current.pendingTranscript).toBe('Texto ditado')
  })

  it('confirming the pending transcript replaces the text and clears the prompt', async () => {
    const onChangeMock = vi.fn()
    let resolveTranscript: (value: string | null) => void = () => undefined
    const startRecognitionMock = vi.fn(
      () =>
        new Promise<string | null>((resolve) => {
          resolveTranscript = resolve
        }),
    )
    useSpeechRecognitionMock.mockReturnValue(
      speechRecognitionPorts({ startRecognition: startRecognitionMock }),
    )
    const { result } = renderHook(() =>
      useTranslationQuestion({
        onChange: onChangeMock,
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        value: 'Texto existente',
      }),
    )

    let started: Promise<void> = Promise.resolve()
    act(() => {
      started = result.current.handleStartDictation()
    })
    await act(async () => {
      resolveTranscript('Texto ditado')
      await started
    })
    act(() => result.current.handleConfirmReplace())

    expect(onChangeMock).toHaveBeenCalledWith('Texto ditado')
    expect(result.current.pendingTranscript).toBeNull()
  })

  it('declining the pending transcript keeps the original text untouched', async () => {
    const onChangeMock = vi.fn()
    let resolveTranscript: (value: string | null) => void = () => undefined
    const startRecognitionMock = vi.fn(
      () =>
        new Promise<string | null>((resolve) => {
          resolveTranscript = resolve
        }),
    )
    useSpeechRecognitionMock.mockReturnValue(
      speechRecognitionPorts({ startRecognition: startRecognitionMock }),
    )
    const { result } = renderHook(() =>
      useTranslationQuestion({
        onChange: onChangeMock,
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        value: 'Texto existente',
      }),
    )

    let started: Promise<void> = Promise.resolve()
    act(() => {
      started = result.current.handleStartDictation()
    })
    await act(async () => {
      resolveTranscript('Texto ditado')
      await started
    })
    act(() => result.current.handleDeclineReplace())

    expect(onChangeMock).not.toHaveBeenCalled()
    expect(result.current.pendingTranscript).toBeNull()
  })

  it.each(['cancelled', 'denied', 'unavailable', 'failed'])(
    'preserves existing text when dictation produces no transcript: %s',
    async () => {
      const onChangeMock = vi.fn()
      const startRecognitionMock = vi.fn().mockResolvedValue(null)
      useSpeechRecognitionMock.mockReturnValue(
        speechRecognitionPorts({ startRecognition: startRecognitionMock }),
      )
      const { result } = renderHook(() =>
        useTranslationQuestion({
          onChange: onChangeMock,
          question: QUESTION,
          questionNumber: 1,
          totalQuestions: 1,
          value: 'Texto preservado',
        }),
      )

      await act(async () => result.current.handleStartDictation())

      expect(onChangeMock).not.toHaveBeenCalled()
      expect(result.current.pendingTranscript).toBeNull()
    },
  )

  it('does not start a new dictation operation while disabled', async () => {
    const startRecognitionMock = vi.fn().mockResolvedValue('Texto ditado')
    useSpeechRecognitionMock.mockReturnValue(
      speechRecognitionPorts({ startRecognition: startRecognitionMock }),
    )
    const { result } = renderHook(() =>
      useTranslationQuestion({
        disabled: true,
        onChange: vi.fn(),
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        value: '',
      }),
    )

    await act(async () => result.current.handleStartDictation())

    expect(startRecognitionMock).not.toHaveBeenCalled()
  })

  it('stops the active recognition through the shared hook', () => {
    const finishRecognitionMock = vi.fn()
    useSpeechRecognitionMock.mockReturnValue(
      speechRecognitionPorts({ finishRecognition: finishRecognitionMock }),
    )
    const { result } = renderHook(() =>
      useTranslationQuestion({
        onChange: vi.fn(),
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        value: '',
      }),
    )

    act(() => result.current.handleStopDictation())

    expect(finishRecognitionMock).toHaveBeenCalledOnce()
  })

  it('cancels the active recognition and clears any pending transcript', async () => {
    const onChangeMock = vi.fn()
    const cancelRecognitionMock = vi.fn()
    let resolveTranscript: (value: string | null) => void = () => undefined
    const startRecognitionMock = vi.fn(
      () =>
        new Promise<string | null>((resolve) => {
          resolveTranscript = resolve
        }),
    )
    useSpeechRecognitionMock.mockReturnValue(
      speechRecognitionPorts({
        cancelRecognition: cancelRecognitionMock,
        startRecognition: startRecognitionMock,
      }),
    )
    const { result } = renderHook(() =>
      useTranslationQuestion({
        onChange: onChangeMock,
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        value: 'Texto existente',
      }),
    )

    let started: Promise<void> = Promise.resolve()
    act(() => {
      started = result.current.handleStartDictation()
    })
    act(() => result.current.handleCancelDictation())
    resolveTranscript('Texto ditado tardio')
    await act(async () => started)

    expect(cancelRecognitionMock).toHaveBeenCalled()
    expect(result.current.pendingTranscript).toBeNull()
    expect(onChangeMock).not.toHaveBeenCalled()
  })

  it('releases the dictation operation when the question changes', () => {
    const cancelRecognitionMock = vi.fn()
    useSpeechRecognitionMock.mockReturnValue(
      speechRecognitionPorts({ cancelRecognition: cancelRecognitionMock }),
    )
    const { rerender } = renderHook(
      (props: { question: TranslationQuestion }) =>
        useTranslationQuestion({
          onChange: vi.fn(),
          question: props.question,
          questionNumber: 1,
          totalQuestions: 1,
          value: '',
        }),
      { initialProps: { question: QUESTION } },
    )

    rerender({ question: OTHER_QUESTION })

    expect(cancelRecognitionMock).toHaveBeenCalled()
  })

  it('releases the dictation operation on unmount', () => {
    const cancelRecognitionMock = vi.fn()
    useSpeechRecognitionMock.mockReturnValue(
      speechRecognitionPorts({ cancelRecognition: cancelRecognitionMock }),
    )
    const { unmount } = renderHook(() =>
      useTranslationQuestion({
        onChange: vi.fn(),
        question: QUESTION,
        questionNumber: 1,
        totalQuestions: 1,
        value: '',
      }),
    )
    cancelRecognitionMock.mockClear()

    unmount()

    expect(cancelRecognitionMock).toHaveBeenCalled()
  })
})
