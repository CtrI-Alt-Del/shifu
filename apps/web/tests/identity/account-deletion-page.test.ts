import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { installAccountBackend } from '../support/account-backend'

test.describe('AccountDeletionPage', () => {
  test('confirms deletion, clears the account shell and shows pending status on mobile', async ({
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
    await expect(authenticatedPage.getByText(/bloqueado imediatamente/)).toContainText(
      '24 horas',
    )
    await expect(authenticatedPage.getByText(/navegador desconectado/)).toBeVisible()

    const trigger = authenticatedPage.getByRole('button', { name: 'Excluir minha conta' })
    await trigger.focus()
    await authenticatedPage.keyboard.press('Enter')
    const dialog = authenticatedPage.getByRole('dialog', { name: 'Excluir sua conta?' })
    const password = dialog.getByLabel('Senha atual')
    const consent = dialog.getByRole('checkbox', {
      name: 'Entendo que o encerramento é definitivo',
    })
    const finalButton = dialog.getByRole('button', { name: 'Excluir definitivamente' })
    await expect(dialog).toBeVisible()
    await expect(password).toBeFocused()
    await expect(finalButton).toBeDisabled()
    await password.fill('local-preparation-secret')
    await expect(finalButton).toBeDisabled()
    await consent.focus()
    await authenticatedPage.keyboard.press('Space')
    await expect(consent).toBeChecked()
    await expect(finalButton).toBeEnabled()

    await dialog.getByRole('button', { name: 'Cancelar' }).click()
    await expect(dialog).not.toBeVisible()
    await expect(trigger).toBeFocused()
    expect(backend.prepareRequests).toEqual([])
    expect(backend.deletionRequests).toEqual([])
    await trigger.press('Enter')
    await expect(password).toHaveValue('')
    await expect(consent).not.toBeChecked()
    await expect(password).toHaveAttribute('type', 'password')
    await password.fill('local-preparation-secret')
    await dialog.getByText('Entendo que o encerramento é definitivo').click()
    await finalButton.click()

    await expect(
      authenticatedPage.getByRole('heading', { name: 'Eliminação em andamento' }),
    ).toBeVisible()
    await expect(authenticatedPage.getByText(/bloqueado/)).toBeVisible()
    await expect(authenticatedPage.getByText(/eliminados em até 24 horas/)).toBeVisible()
    await expect(
      authenticatedPage.getByRole('navigation', { name: 'Configurações da conta' }),
    ).toHaveCount(0)
    expect(backend.prepareRequests).toEqual([{}])
    expect(backend.deletionRequests).toEqual([
      { currentPassword: 'local-preparation-secret', confirmed: true },
    ])
    expect(backend.isClosed).toBe(true)
    expect(mutationRequests).toEqual([
      'POST /api/auth/account/deletion/prepare',
      'POST /api/auth/account/deletion',
    ])
    expect(
      await authenticatedPage.evaluate(() => document.documentElement.scrollWidth),
    ).toBe(390)
  })

  test('recovers a committed closure after losing the confirmation response', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage, {
      deletionResponseLost: true,
    })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountDelete)
    await authenticatedPage.getByRole('button', { name: 'Excluir minha conta' }).click()
    await authenticatedPage.getByLabel('Senha atual').fill('local-preparation-secret')
    await authenticatedPage
      .getByText('Entendo que o encerramento é definitivo', { exact: true })
      .click()
    await authenticatedPage
      .getByRole('button', { name: 'Excluir definitivamente' })
      .click()

    await expect(
      authenticatedPage.getByRole('heading', { name: 'Eliminação em andamento' }),
    ).toBeVisible()
    expect(backend.deletionRequests).toHaveLength(1)
    expect(backend.deletionStatusRequests).toBe(1)
    expect(backend.isClosed).toBe(true)
  })

  test('shows a wrong-password error without reporting closure', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage, {
      deletionFailure: 403,
    })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountDelete)
    await authenticatedPage.getByRole('button', { name: 'Excluir minha conta' }).click()
    await authenticatedPage.getByLabel('Senha atual').fill('wrong-password')
    await authenticatedPage
      .getByText('Entendo que o encerramento é definitivo', { exact: true })
      .click()
    await authenticatedPage
      .getByRole('button', { name: 'Excluir definitivamente' })
      .click()

    await expect(authenticatedPage.getByRole('alert')).toHaveText(
      'A senha atual está incorreta.',
    )
    await expect(authenticatedPage.getByRole('dialog')).toBeVisible()
    await expect(
      authenticatedPage.getByRole('heading', { name: 'Conta encerrada' }),
    ).toHaveCount(0)
    expect(backend.isClosed).toBe(false)
    expect(backend.deletionRequests).toEqual([
      { currentPassword: 'wrong-password', confirmed: true },
    ])
  })

  test('redirects an anonymous visitor before protected content renders', async ({
    page,
  }) => {
    await page.goto(ROUTES.accountDelete)
    await expect(page).toHaveURL(/\/login\/?$/)
    await expect(page.getByRole('heading', { name: 'Sua conta' })).not.toBeVisible()
  })
})
