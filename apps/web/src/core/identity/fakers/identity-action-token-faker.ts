import { faker } from '@faker-js/faker'

export class IdentityActionTokenFaker {
  static fake(): string {
    return faker.string.alphanumeric({ length: 43 })
  }

  static fakeMany(count = 10): string[] {
    return Array.from({ length: count }, () => IdentityActionTokenFaker.fake())
  }
}
