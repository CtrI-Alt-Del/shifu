import type { DragEndEvent } from '@dnd-kit/core'
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { FillBlanksPlacement } from '@/core/learning/choice-activity'
import { FillBlanksQuestionFaker } from '@/core/learning/fakers'

import type { FillBlanksQuestionProps } from '..'
import {
  BANK_DROP_ID,
  BANK_WORD_DRAG_PREFIX,
  BLANK_DROP_PREFIX,
  PLACED_WORD_DRAG_PREFIX,
  useFillBlanksQuestion,
} from '../use-fill-blanks-question'

function setup(
  placements: readonly FillBlanksPlacement[] = [],
  overrides: Partial<FillBlanksQuestionProps> = {},
) {
  const onPlacementsChange = vi.fn()
  const props: FillBlanksQuestionProps = {
    onPlacementsChange,
    placements,
    question: FillBlanksQuestionFaker.fake(),
    questionNumber: 1,
    totalQuestions: 4,
    ...overrides,
  }
  const rendered = renderHook(() => useFillBlanksQuestion(props))
  return { ...rendered, onPlacementsChange }
}

function dragEnd(activeId: string, overId: string | null) {
  return {
    active: { id: activeId },
    over: overId === null ? null : { id: overId },
  } as unknown as DragEndEvent
}

