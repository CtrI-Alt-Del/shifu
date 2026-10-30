import type { Page } from '@playwright/test'

import { expect } from '../playwright'

/**
 * Mocked transport for the account section suites. It answers the route-protection
 * server function and the Better Auth account endpoints the account pages call, so
 * the suites prove rendered contracts and outgoing requests, not real persistence.
 */
export const INITIAL_PROFILE = {
  accountId: 'account-test',
  displayName: 'Playwright Learner',
  email: 'playwright@shifu.local',
  timeZone: 'UTC' as string | null,
}

export async function installAccountBackend(
  page: Page,
  options: {
    timeZone?: string | null
    profileFailure?: number
    passwordFailure?: number
    passwordLost?: boolean
    malformed?: boolean
  } = {},
) {
  let profile = {
    ...INITIAL_PROFILE,
    timeZone: options.timeZone === undefined ? 'UTC' : options.timeZone,
  }
  const profileRequests: unknown[] = []
  const passwordRequests: unknown[] = []
  await page.route('**/_serverFn/**', async (route) => {
    const functionId = Buffer.from(
      new URL(route.request().url()).pathname.split('/').at(-1) ?? '',
      'base64url',
    ).toString()
    if (!functionId.includes('middlewares/require-auth-middleware.ts')) {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        result: { displayName: profile.displayName, email: profile.email },
      }),
    })
  })
  let shouldFailProfile = options.profileFailure
  await page.route('**/api/auth/account', async (route) => {
    expect(route.request().method()).toBe('GET')
    await route.fulfill({
      status: shouldFailProfile ?? 200,
      contentType: 'application/json',
      body: JSON.stringify(
        shouldFailProfile
          ? { message: 'Indisponível.' }
          : options.malformed
            ? { unexpected: true }
            : profile,
      ),
    })
  })
  await page.route('**/api/auth/account/profile', async (route) => {
    expect(route.request().method()).toBe('POST')
    const body = route.request().postDataJSON()
    profileRequests.push(body)
    if (!shouldFailProfile) profile = { ...profile, ...body }
    await route.fulfill({
      status: shouldFailProfile ?? 200,
      contentType: 'application/json',
      body: JSON.stringify(
        shouldFailProfile
          ? { message: 'Revise o perfil.', field: 'displayName' }
          : profile,
      ),
    })
  })
  await page.route('**/api/auth/account/password', async (route) => {
    expect(route.request().method()).toBe('POST')
    passwordRequests.push(route.request().postDataJSON())
    if (options.passwordLost) {
      await route.abort('failed')
      return
    }
    await route.fulfill({
      status: options.passwordFailure ?? 200,
      contentType: 'application/json',
      body: JSON.stringify(
        options.passwordFailure
          ? { message: 'Senha atual incorreta.', code: 'invalid_current_password' }
          : { changed: true },
      ),
    })
  })
  return {
    profileRequests,
    passwordRequests,
    recoverProfile() {
      shouldFailProfile = undefined
    },
  }
}
