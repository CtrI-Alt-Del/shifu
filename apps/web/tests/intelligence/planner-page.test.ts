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
    { id: 'never', text: 'Nunca', exclusive: false, open: false },
    {
      id: 'copied',
      text: 'Já copiei e adaptei alguns scripts',
      exclusive: false,
      open: false,
    },
    {
      id: 'simple',
      text: 'Escrevo scripts simples sozinho',
      exclusive: false,
      open: false,
    },
    { id: 'nao-sei', text: 'Não sei', exclusive: true, open: false },
  ],
}
const secondQuestion: PlanningQuestion = {
  id: 'q2',
  text: 'O que você quer automatizar?',
  kind: 'multiple',
  options: [
    { id: 'sheets', text: 'Planilhas e relatórios', exclusive: false, open: false },
    { id: 'files', text: 'Organização de arquivos', exclusive: false, open: false },
    { id: 'texts', text: 'Tratamento de textos', exclusive: false, open: false },
    { id: 'nao-sei', text: 'Não sei', exclusive: true, open: false },
  ],
}
const thirdQuestion: PlanningQuestion = {
  id: 'q3',
  text: 'Que resultado você quer alcançar com os scripts?',
  kind: 'single',
  options: [
    {
      id: 'reports',
      text: 'Criar relatórios a partir de planilhas',
      exclusive: false,
      open: false,
    },
    {
      id: 'rename',
      text: 'Organizar e renomear arquivos',
      exclusive: false,
      open: false,
    },
    { id: 'combine', text: 'Combinar essas tarefas', exclusive: false, open: false },
    { id: 'nao-sei', text: 'Não sei', exclusive: true, open: false },
  ],
}
const secondBatchQuestion: PlanningQuestion = {
  id: 'q4',
  text: 'Quanto tempo por semana você consegue dedicar?',
  kind: 'single',
  options: [
    { id: 'little', text: 'Menos de duas horas', exclusive: false, open: false },
    { id: 'some', text: 'Entre duas e cinco horas', exclusive: false, open: false },
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
  restartResult: PlanningSession | { kind: string; message?: string } | null
  confirmResult:
    | { goalId: string; replayed: boolean }
    | { kind: string; message?: string }
  confirmStatus: number
  confirmHold: Promise<void> | null
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

const NEW_INTENT = 'Quero criar APIs web com Python para integrar sistemas.'
const GOAL_ID = '01SHF000000000000000000777'
const CONFIRMATION_KEY_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
const REVIEW_PROPOSAL = PlanningSessionFaker.fakeProposal({
  title: 'Automatizar tarefas do dia a dia com Python',
  description:
    'Quero parar de fazer planilha na mão e escrever scripts que resolvam isso por mim.',
  skills: [
    {
      skillId: 'skill-logic',
      name: 'Lógica de programação',
      justification:
        'Você já adaptou scripts. Esta habilidade ajuda a entender a sequência de passos e as decisões por trás deles.',
    },
    {
      skillId: 'skill-python',
      name: 'Python essencial',
      justification:
        'Para escrever seus próprios scripts em Python: variáveis, funções e manipulação de dados.',
    },
    {
      skillId: 'skill-automation',
      name: 'Automação de arquivos e planilhas',
      justification:
        'Para aplicar a lógica e o Python ao que você pediu: ler, transformar e gerar arquivos e planilhas.',
    },
  ],
  relations: [
    { skillId: 'skill-automation', foundationSkillId: 'skill-logic' },
    { skillId: 'skill-automation', foundationSkillId: 'skill-python' },
  ],
})

function interviewSession(overrides: Partial<PlanningSession> = {}): PlanningSession {
  return PlanningSessionFaker.fake({
    id: PLANNING_ID,
    intent: INTENT,
    status: 'interview',
    batch: { id: 'batch-1', questions: [firstQuestion, secondQuestion, thirdQuestion] },
    ...overrides,
  })
}

function proposalSession(overrides: Partial<PlanningSession> = {}): PlanningSession {
  return interviewSession({
    status: 'proposal',
    batch: null,
    answeredBatchCount: 1,
    proposal: REVIEW_PROPOSAL,
    ...overrides,
  })
}

function restartedSession(overrides: Partial<PlanningSession> = {}): PlanningSession {
  return processingSession({
    generation: 2,
    answeredBatchCount: 0,
    operation: { kind: 'restart', startedAt: new Date().toISOString(), stage: null },
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
  return {
    session,
    loadFailure: false,
    answerResult: null,
    retryResult: null,
    restartResult: null,
    confirmResult: { goalId: GOAL_ID, replayed: false },
    confirmStatus: 200,
    confirmHold: null,
    calls: [],
  }
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
    if (exportName.startsWith('restartPlanningServer')) {
      transport.calls.push({ exportName, data: serverFnInput(request) })
      await fulfill(transport.restartResult ?? transport.session)
      return
    }
    if (exportName.startsWith('confirmPlanningServer')) {
      transport.calls.push({ exportName, data: serverFnInput(request) })
      if (transport.confirmHold) await transport.confirmHold
      if (transport.confirmStatus !== 200) {
        await route.fulfill({
          body: JSON.stringify({ error: 'upstream unavailable' }),
          contentType: 'application/json',
          status: transport.confirmStatus,
        })
        return
      }
      await fulfill(transport.confirmResult)
      return
    }
    if (exportName.startsWith('getGoalDetail')) {
      transport.calls.push({ exportName, data: serverFnInput(request) })
      await fulfill({
        kind: 'success',
        detail: {
          goalId: GOAL_ID,
          title: 'Automatizar planilhas com Python',
          description: REVIEW_PROPOSAL.description,
          relations: [],
          skills: REVIEW_PROPOSAL.skills.map((skill, index) => ({
            skillExperienceId: `01SHF00000000000000000080${index}`,
            skillId: skill.skillId,
            name: skill.name,
            skillName: skill.name,
            status: 'not-started',
            progress: null,
            inclusionReason: skill.justification,
          })),
        },
      })
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

async function capture(page: Page, name: string, tall = false) {
  if (!CAPTURE_DIR) return

  // Tall frames are captured on a viewport as tall as the document, like the frames.
  const viewport = page.viewportSize()
  if (tall && viewport) {
    const height = await page.evaluate(() => document.documentElement.scrollHeight)
    await page.setViewportSize({
      width: viewport.width,
      height: Math.max(viewport.height, height),
    })
  }
  await page.screenshot({ animations: 'disabled', path: `${CAPTURE_DIR}/${name}.png` })
  if (tall && viewport) await page.setViewportSize(viewport)
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

test('opens a text field for "Outro" and sends the learner text with the answers', async ({
  authenticatedPage,
  bff,
}) => {
  const openQuestion: PlanningQuestion = {
    ...secondQuestion,
    options: [
      ...secondQuestion.options.slice(0, -1),
      { id: 'outro', text: 'Outro', exclusive: false, open: true },
      ...secondQuestion.options.slice(-1),
    ],
  }
  const transport = transportFor(
    interviewSession({ batch: { id: 'batch-1', questions: [openQuestion] } }),
  )
  transport.answerResult = processingSession({
    operation: { kind: 'answer', startedAt: new Date().toISOString(), stage: null },
    answeredBatchCount: 1,
  })
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  const submit = authenticatedPage.getByRole('button', { name: 'Enviar respostas' })
  await expect(authenticatedPage.getByLabel('Descreva sua resposta')).toHaveCount(0)
  await chooseOption(authenticatedPage, 'checkbox', 'Planilhas e relatórios')
  await chooseOption(authenticatedPage, 'checkbox', 'Outro')
  const field = authenticatedPage.getByLabel('Descreva sua resposta')
  await expect(field).toBeFocused()
  await expect(submit).toBeDisabled()

  await field.fill('  macros no Excel ')
  await expect(authenticatedPage.getByText('18/200 caracteres')).toBeVisible()
  await expect(submit).toBeEnabled()

  transport.session = transport.answerResult
  await submit.click()

  const submissions = callsTo(transport, 'answerPlanningQuestionsServer')
  expect(submissions).toHaveLength(1)
  expect(submissions[0]?.data).toEqual({
    planningId: PLANNING_ID,
    batchId: 'batch-1',
    answers: [
      {
        questionId: 'q2',
        optionIds: ['sheets', 'outro'],
        otherText: 'macros no Excel',
      },
    ],
  })
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

test('renders the review surface for a validated proposal even without an interview (CA-19)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(proposalSession({ answeredBatchCount: 0 }))
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Revise seu objetivo' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByLabel('Título')).toHaveValue(REVIEW_PROPOSAL.title)
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

/**
 * Proposal review (SHIFU-93). The acceptance criteria below refer to
 * `documentation/features/intelligence/planner-review/spec.md`.
 */

const REVIEW_HEADING = { level: 1, name: 'Revise seu objetivo' } as const
const GRAPH_NAME = 'Grafo das Habilidades propostas'
const LIST_NAME = 'Habilidades sugeridas'
const DIALOG_NAME = 'Reiniciar planejamento'
const INTENT_LABEL = 'O que você quer aprender?'

test('reviews a validated proposal in the graph and list views and keeps the edits (review CA-01 … CA-03)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(proposalSession())
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(authenticatedPage.getByRole('heading', REVIEW_HEADING)).toBeVisible()
  const title = authenticatedPage.getByLabel('Título')
  await expect(title).toHaveValue(REVIEW_PROPOSAL.title)
  await expect(authenticatedPage.getByLabel('Descrição')).toHaveValue(
    REVIEW_PROPOSAL.description,
  )
  await expect(authenticatedPage.getByRole('tab', { name: 'Grafo' })).toHaveAttribute(
    'aria-selected',
    'true',
  )
  await expect(
    authenticatedPage.getByText(
      'As três habilidades se complementam. Você escolhe por onde começar.',
    ),
  ).toBeVisible()
  const graph = authenticatedPage.getByRole('region', { name: GRAPH_NAME })
  await expect(
    graph.getByRole('article', {
      name: `Proposta de Objetivo: ${REVIEW_PROPOSAL.title}`,
    }),
  ).toBeVisible()
  for (const skill of REVIEW_PROPOSAL.skills) {
    await expect(
      graph.getByRole('article', { name: `Habilidade ${skill.name}` }),
    ).toContainText(skill.justification)
  }
  await expect(graph.getByRole('link')).toHaveCount(0)
  await expect(graph.getByRole('progressbar')).toHaveCount(0)
  await expect(authenticatedPage.getByRole('list', { name: LIST_NAME })).toHaveCount(0)

  await title.fill('Automatizar planilhas com Python')
  await authenticatedPage.getByRole('tab', { name: 'Lista' }).click()
  const list = authenticatedPage.getByRole('list', { name: LIST_NAME })
  await expect(list.getByRole('listitem')).toHaveCount(3)
  for (const [index, skill] of REVIEW_PROPOSAL.skills.entries()) {
    await expect(list.getByRole('listitem').nth(index)).toContainText(skill.name)
    await expect(list.getByRole('listitem').nth(index)).toContainText(skill.justification)
  }
  await expect(list.getByRole('textbox')).toHaveCount(0)
  await expect(graph).toHaveCount(0)
  await expect(title).toHaveValue('Automatizar planilhas com Python')

  await authenticatedPage.getByRole('tab', { name: 'Grafo' }).click()
  await expect(
    graph.getByRole('article', {
      name: 'Proposta de Objetivo: Automatizar planilhas com Python',
    }),
  ).toBeVisible()
  await expect(title).toHaveValue('Automatizar planilhas com Python')
  expect(callsTo(transport, 'answerPlanningQuestionsServer')).toHaveLength(0)
  expect(callsTo(transport, 'restartPlanningServer')).toHaveLength(0)
})

test('validates the edited Goal fields before any confirmation is sent (review CA-04)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(proposalSession())
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)
  const title = authenticatedPage.getByLabel('Título')
  const description = authenticatedPage.getByLabel('Descrição')
  const createGoal = authenticatedPage.getByRole('button', { name: 'Criar objetivo' })

  await title.fill('')
  await createGoal.click()
  await expect(authenticatedPage.getByRole('alert')).toContainText(
    'Informe um título para o Objetivo.',
  )
  await expect(title).toBeFocused()
  await expect(title).toHaveAttribute('aria-invalid', 'true')

  await title.fill('  Automatizar planilhas com Python  ')
  await expect(authenticatedPage.getByRole('alert')).toHaveCount(0)
  await description.fill('   ')
  await createGoal.click()
  await expect(authenticatedPage.getByRole('alert')).toContainText(
    'Informe uma descrição para o Objetivo.',
  )
  await expect(description).toBeFocused()
  expect(callsTo(transport, 'confirmPlanningServer')).toHaveLength(0)
  expect(callsTo(transport, 'cancelPlanningServer')).toHaveLength(0)
  await expect(authenticatedPage).toHaveURL(new RegExp(`${PLANNER_PATH}/?$`))
})

test('restarts the planning from the review with a new intention and lands on the new interview (review CA-06 … CA-08)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(proposalSession())
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)
  const trigger = authenticatedPage.getByRole('button', {
    name: 'Reiniciar planejamento',
  })
  const dialog = authenticatedPage.getByRole('alertdialog', { name: DIALOG_NAME })
  const field = dialog.getByLabel(INTENT_LABEL)

  await trigger.click()
  await expect(dialog).toBeVisible()
  await expect(field).toHaveValue(INTENT)
  await expect(field).toBeFocused()
  await expect(dialog.getByRole('button', { name: 'Cancelar' })).toHaveCount(0)
  await expect(dialog).toContainText(
    'Ao continuar, a proposta e as respostas anteriores serão substituídas por um novo planejamento.',
  )

  await dialog.getByRole('button', { name: 'Fechar' }).click()
  await expect(dialog).toBeHidden()
  await expect(trigger).toBeFocused()

  await trigger.click()
  await expect(field).toBeFocused()
  await authenticatedPage.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  await expect(trigger).toBeFocused()
  await expect(authenticatedPage.getByLabel('Título')).toHaveValue(REVIEW_PROPOSAL.title)

  await trigger.click()
  await field.fill('   ')
  await dialog.getByRole('button', { name: 'Iniciar planejamento' }).click()
  await expect(dialog.getByRole('alert')).toContainText(
    'Descreva o que você quer aprender antes de continuar.',
  )
  expect(callsTo(transport, 'restartPlanningServer')).toHaveLength(0)

  const restarted = restartedSession({ intent: NEW_INTENT })
  transport.restartResult = restarted
  transport.session = restarted
  await field.fill(NEW_INTENT)
  await dialog.getByRole('button', { name: 'Iniciar planejamento' }).click()

  await expect(authenticatedPage.getByRole('status')).toContainText(
    'Analisando seu objetivo…',
  )
  await expect(dialog).toBeHidden()
  await expect(authenticatedPage.getByText(NEW_INTENT)).toBeVisible()
  await expect(authenticatedPage.getByRole('heading', REVIEW_HEADING)).toHaveCount(0)
  expect(callsTo(transport, 'restartPlanningServer')).toHaveLength(1)
  expect(callsTo(transport, 'restartPlanningServer')[0].data).toEqual({
    planningId: PLANNING_ID,
    initialIntent: NEW_INTENT,
  })

  transport.session = interviewSession({
    intent: NEW_INTENT,
    generation: 2,
    answeredBatchCount: 0,
    batch: { id: 'batch-2', questions: [secondBatchQuestion] },
  })
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: secondBatchQuestion.text }),
  ).toBeVisible({ timeout: 6_000 })
  await expect(
    authenticatedPage.getByText('Pergunta 1 de 1 deste conjunto'),
  ).toBeVisible()
  await expect(authenticatedPage.getByText(NEW_INTENT)).toBeVisible()
})

test('keeps the proposal and reports a refused restart inside the dialog (review CA-09)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(proposalSession())
  transport.restartResult = {
    kind: 'conflict',
    message: 'Já existe uma operação em andamento neste planejamento.',
  }
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)
  const dialog = authenticatedPage.getByRole('alertdialog', { name: DIALOG_NAME })

  await authenticatedPage.getByRole('button', { name: 'Reiniciar planejamento' }).click()
  await dialog.getByLabel(INTENT_LABEL).fill(NEW_INTENT)
  await dialog.getByRole('button', { name: 'Iniciar planejamento' }).click()

  await expect(dialog.getByRole('alert')).toContainText(
    'Já existe uma operação em andamento neste planejamento.',
  )
  await expect(dialog.getByRole('button', { name: 'Iniciar planejamento' })).toBeEnabled()
  expect(callsTo(transport, 'restartPlanningServer')).toHaveLength(1)
  await expect
    .poll(() => callsTo(transport, 'getPlanningSessionServer').length)
    .toBeGreaterThanOrEqual(2)

  await dialog.getByRole('button', { name: 'Fechar' }).click()
  await expect(authenticatedPage.getByRole('heading', REVIEW_HEADING)).toBeVisible()
  await expect(authenticatedPage.getByLabel('Título')).toHaveValue(REVIEW_PROPOSAL.title)
})

