import type { APIRequestContext, Locator, Page } from '@playwright/test'

import type { AiQuotaUsage } from '@/core/intelligence/ai-quota-usage'
import { AiQuotaUsageFaker } from '@/core/intelligence/fakers/ai-quota-usage-faker'
import type { SignInHandlerAccount } from '../fixtures/identity-module-fixture'
import { expect, signInPassword } from '../playwright'
import {
  ATTEMPT_ID,
  CONVERSATION_TEXTS,
  MESSAGE_IDS,
  SESSION_ID,
  SESSION_TITLE,
  serverFnExport,
} from './mentor-memories-backend'

/**
 * Support for the AI quota browser suites (SHIFU-118).
 *
 * Two kinds of transport are used on purpose:
 * - a mocked `_serverFn` for the quota reading and for widget states that only need
 *   a reading, as the other suites do;
 * - the controlled upstream `identity-account-upstream.mjs`, which refuses the AI
 *   start routes of one real account with 429 `ai_quota_exhausted` and passes every
 *   other request to the real API, so the real server functions and their error
 *   classification run.
 */
export const AI_QUOTA_ACCOUNT_ID = 'playwright-account'
export const AI_QUOTA_RENEWAL_LABEL = '1º de dezembro de 2026'
/** Each surface names what comes back on renewal, as the Penpot boards do. */
export const AI_QUOTA_MENTOR_BLOCKED_MESSAGE = `Sua cota de IA acabou. Novas mensagens e novas tentativas voltam em ${AI_QUOTA_RENEWAL_LABEL}. Seu histórico continua disponível.`
export const AI_QUOTA_HOME_BLOCKED_MESSAGE = `Sua cota de IA acabou. O planejamento com IA volta em ${AI_QUOTA_RENEWAL_LABEL}. Você pode criar um Objetivo manualmente agora.`
export const AI_QUOTA_PLANNER_FAILURE_BLOCKED_MESSAGE = `Sua cota de IA acabou. Novas tentativas voltam em ${AI_QUOTA_RENEWAL_LABEL}. Você ainda pode cancelar e criar um Objetivo manualmente.`
export const AI_QUOTA_PLANNER_PROPOSAL_BLOCKED_MESSAGE = `Sua cota de IA acabou. Reiniciar o planejamento volta em ${AI_QUOTA_RENEWAL_LABEL}. Você ainda pode criar este Objetivo agora.`
/** The usage warning of the Mentor, at 85%. */
export const AI_QUOTA_WARNING_MESSAGE = `Você já usou 85% da sua cota de IA deste mês. Quando ela acabar, o Mentor e o planejamento assistido pausam até ${AI_QUOTA_RENEWAL_LABEL}.`

/** The quota month is the month before the renewal date, `2026-12-01` renews November. */
export function aiQuotaDismissalKey(accountId: string, monthKey = '2026-11') {
  return `shifu:ai-quota-warning-dismissed:${accountId}:${monthKey}`
}

export function aiQuotaUsageOf(percentage: number): AiQuotaUsage {
  const status =
    percentage >= 100 ? 'blocked' : percentage >= 80 ? 'near_limit' : 'normal'
  return AiQuotaUsageFaker.fake({ status, percentage })
}

export type AiQuotaReading = number | 'unavailable'

export type AiQuotaReadingBackend = {
  /** How many times the page asked for the reading. */
  reads: () => number
  /** Changes what the next reading answers; the page keeps what it already read. */
  setReading: (reading: AiQuotaReading) => void
  /** Waits for the first reading and until none is in flight, so a change cannot race a mount refetch. */
  settled: () => Promise<void>
}

/** Mocks the quota reading server function; every other server function falls through. */
export async function installAiQuotaReading(
  page: Page,
  initial: AiQuotaReading,
  accountId = AI_QUOTA_ACCOUNT_ID,
): Promise<AiQuotaReadingBackend> {
  let current = initial
  let reads = 0
  let inFlight = 0
  await page.route('**/_serverFn/**', async (route) => {
    if (
      !(serverFnExport(route.request().url()) ?? '').startsWith('getAiQuotaUsageServer')
    ) {
      await route.fallback()
      return
    }
    reads += 1
    inFlight += 1
    try {
      if (current === 'unavailable') {
        await route.fulfill({
          body: JSON.stringify({ error: 'Internal Server Error' }),
          contentType: 'application/json',
          status: 500,
        })
        return
      }
      await route.fulfill({
        body: JSON.stringify({ result: { usage: aiQuotaUsageOf(current), accountId } }),
        contentType: 'application/json',
        status: 200,
      })
    } finally {
      inFlight -= 1
    }
  })
  return {
    reads: () => reads,
    setReading: (reading) => {
      current = reading
    },
    settled: async () => {
      await expect
        .poll(async () => {
          const readsBefore = reads
          await new Promise((resolve) => setTimeout(resolve, 300))
          return reads > 0 && inFlight === 0 && reads === readsBefore
        })
        .toBe(true)
    },
  }
}

/** Counts the server function POSTs by export name prefix, mocked or not. */
export function recordServerFunctionCalls(page: Page) {
  const exportNames: string[] = []
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().includes('/_serverFn/'))
      exportNames.push(serverFnExport(request.url()) ?? '')
  })
  return {
    callsTo: (prefix: string) =>
      exportNames.filter((exportName) => exportName.startsWith(prefix)).length,
  }
}

