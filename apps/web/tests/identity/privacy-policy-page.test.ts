import { expect, test } from '../playwright'

const PRIVACY_CONTACT_EMAIL = 'shifu.ctrlaltdel@gmail.com'
const PRIVACY_CONTACT_MAILTO =
  'mailto:shifu.ctrlaltdel@gmail.com?subject=Solicita%C3%A7%C3%A3o%20sobre%20meus%20dados%20%E2%80%94%20Shifu&body=Ol%C3%A1!%20Gostaria%20de%20solicitar%3A%20%5Bdescreva%20seu%20pedido%5D.'

test.describe('PrivacyPolicyPage public route', () => {
  test('renders the notice directly without a session or private navigation', async ({
    page,
  }) => {
    const consoleErrors: string[] = []
    const pageErrors: string[] = []
    const identityApiRequests: string[] = []
    page.on('console', (message) => {
      if (message.type() === 'error') {
        consoleErrors.push(message.text())
      }
    })
    page.on('pageerror', (error) => pageErrors.push(error.message))
    page.on('request', (request) => {
      if (new URL(request.url()).port === '7777') {
        identityApiRequests.push(request.url())
      }
    })
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto('/privacy/', { waitUntil: 'domcontentloaded' })

    await expect(
      page.getByRole('heading', { level: 1, name: 'Política de privacidade' }),
    ).toBeVisible()
    await expect(
      page.getByRole('navigation', { name: 'Conteúdo da política' }),
    ).toBeVisible()
    await expect(
      page.getByRole('navigation', { name: 'Navegação principal' }),
    ).not.toBeVisible()
    await expect(page).toHaveTitle('Política de privacidade — Shifu')
    await expect(
      page.getByText('Versão 1.0. Atualizada em 21 de outubro de 2026.'),
    ).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(1440)
    await page.screenshot({
      fullPage: true,
      path: '.playwright-cli/screenshots/privacy-policy-desktop-1440.png',
    })
    expect(consoleErrors).toEqual([])
    expect(pageErrors).toEqual([])
    expect(identityApiRequests).toEqual([])
  })

  test('discloses data purposes, legal bases, minors, providers and retention', async ({
    page,
  }) => {
    await page.goto('/privacy/', { waitUntil: 'domcontentloaded' })

    await expect(
      page.getByRole('heading', { name: 'Dados, finalidades e bases legais' }),
    ).toBeVisible()
    await expect(
      page.getByRole('heading', { name: 'Crianças e adolescentes' }),
    ).toBeVisible()
    await expect(page.getByText(/art\. 7º, V, da LGPD/).first()).toBeVisible()
    await expect(
      page.getByRole('link', { name: 'Estatuto Digital da Criança e do Adolescente' }),
    ).toBeVisible()
    await expect(
      page.getByText(/OpenRouter, OpenAI, Amazon Bedrock e DeepSeek/),
    ).toBeVisible()
    await expect(
      page.getByText(/Registros de acesso à aplicação são conservados por seis meses/),
    ).toBeVisible()
    await expect(
      page.getByText(/petição à Autoridade Nacional de Proteção de Dados \(ANPD\)/),
    ).toBeVisible()
    await expect(
      page.getByText(/consequências dessa escolha, quando ele for solicitado/),
    ).toBeVisible()
    await expect(page.getByText(/Cópias de segurança.*30 dias/s)).toBeVisible()
  })

  test('exposes the exact privacy mailto without claiming message delivery', async ({
    page,
  }) => {
    await page.goto('/privacy/', { waitUntil: 'domcontentloaded' })

    const emailLinks = page.getByRole('link', { name: PRIVACY_CONTACT_EMAIL })
    await expect(emailLinks.first()).toHaveAttribute('href', PRIVACY_CONTACT_MAILTO)
    await expect(emailLinks).toHaveCount(3)
    await expect(
      page.getByText(/não confirma que o Shifu recebeu o pedido/),
    ).toBeVisible()
  })

  test('follows section anchors by keyboard and fits the mobile viewport', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/privacy/', { waitUntil: 'domcontentloaded' })

    const sectionLinks = await page
      .getByRole('navigation', { name: 'Conteúdo da política' })
      .getByRole('link')
      .all()
    for (const link of sectionLinks) {
      const hash = await link.getAttribute('href')
      if (!hash) {
        throw new Error('Section link must have an href')
      }
      await link.focus()
      await page.keyboard.press('Enter')
      await expect(page).toHaveURL(new RegExp(`${hash}$`))
      await expect(page.locator(hash)).toBeFocused()
      await expect(page.locator(hash)).toHaveClass(/focus-visible:outline-2/)
    }
    await expect(page).toHaveURL(/#atualizacoes$/)
    await page.screenshot({
      fullPage: true,
      path: '.playwright-cli/screenshots/privacy-policy-mobile-390.png',
    })
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
  })
})
