import type { Page } from '@playwright/test'

import type { AccountAppearance } from '../../src/core/identity/account-appearance'

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
  appearance: 'dark' as AccountAppearance,
}

export async function installAccountBackend(
  page: Page,
  options: {
    timeZone?: string | null
    appearance?: AccountAppearance
    profileFailure?: number
    passwordFailure?: number
    passwordLost?: boolean
    malformed?: boolean
    deletionFailure?: number
    deletionResponseLost?: boolean
  } = {},
) {
  let profile = {
    ...INITIAL_PROFILE,
    timeZone: options.timeZone === undefined ? 'UTC' : options.timeZone,
    appearance: options.appearance ?? INITIAL_PROFILE.appearance,
  }
  const profileRequests: unknown[] = []
  const passwordRequests: unknown[] = []
  const prepareRequests: unknown[] = []
  const deletionRequests: unknown[] = []
  let deletionStatusRequests = 0
  let isClosed = false
  await page.route('**/_serverFn/**', async (route) => {
    const functionId = Buffer.from(
      new URL(route.request().url()).pathname.split('/').at(-1) ?? '',
      'base64url',
    ).toString()
    if (
      functionId.includes('routes/account/route.tsx') ||
      functionId.includes('requireAccountAccessOrDeletionStatus') ||
      functionId.includes('account/route.tsx')
    ) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          result: {
            accountDeletionStatus: isClosed
              ? {
                  state: 'closed',
                  closed_at: '2026-11-21T12:00:00Z',
                  erasure: 'pending',
                }
              : null,
            displayName: isClosed ? '' : profile.displayName,
            email: isClosed ? '' : profile.email,
          },
        }),
      })
      return
    }
    if (!functionId.includes('middlewares/require-auth-middleware.ts')) {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        result: {
          displayName: profile.displayName,
          email: profile.email,
          appearance: profile.appearance,
        },
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
  await page.route('**/api/auth/account/deletion/prepare', async (route) => {
    expect(route.request().method()).toBe('POST')
    prepareRequests.push(route.request().postDataJSON())
    await route.fulfill({
      status: 201,
      headers: {
        'cache-control': 'no-store',
        'set-cookie':
          'shifu-account-erasure=mock-signed-recovery; Path=/; Max-Age=86400; HttpOnly; Secure; SameSite=Strict',
      },
      contentType: 'application/json',
      body: JSON.stringify({ state: 'prepared' }),
    })
  })
  await page.route('**/api/auth/account/deletion', async (route) => {
    if (route.request().method() === 'GET') {
      deletionStatusRequests += 1
      await route.fulfill({
        status: isClosed ? 200 : 403,
        headers: { 'cache-control': 'no-store' },
        contentType: 'application/json',
        body: JSON.stringify(
          isClosed
            ? {
                state: 'closed',
                closedAt: '2026-11-21T12:00:00Z',
                erasure: 'pending',
              }
            : { code: 'preparation_expired' },
        ),
      })
      return
    }

    expect(route.request().method()).toBe('POST')
    deletionRequests.push(route.request().postDataJSON())
    if (options.deletionFailure) {
      await route.fulfill({
        status: options.deletionFailure,
        headers: { 'cache-control': 'no-store' },
        contentType: 'application/json',
        body: JSON.stringify({ code: 'invalid_current_password' }),
      })
      return
    }
    isClosed = true
    if (options.deletionResponseLost) {
      await route.abort('connectionreset')
      return
    }
    await route.fulfill({
      status: 202,
      headers: { 'cache-control': 'no-store' },
      contentType: 'application/json',
      body: JSON.stringify({
        state: 'closed',
        closedAt: '2026-11-21T12:00:00Z',
        erasure: 'pending',
      }),
    })
  })
  return {
    profileRequests,
    passwordRequests,
    prepareRequests,
    deletionRequests,
    get deletionStatusRequests() {
      return deletionStatusRequests
    },
    get isClosed() {
      return isClosed
    },
    recoverProfile() {
      shouldFailProfile = undefined
    },
  }
}
