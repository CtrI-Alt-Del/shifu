import {
  DiagnosticOverviewFaker,
  DiagnosticRunIdFaker,
  LearningRouteIdsFaker,
  SkillExperienceDetailFaker,
} from '@/core/learning/fakers'
import type { BffFixtureContract } from '../fixtures/bff-fixture'
import { expect, navigateAuthenticatedPage, test } from '../playwright'

const routeIds = LearningRouteIdsFaker.fake()
const IDS = {
  goalId: routeIds.goalId,
  skillId: routeIds.skillId,
  masteredCompetencyId: routeIds.nextCompetencyId,
  focusCompetencyId: routeIds.competencyId,
  blockedCompetencyId: routeIds.otherCompetencyId,
  activityId: routeIds.activityId,
  attemptId: routeIds.attemptId,
  evaluationId: routeIds.evaluationId,
}

const skillPath = `/learning/goals/${IDS.goalId}/skills/${IDS.skillId}`

const diagnosticResponse = DiagnosticOverviewFaker.fake({
  runState: 'settled',
  readyToComplete: false,
  nextCompetencyId: null,
  nextActivityId: null,
  pendingAttemptId: null,
  pendingAttemptStatus: null,
  activitySequence: [
    {
      competencyId: IDS.focusCompetencyId,
      activityId: IDS.activityId,
    },
  ],
  focusCompetencyId: IDS.focusCompetencyId,
  initialOverallResult: 72.33,
  overallCoverageComplete: true,
  directCompletion: false,
  competencies: [],
})

const experienceResponse = SkillExperienceDetailFaker.fake({
  goalId: IDS.goalId,
  skillId: IDS.skillId,
  skillName: 'Lógica de programação',
  skillStatus: 'learning',
  overallResult: 72.33,
  overallCoverageComplete: true,
  focusCompetencyId: IDS.focusCompetencyId,
  focusCompetencyName: 'Estruturas de repetição',
  competencies: [
    {
      competencyId: IDS.masteredCompetencyId,
      competencyName: 'Variáveis e tipos',
      position: 1,
      progress: 92,
      coverageComplete: true,
      status: 'mastered',
      availability: 'available',
      isFocus: false,
    },
    {
      competencyId: IDS.focusCompetencyId,
      competencyName: 'Estruturas de repetição',
      position: 2,
      progress: 72,
      coverageComplete: true,
      status: 'proficient',
      availability: 'available',
      isFocus: true,
    },
    {
      competencyId: IDS.blockedCompetencyId,
      competencyName: 'Funções',
      position: 3,
      progress: 35,
      coverageComplete: false,
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
    reason: 'Praticar o conceito principal',
    targetConceptName: null,
    materialId: null,
    gap: null,
  },
  recommendationGap: null,
  evaluation: null,
})

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

async function mockTransport(bff: BffFixtureContract, overrides: Overrides = {}) {
  await bff.route(async (route) => {
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
  bff,
}) => {
  await mockTransport(bff)

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Lógica de programação' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Em aprendizado')).toBeVisible()
  await expect(
    authenticatedPage.getByText('Progresso demonstrado').locator('..'),
  ).toContainText('72%')
  await expect(
    authenticatedPage.getByRole('link', { name: 'Ver diagnóstico consolidado' }),
  ).toHaveAttribute('href', `${skillPath}/diagnostic/result`)
  await expect(
    authenticatedPage.getByText('Somar os números pares de uma lista'),
  ).toBeVisible()
  await expect(authenticatedPage.getByRole('listitem')).toHaveCount(3)
})

