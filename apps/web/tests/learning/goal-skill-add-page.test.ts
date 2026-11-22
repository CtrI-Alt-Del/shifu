/**
 * Browser integration with mocked transport for the manual add Skill page. It proves
 * the UI-to-BFF contract (server-function names and payloads), the route behavior and
 * the visible states. Server authorization and persistence belong to the server suites.
 */
import type { Page, Route } from '@playwright/test'

import { ROUTES } from '@/constants/routes'
import {
  DiagnosticOverviewFaker,
  GoalDetailFaker,
  LearningRouteIdsFaker,
  SkillExperienceDetailFaker,
} from '@/core/learning/fakers'
import type { SkillExperienceReference } from '@/core/learning/skill-experience-reference'
import type { BffFixtureContract } from '../fixtures/bff-fixture'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { serverFnExport, serverFnInput } from '../support/mentor-memories-backend'

const ids = LearningRouteIdsFaker.fake()
const OTHER_GOAL_ID = LearningRouteIdsFaker.fake().goalId
const SECOND_OTHER_GOAL_ID = LearningRouteIdsFaker.fake().goalId
const FOUNDATION_ID = LearningRouteIdsFaker.fake().skillId
const OTHER_SKILL_ID = LearningRouteIdsFaker.fake().skillId

const addPath = `/learning/goals/${ids.goalId}/skills/add/`
const goalPath = `/learning/goals/${ids.goalId}/`
const SCREENSHOT_DIRECTORY = '.playwright-cli/screenshots/skill-completion'
const NOTICE_TITLE = 'Você já tem esta Habilidade em outro Objetivo'

type CatalogSkillResponse = {
  id: string
  name: string
  description: string
  alreadyInGoal: boolean
  skillExperienceId: string | null
  foundations: { skillId: string; name: string; status: 'missing' | 'present' }[]
}

const LOGIC_SKILL: CatalogSkillResponse = {
  id: ids.skillId,
  name: 'Lógica de programação',
  description: 'Variáveis, condicionais, repetição e funções.',
  alreadyInGoal: false,
  skillExperienceId: null,
  foundations: [],
}
const PYTHON_SKILL: CatalogSkillResponse = {
  id: OTHER_SKILL_ID,
  name: 'Python para análise de dados',
  description: 'Pandas, limpeza e agregação de tabelas.',
  alreadyInGoal: false,
  skillExperienceId: null,
  foundations: [{ skillId: FOUNDATION_ID, name: 'Variáveis e tipos', status: 'missing' }],
}
const SQL_SKILL: CatalogSkillResponse = {
  id: LearningRouteIdsFaker.fake().skillId,
  name: 'SQL básico',
  description: 'Consultas, filtros e junções.',
  alreadyInGoal: false,
  skillExperienceId: null,
  foundations: [],
}
const CATALOG = [LOGIC_SKILL, PYTHON_SKILL, SQL_SKILL]

const COMPLETED_ELSEWHERE: SkillExperienceReference = {
  goalId: OTHER_GOAL_ID,
  goalTitle: 'Carreira em dados',
  skillExperienceId: LearningRouteIdsFaker.fake().skillExperienceId,
  skillId: ids.skillId,
  status: 'completed',
}
const LEARNING_ELSEWHERE: SkillExperienceReference = {
  goalId: SECOND_OTHER_GOAL_ID,
  goalTitle: 'Dados na prática',
  skillExperienceId: LearningRouteIdsFaker.fake().skillExperienceId,
  skillId: ids.skillId,
  status: 'learning',
}

type CatalogMode = 'ready' | 'fail' | 'hold'
type LookupMode = 'ready' | 'fail'
type AddMode = 'ready' | 'fail'

type BackendOptions = {
  catalog?: CatalogMode
  lookup?: LookupMode
  add?: AddMode
  experiences?: SkillExperienceReference[]
}

/**
 * The shared `serverFnInput` helper decodes objects and strings but leaves seroval
 * arrays (`{ t: 9, a: [...] }`) serialized, so array fields are decoded here.
 */
function decodeSerovalArrays(value: unknown): unknown {
  if (typeof value !== 'object' || value === null) return value
  const record = value as Record<string, unknown>
  if (record.t === 9 && Array.isArray(record.a)) {
    return record.a.map((item) => {
      const decoded = item as { t?: unknown; s?: unknown }
      return decoded.t === 1 ? decoded.s : decodeSerovalArrays(item)
    })
  }
  return Object.fromEntries(
    Object.entries(record).map(([key, nested]) => [key, decodeSerovalArrays(nested)]),
  )
}

