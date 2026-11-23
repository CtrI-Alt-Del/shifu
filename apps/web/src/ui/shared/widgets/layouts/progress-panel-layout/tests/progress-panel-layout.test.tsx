import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ProgressPanelLayout } from '..'

function renderLayout() {
  return render(
    <ProgressPanelLayout
      engagementSection={<section aria-label='Seção de engajamento' />}
      engagementSummary={<p>Resumo de engajamento</p>}
      learningSection={<section aria-label='Seção de aprendizagem' />}
      learningSummary={<p>Resumo de aprendizagem</p>}
    />,
  )
}

describe('ProgressPanelLayout', () => {
  afterEach(cleanup)

  it('renders the four slots in board order', () => {
    renderLayout()

    const learningSummary = screen.getByText('Resumo de aprendizagem')
    const engagementSummary = screen.getByText('Resumo de engajamento')
    const learningSection = screen.getByRole('region', { name: 'Seção de aprendizagem' })
    const engagementSection = screen.getByRole('region', { name: 'Seção de engajamento' })
    const followingOrder = Node.DOCUMENT_POSITION_FOLLOWING

    expect(
      learningSummary.compareDocumentPosition(engagementSummary) & followingOrder,
    ).toBe(followingOrder)
    expect(
      engagementSummary.compareDocumentPosition(learningSection) & followingOrder,
    ).toBe(followingOrder)
    expect(
      learningSection.compareDocumentPosition(engagementSection) & followingOrder,
    ).toBe(followingOrder)
  })

  it('keeps each summary slot in its own two-column track', () => {
    renderLayout()

    const learningTrack = screen.getByText('Resumo de aprendizagem').parentElement
    const engagementTrack = screen.getByText('Resumo de engajamento').parentElement

    expect(learningTrack).toHaveClass('grid-cols-2', 'lg:col-span-2')
    expect(engagementTrack).toHaveClass('grid-cols-2', 'lg:col-span-2')
    expect(learningTrack?.parentElement).toBe(engagementTrack?.parentElement)
    expect(learningTrack?.parentElement).toHaveClass('lg:grid-cols-4')
  })
})
