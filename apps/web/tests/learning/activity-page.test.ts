import type { Page } from '@playwright/test'
import { ROUTES } from '@/constants/routes'
import {
  ChoiceActivityDetailFaker,
  ChoiceQuestionFaker,
  FillBlanksQuestionFaker,
  LearningRouteIdsFaker,
  PairMatchingQuestionFaker,
} from '@/core/learning/fakers'
import { installControlledDictation } from '../support/native-dictation'
import {
  IMAGE_CHOICE_FOOTER_WIDTHS,
  expectImageChoiceFootersContained,
} from '../support/image-choice-footer'
import { GamificationTransportFixture } from '../fixtures/gamification-transport-fixture'
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

const registerOrderingAnswerTest = (outcome: 'correct' | 'incorrect') =>
  test(`verifies and submits ${outcome === 'correct' ? 'a correct' : 'an incorrect'} ordering answer through the Activity route`, async ({
    authenticatedPage,
    bff,
  }) => {
    const isCorrect = outcome === 'correct'
    const orderingActivity = {
      ...activity,
      activityRevision: 'ordering-revision-1',
      orderingPassageKey: null,
      questions: [
        {
          key: 'ordering-1',
          kind: 'ordering' as const,
          prompt: 'Organize o preparo.',
          steps: [
            { key: 'wash', text: 'Lavar os legumes' },
            { key: 'cut', text: 'Cortar os legumes' },
            { key: 'cook', text: 'Aquecer a frigideira' },
          ],
          initialOrderedStepKeys: ['wash', 'cut', 'cook'],
          verified: null,
        },
      ],
    }
    const requests: string[] = []
    const passageKeys: string[] = []
    await bff.route(async (route) => {
      const body = route.request().postData() ?? ''
      const envelope = body ? (JSON.parse(body) as { t?: SerializedServerValue }) : null
      const serverPayload = envelope?.t ? decodeServerValue(envelope.t) : null
      const data = (serverPayload as { data?: Record<string, unknown> } | null)?.data
      const submission = data?.submission as Record<string, unknown> | undefined
      const passageKey = data?.passageKey ?? submission?.passageKey
      if (typeof passageKey === 'string') passageKeys.push(passageKey)
      const payload = decodeURIComponent(`${route.request().url()} ${body}`)
      if (!payload.includes(ids.activityId)) return route.fallback()
      requests.push(payload)
      if (!payload.includes('questionKey') && !payload.includes('submissionKey')) {
        await route.fulfill({
          body: JSON.stringify({ result: orderingActivity }),
          contentType: 'application/json',
        })
        return
      }
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
      await route.fulfill({
        body: JSON.stringify({
          result: {
            status: 'conclusive',
            score: isCorrect ? 100 : 0,
            isCorrect,
            explanation: isCorrect ? 'Ordem correta.' : 'Ordem incorreta.',
          },
        }),
        contentType: 'application/json',
      })
    })

    await navigateAuthenticatedPage(authenticatedPage, activityPath)
    const prompt = authenticatedPage.getByRole('heading', { name: 'Organize o preparo.' })
    await expect
      .poll(
        () =>
          prompt.evaluate((element) => {
            let opacity = 1
            let current: HTMLElement | null = element as HTMLElement
            while (current) {
              opacity *= Number(getComputedStyle(current).opacity)
              current = current.parentElement
            }
            return opacity
          }),
        { timeout: 5000 },
      )
      .toBeGreaterThan(0.99)
    await authenticatedPage.setViewportSize({ width: 1440, height: 980 })
    await authenticatedPage.screenshot({
      path: `.playwright-cli/screenshots/shifu-129-ordering-initial-${outcome}-desktop-1440.png`,
      fullPage: true,
      animations: 'disabled',
    })
    await authenticatedPage.setViewportSize({ width: 390, height: 844 })
    await authenticatedPage.screenshot({
      path: `.playwright-cli/screenshots/shifu-129-ordering-initial-${outcome}-mobile-390.png`,
      fullPage: true,
      animations: 'disabled',
    })
    await authenticatedPage.setViewportSize({ width: 1440, height: 980 })
    if (isCorrect)
      await authenticatedPage
        .getByRole('button', { name: 'Mover para baixo: Lavar os legumes' })
        .click()
    await expect(
      authenticatedPage.getByRole('button', { name: 'Verificar' }),
    ).toBeEnabled()
    await authenticatedPage.getByRole('button', { name: 'Verificar' }).click()
    await expect(
      authenticatedPage.getByText(isCorrect ? 'Ordem correta.' : 'Ordem incorreta.', {
        exact: true,
      }),
    ).toBeVisible()
    await authenticatedPage.screenshot({
      path: `.playwright-cli/screenshots/shifu-129-ordering-${outcome}-desktop-1440.png`,
      fullPage: true,
      animations: 'disabled',
    })
    await authenticatedPage.setViewportSize({ width: 390, height: 844 })
    const submitButton = authenticatedPage.getByRole('button', {
      name: 'Enviar atividade',
    })
    await authenticatedPage.evaluate(() =>
      window.scrollTo(0, document.documentElement.scrollHeight),
    )
    const submitBounds = await submitButton.boundingBox()
    const bottomNavigationBounds = await authenticatedPage
      .getByRole('navigation', { name: 'Navegação inferior' })
      .boundingBox()
    const mentorFabBounds = await authenticatedPage
      .getByRole('button', { name: 'Abrir Mentor' })
      .boundingBox()
    if (!submitBounds || !bottomNavigationBounds || !mentorFabBounds)
      throw new Error('Ordering mobile actions must have visible bounds')
    expect(submitBounds.height).toBeGreaterThanOrEqual(44)
    expect(submitBounds.y + submitBounds.height).toBeLessThanOrEqual(
      bottomNavigationBounds.y,
    )
    expect(submitBounds.x + submitBounds.width).toBeLessThanOrEqual(mentorFabBounds.x)
    await authenticatedPage.screenshot({
      path: `.playwright-cli/screenshots/shifu-129-ordering-${outcome}-mobile-390.png`,
      animations: 'disabled',
    })
    await authenticatedPage.getByRole('button', { name: 'Enviar atividade' }).click()
    await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))

    expect(requests.some((payload) => payload.includes('orderedStepKeys'))).toBe(true)
    expect(passageKeys).toHaveLength(2)
    expect(passageKeys[0]).toBeTruthy()
    expect(passageKeys[1]).toBe(passageKeys[0])
  })

registerOrderingAnswerTest('correct')
registerOrderingAnswerTest('incorrect')

type SerializedServerValue = {
  t?: number
  s?: unknown
  a?: SerializedServerValue[]
  p?: { k?: string[]; v?: SerializedServerValue[] }
}

const decodeServerValue = (value: SerializedServerValue): unknown => {
  if (value.t === 1) return value.s
  if (value.t === 9) return value.a?.map(decodeServerValue) ?? []
  if (value.t === 10 && value.p?.k && value.p.v)
    return Object.fromEntries(
      value.p.k.map((key, index) => [key, decodeServerValue(value.p?.v?.[index] ?? {})]),
    )
  return null
}

const decodeSerializedMarkup = (payload: string) => payload.replace(/\\{1,2}x3[cC]/g, '<')