test('cancels the planning from the review and returns to the Home (review CA-10)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(proposalSession())
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await authenticatedPage.getByRole('button', { name: 'Cancelar' }).click()

  await expect(authenticatedPage).toHaveURL(/\/$/)
  expect(callsTo(transport, 'cancelPlanningServer')).toHaveLength(1)
  expect(callsTo(transport, 'cancelPlanningServer')[0].data).toEqual({
    planningId: PLANNING_ID,
  })
})

test('reviews at mobile width with keyboard tabs, dialog and stacked actions (review CA-11)', async ({
  authenticatedPage,
  bff,
}) => {
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })
  const transport = transportFor(proposalSession())
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await expect(authenticatedPage.getByRole('heading', REVIEW_HEADING)).toBeVisible()
  await expectNoHorizontalScroll(authenticatedPage)

  await authenticatedPage.getByRole('tab', { name: 'Grafo' }).focus()
  await authenticatedPage.keyboard.press('ArrowRight')
  await expect(authenticatedPage.getByRole('tab', { name: 'Lista' })).toHaveAttribute(
    'aria-selected',
    'true',
  )
  await expect(authenticatedPage.getByRole('list', { name: LIST_NAME })).toBeVisible()
  await expectNoHorizontalScroll(authenticatedPage)

  const trigger = authenticatedPage.getByRole('button', {
    name: 'Reiniciar planejamento',
  })
  await trigger.focus()
  await authenticatedPage.keyboard.press('Enter')
  const dialog = authenticatedPage.getByRole('alertdialog', { name: DIALOG_NAME })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByLabel(INTENT_LABEL)).toBeFocused()
  await authenticatedPage.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  await expect(trigger).toBeFocused()

  const actions = authenticatedPage.getByRole('button', {
    name: /^(Cancelar|Reiniciar planejamento|Criar objetivo)$/,
  })
  await expect(actions).toHaveCount(3)
  const widths = await actions.evaluateAll((buttons) =>
    buttons.map((button) => button.getBoundingClientRect().width),
  )
  expect(widths[0]).toBeLessThan(200)
  expect(widths[1]).toBeGreaterThan(300)
  expect(widths[2]).toBeGreaterThan(300)
})

