import type { Page, Route } from '@playwright/test'

type BffRouteHandler = (route: Route) => void | Promise<void>

export type BffFixtureContract = {
  route: (handler: BffRouteHandler) => Promise<void>
}

export const BffFixture = (page: Page): BffFixtureContract => ({
  route: async (handler) => {
    await page.route('**/_serverFn/**', handler)
  },
})
