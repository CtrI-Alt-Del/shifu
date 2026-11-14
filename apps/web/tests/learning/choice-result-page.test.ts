import type { Page } from '@playwright/test'
import { ROUTES } from '@/constants/routes'
import { GamificationTransportFixture } from '../fixtures/gamification-transport-fixture'
import {
  ChoiceActivityDetailFaker,
  ChoiceAttemptDetailFaker,
  ChoiceQuestionFaker,
  ChoiceResultQuestionFaker,
  LearningRouteIdsFaker,
} from '@/core/learning/fakers'
import { expect, navigateAuthenticatedPage, signInPassword, test } from '../playwright'

type EntranceFrame = Array<{ opacity: number; x: number; y: number }>
type EntranceWindow = Window & { __learningEntranceFrames?: Promise<EntranceFrame[]> }

async function sampleEntrance(page: Page, selector: string) {
  await page.evaluate((targetSelector) => {
    const state = window as EntranceWindow
    state.__learningEntranceFrames = new Promise<EntranceFrame[]>((resolve) => {
      const frames: EntranceFrame[] = []
      function sample() {
        const targets = [...document.querySelectorAll(targetSelector)]
        if (targets.length > 0) {
          frames.push(
            targets.map((target) => {
              const style = getComputedStyle(target)
              const matrix = new DOMMatrixReadOnly(
                style.transform === 'none' ? undefined : style.transform,
              )
              return { opacity: Number(style.opacity), x: matrix.m41, y: matrix.m42 }
            }),
          )
        }
        if (frames.length === 90) resolve(frames)
        else requestAnimationFrame(sample)
      }
      requestAnimationFrame(sample)
    })
  }, selector)
}

async function entranceFrames(page: Page) {
  return page.evaluate(() => (window as EntranceWindow).__learningEntranceFrames)
}

const ids = LearningRouteIdsFaker.fake()
const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`
const competencyPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}`
const attemptPath = `${activityPath}/attempts/${ids.attemptId}`
const activity = ChoiceActivityDetailFaker.fake({
  activityId: ids.activityId,
  title: 'Somar os números pares',
  latestAttemptId: ids.attemptId,
  questions: [
    ChoiceQuestionFaker.fake({
      key: 'q1',
      prompt: 'Qual é o resultado?',
      options: [
        { key: 'a', text: '4' },
        { key: 'b', text: '6' },
        { key: 'c', text: '8' },
      ],
    }),
  ],
})
const completedAttempt = ChoiceAttemptDetailFaker.fake({
  attemptId: ids.attemptId,
  activityId: ids.activityId,
  status: 'completed',
  submittedAt: '2026-09-23T12:00:00Z',
  score: 0,
  progressBefore: 9,
  progressAfter: 3,
  statusAfter: 'learning',
  questions: [
    ChoiceResultQuestionFaker.fake(
      {
        key: 'q1',
        prompt: 'Qual é o resultado?',
        submittedOptionKeys: ['b'],
        score: 0,
        isCorrect: false,
        explanation: 'A soma correta não foi selecionada.',
      },
      { revealCorrectOptionKeys: false },
    ),
  ],
  nextAction: {
    competencyId: ids.nextCompetencyId,
    activityId: ids.nextActivityId,
    difficulty: 'easy',
    type: 'reinforcement',
  },
})

function serverFnExport(url: string): string | null {
  const segment = new URL(url).pathname.split('/_serverFn/')[1]
  if (!segment) return null
  try {
    return JSON.parse(Buffer.from(segment, 'base64').toString('utf-8')).export
  } catch {
    return null
  }
}

const adaptiveDetail = {
  availability: 'available',
  goalId: ids.goalId,
  skillId: ids.skillId,
  skillName: 'Lógica',
  competencyId: ids.competencyId,
  competencyName: 'Repetição',
  progress: null,
  status: 'learning',
  isFocus: true,
  focusReturned: false,
  focusCompetencyId: ids.competencyId,
  focusCompetencyName: 'Repetição',
  items: [],
  recommendation: null,
  coverageComplete: false,
  verificationCause: null,
  adaptive: {
    targetConceptId: ids.targetConceptId,
    targetConceptName: 'Laços',
    originalTargetConceptId: ids.targetConceptId,
    originalTargetConceptName: 'Laços',
    recommendedCompetencyId: ids.nextCompetencyId,
    materialCompetencyId: ids.nextCompetencyId,
    reason: 'coverage',
    difficulty: 'easy',
    activityId: ids.nextActivityId,
    materialId: null,
    materialIsOptional: false,
    gap: null,
  },
}

