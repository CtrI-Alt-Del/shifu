import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ELK from 'elkjs/lib/elk.bundled.js'
import type { Edge } from '@xyflow/react'

import type { GoalSkillDetail, GoalSkillRelation } from '@/core/learning/goal-detail'

import type { GoalFlowNodeType, GoalGraphNodeType } from './goal-graph-node'

const MIN_ZOOM = 0.25
const MAX_ZOOM = 2
const ZOOM_STEP = 0.2
const NODE_WIDTH = 352
const NODE_HEIGHT = 118
const ROOT_ID = 'goal-root'

export function useGoalSkillGraph(
  goalId: string,
  skills: readonly GoalSkillDetail[],
  relations: readonly GoalSkillRelation[],
  title: string,
  onRemoveSkill: (skill: GoalSkillDetail, trigger: HTMLButtonElement) => void,
) {
  const onRemoveSkillRef = useRef(onRemoveSkill)
  onRemoveSkillRef.current = onRemoveSkill
  const [nodes, setNodes] = useState<GoalFlowNodeType[]>([])
  const [isLayoutError, setIsLayoutError] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null)
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null)
  const nodeBySkillId = useMemo(
    () => new Map(skills.map((skill) => [skill.skillId, skill])),
    [skills],
  )
  const layoutEdges = useMemo<Edge[]>(() => {
    const prerequisiteEdges = relations
      .filter(
        (relation) =>
          nodeBySkillId.has(relation.foundationSkillId) &&
          nodeBySkillId.has(relation.skillId),
      )
      .map((relation) => ({
        id: `${relation.foundationSkillId}-${relation.skillId}`,
        source: relation.foundationSkillId,
        target: relation.skillId,
        type: 'smoothstep',
      }))
    const dependentIds = new Set(prerequisiteEdges.map((edge) => edge.target))
    return [
      ...prerequisiteEdges,
      ...skills
        .filter((skill) => !dependentIds.has(skill.skillId))
        .map((skill) => ({
          id: `${ROOT_ID}-${skill.skillId}`,
          source: ROOT_ID,
          target: skill.skillId,
          type: 'smoothstep',
        })),
    ]
  }, [nodeBySkillId, relations, skills])
  const activeNodeId = hoveredNodeId ?? focusedNodeId
  const highlightedEdgeIds = useMemo(() => {
    const pathEdges = new Set<string>()
    if (!activeNodeId) return pathEdges

    const pendingNodeIds = [activeNodeId]
    const visitedNodeIds = new Set<string>()
    while (pendingNodeIds.length > 0) {
      const nodeId = pendingNodeIds.pop()
      if (!nodeId || visitedNodeIds.has(nodeId)) continue
      visitedNodeIds.add(nodeId)
      for (const edge of layoutEdges) {
        if (edge.target !== nodeId) continue
        pathEdges.add(edge.id)
        pendingNodeIds.push(edge.source)
      }
    }
    return pathEdges
  }, [activeNodeId, layoutEdges])
  const edges = useMemo(
    () =>
      layoutEdges.map((edge) =>
        highlightedEdgeIds.has(edge.id)
          ? {
              ...edge,
              className: 'goal-graph-highlighted-edge',
              style: {
                stroke: 'var(--selo-text)',
                strokeWidth: 2.5,
                strokeDasharray: '6 4',
              },
            }
          : edge,
      ),
    [highlightedEdgeIds, layoutEdges],
  )

  useEffect(() => {
    let isCurrent = true
    const elk = new ELK()
    const graph = {
      id: 'goal-skill-graph',
      layoutOptions: {
        'elk.algorithm': 'layered',
        'elk.direction': 'DOWN',
        'elk.layered.spacing.nodeNodeBetweenLayers': '48',
        'elk.spacing.nodeNode': '40',
      },
      children: [
        { id: ROOT_ID, width: 388, height: 82 },
        ...skills.map((skill) => ({
          id: skill.skillId,
          width: NODE_WIDTH,
          height: NODE_HEIGHT,
        })),
      ],
      edges: layoutEdges.map((edge) => ({
        id: edge.id,
        sources: [edge.source],
        targets: [edge.target],
      })),
    }
    void elk
      .layout(graph)
      .then((layout) => {
        if (!isCurrent) return
        const root = layout.children?.find((child) => child.id === ROOT_ID)
        setNodes([
          {
            id: ROOT_ID,
            type: 'goalRoot',
            position: { x: root?.x ?? 0, y: root?.y ?? 0 },
            data: { title },
          },
          ...skills.map((skill): GoalGraphNodeType => {
            const child = layout.children?.find(
              (candidate) => candidate.id === skill.skillId,
            )
            return {
              id: skill.skillId,
              type: 'goalSkill',
              position: { x: child?.x ?? 0, y: child?.y ?? 0 },
              data: {
                goalId,
                skill,
                onRemove: (trigger) => onRemoveSkillRef.current(skill, trigger),
              },
            }
          }),
        ])
        setIsLayoutError(false)
      })
      .catch(() => {
        if (!isCurrent) return
        setNodes([
          {
            id: ROOT_ID,
            type: 'goalRoot',
            position: { x: 150, y: 0 },
            data: { title },
          },
          ...skills.map(
            (skill, index): GoalGraphNodeType => ({
              id: skill.skillId,
              type: 'goalSkill',
              position: {
                x: (index % 3) * (NODE_WIDTH + 40),
                y: 180 + Math.floor(index / 3) * 200,
              },
              data: {
                goalId,
                skill,
                onRemove: (trigger) => onRemoveSkillRef.current(skill, trigger),
              },
            }),
          ),
        ])
        setIsLayoutError(true)
      })
    return () => {
      isCurrent = false
    }
  }, [goalId, layoutEdges, skills, title])

  const handleZoomIn = useCallback(
    () => setZoom((current) => Math.min(MAX_ZOOM, current + ZOOM_STEP)),
    [],
  )
  const handleZoomOut = useCallback(
    () => setZoom((current) => Math.max(MIN_ZOOM, current - ZOOM_STEP)),
    [],
  )
  const handleZoomChange = useCallback((value: number) => setZoom(value), [])
  const handleNodeHover = useCallback((nodeId: string | null) => {
    setHoveredNodeId(nodeId)
  }, [])
  const handleNodeFocus = useCallback((nodeId: string | null) => {
    setFocusedNodeId(nodeId)
  }, [])

  return {
    nodes,
    edges,
    zoom,
    isLayoutError,
    canZoomIn: zoom < MAX_ZOOM,
    canZoomOut: zoom > MIN_ZOOM,
    handleZoomIn,
    handleZoomOut,
    handleZoomChange,
    handleNodeHover,
    handleNodeFocus,
  }
}
