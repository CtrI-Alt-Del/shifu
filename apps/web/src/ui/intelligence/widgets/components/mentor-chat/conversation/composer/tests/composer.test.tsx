import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import type { FormEvent } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { Composer } from '..'
import { useComposer } from '../use-composer'

vi.mock('../use-composer', () => ({ useComposer: vi.fn() }))
const useComposerMock = vi.mocked(useComposer)
const sendFirstMessageMock = vi.fn()
const setDraftMock = vi.fn()

describe('Composer', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)

  it.each(['page', 'fab'] as const)(
    'submits the first message and keeps future controls unavailable on %s',
    (surface) => {
      useComposerMock.mockReturnValue({
        canSend: true,
        draft: 'Dúvida',
        handleSubmit: (event: FormEvent<HTMLFormElement>) => {
          event.preventDefault()
          sendFirstMessageMock()
        },
        hasAcceptedSession: false,
        isSubmittingFirstMessage: false,
        sendFirstMessage: sendFirstMessageMock,
        setDraft: setDraftMock,
        submissionError: null,
      } as unknown as ReturnType<typeof useComposer>)
      render(<Composer surface={surface} />)
      fireEvent.click(screen.getByRole('button', { name: 'Enviar' }))
      expect(sendFirstMessageMock).toHaveBeenCalledOnce()
      expect(
        screen.getByRole('button', {
          name: 'Anexar arquivo ou imagem. Indisponível no momento',
        }),
      ).toBeDisabled()
      expect(
        screen.getByRole('button', { name: 'Gravar ditado. Indisponível no momento' }),
      ).toBeDisabled()
      if (surface === 'fab') {
        expect(
          screen.queryByRole('button', { name: 'Memórias. Indisponível no momento' }),
        ).not.toBeInTheDocument()
      }
    },
  )

  it('retains the entered text and provides a retry after recoverable failure', () => {
    useComposerMock.mockReturnValue({
      canSend: true,
      draft: 'Mensagem preservada',
      handleSubmit: vi.fn(),
      hasAcceptedSession: false,
      isSubmittingFirstMessage: false,
      sendFirstMessage: sendFirstMessageMock,
      setDraft: setDraftMock,
      submissionError: 'Não foi possível enviar sua mensagem. Tente novamente.',
    } as unknown as ReturnType<typeof useComposer>)
    render(<Composer />)
    expect(screen.getByLabelText('Escreva sua mensagem para o Mentor')).toHaveValue(
      'Mensagem preservada',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(sendFirstMessageMock).toHaveBeenCalled()
  })
  it('locks the draft and announces first-message submission while pending', () => {
    useComposerMock.mockReturnValue({
      canSend: false,
      draft: 'Dúvida preservada',
      handleSubmit: vi.fn(),
      hasAcceptedSession: false,
      isSubmittingFirstMessage: true,
      sendFirstMessage: sendFirstMessageMock,
      setDraft: setDraftMock,
      submissionError: null,
    } as unknown as ReturnType<typeof useComposer>)
    render(<Composer surface='page' />)
    expect(screen.getByRole('form')).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByRole('textbox')).toBeDisabled()
    expect(screen.getByRole('textbox')).toHaveValue('Dúvida preservada')
    expect(screen.getByRole('button', { name: 'Enviando…' })).toBeDisabled()
    expect(sendFirstMessageMock).not.toHaveBeenCalled()
  })
})