type BackendCall = { exportName: string; method: string; data: Record<string, unknown> }

/**
 * Stateful mock of the Learning BFF server functions used by the add page and the Goal
 * page it returns to. `releaseCatalog` frees a held catalog request, and
 * `setCatalogMode` lets a test move the catalog from failing to ready.
 */
async function installBackend(bff: BffFixtureContract, options: BackendOptions = {}) {
  const calls: BackendCall[] = []
  let catalogMode: CatalogMode = options.catalog ?? 'ready'
  let releaseCatalog: () => void = () => undefined
  const catalogGate = new Promise<void>((resolve) => {
    releaseCatalog = resolve
  })

  function fulfillJson(route: Route, result: unknown) {
    return route.fulfill({
      body: JSON.stringify({ result }),
      contentType: 'application/json',
      status: 200,
    })
  }

  function fulfillFailure(route: Route) {
    return route.fulfill({
      body: JSON.stringify({ error: 'Internal Server Error' }),
      contentType: 'application/json',
      status: 500,
    })
  }

  await bff.route(async (route) => {
    const request = route.request()
    const exportName = serverFnExport(request.url()) ?? ''
    const data = decodeSerovalArrays(serverFnInput(request)) as Record<string, unknown>

    if (exportName.startsWith('searchSkillCatalog_')) {
      calls.push({ exportName, method: request.method(), data })
      if (catalogMode === 'fail') {
        await fulfillFailure(route)
        return
      }
      if (catalogMode === 'hold') await catalogGate
      const query = String(data.query ?? '').toLocaleLowerCase()
      const items = CATALOG.filter((skill) =>
        skill.name.toLocaleLowerCase().includes(query),
      )
      await fulfillJson(route, { items, nextCursor: null })
      return
    }

    if (exportName.startsWith('listSkillExperiencesOfSkill_')) {
      calls.push({ exportName, method: request.method(), data })
      if (options.lookup === 'fail') {
        await fulfillFailure(route)
        return
      }
      await fulfillJson(route, options.experiences ?? [])
      return
    }

    if (exportName.startsWith('addSkillToGoal_')) {
      calls.push({ exportName, method: request.method(), data })
      if (options.add === 'fail') {
        await fulfillFailure(route)
        return
      }
      await fulfillJson(route, [
        { id: LearningRouteIdsFaker.fake().skillExperienceId, skillId: ids.skillId },
      ])
      return
    }

    if (exportName.startsWith('getGoalDetail')) {
      calls.push({ exportName, method: request.method(), data })
      await fulfillJson(route, {
        kind: 'success',
        detail: GoalDetailFaker.fake({
          goalId: ids.goalId,
          title: 'Fundamentos de programação',
          skills: [],
          relations: [],
        }),
      })
      return
    }

    if (exportName.startsWith('getSkillExperienceAction')) {
      await fulfillJson(
        route,
        SkillExperienceDetailFaker.fake({
          goalId: OTHER_GOAL_ID,
          skillId: ids.skillId,
          skillName: LOGIC_SKILL.name,
          skillStatus: 'learning',
          competencies: [],
          recommendation: null,
          recommendationGap: null,
          evaluation: null,
          completion: null,
        }),
      )
      return
    }

    if (exportName.startsWith('getDiagnosticAction')) {
      await fulfillJson(
        route,
        DiagnosticOverviewFaker.fake({
          runState: 'settled',
          readyToComplete: false,
          nextCompetencyId: null,
          nextActivityId: null,
          pendingAttemptId: null,
          pendingAttemptStatus: null,
          activitySequence: [],
          competencies: [],
        }),
      )
      return
    }

    await route.fallback()
  })

  return {
    callsOf: (name: string) => calls.filter((call) => call.exportName.startsWith(name)),
    releaseCatalog: () => releaseCatalog(),
    setCatalogMode: (mode: CatalogMode) => {
      catalogMode = mode
    },
  }
}

function collectConsoleErrors(page: Page) {
  const errors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  page.on('pageerror', (error) => errors.push(error.message))
  return errors
}