test('renders actual result route from safe Activity and Attempt contracts, protects hidden labels, and opens the recommendation', async ({
  authenticatedPage,
  bff,
}) => {
  const calls: Array<{ url: string; body: string }> = []

  await bff.route(async (route) => {
    const url = route.request().url()
    const body = route.request().postData() ?? ''
    const payload = decodeURIComponent(`${url} ${body}`)
    calls.push({ url, body: payload })
    if (serverFnExport(url)?.startsWith('getCompetencyDetailAction_')) {
      await route.fulfill({
        body: JSON.stringify({ result: adaptiveDetail }),
        contentType: 'application/json',
      })
      return
    }
    if (payload.includes(ids.attemptId)) {
      await route.fulfill({
        body: JSON.stringify({ result: completedAttempt }),
        contentType: 'application/json',
      })
      return
    }
    if (payload.includes(ids.activityId) || payload.includes(ids.nextActivityId)) {
      const nextActivity = payload.includes(ids.nextActivityId)
        ? { ...activity, activityId: ids.nextActivityId, title: 'Reforço recomendado' }
        : activity
      await route.fulfill({
        body: JSON.stringify({ result: nextActivity }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })

  const entranceSelector = 'details[aria-labelledby="choice-result-question-1"]'
  await authenticatedPage.emulateMedia({ reducedMotion: 'no-preference' })
  await sampleEntrance(authenticatedPage, entranceSelector)
  await navigateAuthenticatedPage(authenticatedPage, attemptPath)

  const resultHeading = authenticatedPage.getByRole('heading', {
    name: 'Resultado da Atividade',
  })
  await expect(resultHeading).toBeVisible()
  const progressHeading = authenticatedPage.getByRole('heading', {
    name: 'Progresso demonstrado da Habilidade',
  })
  await expect(progressHeading).toBeVisible()
  await expect(
    authenticatedPage.locator('section').filter({ has: progressHeading }),
  ).toContainText(/Antes:\s*9%.*Agora:\s*3%/)
  await expect(
    authenticatedPage.getByText('A soma correta não foi selecionada.'),
  ).not.toBeVisible()
  await authenticatedPage
    .locator('summary')
    .filter({ hasText: 'Questão 1 · escolha única · incorreta' })
    .click()
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Qual é o resultado?' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('6', { exact: true })).toBeVisible()
  await expect(authenticatedPage.getByText('4', { exact: true })).not.toBeVisible()
  await expect(
    authenticatedPage.getByText('A soma correta não foi selecionada.'),
  ).toBeVisible()
  const resultCard = authenticatedPage.locator('.choice-result-card').first()
  await expect(resultCard).toHaveAttribute('open', '')
  await expect
    .poll(() =>
      resultCard.evaluate((card) => {
        const style = getComputedStyle(card, '::details-content')
        return {
          opacity: Number(style.opacity),
          offset: new DOMMatrixReadOnly(style.transform).m42,
        }
      }),
    )
    .toEqual({ opacity: 1, offset: 0 })
  expect(
    await resultCard.evaluate((card) =>
      getComputedStyle(card, '::details-content')
        .transitionDuration.split(',')
        .some((duration) => Number.parseFloat(duration) > 0),
    ),
  ).toBe(true)
  const normalFrames = await entranceFrames(authenticatedPage)
  expect(normalFrames).toHaveLength(90)
  expect(normalFrames?.some(([card]) => card.opacity > 0 && card.opacity < 1)).toBe(true)
  expect(normalFrames?.some(([card]) => card.x < 0)).toBe(true)
  expect(normalFrames?.at(-1)).toEqual([{ opacity: 1, x: 0, y: 0 }])

  await navigateAuthenticatedPage(authenticatedPage, ROUTES.privacy)
  await authenticatedPage.emulateMedia({ reducedMotion: 'reduce' })
  await sampleEntrance(authenticatedPage, entranceSelector)
  await navigateAuthenticatedPage(authenticatedPage, attemptPath)
  const reducedFrames = await entranceFrames(authenticatedPage)
  expect(reducedFrames).toHaveLength(90)
  expect(
    reducedFrames?.every(([card]) => card.opacity === 1 && card.x === 0 && card.y === 0),
  ).toBe(true)
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Resultado da Atividade' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('progressbar', {
      name: 'Progresso demonstrado da Habilidade após a avaliação',
    }),
  ).toHaveAttribute('aria-valuenow', '3')
  await resultCard.locator('summary').click()
  await expect(resultCard).toHaveAttribute('open', '')
  expect(
    await resultCard.evaluate(
      (card) => getComputedStyle(card, '::details-content').transitionDuration,
    ),
  ).toBe('0s')
  await resultCard.locator('summary').click()
  await expect(
    authenticatedPage.getByText('A soma correta não foi selecionada.'),
  ).not.toBeVisible()
  await resultCard.locator('summary').focus()
  await authenticatedPage.keyboard.press('Enter')
  await expect(resultCard).toHaveAttribute('open', '')
  await expect(
    authenticatedPage.getByText('A soma correta não foi selecionada.'),
  ).toBeVisible()
  expect(calls.some(({ body }) => body.includes(ids.activityId))).toBe(true)
  expect(calls.some(({ body }) => body.includes(ids.attemptId))).toBe(true)

  await expect(
    authenticatedPage.getByRole('button', { name: 'Voltar para Atividade' }),
  ).toHaveCount(0)
  const backToCompetency = authenticatedPage.getByRole('link', {
    name: 'Voltar para a Competência',
  })
  await expect(backToCompetency).toBeVisible()
  await expect(backToCompetency).toHaveAttribute('href', competencyPath)
  await authenticatedPage
    .getByRole('link', { name: /Abrir Atividade recomendada/ })
    .click()
  await expect(authenticatedPage).toHaveURL(
    new RegExp(`${ids.nextCompetencyId}/activities/${ids.nextActivityId}/?$`),
  )
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Reforço recomendado' }),
  ).toBeVisible()
})

