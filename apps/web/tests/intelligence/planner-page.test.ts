import type { Page, Request } from '@playwright/test'

import { PlanningSessionFaker } from '@/core/intelligence/fakers/planning-session-faker'
import type {
  PlanningQuestion,
  PlanningSession,
} from '@/core/intelligence/planning-session'
import type { BffFixtureContract } from '../fixtures/bff-fixture'
import { expect, navigateAuthenticatedPage, test } from '../playwright'

/**
 * Browser integration with mocked `_serverFn` transport: the real route, middleware,
 * Home composer entry and planner page composition run against stateful mocks. It
 * never reaches the FastAPI service; server authorization and persistence are proven
 * by the server suites of SHIFU-91.
 */

const PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
const PLANNER_PATH = `/intelligence/planner/${PLANNING_ID}`
const INTENT =
  'Quero automatizar tarefas do dia a dia e parar de fazer planilhas na mão com Python.'

const firstQuestion: PlanningQuestion = {
  id: 'q1',
  text: 'Você já escreveu algum código antes?',
  kind: 'single',
  options: [
    { id: 'never', text: 'Nunca', exclusive: false },
    { id: 'copied', text: 'Já copiei e adaptei alguns scripts', exclusive: false },
    { id: 'simple', text: 'Escrevo scripts simples sozinho', exclusive: false },
    { id: 'nao-sei', text: 'Não sei', exclusive: true },
  ],
}
const secondQuestion: PlanningQuestion = {
  id: 'q2',
  text: 'O que você quer automatizar?',
  kind: 'multiple',
  options: [
    { id: 'sheets', text: 'Planilhas e relatórios', exclusive: false },
    { id: 'files', text: 'Organização de arquivos', exclusive: false },
    { id: 'texts', text: 'Tratamento de textos', exclusive: false },
    { id: 'nao-sei', text: 'Não sei', exclusive: true },
  ],
}
const thirdQuestion: PlanningQuestion = {
  id: 'q3',
  text: 'Que resultado você quer alcançar com os scripts?',
  kind: 'single',
  options: [
    { id: 'reports', text: 'Criar relatórios a partir de planilhas', exclusive: false },
    { id: 'rename', text: 'Organizar e renomear arquivos', exclusive: false },
    { id: 'combine', text: 'Combinar essas tarefas', exclusive: false },
    { id: 'nao-sei', text: 'Não sei', exclusive: true },
  ],
}
const secondBatchQuestion: PlanningQuestion = {
  id: 'q4',
  text: 'Quanto tempo por semana você consegue dedicar?',
  kind: 'single',
  options: [
    { id: 'little', text: 'Menos de duas horas', exclusive: false },
    { id: 'some', text: 'Entre duas e cinco horas', exclusive: false },
  ],
}

type ServerFunctionCall = {
  exportName: string
  data: Record<string, unknown>
}

type PlannerTransport = {
  session: PlanningSession | null
  loadFailure: boolean
  answerResult: PlanningSession | { kind: string; message?: string } | null
  retryResult: PlanningSession | null
  calls: ServerFunctionCall[]
}

function serverFnExport(url: string): string {
  const segment = new URL(url).pathname.split('/_serverFn/')[1]
  if (!segment) return ''

  try {
    const descriptor = JSON.parse(
      Buffer.from(decodeURIComponent(segment), 'base64').toString('utf-8'),
    ) as { export?: unknown }
    return typeof descriptor.export === 'string' ? descriptor.export : ''
  } catch {
    return ''
  }
}

function unwrapServerFunctionInput(value: unknown): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return {}

  const record = value as Record<string, unknown>
  for (const key of ['data', 'input', 'json', 'payload']) {
    const nested = record[key]
    if (typeof nested === 'object' && nested !== null && !Array.isArray(nested)) {
      return unwrapServerFunctionInput(nested)
    }
  }

  return record
}

