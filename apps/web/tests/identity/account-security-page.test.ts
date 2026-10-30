import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { installAccountBackend } from '../support/account-backend'

// Browser integration with mocked transport: proves the password form's rendered
// contract and outgoing requests, not server authorization.
test.describe('AccountSecurityPage', () => {
  test('validates a short password before sending a request', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountSecurity)
    await expect(authenticatedPage).toHaveURL(/\/account\/security\/?$/)
    await authenticatedPage
      .getByLabel('Senha atual', { exact: true })
      .fill('current-password')
    await authenticatedPage
      .getByLabel('Nova senha · mínimo de 8 caracteres')
      .fill('1234567')
    await authenticatedPage
      .getByRole('button', { name: 'Alterar senha', exact: true })
      .click()
    await expect(authenticatedPage.getByRole('alert')).toContainText('Revise')
    expect(backend.passwordRequests).toEqual([])
  })
  test('clears a typed password when leaving and returning to the section', async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountSecurity)
    await authenticatedPage
      .getByLabel('Senha atual', { exact: true })
      .fill('draft-secret')
    const navigation = authenticatedPage.getByRole('navigation', {
      name: 'Configurações da conta',
    })
    await navigation.getByRole('link', { name: 'Perfil' }).click()
    await expect(authenticatedPage).toHaveURL(/\/account\/profile\/?$/)
    await expect(
      authenticatedPage.getByLabel('Senha atual', { exact: true }),
    ).toHaveCount(0)
    await expect(authenticatedPage.getByLabel('Nome de exibição')).toBeVisible()
    await navigation.getByRole('link', { name: 'Segurança' }).click()
    await expect(authenticatedPage).toHaveURL(/\/account\/security\/?$/)
    await expect(
      authenticatedPage.getByLabel('Senha atual', { exact: true }),
    ).toHaveValue('')
  })
  for (const status of [401, 403, 503])
    test(`clears passwords after a confirmed ${status} rejection`, async ({
      authenticatedPage,
    }) => {
      const backend = await installAccountBackend(authenticatedPage, {
        passwordFailure: status,
      })
      await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountSecurity)
      await authenticatedPage
        .getByLabel('Senha atual', { exact: true })
        .fill('current-password')
      await authenticatedPage
        .getByLabel('Nova senha · mínimo de 8 caracteres')
        .fill('new-password')
      await authenticatedPage
        .getByRole('button', { name: 'Alterar senha', exact: true })
        .click()
      await expect(authenticatedPage.getByRole('alert')).toBeVisible()
      await expect(
        authenticatedPage.getByLabel('Senha atual', { exact: true }),
      ).toHaveValue('')
      await expect(
        authenticatedPage.getByLabel('Nova senha · mínimo de 8 caracteres'),
      ).toHaveValue('')
      expect(backend.passwordRequests).toEqual([
        { currentPassword: 'current-password', newPassword: 'new-password' },
      ])
    })
  test('announces uncertain transport once and never retries the password change', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage, { passwordLost: true })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountSecurity)
    await authenticatedPage
      .getByLabel('Senha atual', { exact: true })
      .fill('current-password')
    await authenticatedPage
      .getByLabel('Nova senha · mínimo de 8 caracteres')
      .fill('new-password')
    await authenticatedPage
      .getByRole('button', { name: 'Alterar senha', exact: true })
      .click()
    await expect(authenticatedPage.getByRole('alert')).toContainText(/confirmar/)
    await expect(
      authenticatedPage.getByLabel('Senha atual', { exact: true }),
    ).toHaveValue('')
    expect(backend.passwordRequests).toHaveLength(1)
  })
  test('blocks duplicate password submits while pending', async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountSecurity)
    let releaseChange: () => void = () => undefined
    const pendingChange = new Promise<void>((resolve) => {
      releaseChange = resolve
    })
    let requestsCount = 0
    await authenticatedPage.route('**/api/auth/account/password', async (route) => {
      requestsCount += 1
      await pendingChange
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ changed: true }),
      })
    })
    await authenticatedPage
      .getByLabel('Senha atual', { exact: true })
      .fill('current-password')
    await authenticatedPage
      .getByLabel('Nova senha · mínimo de 8 caracteres')
      .fill('new-password')
    await authenticatedPage
      .getByRole('button', { name: 'Alterar senha', exact: true })
      .click()
    await expect(
      authenticatedPage.getByRole('button', { name: 'Alterando…' }),
    ).toBeDisabled()
    await authenticatedPage
      .getByRole('form', { name: 'Alterar senha' })
      .evaluate((form) => {
        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
      })
    expect(requestsCount).toBe(1)
    releaseChange()
    await expect(authenticatedPage.getByRole('status')).toContainText('Senha alterada.')
  })
  test('redirects an anonymous visitor before protected content renders', async ({
    page,
  }) => {
    await page.goto(ROUTES.accountSecurity)
    await expect(page).toHaveURL(/\/login\/?$/)
    await expect(page.getByRole('heading', { name: 'Sua conta' })).not.toBeVisible()
  })
})
