import { expect, navigateAuthenticatedPage, test } from '../playwright'

const IDS = {
  activityId: '01SHF000000000000000000005',
  competencyId: '01SHF000000000000000000001',
  goalId: '01SHF000000000000000000003',
  materialId: '01SHF000000000000000000006',
  otherCompetencyId: '01SHF000000000000000000009',
  skillId: '01SHF000000000000000000004',
}

const competencyPath = `/learning/goals/${IDS.goalId}/skills/${IDS.skillId}/competencies/${IDS.competencyId}`
const materialPath = `${competencyPath}/materials/${IDS.materialId}`

const MARKDOWN = [
  'O laço percorre uma sequência de valores.',
  '',
  'Repetir à mão falha quando os dados crescem.',
  '',
  '```python',
  'for numero in [1, 2, 3]:',
  '    print(numero)',
  '```',
  '',
  'Use `print` para inspecionar cada passo.',
].join('\n')

const availableResponse = {
  availability: 'available',
  competencyId: IDS.competencyId,
  competencyName: 'Estruturas de repetição',
  content: MARKDOWN,
  goalId: IDS.goalId,
  materialId: IDS.materialId,
  materialTitle: 'Repetição com for',
  recommendation: {
    activityId: IDS.activityId,
    competencyId: IDS.competencyId,
    difficulty: 'hard',
    type: 'new-activity',
  },
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
}

const unavailableResponse = {
  availability: 'unavailable',
  competencyId: IDS.competencyId,
  competencyName: 'Funções',
  focusCompetencyId: IDS.otherCompetencyId,
  focusCompetencyName: 'Fundamentos de lógica',
  goalId: IDS.goalId,
  materialId: IDS.materialId,
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
}

test('renders the official markdown and sends one typed RPC request', async ({
  authenticatedPage,
}) => {
  let materialRequests = 0
  let requestUrl = ''
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    requestUrl = route.request().url()
    if (!requestUrl.includes(IDS.materialId)) {
      await route.fallback()
      return
    }

    materialRequests += 1
    await route.fulfill({
      body: JSON.stringify({ result: availableResponse }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, materialPath)

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Repetição com for' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText('O laço percorre uma sequência de valores.'),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('region', { name: 'Bloco de código em python' }),
  ).toContainText('for numero in [1, 2, 3]:')
  expect(materialRequests).toBe(1)
  expect(requestUrl).toContain(IDS.goalId)
  expect(requestUrl).toContain(IDS.skillId)
  expect(requestUrl).toContain(IDS.competencyId)
  expect(requestUrl).toContain(IDS.materialId)
  await expect(authenticatedPage).toHaveURL(new RegExp(`${IDS.materialId}$`))
})

test('does not interpret HTML embedded in the markdown', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(IDS.materialId)) {
      await route.fallback()
      return
    }

    await route.fulfill({
      body: JSON.stringify({
        result: {
          ...availableResponse,
          content: 'Atenção <img src=x onerror="window.__xss = true"> e <b>negrito</b>.',
        },
      }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, materialPath)

  await expect(
    authenticatedPage.getByText(
      'Atenção <img src=x onerror="window.__xss = true"> e <b>negrito</b>.',
    ),
  ).toBeVisible()
  expect(await authenticatedPage.locator('article img').count()).toBe(0)
  expect(await authenticatedPage.locator('article b').count()).toBe(0)
  expect(await authenticatedPage.evaluate(() => '__xss' in window)).toBe(false)
})

test('returns to the Competency of origin from the material', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const url = route.request().url()
    if (!url.includes(IDS.materialId) && !url.includes(IDS.competencyId)) {
      await route.fallback()
      return
    }

    await route.fulfill({
      body: JSON.stringify({ result: availableResponse }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, materialPath)
  await authenticatedPage
    .getByRole('link', { name: 'Voltar para a Competência Estruturas de repetição' })
    .click()

  await expect(authenticatedPage).toHaveURL(new RegExp(`${IDS.competencyId}$`))
})

test('opens the recommended Activity of the source Competency', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(IDS.materialId)) {
      await route.fallback()
      return
    }

    await route.fulfill({
      body: JSON.stringify({ result: availableResponse }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, materialPath)
  await expect(
    authenticatedPage.getByRole('heading', {
      name: 'Continuar em Estruturas de repetição',
    }),
  ).toBeVisible()
  await authenticatedPage.getByRole('button', { name: 'Praticar' }).click()

  await expect(authenticatedPage).toHaveURL(new RegExp(`activities/${IDS.activityId}$`))
})

test('omits the recommendation block when the Competency has none', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(IDS.materialId)) {
      await route.fallback()
      return
    }

    await route.fulfill({
      body: JSON.stringify({
        result: { ...availableResponse, recommendation: null },
      }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, materialPath)

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Repetição com for' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByRole('button', { name: 'Praticar' })).toHaveCount(0)
  await expect(authenticatedPage.getByText(/Continuar em/)).toHaveCount(0)
})

test('restricts the content when the Competency is not released', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(IDS.materialId)) {
      await route.fallback()
      return
    }

    await route.fulfill({
      body: JSON.stringify({ result: unavailableResponse }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, materialPath)

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Material ainda indisponível',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText(/Fundamentos de lógica/)).toBeVisible()
  await expect(authenticatedPage.getByText('O laço percorre')).toHaveCount(0)
})

test('keeps a private absence generic', async ({ authenticatedPage }) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(IDS.materialId)) {
      await route.fallback()
      return
    }

    await route.fulfill({
      body: JSON.stringify({ result: { kind: 'not-found' } }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, materialPath)

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Recurso não encontrado' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Repetição com for')).toHaveCount(0)
})