/**
 * Goal creation from the confirmed proposal (SHIFU-95). The acceptance criteria below
 * refer to `documentation/features/intelligence/planner-confirmation/spec.md`.
 */

const CREATE_GOAL = { name: 'Criar objetivo' }
const RETRY_GOAL = { name: 'Tentar criar objetivo' }
const VERIFY_GOAL = { name: 'Verificar resultado' }

function holdConfirmation(transport: PlannerTransport) {
  let release: () => void = () => undefined
  transport.confirmHold = new Promise<void>((resolve) => {
    release = resolve
  })
  return () => {
    transport.confirmHold = null
    release()
  }
}

test('creates the Goal from the confirmed proposal with the edits and lands on its page (confirmation CA-01, CA-02, CA-08)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(proposalSession())
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)
  const release = holdConfirmation(transport)

  await authenticatedPage.getByLabel('Título').fill(' Automatizar planilhas com Python ')
  await authenticatedPage.getByRole('button', CREATE_GOAL).click()

  await expect(authenticatedPage.getByText('Criando seu objetivo…')).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Criando objetivo…' }),
  ).toBeDisabled()
  await expect(authenticatedPage.getByLabel('Título')).toBeDisabled()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Reiniciar planejamento' }),
  ).toBeDisabled()
  await expect(authenticatedPage.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
  await expectNoHorizontalScroll(authenticatedPage)
  release()

  await expect(authenticatedPage).toHaveURL(new RegExp(`/learning/goals/${GOAL_ID}/?$`))
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Automatizar planilhas com Python',
    }),
  ).toBeVisible()
  await authenticatedPage.getByRole('tab', { name: 'Lista' }).click()
  await expect(
    authenticatedPage.getByText(REVIEW_PROPOSAL.skills[0].justification),
  ).toBeVisible()

  const confirmations = callsTo(transport, 'confirmPlanningServer')
  expect(confirmations).toHaveLength(1)
  expect(confirmations[0].data).toEqual({
    planningId: PLANNING_ID,
    confirmationKey: expect.stringMatching(CONFIRMATION_KEY_PATTERN),
    title: 'Automatizar planilhas com Python',
    description: REVIEW_PROPOSAL.description,
  })
  expect(callsTo(transport, 'cancelPlanningServer')).toHaveLength(0)
})