function decodeServerFunctionValue(value: unknown): unknown {
  if (typeof value !== 'object' || value === null) return value
  if (Array.isArray(value)) return value.map(decodeServerFunctionValue)

  const record = value as Record<string, unknown>
  if (typeof record.t !== 'number') {
    return Object.fromEntries(
      Object.entries(record).map(([key, nested]) => [
        key,
        decodeServerFunctionValue(nested),
      ]),
    )
  }

  if (record.t === 0 || record.t === 1) return record.s
  if (record.t === 2) return undefined
  if (record.t === 9 && Array.isArray(record.a)) {
    return record.a.map(decodeServerFunctionValue)
  }
  if (record.t === 10) {
    const properties = record.p as { k?: unknown; v?: unknown } | undefined
    const keys = properties?.k
    const values = properties?.v
    if (!Array.isArray(keys) || !Array.isArray(values)) return value

    return Object.fromEntries(
      keys.map((key, index) => [String(key), decodeServerFunctionValue(values[index])]),
    )
  }

  return value
}

function serverFnInput(request: Request): Record<string, unknown> {
  const body = request.postData()
  if (body) {
    try {
      const serialized = JSON.parse(body) as { t?: unknown }
      return unwrapServerFunctionInput(
        decodeServerFunctionValue(serialized.t ? serialized.t : serialized),
      )
    } catch {
      // GET server functions carry their input in the request URL instead.
    }
  }

  const url = new URL(request.url())
  for (const value of url.searchParams.values()) {
    try {
      const serialized = JSON.parse(value) as { t?: unknown }
      const input = unwrapServerFunctionInput(
        decodeServerFunctionValue(serialized.t ? serialized.t : serialized),
      )
      if (Object.keys(input).length) return input
    } catch {
      // Ordinary query parameters are preserved below.
    }
  }

  return Object.fromEntries(url.searchParams.entries())
}

function interviewSession(overrides: Partial<PlanningSession> = {}): PlanningSession {
  return PlanningSessionFaker.fake({
    id: PLANNING_ID,
    intent: INTENT,
    status: 'interview',
    batch: { id: 'batch-1', questions: [firstQuestion, secondQuestion, thirdQuestion] },
    ...overrides,
  })
}

function processingSession(overrides: Partial<PlanningSession> = {}): PlanningSession {
  return PlanningSessionFaker.fake({
    id: PLANNING_ID,
    intent: INTENT,
    status: 'processing',
    batch: null,
    operation: { kind: 'start', startedAt: new Date().toISOString(), stage: null },
    ...overrides,
  })
}

function transportFor(session: PlanningSession | null): PlannerTransport {
  return { session, loadFailure: false, answerResult: null, retryResult: null, calls: [] }
}

function callsTo(transport: PlannerTransport, prefix: string) {
  return transport.calls.filter((call) => call.exportName.startsWith(prefix))
}

async function mockPlanner(bff: BffFixtureContract, transport: PlannerTransport) {
  await bff.route(async (route) => {
    const request = route.request()
    const exportName = serverFnExport(request.url())
    const fulfill = (result: unknown) =>
      route.fulfill({
        body: JSON.stringify({ result }),
        contentType: 'application/json',
        status: 200,
      })

    if (exportName.startsWith('fetchHomeGoals')) {
      await fulfill([])
      return
    }
    if (exportName.startsWith('getAvailableSkillsAction')) {
      await fulfill([])
      return
    }
    if (exportName.startsWith('startPlanningSession')) {
      transport.calls.push({ exportName, data: serverFnInput(request) })
      await fulfill({ id: PLANNING_ID, created_at: new Date().toISOString() })
      return
    }
    if (exportName.startsWith('getPlanningSessionServer')) {
      transport.calls.push({ exportName, data: serverFnInput(request) })
      if (transport.loadFailure) {
        await route.fulfill({
          body: JSON.stringify({ error: 'upstream unavailable' }),
          contentType: 'application/json',
          status: 500,
        })
        return
      }
      await fulfill(transport.session ?? { kind: 'not-found' })
      return
    }
    if (exportName.startsWith('answerPlanningQuestionsServer')) {
      transport.calls.push({ exportName, data: serverFnInput(request) })
      await fulfill(transport.answerResult ?? transport.session)
      return
    }
    if (exportName.startsWith('retryPlanningServer')) {
      transport.calls.push({ exportName, data: serverFnInput(request) })
      await fulfill(transport.retryResult ?? transport.session)
      return
    }
    if (exportName.startsWith('cancelPlanningServer')) {
      transport.calls.push({ exportName, data: serverFnInput(request) })
      await fulfill({ cancelled: true })
      return
    }

    await route.fallback()
  })
}

