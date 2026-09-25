import { expect, navigateAuthenticatedPage, test } from '../playwright'

const IDS = {
  activityId: '01SHF000000000000000000005',
  competencyId: '01SHF000000000000000000001',
  goalId: '01SHF000000000000000000003',
  materialId: '01SHF000000000000000000006',
  skillId: '01SHF000000000000000000004',
}

const detailPath = `/learning/goals/${IDS.goalId}/skills/${IDS.skillId}/competencies/${IDS.competencyId}`

const availableResponse = {
  availability: 'available',
  competencyId: IDS.competencyId,
  competencyName: 'Estruturas de repetição',
  focusCompetencyId: IDS.competencyId,
  focusCompetencyName: 'Estruturas de repetição',
  focusReturned: false,
  goalId: IDS.goalId,
  isFocus: true,
  items: [
    {
      id: IDS.materialId,
      kind: 'material',
      position: 1,
      title: 'Repetição com for',
    },
    {
      activityType: 'learning',
      difficulty: 'hard',
      id: IDS.activityId,
      kind: 'activity',
      latestScore: null,
      position: 2,
      title: 'Somar os números pares de uma lista',
    },
  ],
  progress: 72,
  recommendation: {
    activityId: IDS.activityId,
    competencyId: IDS.competencyId,
    difficulty: 'hard',
    type: 'new-activity',
  },
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
  status: 'proficient',
}

test('renders the available focus state and sends one typed RPC request', async ({
  authenticatedPage,
}) => {
  let detailRequests = 0
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const requestUrl = route.request().url()
    if (!requestUrl.includes(IDS.competencyId)) {
      await route.fallback()
      return
    }

    detailRequests += 1
    await route.fulfill({
      body: JSON.stringify({ result: availableResponse }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, detailPath)

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Estruturas de repetição',
    }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('link', {
      name: 'Praticar Somar os números pares de uma lista',
    }),
  ).toHaveAttribute(
    'href',
    `/learning/goals/${IDS.goalId}/skills/${IDS.skillId}/competencies/${IDS.competencyId}/activities/${IDS.activityId}`,
  )
  expect(detailRequests).toBe(1)
  await expect(authenticatedPage.locator('body')).not.toHaveCSS('overflow-x', 'scroll')
})

