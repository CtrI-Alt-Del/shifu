import type { ReactFlowInstance } from '@xyflow/react'
import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { LearnerMemoryFaker } from '@/core/intelligence/fakers/learner-memory-faker'
import type { LearnerMemory } from '@/core/intelligence/learner-memory'

import {
  MEMORY_MAP_HUB_ID,
  MEMORY_MAP_MAX_ZOOM,
  MEMORY_MAP_MIN_ZOOM,
  type MemoryMapFlowNode,
  useMemoryMap,
} from '../use-memory-map'
import type { MemoryMapNodeType } from '../memory-map-node'

const onSelectMemoryMock = vi.fn()
const zoomToMock = vi.fn()
const fitViewMock = vi.fn()

const memories: LearnerMemory[] = [
  LearnerMemoryFaker.fake({
    id: '01J7T8AC91Z5K8M4JQ8C2D6F01',
    concepts: [{ key: 'funcao', label: 'Funções' }],
  }),
  LearnerMemoryFaker.fake({
    id: '01J7T8AC91Z5K8M4JQ8C2D6F02',
    concepts: [{ key: 'funcao', label: 'Funções' }],
  }),
  LearnerMemoryFaker.fake({
    id: '01J7T8AC91Z5K8M4JQ8C2D6F03',
    concepts: [{ key: 'laco', label: 'Laços' }],
  }),
  LearnerMemoryFaker.fake({
    id: '01J7T8AC91Z5K8M4JQ8C2D6F04',
    concepts: [],
  }),
]

function stubViewport(matches: boolean) {
  const listeners = new Set<(event: MediaQueryListEvent) => void>()
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({
      matches,
      addEventListener: (_type: string, listener: (event: MediaQueryListEvent) => void) =>
        listeners.add(listener),
      removeEventListener: (
        _type: string,
        listener: (event: MediaQueryListEvent) => void,
      ) => listeners.delete(listener),
    })),
  )
  return {
    change(nextMatches: boolean) {
      for (const listener of listeners)
        listener({ matches: nextMatches } as MediaQueryListEvent)
    },
  }
}

function renderMap(
  items: LearnerMemory[] = memories,
  selectedMemoryId: string | null = null,
) {
  return renderHook(
    (props: { memories: LearnerMemory[]; selectedMemoryId: string | null }) =>
      useMemoryMap({ ...props, onSelectMemory: onSelectMemoryMock }),
    { initialProps: { memories: items, selectedMemoryId } },
  )
}

function memoryNodes(nodes: MemoryMapFlowNode[]) {
  return nodes.filter((node): node is MemoryMapNodeType => node.type === 'memoryNode')
}

