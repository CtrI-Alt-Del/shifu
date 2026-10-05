import { faker } from '@faker-js/faker'

import type { ChoiceQuestion } from '@/core/learning/choice-activity'

export class ChoiceQuestionFaker {
  static fake(overrides: Partial<ChoiceQuestion> = {}): ChoiceQuestion {
    return {
      key: faker.string.alphanumeric({ length: 6 }),
      kind: 'single_choice',
      prompt: faker.lorem.sentence(),
      options: [
        { key: 'a', text: faker.word.noun() },
        { key: 'b', text: faker.word.noun() },
      ],
      ...overrides,
    }
  }

  static fakeMany(count = 10): ChoiceQuestion[] {
    return Array.from({ length: count }, () => ChoiceQuestionFaker.fake())
  }
}
