import { useEffect, useMemo, useRef, useState } from 'react'
import ELK from 'elkjs/lib/elk.bundled.js'
import type { Edge, NodeChange, ReactFlowInstance } from '@xyflow/react'

import type {
  PlanningProposalSkill,
  PlanningSkillRelation,
} from '@/core/intelligence/planning-session'

import type { ProposalFlowNodeType } from './proposal-graph-node'

export const PROPOSAL_GRAPH_MIN_ZOOM = 0.25
export const PROPOSAL_GRAPH_MAX_ZOOM = 2
export const PROPOSAL_GRAPH_ZOOM_STEP = 0.2
export const PROPOSAL_ROOT_ID = 'proposal-root'

/** Below this container width the nodes share each layer, as in the mobile frame. */
export const COMPACT_GRAPH_MAX_WIDTH = 800
const WIDE_NODE_WIDTH = 360
const WIDE_ROOT_WIDTH = 400
const WIDE_NODE_GAP = 48
const WIDE_LAYER_GAP = 48
const WIDE_INSET = 24
const COMPACT_MIN_NODE_WIDTH = 140
const COMPACT_NODE_GAP = 16
const COMPACT_LAYER_GAP = 32
const COMPACT_INSET = 16

type GraphGeometry = {
  isCompact: boolean
  inset: number
  nodeGap: number
  layerGap: number
  rootWidth: number
  widthOf: (depth: number) => number
}

export function useProposalSkillGraph(
  title: string,
  skills: PlanningProposalSkill[],
  relations: PlanningSkillRelation[],
) {
  const graphRef = useRef<HTMLElement>(null)
  const [instance, setInstance] =
    useState<ReactFlowInstance<ProposalFlowNodeType> | null>(null)
  const [containerWidth, setContainerWidth] = useState(0)
  const [measureTick, setMeasureTick] = useState(0)
  const [nodes, setNodes] = useState<ProposalFlowNodeType[]>([])
  const [isLayoutError, setIsLayoutError] = useState(false)
  const [zoom, setZoom] = useState(1)
  const edges = useMemo<Edge[]>(() => {
    const skillIds = new Set(skills.map((skill) => skill.skillId))
    // Only relations between proposed Skills are drawn; nothing is inferred.
    const relationEdges = relations
      .filter(
        (relation) =>
          skillIds.has(relation.foundationSkillId) &&
          skillIds.has(relation.skillId) &&
          relation.foundationSkillId !== relation.skillId,
      )
      .map((relation) => ({
        id: `${relation.foundationSkillId}-${relation.skillId}`,
        source: relation.foundationSkillId,
        target: relation.skillId,
        type: 'smoothstep',
      }))
    const dependentIds = new Set(relationEdges.map((edge) => edge.target))
    return [
      ...relationEdges,
      ...skills
        .filter((skill) => !dependentIds.has(skill.skillId))
        .map((skill) => ({
          id: `${PROPOSAL_ROOT_ID}-${skill.skillId}`,
          source: PROPOSAL_ROOT_ID,
          target: skill.skillId,
          type: 'smoothstep',
        })),
    ]
  }, [relations, skills])
  // An unmeasured container (first paint) lays out as the wide frame.
  const layoutWidth =
    containerWidth > 0 && containerWidth < COMPACT_GRAPH_MAX_WIDTH ? containerWidth : 0
  const isCompact = layoutWidth > 0

  useEffect(() => {
    const element = graphRef.current
    if (!element) return

    const measure = () => setContainerWidth(element.clientWidth)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    let isCurrent = true
    const geometry = geometryFor(layoutWidth, skills, edges)
    const sizedNodes = buildNodes(title, skills, edges, geometry)
    const elk = new ELK()
    const graph = {
      id: 'proposal-skill-graph',
      layoutOptions: {
        'elk.algorithm': 'layered',
        'elk.direction': 'DOWN',
        'elk.layered.spacing.nodeNodeBetweenLayers': String(geometry.layerGap),
        'elk.spacing.nodeNode': String(geometry.nodeGap),
        // Skills keep the order proposed by the backend inside each layer.
        'elk.layered.considerModelOrder.strategy': 'NODES_AND_EDGES',
        'elk.layered.crossingMinimization.forceNodeModelOrder': 'true',
      },
      children: sizedNodes.map((node) => ({
        id: node.id,
        width: node.data.width,
        height: node.data.height,
      })),
      edges: edges.map((edge) => ({
        id: edge.id,
        sources: [edge.source],
        targets: [edge.target],
      })),
    }
    void elk
      .layout(graph)
      .then((layout) => {
        if (!isCurrent) return

        const positions = new Map(
          (layout.children ?? []).map((child) => [
            child.id,
            { x: child.x ?? 0, y: child.y ?? 0 },
          ]),
        )
        setNodes(
          centerLayers(
            placeNodes(sizedNodes, (id) => positions.get(id)),
            depthsOf(skills, edges),
            geometry.nodeGap,
          ),
        )
        setIsLayoutError(false)
      })
      .catch(() => {
        if (!isCurrent) return

        setNodes(placeNodes(sizedNodes, gridPositionFor(sizedNodes, geometry)))
        setIsLayoutError(true)
      })
    return () => {
      isCurrent = false
    }
  }, [edges, layoutWidth, skills, title])

  // biome-ignore lint/correctness/useExhaustiveDependencies: the fit also reruns after the nodes are measured and the container resized.
  useEffect(() => {
    fitToTop()
  }, [instance, nodes, containerWidth, measureTick])

  function fitToTop() {
    const element = graphRef.current
    if (!instance || !element || nodes.length === 0) return

    const measuredNodes = instance.getNodes()
    let minX = Number.POSITIVE_INFINITY
    let minY = Number.POSITIVE_INFINITY
    let maxX = Number.NEGATIVE_INFINITY
    let maxY = Number.NEGATIVE_INFINITY
    for (const node of nodes) {
      const measured = measuredNodes.find(
        (candidate) => candidate.id === node.id,
      )?.measured
      const width = measured?.width ?? node.data.width
      const height = measured?.height ?? node.data.height
      minX = Math.min(minX, node.position.x)
      minY = Math.min(minY, node.position.y)
      maxX = Math.max(maxX, node.position.x + width)
      maxY = Math.max(maxY, node.position.y + height)
    }
    const inset = isCompact ? COMPACT_INSET : WIDE_INSET
    const availableWidth = Math.max(1, element.clientWidth - inset * 2)
    const availableHeight = Math.max(1, element.clientHeight - inset * 2)
    const fitZoom = Math.min(
      1,
      availableWidth / (maxX - minX),
      availableHeight / (maxY - minY),
    )
    const nextZoom = Math.max(PROPOSAL_GRAPH_MIN_ZOOM, fitZoom)
    // The tree hangs from the top inset, centered horizontally, as drawn in the frames.
    void instance.setViewport({
      x: (element.clientWidth - (maxX - minX) * nextZoom) / 2 - minX * nextZoom,
      y: inset - minY * nextZoom,
      zoom: nextZoom,
    })
    setZoom(nextZoom)
  }

  function handleInit(flow: ReactFlowInstance<ProposalFlowNodeType>) {
    setInstance(flow)
  }

  function handleNodesChange(changes: NodeChange<ProposalFlowNodeType>[]) {
    if (changes.some((change) => change.type === 'dimensions')) {
      setMeasureTick((current) => current + 1)
    }
  }

  function handleRestore() {
    fitToTop()
  }

  function handleZoomIn() {
    const next = Math.min(PROPOSAL_GRAPH_MAX_ZOOM, zoom + PROPOSAL_GRAPH_ZOOM_STEP)
    void instance?.zoomTo(next)
    setZoom(next)
  }

  function handleZoomOut() {
    const next = Math.max(PROPOSAL_GRAPH_MIN_ZOOM, zoom - PROPOSAL_GRAPH_ZOOM_STEP)
    void instance?.zoomTo(next)
    setZoom(next)
  }

  function handleZoomChange(value: number) {
    setZoom(value)
  }

  return {
    graphRef,
    nodes,
    edges,
    zoom,
    isLayoutError,
    isReady: instance !== null && nodes.length > 0,
    canZoomIn: zoom < PROPOSAL_GRAPH_MAX_ZOOM,
    canZoomOut: zoom > PROPOSAL_GRAPH_MIN_ZOOM,
    handleInit,
    handleNodesChange,
    handleRestore,
    handleZoomIn,
    handleZoomOut,
    handleZoomChange,
  }
}

