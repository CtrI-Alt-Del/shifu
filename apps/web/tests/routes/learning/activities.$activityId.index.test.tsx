import { expect, navigateAuthenticatedPage, test } from '../../playwright'

const ids = {
  goalId: '01SHF000000000000000000003',
  skillId: '01SHF000000000000000000004',
  competencyId: '01SHF000000000000000000001',
  activityId: '01SHF000000000000000000005',
  attemptId: '01SHF000000000000000000009',
}
const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`
const activityResponse = {
  activityId: ids.activityId,
  title: 'Somar os números pares',
  difficulty: 'medium',
  canSubmit: true,
  latestAttemptId: null,
  unresolvedAttemptId: null,
  questions: [
    {
      key: 'q1',
      kind: 'single_choice',
      prompt: 'Qual é o primeiro resultado?',
      options: [
        { key: 'a', text: '4' },
        { key: 'b', text: '6' },
      ],
    },
    {
      key: 'q2',
      kind: 'multiple_selection',
      prompt: 'Selecione os pares',
      options: [
        { key: 'c', text: '2' },
        { key: 'd', text: '3' },
      ],
    },
  ],
}

test.describe('Activity index route', () => {
  test('shows a recoverable load error and retries the same Activity IDs', async ({
    authenticatedPage,
  }) => {
    let activityCalls = 0
    const requests: string[] = []
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
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
  }) => {
    const requests: string[] = []
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
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
  }) => {
    const savedActivity = { ...activityResponse, unresolvedAttemptId: ids.attemptId }
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
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
    await authenticatedPage.route('**/_serverFn/**', async (route) => {
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
    const submission = requests.find((request) => request.includes('submissionKey')) ?? ''
    expect(submission).toContain('revision-mixed-1')
    expect(submission).toContain('code-1')
    expect(submission).toContain('const users = [')
    expect(submission).toContain('Alice')
    expect(submission).toContain("process.stdin.once('data'")
  })
})
