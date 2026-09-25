import { useEffect, useRef, useState } from 'react'
import { Background, Controls, ReactFlow, type ReactFlowInstance } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './goal-skill-graph.css'

import type { GoalSkillDetail, GoalSkillRelation } from '@/core/learning/goal-detail'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { GoalGraphControls } from './goal-graph-controls'
import { GoalGraphNode, GoalRootNode, type GoalFlowNodeType } from './goal-graph-node'
import { useGoalSkillGraph } from './use-goal-skill-graph'

const NODE_TYPES = { goalSkill: GoalGraphNode, goalRoot: GoalRootNode }

export type GoalSkillGraphProps = {
  goalId: string
  skills: readonly GoalSkillDetail[]
  relations: readonly GoalSkillRelation[]
  title: string
}

export const GoalSkillGraph = ({
  goalId,
  relations,
  skills,
  title,
}: GoalSkillGraphProps) => {
  const {
    nodes,
    edges,
    zoom,
    isLayoutError,
    canZoomIn,
    canZoomOut,
    handleZoomIn,
    handleZoomOut,
    handleZoomChange,
    handleNodeHover,
    handleNodeFocus,
  } = useGoalSkillGraph(goalId, skills, relations, title)
  const [instance, setInstance] = useState<ReactFlowInstance<GoalFlowNodeType> | null>(
    null,
  )
  const graphRef = useRef<HTMLElement>(null)
  const fitGraph = () => void instance?.fitView({ maxZoom: 1, padding: 0.08 })

  useEffect(() => {
    if (!instance || nodes.length === 0 || !graphRef.current) return
    const observer = new ResizeObserver(() => {
      void instance.fitView({ maxZoom: 1, padding: 0.08 })
    })
    observer.observe(graphRef.current)
    void instance.fitView({ maxZoom: 1, padding: 0.08 })
    return () => observer.disconnect()
  }, [instance, nodes])

  return (
    <section
      aria-label='Grafo de Habilidades'
      className='relative h-[40rem] overflow-hidden rounded-[10px] border border-border bg-surface-alt'
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) handleNodeFocus(null)
      }}
      onFocusCapture={(event) =>
        handleNodeFocus(
          event.target.closest<HTMLElement>('.react-flow__node[data-id]')?.dataset.id ??
            null,
        )
      }
      ref={graphRef}
    >
      <div className='group absolute left-3 top-3 z-10'>
        <Button
          aria-label='Restaurar posição inicial do grafo'
          className='size-11 min-h-0! p-0! focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-selo-text'
          disabled={!instance || nodes.length === 0}
          onClick={fitGraph}
          type='button'
          variant='ghost'
        >
          <Icon name='network' size={16} />
        </Button>
        <span
          className='pointer-events-none absolute left-full top-1/2 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-control-border bg-card px-3 py-2 text-xs text-foreground opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100'
          role='tooltip'
        >
          Restaurar posição inicial do grafo
        </span>
      </div>
      {isLayoutError ? (
        <p className='absolute left-4 top-4 z-10 rounded bg-card p-3 text-sm text-muted-foreground'>
          O layout do grafo foi ajustado para manter as Habilidades acessíveis.
        </p>
      ) : null}
      <div className='absolute bottom-5 right-5 z-10'>
        <GoalGraphControls
          canZoomIn={canZoomIn}
          canZoomOut={canZoomOut}
          onZoomIn={() => {
            void instance?.zoomTo(Math.min(2, zoom + 0.2))
            handleZoomIn()
          }}
          onZoomOut={() => {
            void instance?.zoomTo(Math.max(0.25, zoom - 0.2))
            handleZoomOut()
          }}
          zoom={zoom}
        />
      </div>
      <ReactFlow<GoalFlowNodeType>
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
        onInit={setInstance}
        onMove={(_, viewport) => handleZoomChange(viewport.zoom)}
        onNodeMouseEnter={(_, node) => handleNodeHover(node.id)}
        onNodeMouseLeave={() => handleNodeHover(null)}
        panOnDrag
        proOptions={{ hideAttribution: true }}
        zoomOnDoubleClick={false}
        zoomOnScroll
        zoomOnPinch={false}
      >
        <Background color='var(--border)' gap={24} size={1.5} />
        <Controls showFitView={false} showInteractive={false} showZoom={false} />
      </ReactFlow>
    </section>
  )
}
