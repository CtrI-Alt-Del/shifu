import { Pool } from 'pg'

import { test, expect } from '../playwright'

const databaseURL =
  process.env.BETTER_AUTH_DATABASE_URL ??
  'postgresql://shifu:shifu-local@localhost:54344/shifu'

test('renders the dashboard and records a main-page entry for an active session', async ({
  authenticatedPage,
  authenticatedAccountId,
}) => {
  const pool = new Pool({ connectionString: databaseURL })
  const before = await pool.query(
    "select count(*)::int as count from events where payload->>'account_id' = $1",
    [authenticatedAccountId],
  )

  await authenticatedPage.goto('/')

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Dê forma ao que você quer aprender.',
    }),
  ).toBeVisible()

  await expect
    .poll(
      async () => {
        const result = await pool.query(
          "select count(*)::int as count from events where payload->>'account_id' = $1",
          [authenticatedAccountId],
        )
        return result.rows[0].count
      },
      { timeout: 5_000 },
    )
    .toBe(before.rows[0].count + 1)

  await pool.end()
})

test('redirects an anonymous visitor before the dashboard renders', async ({ page }) => {
  await page.goto('/')

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', { level: 1, name: 'Dê forma ao que você quer aprender.' }),
  ).not.toBeVisible()
})
