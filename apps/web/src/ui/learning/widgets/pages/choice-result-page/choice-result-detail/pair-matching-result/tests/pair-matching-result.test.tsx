import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PairMatchingResult } from '..'
import { usePairMatchingResult } from '../use-pair-matching-result'

vi.mock('../use-pair-matching-result', () => ({ usePairMatchingResult: vi.fn() }))

const usePairMatchingResultMock = vi.mocked(usePairMatchingResult)

const RESULT = {
  key: 'pairs-1',
  kind: 'pair_matching',
  prompt: 'Associe as palavras.',
  score: 50,
  submittedPairs: [],
  correctPairCount: 1,
  totalPairCount: 2,
  outcome: 'partial',
  explanation: 'Alguns pares estão corretos.',
} as const

function hookValue(
  overrides: Partial<ReturnType<typeof usePairMatchingResult>> = {},
): ReturnType<typeof usePairMatchingResult> {
  return {
    outcome: {
      outcome: 'partial',
      iconName: 'circle-alert',
      label: 'Parcialmente correta',
      countText: '1 de 2 pares corretos',
    },
    isFull: false,
    formattedScore: '50',
    submittedItems: [
      { key: 'w0', wordText: 'dog', translationText: 'cachorro' },
      { key: 'w1', wordText: 'house', translationText: 'cachorro' },
    ],
    expectedItems: [],
    ...overrides,
  }
}

function renderResult() {
  render(<PairMatchingResult question={undefined} questionNumber={3} result={RESULT} />)
}

describe('PairMatchingResult', () => {
  beforeEach(() => {
    usePairMatchingResultMock.mockReturnValue(hookValue())
  })

  afterEach(cleanup)

  it('shows the outcome as text with the grade and the explanation', () => {
    renderResult()

    expect(
      screen.getByText(/Questão 3 · Associação · Parcialmente correta/),
    ).toBeVisible()
    expect(screen.getByLabelText('Nota 50 de 100')).toBeVisible()
    expect(screen.getByText('1 de 2 pares corretos')).toBeInTheDocument()
    expect(screen.getByText('Alguns pares estão corretos.')).toBeInTheDocument()
  })

  it('lists the submitted pairs and hides the expected pairs when not released', () => {
    renderResult()

    const submitted = screen.getByRole('list', { name: 'Pares enviados' })
    expect(within(submitted).getAllByRole('listitem')).toHaveLength(2)
    expect(within(submitted).getByText('dog — cachorro')).toBeInTheDocument()
    expect(screen.queryByText('Pares esperados')).not.toBeInTheDocument()
  })

  it('lists the expected pairs when the hook releases them', () => {
    usePairMatchingResultMock.mockReturnValue(
      hookValue({
        expectedItems: [{ key: 'w1', wordText: 'house', translationText: 'casa' }],
      }),
    )
    renderResult()

    expect(
      within(screen.getByRole('list', { name: 'Pares esperados' })).getByText(
        'house — casa',
      ),
    ).toBeInTheDocument()
  })
})
