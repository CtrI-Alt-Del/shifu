import { IdentityDisplayNameFaker } from './identity-display-name-faker'
import { IdentityEmailFaker } from './identity-email-faker'

export type IdentityRegistrationData = {
  displayName: string
  email: string
}

export class IdentityRegistrationDataFaker {
  static fake(
    overrides: Partial<IdentityRegistrationData> = {},
  ): IdentityRegistrationData {
    return {
      displayName: IdentityDisplayNameFaker.fake(),
      email: IdentityEmailFaker.fake(),
      ...overrides,
    }
  }

  static fakeMany(
    count = 10,
    overrides: Partial<IdentityRegistrationData> = {},
  ): IdentityRegistrationData[] {
    return Array.from({ length: count }, () =>
      IdentityRegistrationDataFaker.fake(overrides),
    )
  }
}
