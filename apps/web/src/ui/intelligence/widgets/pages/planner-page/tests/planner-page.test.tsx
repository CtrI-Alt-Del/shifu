import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PlanningSessionFaker } from '@/core/intelligence/fakers/planning-session-faker'
import type { PlanningQuestion } from '@/core/intelligence/planning-session'

import { PlannerPage } from '..'
import { type PlannerPageController, usePlannerPage } from '../use-planner-page'

// Entrance motion settles at once, so assertions see the final state; the
// shared entrance owns its animated cases.
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('../use-planner-page', () => ({
  usePlannerPage: vi.fn(),
}))

vi.stubGlobal(
  'ResizeObserver',
  class {
    observe = vi.fn()
    disconnect = vi.fn()
    unobserve = vi.fn()
  },
)

vi.mock('@xyflow/react', () => ({
  Background: () => null,
  Controls: () => null,
  Handle: () => null,
  Position: { Bottom: 'bottom', Top: 'top' },
  ReactFlow: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
}))

const usePlannerPageMock = vi.mocked(usePlannerPage)
const PLANNING_ID = PlanningSessionFaker.fakeId()
const INTENT = 'Quero automatizar tarefas do dia a dia com Python.'

const singleQuestion: PlanningQuestion = {
  id: 'q1',
  text: 'Você já escreveu algum código antes?',
  kind: 'single',
  options: [
    { id: 'never', text: 'Nunca', exclusive: false, open: false },
    {
      id: 'copied',
      text: 'Já copiei e adaptei alguns scripts',
      exclusive: false,
      open: false,
    },
    { id: 'nao-sei', text: 'Não sei', exclusive: true, open: false },
  ],
}

const multipleQuestion: PlanningQuestion = {
  id: 'q2',
  text: 'O que você quer automatizar?',
  kind: 'multiple',
  options: [
    { id: 'sheets', text: 'Planilhas e relatórios', exclusive: false, open: false },
    { id: 'files', text: 'Organização de arquivos', exclusive: false, open: false },
    { id: 'nao-sei', text: 'Não sei', exclusive: true, open: false },
  ],
}

function controller(
  overrides: Partial<PlannerPageController> = {},
): PlannerPageController {
  return {
    view: 'interview',
    intent: INTENT,
    steps: [
      { number: 1, questionId: 'q1', state: 'current' },
      { number: 2, questionId: 'q2', state: 'pending' },
      { number: 3, questionId: 'q3', state: 'answered' },
    ],
    stepLabel: 'Pergunta 1 de 3 deste conjunto',
    currentQuestion: singleQuestion,
    selectedOptionIds: [],
    otherText: '',
    isOtherSelected: false,
    guidance:
      'Escolha uma alternativa. Você poderá revisar as respostas antes de enviar este conjunto.',
    isFirstStep: true,
    isLastStep: false,
    isBatchComplete: false,
    canSubmit: false,
    processingStage: null,
    proposal: null,
    errorMessage: null,
    restartErrorMessage: null,
    goalCreation: { status: 'idle', message: null },
    generation: 1,
    isSubmitting: false,
    isRetrying: false,
    isRestarting: false,
    isCreatingGoal: false,
    isCancelling: false,
    isAbandoning: false,
    questionHeadingRef: { current: null },
    handleSelectSingle: vi.fn(),
    handleToggleMultiple: vi.fn(),
    handleChangeOtherText: vi.fn(),
    handleGoToStep: vi.fn(),
    handlePrevious: vi.fn(),
    handleNext: vi.fn(),
    handleSubmitAnswers: vi.fn(async () => undefined),
    handleCancel: vi.fn(async () => undefined),
    handleRetry: vi.fn(async () => undefined),
    handleRestart: vi.fn(async () => true),
    handleCreateGoal: vi.fn(async () => undefined),
    handleReformulate: vi.fn(),
    handleCreateManually: vi.fn(),
    handleRetryLoad: vi.fn(),
    handleReturnHome: vi.fn(),
    ...overrides,
  }
}

function renderPage(overrides: Partial<PlannerPageController> = {}) {
  const current = controller(overrides)
  usePlannerPageMock.mockReturnValue(current)
  render(<PlannerPage planningId={PLANNING_ID} />)
  return current
}

