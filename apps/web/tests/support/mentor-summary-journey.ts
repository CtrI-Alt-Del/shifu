import type { Locator, Page, Route } from '@playwright/test'

import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage } from '../playwright'

/**
 * Controlled Mentor backend for the SHIFU-102 summary journeys. It proves rendered
 * contracts and the outgoing server-function requests, not real auth or persistence.
 */
const SESSION_ID = '01J7T8AC91Z5K8M4JQ8C2D6F1A'
const ATTEMPT_ID = '01J7T8AC91Z5K8M4JQ8C2D6F1B'
const SESSION_TITLE = 'Dúvida no laço for'
const SUMMARY_TEXT =
  'Nesta conversa, os assuntos foram range e lista. Você perguntou: “Meu laço não mostra o último item da lista. O que esqueci?” O Mentor orientou: “Veja quais índices range produz e compare com o tamanho da lista.”'
const SUMMARIZING_LABEL = 'Resumindo contexto…'
const SUMMARIZING_PLACEHOLDER = 'Aguarde enquanto o contexto é resumido'
const FAILURE_LABEL =
  'Não foi possível resumir o contexto. O histórico completo continua disponível.'

type Surface = 'page' | 'fab'
type Phase = 'summarizing' | 'summarized' | 'failed'

export type MentorServerFunctionCall = {
  exportName: string
  method: string
  data: Record<string, unknown>
}

function message(
  id: string,
  role: 'learner' | 'mentor',
  content: string,
  createdAt: string,
  inReplyToMessageId: string | null = null,
) {
  return {
    id,
    sessionId: SESSION_ID,
    role,
    content,
    createdAt,
    inReplyToMessageId,
    attachments: [],
  }
}

const FIRST = message(
  'FIRST',
  'learner',
  'Meu laço não mostra o último item da lista. O que esqueci?',
  '2026-10-18T12:00:00Z',
)
const FIRST_ANSWER = message(
  'FIRSTANSWER',
  'mentor',
  'Veja quais índices range produz e compare com o tamanho da lista.',
  '2026-10-18T12:01:00Z',
  'FIRST',
)
const SECOND = message(
  'SECOND',
  'learner',
  'Pode mostrar os índices de uma lista com 5 itens?',
  '2026-10-18T12:02:00Z',
)
const BOUNDARY = message(
  'BOUNDARY',
  'mentor',
  'Com cinco itens, range(5) produz os índices de 0 a 4.',
  '2026-10-18T12:03:00Z',
  'SECOND',
)
const PENDING = message(
  'PENDING',
  'learner',
  'Então por que o último item da lista não aparece?',
  '2026-10-18T12:04:00Z',
)
const ANSWER = message(
  'ANSWER',
  'mentor',
  'O limite final de range fica de fora.',
  '2026-10-18T12:05:00Z',
  'PENDING',
)

function serverFnExport(url: string): string | null {
  const segment = new URL(url).pathname.split('/_serverFn/')[1]
  if (!segment) return null
  try {
    const descriptor = JSON.parse(
      Buffer.from(decodeURIComponent(segment), 'base64').toString('utf-8'),
    ) as { export?: unknown }
    return typeof descriptor.export === 'string' ? descriptor.export : null
  } catch {
    return null
  }
}

function decodeServerFunctionValue(value: unknown): unknown {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return value
  const record = value as Record<string, unknown>
  if (typeof record.t !== 'number') return value
  if (record.t === 1) return record.s
  if (record.t === 2) return undefined
  if (record.t === 10) {
    const properties = record.p as { k?: unknown; v?: unknown } | undefined
    if (!Array.isArray(properties?.k) || !Array.isArray(properties?.v)) return value
    const values = properties.v
    return Object.fromEntries(
      properties.k.map((key, index) => [
        String(key),
        decodeServerFunctionValue(values[index]),
      ]),
    )
  }
  return value
}

function unwrapServerFunctionInput(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return {}
  const record = value as Record<string, unknown>
  for (const key of ['data', 'input', 'json', 'payload']) {
    const nested = record[key]
    if (typeof nested === 'object' && nested !== null && !Array.isArray(nested))
      return unwrapServerFunctionInput(nested)
  }
  return record
}

