import { faker } from '@faker-js/faker'

export type IdentityEmailFakerOptions = {
  domain?: string
  suffix?: string
}

export class IdentityEmailFaker {
  static fake(options: IdentityEmailFakerOptions = {}): string {
    const domain = options.domain ?? 'example.com'
    const username = faker.internet.username().toLowerCase()
    const suffix = options.suffix ? `-${options.suffix}` : ''

    return `${username}${suffix}@${domain}`
  }

  static fakeMany(count = 10, options: IdentityEmailFakerOptions = {}): string[] {
    return Array.from({ length: count }, () => IdentityEmailFaker.fake(options))
  }
}
