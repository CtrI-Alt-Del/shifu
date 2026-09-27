import { expect, navigateAuthenticatedPage, test } from '../playwright'

const IDS = {
  goalId: '01SHF000000000000000000003',
  skillId: '01SHF000000000000000000004',
  masteredCompetencyId: '01SHF000000000000000000001',
  focusCompetencyId: '01SHF000000000000000000002',
  blockedCompetencyId: '01SHF000000000000000000009',
  activityId: '01SHF000000000000000000005',
  attemptId: '01SHF000000000000000000007',
  evaluationId: '01SHF000000000000000000008',
}

const skillPath = `/learning/goals/${IDS.goalId}/skills/${IDS.skillId}`

const diagnosticResponse = {
  status: 'learning',
  nextCompetencyId: null,
  nextActivityId: null,
  pendingAttemptId: null,
  pendingAttemptStatus: null,
  focusCompetencyId: IDS.focusCompetencyId,
  competencies: [],
}

const experienceResponse = {
  goalId: IDS.goalId,
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
  skillStatus: 'learning',
  overallResult: 72.33,
  focusCompetencyId: IDS.focusCompetencyId,
  focusCompetencyName: 'Estruturas de repetição',
  competencies: [
    {
      competencyId: IDS.masteredCompetencyId,
      competencyName: 'Variáveis e tipos',
      position: 1,
      progress: 92,
      status: 'mastered',
      availability: 'available',
      isFocus: false,
    },
    {
      competencyId: IDS.focusCompetencyId,
      competencyName: 'Estruturas de repetição',
      position: 2,
      progress: 72,
      status: 'proficient',
      availability: 'available',
      isFocus: true,
    },
    {
      competencyId: IDS.blockedCompetencyId,
      competencyName: 'Funções',
      position: 3,
      progress: 35,
      status: 'learning',
      availability: 'unavailable',
      isFocus: false,
    },
  ],
  recommendation: {
    competencyId: IDS.focusCompetencyId,
    competencyName: 'Estruturas de repetição',
    activityId: IDS.activityId,
    activityTitle: 'Somar os números pares de uma lista',
    difficulty: 'hard',
    type: 'new-activity',
  },
  evaluation: null,
}

type Overrides = { experience?: Record<string, unknown> }

function serverFnExport(url: string) {
  const id = new URL(url).pathname.split('/_serverFn/')[1] ?? ''
  try {
    return String(
      JSON.parse(Buffer.from(decodeURIComponent(id), 'base64').toString()).export ?? '',
    )
  } catch {
    return ''
  }
}

async function mockTransport(
  page: Parameters<typeof navigateAuthenticatedPage>[0],
  overrides: Overrides = {},
) {
  await page.route('**/_serverFn/**', async (route) => {
    const exported = serverFnExport(route.request().url())

    if (exported.startsWith('getSkillExperienceAction')) {
      await route.fulfill({
        body: JSON.stringify({
          result: { ...experienceResponse, ...overrides.experience },
        }),
        contentType: 'application/json',
      })
      return
    }

    if (exported.startsWith('getDiagnosticAction')) {
      await route.fulfill({
        body: JSON.stringify({ result: diagnosticResponse }),
        contentType: 'application/json',
      })
      return
    }

    if (exported.startsWith('getGoalDetail')) {
      await route.fulfill({
        body: JSON.stringify({
          result: {
            kind: 'success',
            detail: {
              goalId: IDS.goalId,
              title: 'Aprender a programar',
              skills: [
                {
                  skillId: IDS.skillId,
                  skillName: 'Lógica de programação',
                  name: 'Lógica de programação',
                },
              ],
            },
          },
        }),
        contentType: 'application/json',
      })
      return
    }

    await route.fallback()
  })
}

test('renders the Skill experience with its result, focus and recommendation', async ({
  authenticatedPage,
}) => {
  await mockTransport(authenticatedPage)

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Lógica de programação' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Em aprendizado')).toBeVisible()
  await expect(authenticatedPage.getByText('Resultado geral')).toBeVisible()
  await expect(
    authenticatedPage.getByText('Somar os números pares de uma lista'),
  ).toBeVisible()
  await expect(authenticatedPage.getByRole('listitem')).toHaveCount(3)
})

