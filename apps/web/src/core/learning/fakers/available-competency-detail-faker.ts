import { faker } from '@faker-js/faker'

import type { AvailableCompetencyDetail } from '@/core/learning/competency-detail'

export class AvailableCompetencyDetailFaker {
  static fake(
    overrides: Partial<AvailableCompetencyDetail> = {},
  ): AvailableCompetencyDetail {
    const competencyId = fakeUlid()
    const activityId = fakeUlid()
    return {
      availability: 'available',
      goalId: fakeUlid(),
      skillId: fakeUlid(),
      skillName: faker.lorem.words(2),
      competencyId,
      competencyName: faker.lorem.words(3),
      progress: faker.number.int({ min: 0, max: 100 }),
      status: 'learning',
      isFocus: false,
      focusReturned: false,
      focusCompetencyId: null,
      focusCompetencyName: null,
      items: [
        {
          kind: 'activity',
          id: activityId,
          title: faker.lorem.words(4),
          position: 1,
          activityType: 'learning',
          difficulty: 'medium',
          latestScore: null,
        },
      ],
      recommendation: {
        competencyId,
        activityId,
        difficulty: 'medium',
        type: 'new-activity',
      },
      ...overrides,
    }
  }

  static fakeMany(count = 10): AvailableCompetencyDetail[] {
    return Array.from({ length: count }, () => AvailableCompetencyDetailFaker.fake())
  }
}

function fakeUlid(): string {
  return faker.string.alphanumeric({ length: 26, casing: 'upper' })
}