function geometryFor(
  layoutWidth: number,
  skills: PlanningProposalSkill[],
  edges: Edge[],
): GraphGeometry {
  if (layoutWidth === 0) {
    return {
      isCompact: false,
      inset: WIDE_INSET,
      nodeGap: WIDE_NODE_GAP,
      layerGap: WIDE_LAYER_GAP,
      rootWidth: WIDE_ROOT_WIDTH,
      widthOf: () => WIDE_NODE_WIDTH,
    }
  }

  const rowWidth = Math.max(COMPACT_MIN_NODE_WIDTH, layoutWidth - COMPACT_INSET * 2)
  const layerCounts = new Map<number, number>()
  for (const depth of depthsOf(skills, edges).values()) {
    layerCounts.set(depth, (layerCounts.get(depth) ?? 0) + 1)
  }
  return {
    isCompact: true,
    inset: COMPACT_INSET,
    nodeGap: COMPACT_NODE_GAP,
    layerGap: COMPACT_LAYER_GAP,
    rootWidth: rowWidth,
    widthOf: (depth) => {
      const count = layerCounts.get(depth) ?? 1
      return Math.max(
        COMPACT_MIN_NODE_WIDTH,
        Math.floor((rowWidth - COMPACT_NODE_GAP * (count - 1)) / count),
      )
    },
  }
}