test('opens a released Competency and keeps the identifiers of the route', async ({
  authenticatedPage,
}) => {
  await mockTransport(authenticatedPage)

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(
    authenticatedPage.getByRole('link', { name: /Variáveis e tipos/ }),
  ).toHaveAttribute('href', `${skillPath}/competencies/${IDS.masteredCompetencyId}`)
})

test('keeps a blocked Competency on the page and explains the requirement', async ({
  authenticatedPage,
}) => {
  await mockTransport(authenticatedPage)

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(authenticatedPage.getByRole('link', { name: /Funções/ })).toHaveCount(0)
  await authenticatedPage.getByRole('button', { name: /Funções/ }).click()

  await expect(authenticatedPage.getByRole('alert')).toContainText(
    'Funções ainda está bloqueada',
  )
  await expect(authenticatedPage).toHaveURL(new RegExp(`${IDS.skillId}$`))
})

test('continues the recommended Activity with all four identifiers', async ({
  authenticatedPage,
}) => {
  await mockTransport(authenticatedPage)

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(
    authenticatedPage.getByRole('link', { name: 'Continuar praticando' }),
  ).toHaveAttribute(
    'href',
    `${skillPath}/competencies/${IDS.focusCompetencyId}/activities/${IDS.activityId}`,
  )
  await expect(
    authenticatedPage.getByRole('link', { name: 'Escolher outra' }),
  ).toHaveAttribute('href', `${skillPath}/competencies/${IDS.focusCompetencyId}`)
})

test('omits the recommendation block when the focus has none', async ({
  authenticatedPage,
}) => {
  await mockTransport(authenticatedPage, { experience: { recommendation: null } })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(
    authenticatedPage.getByRole('link', { name: 'Continuar praticando' }),
  ).toHaveCount(0)
  await expect(authenticatedPage.getByRole('listitem')).toHaveCount(3)
})

test('pauses new attempts while an evaluation is running', async ({
  authenticatedPage,
}) => {
  await mockTransport(authenticatedPage, {
    experience: {
      recommendation: null,
      evaluation: {
        evaluationId: IDS.evaluationId,
        attemptId: IDS.attemptId,
        activityId: IDS.activityId,
        competencyId: IDS.focusCompetencyId,
        status: 'pending',
      },
    },
  })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(authenticatedPage.getByRole('status')).toContainText(
    'Avaliando sua resposta',
  )
  await expect(
    authenticatedPage.getByRole('link', { name: 'Continuar praticando' }),
  ).toHaveCount(0)
  await expect(authenticatedPage.getByRole('listitem')).toHaveCount(3)
})

