import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import type { ReactFlowInstance } from '@xyflow/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  PlanningProposalSkill,
  PlanningSkillRelation,
} from '@/core/intelligence/planning-session'

import type { ProposalFlowNodeType } from '../proposal-skill-graph/proposal-graph-node'
import {
  PROPOSAL_ROOT_ID,
  useProposalSkillGraph,
} from '../proposal-skill-graph/use-proposal-skill-graph'

const mocks = vi.hoisted(() => ({
  layout: vi.fn(),
}))

vi.mock('elkjs/lib/elk.bundled.js', () => ({
  default: class {
    layout = mocks.layout
  },
}))

const skills: PlanningProposalSkill[] = [
  { skillId: 'logic', name: 'Lógica de programação', justification: 'Base.' },
  { skillId: 'python', name: 'Python essencial', justification: 'Scripts.' },
  { skillId: 'automation', name: 'Automação de planilhas', justification: 'Aplicação.' },
]
const relations: PlanningSkillRelation[] = [
  { skillId: 'automation', foundationSkillId: 'python' },
  { skillId: 'automation', foundationSkillId: 'unknown' },
  { skillId: 'python', foundationSkillId: 'python' },
]

describe('useProposalSkillGraph', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    mocks.layout.mockResolvedValue({
      children: [
        { id: PROPOSAL_ROOT_ID, x: 200, y: 0 },
        { id: 'logic', x: 0, y: 150 },
        { id: 'python', x: 400, y: 150 },
        { id: 'automation', x: 400, y: 360 },
      ],
    })
  })

  it('draws only the Curriculum relations between proposed Skills plus root edges (CA-03)', async () => {
    const { result } = renderHook(() =>
      useProposalSkillGraph('Automação com Python', skills, relations),
    )

    expect(result.current.edges.map((edge) => edge.id)).toEqual([
      'python-automation',
      `${PROPOSAL_ROOT_ID}-logic`,
      `${PROPOSAL_ROOT_ID}-python`,
    ])
    await waitFor(() => expect(result.current.nodes).toHaveLength(4))
    expect(result.current.nodes[1].position).toEqual({ x: 0, y: 150 })
    expect(result.current.nodes[2].position).toEqual({ x: 408, y: 150 })
    expect(result.current.nodes[0]).toMatchObject({
      id: PROPOSAL_ROOT_ID,
      type: 'proposalRoot',
      position: { x: 184, y: 0 },
      data: { title: 'Automação com Python', width: 400 },
    })
    expect(result.current.nodes[3]).toMatchObject({
      id: 'automation',
      type: 'proposalSkill',
      position: { x: 204, y: 360 },
      data: { skill: skills[2], width: 360, isCompact: false },
    })
    expect(result.current.isLayoutError).toBe(false)
    expect(result.current.isReady).toBe(false)
    expect(mocks.layout).toHaveBeenCalledWith(
      expect.objectContaining({
        layoutOptions: expect.objectContaining({
          'elk.layered.spacing.nodeNodeBetweenLayers': '48',
          'elk.spacing.nodeNode': '48',
        }),
        children: [
          expect.objectContaining({ id: PROPOSAL_ROOT_ID, width: 400 }),
          expect.objectContaining({ id: 'logic', width: 360 }),
          expect.objectContaining({ id: 'python', width: 360 }),
          expect.objectContaining({ id: 'automation', width: 360 }),
        ],
        edges: [
          { id: 'python-automation', sources: ['python'], targets: ['automation'] },
          {
            id: `${PROPOSAL_ROOT_ID}-logic`,
            sources: [PROPOSAL_ROOT_ID],
            targets: ['logic'],
          },
          {
            id: `${PROPOSAL_ROOT_ID}-python`,
            sources: [PROPOSAL_ROOT_ID],
            targets: ['python'],
          },
        ],
      }),
    )
  })

  it('sizes the layout boxes from the copy and survives circular relations', async () => {
    const longSkill: PlanningProposalSkill = {
      skillId: 'long',
      name: 'Automação de arquivos e planilhas com Python',
      justification:
        'Para aplicar a lógica e o Python ao que você pediu: ler, transformar e gerar arquivos e planilhas do dia a dia.',
    }
    const circular: PlanningSkillRelation[] = [
      { skillId: 'logic', foundationSkillId: 'python' },
      { skillId: 'python', foundationSkillId: 'logic' },
    ]
    const circularSkills = [skills[0], skills[1], longSkill]
    const { result } = renderHook(() =>
      useProposalSkillGraph('Título', circularSkills, circular),
    )

    await waitFor(() => expect(result.current.nodes).toHaveLength(4))
    const [, logic, , long] = result.current.nodes
    expect(long.data.height).toBeGreaterThan(logic.data.height)
    expect(result.current.edges.map((edge) => edge.id)).toEqual([
      'python-logic',
      'logic-python',
      `${PROPOSAL_ROOT_ID}-long`,
    ])
  })

  it('falls back to a two-column grid when the layout engine fails and reports it', async () => {
    mocks.layout.mockRejectedValue(new Error('layout failed'))
    const emptyRelations: PlanningSkillRelation[] = []
    const { result } = renderHook(() =>
      useProposalSkillGraph('Título', skills, emptyRelations),
    )

    await waitFor(() => expect(result.current.isLayoutError).toBe(true))
    const [root, first, second, third] = result.current.nodes
    expect(root.position).toEqual({ x: 0, y: 0 })
    expect(first.position.x).toBe(0)
    expect(first.position.y).toBeGreaterThan(root.data.height)
    expect(second.position).toEqual({ x: 408, y: first.position.y })
    expect(third.position.x).toBe(0)
    expect(third.position.y).toBeGreaterThan(first.position.y)
  })

  it('clamps the zoom between the configured bounds and forwards it to the flow', async () => {
    const flow = {
      zoomTo: vi.fn(async () => true),
      setViewport: vi.fn(),
      getNodes: () => [],
    }
    const emptyRelations: PlanningSkillRelation[] = []
    const { result } = renderHook(() =>
      useProposalSkillGraph('Título', skills, emptyRelations),
    )
    await waitFor(() => expect(result.current.nodes).toHaveLength(4))

    act(() => {
      result.current.handleInit(
        flow as unknown as ReactFlowInstance<ProposalFlowNodeType>,
      )
    })
    expect(result.current.zoom).toBe(1)
    expect(result.current.canZoomIn).toBe(true)
    expect(result.current.canZoomOut).toBe(true)
    act(() => result.current.handleZoomChange(1.9))
    act(() => result.current.handleZoomIn())
    expect(result.current.zoom).toBe(2)
    expect(result.current.canZoomIn).toBe(false)
    expect(flow.zoomTo).toHaveBeenLastCalledWith(2)
    act(() => result.current.handleZoomChange(0.3))
    act(() => result.current.handleZoomOut())
    expect(result.current.zoom).toBe(0.25)
    expect(result.current.canZoomOut).toBe(false)
    expect(flow.zoomTo).toHaveBeenLastCalledWith(0.25)
    act(() => result.current.handleRestore())
    expect(flow.setViewport).not.toHaveBeenCalled()
  })
})