test('assesses and submits an HTML/CSS/JavaScript question through the protected Activity route', async ({
  authenticatedPage,
  bff,
}) => {
  const htmlSource = '<main><h1>Minha página</h1></main>'
  const htmlActivity = {
    ...activity,
    accountId: 'playwright-account',
    activityRevision: 'html-revision-1',
    questions: [
      {
        key: 'html-1',
        kind: 'html_css_js',
        prompt: 'Crie uma página semântica.',
        initialFiles: [{ path: 'index.html', content: '<main></main>', editable: true }],
        entrypoint: 'index.html',
        editablePaths: ['index.html'],
        fixedDependencies: [{ name: 'vite', version: '7.0.0' }],
        permittedCommands: [],
        criteria: [{ key: 'semantic', name: 'HTML semântico', weightPercentage: 100 }],
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
            criteria: [
              {
                key: 'semantic',
                weightPercentage: 100,
                level: '100',
                commentId: 'complete',
                comment: 'Estrutura semântica correta.',
              },
            ],
            submittedFiles: [{ path: 'index.html', content: htmlSource }],
          },
        }),
        contentType: 'application/json',
      })
      return
    }
    await route.fulfill({
      body: JSON.stringify({ result: htmlActivity }),
      contentType: 'application/json',
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, activityPath)
  await expect(authenticatedPage.getByText(/Prática indisponível/i)).toBeVisible()
  const editor = authenticatedPage.getByRole('textbox', { name: 'Código: index.html' })
  await authenticatedPage
    .context()
    .grantPermissions(['clipboard-read', 'clipboard-write'])
  await authenticatedPage.evaluate(
    async (source) => navigator.clipboard.writeText(source),
    htmlSource,
  )
  await editor.focus()
  await authenticatedPage.keyboard.press('Control+A')
  await authenticatedPage.keyboard.press('Control+V')
  await expect(authenticatedPage.locator('.monaco-editor')).toBeVisible()
  await authenticatedPage.getByRole('button', { name: 'Avaliar questão' }).click()
  await expect(authenticatedPage.getByText('Estrutura semântica correta.')).toBeVisible()
  await authenticatedPage.getByRole('button', { name: 'Enviar atividade' }).click()
  await expect(authenticatedPage).toHaveURL(
    new RegExp(`${ids.activityId}/attempts/${ids.attemptId}$`),
  )

  const previewRequest =
    requests.find(
      (request) => request.includes('questionKey') || request.includes('question_key'),
    ) ?? ''
  const submissionRequest =
    requests.find(
      (request) =>
        request.includes('submissionKey') || request.includes('submission_key'),
    ) ?? ''
  expect(previewRequest).toContain('html_css_js')
  expect(previewRequest).toContain('html-revision-1')
  expect(previewRequest).toContain('index.html')
  expect(submissionRequest).toContain('html_css_js')
  expect(decodeSerializedMarkup(submissionRequest)).toContain(htmlSource)
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

  const entranceSelector =
    'section[aria-labelledby="choice-question-q1"] > div:has(> #choice-question-q1), fieldset[aria-labelledby="choice-question-q1"] > div'
  await authenticatedPage.emulateMedia({ reducedMotion: 'no-preference' })
  await sampleEntrance(authenticatedPage, entranceSelector)
  await navigateAuthenticatedPage(authenticatedPage, activityPath)

  await expect(authenticatedPage.locator('pre code')).toHaveText(
    /pode_entrar = tem_cracha and tem_senha/,
  )
  const normalFrames = await entranceFrames(authenticatedPage)
  expect(normalFrames).toHaveLength(90)
  for (let target = 0; target < 5; target += 1) {
    expect(
      normalFrames?.some(
        (frame) => frame[target].opacity > 0 && frame[target].opacity < 1,
      ),
    ).toBe(true)
    expect(normalFrames?.some((frame) => frame[target].y > 0)).toBe(true)
  }
  expect(normalFrames?.at(-1)).toEqual(
    Array.from({ length: 5 }, () => ({ opacity: 1, x: 0, y: 0 })),
  )

  // Remount under reduced motion and observe its first paint, rather than
  // inspecting a finished normal entrance after changing the preference.
  await navigateAuthenticatedPage(authenticatedPage, ROUTES.privacy)
  await authenticatedPage.emulateMedia({ reducedMotion: 'reduce' })
  await sampleEntrance(authenticatedPage, entranceSelector)
  await navigateAuthenticatedPage(authenticatedPage, activityPath)
  const reducedFrames = await entranceFrames(authenticatedPage)
  expect(reducedFrames).toHaveLength(90)
  expect(
    reducedFrames?.every(
      (frame) =>
        frame.length === 5 &&
        frame.every((target) => target.opacity === 1 && target.x === 0 && target.y === 0),
    ),
  ).toBe(true)
  await expect(
    authenticatedPage.getByRole('heading', { name: /Quais afirmações são verdadeiras/ }),
  ).toBeVisible()
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
      const appShell = authenticatedPage
        .getByRole('main')
        .filter({ has: submitAnswers })
        .first()
        .locator('..')
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

test('keeps the integrated route usable on mobile when practice is unavailable', async ({
  authenticatedPage,
  bff,
  activeAccount,
}) => {
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })
  await authenticatedPage.addInitScript(() => {
    Object.defineProperty(window, 'crossOriginIsolated', {
      value: false,
      configurable: true,
    })
  })
  const integrated = {
    ...activity,
    activityRevision: 'integrated-browser-v1',
    accountId: activeAccount.accountId,
    questions: [
      {
        key: 'integrated',
        kind: 'react_fastify',
        prompt: 'Conecte a lista à API',
        initialFiles: [
          {
            path: 'src/App.tsx',
            content: 'export default function App() {\n  return null\n}',
            editable: true,
          },
          { path: 'server.js', content: 'console.log("API")', editable: true },
        ],
        editablePaths: ['src/App.tsx', 'server.js'],
        frontendEntrypoint: 'src/App.tsx',
        apiEntrypoint: 'server.js',
        frontendCommandId: 'web',
        apiCommandId: 'api',
        fixedDependencies: [],
        permittedCommands: [],
        additionalFilePolicy: {
          allowedDirectories: ['src'],
          allowedExtensions: ['.tsx'],
          maxFiles: 2,
        },
        httpExamples: [
          {
            key: 'list',
            title: 'Listar tarefas',
            method: 'GET',
            path: '/api/tasks',
            body: null,
          },
        ],
        criteria: [
          { key: 'integration', name: 'Integração com a API', weightPercentage: 100 },
        ],
      },
    ],
  }
  await bff.route(async (route) => {
    const payload = decodeURIComponent(
      `${route.request().url()} ${route.request().postData() ?? ''}`,
    )
    if (payload.includes(ids.activityId)) {
      await route.fulfill({
        body: JSON.stringify({ result: integrated }),
        contentType: 'application/json',
      })
      return
    }
    await route.fallback()
  })
  await navigateAuthenticatedPage(authenticatedPage, activityPath)
  await expect(
    authenticatedPage.getByRole('region', { name: 'Questão React + Fastify' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Peso 100%')).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Avaliar questão' }),
  ).toBeEnabled()
  const editor = authenticatedPage.locator('.monaco-editor').first()
  await expect
    .poll(async () => (await editor.boundingBox())?.height ?? 0)
    .toBeGreaterThanOrEqual(300)
  await expect(editor.locator('.view-line').filter({ hasText: /return/ })).toBeVisible()
  expect(await editor.locator('.view-line').count()).toBeGreaterThanOrEqual(3)
  await authenticatedPage.getByRole('tab', { name: 'Arquivos' }).click()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Novo arquivo' }),
  ).toHaveCount(1)
  await authenticatedPage
    .getByRole('textbox', { name: 'Caminho do novo arquivo' })
    .fill('src/Badge.tsx')
  await authenticatedPage.getByRole('button', { name: 'Novo arquivo' }).click()
  await expect(
    authenticatedPage.getByRole('treeitem', { name: 'Badge.tsx' }),
  ).toBeVisible()
  await authenticatedPage.getByRole('tab', { name: 'HTTP' }).click()
  await expect(
    authenticatedPage.getByRole('textbox', { name: 'Rota da API' }),
  ).toHaveValue('/api/tasks')
  await expect(
    authenticatedPage.getByRole('button', { name: 'Enviar requisição' }),
  ).toBeDisabled()
  await authenticatedPage.getByRole('tab', { name: 'Terminal' }).click()
  await expect(
    authenticatedPage.getByRole('textbox', { name: 'Comando permitido' }),
  ).toBeVisible()
  expect(
    await authenticatedPage.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true)
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.activityId}/?$`))
})

const PROMPT = 'Traduza a frase a seguir para o inglês.'
const SOURCE_TEXT = 'Bom dia, como você está?'
const REFERENCE_TRANSLATION = 'Good morning, how is it going?'

function translationActivity(overrides: Record<string, unknown> = {}) {
  return {
    activityId: ids.activityId,
    title: 'Tradução de texto',
    difficulty: 'medium',
    canSubmit: true,
    latestAttemptId: null,
    unresolvedAttemptId: null,
    activityRevision: 'translation-revision-1',
    questions: [
      {
        key: 'q1',
        kind: 'translation',
        prompt: PROMPT,
        sourceLanguage: 'pt-BR',
        targetLanguage: 'en-US',
        sourceText: SOURCE_TEXT,
        criteria: [
          {
            key: 'semantic_preservation',
            name: 'Preservação semântica',
            weightPercentage: 70,
          },
          {
            key: 'grammatical_adequacy',
            name: 'Adequação gramatical',
            weightPercentage: 30,
          },
        ],
      },
    ],
    ...overrides,
  }
}

const fillBlanksActivity = {
  ...activity,
  accountId: 'playwright-account',
  activityRevision: 'fill-revision-1',
  questions: [
    FillBlanksQuestionFaker.fake({
      segments: [
        { text: 'She ', blankKey: null },
        { text: null, blankKey: 'b1' },
        { text: ' to school and ', blankKey: null },
        { text: null, blankKey: 'b2' },
        { text: '.', blankKey: null },
      ],
      bank: [
        { key: 'w1', word: 'goes' },
        { key: 'w2', word: 'does' },
        { key: 'w3', word: 'go' },
      ],
    }),
    ChoiceQuestionFaker.fake({
      key: 'q1',
      prompt: 'Qual é o resultado?',
      options: [
        { key: 'a', text: '4' },
        { key: 'b', text: '6' },
      ],
    }),
  ],
}

async function stubFillBlanksActivity(
  bff: {
    route: (
      handler: (route: import('@playwright/test').Route) => Promise<void>,
    ) => Promise<void>
  },
  requests: string[],
) {
  let fillPreviews = 0
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
      const isFill = payload.includes('fill-1')
      fillPreviews += isFill ? 1 : 0
      const result = !isFill
        ? { status: 'conclusive', score: 100, explanation: 'Correto.', isCorrect: true }
        : fillPreviews === 1
          ? {
              status: 'conclusive',
              score: 50,
              explanation: 'Quase lá. Revise a forma do verbo.',
              isCorrect: false,
              correctBlankCount: 1,
              blankCount: 2,
            }
          : {
              status: 'conclusive',
              score: 100,
              explanation: 'Correto! O verbo recebe -s ou -es.',
              isCorrect: true,
              correctBlankCount: 2,
              blankCount: 2,
            }
      await route.fulfill({
        body: JSON.stringify({ result }),
        contentType: 'application/json',
      })
      return
    }
    await route.fulfill({
      body: JSON.stringify({ result: fillBlanksActivity }),
      contentType: 'application/json',
    })
  })
}

const FILL_BLANKS_VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]

for (const viewport of FILL_BLANKS_VIEWPORTS) {
  test(`fills, checks, edits, re-checks and submits a fill-in-the-blank Activity by keyboard on ${viewport.name}`, async ({
    authenticatedPage,
    bff,
  }) => {
    await authenticatedPage.setViewportSize({
      width: viewport.width,
      height: viewport.height,
    })
    const requests: string[] = []
    await stubFillBlanksActivity(bff, requests)

    await navigateAuthenticatedPage(authenticatedPage, activityPath)
    const bank = authenticatedPage.getByRole('region', { name: 'Banco de palavras' })
    const word = (name: string) =>
      bank.getByRole('button', { name: new RegExp(`^${name}( Selecionada)?$`) })
    const emptyBlank = (number: number) =>
      authenticatedPage.getByRole('button', { name: `Lacuna ${number}: vazia` })
    const filledBlank = (number: number, text: string) =>
      authenticatedPage.getByRole('button', {
        name: new RegExp(
          `^Lacuna ${number}: ${text} ?\\. Ative para remover a palavra\\.$`,
        ),
      })

    await expect(emptyBlank(1)).toBeVisible()
    await expect(authenticatedPage.getByText('0 de 2 lacunas preenchidas')).toBeVisible()
    await expect(
      authenticatedPage.getByRole('button', { name: 'Avaliar resposta' }),
    ).toBeDisabled()

    await word('go').focus()
    await authenticatedPage.keyboard.press('Enter')
    await expect(word('go')).toHaveAttribute('aria-pressed', 'true')
    await emptyBlank(1).focus()
    await authenticatedPage.keyboard.press('Enter')
    await expect(filledBlank(1, 'go')).toBeVisible()
    await expect(word('go')).toHaveCount(0)

    await word('does').focus()
    await authenticatedPage.keyboard.press('Enter')
    await emptyBlank(2).focus()
    await authenticatedPage.keyboard.press('Enter')
    await expect(filledBlank(2, 'does')).toBeVisible()
    await expect(authenticatedPage.getByText('2 de 2 lacunas preenchidas')).toBeVisible()

    const check = authenticatedPage.getByRole('button', { name: 'Avaliar resposta' })
    await expect(check).toBeEnabled()
    await check.focus()
    await authenticatedPage.keyboard.press('Enter')
    const result = authenticatedPage.getByRole('region', { name: 'Resultado' })
    await expect(result).toContainText('Parcialmente correta')
    await expect(result).toContainText('1 de 2 lacunas corretas')
    await expect(result).toContainText('Quase lá. Revise a forma do verbo.')
    await expect(result).not.toContainText('goes')

    // The fill stays editable after the feedback: a replaced word returns to the bank.
    await word('goes').focus()
    await authenticatedPage.keyboard.press('Enter')
    await filledBlank(1, 'go').focus()
    await authenticatedPage.keyboard.press('Enter')
    await expect(filledBlank(1, 'goes')).toBeVisible()
    await expect(word('go')).toHaveCount(1)
    await expect(result).toHaveCount(0)
    await expect(
      authenticatedPage.getByRole('button', { name: 'Avaliar resposta' }),
    ).toBeEnabled()

    await authenticatedPage.getByRole('button', { name: 'Avaliar resposta' }).click()
    await expect(result).toContainText('Resposta correta')
    await expect(result).toContainText('2 de 2 lacunas corretas')
    await authenticatedPage.getByRole('button', { name: 'Próxima questão' }).click()

    await authenticatedPage.getByRole('radio', { name: '4' }).focus()
    await authenticatedPage.keyboard.press('Space')
    await authenticatedPage.getByRole('button', { name: 'Avaliar resposta' }).click()
    await authenticatedPage.getByRole('button', { name: 'Enviar respostas' }).click()
    await expect(authenticatedPage).toHaveURL(
      new RegExp(`${ids.activityId}/attempts/${ids.attemptId}$`),
    )

    const fillPreviews = requests.filter(
      (request) =>
        request.includes('questionKey') &&
        !request.includes('submissionKey') &&
        request.includes('fill-1'),
    )
    expect(fillPreviews).toHaveLength(2)
    for (const request of fillPreviews) {
      expect(request).toContain('fill_blanks')
      expect(request).toContain('fill-revision-1')
    }
    expect(fillPreviews[0]).toContain('w3')
    expect(fillPreviews[1]).toContain('w1')
    expect(fillPreviews[1]).not.toContain('w3')
    const submission =
      requests.find(
        (request) =>
          request.includes('submissionKey') || request.includes('submission_key'),
      ) ?? ''
    expect(submission).toContain('fill_blanks')
    expect(submission).toContain('w1')
    expect(submission).toContain('w2')
    expect(submission).toContain('fill-revision-1')
  })
}

const pairMatchingActivity = {
  ...activity,
  accountId: 'playwright-account',
  activityRevision: 'pair-revision-1',
  questions: [
    PairMatchingQuestionFaker.fake(),
    ChoiceQuestionFaker.fake({
      key: 'q1',
      prompt: 'Qual é o resultado?',
      options: [
        { key: 'a', text: '4' },
        { key: 'b', text: '6' },
      ],
    }),
  ],
}

async function stubPairMatchingActivity(
  bff: {
    route: (
      handler: (route: import('@playwright/test').Route) => Promise<void>,
    ) => Promise<void>
  },
  requests: string[],
) {
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
      const isPair = payload.includes('pairs-1')
      const result = isPair
        ? {
            status: 'conclusive',
            score: 33.33,
            explanation: 'Alguns pares estão corretos. Revise o vocabulário.',
            isCorrect: false,
            outcome: 'partial',
            correctPairCount: 1,
            totalPairCount: 3,
          }
        : { status: 'conclusive', score: 100, explanation: 'Correto.', isCorrect: true }
      await route.fulfill({
        body: JSON.stringify({ result }),
        contentType: 'application/json',
      })
      return
    }
    await route.fulfill({
      body: JSON.stringify({ result: pairMatchingActivity }),
      contentType: 'application/json',
    })
  })
}

const PAIR_MATCHING_VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]

for (const viewport of PAIR_MATCHING_VIEWPORTS) {
  test(`pairs, verifies, locks and submits a pair matching Activity by keyboard on ${viewport.name}`, async ({
    authenticatedPage,
    bff,
  }) => {
    await authenticatedPage.setViewportSize({
      width: viewport.width,
      height: viewport.height,
    })
    const requests: string[] = []
    await stubPairMatchingActivity(bff, requests)

    await navigateAuthenticatedPage(authenticatedPage, activityPath)
    await expect(authenticatedPage.getByText('Inglês (Estados Unidos)')).toBeVisible()
    await expect(authenticatedPage.getByText('Português (Brasil)')).toBeVisible()
    await expect(authenticatedPage.getByText('0 de 3 pares formados.')).toBeVisible()
    const verify = authenticatedPage.getByRole('button', { name: 'Avaliar resposta' })
    await expect(verify).toBeDisabled()

    const wordsList = authenticatedPage.locator('ul').nth(0)
    const translationsList = authenticatedPage.locator('ul').nth(1)
    const pair = async (word: string, translation: string) => {
      await wordsList.getByRole('button', { name: new RegExp(`^${word}`) }).focus()
      await authenticatedPage.keyboard.press('Enter')
      await translationsList
        .getByRole('button', { name: new RegExp(`^${translation}`) })
        .focus()
      await authenticatedPage.keyboard.press('Enter')
    }

    // A wrong but complete pairing is valid; verification does not need correctness.
    await pair('dog', 'casa')
    await pair('house', 'água')
    await expect(verify).toBeDisabled()
    await pair('water', 'cachorro')
    await expect(authenticatedPage.getByText('3 de 3 pares formados.')).toBeVisible()
    await expect(verify).toBeEnabled()

    // A pair is replaced by selecting its word again and choosing another translation.
    await wordsList.getByRole('button', { name: /^water/ }).focus()
    await authenticatedPage.keyboard.press('Enter')
    await translationsList.getByRole('button', { name: /^água/ }).focus()
    await authenticatedPage.keyboard.press('Enter')
    await expect(authenticatedPage.getByText('2 de 3 pares formados.')).toBeVisible()
    await pair('house', 'cachorro')
    await expect(authenticatedPage.getByText('3 de 3 pares formados.')).toBeVisible()

    await verify.focus()
    await authenticatedPage.keyboard.press('Enter')
    const result = authenticatedPage.getByRole('region', { name: 'Resultado' })
    await expect(result).toContainText('Parcialmente correta')
    await expect(result).toContainText('1 de 3 pares corretos')
    await expect(result).toContainText(
      'Alguns pares estão corretos. Revise o vocabulário.',
    )
    await expect(result).not.toContainText('esperad')

    // After verifying, the evaluated answer is read-only.
    for (const button of await wordsList.getByRole('button').all())
      await expect(button).toBeDisabled()
    await expect(
      authenticatedPage.getByText('Resposta avaliada: não é possível alterar.'),
    ).toBeVisible()
    await authenticatedPage.getByRole('button', { name: 'Próxima questão' }).click()

    await authenticatedPage.getByRole('radio', { name: '4' }).focus()
    await authenticatedPage.keyboard.press('Space')
    await authenticatedPage.getByRole('button', { name: 'Avaliar resposta' }).click()
    await authenticatedPage.getByRole('button', { name: 'Enviar respostas' }).click()
    await expect(authenticatedPage).toHaveURL(
      new RegExp(`${ids.activityId}/attempts/${ids.attemptId}$`),
    )

    const previews = requests.filter(
      (request) =>
        request.includes('questionKey') &&
        !request.includes('submissionKey') &&
        request.includes('pairs-1'),
    )
    expect(previews).toHaveLength(1)
    expect(previews[0]).toContain('pair_matching')
    expect(previews[0]).toContain('pair-revision-1')
    for (const key of ['w-3f9a21c4', 'w-b07d5e18', 'w-5c1e9a73']) {
      expect(previews[0]).toContain(key)
    }
    const submission =
      requests.find(
        (request) =>
          request.includes('submissionKey') || request.includes('submission_key'),
      ) ?? ''
    expect(submission).toContain('pair_matching')
    expect(submission).toContain('pair-revision-1')
    // The submitted pairs are the ones that were verified (dog-casa, house-cachorro).
    expect(submission).toContain('t-91c7d3fa')
    expect(submission).toContain('t-e2480b6d')
  })
}

test('drops a bank word on a blank with the mouse', async ({
  authenticatedPage,
  bff,
}) => {
  await authenticatedPage.setViewportSize({ width: 1440, height: 900 })
  await stubFillBlanksActivity(bff, [])

  await navigateAuthenticatedPage(authenticatedPage, activityPath)
  const bank = authenticatedPage.getByRole('region', { name: 'Banco de palavras' })
  const source = bank.getByRole('button', { name: 'does', exact: true })
  const target = authenticatedPage.getByRole('button', { name: 'Lacuna 2: vazia' })
  const from = await source.boundingBox()
  const to = await target.boundingBox()
  if (!from || !to) throw new Error('Drag source or target is not visible.')

  await authenticatedPage.mouse.move(from.x + from.width / 2, from.y + from.height / 2)
  await authenticatedPage.mouse.down()
  await authenticatedPage.mouse.move(to.x + to.width / 2 - 20, to.y + to.height / 2, {
    steps: 12,
  })
  await authenticatedPage.mouse.move(to.x + to.width / 2, to.y + to.height / 2, {
    steps: 4,
  })
  await authenticatedPage.mouse.up()

  await expect(
    authenticatedPage.getByRole('button', {
      name: /^Lacuna 2: does ?\. Ative para remover a palavra\.$/,
    }),
  ).toBeVisible()
  await expect(bank.getByRole('button', { name: 'does', exact: true })).toHaveCount(0)
})

test.describe('VM-01 — Typed translation happy path', () => {
  test('types a translation, requests feedback, and submits through the real Activity route', async ({
    authenticatedPage,
    bff,
  }) => {
    const activity = translationActivity()
    const submittedText = 'Good morning, how are you?'
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
              criteria: [
                {
                  key: 'semantic_preservation',
                  weightPercentage: 70,
                  level: '100',
                  commentId: 'semantic-100',
                  comment: 'Sentido preservado integralmente.',
                },
                {
                  key: 'grammatical_adequacy',
                  weightPercentage: 30,
                  level: '100',
                  commentId: 'grammar-100',
                  comment: 'Gramática correta.',
                },
              ],
              submittedText,
            },
          }),
          contentType: 'application/json',
        })
        return
      }
      await route.fulfill({
        body: JSON.stringify({ result: activity }),
        contentType: 'application/json',
      })
    })

    // Controlled dictation shadows the real native recognizer, which otherwise
    // crashes the headless renderer when instantiated with no audio device.
    await installControlledDictation(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, activityPath)

    await expect(authenticatedPage.getByRole('heading', { name: PROMPT })).toBeVisible()
    await expect(authenticatedPage.getByText(SOURCE_TEXT)).toBeVisible()

    const textarea = authenticatedPage.getByRole('textbox', { name: 'Sua tradução' })
    await textarea.focus()
    await authenticatedPage.keyboard.type(submittedText)
    await expect(textarea).toHaveValue(submittedText)

    const assessButton = authenticatedPage.getByRole('button', {
      name: 'Avaliar resposta',
    })
    await expect(assessButton).toBeEnabled()
    await assessButton.focus()
    await expect(assessButton).toBeFocused()
    await authenticatedPage.keyboard.press('Enter')

    await expect(
      authenticatedPage.getByRole('heading', { name: 'Resultado', exact: true }),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByText('Sentido preservado integralmente.'),
    ).toBeVisible()
    await expect(authenticatedPage.getByText('Gramática correta.')).toBeVisible()
    await expect(authenticatedPage.getByText('Pontuação:')).toBeVisible()

    const submitButton = authenticatedPage.getByRole('button', {
      name: 'Enviar respostas',
    })
    await submitButton.focus()
    await expect(submitButton).toBeFocused()
    await authenticatedPage.keyboard.press('Enter')

    await expect(authenticatedPage).toHaveURL(
      new RegExp(`${ids.activityId}/attempts/${ids.attemptId}$`),
    )

    const previewRequest =
      requests.find(
        (request) => request.includes('questionKey') || request.includes('question_key'),
      ) ?? ''
    const submissionRequest =
      requests.find(
        (request) =>
          request.includes('submissionKey') || request.includes('submission_key'),
      ) ?? ''
    expect(previewRequest).toContain('translation-revision-1')
    expect(decodeURIComponent(previewRequest)).toContain(submittedText)
    expect(submissionRequest).toContain('translation-revision-1')
    expect(decodeURIComponent(submissionRequest)).toContain(submittedText)
  })

  test('keeps the translation question usable without horizontal overflow on a narrow viewport', async ({
    authenticatedPage,
    bff,
  }) => {
    const activity = translationActivity()
    await bff.route(async (route) => {
      const payload = decodeURIComponent(route.request().url())
      if (!payload.includes(ids.activityId)) return route.fallback()
      await route.fulfill({
        body: JSON.stringify({ result: activity }),
        contentType: 'application/json',
      })
    })

    await authenticatedPage.setViewportSize({ width: 390, height: 844 })
    await installControlledDictation(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, activityPath)

    await expect(authenticatedPage.getByRole('heading', { name: PROMPT })).toBeVisible()
    await expect(
      authenticatedPage.getByRole('textbox', { name: 'Sua tradução' }),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByRole('button', { name: 'Iniciar ditado' }),
    ).toBeVisible()
    expect(
      await authenticatedPage.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(390)
  })
})

test.describe('VM-02 — Dictation capture, confirm-replace and failure recovery', () => {
  test('confirms or declines a dictated transcript and preserves text after a denied-permission failure', async ({
    authenticatedPage,
    bff,
  }) => {
    const activity = translationActivity()
    await bff.route(async (route) => {
      const payload = decodeURIComponent(route.request().url())
      if (!payload.includes(ids.activityId)) return route.fallback()
      await route.fulfill({
        body: JSON.stringify({ result: activity }),
        contentType: 'application/json',
      })
    })

    await installControlledDictation(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, activityPath)

    const textarea = authenticatedPage.getByRole('textbox', { name: 'Sua tradução' })
    await textarea.fill('Rascunho inicial')

    const startButton = authenticatedPage.getByRole('button', {
      name: 'Iniciar ditado',
    })
    const stopButton = authenticatedPage.getByRole('button', { name: 'Parar ditado' })
    const cancelDictationButton = authenticatedPage.getByRole('button', {
      name: 'Cancelar ditado',
    })

    // First dictation: decline the replacement, original text must survive.
    await startButton.click()
    await expect(authenticatedPage.getByText('Preparando o microfone…')).toBeVisible()
    await authenticatedPage.evaluate(() => {
      const native = window as typeof window & {
        SpeechRecognition: { current: { onstart: (() => void) | null } }
      }
      native.SpeechRecognition.current.onstart?.()
    })
    await expect(authenticatedPage.getByText(/Gravando ditado…/)).toBeVisible()
    await expect(stopButton).toBeEnabled()
    await stopButton.click()
    await expect(authenticatedPage.getByText('Transcrevendo o ditado…')).toBeVisible()
    await authenticatedPage.evaluate(() => {
      const native = window as typeof window & {
        SpeechRecognition: {
          current: {
            onresult: ((event: unknown) => void) | null
            onend: (() => void) | null
          }
        }
      }
      native.SpeechRecognition.current.onresult?.({
        resultIndex: 0,
        results: [{ isFinal: true, 0: { transcript: 'Texto ditado descartado' } }],
      })
      native.SpeechRecognition.current.onend?.()
    })

    const confirmDialog = authenticatedPage.getByRole('alertdialog', {
      name: 'Confirmar substituição por ditado',
    })
    await expect(confirmDialog).toBeVisible()
    await expect(confirmDialog.getByText('Texto ditado descartado')).toBeVisible()
    await confirmDialog.getByRole('button', { name: 'Cancelar', exact: true }).click()
    await expect(confirmDialog).toHaveCount(0)
    await expect(textarea).toHaveValue('Rascunho inicial')

    // Second dictation: confirm the replacement this time.
    await startButton.click()
    await authenticatedPage.evaluate(() => {
      const native = window as typeof window & {
        SpeechRecognition: { current: { onstart: (() => void) | null } }
      }
      native.SpeechRecognition.current.onstart?.()
    })
    await stopButton.click()
    await authenticatedPage.evaluate(() => {
      const native = window as typeof window & {
        SpeechRecognition: {
          current: {
            onresult: ((event: unknown) => void) | null
            onend: (() => void) | null
          }
        }
      }
      native.SpeechRecognition.current.onresult?.({
        resultIndex: 0,
        results: [{ isFinal: true, 0: { transcript: 'Bom dia, tudo bem?' } }],
      })
      native.SpeechRecognition.current.onend?.()
    })
    await expect(confirmDialog).toBeVisible()
    await confirmDialog.getByRole('button', { name: 'Confirmar' }).click()
    await expect(confirmDialog).toHaveCount(0)
    await expect(textarea).toHaveValue('Bom dia, tudo bem?')

    // Third dictation: a denied-permission failure must preserve the confirmed text.
    await startButton.click()
    await authenticatedPage.evaluate(() => {
      const native = window as typeof window & {
        SpeechRecognition: { current: { onstart: (() => void) | null } }
      }
      native.SpeechRecognition.current.onstart?.()
    })
    await authenticatedPage.evaluate(() => {
      const native = window as typeof window & {
        SpeechRecognition: {
          current: { onerror: ((event: { error: string }) => void) | null }
        }
      }
      native.SpeechRecognition.current.onerror?.({ error: 'not-allowed' })
    })
    await expect(
      authenticatedPage.getByRole('alert').filter({
        hasText: 'Permissão do microfone negada. Você pode continuar digitando.',
      }),
    ).toBeVisible()
    await expect(textarea).toHaveValue('Bom dia, tudo bem?')
    await expect(cancelDictationButton).toBeDisabled()
    await expect(startButton).toBeEnabled()

    // Typing must still work after the failure.
    await textarea.focus()
    await authenticatedPage.keyboard.type(' Ainda digitando.')
    await expect(textarea).toHaveValue('Bom dia, tudo bem? Ainda digitando.')

    // Fourth dictation: a transcription failure (no transcript before onend)
    // must also preserve the existing text and surface its own message.
    await startButton.click()
    await authenticatedPage.evaluate(() => {
      const native = window as typeof window & {
        SpeechRecognition: { current: { onstart: (() => void) | null } }
      }
      native.SpeechRecognition.current.onstart?.()
    })
    await stopButton.click()
    await authenticatedPage.evaluate(() => {
      const native = window as typeof window & {
        SpeechRecognition: { current: { onend: (() => void) | null } }
      }
      native.SpeechRecognition.current.onend?.()
    })
    await expect(
      authenticatedPage.getByRole('alert').filter({
        hasText: 'Não foi possível reconhecer o ditado.',
      }),
    ).toBeVisible()
    await expect(textarea).toHaveValue('Bom dia, tudo bem? Ainda digitando.')
  })

  test('explains unavailability and keeps the field usable when no recognizer exists', async ({
    authenticatedPage,
    bff,
  }) => {
    const activity = translationActivity()
    await bff.route(async (route) => {
      const payload = decodeURIComponent(route.request().url())
      if (!payload.includes(ids.activityId)) return route.fallback()
      await route.fulfill({
        body: JSON.stringify({ result: activity }),
        contentType: 'application/json',
      })
    })

    // navigateAuthenticatedPage performs a client-side route change on the
    // already-loaded document, so addInitScript (which only fires on a new
    // document load) would run too late. Override the globals in place instead,
    // the same way installControlledDictation does for the other scenarios. A
    // plain delete can also no-op on a non-configurable native global, so
    // overwrite the value directly.
    await authenticatedPage.evaluate(() => {
      for (const name of ['SpeechRecognition', 'webkitSpeechRecognition']) {
        try {
          Object.defineProperty(window, name, {
            value: undefined,
            configurable: true,
            writable: true,
          })
        } catch {
          // The native global could not be overridden; leave it as is.
        }
      }
    })
    await navigateAuthenticatedPage(authenticatedPage, activityPath)

    await expect(
      authenticatedPage.getByText(
        'Ditado indisponível neste navegador. Continue digitando.',
      ),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByRole('button', { name: 'Iniciar ditado' }),
    ).toHaveCount(0)
    const textarea = authenticatedPage.getByRole('textbox', { name: 'Sua tradução' })
    await textarea.fill('Resposta digitada sem ditado')
    await expect(textarea).toHaveValue('Resposta digitada sem ditado')
  })
})

test.describe('VM-03 — Inconclusive and partial-result disclosure', () => {
  test('blocks advance while inconclusive, reevaluates, and discloses a partial label without the reference translation', async ({
    authenticatedPage,
    bff,
  }) => {
    const activity = translationActivity()
    const submittedText = 'Good morning, how are things?'
    let previewCalls = 0

    await bff.route(async (route) => {
      const payload = decodeURIComponent(
        `${route.request().url()} ${route.request().postData() ?? ''}`,
      )
      if (!payload.includes(ids.activityId)) return route.fallback()
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
        previewCalls += 1
        if (previewCalls === 1) {
          await route.fulfill({
            body: JSON.stringify({
              result: {
                status: 'inconclusive',
                score: null,
                criteria: [
                  {
                    key: 'semantic_preservation',
                    weightPercentage: 70,
                    level: 'inconclusive',
                    commentId: 'semantic-inconclusive',
                    comment: 'Não foi possível avaliar o sentido.',
                  },
                  {
                    key: 'grammatical_adequacy',
                    weightPercentage: 30,
                    level: '75',
                    commentId: 'grammar-75',
                    comment: 'Pequenos desvios gramaticais.',
                  },
                ],
                submittedText,
              },
            }),
            contentType: 'application/json',
          })
          return
        }
        await route.fulfill({
          body: JSON.stringify({
            result: {
              status: 'conclusive',
              score: 65,
              criteria: [
                {
                  key: 'semantic_preservation',
                  weightPercentage: 70,
                  level: '75',
                  commentId: 'semantic-75',
                  comment: 'O sentido geral foi preservado parcialmente.',
                },
                {
                  key: 'grammatical_adequacy',
                  weightPercentage: 30,
                  level: '25',
                  commentId: 'grammar-25',
                  comment: 'Vários desvios gramaticais.',
                },
              ],
              submittedText,
            },
          }),
          contentType: 'application/json',
        })
        return
      }
      if (payload.includes(ids.attemptId)) {
        await route.fulfill({
          body: JSON.stringify({
            result: {
              attemptId: ids.attemptId,
              activityId: ids.activityId,
              status: 'completed',
              submittedAt: '2026-11-14T12:00:00Z',
              retryAllowed: false,
              score: 65,
              questions: [
                {
                  key: 'q1',
                  kind: 'translation',
                  prompt: PROMPT,
                  score: 65,
                  submittedText,
                  criterionResults: [
                    {
                      key: 'semantic_preservation',
                      weightPercentage: 70,
                      level: 75,
                      commentId: 'semantic-75',
                      comment: 'O sentido geral foi preservado parcialmente.',
                    },
                    {
                      key: 'grammatical_adequacy',
                      weightPercentage: 30,
                      level: 25,
                      commentId: 'grammar-25',
                      comment: 'Vários desvios gramaticais.',
                    },
                  ],
                  conceptObservations: [],
                },
              ],
            },
          }),
          contentType: 'application/json',
        })
        return
      }
      await route.fulfill({
        body: JSON.stringify({ result: activity }),
        contentType: 'application/json',
      })
    })

    await installControlledDictation(authenticatedPage)
    await navigateAuthenticatedPage(authenticatedPage, activityPath)
    const textarea = authenticatedPage.getByRole('textbox', { name: 'Sua tradução' })
    await textarea.fill(submittedText)
    await authenticatedPage.getByRole('button', { name: 'Avaliar resposta' }).click()

    await expect(
      authenticatedPage.getByText(
        'Não foi possível concluir esta avaliação. Reavalie a mesma resposta.',
      ),
    ).toBeVisible()
    const reevaluateButton = authenticatedPage.getByRole('button', {
      name: 'Reavaliar resposta',
    })
    await expect(reevaluateButton).toBeVisible()
    await expect(
      authenticatedPage.getByRole('button', { name: 'Enviar respostas' }),
    ).toHaveCount(0)

    await reevaluateButton.click()

    await expect(authenticatedPage.getByText('Pontuação:')).toBeVisible()
    await expect(
      authenticatedPage.getByText('O sentido geral foi preservado parcialmente.'),
    ).toBeVisible()
    const submitButton = authenticatedPage.getByRole('button', {
      name: 'Enviar respostas',
    })
    await expect(submitButton).toBeVisible()
    await submitButton.click()

    await expect(authenticatedPage).toHaveURL(
      new RegExp(`${ids.activityId}/attempts/${ids.attemptId}$`),
    )
    expect(previewCalls).toBe(2)

    const resultSummary = authenticatedPage
      .locator('summary')
      .filter({ hasText: 'Questão 1 · Tradução · Parcialmente correta' })
    await expect(resultSummary).toBeVisible()
    await resultSummary.click()
    await expect(authenticatedPage.getByText(submittedText)).toBeVisible()
    await expect(authenticatedPage.getByText(REFERENCE_TRANSLATION)).not.toBeVisible()
  })
})

const IMAGE_CHOICE_OPTIONS = [
  {
    key: 'opt-3f9a21c4b07d',
    imagePath: '/curriculum/images/2d165276ed215938.webp',
    description: 'Fatias brancas e firmes, sem brilho, espalhadas na frigideira escura.',
  },
  {
    key: 'opt-b07d5e185c1e',
    imagePath: '/curriculum/images/51de9b1cc23dd653.webp',
    description: 'Fatias claras e translúcidas, com as bordas ainda frescas.',
  },
  {
    key: 'opt-5c1e9a7391c7',
    imagePath: '/curriculum/images/5c8a6a6b47848a6f.webp',
    description: 'Tiras marrons, macias e brilhantes, bem misturadas.',
  },
  {
    key: 'opt-91c7d3fa0a6b',
    imagePath: '/curriculum/images/655fecc77404ac40.webp',
    description: 'Fatias escuras, com anéis enrolados e bordas pretas.',
  },
] as const

const IMAGE_CHOICE_VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 1080 },
  { name: 'mobile', width: 390, height: 844 },
] as const

for (const viewport of IMAGE_CHOICE_VIEWPORTS) {
  test(`selects, verifies, locks and submits an image choice question on ${viewport.name}`, async ({
    authenticatedPage,
    bff,
  }) => {
    const imageActivity = {
      ...activity,
      activityRevision: 'image-revision-1',
      title: 'Ponto de cocção',
      difficulty: 'easy' as const,
      questions: [
        {
          key: 'image-1',
          kind: 'image_choice' as const,
          prompt: 'Qual destas cebolas está caramelizada?',
          options: IMAGE_CHOICE_OPTIONS,
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
      if (payload.includes('submissionKey')) {
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
      if (payload.includes('questionKey')) {
        await route.fulfill({
          body: JSON.stringify({
            result: {
              status: 'conclusive',
              score: 0,
              isCorrect: false,
              optionFeedback: 'Essa cebola passou do ponto e queimou.',
              explanation: 'Revise a cor e a textura da cebola.',
            },
          }),
          contentType: 'application/json',
        })
        return
      }
      await route.fulfill({
        body: JSON.stringify({ result: imageActivity }),
        contentType: 'application/json',
      })
    })

    await authenticatedPage.setViewportSize({
      width: viewport.width,
      height: viewport.height,
    })
    await navigateAuthenticatedPage(authenticatedPage, activityPath)
    const group = authenticatedPage.getByRole('radiogroup', {
      name: 'Qual destas cebolas está caramelizada?',
    })
    await expect(group).toBeVisible()
    await expect(authenticatedPage.getByRole('radio')).toHaveCount(4)
    await expect(
      authenticatedPage.getByRole('button', { name: 'Verificar' }),
    ).toBeDisabled()

    // The four static photos load from their opaque curricular paths.
    await expect
      .poll(() =>
        authenticatedPage.evaluate(() =>
          [...document.querySelectorAll('img')].map(
            (image) => image.complete && image.naturalWidth > 0,
          ),
        ),
      )
      .toEqual([true, true, true, true])
    await expect(authenticatedPage.getByRole('img')).toHaveCount(0)
    await expect(
      authenticatedPage.getByRole('radio', { name: 'Opção 3' }),
    ).toHaveAccessibleDescription(IMAGE_CHOICE_OPTIONS[2].description)

    const cards = authenticatedPage.locator('label.image-choice-card')
    const boxes = await cards.evaluateAll((elements) =>
      elements.map((element) => {
        const { x, y, width, height } = element.getBoundingClientRect()
        return { x, y, width, height }
      }),
    )
    expect(boxes).toHaveLength(4)
    if (viewport.name === 'desktop') {
      expect(new Set(boxes.map((box) => Math.round(box.y))).size).toBe(1)
    } else {
      expect(Math.round(boxes[0].y)).toBe(Math.round(boxes[1].y))
      expect(Math.round(boxes[2].y)).toBe(Math.round(boxes[3].y))
      expect(boxes[2].y).toBeGreaterThan(boxes[0].y)
      for (const box of boxes) expect(box.height).toBeGreaterThanOrEqual(44)
    }

    // Click, then arrows, then click again: the choice changes freely before verifying.
    await cards.nth(0).click()
    await expect(authenticatedPage.getByRole('radio', { name: 'Opção 1' })).toBeChecked()
    await authenticatedPage.keyboard.press('ArrowRight')
    await expect(authenticatedPage.getByRole('radio', { name: 'Opção 2' })).toBeChecked()
    await expect(authenticatedPage.getByText('Selecionada')).toHaveCount(1)
    await cards.nth(3).click()
    await expect(authenticatedPage.getByRole('radio', { name: 'Opção 4' })).toBeChecked()
    await authenticatedPage.screenshot({
      path: `.playwright-cli/screenshots/shifu-131-image-choice-selection-${viewport.name}.png`,
      fullPage: true,
      animations: 'disabled',
    })

    if (viewport.name === 'desktop') {
      for (const width of IMAGE_CHOICE_FOOTER_WIDTHS) {
        await authenticatedPage.setViewportSize({ width, height: viewport.height })
        await expectImageChoiceFootersContained(authenticatedPage)
      }
      await authenticatedPage.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      })
    }

    await authenticatedPage.getByRole('button', { name: 'Verificar' }).click()
    await expect(
      authenticatedPage.getByRole('heading', { name: 'Resposta incorreta' }),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByText('Essa cebola passou do ponto e queimou.'),
    ).toBeVisible()
    await expect(
      authenticatedPage.getByText(
        'Retorno provisório. O resultado oficial aparece ao enviar a Atividade.',
      ),
    ).toBeVisible()
    for (const radio of await authenticatedPage.getByRole('radio').all())
      await expect(radio).toBeDisabled()
    await expect(authenticatedPage.getByRole('radio', { name: 'Opção 4' })).toBeChecked()
    await expect(authenticatedPage.locator('[data-tone="incorrect"]')).toHaveCount(1)
    await expect(authenticatedPage.locator('[data-tone="correct"]')).toHaveCount(0)
    await expect(authenticatedPage.getByText('Sua resposta')).toHaveCount(1)
    expect(
      await authenticatedPage.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true)
    await authenticatedPage.screenshot({
      path: `.playwright-cli/screenshots/shifu-131-image-choice-incorrect-${viewport.name}.png`,
      fullPage: true,
      animations: 'disabled',
    })

    if (viewport.name === 'desktop') {
      for (const width of IMAGE_CHOICE_FOOTER_WIDTHS) {
        await authenticatedPage.setViewportSize({ width, height: viewport.height })
        await expectImageChoiceFootersContained(authenticatedPage)
      }
      await authenticatedPage.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      })
    }

    expect(requests.some((payload) => payload.includes('image_choice'))).toBe(true)
    expect(
      requests.some(
        (payload) =>
          payload.includes('questionKey') &&
          payload.includes(IMAGE_CHOICE_OPTIONS[3].key),
      ),
    ).toBe(true)

    await authenticatedPage.getByRole('button', { name: 'Enviar atividade' }).click()
    await expect(authenticatedPage).toHaveURL(new RegExp(`${ids.attemptId}/?$`))
    expect(
      requests.some(
        (payload) =>
          payload.includes('submissionKey') &&
          payload.includes(IMAGE_CHOICE_OPTIONS[3].key),
      ),
    ).toBe(true)
  })
}

test.describe('Image choice routed REST transport', () => {
  const imageWire = {
    key: 'image-1',
    kind: 'image_choice',
    prompt: 'Qual destas cebolas está caramelizada?',
    options: IMAGE_CHOICE_OPTIONS.map((option) => ({
      key: option.key,
      image_path: option.imagePath,
      description: option.description,
    })),
  }
  const previewPath = `${activityPath}/questions/image-1/preliminary-evaluations`
  const activityWire = (overrides: Record<string, unknown>) => ({
    activity_id: ids.activityId,
    competency_id: ids.competencyId,
    title: 'Ponto de cocção',
    type: 'practice',
    difficulty: 'easy',
    questions: [imageWire],
    latest_attempt_id: null,
    can_submit: true,
    activity_revision: 'image-transport',
    ...overrides,
  })

  // The BFF mapping runs for real; only the upstream bodies are faked.
  test('maps the learning payload and the preliminary feedback from the HTTP wire', async ({
    page,
    request,
    activeAccount,
  }) => {
    const transport = GamificationTransportFixture(request, activeAccount.accountId)
    await transport.register({
      [activityPath]: { body: activityWire({}) },
      [previewPath]: {
        body: {
          status: 'conclusive',
          score: 0,
          is_correct: false,
          explanation: 'Revise a cor e a textura da cebola.',
          option_feedback: 'Essa cebola passou do ponto e queimou.',
        },
      },
    })
    try {
      const signIn = await page.request.post('/api/auth/sign-in/identity', {
        data: { email: activeAccount.email, password: signInPassword },
        headers: { 'x-forwarded-for': activeAccount.ipAddress },
      })
      expect(signIn.status()).toBe(200)
      await page.goto(activityPath)

      await expect(page.getByRole('radio')).toHaveCount(4)
      const sources = await page
        .locator('label.image-choice-card img')
        .evaluateAll((images) => images.map((image) => image.getAttribute('src')))
      expect(sources).toEqual(IMAGE_CHOICE_OPTIONS.map((option) => option.imagePath))
      await expect(
        page.getByRole('radio', { name: 'Opção 3' }),
      ).toHaveAccessibleDescription(IMAGE_CHOICE_OPTIONS[2].description)
      // The learning payload carries no answer: nothing is marked before verifying.
      await expect(page.locator('[data-tone="correct"]')).toHaveCount(0)

      await page.locator('label.image-choice-card').nth(3).click()
      await page.getByRole('button', { name: 'Verificar' }).click()
      await expect(
        page.getByRole('heading', { name: 'Resposta incorreta' }),
      ).toBeVisible()
      await expect(page.getByText('Essa cebola passou do ponto e queimou.')).toBeVisible()
      await expect(page.getByText('Revise a cor e a textura da cebola.')).toBeVisible()
      await expect(page.locator('[data-tone="correct"]')).toHaveCount(0)

      const observed = await transport.observations()
      expect(observed.filter((entry) => entry.path === activityPath)).toEqual(
        expect.arrayContaining([expect.objectContaining({ method: 'GET', status: 200 })]),
      )
      expect(observed.filter((entry) => entry.path === previewPath)).toEqual(
        expect.arrayContaining([
          expect.objectContaining({ method: 'POST', status: 200 }),
        ]),
      )
    } finally {
      await transport.dispose()
    }
  })

  for (const scenario of [
    {
      name: 'rejects an image choice question inside a diagnostic Activity',
      questions: [imageWire],
      extra: { is_diagnostic: true },
    },
    {
      name: 'rejects a question of an unknown kind',
      questions: [{ key: 'mystery-1', kind: 'mystery', prompt: 'Qual?' }],
      extra: {},
    },
  ]) {
    test(`${scenario.name} without rendering the Activity`, async ({
      page,
      request,
      activeAccount,
    }) => {
      const transport = GamificationTransportFixture(request, activeAccount.accountId)
      await transport.register({
        [activityPath]: {
          body: activityWire({ questions: scenario.questions, ...scenario.extra }),
        },
      })
      try {
        const signIn = await page.request.post('/api/auth/sign-in/identity', {
          data: { email: activeAccount.email, password: signInPassword },
          headers: { 'x-forwarded-for': activeAccount.ipAddress },
        })
        expect(signIn.status()).toBe(200)
        await page.goto(activityPath)

        await expect(
          page.getByRole('heading', { name: 'Não foi possível carregar esta Atividade' }),
        ).toBeVisible()
        await expect(page.getByRole('radio')).toHaveCount(0)
        await expect(page.locator('img[src^="/curriculum/images/"]')).toHaveCount(0)
        await expect(page.getByRole('button', { name: 'Verificar' })).toHaveCount(0)
        expect(
          (await transport.observations()).filter((entry) => entry.path === activityPath),
        ).toEqual(
          expect.arrayContaining([
            expect.objectContaining({ method: 'GET', status: 200 }),
          ]),
        )
      } finally {
        await transport.dispose()
      }
    })
  }
})
