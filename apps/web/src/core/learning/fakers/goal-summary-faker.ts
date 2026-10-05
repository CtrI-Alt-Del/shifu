import { faker } from '@faker-js/faker'

import type { GoalSummary } from '@/core/learning/goal-summary'

export class GoalSummaryFaker {
  static fake(overrides: Partial<GoalSummary> = {}): GoalSummary {
    return {
      description: faker.lorem.sentence(),
      id: fakeUlid(),
      skillCount: faker.number.int({ min: 1, max: 8 }),
      title: faker.lorem.words(3),
      updatedAt: faker.date
        .recent({ refDate: new Date('2026-09-23T12:00:00Z') })
        .toISOString(),
      ...overrides,
    }
  }

  static fakeMany(count = 10): GoalSummary[] {
    return Array.from({ length: count }, () => GoalSummaryFaker.fake())
  }
}

function fakeUlid(): string {
  return faker.string.alphanumeric({ length: 26, casing: 'upper' })
}
