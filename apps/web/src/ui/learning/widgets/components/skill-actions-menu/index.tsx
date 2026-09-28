import { useRef } from 'react'

import { Button } from '@/ui/shadcn/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/ui/shadcn/dropdown-menu'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type SkillActionsMenuProps = {
  skillName: string
  onRemove: (trigger: HTMLButtonElement) => void
}

export const SkillActionsMenu = ({ skillName, onRemove }: SkillActionsMenuProps) => {
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
            className='pointer-events-none absolute inset-1 rounded-md border border-control-border bg-muted transition-colors group-hover:bg-muted/70'
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
