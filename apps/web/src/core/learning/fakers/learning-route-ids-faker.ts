import { faker } from '@faker-js/faker'

export type LearningRouteIds = {
  goalId: string
  skillId: string
  skillExperienceId: string
  competencyId: string
  otherCompetencyId: string
  activityId: string
  attemptId: string
  evaluationId: string
  materialId: string
  targetConceptId: string
  nextCompetencyId: string
  nextActivityId: string
}

export class LearningRouteIdsFaker {
  static fake(overrides: Partial<LearningRouteIds> = {}): LearningRouteIds {
    return {
      goalId: fakeUlid(),
      skillId: fakeUlid(),
      skillExperienceId: fakeUlid(),
      competencyId: fakeUlid(),
      otherCompetencyId: fakeUlid(),
      activityId: fakeUlid(),
      attemptId: fakeUlid(),
      evaluationId: fakeUlid(),
      materialId: fakeUlid(),
      targetConceptId: fakeUlid(),
      nextCompetencyId: fakeUlid(),
      nextActivityId: fakeUlid(),
      ...overrides,
    }
  }

  static fakeMany(count = 10): LearningRouteIds[] {
    return Array.from({ length: count }, () => LearningRouteIdsFaker.fake())
  }
}

function fakeUlid(): string {
  return faker.string.alphanumeric({ length: 26, casing: 'upper' })
}