test('protects the Competency route and preserves its dynamic IDs', async ({
  authenticatedPage,
}) => {
  let requestUrl = ''
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    requestUrl = route.request().url()
    if (!requestUrl.includes(IDS.competencyId)) {
      await route.fallback()
      return
    }

    await route.fulfill({
      body: JSON.stringify({
        result: {
          availability: 'unavailable',
          competencyId: IDS.competencyId,
          competencyName: 'Estruturas de repetição',
          focusCompetencyId: null,
          focusCompetencyName: null,
          goalId: IDS.goalId,
          skillId: IDS.skillId,
          skillName: 'Lógica de programação',
        },
      }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, detailPath)

  await expect(authenticatedPage).toHaveURL(new RegExp(`${IDS.competencyId}$`))
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Competência ainda indisponível' }),
  ).toBeVisible()
  expect(requestUrl).toContain(IDS.goalId)
  expect(requestUrl).toContain(IDS.skillId)
  expect(requestUrl).toContain(IDS.competencyId)
})

test('redirects anonymous visitors before the Competency detail request', async ({
  page,
}) => {
  await page.goto(detailPath)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(
    page.getByRole('heading', { name: 'Estruturas de repetição' }),
  ).not.toBeVisible()
})

test('navigates from the Competency detail to the protected Activity route', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const body = route.request().postData() ?? ''
    const payload = decodeURIComponent(`${route.request().url()} ${body}`)
    if (payload.includes(IDS.activityId)) {
      await route.fulfill({
        body: JSON.stringify({
          result: {
            activityId: IDS.activityId,
            title: 'Somar os números pares de uma lista',
            difficulty: 'hard',
            canSubmit: true,
            latestAttemptId: null,
            unresolvedAttemptId: null,
            questions: [
              {
                key: 'q1',
                kind: 'single_choice',
                prompt: 'Qual soma?',
                options: [
                  { key: 'a', text: '2' },
                  { key: 'b', text: '4' },
                ],
              },
            ],
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    if (payload.includes(IDS.competencyId)) {
      await route.fulfill({
        body: JSON.stringify({ result: availableResponse }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, detailPath)
  await authenticatedPage
    .getByRole('link', { name: 'Praticar Somar os números pares de uma lista' })
    .click()
  await expect(authenticatedPage).toHaveURL(new RegExp(`${IDS.activityId}/?$`))
  await expect(
    authenticatedPage.getByRole('heading', {
      name: 'Somar os números pares de uma lista',
    }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Qual soma?' }),
  ).toBeVisible()
})

test('redirects anonymous visitors before the Activity contract loader', async ({
  page,
}) => {
  await page.goto(`${detailPath}/activities/${IDS.activityId}`)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(page.locator('body')).not.toContainText('Not Found')
})

test('links a Material row to its own route with the Competency of origin', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    if (!route.request().url().includes(IDS.competencyId)) {
      await route.fallback()
      return
    }

    await route.fulfill({
      body: JSON.stringify({ result: availableResponse }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, detailPath)

  await expect(
    authenticatedPage.getByRole('link', {
      name: 'Repetição com for — Material de apoio',
    }),
  ).toHaveAttribute('href', `${detailPath}/materials/${IDS.materialId}`)
})

test('renders the official Material with a path back to its Competency', async ({
  authenticatedPage,
}) => {
  const materialPath = `${detailPath}/materials/${IDS.materialId}`
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const descriptor = new URL(route.request().url()).pathname.split('/_serverFn/')[1]
    if (descriptor) {
      const fn = JSON.parse(Buffer.from(descriptor, 'base64').toString('utf-8')).export
      if (fn.startsWith('getMaterialDetailAction_')) {
        await route.fulfill({
          body: JSON.stringify({
            result: {
              availability: 'available',
              goalId: IDS.goalId,
              skillId: IDS.skillId,
              skillName: 'Lógica de programação',
              competencyId: IDS.competencyId,
              competencyName: 'Estruturas de repetição',
              materialId: IDS.materialId,
              materialTitle: 'Repetição com for',
              content: 'Leia sobre laços de repetição.',
              recommendation: {
                activityId: IDS.activityId,
                competencyId: IDS.competencyId,
                difficulty: 'hard',
                type: 'new-activity',
              },
            },
          }),
          contentType: 'application/json',
        })
        return
      }
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, materialPath)

  await expect(
    authenticatedPage.getByRole('heading', { name: 'Repetição com for' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText('Leia sobre laços de repetição.'),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('link', { name: /Voltar para a Competência/ }),
  ).toHaveAttribute('href', detailPath)
  await expect(
    authenticatedPage.getByText(/leitura é opcional e não altera seu progresso/i),
  ).toBeVisible()
})

test('redirects anonymous visitors before the Material contract loader', async ({
  page,
}) => {
  await page.goto(`${detailPath}/materials/${IDS.materialId}`)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(page.locator('body')).not.toContainText('Not Found')
})

test('replaces a recoverable error after one explicit retry without changing IDs', async ({
  authenticatedPage,
}) => {
  let detailRequests = 0
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const requestUrl = route.request().url()
    if (!requestUrl.includes(IDS.competencyId)) {
      await route.fallback()
      return
    }

    detailRequests += 1
    if (detailRequests === 1) {
      await route.fulfill({ status: 503, body: JSON.stringify({ kind: 'unavailable' }) })
      return
    }

    await route.fulfill({
      body: JSON.stringify({ result: availableResponse }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, detailPath)
  await expect(
    authenticatedPage.getByRole('heading', {
      name: 'Não foi possível carregar esta Competência',
    }),
  ).toBeVisible()
  await authenticatedPage.getByRole('button', { name: 'Tentar novamente' }).click()
  await expect(
    authenticatedPage.getByRole('heading', {
      name: 'Estruturas de repetição',
    }),
  ).toBeVisible()
  expect(detailRequests).toBe(2)
})