test('replaces a recoverable error after one explicit retry', async ({
  authenticatedPage,
}) => {
  let materialRequests = 0
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(IDS.materialId)) {
      await route.fallback()
      return
    }

    materialRequests += 1
    if (materialRequests === 1) {
      await route.fulfill({
        body: JSON.stringify({ kind: 'unavailable' }),
        status: 503,
      })
      return
    }

    await route.fulfill({
      body: JSON.stringify({ result: availableResponse }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, materialPath)
  await expect(
    authenticatedPage.getByRole('heading', {
      name: 'Não foi possível carregar este Material',
    }),
  ).toBeVisible()
  await authenticatedPage.getByRole('button', { name: 'Tentar novamente' }).click()

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Repetição com for' }),
  ).toBeVisible()
  expect(materialRequests).toBe(2)
})

test('redirects anonymous visitors before requesting the material', async ({ page }) => {
  let materialRequested = false
  await page.route('**/_serverFn/**', async (route) => {
    if (route.request().url().includes(IDS.materialId)) materialRequested = true
    await route.fallback()
  })

  await page.goto(materialPath)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(page.getByRole('heading', { name: 'Repetição com for' })).toHaveCount(0)
  expect(materialRequested).toBe(false)
})

test('reaches the code block and the recommendation by keyboard', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(IDS.materialId)) {
      await route.fallback()
      return
    }

    await route.fulfill({
      body: JSON.stringify({ result: availableResponse }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, materialPath)
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Repetição com for' }),
  ).toBeVisible()

  const codeBlock = authenticatedPage.getByRole('region', {
    name: 'Bloco de código em python',
  })
  await codeBlock.focus()
  await expect(codeBlock).toBeFocused()

  await authenticatedPage.getByRole('button', { name: 'Praticar' }).focus()
  await expect(authenticatedPage.getByRole('button', { name: 'Praticar' })).toBeFocused()
})

test('keeps a comfortable reading column on a narrow viewport', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.setViewportSize({ height: 812, width: 375 })
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(IDS.materialId)) {
      await route.fallback()
      return
    }

    await route.fulfill({
      body: JSON.stringify({ result: availableResponse }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, materialPath)

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Repetição com for' }),
  ).toBeVisible()
  const hasHorizontalScroll = await authenticatedPage.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalScroll).toBe(false)
})
