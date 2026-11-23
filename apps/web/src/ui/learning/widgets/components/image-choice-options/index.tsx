import type { CSSProperties } from 'react'

import type { ImageChoiceOption } from '@/core/learning/choice-activity'
import { RadioGroup } from '@/ui/shadcn/radio-group'
import { Icon } from '@/ui/shared/widgets/components/icon'

import './image-choice-options.css'

const MAX_COLUMNS = 4

export type ImageChoiceOptionsState = 'selecting' | 'verified' | 'history'

export type ImageChoiceOptionsProps = {
  name: string
  labelledBy: string
  options: readonly ImageChoiceOption[]
  selectedOptionKey: string | null
  state: ImageChoiceOptionsState
  isCorrect?: boolean
  disclosedCorrectOptionKey?: string
  disabled?: boolean
  onSelectOption?: (optionKey: string) => void
}

export const ImageChoiceOptions = ({
  name,
  labelledBy,
  options,
  selectedOptionKey,
  state,
  isCorrect = false,
  disclosedCorrectOptionKey,
  disabled = false,
  onSelectOption,
}: ImageChoiceOptionsProps) => {
  const isSelecting = state === 'selecting'
  const isReadOnly = !isSelecting || disabled

  return (
    <RadioGroup
      aria-labelledby={labelledBy}
      className='image-choice-grid'
      disabled={isReadOnly}
      name={name}
      onValueChange={(optionKey) => onSelectOption?.(optionKey)}
      style={
        {
          '--image-choice-columns': Math.min(options.length, MAX_COLUMNS),
        } as CSSProperties
      }
      value={selectedOptionKey ?? ''}
    >
      {options.map((option, index) => {
        const isChosen = option.key === selectedOptionKey
        const isReleasedCorrect =
          !isSelecting && !isChosen && option.key === disclosedCorrectOptionKey
        const tone = isSelecting
          ? isChosen
            ? 'selected'
            : 'idle'
          : isChosen
            ? isCorrect
              ? 'correct'
              : 'incorrect'
            : isReleasedCorrect
              ? 'correct'
              : 'dimmed'
        const status = isSelecting
          ? isChosen
            ? 'Selecionada'
            : null
          : isChosen
            ? 'Sua resposta'
            : isReleasedCorrect
              ? 'Resposta correta'
              : null
        const descriptionId = `${name}-${option.key}-description`

        return (
          <label
            className='image-choice-card'
            data-interactive={!isReadOnly}
            data-tone={tone}
            key={option.key}
          >
            <input
              aria-describedby={descriptionId}
              aria-label={`Opção ${index + 1}`}
              checked={isChosen}
              className='sr-only'
              data-focus-ring='delegated'
              disabled={isReadOnly}
              name={name}
              onChange={() => onSelectOption?.(option.key)}
              type='radio'
              value={option.key}
            />
            <img
              alt=''
              className='image-choice-photo'
              decoding='async'
              draggable={false}
              src={option.imagePath}
            />
            <span className='image-choice-footer'>
              <span className='image-choice-label'>
                {tone === 'correct' ? (
                  <Icon aria-hidden='true' name='check' size={24} />
                ) : tone === 'incorrect' ? (
                  <Icon aria-hidden='true' name='x' size={24} />
                ) : (
                  <span aria-hidden='true' className='image-choice-radio' />
                )}
                <span aria-hidden='true'>Opção {index + 1}</span>
              </span>
              {status ? <span className='image-choice-status'>{status}</span> : null}
            </span>
            <span className='sr-only' id={descriptionId}>
              {option.description}
            </span>
          </label>
        )
      })}
    </RadioGroup>
  )
}