const CAPTURE_DIR = process.env.PLANNER_CAPTURE_DIR

async function capture(page: Page, name: string) {
  if (!CAPTURE_DIR) return
  await page.screenshot({ path: `${CAPTURE_DIR}/${name}.png`, fullPage: false })
}

async function expectNoHorizontalScroll(page: Page) {
  const hasHorizontalScroll = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalScroll).toBe(false)
}

type FrameSet = {
  question: string
  multiple: string
  last: string
  review: string
  analyzing: string
  interviewing: string
  retrieving: string
  composing: string
  failed: string
  outOfScope: string
  unsupported: string
  validationFailed: string
}

const DESKTOP_FRAMES: FrameSet = {
  question: 'q8TK6d',
  multiple: 'R9DLj',
  last: 'L0i7L1',
  review: 'OUE0P',
  analyzing: 'CM4DZ',
  interviewing: 'NmsmF',
  retrieving: 'AiygN',
  composing: 'nKwq9',
  failed: 'gLg9C',
  outOfScope: 'kLZY2',
  unsupported: 'B6LwtJ',
  validationFailed: 'PwKlt',
}

const MOBILE_FRAMES: FrameSet = {
  question: 'veOpx',
  multiple: 'ojjlR',
  last: 'v6t4v',
  review: 'ZmelL',
  analyzing: 'ZlbGK',
  interviewing: 'sgL1E',
  retrieving: 'KPglx',
  composing: 'FtBY1',
  failed: 'Aj406',
  outOfScope: 'AECyy',
  unsupported: 'H1SrH',
  validationFailed: 'k4oQiw',
}

async function walkThroughEveryFrame(
  page: Page,
  bff: BffFixtureContract,
  frames: FrameSet,
) {
  const transport = transportFor(interviewSession())
  transport.answerResult = processingSession({
    operation: { kind: 'answer', startedAt: new Date().toISOString(), stage: null },
    answeredBatchCount: 1,
  })
  await mockPlanner(bff, transport)
  await openPlannerFromHome(page)

  await chooseOption(page, 'radio', 'Já copiei e adaptei alguns scripts')
  await expectNoHorizontalScroll(page)
  await capture(page, frames.question)

  await page.getByRole('button', { name: 'Próxima' }).click()
  await chooseOption(page, 'checkbox', 'Planilhas e relatórios')
  await chooseOption(page, 'checkbox', 'Organização de arquivos')
  await expect(page.getByText('Pergunta 2 de 3 deste conjunto')).toBeVisible()
  await expectNoHorizontalScroll(page)
  await capture(page, frames.multiple)

  await page.getByRole('button', { name: 'Próxima' }).click()
  await chooseOption(page, 'radio', 'Combinar essas tarefas')
  await expect(page.getByRole('button', { name: 'Enviar respostas' })).toBeEnabled()
  await expectNoHorizontalScroll(page)
  await capture(page, frames.last)

  await page.getByRole('button', { name: '1 · Respondida' }).click()
  await expect(
    page.getByText('Revisando pergunta 1 de 3 · conjunto respondido'),
  ).toBeVisible()
  await expectNoHorizontalScroll(page)
  await capture(page, frames.review)

  await page.getByRole('button', { name: '3 · Respondida' }).click()
  transport.session = transport.answerResult
  await page.getByRole('button', { name: 'Enviar respostas' }).click()
  await expect(page.getByRole('status')).toContainText('Preparando o próximo passo…')
  await expectNoHorizontalScroll(page)
  await capture(page, frames.interviewing)

  for (const [stage, title, frame] of [
    ['retrieving', 'Consultando o Currículo…', frames.retrieving],
    ['composing', 'Montando sua proposta…', frames.composing],
    ['analyzing', 'Analisando seu objetivo…', frames.analyzing],
  ] as const) {
    transport.session = processingSession({
      operation: {
        kind: stage === 'analyzing' ? 'start' : 'answer',
        startedAt: new Date().toISOString(),
        stage,
      },
      answeredBatchCount: stage === 'analyzing' ? 0 : 1,
    })
    await expect(page.getByRole('status')).toContainText(title, { timeout: 6_000 })
    await expectNoHorizontalScroll(page)
    await capture(page, frame)
  }

  transport.session = interviewSession({
    status: 'failed',
    batch: null,
    answeredBatchCount: 1,
    failureCode: 'service_unavailable',
  })
  await expect(page.getByRole('alert')).toContainText('Não conseguimos continuar agora', {
    timeout: 6_000,
  })
  await expectNoHorizontalScroll(page)
  await capture(page, frames.failed)

  for (const [status, heading, frame] of [
    ['out-of-scope', 'Vamos planejar sua aprendizagem', frames.outOfScope],
    ['unsupported', 'Ainda não temos Habilidades para isso', frames.unsupported],
    [
      'validation-failed',
      'Não conseguimos concluir sua proposta',
      frames.validationFailed,
    ],
  ] as const) {
    transport.session = interviewSession({ status, batch: null })
    await openPlannerFromHome(page)
    await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible()
    await expectNoHorizontalScroll(page)
    await capture(page, frame)
  }
}

