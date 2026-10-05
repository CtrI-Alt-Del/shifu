import { faker } from '@faker-js/faker'

import type { ChoiceAttemptDetail } from '@/core/learning/choice-activity'

export class ChoiceAttemptDetailFaker {
  static fake(overrides: Partial<ChoiceAttemptDetail> = {}): ChoiceAttemptDetail {
    return {
      attemptId: faker.string.alphanumeric({ length: 26, casing: 'upper' }),
      activityId: faker.string.alphanumeric({ length: 26, casing: 'upper' }),
      status: 'pending',
      submittedAt: faker.date
        .recent({ refDate: new Date('2026-09-23T12:00:00Z') })
        .toISOString(),
      retryAllowed: false,
      ...overrides,
    }
  }

  static fakeMany(count = 10): ChoiceAttemptDetail[] {
    return Array.from({ length: count }, () => ChoiceAttemptDetailFaker.fake())
  }
}
