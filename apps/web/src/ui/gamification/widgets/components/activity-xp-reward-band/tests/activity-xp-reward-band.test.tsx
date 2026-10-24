import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ActivityXpRewardBand } from '..'
import {
  type ActivityXpRewardBandState,
  useActivityXpRewardBand,
} from '../use-activity-xp-reward-band'

vi.mock('../use-activity-xp-reward-band', () => ({
  useActivityXpRewardBand: vi.fn(),
}))

const useActivityXpRewardBandMock = vi.mocked(useActivityXpRewardBand)

const ACTIVITY_ID = 'activity-1'
const ATTEMPT_ID = 'attempt-1'

function mockState(state: ActivityXpRewardBandState) {
  useActivityXpRewardBandMock.mockReturnValue(state)
}

describe('ActivityXpRewardBand', () => {
  afterEach(cleanup)

  beforeEach(() => mockState({ status: 'pending' }))

  it('identifies the pending state from its own text and announces it politely', () => {
    render(<ActivityXpRewardBand activityId={ACTIVITY_ID} attemptId={ATTEMPT_ID} />)

    const band = screen.getByLabelText('Recompensa de XP desta Atividade')
    expect(band).toHaveAttribute('aria-live', 'polite')
    expect(band).toHaveTextContent('Confirmando o XP desta Atividade')
  })

  it('shows the confirmed additional XP and the cumulative amounts when granted', () => {
    mockState({ status: 'granted', additionalXp: 6, grantedXp: 6, maximumXp: 10 })

    render(<ActivityXpRewardBand activityId={ACTIVITY_ID} attemptId={ATTEMPT_ID} />)

    expect(screen.getByText('+6 XP')).toBeVisible()
    expect(screen.getByText('6 de 10 XP confirmados nesta Atividade.')).toBeVisible()
  })

  it('states plainly that no additional XP was earned, never a loss', () => {
    mockState({ status: 'no-additional', grantedXp: 10, maximumXp: 10 })

    render(<ActivityXpRewardBand activityId={ACTIVITY_ID} attemptId={ATTEMPT_ID} />)

    const band = screen.getByLabelText('Recompensa de XP desta Atividade')
    expect(band).toHaveTextContent('não gerou XP adicional')
    expect(band).not.toHaveTextContent(/perdeu|perda|-\d/u)
  })

  it('states the unavailable outcome without inventing an amount', () => {
    mockState({ status: 'unavailable' })

    render(<ActivityXpRewardBand activityId={ACTIVITY_ID} attemptId={ATTEMPT_ID} />)

    const band = screen.getByLabelText('Recompensa de XP desta Atividade')
    expect(band).toHaveTextContent('Não foi possível confirmar o XP agora')
    expect(band).not.toHaveTextContent(/[+-]\s*\d/u)
  })
})
