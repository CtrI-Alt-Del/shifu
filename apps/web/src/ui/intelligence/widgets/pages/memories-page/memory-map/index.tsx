import { Background, ReactFlow } from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import type { LearnerMemory } from '@/core/intelligence/learner-memory'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { MemoryMapHub } from './memory-map-hub'
import { MemoryMapNode } from './memory-map-node'
import {
  MEMORY_MAP_MAX_ZOOM,
  MEMORY_MAP_MIN_ZOOM,
  type MemoryMapFlowNode,
  useMemoryMap,
} from './use-memory-map'

const NODE_TYPES = { memoryHub: MemoryMapHub, memoryNode: MemoryMapNode }

export type MemoryMapProps = {
  memories: LearnerMemory[]
  selectedMemoryId: string | null
  onSelectMemory: (memoryId: string) => void
}

export const MemoryMap = (props: MemoryMapProps) => {
  const { memories } = props
  const {
    nodes,
    edges,
    zoom,
    containerRef,
    canZoomIn,
    canZoomOut,
    handleInit,
    handleZoomIn,
    handleZoomOut,
    handleZoomChange,
  } = useMemoryMap(props)
  const countLabel = memories.length === 1 ? '1 memória' : `${memories.length} memórias`

  return (
    <section
      aria-label='Mapa de memórias'
      className='rounded-[10px] border border-border bg-card p-4 lg:p-6'
      ref={containerRef}
    >
      <div className='flex items-start justify-between gap-3'>
        <div>
          <h2 className='font-serif text-2xl font-normal'>Mapa de memórias</h2>
          <p className='text-xs text-muted-foreground'>
            {countLabel} · selecione um nó para ver os detalhes
          </p>
        </div>
        <fieldset className='flex items-center gap-1 rounded-md border border-control-border bg-muted p-1'>
          <legend className='sr-only'>Controles do mapa</legend>
          <Button
            aria-label='Reduzir mapa'
            className='size-11 px-0'
            disabled={!canZoomOut}
            onClick={handleZoomOut}
            type='button'
            variant='ghost'
          >
            <Icon name='minus' size={18} />
          </Button>
          <output
            aria-label={`Zoom do mapa: ${Math.round(zoom * 100)}%`}
            className='min-w-14 text-center text-sm font-semibold'
          >
            {Math.round(zoom * 100)}%
          </output>
          <Button
            aria-label='Ampliar mapa'
            className='size-11 px-0'
            disabled={!canZoomIn}
            onClick={handleZoomIn}
            type='button'
            variant='ghost'
          >
            <Icon name='plus' size={18} />
          </Button>
        </fieldset>
      </div>
      <div className='mt-4 h-[22rem] sm:h-[28rem] lg:h-[32rem]'>
        <ReactFlow<MemoryMapFlowNode>
          disableKeyboardA11y
          edges={edges}
          edgesFocusable={false}
          fitView
          fitViewOptions={{ maxZoom: 1, padding: 0.15 }}
          maxZoom={MEMORY_MAP_MAX_ZOOM}
          minZoom={MEMORY_MAP_MIN_ZOOM}
          nodes={nodes}
          nodeTypes={NODE_TYPES}
          nodesConnectable={false}
          nodesDraggable={false}
          nodesFocusable={false}
          elementsSelectable={false}
          onInit={handleInit}
          onMove={(_, viewport) => handleZoomChange(viewport.zoom)}
          panOnDrag
          preventScrolling={false}
          proOptions={{ hideAttribution: true }}
          zoomOnDoubleClick={false}
          zoomOnPinch={false}
          zoomOnScroll={false}
        >
          <Background color='var(--border)' gap={24} size={1.5} />
        </ReactFlow>
      </div>
      <p className='mt-3 text-xs text-muted-foreground'>
        Selecione uma memória para ver sua origem e gerenciá-la.
      </p>
    </section>
  )
}
