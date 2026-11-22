import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { OrderingQuestion as OrderingQuestionData } from '@/core/learning/choice-activity'

import { useOrderingQuestion } from '../use-ordering-question'

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

    act(() => result.current.handleMoveStep('last', -1))
    expect(result.current.order).toEqual(['first', 'last', 'middle'])
    expect(result.current.announcement).toBe('Etapa final agora está na posição 2 de 3.')
    act(() => result.current.handleMoveStep('first', 1))
    expect(result.current.order).toEqual(['last', 'first', 'middle'])
    expect(onOrderChangeMock).toHaveBeenCalledTimes(2)

    rerender({ disabled: true })
    act(() => result.current.handleMoveStep('first', -1))
    expect(result.current.order).toEqual(['last', 'first', 'middle'])
  })

  it('does not move a step past either boundary', () => {
    const { result } = renderHook(() => useOrderingQuestion({ question: QUESTION }))

    act(() => result.current.handleMoveStep('first', -1))
    act(() => result.current.handleMoveStep('last', 1))

    expect(result.current.order).toEqual(QUESTION.initialOrderedStepKeys)
  })
})