async function chooseOption(page: Page, role: 'radio' | 'checkbox', name: string) {
  // The shared radio and checkbox inputs are visually hidden; the learner clicks the row.
  await page.getByRole(role, { name }).locator('..').click()
}

async function openPlannerFromHome(page: Page) {
  await navigateAuthenticatedPage(page, '/')
  await page.getByLabel('O que você quer aprender?').fill(INTENT)
  await page.getByRole('button', { name: 'Planejar com IA' }).click()
  await expect(page).toHaveURL(new RegExp(`${PLANNER_PATH}/?$`))
}

test('redirects an anonymous visitor to the login before the planner renders', async ({
  page,
}) => {
  await page.goto(`${PLANNER_PATH}/`)

  await expect(page).toHaveURL(/\/login\/?$/)
  await expect(page.getByText('O que você quer alcançar')).not.toBeVisible()
})

test('opens the planner from the Home composer with the stored intention and the first question (CA-01, CA-02)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(interviewSession())
  await mockPlanner(bff, transport)

  await openPlannerFromHome(authenticatedPage)

  const start = callsTo(transport, 'startPlanningSession')
  expect(start).toHaveLength(1)
  expect(start[0]?.data).toEqual({ initialIntent: INTENT })
  await expect
    .poll(() => callsTo(transport, 'getPlanningSessionServer').length)
    .toBeGreaterThan(0)
  expect(callsTo(transport, 'getPlanningSessionServer')[0]?.data).toEqual({
    planningId: PLANNING_ID,
  })
  await expect(authenticatedPage.getByText('O que você quer alcançar')).toBeVisible()
  await expect(authenticatedPage.getByText(INTENT)).toBeVisible()
  await expect(
    authenticatedPage.getByText('Pergunta 1 de 3 deste conjunto'),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: '1 · Atual' }),
  ).toHaveAttribute('aria-current', 'step')
  await expect(
    authenticatedPage.getByRole('button', { name: '2 · Pendente' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: '3 · Pendente' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Você já escreveu algum código antes?',
    }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText(
      'Escolha uma alternativa. Você poderá revisar as respostas antes de enviar este conjunto.',
    ),
  ).toBeVisible()
  await expect(authenticatedPage.getByRole('radio')).toHaveCount(4)
  await expect(authenticatedPage.getByRole('textbox')).toHaveCount(0)
  await expect(authenticatedPage.getByRole('button', { name: 'Anterior' })).toHaveCount(0)
  await expect(authenticatedPage.getByRole('button', { name: 'Próxima' })).toBeEnabled()
  await expect(authenticatedPage.getByRole('button', { name: 'Cancelar' })).toBeEnabled()
  expect(callsTo(transport, 'createGoal')).toHaveLength(0)
})

test('navigates freely inside the batch, keeps the selections and gates the submission (CA-03, CA-05)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(interviewSession())
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await chooseOption(authenticatedPage, 'radio', 'Já copiei e adaptei alguns scripts')
  await authenticatedPage.getByRole('button', { name: 'Próxima' }).click()
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'O que você quer automatizar?',
    }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText('Pergunta 2 de 3 deste conjunto'),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: '1 · Respondida' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: '2 · Atual' }),
  ).toHaveAttribute('aria-current', 'step')

  await authenticatedPage.getByRole('button', { name: 'Anterior' }).click()
  await expect(
    authenticatedPage.getByRole('radio', { name: 'Já copiei e adaptei alguns scripts' }),
  ).toBeChecked()

  await authenticatedPage.getByRole('button', { name: '3 · Pendente' }).click()
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Que resultado você quer alcançar com os scripts?',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByRole('button', { name: 'Próxima' })).toHaveCount(0)
  await expect(
    authenticatedPage.getByRole('button', { name: 'Enviar respostas' }),
  ).toBeDisabled()
  await expect(
    authenticatedPage.getByText(
      'Escolha uma alternativa. Responda todas as perguntas do conjunto para enviar.',
    ),
  ).toBeVisible()
  expect(callsTo(transport, 'answerPlanningQuestionsServer')).toHaveLength(0)
})

