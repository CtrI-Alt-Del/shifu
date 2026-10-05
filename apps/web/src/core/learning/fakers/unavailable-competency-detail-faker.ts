import { faker } from '@faker-js/faker'

import type { UnavailableCompetencyDetail } from '@/core/learning/competency-detail'

export class UnavailableCompetencyDetailFaker {
  static fake(
    overrides: Partial<UnavailableCompetencyDetail> = {},
  ): UnavailableCompetencyDetail {
    return {
      availability: 'unavailable',
      goalId: fakeUlid(),
      skillId: fakeUlid(),
      skillName: faker.lorem.words(2),
      competencyId: fakeUlid(),
      competencyName: faker.lorem.words(3),
      focusCompetencyId: null,
      focusCompetencyName: null,
      ...overrides,
    }
  }

  static fakeMany(count = 10): UnavailableCompetencyDetail[] {
    return Array.from({ length: count }, () => UnavailableCompetencyDetailFaker.fake())
  }
}

function fakeUlid(): string {
  return faker.string.alphanumeric({ length: 26, casing: 'upper' })
}
