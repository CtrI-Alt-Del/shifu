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
          className='size-11 min-h-0! shrink-0 rounded-md border border-control-border bg-muted p-0! text-muted-foreground hover:bg-muted hover:text-foreground'
          ref={triggerRef}
          type='button'
          variant='ghost'
        >
          <Icon name='ellipsis' size={18} />
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