test('keeps Não sei exclusive inside a multiple-choice question (CA-04)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(
    interviewSession({ batch: { id: 'batch-1', questions: [secondQuestion] } }),
  )
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(
    authenticatedPage.getByText(
      'Selecione uma ou mais alternativas. “Não sei” não pode ser combinado com outras respostas.',
    ),
  ).toBeVisible()
  const sheets = authenticatedPage.getByRole('checkbox', {
    name: 'Planilhas e relatórios',
  })
  const files = authenticatedPage.getByRole('checkbox', {
    name: 'Organização de arquivos',
  })
  const unknown = authenticatedPage.getByRole('checkbox', { name: 'Não sei' })
  await sheets.locator('..').click()
  await files.locator('..').click()
  await expect(sheets).toBeChecked()
  await expect(files).toBeChecked()

  await unknown.locator('..').click()
  await expect(unknown).toBeChecked()
  await expect(sheets).not.toBeChecked()
  await expect(files).not.toBeChecked()

  await sheets.locator('..').click()
  await expect(sheets).toBeChecked()
  await expect(unknown).not.toBeChecked()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Enviar respostas' }),
  ).toBeEnabled()
})

test('sends the complete batch, mirrors the real processing stages and renders the next batch (CA-06 … CA-09)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(interviewSession())
  transport.answerResult = processingSession({
    operation: { kind: 'answer', startedAt: new Date().toISOString(), stage: null },
    answeredBatchCount: 1,
  })
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await chooseOption(authenticatedPage, 'radio', 'Nunca')
  await authenticatedPage.getByRole('button', { name: 'Próxima' }).click()
  await chooseOption(authenticatedPage, 'checkbox', 'Planilhas e relatórios')
  await chooseOption(authenticatedPage, 'checkbox', 'Organização de arquivos')
  await authenticatedPage.getByRole('button', { name: 'Próxima' }).click()
  await chooseOption(authenticatedPage, 'radio', 'Combinar essas tarefas')
  await expect(
    authenticatedPage.getByText(
      'Escolha uma alternativa. Todas as perguntas estão respondidas; revise as etapas antes de enviar.',
    ),
  ).toBeVisible()
  await authenticatedPage.getByRole('button', { name: '1 · Respondida' }).click()
  await expect(
    authenticatedPage.getByText('Revisando pergunta 1 de 3 · conjunto respondido'),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText(
      'Você pode alterar esta resposta. Use as etapas para revisar as demais e enviar na última pergunta.',
    ),
  ).toBeVisible()
  await authenticatedPage.getByRole('button', { name: '3 · Respondida' }).click()

  transport.session = transport.answerResult
  await authenticatedPage.getByRole('button', { name: 'Enviar respostas' }).click()

  const submissions = callsTo(transport, 'answerPlanningQuestionsServer')
  expect(submissions).toHaveLength(1)
  expect(submissions[0]?.data).toEqual({
    planningId: PLANNING_ID,
    batchId: 'batch-1',
    answers: [
      { questionId: 'q1', optionIds: ['never'] },
      { questionId: 'q2', optionIds: ['sheets', 'files'] },
      { questionId: 'q3', optionIds: ['combine'] },
    ],
  })
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Planeje seu objetivo' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByRole('status')).toContainText(
    'Preparando o próximo passo…',
  )
  await expect(authenticatedPage.getByRole('status')).toContainText(
    'Suas respostas foram enviadas. Estamos verificando o que falta esclarecer.',
  )
  await expect(
    authenticatedPage.getByRole('button', { name: 'Processando…' }),
  ).toBeDisabled()
  await expect(authenticatedPage.getByRole('button', { name: 'Cancelar' })).toBeEnabled()
  await expect(authenticatedPage.getByRole('radio')).toHaveCount(0)

  const pollsBefore = callsTo(transport, 'getPlanningSessionServer').length
  transport.session = processingSession({
    operation: {
      kind: 'answer',
      startedAt: new Date().toISOString(),
      stage: 'retrieving',
    },
    answeredBatchCount: 1,
  })
  await expect(authenticatedPage.getByRole('status')).toContainText(
    'Consultando o Currículo…',
    { timeout: 6_000 },
  )
  await expect(
    authenticatedPage.getByRole('button', { name: 'Consultando…' }),
  ).toBeDisabled()
  transport.session = processingSession({
    operation: {
      kind: 'answer',
      startedAt: new Date().toISOString(),
      stage: 'composing',
    },
    answeredBatchCount: 1,
  })
  await expect(authenticatedPage.getByRole('status')).toContainText(
    'Montando sua proposta…',
    { timeout: 6_000 },
  )
  await expect(
    authenticatedPage.getByRole('button', { name: 'Montando proposta…' }),
  ).toBeDisabled()
  expect(callsTo(transport, 'getPlanningSessionServer').length).toBeGreaterThan(
    pollsBefore,
  )

  transport.session = interviewSession({
    batch: { id: 'batch-2', questions: [secondBatchQuestion] },
    answeredBatchCount: 1,
  })
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Quanto tempo por semana você consegue dedicar?',
    }),
  ).toBeVisible({ timeout: 6_000 })
  await expect(
    authenticatedPage.getByText('Pergunta 1 de 1 deste conjunto'),
  ).toBeVisible()
  await expect(authenticatedPage.getByRole('button', { name: '1 · Atual' })).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: '2 · Pendente' }),
  ).toHaveCount(0)
  await expect(
    authenticatedPage.getByRole('radio', { name: 'Menos de duas horas' }),
  ).not.toBeChecked()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Enviar respostas' }),
  ).toBeDisabled()

  const pollsAfterInterview = callsTo(transport, 'getPlanningSessionServer').length
  await authenticatedPage.waitForTimeout(2_600)
  expect(callsTo(transport, 'getPlanningSessionServer').length).toBe(pollsAfterInterview)
})

