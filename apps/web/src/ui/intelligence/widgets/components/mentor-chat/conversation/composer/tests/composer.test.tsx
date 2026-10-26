import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { FormEvent } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { Composer } from '..'
import { useComposer } from '../use-composer'
import type { MentorDraftAttachment } from '@/ui/intelligence/contexts/mentor-context/types'

vi.mock('../use-composer', () => ({ useComposer: vi.fn() }))
const useComposerMock = vi.mocked(useComposer)
const sendFirstMessageMock = vi.fn()
const setDraftMock = vi.fn()
const addAttachmentsMock = vi.fn()
const removeAttachmentMock = vi.fn().mockResolvedValue(undefined)

describe('Composer', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)

  it.each(['page', 'fab'] as const)(
    'submits the first message and keeps future controls unavailable on %s',
    (surface) => {
      useComposerMock.mockReturnValue({
        canSend: true,
        canManageAttachments: true,
        draftAttachments: [],
        addAttachments: addAttachmentsMock,
        removeAttachment: removeAttachmentMock,
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
          name: 'Anexar arquivo ou imagem',
        }),
      ).toBeEnabled()
      expect(
        screen.getByRole('button', { name: 'Gravar ditado. Indisponível no momento' }),
      ).toBeDisabled()
      if (surface === 'fab') {
        expect(screen.queryByRole('link', { name: 'Memórias' })).not.toBeInTheDocument()
      }
    },
  )

  it('retains the entered text and provides a retry after recoverable failure', () => {
    useComposerMock.mockReturnValue({
      canSend: true,
      canManageAttachments: true,
      draftAttachments: [],
      addAttachments: addAttachmentsMock,
      removeAttachment: removeAttachmentMock,
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
  it.each([
    [false, 'Pergunte ao Mentor…'],
    [true, 'Aguarde enquanto o contexto é resumido'],
  ] as const)(
    'shows the placeholder for summarizing=%s and keeps the draft locked while summarizing',
    (isSummarizingContext, placeholder) => {
      useComposerMock.mockReturnValue({
        canSend: false,
        canManageAttachments: !isSummarizingContext,
        draftAttachments: [],
        addAttachments: addAttachmentsMock,
        removeAttachment: removeAttachmentMock,
        draft: '',
        handleSubmit: vi.fn(),
        hasAcceptedSession: true,
        isResponsePending: isSummarizingContext,
        isSubmittingFirstMessage: false,
        placeholder,
        sendFirstMessage: sendFirstMessageMock,
        setDraft: setDraftMock,
        submissionError: null,
      } as unknown as ReturnType<typeof useComposer>)
      render(<Composer surface='page' />)
      const textbox = screen.getByRole('textbox')
      expect(textbox).toHaveAttribute('placeholder', placeholder)
      if (isSummarizingContext) {
        expect(textbox).toBeDisabled()
        expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
        expect(
          screen.getByRole('button', { name: 'Anexar arquivo ou imagem' }),
        ).toBeDisabled()
      } else expect(textbox).toBeEnabled()
    },
  )
  it('locks the draft and announces first-message submission while pending', () => {
    useComposerMock.mockReturnValue({
      canSend: false,
      canManageAttachments: false,
      draftAttachments: [],
      addAttachments: addAttachmentsMock,
      removeAttachment: removeAttachmentMock,
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
      canManageAttachments: false,
      draftAttachments: [],
      addAttachments: addAttachmentsMock,
      removeAttachment: removeAttachmentMock,
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
    expect(screen.getByTestId('dictation-wave')).toHaveAttribute('aria-hidden', 'true')
    expect(
      screen.getByText('Fale sua mensagem. Ao encerrar, você poderá revisar o texto.'),
    ).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Encerrar ditado' }))
    expect(finishDictation).toHaveBeenCalledOnce()
  })
  it('focuses the editable reviewed draft', () => {
    setup({ dictationStatus: 'review', isDictationBusy: false, canSend: true })
    expect(screen.getByRole('status')).toHaveTextContent('Revise seu ditado')
    expect(screen.queryByTestId('dictation-wave')).not.toBeInTheDocument()
    expect(
      screen.getByText('Edite o texto se precisar e toque em Enviar.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('textbox')).toBeEnabled()
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Texto revisado' } })
    expect(setDraftMock).toHaveBeenCalledWith('Texto revisado')
  })
  it.each(['preparing', 'recording', 'transcribing'])(
    'keeps attachment controls disabled during active dictation: %s',
    (dictationStatus) => {
      setup({ dictationStatus, isDictationBusy: dictationStatus === 'recording' })
      expect(
        screen.getByRole('button', {
          name: 'Anexar arquivo ou imagem',
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
  it('keeps attachment selection available while reviewing the transcript', () => {
    setup({
      dictationStatus: 'review',
      isDictationBusy: false,
      canManageAttachments: true,
    })
    expect(screen.getByRole('button', { name: 'Anexar arquivo ou imagem' })).toBeEnabled()
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

describe('Composer attachments', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)

  function setup(overrides: Record<string, unknown> = {}) {
    useComposerMock.mockReturnValue({
      canSend: false,
      canManageAttachments: true,
      draft: 'Dúvida preservada',
      draftAttachments: [],
      addAttachments: addAttachmentsMock,
      removeAttachment: removeAttachmentMock,
      isSubmittingFirstMessage: false,
      isResponsePending: false,
      isDictationBusy: false,
      canStartDictation: false,
      dictationLanguageAvailability: 'unavailable',
      dictationInstallationStatus: 'idle',
      dictationStatus: 'idle',
      handleSubmit: vi.fn(),
      setDraft: setDraftMock,
      textareaRef: { current: null },
      ...overrides,
    } as unknown as ReturnType<typeof useComposer>)
    return render(<Composer surface='page' />)
  }

  it('announces formats and limits before selection and delegates selected files', () => {
    setup()
    const file = new File(['resumo'], 'resumo.txt', { type: 'text/plain' })
    expect(
      screen.getByText(/até cinco arquivos PNG, JPG, WebP, PDF, JSON, CSV ou TXT/),
    ).toBeVisible()
    expect(screen.getByText(/até 2 MB/)).toBeVisible()
    expect(
      screen.getByText(/A mensagem de texto é opcional ao enviar arquivos/),
    ).toBeVisible()
    expect(
      screen.queryByText(/Escreva uma mensagem para continuar/),
    ).not.toBeInTheDocument()
    fireEvent.change(
      screen.getByLabelText('Selecionar arquivos PNG, JPG, WebP, PDF, JSON, CSV ou TXT'),
      { target: { files: [file] } },
    )
    expect(addAttachmentsMock).toHaveBeenCalledWith([file])
  })

  it('renders prepared attachment metadata and image preview, then restores focus after removal', async () => {
    const file = new File(['pixels'], 'desenho.png', { type: 'image/png' })
    const draftAttachment: MentorDraftAttachment = {
      localKey: 'local-1',
      uploadKey: 'upload-1',
      file,
      previewUrl: 'blob:desenho',
      attachment: {
        attachmentId: '01J7T8AC91Z5K8M4JQ8C2D6F0B',
        filename: file.name,
        mediaType: 'image/png',
        sizeBytes: file.size,
        status: 'processing',
        failureCode: null,
        analyzedPages: [],
        illegiblePages: [],
        uninterpretedPages: [],
      },
      error: null,
    }
    setup({ draftAttachments: [draftAttachment] })
    expect(screen.getByText('desenho.png')).toBeVisible()
    expect(screen.getByText('IMAGE/PNG · 1 KB')).toBeVisible()
    expect(screen.getByText('Preparando arquivo…')).toHaveAttribute('role', 'status')
    expect(screen.getByRole('img', { name: 'Prévia de desenho.png' })).toHaveAttribute(
      'src',
      'blob:desenho',
    )
    const attachButton = screen.getByRole('button', { name: 'Anexar arquivo ou imagem' })
    fireEvent.click(screen.getByRole('button', { name: 'Remover desenho.png' }))
    await waitFor(() => expect(attachButton).toHaveFocus())
    expect(removeAttachmentMock).toHaveBeenCalledWith('local-1')
  })

  it('keeps optional attachment handlers safe and forwards the composer controls', async () => {
    const file = new File(['draft'], 'rascunho.txt', { type: 'text/plain' })
    const draftAttachment: MentorDraftAttachment = {
      localKey: 'local-default',
      uploadKey: 'upload-default',
      file,
      previewUrl: null,
      attachment: null,
      error: null,
      retryable: true,
    }
    const startDictation = vi.fn()
    const installDictationLanguage = vi.fn()
    setup({
      addAttachments: undefined,
      removeAttachment: undefined,
      draftAttachments: [draftAttachment],
      canStartDictation: true,
      canInstallDictationLanguage: true,
      dictationLanguageAvailability: 'unavailable',
      startDictation,
      installDictationLanguage,
    })

    const attachButton = screen.getByRole('button', { name: 'Anexar arquivo ou imagem' })
    const fileInput = screen.getByLabelText(
      'Selecionar arquivos PNG, JPG, WebP, PDF, JSON, CSV ou TXT',
    ) as HTMLInputElement
    const inputClick = vi.spyOn(fileInput, 'click')
    fireEvent.click(attachButton)
    expect(inputClick).toHaveBeenCalledOnce()

    fireEvent.change(fileInput, { target: { files: null } })
    expect(fileInput.value).toBe('')

    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    fireEvent.click(screen.getByRole('button', { name: 'Remover rascunho.txt' }))
    await waitFor(() => expect(attachButton).toHaveFocus())
    fireEvent.click(screen.getByRole('button', { name: 'Instalar pacote de idioma' }))
    fireEvent.click(screen.getByRole('button', { name: 'Gravar ditado' }))
    expect(installDictationLanguage).toHaveBeenCalledWith('page')
    expect(startDictation).toHaveBeenCalledWith('page')
  })
})

it('offers dictation without an install prompt when the language pack is available', () => {
  useComposerMock.mockReturnValue({
    canStartDictation: true,
    canManageAttachments: true,
    draftAttachments: [],
    addAttachments: addAttachmentsMock,
    removeAttachment: removeAttachmentMock,
    dictationLanguageAvailability: 'available',
    draft: '',
    handleSubmit: vi.fn(),
    setDraft: vi.fn(),
  } as unknown as ReturnType<typeof useComposer>)
  render(<Composer surface='page' />)
  expect(
    screen.queryByText(
      'O navegador pode usar um serviço na nuvem para reconhecer sua fala.',
    ),
  ).not.toBeInTheDocument()
  expect(
    screen.queryByRole('button', { name: 'Instalar pacote de idioma' }),
  ).not.toBeInTheDocument()
})

describe('Composer action block', () => {
  beforeEach(() => {
    cleanup()
    vi.clearAllMocks()
  })
  afterEach(cleanup)
  const refreshActionsMock = vi.fn()

  function mockBlocked(overrides: object = {}) {
    useComposerMock.mockReturnValue({
      canSend: false,
      canManageAttachments: false,
      canStartDictation: false,
      draftAttachments: [],
      addAttachments: addAttachmentsMock,
      removeAttachment: removeAttachmentMock,
      draft: 'Dúvida preservada',
      handleSubmit: vi.fn(),
      hasAcceptedSession: true,
      isActionBlocked: true,
      isRefreshingActions: false,
      hasActionRefreshTimedOut: false,
      refreshActions: refreshActionsMock,
      isSubmittingFirstMessage: false,
      sendFirstMessage: sendFirstMessageMock,
      setDraft: setDraftMock,
      submissionError: null,
      ...overrides,
    } as unknown as ReturnType<typeof useComposer>)
  }

  it.each(['page', 'fab'] as const)(
    'explains the block and disables the input, attachment and dictation on %s',
    (surface) => {
      mockBlocked()
      render(<Composer surface={surface} />)

      const textbox = screen.getByRole('textbox')
      expect(
        screen.getByText('Confirme ou recuse a ação proposta para continuar.'),
      ).toBeVisible()
      expect(textbox).toBeDisabled()
      expect(textbox).toHaveAccessibleDescription(
        'Confirme ou recuse a ação proposta para continuar.',
      )
      expect(
        screen.getByRole('button', { name: 'Anexar arquivo ou imagem' }),
      ).toBeDisabled()
      expect(
        screen.getByRole('button', { name: 'Gravar ditado. Indisponível no momento' }),
      ).toBeDisabled()
      expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
    },
  )

  it('keeps the draft while blocked', () => {
    mockBlocked()
    render(<Composer surface='page' />)

    expect(screen.getByRole('textbox')).toHaveValue('Dúvida preservada')
  })

  it('announces the refresh instead of the block reason while the conversation is re-read', () => {
    mockBlocked({ isRefreshingActions: true })
    render(<Composer surface='page' />)

    expect(screen.getByRole('status')).toHaveTextContent('Atualizando a conversa…')
    expect(
      screen.queryByText('Confirme ou recuse a ação proposta para continuar.'),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('textbox')).toBeDisabled()
  })

  it('offers Tentar novamente after the refresh limit and re-reads when pressed', () => {
    mockBlocked({ hasActionRefreshTimedOut: true })
    render(<Composer surface='page' />)

    expect(screen.getByRole('status')).toHaveTextContent(
      'Ainda não foi possível atualizar a conversa.',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(refreshActionsMock).toHaveBeenCalledOnce()
  })

  it('shows no block copy when the conversation accepts messages', () => {
    mockBlocked({ isActionBlocked: false, canSend: true, canManageAttachments: true })
    render(<Composer surface='page' />)

    expect(
      screen.queryByText('Confirme ou recuse a ação proposta para continuar.'),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('textbox')).toBeEnabled()
    expect(
      screen.queryByRole('button', { name: 'Tentar novamente' }),
    ).not.toBeInTheDocument()
  })
})
