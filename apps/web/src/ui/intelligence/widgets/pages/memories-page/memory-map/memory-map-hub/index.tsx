import { Handle, type Node, type NodeProps, Position } from '@xyflow/react'

import { Icon } from '@/ui/shared/widgets/components/icon'

export type MemoryMapHubData = { label: string }
export type MemoryMapHubType = Node<MemoryMapHubData, 'memoryHub'>

export const MemoryMapHub = ({ data }: NodeProps<MemoryMapHubType>) => (
  <div className='relative flex size-20 items-center justify-center rounded-full border-2 border-foreground! bg-surface-alt ring-8 ring-foreground/10'>
    <Handle
      className='pointer-events-none opacity-0'
      isConnectable={false}
      position={Position.Top}
      style={{ top: '50%' }}
      type='source'
    />
    <Icon name='brain' className='size-8 text-foreground' />
    <span className='pointer-events-none absolute top-full mt-2 whitespace-nowrap rounded bg-card px-1 text-lg font-medium text-foreground'>
      {data.label}
    </span>
  </div>
)
