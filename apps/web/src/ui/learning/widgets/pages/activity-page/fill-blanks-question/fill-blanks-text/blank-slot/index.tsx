import { X } from 'lucide-react'

import type { FillBlanksWord } from '@/core/learning/choice-activity'
import { Button } from '@/ui/shadcn/button'

import { useBlankSlot } from './use-blank-slot'

export type BlankSlotProps = {
  blankKey: string
  blankNumber: number
  contentLanguage: string
  disabled: boolean
  onActivate: (blankKey: string) => void
  placedWord: FillBlanksWord | null
}

export const BlankSlot = (props: BlankSlotProps) => {
  const { blankNumber, contentLanguage, disabled, placedWord } = props
  const { isDragging, isOver, listeners, style, setNodeRef, handleActivate } =
    useBlankSlot(props)

  return (
    <Button
      className='fill-blanks-blank mx-1 align-baseline'
      data-dragging={isDragging}
      data-filled={placedWord !== null}
      data-over={isOver}
      disabled={disabled}
      onClick={handleActivate}
      ref={setNodeRef}
      style={style}
      type='button'
      variant='outline'
      {...listeners}
    >
      {placedWord ? (
        <>
          <span className='sr-only'>Lacuna {blankNumber}:</span>{' '}
          <span lang={contentLanguage}>{placedWord.word}</span>
          <span className='sr-only'>. Ative para remover a palavra.</span>
          <X aria-hidden='true' className='size-3.5 text-muted-foreground' />
        </>
      ) : (
        <>
          <span aria-hidden='true'>{blankNumber}</span>
          <span className='sr-only'>Lacuna {blankNumber}: vazia</span>
        </>
      )}
    </Button>
  )
}
