import { Background, Controls, ReactFlow } from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import type { GoalSkillDetail, GoalSkillRelation } from '@/core/learning/goal-detail'

import { GoalGraphControls } from './goal-graph-controls'
import { GoalGraphNode, type GoalGraphNodeType } from './goal-graph-node'
import { useGoalSkillGraph } from './use-goal-skill-graph'

const NODE_TYPES = { goalSkill: GoalGraphNode }

export type GoalSkillGraphProps = {
  goalId: string
  skills: readonly GoalSkillDetail[]
  relations: readonly GoalSkillRelation[]
}

export const GoalSkillGraph = ({ goalId, relations, skills }: GoalSkillGraphProps) => {
  const {
    nodes,
    edges,
    zoom,
    isLayoutError,
    canZoomIn,
    canZoomOut,
    handleZoomIn,
    handleZoomOut,
  } = useGoalSkillGraph(goalId, skills, relations)

  return (
    <section
      aria-label='Grafo de Habilidades'
      className='relative h-[34rem] overflow-hidden rounded-lg border border-border bg-muted sm:h-[38rem]'
    >
      {isLayoutError ? (
        <p className='absolute left-4 top-4 z-10 rounded bg-card p-3 text-sm text-muted-foreground'>
          O layout do grafo foi ajustado para manter as Habilidades acessíveis.
        </p>
      ) : null}
      <div className='absolute right-3 top-3 z-10'>
        <GoalGraphControls
          canZoomIn={canZoomIn}
          canZoomOut={canZoomOut}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          zoom={zoom}
        />
      </div>
      <ReactFlow<GoalGraphNodeType>
        edges={edges}
        fitView
        fitViewOptions={{ maxZoom: 1 }}
        maxZoom={2}
        minZoom={0.25}
        nodes={nodes}
        nodeTypes={NODE_TYPES}
        nodesConnectable={false}
        nodesDraggable={false}
        nodesFocusable
        panOnDrag={false}
        proOptions={{ hideAttribution: true }}
        zoomOnDoubleClick={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        viewport={{ x: 0, y: 0, zoom }}
      >
        <Background gap={24} />
        <Controls showFitView={false} showInteractive={false} showZoom={false} />
      </ReactFlow>
    </section>
  )
}