function serverFnInput(request: { url: () => string }): Record<string, unknown> {
  const url = new URL(request.url())
  for (const value of url.searchParams.values()) {
    try {
      const serialized = JSON.parse(value) as { t?: unknown }
      const input = unwrapServerFunctionInput(
        decodeServerFunctionValue(serialized.t ? serialized.t : serialized),
      )
      if (Object.keys(input).length) return input
    } catch {
      // Preserve ordinary query parameters below.
    }
  }
  return Object.fromEntries(url.searchParams.entries())
}

function sseEvent(sequence: number, overrides: Record<string, unknown>) {
  const data = {
    session_id: SESSION_ID,
    attempt_id: ATTEMPT_ID,
    sequence,
    kind: 'status',
    status: 'processing',
    block: null,
    consultation: null,
    progress: null,
    failure_code: null,
    created_at: '2026-10-18T12:05:00Z',
    ...overrides,
  }
  return `id: ${sequence}\nevent: mentor.response\ndata: ${JSON.stringify(data)}\n\n`
}

export async function installMentorSummaryBackend(
  page: Page,
  initialPhase: Phase,
): Promise<{
  calls: MentorServerFunctionCall[]
  releaseSummarization: () => void
}> {
  const calls: MentorServerFunctionCall[] = []
  let phase = initialPhase
  let release: () => void = () => undefined
  const released = new Promise<void>((resolve) => {
    release = resolve
  })
  const session = {
    id: SESSION_ID,
    title: SESSION_TITLE,
    createdAt: '2026-10-18T12:00:00Z',
    updatedAt: '2026-10-18T12:05:00Z',
    lastActivityAt: '2026-10-18T12:05:00Z',
  }

  function detail(cursor: unknown) {
    const summary =
      phase === 'summarized'
        ? {
            current: {
              version: 2,
              boundaryMessageId: BOUNDARY.id,
              coveredMessageCount: 21,
              completedAt: '2026-10-18T14:00:00Z',
            },
            failureAfterMessageId: null,
          }
        : {
            current: null,
            failureAfterMessageId: phase === 'failed' ? PENDING.id : null,
          }
    const pages: Record<string, { items: unknown[]; nextCursor: string | null }> = {
      first: {
        items: phase === 'summarizing' ? [PENDING] : [PENDING, ANSWER],
        nextCursor: 'older-1',
      },
      'older-1': { items: [SECOND, BOUNDARY], nextCursor: 'older-2' },
      'older-2': { items: [FIRST, FIRST_ANSWER], nextCursor: null },
    }
    return {
      session,
      messages: pages[typeof cursor === 'string' ? cursor : 'first'],
      pendingLearnerMessageId: phase === 'summarizing' ? PENDING.id : null,
      response:
        phase === 'summarizing'
          ? {
              attemptId: ATTEMPT_ID,
              learnerMessageId: PENDING.id,
              status: 'processing',
              blocks: [],
              consultations: [],
              lastSequence: 1,
              failureCode: null,
              progress: 'summarize-context',
            }
          : null,
      summary,
    }
  }

  async function fulfillJson(route: Route, result: unknown) {
    await route.fulfill({
      body: JSON.stringify({ result }),
      contentType: 'application/json',
      status: 200,
    })
  }

  await page.route(
    /\/api\/intelligence\/mentor-sessions\/[^/]+\/events/,
    async (route) => {
      await released
      phase = 'summarized'
      await route.fulfill({
        body: [
          sseEvent(2, { progress: null }),
          sseEvent(3, { kind: 'completed', status: 'completed' }),
        ].join(''),
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-store' },
        status: 200,
      })
    },
  )
  await page.route('**/_serverFn/**', async (route) => {
    const request = route.request()
    const exportName = serverFnExport(request.url()) ?? ''
    const data = serverFnInput(request)
    if (exportName.startsWith('getAchievements_')) {
      await fulfillJson(route, {
        kind: 'success',
        overview: { level: 1, totalXp: 0, xpForNextLevel: 100, achievements: [] },
      })
      return
    }
    if (exportName.includes('listMentorSessionsServer')) {
      await fulfillJson(route, { items: [session], nextCursor: null })
      return
    }
    if (exportName.includes('getMentorSessionSummaryServer')) {
      calls.push({ exportName, method: request.method(), data })
      await fulfillJson(route, {
        version: 2,
        text: SUMMARY_TEXT,
        coveredMessageCount: 21,
        firstMessageId: FIRST.id,
      })
      return
    }
    if (exportName.includes('getMentorSessionServer')) {
      calls.push({ exportName, method: request.method(), data })
      await fulfillJson(route, detail(data.cursor))
      return
    }
    await route.fallback()
  })
  return { calls, releaseSummarization: release }
}

