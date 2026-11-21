import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  PairMatchingPair,
  PairMatchingQuestion as PairMatchingQuestionCore,
} from '@/core/learning/choice-activity'

import { PairMatchingQuestion } from '..'
import type { PairMatchingQuestionProps } from '../use-pair-matching-question'
import { usePairMatchingQuestion } from '../use-pair-matching-question'

vi.mock('../use-pair-matching-question', () => ({
  usePairMatchingQuestion: vi.fn(),
}))

const usePairMatchingQuestionMock = vi.mocked(usePairMatchingQuestion)

const QUESTION: PairMatchingQuestionCore = {
  key: 'pairs-1',
  kind: 'pair_matching',
  prompt: 'Associe cada palavra à sua tradução.',
  sourceLanguage: 'en',
  targetLanguage: 'pt-BR',
  words: [
    { key: 'w0', text: 'dog' },
    { key: 'w1', text: 'house' },
  ],
  translations: [
    { key: 't1', text: 'casa' },
    { key: 't0', text: 'cachorro' },
  ],
}

function hookValue(
  pairs: readonly PairMatchingPair[] = [],
  overrides: Partial<ReturnType<typeof usePairMatchingQuestion>> = {},
): ReturnType<typeof usePairMatchingQuestion> {
  return {
    selectedWordKey: null,
    announcement: '',
    isComplete: pairs.length === QUESTION.words.length,
    wordText: (key) => QUESTION.words.find((word) => word.key === key)?.text ?? key,
    translationText: (key) =>
      QUESTION.translations.find((item) => item.key === key)?.text ?? key,
    translationKeyByWord: new Map(
      pairs.map((pair) => [pair.wordKey, pair.translationKey]),
    ),
    wordKeyByTranslation: new Map(
      pairs.map((pair) => [pair.translationKey, pair.wordKey]),
    ),
    pairNumber: (key) => QUESTION.words.findIndex((word) => word.key === key) + 1,
    handleSelectWord: vi.fn(),
    handleSelectTranslation: vi.fn(),
    handleRemovePair: vi.fn(),
    handleClearSelection: vi.fn(),
    ...overrides,
  }
}

function renderQuestion(overrides: Partial<PairMatchingQuestionProps> = {}) {
  const props: PairMatchingQuestionProps = {
    onChange: vi.fn(),
    pairs: [],
    question: QUESTION,
    questionNumber: 1,
    totalQuestions: 3,
    ...overrides,
  }
  render(<PairMatchingQuestion {...props} />)
  return props
}

describe('PairMatchingQuestion', () => {
  beforeEach(() => {
    usePairMatchingQuestionMock.mockReturnValue(hookValue())
  })

  afterEach(cleanup)

  it('renders the prompt, languages and both lists in display order', () => {
    renderQuestion()

    expect(
      screen.getByRole('heading', { name: 'Associe cada palavra à sua tradução.' }),
    ).toBeVisible()
    expect(screen.getByText('Idioma das palavras')).toBeVisible()
    const lists = screen.getAllByRole('list')
    expect(
      within(lists[0])
        .getAllByRole('button')
        .map((item) => item.textContent),
    ).toEqual(['dog', 'house'])
    expect(
      within(lists[1])
        .getAllByRole('button')
        .map((item) => item.textContent),
    ).toEqual(['casa', 'cachorro'])
    expect(screen.getByText('0 de 2 pares formados.')).toBeVisible()
  })

  it('forwards word and translation selection to the owning hook', () => {
    const hook = hookValue()
    usePairMatchingQuestionMock.mockReturnValue(hook)
    renderQuestion()

    fireEvent.click(screen.getByRole('button', { name: 'dog' }))
    fireEvent.click(screen.getByRole('button', { name: 'cachorro' }))

    expect(hook.handleSelectWord).toHaveBeenCalledWith('w0')
    expect(hook.handleSelectTranslation).toHaveBeenCalledWith('t0')
  })

  it('shows a selected word with pressed state and without a duplicated state name', () => {
    usePairMatchingQuestionMock.mockReturnValue(hookValue([], { selectedWordKey: 'w0' }))
    renderQuestion()

    const word = screen.getByRole('button', { name: 'dog' })
    expect(word).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'house' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })

  it('shows formed pairs with number, text and a labelled remove control', () => {
    const pairs = [{ wordKey: 'w0', translationKey: 't0' }]
    usePairMatchingQuestionMock.mockReturnValue(hookValue(pairs))
    renderQuestion({ pairs })

    expect(screen.getByRole('button', { name: 'dog, par 1 com cachorro' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'cachorro, par 1 com dog' })).toBeVisible()
    expect(
      within(screen.getByRole('list', { name: 'Pares formados' })).getByRole('listitem'),
    ).toHaveTextContent('Par 1: dog — cachorro')
    expect(screen.getByText('1 de 2 pares formados.')).toBeVisible()
  })

  it('removes a pair and keeps keyboard focus on its word', () => {
    const pairs = [{ wordKey: 'w0', translationKey: 't0' }]
    const hook = hookValue(pairs)
    usePairMatchingQuestionMock.mockReturnValue(hook)
    renderQuestion({ pairs })

    fireEvent.click(screen.getByRole('button', { name: 'Remover par 1: dog e cachorro' }))

    expect(hook.handleRemovePair).toHaveBeenCalledWith('w0')
    expect(screen.getByRole('button', { name: 'dog, par 1 com cachorro' })).toHaveFocus()
  })

  it('clears a pending selection with Escape', () => {
    const hook = hookValue([], { selectedWordKey: 'w0' })
    usePairMatchingQuestionMock.mockReturnValue(hook)
    renderQuestion()

    fireEvent.keyDown(screen.getByRole('button', { name: 'dog' }), { key: 'Escape' })

    expect(hook.handleClearSelection).toHaveBeenCalledTimes(1)
  })

  it('announces the current step to assistive technology', () => {
    usePairMatchingQuestionMock.mockReturnValue(
      hookValue([], { announcement: 'Selecione primeiro uma palavra.' }),
    )
    renderQuestion()

    expect(screen.getByRole('status')).toHaveTextContent(
      'Selecione primeiro uma palavra.',
    )
  })

  it('is read-only after verification and says so in text', () => {
    const pairs = [
      { wordKey: 'w0', translationKey: 't0' },
      { wordKey: 'w1', translationKey: 't1' },
    ]
    usePairMatchingQuestionMock.mockReturnValue(hookValue(pairs))
    renderQuestion({ disabled: true, pairs })

    for (const button of screen.getAllByRole('button')) expect(button).toBeDisabled()
    expect(screen.getAllByText('Somente leitura')).toHaveLength(2)
    expect(screen.getByText(/Resposta avaliada: não é possível alterar\./)).toBeVisible()
    expect(screen.queryByRole('button', { name: /Remover par/ })).toBeNull()
  })
})
