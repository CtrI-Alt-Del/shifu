import type { Page, Route } from '@playwright/test'

import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage } from '../playwright'

/**
 * Controlled, stateful Mentor/memories backend for the SHIFU-101 browser suites.
 * It answers the BFF server functions with the post-mapping shapes the web layer
 * consumes, so it proves rendered contracts and outgoing requests, not real auth
 * or persistence.
 */
export const SESSION_ID = '01J7T8AC91Z5K8M4JQ8C2D6F10'
export const SESSION_TITLE = 'Dúvida no laço for'
export const ATTEMPT_ID = '01J7T8AC91Z5K8M4JQ8C2D6F41'

export const MESSAGE_IDS = {
  firstQuestion: '01J7T8AC91Z5K8M4JQ8C2D6F11',
  firstAnswer: '01J7T8AC91Z5K8M4JQ8C2D6F12',
  knowledgeQuestion: '01J7T8AC91Z5K8M4JQ8C2D6F13',
  knowledgeAnswer: '01J7T8AC91Z5K8M4JQ8C2D6F14',
  unansweredQuestion: '01J7T8AC91Z5K8M4JQ8C2D6F15',
  latestQuestion: '01J7T8AC91Z5K8M4JQ8C2D6F16',
  latestAnswer: '01J7T8AC91Z5K8M4JQ8C2D6F17',
  deleted: '01J7T8AC91Z5K8M4JQ8C2D6F1Z',
} as const

export const MEMORY_IDS = {
  preference: '01J7T8AC91Z5K8M4JQ8C2D6F21',
  interest: '01J7T8AC91Z5K8M4JQ8C2D6F23',
  knowledge: '01J7T8AC91Z5K8M4JQ8C2D6F25',
  difficulty: '01J7T8AC91Z5K8M4JQ8C2D6F26',
  missingOrigin: '01J7T8AC91Z5K8M4JQ8C2D6F27',
  shortExplanations: '01J7T8AC91Z5K8M4JQ8C2D6F28',
  webKnowledge: '01J7T8AC91Z5K8M4JQ8C2D6F29',
  deletedConversation: '01J7T8AC91Z5K8M4JQ8C2D6F2A',
} as const

const ITEM_IDS = {
  created: '01J7T8AC91Z5K8M4JQ8C2D6F31',
  removed: '01J7T8AC91Z5K8M4JQ8C2D6F32',
  unanswered: '01J7T8AC91Z5K8M4JQ8C2D6F33',
  updated: '01J7T8AC91Z5K8M4JQ8C2D6F34',
} as const

type Category =
  | 'explanation_preference'
  | 'declared_knowledge'
  | 'interest_or_intention'
  | 'recurring_difficulty'

export type BackendMemory = {
  id: string
  category: Category
  content: string
  version: number
  createdAt: string
  updatedAt: string
  origins: {
    sessionId: string
    messageId: string | null
    conversationTitle: string | null
    isAvailable: boolean
    declaredAt: string
  }[]
  concepts: { key: string; label: string }[]
}

type BackendItem = {
  id: string
  sourceMessageId: string
  kind: 'created' | 'updated'
  category: Category
  memoryId: string | null
  content: string | null
  previousContent: string | null
  createdAt: string
}

export type ServerFunctionCall = {
  exportName: string
  method: string
  data: Record<string, unknown>
}

type FailableOperation = 'list' | 'get' | 'edit' | 'remove'

export const CATEGORY_LABELS: Record<Category, string> = {
  explanation_preference: 'Preferência de explicação',
  declared_knowledge: 'Conhecimento declarado',
  interest_or_intention: 'Interesse ou intenção',
  recurring_difficulty: 'Dificuldades recorrentes',
}

function origin(
  messageId: string | null,
  isAvailable = true,
  declaredAt = '2026-10-04T15:00:00Z',
) {
  return {
    sessionId: SESSION_ID,
    messageId,
    conversationTitle: isAvailable ? SESSION_TITLE : null,
    isAvailable,
    declaredAt,
  }
}

