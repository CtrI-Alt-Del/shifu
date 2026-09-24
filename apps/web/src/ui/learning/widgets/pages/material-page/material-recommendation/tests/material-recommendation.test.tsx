import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ActivityRecommendation } from '@/core/learning/competency-detail'

import { MaterialRecommendation } from '..'

const recommendation: ActivityRecommendation = {
  activityId: '01SHF000000000000000000005',
  competencyId: '01SHF000000000000000000001',
  difficulty: 'hard',
  type: 'new-activity',
}

function renderWidget(
  overrides: Partial<Parameters<typeof MaterialRecommendation>[0]> = {},
) {
  const onOpen = vi.fn()

  render(
    <MaterialRecommendation
      competencyName='Estruturas de repetição'
      hasFailure={false}
      isPending={false}
      onOpen={onOpen}
      recommendation={recommendation}
      {...overrides}
    />,
  )

  return { onOpen }
}

describe('MaterialRecommendation', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('names the Competency of origin and describes the recommendation in pt-BR', () => {
    renderWidget()

    expect(
      screen.getByRole('heading', { name: 'Continuar em Estruturas de repetição' }),
    ).toBeVisible()
    expect(screen.getByText('Atividade nova · Difícil')).toBeVisible()
  })

  it('labels a reinforcement recommendation with its own pt-BR wording', () => {
    renderWidget({
      recommendation: { ...recommendation, difficulty: 'medium', type: 'reinforcement' },
    })

    expect(screen.getByText('Reforço · Média')).toBeVisible()
  })

  it('delegates the selection to its owner', () => {
    const { onOpen } = renderWidget()

    fireEvent.click(screen.getByRole('button', { name: 'Praticar' }))

    expect(onOpen).toHaveBeenCalledTimes(1)
  })

  it('blocks a duplicate selection while the Activity is opening', () => {
    const { onOpen } = renderWidget({ isPending: true })

    const button = screen.getByRole('button', { name: 'Abrindo...' })
    fireEvent.click(button)

    expect(button).toBeDisabled()
    expect(onOpen).not.toHaveBeenCalled()
  })

  it('reports a failure to open the Activity without hiding the action', () => {
    renderWidget({ hasFailure: true })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível abrir a Atividade agora. O material continua aqui — tente novamente.',
    )
    expect(screen.getByRole('button', { name: 'Praticar' })).toBeEnabled()
  })

  it('shows no failure message on the normal state', () => {
    renderWidget()

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