test('cancels during processing, returns to the Home and ignores a late result (CA-10)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(processingSession())
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(authenticatedPage.getByRole('status')).toContainText(
    'Analisando seu objetivo…',
  )
  await expect(
    authenticatedPage.getByRole('button', { name: 'Analisando…' }),
  ).toBeDisabled()
  await authenticatedPage.getByRole('button', { name: 'Cancelar' }).click()

  await expect(authenticatedPage).toHaveURL(/\/$/)
  const cancels = callsTo(transport, 'cancelPlanningServer')
  expect(cancels).toHaveLength(1)
  expect(cancels[0]?.data).toEqual({ planningId: PLANNING_ID })
  const pollsAfterCancel = callsTo(transport, 'getPlanningSessionServer').length

  transport.session = interviewSession()
  await authenticatedPage.waitForTimeout(2_600)
  await expect(authenticatedPage).toHaveURL(/\/$/)
  await expect(authenticatedPage.getByText('O que você quer alcançar')).toHaveCount(0)
  expect(callsTo(transport, 'getPlanningSessionServer').length).toBe(pollsAfterCancel)
})

test('abandons a planning opened without the composer entry, such as a reload (CA-11)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(interviewSession())
  await mockPlanner(bff, transport)

  await navigateAuthenticatedPage(authenticatedPage, `${PLANNER_PATH}/`)

  await expect(authenticatedPage).toHaveURL(/\/$/)
  expect(callsTo(transport, 'cancelPlanningServer')).toHaveLength(1)
  expect(callsTo(transport, 'getPlanningSessionServer')).toHaveLength(0)
  await expect(authenticatedPage.getByRole('radio')).toHaveCount(0)
})

