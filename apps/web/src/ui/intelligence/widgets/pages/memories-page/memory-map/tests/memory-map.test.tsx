import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createRef } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { LearnerMemoryFaker } from '@/core/intelligence/fakers/learner-memory-faker'
import type { LearnerMemory } from '@/core/intelligence/learner-memory'

import { MemoryMap } from '..'
import {
  MEMORY_MAP_HUB_ID,
  type MemoryMapFlowNode,
  useMemoryMap,
} from '../use-memory-map'

const mocks = vi.hoisted(() => ({
  reactFlowProps: vi.fn(),
}))

vi.mock('@xyflow/react', () => ({
  Background: () => null,
  Handle: () => null,
  Position: { Top: 'top' },
  ReactFlow: (props: {
    nodes: { id: string; type: string; data: unknown }[]
    nodeTypes: Record<
      string,
      (nodeProps: { id: string; data: unknown }) => React.ReactNode
    >
  }) => {
    mocks.reactFlowProps(props)
    return (
      <div data-testid='flow'>
        {props.nodes.map((node) => {
          const NodeComponent = props.nodeTypes[node.type]
          return NodeComponent ? (
            <NodeComponent data={node.data} id={node.id} key={node.id} />
          ) : null
        })}
      </div>
    )
  },
}))
vi.mock('../use-memory-map', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../use-memory-map')>()),
  useMemoryMap: vi.fn(),
}))

const useMemoryMapMock = vi.mocked(useMemoryMap)
const onSelectMemoryMock = vi.fn()
const handleZoomInMock = vi.fn()
const handleZoomOutMock = vi.fn()
const handleZoomChangeMock = vi.fn()
const handleInitMock = vi.fn()

const memories: LearnerMemory[] = [
  LearnerMemoryFaker.fake({
    id: '01J7T8AC91Z5K8M4JQ8C2D6F01',
    category: 'explanation_preference',
    content: 'Prefiro exemplos curtos em JavaScript.',
  }),
  LearnerMemoryFaker.fake({
    id: '01J7T8AC91Z5K8M4JQ8C2D6F02',
    category: 'recurring_difficulty',
    content: 'Confundo exibir e retornar valores.',
  }),
]

function mockMap(selectedMemoryId: string | null, overrides = {}) {
  const nodes: MemoryMapFlowNode[] = [
    {
      id: MEMORY_MAP_HUB_ID,
      type: 'memoryHub',
      position: { x: 0, y: 0 },
      data: { label: 'Suas memórias' },
    },
    ...memories.map((memory, index) => ({
      id: memory.id,
      type: 'memoryNode' as const,
      position: { x: index * 100, y: 0 },
      data: {
        memory,
        isSelected: memory.id === selectedMemoryId,
        onSelect: onSelectMemoryMock,
      },
    })),
  ]
  useMemoryMapMock.mockReturnValue({
    nodes,
    edges: [],
    zoom: 1,
    containerRef: createRef<HTMLElement>(),
    canZoomIn: true,
    canZoomOut: true,
    fitMap: vi.fn(),
    handleInit: handleInitMock,
    handleZoomIn: handleZoomInMock,
    handleZoomOut: handleZoomOutMock,
    handleZoomChange: handleZoomChangeMock,
    ...overrides,
  })
}