async function openAddPage(page: Page, viewport = { width: 1440, height: 900 }) {
  await page.setViewportSize(viewport)
  await navigateAuthenticatedPage(page, addPath)
  await expect(
    page.getByRole('heading', { level: 1, name: 'Adicionar Habilidade' }),
  ).toBeVisible()
}

function skillRow(page: Page, skillName: string) {
  return page
    .getByRole('heading', { name: skillName, level: 3 })
    .locator('xpath=ancestor::div[contains(@class, "rounded-xl")][1]')
}

async function openDialogFor(page: Page, skillName: string) {
  await skillRow(page, skillName).getByRole('button', { name: 'Adicionar' }).click()
  const dialog = page.getByRole('dialog', { name: `Adicionar ${skillName}?` })
  await expect(dialog).toBeVisible()
  return dialog
}

test('redirects an anonymous visitor to the login page before the add page renders', async ({
  page,
}) => {
  await page.goto(addPath)

  await expect(page).toHaveURL(new RegExp(`${ROUTES.login}/?$`))
  await expect(
    page.getByRole('heading', { level: 1, name: 'Adicionar Habilidade' }),
  ).not.toBeVisible()
})

test('renders the back link, the heading, the search field and the catalog for the Goal', async ({
  authenticatedPage,
  bff,
}) => {
  const backend = await installBackend(bff)

  await openAddPage(authenticatedPage)

  await expect(authenticatedPage).toHaveURL(new RegExp(`${addPath}?$`))
  await expect(
    authenticatedPage.getByRole('link', { name: 'Voltar ao Objetivo' }),
  ).toHaveAttribute('href', new RegExp(`/learning/goals/${ids.goalId}/?$`))
  await expect(
    authenticatedPage.getByRole('textbox', { name: 'Buscar no Currículo' }),
  ).toBeVisible()
  for (const skill of CATALOG) {
    await expect(
      authenticatedPage.getByRole('heading', { name: skill.name, level: 3 }),
    ).toBeVisible()
    await expect(authenticatedPage.getByText(skill.description)).toBeVisible()
  }
  const [catalogCall] = backend.callsOf('searchSkillCatalog_')
  expect(catalogCall?.data).toMatchObject({ goalId: ids.goalId })
})

test('shows the catalog loading state until the request is answered', async ({
  authenticatedPage,
  bff,
}) => {
  const backend = await installBackend(bff, { catalog: 'hold' })

  await openAddPage(authenticatedPage)

  await expect(authenticatedPage.getByText('Carregando habilidades...')).toBeVisible()
  await expect(authenticatedPage.getByRole('button', { name: 'Adicionar' })).toHaveCount(
    0,
  )

  backend.releaseCatalog()

  await expect(authenticatedPage.getByText('Carregando habilidades...')).not.toBeVisible()
  await expect(
    authenticatedPage.getByRole('heading', { name: LOGIC_SKILL.name, level: 3 }),
  ).toBeVisible()
})

test('shows the catalog failure without addition controls and recovers through the retry button', async ({
  authenticatedPage,
  bff,
}) => {
  const backend = await installBackend(bff, { catalog: 'fail' })

  await openAddPage(authenticatedPage)

  await expect(authenticatedPage.getByRole('alert')).toBeVisible()
  await expect(authenticatedPage.getByRole('button', { name: 'Adicionar' })).toHaveCount(
    0,
  )
  await expect(
    authenticatedPage.getByRole('link', { name: 'Voltar ao Objetivo' }),
  ).toBeVisible()
  expect(backend.callsOf('searchSkillCatalog_')).toHaveLength(1)

  const retryButton = authenticatedPage.getByRole('button', { name: 'Tentar novamente' })
  await expect(retryButton).toBeVisible()
  expect((await retryButton.boundingBox())?.height).toBeGreaterThanOrEqual(44)
  await retryButton.focus()
  await expect(retryButton).toBeFocused()

  backend.setCatalogMode('ready')
  await authenticatedPage.keyboard.press('Enter')

  await expect(authenticatedPage.getByRole('alert')).toHaveCount(0)
  for (const skill of CATALOG) {
    await expect(
      authenticatedPage.getByRole('heading', { name: skill.name, level: 3 }),
    ).toBeVisible()
  }
  const catalogCalls = backend.callsOf('searchSkillCatalog_')
  expect(catalogCalls).toHaveLength(2)
  expect(catalogCalls[1]?.data).toMatchObject({ goalId: ids.goalId })
})

