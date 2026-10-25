import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { useEffect, type ComponentType, type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PlanningSessionFaker } from '@/core/intelligence/fakers/planning-session-faker'

import { PlanningProposalReview } from '..'
import {
  type PlanningProposalReviewController,
  type PlanningProposalReviewProps,
  usePlanningProposalReview,
} from '../use-planning-proposal-review'

// Entrance motion settles at once, so assertions see the final state; the
// shared entrance owns its animated cases.
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('../use-planning-proposal-review', () => ({
  usePlanningProposalReview: vi.fn(),
}))

type FlowNode = { id: string; type: string; data: Record<string, unknown> }
type ReactFlowMockProps = {
  children?: ReactNode
  nodes: FlowNode[]
  nodeTypes: Record<string, ComponentType<{ data: Record<string, unknown> }>>
  onInit?: (instance: unknown) => void
  onMove?: (event: unknown, viewport: { x: number; y: number; zoom: number }) => void
}

const flowInstance = vi.hoisted(() => ({
  setViewport: vi.fn(async () => true),
  zoomTo: vi.fn(async () => true),
  getNodes: () => [],
}))

vi.mock('@xyflow/react', () => ({
  Background: () => null,
  Controls: () => null,
  Handle: () => null,
  Position: { Bottom: 'bottom', Top: 'top' },
  ReactFlow: ({ children, nodes, nodeTypes, onInit, onMove }: ReactFlowMockProps) => {
    useEffect(() => {
      onInit?.(flowInstance)
      onMove?.(undefined, { x: 0, y: 0, zoom: 1.2 })
    }, [onInit, onMove])
    return (
      <div>
        {nodes.map((node) => {
          const NodeComponent = nodeTypes[node.type]
          return NodeComponent ? <NodeComponent data={node.data} key={node.id} /> : null
        })}
        {children}
      </div>
    )
  },
}))

const elkMocks = vi.hoisted(() => ({ layout: vi.fn() }))

vi.mock('elkjs/lib/elk.bundled.js', () => ({
  default: class {
    layout = elkMocks.layout
  },
}))

const usePlanningProposalReviewMock = vi.mocked(usePlanningProposalReview)
const PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
const INTENT = 'Quero automatizar tarefas do dia a dia com Python.'
const proposal = PlanningSessionFaker.fakeProposal({
  title: 'Automação com Python',
  description: 'Scripts para planilhas.',
  skills: [
    {
      skillId: 'logic',
      name: 'Lógica de programação',
      justification: 'Você já adaptou scripts.',
    },
    {
      skillId: 'python',
      name: 'Python essencial',
      justification: 'Para escrever scripts.',
    },
  ],
  relations: [{ skillId: 'python', foundationSkillId: 'logic' }],
})

function controller(
  overrides: Partial<PlanningProposalReviewController> = {},
): PlanningProposalReviewController {
  return {
    view: 'graph',
    title: 'Automação com Python',
    description: 'Scripts para planilhas.',
    titleError: null,
    descriptionError: null,
    relationSummary:
      'As duas habilidades se complementam. Você escolhe por onde começar.',
    isRestartDialogOpen: false,
    isFrozen: false,
    createGoalLabel: 'Criar objetivo',
    goalCreationNotice: null,
    titleRef: { current: null },
    descriptionRef: { current: null },
    restartTriggerRef: { current: null },
    handleViewChange: vi.fn(),
    handleTitleChange: vi.fn(),
    handleDescriptionChange: vi.fn(),
    handleCreateGoal: vi.fn(),
    handleOpenRestart: vi.fn(),
    handleCloseRestart: vi.fn(),
    handleSubmitRestart: vi.fn(async () => undefined),
    ...overrides,
  }
}

