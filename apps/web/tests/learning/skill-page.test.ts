import type { Page } from '@playwright/test'

import {
  AvailableCompetencyDetailFaker,
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

type Overrides = {
  experience?: Record<string, unknown>
  diagnostic?: Record<string, unknown>
}

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
        body: JSON.stringify({
          result: { ...diagnosticResponse, ...overrides.diagnostic },
        }),
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

type CompletedStateName = 'evolution' | 'diagnosis' | 'partial'

const evolutionCompletion = SkillExperienceDetailFaker.fakeCompletion()
const [firstCompetency, secondCompetency, thirdCompetency, fourthCompetency] =
  evolutionCompletion.competencies
if (!firstCompetency || !secondCompetency || !thirdCompetency || !fourthCompetency)
  throw new Error('The completion faker must provide four Competencies')

const COMPLETED_STATES: Record<
  CompletedStateName,
  {
    completion: ReturnType<typeof SkillExperienceDetailFaker.fakeCompletion>
    intro: string
    legend: string[]
    indicators: string[]
    overall: { initial: string; final: string; sign: string; startingLabel?: string }
    review: string
  }
> = {
  evolution: {
    completion: evolutionCompletion,
    intro:
      'Compare o ponto de partida com o resultado final. A prática continua liberada, mas novas notas não alteram este resumo.',
    legend: ['Ponto de partida', 'Evolução até agora'],
    indicators: [
      'Do início à conclusão11 dias',
      'Atividades de aprendizagem feitas14',
      'Tentativas enviadas até a conclusão22',
    ],
    overall: { initial: '64%', final: '91%', sign: '→' },
    review:
      'Notas de revisão ficam no histórico e não alteram o resultado oficial desta Habilidade.',
  },
  diagnosis: {
    completion: SkillExperienceDetailFaker.fakeCompletion({
      startedOn: '2026-09-02',
      completedOn: '2026-09-02',
      durationDays: 0,
      completedByDiagnosis: true,
      learningActivityCount: null,
      learningAttemptCount: null,
      initialResult: 90,
      finalResult: 90,
      competencies: [
        { ...firstCompetency, initialProgress: 92, finalProgress: 92 },
        { ...secondCompetency, initialProgress: 90, finalProgress: 90 },
        { ...thirdCompetency, initialProgress: 88, finalProgress: 88 },
        { ...fourthCompetency, initialProgress: 91, finalProgress: 91 },
      ].map((competency) => ({ ...competency, masteredOn: '2026-09-02' })),
      review: { attemptCount: 0, latestScore: null },
    }),
    intro:
      'Você concluiu esta Habilidade no diagnóstico, por isso o ponto de partida e o resultado final são iguais. A prática continua liberada, mas novas notas não alteram este resumo.',
    legend: ['Ponto de partida = resultado final'],
    indicators: ['Do início à conclusãoNo mesmo dia'],
    overall: { initial: '90%', final: '90%', sign: '=' },
    review:
      'Você ainda não fez revisões. A prática continua disponível, e as notas de revisão não alteram o resultado oficial desta Habilidade.',
  },
  partial: {
    completion: SkillExperienceDetailFaker.fakeCompletion({
      initialResult: 75,
      initialResultCoverage: 'partial',
      competencies: [
        firstCompetency,
        secondCompetency,
        { ...thirdCompetency, initialCoverage: 'partial' },
        { ...fourthCompetency, initialProgress: null, initialCoverage: 'unknown' },
      ],
    }),
    intro:
      'Compare o ponto de partida com o resultado final. O diagnóstico não observou todas as dificuldades, então parte do ponto de partida é parcial ou desconhecida. A prática continua liberada, mas novas notas não alteram este resumo.',
    legend: ['Ponto de partida', 'Evolução até agora', 'Resultado sem ponto de partida'],
    indicators: [
      'Do início à conclusão11 dias',
      'Atividades de aprendizagem feitas14',
      'Tentativas enviadas até a conclusão22',
    ],
    overall: {
      initial: '75%',
      final: '91%',
      sign: '→',
      startingLabel: 'Ponto de partida parcial',
    },
    review:
      'Notas de revisão ficam no histórico e não alteram o resultado oficial desta Habilidade.',
  },
}

const VIEWPORTS = [
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'mobile-390', width: 390, height: 844 },
] as const

const completedCompetencyPath = (competencyId: string) =>
  `${skillPath}/competencies/${competencyId}`

function trackBrowserErrors(page: Page) {
  const consoleErrors: string[] = []
  const pageErrors: string[] = []
  page.on('console', (message) => {
    // Unmocked shell requests may log failed resource loads; only script errors count.
    if (message.type() === 'error' && !/Failed to load resource/.test(message.text()))
      consoleErrors.push(message.text())
  })
  page.on('pageerror', (error) => pageErrors.push(error.message))
  return { consoleErrors, pageErrors }
}

