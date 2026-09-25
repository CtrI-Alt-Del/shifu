import { ROUTES } from '../../../src/constants/routes'

import { expect, test } from '../../playwright'

test.describe('PendingConfirmationPage', () => {
  test('exits the pending context and redirects to Entrar', async ({ page }) => {
    let requestCount = 0
    const requests: Array<{ method: string; pathname: string }> = []
    let releaseResponse: () => void = () => undefined
    const responseReady = new Promise<void>((resolve) => {
      releaseResponse = resolve
    })

    await page.route('**/api/auth/pending-confirmation/sign-out', async (route) => {
      requestCount += 1
      requests.push({
        method: route.request().method(),
        pathname: new URL(route.request().url()).pathname,
      })
      await responseReady
      await route.fulfill({ body: '{}', contentType: 'application/json', status: 200 })
    })

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(`${ROUTES.pendingConfirmation}/`)
    await page.waitForFunction(() => '__TSR_ROUTER__' in window)
    await page.waitForLoadState('networkidle')

    await expect(
      page.getByRole('heading', { name: 'Aguardando confirmação' }),
    ).toBeVisible()
    await page.getByRole('button', { name: 'Sair' }).click()
    await expect(page.getByRole('button', { name: 'Saindo...' })).toBeDisabled()
    await expect.poll(() => requestCount).toBe(1)
    releaseResponse()

    await expect(page).toHaveURL(/\/login\/?$/)
    expect(requestCount).toBe(1)
    expect(requests).toEqual([
      { method: 'POST', pathname: '/api/auth/pending-confirmation/sign-out' },
    ])
  })

  test('keeps the pending page usable and retries after a safe failure', async ({
    page,
  }) => {
    let requestCount = 0
    const requests: Array<{ method: string; pathname: string }> = []
    let releaseFirstResponse: () => void = () => undefined
    const firstResponseReady = new Promise<void>((resolve) => {
      releaseFirstResponse = resolve
    })

    await page.route('**/api/auth/pending-confirmation/sign-out', async (route) => {
      requestCount += 1
      requests.push({
        method: route.request().method(),
        pathname: new URL(route.request().url()).pathname,
      })
      if (requestCount === 1) {
        await firstResponseReady
        await route.fulfill({
          body: JSON.stringify({ message: 'unavailable' }),
          contentType: 'application/json',
          status: 503,
        })
        return
      }

      await route.fulfill({ body: '{}', contentType: 'application/json', status: 200 })
    })

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(`${ROUTES.pendingConfirmation}/`)
    await page.waitForFunction(() => '__TSR_ROUTER__' in window)
    await page.getByRole('button', { name: 'Sair' }).click()

    await expect(page.getByRole('button', { name: 'Saindo...' })).toBeDisabled()
    await expect.poll(() => requestCount).toBe(1)
    releaseFirstResponse()

    await expect(page.getByRole('alert')).toHaveText(
      'Não foi possível sair agora. Tente novamente.',
    )
    await expect(page).toHaveURL(/\/pending-confirmation\/?$/)

    await page.getByRole('button', { name: 'Sair' }).click()
    await expect(page).toHaveURL(/\/login\/?$/)
    expect(requestCount).toBe(2)
    expect(requests).toEqual([
      { method: 'POST', pathname: '/api/auth/pending-confirmation/sign-out' },
      { method: 'POST', pathname: '/api/auth/pending-confirmation/sign-out' },
    ])
  })
})