/** Longest path from the proposal root, following only the drawn relations. */
function depthsOf(skills: PlanningProposalSkill[], edges: Edge[]): Map<string, number> {
  const foundations = new Map<string, string[]>()
  for (const edge of edges) {
    if (edge.source === PROPOSAL_ROOT_ID) continue
    foundations.set(edge.target, [...(foundations.get(edge.target) ?? []), edge.source])
  }
  const depths = new Map<string, number>()
  const visiting = new Set<string>()
  const depthOf = (id: string): number => {
    const known = depths.get(id)
    if (known !== undefined) return known
    if (visiting.has(id)) return 1

    visiting.add(id)
    const depth = 1 + Math.max(0, ...(foundations.get(id) ?? []).map(depthOf))
    visiting.delete(id)
    depths.set(id, depth)
    return depth
  }
  for (const skill of skills) depthOf(skill.skillId)
  return depths
}

function buildNodes(
  title: string,
  skills: PlanningProposalSkill[],
  edges: Edge[],
  geometry: GraphGeometry,
): ProposalFlowNodeType[] {
  const depths = depthsOf(skills, edges)
  return [
    {
      id: PROPOSAL_ROOT_ID,
      type: 'proposalRoot',
      position: { x: 0, y: 0 },
      data: {
        title,
        width: geometry.rootWidth,
        height: estimateRootHeight(title, geometry.rootWidth),
      },
    },
    ...skills.map((skill): ProposalFlowNodeType => {
      const width = geometry.widthOf(depths.get(skill.skillId) ?? 1)
      return {
        id: skill.skillId,
        type: 'proposalSkill',
        position: { x: 0, y: 0 },
        data: {
          skill,
          width,
          height: estimateSkillHeight(skill, width, geometry.isCompact),
          isCompact: geometry.isCompact,
        },
      }
    }),
  ]
}

function placeNodes(
  nodes: ProposalFlowNodeType[],
  positionOf: (id: string) => { x: number; y: number } | undefined,
): ProposalFlowNodeType[] {
  return nodes.map((node) => ({
    ...node,
    position: positionOf(node.id) ?? { x: 0, y: 0 },
  }))
}

/**
 * Every layer is centered on the widest one, as drawn: the engine keeps the vertical
 * spacing and the order inside each layer, the rows are laid out here.
 */
function centerLayers(
  nodes: ProposalFlowNodeType[],
  depths: Map<string, number>,
  nodeGap: number,
): ProposalFlowNodeType[] {
  const layers = new Map<number, ProposalFlowNodeType[]>()
  for (const node of nodes) {
    const depth = node.id === PROPOSAL_ROOT_ID ? 0 : (depths.get(node.id) ?? 1)
    layers.set(depth, [...(layers.get(depth) ?? []), node])
  }
  const widthOf = (layer: ProposalFlowNodeType[]) =>
    layer.reduce((sum, node) => sum + node.data.width, 0) + nodeGap * (layer.length - 1)
  const treeWidth = Math.max(...[...layers.values()].map(widthOf))
  const xOf = new Map<string, number>()
  for (const layer of layers.values()) {
    let x = (treeWidth - widthOf(layer)) / 2
    for (const node of [...layer].sort(
      (left, right) => left.position.x - right.position.x,
    )) {
      xOf.set(node.id, x)
      x += node.data.width + nodeGap
    }
  }
  return nodes.map((node) => ({
    ...node,
    position: { x: xOf.get(node.id) ?? node.position.x, y: node.position.y },
  }))
}

function gridPositionFor(nodes: ProposalFlowNodeType[], geometry: GraphGeometry) {
  const [root, ...skillNodes] = nodes
  const columns = 2
  const rowHeight =
    Math.max(...skillNodes.map((node) => node.data.height), 0) + geometry.nodeGap
  return (id: string) => {
    if (id === PROPOSAL_ROOT_ID) return { x: 0, y: 0 }

    const index = skillNodes.findIndex((node) => node.id === id)
    const node = skillNodes[index]
    if (!node) return undefined

    return {
      x: (index % columns) * (node.data.width + geometry.nodeGap),
      y: root.data.height + geometry.layerGap + Math.floor(index / columns) * rowHeight,
    }
  }
}

/** Greedy word wrap with an average glyph width; only used to size the layout boxes. */
function estimateLines(text: string, width: number, glyphWidth: number): number {
  const capacity = Math.max(1, Math.floor(width / glyphWidth))
  let lines = 1
  let used = 0
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const length = word.length + (used > 0 ? 1 : 0)
    if (used > 0 && used + length > capacity) {
      lines += 1
      used = word.length
    } else {
      used += length
    }
  }
  return lines
}

function estimateSkillHeight(
  skill: PlanningProposalSkill,
  width: number,
  isCompact: boolean,
): number {
  const innerWidth = width - 32
  const nameLines = estimateLines(skill.name, isCompact ? innerWidth : innerWidth - 46, 8)
  const justificationLines = estimateLines(skill.justification, innerWidth, 6.8)
  const header = isCompact ? 34 + 8 + nameLines * 18 : Math.max(34, nameLines * 18)
  return 24 + header + 12 + justificationLines * 19.5
}

function estimateRootHeight(title: string, width: number): number {
  const titleLines = estimateLines(title, width - 32 - 52, 8.5)
  return 28 + Math.max(40, titleLines * 19 + 4 + 15)
}