async function mockCompletedTransport(
  bff: BffFixtureContract,
  stateName: CompletedStateName,
) {
  const { completion } = COMPLETED_STATES[stateName]
  const detailRequests: string[] = []
  await mockTransport(bff, {
    diagnostic: { status: 'completed' },
    experience: {
      skillStatus: 'completed',
      recommendation: null,
      overallResult: completion.finalResult,
      completion,
    },
  })
  await bff.route(async (route) => {
    if (serverFnExport(route.request().url()).startsWith('getSkillExperienceAction'))
      detailRequests.push(
        decodeURIComponent(
          `${route.request().url()} ${route.request().postData() ?? ''}`,
        ),
      )
    await route.fallback()
  })
  return { completion, detailRequests }
}

for (const stateName of Object.keys(COMPLETED_STATES) as CompletedStateName[]) {
  for (const viewport of VIEWPORTS) {
    test(`renders the ${stateName} completed Skill at ${viewport.name} and marks Objetivos active`, async ({
      authenticatedPage,
      bff,
    }) => {
      const expected = COMPLETED_STATES[stateName]
      const { completion, detailRequests } = await mockCompletedTransport(bff, stateName)
      const { consoleErrors, pageErrors } = trackBrowserErrors(authenticatedPage)
      await authenticatedPage.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      })
      await authenticatedPage.emulateMedia({ reducedMotion: 'reduce' })

      await navigateAuthenticatedPage(authenticatedPage, skillPath)

      await expect(
        authenticatedPage.getByRole('heading', {
          level: 1,
          name: 'Lógica de programação',
        }),
      ).toBeVisible()
      await expect(authenticatedPage).toHaveURL(skillPath)
      await expect(
        authenticatedPage.getByText('Concluída', { exact: true }),
      ).toBeVisible()
      await expect(
        authenticatedPage.getByText(
          stateName === 'diagnosis' ? '2 set → 2 set' : '2 set → 13 set',
        ),
      ).toBeVisible()
      await expect(authenticatedPage.getByText(expected.intro)).toBeVisible()
      await expect(
        authenticatedPage
          .getByRole('list', { name: 'Indicadores da Habilidade' })
          .getByRole('listitem'),
      ).toHaveText(expected.indicators)
      await expect(
        authenticatedPage
          .getByRole('list', { name: 'Legenda da comparação' })
          .getByRole('listitem'),
      ).toHaveText(expected.legend)

      const overall = authenticatedPage.getByRole('region', {
        name: 'Resultado geral da Habilidade',
      })
      await expect(overall).toContainText(expected.overall.initial)
      await expect(overall).toContainText(expected.overall.final)
      await expect(overall).toContainText(expected.overall.sign)
      if (expected.overall.startingLabel)
        await expect(overall).toContainText(expected.overall.startingLabel)
      else await expect(overall).not.toContainText('Ponto de partida')

      const rows = authenticatedPage
        .getByRole('region', { name: 'Competências desta Habilidade' })
        .getByRole('link')
      await expect(rows).toHaveCount(completion.competencies.length)
      for (const competency of completion.competencies) {
        await expect(
          authenticatedPage.getByRole('link', {
            name: new RegExp(`^${competency.competencyName}\\.`),
          }),
        ).toHaveAttribute('href', completedCompetencyPath(competency.competencyId))
      }
      if (stateName === 'partial') {
        await expect(rows.nth(2)).toContainText('Ponto de partida parcial')
        await expect(rows.nth(3)).toContainText('Ponto de partida desconhecido')
        await expect(rows.nth(3)).toContainText('—')
      }
      if (stateName === 'diagnosis') {
        await expect(overall).toContainText('=')
        await expect(rows.first()).toContainText('Dominada em 2 set')
      }

      const review = authenticatedPage.getByRole('region', { name: 'Prática de revisão' })
      await expect(review).toContainText(expected.review)
      if (stateName === 'diagnosis')
        await expect(review.getByRole('listitem')).toHaveCount(0)
      else {
        await expect(review).toContainText('3tentativas de revisão')
        await expect(review).toContainText('85última nota de revisão')
      }

      await expect(
        authenticatedPage.getByRole('link', { name: 'Voltar ao Objetivo' }),
      ).toHaveAttribute('href', `/learning/goals/${IDS.goalId}`)
      await expect(
        authenticatedPage.getByRole('link', { name: 'Ver diagnóstico consolidado' }),
      ).toHaveCount(0)
      await expect(authenticatedPage.getByText('Progresso demonstrado')).toHaveCount(0)

      if (viewport.width >= 1024) {
        const navigation = authenticatedPage.getByRole('navigation', {
          name: 'Navegação principal',
        })
        await expect(navigation.getByRole('link', { name: 'Objetivos' })).toHaveAttribute(
          'aria-current',
          'page',
        )
        await expect(navigation.locator('[aria-current="page"]')).toHaveCount(1)
      } else {
        const bottomBar = authenticatedPage.getByRole('navigation', {
          name: 'Navegação inferior',
        })
        await expect(
          bottomBar.getByRole('link', { name: 'Objetivos — navegação inferior' }),
        ).toHaveAttribute('aria-current', 'page')
        await expect(bottomBar.locator('[aria-current="page"]')).toHaveCount(1)
      }

      const menuSurface = authenticatedPage
        .getByRole('button', { name: 'Mais ações de Lógica de programação' })
        .locator('span[aria-hidden="true"]')
      const menuBox = await menuSurface.boundingBox()
      expect(menuBox?.width).toBe(44)
      expect(menuBox?.height).toBe(44)
      await expect(menuSurface).toHaveCSS('border-top-width', '1px')
      // The design stroke is white at 33% (token control-border), not the 8% base color.
      await expect(menuSurface).toHaveCSS('border-top-color', 'rgba(255, 255, 255, 0.33)')

      const overflow = await authenticatedPage.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      )
      expect(overflow).toBeLessThanOrEqual(0)

      await authenticatedPage.screenshot({
        fullPage: true,
        path: `.playwright-cli/screenshots/skill-completion/skill-completion-${stateName}-${viewport.name}.png`,
      })

      expect(detailRequests.length).toBeGreaterThanOrEqual(1)
      for (const request of detailRequests) {
        expect(request).toContain(IDS.goalId)
        expect(request).toContain(IDS.skillId)
      }
      expect(consoleErrors).toEqual([])
      expect(pageErrors).toEqual([])
    })
  }
}

