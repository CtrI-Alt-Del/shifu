import type { Edge, ReactFlowInstance } from '@xyflow/react'
import { useEffect, useMemo, useRef, useState } from 'react'

import type { LearnerMemory } from '@/core/intelligence/learner-memory'

import type { MemoryMapHubType } from './memory-map-hub'
import type { MemoryMapNodeType } from './memory-map-node'

export const MEMORY_MAP_MIN_ZOOM = 0.25
export const MEMORY_MAP_MAX_ZOOM = 2
export const MEMORY_MAP_ZOOM_STEP = 0.2
export const MEMORY_MAP_HUB_ID = 'memory-map-hub'
export const MEMORY_MAP_DESKTOP_QUERY = '(min-width: 1024px)'

const MIN_RADIUS = 170
const NODE_GAP = 8
const FIT_OPTIONS = { maxZoom: 1, padding: 0.15 }
// Links are decoration: the List view and the node names carry the information.
const DECORATIVE_EDGE = {
  ariaRole: 'presentation',
  domAttributes: { 'aria-hidden': true },
} as const
const HUB_SIZE = 80
// The node box is the touch target (the visible circle is smaller); the canvas can be
// zoomed out (about 0.68 at 390 px), so it is much larger than the 44 px minimum.
const NODE_SIZE = 80

export type MemoryMapFlowNode = MemoryMapHubType | MemoryMapNodeType

export type UseMemoryMapInput = {
  memories: LearnerMemory[]
  selectedMemoryId: string | null
  onSelectMemory: (memoryId: string) => void
}

export function useMemoryMap({
  memories,
  selectedMemoryId,
  onSelectMemory,
}: UseMemoryMapInput) {
  const [zoom, setZoom] = useState(1)
  const [isDesktop, setIsDesktop] = useState(false)
  const instanceRef = useRef<ReactFlowInstance<MemoryMapFlowNode> | null>(null)
  const containerRef = useRef<HTMLElement | null>(null)
  const onSelectMemoryRef = useRef(onSelectMemory)
  onSelectMemoryRef.current = onSelectMemory

  useEffect(function trackDesktopViewport() {
    const mediaQuery = window.matchMedia?.(MEMORY_MAP_DESKTOP_QUERY)
    if (!mediaQuery) return
    function handleChange(event: MediaQueryListEvent) {
      setIsDesktop(event.matches)
    }
    setIsDesktop(mediaQuery.matches)
    mediaQuery.addEventListener?.('change', handleChange)
    return () => mediaQuery.removeEventListener?.('change', handleChange)
  }, [])

  const nodes = useMemo<MemoryMapFlowNode[]>(() => {
    const total = memories.length
    // Keep neighbouring nodes apart when there are many memories.
    const radius = Math.max(MIN_RADIUS, (total * (NODE_SIZE + NODE_GAP)) / (2 * Math.PI))
    return [
      {
        id: MEMORY_MAP_HUB_ID,
        type: 'memoryHub',
        position: { x: -HUB_SIZE / 2, y: -HUB_SIZE / 2 },
        data: { label: 'Suas memórias' },
        draggable: false,
        selectable: false,
      },
      ...memories.map((memory, index): MemoryMapNodeType => {
        const angle = (2 * Math.PI * index) / total - Math.PI / 2
        return {
          id: memory.id,
          type: 'memoryNode',
          position: {
            x: radius * Math.cos(angle) - NODE_SIZE / 2,
            y: radius * Math.sin(angle) - NODE_SIZE / 2,
          },
          data: {
            memory,
            isSelected: memory.id === selectedMemoryId,
            onSelect: (memoryId) => onSelectMemoryRef.current(memoryId),
          },
          draggable: false,
          selectable: false,
        }
      }),
    ]
  }, [memories, selectedMemoryId])

  const edges = useMemo<Edge[]>(() => {
    const hubEdges = memories.map(
      (memory): Edge => ({
        id: `hub-${memory.id}`,
        source: MEMORY_MAP_HUB_ID,
        target: memory.id,
        type: 'straight',
        ...DECORATIVE_EDGE,
        style: {
          stroke: 'var(--selo-text)',
          strokeOpacity: memory.id === selectedMemoryId ? 1 : 0.5,
          strokeWidth: memory.id === selectedMemoryId ? 2 : 1,
        },
      }),
    )
    if (!isDesktop) return hubEdges

    const conceptEdges: Edge[] = []
    memories.forEach((memory, index) => {
      const keys = new Set(memory.concepts.map((concept) => concept.key))
      for (const other of memories.slice(index + 1)) {
        if (!other.concepts.some((concept) => keys.has(concept.key))) continue
        conceptEdges.push({
          id: `concept-${memory.id}-${other.id}`,
          source: memory.id,
          target: other.id,
          type: 'straight',
          ...DECORATIVE_EDGE,
          style: {
            stroke: 'var(--jade-solid)',
            strokeDasharray: '4 4',
            strokeOpacity: 0.7,
          },
        })
      }
    })
    return [...hubEdges, ...conceptEdges]
  }, [isDesktop, memories, selectedMemoryId])

  useEffect(
    function refitOnLayoutChange() {
      const instance = instanceRef.current
      const container = containerRef.current
      if (!instance || !container || nodes.length === 0) return
      const observer =
        typeof ResizeObserver === 'undefined'
          ? null
          : new ResizeObserver(() => void instance.fitView(FIT_OPTIONS))
      observer?.observe(container)
      void instance.fitView(FIT_OPTIONS)
      return () => observer?.disconnect()
    },
    [nodes],
  )

  function fitMap() {
    void instanceRef.current?.fitView(FIT_OPTIONS)
  }

  function handleInit(instance: ReactFlowInstance<MemoryMapFlowNode>) {
    instanceRef.current = instance
    fitMap()
  }

  function handleZoomIn() {
    const next = roundZoom(Math.min(MEMORY_MAP_MAX_ZOOM, zoom + MEMORY_MAP_ZOOM_STEP))
    void instanceRef.current?.zoomTo(next)
    setZoom(next)
  }

  function handleZoomOut() {
    const next = roundZoom(Math.max(MEMORY_MAP_MIN_ZOOM, zoom - MEMORY_MAP_ZOOM_STEP))
    void instanceRef.current?.zoomTo(next)
    setZoom(next)
  }

  function handleZoomChange(value: number) {
    setZoom(roundZoom(value))
  }

  function roundZoom(value: number) {
    return Math.round(value * 100) / 100
  }

  return {
    nodes,
    edges,
    zoom,
    containerRef,
    canZoomIn: zoom < MEMORY_MAP_MAX_ZOOM,
    canZoomOut: zoom > MEMORY_MAP_MIN_ZOOM,
    fitMap,
    handleInit,
    handleZoomIn,
    handleZoomOut,
    handleZoomChange,
  }
}
