import { faker } from '@faker-js/faker'

import type { GoalDetail } from '@/core/learning/goal-detail'

export class GoalDetailFaker {
  static fake(overrides: Partial<GoalDetail> = {}): GoalDetail {
    const skillId = fakeUlid()
    return {
      goalId: fakeUlid(),
      title: faker.lorem.words(3),
      description: faker.lorem.sentence(),
      skills: [
        {
          skillExperienceId: fakeUlid(),
          skillId,
          name: faker.lorem.words(2),
          status: 'learning',
          progress: faker.number.int({ min: 1, max: 99 }),
          inclusionReason: faker.lorem.sentence(),
        },
      ],
      relations: [],
      ...overrides,
    }
  }

  static fakeMany(count = 10): GoalDetail[] {
    return Array.from({ length: count }, () => GoalDetailFaker.fake())
  }
}

function fakeUlid(): string {
  return faker.string.alphanumeric({ length: 26, casing: 'upper' })
}
