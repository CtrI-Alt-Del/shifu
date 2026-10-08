import { expect, test } from '../playwright'

import {
  IdentityDisplayNameFaker,
  IdentityRegistrationDataFaker,
} from '../../src/core/identity/fakers'

test.describe('RegisterPage route with mocked transport', () => {
  test('renders the public form without horizontal overflow at a narrow viewport', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 812 })

    await page.goto('/register/')

    await expect(
      page.getByRole('heading', { level: 1, name: 'Criar conta' }),
    ).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'Nome de exibição' })).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'E-mail' })).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'Senha' })).toBeVisible()
    await expect(page.getByText('Use pelo menos 8 caracteres.')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Entrar' })).toHaveAttribute(
      'href',
      '/login',
    )
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(375)
  })

  test('preserves valid input and announces client validation failures', async ({
    page,
  }) => {
    const displayName = IdentityDisplayNameFaker.fake()

    await page.goto('/register/')
    await page.waitForLoadState('networkidle')
    await page.getByRole('textbox', { name: 'Nome de exibição' }).fill(displayName)
    await page.getByRole('textbox', { name: 'E-mail' }).fill('invalid-email')
    await page.getByRole('button', { name: 'Criar conta' }).click()

    await expect(page.getByRole('alert')).toHaveText('Revise os campos destacados')
    await expect(page.getByRole('textbox', { name: 'Nome de exibição' })).toHaveValue(
      displayName,
    )
    await expect(page.getByRole('textbox', { name: 'E-mail' })).toHaveValue(
      'invalid-email',
    )
    await expect(page.getByText('Informe um e-mail válido.')).toBeVisible()
  })

  test('posts registration credentials only to the same-origin BFF and continues pending', async ({
    page,
  }) => {
    const registration = IdentityRegistrationDataFaker.fake()
    const password = 'password-123'
    let requestBody: unknown

    await page.route('**/api/auth/register/identity', async (route) => {
      requestBody = route.request().postDataJSON()
      await route.fulfill({
        body: JSON.stringify({ redirectTo: '/pending-confirmation' }),
        contentType: 'application/json',
        status: 200,
      })
    })

    await page.goto('/register/')
    await page.waitForLoadState('networkidle')
    await page
      .getByRole('textbox', { name: 'Nome de exibição' })
      .fill(registration.displayName)
    await page.getByRole('textbox', { name: 'E-mail' }).fill(registration.email)
    await page.getByRole('textbox', { name: 'Senha' }).fill(password)
    await page.getByRole('button', { name: 'Criar conta' }).click()

    await expect(page).toHaveURL(/\/pending-confirmation\/?$/)
    expect(requestBody).toEqual({
      displayName: registration.displayName,
      email: registration.email,
      password,
    })
  })
})
