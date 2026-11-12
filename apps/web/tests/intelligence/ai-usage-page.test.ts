import type { Page } from '@playwright/test'

import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { installAccountBackend } from '../support/account-backend'
import { type AiQuotaReading, installAiQuotaReading } from '../support/ai-quota-backend'

// Browser integration with a mocked quota reading: proves the route, the account tab
// bar and the page states with their text, progress bar and keyboard path. The reading itself
// is mocked, so server persistence is proven by the server suites.
const VIEWPORTS = [
  { name: '1440 x 900', width: 1440, height: 900 },
  { name: '390 x 844', width: 390, height: 844 },
] as const

const RENEWAL_DATE = '1º de dezembro de 2026'

const READY_STATES: {
  name: string
  reading: AiQuotaReading
  percentage: string
  sentence: string
  indicator: string
}[] = [
  {
    name: 'normal',
    reading: 42,
    percentage: '42%',
    sentence: 'O Mentor e o planejamento assistido estão disponíveis.',
    indicator: 'Uso da IA: 42% da cota mensal',
  },
  {
    name: 'near-limit',
    reading: 85,
    percentage: '85%',
    sentence:
      'Perto do limite. Quando a cota acabar, o Mentor e o planejamento assistido pausam até a renovação.',
    indicator: 'Uso da IA: 85% da cota mensal, perto do limite',
  },
  {
    name: 'blocked',
    reading: 100,
    percentage: '100%',
    sentence: `Cota esgotada. O Mentor e o planejamento assistido voltam em ${RENEWAL_DATE}. Seus Objetivos e Atividades continuam disponíveis.`,
    indicator: 'Uso da IA: 100% da cota mensal, cota esgotada',
  },
]

const UNAVAILABLE_SENTENCE =
  'Não foi possível carregar o uso da IA agora. Tente de novo em instantes.'

async function prepare(page: Page, reading: AiQuotaReading) {
  // The suite asserts the final figure, so the counter must not race its animation.
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await installAccountBackend(page)
  return installAiQuotaReading(page, reading)
}

