import { expect, test } from '../playwright'

import { IdentityEmailFaker } from '../../src/core/identity/fakers'

test.describe('SignInPage', () => {
  test('renders a public responsive form with canonical sibling links', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 })

    await page.goto('/login/')

    await expect(page.getByRole('heading', { level: 1, name: 'Entrar' })).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'E-mail' })).toHaveValue(
      'student.seed@shifu.com',
    )
    await expect(page.getByRole('textbox', { name: 'E-mail' })).toHaveAttribute(
      'placeholder',
      'voce@exemplo.com',
    )
    await expect(page.getByRole('textbox', { name: 'Senha' })).toHaveValue(
      'ShifuSeed123!',
    )
    await expect(page.getByRole('textbox', { name: 'Senha' })).toHaveAttribute(
      'placeholder',
      '••••••••',
    )
    await expect(
      page.getByRole('navigation', { name: 'Navegação principal' }),
    ).not.toBeVisible()
    await expect(page.getByRole('link', { name: 'Criar conta' })).toHaveAttribute(
      'href',
      '/register',
    )
    await expect(page.getByRole('link', { name: 'Esqueci minha senha' })).toHaveAttribute(
      'href',
      '/forgot-password',
    )
    await expect(
      page.getByRole('link', { name: 'Política de privacidade' }),
    ).toHaveAttribute('href', '/privacy')
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(375)
    await page.getByRole('link', { name: 'Política de privacidade' }).click()
    await expect(page).toHaveURL(/\/privacy\/?$/)
    await expect(
      page.getByRole('heading', {
        level: 1,
        name: 'Política de privacidade',
      }),
    ).toBeVisible()
  })

  test('maps a rejected auth-handler response to the generic alert and clears the password', async ({
    page,
  }) => {
    const email = IdentityEmailFaker.fake()
    let requestBody: unknown

    await page.route('**/api/auth/sign-in/identity', async (route) => {
      requestBody = route.request().postDataJSON()
      await route.fulfill({
        body: JSON.stringify({ message: 'invalid credentials' }),
        contentType: 'application/json',
        status: 401,
      })
    })

    await page.goto('/login/')
    await expect(page.locator('body')).toHaveAttribute('data-hydrated', 'true', {
      timeout: 30_000,
    })
    await page.getByRole('textbox', { name: 'E-mail' }).fill(email)
    await page.getByRole('textbox', { name: 'Senha' }).fill('wrong-password')
    await page.getByRole('button', { name: 'Entrar' }).click()

    await expect(page.getByRole('alert')).toHaveText('E-mail ou senha inválidos.')
    expect(requestBody).toEqual({ email, password: 'wrong-password' })
    await expect(page.getByRole('textbox', { name: 'E-mail' })).toHaveValue(email)
    await expect(page.getByRole('textbox', { name: 'Senha' })).toHaveValue('')
  })

  test('keeps both fields available after a recoverable auth-handler failure', async ({
    page,
  }) => {
    const email = IdentityEmailFaker.fake()
    let requestBody: unknown

    await page.route('**/api/auth/sign-in/identity', async (route) => {
      requestBody = route.request().postDataJSON()
      await route.fulfill({
        body: JSON.stringify({ message: 'service unavailable' }),
        contentType: 'application/json',
        status: 503,
      })
    })

    await page.goto('/login/')
    await expect(page.locator('body')).toHaveAttribute('data-hydrated', 'true', {
      timeout: 30_000,
    })
    await page.getByRole('textbox', { name: 'E-mail' }).fill(email)
    await page.getByRole('textbox', { name: 'Senha' }).fill('correct-password')
    await page.getByRole('button', { name: 'Entrar' }).click()

    await expect(page.getByRole('alert')).toHaveText(
      'Não foi possível entrar agora. Tente novamente.',
    )
    expect(requestBody).toEqual({ email, password: 'correct-password' })
    await expect(page.getByRole('textbox', { name: 'E-mail' })).toHaveValue(email)
    await expect(page.getByRole('textbox', { name: 'Senha' })).toHaveValue(
      'correct-password',
    )
  })
})