describe('useMemoryMap', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    stubViewport(false)
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('places the hub at the centre and the memories on a circle in list order', () => {
    const { result } = renderMap()
    const [hub, ...others] = result.current.nodes

    expect(hub?.id).toBe(MEMORY_MAP_HUB_ID)
    expect(hub?.type).toBe('memoryHub')
    expect(others.map((node) => node.id)).toEqual(memories.map((memory) => memory.id))
    const centres = others.map((node) => ({
      x: node.position.x + 40,
      y: node.position.y + 40,
    }))
    const radius = Math.hypot(centres[0]?.x ?? 0, centres[0]?.y ?? 0)
    // First memory at the top, then clockwise quarter turns for four memories.
    expect(centres[0]?.x).toBeCloseTo(0)
    expect(centres[0]?.y).toBeCloseTo(-radius)
    expect(centres[1]?.x).toBeCloseTo(radius)
    expect(centres[1]?.y).toBeCloseTo(0)
    expect(centres[2]?.x).toBeCloseTo(0)
    expect(centres[2]?.y).toBeCloseTo(radius)
    expect(centres[3]?.x).toBeCloseTo(-radius)
    expect(centres[3]?.y).toBeCloseTo(0)
  })

  it('computes the same layout for the same input', () => {
    const first = renderMap().result.current.nodes.map((node) => node.position)
    const second = renderMap().result.current.nodes.map((node) => node.position)

    expect(second).toEqual(first)
  })

  it('grows the circle so many memories do not overlap', () => {
    const many = LearnerMemoryFaker.fakeMany(60)
    const { result } = renderMap(many)
    const [first, second] = memoryNodes(result.current.nodes)
    const distance = Math.hypot(
      (first?.position.x ?? 0) - (second?.position.x ?? 0),
      (first?.position.y ?? 0) - (second?.position.y ?? 0),
    )

    expect(distance).toBeGreaterThanOrEqual(80)
  })

  it('flags the selected memory and reports a node selection', () => {
    const { result } = renderMap(memories, memories[1]?.id ?? null)
    const nodes = memoryNodes(result.current.nodes)

    expect(nodes.map((node) => node.data.isSelected)).toEqual([false, true, false, false])
    nodes[0]?.data.onSelect(memories[0]?.id ?? '')

    expect(onSelectMemoryMock).toHaveBeenCalledWith(memories[0]?.id)
  })

  it('links every memory to the hub and adds no concept link on mobile', () => {
    const { result } = renderMap()

    expect(result.current.edges.map((edge) => edge.id)).toEqual(
      memories.map((memory) => `hub-${memory.id}`),
    )
    expect(result.current.edges.every((edge) => edge.source === MEMORY_MAP_HUB_ID)).toBe(
      true,
    )
  })

  it('adds links between memories sharing a concept key on desktop only', () => {
    stubViewport(true)
    const { result } = renderMap()

    const conceptEdges = result.current.edges.filter((edge) =>
      edge.id.startsWith('concept-'),
    )
    expect(
      result.current.edges.filter((edge) => edge.id.startsWith('hub-')),
    ).toHaveLength(4)
    expect(conceptEdges).toHaveLength(1)
    expect(conceptEdges[0]).toMatchObject({
      source: memories[0]?.id,
      target: memories[1]?.id,
    })
  })

  it('follows the viewport when it crosses the desktop breakpoint', () => {
    const viewport = stubViewport(false)
    const { result } = renderMap()
    expect(result.current.edges.some((edge) => edge.id.startsWith('concept-'))).toBe(
      false,
    )

    act(() => viewport.change(true))
    expect(result.current.edges.some((edge) => edge.id.startsWith('concept-'))).toBe(true)

    act(() => viewport.change(false))
    expect(result.current.edges.some((edge) => edge.id.startsWith('concept-'))).toBe(
      false,
    )
  })

  it('works without matchMedia support', () => {
    vi.unstubAllGlobals()
    const { result } = renderMap()

    expect(result.current.edges).toHaveLength(memories.length)
  })

  it('highlights the edge of the selected memory', () => {
    const { result } = renderMap(memories, memories[2]?.id ?? null)
    const selectedEdge = result.current.edges.find(
      (edge) => edge.id === `hub-${memories[2]?.id}`,
    )
    const otherEdge = result.current.edges.find(
      (edge) => edge.id === `hub-${memories[0]?.id}`,
    )

    expect(selectedEdge?.style?.strokeOpacity).toBe(1)
    expect(otherEdge?.style?.strokeOpacity).toBe(0.5)
  })

  it('zooms in and out in steps and stops at the bounds', () => {
    const { result } = renderMap()
    act(() =>
      result.current.handleInit({
        zoomTo: zoomToMock,
        fitView: fitViewMock,
      } as unknown as ReactFlowInstance<MemoryMapFlowNode>),
    )

    expect(fitViewMock).toHaveBeenCalledOnce()
    expect(result.current.canZoomIn).toBe(true)
    act(() => result.current.handleZoomIn())
    expect(result.current.zoom).toBe(1.2)
    expect(zoomToMock).toHaveBeenLastCalledWith(1.2)

    for (let step = 0; step < 10; step += 1) act(() => result.current.handleZoomIn())
    expect(result.current.zoom).toBe(MEMORY_MAP_MAX_ZOOM)
    expect(result.current.canZoomIn).toBe(false)

    for (let step = 0; step < 20; step += 1) act(() => result.current.handleZoomOut())
    expect(result.current.zoom).toBe(MEMORY_MAP_MIN_ZOOM)
    expect(result.current.canZoomOut).toBe(false)
  })

  it('zooms without an initialized canvas and follows viewport zoom changes', () => {
    const { result } = renderMap()

    act(() => result.current.handleZoomOut())
    expect(result.current.zoom).toBe(0.8)
    act(() => result.current.handleZoomChange(1.2345))

    expect(result.current.zoom).toBe(1.23)
    expect(zoomToMock).not.toHaveBeenCalled()
  })

  it('refits the canvas when the layout or its container size changes', () => {
    const resizeCallbacks: (() => void)[] = []
    const disconnectMock = vi.fn()
    vi.stubGlobal(
      'ResizeObserver',
      class {
        constructor(callback: () => void) {
          resizeCallbacks.push(callback)
        }
        observe() {}
        disconnect() {
          disconnectMock()
        }
      },
    )
    const { result, rerender, unmount } = renderMap()
    act(() => {
      result.current.containerRef.current = document.createElement('section')
      result.current.handleInit({
        zoomTo: zoomToMock,
        fitView: fitViewMock,
      } as unknown as ReactFlowInstance<MemoryMapFlowNode>)
    })
    fitViewMock.mockClear()

    rerender({ memories: memories.slice(0, 2), selectedMemoryId: null })
    expect(fitViewMock).toHaveBeenCalledOnce()
    resizeCallbacks.at(-1)?.()
    expect(fitViewMock).toHaveBeenCalledTimes(2)

    unmount()
    expect(disconnectMock).toHaveBeenCalled()
  })

  it('keeps the viewport when a memory is selected or the same list is read again', () => {
    const { result, rerender } = renderMap()
    act(() => {
      result.current.containerRef.current = document.createElement('section')
      result.current.handleInit({
        zoomTo: zoomToMock,
        fitView: fitViewMock,
      } as unknown as ReactFlowInstance<MemoryMapFlowNode>)
    })
    rerender({ memories, selectedMemoryId: null })
    fitViewMock.mockClear()

    rerender({ memories, selectedMemoryId: memories[1].id })
    rerender({
      memories: memories.map((memory) => ({ ...memory })),
      selectedMemoryId: null,
    })

    expect(fitViewMock).not.toHaveBeenCalled()
  })

  it('fits the canvas on demand', () => {
    const { result } = renderMap()
    act(() =>
      result.current.handleInit({
        zoomTo: zoomToMock,
        fitView: fitViewMock,
      } as unknown as ReactFlowInstance<MemoryMapFlowNode>),
    )
    fitViewMock.mockClear()

    act(() => result.current.fitMap())

    expect(fitViewMock).toHaveBeenCalledOnce()
  })
})
