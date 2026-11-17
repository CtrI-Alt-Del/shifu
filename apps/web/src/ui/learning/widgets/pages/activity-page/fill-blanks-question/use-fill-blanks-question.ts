import {
  type DragEndEvent,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import { useState } from 'react'

import type { FillBlanksPlacement, FillBlanksWord } from '@/core/learning/choice-activity'

import type { FillBlanksQuestionProps } from '.'

export const BANK_DROP_ID = 'bank'
export const BLANK_DROP_PREFIX = 'blank:'
export const BANK_WORD_DRAG_PREFIX = 'word:'
export const PLACED_WORD_DRAG_PREFIX = 'placed:'

const POINTER_DRAG_DISTANCE = 8
const TOUCH_DRAG_DELAY_MS = 200
const TOUCH_DRAG_TOLERANCE = 8

function placeWord(
  placements: readonly FillBlanksPlacement[],
  blankKey: string,
  wordKey: string,
) {
  // An occurrence fills one blank only, and a filled blank holds one occurrence.
  return [
    ...placements.filter(
      (placement) => placement.blankKey !== blankKey && placement.wordKey !== wordKey,
    ),
    { blankKey, wordKey },
  ]
}

function removeBlank(placements: readonly FillBlanksPlacement[], blankKey: string) {
  return placements.filter((placement) => placement.blankKey !== blankKey)
}

export function useFillBlanksQuestion({
  disabled = false,
  onPlacementsChange,
  placements,
  question,
}: FillBlanksQuestionProps) {
  const [selectedWordKey, setSelectedWordKey] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')
  // Keyboard and assistive technology use select-then-place; drag is for pointer and touch.
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: POINTER_DRAG_DISTANCE },
    }),
    useSensor(TouchSensor, {
      activationConstraint: {
        delay: TOUCH_DRAG_DELAY_MS,
        tolerance: TOUCH_DRAG_TOLERANCE,
      },
    }),
  )
  const wordByKey = new Map<string, FillBlanksWord>(
    question.bank.map((word) => [word.key, word]),
  )
  const blankNumberByKey = new Map<string, number>(
    question.segments
      .flatMap((segment) => (segment.blankKey ? [segment.blankKey] : []))
      .map((blankKey, index) => [blankKey, index + 1]),
  )
  const placedWordKeyByBlank = new Map<string, string>(
    placements.map((placement) => [placement.blankKey, placement.wordKey]),
  )
  const placedWordKeys = new Set(placements.map((placement) => placement.wordKey))
  const availableWords = question.bank.filter((word) => !placedWordKeys.has(word.key))
  const filledBlankCount = placements.length
  const blankCount = blankNumberByKey.size

  function describeWord(wordKey: string) {
    return `"${wordByKey.get(wordKey)?.word ?? ''}"`
  }

  function describeBlank(blankKey: string) {
    return `lacuna ${blankNumberByKey.get(blankKey) ?? ''}`
  }

  function commitPlacement(blankKey: string, wordKey: string) {
    const previousWordKey = placedWordKeyByBlank.get(blankKey)
    onPlacementsChange(placeWord(placements, blankKey, wordKey))
    setSelectedWordKey(null)
    setAnnouncement(
      previousWordKey && previousWordKey !== wordKey
        ? `Palavra ${describeWord(wordKey)} substituiu ${describeWord(previousWordKey)} na ${describeBlank(blankKey)}. A palavra anterior voltou ao banco.`
        : `Palavra ${describeWord(wordKey)} colocada na ${describeBlank(blankKey)}.`,
    )
  }

  function commitRemoval(blankKey: string) {
    const wordKey = placedWordKeyByBlank.get(blankKey)
    if (!wordKey) return

    onPlacementsChange(removeBlank(placements, blankKey))
    setAnnouncement(
      `Palavra ${describeWord(wordKey)} removida da ${describeBlank(blankKey)}. Ela voltou ao banco.`,
    )
  }

  function handleWordSelect(wordKey: string) {
    if (disabled) return

    if (selectedWordKey === wordKey) {
      setSelectedWordKey(null)
      setAnnouncement(`Seleção da palavra ${describeWord(wordKey)} cancelada.`)
      return
    }
    setSelectedWordKey(wordKey)
    setAnnouncement(`Palavra ${describeWord(wordKey)} selecionada. Escolha uma lacuna.`)
  }

  function handleBlankActivate(blankKey: string) {
    if (disabled) return

    if (selectedWordKey) {
      commitPlacement(blankKey, selectedWordKey)
      return
    }
    if (placedWordKeyByBlank.has(blankKey)) {
      commitRemoval(blankKey)
      return
    }
    setAnnouncement(`${describeBlank(blankKey)} vazia. Selecione uma palavra do banco.`)
  }

  function handleDragStart() {
    if (disabled) return

    setSelectedWordKey(null)
    setAnnouncement('Arrastando a palavra. Solte sobre uma lacuna.')
  }

  function handleDragEnd(event: DragEndEvent) {
    const activeId = String(event.active.id)
    const overId = event.over ? String(event.over.id) : null
    if (disabled || overId === null) return

    const sourceBlankKey = activeId.startsWith(PLACED_WORD_DRAG_PREFIX)
      ? activeId.slice(PLACED_WORD_DRAG_PREFIX.length)
      : null
    const wordKey =
      sourceBlankKey !== null
        ? placedWordKeyByBlank.get(sourceBlankKey)
        : activeId.slice(BANK_WORD_DRAG_PREFIX.length)
    if (!wordKey) return

    if (overId === BANK_DROP_ID) {
      if (sourceBlankKey !== null) commitRemoval(sourceBlankKey)
      return
    }
    if (!overId.startsWith(BLANK_DROP_PREFIX)) return

    const targetBlankKey = overId.slice(BLANK_DROP_PREFIX.length)
    if (targetBlankKey === sourceBlankKey) return

    commitPlacement(targetBlankKey, wordKey)
  }

  function handleDragCancel() {
    setAnnouncement('Arrasto cancelado.')
  }

  return {
    announcement,
    availableWords,
    blankCount,
    blankNumberByKey,
    filledBlankCount,
    placedWordKeyByBlank,
    selectedWordKey,
    sensors,
    wordByKey,
    handleBlankActivate,
    handleDragCancel,
    handleDragEnd,
    handleDragStart,
    handleWordSelect,
  }
}
