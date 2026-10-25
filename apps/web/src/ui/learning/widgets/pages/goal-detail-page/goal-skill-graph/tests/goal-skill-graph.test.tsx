import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { useEffect, type ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { GoalSkillDetail } from '@/core/learning/goal-detail'

import { GoalSkillGraph } from '..'
import type { GoalFlowNodeType } from '../goal-graph-node'
import { useGoalSkillGraph } from '../use-goal-skill-graph'

type ReactFlowMockProps = {
  children?: ReactNode
  nodes: { id: string }[]
  onInit?: (instance: unknown) => void
  onMove?: (event: unknown, viewport: { x: number; y: number; zoom: number }) => void
  onNodeMouseEnter?: (event: unknown, node: { id: string }) => void
  onNodeMouseLeave?: () => void
}

const flowInstance = vi.hoisted(() => ({
  fitView: vi.fn(async () => true),
  zoomTo: vi.fn(async () => true),
}))

vi.mock('@xyflow/react', () => ({
  Background: () => null,
  Controls: () => null,
  Handle: () => null,
  Position: { Bottom: 'bottom', Top: 'top' },
  ReactFlow: ({
    children,
    nodes,
    onInit,
    onMove,
    onNodeMouseEnter,
    onNodeMouseLeave,
  }: ReactFlowMockProps) => {
    useEffect(() => {
      onInit?.(flowInstance)
      onMove?.(undefined, { x: 0, y: 0, zoom: 0.8 })
    }, [onInit, onMove])
    return (
      <div>
        {nodes.map((node) => (
          <div className='react-flow__node' data-id={node.id} key={node.id}>
            <button
              onMouseEnter={() => onNodeMouseEnter?.(undefined, node)}
              onMouseLeave={() => onNodeMouseLeave?.()}
              type='button'
            >
              {node.id}
            </button>
          </div>
        ))}
        {children}
      </div>
    )
  },
}))
vi.mock('../use-goal-skill-graph', () => ({ useGoalSkillGraph: vi.fn() }))

const useGoalSkillGraphMock = vi.mocked(useGoalSkillGraph)
const rootNode: GoalFlowNodeType = {
  id: 'goal-root',
  type: 'goalRoot',
  position: { x: 0, y: 0 },
  data: { title: 'Fundamentos de programação' },
}
const skill: GoalSkillDetail = {
  skillExperienceId: '01SHF000000000000000000004',
  skillId: '01SHF000000000000000000005',
  name: 'Lógica',
  status: 'learning',
  progress: 60,
  inclusionReason: null,
}

describe('GoalSkillGraph', () => {
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
  })

  it('fits the graph once the flow is ready, restores it on demand and reports focus and hover', () => {
    const handleZoomChange = vi.fn()
    const handleNodeHover = vi.fn()
    const handleNodeFocus = vi.fn()
    useGoalSkillGraphMock.mockReturnValue({
      nodes: [rootNode],
      edges: [],
      zoom: 1,
      isLayoutError: false,
      canZoomIn: true,
      canZoomOut: true,
      handleZoomIn: vi.fn(),
      handleZoomOut: vi.fn(),
      handleZoomChange,
      handleNodeHover,
      handleNodeFocus,
    })
    render(
      <GoalSkillGraph
        goalId='01SHF000000000000000000003'
        onRemoveSkill={vi.fn()}
        relations={[]}
        skills={[skill]}
        title='Fundamentos de programação'
      />,
    )
    const graph = screen.getByRole('region', { name: 'Grafo de Habilidades' })

    expect(flowInstance.fitView).toHaveBeenCalledWith({ maxZoom: 1, padding: 0.08 })
    expect(handleZoomChange).toHaveBeenCalledWith(0.8)
    fireEvent.click(within(graph).getByRole('button', { name: 'Ampliar grafo' }))
    expect(flowInstance.zoomTo).toHaveBeenLastCalledWith(1.2)
    fireEvent.click(within(graph).getByRole('button', { name: 'Reduzir grafo' }))
    expect(flowInstance.zoomTo).toHaveBeenLastCalledWith(0.8)

    const restore = within(graph).getByRole('button', {
      name: 'Restaurar posição inicial do grafo',
    })
    expect(restore).toBeEnabled()
    flowInstance.fitView.mockClear()
    fireEvent.click(restore)
    expect(flowInstance.fitView).toHaveBeenCalledOnce()

    const nodeButton = within(graph).getByRole('button', { name: 'goal-root' })
    fireEvent.focus(nodeButton)
    expect(handleNodeFocus).toHaveBeenLastCalledWith('goal-root')
    fireEvent.blur(nodeButton, { relatedTarget: document.body })
    expect(handleNodeFocus).toHaveBeenLastCalledWith(null)
    fireEvent.mouseEnter(nodeButton)
    expect(handleNodeHover).toHaveBeenLastCalledWith('goal-root')
    fireEvent.mouseLeave(nodeButton)
    expect(handleNodeHover).toHaveBeenLastCalledWith(null)
  })

  it('renders accessible bounded zoom controls from its graph controller', () => {
    const handleZoomIn = vi.fn()
    const handleZoomOut = vi.fn()
    useGoalSkillGraphMock.mockReturnValue({
      nodes: [],
      edges: [],
      zoom: 1,
      isLayoutError: false,
      canZoomIn: true,
      canZoomOut: true,
      handleZoomIn,
      handleZoomOut,
      handleZoomChange: vi.fn(),
      handleNodeHover: vi.fn(),
      handleNodeFocus: vi.fn(),
    })
    render(
      <GoalSkillGraph
        goalId='01SHF000000000000000000003'
        onRemoveSkill={vi.fn()}
        relations={[]}
        skills={[skill]}
        title='Fundamentos de programação'
      />,
    )

    expect(screen.getByRole('group', { name: 'Controles do grafo' })).toBeVisible()
    expect(screen.getByLabelText('Zoom do grafo: 100%')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Ampliar grafo' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reduzir grafo' }))
    expect(handleZoomIn).toHaveBeenCalledOnce()
    expect(handleZoomOut).toHaveBeenCalledOnce()
  })

  it('keeps graph fallback feedback visible without making graph edits available', () => {
    useGoalSkillGraphMock.mockReturnValue({
      nodes: [],
      edges: [],
      zoom: 0.25,
      isLayoutError: true,
      canZoomIn: true,
      canZoomOut: false,
      handleZoomIn: vi.fn(),
      handleZoomOut: vi.fn(),
      handleZoomChange: vi.fn(),
      handleNodeHover: vi.fn(),
      handleNodeFocus: vi.fn(),
    })
    render(
      <GoalSkillGraph
        goalId='01SHF000000000000000000003'
        onRemoveSkill={vi.fn()}
        relations={[]}
        skills={[skill]}
        title='Fundamentos de programação'
      />,
    )
    expect(
      screen.getByText(
        'O layout do grafo foi ajustado para manter as Habilidades acessíveis.',
      ),
    ).toBeVisible()
    expect(screen.getByRole('button', { name: 'Reduzir grafo' })).toBeDisabled()
    expect(
      screen.getByRole('button', { name: 'Restaurar posição inicial do grafo' }),
    ).toBeDisabled()
    expect(flowInstance.fitView).not.toHaveBeenCalled()
  })
})