test('sends the search text to the catalog request and shows the empty search result', async ({
  authenticatedPage,
  bff,
}) => {
  const backend = await installBackend(bff)
  await openAddPage(authenticatedPage)

  await authenticatedPage
    .getByRole('textbox', { name: 'Buscar no Currículo' })
    .fill('sem resultado')

  await expect(authenticatedPage.getByText('Nenhuma habilidade encontrada')).toBeVisible()
  await expect(authenticatedPage.getByRole('button', { name: 'Adicionar' })).toHaveCount(
    0,
  )
  const searchCalls = backend.callsOf('searchSkillCatalog_')
  expect(searchCalls.at(-1)?.data).toMatchObject({
    goalId: ids.goalId,
    query: 'sem resultado',
  })

  await authenticatedPage.getByRole('textbox', { name: 'Buscar no Currículo' }).fill('')
  await expect(
    authenticatedPage.getByRole('heading', { name: LOGIC_SKILL.name, level: 3 }),
  ).toBeVisible()
})

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`opens the dialog with the other Goal notice and its link on ${viewport.name}`, async ({
    authenticatedPage,
    bff,
  }) => {
    const consoleErrors = collectConsoleErrors(authenticatedPage)
    const backend = await installBackend(bff, { experiences: [COMPLETED_ELSEWHERE] })
    await openAddPage(authenticatedPage, viewport)

    const dialog = await openDialogFor(authenticatedPage, LOGIC_SKILL.name)

    await expect(
      dialog.getByText('Esta Habilidade não possui bases sugeridas no Currículo.'),
    ).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Fechar' })).toBeVisible()
    const notice = dialog.getByRole('region', { name: NOTICE_TITLE })
    await expect(notice).toBeVisible()
    await expect(notice).toContainText(
      'No Objetivo “Carreira em dados”, ela está concluída. Aqui ela começa do zero, com um novo diagnóstico, e nenhum resultado é copiado.',
    )
    const link = notice.getByRole('link', { name: 'Ver em Carreira em dados' })
    await expect(link).toHaveAttribute(
      'href',
      `/learning/goals/${OTHER_GOAL_ID}/skills/${ids.skillId}`,
    )
    await expect(
      dialog.getByText('A Habilidade será adicionada como não iniciada.'),
    ).toBeVisible()
    await expect(dialog.getByRole('button', { name: 'Cancelar' })).toBeVisible()
    await expect(
      dialog.getByRole('button', { name: 'Adicionar habilidade' }),
    ).toBeEnabled()

    const [lookup] = backend.callsOf('listSkillExperiencesOfSkill_')
    expect(lookup?.data).toMatchObject({ skillId: ids.skillId })

    await dialog.evaluate((element) =>
      Promise.all(element.getAnimations().map((animation) => animation.finished)),
    )
    await authenticatedPage.screenshot({
      path: `${SCREENSHOT_DIRECTORY}/add-skill-dialog-notice-${viewport.name}-${viewport.width}x${viewport.height}.png`,
    })

    const hasHorizontalScroll = await authenticatedPage.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    )
    expect(hasHorizontalScroll).toBe(false)
    expect(consoleErrors).toEqual([])
  })
}

test('follows the notice link to the other experience and returns to the add page', async ({
  authenticatedPage,
  bff,
}) => {
  await installBackend(bff, { experiences: [COMPLETED_ELSEWHERE] })
  await openAddPage(authenticatedPage)
  const dialog = await openDialogFor(authenticatedPage, LOGIC_SKILL.name)

  await dialog.getByRole('link', { name: 'Ver em Carreira em dados' }).click()

  await expect(authenticatedPage).toHaveURL(
    new RegExp(`/learning/goals/${OTHER_GOAL_ID}/skills/${ids.skillId}/?$`),
  )

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: LOGIC_SKILL.name }),
  ).toBeVisible()

  await authenticatedPage.goBack()

  await expect(authenticatedPage).toHaveURL(new RegExp(`${addPath}?$`))
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Adicionar Habilidade' }),
  ).toBeVisible()
})

