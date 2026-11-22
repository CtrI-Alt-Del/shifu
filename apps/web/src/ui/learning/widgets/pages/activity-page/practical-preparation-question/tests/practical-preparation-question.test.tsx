import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { PracticalPreparationQuestion as PracticalPreparationQuestionData } from '@/core/learning/choice-activity'

import { PracticalPreparationQuestion } from '..'
import type { PracticalPreparationQuestionWidgetProps } from '..'
import {
  type PracticeRecordView,
  usePracticalPreparationQuestion,
} from '../use-practical-preparation-question'

vi.mock('../use-practical-preparation-question', () => ({
  usePracticalPreparationQuestion: vi.fn(),
}))

const usePracticalPreparationQuestionMock = vi.mocked(usePracticalPreparationQuestion)

type HookValue = ReturnType<typeof usePracticalPreparationQuestion>

const QUESTION: PracticalPreparationQuestionData = {
  key: 'practice-1',
  kind: 'practical_preparation',
  prompt: 'Prepare legumes salteados.',
  guidance: ['Use fogo alto.', 'Corte os legumes em tamanhos parecidos.'],
  references: [{ label: 'Guia de cortes básicos', accessibleText: 'Texto acessível' }],
  difficulty: 'easy',
  records: [
    { key: 'cuts', label: 'Cortes', mustShow: 'Os legumes já cortados' },
    { key: 'cooking', label: 'Durante o preparo', mustShow: 'A frigideira em uso' },
    { key: 'dish', label: 'Prato final', mustShow: 'O prato pronto' },
  ],
  criteria: [
    { key: 'cut', name: 'Corte', description: 'Cortes uniformes', weight: 40 },
    { key: 'heat', name: 'Calor', description: 'Ponto de cozimento', weight: 60 },
  ],
}

const PROPS: PracticalPreparationQuestionWidgetProps = {
  question: QUESTION,
  activityTitle: 'Legumes salteados',
  difficulty: 'easy',
  questionNumber: 1,
  totalQuestions: 1,
  ids: {
    goalId: 'G'.repeat(26),
    skillId: 'S'.repeat(26),
    competencyId: 'C'.repeat(26),
    activityId: 'A'.repeat(26),
  },
  isOnlineAuthority: true,
  onDraftStateChange: vi.fn(),
  footer: <button type='button'>Enviar Atividade</button>,
}

function createRecords(
  statuses: readonly PracticeRecordView['status'][],
): readonly PracticeRecordView[] {
  return QUESTION.records.map((record, index) => ({
    record,
    status: statuses[index] ?? 'missing',
    thumbnailUrl:
      statuses[index] === 'ready'
        ? `/api/photos/${record.key}?v=photo-${record.key}`
        : null,
    fileName: null,
    meta: statuses[index] === 'ready' ? 'JPEG · 1,2 MB' : null,
    message: null,
    canRetry: false,
  }))
}

function createHookValue(overrides: Partial<HookValue> = {}): HookValue {
  return {
    viewState: 'ready',
    loadErrorMessage: null,
    isOffline: false,
    notice: null,
    records: createRecords(['ready', 'ready', 'ready']),
    reflection: '',
    isReflectionOpen: false,
    saveState: 'saved',
    saveStateLabel: 'Rascunho salvo na sua conta',
    saveStateDetail: null,
    saveStateHelper: 'Continue de onde parou, inclusive em outro dispositivo.',
    isComplete: true,
    isControlsDisabled: false,
    handleReloadDraft: vi.fn(),
    handleToggleReflection: vi.fn(),
    handleChangeReflection: vi.fn(),
    handleBlurReflection: vi.fn(),
    handleRetrySaveReflection: vi.fn(),
    handleSelectPhoto: vi.fn(),
    handleRetryPhoto: vi.fn(),
    handleRemovePhoto: vi.fn(),
    ...overrides,
  }
}

