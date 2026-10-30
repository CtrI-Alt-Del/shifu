import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { installAccountBackend } from '../support/account-backend'

// Browser integration with mocked transport: proves the deletion preparation UI
// sends nothing and clears canceled data, not real account closure.
test.describe('AccountDeletionPage', () => {
  test('prepares deletion safely, clears canceled data and supports keyboard and mobile', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage)
    const mutationRequests: string[] = []
    authenticatedPage.on('request', (request) => {
      if (
        ['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method()) &&
        new URL(request.url()).pathname.startsWith('/api/')
      ) {
        mutationRequests.push(`${request.method()} ${new URL(request.url()).pathname}`)
      }
    })
    await authenticatedPage.setViewportSize({ width: 390, height: 844 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountDelete)
    await expect(authenticatedPage).toHaveURL(/\/account\/delete\/?$/)
    const navigation = authenticatedPage.getByRole('navigation', {
      name: 'Configurações da conta',
    })
    await expect(navigation.getByRole('link', { name: 'Excluir conta' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    const trigger = authenticatedPage.getByRole('button', { name: 'Excluir minha conta' })
    await expect(authenticatedPage.getByText(/ainda não está disponível/)).toBeVisible()
    await expect(
      authenticatedPage.getByText(/após o encerramento confirmado/),
    ).toContainText('24 horas')
    await trigger.focus()
    await expect(trigger).toBeFocused()
    await authenticatedPage.keyboard.press('Enter')
    const dialog = authenticatedPage.getByRole('dialog', { name: 'Excluir sua conta?' })
    const password = dialog.getByLabel('Senha atual')
    const consent = dialog.getByRole('checkbox', {
      name: 'Entendo que isso é definitivo',
    })
    const finalButton = dialog.getByRole('button', { name: 'Excluir definitivamente' })
    await expect(dialog).toBeVisible()
    await expect(password).toBeFocused()
    for (const hasPassword of [false, true]) {
      await password.fill(hasPassword ? 'local-preparation-secret' : '')
      for (const hasConsent of [false, true]) {
        if ((await consent.isChecked()) !== hasConsent) {
          await consent.focus()
          await authenticatedPage.keyboard.press('Space')
        }
        await expect(consent).toHaveJSProperty('checked', hasConsent)
        await expect(finalButton).toBeDisabled()
        await password.press('Enter')
        await expect(dialog).toBeVisible()
      }
    }
    await dialog.getByRole('button', { name: 'Mostrar senha' }).click()
    await expect(password).toHaveAttribute('type', 'text')
    await dialog.getByRole('button', { name: 'Cancelar' }).click()
    await expect(dialog).not.toBeVisible()
    await expect(trigger).toBeFocused()
    await trigger.press('Enter')
    await expect(password).toHaveValue('')
    await expect(consent).not.toBeChecked()
    await expect(password).toHaveAttribute('type', 'password')
    await password.fill('discard-on-escape')
    await consent.focus()
    await authenticatedPage.keyboard.press('Space')
    await expect(consent).toBeChecked()
    await dialog.getByRole('button', { name: 'Mostrar senha' }).click()
    await authenticatedPage.keyboard.press('Escape')
    await expect(trigger).toBeFocused()
    await trigger.click()
    await expect(password).toHaveValue('')
    await expect(consent).not.toBeChecked()
    await expect(password).toHaveAttribute('type', 'password')
    await dialog.getByRole('link', { name: 'Política de privacidade' }).focus()
    await authenticatedPage.keyboard.press('Shift+Tab')
    await expect(dialog.getByRole('button', { name: 'Fechar confirmação' })).toBeFocused()
    expect(
      await authenticatedPage.evaluate(() => document.documentElement.scrollWidth),
    ).toBe(390)
    await password.fill('discard-on-close')
    await consent.focus()
    await authenticatedPage.keyboard.press('Space')
    await dialog.getByRole('button', { name: 'Mostrar senha' }).click()
    await dialog.getByRole('button', { name: 'Fechar confirmação' }).click()
    await expect(dialog).not.toBeVisible()
    await expect(trigger).toBeFocused()
    await trigger.click()
    await expect(password).toHaveValue('')
    await expect(consent).not.toBeChecked()
    await expect(password).toHaveAttribute('type', 'password')
    await authenticatedPage.keyboard.press('Escape')
    await navigation.getByRole('link', { name: 'Segurança' }).click()
    await expect(authenticatedPage).toHaveURL(/\/account\/security\/?$/)
    await navigation.getByRole('link', { name: 'Excluir conta' }).click()
    await expect(authenticatedPage).toHaveURL(/\/account\/delete\/?$/)
    await trigger.click()
    await expect(password).toHaveValue('')
    await expect(consent).not.toBeChecked()
    await password.fill('discard-on-navigation')
    await dialog.getByRole('link', { name: 'Política de privacidade' }).click()
    await expect(authenticatedPage).toHaveURL(/\/privacy\/?$/)
    await expect(
      authenticatedPage.getByRole('heading', {
        name: 'Política de privacidade',
        exact: true,
      }),
    ).toBeVisible()
    expect(backend.profileRequests).toEqual([])
    expect(backend.passwordRequests).toEqual([])
    expect(mutationRequests).toEqual([])
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountDelete)
    await trigger.click()
    await expect(password).toHaveValue('')
    await expect(consent).not.toBeChecked()
    await expect(password).toHaveAttribute('type', 'password')
    await expect(finalButton).toBeDisabled()
  })
  test('redirects an anonymous visitor before protected content renders', async ({
    page,
  }) => {
    await page.goto(ROUTES.accountDelete)
    await expect(page).toHaveURL(/\/login\/?$/)
    await expect(page.getByRole('heading', { name: 'Sua conta' })).not.toBeVisible()
  })
})