describe('MemoryMap', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)

  it('renders the titled map with the hub, the count and one node per memory', () => {
    mockMap(null)
    render(
      <MemoryMap memories={memories} onSelectMemory={vi.fn()} selectedMemoryId={null} />,
    )

    expect(screen.getByRole('region', { name: 'Mapa de memórias' })).toBeVisible()
    expect(
      screen.getByText('2 memórias · selecione um nó para ver os detalhes'),
    ).toBeVisible()
    expect(screen.getByText('Suas memórias')).toBeVisible()
    expect(
      screen.getByRole('button', {
        name: 'Preferência de explicação: Prefiro exemplos curtos em JavaScript.',
      }),
    ).toHaveAttribute('aria-pressed', 'false')
    expect(
      screen.getByRole('button', {
        name: 'Dificuldades recorrentes: Confundo exibir e retornar valores.',
      }),
    ).toBeVisible()
  })

  it('uses the singular count for one memory', () => {
    mockMap(null)
    render(
      <MemoryMap
        memories={[memories[0] as LearnerMemory]}
        onSelectMemory={vi.fn()}
        selectedMemoryId={null}
      />,
    )

    expect(
      screen.getByText('1 memória · selecione um nó para ver os detalhes'),
    ).toBeVisible()
  })

  it('marks the selected node as pressed', () => {
    mockMap(memories[1]?.id ?? null)
    render(
      <MemoryMap
        memories={memories}
        onSelectMemory={vi.fn()}
        selectedMemoryId={memories[1]?.id ?? null}
      />,
    )

    expect(
      screen.getByRole('button', {
        name: 'Dificuldades recorrentes: Confundo exibir e retornar valores.',
      }),
    ).toHaveAttribute('aria-pressed', 'true')
  })

  it('selects a node with a click, Enter and Space from the keyboard', async () => {
    const user = userEvent.setup()
    mockMap(null)
    render(
      <MemoryMap memories={memories} onSelectMemory={vi.fn()} selectedMemoryId={null} />,
    )
    const node = screen.getByRole('button', {
      name: 'Preferência de explicação: Prefiro exemplos curtos em JavaScript.',
    })

    await user.click(node)
    node.focus()
    await user.keyboard('{Enter}')
    await user.keyboard(' ')

    expect(node).toHaveFocus()
    expect(onSelectMemoryMock).toHaveBeenCalledTimes(3)
    expect(onSelectMemoryMock).toHaveBeenCalledWith(memories[0]?.id)
  })

  it('reaches each node with a single Tab stop', async () => {
    const user = userEvent.setup()
    mockMap(null)
    render(
      <MemoryMap memories={memories} onSelectMemory={vi.fn()} selectedMemoryId={null} />,
    )

    // Two zoom controls come first, then one stop per node.
    for (let stop = 0; stop < 4; stop += 1) await user.tab()

    expect(
      screen.getByRole('button', {
        name: 'Dificuldades recorrentes: Confundo exibir e retornar valores.',
      }),
    ).toHaveFocus()
  })

  it('offers bounded zoom controls that delegate to the hook', async () => {
    const user = userEvent.setup()
    mockMap(null)
    render(
      <MemoryMap memories={memories} onSelectMemory={vi.fn()} selectedMemoryId={null} />,
    )

    expect(screen.getByRole('group', { name: 'Controles do mapa' })).toBeVisible()
    expect(screen.getByLabelText('Zoom do mapa: 100%')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Ampliar mapa' }))
    await user.click(screen.getByRole('button', { name: 'Reduzir mapa' }))

    expect(handleZoomInMock).toHaveBeenCalledOnce()
    expect(handleZoomOutMock).toHaveBeenCalledOnce()
  })

  it('disables a zoom control at its limit', () => {
    mockMap(null, { zoom: 2, canZoomIn: false })
    render(
      <MemoryMap memories={memories} onSelectMemory={vi.fn()} selectedMemoryId={null} />,
    )

    expect(screen.getByRole('button', { name: 'Ampliar mapa' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reduzir mapa' })).toBeEnabled()
    expect(screen.getByLabelText('Zoom do mapa: 200%')).toBeVisible()
  })

  it('wires viewport changes and initialization to its hook and keeps the canvas non-draggable', () => {
    mockMap(null)
    render(
      <MemoryMap memories={memories} onSelectMemory={vi.fn()} selectedMemoryId={null} />,
    )
    const props = mocks.reactFlowProps.mock.calls[0]?.[0] as {
      onInit: unknown
      onMove: (event: null, viewport: { zoom: number }) => void
      nodesDraggable: boolean
      nodesFocusable: boolean
    }

    props.onMove(null, { zoom: 1.4 })

    expect(props.onInit).toBe(handleInitMock)
    expect(handleZoomChangeMock).toHaveBeenCalledWith(1.4)
    expect(props.nodesDraggable).toBe(false)
    expect(props.nodesFocusable).toBe(false)
  })
})