export function buildMemories(): BackendMemory[] {
  return [
    {
      id: MEMORY_IDS.preference,
      category: 'explanation_preference',
      content: 'Agora prefiro exemplos em Python.',
      version: 2,
      createdAt: '2026-10-04T15:00:00Z',
      updatedAt: '2026-10-08T15:00:00Z',
      origins: [
        origin(MESSAGE_IDS.firstQuestion),
        origin(MESSAGE_IDS.latestQuestion, true, '2026-10-08T15:00:00Z'),
      ],
      concepts: [
        { key: 'exemplo', label: 'Exemplos' },
        { key: 'python', label: 'Python' },
      ],
    },
    {
      id: MEMORY_IDS.interest,
      category: 'interest_or_intention',
      content: 'Quero criar aplicações web.',
      version: 1,
      createdAt: '2026-10-07T15:00:00Z',
      updatedAt: '2026-10-07T15:00:00Z',
      origins: [origin(MESSAGE_IDS.unansweredQuestion, true, '2026-10-07T15:00:00Z')],
      concepts: [],
    },
    {
      id: MEMORY_IDS.knowledge,
      category: 'declared_knowledge',
      content: 'Conheço variáveis e condicionais em Python.',
      version: 1,
      createdAt: '2026-10-03T15:00:00Z',
      updatedAt: '2026-10-03T15:00:00Z',
      origins: [origin(MESSAGE_IDS.firstQuestion, true, '2026-10-03T15:00:00Z')],
      concepts: [{ key: 'python', label: 'Python' }],
    },
    {
      id: MEMORY_IDS.difficulty,
      category: 'recurring_difficulty',
      content: 'Confundo exibir e retornar valores.',
      version: 1,
      createdAt: '2026-10-02T15:00:00Z',
      updatedAt: '2026-10-02T15:00:00Z',
      origins: [
        origin(MESSAGE_IDS.firstQuestion, true, '2026-10-02T15:00:00Z'),
        origin(null, false, '2026-10-01T15:00:00Z'),
      ],
      concepts: [
        { key: 'funcao', label: 'Funções' },
        { key: 'retorno de valor', label: 'Retorno de valores' },
      ],
    },
    {
      id: MEMORY_IDS.missingOrigin,
      category: 'interest_or_intention',
      content: 'Quero construir um portfólio.',
      version: 1,
      createdAt: '2026-10-02T12:00:00Z',
      updatedAt: '2026-10-02T12:00:00Z',
      origins: [origin(MESSAGE_IDS.deleted, true, '2026-10-02T12:00:00Z')],
      concepts: [],
    },
    {
      id: MEMORY_IDS.shortExplanations,
      category: 'explanation_preference',
      content: 'Prefiro explicações passo a passo.',
      version: 1,
      createdAt: '2026-10-01T12:00:00Z',
      updatedAt: '2026-10-01T12:00:00Z',
      origins: [origin(MESSAGE_IDS.firstQuestion, true, '2026-10-01T12:00:00Z')],
      concepts: [],
    },
    {
      id: MEMORY_IDS.webKnowledge,
      category: 'declared_knowledge',
      content: 'Tenho noções de HTML e CSS.',
      version: 1,
      createdAt: '2026-09-30T12:00:00Z',
      updatedAt: '2026-09-30T12:00:00Z',
      origins: [origin(MESSAGE_IDS.firstQuestion, true, '2026-09-30T12:00:00Z')],
      concepts: [],
    },
    {
      id: MEMORY_IDS.deletedConversation,
      category: 'recurring_difficulty',
      content: 'Tenho dificuldade em rastrear valores em laços.',
      version: 1,
      createdAt: '2026-09-29T12:00:00Z',
      updatedAt: '2026-09-29T12:00:00Z',
      origins: [origin(null, false, '2026-09-29T12:00:00Z')],
      concepts: [{ key: 'retorno de valor', label: 'Retorno de valores' }],
    },
  ]
}

