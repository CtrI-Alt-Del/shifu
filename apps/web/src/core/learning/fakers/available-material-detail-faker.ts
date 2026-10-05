import { faker } from '@faker-js/faker'

import type { AvailableMaterialDetail } from '@/core/learning/material-detail'

export class AvailableMaterialDetailFaker {
  static fake(overrides: Partial<AvailableMaterialDetail> = {}): AvailableMaterialDetail {
    return {
      availability: 'available',
      goalId: fakeUlid(),
      skillId: fakeUlid(),
      skillName: faker.lorem.words(2),
      competencyId: fakeUlid(),
      competencyName: faker.lorem.words(3),
      materialId: fakeUlid(),
      materialTitle: faker.lorem.words(3),
      content: faker.lorem.paragraphs(2),
      recommendation: null,
      ...overrides,
    }
  }

  static fakeMany(count = 10): AvailableMaterialDetail[] {
    return Array.from({ length: count }, () => AvailableMaterialDetailFaker.fake())
  }
}

function fakeUlid(): string {
  return faker.string.alphanumeric({ length: 26, casing: 'upper' })
}
