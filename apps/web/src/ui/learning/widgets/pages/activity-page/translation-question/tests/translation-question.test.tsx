import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { TranslationQuestion as TranslationQuestionCore } from '@/core/learning/choice-activity'

import { TranslationQuestion } from '..'
import type { TranslationQuestionProps } from '../use-translation-question'
import { useTranslationQuestion } from '../use-translation-question'

vi.mock('../use-translation-question', () => ({
  useTranslationQuestion: vi.fn(),
}))

const useTranslationQuestionMock = vi.mocked(useTranslationQuestion)

const QUESTION: TranslationQuestionCore = {
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

function baseHookValue(): ReturnType<typeof useTranslationQuestion> {
  return {
    status: 'idle',
    error: null,
    elapsedSeconds: 0,
    languageAvailability: 'available',
    pendingTranscript: null,
    handleChangeText: vi.fn(),
    handleStartDictation: vi.fn(),
    handleStopDictation: vi.fn(),
    handleCancelDictation: vi.fn(),
    handleConfirmReplace: vi.fn(),
    handleDeclineReplace: vi.fn(),
  }
}

function renderQuestion(overrides: Partial<TranslationQuestionProps> = {}) {
  const props: TranslationQuestionProps = {
    onChange: vi.fn(),
    question: QUESTION,
    questionNumber: 1,
    totalQuestions: 3,
    value: '',
    ...overrides,
  }
  render(<TranslationQuestion {...props} />)
  return props
}

describe('TranslationQuestion', () => {
  beforeEach(() => {
    useTranslationQuestionMock.mockReturnValue(baseHookValue())
  })

  afterEach(cleanup)

  it('renders the prompt, languages, source text and current answer', () => {
    renderQuestion({ value: 'Good morning, how are you?' })

    expect(
      screen.getByRole('heading', { name: 'Traduza o texto abaixo para o inglês.' }),
    ).toBeVisible()
    expect(screen.getByText('Português')).toBeVisible()
    expect(screen.getByText('Inglês')).toBeVisible()
    expect(screen.getByText('Bom dia, como você está?')).toBeVisible()
    expect(screen.getByLabelText('Sua tradução')).toHaveValue(
      'Good morning, how are you?',
    )
  })

  it('reports typed changes through the hook handler', () => {
    const handleChangeTextMock = vi.fn()
    useTranslationQuestionMock.mockReturnValue({
      ...baseHookValue(),
      handleChangeText: handleChangeTextMock,
    })
    renderQuestion()

    fireEvent.change(screen.getByLabelText('Sua tradução'), {
      target: { value: 'Translated text' },
    })

    expect(handleChangeTextMock).toHaveBeenCalledWith('Translated text')
  })

  it('disables the text field and dictation controls while frozen', () => {
    renderQuestion({ disabled: true })

    expect(screen.getByLabelText('Sua tradução')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Iniciar ditado' })).toBeDisabled()
  })

  it('delegates start, stop and cancel dictation actions', () => {
    const handleStartDictationMock = vi.fn()
    const handleStopDictationMock = vi.fn()
    const handleCancelDictationMock = vi.fn()
    useTranslationQuestionMock.mockReturnValue({
      ...baseHookValue(),
      status: 'recording',
      handleStartDictation: handleStartDictationMock,
      handleStopDictation: handleStopDictationMock,
      handleCancelDictation: handleCancelDictationMock,
    })
    renderQuestion()

    fireEvent.click(screen.getByRole('button', { name: 'Parar ditado' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar ditado' }))

    expect(handleStopDictationMock).toHaveBeenCalledOnce()
    expect(handleCancelDictationMock).toHaveBeenCalledOnce()
  })

  it('shows recording status text with elapsed time, never color-only', () => {
    useTranslationQuestionMock.mockReturnValue({
      ...baseHookValue(),
      status: 'recording',
      elapsedSeconds: 7,
    })
    renderQuestion()

    expect(screen.getByText('Gravando ditado… (7s)')).toBeVisible()
  })

  it('surfaces a dictation error as visible text while preserving the typed answer', () => {
    useTranslationQuestionMock.mockReturnValue({
      ...baseHookValue(),
      status: 'error',
      error: 'Permissão do microfone negada. Você pode continuar digitando.',
    })
    renderQuestion({ value: 'Texto preservado' })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Permissão do microfone negada. Você pode continuar digitando.',
    )
    expect(screen.getByLabelText('Sua tradução')).toHaveValue('Texto preservado')
  })

  it('hides dictation controls and explains unavailability when the browser lacks support', () => {
    useTranslationQuestionMock.mockReturnValue({
      ...baseHookValue(),
      languageAvailability: 'unavailable',
    })
    renderQuestion({ value: 'Texto preservado' })

    expect(
      screen.queryByRole('button', { name: 'Iniciar ditado' }),
    ).not.toBeInTheDocument()
    expect(
      screen.getByText('Ditado indisponível neste navegador. Continue digitando.'),
    ).toBeVisible()
    expect(screen.getByLabelText('Sua tradução')).toHaveValue('Texto preservado')
  })

  it('asks for confirmation before replacing existing text with a dictated transcript', () => {
    const handleConfirmReplaceMock = vi.fn()
    const handleDeclineReplaceMock = vi.fn()
    useTranslationQuestionMock.mockReturnValue({
      ...baseHookValue(),
      pendingTranscript: 'Novo texto ditado',
      handleConfirmReplace: handleConfirmReplaceMock,
      handleDeclineReplace: handleDeclineReplaceMock,
    })
    renderQuestion({ value: 'Texto original' })

    expect(screen.getByText('Substituir texto por ditado?')).toBeVisible()
    expect(screen.getByText('Novo texto ditado')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar' }))
    expect(handleConfirmReplaceMock).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(handleDeclineReplaceMock).toHaveBeenCalledOnce()
  })
})
