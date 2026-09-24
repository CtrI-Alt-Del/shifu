import { useCallback, useEffect, useMemo, useState } from 'react'
import ELK from 'elkjs/lib/elk.bundled.js'
import type { Edge } from '@xyflow/react'

import type { GoalSkillDetail, GoalSkillRelation } from '@/core/learning/goal-detail'

import type { GoalGraphNodeType } from './goal-graph-node'

const MIN_ZOOM = 0.25
const MAX_ZOOM = 2
const ZOOM_STEP = 0.2
const NODE_WIDTH = 256
const NODE_HEIGHT = 150

export function useGoalSkillGraph(
  goalId: string,
  skills: readonly GoalSkillDetail[],
  relations: readonly GoalSkillRelation[],
) {
  const [nodes, setNodes] = useState<GoalGraphNodeType[]>([])
  const [isLayoutError, setIsLayoutError] = useState(false)
  const [zoom, setZoom] = useState(1)
  const nodeBySkillId = useMemo(
    () => new Map(skills.map((skill) => [skill.skillId, skill])),
    [skills],
  )
  const edges = useMemo<Edge[]>(
    () =>
      relations
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
        })),
    [nodeBySkillId, relations],
  )

  useEffect(() => {
    let isCurrent = true
    const elk = new ELK()
    const graph = {
      id: 'goal-skill-graph',
      layoutOptions: {
        'elk.algorithm': 'layered',
        'elk.direction': 'DOWN',
        'elk.layered.spacing.nodeNodeBetweenLayers': '72',
        'elk.spacing.nodeNode': '40',
      },
      children: skills.map((skill) => ({
        id: skill.skillId,
        width: NODE_WIDTH,
        height: NODE_HEIGHT,
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
        setNodes(
          skills.map((skill) => {
            const child = layout.children?.find(
              (candidate) => candidate.id === skill.skillId,
            )
            return {
              id: skill.skillId,
              type: 'goalSkill',
              position: { x: child?.x ?? 0, y: child?.y ?? 0 },
              data: { goalId, skill },
            }
          }),
        )
        setIsLayoutError(false)
      })
      .catch(() => {
        if (!isCurrent) return
        setNodes(
          skills.map((skill, index) => ({
            id: skill.skillId,
            type: 'goalSkill',
            position: { x: (index % 3) * 300, y: Math.floor(index / 3) * 200 },
            data: { goalId, skill },
          })),
        )
        setIsLayoutError(true)
      })
    return () => {
      isCurrent = false
    }
  }, [edges, goalId, skills])

  const handleZoomIn = useCallback(
    () => setZoom((current) => Math.min(MAX_ZOOM, current + ZOOM_STEP)),
    [],
  )
  const handleZoomOut = useCallback(
    () => setZoom((current) => Math.max(MIN_ZOOM, current - ZOOM_STEP)),
    [],
  )

  return {
    nodes,
    edges,
    zoom,
    isLayoutError,
    canZoomIn: zoom < MAX_ZOOM,
    canZoomOut: zoom > MIN_ZOOM,
    handleZoomIn,
    handleZoomOut,
  }
}
