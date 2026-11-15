import { LearningRouteIdsFaker } from '@/core/learning/fakers'
import { installControlledDictation } from '../support/native-dictation'
import { expect, navigateAuthenticatedPage, test } from '../playwright'

const ids = LearningRouteIdsFaker.fake()
const activityPath = `/learning/goals/${ids.goalId}/skills/${ids.skillId}/competencies/${ids.competencyId}/activities/${ids.activityId}`

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
