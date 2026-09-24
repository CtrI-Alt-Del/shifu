import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'

export type GoalGraphControlsProps = {
  zoom: number
  canZoomIn: boolean
  canZoomOut: boolean
  onZoomIn: () => void
  onZoomOut: () => void
}

export const GoalGraphControls = ({
  zoom,
  canZoomIn,
  canZoomOut,
  onZoomIn,
  onZoomOut,
}: GoalGraphControlsProps) => (
  <fieldset className='flex items-center gap-1 rounded-md border border-control-border bg-card p-1'>
    <legend className='sr-only'>Controles do grafo</legend>
    <Button
      aria-label='Reduzir grafo'
      className='size-11 px-0'
      disabled={!canZoomOut}
      onClick={onZoomOut}
      type='button'
      variant='ghost'
    >
      <Icon name='minus' size={18} />
    </Button>
    <output
      aria-label={`Zoom do grafo: ${Math.round(zoom * 100)}%`}
      className='min-w-14 text-center text-sm font-semibold'
    >
      {Math.round(zoom * 100)}%
    </output>
    <Button
      aria-label='Ampliar grafo'
      className='size-11 px-0'
      disabled={!canZoomIn}
      onClick={onZoomIn}
      type='button'
      variant='ghost'
    >
      <Icon name='plus' size={18} />
    </Button>
  </fieldset>
)
