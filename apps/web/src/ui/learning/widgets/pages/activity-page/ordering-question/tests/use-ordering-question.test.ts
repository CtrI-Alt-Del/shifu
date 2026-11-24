import type { DragEndEvent } from '@dnd-kit/core'
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { OrderingQuestion as OrderingQuestionData } from '@/core/learning/choice-activity'

import { STEP_DRAG_PREFIX, useOrderingQuestion } from '../use-ordering-question'

const QUESTION: OrderingQuestionData = {
  key: 'order-1',
  kind: 'ordering',
  prompt: 'Organize o preparo.',
  steps: [
    { key: 'first', text: 'Etapa inicial' },
    { key: 'middle', text: 'Etapa intermediária' },
    { key: 'last', text: 'Etapa final' },
  ],
  initialOrderedStepKeys: ['first', 'middle', 'last'],
  verified: null,
}

function dragEnd(activeStepKey: string, overId: string | null): DragEndEvent {
  return {
    active: { id: `${STEP_DRAG_PREFIX}${activeStepKey}` },
    over: overId === null ? null : { id: overId },
  } as unknown as DragEndEvent
}

describe('useOrderingQuestion', () => {
  it('moves steps in either direction and preserves the order when disabled', () => {
    const onOrderChangeMock = vi.fn()
    const { result, rerender } = renderHook(
      ({ disabled }: { disabled: boolean }) =>
        useOrderingQuestion({
          question: QUESTION,
          disabled,
          onOrderChange: onOrderChangeMock,
        }),
      { initialProps: { disabled: false } },
    )

    expect(result.current.moveCount).toBe(0)
    act(() => result.current.handleMoveStep('last', -1))
    expect(result.current.order).toEqual(['first', 'last', 'middle'])
    expect(result.current.sortableIds).toEqual([
      `${STEP_DRAG_PREFIX}first`,
      `${STEP_DRAG_PREFIX}last`,
      `${STEP_DRAG_PREFIX}middle`,
    ])
    expect(result.current.announcement).toBe('Etapa final agora está na posição 2 de 3.')
    act(() => result.current.handleMoveStep('first', 1))
    expect(result.current.order).toEqual(['last', 'first', 'middle'])
    expect(onOrderChangeMock).toHaveBeenCalledTimes(2)
    expect(result.current.moveCount).toBe(2)

    rerender({ disabled: true })
    act(() => result.current.handleMoveStep('first', -1))
    expect(result.current.order).toEqual(['last', 'first', 'middle'])
    expect(result.current.moveCount).toBe(2)
  })

  it('does not move a step past either boundary', () => {
    const { result } = renderHook(() => useOrderingQuestion({ question: QUESTION }))

    act(() => result.current.handleMoveStep('first', -1))
    act(() => result.current.handleMoveStep('last', 1))

    expect(result.current.order).toEqual(QUESTION.initialOrderedStepKeys)
    expect(result.current.moveCount).toBe(0)
  })

  it('drops a dragged step at the position of the step under it', () => {
    const onOrderChangeMock = vi.fn()
    const { result } = renderHook(() =>
      useOrderingQuestion({ question: QUESTION, onOrderChange: onOrderChangeMock }),
    )

    act(() => result.current.handleDragStart())
    expect(result.current.announcement).toBe(
      'Arrastando a etapa. Solte sobre a posição desejada.',
    )
    act(() => result.current.handleDragEnd(dragEnd('last', `${STEP_DRAG_PREFIX}first`)))

    expect(result.current.order).toEqual(['last', 'first', 'middle'])
    expect(result.current.announcement).toBe('Etapa final agora está na posição 1 de 3.')
    expect(onOrderChangeMock).toHaveBeenCalledWith(['last', 'first', 'middle'])

    act(() => result.current.handleDragEnd(dragEnd('last', `${STEP_DRAG_PREFIX}middle`)))
    expect(result.current.order).toEqual(['first', 'middle', 'last'])
    // Drag reorders animate through the sortable transition, not the button-move counter.
    expect(result.current.moveCount).toBe(0)
  })

  it('keeps the order when a drag ends outside a step, on itself or while disabled', () => {
    const onOrderChangeMock = vi.fn()
    const { result, rerender } = renderHook(
      ({ disabled }: { disabled: boolean }) =>
        useOrderingQuestion({
          question: QUESTION,
          disabled,
          onOrderChange: onOrderChangeMock,
        }),
      { initialProps: { disabled: false } },
    )

    act(() => result.current.handleDragEnd(dragEnd('first', null)))
    act(() => result.current.handleDragEnd(dragEnd('first', 'elsewhere')))
    act(() => result.current.handleDragEnd(dragEnd('first', `${STEP_DRAG_PREFIX}first`)))
    rerender({ disabled: true })
    act(() => result.current.handleDragStart())
    act(() => result.current.handleDragEnd(dragEnd('first', `${STEP_DRAG_PREFIX}last`)))

    expect(result.current.order).toEqual(QUESTION.initialOrderedStepKeys)
    expect(result.current.announcement).toBe('')
    expect(onOrderChangeMock).not.toHaveBeenCalled()
  })

  it('announces a cancelled drag', () => {
    const { result } = renderHook(() => useOrderingQuestion({ question: QUESTION }))

    act(() => result.current.handleDragCancel())

    expect(result.current.announcement).toBe('Arrasto cancelado.')
  })
})