test('lists each other Goal with its own status and leaves the destination Goal out', async ({
  authenticatedPage,
  bff,
}) => {
  await installBackend(bff, {
    experiences: [
      { ...COMPLETED_ELSEWHERE },
      { ...LEARNING_ELSEWHERE },
      {
        goalId: ids.goalId,
        goalTitle: 'Fundamentos de programação',
        skillExperienceId: LearningRouteIdsFaker.fake().skillExperienceId,
        skillId: ids.skillId,
        status: 'not-started',
      },
    ],
  })
  await openAddPage(authenticatedPage)

  const dialog = await openDialogFor(authenticatedPage, LOGIC_SKILL.name)

  const notice = dialog.getByRole('region', { name: NOTICE_TITLE })
  await expect(notice).toContainText(
    'No Objetivo “Carreira em dados”, ela está concluída.',
  )
  await expect(notice).toContainText(
    'No Objetivo “Dados na prática”, ela está em aprendizado.',
  )
  await expect(notice).not.toContainText('Fundamentos de programação')
  await expect(notice.getByRole('link')).toHaveCount(2)
  await expect(
    notice.getByRole('link', { name: 'Ver em Dados na prática' }),
  ).toHaveAttribute(
    'href',
    `/learning/goals/${SECOND_OTHER_GOAL_ID}/skills/${ids.skillId}`,
  )
})

test('shows no notice when the Skill exists nowhere else', async ({
  authenticatedPage,
  bff,
}) => {
  const backend = await installBackend(bff, { experiences: [] })
  await openAddPage(authenticatedPage)

  const dialog = await openDialogFor(authenticatedPage, LOGIC_SKILL.name)

  await expect.poll(() => backend.callsOf('listSkillExperiencesOfSkill_').length).toBe(1)
  await expect(dialog.getByRole('region', { name: NOTICE_TITLE })).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: 'Adicionar habilidade' })).toBeEnabled()
})

test('shows no notice and still adds when the other experiences lookup fails', async ({
  authenticatedPage,
  bff,
}) => {
  const backend = await installBackend(bff, { lookup: 'fail' })
  await openAddPage(authenticatedPage)

  const dialog = await openDialogFor(authenticatedPage, LOGIC_SKILL.name)

  await expect.poll(() => backend.callsOf('listSkillExperiencesOfSkill_').length).toBe(1)
  await expect(dialog.getByRole('region', { name: NOTICE_TITLE })).toHaveCount(0)
  await expect(dialog.getByRole('alert')).toHaveCount(0)

  await dialog.getByRole('button', { name: 'Adicionar habilidade' }).click()

  await expect(dialog).not.toBeVisible()
  expect(backend.callsOf('addSkillToGoal_')).toHaveLength(1)
})

test('confirms the addition with the Skill id and the selected bases', async ({
  authenticatedPage,
  bff,
}) => {
  const backend = await installBackend(bff)
  await openAddPage(authenticatedPage)

  const dialog = await openDialogFor(authenticatedPage, PYTHON_SKILL.name)
  await expect(
    dialog.getByRole('heading', { name: 'Bases ausentes (1)', level: 3 }),
  ).toBeVisible()
  await dialog.getByRole('checkbox', { name: /Variáveis e tipos/ }).check()
  await expect(
    dialog.getByText(
      'A Habilidade e as bases selecionadas serão adicionadas como não iniciadas.',
    ),
  ).toBeVisible()
  await dialog.getByRole('button', { name: 'Adicionar habilidade' }).click()

  await expect(dialog).not.toBeVisible()
  const addCalls = backend.callsOf('addSkillToGoal_')
  expect(addCalls).toHaveLength(1)
  expect(addCalls[0]?.method).toBe('POST')
  expect(addCalls[0]?.data).toEqual({
    goalId: ids.goalId,
    skillId: OTHER_SKILL_ID,
    foundationSkillIds: [FOUNDATION_ID],
  })
})

test('confirms the addition of a Skill without bases and without a selection', async ({
  authenticatedPage,
  bff,
}) => {
  const backend = await installBackend(bff)
  await openAddPage(authenticatedPage)

  const dialog = await openDialogFor(authenticatedPage, SQL_SKILL.name)
  await dialog.getByRole('button', { name: 'Adicionar habilidade' }).click()

  await expect(dialog).not.toBeVisible()
  expect(backend.callsOf('addSkillToGoal_')[0]?.data).toEqual({
    goalId: ids.goalId,
    skillId: SQL_SKILL.id,
    foundationSkillIds: [],
  })
})

