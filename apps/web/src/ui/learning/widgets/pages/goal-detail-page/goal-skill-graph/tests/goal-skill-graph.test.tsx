import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { GoalSkillDetail } from '@/core/learning/goal-detail'

import { GoalSkillGraph } from '..'
import { useGoalSkillGraph } from '../use-goal-skill-graph'

vi.mock('@xyflow/react', () => ({
  Background: () => null,
  Controls: () => null,
  ReactFlow: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))
vi.mock('../use-goal-skill-graph', () => ({ useGoalSkillGraph: vi.fn() }))

const useGoalSkillGraphMock = vi.mocked(useGoalSkillGraph)
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
  })
})