test('keeps the proposal after a refused creation and replays the same confirmation on retry (confirmation CA-03, CA-05)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(proposalSession())
  transport.confirmResult = {
    kind: 'conflict',
    message: 'Este Skill ainda não está pronto para iniciar.',
  }
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await authenticatedPage.getByRole('button', CREATE_GOAL).click()
  await expect(authenticatedPage.getByRole('alert')).toContainText(
    'Não foi possível criar o objetivo',
  )
  await expect(authenticatedPage.getByRole('alert')).toContainText(
    'Este Skill ainda não está pronto para iniciar. Sua proposta foi mantida.',
  )
  await expect(authenticatedPage.getByLabel('Título')).toBeEnabled()
  await expect(authenticatedPage.getByLabel('Título')).toHaveValue(REVIEW_PROPOSAL.title)
  await expect(authenticatedPage).toHaveURL(new RegExp(`${PLANNER_PATH}/?$`))

  const release = holdConfirmation(transport)
  await authenticatedPage.getByRole('button', RETRY_GOAL).dblclick()
  await expect(authenticatedPage.getByText('Criando seu objetivo…')).toBeVisible()
  release()
  await expect(authenticatedPage.getByRole('button', RETRY_GOAL)).toBeVisible()

  transport.confirmResult = { goalId: GOAL_ID, replayed: false }
  await authenticatedPage.getByRole('button', RETRY_GOAL).click()
  await expect(authenticatedPage).toHaveURL(new RegExp(`/learning/goals/${GOAL_ID}/?$`))

  const keys = callsTo(transport, 'confirmPlanningServer').map(
    (call) => call.data.confirmationKey,
  )
  expect(keys).toHaveLength(3)
  expect(new Set(keys).size).toBe(1)
})