test('keeps the dialog open with the failure and the selection when the addition fails', async ({
  authenticatedPage,
  bff,
}) => {
  const backend = await installBackend(bff, { add: 'fail' })
  await openAddPage(authenticatedPage)

  const dialog = await openDialogFor(authenticatedPage, PYTHON_SKILL.name)
  await dialog.getByRole('checkbox', { name: /Variáveis e tipos/ }).check()
  await dialog.getByRole('button', { name: 'Adicionar habilidade' }).click()

  await expect(dialog.getByRole('alert')).toBeVisible()
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('checkbox', { name: /Variáveis e tipos/ })).toBeChecked()
  await expect(dialog.getByRole('button', { name: 'Adicionar habilidade' })).toBeEnabled()
  expect(backend.callsOf('addSkillToGoal_')).toHaveLength(1)
})

test('cancels the dialog without adding the Skill', async ({
  authenticatedPage,
  bff,
}) => {
  const backend = await installBackend(bff)
  await openAddPage(authenticatedPage)

  const dialog = await openDialogFor(authenticatedPage, LOGIC_SKILL.name)
  await dialog.getByRole('button', { name: 'Cancelar' }).click()

  await expect(dialog).not.toBeVisible()
  expect(backend.callsOf('addSkillToGoal_')).toHaveLength(0)
})

test('traps focus in the dialog, closes it with Escape and returns focus to the Skill action', async ({
  authenticatedPage,
  bff,
}) => {
  await installBackend(bff, { experiences: [COMPLETED_ELSEWHERE] })
  await openAddPage(authenticatedPage)

  const opener = skillRow(authenticatedPage, LOGIC_SKILL.name).getByRole('button', {
    name: 'Adicionar',
  })
  await opener.focus()
  await authenticatedPage.keyboard.press('Enter')
  const dialog = authenticatedPage.getByRole('dialog', {
    name: `Adicionar ${LOGIC_SKILL.name}?`,
  })
  await expect(dialog).toBeVisible()
  await expect(
    dialog.getByRole('link', { name: 'Ver em Carreira em dados' }),
  ).toBeVisible()

  const closeButton = dialog.getByRole('button', { name: 'Fechar' })
  const noticeLink = dialog.getByRole('link', { name: 'Ver em Carreira em dados' })
  const cancelButton = dialog.getByRole('button', { name: 'Cancelar' })
  const confirmButton = dialog.getByRole('button', { name: 'Adicionar habilidade' })

  await expect(closeButton).toBeFocused()
  await authenticatedPage.keyboard.press('Tab')
  await expect(noticeLink).toBeFocused()
  await authenticatedPage.keyboard.press('Tab')
  await expect(cancelButton).toBeFocused()
  await authenticatedPage.keyboard.press('Tab')
  await expect(confirmButton).toBeFocused()
  await authenticatedPage.keyboard.press('Tab')
  await expect(closeButton).toBeFocused()
  await authenticatedPage.keyboard.press('Shift+Tab')
  await expect(confirmButton).toBeFocused()

  await authenticatedPage.keyboard.press('Escape')

  await expect(dialog).not.toBeVisible()
  await expect(opener).toBeFocused()
})

test('returns to the Goal from the back link', async ({ authenticatedPage, bff }) => {
  const backend = await installBackend(bff)
  await openAddPage(authenticatedPage)

  await authenticatedPage.getByRole('link', { name: 'Voltar ao Objetivo' }).click()

  await expect(authenticatedPage).toHaveURL(new RegExp(`${goalPath}?$`))
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Fundamentos de programação',
    }),
  ).toBeVisible()
  expect(backend.callsOf('getGoalDetail')[0]?.data).toMatchObject({ goalId: ids.goalId })
})

test('reaches the back link by keyboard with a visible focus', async ({
  authenticatedPage,
  bff,
}) => {
  await installBackend(bff)
  await openAddPage(authenticatedPage)

  const backLink = authenticatedPage.getByRole('link', { name: 'Voltar ao Objetivo' })
  await backLink.focus()

  await expect(backLink).toBeFocused()
  const outlineWidth = await backLink.evaluate(
    (element) => getComputedStyle(element).outlineWidth,
  )
  expect(Number.parseFloat(outlineWidth)).toBeGreaterThan(0)

  await authenticatedPage.keyboard.press('Enter')
  await expect(authenticatedPage).toHaveURL(new RegExp(`${goalPath}?$`))
})
