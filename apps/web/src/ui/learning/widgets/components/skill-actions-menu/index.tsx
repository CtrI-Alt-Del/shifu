import { useRef } from 'react'

import { Button } from '@/ui/shadcn/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/ui/shadcn/dropdown-menu'
import { Icon } from '@/ui/shared/widgets/components/icon'

// The full surface uses the important border: the plain utility loses to the base border
// color and would render the stroke at 8% instead of the design's 33% (ui-layer rules
// already use the `!` form for these outline strokes).
const SURFACE_CLASS = {
  inset: 'inset-1 border-control-border',
  full: 'inset-0 border-control-border!',
} as const

export type SkillActionsMenuProps = {
  skillName: string
  /** `inset` keeps the 36 px visible square; `full` fills the whole 44 px target. */
  surface?: 'inset' | 'full'
  onRemove: (trigger: HTMLButtonElement) => void
}

export const SkillActionsMenu = ({
  skillName,
  surface = 'inset',
  onRemove,
}: SkillActionsMenuProps) => {
  const triggerRef = useRef<HTMLButtonElement>(null)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          aria-label={`Mais ações de ${skillName}`}
          className='group relative size-11 min-h-0! shrink-0 rounded-md bg-transparent p-0! text-muted-foreground hover:bg-transparent hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-selo-text'
          ref={triggerRef}
          type='button'
          variant='ghost'
        >
          <span
            aria-hidden='true'
            className={`pointer-events-none absolute ${SURFACE_CLASS[surface]} rounded-md border bg-muted transition-colors group-hover:bg-muted/70`}
          />
          <Icon className='relative' name='ellipsis' size={16} />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align='end'>
        <DropdownMenuItem
          className='text-selo-text'
          onSelect={() => {
            if (triggerRef.current) onRemove(triggerRef.current)
          }}
        >
          <Icon name='trash-2' size={17} />
          Remover habilidade
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