test('reports a lost response as uncertain and recovers the same confirmation (confirmation CA-06, CA-07)', async ({
  authenticatedPage,
  bff,
}) => {
  const transport = transportFor(proposalSession())
  transport.confirmStatus = 500
  await mockPlanner(bff, transport)
  await openPlannerFromHome(authenticatedPage)

  await authenticatedPage.getByRole('button', CREATE_GOAL).click()
  await expect(
    authenticatedPage.getByText('Não conseguimos confirmar a criação do objetivo'),
  ).toBeVisible()
  await expect(authenticatedPage.getByRole('alert')).toHaveCount(0)
  await expect(authenticatedPage.getByLabel('Título')).toBeDisabled()
  await expect(
    authenticatedPage.getByRole('button', { name: 'Reiniciar planejamento' }),
  ).toBeDisabled()
  await expect(authenticatedPage.getByRole('button', { name: 'Cancelar' })).toBeDisabled()
  await expect(authenticatedPage.getByRole('button', VERIFY_GOAL)).toBeEnabled()

  transport.confirmStatus = 200
  transport.confirmResult = { goalId: GOAL_ID, replayed: true }
  await authenticatedPage.getByRole('button', VERIFY_GOAL).click()

  await expect(authenticatedPage).toHaveURL(new RegExp(`/learning/goals/${GOAL_ID}/?$`))
  const keys = callsTo(transport, 'confirmPlanningServer').map(
    (call) => call.data.confirmationKey,
  )
  expect(keys).toHaveLength(2)
  expect(keys[0]).toBe(keys[1])
})