test('recovers a failed evaluation without hiding the released content', async ({
  authenticatedPage,
}) => {
  await mockTransport(authenticatedPage, {
    experience: {
      recommendation: null,
      evaluation: {
        evaluationId: IDS.evaluationId,
        attemptId: IDS.attemptId,
        activityId: IDS.activityId,
        competencyId: IDS.focusCompetencyId,
        status: 'failed',
      },
    },
  })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(authenticatedPage.getByRole('alert')).toContainText(
    'A avaliação não pôde terminar',
  )
  await expect(
    authenticatedPage.getByRole('button', { name: 'Tentar novamente' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('link', { name: /Variáveis e tipos/ }),
  ).toBeVisible()
})

test('is operable by keyboard and has no horizontal scroll on a narrow viewport', async ({
  authenticatedPage,
}) => {
  await mockTransport(authenticatedPage)
  await authenticatedPage.setViewportSize({ height: 812, width: 375 })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await authenticatedPage.getByRole('link', { name: 'Continuar praticando' }).focus()
  await expect(
    authenticatedPage.getByRole('link', { name: 'Continuar praticando' }),
  ).toBeFocused()

  const overflow = await authenticatedPage.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)
})

test('removes the Skill once and returns to the same Objective graph', async ({
  authenticatedPage,
}) => {
  let removalRequests = 0
  let removed = false
  await mockTransport(authenticatedPage)
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const exported = serverFnExport(route.request().url())
    if (exported.startsWith('getGoalDetail') && removed) {
      await route.fulfill({
        body: JSON.stringify({
          result: {
            kind: 'success',
            detail: {
              goalId: IDS.goalId,
              title: 'Aprender a programar',
              skills: [],
              relations: [],
            },
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    if (!exported.startsWith('removeSkill')) {
      await route.fallback()
      return
    }
    removalRequests += 1
    expect(route.request().method()).toBe('POST')
    expect(route.request().postData() ?? '').toContain(IDS.goalId)
    expect(route.request().postData() ?? '').toContain(IDS.skillId)
    removed = true
    await route.fulfill({
      body: JSON.stringify({ result: undefined }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)
  const trigger = authenticatedPage.getByRole('button', {
    name: 'Mais ações de Lógica de programação',
  })
  await trigger.focus()
  await trigger.press('Enter')
  await authenticatedPage.getByRole('menuitem', { name: 'Remover habilidade' }).click()
  const dialog = authenticatedPage.getByRole('alertdialog')
  await expect(dialog.getByText('Lógica de programação', { exact: true })).toBeVisible()
  await expect(dialog.getByText(/Somente esta experiência será removida/)).toBeVisible()
  await dialog.getByRole('button', { name: 'Remover habilidade' }).click()

  await expect(authenticatedPage).toHaveURL(`/learning/goals/${IDS.goalId}`)
  await expect(
    authenticatedPage.getByText('Lógica de programação', { exact: true }),
  ).not.toBeVisible()
  expect(removalRequests).toBe(1)
})

test('cancels with Escape, restores focus and retries a failed removal on mobile', async ({
  authenticatedPage,
}) => {
  let removalRequests = 0
  let removed = false
  await mockTransport(authenticatedPage)
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const exported = serverFnExport(route.request().url())
    if (exported.startsWith('getGoalDetail') && removed) {
      await route.fulfill({
        body: JSON.stringify({
          result: {
            kind: 'success',
            detail: {
              goalId: IDS.goalId,
              title: 'Aprender a programar',
              skills: [],
              relations: [],
            },
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    if (!exported.startsWith('removeSkill')) {
      await route.fallback()
      return
    }
    removalRequests += 1
    if (removalRequests > 1) {
      removed = true
      await route.fulfill({
        body: JSON.stringify({ result: undefined }),
        contentType: 'application/json',
      })
      return
    }
    await route.fulfill({
      body: JSON.stringify({ error: 'Internal Server Error' }),
      contentType: 'application/json',
      status: 500,
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)
  const trigger = authenticatedPage.getByRole('button', {
    name: 'Mais ações de Lógica de programação',
  })
  await trigger.click()
  await authenticatedPage.getByRole('menuitem', { name: 'Remover habilidade' }).click()
  await authenticatedPage.keyboard.press('Escape')
  await expect(authenticatedPage.getByRole('alertdialog')).not.toBeVisible()
  await expect(trigger).toBeFocused()
  expect(removalRequests).toBe(0)

  await trigger.click()
  await authenticatedPage.getByRole('menuitem', { name: 'Remover habilidade' }).click()
  const confirmButton = authenticatedPage
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Remover habilidade' })
  await confirmButton.evaluate((button) => {
    const confirm = button as HTMLButtonElement
    confirm.click()
    confirm.click()
  })
  await expect(authenticatedPage.getByRole('alertdialog')).toContainText(
    'Não foi possível remover a Habilidade. Tente novamente.',
  )
  expect(removalRequests).toBe(1)
  await confirmButton.click()
  await expect(authenticatedPage).toHaveURL(`/learning/goals/${IDS.goalId}`)
  await expect(
    authenticatedPage.getByText('Lógica de programação', { exact: true }),
  ).not.toBeVisible()
  expect(removalRequests).toBe(2)
  const overflow = await authenticatedPage.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)
})
