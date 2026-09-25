import { createHash } from 'node:crypto'
import { Pool } from 'pg'
import type { Page } from '@playwright/test'

import { test as base, expect } from '@playwright/test'

const databaseURL =
  process.env.BETTER_AUTH_DATABASE_URL ??
  'postgresql://shifu:shifu-local@localhost:54344/shifu'

const password = 'shifu-test-password'
const passwordHash =
  '$argon2id$v=19$m=65536,t=3,p=4$NZOAC8u9ikq/le8/VMMOUw$DX2SZn2995YE57/aos2DXTVj4ocvfPZpLjKhULhp3Mg'

export const signInPassword = password
export const signInPasswordHash = passwordHash

export type SignInHandlerAccount = {
  accountId: string
  email: string
  ipAddress: string
}

type IdentityModuleFixtures = {
  authenticatedPage: Page
  activeAccount: SignInHandlerAccount
  pendingAccount: SignInHandlerAccount
}

export const test = base.extend<IdentityModuleFixtures>({
  authenticatedPage: async ({ page }, use) => {
    await page.route('**/_serverFn/**', async (route) => {
      const serverFunction = Buffer.from(
        new URL(route.request().url()).pathname.split('/').at(-1) ?? '',
        'base64url',
      ).toString()

      if (
        !serverFunction.includes('middlewares/require-auth-middleware.ts') &&
        !serverFunction.includes('middlewares/enter-main-page-middleware.ts')
      ) {
        await route.continue()
        return
      }

      await route.fulfill({
        body: JSON.stringify({
          result: {
            displayName: 'Playwright Learner',
            email: 'playwright@shifu.local',
          },
        }),
        contentType: 'application/json',
        status: 200,
      })
    })

    try {
      await page.goto('/login/')
      await page.waitForFunction(() => '__TSR_ROUTER__' in window)
      await use(page)
    } finally {
      await page.unroute('**/_serverFn/**')
    }
  },
  activeAccount: async ({ browserName }, use, testInfo) => {
    void browserName
    const pool = new Pool({ connectionString: databaseURL })
    const account = makeAccount(testInfo.testId, 'active')
    await seedAccount(pool, account, 'active')

    try {
      await use(account)
    } finally {
      await cleanupAccount(pool, account)
      await pool.end()
    }
  },
  pendingAccount: async ({ browserName }, use, testInfo) => {
    void browserName
    const pool = new Pool({ connectionString: databaseURL })
    const account = makeAccount(testInfo.testId, 'pending')
    await seedAccount(pool, account, 'pending-confirmation')

    try {
      await use(account)
    } finally {
      await cleanupAccount(pool, account)
      await pool.end()
    }
  },
})

export { expect }

export async function navigateAuthenticatedPage(page: Page, route: string) {
  await page.evaluate((to) => {
    const router = (
      window as typeof window & {
        __TSR_ROUTER__: { navigate: (options: { to: string }) => Promise<void> }
      }
    ).__TSR_ROUTER__

    return router.navigate({ to })
  }, route)
}

function makeAccount(testId: string, kind: 'active' | 'pending') {
  const prefix = kind === 'active' ? '01SHI' : '01SHG'
  const hash = BigInt(
    `0x${createHash('sha256').update(`${kind}:${testId}`).digest('hex')}`,
  )
  const identifier = String(hash % 10n ** 21n).padStart(21, '0')
  const ipAddress = Number((hash % 254n) + 1n)

  return {
    accountId: `${prefix}${identifier}`,
    email: `handler-${kind}-${identifier}@shifu.local`,
    ipAddress: `198.51.${kind === 'active' ? '100' : '101'}.${ipAddress}`,
  }
}

async function seedAccount(
  pool: Pool,
  account: SignInHandlerAccount,
  status: 'active' | 'pending-confirmation',
) {
  await pool.query(
    `
      insert into identity_accounts (
        id, display_name, email, password_hash, status, access_version,
        time_zone, created_at, updated_at, confirmed_at, deleted_at, deletion_reason
      ) values ($1, $2, $3, $4, $5::text, 1, 'America/Sao_Paulo', now(), now(),
        case when $5::text = 'active' then now() else null end, null, null)
      on conflict (id) do update set
        display_name = excluded.display_name,
        email = excluded.email,
        password_hash = excluded.password_hash,
        status = excluded.status,
        access_version = excluded.access_version,
        confirmed_at = excluded.confirmed_at,
        deleted_at = null,
        deletion_reason = null
    `,
    [
      account.accountId,
      'Handler Test Learner',
      account.email,
      signInPasswordHash,
      status,
    ],
  )
}

async function cleanupAccount(pool: Pool, account: SignInHandlerAccount) {
  await pool.query("delete from events where payload->>'account_id' = $1", [
    account.accountId,
  ])
  await pool.query('delete from better_auth_verifications where value like $1', [
    `%${account.accountId}%`,
  ])
  await pool.query('delete from better_auth_sessions where user_id = $1', [
    account.accountId,
  ])
  await pool.query('delete from better_auth_accounts where user_id = $1', [
    account.accountId,
  ])
  await pool.query('delete from better_auth_users where id = $1', [account.accountId])
  await pool.query('delete from better_auth_rate_limits where key like $1', [
    `${account.ipAddress}%`,
  ])
  await pool.query('delete from identity_accounts where id = $1', [account.accountId])
}
