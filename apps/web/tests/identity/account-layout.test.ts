import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { installAccountBackend } from '../support/account-backend'

// Browser integration with mocked transport: proves the account section routes,
// their navigation bar and the protected redirect, not server persistence.
test.describe('AccountLayout', () => {
  test('redirects the account root to Perfil and marks the active section as a link', async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
    await expect(authenticatedPage).toHaveURL(/\/account\/profile\/?$/)
    await expect(
      authenticatedPage.getByRole('heading', { level: 1, name: 'Sua conta' }),
    ).toBeVisible()
    const navigation = authenticatedPage.getByRole('navigation', {
      name: 'Configurações da conta',
    })
    await expect(navigation.getByRole('link')).toHaveText([
      'Perfil',
      'Segurança',
      'Excluir conta',
    ])
    await expect(navigation.getByRole('link', { name: 'Perfil' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await expect(navigation.getByRole('link', { name: 'Segurança' })).not.toHaveAttribute(
      'aria-current',
      'page',
    )
    await expect(authenticatedPage.getByRole('tab')).toHaveCount(0)
    await expect(authenticatedPage.getByLabel('Nome de exibição')).toBeVisible()
  })
  test('navigates between sections by pointer, keyboard and history', async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountProfile)
    const navigation = authenticatedPage.getByRole('navigation', {
      name: 'Configurações da conta',
    })
    await navigation.getByRole('link', { name: 'Segurança' }).click()
    await expect(authenticatedPage).toHaveURL(/\/account\/security\/?$/)
    await expect(navigation.getByRole('link', { name: 'Segurança' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await expect(
      authenticatedPage.getByLabel('Senha atual', { exact: true }),
    ).toBeVisible()
    await expect(authenticatedPage.getByLabel('Nome de exibição')).toHaveCount(0)
    await navigation.getByRole('link', { name: 'Segurança' }).focus()
    await authenticatedPage.keyboard.press('Tab')
    await expect(navigation.getByRole('link', { name: 'Excluir conta' })).toBeFocused()
    await authenticatedPage.keyboard.press('Enter')
    await expect(authenticatedPage).toHaveURL(/\/account\/delete\/?$/)
    await expect(navigation.getByRole('link', { name: 'Excluir conta' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await expect(
      authenticatedPage.getByRole('button', { name: 'Excluir minha conta' }),
    ).toBeVisible()
    await authenticatedPage.goBack()
    await expect(authenticatedPage).toHaveURL(/\/account\/security\/?$/)
    await expect(
      authenticatedPage.getByLabel('Senha atual', { exact: true }),
    ).toBeVisible()
  })
  test('opens the profile section from the account menu without a redirect hop', async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountSecurity)
    await authenticatedPage.getByRole('button', { name: 'Abrir menu da conta' }).click()
    await authenticatedPage.getByRole('menuitem', { name: 'Sua conta' }).click()
    await expect(authenticatedPage).toHaveURL(/\/account\/profile\/?$/)
    await expect(authenticatedPage.getByLabel('Nome de exibição')).toHaveValue(
      'Playwright Learner',
    )
  })
  test('keeps the section bar inside a narrow viewport', async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage)
    await authenticatedPage.setViewportSize({ width: 390, height: 844 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountDelete)
    const navigation = authenticatedPage.getByRole('navigation', {
      name: 'Configurações da conta',
    })
    for (const label of ['Perfil', 'Segurança', 'Excluir conta'])
      await expect(navigation.getByRole('link', { name: label })).toBeVisible()
    expect(
      await authenticatedPage.evaluate(() => document.documentElement.scrollWidth),
    ).toBe(390)
  })
  for (const path of [ROUTES.account, ROUTES.accountSecurity, ROUTES.accountDelete])
    test(`redirects an anonymous visitor from ${path} before protected content renders`, async ({
      page,
    }) => {
      await page.goto(path)
      await expect(page).toHaveURL(/\/login\/?$/)
      await expect(page.getByRole('heading', { name: 'Sua conta' })).not.toBeVisible()
    })
})