test('keeps a failed planning on the page and recovers through retry (CA-12)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(
    interviewSession({
      status: 'failed',
      batch: null,
      answeredBatchCount: 1,
      failureCode: 'service_unavailable',
    }),
  )
  transport.retryResult = processingSession({
    operation: { kind: 'retry', startedAt: new Date().toISOString(), stage: null },
    answeredBatchCount: 1,
  })
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Planeje seu objetivo' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByRole('alert')).toContainText(
    'Não conseguimos continuar agora',
  )
  await expect(authenticatedPage.getByRole('alert')).toContainText(
    'Seu planejamento permanece nesta página. Tente novamente para continuar de onde parou.',
  )
  await expect(
    authenticatedPage.getByText('Vamos planejar sua aprendizagem'),
  ).toHaveCount(0)

  transport.session = transport.retryResult
  await authenticatedPage.getByRole('button', { name: 'Tentar novamente' }).click()

  expect(callsTo(transport, 'retryPlanningServer')).toHaveLength(1)
  await expect(authenticatedPage.getByRole('status')).toContainText(
    'Preparando o próximo passo…',
  )
  transport.session = interviewSession({ answeredBatchCount: 1 })
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Você já escreveu algum código antes?',
    }),
  ).toBeVisible({ timeout: 6_000 })
})

test('shows a recoverable error when the planning cannot be loaded and retries the request (CA-13)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(interviewSession())
  transport.loadFailure = true
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Não foi possível carregar o planejamento',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText(/fora desse escopo/)).toHaveCount(0)
  await expect(authenticatedPage.getByText(/Habilidades para isso/)).toHaveCount(0)

  transport.loadFailure = false
  await authenticatedPage.getByRole('button', { name: 'Tentar novamente' }).click()

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Você já escreveu algum código antes?',
    }),
  ).toBeVisible()
  expect(callsTo(transport, 'cancelPlanningServer')).toHaveLength(0)
})

test('reports a concurrent operation on submit and refreshes the state (CA-14)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(
    interviewSession({ batch: { id: 'batch-1', questions: [firstQuestion] } }),
  )
  transport.answerResult = {
    kind: 'conflict',
    message: 'Já existe uma operação em andamento neste planejamento.',
  }
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await chooseOption(authenticatedPage, 'radio', 'Nunca')
  const pollsBefore = callsTo(transport, 'getPlanningSessionServer').length
  await authenticatedPage.getByRole('button', { name: 'Enviar respostas' }).click()

  await expect(authenticatedPage.getByRole('alert')).toHaveText(
    'Já existe uma operação em andamento neste planejamento.',
  )
  expect(callsTo(transport, 'answerPlanningQuestionsServer')).toHaveLength(1)
  await expect
    .poll(() => callsTo(transport, 'getPlanningSessionServer').length)
    .toBeGreaterThan(pollsBefore)
  await expect(authenticatedPage.getByRole('radio', { name: 'Nunca' })).toBeChecked()
})

test('explains an out-of-scope request and lets the learner reformulate (CA-15, CA-18)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(
    interviewSession({ status: 'out-of-scope', batch: null }),
  )
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Vamos planejar sua aprendizagem',
    }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText(
      'O planejador ajuda a criar objetivos de aprendizagem. Esse pedido está fora desse escopo. Descreva o que você quer aprender ou desenvolver.',
    ),
  ).toBeVisible()
  await expect(authenticatedPage.getByRole('radio')).toHaveCount(0)
  await authenticatedPage.getByRole('button', { name: 'Reformular' }).click()

  await expect(authenticatedPage).toHaveURL(/\/$/)
  expect(callsTo(transport, 'cancelPlanningServer')).toHaveLength(1)
  await expect(authenticatedPage.getByLabel('O que você quer aprender?')).toBeVisible()
})

test('opens the manual Goal form from an unsupported Goal (CA-16, CA-18)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(interviewSession({ status: 'unsupported', batch: null }))
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Ainda não temos Habilidades para isso',
    }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByText(
      'Nenhuma combinação do Currículo representa bem o que você descreveu. Você pode reformular a intenção ou montar o Objetivo por conta própria.',
    ),
  ).toBeVisible()
  await authenticatedPage.getByRole('button', { name: 'Criar manualmente' }).click()

  await expect(authenticatedPage).toHaveURL(/\/learning\/goals\/new\/?$/)
  expect(callsTo(transport, 'cancelPlanningServer')).toHaveLength(1)
})

