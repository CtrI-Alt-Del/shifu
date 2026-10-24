import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ActivityRecommendation } from '@/core/learning/competency-detail'

const ids = {
  goalId: 'goal-1',
  skillId: 'skill-1',
  competencyId: 'competency-1',
  activityId: 'activity-1',
  attemptId: 'attempt-1',
}

const mocks = vi.hoisted(() => ({
  navigateTo: vi.fn(),
  useParams: vi.fn(),
  choiceResultPage: vi.fn((_props: unknown) => <div data-testid='choice-result-page' />),
}))

vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => (options: unknown) => ({
    useParams: mocks.useParams,
    options,
  }),
}))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: () => ({ navigateTo: mocks.navigateTo }),
}))
vi.mock('@/ui/gamification/widgets/components/activity-xp-reward-band', () => ({
  ActivityXpRewardBand: (props: { activityId: string; attemptId: string }) => (
    <div
      data-activity-id={props.activityId}
      data-attempt-id={props.attemptId}
      data-testid='reward-band'
    />
  ),
}))
vi.mock('@/ui/learning/widgets/pages/choice-result-page', () => ({
  ChoiceResultPage: (props: unknown) => mocks.choiceResultPage(props),
}))

import { Route } from '..'

type AttemptIndexRouteOptions = { component: () => React.ReactElement }

function routeOptions() {
  return (Route as unknown as { options: AttemptIndexRouteOptions }).options
}

describe('AttemptIndexRoute', () => {
  afterEach(cleanup)

  it('renders the result page with the ids, the reward band, and working navigation callbacks', () => {
    mocks.useParams.mockReturnValue(ids)

    const Component = routeOptions().component
    render(<Component />)

    expect(screen.getByTestId('choice-result-page')).toBeInTheDocument()
    const props = mocks.choiceResultPage.mock.calls.at(-1)?.[0] as {
      goalId: string
      skillId: string
      competencyId: string
      activityId: string
      attemptId: string
      rewardBand: React.ReactElement
      onOpenRecommendation: (recommendation: ActivityRecommendation) => void
      onSessionExpired: () => void
    }

    expect(props).toMatchObject(ids)
    expect(props.rewardBand.props).toMatchObject({
      activityId: ids.activityId,
      attemptId: ids.attemptId,
    })

    props.onSessionExpired()
    expect(mocks.navigateTo).toHaveBeenCalledWith('login')

    const recommendation: ActivityRecommendation = {
      competencyId: 'competency-2',
      activityId: 'activity-2',
      difficulty: 'medium',
      type: 'reinforcement',
    }
    props.onOpenRecommendation(recommendation)
    expect(mocks.navigateTo).toHaveBeenCalledWith('learningActivity', {
      goalId: ids.goalId,
      skillId: ids.skillId,
      competencyId: recommendation.competencyId,
      activityId: recommendation.activityId,
    })
  })
})
