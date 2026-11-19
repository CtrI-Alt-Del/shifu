import type { FillBlanksWord } from '@/core/learning/choice-activity'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'

import { useBankWord } from './use-bank-word'

export type BankWordProps = {
  contentLanguage: string
  disabled: boolean
  isSelected: boolean
  onSelect: (wordKey: string) => void
  word: FillBlanksWord
}

export const BankWord = (props: BankWordProps) => {
  const { contentLanguage, disabled, isSelected, word } = props
  const { isDragging, listeners, setNodeRef, style, handleSelect } = useBankWord(props)

  return (
    <Button
      aria-pressed={isSelected}
      className='fill-blanks-word gap-2'
      data-dragging={isDragging}
      data-selected={isSelected}
      disabled={disabled}
      onClick={handleSelect}
      ref={setNodeRef}
      style={style}
      type='button'
      variant='outline'
      {...listeners}
    >
      <Icon
        aria-hidden='true'
        className='text-muted-foreground'
        name='grip-vertical'
        size={14}
      />
      <span lang={contentLanguage}>{word.word}</span>
      {isSelected ? (
        <span className='text-xs font-medium text-selo-text'>Selecionada</span>
      ) : null}
    </Button>
  )
}
