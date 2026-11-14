import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { INITIAL_PROFILE, installAccountBackend } from '../support/account-backend'

// Browser integration with mocked transport: proves the profile page's rendered
// contract and outgoing requests, not server persistence.
test.describe('AccountProfilePage', () => {
  test('edits the canonical profile at mobile width and keeps the privacy destinations', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage)
    await authenticatedPage.setViewportSize({ width: 390, height: 844 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountProfile)
    await expect(authenticatedPage).toHaveURL(/\/account\/profile\/?$/)
    await expect(
      authenticatedPage.getByRole('heading', { name: 'Sua conta' }),
    ).toBeVisible()
    await expect(authenticatedPage.getByLabel('E-mail · não editável')).toHaveAttribute(
      'readonly',
      '',
    )
    await expect(authenticatedPage.getByRole('combobox')).toContainText(
      'Tempo universal coordenado',
    )
    await authenticatedPage.getByLabel('Nome de exibição').fill('  Nome atualizado  ')
    await authenticatedPage.getByRole('button', { name: 'Salvar', exact: true }).click()
    await expect(authenticatedPage.getByRole('status')).toHaveText('Perfil salvo.')
    expect(backend.profileRequests).toEqual([
      { displayName: 'Nome atualizado', timeZone: 'UTC' },
    ])
    await authenticatedPage.getByRole('button', { name: 'Abrir menu da conta' }).click()
    await expect(
      authenticatedPage.getByRole('menu').getByText('Nome atualizado'),
    ).toBeVisible()
    await authenticatedPage.keyboard.press('Escape')
    await authenticatedPage.getByRole('combobox').focus()
    await authenticatedPage.keyboard.press('Enter')
    await authenticatedPage.keyboard.press('Escape')
    await expect(authenticatedPage.getByRole('combobox')).toBeFocused()
    expect(
      await authenticatedPage.evaluate(() => document.documentElement.scrollWidth),
    ).toBe(390)
    await expect(
      authenticatedPage.getByRole('link', { name: 'Consultar política de privacidade' }),
    ).toHaveAttribute('href', ROUTES.privacy)
    await expect(
      authenticatedPage.getByRole('link', { name: 'Solicitar atendimento' }),
    ).toHaveAttribute('href', /^mailto:/)
    await authenticatedPage
      .getByRole('link', { name: 'Consultar política de privacidade' })
      .click()
    await expect(authenticatedPage).toHaveURL(/\/privacy\/?$/)
  })
  test('identifies the browser timezone suggestion without persisting on read', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage, { timeZone: null })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountProfile)
    await expect(
      authenticatedPage.getByText(
        'Sugestão do navegador. Este fuso ainda não foi salvo.',
      ),
    ).toBeVisible()
    expect(backend.profileRequests).toEqual([])
  })
  test('validates an invalid name before sending a request', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountProfile)
    await authenticatedPage.getByLabel('Nome de exibição').fill(' ')
    await authenticatedPage.getByRole('button', { name: 'Salvar', exact: true }).click()
    await expect(authenticatedPage.getByRole('alert')).toContainText('Revise')
    expect(backend.profileRequests).toEqual([])
  })
  test('recovers from a profile outage without rendering fictitious data', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage, {
      profileFailure: 503,
    })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountProfile)
    await expect(authenticatedPage.getByRole('alert')).toBeVisible()
    await expect(authenticatedPage.getByLabel('Nome de exibição')).not.toBeVisible()
    backend.recoverProfile()
    await authenticatedPage.getByRole('button', { name: 'Tentar novamente' }).click()
    await expect(authenticatedPage.getByLabel('Nome de exibição')).toHaveValue(
      'Playwright Learner',
    )
  })
  test('keeps a non-sensitive draft after a server validation rejection and recovers explicitly', async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage)
    let failSave = true
    const bodies: unknown[] = []
    await authenticatedPage.route('**/api/auth/account/profile', async (route) => {
      const body = route.request().postDataJSON()
      bodies.push(body)
      await route.fulfill({
        status: failSave ? 400 : 200,
        contentType: 'application/json',
        body: JSON.stringify(
          failSave
            ? {
                message: 'Nome inválido.',
                code: 'invalid_display_name',
                field: 'displayName',
              }
            : { ...INITIAL_PROFILE, ...body },
        ),
      })
    })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountProfile)
    await authenticatedPage.getByLabel('Nome de exibição').fill('Rascunho mantido')
    await authenticatedPage.getByRole('button', { name: 'Salvar', exact: true }).click()
    await expect(authenticatedPage.getByRole('alert')).toBeVisible()
    await expect(authenticatedPage.getByLabel('Nome de exibição')).toHaveValue(
      'Rascunho mantido',
    )
    failSave = false
    await authenticatedPage.getByRole('button', { name: 'Salvar', exact: true }).click()
    await expect(authenticatedPage.getByRole('status')).toContainText('Perfil salvo.')
    expect(bodies).toHaveLength(2)
  })
  test('announces the profile load while the read is pending', async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage)
    let releaseRead: () => void = () => undefined
    const pendingRead = new Promise<void>((resolve) => {
      releaseRead = resolve
    })
    await authenticatedPage.route('**/api/auth/account', async (route) => {
      await pendingRead
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(INITIAL_PROFILE),
      })
    })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountProfile)
    await expect(
      authenticatedPage.getByRole('status', { name: 'Carregando sua conta' }),
    ).toBeVisible()
    releaseRead()
    await expect(authenticatedPage.getByLabel('Nome de exibição')).toHaveValue(
      'Playwright Learner',
    )
  })
  test('renders malformed profile responses as recoverable failures', async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage, { malformed: true })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountProfile)
    await expect(authenticatedPage.getByRole('alert')).toBeVisible()
    await expect(
      authenticatedPage.getByRole('button', { name: 'Tentar novamente' }),
    ).toBeEnabled()
  })
  test('redirects an anonymous visitor before protected content renders', async ({
    page,
  }) => {
    await page.goto(ROUTES.accountProfile)
    await expect(page).toHaveURL(/\/login\/?$/)
    await expect(page.getByRole('heading', { name: 'Sua conta' })).not.toBeVisible()
  })
})