type ConfirmationFrameSet = { creating: string; failed: string }

const DESKTOP_CONFIRMATION_FRAMES: ConfirmationFrameSet = {
  creating: 'BswO3',
  failed: 'qJw1C',
}
const MOBILE_CONFIRMATION_FRAMES: ConfirmationFrameSet = {
  creating: 'FxmF8',
  failed: 'n8OPLr',
}

async function walkThroughConfirmationFrames(
  page: Page,
  bff: BffFixtureContract,
  frames: ConfirmationFrameSet,
) {
  const transport = transportFor(proposalSession())
  transport.confirmResult = { kind: 'unavailable' }
  await mockPlanner(bff, transport)
  await openPlannerFromHome(page)
  await page.getByRole('tab', { name: 'Lista' }).click()
  await expect(page.getByRole('list', { name: LIST_NAME })).toBeVisible()

  const release = holdConfirmation(transport)
  await page.getByRole('button', CREATE_GOAL).click()
  await expect(page.getByText('Criando seu objetivo…')).toBeVisible()
  await expectNoHorizontalScroll(page)
  await capture(page, frames.creating, true)

  transport.confirmResult = {
    kind: 'conflict',
    message: 'Este Skill ainda não está pronto para iniciar.',
  }
  release()
  await expect(page.getByRole('button', RETRY_GOAL)).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('Não foi possível criar o objetivo')
  await expectNoHorizontalScroll(page)
  await capture(page, frames.failed, true)
}