function renderReview(
  controllerOverrides: Partial<PlanningProposalReviewController> = {},
  propsOverrides: Partial<PlanningProposalReviewProps> = {},
) {
  const current = controller(controllerOverrides)
  usePlanningProposalReviewMock.mockReturnValue(current)
  const props: PlanningProposalReviewProps = {
    planningId: PLANNING_ID,
    intent: INTENT,
    proposal,
    isCancelling: false,
    isRestarting: false,
    restartErrorMessage: null,
    goalCreation: { status: 'idle', message: null },
    onCancel: vi.fn(),
    onRestart: vi.fn(async () => true),
    onCreateGoal: vi.fn(),
    ...propsOverrides,
  }
  render(<PlanningProposalReview {...props} />)
  return { current, props }
}

function measureContainer(width: number, height: number) {
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
    configurable: true,
    get: () => width,
  })
  Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
    configurable: true,
    get: () => height,
  })
}

describe('PlanningProposalReview', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe = vi.fn()
        disconnect = vi.fn()
        unobserve = vi.fn()
      },
    )
    measureContainer(1170, 640)
    elkMocks.layout.mockResolvedValue({
      children: [
        { id: 'proposal-root', x: 0, y: 0 },
        { id: 'logic', x: 0, y: 150 },
        { id: 'python', x: 400, y: 150 },
      ],
    })
  })

  it('renders the proposal in the graph view with the editable fields and read-only Skills (CA-01, CA-03)', async () => {
    const { current } = renderReview()

    expect(
      screen.getByRole('heading', { level: 1, name: 'Revise seu objetivo' }),
    ).toBeVisible()
    expect(screen.getByLabelText('Título')).toHaveValue('Automação com Python')
    expect(screen.getByLabelText('Descrição')).toHaveValue('Scripts para planilhas.')
    expect(screen.getByRole('tab', { name: 'Grafo' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByRole('tab', { name: 'Lista' })).toHaveAttribute(
      'aria-selected',
      'false',
    )
    expect(screen.getByText(current.relationSummary)).toBeVisible()
    const graph = screen.getByRole('region', { name: 'Grafo das Habilidades propostas' })
    expect(
      await within(graph).findByRole('article', {
        name: 'Proposta de Objetivo: Automação com Python',
      }),
    ).toBeVisible()
    expect(
      within(graph).getByRole('article', { name: 'Habilidade Lógica de programação' }),
    ).toHaveTextContent('Você já adaptou scripts.')
    expect(
      within(graph).getByRole('article', { name: 'Habilidade Python essencial' }),
    ).toHaveTextContent('Para escrever scripts.')
    expect(within(graph).queryByRole('link')).not.toBeInTheDocument()
    expect(
      within(graph).queryByRole('button', { name: /remover/i }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('list', { name: 'Habilidades sugeridas' }),
    ).not.toBeInTheDocument()

    fireEvent.click(within(graph).getByRole('button', { name: 'Ampliar grafo' }))
    fireEvent.click(within(graph).getByRole('button', { name: 'Reduzir grafo' }))
    fireEvent.click(
      within(graph).getByRole('button', { name: 'Restaurar posição inicial do grafo' }),
    )
    expect(flowInstance.zoomTo).toHaveBeenCalledTimes(2)
    expect(flowInstance.setViewport).toHaveBeenLastCalledWith({ x: 385, y: 24, zoom: 1 })
    expect(
      within(graph).getByRole('article', { name: 'Habilidade Python essencial' }),
    ).toHaveStyle({ width: '360px' })
  })

  it('shares each layer between the Skills on a narrow container, as in the mobile frame', async () => {
    measureContainer(350, 800)
    renderReview()

    const graph = screen.getByRole('region', { name: 'Grafo das Habilidades propostas' })
    expect(
      await within(graph).findByRole('article', {
        name: 'Proposta de Objetivo: Automação com Python',
      }),
    ).toHaveStyle({ width: '318px' })
    expect(
      within(graph).getByRole('article', { name: 'Habilidade Lógica de programação' }),
    ).toHaveStyle({ width: '318px' })
    expect(
      within(graph).getByRole('article', { name: 'Habilidade Python essencial' }),
    ).toHaveStyle({ width: '318px' })
    expect(flowInstance.setViewport).toHaveBeenLastCalledWith({ x: 16, y: 16, zoom: 1 })
  })

  it('tells the learner when the graph layout fell back to the grid', async () => {
    elkMocks.layout.mockRejectedValueOnce(new Error('layout failed'))
    renderReview()

    expect(
      await screen.findByText(
        'O layout do grafo foi ajustado para manter as Habilidades acessíveis.',
      ),
    ).toBeVisible()
    const graph = screen.getByRole('region', { name: 'Grafo das Habilidades propostas' })
    expect(
      within(graph).getByRole('article', { name: 'Habilidade Python essencial' }),
    ).toBeVisible()
  })

  it('renders the same Skills and justifications in the list view (CA-02)', () => {
    const { current } = renderReview({ view: 'list' })

    expect(screen.getByRole('tab', { name: 'Lista' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(
      screen.queryByRole('region', { name: 'Grafo das Habilidades propostas' }),
    ).not.toBeInTheDocument()
    const list = screen.getByRole('list', { name: 'Habilidades sugeridas' })
    const items = within(list).getAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('Lógica de programação')
    expect(items[0]).toHaveTextContent('Você já adaptou scripts.')
    expect(items[1]).toHaveTextContent('Python essencial')
    expect(within(list).queryByRole('textbox')).not.toBeInTheDocument()

    fireEvent.mouseDown(screen.getByRole('tab', { name: 'Grafo' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Grafo' }))
    expect(current.handleViewChange).toHaveBeenCalledWith('graph')
  })

  it('wires the field edits, the validation messages and the actions (CA-04, CA-05)', () => {
    const { current, props } = renderReview(
      {
        titleError: 'Informe um título para o Objetivo.',
        descriptionError: 'Informe uma descrição para o Objetivo.',
      },
      { goalCreation: { status: 'idle', message: null } },
    )

    fireEvent.change(screen.getByLabelText('Título'), { target: { value: 'Novo' } })
    expect(current.handleTitleChange).toHaveBeenCalledWith('Novo')
    fireEvent.change(screen.getByLabelText('Descrição'), { target: { value: 'Texto' } })
    expect(current.handleDescriptionChange).toHaveBeenCalledWith('Texto')
    expect(screen.getByLabelText('Título')).toHaveAttribute('aria-invalid', 'true')
    const alerts = screen.getAllByRole('alert')
    expect(alerts[0]).toHaveTextContent('Informe um título para o Objetivo.')
    expect(alerts[1]).toHaveTextContent('Informe uma descrição para o Objetivo.')

    fireEvent.click(screen.getByRole('button', { name: 'Criar objetivo' }))
    expect(current.handleCreateGoal).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Reiniciar planejamento' }))
    expect(current.handleOpenRestart).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(props.onCancel).toHaveBeenCalledOnce()
  })

  it('renders the creation progress, the failure and the uncertain result as the frames draw them', () => {
    renderReview(
      {
        isFrozen: true,
        createGoalLabel: 'Criando objetivo…',
        goalCreationNotice: {
          tone: 'processing',
          title: 'Criando seu objetivo…',
          support: 'Estamos salvando o objetivo e as habilidades que você confirmou.',
        },
      },
      { goalCreation: { status: 'creating', message: null } },
    )
    expect(screen.getByText('Criando seu objetivo…')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Criando objetivo…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Criando objetivo…' })).toHaveAttribute(
      'aria-busy',
      'true',
    )
    expect(screen.getByLabelText('Título')).toBeDisabled()
    expect(screen.getByLabelText('Descrição')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reiniciar planejamento' })).toBeDisabled()
    cleanup()

    renderReview(
      {
        createGoalLabel: 'Tentar criar objetivo',
        goalCreationNotice: {
          tone: 'failure',
          title: 'Não foi possível criar o objetivo',
          support: 'Sua proposta foi mantida. Tente criar o objetivo novamente.',
        },
      },
      { goalCreation: { status: 'failed', message: null } },
    )
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível criar o objetivo',
    )
    expect(screen.getByRole('button', { name: 'Tentar criar objetivo' })).toBeEnabled()
    expect(screen.getByLabelText('Título')).toBeEnabled()
    cleanup()

    const { current } = renderReview(
      {
        isFrozen: true,
        createGoalLabel: 'Verificar resultado',
        goalCreationNotice: {
          tone: 'uncertain',
          title: 'Não conseguimos confirmar a criação do objetivo',
          support: 'A resposta não chegou.',
        },
      },
      { goalCreation: { status: 'uncertain', message: null } },
    )
    expect(
      screen.getByText('Não conseguimos confirmar a criação do objetivo'),
    ).toBeVisible()
    expect(screen.getByLabelText('Título')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reiniciar planejamento' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Verificar resultado' }))
    expect(current.handleCreateGoal).toHaveBeenCalledOnce()
  })

  it('disables every action while a restart or a cancel is in flight', () => {
    renderReview({}, { isRestarting: true })

    expect(screen.getByRole('button', { name: 'Reiniciar planejamento' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Criar objetivo' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
    cleanup()

    renderReview({}, { isCancelling: true })
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
  })

  it('opens the restart dialog with the active intention, a single action and a close control (CA-06, CA-07)', () => {
    const { current } = renderReview(
      { isRestartDialogOpen: true },
      { restartErrorMessage: 'Já existe uma operação em andamento neste planejamento.' },
    )

    const dialog = screen.getByRole('alertdialog', { name: 'Reiniciar planejamento' })
    expect(within(dialog).getByLabelText('O que você quer aprender?')).toHaveValue(INTENT)
    expect(within(dialog).getByLabelText('O que você quer aprender?')).toHaveFocus()
    expect(dialog).toHaveTextContent(
      'Ao continuar, a proposta e as respostas anteriores serão substituídas por um novo planejamento.',
    )
    expect(within(dialog).getByRole('alert')).toHaveTextContent(
      'Já existe uma operação em andamento neste planejamento.',
    )
    expect(
      within(dialog).getByRole('button', { name: 'Iniciar planejamento' }),
    ).toBeEnabled()
    expect(
      within(dialog).queryByRole('button', { name: 'Cancelar' }),
    ).not.toBeInTheDocument()

    fireEvent.change(within(dialog).getByLabelText('O que você quer aprender?'), {
      target: { value: 'Quero aprender APIs web' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Iniciar planejamento' }))
    expect(current.handleSubmitRestart).toHaveBeenCalledWith('Quero aprender APIs web')

    fireEvent.click(within(dialog).getByRole('button', { name: 'Fechar' }))
    expect(current.handleCloseRestart).toHaveBeenCalledOnce()
    fireEvent.keyDown(dialog, { key: 'Escape' })
    expect(current.handleCloseRestart).toHaveBeenCalledTimes(2)
  })

  it('rejects an empty intention inside the dialog before calling the restart', () => {
    const { current } = renderReview({ isRestartDialogOpen: true })
    const dialog = screen.getByRole('alertdialog', { name: 'Reiniciar planejamento' })

    fireEvent.change(within(dialog).getByLabelText('O que você quer aprender?'), {
      target: { value: '   ' },
    })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Iniciar planejamento' }))

    expect(within(dialog).getByRole('alert')).toHaveTextContent(
      'Descreva o que você quer aprender antes de continuar.',
    )
    expect(current.handleSubmitRestart).not.toHaveBeenCalled()
  })

  it('shows the busy state of the restart action', () => {
    renderReview({ isRestartDialogOpen: true }, { isRestarting: true })

    const dialog = screen.getByRole('alertdialog', { name: 'Reiniciar planejamento' })
    expect(within(dialog).getByRole('button', { name: 'Iniciando…' })).toBeDisabled()
    expect(within(dialog).getByLabelText('O que você quer aprender?')).toBeDisabled()
  })
})