function buildItems(): BackendItem[] {
  return [
    {
      id: ITEM_IDS.created,
      sourceMessageId: MESSAGE_IDS.firstQuestion,
      kind: 'created',
      category: 'explanation_preference',
      memoryId: MEMORY_IDS.preference,
      content: 'Prefiro exemplos curtos em JavaScript.',
      previousContent: null,
      createdAt: '2026-10-04T15:00:05Z',
    },
    {
      id: ITEM_IDS.removed,
      sourceMessageId: MESSAGE_IDS.knowledgeQuestion,
      kind: 'created',
      category: 'declared_knowledge',
      memoryId: null,
      content: null,
      previousContent: null,
      createdAt: '2026-10-05T15:00:05Z',
    },
    {
      id: ITEM_IDS.unanswered,
      sourceMessageId: MESSAGE_IDS.unansweredQuestion,
      kind: 'created',
      category: 'interest_or_intention',
      memoryId: MEMORY_IDS.interest,
      content: 'Quero criar aplicações web.',
      previousContent: null,
      createdAt: '2026-10-07T15:00:05Z',
    },
    {
      id: ITEM_IDS.updated,
      sourceMessageId: MESSAGE_IDS.latestQuestion,
      kind: 'updated',
      category: 'explanation_preference',
      memoryId: MEMORY_IDS.preference,
      content: 'Agora prefiro exemplos em Python.',
      previousContent: 'Prefiro exemplos curtos em JavaScript.',
      createdAt: '2026-10-08T15:00:05Z',
    },
  ]
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

export const CONVERSATION_TEXTS = {
  firstQuestion: 'Prefiro exemplos curtos em JavaScript.',
  knowledgeQuestion: 'Sei Python.',
  unansweredQuestion: 'Quero criar aplicações web.',
  latestQuestion: 'Agora prefiro exemplos em Python.',
  answer: 'Anotado. Vou considerar isso nas próximas explicações.',
} as const

const MESSAGE_PAGES: Record<
  string,
  { items: ReturnType<typeof message>[]; nextCursor: string | null }
> = {
  first: {
    items: [
      message(
        MESSAGE_IDS.latestQuestion,
        'learner',
        CONVERSATION_TEXTS.latestQuestion,
        '2026-10-08T15:00:00Z',
      ),
      message(
        MESSAGE_IDS.latestAnswer,
        'mentor',
        CONVERSATION_TEXTS.answer,
        '2026-10-08T15:00:02Z',
        MESSAGE_IDS.latestQuestion,
      ),
    ],
    nextCursor: 'older-1',
  },
  'older-1': {
    items: [
      message(
        MESSAGE_IDS.knowledgeQuestion,
        'learner',
        CONVERSATION_TEXTS.knowledgeQuestion,
        '2026-10-05T15:00:00Z',
      ),
      message(
        MESSAGE_IDS.knowledgeAnswer,
        'mentor',
        CONVERSATION_TEXTS.answer,
        '2026-10-05T15:00:02Z',
        MESSAGE_IDS.knowledgeQuestion,
      ),
      message(
        MESSAGE_IDS.unansweredQuestion,
        'learner',
        CONVERSATION_TEXTS.unansweredQuestion,
        '2026-10-07T15:00:00Z',
      ),
    ],
    nextCursor: 'older-2',
  },
  'older-2': {
    items: [
      message(
        MESSAGE_IDS.firstQuestion,
        'learner',
        CONVERSATION_TEXTS.firstQuestion,
        '2026-10-04T15:00:00Z',
      ),
      message(
        MESSAGE_IDS.firstAnswer,
        'mentor',
        CONVERSATION_TEXTS.answer,
        '2026-10-04T15:00:02Z',
        MESSAGE_IDS.firstQuestion,
      ),
    ],
    nextCursor: null,
  },
}

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
  if (record.t === 0) return record.s
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

function serverFnInput(request: {
  postData: () => string | null
  url: () => string
}): Record<string, unknown> {
  const body = request.postData()
  if (body) {
    try {
      const serialized = JSON.parse(body) as { t?: unknown }
      const input = unwrapServerFunctionInput(
        decodeServerFunctionValue(serialized.t ? serialized.t : serialized),
      )
      if (Object.keys(input).length) return input
    } catch {
      // GET server functions carry their input in the URL instead.
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
      // Preserve ordinary query parameters below.
    }
  }
  return Object.fromEntries(url.searchParams.entries())
}

function normalize(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase()
}

export type MemoriesBackend = {
  calls: ServerFunctionCall[]
  callsOf: (operation: FailableOperation | 'session') => ServerFunctionCall[]
  readMemories: () => BackendMemory[]
  setMemories: (memories: BackendMemory[]) => void
  failNext: (operation: FailableOperation, count?: number) => void
  holdList: () => () => void
  bumpVersion: (memoryId: string, content: string) => void
}

const OPERATION_EXPORTS: Record<FailableOperation | 'session', string> = {
  list: 'listLearnerMemoriesServer',
  get: 'getLearnerMemoryServer',
  edit: 'editLearnerMemoryServer',
  remove: 'removeLearnerMemoryServer',
  session: 'getMentorSessionServer',
}

export async function installMentorMemoriesBackend(
  page: Page,
  initialMemories: BackendMemory[] = buildMemories(),
): Promise<MemoriesBackend> {
  const calls: ServerFunctionCall[] = []
  let memories = initialMemories
  const items = buildItems()
  const failures = new Map<FailableOperation, number>()
  let listGate: Promise<void> | null = null
  const session = {
    id: SESSION_ID,
    title: SESSION_TITLE,
    createdAt: '2026-10-04T15:00:00Z',
    updatedAt: '2026-10-08T15:00:00Z',
    lastActivityAt: '2026-10-08T15:00:00Z',
  }

  function fulfillJson(route: Route, result: unknown, status = 200) {
    return route.fulfill({
      body: JSON.stringify({ result }),
      contentType: 'application/json',
      status,
    })
  }

  function failRequest(route: Route) {
    return route.fulfill({
      body: JSON.stringify({ error: 'Internal Server Error' }),
      contentType: 'application/json',
      status: 500,
    })
  }

  function consumeFailure(operation: FailableOperation): boolean {
    const remaining = failures.get(operation) ?? 0
    if (remaining <= 0) return false
    failures.set(operation, remaining - 1)
    return true
  }

  function detail(cursor: unknown) {
    return {
      session,
      messages: MESSAGE_PAGES[typeof cursor === 'string' ? cursor : 'first'],
      pendingLearnerMessageId: null,
      response: {
        attemptId: ATTEMPT_ID,
        learnerMessageId: MESSAGE_IDS.latestQuestion,
        status: 'completed',
        blocks: [
          {
            blockKey: 'noted',
            ordinal: 0,
            intent: null,
            content: CONVERSATION_TEXTS.answer,
            sources: [],
          },
        ],
        consultations: [],
        lastSequence: 3,
        failureCode: null,
        progress: null,
      },
      summary: { current: null, failureAfterMessageId: null },
      memoryItems: items,
    }
  }

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

    const operation = (
      Object.entries(OPERATION_EXPORTS) as [FailableOperation | 'session', string][]
    ).find(([, name]) => exportName.includes(name))?.[0]

    if (exportName.includes('listMentorSessionsServer')) {
      await fulfillJson(route, { items: [session], nextCursor: null })
      return
    }
    if (!operation) {
      await route.fallback()
      return
    }

    calls.push({ exportName, method: request.method(), data })

    if (operation === 'session') {
      await fulfillJson(route, detail(data.cursor))
      return
    }

    if (operation === 'list' && listGate) await listGate

    if (consumeFailure(operation as FailableOperation)) {
      await failRequest(route)
      return
    }

    if (operation === 'list') {
      const query = normalize(String(data.q ?? ''))
      const category = typeof data.category === 'string' ? data.category : null
      const result = memories
        .filter(
          (memory) =>
            normalize(memory.content).includes(query) &&
            (!category || memory.category === category),
        )
        .sort(
          (left, right) =>
            right.updatedAt.localeCompare(left.updatedAt) ||
            left.id.localeCompare(right.id),
        )
      await fulfillJson(route, result)
      return
    }

    const memoryId = String(data.memoryId ?? '')
    const memory = memories.find((candidate) => candidate.id === memoryId)

    if (operation === 'get') {
      await fulfillJson(route, memory ? { kind: 'ok', memory } : { kind: 'not-found' })
      return
    }

    if (operation === 'edit') {
      if (!memory) {
        await fulfillJson(route, { kind: 'not-found' })
        return
      }
      const content = String(data.content ?? '').trim()
      if (data.expectedVersion !== memory.version) {
        await fulfillJson(route, { kind: 'conflict' })
        return
      }
      if (!content || [...content].length > 280) {
        await fulfillJson(route, { kind: 'invalid' })
        return
      }
      memory.content = content
      memory.version += 1
      memory.updatedAt = '2026-10-21T12:00:00Z'
      await fulfillJson(route, { kind: 'ok', memory })
      return
    }

    memories = memories.filter((candidate) => candidate.id !== memoryId)
    for (const item of items) {
      if (item.memoryId === memoryId) {
        item.memoryId = null
        item.content = null
        item.previousContent = null
      }
    }
    await fulfillJson(route, { kind: 'ok' })
  })

  return {
    calls,
    callsOf: (operation) =>
      calls.filter((call) => call.exportName.includes(OPERATION_EXPORTS[operation])),
    readMemories: () => memories,
    setMemories: (next) => {
      memories = next
    },
    failNext: (operation, count = 1) => {
      failures.set(operation, count)
    },
    holdList: () => {
      let release: () => void = () => undefined
      listGate = new Promise<void>((resolve) => {
        release = () => {
          listGate = null
          resolve()
        }
      })
      return release
    },
    bumpVersion: (memoryId, content) => {
      const memory = memories.find((candidate) => candidate.id === memoryId)
      if (!memory) throw new Error(`Unknown memory ${memoryId}`)
      memory.content = content
      memory.version += 1
      memory.updatedAt = '2026-10-21T11:00:00Z'
    },
  }
}

