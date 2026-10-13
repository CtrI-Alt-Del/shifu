/** Shared Playwright fixture factory for module-owned browser suites. */

import { test as base } from './fixtures/identity-module-fixture'
import { BffFixture } from './fixtures/bff-fixture'
import { MentorStreamFixture } from './fixtures/mentor-stream-fixture'

export {
  expect,
  navigateAuthenticatedPage,
  signInPassword,
  signInPasswordHash,
} from './fixtures/identity-module-fixture'

export const test = base.extend<{
  bff: ReturnType<typeof BffFixture>
  mentorStream: ReturnType<typeof MentorStreamFixture>
}>({
  mentorStream: async ({ request, activeAccount }, use, testInfo) => {
    const fixture = MentorStreamFixture(request, activeAccount, testInfo.testId)
    try {
      await use(fixture)
    } finally {
      await fixture.dispose()
    }
  },
  bff: async ({ authenticatedPage }, use) => {
    await use(BffFixture(authenticatedPage))
  },
})
