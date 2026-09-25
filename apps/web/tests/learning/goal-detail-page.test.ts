import { expect, navigateAuthenticatedPage, test } from '../playwright'

const ids = {
  goalId: '01SHF000000000000000000003',
  skillExperienceId: '01SHF000000000000000000004',
  skillId: '01SHF000000000000000000005',
}

const detailPath = `/learning/goals/${ids.goalId}/`

const detailResponse = {
  goalId: ids.goalId,
  title: 'Fundamentos de programação',
  description: 'Construa uma base sólida para resolver problemas.',
  skills: [
    {
      skillExperienceId: ids.skillExperienceId,
      skillId: ids.skillId,
      name: 'Lógica de programação',
      status: 'learning',
      progress: 60,
      inclusionReason: 'Base para programação',
    },
  ],
  relations: [],
}

test('renders the real goal detail and preserves the skill destination through mocked BFF transport', async ({
  authenticatedPage,
}) => {
  let goalDetailRequests = 0
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(ids.goalId)) {
      await route.fallback()
      return
    }
    goalDetailRequests += 1
    await route.fulfill({
      body: JSON.stringify({ result: { kind: 'success', detail: detailResponse } }),
      contentType: 'application/json',
      status: 200,
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, detailPath)

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: detailResponse.title }),
  ).toBeVisible()
  await authenticatedPage.getByRole('tab', { name: 'Lista' }).click()
  await expect(
    authenticatedPage.getByRole('link', { name: 'Lógica de programação' }),
  ).toHaveAttribute('href', `/learning/goals/${ids.goalId}/skills/${ids.skillId}`)
  await expect(
    authenticatedPage.getByRole('button', {
      name: 'Mais ações de Lógica de programação',
    }),
  ).toBeDisabled()
  expect(goalDetailRequests).toBe(1)
})

test('pans the canvas and restores its initial view from the graph button', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(ids.goalId)) {
      await route.fallback()
      return
    }
    await route.fulfill({
      body: JSON.stringify({ result: { kind: 'success', detail: detailResponse } }),
      contentType: 'application/json',
      status: 200,
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, detailPath)

  const graph = authenticatedPage.getByRole('region', { name: 'Grafo de Habilidades' })
  const viewport = graph.locator('.react-flow__viewport')
  const reset = graph.getByRole('button', { name: 'Restaurar posição inicial do grafo' })
  await expect(reset).toBeEnabled({ timeout: 15_000 })
  const initialTransform = await viewport.evaluate((element) => element.style.transform)
  await graph.scrollIntoViewIfNeeded()
  const pane = graph.locator('.react-flow__pane')
  const bounds = await pane.boundingBox()
  expect(bounds).not.toBeNull()
  if (!bounds) return
  await authenticatedPage.mouse.move(bounds.x + 45, bounds.y + bounds.height - 90)
  await authenticatedPage.mouse.down()
  await authenticatedPage.mouse.move(bounds.x + 145, bounds.y + bounds.height - 90, {
    steps: 5,
  })
  await authenticatedPage.mouse.up()
  await expect
    .poll(() => viewport.evaluate((element) => element.style.transform))
    .not.toBe(initialTransform)
  const pannedTransform = await viewport.evaluate((element) => element.style.transform)
  await graph.getByRole('button', { name: 'Ampliar grafo' }).click()
  await expect
    .poll(() => viewport.evaluate((element) => element.style.transform))
    .not.toBe(pannedTransform)

  await reset.hover()
  await expect(graph.getByRole('tooltip')).toBeVisible()
  await reset.click()
  await expect
    .poll(() => viewport.evaluate((element) => element.style.transform))
    .toBe(initialTransform)

  await authenticatedPage.mouse.move(bounds.x + 45, bounds.y + bounds.height - 90)
  await authenticatedPage.mouse.wheel(0, -400)
  await expect
    .poll(() => viewport.evaluate((element) => element.style.transform))
    .not.toBe(initialTransform)
  const wheelZoomTransform = await viewport.evaluate((element) => element.style.transform)
  await authenticatedPage.mouse.wheel(0, 400)
  await expect
    .poll(() => viewport.evaluate((element) => element.style.transform))
    .not.toBe(wheelZoomTransform)
  await reset.click()
  await expect
    .poll(() => viewport.evaluate((element) => element.style.transform))
    .toBe(initialTransform)

  await authenticatedPage.setViewportSize({ width: 390, height: 844 })
  await graph.scrollIntoViewIfNeeded()
  const mobileInitialTransform = await viewport.evaluate(
    (element) => element.style.transform,
  )
  const mobileBounds = await pane.boundingBox()
  expect(mobileBounds).not.toBeNull()
  if (!mobileBounds) return
  await authenticatedPage.mouse.move(
    mobileBounds.x + 35,
    mobileBounds.y + mobileBounds.height - 90,
  )
  await authenticatedPage.mouse.down()
  await authenticatedPage.mouse.move(
    mobileBounds.x + 85,
    mobileBounds.y + mobileBounds.height - 90,
    { steps: 5 },
  )
  await authenticatedPage.mouse.up()
  await expect
    .poll(() => viewport.evaluate((element) => element.style.transform))
    .not.toBe(mobileInitialTransform)
  await reset.focus()
  await expect(graph.getByRole('tooltip')).toBeVisible()
  await reset.press('Enter')
  await expect
    .poll(() => viewport.evaluate((element) => element.style.transform))
    .toBe(mobileInitialTransform)
})

