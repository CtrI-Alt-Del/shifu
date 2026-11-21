import { act, cleanup, renderHook } from '@testing-library/react'
import type { KeyboardEvent } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type {
  PairMatchingPair,
  PairMatchingQuestion,
} from '@/core/learning/choice-activity'

import {
  type PairMatchingQuestionProps,
  usePairMatchingQuestion,
} from '../use-pair-matching-question'

const QUESTION: PairMatchingQuestion = {
  key: 'pairs-1',
  kind: 'pair_matching',
  prompt: 'Associe',
  sourceLanguage: 'en',
  targetLanguage: 'pt-BR',
  words: [
    { key: 'w0', text: 'dog' },
    { key: 'w1', text: 'house' },
    { key: 'w2', text: 'water' },
  ],
  translations: [
    { key: 't1', text: 'casa' },
    { key: 't2', text: 'água' },
    { key: 't0', text: 'cachorro' },
  ],
}

function setup(initial: readonly PairMatchingPair[] = [], disabled = false) {
  let pairs = initial
  const onChange = vi.fn((next: readonly PairMatchingPair[]) => {
    pairs = next
  })
  const props = (): PairMatchingQuestionProps => ({
    question: QUESTION,
    questionNumber: 1,
    totalQuestions: 3,
    pairs,
    disabled,
    onChange,
  })
  const hook = renderHook(
    (current: PairMatchingQuestionProps) => usePairMatchingQuestion(current),
    { initialProps: props() },
  )
  const act2 = (action: () => void) => {
    act(action)
    hook.rerender(props())
  }
  return { hook, act2, onChange, current: () => pairs }
}

describe('usePairMatchingQuestion', () => {
  afterEach(cleanup)

  it('forms a pair by selecting a word and then its translation', () => {
    const { hook, act2, onChange } = setup()

    act2(() => hook.result.current.handleSelectWord('w0'))
    expect(hook.result.current.selectedWordKey).toBe('w0')
    act2(() => hook.result.current.handleSelectTranslation('t0'))

    expect(onChange).toHaveBeenLastCalledWith([{ wordKey: 'w0', translationKey: 't0' }])
    expect(hook.result.current.selectedWordKey).toBeNull()
    expect(hook.result.current.announcement).toBe('Par formado: dog com cachorro.')
  })

  it('forms nothing when a translation is chosen before a word', () => {
    const { hook, act2, onChange } = setup()

    act2(() => hook.result.current.handleSelectTranslation('t0'))

    expect(onChange).not.toHaveBeenCalled()
    expect(hook.result.current.announcement).toBe('Selecione primeiro uma palavra.')
  })

  it('releases the previous pair when another word takes the same translation', () => {
    const { hook, act2, current } = setup([{ wordKey: 'w0', translationKey: 't0' }])

    act2(() => hook.result.current.handleSelectWord('w1'))
    act2(() => hook.result.current.handleSelectTranslation('t0'))

    expect(current()).toEqual([{ wordKey: 'w1', translationKey: 't0' }])
    expect(hook.result.current.announcement).toContain('O par de dog foi desfeito.')
  })

  it('replaces a pair by selecting a paired word and choosing a new translation', () => {
    const { hook, act2, current } = setup([{ wordKey: 'w0', translationKey: 't0' }])

    act2(() => hook.result.current.handleSelectWord('w0'))
    expect(current()).toEqual([])
    expect(hook.result.current.selectedWordKey).toBe('w0')
    act2(() => hook.result.current.handleSelectTranslation('t1'))

    expect(current()).toEqual([{ wordKey: 'w0', translationKey: 't1' }])
  })

  it('removes a pair and clears a pending selection with Escape', () => {
    const { hook, act2, current } = setup([
      { wordKey: 'w0', translationKey: 't0' },
      { wordKey: 'w1', translationKey: 't1' },
    ])

    act2(() => hook.result.current.handleRemovePair('w0'))
    expect(current()).toEqual([{ wordKey: 'w1', translationKey: 't1' }])
    act2(() => hook.result.current.handleSelectWord('w2'))
    act2(() => hook.result.current.handleClearSelection())

    expect(hook.result.current.selectedWordKey).toBeNull()
  })

  it('cancels the selection by choosing the same word again', () => {
    const { hook, act2 } = setup()

    act2(() => hook.result.current.handleSelectWord('w0'))
    act2(() => hook.result.current.handleSelectWord('w0'))

    expect(hook.result.current.selectedWordKey).toBeNull()
  })

  it('reports completeness only with every pair formed', () => {
    const full = [
      { wordKey: 'w0', translationKey: 't0' },
      { wordKey: 'w1', translationKey: 't1' },
      { wordKey: 'w2', translationKey: 't2' },
    ]

    expect(setup(full.slice(0, 2)).hook.result.current.isComplete).toBe(false)
    expect(setup(full).hook.result.current.isComplete).toBe(true)
  })

  it('ignores every interaction while disabled', () => {
    const { hook, act2, onChange } = setup(
      [{ wordKey: 'w0', translationKey: 't0' }],
      true,
    )

    act2(() => hook.result.current.handleSelectWord('w1'))
    act2(() => hook.result.current.handleSelectTranslation('t1'))
    act2(() => hook.result.current.handleRemovePair('w0'))

    expect(onChange).not.toHaveBeenCalled()
    expect(hook.result.current.selectedWordKey).toBeNull()
  })

  it('lists the formed pairs in word order and labels the languages in pt-BR', () => {
    const { hook } = setup([
      { wordKey: 'w2', translationKey: 't2' },
      { wordKey: 'w0', translationKey: 't0' },
    ])

    expect(hook.result.current.orderedPairs.map((pair) => pair.wordKey)).toEqual([
      'w0',
      'w2',
    ])
    expect(hook.result.current.sourceLanguageLabel).toBe('Inglês')
    expect(hook.result.current.targetLanguageLabel).toBe('Português (Brasil)')
  })

  it('clears a pending selection when Escape is pressed and ignores other keys', () => {
    const { hook, act2 } = setup()

    act2(() => hook.result.current.handleSelectWord('w0'))
    act2(() => hook.result.current.handleKeyDown({ key: 'Enter' } as KeyboardEvent))
    expect(hook.result.current.selectedWordKey).toBe('w0')
    act2(() => hook.result.current.handleKeyDown({ key: 'Escape' } as KeyboardEvent))

    expect(hook.result.current.selectedWordKey).toBeNull()
    expect(hook.result.current.announcement).toBe('Seleção cancelada.')
  })

  it('moves keyboard focus to the word when its pair is removed', () => {
    const { hook, act2 } = setup([{ wordKey: 'w0', translationKey: 't0' }])
    const button = document.createElement('button')
    document.body.append(button)
    hook.result.current.registerWordButton('w0')(button)

    act2(() => hook.result.current.handleRemovePair('w0'))

    expect(button).toHaveFocus()
    button.remove()
  })

  it('does not move focus after the word button is released', () => {
    const { hook, act2 } = setup([{ wordKey: 'w0', translationKey: 't0' }])
    const button = document.createElement('button')
    document.body.append(button)
    const register = hook.result.current.registerWordButton('w0')
    register(button)
    register(null)

    act2(() => hook.result.current.handleRemovePair('w0'))

    expect(button).not.toHaveFocus()
    button.remove()
  })
})