export async function openMentorConversation(page: Page, surface: Surface) {
  if (surface === 'page') {
    await navigateAuthenticatedPage(page, ROUTES.intelligence)
    await expect(
      page.getByRole('heading', { level: 1, name: 'Nova conversa' }),
    ).toBeVisible()
    await page.evaluate((sessionId) => {
      const router = (
        window as typeof window & {
          __TSR_ROUTER__: {
            navigate: (options: {
              to: string
              search: { session: string }
            }) => Promise<void>
          }
        }
      ).__TSR_ROUTER__
      return router.navigate({ to: '/intelligence', search: { session: sessionId } })
    }, SESSION_ID)
  } else {
    await navigateAuthenticatedPage(page, ROUTES.gamification)
    await page.getByRole('button', { name: 'Abrir Mentor' }).click()
    await page.getByRole('button', { name: 'Histórico de conversas' }).click()
    await page.getByRole('button', { name: SESSION_TITLE, exact: true }).click()
  }
  await expect(page.getByRole('heading', { level: 1, name: SESSION_TITLE })).toBeVisible()
}

function messageList(page: Page): Locator {
  return page.getByRole('list', { name: 'Mensagens da conversa' })
}

async function listTexts(page: Page): Promise<string[]> {
  return messageList(page).getByRole('listitem').allTextContents()
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)
}

async function expectFocusInside(container: Locator) {
  await expect
    .poll(() => container.evaluate((element) => element.contains(document.activeElement)))
    .toBe(true)
}

export async function expectSummarizingState(
  page: Page,
  surface: Surface,
  width: number,
) {
  const form = page.getByRole('form', { name: 'Enviar mensagem ao Mentor' })
  await expect(
    page.getByRole('status').filter({ hasText: SUMMARIZING_LABEL }),
  ).toBeVisible()
  await expect(page.getByRole('button', { name: 'Ver resumo' })).toHaveCount(0)
  await expect(form.getByRole('textbox')).toBeDisabled()
  await expect(form.getByRole('textbox')).toHaveAttribute(
    'placeholder',
    SUMMARIZING_PLACEHOLDER,
  )
  await expect(page.getByRole('button', { name: 'Cancelar resposta' })).toBeVisible()
  await expect(page.getByText(PENDING.content)).toBeVisible()
  await expectNoHorizontalOverflow(page)
  await page.screenshot({
    path: `.playwright-cli/screenshots/shifu-102-${surface}-${width}-summarizing.png`,
  })
}

