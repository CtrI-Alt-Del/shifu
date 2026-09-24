import type { Page } from '@playwright/test'

import { expect, navigateAuthenticatedPage, test } from '../playwright'

const GOAL_ID = '01SHF000000000000000000003'
const SKILL_ID = '01SHF000000000000000000004'

// Home's data (the objectives list) and its start-planning mutation are
// fetched through server functions that call FastAPI from the Node process,
// not from the browser directly (see spec.md's BFF composition). The shared
// `authenticatedPage` fixture already stubs every `_serverFn` call with a
// fixed access payload so unrelated suites can sign in; here we additionally
// stub the Home-specific calls so this suite can assert real UI behavior
// without a running backend. Each server function's request path is a
// base64url-encoded `{"file": ..., "export": ...}` descriptor, which lets us
// identify the exact function being called (instead of guessing from request
// order, which is unreliable once React re-invokes an effect/query).
function decodeServerFnDescriptor(url: string): { export: string; file: string } | null {
  const segment = new URL(url).pathname.split('/_serverFn/')[1]
  if (!segment) return null

  try {
    const json = Buffer.from(segment, 'base64').toString('utf-8')
    return JSON.parse(json)
  } catch {
    return null
  }
}

// A server-function response is an RPC envelope, not the handler's raw return
// value: the client resolves `result.result` (see `createServerFn`'s client
// path in `@tanstack/start-client-core`). Returning the bare value makes the
// caller receive `undefined` instead of the payload, so every stub must wrap.
function serverFnResponse(result: unknown) {
  return {
    body: JSON.stringify({ result }),
    contentType: 'application/json',
    status: 200,
  }
}

async function mockHomeServerFunctions(page: Page, options: { goals?: unknown[] } = {}) {
  const goals = options.goals ?? [
    {
      description: 'Construir uma base sólida para resolver problemas com clareza.',
      id: GOAL_ID,
      skillCount: 3,
      title: 'Lógica de programação',
      updatedAt: '2026-01-05T00:00:00.000Z',
    },
  ]

  await page.route('**/_serverFn/**', async (route) => {
    const descriptor = decodeServerFnDescriptor(route.request().url())

    if (descriptor?.file.includes('use-home-goals-query')) {
      await route.fulfill(serverFnResponse(goals))
      return
    }

    if (descriptor?.file.includes('use-start-planning-action')) {
      await route.fulfill(
        serverFnResponse({
          created_at: '2026-01-06T00:00:00.000Z',
          id: 'playwright-planning-id',
        }),
      )
      return
    }

    if (descriptor?.export.startsWith('getGoalDetailAction_')) {
      await route.fulfill(
        serverFnResponse({
          goalId: GOAL_ID,
          title: 'Lógica de programação',
          description: 'Construir uma base sólida para resolver problemas com clareza.',
          skills: [
            {
              skillId: SKILL_ID,
              skillName: 'Lógica',
              status: 'not-started',
              policyId: 'adaptive-v2',
            },
          ],
        }),
      )
      return
    }

    if (descriptor?.export.startsWith('getAvailableSkillsAction_')) {
      await route.fulfill(
        serverFnResponse([
          { id: SKILL_ID, name: 'Lógica', available: true, unavailableReason: null },
        ]),
      )
      return
    }

    await route.fulfill(
      serverFnResponse({
        accountId: 'playwright-account',
        accessToken: 'playwright-access-token',
        displayName: 'Playwright Learner',
        timeZone: 'America/Sao_Paulo',
      }),
    )
  })
}

