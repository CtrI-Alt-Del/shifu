import { PlanningSessionFaker } from '@/core/intelligence/fakers/planning-session-faker'
import { GoalSummaryFaker, LearningRouteIdsFaker } from '@/core/learning/fakers'
import type { BffFixtureContract } from '../fixtures/bff-fixture'

import { expect, navigateAuthenticatedPage, test } from '../playwright'
import {
  AI_QUOTA_HOME_BLOCKED_MESSAGE,
  AiQuotaUpstreamFixture,
  clickIgnoringDisabled,
  expectBlockedControl,
  expectBox,
  installAiQuotaReading,
  openRealPage,
  recordServerFunctionCalls,
  signInRealAccount,
} from '../support/ai-quota-backend'

const learningIds = LearningRouteIdsFaker.fake()
const GOAL_ID = learningIds.goalId
const SKILL_ID = learningIds.skillId
// The planner route validates the id as a ULID before loading the session.
const PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'

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

async function mockHomeServerFunctions(
  bff: BffFixtureContract,
  options: { goals?: unknown[] } = {},
) {
  const goals = options.goals ?? [
    GoalSummaryFaker.fake({
      description: 'Construir uma base sólida para resolver problemas com clareza.',
      id: GOAL_ID,
      skillCount: 3,
      title: 'Lógica de programação',
      updatedAt: '2026-01-05T00:00:00.000Z',
    }),
  ]

  await bff.route(async (route) => {
    const descriptor = decodeServerFnDescriptor(route.request().url())

    if (descriptor?.file.includes('use-home-goals-query')) {
      await route.fulfill(serverFnResponse(goals))
      return
    }

    if (descriptor?.file.includes('use-start-planning-action')) {
      await route.fulfill(
        serverFnResponse({
          created_at: '2026-01-06T00:00:00.000Z',
          id: PLANNING_ID,
        }),
      )
      return
    }

    // The planner page polls the session right after the Home hands over.
    if (descriptor?.file.includes('use-planning-session-query')) {
      await route.fulfill(
        serverFnResponse(
          PlanningSessionFaker.fake({
            id: PLANNING_ID,
            intent: 'quero aprender Python',
            status: 'processing',
            batch: null,
            operation: {
              kind: 'start',
              startedAt: '2026-01-06T00:00:00.000Z',
              stage: null,
            },
          }),
        ),
      )
      return
    }

    if (descriptor?.file.includes('get-goal-detail')) {
      await route.fulfill(
        serverFnResponse({
          kind: 'success',
          detail: {
            description: 'Construir uma base sólida para resolver problemas com clareza.',
            goalId: GOAL_ID,
            relations: [],
            skills: [
              {
                skillExperienceId: learningIds.skillExperienceId,
                skillId: SKILL_ID,
                name: 'Lógica',
                skillName: 'Lógica',
                status: 'not-started',
                progress: null,
                inclusionReason: null,
                policyId: 'learning-adaptive-v2',
              },
            ],
            title: 'Lógica de programação',
          },
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
    bff,
  }) => {
    await mockHomeServerFunctions(bff)
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

  test('selecting an objective card navigates to its real detail route (CA-04)', async ({
    authenticatedPage,
    bff,
  }) => {
    await mockHomeServerFunctions(bff)
    await navigateAuthenticatedPage(authenticatedPage, '/')

    await authenticatedPage.getByRole('link', { name: /Lógica de programação/ }).click()

    await expect(authenticatedPage).toHaveURL(new RegExp(`/learning/goals/${GOAL_ID}/?$`))
    await expect(
      authenticatedPage.getByRole('heading', { level: 1, name: 'Lógica de programação' }),
    ).toBeVisible()
  })

  test('selecting Criar manualmente navigates to the Goal form (CA-05)', async ({
    authenticatedPage,
    bff,
  }) => {
    await mockHomeServerFunctions(bff)
    await navigateAuthenticatedPage(authenticatedPage, '/')

    await authenticatedPage.getByRole('link', { name: 'Criar manualmente' }).click()

    await expect(authenticatedPage).toHaveURL(/\/learning\/goals\/new\/?$/)
    await expect(authenticatedPage.getByLabel('Título do Objetivo *')).toBeVisible()
  })

  test('submitting a non-empty intent starts a planning session and navigates to the planner (CA-06)', async ({
    authenticatedPage,
    bff,
  }) => {
    await mockHomeServerFunctions(bff)
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
      new RegExp(`/intelligence/planner/${PLANNING_ID}/?$`),
    )
    await expect(authenticatedPage.getByRole('status')).toContainText(
      'Analisando seu objetivo…',
    )
  })

  test('rejects an empty intent without ever sending a request (CA-07)', async ({
    authenticatedPage,
    bff,
  }) => {
    await mockHomeServerFunctions(bff)
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
    bff,
  }) => {
    await mockHomeServerFunctions(bff, { goals: [] })
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
    bff,
  }) => {
    await authenticatedPage.setViewportSize({ height: 812, width: 375 })
    await mockHomeServerFunctions(bff)
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

const INTENT_LABEL = 'O que você quer aprender?'
const BLOCKED_CARD_ID = 'planning-intent-ai-quota-blocked'
const START_ERROR = 'Não foi possível iniciar o planejamento agora. Tente novamente.'

test.describe('Home page AI quota', () => {
  for (const viewport of [
    { name: '1440 x 900', width: 1440, height: 900 },
    { name: '390 x 844', width: 390, height: 844 },
  ])
    test(`blocks Planejar com IA at 100% and keeps Criar manualmente working at ${viewport.name} (CA-20, CA-23)`, async ({
      authenticatedPage,
      bff,
    }) => {
      await mockHomeServerFunctions(bff)
      await installAiQuotaReading(authenticatedPage, 100)
      const calls = recordServerFunctionCalls(authenticatedPage)
      await authenticatedPage.setViewportSize(viewport)

      await navigateAuthenticatedPage(authenticatedPage, '/')

      const card = authenticatedPage.getByRole('status').filter({
        hasText: AI_QUOTA_HOME_BLOCKED_MESSAGE,
      })
      await expect(card).toBeVisible()
      await expect(card).toHaveAttribute('id', BLOCKED_CARD_ID)
      await expect(card.getByRole('link', { name: 'Ver uso da IA' })).toHaveAttribute(
        'href',
        '/account/ai-usage',
      )
      await expect(card.locator('svg')).toHaveCount(1)
      const intent = authenticatedPage.getByLabel(INTENT_LABEL)
      await expect(intent).toBeDisabled()
      // The board stacks the field, then the blocked card, then the actions.
      const intentBox = await intent.boundingBox()
      const cardBox = await card.boundingBox()
      const planBox = await authenticatedPage
        .getByRole('button', { name: 'Planejar com IA' })
        .boundingBox()
      expect(cardBox?.y).toBeGreaterThanOrEqual(
        (intentBox?.y ?? 0) + (intentBox?.height ?? 0),
      )
      expect(planBox?.y).toBeGreaterThanOrEqual(
        (cardBox?.y ?? 0) + (cardBox?.height ?? 0),
      )
      expect(cardBox?.height).toBeLessThanOrEqual(viewport.width >= 1024 ? 60 : 150)
      await expect(intent).toHaveAttribute('aria-describedby', BLOCKED_CARD_ID)
      const plan = authenticatedPage.getByRole('button', { name: 'Planejar com IA' })
      await expectBlockedControl(plan, BLOCKED_CARD_ID)
      await clickIgnoringDisabled(plan)
      expect(calls.callsTo('startPlanningSession')).toBe(0)
      await expect(authenticatedPage).toHaveURL(/\/$/)

      const manual = authenticatedPage.getByRole('link', { name: 'Criar manualmente' })
      await expect(manual).toBeEnabled()
      await expectBox(manual, { height: 44 })
      await manual.click()

      await expect(authenticatedPage).toHaveURL(/\/learning\/goals\/new\/?$/)
      await expect(authenticatedPage.getByLabel('Título do Objetivo *')).toBeVisible()
    })

  test('shows the blocked card, not a generic error, when the server refuses the planning start and keeps Criar manualmente available (CA-21)', async ({
    page,
    request,
    activeAccount,
  }) => {
    // A real session: the real server function and planningFailure classify the 429.
    await signInRealAccount(page, activeAccount)
    const reading = await installAiQuotaReading(page, 79, activeAccount.accountId)
    const upstream = await AiQuotaUpstreamFixture(request, activeAccount.accountId)
    try {
      await openRealPage(page, '/')
      const intent = page.getByLabel(INTENT_LABEL)
      await expect(intent).toBeEnabled()
      await intent.fill('quero aprender Python')
      await reading.settled()
      // The reading showed 79%, but the server is already at 100% when the planning starts.
      reading.setReading(100)
      const readsBefore = reading.reads()

      await page.getByRole('button', { name: 'Planejar com IA' }).click()

      const card = page
        .getByRole('alert')
        .filter({ hasText: AI_QUOTA_HOME_BLOCKED_MESSAGE })
      await expect(card).toBeVisible()
      await expect(card).toHaveAttribute('id', BLOCKED_CARD_ID)
      await expect(page).toHaveURL(/\/$/)
      await expect(intent).toBeDisabled()
      await expectBlockedControl(
        page.getByRole('button', { name: 'Planejar com IA' }),
        BLOCKED_CARD_ID,
      )
      await expect(page.getByText(START_ERROR)).toHaveCount(0)
      await expect.poll(() => reading.reads()).toBeGreaterThan(readsBefore)
      expect(await upstream.hits()).toEqual({ 'POST /intelligence/planning-sessions': 1 })

      const manual = page.getByRole('link', { name: 'Criar manualmente' })
      await expect(manual).toBeEnabled()
      await expect(manual).toHaveAttribute('href', '/learning/goals/new')
    } finally {
      await upstream.dispose()
    }
  })
})