function renderQuestion(props: Partial<PracticalPreparationQuestionWidgetProps> = {}) {
  return render(<PracticalPreparationQuestion {...PROPS} {...props} />)
}

describe('PracticalPreparationQuestion', () => {
  beforeEach(() => {
    usePracticalPreparationQuestionMock.mockReturnValue(createHookValue())
  })

  afterEach(() => cleanup())

  it('shows the prompt, guidance, references and weighted criteria from the Curriculum', () => {
    renderQuestion()

    expect(screen.getByText('Prepare legumes salteados.')).toBeVisible()
    expect(screen.getByText('Use fogo alto.')).toBeVisible()
    expect(screen.getByText('Guia de cortes básicos')).toBeVisible()
    const criteria = screen
      .getByRole('heading', { name: 'O que será avaliado' })
      .closest('section') as HTMLElement
    expect(within(criteria).getByText('Corte')).toBeVisible()
    expect(within(criteria).getByText('Peso 40%')).toBeVisible()
    expect(within(criteria).getByText('Peso 60%')).toBeVisible()
    expect(
      within(criteria).getByText(
        'A avaliação considera apenas o que as fotos permitem observar.',
      ),
    ).toBeVisible()
  })

  it('states the photo format and size rules before any file is chosen', () => {
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({
        records: createRecords(['missing', 'missing', 'missing']),
        isComplete: false,
      }),
    )
    renderQuestion()

    expect(
      screen.getByText(
        'Formatos aceitos: JPEG, PNG ou WebP. Tamanho máximo: 10 MB por foto.',
      ),
    ).toBeVisible()
    expect(screen.getAllByText('Obrigatória')).toHaveLength(3)
    expect(screen.getByText('Mostre: Os legumes já cortados')).toBeVisible()
    expect(screen.getByText('Adicione as 3 fotos para enviar a Atividade.')).toBeVisible()
  })

  it('numbers each record and shows a described thumbnail with its status in text', () => {
    renderQuestion()

    expect(screen.getByRole('heading', { name: '1. Cortes' })).toBeVisible()
    expect(screen.getByRole('heading', { name: '3. Prato final' })).toBeVisible()
    const thumbnail = screen.getByAltText('Foto do registro: Cortes')
    expect(thumbnail).toHaveAttribute('src', '/api/photos/cuts?v=photo-cuts')
    expect(screen.getAllByText('Foto adicionada')).toHaveLength(3)
    expect(screen.getAllByText('JPEG · 1,2 MB')).toHaveLength(3)
    expect(screen.getByRole('button', { name: 'Trocar foto: Cortes' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Remover foto: Cortes' })).toBeEnabled()
    expect(
      screen.getByText('As fotos enviadas ficam registradas nesta tentativa.'),
    ).toBeVisible()
  })

  it('keeps the photo status and the row actions in separate blocks so they cannot overlap', () => {
    renderQuestion()

    const row = screen
      .getByRole('heading', { name: '1. Cortes' })
      .closest('li') as HTMLElement
    const status = within(row).getByText('Foto adicionada')
    const replace = within(row).getByRole('button', { name: 'Trocar foto: Cortes' })
    expect(status.parentElement?.parentElement?.contains(replace)).toBe(false)
    expect(replace.parentElement).toHaveClass('shrink-0')
    expect(within(row).getByText('JPEG · 1,2 MB')).toBeVisible()
  })

  it('shows the question counter and keeps the reflection chevron closed by default', () => {
    renderQuestion()

    expect(screen.getByText(/Questão 1 de 1/)).toBeVisible()
    expect(screen.getByText(/preparação prática/)).toBeVisible()
    expect(
      screen.getByRole('progressbar', { name: 'Progresso da Atividade' }),
    ).toBeVisible()
  })

  it('renders the submit footer inside the preparation card', () => {
    renderQuestion()

    expect(screen.getByRole('button', { name: 'Enviar Atividade' })).toBeVisible()
  })

  it('delegates the chosen file with its record key', () => {
    const handleSelectPhotoMock = vi.fn()
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({
        records: createRecords(['missing', 'missing', 'missing']),
        handleSelectPhoto: handleSelectPhotoMock,
      }),
    )
    const { container } = renderQuestion()
    const file = new File(['bytes'], 'cortes.jpg', { type: 'image/jpeg' })
    const input = container.querySelectorAll<HTMLInputElement>('input[type="file"]')[0]

    expect(input).toHaveAttribute('accept', 'image/jpeg,image/png,image/webp')
    fireEvent.change(input, { target: { files: [file] } })

    expect(handleSelectPhotoMock).toHaveBeenCalledWith('cuts', file)
  })

  it('opens the file picker from the visible add button', () => {
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({ records: createRecords(['missing', 'missing', 'missing']) }),
    )
    const { container } = renderQuestion()
    const input = container.querySelectorAll<HTMLInputElement>('input[type="file"]')[0]
    const clickMock = vi.spyOn(input, 'click')

    fireEvent.click(screen.getByRole('button', { name: 'Adicionar foto: Cortes' }))

    expect(clickMock).toHaveBeenCalledTimes(1)
  })

  it('opens the file picker again from the replace button', () => {
    const { container } = renderQuestion()
    const input = container.querySelectorAll<HTMLInputElement>('input[type="file"]')[1]
    const clickMock = vi.spyOn(input, 'click')

    fireEvent.click(
      screen.getByRole('button', { name: 'Trocar foto: Durante o preparo' }),
    )

    expect(clickMock).toHaveBeenCalledTimes(1)
  })

  it('removes a photo through its labelled button', () => {
    const handleRemovePhotoMock = vi.fn()
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({ handleRemovePhoto: handleRemovePhotoMock }),
    )
    renderQuestion()

    fireEvent.click(screen.getByRole('button', { name: 'Remover foto: Prato final' }))

    expect(handleRemovePhotoMock).toHaveBeenCalledWith('dish')
  })

  it('announces a photo in transfer with text and disables its controls', () => {
    const records = createRecords(['uploading', 'removing', 'ready']).map(
      (view, index) => (index === 0 ? { ...view, fileName: 'prato.jpg' } : view),
    )
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({ records, isComplete: false }),
    )
    renderQuestion()

    expect(screen.getByText('Adicionando foto…')).toBeVisible()
    expect(screen.getByText('prato.jpg')).toBeVisible()
    expect(screen.getByText('Removendo foto…')).toBeVisible()
    expect(
      screen.queryByRole('button', { name: 'Adicionar foto: Cortes' }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Trocar foto: Prato final' })).toBeEnabled()
  })

  it('shows a failed upload with its message and retries the same record', () => {
    const handleRetryPhotoMock = vi.fn()
    const records = createRecords(['failed', 'ready', 'ready']).map((view, index) =>
      index === 0
        ? {
            ...view,
            fileName: 'prato.jpg',
            message: 'Não foi possível enviar a foto. Tente novamente.',
            canRetry: true,
          }
        : view,
    )
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({
        records,
        isComplete: false,
        handleRetryPhoto: handleRetryPhotoMock,
      }),
    )
    renderQuestion()

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível enviar a foto. Tente novamente.',
    )
    expect(screen.getByText('prato.jpg')).toBeVisible()
    expect(
      screen.getByRole('button', { name: 'Escolher outra foto: Cortes' }),
    ).toBeEnabled()
    fireEvent.click(
      screen.getByRole('button', { name: 'Tentar enviar novamente: Cortes' }),
    )

    expect(handleRetryPhotoMock).toHaveBeenCalledWith('cuts')
  })

  it('hides the retry button when the failure cannot be retried', () => {
    const records = createRecords(['failed', 'ready', 'ready']).map((view, index) =>
      index === 0 ? { ...view, message: 'A foto excede 10 MB.', canRetry: false } : view,
    )
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({ records, isComplete: false }),
    )
    renderQuestion()

    expect(
      screen.queryByRole('button', { name: /Tentar enviar novamente/ }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('A foto excede 10 MB.')
  })

  it('keeps the previous photo and offers a retry when a replacement failed', () => {
    const handleRetryPhotoMock = vi.fn()
    const records = createRecords(['ready', 'ready', 'ready']).map((view, index) =>
      index === 0
        ? {
            ...view,
            message: 'Não foi possível enviar a foto. Tente novamente.',
            canRetry: true,
          }
        : view,
    )
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({ records, handleRetryPhoto: handleRetryPhotoMock }),
    )
    renderQuestion()

    expect(screen.getByAltText('Foto do registro: Cortes')).toBeVisible()
    fireEvent.click(
      screen.getByRole('button', { name: 'Tentar enviar novamente: Cortes' }),
    )

    expect(handleRetryPhotoMock).toHaveBeenCalledWith('cuts')
  })

  it('keeps the reflection collapsed and optional until opened', () => {
    const handleToggleReflectionMock = vi.fn()
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({ handleToggleReflection: handleToggleReflectionMock }),
    )
    renderQuestion()

    const toggle = screen.getByRole('button', { name: 'Sua percepção · opcional' })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    expect(
      screen.getByText(
        'Conte como ficaram o sabor, o aroma e a textura. Sua reflexão não altera a nota.',
      ),
    ).toBeVisible()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    fireEvent.click(toggle)

    expect(handleToggleReflectionMock).toHaveBeenCalledTimes(1)
  })

  it('identifies the open reflection as written by the learner and delegates edits', () => {
    const handleChangeReflectionMock = vi.fn()
    const handleBlurReflectionMock = vi.fn()
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({
        isReflectionOpen: true,
        reflection: 'Usei pouco óleo.',
        handleChangeReflection: handleChangeReflectionMock,
        handleBlurReflection: handleBlurReflectionMock,
      }),
    )
    renderQuestion()

    const field = screen.getByRole('textbox', {
      name: 'Seu relato sobre a preparação (escrito por você)',
    })
    expect(field).toHaveValue('Usei pouco óleo.')
    fireEvent.change(field, { target: { value: 'Usei pouco óleo e fogo alto.' } })
    fireEvent.blur(field)

    expect(handleChangeReflectionMock).toHaveBeenCalledWith(
      'Usei pouco óleo e fogo alto.',
    )
    expect(handleBlurReflectionMock).toHaveBeenCalledTimes(1)
    expect(
      screen.getByRole('button', { name: 'Sua percepção · opcional' }),
    ).toHaveAttribute('aria-expanded', 'true')
  })

  it('shows the saved and saving draft states with text and helper copy', () => {
    usePracticalPreparationQuestionMock.mockReturnValue(createHookValue())
    const { rerender } = renderQuestion()
    expect(screen.getByText('Rascunho salvo na sua conta')).toBeVisible()
    expect(
      screen.getByText('Continue de onde parou, inclusive em outro dispositivo.'),
    ).toBeVisible()

    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({
        saveState: 'saving',
        saveStateLabel: 'Salvando rascunho…',
        saveStateHelper: 'Você pode continuar enquanto a foto é adicionada.',
      }),
    )
    rerender(<PracticalPreparationQuestion {...PROPS} />)
    expect(screen.getByText('Salvando rascunho…')).toBeVisible()
    expect(screen.queryByText(/outro dispositivo/)).not.toBeInTheDocument()
  })

  it('offers a retry and never promises another device when saving failed', () => {
    const handleRetrySaveReflectionMock = vi.fn()
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({
        saveState: 'failed',
        saveStateLabel: 'Rascunho não salvo',
        saveStateDetail:
          'Tente novamente antes de sair. As últimas alterações ainda não estão salvas na sua conta.',
        saveStateHelper: null,
        handleRetrySaveReflection: handleRetrySaveReflectionMock,
      }),
    )
    renderQuestion()

    expect(screen.getByText('Rascunho não salvo')).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível salvar as alterações',
    )
    expect(screen.queryByText('Rascunho salvo na sua conta')).not.toBeInTheDocument()
    expect(screen.queryByText(/outro dispositivo/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar salvar novamente' }))

    expect(handleRetrySaveReflectionMock).toHaveBeenCalledTimes(1)
  })

  it('disables the photo and reflection controls while the question is locked', () => {
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({ isControlsDisabled: true, isReflectionOpen: true }),
    )
    renderQuestion()

    expect(screen.getByRole('button', { name: 'Trocar foto: Cortes' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Remover foto: Cortes' })).toBeDisabled()
    expect(
      screen.getByRole('textbox', {
        name: 'Seu relato sobre a preparação (escrito por você)',
      }),
    ).toBeDisabled()
  })

  it('shows the sending state with the photos read only and the footer', () => {
    renderQuestion({ isSubmitting: true })

    expect(screen.getByRole('heading', { name: 'Enviando sua Atividade…' })).toBeVisible()
    expect(screen.getByText('Enviando fotos e resposta…')).toBeVisible()
    expect(screen.getByText('Aguarde a confirmação do envio.')).toBeVisible()
    expect(screen.getByText('Envio em andamento.')).toBeVisible()
    expect(screen.getAllByRole('img')).toHaveLength(3)
    expect(screen.queryByRole('button', { name: /Remover foto/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Enviar Atividade' })).toBeVisible()
  })

  it('announces the draft loading state without showing the records', () => {
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({ viewState: 'loading' }),
    )
    renderQuestion()

    expect(screen.getByLabelText('Carregando rascunho...')).toHaveAttribute(
      'aria-busy',
      'true',
    )
    expect(
      screen.queryByRole('list', { name: 'Registros fotográficos' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Enviar Atividade' }),
    ).not.toBeInTheDocument()
  })

  it('shows a load failure with a retry action', () => {
    const handleReloadDraftMock = vi.fn()
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({
        viewState: 'error',
        loadErrorMessage: 'Não foi possível carregar seu rascunho agora.',
        handleReloadDraft: handleReloadDraftMock,
      }),
    )
    renderQuestion()

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível carregar seu rascunho agora.',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(handleReloadDraftMock).toHaveBeenCalledTimes(1)
  })

  it('asks for a connection before restoring a draft when the session is not confirmed', () => {
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({ viewState: 'offline' }),
    )
    renderQuestion()

    expect(
      screen.getByText(
        'Sem conexão confirmada. Conecte-se para carregar e editar seu rascunho.',
      ),
    ).toBeVisible()
    expect(
      screen.queryByRole('list', { name: 'Registros fotográficos' }),
    ).not.toBeInTheDocument()
  })

  it('reports an unavailable draft when no Activity route is known', () => {
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({ viewState: 'unavailable' }),
    )
    renderQuestion()

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível abrir o rascunho desta preparação.',
    )
  })

  it('keeps the draft visible with an offline warning after the connection drops', () => {
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({
        isOffline: true,
        isControlsDisabled: true,
        saveStateHelper: null,
        saveStateDetail:
          'Sem conexão. As alterações só serão salvas quando a conexão voltar.',
      }),
    )
    renderQuestion()

    expect(
      screen.getByText(
        'Sem conexão. As alterações só serão salvas quando a conexão voltar.',
      ),
    ).toBeVisible()
    expect(screen.getByAltText('Foto do registro: Cortes')).toBeVisible()
  })

  it('explains that the draft was reloaded after a conflict from another device', () => {
    usePracticalPreparationQuestionMock.mockReturnValue(
      createHookValue({ notice: 'conflict' }),
    )
    renderQuestion()

    expect(
      screen.getByText(/Seu rascunho foi alterado em outro dispositivo/),
    ).toBeVisible()
  })
})