export async function exerciseSummaryJourney(
  page: Page,
  surface: Surface,
  width: number,
) {
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 })
  const { calls, releaseSummarization } = await installMentorSummaryBackend(
    page,
    'summarizing',
  )
  await openMentorConversation(page, surface)
  await expectSummarizingState(page, surface, width)

  releaseSummarization()
  const trigger = page.getByRole('button', { name: 'Ver resumo' })
  await expect(trigger).toBeVisible()
  await expect(page.getByText(SUMMARIZING_LABEL)).toHaveCount(0)
  await expect(
    page.getByRole('textbox', { name: 'Escreva sua mensagem para o Mentor' }),
  ).toBeEnabled()
  await expect(trigger).toHaveAttribute('aria-haspopup', 'dialog')
  // The marker follows its boundary message, or leads the list while that message is
  // still in an unloaded older page (small viewports may auto-load that page first).
  const loadedTexts = await listTexts(page)
  const markerIndex = loadedTexts.findIndex((text) => text.includes('Contexto resumido'))
  expect(markerIndex).toBeGreaterThanOrEqual(0)
  if (markerIndex === 0) expect(loadedTexts[1]).toContain(PENDING.content)
  else expect(loadedTexts[markerIndex - 1]).toContain(BOUNDARY.content)
  await page.screenshot({
    path: `.playwright-cli/screenshots/shifu-102-${surface}-${width}-summarized.png`,
  })

  const dialog = page.getByRole('dialog', { name: 'Resumo desta conversa' })
  await trigger.focus()
  await page.keyboard.press('Enter')
  await expect(dialog).toBeVisible()
  await expect(dialog).toContainText('Suas mensagens originais continuam disponíveis.')
  await expect(dialog).toContainText(SUMMARY_TEXT)
  await expect(
    dialog.getByRole('button', { name: 'Ver mensagens originais' }),
  ).toBeEnabled()
  await expectFocusInside(dialog)
  const summaryCall = calls.find((call) =>
    call.exportName.includes('getMentorSessionSummaryServer'),
  )
  expect(summaryCall).toMatchObject({ method: 'GET', data: { sessionId: SESSION_ID } })
  for (let step = 0; step < 6; step += 1) {
    await page.keyboard.press('Tab')
    await expectFocusInside(dialog)
  }
  await expectDialogLayout(page, dialog, surface, width)
  await page.screenshot({
    path: `.playwright-cli/screenshots/shifu-102-${surface}-${width}-dialog.png`,
  })

  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(trigger).toBeFocused()
  if (surface === 'fab')
    await expect(page.getByRole('dialog', { name: 'Painel do Mentor' })).toBeVisible()

  await trigger.click()
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: 'Fechar resumo' }).click()
  await expect(dialog).toHaveCount(0)
  await expect(trigger).toBeFocused()

  await trigger.click()
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: 'Fechar', exact: true }).click()
  await expect(dialog).toHaveCount(0)
  await expect(trigger).toBeFocused()

  await trigger.click()
  await dialog.getByRole('button', { name: 'Ver mensagens originais' }).click()
  await expect(dialog).toHaveCount(0)
  const first = page.locator(`[data-message-id="${FIRST.id}"]`)
  await expect(first).toBeVisible()
  await expect(first).toBeFocused()
  const pagedCursors = calls
    .filter((call) => call.exportName.includes('getMentorSessionServer'))
    .map((call) => call.data.cursor)
    .filter(Boolean)
  expect(pagedCursors).toEqual(['older-1', 'older-2'])
  const texts = await listTexts(page)
  const expectedOrder = [
    FIRST.content,
    FIRST_ANSWER.content,
    SECOND.content,
    BOUNDARY.content,
    'Contexto resumido',
    PENDING.content,
    ANSWER.content,
  ]
  expect(texts).toHaveLength(expectedOrder.length)
  expectedOrder.forEach((content, index) => {
    expect(texts[index]).toContain(content)
  })
  await expectNoHorizontalOverflow(page)
  await page.screenshot({
    path: `.playwright-cli/screenshots/shifu-102-${surface}-${width}-originals.png`,
  })
}

async function expectDialogLayout(
  page: Page,
  dialog: Locator,
  surface: Surface,
  width: number,
) {
  await dialog.evaluate((element) =>
    Promise.all(element.getAnimations().map((animation) => animation.finished)),
  )
  const box = await dialog.boundingBox()
  if (!box) throw new Error('The summary dialog has no layout box')
  await expectNoHorizontalOverflow(page)
  if (width === 390) {
    expect(Math.abs(box.x - 16)).toBeLessThanOrEqual(1)
    expect(Math.abs(width - (box.x + box.width) - 16)).toBeLessThanOrEqual(1)
    for (const name of ['Ver mensagens originais', 'Fechar resumo']) {
      const button = await dialog.getByRole('button', { name }).boundingBox()
      expect(button?.height).toBeGreaterThanOrEqual(44)
      expect(button?.width).toBeGreaterThan(box.width / 2)
    }
  } else {
    expect(box.width).toBeLessThanOrEqual(512 + 1)
    expect(Math.abs(box.x + box.width / 2 - width / 2)).toBeLessThanOrEqual(2)
  }
  if (surface === 'fab') {
    const isOnTop = await dialog.evaluate((element) => {
      const rect = element.getBoundingClientRect()
      const hit = document.elementFromPoint(
        rect.left + rect.width / 2,
        rect.top + rect.height / 2,
      )
      return Boolean(hit && element.contains(hit))
    })
    expect(isOnTop).toBe(true)
  }
}

export async function exerciseSummaryFailure(page: Page, surface: Surface) {
  await page.setViewportSize({ width: 1440, height: 900 })
  await installMentorSummaryBackend(page, 'failed')
  await openMentorConversation(page, surface)
  const texts = await listTexts(page)
  expect(texts[0]).toContain(PENDING.content)
  expect(texts[1]).toContain(FAILURE_LABEL)
  await expect(page.getByRole('button', { name: 'Ver resumo' })).toHaveCount(0)
  await expect(page.getByText(SUMMARIZING_LABEL)).toHaveCount(0)
  await page.screenshot({
    path: `.playwright-cli/screenshots/shifu-102-${surface}-failure.png`,
  })
}
