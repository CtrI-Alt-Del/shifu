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