describe('Composer dictation', () => {
  const cancelDictation = vi.fn()
  const finishDictation = vi.fn()
  const startDictation = vi.fn()
  const installDictationLanguage = vi.fn()
  function setup(overrides: Record<string, unknown> = {}) {
    useComposerMock.mockReturnValue({
      draft: 'Rascunho preservado',
      canSend: false,
      isDictationBusy: true,
      dictationStatus: 'preparing',
      dictationElapsedSeconds: 12,
      canStartDictation: false,
      dictationLanguageAvailability: 'available',
      dictationInstallationStatus: 'idle',
      cancelDictation,
      finishDictation,
      startDictation,
      installDictationLanguage,
      setDraft: setDraftMock,
      handleSubmit: vi.fn(),
      textareaRef: { current: null },
      ...overrides,
    } as unknown as ReturnType<typeof useComposer>)
    return render(<Composer surface='page' />)
  }
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)
  it('exposes preparation with cancellation', () => {
    setup()
    expect(screen.getByRole('status')).toHaveTextContent('Preparando ditado…')
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(cancelDictation).toHaveBeenCalledOnce()
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
  })
  it('exposes recording duration and controls', () => {
    setup({ dictationStatus: 'recording' })
    expect(screen.getByRole('status')).toHaveTextContent('Gravando ditado…')
    expect(screen.getByText('00:12')).toBeInTheDocument()
    expect(
      screen.getByText('Fale sua mensagem. Ao encerrar, você poderá revisar o texto.'),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Encerrar ditado' }))
    expect(finishDictation).toHaveBeenCalledOnce()
  })
  it('focuses the editable reviewed draft', () => {
    setup({ dictationStatus: 'review', isDictationBusy: false, canSend: true })
    expect(screen.getByRole('status')).toHaveTextContent('Revise seu ditado')
    expect(
      screen.getByText('Edite o texto se precisar e toque em Enviar.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('textbox')).toBeEnabled()
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Texto revisado' } })
    expect(setDraftMock).toHaveBeenCalledWith('Texto revisado')
  })
  it.each(['recording', 'review', 'error'])(
    'keeps unavailable attachment controls untouched: %s',
    (dictationStatus) => {
      setup({ dictationStatus, isDictationBusy: dictationStatus === 'recording' })
      expect(
        screen.getByRole('button', {
          name: 'Anexar arquivo ou imagem. Indisponível no momento',
        }),
      ).toBeDisabled()
      expect(screen.getByRole('textbox')).toHaveValue('Rascunho preservado')
    },
  )
  it('announces installation without acquiring the microphone', () => {
    setup({
      dictationStatus: 'idle',
      isDictationBusy: false,
      dictationInstallationStatus: 'installing',
    })
    expect(screen.getByRole('status')).toHaveTextContent('Instalando pacote de idioma…')
    expect(startDictation).not.toHaveBeenCalled()
    expect(screen.getByRole('textbox')).toBeEnabled()
  })
  it('renders accessible keyboard dictation controls', () => {
    setup({ dictationStatus: 'recording' })
    for (const name of ['Cancelar', 'Encerrar ditado']) {
      const button = screen.getByRole('button', { name })
      expect(button).toHaveAttribute('type', 'button')
      expect(button.className).toContain('min-h-11')
      button.focus()
      expect(button).toHaveFocus()
    }
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite')
  })
  it('preserves typing when local Portuguese is unavailable with the exact fallback copy', () => {
    setup({
      dictationStatus: 'idle',
      isDictationBusy: false,
      canSend: true,
      dictationLanguageAvailability: 'unavailable',
    })
    expect(screen.getByRole('status')).toHaveTextContent(
      'Ditado indisponível neste navegador. Continue digitando.',
    )
    expect(screen.getByRole('textbox')).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeEnabled()
    expect(
      screen.getByRole('button', { name: 'Gravar ditado. Indisponível no momento' }),
    ).toBeDisabled()
  })
  it('announces installation success without starting recognition with the exact copy', () => {
    setup({
      dictationStatus: 'idle',
      isDictationBusy: false,
      dictationInstallationStatus: 'installed',
      canStartDictation: true,
    })
    expect(screen.getByRole('status')).toHaveTextContent(
      'Pacote de idioma instalado. Você pode gravar seu ditado.',
    )
    expect(startDictation).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Gravar ditado' })).toBeEnabled()
  })
})