describe('useFillBlanksQuestion', () => {
  it('derives the blank numbers, the available bank and the filled count', () => {
    const { result } = setup([
      { blankKey: 'b1', wordKey: 'w1' },
      { blankKey: 'b3', wordKey: 'w4' },
    ])

    expect(result.current.blankCount).toBe(3)
    expect(result.current.filledBlankCount).toBe(2)
    expect(Object.fromEntries(result.current.blankNumberByKey)).toEqual({
      b1: 1,
      b2: 2,
      b3: 3,
    })
    expect(result.current.availableWords.map((word) => word.key)).toEqual([
      'w2',
      'w3',
      'w5',
      'w6',
    ])
    expect(result.current.placedWordKeyByBlank.get('b1')).toBe('w1')
    expect(result.current.wordByKey.get('w5')?.word).toBe('day')
    expect(result.current.selectedWordKey).toBeNull()
    expect(result.current.announcement).toBe('')
    expect(result.current.sensors).toHaveLength(2)
  })

  it('numbers the blanks when text segments arrive without null fields', () => {
    const base = FillBlanksQuestionFaker.fake()
    const question = {
      ...base,
      segments: base.segments.map((segment) => ({
        text: segment.text ?? undefined,
        blankKey: segment.blankKey ?? undefined,
      })),
    } as unknown as typeof base
    const { result } = setup([], { question })

    expect(result.current.blankCount).toBe(3)
    expect(Object.fromEntries(result.current.blankNumberByKey)).toEqual({
      b1: 1,
      b2: 2,
      b3: 3,
    })
  })

  it('selects a word and announces it, then cancels the selection on a second click', () => {
    const { result } = setup()

    act(() => result.current.handleWordSelect('w1'))
    expect(result.current.selectedWordKey).toBe('w1')
    expect(result.current.announcement).toBe(
      'Palavra "goes" selecionada. Escolha uma lacuna.',
    )

    act(() => result.current.handleWordSelect('w1'))
    expect(result.current.selectedWordKey).toBeNull()
    expect(result.current.announcement).toBe('Seleção da palavra "goes" cancelada.')
  })

  it('places the selected word in an empty blank and clears the selection', () => {
    const { result, onPlacementsChange } = setup()

    act(() => result.current.handleWordSelect('w1'))
    act(() => result.current.handleBlankActivate('b1'))

    expect(onPlacementsChange).toHaveBeenCalledWith([{ blankKey: 'b1', wordKey: 'w1' }])
    expect(result.current.selectedWordKey).toBeNull()
    expect(result.current.announcement).toBe('Palavra "goes" colocada na lacuna 1.')
  })

  it('replaces the word of a filled blank and returns the previous word to the bank', () => {
    const { result, onPlacementsChange } = setup([{ blankKey: 'b1', wordKey: 'w1' }])

    act(() => result.current.handleWordSelect('w2'))
    act(() => result.current.handleBlankActivate('b1'))

    expect(onPlacementsChange).toHaveBeenCalledWith([{ blankKey: 'b1', wordKey: 'w2' }])
    expect(result.current.announcement).toBe(
      'Palavra "walks" substituiu "goes" na lacuna 1. A palavra anterior voltou ao banco.',
    )
  })

  it('removes the word of a filled blank when no word is selected', () => {
    const { result, onPlacementsChange } = setup([
      { blankKey: 'b1', wordKey: 'w1' },
      { blankKey: 'b2', wordKey: 'w3' },
    ])

    act(() => result.current.handleBlankActivate('b1'))

    expect(onPlacementsChange).toHaveBeenCalledWith([{ blankKey: 'b2', wordKey: 'w3' }])
    expect(result.current.announcement).toBe(
      'Palavra "goes" removida da lacuna 1. Ela voltou ao banco.',
    )
  })

  it('asks for a word when an empty blank is activated without a selection', () => {
    const { result, onPlacementsChange } = setup()

    act(() => result.current.handleBlankActivate('b2'))

    expect(onPlacementsChange).not.toHaveBeenCalled()
    expect(result.current.announcement).toBe(
      'lacuna 2 vazia. Selecione uma palavra do banco.',
    )
  })

  it('never moves a word between blanks without an explicit placement', () => {
    const { result, onPlacementsChange } = setup([{ blankKey: 'b1', wordKey: 'w1' }])

    act(() => result.current.handleWordSelect('w2'))
    act(() => result.current.handleBlankActivate('b2'))

    expect(onPlacementsChange).toHaveBeenCalledWith([
      { blankKey: 'b1', wordKey: 'w1' },
      { blankKey: 'b2', wordKey: 'w2' },
    ])
  })

  it('places a dragged bank word on a blank and ignores a drop outside any target', () => {
    const { result, onPlacementsChange } = setup()

    act(() =>
      result.current.handleDragEnd(
        dragEnd(`${BANK_WORD_DRAG_PREFIX}w3`, `${BLANK_DROP_PREFIX}b2`),
      ),
    )
    expect(onPlacementsChange).toHaveBeenCalledWith([{ blankKey: 'b2', wordKey: 'w3' }])

    onPlacementsChange.mockClear()
    act(() => result.current.handleDragEnd(dragEnd(`${BANK_WORD_DRAG_PREFIX}w3`, null)))
    act(() =>
      result.current.handleDragEnd(dragEnd(`${BANK_WORD_DRAG_PREFIX}w3`, BANK_DROP_ID)),
    )
    expect(onPlacementsChange).not.toHaveBeenCalled()
  })

  it('moves a placed word to another blank and returns the target word to the bank', () => {
    const { result, onPlacementsChange } = setup([
      { blankKey: 'b1', wordKey: 'w1' },
      { blankKey: 'b2', wordKey: 'w3' },
    ])

    act(() =>
      result.current.handleDragEnd(
        dragEnd(`${PLACED_WORD_DRAG_PREFIX}b1`, `${BLANK_DROP_PREFIX}b2`),
      ),
    )

    expect(onPlacementsChange).toHaveBeenCalledWith([{ blankKey: 'b2', wordKey: 'w1' }])
  })

  it('returns a placed word to the bank when it is dropped there and ignores its own blank', () => {
    const { result, onPlacementsChange } = setup([{ blankKey: 'b1', wordKey: 'w1' }])

    act(() =>
      result.current.handleDragEnd(
        dragEnd(`${PLACED_WORD_DRAG_PREFIX}b1`, `${BLANK_DROP_PREFIX}b1`),
      ),
    )
    expect(onPlacementsChange).not.toHaveBeenCalled()

    act(() =>
      result.current.handleDragEnd(dragEnd(`${PLACED_WORD_DRAG_PREFIX}b1`, BANK_DROP_ID)),
    )
    expect(onPlacementsChange).toHaveBeenCalledWith([])
  })

  it('announces the start and the cancellation of a drag and clears the selection', () => {
    const { result } = setup()

    act(() => result.current.handleWordSelect('w1'))
    act(() => result.current.handleDragStart())
    expect(result.current.selectedWordKey).toBeNull()
    expect(result.current.announcement).toBe(
      'Arrastando a palavra. Solte sobre uma lacuna.',
    )

    act(() => result.current.handleDragCancel())
    expect(result.current.announcement).toBe('Arrasto cancelado.')
  })

  it('ignores every interaction while the question is disabled', () => {
    const { result, onPlacementsChange } = setup([{ blankKey: 'b1', wordKey: 'w1' }], {
      disabled: true,
    })

    act(() => result.current.handleWordSelect('w2'))
    act(() => result.current.handleBlankActivate('b1'))
    act(() => result.current.handleDragStart())
    act(() =>
      result.current.handleDragEnd(
        dragEnd(`${BANK_WORD_DRAG_PREFIX}w2`, `${BLANK_DROP_PREFIX}b2`),
      ),
    )

    expect(result.current.selectedWordKey).toBeNull()
    expect(result.current.announcement).toBe('')
    expect(onPlacementsChange).not.toHaveBeenCalled()
  })
})
