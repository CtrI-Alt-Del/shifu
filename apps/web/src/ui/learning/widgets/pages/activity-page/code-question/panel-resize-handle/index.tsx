import type { KeyboardEventHandler, PointerEventHandler } from 'react'

export type PanelResizeHandleProps = {
  label: string
  minimum: number
  maximum: number
  current: number
  onPointerDown: PointerEventHandler<HTMLDivElement>
  onPointerMove: PointerEventHandler<HTMLDivElement>
  onPointerUp: PointerEventHandler<HTMLDivElement>
  onPointerCancel: PointerEventHandler<HTMLDivElement>
  onKeyDown: KeyboardEventHandler<HTMLDivElement>
}

export const PanelResizeHandle = (props: PanelResizeHandleProps) => (
  <hr
    aria-label={props.label}
    aria-orientation='vertical'
    aria-valuemin={props.minimum}
    aria-valuemax={props.maximum}
    aria-valuenow={props.current}
    aria-valuetext={`${props.current} pixels`}
    tabIndex={0}
    className='relative m-0 hidden h-full w-2 cursor-col-resize touch-none select-none border-0 bg-muted before:pointer-events-none before:absolute before:inset-y-0 before:left-1/2 before:w-px before:-translate-x-1/2 before:bg-border hover:bg-success/20 hover:before:bg-success focus-visible:z-10 focus-visible:bg-success/20 focus-visible:before:bg-success lg:block'
    onPointerDown={props.onPointerDown}
    onPointerMove={props.onPointerMove}
    onPointerUp={props.onPointerUp}
    onPointerCancel={props.onPointerCancel}
    onKeyDown={props.onKeyDown}
  />
)
