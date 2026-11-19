import type { Page } from '@playwright/test'

import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { INITIAL_PROFILE, installAccountBackend } from '../support/account-backend'
import {
  collectApplicationErrors,
  installBrowserPushStub,
  installStreakReminderBackend,
  pushStubCalls,
  STUB_SUBSCRIPTION,
} from '../support/streak-reminder-backend'

// The reminders card reads its own state, which the profile scenarios do not
// depend on, so they answer it with a disabled preference.
async function installReminderDefaults(page: Page) {
  await installStreakReminderBackend(page)
  await installBrowserPushStub(page)
}

// Browser integration with mocked transport: proves the profile page's rendered
// contract and outgoing requests, not server persistence.
test.describe('AccountProfilePage', () => {
  test('edits the canonical profile at mobile width and keeps the privacy destinations', async ({
    authenticatedPage,
  }) => {
    await installReminderDefaults(authenticatedPage)
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
    await expect(
      authenticatedPage.getByRole('combobox', { name: 'Fuso horário' }),
    ).toContainText('Tempo universal coordenado')
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
    await authenticatedPage.getByRole('combobox', { name: 'Fuso horário' }).focus()
    await authenticatedPage.keyboard.press('Enter')
    await authenticatedPage.keyboard.press('Escape')
    await expect(
      authenticatedPage.getByRole('combobox', { name: 'Fuso horário' }),
    ).toBeFocused()
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
    await installReminderDefaults(authenticatedPage)
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
    await installReminderDefaults(authenticatedPage)
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
    await installReminderDefaults(authenticatedPage)
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
    await installReminderDefaults(authenticatedPage)
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
    await installReminderDefaults(authenticatedPage)
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
    await installReminderDefaults(authenticatedPage)
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

  test('shows the reminders card between the form and the privacy card and keeps its controls working by keyboard at 1440 x 900', async ({
    authenticatedPage: page,
  }) => {
    const errors = collectApplicationErrors(page)
    const backend = await installStreakReminderBackend(page, { enabled: true })
    await installBrowserPushStub(page, { permission: 'granted' })
    await installAccountBackend(page)
    await page.setViewportSize({ width: 1440, height: 900 })
    await navigateAuthenticatedPage(page, ROUTES.accountProfile)

    const card = page.getByRole('region', { name: 'Lembrete de sequência' })
    await expect(card).toBeVisible()
    await expect(
      card.getByRole('switch', { name: 'Lembrete de sequência Ativados', exact: true }),
    ).toBeChecked()
    await expect(
      card.getByRole('combobox', { name: 'Horário do lembrete' }),
    ).toContainText('18:00')
    await expect(card.getByRole('status')).toHaveCount(0)
    const [formBox, cardBox, privacyBox] = await Promise.all([
      page.getByLabel('Nome de exibição').boundingBox(),
      card.boundingBox(),
      page.getByRole('region', { name: 'Seus dados e privacidade' }).boundingBox(),
    ])
    expect(formBox?.y).toBeLessThan(cardBox?.y ?? 0)
    expect(cardBox?.y).toBeLessThan(privacyBox?.y ?? 0)

    // Enabled and allowed: this browser is registered again once, silently.
    await expect.poll(() => backend.callsNamed('subscription').length).toBe(1)
    expect(backend.callsNamed('public-key')).toHaveLength(1)
    expect(backend.callsNamed('subscription')[0].data).toMatchObject(STUB_SUBSCRIPTION)

    const switchControl = card.getByRole('switch', {
      name: 'Lembrete de sequência Ativados',
      exact: true,
    })
    await switchControl.focus()
    await page.keyboard.press('Space')
    await expect(
      card.getByRole('switch', {
        name: 'Lembrete de sequência Desativados',
        exact: true,
      }),
    ).not.toBeChecked()
    expect(backend.callsNamed('preference').map((call) => call.data.enabled)).toEqual([
      false,
    ])
    expect(backend.callsNamed('subscription')).toHaveLength(1)

    await card
      .getByRole('switch', { name: 'Lembrete de sequência Desativados', exact: true })
      .focus()
    await page.keyboard.press('Space')
    await expect(
      card.getByRole('switch', { name: 'Lembrete de sequência Ativados', exact: true }),
    ).toBeChecked()
    expect(backend.callsNamed('preference').map((call) => call.data.enabled)).toEqual([
      false,
      true,
    ])
    expect(backend.callsNamed('subscription')).toHaveLength(2)

    const hourField = card.getByRole('combobox', { name: 'Horário do lembrete' })
    await hourField.focus()
    await page.keyboard.press('Enter')
    await page.getByRole('option', { name: '20:00' }).click()
    await expect(hourField).toContainText('20:00')
    await expect(hourField).toBeFocused()
    expect(backend.callsNamed('hour').map((call) => call.data.hour)).toEqual([20])
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(1440)
    expect(errors).toEqual([])
  })

  test('reaches the switch and the hour by keyboard and avoids horizontal overflow at 390 x 844', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installStreakReminderBackend(page, { enabled: true })
    await installBrowserPushStub(page, { permission: 'granted' })
    await installAccountBackend(page)
    await page.setViewportSize({ width: 390, height: 844 })
    await navigateAuthenticatedPage(page, ROUTES.accountProfile)

    const card = page.getByRole('region', { name: 'Lembrete de sequência' })
    await expect(card).toBeVisible()
    await card
      .getByRole('switch', { name: 'Lembrete de sequência Ativados', exact: true })
      .focus()
    await page.keyboard.press('Tab')
    await expect(
      card.getByRole('combobox', { name: 'Horário do lembrete' }),
    ).toBeFocused()
    await page.keyboard.press('Enter')
    await page.getByRole('option', { name: '07:00' }).click()
    await expect(
      card.getByRole('combobox', { name: 'Horário do lembrete' }),
    ).toContainText('07:00')
    expect(backend.callsNamed('hour').map((call) => call.data.hour)).toEqual([7])
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(390)
  })

  test('enrolls this browser before turning the reminders on from the card', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installStreakReminderBackend(page, { enabled: false })
    await installBrowserPushStub(page, {
      permission: 'default',
      requestResult: 'granted',
    })
    await installAccountBackend(page)
    await navigateAuthenticatedPage(page, ROUTES.accountProfile)

    const card = page.getByRole('region', { name: 'Lembrete de sequência' })
    await card
      .getByRole('switch', { name: 'Lembrete de sequência Desativados', exact: true })
      .click()

    await expect(
      card.getByRole('switch', { name: 'Lembrete de sequência Ativados', exact: true }),
    ).toBeChecked()
    expect(backend.writeOrder()).toEqual(['public-key', 'subscription', 'preference'])
    expect(await pushStubCalls(page)).toEqual([
      'requestPermission',
      'register /sw.js',
      'subscribe',
    ])
  })

  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 390, height: 844 },
  ]) {
    test(`explains in text that notifications are blocked and keeps the preference on at ${viewport.width} x ${viewport.height}`, async ({
      authenticatedPage: page,
    }) => {
      const backend = await installStreakReminderBackend(page, { enabled: true })
      await installBrowserPushStub(page, { permission: 'denied' })
      await installAccountBackend(page)
      await page.setViewportSize(viewport)
      await navigateAuthenticatedPage(page, ROUTES.accountProfile)

      const card = page.getByRole('region', { name: 'Lembrete de sequência' })
      const notice = card.getByRole('status')
      await expect(notice).toContainText('Notificações bloqueadas neste navegador')
      await expect(notice).toContainText(
        'permita notificações do Shifu nas configurações do navegador',
      )
      await expect(
        card.getByRole('switch', { name: 'Lembrete de sequência Ativados', exact: true }),
      ).toBeChecked()
      // A blocked browser is never registered, not even silently.
      expect(backend.callsNamed('subscription')).toHaveLength(0)
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(viewport.width)

      await card
        .getByRole('switch', { name: 'Lembrete de sequência Ativados', exact: true })
        .click()
      await expect(
        card.getByRole('switch', {
          name: 'Lembrete de sequência Desativados',
          exact: true,
        }),
      ).not.toBeChecked()
      expect(backend.writeOrder()).toEqual(['preference'])
    })
  }

  test('explains in text that this browser cannot receive notifications', async ({
    authenticatedPage: page,
  }) => {
    await installStreakReminderBackend(page, { enabled: true })
    await installBrowserPushStub(page, { supported: false })
    await installAccountBackend(page)
    await navigateAuthenticatedPage(page, ROUTES.accountProfile)

    const notice = page
      .getByRole('region', { name: 'Lembrete de sequência' })
      .getByRole('status')
    await expect(notice).toContainText('Este navegador não recebe notificações')
  })

  test('reverts the hour when saving fails', async ({ authenticatedPage: page }) => {
    const backend = await installStreakReminderBackend(page, {
      enabled: true,
      hourFailure: true,
    })
    await installBrowserPushStub(page, { permission: 'granted' })
    await installAccountBackend(page)
    await navigateAuthenticatedPage(page, ROUTES.accountProfile)

    const hourField = page
      .getByRole('region', { name: 'Lembrete de sequência' })
      .getByRole('combobox', { name: 'Horário do lembrete' })
    await hourField.click()
    await page.getByRole('option', { name: '21:00' }).click()

    await expect.poll(() => backend.callsNamed('hour').length).toBe(1)
    await expect(
      page.getByText('Não foi possível salvar o horário. Tente novamente.'),
    ).toBeVisible()
    await expect(hourField).toContainText('18:00')
    await expect(hourField).toBeEnabled()
    await expect(hourField).toBeFocused()
  })

  test('shows a recoverable card error without hiding the profile form', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installStreakReminderBackend(page, {
      preferenceReadFailure: true,
    })
    await installBrowserPushStub(page)
    await installAccountBackend(page)
    await navigateAuthenticatedPage(page, ROUTES.accountProfile)

    const card = page.getByRole('region', { name: 'Lembrete de sequência' })
    await expect(card.getByRole('alert')).toContainText(
      'Não foi possível carregar os lembretes agora.',
    )
    await expect(page.getByLabel('Nome de exibição')).toHaveValue('Playwright Learner')

    backend.recoverPreferenceRead()
    await card.getByRole('button', { name: 'Tentar novamente' }).click()

    await expect(
      card.getByRole('switch', {
        name: 'Lembrete de sequência Desativados',
        exact: true,
      }),
    ).toBeVisible()
  })

  test('replaces a browser subscription made for another server key during the silent refresh', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installStreakReminderBackend(page, { enabled: true })
    await installBrowserPushStub(page, {
      permission: 'granted',
      existingSubscription: 'other-key',
    })
    await installAccountBackend(page)
    await navigateAuthenticatedPage(page, ROUTES.accountProfile)

    await expect.poll(() => backend.callsNamed('subscription').length).toBe(1)
    expect(await pushStubCalls(page)).toEqual([
      'register /sw.js',
      'unsubscribe',
      'subscribe',
    ])
  })

  test('keeps a browser subscription made for the current server key during the silent refresh', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installStreakReminderBackend(page, { enabled: true })
    await installBrowserPushStub(page, {
      permission: 'granted',
      existingSubscription: 'current-key',
    })
    await installAccountBackend(page)
    await navigateAuthenticatedPage(page, ROUTES.accountProfile)

    await expect.poll(() => backend.callsNamed('subscription').length).toBe(1)
    expect(await pushStubCalls(page)).toEqual(['register /sw.js'])
  })
})