/** A real Better Auth session for a seeded account, so server functions reach the real API. */
export async function signInRealAccount(page: Page, account: SignInHandlerAccount) {
  const response = await page.request.post('/api/auth/sign-in/identity', {
    data: { email: account.email, password: signInPassword },
    headers: { 'x-forwarded-for': account.ipAddress },
  })
  expect(response.status()).toBe(200)
}

/** Opens a route with a document load and waits for hydration, like the base fixture. */
export async function openRealPage(page: Page, path: string) {
  await page.goto(path)
  await page.waitForFunction(() => '__TSR_ROUTER__' in window, null, {
    timeout: 30_000,
  })
  await page.waitForFunction(() => document.body.dataset.hydrated === 'true', null, {
    timeout: 30_000,
  })
}

/**
 * The per-account quota-exhausted scenario of the controlled upstream. While it is
 * enabled, the account's Mentor create/send/retry and planning start/restart/retry
 * requests answer 429 `ai_quota_exhausted`.
 */
export async function AiQuotaUpstreamFixture(
  request: APIRequestContext,
  accountId: string,
) {
  const port = process.env.SHIFU_ACCOUNT_TEST_PROXY_PORT
  if (!port)
    throw new Error(
      'The AI quota scenario requires SHIFU_ACCOUNT_TEST_PROXY_PORT from playwright.config.ts',
    )
  const controlURL = `http://127.0.0.1:${port}/__account-control/${accountId}`
  const enabled = await request.post(controlURL, {
    data: { scenario: 'ai-quota-exhausted' },
  })
  if (!enabled.ok()) throw new Error('Could not enable the AI quota upstream scenario')

  /** Refused requests by `METHOD path`, as the upstream saw them. */
  async function hits(): Promise<Record<string, number>> {
    const response = await request.get(controlURL)
    if (!response.ok()) throw new Error('Could not read the AI quota upstream hits')
    return (await response.json()).hits
  }
  async function dispose() {
    await request.delete(controlURL)
  }
  return { hits, dispose }
}

/** A blocked control stays visible and focusable, ignores clicks and points at the card. */
export async function expectBlockedControl(control: Locator, cardId: string) {
  await expect(control).toBeVisible()
  await expect(control).toHaveAttribute('aria-disabled', 'true')
  await expect(control).toHaveAttribute('aria-describedby', cardId)
  await control.focus()
  await expect(control).toBeFocused()
}

/** Playwright refuses to click an aria-disabled element, so the click is forced. */
export async function clickIgnoringDisabled(control: Locator) {
  await control.click({ force: true })
}

/**
 * Asserts the settled size of a control. Entrance animations can leave a transient
 * sub-pixel scale (for example 43.99997 px), so the box is polled until it settles.
 */
export async function expectBox(
  control: Locator,
  minimum: { width?: number; height?: number },
) {
  if (minimum.width) {
    await expect
      .poll(async () => (await control.boundingBox())?.width ?? 0)
      .toBeGreaterThanOrEqual(minimum.width)
  }
  if (minimum.height) {
    await expect
      .poll(async () => (await control.boundingBox())?.height ?? 0)
      .toBeGreaterThanOrEqual(minimum.height)
  }
}

type MentorResponseFixture = 'completed' | 'failed'

function mentorConversation(response: MentorResponseFixture) {
  const session = {
    id: SESSION_ID,
    title: SESSION_TITLE,
    createdAt: '2026-10-08T15:00:00Z',
    updatedAt: '2026-10-08T15:00:02Z',
    lastActivityAt: '2026-10-08T15:00:02Z',
  }
  const learner = {
    id: MESSAGE_IDS.latestQuestion,
    sessionId: SESSION_ID,
    role: 'learner',
    content: CONVERSATION_TEXTS.latestQuestion,
    createdAt: '2026-10-08T15:00:00Z',
    inReplyToMessageId: null,
    attachments: [],
  }
  const answer = {
    id: MESSAGE_IDS.latestAnswer,
    sessionId: SESSION_ID,
    role: 'mentor',
    content: CONVERSATION_TEXTS.answer,
    createdAt: '2026-10-08T15:00:02Z',
    inReplyToMessageId: MESSAGE_IDS.latestQuestion,
    attachments: [],
  }
  const failed = response === 'failed'
  return {
    session,
    detail: {
      session,
      messages: { items: failed ? [learner] : [learner, answer], nextCursor: null },
      pendingLearnerMessageId: failed ? learner.id : null,
      response: failed
        ? {
            attemptId: ATTEMPT_ID,
            learnerMessageId: learner.id,
            status: 'failed',
            blocks: [],
            consultations: [],
            lastSequence: 2,
            failureCode: 'service_unavailable',
            progress: null,
          }
        : null,
      summary: { current: null, failureAfterMessageId: null },
      memoryItems: [],
      actionItems: [],
    },
  }
}

/** One Mentor conversation in the history, whose last answer completed or failed. */
export async function installMentorConversation(
  page: Page,
  response: MentorResponseFixture,
) {
  const { session, detail } = mentorConversation(response)
  await page.route('**/_serverFn/**', async (route) => {
    const exportName = serverFnExport(route.request().url()) ?? ''
    const isList = exportName.includes('listMentorSessionsServer')
    if (!isList && !exportName.includes('getMentorSessionServer')) {
      await route.fallback()
      return
    }
    await route.fulfill({
      body: JSON.stringify({
        result: isList ? { items: [session], nextCursor: null } : detail,
      }),
      contentType: 'application/json',
      status: 200,
    })
  })
}
