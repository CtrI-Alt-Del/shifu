/** Shared Playwright fixture factory for module-owned browser suites. */

import { test as base } from './fixtures/identity-module-fixture'
import { BffFixture } from './fixtures/bff-fixture'

export {
  expect,
  navigateAuthenticatedPage,
  signInPassword,
  signInPasswordHash,
} from './fixtures/identity-module-fixture'

export const test = base.extend<{ bff: ReturnType<typeof BffFixture> }>({
  bff: async ({ authenticatedPage }, use) => {
    await use(BffFixture(authenticatedPage))
  },
})
