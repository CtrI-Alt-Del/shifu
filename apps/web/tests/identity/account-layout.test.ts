import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { installAccountBackend } from '../support/account-backend'
import { expectBox, installAiQuotaReading } from '../support/ai-quota-backend'

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
      'Uso da IA',
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
    // Uso da IA sits between Segurança and Excluir conta.
    await expect(navigation.getByRole('link', { name: 'Uso da IA' })).toBeFocused()
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
    for (const label of ['Perfil', 'Segurança', 'Uso da IA', 'Excluir conta'])
      await expect(navigation.getByRole('link', { name: label })).toBeVisible()
    expect(
      await authenticatedPage.evaluate(() => document.documentElement.scrollWidth),
    ).toBe(390)
  })
  test('opens Uso da IA between Segurança and Excluir conta and marks it as the current section (CA-16)', async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage)
    await installAiQuotaReading(authenticatedPage, 42)
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountSecurity)
    const navigation = authenticatedPage.getByRole('navigation', {
      name: 'Configurações da conta',
    })
    await expect(navigation.getByRole('link')).toHaveText([
      'Perfil',
      'Segurança',
      'Uso da IA',
      'Excluir conta',
    ])

    await navigation.getByRole('link', { name: 'Uso da IA' }).click()

    await expect(authenticatedPage).toHaveURL(/\/account\/ai-usage\/?$/)
    await expect(navigation.getByRole('link', { name: 'Uso da IA' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    await expect(navigation.getByRole('link', { name: 'Segurança' })).not.toHaveAttribute(
      'aria-current',
      'page',
    )
    await expect(
      authenticatedPage.getByRole('region', { name: 'Uso da IA' }).getByText('42%', {
        exact: true,
      }),
    ).toBeVisible()
    await navigation.getByRole('link', { name: 'Excluir conta' }).click()
    await expect(authenticatedPage).toHaveURL(/\/account\/delete\/?$/)
    await authenticatedPage.goBack()
    await expect(authenticatedPage).toHaveURL(/\/account\/ai-usage\/?$/)
  })
  for (const viewport of [
    { name: '390 x 844', width: 390, height: 844 },
    { name: '1440 x 900', width: 1440, height: 900 },
  ])
    test(`keeps every section tab at least 44 px tall at ${viewport.name} (CA-23)`, async ({
      authenticatedPage,
    }) => {
      await installAccountBackend(authenticatedPage)
      await installAiQuotaReading(authenticatedPage, 42)
      await authenticatedPage.setViewportSize(viewport)
      await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountAiUsage)
      const navigation = authenticatedPage.getByRole('navigation', {
        name: 'Configurações da conta',
      })

      for (const label of ['Perfil', 'Segurança', 'Uso da IA', 'Excluir conta']) {
        const tab = navigation.getByRole('link', { name: label })
        await expectBox(tab, { height: 44 })
        // All four tabs sit inside the viewport without clipping or scrolling.
        const box = await tab.boundingBox()
        expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual(viewport.width)
      }
      // The board's tab strip is 52 px: 44 px tabs inside a 4 px inset.
      const strip = await navigation.locator('ul').boundingBox()
      expect(Math.round(strip?.height ?? 0)).toBe(52)
    })
  for (const path of [
    ROUTES.account,
    ROUTES.accountSecurity,
    ROUTES.accountAiUsage,
    ROUTES.accountDelete,
  ])
    test(`redirects an anonymous visitor from ${path} before protected content renders`, async ({
      page,
    }) => {
      await page.goto(path)
      await expect(page).toHaveURL(/\/login\/?$/)
      await expect(page.getByRole('heading', { name: 'Sua conta' })).not.toBeVisible()
    })
})