test.describe('AiUsagePage', () => {
  test('redirects an anonymous visitor before the usage page renders', async ({
    page,
  }) => {
    await page.goto(ROUTES.accountAiUsage)

    await expect(page).toHaveURL(/\/login\/?$/)
    await expect(page.getByRole('heading', { name: 'Uso da IA' })).not.toBeVisible()
  })

  for (const viewport of VIEWPORTS)
    for (const state of READY_STATES)
      test(`shows the ${state.name} state with percentage, renewal, bar and text at ${viewport.name} (CA-16, CA-23)`, async ({
        authenticatedPage,
      }) => {
        await prepare(authenticatedPage, state.reading)
        await authenticatedPage.setViewportSize(viewport)
        await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountAiUsage)

        await expect(authenticatedPage).toHaveURL(/\/account\/ai-usage\/?$/)
        await expect(
          authenticatedPage.getByRole('heading', { level: 1, name: 'Sua conta' }),
        ).toBeVisible()
        const section = authenticatedPage.getByRole('region', { name: 'Uso da IA' })
        await expect(section.getByText(state.percentage, { exact: true })).toBeVisible()
        await expect(
          section.getByText('Quanto da sua cota mensal de IA você já usou.'),
        ).toBeVisible()
        await expect(section.getByText('da cota usada')).toBeVisible()
        await expect(section.getByText(`Renova em ${RENEWAL_DATE}`)).toBeVisible()
        // The state never relies on color alone: its sentence names it in words.
        await expect(section.getByText(state.sentence)).toBeVisible()
        await expect(
          section.getByRole('progressbar', { name: 'Cota de IA usada' }),
        ).toHaveAttribute('aria-valuenow', state.percentage.replace('%', ''))
        await expect(section.getByRole('button')).toHaveCount(0)
        await expect(
          authenticatedPage.getByRole('link', { name: state.indicator, exact: true }),
        ).toBeVisible()
        const navigation = authenticatedPage.getByRole('navigation', {
          name: 'Configurações da conta',
        })
        await expect(navigation.getByRole('link', { name: 'Uso da IA' })).toHaveAttribute(
          'aria-current',
          'page',
        )
        for (const label of ['Perfil', 'Segurança', 'Excluir conta'])
          await expect(navigation.getByRole('link', { name: label })).toBeVisible()
        expect(
          await authenticatedPage.evaluate(() => document.documentElement.scrollWidth),
        ).toBeLessThanOrEqual(viewport.width)
      })

  for (const viewport of VIEWPORTS)
    test(`shows the unavailable state and reads again on Tentar novamente at ${viewport.name} (CA-16, CA-23)`, async ({
      authenticatedPage,
    }) => {
      const reading = await prepare(authenticatedPage, 'unavailable')
      await authenticatedPage.setViewportSize(viewport)
      await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountAiUsage)

      const section = authenticatedPage.getByRole('region', { name: 'Uso da IA' })
      const message = authenticatedPage.getByRole('alert').filter({
        hasText: UNAVAILABLE_SENTENCE,
      })
      await expect(message).toBeVisible()
      await expect(section.getByRole('heading', { name: 'Uso da IA' })).toBeVisible()
      await expect(
        section.getByText('Quanto da sua cota mensal de IA você já usou.'),
      ).toBeVisible()
      await expect(
        authenticatedPage.getByRole('link', {
          name: 'Uso da IA: indisponível no momento',
        }),
      ).toBeVisible()
      const navigation = authenticatedPage.getByRole('navigation', {
        name: 'Configurações da conta',
      })
      await expect(navigation.getByRole('link', { name: 'Uso da IA' })).toHaveAttribute(
        'aria-current',
        'page',
      )
      await expect(navigation.getByRole('link', { name: 'Perfil' })).toBeVisible()

      const readsBefore = reading.reads()
      reading.setReading(42)
      await section.getByRole('button', { name: 'Tentar novamente' }).click()

      await expect.poll(() => reading.reads()).toBeGreaterThan(readsBefore)
      await expect(
        authenticatedPage.getByRole('region', { name: 'Uso da IA' }).getByText('42%', {
          exact: true,
        }),
      ).toBeVisible()
      await expect(message).toHaveCount(0)
    })

  for (const viewport of VIEWPORTS)
    test(`reaches Uso da IA with Tab and Enter and keeps the other tabs at ${viewport.name} (CA-16, CA-23)`, async ({
      authenticatedPage,
    }) => {
      await prepare(authenticatedPage, 42)
      await authenticatedPage.setViewportSize(viewport)
      await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountProfile)
      const navigation = authenticatedPage.getByRole('navigation', {
        name: 'Configurações da conta',
      })
      const links = {
        profile: navigation.getByRole('link', { name: 'Perfil' }),
        security: navigation.getByRole('link', { name: 'Segurança' }),
        usage: navigation.getByRole('link', { name: 'Uso da IA' }),
      }

      await links.profile.focus()
      await authenticatedPage.keyboard.press('Tab')
      await expect(links.security).toBeFocused()
      await authenticatedPage.keyboard.press('Tab')
      await expect(links.usage).toBeFocused()
      await authenticatedPage.keyboard.press('Enter')

      await expect(authenticatedPage).toHaveURL(/\/account\/ai-usage\/?$/)
      await expect(links.usage).toHaveAttribute('aria-current', 'page')
      await expect(
        authenticatedPage
          .getByRole('region', { name: 'Uso da IA' })
          .getByText('42%', { exact: true }),
      ).toBeVisible()
      for (const label of ['Perfil', 'Segurança', 'Excluir conta'])
        await expect(navigation.getByRole('link', { name: label })).toBeVisible()
    })

  test('opens the usage page from the header indicator (CA-16)', async ({
    authenticatedPage,
  }) => {
    await prepare(authenticatedPage, 42)
    await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
    await navigateAuthenticatedPage(authenticatedPage, ROUTES.accountSecurity)

    await authenticatedPage
      .getByRole('link', { name: 'Uso da IA: 42% da cota mensal', exact: true })
      .click()

    await expect(authenticatedPage).toHaveURL(/\/account\/ai-usage\/?$/)
    await expect(
      authenticatedPage
        .getByRole('region', { name: 'Uso da IA' })
        .getByText('42%', { exact: true }),
    ).toBeVisible()
  })
})
