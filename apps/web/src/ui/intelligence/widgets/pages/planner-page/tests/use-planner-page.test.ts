import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { createElement, type PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { PlanningSessionFaker } from '@/core/intelligence/fakers/planning-session-faker'
import type {
  PlanningGoalCreationRequest,
  PlanningQuestion,
  PlanningSession,
} from '@/core/intelligence/planning-session'
import { registerPlanningEntry } from '@/ui/intelligence/planning-entry'
import { planningSessionQueryKey } from '@/ui/intelligence/hooks/use-planning-session-query'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { usePlannerPage } from '../use-planner-page'

const mocks = vi.hoisted(() => ({
  request: new Request('http://shifu.test/intelligence/planner'),
  getCurrentAccess: vi.fn(),
  service: {
    getPlanningSession: vi.fn(),
    answerPlanningQuestions: vi.fn(),
    retryPlanning: vi.fn(),
    restartPlanning: vi.fn(),
    cancelPlanning: vi.fn(),
  },
}))

vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => ({
    validator: (validate: (data: unknown) => unknown) => ({
      handler:
        (handler: (context: { data: unknown }) => Promise<unknown>) =>
        async (context: { data: unknown }) =>
          handler({ data: validate(context.data) }),
    }),
  }),
}))

vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => mocks.request,
}))

vi.mock('@/constants/server-env', () => ({
  SERVER_ENV: { shifuServerAppUrl: 'http://shifu.test' },
}))

vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.getCurrentAccess }),
}))

vi.mock('@/rest/axios/axios-rest-client', () => ({
  AxiosRestClient: () => ({}),
}))

vi.mock('@/rest/services/intelligence-service', () => ({
  IntelligenceService: () => mocks.service,
}))

vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: vi.fn(),
}))

const useNavigationMock = vi.mocked(useNavigation)
const navigateToMock = vi.fn(async () => undefined)
const PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
const INTENT = 'Quero automatizar tarefas do dia a dia com Python.'

const firstQuestion: PlanningQuestion = {
  id: 'q1',
  text: 'Você já escreveu algum código antes?',
  kind: 'single',
  options: [
    { id: 'never', text: 'Nunca', exclusive: false },
    { id: 'copied', text: 'Já copiei e adaptei alguns scripts', exclusive: false },
    { id: 'nao-sei', text: 'Não sei', exclusive: true },
  ],
}
const secondQuestion: PlanningQuestion = {
  id: 'q2',
  text: 'O que você quer automatizar?',
  kind: 'multiple',
  options: [
    { id: 'sheets', text: 'Planilhas e relatórios', exclusive: false },
    { id: 'files', text: 'Organização de arquivos', exclusive: false },
    { id: 'texts', text: 'Tratamento de textos', exclusive: false },
    { id: 'nao-sei', text: 'Não sei', exclusive: true },
  ],
}
const thirdQuestion: PlanningQuestion = {
  id: 'q3',
  text: 'Que resultado você quer alcançar com os scripts?',
  kind: 'single',
  options: [
    { id: 'reports', text: 'Criar relatórios a partir de planilhas', exclusive: false },
    { id: 'combine', text: 'Combinar essas tarefas', exclusive: false },
  ],
}

function interviewSession(overrides: Partial<PlanningSession> = {}): PlanningSession {
  return PlanningSessionFaker.fake({
    id: PLANNING_ID,
    intent: INTENT,
    batch: { id: 'batch-1', questions: [firstQuestion, secondQuestion, thirdQuestion] },
    ...overrides,
  })
}

function processingSession(overrides: Partial<PlanningSession> = {}): PlanningSession {
  return PlanningSessionFaker.fake({
    id: PLANNING_ID,
    intent: INTENT,
    status: 'processing',
    batch: null,
    operation: { kind: 'start', startedAt: new Date().toISOString(), stage: null },
    ...overrides,
  })
}

function renderPlannerPage(
  onCreateGoal?: (request: PlanningGoalCreationRequest) => void | Promise<void>,
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const wrapper = ({ children }: PropsWithChildren) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
  const rendered = renderHook(
    () => usePlannerPage({ planningId: PLANNING_ID, onCreateGoal }),
    { wrapper },
  )
  return { ...rendered, queryClient }
}

