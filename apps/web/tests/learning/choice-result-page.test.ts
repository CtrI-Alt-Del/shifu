import { expect, navigateAuthenticatedPage, test } from '../playwright'

const ids = {
  goalId: '01SHF000000000000000000003',
  skillId: '01SHF000000000000000000004',
  competencyId: '01SHF000000000000000000001',
  activityId: '01SHF000000000000000000005',
  attemptId: '01SHF000000000000000000009',
  nextCompetencyId: '01SHF000000000000000000002',
  nextActivityId: '01SHF000000000000000000010',
}
const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`
const attemptPath = `${activityPath}/attempts/${ids.attemptId}`
const activity = {
  activityId: ids.activityId,
  title: 'Somar os números pares',
  difficulty: 'medium',
  canSubmit: true,
  latestAttemptId: ids.attemptId,
  unresolvedAttemptId: null,
  questions: [
    {
      key: 'q1',
      kind: 'single_choice',
      prompt: 'Qual é o resultado?',
      options: [
        { key: 'a', text: '4' },
        { key: 'b', text: '6' },
        { key: 'c', text: '8' },
      ],
    },
  ],
}
const completedAttempt = {
  attemptId: ids.attemptId,
  activityId: ids.activityId,
  status: 'completed',
  submittedAt: '2026-09-23T12:00:00Z',
  retryAllowed: false,
  score: 0,
  progressBefore: 9,
  progressAfter: 3,
  statusAfter: 'learning',
  questions: [
    {
      key: 'q1',
      prompt: 'Qual é o resultado?',
      submittedOptionKeys: ['b'],
      score: 0,
      isCorrect: false,
      explanation: 'A soma correta não foi selecionada.',
    },
  ],
  nextAction: {
    competencyId: ids.nextCompetencyId,
    activityId: ids.nextActivityId,
    difficulty: 'easy',
    type: 'reinforcement',
  },
}

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
    targetConceptId: '01SHF000000000000000000011',
    targetConceptName: 'Laços',
    originalTargetConceptId: '01SHF000000000000000000011',
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
}) => {
  const calls: Array<{ url: string; body: string }> = []
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
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

  await navigateAuthenticatedPage(authenticatedPage, attemptPath)
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Resultado da Atividade' }),
  ).toBeVisible()
  const progressHeading = authenticatedPage.getByRole('heading', {
    name: 'Progresso da Competência',
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
  expect(await resultCard.evaluate((card) => getComputedStyle(card).animationName)).toBe(
    'choice-result-reveal',
  )
  await authenticatedPage.emulateMedia({ reducedMotion: 'reduce' })
  expect(await resultCard.evaluate((card) => getComputedStyle(card).animationName)).toBe(
    'none',
  )
  expect(calls.some(({ body }) => body.includes(ids.activityId))).toBe(true)
  expect(calls.some(({ body }) => body.includes(ids.attemptId))).toBe(true)

  await expect(
    authenticatedPage.getByRole('button', { name: 'Voltar para Atividade' }),
  ).toHaveCount(0)
  const backToSkill = authenticatedPage.getByRole('link', {
    name: 'Voltar para a Habilidade',
  })
  await expect(backToSkill).toBeVisible()
  await expect(backToSkill).toHaveAttribute(
    'href',
    `/learning/goals/${ids.goalId}/skills/${ids.skillId}`,
  )
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
}) => {
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
      completedAttempt.questions[0],
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

  await authenticatedPage.route('**/_serverFn/**', async (route) => {
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

  await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
  await expect(
    authenticatedPage.getByLabel('Nota da Atividade 37,5 de 100'),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('heading', {
      name: 'Progresso da Competência',
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
  await authenticatedPage.getByRole('main').nth(2).screenshot({
    path: '/tmp/shifu-choice-result-default-desktop.png',
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
  await authenticatedPage.getByRole('main').nth(2).screenshot({
    path: '/tmp/shifu-choice-result-expanded-desktop.png',
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
  await authenticatedPage
    .locator('main > main')
    .screenshot({ path: '/tmp/shifu-choice-result-expanded-mobile-current.png' })
})