type MemoriesSearch = {
  q?: string
  category?: string
  view?: string
  memory?: string
}

type TanStackRouter = {
  navigate: (options: { to: string; search?: Record<string, unknown> }) => Promise<void>
}

/** Client-side navigation keeps the mocked session; a document load would run the real auth. */
export async function openMemoriesPage(page: Page, search: MemoriesSearch = {}) {
  await navigateWithSearch(page, ROUTES.intelligenceMemories, search)
  await expect(page.getByRole('heading', { level: 1, name: 'Memórias' })).toBeVisible()
}

export async function navigateWithSearch(
  page: Page,
  to: string,
  search: Record<string, unknown>,
) {
  if (!Object.keys(search).length) {
    await navigateAuthenticatedPage(page, to)
    return
  }
  await page.evaluate(
    ({ destination, destinationSearch }) => {
      const router = (window as typeof window & { __TSR_ROUTER__: TanStackRouter })
        .__TSR_ROUTER__
      return router.navigate({ to: destination, search: destinationSearch })
    },
    { destination: to, destinationSearch: search },
  )
}

export async function openMentorPage(page: Page, search: Record<string, unknown> = {}) {
  await navigateWithSearch(page, ROUTES.intelligence, search)
}

export async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)
}

export function searchOf(page: Page): URLSearchParams {
  return new URL(page.url()).searchParams
}

export async function openMentorFabConversation(page: Page) {
  await navigateAuthenticatedPage(page, ROUTES.gamification)
  await page.getByRole('button', { name: 'Abrir Mentor' }).click()
  await page.getByRole('button', { name: 'Histórico de conversas' }).click()
  await page.getByRole('button', { name: SESSION_TITLE, exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: SESSION_TITLE })).toBeVisible()
}
