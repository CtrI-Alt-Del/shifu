import { faker } from '@faker-js/faker'

import type { UnavailableMaterialDetail } from '@/core/learning/material-detail'

export class UnavailableMaterialDetailFaker {
  static fake(
    overrides: Partial<UnavailableMaterialDetail> = {},
  ): UnavailableMaterialDetail {
    return {
      availability: 'unavailable',
      goalId: fakeUlid(),
      skillId: fakeUlid(),
      skillName: faker.lorem.words(2),
      competencyId: fakeUlid(),
      competencyName: faker.lorem.words(3),
      materialId: fakeUlid(),
      focusCompetencyId: fakeUlid(),
      focusCompetencyName: faker.lorem.words(3),
      ...overrides,
    }
  }

  static fakeMany(count = 10): UnavailableMaterialDetail[] {
    return Array.from({ length: count }, () => UnavailableMaterialDetailFaker.fake())
  }
}

function fakeUlid(): string {
  return faker.string.alphanumeric({ length: 26, casing: 'upper' })
}