test('renders the approved desktop creation frames without horizontal scroll (confirmation VM-02)', async ({
  authenticatedPage,
  bff,
}) => {
  await authenticatedPage.setViewportSize({ width: 1440, height: 900 })

  await walkThroughConfirmationFrames(authenticatedPage, bff, DESKTOP_CONFIRMATION_FRAMES)
})

test('renders the approved mobile creation frames without horizontal scroll (confirmation VM-02)', async ({
  authenticatedPage,
  bff,
}) => {
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })

  await walkThroughConfirmationFrames(authenticatedPage, bff, MOBILE_CONFIRMATION_FRAMES)
})

type ReviewFrameSet = {
  graph: string
  list: string
  restart: string
  analyzing: string
}

const DESKTOP_REVIEW_FRAMES: ReviewFrameSet = {
  graph: 'bzItW',
  list: 'zX9Ow',
  restart: 'eSaNL',
  analyzing: 'SU4H8',
}

const MOBILE_REVIEW_FRAMES: ReviewFrameSet = {
  graph: 'gXrEP',
  list: 'zCbC0',
  restart: 'NxoN7',
  analyzing: 'lPCGg',
}

async function walkThroughReviewFrames(
  page: Page,
  bff: BffFixtureContract,
  frames: ReviewFrameSet,
) {
  const transport = transportFor(proposalSession())
  await mockPlanner(bff, transport)
  await openPlannerFromHome(page)

  const graph = page.getByRole('region', { name: GRAPH_NAME })
  for (const skill of REVIEW_PROPOSAL.skills) {
    await expect(
      graph.getByRole('article', { name: `Habilidade ${skill.name}` }),
    ).toBeVisible()
  }
  await expectNoHorizontalScroll(page)
  await capture(page, frames.graph, true)

  await page.getByRole('tab', { name: 'Lista' }).click()
  await expect(page.getByRole('list', { name: LIST_NAME })).toBeVisible()
  await expectNoHorizontalScroll(page)
  await capture(page, frames.list, true)

  await page.getByRole('button', { name: 'Reiniciar planejamento' }).click()
  const dialog = page.getByRole('alertdialog', { name: DIALOG_NAME })
  await expect(dialog.getByLabel(INTENT_LABEL)).toHaveValue(INTENT)
  await expectNoHorizontalScroll(page)
  await capture(page, frames.restart)

  const restarted = restartedSession()
  transport.restartResult = restarted
  transport.session = restarted
  await dialog.getByRole('button', { name: 'Iniciar planejamento' }).click()
  await expect(page.getByRole('status')).toContainText('Analisando seu objetivo…')
  await expect(dialog).toBeHidden()
  await expectNoHorizontalScroll(page)
  await capture(page, frames.analyzing)
}

test('renders every approved desktop review frame without horizontal scroll (review VM-02)', async ({
  authenticatedPage,
  bff,
}) => {
  await authenticatedPage.setViewportSize({ width: 1440, height: 900 })

  await walkThroughReviewFrames(authenticatedPage, bff, DESKTOP_REVIEW_FRAMES)
})

test('renders every approved mobile review frame without horizontal scroll (review VM-02)', async ({
  authenticatedPage,
  bff,
}) => {
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })

  await walkThroughReviewFrames(authenticatedPage, bff, MOBILE_REVIEW_FRAMES)
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
