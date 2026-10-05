import { faker } from '@faker-js/faker'

export class IdentityDisplayNameFaker {
  static fake(): string {
    return faker.person.fullName()
  }

  static fakeMany(count = 10): string[] {
    return Array.from({ length: count }, () => IdentityDisplayNameFaker.fake())
  }
}
