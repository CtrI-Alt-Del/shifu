import {
  ChoiceActivityDetailFaker,
  ChoiceQuestionFaker,
  LearningRouteIdsFaker,
} from '@/core/learning/fakers'
import { expect, navigateAuthenticatedPage, test } from '../playwright'

const ids = LearningRouteIdsFaker.fake()
const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`
const competencyPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}`
const activity = ChoiceActivityDetailFaker.fake({
  activityId: ids.activityId,
  title: 'Somar os números pares',
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

test('runs the actual Activity route, preserves the answer, and blocks unsent in-app navigation', async ({
  authenticatedPage,
  bff,
}) => {
  const calls: Array<{ url: string; body: string }> = []

  await bff.route(async (route) => {
    const url = route.request().url()
    const body = route.request().postData() ?? ''
    const payload = decodeURIComponent(`${url} ${body}`)
    calls.push({ url, body: payload })
    if (payload.includes(ids.activityId)) {
      await route.fulfill({
        body: JSON.stringify({ result: activity }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, activityPath)
  const firstOption = authenticatedPage.getByRole('radio', { name: '4' })
  await firstOption.focus()
  await authenticatedPage.keyboard.press('Shift+Tab')
  await authenticatedPage.keyboard.press('Tab')

  await expect(firstOption).toBeFocused()
  expect(await firstOption.evaluate((input) => input.matches(':focus-visible'))).toBe(
    true,
  )
  expect(
    await firstOption.evaluate((input) => {
      const label = input.closest('label')
      if (!label) return null
      const style = getComputedStyle(label)
      return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth }
    }),
  ).toEqual({ outlineStyle: 'solid', outlineWidth: '2px' })
  await authenticatedPage.keyboard.press('Space')

  await expect(firstOption).toBeChecked()

  const dialogMessage = new Promise<string>((resolve) => {
    authenticatedPage.once('dialog', async (dialog) => {
      resolve(dialog.message())
      await dialog.accept()
    })
  })
  await authenticatedPage.evaluate((to) => {
    const router = (
      window as Window & {
        __TSR_ROUTER__: { navigate: (options: { to: string }) => Promise<void> }
      }
    ).__TSR_ROUTER__
    return router.navigate({ to })
  }, competencyPath)
  expect(await dialogMessage).toContain('respostas não foram enviadas')
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.competencyId}/?$`))
  expect(
    calls.some(
      ({ body }) =>
        body.includes(ids.goalId) &&
        body.includes(ids.skillId) &&
        body.includes(ids.competencyId) &&
        body.includes(ids.activityId),
    ),
  ).toBe(true)
})

test('shows Markdown code and accepts a complete multiple-selection answer', async ({
  authenticatedPage,
  bff,
}) => {
  const multipleActivity = {
    ...activity,
    questions: [
      {
        key: 'q1',
        kind: 'multiple_selection',
        prompt:
          'Considere o código:\n\n```python\ntem_cracha = True\ntem_senha = False\npode_entrar = tem_cracha and tem_senha\n```\n\nQuais afirmações são verdadeiras?',
        options: [
          { key: 'a', text: 'tem_cracha é True.' },
          { key: 'b', text: 'tem_senha é True.' },
          { key: 'c', text: 'pode_entrar é False.' },
          { key: 'd', text: 'pode_entrar é True.' },
        ],
      },
    ],
  }

  await bff.route(async (route) => {
    const payload = decodeURIComponent(route.request().url())
    if (payload.includes(ids.activityId)) {
      await route.fulfill({
        body: JSON.stringify({ result: multipleActivity }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, activityPath)

  await expect(authenticatedPage.locator('pre code')).toHaveText(
    /pode_entrar = tem_cracha and tem_senha/,
  )
  const prompt = authenticatedPage.locator('.choice-question-prompt')
  expect(await prompt.evaluate((node) => getComputedStyle(node).animationName)).toBe(
    'choice-prompt-enter',
  )
  await authenticatedPage.getByText('tem_cracha é True.').click()
  await authenticatedPage.getByText('pode_entrar é False.').click()

  await expect(
    authenticatedPage.getByRole('checkbox', { name: 'tem_cracha é True.' }),
  ).toBeChecked()
  await expect(
    authenticatedPage.getByRole('checkbox', { name: 'pode_entrar é False.' }),
  ).toBeChecked()
  await expect(
    authenticatedPage.getByRole('checkbox', { name: 'tem_senha é True.' }),
  ).not.toBeChecked()
  const optionCards = authenticatedPage.locator('.choice-question-option')
  expect(
    await optionCards.evaluateAll((cards) =>
      cards.map((card) => ({
        name: getComputedStyle(card).animationName,
        delay: getComputedStyle(card).animationDelay,
      })),
    ),
  ).toEqual([
    { name: 'choice-option-enter', delay: '0.08s' },
    { name: 'choice-option-enter', delay: '0.14s' },
    { name: 'choice-option-enter', delay: '0.2s' },
    { name: 'choice-option-enter', delay: '0.26s' },
  ])
  await authenticatedPage.emulateMedia({ reducedMotion: 'reduce' })
  expect(await prompt.evaluate((node) => getComputedStyle(node).animationName)).toBe(
    'none',
  )
  expect(
    await optionCards.evaluateAll((cards) =>
      cards.map((card) => getComputedStyle(card).animationName),
    ),
  ).toEqual(['none', 'none', 'none', 'none'])
  await expect(
    authenticatedPage.getByRole('checkbox', { name: 'tem_cracha é True.' }),
  ).toBeChecked()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Enviar respostas' }),
  ).toBeEnabled()
})

// Route-level cases for the owning page stay with its browser integration suite.
test.describe('ActivityPage route coverage', () => {
  const ids = LearningRouteIdsFaker.fake()
  const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`

  const activityResponse = ChoiceActivityDetailFaker.fake({
    activityId: ids.activityId,
    title: 'Somar os números pares',
    questions: [
      ChoiceQuestionFaker.fake({
        key: 'question-1',
        prompt: 'Qual é o resultado?',
        options: [
          { key: 'a', text: '4' },
          { key: 'b', text: '6' },
        ],
      }),
    ],
  })

  test.describe('Activity route parent', () => {
    test('redirects anonymous visitors before rendering a nested child', async ({
      page,
    }) => {
      await page.goto(`${activityPath}/attempts/${ids.attemptId}`)

      await expect(page).toHaveURL(/\/login\/?$/)
      await expect(
        page.getByRole('heading', { name: 'Somar os números pares' }),
      ).not.toBeVisible()
    })

    test('authenticates once and renders the selected nested Activity through Outlet', async ({
      authenticatedPage,
      bff,
    }) => {
      await bff.route(async (route) => {
        const body = route.request().postData() ?? ''
        const payload = decodeURIComponent(`${route.request().url()} ${body}`)
        if (payload.includes(ids.activityId)) {
          await route.fulfill({
            body: JSON.stringify({ result: activityResponse }),
            contentType: 'application/json',
          })
          return
        }
        await route.fallback()
      })

      await navigateAuthenticatedPage(authenticatedPage, activityPath)

      await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.activityId}/?$`))
      await expect(
        authenticatedPage.getByRole('heading', { name: activityResponse.title }),
      ).toBeVisible()
      await expect(
        authenticatedPage.getByRole('heading', {
          name: activityResponse.questions[0].prompt,
        }),
      ).toBeVisible()
    })
  })
})

// Route-level cases for the owning page stay with its browser integration suite.
test.describe('ActivityPage route coverage', () => {
  const ids = LearningRouteIdsFaker.fake()
  const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`
  const activityResponse = ChoiceActivityDetailFaker.fake({
    activityId: ids.activityId,
    title: 'Somar os números pares',
    questions: [
      ChoiceQuestionFaker.fake({
        key: 'q1',
        prompt: 'Qual é o primeiro resultado?',
        options: [
          { key: 'a', text: '4' },
          { key: 'b', text: '6' },
        ],
      }),
      ChoiceQuestionFaker.fake({
        key: 'q2',
        kind: 'multiple_selection',
        prompt: 'Selecione os pares',
        options: [
          { key: 'c', text: '2' },
          { key: 'd', text: '3' },
        ],
      }),
    ],
  })

  test.describe('Activity index route', () => {
    test('shows a recoverable load error and retries the same Activity IDs', async ({
      authenticatedPage,
      bff,
    }) => {
      let activityCalls = 0
      const requests: string[] = []

      await bff.route(async (route) => {
        const body = route.request().postData() ?? ''
        const payload = decodeURIComponent(`${route.request().url()} ${body}`)
        if (!payload.includes(ids.activityId)) return route.fallback()
        requests.push(payload)
        activityCalls += 1
        if (activityCalls === 1) {
          await route.fulfill({
            status: 503,
            body: JSON.stringify({ result: { kind: 'unavailable' } }),
          })
          return
        }
        await route.fulfill({
          body: JSON.stringify({ result: activityResponse }),
          contentType: 'application/json',
        })
      })

      await navigateAuthenticatedPage(authenticatedPage, activityPath)

      await expect(
        authenticatedPage.getByRole('heading', {
          name: 'Não foi possível carregar esta Atividade',
        }),
      ).toBeVisible()
      await authenticatedPage.getByRole('button', { name: 'Tentar novamente' }).click()

      await expect(
        authenticatedPage.getByRole('heading', { name: activityResponse.title }),
      ).toBeVisible()
      await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.activityId}/?$`))
      expect(activityCalls).toBe(2)
      expect(
        requests.every(
          (body) =>
            body.includes(ids.goalId) &&
            body.includes(ids.skillId) &&
            body.includes(ids.competencyId),
        ),
      ).toBe(true)
    })

    test('submits ordered answers and navigates to the saved attempt URL', async ({
      authenticatedPage,
      bff,
    }) => {
      const requests: string[] = []

      await bff.route(async (route) => {
        const body = route.request().postData() ?? ''
        const payload = decodeURIComponent(`${route.request().url()} ${body}`)
        if (!payload.includes(ids.activityId)) return route.fallback()
        requests.push(payload)
        if (payload.includes('submissionKey') || payload.includes('submission_key')) {
          await route.fulfill({
            body: JSON.stringify({
              result: {
                attemptId: ids.attemptId,
                status: 'pending',
                resultUrl: `${activityPath}/attempts/${ids.attemptId}`,
              },
            }),
            contentType: 'application/json',
          })
          return
        }
        if (payload.includes('questionKey') || payload.includes('question_key')) {
          await route.fulfill({
            body: JSON.stringify({
              result: { status: 'conclusive', score: 100, explanation: 'Correto.' },
            }),
            contentType: 'application/json',
          })
          return
        }
        await route.fulfill({
          body: JSON.stringify({ result: activityResponse }),
          contentType: 'application/json',
        })
      })

      await navigateAuthenticatedPage(authenticatedPage, activityPath)
      await authenticatedPage.getByText('4', { exact: true }).click()
      await authenticatedPage.getByRole('button', { name: 'Próxima questão' }).click()
      await authenticatedPage.getByText('2', { exact: true }).click()
      await authenticatedPage.getByText('3', { exact: true }).click()
      await authenticatedPage.getByRole('button', { name: 'Enviar respostas' }).click()

      await expect(authenticatedPage).toHaveURL(
        new RegExp(`${ids.activityId}/attempts/${ids.attemptId}$`),
      )
      const submission =
        requests.find(
          (body) => body.includes('submissionKey') || body.includes('submission_key'),
        ) ?? ''
      expect(submission).toContain(ids.goalId)
      expect(submission).toContain('q1')
      expect(submission).toContain('q2')
      expect(submission).toContain('a')
      expect(submission).toContain('c')
      expect(submission).toContain('d')
    })

    test('returns an owner with an unresolved saved attempt to its result route', async ({
      authenticatedPage,
      bff,
    }) => {
      const savedActivity = { ...activityResponse, unresolvedAttemptId: ids.attemptId }

      await bff.route(async (route) => {
        const payload = decodeURIComponent(
          `${route.request().url()} ${route.request().postData() ?? ''}`,
        )
        if (payload.includes(ids.attemptId)) {
          await route.fulfill({
            body: JSON.stringify({
              result: {
                attemptId: ids.attemptId,
                activityId: ids.activityId,
                status: 'pending',
                submittedAt: '2026-09-23T12:00:00Z',
                retryAllowed: false,
              },
            }),
            contentType: 'application/json',
          })
          return
        }
        if (payload.includes(ids.activityId)) {
          await route.fulfill({
            body: JSON.stringify({ result: savedActivity }),
            contentType: 'application/json',
          })
          return
        }
        await route.fallback()
      })

      await navigateAuthenticatedPage(authenticatedPage, activityPath)

      await expect(authenticatedPage).toHaveURL(
        new RegExp(`${ids.activityId}/attempts/${ids.attemptId}/?$`),
      )
      await expect(
        authenticatedPage.getByRole('heading', { name: 'Avaliação em andamento' }),
      ).toBeVisible()
    })

    test('previews a code question and submits its frozen editable file with the Activity revision', async ({
      authenticatedPage,
      bff,
    }, testInfo) => {
      await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
      const sourceCode = [
        'const users = [',
        '  { name: "Alice", age: 25 },',
        '  { name: "Bob", age: 17 },',
        '  { name: "Charlie", age: 30 },',
        '];',
        '',
        'function getAdults(users) {',
        '  return users.filter((user) => user.age >= 18);',
        '}',
        '',
        'const adults = getAdults(users);',
        'adults.forEach((user) => {',
        // biome-ignore lint/suspicious/noTemplateCurlyInString: These placeholders are JavaScript source in the editor fixture.
        '  console.log(`${user.name} is ${user.age} years old.`);',
        '});',
        "console.log('READY')",
        "process.stdin.once('data', (chunk) => { console.log('ECHO:' + chunk.toString().trim()); process.exit(0) })",
      ].join('\n')
      const mixedActivity = {
        ...activityResponse,
        activityRevision: 'revision-mixed-1',
        questions: [
          ...activityResponse.questions,
          {
            key: 'code-1',
            kind: 'javascript_stdin',
            prompt: 'Leia um número e imprima seu dobro.',
            initialFiles: [{ path: 'index.js', content: '', editable: true }],
            entrypoint: 'index.js',
            editablePaths: ['index.js'],
            fixedDependencies: [],
            permittedCommands: [
              { id: 'run-main', executable: 'node', arguments: ['index.js'] },
            ],
            criteria: [{ key: 'correct', name: 'Correção', weightPercentage: 100 }],
          },
        ],
      }
      const requests: string[] = []

      await bff.route(async (route) => {
        const payload = decodeURIComponent(
          `${route.request().url()} ${route.request().postData() ?? ''}`,
        )
        if (!payload.includes(ids.activityId)) return route.fallback()
        requests.push(payload)
        if (payload.includes('submissionKey') || payload.includes('submission_key')) {
          await route.fulfill({
            body: JSON.stringify({
              result: {
                attemptId: ids.attemptId,
                status: 'pending',
                resultUrl: `${activityPath}/attempts/${ids.attemptId}`,
              },
            }),
            contentType: 'application/json',
          })
          return
        }
        if (payload.includes('questionKey') || payload.includes('question_key')) {
          await route.fulfill({
            body: JSON.stringify({
              result: {
                status: 'conclusive',
                score: 100,
                explanation: 'Resposta avaliada.',
                criteria: payload.includes('code-1')
                  ? [
                      {
                        key: 'correct',
                        weightPercentage: 100,
                        level: '100',
                        commentId: 'correct-100',
                        comment: 'Solução correta.',
                      },
                    ]
                  : undefined,
                submittedFiles: payload.includes('code-1')
                  ? [{ path: 'index.js', content: sourceCode }]
                  : undefined,
              },
            }),
            contentType: 'application/json',
          })
          return
        }
        await route.fulfill({
          body: JSON.stringify({ result: mixedActivity }),
          contentType: 'application/json',
        })
      })

      await navigateAuthenticatedPage(authenticatedPage, activityPath)
      await authenticatedPage.getByText('4', { exact: true }).click()
      await authenticatedPage.getByRole('button', { name: 'Avaliar resposta' }).click()

      await expect(
        authenticatedPage.getByRole('heading', { name: 'Resultado', exact: true }),
      ).toBeVisible()
      await authenticatedPage.getByRole('button', { name: 'Próxima questão' }).click()
      await authenticatedPage.getByText('2', { exact: true }).click()
      await authenticatedPage.getByRole('button', { name: 'Avaliar resposta' }).click()
      await authenticatedPage.getByRole('button', { name: 'Próxima questão' }).click()

      await expect(
        authenticatedPage.getByRole('heading', { name: 'Somar os números pares' }),
      ).toBeVisible()
      await authenticatedPage.getByRole('tab', { name: 'Arquivos' }).click()

      await expect(
        authenticatedPage.getByRole('tree', { name: 'Arquivos do projeto' }),
      ).toBeVisible()
      await expect(
        authenticatedPage.getByRole('treeitem', { name: 'index.js' }),
      ).toHaveAttribute('aria-selected', 'true')
      await authenticatedPage.screenshot({
        path: testInfo.outputPath('code-question-tree-1440x900.png'),
      })
      await authenticatedPage.getByRole('tab', { name: 'Enunciado' }).click()
      const codeEditor = authenticatedPage.getByRole('textbox', {
        name: 'Código: index.js',
      })
      await authenticatedPage
        .context()
        .grantPermissions(['clipboard-read', 'clipboard-write'])
      await authenticatedPage.evaluate(
        async (code) => navigator.clipboard.writeText(code),
        sourceCode,
      )
      await codeEditor.focus()

      await expect(authenticatedPage.locator('.monaco-editor')).toBeVisible()
      await expect(
        authenticatedPage.locator('.monaco-editor .monaco-editor-background'),
      ).toHaveCSS('background-color', 'rgb(27, 27, 27)')
      await authenticatedPage.keyboard.press('Control+V')
      await expect
        .poll(async () =>
          authenticatedPage
            .locator('.monaco-editor .view-line span')
            .evaluateAll((spans) => {
              const keyword = spans.find((span) => span.textContent?.trim() === 'const')
              return keyword ? getComputedStyle(keyword).color : null
            }),
        )
        .toBe('rgb(255, 110, 180)')
      await expect(
        authenticatedPage.getByRole('application', {
          name: 'Terminal interativo. Digite a entrada padrão e pressione Enter.',
        }),
      ).toBeVisible()
      await expect(
        authenticatedPage.getByRole('log', { name: 'Transcrição do Terminal' }),
      ).toContainText('READY', { timeout: 15_000 })
      const terminalInput = authenticatedPage.locator('.xterm-helper-textarea')
      await terminalInput.focus()
      await authenticatedPage.keyboard.type('21')
      await authenticatedPage.keyboard.press('Enter')

      await expect(
        authenticatedPage.getByRole('log', { name: 'Transcrição do Terminal' }),
      ).toContainText('ECHO:21', { timeout: 30_000 })
      await expect(
        authenticatedPage.getByRole('button', { name: /Executar node/ }),
      ).toHaveCount(0)
      await expect(
        authenticatedPage.getByRole('textbox', {
          name: /Entrada padrão|Comando permitido/,
        }),
      ).toHaveCount(0)
      await authenticatedPage.screenshot({
        path: testInfo.outputPath('code-question-terminal-1440x900.png'),
      })
      await authenticatedPage.setViewportSize({ width: 390, height: 844 })
      await authenticatedPage.getByRole('tab', { name: 'Enunciado' }).click()
      const mobileTerminal = authenticatedPage.getByRole('application', {
        name: 'Terminal interativo. Digite a entrada padrão e pressione Enter.',
      })
      await mobileTerminal.scrollIntoViewIfNeeded()
      await expect(
        authenticatedPage.getByRole('log', { name: 'Transcrição do Terminal' }),
      ).toContainText('ECHO:21', { timeout: 30_000 })
      await expect
        .poll(() =>
          mobileTerminal.evaluate((element) => element.getBoundingClientRect().height),
        )
        .toBeLessThanOrEqual(448)
      await authenticatedPage.screenshot({
        path: testInfo.outputPath('code-question-terminal-output-390x844.png'),
      })
      await authenticatedPage.getByRole('tab', { name: 'Arquivos' }).click()

      await expect(
        authenticatedPage.getByRole('tree', { name: 'Arquivos do projeto' }),
      ).toBeVisible()
      expect(
        await authenticatedPage.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(390)
      await authenticatedPage.screenshot({
        path: testInfo.outputPath('code-question-tree-390x844.png'),
        fullPage: true,
      })
      await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
      await authenticatedPage.getByRole('button', { name: 'Avaliar questão' }).click()

      await expect(authenticatedPage.getByText('Solução correta.')).toBeVisible()
      await expect(authenticatedPage.getByText('Correção', { exact: true })).toBeVisible()
      await expect(authenticatedPage.getByText('correct', { exact: true })).toHaveCount(0)
      const submitAnswers = authenticatedPage.getByRole('button', {
        name: 'Enviar respostas',
      })
      await authenticatedPage.setViewportSize({ width: 1440, height: 520 })
      await submitAnswers.scrollIntoViewIfNeeded()
      await expect
        .poll(() =>
          authenticatedPage
            .getByRole('region', { name: 'Questão de código' })
            .evaluate((element) => element.getBoundingClientRect().height),
        )
        .toBeLessThanOrEqual(520)
      const appShell = authenticatedPage.getByRole('main').nth(1).locator('..')
      await expect
        .poll(() =>
          Promise.all([
            appShell.evaluate(
              (element) => element.getBoundingClientRect().bottom + window.scrollY,
            ),
            submitAnswers.evaluate(
              (element) => element.getBoundingClientRect().bottom + window.scrollY,
            ),
          ]).then(([shellBottom, actionBottom]) => shellBottom - actionBottom),
        )
        .toBeGreaterThanOrEqual(-1)
      await authenticatedPage.screenshot({
        path: testInfo.outputPath('code-question-feedback-viewport-1440x520.png'),
      })
      await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
      await authenticatedPage.getByRole('button', { name: 'Enviar respostas' }).click()

      await expect(authenticatedPage).toHaveURL(
        new RegExp(`${ids.activityId}/attempts/${ids.attemptId}$`),
      )
      const codePreview =
        requests.find(
          (request) => request.includes('code-1') && request.includes('questionKey'),
        ) ?? ''
      expect(codePreview).toContain('revision-mixed-1')
      expect(codePreview).toContain('index.js')
      const submission =
        requests.find((request) => request.includes('submissionKey')) ?? ''
      expect(submission).toContain('revision-mixed-1')
      expect(submission).toContain('code-1')
      expect(submission).toContain('const users = [')
      expect(submission).toContain('Alice')
      expect(submission).toContain("process.stdin.once('data'")
    })
  })
})