test('highlights only the prerequisite path of a hovered or focused skill', async ({
  authenticatedPage,
}) => {
  const pathSkills = ['A', 'B', 'C', 'D', 'E'].map((name, index) => ({
    skillExperienceId: `01SHF00000000000000000001${index}`,
    skillId: `01SHF00000000000000000002${index}`,
    name,
    status: 'not-started' as const,
    progress: null,
    inclusionReason: null,
  }))
  const [a, b, c, d, e] = pathSkills
  const pathDetail = {
    ...detailResponse,
    skills: pathSkills,
    relations: [
      { foundationSkillId: a.skillId, skillId: b.skillId },
      { foundationSkillId: b.skillId, skillId: c.skillId },
      { foundationSkillId: e.skillId, skillId: c.skillId },
    ],
  }
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(ids.goalId)) {
      await route.fallback()
      return
    }
    await route.fulfill({
      body: JSON.stringify({ result: { kind: 'success', detail: pathDetail } }),
      contentType: 'application/json',
      status: 200,
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, detailPath)

  const graph = authenticatedPage.getByRole('region', { name: 'Grafo de Habilidades' })
  const edge = (id: string) =>
    graph.locator(`.react-flow__edge[data-id="${id}"] .react-flow__edge-path`)
  const pathEdgeIds = [
    `goal-root-${a.skillId}`,
    `${a.skillId}-${b.skillId}`,
    `${b.skillId}-${c.skillId}`,
    `goal-root-${e.skillId}`,
    `${e.skillId}-${c.skillId}`,
  ]
  const unrelatedEdge = edge(`goal-root-${d.skillId}`)
  const card = graph
    .getByRole('link', { name: 'Abrir Habilidade C' })
    .locator('xpath=ancestor::article')
  await card.hover()
  for (const edgeId of pathEdgeIds) {
    await expect(edge(edgeId)).toHaveCSS('stroke', 'rgb(242, 139, 139)')
    await expect(edge(edgeId)).toHaveCSS('animation-name', 'goal-graph-path-flow')
  }
  await expect(unrelatedEdge).not.toHaveCSS('stroke', 'rgb(242, 139, 139)')
  await expect(unrelatedEdge).toHaveCSS('animation-name', 'none')

  await authenticatedPage.emulateMedia({ reducedMotion: 'reduce' })
  for (const edgeId of pathEdgeIds) {
    await expect(edge(edgeId)).toHaveCSS('animation-name', 'none')
  }
  await authenticatedPage.emulateMedia({ reducedMotion: 'no-preference' })

  await graph.locator('.react-flow__pane').hover({ position: { x: 20, y: 80 } })
  for (const edgeId of pathEdgeIds) {
    await expect(edge(edgeId)).not.toHaveCSS('stroke', 'rgb(242, 139, 139)')
  }
  await card.getByRole('link', { name: 'Abrir Habilidade C' }).focus()
  for (const edgeId of pathEdgeIds) {
    await expect(edge(edgeId)).toHaveCSS('stroke', 'rgb(242, 139, 139)')
  }
})

test('shows private absence without objective data through mocked BFF transport', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(ids.goalId)) {
      await route.fallback()
      return
    }
    await route.fulfill({
      body: JSON.stringify({ result: { kind: 'not-found' } }),
      contentType: 'application/json',
      status: 200,
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, detailPath)

  await expect(
    authenticatedPage.getByRole('heading', { name: 'Objetivo não encontrado' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('heading', { name: detailResponse.title }),
  ).not.toBeVisible()
})

test('redirects anonymous visitors before a goal detail request', async ({ page }) => {
  await page.goto(detailPath)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', { name: detailResponse.title }),
  ).not.toBeVisible()
})