test('distinguishes a proposal that failed validation and retries it (CA-17)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(
    interviewSession({
      status: 'validation-failed',
      batch: null,
      failureCode: 'validation_exhausted',
    }),
  )
  transport.retryResult = processingSession({
    operation: { kind: 'retry', startedAt: new Date().toISOString(), stage: 'composing' },
  })
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Não conseguimos concluir sua proposta',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText(/Nenhum objetivo foi criado/)).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Reformular' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Criar manualmente' }),
  ).toBeVisible()

  transport.session = transport.retryResult
  await authenticatedPage.getByRole('button', { name: 'Tentar novamente' }).click()

  expect(callsTo(transport, 'retryPlanningServer')).toHaveLength(1)
  await expect(authenticatedPage.getByRole('status')).toContainText(
    'Montando sua proposta…',
  )
})

test('hands a validated proposal to the review boundary even without an interview (CA-19)', async ({
  authenticatedPage,
  bff,
}) => {
  const proposal = PlanningSessionFaker.fakeProposal({ title: 'Automação com Python' })
  const transport = transportFor(
    interviewSession({ status: 'proposal', batch: null, proposal }),
  )
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Sua proposta está pronta para revisão',
    }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Automação com Python')).toBeVisible()
  await expect(authenticatedPage.getByText(INTENT)).toBeVisible()
  await expect(authenticatedPage.getByRole('radio')).toHaveCount(0)
  await expect(
    authenticatedPage.getByRole('button', { name: 'Enviar respostas' }),
  ).toHaveCount(0)
})

test('tells the learner when the planning no longer exists (CA-23)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(null)
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Planejamento não encontrado',
    }),
  ).toBeVisible()
  await authenticatedPage.getByRole('button', { name: 'Voltar à Home' }).click()

  await expect(authenticatedPage).toHaveURL(/\/$/)
  expect(callsTo(transport, 'cancelPlanningServer')).toHaveLength(0)
})

test('works at mobile width with keyboard selection and navigation (CA-20, CA-21)', async ({
  authenticatedPage,
  bff,
}) => {
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })
  const transport = transportFor(interviewSession())
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Você já escreveu algum código antes?',
    }),
  ).toBeVisible()
  const hasHorizontalScroll = await authenticatedPage.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasHorizontalScroll).toBe(false)

  await authenticatedPage.getByRole('radio', { name: 'Nunca' }).focus()
  await authenticatedPage.keyboard.press('ArrowDown')
  await expect(
    authenticatedPage.getByRole('radio', { name: 'Já copiei e adaptei alguns scripts' }),
  ).toBeChecked()
  await authenticatedPage.keyboard.press('Tab')
  await expect(authenticatedPage.getByRole('button', { name: 'Cancelar' })).toBeFocused()
  await authenticatedPage.keyboard.press('Tab')
  await expect(authenticatedPage.getByRole('button', { name: 'Próxima' })).toBeFocused()
  await authenticatedPage.keyboard.press('Enter')

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'O que você quer automatizar?',
    }),
  ).toBeFocused()
  await expect(
    authenticatedPage.getByRole('button', { name: '2 · Atual' }),
  ).toHaveAttribute('aria-current', 'step')
  await expect(
    authenticatedPage.getByRole('button', { name: '1 · Respondida' }),
  ).toBeVisible()
  const actions = authenticatedPage.getByRole('button', {
    name: /Anterior|Próxima|Cancelar/,
  })
  await expect(actions).toHaveCount(3)
  const widths = await actions.evaluateAll((buttons) =>
    buttons.map((button) => button.getBoundingClientRect().width),
  )
  expect(widths[0]).toBeLessThan(200)
  expect(widths[1]).toBeGreaterThan(300)
  expect(widths[2]).toBeGreaterThan(300)
})

test('renders every approved desktop frame state without horizontal scroll (VM-02)', async ({
  authenticatedPage,
  bff,
}) => {
  test.setTimeout(120_000)
  await authenticatedPage.setViewportSize({ width: 1440, height: 900 })

  await walkThroughEveryFrame(authenticatedPage, bff, DESKTOP_FRAMES)
})

test('renders every approved mobile frame state without horizontal scroll (CA-20, VM-02)', async ({
  authenticatedPage,
  bff,
}) => {
  test.setTimeout(120_000)
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })

  await walkThroughEveryFrame(authenticatedPage, bff, MOBILE_FRAMES)
})