test('opens a Competency from the completed view by keyboard and returns with the back link', async ({
  authenticatedPage,
  bff,
}) => {
  const { completion } = await mockCompletedTransport(bff, 'evolution')
  const target = completion.competencies[0]
  if (!target) throw new Error('The completion must have a first Competency')
  const competencyRequests: string[] = []
  await bff.route(async (route) => {
    if (!serverFnExport(route.request().url()).startsWith('getCompetencyDetailAction')) {
      await route.fallback()
      return
    }
    competencyRequests.push(decodeURIComponent(route.request().url()))
    await route.fulfill({
      body: JSON.stringify({
        result: AvailableCompetencyDetailFaker.fake({
          competencyId: target.competencyId,
          competencyName: target.competencyName,
          goalId: IDS.goalId,
          skillId: IDS.skillId,
          skillName: 'Lógica de programação',
        }),
      }),
      contentType: 'application/json',
    })
  })
  const { consoleErrors, pageErrors } = trackBrowserErrors(authenticatedPage)
  await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
  await authenticatedPage.emulateMedia({ reducedMotion: 'reduce' })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Lógica de programação' }),
  ).toBeVisible()

  const menuTrigger = authenticatedPage.getByRole('button', {
    name: 'Mais ações de Lógica de programação',
  })
  const firstRow = authenticatedPage.getByRole('link', {
    name: new RegExp(`^${target.competencyName}\\.`),
  })
  await menuTrigger.focus()
  await authenticatedPage.keyboard.press('Tab')
  await expect(firstRow).toBeFocused()
  await expect(firstRow).toHaveCSS('outline-style', 'solid')
  await expect(firstRow).toHaveCSS('outline-width', '2px')

  await authenticatedPage.keyboard.press('Enter')

  await expect(authenticatedPage).toHaveURL(completedCompetencyPath(target.competencyId))
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: target.competencyName }),
  ).toBeVisible()
  expect(competencyRequests.length).toBeGreaterThanOrEqual(1)
  expect(competencyRequests[0]).toContain(target.competencyId)

  await authenticatedPage.getByRole('link', { name: 'Voltar para a Habilidade' }).click()

  await expect(authenticatedPage).toHaveURL(skillPath)
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Lógica de programação' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Concluída', { exact: true })).toBeVisible()
  expect(consoleErrors).toEqual([])
  expect(pageErrors).toEqual([])
})

test('counts the completed indicators up to their final values', async ({
  authenticatedPage,
  bff,
}) => {
  await mockCompletedTransport(bff, 'evolution')
  await authenticatedPage.setViewportSize({ width: 1440, height: 900 })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  const indicators = authenticatedPage.getByRole('list', {
    name: 'Indicadores da Habilidade',
  })
  await expect(indicators).toContainText('11 dias')
  await expect(indicators).toContainText('14')
  await expect(indicators).toContainText('22')
  await expect(
    authenticatedPage.getByRole('region', { name: 'Prática de revisão' }),
  ).toContainText('85')
})

test('shows the completed indicators at their final values on first render under reduced motion', async ({
  authenticatedPage,
  bff,
}) => {
  await mockCompletedTransport(bff, 'evolution')
  await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
  await authenticatedPage.emulateMedia({ reducedMotion: 'reduce' })

  await navigateAuthenticatedPage(authenticatedPage, skillPath)

  // The indicators render together with the heading, so a count-up that had
  // started would still read a lower figure here instead of the final one.
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Lógica de programação' }),
  ).toBeVisible()
  const duration = authenticatedPage
    .getByRole('list', { name: 'Indicadores da Habilidade' })
    .getByRole('listitem')
    .filter({ hasText: 'Do início à conclusão' })
  expect(await duration.textContent()).toBe('Do início à conclusão11 dias')
  const review = authenticatedPage.getByRole('region', { name: 'Prática de revisão' })
  expect(await review.textContent()).toContain('85última nota de revisão')
})