test('renders mixed official details as independent keyboard-accessible disclosures', async ({
  authenticatedPage,
  bff,
}, testInfo) => {
  await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
  const mixedActivity = {
    ...activity,
    questions: [
      ...activity.questions,
      {
        key: 'code-1',
        kind: 'javascript_stdin',
        prompt: 'Leia um número e imprima o dobro.',
        initialFiles: [{ path: 'main.js', content: '', editable: true }],
        entrypoint: 'main.js',
        editablePaths: ['main.js'],
        fixedDependencies: [],
        permittedCommands: [],
        criteria: [{ key: 'correctness', name: 'Correção', weightPercentage: 100 }],
      },
    ],
  }
  const mixedAttempt = {
    ...completedAttempt,
    score: 37.5,
    questions: [
      completedAttempt.questions?.[0] ??
        ChoiceResultQuestionFaker.fake({
          key: 'q1',
          prompt: 'Qual é o resultado?',
          submittedOptionKeys: ['b'],
          score: 0,
          isCorrect: false,
          explanation: 'A soma correta não foi selecionada.',
        }),
      {
        key: 'code-1',
        kind: 'javascript_stdin',
        prompt: 'Leia um número e imprima o dobro.',
        score: 75,
        submittedFiles: [{ path: 'main.js', content: 'console.log(Number(input) * 2)' }],
        criterionResults: [
          {
            key: 'correctness',
            weightPercentage: 100,
            level: 75,
            commentId: 'correctness-75',
            comment: 'A solução trata a entrada corretamente.',
          },
        ],
        conceptObservations: [
          { conceptId: 'stdin', level: 75, observationId: 'stdin-observed' },
        ],
      },
    ],
  }

  await bff.route(async (route) => {
    const body = route.request().postData() ?? ''
    const payload = decodeURIComponent(`${route.request().url()} ${body}`)
    if (payload.includes(ids.attemptId)) {
      await route.fulfill({
        body: JSON.stringify({ result: mixedAttempt }),
        contentType: 'application/json',
      })
      return
    }
    if (payload.includes(ids.activityId)) {
      await route.fulfill({
        body: JSON.stringify({ result: mixedActivity }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, attemptPath)

  const choiceSummary = authenticatedPage.locator('summary').filter({
    hasText: 'Questão 1 · escolha única · incorreta',
  })
  const codeSummary = authenticatedPage.locator('summary').filter({
    hasText: 'Questão 2 · JavaScript · entrada padrão',
  })
  const choiceDisclosure = choiceSummary.locator('..')
  const codeDisclosure = codeSummary.locator('..')
  const resultContent = authenticatedPage
    .getByRole('main')
    .filter({ has: choiceSummary })
    .last()

  await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
  await expect(
    authenticatedPage.getByLabel('Nota da Atividade 37,5 de 100'),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('heading', {
      name: 'Progresso demonstrado da Habilidade',
    }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByLabel('Nota da Atividade 37,5 de 100'),
  ).toContainText('0 de 2 questões corretas')
  await expect(choiceDisclosure).not.toHaveAttribute('open', '')
  await expect(codeDisclosure).not.toHaveAttribute('open', '')
  await expect(
    authenticatedPage.getByText('console.log(Number(input) * 2)'),
  ).not.toBeVisible()
  await resultContent.screenshot({
    path: testInfo.outputPath('choice-result-default-desktop.png'),
  })

  await codeSummary.focus()
  await authenticatedPage.keyboard.press('Space')

  await expect(codeDisclosure).toHaveAttribute('open', '')

  await choiceSummary.click()

  await expect(choiceDisclosure).toHaveAttribute('open', '')
  await expect(codeDisclosure).toHaveAttribute('open', '')
  await expect(
    authenticatedPage.getByText('A solução trata a entrada corretamente.'),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText('Correção · peso 100% · nível 75'),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('stdin · nível 75')).toBeVisible()
  await expect(authenticatedPage.getByText('Somente leitura')).toBeVisible()
  await expect(authenticatedPage.getByText('Terminal')).toHaveCount(0)
  await resultContent.screenshot({
    path: testInfo.outputPath('choice-result-expanded-desktop.png'),
  })

  await codeSummary.focus()
  await authenticatedPage.keyboard.press('Enter')

  await expect(codeDisclosure).not.toHaveAttribute('open', '')
  await expect(choiceDisclosure).toHaveAttribute('open', '')
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))

  await authenticatedPage.setViewportSize({ width: 390, height: 844 })
  await expect(choiceDisclosure).toHaveAttribute('open', '')
  expect(
    await authenticatedPage.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390)
  const mobileSummaryBounds = await authenticatedPage
    .locator('.choice-result-card > summary')
    .evaluateAll((summaries) =>
      summaries.map((summary) => {
        const label = summary.children[0].getBoundingClientRect()
        const score = summary.querySelector('output')?.getBoundingClientRect()
        return score ? { labelBottom: label.bottom, scoreTop: score.top } : null
      }),
    )
  expect(mobileSummaryBounds.length).toBe(2)
  for (const bounds of mobileSummaryBounds) {
    if (bounds === null) throw new Error('A result summary score must be rendered')
    expect(bounds.labelBottom).toBeLessThanOrEqual(bounds.scoreTop)
  }
  await resultContent.screenshot({
    path: testInfo.outputPath('choice-result-expanded-mobile.png'),
  })
})

test.describe('Activity XP reward band integration', () => {
  const ids = LearningRouteIdsFaker.fake()
  const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`
  const attemptPath = `${activityPath}/attempts/${ids.attemptId}`
  const activity = ChoiceActivityDetailFaker.fake({
    activityId: ids.activityId,
    title: 'Somar os números pares',
    latestAttemptId: ids.attemptId,
    questions: [
      ChoiceQuestionFaker.fake({
        key: 'q1',
        prompt: 'Qual é o resultado?',
        options: [
          { key: 'a', text: '4' },
          { key: 'b', text: '6' },
        ],
      }),
    ],
  })
  const completed = ChoiceAttemptDetailFaker.fake({
    attemptId: ids.attemptId,
    activityId: ids.activityId,
    status: 'completed',
    score: 67,
    progressBefore: 50,
    progressAfter: 55,
    questions: [
      ChoiceResultQuestionFaker.fake({
        key: 'q1',
        prompt: 'Qual é o resultado?',
        submittedOptionKeys: ['b'],
        score: 100,
        isCorrect: true,
        explanation: 'A soma é 6.',
      }),
    ],
  })

  test('requests the reward endpoint for the attempt and renders a granted band beside the unchanged result', async ({
    authenticatedPage,
    bff,
  }) => {
    let rewardCalled = false

    await bff.route(async (route) => {
      const url = route.request().url()
      const body = route.request().postData() ?? ''
      const payload = decodeURIComponent(`${url} ${body}`)
      if (serverFnExport(url)?.startsWith('getActivityXpReward_')) {
        rewardCalled = true
        await route.fulfill({
          body: JSON.stringify({
            result: {
              kind: 'success',
              reward: {
                activityId: ids.activityId,
                attemptId: ids.attemptId,
                state: 'granted',
                additionalXp: 6,
                grantedXp: 6,
                maximumXp: 10,
              },
            },
          }),
          contentType: 'application/json',
        })
        return
      }
      if (payload.includes(ids.attemptId)) {
        await route.fulfill({
          body: JSON.stringify({ result: completed }),
          contentType: 'application/json',
        })
        return
      }
      if (payload.includes(ids.activityId)) {
        await route.fulfill({
          body: JSON.stringify({ result: activity }),
          contentType: 'application/json',
        })
        return
      }
      await route.fallback()
    })

    await navigateAuthenticatedPage(authenticatedPage, attemptPath)

    await expect(
      authenticatedPage.getByRole('heading', { name: 'Resultado da Atividade' }),
    ).toBeVisible()
    await expect(authenticatedPage.getByText('+6 XP')).toBeVisible()
    await expect(
      authenticatedPage.getByLabel('Nota da Atividade 67 de 100'),
    ).toBeVisible()
    await expect.poll(() => rewardCalled).toBe(true)
  })

  test('shows a pending reward statement while Gamification has not confirmed it, without altering the Learning result', async ({
    authenticatedPage,
    bff,
  }) => {
    await bff.route(async (route) => {
      const url = route.request().url()
      const body = route.request().postData() ?? ''
      const payload = decodeURIComponent(`${url} ${body}`)
      if (serverFnExport(url)?.startsWith('getActivityXpReward_')) {
        await route.fulfill({
          body: JSON.stringify({
            result: {
              kind: 'success',
              reward: {
                activityId: ids.activityId,
                attemptId: ids.attemptId,
                state: 'pending',
                additionalXp: 0,
                grantedXp: 0,
                maximumXp: null,
              },
            },
          }),
          contentType: 'application/json',
        })
        return
      }
      if (payload.includes(ids.attemptId)) {
        await route.fulfill({
          body: JSON.stringify({ result: completed }),
          contentType: 'application/json',
        })
        return
      }
      if (payload.includes(ids.activityId)) {
        await route.fulfill({
          body: JSON.stringify({ result: activity }),
          contentType: 'application/json',
        })
        return
      }
      await route.fallback()
    })

    await navigateAuthenticatedPage(authenticatedPage, attemptPath)

    await expect(
      authenticatedPage.getByRole('heading', { name: 'Resultado da Atividade' }),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByText('Confirmando o XP desta Atividade'),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByLabel('Nota da Atividade 67 de 100'),
    ).toBeVisible()
  })
})

test.describe('ChoiceResultPage route coverage', () => {
  const ids = LearningRouteIdsFaker.fake()
  const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`
  const attemptPath = `${activityPath}/attempts/${ids.attemptId}`
  const activity = ChoiceActivityDetailFaker.fake({
    activityId: ids.activityId,
    title: 'Somar os números pares',
    latestAttemptId: ids.attemptId,
    unresolvedAttemptId: ids.attemptId,
    questions: [
      ChoiceQuestionFaker.fake({
        key: 'q1',
        prompt: 'Qual é o resultado?',
        options: [
          { key: 'a', text: '4' },
          { key: 'b', text: '6' },
        ],
      }),
    ],
  })
  const pending = ChoiceAttemptDetailFaker.fake({
    attemptId: ids.attemptId,
    activityId: ids.activityId,
  })
  const completed = ChoiceAttemptDetailFaker.fake({
    attemptId: ids.attemptId,
    activityId: ids.activityId,
    status: 'completed',
    score: 100,
    progressBefore: 50,
    progressAfter: 55,
    questions: [
      ChoiceResultQuestionFaker.fake({
        key: 'q1',
        prompt: 'Qual é o resultado?',
        submittedOptionKeys: ['a'],
        score: 100,
        isCorrect: true,
        explanation: 'A soma é 4.',
      }),
    ],
  })

  test.describe('Attempt index route', () => {
    test('loads Activity and Attempt, announces pending, and refreshes immediately when visible', async ({
      authenticatedPage,
      bff,
    }) => {
      let attemptReads = 0
      const requestUrls: string[] = []

      await bff.route(async (route) => {
        const body = route.request().postData() ?? ''
        const payload = decodeURIComponent(`${route.request().url()} ${body}`)
        requestUrls.push(route.request().url())
        if (payload.includes(ids.attemptId)) {
          attemptReads += 1
          await route.fulfill({
            body: JSON.stringify({ result: pending }),
            contentType: 'application/json',
          })
          return
        }
        if (payload.includes(ids.activityId)) {
          await route.fulfill({
            body: JSON.stringify({ result: activity }),
            contentType: 'application/json',
          })
          return
        }
        await route.fallback()
      })

      await navigateAuthenticatedPage(authenticatedPage, attemptPath)

      await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
      await expect(
        authenticatedPage.getByRole('heading', { name: 'Avaliação em andamento' }),
      ).toBeVisible()
      const pendingStatus = authenticatedPage
        .getByRole('status')
        .filter({ hasText: 'Estamos avaliando suas respostas.' })
      await expect(pendingStatus).toHaveAttribute('aria-busy', 'true')
      const indicator = pendingStatus.locator('[aria-hidden="true"] span')
      await expect(indicator).toHaveCount(1)
      await expect(indicator).toHaveCSS('animation-name', 'choice-result-pending-sweep')

      await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
      await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
      await expect(
        authenticatedPage.getByRole('heading', { name: 'Avaliação em andamento' }),
      ).toBeVisible()
      await authenticatedPage.setViewportSize({ width: 390, height: 844 })
      await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
      await expect(
        authenticatedPage.getByRole('heading', { name: 'Avaliação em andamento' }),
      ).toBeVisible()
      await authenticatedPage.emulateMedia({ reducedMotion: 'reduce' })
      await expect(indicator).toHaveCSS('animation-name', 'none')

      await authenticatedPage.evaluate(() =>
        document.dispatchEvent(new Event('visibilitychange')),
      )
      await expect.poll(() => attemptReads).toBeGreaterThan(1)
      expect(requestUrls.length).toBeGreaterThanOrEqual(2)
    })

    test('retries a failed evaluation on the same attempt and renders the completed result', async ({
      authenticatedPage,
      bff,
    }) => {
      let attemptUrl = ''
      let retryUrl = ''
      let attemptReads = 0

      await bff.route(async (route) => {
        const requestUrl = route.request().url()
        const body = route.request().postData() ?? ''
        const payload = decodeURIComponent(`${requestUrl} ${body}`)
        if (payload.includes(ids.attemptId)) {
          if (!attemptUrl) attemptUrl = requestUrl
          if (requestUrl !== attemptUrl) {
            retryUrl = requestUrl
            await route.fulfill({
              body: JSON.stringify({ result: { ok: true } }),
              contentType: 'application/json',
            })
            return
          }
          attemptReads += 1
          await route.fulfill({
            body: JSON.stringify({
              result:
                attemptReads === 1
                  ? {
                      ...pending,
                      status: 'failed',
                      retryAllowed: true,
                      failureMessage: 'A avaliação foi interrompida.',
                    }
                  : completed,
            }),
            contentType: 'application/json',
          })
          return
        }
        if (payload.includes(ids.activityId)) {
          await route.fulfill({
            body: JSON.stringify({ result: activity }),
            contentType: 'application/json',
          })
          return
        }
        await route.fallback()
      })

      await navigateAuthenticatedPage(authenticatedPage, attemptPath)

      await expect(
        authenticatedPage.getByRole('heading', {
          name: 'A avaliação não pôde ser concluída',
        }),
      ).toBeVisible()
      await authenticatedPage.getByRole('button', { name: 'Tentar novamente' }).click()

      await expect(
        authenticatedPage.getByRole('heading', { name: 'Resultado da Atividade' }),
      ).toBeVisible()
      await authenticatedPage.getByText(/Questão 1 · escolha única/).click()

      await expect(authenticatedPage.getByText('A soma é 4.')).toBeVisible()
      expect(retryUrl).not.toBe('')
      expect(attemptReads).toBeGreaterThanOrEqual(2)
    })

    test('renders all completed details without a repeat shortcut', async ({
      authenticatedPage,
      bff,
    }) => {
      await bff.route(async (route) => {
        const body = route.request().postData() ?? ''
        const payload = decodeURIComponent(`${route.request().url()} ${body}`)
        if (payload.includes(ids.attemptId)) {
          await route.fulfill({
            body: JSON.stringify({ result: completed }),
            contentType: 'application/json',
          })
          return
        }
        if (payload.includes(ids.activityId)) {
          await route.fulfill({
            body: JSON.stringify({ result: activity }),
            contentType: 'application/json',
          })
          return
        }
        await route.fallback()
      })

      await navigateAuthenticatedPage(authenticatedPage, attemptPath)

      await expect(
        authenticatedPage.getByRole('heading', { name: 'Resultado da Atividade' }),
      ).toBeVisible()
      await expect(
        authenticatedPage.getByLabel('Nota da Atividade 100 de 100'),
      ).toBeVisible()
      await authenticatedPage.getByText(/Questão 1 · escolha única/).click()

      await expect(authenticatedPage.getByText('A soma é 4.')).toBeVisible()
      await expect(
        authenticatedPage.getByRole('button', { name: 'Voltar para Atividade' }),
      ).toHaveCount(0)
      await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
    })
  })
})

test('renders the HTML/CSS/JavaScript attempt as historical read-only content', async ({
  authenticatedPage,
  bff,
}) => {
  const htmlQuestion = {
    key: 'html-1',
    kind: 'html_css_js',
    prompt: 'Crie uma página semântica.',
    initialFiles: [{ path: 'index.html', content: '<main></main>', editable: true }],
    entrypoint: 'index.html',
    editablePaths: ['index.html'],
    fixedDependencies: [{ name: 'vite', version: '7.0.0' }],
    permittedCommands: [{ id: 'dev', executable: 'npm', arguments: ['run', 'dev'] }],
    criteria: [{ key: 'semantic', name: 'HTML semântico', weightPercentage: 100 }],
  }
  const htmlActivity = { ...activity, questions: [htmlQuestion] }
  const htmlAttempt = {
    ...completedAttempt,
    questions: [
      {
        key: 'html-1',
        kind: 'html_css_js',
        prompt: htmlQuestion.prompt,
        score: 85,
        submittedFiles: [{ path: 'index.html', content: '<main>página final</main>' }],
        criterionResults: [
          {
            key: 'semantic',
            weightPercentage: 100,
            level: 85,
            commentId: 'semantic-good',
            comment: 'A estrutura usa os elementos esperados.',
          },
        ],
        conceptObservations: [],
      },
    ],
  }

  await bff.route(async (route) => {
    const payload = decodeURIComponent(
      `${route.request().url()} ${route.request().postData() ?? ''}`,
    )
    if (payload.includes(ids.attemptId)) {
      await route.fulfill({
        body: JSON.stringify({ result: htmlAttempt }),
        contentType: 'application/json',
      })
      return
    }
    if (payload.includes(ids.activityId)) {
      await route.fulfill({
        body: JSON.stringify({ result: htmlActivity }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, attemptPath)
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
  const htmlDisclosure = authenticatedPage.locator('summary').filter({
    hasText: 'Questão 1 · HTML, CSS e JavaScript',
  })
  await expect(htmlDisclosure).toBeVisible()
  await htmlDisclosure.click()
  await expect(authenticatedPage.getByText('página final')).toBeVisible()
  await expect(authenticatedPage.getByText('Somente leitura')).toBeVisible()
  await expect(
    authenticatedPage.getByText('HTML semântico · peso 100% · nível 85'),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText('A estrutura usa os elementos esperados.'),
  ).toBeVisible()
  await expect(authenticatedPage.getByTitle('Prévia isolada da página')).toHaveCount(0)
  await expect(
    authenticatedPage.getByRole('button', { name: /Executar|Avaliar/ }),
  ).toHaveCount(0)
})

test('shows immutable integrated files in the routed historical result on mobile', async ({
  authenticatedPage,
  bff,
}) => {
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })
  const integratedAttempt = {
    ...completedAttempt,
    score: 100,
    questions: [
      {
        key: 'integrated',
        kind: 'react_fastify',
        prompt: 'Resposta integrada preservada',
        score: 100,
        submittedFiles: [
          { path: 'src/App.tsx', content: 'frontend histórico' },
          { path: 'server.js', content: 'API histórica' },
          { path: 'routes/tasks.js', content: 'rota adicional histórica' },
        ],
        criterionResults: [
          {
            key: 'integration',
            weightPercentage: 100,
            level: 100,
            commentId: 'correct',
            comment: 'Integração correta',
          },
        ],
        conceptObservations: [],
      },
    ],
  }
  await bff.route(async (route) => {
    const url = route.request().url()
    const payload = decodeURIComponent(`${url} ${route.request().postData() ?? ''}`)
    if (serverFnExport(url)?.startsWith('getCompetencyDetailAction_')) {
      await route.fulfill({
        body: JSON.stringify({ result: adaptiveDetail }),
        contentType: 'application/json',
      })
      return
    }
    if (payload.includes(ids.attemptId)) {
      await route.fulfill({
        body: JSON.stringify({ result: integratedAttempt }),
        contentType: 'application/json',
      })
      return
    }
    if (payload.includes(ids.activityId)) {
      await route.fulfill({
        body: JSON.stringify({ result: activity }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })
  await navigateAuthenticatedPage(authenticatedPage, attemptPath)
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Resultado da Atividade' }),
  ).toBeVisible()
  await authenticatedPage
    .locator('summary')
    .filter({ hasText: 'React + Fastify' })
    .click()
  await expect(
    authenticatedPage.getByText('frontend histórico', { exact: true }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText('API histórica', { exact: true }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText('rota adicional histórica', { exact: true }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText('Somente leitura', { exact: true }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Avaliar questão' }),
  ).toHaveCount(0)
  await expect(authenticatedPage.locator('iframe')).toHaveCount(0)
  expect(
    await authenticatedPage.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true)
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
})

// The reward service is exercised through its actual result-route consumer.
// The opt-in upstream controls JSON responses; Identity/Better Auth remain real.
test.describe('Activity XP reward routed REST transport', () => {
  for (const fails of [false, true]) {
    test(`reward ${fails ? 'preserves the saved result after an HTTP failure' : 'maps authenticated HTTP data'}`, async ({
      page,
      request,
      activeAccount,
    }) => {
      const transport = GamificationTransportFixture(request, activeAccount.accountId)
      const rewardPath = `/gamification/activities/${ids.activityId}/attempts/${ids.attemptId}/xp-reward`
      await transport.register({
        [activityPath]: {
          body: {
            activity_id: ids.activityId,
            competency_id: ids.competencyId,
            title: 'Somar os números pares',
            type: 'practice',
            difficulty: 'easy',
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
            latest_attempt_id: ids.attemptId,
            can_submit: false,
            activity_revision: 'reward-transport',
          },
        },
        [attemptPath]: {
          body: {
            attempt_id: ids.attemptId,
            activity_id: ids.activityId,
            status: 'completed',
            submitted_at: '2026-09-23T12:00:00Z',
            retry_allowed: false,
            score: 100,
            progress_before: 0,
            progress_after: 100,
            status_before: 'learning',
            status_after: 'mastered',
            questions: [],
            next_action: null,
          },
        },
        [competencyPath]: {
          status: 404,
          body: { code: 'not_found', message: 'Recurso não encontrado.' },
        },
        [rewardPath]: fails
          ? {
              status: 503,
              body: {
                code: 'service_unavailable',
                message: 'Serviço temporariamente indisponível.',
              },
            }
          : {
              body: {
                activityId: ids.activityId,
                attemptId: ids.attemptId,
                state: 'granted',
                additionalXp: 6,
                grantedXp: 6,
                maximumXp: 20,
              },
            },
      })
      try {
        const signIn = await page.request.post('/api/auth/sign-in/identity', {
          data: { email: activeAccount.email, password: signInPassword },
          headers: { 'x-forwarded-for': activeAccount.ipAddress },
        })
        expect(signIn.status()).toBe(200)
        await page.goto(attemptPath)
        await expect(page).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
        const band = page.getByRole('region', {
          name: 'Recompensa de XP desta Atividade',
        })
        if (fails)
          await expect(band).toContainText(
            'Não foi possível confirmar o XP agora. Seu resultado continua salvo.',
          )
        else {
          await expect(band).toContainText('+6 XP')
          await expect(band).toContainText('6 de 20 XP confirmados nesta Atividade.')
        }
        await expect
          .poll(
            async () =>
              (await transport.observations()).filter(
                (entry) => entry.path === rewardPath,
              ).length,
          )
          .toBeGreaterThan(0)
        expect(
          (await transport.observations()).filter((entry) => entry.path === rewardPath),
        ).toEqual(
          expect.arrayContaining([
            {
              method: 'GET',
              path: rewardPath,
              authorization: true,
              cookie: false,
              bffMark: true,
              accountId: activeAccount.accountId,
              status: fails ? 503 : 200,
            },
          ]),
        )
      } finally {
        await transport.dispose()
      }
    })
  }
})
