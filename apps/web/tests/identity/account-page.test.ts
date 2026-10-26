import type { Page } from '@playwright/test'
import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage, test } from '../playwright'

const INITIAL_PROFILE = {
  accountId: 'account-test',
  displayName: 'Playwright Learner',
  email: 'playwright@shifu.local',
  timeZone: 'UTC' as string | null,
}

async function installAccountBackend(
  page: Page,
  options: {
    timeZone?: string | null
    profileFailure?: number
    passwordFailure?: number
    passwordLost?: boolean
    malformed?: boolean
  } = {},
) {
  let profile = {
    ...INITIAL_PROFILE,
    timeZone: options.timeZone === undefined ? 'UTC' : options.timeZone,
  }
  const profileRequests: unknown[] = []
  const passwordRequests: unknown[] = []
  await page.route('**/_serverFn/**', async (route) => {
    const functionId = Buffer.from(
      new URL(route.request().url()).pathname.split('/').at(-1) ?? '',
      'base64url',
    ).toString()
    if (!functionId.includes('middlewares/require-auth-middleware.ts')) {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        result: { displayName: profile.displayName, email: profile.email },
      }),
    })
  })
  let shouldFailProfile = options.profileFailure
  await page.route('**/api/auth/account', async (route) => {
    expect(route.request().method()).toBe('GET')
    await route.fulfill({
      status: shouldFailProfile ?? 200,
      contentType: 'application/json',
      body: JSON.stringify(
        shouldFailProfile
          ? { message: 'Indisponível.' }
          : options.malformed
            ? { unexpected: true }
            : profile,
      ),
    })
  })
  await page.route('**/api/auth/account/profile', async (route) => {
    expect(route.request().method()).toBe('POST')
    const body = route.request().postDataJSON()
    profileRequests.push(body)
    if (!shouldFailProfile) profile = { ...profile, ...body }
    await route.fulfill({
      status: shouldFailProfile ?? 200,
      contentType: 'application/json',
      body: JSON.stringify(
        shouldFailProfile
          ? { message: 'Revise o perfil.', field: 'displayName' }
          : profile,
      ),
    })
  })
  await page.route('**/api/auth/account/password', async (route) => {
    expect(route.request().method()).toBe('POST')
    passwordRequests.push(route.request().postDataJSON())
    if (options.passwordLost) {
      await route.abort('failed')
      return
    }
    await route.fulfill({
      status: options.passwordFailure ?? 200,
      contentType: 'application/json',
      body: JSON.stringify(
        options.passwordFailure
          ? { message: 'Senha atual incorreta.', code: 'invalid_current_password' }
          : { changed: true },
      ),
    })
  })
  return {
    profileRequests,
    passwordRequests,
    recoverProfile() {
      shouldFailProfile = undefined
    },
  }
}

test.describe('AccountPage', () => {
  test('edits the canonical profile and preserves drafts across tabs at mobile width', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage)
    await authenticatedPage.setViewportSize({ width: 390, height: 844 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
    await expect(authenticatedPage).toHaveURL(/\/account\/?$/)
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
    await authenticatedPage.getByRole('tab', { name: 'Segurança' }).click()
    await authenticatedPage
      .getByLabel('Senha atual', { exact: true })
      .fill('draft-secret')
    await authenticatedPage.getByRole('tab', { name: 'Perfil', exact: true }).click()
    await expect(authenticatedPage.getByLabel('Nome de exibição')).toHaveValue(
      '  Nome atualizado  ',
    )
    await authenticatedPage.getByRole('tab', { name: 'Segurança' }).click()
    await expect(
      authenticatedPage.getByLabel('Senha atual', { exact: true }),
    ).toHaveValue('')
    await authenticatedPage.getByRole('tab', { name: 'Perfil', exact: true }).click()
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
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
    await authenticatedPage.getByRole('tab', { name: 'Perfil', exact: true }).focus()
    await authenticatedPage.keyboard.press('End')
    const deletionTab = authenticatedPage.getByRole('tab', { name: 'Excluir conta' })
    await expect(deletionTab).toHaveAttribute('aria-selected', 'true')
    await expect(deletionTab).toBeFocused()
    const trigger = authenticatedPage.getByRole('button', { name: 'Excluir minha conta' })
    await expect(authenticatedPage.getByText(/ainda não está disponível/)).toBeVisible()
    await expect(
      authenticatedPage.getByText(/após o encerramento confirmado/),
    ).toContainText('24 horas')
    await authenticatedPage.keyboard.press('Tab')
    await authenticatedPage.keyboard.press('Tab')
    await authenticatedPage.keyboard.press('Tab')
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
    await authenticatedPage.getByRole('tab', { name: 'Segurança' }).click()
    await deletionTab.click()
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
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
    await deletionTab.click()
    await trigger.click()
    await expect(password).toHaveValue('')
    await expect(consent).not.toBeChecked()
    await expect(password).toHaveAttribute('type', 'password')
    await expect(finalButton).toBeDisabled()
  })
  test('identifies the browser timezone suggestion without persisting on read', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage, { timeZone: null })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
    await expect(
      authenticatedPage.getByText(
        'Sugestão do navegador. Este fuso ainda não foi salvo.',
      ),
    ).toBeVisible()
    expect(backend.profileRequests).toEqual([])
  })
  test('validates invalid name and password before sending requests', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
    await authenticatedPage.getByLabel('Nome de exibição').fill(' ')
    await authenticatedPage.getByRole('button', { name: 'Salvar', exact: true }).click()
    await expect(authenticatedPage.getByRole('alert')).toContainText('Revise')
    expect(backend.profileRequests).toEqual([])
    await authenticatedPage.getByRole('tab', { name: 'Segurança' }).click()
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
  for (const status of [401, 403, 503])
    test(`clears passwords after a confirmed ${status} rejection`, async ({
      authenticatedPage,
    }) => {
      const backend = await installAccountBackend(authenticatedPage, {
        passwordFailure: status,
      })
      await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
      await authenticatedPage.getByRole('tab', { name: 'Segurança' }).click()
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
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
    await authenticatedPage.getByRole('tab', { name: 'Segurança' }).click()
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
  test('recovers from a profile outage without rendering fictitious data', async ({
    authenticatedPage,
  }) => {
    const backend = await installAccountBackend(authenticatedPage, {
      profileFailure: 503,
    })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
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
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
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
  test('announces load and blocks duplicate password submits while pending', async ({
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
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
    await expect(
      authenticatedPage.getByRole('status', { name: 'Carregando sua conta' }),
    ).toBeVisible()
    releaseRead()
    await authenticatedPage.getByRole('tab', { name: 'Segurança' }).click()
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
  test('renders malformed profile responses as recoverable failures', async ({
    authenticatedPage,
  }) => {
    await installAccountBackend(authenticatedPage, { malformed: true })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.account)
    await expect(authenticatedPage.getByRole('alert')).toBeVisible()
    await expect(
      authenticatedPage.getByRole('button', { name: 'Tentar novamente' }),
    ).toBeEnabled()
  })
  test('redirects an anonymous visitor before protected content renders', async ({
    page,
  }) => {
    await page.goto(ROUTES.account)
    await expect(page).toHaveURL(/\/login\/?$/)
    await expect(page.getByRole('heading', { name: 'Sua conta' })).not.toBeVisible()
  })
})
