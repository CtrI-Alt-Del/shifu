import { faker } from '@faker-js/faker'

export type Planning = {
  planningId: string
}

export class PlanningFaker {
  static fake(overrides: Partial<Planning> = {}): Planning {
    return {
      planningId: faker.string.uuid(),
      ...overrides,
    }
  }

  static fakeMany(count = 10): Planning[] {
    return Array.from({ length: count }, () => PlanningFaker.fake())
  }
}
