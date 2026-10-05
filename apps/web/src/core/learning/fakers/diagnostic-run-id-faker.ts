import { faker } from '@faker-js/faker'

export class DiagnosticRunIdFaker {
  static fake(): string {
    return faker.string.uuid()
  }

  static fakeMany(count = 10): string[] {
    return Array.from({ length: count }, () => DiagnosticRunIdFaker.fake())
  }
}
