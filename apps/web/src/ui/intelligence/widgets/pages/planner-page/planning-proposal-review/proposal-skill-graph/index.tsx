import { Background, Controls, ReactFlow } from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import type {
  PlanningProposalSkill,
  PlanningSkillRelation,
} from '@/core/intelligence/planning-session'
import { Button } from '@/ui/shadcn/button'
import { GraphZoomControls } from '@/ui/shared/widgets/components/graph-zoom-controls'
import { Icon } from '@/ui/shared/widgets/components/icon'

import {
  type ProposalFlowNodeType,
  ProposalGraphNode,
  ProposalRootNode,
} from './proposal-graph-node'
import {
  PROPOSAL_GRAPH_MAX_ZOOM,
  PROPOSAL_GRAPH_MIN_ZOOM,
  useProposalSkillGraph,
} from './use-proposal-skill-graph'

const NODE_TYPES = { proposalSkill: ProposalGraphNode, proposalRoot: ProposalRootNode }
const EDGE_OPTIONS = {
  type: 'smoothstep',
  style: { stroke: 'var(--control-border)', strokeWidth: 2 },
}

export type ProposalSkillGraphProps = {
  title: string
  skills: PlanningProposalSkill[]
  relations: PlanningSkillRelation[]
}

export const ProposalSkillGraph = ({
  title,
  skills,
  relations,
}: ProposalSkillGraphProps) => {
  const {
    graphRef,
    nodes,
    edges,
    zoom,
    isLayoutError,
    isReady,
    canZoomIn,
    canZoomOut,
    handleInit,
    handleNodesChange,
    handleRestore,
    handleZoomIn,
    handleZoomOut,
    handleZoomChange,
  } = useProposalSkillGraph(title, skills, relations)

  return (
    <section
      aria-label='Grafo das Habilidades propostas'
      className='relative h-[50rem] overflow-hidden rounded-[10px] border border-border bg-surface-alt lg:h-[40rem]'
      ref={graphRef}
    >
      <div className='group absolute left-1.5 top-1.5 z-10'>
        <Button
          aria-label='Restaurar posição inicial do grafo'
          className='size-11 min-h-0! p-0! text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-selo-text'
          disabled={!isReady}
          onClick={handleRestore}
          type='button'
          variant='ghost'
        >
          <Icon name='git-fork' size={16} />
        </Button>
        <span
          className='pointer-events-none absolute left-full top-1/2 ml-2 -translate-y-1/2 whitespace-nowrap rounded-md border border-control-border bg-card px-3 py-2 text-xs text-foreground opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100'
          role='tooltip'
        >
          Restaurar posição inicial do grafo
        </span>
      </div>
      {isLayoutError ? (
        <p className='absolute left-4 top-16 z-10 rounded bg-card p-3 text-sm text-muted-foreground'>
          O layout do grafo foi ajustado para manter as Habilidades acessíveis.
        </p>
      ) : null}
      <div className='absolute bottom-4 right-4 z-10 lg:bottom-5 lg:right-6'>
        <GraphZoomControls
          canZoomIn={canZoomIn}
          canZoomOut={canZoomOut}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          zoom={zoom}
        />
      </div>
      <ReactFlow<ProposalFlowNodeType>
        defaultEdgeOptions={EDGE_OPTIONS}
        edges={edges}
        maxZoom={PROPOSAL_GRAPH_MAX_ZOOM}
        minZoom={PROPOSAL_GRAPH_MIN_ZOOM}
        nodes={nodes}
        nodeTypes={NODE_TYPES}
        nodesConnectable={false}
        nodesDraggable={false}
        nodesFocusable
        onInit={handleInit}
        onMove={(_, viewport) => handleZoomChange(viewport.zoom)}
        onNodesChange={handleNodesChange}
        panOnDrag
        proOptions={{ hideAttribution: true }}
        zoomOnDoubleClick={false}
        zoomOnPinch={false}
        zoomOnScroll
      >
        <Background color='var(--border)' gap={24} size={1.5} />
        <Controls showFitView={false} showInteractive={false} showZoom={false} />
      </ReactFlow>
    </section>
  )
}