describe('PlannerPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows a loading skeleton with an accessible busy label', () => {
    renderPage({ view: 'loading', intent: null, currentQuestion: null, steps: [] })

    expect(
      screen.getByRole('status', { name: 'Carregando planejamento…' }),
    ).toHaveAttribute('aria-busy', 'true')
    expect(screen.queryByRole('heading')).not.toBeInTheDocument()
  })

  it('renders the intention, the step trail and a single-choice question (CA-02)', () => {
    const current = renderPage()

    expect(screen.getByText('O que você quer alcançar')).toBeVisible()
    expect(screen.getByText(INTENT)).toBeVisible()
    expect(screen.getByText('Pergunta 1 de 3 deste conjunto')).toBeVisible()
    const trail = within(
      screen.getByRole('navigation', { name: 'Perguntas deste conjunto' }),
    )
    expect(trail.getByRole('button', { name: '1 · Atual' })).toHaveAttribute(
      'aria-current',
      'step',
    )
    expect(trail.getByRole('button', { name: '2 · Pendente' })).not.toHaveAttribute(
      'aria-current',
    )
    expect(trail.getByRole('button', { name: '3 · Respondida' })).toBeVisible()
    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Você já escreveu algum código antes?',
      }),
    ).toBeVisible()
    expect(screen.getByText(current.guidance)).toBeVisible()
    expect(screen.getByRole('radiogroup')).toBeVisible()
    expect(screen.getAllByRole('radio')).toHaveLength(3)
    expect(screen.queryByRole('button', { name: 'Anterior' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Próxima' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeEnabled()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('delegates option selection, step navigation and cancel to the hook (CA-03)', () => {
    const current = renderPage({ isFirstStep: false, selectedOptionIds: ['copied'] })

    expect(
      screen.getByRole('radio', { name: 'Já copiei e adaptei alguns scripts' }),
    ).toBeChecked()
    fireEvent.click(screen.getByRole('radio', { name: 'Nunca' }))
    expect(current.handleSelectSingle).toHaveBeenCalledWith('never')

    fireEvent.click(screen.getByRole('button', { name: '3 · Respondida' }))
    expect(current.handleGoToStep).toHaveBeenCalledWith(2)
    fireEvent.click(screen.getByRole('button', { name: 'Anterior' }))
    expect(current.handlePrevious).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Próxima' }))
    expect(current.handleNext).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(current.handleCancel).toHaveBeenCalledOnce()
  })

  it('renders a multiple-choice question with checkboxes and reports toggles (CA-04)', () => {
    const current = renderPage({
      currentQuestion: multipleQuestion,
      selectedOptionIds: ['sheets'],
      guidance:
        'Selecione uma ou mais alternativas. “Não sei” não pode ser combinado com outras respostas.',
    })

    expect(screen.queryByRole('radiogroup')).not.toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Planilhas e relatórios' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Não sei' })).not.toBeChecked()
    fireEvent.click(screen.getByRole('checkbox', { name: 'Não sei' }))
    expect(current.handleToggleMultiple).toHaveBeenCalledWith('nao-sei', true)
    fireEvent.click(screen.getByRole('checkbox', { name: 'Planilhas e relatórios' }))
    expect(current.handleToggleMultiple).toHaveBeenCalledWith('sheets', false)
  })

  it('shows the open answer field only while "Outro" is selected and reports the text', () => {
    const openQuestion: PlanningQuestion = {
      ...multipleQuestion,
      options: [
        ...multipleQuestion.options.slice(0, -1),
        { id: 'outro', text: 'Outro', exclusive: false, open: true },
        ...multipleQuestion.options.slice(-1),
      ],
    }
    renderPage({ currentQuestion: openQuestion, selectedOptionIds: ['sheets'] })
    expect(screen.queryByLabelText('Descreva sua resposta')).not.toBeInTheDocument()
    cleanup()

    const current = renderPage({
      currentQuestion: openQuestion,
      selectedOptionIds: ['outro'],
      isOtherSelected: true,
      otherText: 'Excel',
    })

    const field = screen.getByLabelText('Descreva sua resposta')
    expect(screen.getByRole('checkbox', { name: 'Outro' })).toBeChecked()
    expect(field).toHaveValue('Excel')
    expect(field).toHaveFocus()
    expect(field).toHaveAttribute('maxlength', '200')
    expect(screen.getByText('5/200 caracteres')).toBeInTheDocument()
    fireEvent.change(field, { target: { value: 'planilhas no Excel' } })
    expect(current.handleChangeOtherText).toHaveBeenCalledWith('planilhas no Excel')
  })

  it('offers the submission on the last step only when the batch is complete (CA-05, CA-06)', () => {
    const current = renderPage({
      isFirstStep: false,
      isLastStep: true,
      canSubmit: false,
      stepLabel: 'Pergunta 3 de 3 deste conjunto',
      guidance:
        'Escolha uma alternativa. Responda todas as perguntas do conjunto para enviar.',
    })

    expect(screen.queryByRole('button', { name: 'Próxima' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Enviar respostas' })).toBeDisabled()
    cleanup()

    const ready = renderPage({ isFirstStep: false, isLastStep: true, canSubmit: true })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar respostas' }))
    expect(ready.handleSubmitAnswers).toHaveBeenCalledOnce()
    expect(current.handleSubmitAnswers).not.toHaveBeenCalled()
  })

  it('locks the controls and shows the feedback while a submission is pending or failed', () => {
    renderPage({
      isFirstStep: false,
      isLastStep: true,
      canSubmit: false,
      isSubmitting: true,
      errorMessage: null,
    })

    expect(screen.getByRole('button', { name: 'Enviando…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '1 · Atual' })).toBeDisabled()
    cleanup()

    renderPage({
      isFirstStep: false,
      isLastStep: true,
      canSubmit: true,
      errorMessage: 'Já existe uma operação em andamento neste planejamento.',
    })
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Já existe uma operação em andamento neste planejamento.',
    )
  })

  it('represents the processing stage with a busy action and an available cancel (CA-08)', () => {
    const current = renderPage({
      view: 'processing',
      currentQuestion: null,
      steps: [],
      processingStage: {
        title: 'Consultando o Currículo…',
        support: 'Estamos buscando habilidades relacionadas ao que você quer aprender.',
        busyLabel: 'Consultando…',
      },
    })

    expect(
      screen.getByRole('heading', { level: 1, name: 'Planeje seu objetivo' }),
    ).toBeVisible()
    expect(screen.getByText(INTENT)).toBeVisible()
    expect(screen.getByRole('status')).toHaveTextContent('Consultando o Currículo…')
    expect(screen.getByRole('status')).toHaveTextContent(
      'Estamos buscando habilidades relacionadas ao que você quer aprender.',
    )
    expect(screen.getByRole('button', { name: 'Consultando…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Consultando…' })).toHaveAttribute(
      'aria-busy',
      'true',
    )
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(current.handleCancel).toHaveBeenCalledOnce()
  })

  it('keeps the planning on a technical failure and offers the retry (CA-12)', () => {
    const current = renderPage({ view: 'failed', currentQuestion: null, steps: [] })

    expect(
      screen.getByRole('heading', { level: 1, name: 'Planeje seu objetivo' }),
    ).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent('Não conseguimos continuar agora')
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Seu planejamento permanece nesta página. Tente novamente para continuar de onde parou.',
    )
    expect(screen.queryByText('Vamos planejar sua aprendizagem')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(current.handleRetry).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(current.handleCancel).toHaveBeenCalledOnce()
    cleanup()

    renderPage({ view: 'failed', currentQuestion: null, steps: [], isRetrying: true })
    expect(screen.getByRole('button', { name: 'Tentando novamente…' })).toBeDisabled()
  })

  it('explains an out-of-scope request with the reformulate and manual exits (CA-15, CA-18)', () => {
    const current = renderPage({ view: 'out-of-scope', currentQuestion: null, steps: [] })

    expect(
      screen.getByRole('heading', { level: 1, name: 'Vamos planejar sua aprendizagem' }),
    ).toBeVisible()
    expect(
      screen.getByText(
        'O planejador ajuda a criar objetivos de aprendizagem. Esse pedido está fora desse escopo. Descreva o que você quer aprender ou desenvolver.',
      ),
    ).toBeVisible()
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Criar manualmente' }))
    expect(current.handleCreateManually).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Reformular' }))
    expect(current.handleReformulate).toHaveBeenCalledOnce()
  })

  it('reports an unsupported Goal without inventing Skills (CA-16)', () => {
    const current = renderPage({ view: 'unsupported', currentQuestion: null, steps: [] })

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Ainda não temos Habilidades para isso',
      }),
    ).toBeVisible()
    expect(
      screen.getByText(
        'Nenhuma combinação do Currículo representa bem o que você descreveu. Você pode reformular a intenção ou montar o Objetivo por conta própria.',
      ),
    ).toBeVisible()
    const buttons = screen.getAllByRole('button')
    expect(buttons.map((button) => button.textContent)).toEqual([
      'Reformular',
      'Criar manualmente',
    ])
    fireEvent.click(screen.getByRole('button', { name: 'Reformular' }))
    expect(current.handleReformulate).toHaveBeenCalledOnce()
  })

  it('distinguishes a proposal that could not be validated with three exits (CA-17)', () => {
    const current = renderPage({
      view: 'validation-failed',
      currentQuestion: null,
      steps: [],
      errorMessage:
        'Não foi possível tentar novamente agora. Seu planejamento continua nesta página.',
    })

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Não conseguimos concluir sua proposta',
      }),
    ).toBeVisible()
    expect(screen.getByText(/Nenhum objetivo foi criado/)).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível tentar novamente agora.',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(current.handleRetry).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Reformular' }))
    expect(current.handleReformulate).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Criar manualmente' }))
    expect(current.handleCreateManually).toHaveBeenCalledOnce()
  })

  it('renders the review surface for a validated proposal and wires its actions (CA-19)', () => {
    const proposal = PlanningSessionFaker.fakeProposal({
      title: 'Automação com Python',
      description: 'Scripts para planilhas.',
    })
    const current = renderPage({
      view: 'proposal',
      currentQuestion: null,
      steps: [],
      proposal,
    })

    expect(
      screen.getByRole('heading', { level: 1, name: 'Revise seu objetivo' }),
    ).toBeVisible()
    expect(screen.getByLabelText('Título')).toHaveValue('Automação com Python')
    expect(screen.getByLabelText('Descrição')).toHaveValue('Scripts para planilhas.')
    expect(screen.getByRole('tab', { name: 'Grafo' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(
      screen.getByRole('region', { name: 'Grafo das Habilidades propostas' }),
    ).toBeVisible()
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Enviar respostas' }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reiniciar planejamento' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Criar objetivo' })).toBeEnabled()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(current.handleCancel).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Criar objetivo' }))
    expect(current.handleCreateGoal).toHaveBeenCalledWith({
      planningId: PLANNING_ID,
      confirmationKey: expect.stringMatching(/^[0-9a-f-]{36}$/),
      title: 'Automação com Python',
      description: 'Scripts para planilhas.',
      proposal,
    })
  })

  it('freezes the review while the Goal is being created and offers a retry after a failure', () => {
    const proposal = PlanningSessionFaker.fakeProposal()
    renderPage({
      view: 'proposal',
      currentQuestion: null,
      steps: [],
      proposal,
      goalCreation: { status: 'creating', message: null },
      isCreatingGoal: true,
    })

    expect(screen.getByText('Criando seu objetivo…')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Criando objetivo…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reiniciar planejamento' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
    expect(screen.getByLabelText('Título')).toBeDisabled()
    cleanup()

    renderPage({
      view: 'proposal',
      currentQuestion: null,
      steps: [],
      proposal,
      goalCreation: {
        status: 'failed',
        message: 'Este Skill ainda não está pronto para iniciar.',
      },
    })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível criar o objetivo',
    )
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Este Skill ainda não está pronto para iniciar. Sua proposta foi mantida.',
    )
    expect(screen.getByRole('button', { name: 'Tentar criar objetivo' })).toBeEnabled()
    expect(screen.getByLabelText('Título')).toBeEnabled()
  })

  it('tells the learner when the planning no longer exists (CA-23)', () => {
    const current = renderPage({
      view: 'not-found',
      intent: null,
      currentQuestion: null,
      steps: [],
    })

    expect(
      screen.getByRole('heading', { level: 1, name: 'Planejamento não encontrado' }),
    ).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Voltar à Home' }))
    expect(current.handleReturnHome).toHaveBeenCalledOnce()
  })

  it('shows a recoverable request error that never reads as an outcome (CA-13)', () => {
    const current = renderPage({
      view: 'request-error',
      intent: null,
      currentQuestion: null,
      steps: [],
    })

    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Não foi possível carregar o planejamento',
      }),
    ).toBeVisible()
    expect(screen.queryByText(/fora desse escopo/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Habilidades para isso/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(current.handleRetryLoad).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Voltar à Home' }))
    expect(current.handleReturnHome).toHaveBeenCalledOnce()
  })
})