test('starts a fresh diagnostic entry when reopening an interrupted diagnosis', async ({
  authenticatedPage,
  bff,
}) => {
  const diagnosticRunId = DiagnosticRunIdFaker.fake()
  let diagnosticRequests = 0
  let startRequests = 0
  let startBody = ''
  await mockTransport(bff)

  await bff.route(async (route) => {
    const exported = serverFnExport(route.request().url())
    if (exported.startsWith('getDiagnosticAction')) {
      diagnosticRequests += 1
      const result =
        diagnosticRequests === 1
          ? {
              ...diagnosticResponse,
              status: 'diagnosing',
              runState: 'requires_entry',
            }
          : {
              ...diagnosticResponse,
              status: 'diagnosing',
              runState: 'active',
              nextCompetencyId: IDS.focusCompetencyId,
              nextActivityId: IDS.activityId,
            }
      await route.fulfill({
        body: JSON.stringify({ result }),
        contentType: 'application/json',
      })
      return
    }
    if (exported.startsWith('startSkillAction')) {
      startRequests += 1
      startBody = route.request().postData() ?? ''
      await route.fulfill({
        body: JSON.stringify({ result: { diagnosticRunId } }),
        contentType: 'application/json',
      })
      return
    }
    if (exported.startsWith('getActivityAction')) {
      await route.fulfill({
        body: JSON.stringify({
          result: {
            activityId: IDS.activityId,
            title: 'Somar os números pares',
            difficulty: 'medium',
            activityRevision: 'revision-1',
            canSubmit: true,
            latestAttemptId: null,
            unresolvedAttemptId: null,
            isDiagnostic: true,
            questions: [
              {
                key: 'q1',
                kind: 'single_choice',
                prompt: 'Qual é o resultado?',
                options: [
                  { key: 'a', text: '4' },
                  { key: 'b', text: '6' },
                ],
              },
            ],
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(authenticatedPage).toHaveURL(
    `${skillPath}/competencies/${IDS.focusCompetencyId}/activities/${IDS.activityId}`,
  )
  await expect(authenticatedPage.getByText('Qual é o resultado?')).toBeVisible()
  expect(await authenticatedPage.evaluate(() => window.scrollY)).toBe(0)

  await authenticatedPage.getByRole('radio', { name: '4' }).focus()
  await authenticatedPage.keyboard.press('Space')

  await expect(authenticatedPage.getByRole('radio', { name: '4' })).toBeChecked()
  const secondChoice = authenticatedPage.getByRole('radio', { name: '6' })
  await expect(secondChoice).toBeVisible()
  await expect
    .poll(() =>
      secondChoice.evaluate(
        (element) =>
          window.getComputedStyle(element.closest('.choice-question-option') ?? element)
            .opacity,
      ),
    )
    .toBe('1')
  await expect(
    authenticatedPage.getByRole('link', { name: 'Próxima Atividade' }),
  ).toHaveCount(0)
  expect(diagnosticRequests).toBeGreaterThanOrEqual(2)
  expect(startRequests).toBe(1)
  expect(startBody).toContain('entryKey')
})

test('submits the diagnostic once as a complete batch and opens its consolidated result', async ({
  authenticatedPage,
  bff,
}) => {
  const diagnosticRunId = DiagnosticRunIdFaker.fake()
  const submissionAttemptId = IDS.attemptId
  let diagnosticRequests = 0
  let startBody = ''
  let activityGetPayload = ''
  let diagnosticSubmissionBody = ''
  let diagnosticSubmissionRequests = 0
  let activitySubmissionRequests = 0
  let completionBody = ''
  let previewRequests = 0
  let evaluationReady = false
  let completionRequested = false
  await mockTransport(bff)

  await bff.route(async (route) => {
    const exported = serverFnExport(route.request().url())
    if (exported.startsWith('startSkillAction')) {
      startBody = route.request().postData() ?? ''
      await route.fulfill({
        body: JSON.stringify({ result: { diagnosticRunId } }),
        contentType: 'application/json',
      })
      return
    }
    if (exported.startsWith('getDiagnosticAction')) {
      diagnosticRequests += 1
      let result: Record<string, unknown>
      if (diagnosticRequests === 1) {
        result = {
          ...diagnosticResponse,
          status: 'not-started',
          runState: 'requires_entry',
          competencies: [],
        }
      } else if (diagnosticRequests === 2) {
        result = {
          ...diagnosticResponse,
          status: 'diagnosing',
          runState: 'active',
          nextCompetencyId: IDS.focusCompetencyId,
          nextActivityId: IDS.activityId,
        }
      } else if (!evaluationReady) {
        result = {
          ...diagnosticResponse,
          status: 'diagnosing',
          runState: 'active',
          nextCompetencyId: IDS.focusCompetencyId,
          nextActivityId: IDS.activityId,
          pendingAttemptId: submissionAttemptId,
          pendingAttemptStatus: 'pending',
        }
      } else if (!completionRequested) {
        result = {
          ...diagnosticResponse,
          status: 'diagnosing',
          runState: 'ready_to_complete',
          readyToComplete: true,
        }
      } else {
        result = {
          ...diagnosticResponse,
          status: 'learning',
          runState: 'settled',
          competencies: [
            {
              competencyId: IDS.focusCompetencyId,
              competencyName: 'Estruturas de repetição',
              position: 1,
              progress: 65,
              coverageComplete: false,
              status: 'developing',
              isFocus: true,
              contentReleased: true,
            },
          ],
          initialOverallResult: 65,
          overallCoverageComplete: false,
        }
      }
      await route.fulfill({
        body: JSON.stringify({ result }),
        contentType: 'application/json',
      })
      return
    }
    if (exported.startsWith('getActivityAction')) {
      activityGetPayload = decodeURIComponent(
        `${route.request().url()} ${route.request().postData() ?? ''}`,
      )
      await route.fulfill({
        body: JSON.stringify({
          result: {
            activityId: IDS.activityId,
            title: 'Somar os números pares',
            difficulty: 'medium',
            activityRevision: 'revision-1',
            canSubmit: true,
            latestAttemptId: null,
            unresolvedAttemptId: null,
            isDiagnostic: true,
            questions: [
              {
                key: 'q1',
                kind: 'single_choice',
                prompt: 'Qual é o resultado?',
                options: [
                  { key: 'a', text: '4' },
                  { key: 'b', text: '6' },
                ],
              },
            ],
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    if (exported.startsWith('previewActivityQuestionAction')) {
      previewRequests += 1
    }
    if (exported.startsWith('submitActivityAction')) {
      activitySubmissionRequests += 1
      await route.fulfill({
        body: JSON.stringify({
          result: {
            kind: 'unavailable',
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    if (exported.startsWith('submitDiagnosticAction')) {
      diagnosticSubmissionRequests += 1
      diagnosticSubmissionBody = route.request().postData() ?? ''
      await route.fulfill({
        body: JSON.stringify({ result: { status: 'pending', replayed: false } }),
        contentType: 'application/json',
      })
      return
    }
    if (exported.startsWith('completeDiagnosticAction')) {
      completionRequested = true
      completionBody = route.request().postData() ?? ''
      await route.fulfill({
        body: JSON.stringify({ result: { ok: true } }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)
  await authenticatedPage.getByRole('button', { name: 'Iniciar Habilidade' }).click()

  await expect(authenticatedPage).toHaveURL(
    `${skillPath}/competencies/${IDS.focusCompetencyId}/activities/${IDS.activityId}`,
  )
  await expect(authenticatedPage.getByText('Qual é o resultado?')).toBeVisible()
  expect(startBody).toContain('entryKey')
  expect(startBody).toContain(IDS.goalId)
  expect(startBody).toContain(IDS.skillId)

  await authenticatedPage.getByText('4', { exact: true }).click()

  await expect(authenticatedPage.getByRole('radio', { name: '4' })).toBeChecked()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Enviar diagnóstico' }),
  ).toBeEnabled()
  await authenticatedPage.getByRole('button', { name: 'Enviar diagnóstico' }).click()

  await expect(authenticatedPage.getByText('Avaliando o diagnóstico…')).toBeVisible()
  await expect(authenticatedPage).toHaveURL(
    `${skillPath}/competencies/${IDS.focusCompetencyId}/activities/${IDS.activityId}`,
  )
  await expect(
    authenticatedPage.getByRole('button', { name: 'Enviar diagnóstico' }),
  ).toHaveCount(0)
  await authenticatedPage.evaluate((to) => {
    const router = (
      window as Window & {
        __TSR_ROUTER__: { navigate: (options: { to: string }) => Promise<void> }
      }
    ).__TSR_ROUTER__
    return router.navigate({ to })
  }, skillPath)
  await expect(authenticatedPage).toHaveURL(
    `${skillPath}/competencies/${IDS.focusCompetencyId}/activities/${IDS.activityId}`,
  )
  await expect(authenticatedPage.getByText('Avaliando o diagnóstico…')).toBeVisible()
  await expect(
    authenticatedPage.getByText('Aguardando a avaliação da última resposta.'),
  ).toHaveCount(0)
  evaluationReady = true
  await expect(authenticatedPage).toHaveURL(`${skillPath}/diagnostic/result`)
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Seu ponto de partida' }),
  ).toBeVisible()
  expect(diagnosticSubmissionRequests).toBe(1)
  expect(diagnosticSubmissionBody).toContain(diagnosticRunId)
  expect(diagnosticSubmissionBody).toContain('activityRevision')
  expect(diagnosticSubmissionBody).toContain('selectedOptionKeys')
  expect(activitySubmissionRequests).toBe(0)
  expect(activityGetPayload).toContain(diagnosticRunId)
  expect(completionBody).toContain(diagnosticRunId)
  expect(previewRequests).toBe(0)
})

test('opens a released Competency and keeps the identifiers of the route', async ({
  authenticatedPage,
  bff,
}) => {
  await mockTransport(bff)

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(
    authenticatedPage.getByRole('link', { name: /Variáveis e tipos/ }),
  ).toHaveAttribute('href', `${skillPath}/competencies/${IDS.masteredCompetencyId}`)
})

test('keeps a blocked Competency on the page and explains the requirement', async ({
  authenticatedPage,
  bff,
}) => {
  await mockTransport(bff)

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
  bff,
}) => {
  await mockTransport(bff)

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
  bff,
}) => {
  await mockTransport(bff, { experience: { recommendation: null } })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  await expect(
    authenticatedPage.getByRole('link', { name: 'Continuar praticando' }),
  ).toHaveCount(0)
  await expect(authenticatedPage.getByRole('listitem')).toHaveCount(3)
})

test('pauses new attempts while an evaluation is running', async ({
  authenticatedPage,
  bff,
}) => {
  await mockTransport(bff, {
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
  bff,
}) => {
  await mockTransport(bff, {
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
  bff,
}) => {
  await mockTransport(bff)
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
  bff,
}) => {
  let removalRequests = 0
  let removed = false
  await mockTransport(bff)

  await bff.route(async (route) => {
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
  bff,
}) => {
  let removalRequests = 0
  let removed = false
  await mockTransport(bff)
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })

  await bff.route(async (route) => {
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
