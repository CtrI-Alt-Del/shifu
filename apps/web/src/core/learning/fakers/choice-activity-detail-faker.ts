import { faker } from '@faker-js/faker'

import type { ChoiceActivityDetail } from '@/core/learning/choice-activity'
import { ChoiceQuestionFaker } from './choice-question-faker'

export class ChoiceActivityDetailFaker {
  static fake(overrides: Partial<ChoiceActivityDetail> = {}): ChoiceActivityDetail {
    return {
      activityId: faker.string.alphanumeric({ length: 26, casing: 'upper' }),
      title: faker.lorem.words(4),
      difficulty: 'medium',
      canSubmit: true,
      latestAttemptId: null,
      unresolvedAttemptId: null,
      questions: [ChoiceQuestionFaker.fake()],
      ...overrides,
    }
  }

  static fakeMany(count = 10): ChoiceActivityDetail[] {
    return Array.from({ length: count }, () => ChoiceActivityDetailFaker.fake())
  }
}