describe('usePlannerPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    navigateToMock.mockResolvedValue(undefined)
    useNavigationMock.mockReturnValue({
      navigateTo: navigateToMock as unknown as ReturnType<
        typeof useNavigation
      >['navigateTo'],
      navigateToActivity: vi.fn(),
      navigateToGoalDetail: vi.fn(),
      navigateToPlanner: vi.fn(),
    })
    mocks.getCurrentAccess.mockResolvedValue({
      accessToken: 'access-token',
      email: 'learner@shifu.local',
    })
    mocks.service.getPlanningSession.mockResolvedValue(interviewSession())
    mocks.service.cancelPlanning.mockResolvedValue(undefined)
  })

  it('derives the interview, navigates inside the batch, keeps answers and sends the complete batch (CA-02 … CA-09)', async () => {
    registerPlanningEntry(PLANNING_ID)
    mocks.service.answerPlanningQuestions.mockResolvedValue(
      processingSession({
        operation: { kind: 'answer', startedAt: new Date().toISOString(), stage: null },
        answeredBatchCount: 1,
      }),
    )
    const { result, queryClient } = renderPlannerPage()

    await waitFor(() => expect(result.current.view).toBe('interview'))
    expect(mocks.service.getPlanningSession).toHaveBeenCalledWith(
      'access-token',
      PLANNING_ID,
    )
    expect(result.current.intent).toBe(INTENT)
    expect(result.current.stepLabel).toBe('Pergunta 1 de 3 deste conjunto')
    expect(result.current.steps.map((step) => step.state)).toEqual([
      'current',
      'pending',
      'pending',
    ])
    expect(result.current.guidance).toBe(
      'Escolha uma alternativa. Você poderá revisar as respostas antes de enviar este conjunto.',
    )
    expect(result.current.isFirstStep).toBe(true)
    expect(result.current.canSubmit).toBe(false)

    act(() => result.current.handleSelectSingle('unknown-option'))
    expect(result.current.selectedOptionIds).toEqual([])
    act(() => result.current.handleSelectSingle('copied'))
    expect(result.current.selectedOptionIds).toEqual(['copied'])

    act(() => result.current.handleNext())
    expect(result.current.currentQuestion?.id).toBe('q2')
    expect(result.current.stepLabel).toBe('Pergunta 2 de 3 deste conjunto')
    expect(result.current.steps.map((step) => step.state)).toEqual([
      'answered',
      'current',
      'pending',
    ])
    expect(result.current.guidance).toBe(
      'Selecione uma ou mais alternativas. “Não sei” não pode ser combinado com outras respostas.',
    )
    act(() => result.current.handleToggleMultiple('sheets', true))
    act(() => result.current.handleToggleMultiple('files', true))
    expect(result.current.selectedOptionIds).toEqual(['sheets', 'files'])
    act(() => result.current.handleToggleMultiple('nao-sei', true))
    expect(result.current.selectedOptionIds).toEqual(['nao-sei'])
    act(() => result.current.handleToggleMultiple('texts', true))
    expect(result.current.selectedOptionIds).toEqual(['texts'])
    act(() => result.current.handleToggleMultiple('texts', false))
    expect(result.current.selectedOptionIds).toEqual([])
    act(() => result.current.handleToggleMultiple('missing', true))
    expect(result.current.selectedOptionIds).toEqual([])

    act(() => result.current.handleGoToStep(0))
    expect(result.current.selectedOptionIds).toEqual(['copied'])
    act(() => result.current.handleGoToStep(2))
    expect(result.current.isLastStep).toBe(true)
    expect(result.current.canSubmit).toBe(false)
    expect(result.current.guidance).toBe(
      'Escolha uma alternativa. Responda todas as perguntas do conjunto para enviar.',
    )
    act(() => result.current.handleSelectSingle('combine'))
    expect(result.current.canSubmit).toBe(false)
    act(() => result.current.handlePrevious())
    act(() => result.current.handleToggleMultiple('sheets', true))
    expect(result.current.isBatchComplete).toBe(true)
    expect(result.current.stepLabel).toBe(
      'Revisando pergunta 2 de 3 · conjunto respondido',
    )
    expect(result.current.guidance).toBe(
      'Você pode alterar esta resposta. Use as etapas para revisar as demais e enviar na última pergunta.',
    )
    act(() => result.current.handleNext())
    expect(result.current.guidance).toBe(
      'Escolha uma alternativa. Todas as perguntas estão respondidas; revise as etapas antes de enviar.',
    )
    expect(result.current.canSubmit).toBe(true)
    act(() => result.current.handleGoToStep(99))
    expect(result.current.currentQuestion?.id).toBe('q3')

    await act(async () => {
      await result.current.handleSubmitAnswers()
    })
    expect(mocks.service.answerPlanningQuestions).toHaveBeenCalledWith(
      'access-token',
      PLANNING_ID,
      {
        batchId: 'batch-1',
        answers: [
          { questionId: 'q1', optionIds: ['copied'] },
          { questionId: 'q2', optionIds: ['sheets'] },
          { questionId: 'q3', optionIds: ['combine'] },
        ],
      },
    )
    expect(result.current.view).toBe('processing')
    expect(result.current.processingStage).toEqual({
      title: 'Preparando o próximo passo…',
      support:
        'Suas respostas foram enviadas. Estamos verificando o que falta esclarecer.',
      busyLabel: 'Processando…',
    })
    expect(result.current.canSubmit).toBe(false)
    expect(queryClient.getQueryData(planningSessionQueryKey(PLANNING_ID))).toMatchObject({
      status: 'processing',
    })

    mocks.service.getPlanningSession.mockResolvedValue(
      interviewSession({
        batch: { id: 'batch-2', questions: [thirdQuestion, firstQuestion] },
        answeredBatchCount: 1,
      }),
    )
    await waitFor(() => expect(result.current.view).toBe('interview'), {
      timeout: 4_000,
    })
    expect(result.current.currentQuestion?.id).toBe('q3')
    expect(result.current.selectedOptionIds).toEqual([])
    expect(result.current.steps.map((step) => step.state)).toEqual(['current', 'pending'])
    expect(result.current.stepLabel).toBe('Pergunta 1 de 2 deste conjunto')
  })

  it('abandons a planning opened without the composer entry (CA-11)', async () => {
    const { result } = renderPlannerPage()

    await waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('root'))
    expect(result.current.isAbandoning).toBe(true)
    expect(result.current.view).toBe('loading')
    expect(mocks.service.cancelPlanning).toHaveBeenCalledWith('access-token', PLANNING_ID)
    expect(mocks.service.getPlanningSession).not.toHaveBeenCalled()
  })

  it('cancels the planning, drops its cache and returns to the Home (CA-10)', async () => {
    registerPlanningEntry(PLANNING_ID)
    const { result, queryClient } = renderPlannerPage()
    await waitFor(() => expect(result.current.view).toBe('interview'))

    await act(async () => {
      await result.current.handleCancel()
    })

    expect(mocks.service.cancelPlanning).toHaveBeenCalledTimes(1)
    expect(navigateToMock).toHaveBeenCalledWith('root')
    expect(queryClient.getQueryData(planningSessionQueryKey(PLANNING_ID))).toBeUndefined()
    expect(result.current.view).toBe('loading')
  })

  it('still leaves when the delete fails, so the learner is never stuck', async () => {
    registerPlanningEntry(PLANNING_ID)
    mocks.service.cancelPlanning.mockRejectedValue(new Error('offline'))
    const { result } = renderPlannerPage()
    await waitFor(() => expect(result.current.view).toBe('interview'))

    act(() => result.current.handleCreateManually())

    await waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('learningGoalsNew'))
    expect(mocks.service.cancelPlanning).toHaveBeenCalledTimes(1)
  })

  it('retries a failed planning over the preserved context (CA-12)', async () => {
    registerPlanningEntry(PLANNING_ID)
    mocks.service.getPlanningSession.mockResolvedValue(
      interviewSession({ status: 'failed', batch: null, answeredBatchCount: 1 }),
    )
    mocks.service.retryPlanning.mockResolvedValue(
      processingSession({
        operation: { kind: 'retry', startedAt: new Date().toISOString(), stage: null },
        answeredBatchCount: 1,
      }),
    )
    const { result } = renderPlannerPage()
    await waitFor(() => expect(result.current.view).toBe('failed'))

    await act(async () => {
      await result.current.handleRetry()
    })

    expect(mocks.service.retryPlanning).toHaveBeenCalledWith('access-token', PLANNING_ID)
    expect(result.current.view).toBe('processing')
    expect(result.current.processingStage).toEqual({
      title: 'Preparando o próximo passo…',
      support: 'Estamos verificando o que falta esclarecer.',
      busyLabel: 'Processando…',
    })
  })

  it('maps the reported stage and the operation kind to the processing copy (CA-08)', async () => {
    registerPlanningEntry(PLANNING_ID)
    mocks.service.getPlanningSession.mockResolvedValue(processingSession())
    const { result, queryClient } = renderPlannerPage()
    await waitFor(() => expect(result.current.view).toBe('processing'))
    expect(result.current.processingStage?.title).toBe('Analisando seu objetivo…')
    expect(result.current.processingStage?.busyLabel).toBe('Analisando…')

    act(() => {
      queryClient.setQueryData(
        planningSessionQueryKey(PLANNING_ID),
        processingSession({
          operation: {
            kind: 'start',
            startedAt: new Date().toISOString(),
            stage: 'retrieving',
          },
        }),
      )
    })
    await waitFor(() =>
      expect(result.current.processingStage?.title).toBe('Consultando o Currículo…'),
    )
    expect(result.current.processingStage?.busyLabel).toBe('Consultando…')

    act(() => {
      queryClient.setQueryData(
        planningSessionQueryKey(PLANNING_ID),
        processingSession({
          operation: {
            kind: 'retry',
            startedAt: new Date().toISOString(),
            stage: 'composing',
          },
        }),
      )
    })
    await waitFor(() =>
      expect(result.current.processingStage?.title).toBe('Montando sua proposta…'),
    )
    expect(result.current.processingStage?.busyLabel).toBe('Montando proposta…')

    act(() => {
      queryClient.setQueryData(
        planningSessionQueryKey(PLANNING_ID),
        processingSession({
          operation: { kind: 'retry', startedAt: new Date().toISOString(), stage: null },
        }),
      )
    })
    await waitFor(() =>
      expect(result.current.processingStage?.title).toBe('Analisando seu objetivo…'),
    )
  })

  it('shows a conflict on submit and refreshes the state (CA-14)', async () => {
    registerPlanningEntry(PLANNING_ID)
    mocks.service.getPlanningSession.mockResolvedValue(
      interviewSession({ batch: { id: 'batch-1', questions: [firstQuestion] } }),
    )
    mocks.service.answerPlanningQuestions.mockRejectedValue(
      new RestError('Já existe uma operação em andamento neste planejamento.', 409),
    )
    const { result } = renderPlannerPage()
    await waitFor(() => expect(result.current.view).toBe('interview'))
    act(() => result.current.handleSelectSingle('never'))
    expect(result.current.canSubmit).toBe(true)

    await act(async () => {
      await result.current.handleSubmitAnswers()
    })

    expect(result.current.errorMessage).toBe(
      'Já existe uma operação em andamento neste planejamento.',
    )
    await waitFor(() => expect(mocks.service.getPlanningSession).toHaveBeenCalledTimes(2))
    expect(result.current.view).toBe('interview')
    expect(result.current.selectedOptionIds).toEqual(['never'])
  })

  it('keeps the answers and explains a transport failure of the submission', async () => {
    registerPlanningEntry(PLANNING_ID)
    mocks.service.getPlanningSession.mockResolvedValue(
      interviewSession({ batch: { id: 'batch-1', questions: [firstQuestion] } }),
    )
    mocks.service.answerPlanningQuestions.mockRejectedValue(new Error('socket hang up'))
    const { result } = renderPlannerPage()
    await waitFor(() => expect(result.current.view).toBe('interview'))
    act(() => result.current.handleSelectSingle('never'))

    await act(async () => {
      await result.current.handleSubmitAnswers()
    })

    expect(result.current.errorMessage).toBe(
      'Não foi possível enviar suas respostas agora. Suas escolhas continuam nesta página; tente novamente.',
    )
    expect(result.current.selectedOptionIds).toEqual(['never'])
    expect(result.current.view).toBe('interview')
    act(() => result.current.handleSelectSingle('copied'))
    expect(result.current.errorMessage).toBeNull()
  })

  it('refreshes a planning that disappeared during a retry and leaves on an expired session', async () => {
    registerPlanningEntry(PLANNING_ID)
    mocks.service.getPlanningSession.mockResolvedValue(
      interviewSession({ status: 'validation-failed', batch: null }),
    )
    mocks.service.retryPlanning.mockRejectedValueOnce(new RestError('missing', 404))
    const { result } = renderPlannerPage()
    await waitFor(() => expect(result.current.view).toBe('validation-failed'))

    await act(async () => {
      await result.current.handleRetry()
    })
    await waitFor(() => expect(mocks.service.getPlanningSession).toHaveBeenCalledTimes(2))
    expect(result.current.errorMessage).toBeNull()

    mocks.service.retryPlanning.mockRejectedValueOnce(new RestError('expired', 401))
    await act(async () => {
      await result.current.handleRetry()
    })
    expect(navigateToMock).toHaveBeenCalledWith('login')
  })

  it('reports a missing planning and leaves when the session expired (CA-23)', async () => {
    registerPlanningEntry(PLANNING_ID)
    mocks.service.getPlanningSession.mockRejectedValue(new RestError('missing', 404))
    const { result } = renderPlannerPage()

    await waitFor(() => expect(result.current.view).toBe('not-found'))
    act(() => result.current.handleReturnHome())
    await waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('root'))
    expect(mocks.service.cancelPlanning).not.toHaveBeenCalled()
    cleanup()

    registerPlanningEntry(PLANNING_ID)
    mocks.getCurrentAccess.mockResolvedValue(null)
    renderPlannerPage()
    await waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('login'))
  })

  it('recovers from a failed load through the request retry (CA-13)', async () => {
    registerPlanningEntry(PLANNING_ID)
    mocks.service.getPlanningSession.mockRejectedValueOnce(
      new AuthError('unavailable', 'provider down'),
    )
    const { result } = renderPlannerPage()
    await waitFor(() => expect(result.current.view).toBe('request-error'))

    act(() => result.current.handleRetryLoad())

    await waitFor(() => expect(result.current.view).toBe('interview'))
    expect(mocks.service.getPlanningSession).toHaveBeenCalledTimes(2)
  })

  it('exposes a validated proposal to the review boundary and treats inconsistent payloads as errors (CA-19)', async () => {
    registerPlanningEntry(PLANNING_ID)
    const proposal = PlanningSessionFaker.fakeProposal()
    mocks.service.getPlanningSession.mockResolvedValue(
      interviewSession({ status: 'proposal', batch: null, proposal }),
    )
    const { result, queryClient } = renderPlannerPage()

    await waitFor(() => expect(result.current.view).toBe('proposal'))
    expect(result.current.proposal).toEqual(proposal)
    expect(result.current.steps).toEqual([])
    expect(result.current.stepLabel).toBe('')
    expect(result.current.guidance).toBe('')

    act(() => {
      queryClient.setQueryData(
        planningSessionQueryKey(PLANNING_ID),
        interviewSession({ status: 'interview', batch: null }),
      )
    })
    await waitFor(() => expect(result.current.view).toBe('request-error'))
    act(() => {
      queryClient.setQueryData(
        planningSessionQueryKey(PLANNING_ID),
        interviewSession({ status: 'proposal', batch: null, proposal: null }),
      )
    })
    await waitFor(() => expect(result.current.view).toBe('request-error'))
    act(() => {
      queryClient.setQueryData(
        planningSessionQueryKey(PLANNING_ID),
        interviewSession({ status: 'out-of-scope', batch: null }),
      )
    })
    await waitFor(() => expect(result.current.view).toBe('out-of-scope'))
    act(() => result.current.handleReformulate())
    await waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('root'))
    expect(mocks.service.cancelPlanning).toHaveBeenCalledTimes(1)
  })

  it('restarts the planning from the review and replaces the proposal with the new processing (CA-08)', async () => {
    registerPlanningEntry(PLANNING_ID)
    const proposal = PlanningSessionFaker.fakeProposal()
    mocks.service.getPlanningSession.mockResolvedValue(
      interviewSession({ status: 'proposal', batch: null, proposal, generation: 1 }),
    )
    mocks.service.restartPlanning.mockResolvedValue(
      processingSession({
        generation: 2,
        operation: { kind: 'restart', startedAt: new Date().toISOString(), stage: null },
      }),
    )
    const { result } = renderPlannerPage()
    await waitFor(() => expect(result.current.view).toBe('proposal'))
    expect(result.current.generation).toBe(1)

    let restarted = false
    await act(async () => {
      restarted = await result.current.handleRestart('Quero aprender APIs web')
    })

    expect(restarted).toBe(true)
    expect(mocks.service.restartPlanning).toHaveBeenCalledWith(
      'access-token',
      PLANNING_ID,
      'Quero aprender APIs web',
    )
    expect(result.current.view).toBe('processing')
    expect(result.current.generation).toBe(2)
    expect(result.current.proposal).toBeNull()
    expect(result.current.processingStage?.title).toBe('Analisando seu objetivo…')
    expect(result.current.restartErrorMessage).toBeNull()
  })

  it('keeps the proposal and reports a conflict when the restart is refused (CA-09)', async () => {
    registerPlanningEntry(PLANNING_ID)
    const proposal = PlanningSessionFaker.fakeProposal()
    mocks.service.getPlanningSession.mockResolvedValue(
      interviewSession({ status: 'proposal', batch: null, proposal }),
    )
    mocks.service.restartPlanning.mockRejectedValueOnce(
      new RestError('Já existe uma operação em andamento neste planejamento.', 409),
    )
    const { result } = renderPlannerPage()
    await waitFor(() => expect(result.current.view).toBe('proposal'))

    let restarted = true
    await act(async () => {
      restarted = await result.current.handleRestart('Quero aprender APIs web')
    })

    expect(restarted).toBe(false)
    expect(result.current.restartErrorMessage).toBe(
      'Já existe uma operação em andamento neste planejamento.',
    )
    expect(result.current.view).toBe('proposal')
    expect(result.current.proposal).toEqual(proposal)

    mocks.service.restartPlanning.mockRejectedValueOnce(new Error('offline'))
    await act(async () => {
      restarted = await result.current.handleRestart('Quero aprender APIs web')
    })
    expect(restarted).toBe(false)
    expect(result.current.restartErrorMessage).toBe(
      'Não foi possível reiniciar o planejamento agora. Sua proposta continua nesta página; tente novamente.',
    )
  })

  it('ignores a restart outside the review and delivers the goal creation contract (CA-05)', async () => {
    registerPlanningEntry(PLANNING_ID)
    const { result } = renderPlannerPage()
    await waitFor(() => expect(result.current.view).toBe('interview'))

    let restarted = true
    await act(async () => {
      restarted = await result.current.handleRestart('Quero aprender APIs web')
    })
    expect(restarted).toBe(false)
    expect(mocks.service.restartPlanning).not.toHaveBeenCalled()

    const request: PlanningGoalCreationRequest = {
      planningId: PLANNING_ID,
      title: 'Automação',
      description: 'Scripts',
      proposal: PlanningSessionFaker.fakeProposal(),
    }
    await act(async () => {
      await result.current.handleCreateGoal(request)
    })
    expect(result.current.goalCreationNotice).toBe(
      'A criação do Objetivo chega na próxima etapa do Planejador. Sua proposta e suas edições continuam nesta página.',
    )
    cleanup()

    registerPlanningEntry(PLANNING_ID)
    const onCreateGoal = vi.fn(async () => undefined)
    const consumer = renderPlannerPage(onCreateGoal)
    await waitFor(() => expect(consumer.result.current.view).toBe('interview'))
    await act(async () => {
      await consumer.result.current.handleCreateGoal(request)
    })
    expect(onCreateGoal).toHaveBeenCalledWith(request)
    expect(consumer.result.current.goalCreationNotice).toBeNull()
  })
})
