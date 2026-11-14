import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type GraphZoomControlsProps = {
  zoom: number
  canZoomIn: boolean
  canZoomOut: boolean
  onZoomIn: () => void
  onZoomOut: () => void
}

// 32 px as drawn; the pseudo-element keeps the 44 px touch target required on mobile.
const ZOOM_BUTTON =
  "relative size-8 min-h-0! rounded-sm p-0! text-secondary-foreground before:absolute before:-inset-1.5 before:content-['']"

export const GraphZoomControls = ({
  zoom,
  canZoomIn,
  canZoomOut,
  onZoomIn,
  onZoomOut,
}: GraphZoomControlsProps) => (
  <fieldset className='flex items-center gap-0.5 rounded-md border border-control-border bg-muted p-1'>
    <legend className='sr-only'>Controles do grafo</legend>
    <Button
      aria-label='Reduzir grafo'
      className={ZOOM_BUTTON}
      disabled={!canZoomOut}
      onClick={onZoomOut}
      type='button'
      variant='ghost'
    >
      <Icon name='minus' size={16} />
    </Button>
    <output
      aria-label={`Zoom do grafo: ${Math.round(zoom * 100)}%`}
      className='min-w-14 text-center text-xs font-semibold text-foreground'
    >
      {Math.round(zoom * 100)}%
    </output>
    <Button
      aria-label='Ampliar grafo'
      className={ZOOM_BUTTON}
      disabled={!canZoomIn}
      onClick={onZoomIn}
      type='button'
      variant='ghost'
    >
      <Icon name='plus' size={16} />
    </Button>
  </fieldset>
)
