import { faker } from '@faker-js/faker'

import type { ChoiceResultQuestion } from '@/core/learning/choice-activity'

export class ChoiceResultQuestionFaker {
  static fake(
    overrides: Partial<ChoiceResultQuestion> = {},
    options: { revealCorrectOptionKeys?: boolean } = {},
  ): ChoiceResultQuestion {
    return {
      key: faker.string.alphanumeric({ length: 6 }),
      prompt: faker.lorem.sentence(),
      submittedOptionKeys: ['a'],
      score: 100,
      isCorrect: true,
      explanation: faker.lorem.sentence(),
      ...(options.revealCorrectOptionKeys === false ? {} : { correctOptionKeys: ['a'] }),
      ...overrides,
    }
  }

  static fakeMany(count = 10): ChoiceResultQuestion[] {
    return Array.from({ length: count }, () => ChoiceResultQuestionFaker.fake())
  }
}