test.describe('Home page', () => {
  test('renders the intent field, then Criar manualmente, then the objectives list, in that order', async ({
    authenticatedPage,
  }) => {
    await mockHomeServerFunctions(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, '/')

    await expect(
      authenticatedPage.getByRole('heading', {
        level: 1,
        name: 'O que você quer aprender?',
      }),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByRole('link', { name: 'Criar manualmente' }),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByRole('heading', { level: 2, name: 'Seus Objetivos' }),
    ).toBeVisible()

    const bodyText = await authenticatedPage.locator('body').innerText()
    const intentIndex = bodyText.indexOf('O que você quer aprender?')
    const manualIndex = bodyText.indexOf('Criar manualmente')
    const goalsIndex = bodyText.indexOf('Seus Objetivos')

    expect(intentIndex).toBeGreaterThanOrEqual(0)
    expect(manualIndex).toBeGreaterThan(intentIndex)
    expect(goalsIndex).toBeGreaterThan(manualIndex)
  })

  test('redirects an anonymous visitor before Home renders', async ({ page }) => {
    await page.goto('/')

    await expect(page).toHaveURL(/\/login\/?$/)
    await expect(
      page.getByRole('heading', { level: 1, name: 'O que você quer aprender?' }),
    ).not.toBeVisible()
  })

  test('selecting an objective card navigates to its detail route (CA-04)', async ({
    authenticatedPage,
  }) => {
    await mockHomeServerFunctions(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, '/')

    await authenticatedPage.getByRole('link', { name: /Lógica de programação/ }).click()

    await expect(authenticatedPage).toHaveURL(new RegExp(`/learning/goals/${GOAL_ID}/?$`))
    await expect(
      authenticatedPage.getByRole('heading', { name: 'Lógica de programação', level: 1 }),
    ).toBeVisible()
  })

  test('selecting Criar manualmente navigates to the Goal form (CA-05)', async ({
    authenticatedPage,
  }) => {
    await mockHomeServerFunctions(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, '/')

    await authenticatedPage.getByRole('link', { name: 'Criar manualmente' }).click()

    await expect(authenticatedPage).toHaveURL(/\/learning\/goals\/new\/?$/)
    await expect(authenticatedPage.getByLabel('Título do Objetivo *')).toBeVisible()
  })

  test('submitting a non-empty intent starts a planning session and navigates to the planner (CA-06)', async ({
    authenticatedPage,
  }) => {
    await mockHomeServerFunctions(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, '/')

    const postRequest = authenticatedPage.waitForRequest(
      (request) => request.method() === 'POST' && request.url().includes('/_serverFn/'),
    )
    await authenticatedPage
      .getByLabel('O que você quer aprender?')
      .fill('quero aprender Python')
    await authenticatedPage.getByRole('button', { name: 'Planejar com IA' }).click()
    await postRequest

    await expect(authenticatedPage).toHaveURL(
      /\/intelligence\/planner\/playwright-planning-id\/?$/,
    )
    await expect(
      authenticatedPage.getByText('Seu planejamento está sendo preparado.'),
    ).toBeVisible()
  })

  test('rejects an empty intent without ever sending a request (CA-07)', async ({
    authenticatedPage,
  }) => {
    await mockHomeServerFunctions(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, '/')

    let planningRequestFired = false
    authenticatedPage.on('request', (request) => {
      if (request.method() === 'POST' && request.url().includes('/_serverFn/')) {
        planningRequestFired = true
      }
    })

    await authenticatedPage.getByRole('button', { name: 'Planejar com IA' }).click()

    await expect(authenticatedPage.getByRole('alert')).toHaveText(
      'Descreva o que você quer aprender antes de continuar.',
    )
    await expect(authenticatedPage.getByLabel('O que você quer aprender?')).toBeFocused()
    expect(planningRequestFired).toBe(false)
  })

  test('renders the empty state while keeping the intent field and Criar manualmente usable (CA-11)', async ({
    authenticatedPage,
  }) => {
    await mockHomeServerFunctions(authenticatedPage, { goals: [] })
    await navigateAuthenticatedPage(authenticatedPage, '/')

    await expect(
      authenticatedPage.getByText('Você ainda não tem objetivos.'),
    ).toBeVisible()
    await expect(authenticatedPage.getByLabel('O que você quer aprender?')).toBeEditable()
    await expect(
      authenticatedPage.getByRole('link', { name: 'Criar manualmente' }),
    ).toBeEnabled()
  })

  test('is keyboard-operable at a 375px viewport (CA-12)', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.setViewportSize({ height: 812, width: 375 })
    await mockHomeServerFunctions(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, '/')

    await authenticatedPage.getByLabel('O que você quer aprender?').focus()
    await expect(authenticatedPage.getByLabel('O que você quer aprender?')).toBeFocused()

    await authenticatedPage.keyboard.press('Tab')
    await expect(
      authenticatedPage.getByRole('link', { name: 'Criar manualmente' }),
    ).toBeFocused()

    await authenticatedPage.keyboard.press('Tab')
    await expect(
      authenticatedPage.getByRole('button', { name: 'Planejar com IA' }),
    ).toBeFocused()

    await authenticatedPage.keyboard.press('Tab')
    await expect(
      authenticatedPage.getByRole('link', { name: /Lógica de programação/ }),
    ).toBeFocused()
  })
})
