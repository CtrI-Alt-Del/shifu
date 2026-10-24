import {
  exerciseDictationStates,
  exerciseBrowserManagedControls,
} from '../support/native-dictation'
import {
  exerciseSummaryFailure,
  exerciseSummaryJourney,
} from '../support/mentor-summary-journey'
import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { ROUTES } from '../../src/constants/routes'
import {
  ACTION_IDS,
  ADD_JUSTIFICATION,
  BLOCK_REASON,
  buildPickerProposal,
  buildProposal,
  GOAL_TITLE,
  installMentorActionsBackend,
  openMentorActionsPage,
  OTHER_GOAL_TITLE,
  outcomeOf,
  SKILL_NAME,
} from '../support/mentor-actions-backend'
import {
  CONVERSATION_TEXTS,
  expectNoHorizontalOverflow,
  installMentorMemoriesBackend,
  MEMORY_IDS,
  MESSAGE_IDS,
  openMemoriesPage,
  openMentorPage,
  searchOf,
  SESSION_ID,
  SESSION_TITLE,
} from '../support/mentor-memories-backend'

type MentorSessionFixture = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  lastActivityAt: string
}

type MentorDetailFixture = {
  session: MentorSessionFixture
  messages: {
    items: Array<{
      id: string
      sessionId: string
      role: 'learner' | 'mentor'
      content: string
      createdAt: string
      inReplyToMessageId: string | null
      attachments: []
    }>
    nextCursor: string | null
  }
  pendingLearnerMessageId: string | null
  memoryItems?: unknown[]
}

type MentorServerFunctionCall = {
  exportName: string
  method: string
  url: string
  data: Record<string, unknown>
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
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return value

  const record = value as Record<string, unknown>
  if (typeof record.t !== 'number') return value

  if (record.t === 1) return record.s
  if (record.t === 2) return undefined
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

function serverFnInput(request: { postData: () => string | null; url: () => string }) {
  const body = request.postData()
  if (body) {
    try {
      const serialized = JSON.parse(body) as { t?: unknown }
      return unwrapServerFunctionInput(
        decodeServerFunctionValue(serialized.t ? serialized.t : serialized),
      )
    } catch {
      // GET server functions may carry their input in the request URL instead.
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

function normalizeSearch(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase()
}

test('protects intelligence and renders it for an active session', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, '/intelligence/')

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Nova conversa',
    }),
  ).toBeVisible()

  await authenticatedPage.context().clearCookies()
  await authenticatedPage.goto('/intelligence/')

  await expect(authenticatedPage).toHaveURL(/\/login\/?$/)
})

test('keeps the selected route, editable draft, history, search, rename and deletion synchronized', async ({
  authenticatedPage,
  bff,
}) => {
  const sessions: MentorSessionFixture[] = [
    {
      id: '01J7T8AC91Z5K8M4JQ8C2D6F0B',
      title: 'Plano semanal',
      createdAt: '2026-10-09T12:00:00Z',
      updatedAt: '2026-10-09T12:00:00Z',
      lastActivityAt: '2026-10-09T12:00:00Z',
    },
    {
      id: '01J7T8AC91Z5K8M4JQ8C2D6F0C',
      title: 'Álgebra inicial',
      createdAt: '2026-10-09T11:00:00Z',
      updatedAt: '2026-10-09T11:00:00Z',
      lastActivityAt: '2026-10-09T11:00:00Z',
    },
  ]
  const details = new Map<string, MentorDetailFixture>(
    sessions.map((session, index) => [
      session.id,
      {
        session,
        messages: {
          items: [
            {
              id: `mentor-message-${index + 1}`,
              sessionId: session.id,
              role: 'learner',
              content:
                index === 0 ? 'Quero organizar meu estudo.' : 'Como começo álgebra?',
              createdAt: session.createdAt,
              inReplyToMessageId: null,
              attachments: [],
            },
          ],
          nextCursor: null,
        },
        pendingLearnerMessageId: `mentor-message-${index + 1}`,
        memoryItems: [],
      },
    ]),
  )
  const calls: MentorServerFunctionCall[] = []

  await bff.route(async (route) => {
    const request = route.request()
    const exportName = serverFnExport(request.url())
    const data = serverFnInput(request)

    if (exportName?.startsWith('getAchievements_')) {
      await route.fulfill({
        body: JSON.stringify({
          result: {
            kind: 'success',
            overview: {
              level: 1,
              totalXp: 0,
              xpForNextLevel: 100,
              achievements: [],
            },
          },
        }),
        contentType: 'application/json',
        status: 200,
      })
      return
    }

    const call: MentorServerFunctionCall = {
      exportName: exportName ?? '',
      method: request.method(),
      url: request.url(),
      data,
    }

    if (exportName?.includes('listMentorSessionsServer')) {
      calls.push(call)
      const search = normalizeSearch(String(data.search ?? ''))
      const items = sessions.filter((session) =>
        normalizeSearch(session.title).includes(search),
      )
      await route.fulfill({
        body: JSON.stringify({ result: { items, nextCursor: null } }),
        contentType: 'application/json',
        status: 200,
      })
      return
    }

    if (exportName?.includes('getMentorSessionServer')) {
      calls.push(call)
      const detail = details.get(String(data.sessionId ?? ''))
      await route.fulfill({
        body: JSON.stringify({ result: detail ?? null }),
        contentType: 'application/json',
        status: detail ? 200 : 404,
      })
      return
    }

    if (exportName?.includes('createMentorSessionServer')) {
      calls.push(call)
      const session: MentorSessionFixture = {
        id: '01J7T8AC91Z5K8M4JQ8C2D6F0D',
        title: String(data.firstMessage ?? '').slice(0, 120),
        createdAt: '2026-10-09T13:00:00Z',
        updatedAt: '2026-10-09T13:00:00Z',
        lastActivityAt: '2026-10-09T13:00:00Z',
      }
      sessions.unshift(session)
      const detail: MentorDetailFixture = {
        session,
        messages: { items: [], nextCursor: null },
        pendingLearnerMessageId: null,
        memoryItems: [],
      }
      details.set(session.id, detail)
      await route.fulfill({
        body: JSON.stringify({ result: detail }),
        contentType: 'application/json',
        status: 200,
      })
      return
    }

    if (exportName?.includes('renameMentorSessionServer')) {
      calls.push(call)
      const sessionId = String(data.sessionId ?? '')
      const session = sessions.find((item) => item.id === sessionId)
      if (session) session.title = String(data.title ?? '')
      const detail = details.get(sessionId)
      if (detail && session) detail.session.title = session.title
      await route.fulfill({
        body: JSON.stringify({ result: session ?? null }),
        contentType: 'application/json',
        status: session ? 200 : 404,
      })
      return
    }

    if (exportName?.includes('removeMentorSessionServer')) {
      calls.push(call)
      const sessionId = String(data.sessionId ?? '')
      const sessionIndex = sessions.findIndex((session) => session.id === sessionId)
      if (sessionIndex >= 0) sessions.splice(sessionIndex, 1)
      details.delete(sessionId)
      await route.fulfill({
        body: JSON.stringify({ result: null }),
        contentType: 'application/json',
        status: 200,
      })
      return
    }

    await route.fallback()
  })

  await authenticatedPage.setViewportSize({ width: 1280, height: 800 })
  await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamification)
  await authenticatedPage
    .getByRole('navigation', { name: 'Navegação principal' })
    .getByRole('link', { name: 'Mentor' })
    .click()
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ROUTES.intelligence}/?$`))
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Nova conversa' }),
  ).toBeVisible()

  const firstSession = sessions[0]
  await authenticatedPage
    .getByRole('button', { name: /^Plano semanal(?: , conversa selecionada)?$/ })
    .click()
  await expect(authenticatedPage).toHaveURL(
    new RegExp(`${ROUTES.intelligence}\\?session=${firstSession.id}$`),
  )
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Plano semanal' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Quero organizar meu estudo.')).toBeVisible()

  await authenticatedPage
    .getByRole('button', { name: 'Nova conversa', exact: true })
    .click()
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ROUTES.intelligence}/?$`))
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Nova conversa' }),
  ).toBeVisible()
  const composer = authenticatedPage.getByRole('textbox', {
    name: 'Escreva sua mensagem para o Mentor',
  })
  await expect(composer).toBeEnabled()
  await composer.fill('Este rascunho ainda não foi aceito.')
  await expect(composer).toHaveValue('Este rascunho ainda não foi aceito.')
  expect(
    calls.some((call) => call.exportName.includes('createMentorSessionServer')),
  ).toBe(false)

  const secondSession = sessions[1]
  await authenticatedPage
    .getByRole('button', { name: /^Álgebra inicial(?: , conversa selecionada)?$/ })
    .click()
  await expect(authenticatedPage).toHaveURL(
    new RegExp(`${ROUTES.intelligence}\\?session=${secondSession.id}$`),
  )
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Álgebra inicial' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Como começo álgebra?')).toBeVisible()

  const selectedSessionUrl = new RegExp(
    `${ROUTES.intelligence}\\?session=${secondSession.id}$`,
  )
  await authenticatedPage.goBack()
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ROUTES.gamification}/?$`))
  await expect(
    authenticatedPage.getByRole('main').filter({ hasText: 'Gamificação' }),
  ).toBeVisible()
  // The Calendário tab is the default and fetches on mount; this suite does not
  // mock that request. Let it settle before navigating forward, or the in-flight
  // response races the next route on a slow runner.
  await expect(
    authenticatedPage.getByLabel('Carregando calendário de prática'),
  ).toBeHidden()
  await authenticatedPage.goForward()
  await expect(authenticatedPage).toHaveURL(selectedSessionUrl)
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Álgebra inicial' }),
  ).toBeVisible()
  await authenticatedPage
    .getByRole('button', { name: 'Nova conversa', exact: true })
    .click()
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ROUTES.intelligence}/?$`))
  const detailReadsBeforeDeepLink = calls.filter(
    (call) =>
      call.exportName.includes('getMentorSessionServer') &&
      call.data.sessionId === secondSession.id,
  ).length
  await authenticatedPage.evaluate((sessionId) => {
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

    return router.navigate({
      to: '/intelligence',
      search: { session: sessionId },
    })
  }, secondSession.id)
  await expect(authenticatedPage).toHaveURL(selectedSessionUrl)
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Álgebra inicial' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('Como começo álgebra?')).toBeVisible()
  await expect
    .poll(
      () =>
        calls.filter(
          (call) =>
            call.exportName.includes('getMentorSessionServer') &&
            call.data.sessionId === secondSession.id,
        ).length,
    )
    .toBeGreaterThan(detailReadsBeforeDeepLink)

  const search = authenticatedPage.getByRole('searchbox', {
    name: 'Buscar conversa por título',
  })
  await search.fill('algebra')
  await expect
    .poll(() =>
      calls.some(
        (call) =>
          call.exportName.includes('listMentorSessionsServer') &&
          call.data.search === 'algebra',
      ),
    )
    .toBe(true)
  await expect(
    authenticatedPage.getByRole('button', {
      name: /^Álgebra inicial(?: , conversa selecionada)?$/,
    }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', { name: /^Plano semanal$/ }),
  ).toHaveCount(0)

  await authenticatedPage
    .getByRole('button', { name: 'Renomear Álgebra inicial' })
    .click()
  const renameDialog = authenticatedPage.getByRole('alertdialog')
  await renameDialog.getByLabel('Título da conversa').fill('Álgebra revisada')
  await renameDialog.getByRole('button', { name: 'Salvar' }).click()
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Álgebra revisada' }),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('button', {
      name: /^Álgebra revisada(?: , conversa selecionada)?$/,
    }),
  ).toBeVisible()

  await authenticatedPage
    .getByRole('button', { name: 'Excluir Álgebra revisada' })
    .click()
  const removeDialog = authenticatedPage.getByRole('alertdialog')
  await removeDialog.getByRole('button', { name: 'Excluir conversa' }).click()
  await expect(authenticatedPage).toHaveURL(new RegExp(`${ROUTES.intelligence}/?$`))
  await expect(
    authenticatedPage.getByRole('heading', { level: 1, name: 'Nova conversa' }),
  ).toBeVisible()
  await expect(composer).toBeEnabled()
  await expect(
    authenticatedPage.getByRole('button', {
      name: /^Álgebra revisada(?: , conversa selecionada)?$/,
    }),
  ).toHaveCount(0)

  const detailCall = calls.find(
    (call) =>
      call.exportName.includes('getMentorSessionServer') &&
      call.data.sessionId === secondSession.id,
  )
  expect(detailCall).toMatchObject({
    method: 'GET',
    data: { sessionId: secondSession.id },
  })
  const renameCall = calls.find((call) =>
    call.exportName.includes('renameMentorSessionServer'),
  )
  expect(renameCall).toMatchObject({
    method: 'POST',
    data: { sessionId: secondSession.id, title: 'Álgebra revisada' },
  })
  const removeCall = calls.find((call) =>
    call.exportName.includes('removeMentorSessionServer'),
  )
  expect(removeCall).toMatchObject({
    method: 'POST',
    data: { sessionId: secondSession.id },
  })
  expect(
    calls.some((call) => call.exportName.includes('createMentorSessionServer')),
  ).toBe(false)
})

test('renders native dictation states on page at 1440', async ({ authenticatedPage }) => {
  await exerciseDictationStates(authenticatedPage, 'page', 1440)
})
test('renders native dictation states on page at 390', async ({ authenticatedPage }) => {
  await exerciseDictationStates(authenticatedPage, 'page', 390)
})

test('renders native dictation states without a local language pack on page', async ({
  authenticatedPage,
}) => {
  await exerciseBrowserManagedControls(authenticatedPage, 'page')
})

test('summarizes the context, reads the summary and reveals the originals on page at 1440', async ({
  authenticatedPage,
}) => {
  await exerciseSummaryJourney(authenticatedPage, 'page', 1440)
})
test('summarizes the context, reads the summary and reveals the originals on page at 390', async ({
  authenticatedPage,
}) => {
  await exerciseSummaryJourney(authenticatedPage, 'page', 390)
})
test('shows the summarization failure notice after its learner message on page', async ({
  authenticatedPage,
}) => {
  await exerciseSummaryFailure(authenticatedPage, 'page')
})

// SHIFU-101: memory markers, the Memórias entry and the origin deep link. Browser
// integration with mocked transport; it does not prove real persistence.
test.describe('Mentor page memories', () => {
  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 390, height: 844 },
  ]) {
    test(`opens the Memórias page from the header link at ${viewport.width}`, async ({
      authenticatedPage: page,
    }) => {
      await page.setViewportSize(viewport)
      await installMentorMemoriesBackend(page)
      await openMentorPage(page)
      await expect(
        page.getByRole('heading', { level: 1, name: 'Nova conversa' }),
      ).toBeVisible()

      const link = page.getByRole('link', { name: 'Memórias' })
      await expect(link).toBeVisible()
      expect((await link.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(44)
      await link.click()

      await expect(page).toHaveURL(/\/intelligence\/memories\/?(\?.*)?$/)
      await expect(
        page.getByRole('heading', { level: 1, name: 'Memórias' }),
      ).toBeVisible()
      await expect(
        page.getByRole('list', { name: 'Lista de memórias' }).getByRole('button'),
      ).toHaveCount(8)
      await expectNoHorizontalOverflow(page)
    })
  }

  test('places the markers after the answer of their turn and links to the memory', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await installMentorMemoriesBackend(page)
    await openMentorPage(page, { session: SESSION_ID })
    await expect(
      page.getByRole('heading', { level: 1, name: SESSION_TITLE }),
    ).toBeVisible()

    const answer = page.getByRole('list', { name: 'Resposta do Mentor' })
    const trailing = page.getByRole('list', { name: 'Memórias desta resposta' })
    await expect(answer).toContainText(CONVERSATION_TEXTS.answer)
    await expect(trailing).toContainText('Memória atualizada')
    await expect(trailing).toContainText('Antes: Prefiro exemplos curtos em JavaScript.')
    await expect(trailing).toContainText('Agora: Agora prefiro exemplos em Python.')
    expect(
      await trailing.evaluate(
        (element, other) =>
          Boolean(
            element.compareDocumentPosition(document.querySelector(other) as Element) &
              Node.DOCUMENT_POSITION_PRECEDING,
          ),
        '[aria-label="Resposta do Mentor"]',
      ),
    ).toBe(true)
    // Items whose source message is in an older, unloaded page are not shown yet.
    await expect(page.getByText('Memória criada')).toHaveCount(0)

    // The list also loads older pages on its own near the top, so the explicit button can
    // be replaced between the lookup and the click; retry until the page it loads is shown.
    const loadOlderUntilVisible = async (messageId: string) =>
      expect(async () => {
        const target = page.locator(`[data-message-id="${messageId}"]`)
        if (!(await target.isVisible())) {
          await page
            .getByRole('button', { name: 'Carregar mensagens anteriores' })
            .click({ timeout: 2_000 })
        }
        await expect(target).toBeVisible({ timeout: 2_000 })
      }).toPass({ timeout: 15_000 })

    await loadOlderUntilVisible(MESSAGE_IDS.unansweredQuestion)
    await loadOlderUntilVisible(MESSAGE_IDS.firstQuestion)

    const items = page
      .getByRole('list', { name: 'Mensagens da conversa' })
      .getByRole('listitem')
    await expect(items).toHaveCount(9)
    const texts = await items.allInnerTexts()
    const order = [
      CONVERSATION_TEXTS.firstQuestion,
      CONVERSATION_TEXTS.answer,
      'Memória criada',
      CONVERSATION_TEXTS.knowledgeQuestion,
      CONVERSATION_TEXTS.answer,
      'Memória excluída',
      CONVERSATION_TEXTS.unansweredQuestion,
      'Memória criada',
      CONVERSATION_TEXTS.latestQuestion,
    ]
    order.forEach((content, index) => {
      expect(texts[index]).toContain(content)
    })
    expect(texts[2]).toContain(
      'Preferência de explicação: Prefiro exemplos curtos em JavaScript.',
    )
    expect(texts[7]).toContain('Interesse ou intenção: Quero criar aplicações web.')
    expect(texts[5]).not.toContain('Sei Python.')
    await expect(items.nth(5).getByRole('link')).toHaveCount(0)
    await expect(items.nth(2).getByRole('link', { name: 'Ver memória' })).toBeVisible()
    await expectNoHorizontalOverflow(page)

    await trailing.getByRole('link', { name: 'Ver memória' }).click()

    await expect(page).toHaveURL(/\/intelligence\/memories\/?\?/)
    expect(searchOf(page).get('memory')).toBe(MEMORY_IDS.preference)
    await expect(
      page
        .getByRole('region', { name: 'Detalhes da memória' })
        .getByRole('heading', { level: 2, name: 'Agora prefiro exemplos em Python.' }),
    ).toBeVisible()
  })

  test('follows an origin link, loads older pages until the message appears and clears the URL', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { memory: MEMORY_IDS.preference })

    await page
      .getByRole('region', { name: 'Detalhes da memória' })
      .getByRole('link', { name: SESSION_TITLE })
      .first()
      .click()

    const origin = page.locator(`[data-message-id="${MESSAGE_IDS.firstQuestion}"]`)
    await expect(origin).toBeVisible()
    await expect(origin).toBeFocused()
    await expect.poll(() => searchOf(page).get('message')).toBeNull()
    expect(searchOf(page).get('session')).toBe(SESSION_ID)
    expect(
      backend
        .callsOf('session')
        .map((call) => call.data.cursor)
        .filter(Boolean),
    ).toEqual(['older-1', 'older-2'])
    await expect(origin).toContainText(CONVERSATION_TEXTS.firstQuestion)
  })

  test('opens the conversation normally when the origin message no longer exists', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const backend = await installMentorMemoriesBackend(page)
    await openMemoriesPage(page, { memory: MEMORY_IDS.missingOrigin })

    await page
      .getByRole('region', { name: 'Detalhes da memória' })
      .getByRole('link', { name: SESSION_TITLE })
      .click()

    await expect(
      page.getByRole('heading', { level: 1, name: SESSION_TITLE }),
    ).toBeVisible()
    await expect.poll(() => searchOf(page).get('message')).toBeNull()
    expect(searchOf(page).get('session')).toBe(SESSION_ID)
    await expect(page.getByRole('alert')).toHaveCount(0)
    await expect(page.locator(`[data-message-id="${MESSAGE_IDS.deleted}"]`)).toHaveCount(
      0,
    )
    expect(
      backend
        .callsOf('session')
        .map((call) => call.data.cursor)
        .filter(Boolean),
    ).toEqual(['older-1', 'older-2'])
  })

  test('ignores an invalid message search value without paging', async ({
    authenticatedPage: page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    const backend = await installMentorMemoriesBackend(page)

    await openMentorPage(page, { session: SESSION_ID, message: 'not-a-ulid' })

    await expect(
      page.getByRole('heading', { level: 1, name: SESSION_TITLE }),
    ).toBeVisible()
    expect(searchOf(page).get('message')).toBeNull()
    expect(
      backend
        .callsOf('session')
        .map((call) => call.data.cursor)
        .filter(Boolean),
    ).toEqual([])
  })
})

// SHIFU-104: confirmed Mentor actions on the page (mocked BFF transport and response stream).
test.describe('Mentor page confirmed actions', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
  })

  test('confirms an addition with the keyboard, announces the result and unblocks the composer after the refreshed detail', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installMentorActionsBackend(page, {
      proposal: buildProposal('add_skill'),
    })
    await openMentorActionsPage(page)

    const card = page.getByRole('region', { name: `Adicionar ${SKILL_NAME}?` })
    await expect(card).toBeVisible()
    await expect(card).toContainText(`Objetivo: ${GOAL_TITLE}`)
    await expect(card).toContainText(ADD_JUSTIFICATION)
    await expect(page.getByRole('textbox')).toBeDisabled()
    await expect(page.getByText(BLOCK_REASON)).toBeVisible()
    await expect(
      page.getByRole('button', { name: 'Anexar arquivo ou imagem' }),
    ).toBeDisabled()

    await card.getByRole('button', { name: 'Recusar' }).focus()
    await page.keyboard.press('Tab')
    await expect(card.getByRole('button', { name: 'Adicionar habilidade' })).toBeFocused()
    await page.keyboard.press('Enter')

    const done = page.getByRole('region', { name: `${SKILL_NAME} adicionada` })
    await expect(done).toBeVisible()
    await expect(done.getByRole('status')).toContainText('Adição concluída')
    await expect(done.getByRole('status')).toBeFocused()
    await expect(done.getByRole('button')).toHaveCount(0)
    await expect(done.getByRole('link', { name: 'Ver Objetivo' })).toHaveAttribute(
      'href',
      `/learning/goals/${ACTION_IDS.goal}`,
    )

    const [confirmation] = backend.callsOf('confirmMentorSkillAdditionServer')
    expect(backend.callsOf('confirmMentorSkillAdditionServer')).toHaveLength(1)
    expect(confirmation).toMatchObject({
      method: 'POST',
      data: {
        goalId: ACTION_IDS.goal,
        confirmationId: ACTION_IDS.proposal,
        skillId: ACTION_IDS.skill,
        justification: ADD_JUSTIFICATION,
      },
    })
    await expect(page.getByRole('textbox')).toBeEnabled({ timeout: 15_000 })
    await expect(page.getByText(BLOCK_REASON)).toHaveCount(0)
    expect(backend.proposal().status).toBe('completed')
    await page.screenshot({
      path: '.playwright-cli/screenshots/shifu-104-page-1440-add-completed.png',
    })
  })

  test('keeps the card after leaving and returning and sends nothing without the button', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installMentorActionsBackend(page, {
      proposal: buildProposal('add_skill'),
    })
    await openMentorActionsPage(page)
    await expect(
      page.getByRole('region', { name: `Adicionar ${SKILL_NAME}?` }),
    ).toBeVisible()
    await expect(page.getByRole('textbox')).toBeDisabled()
    await expect(page.getByRole('button', { name: 'Enviar' })).toBeDisabled()

    await openMentorPage(page)
    await expect(
      page.getByRole('heading', { level: 1, name: 'Nova conversa' }),
    ).toBeVisible()
    await openMentorActionsPage(page)

    await expect(
      page.getByRole('region', { name: `Adicionar ${SKILL_NAME}?` }),
    ).toBeVisible()
    expect(backend.callsOf('confirmMentorSkill')).toHaveLength(0)
    expect(backend.proposal().status).toBe('pending')
  })

  test('chooses an Objective in the picker, swaps it and confirms the chosen one', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installMentorActionsBackend(page, {
      proposal: buildPickerProposal('add_skill'),
    })
    await openMentorActionsPage(page)

    const picker = page.getByRole('group', { name: 'Objetivo' })
    await expect(picker).toContainText(
      'Escolha um Objetivo para revisar a proposta de adição.',
    )
    const available = picker.getByRole('button', { name: GOAL_TITLE })
    const containing = picker.getByRole('button', { name: OTHER_GOAL_TITLE })
    await expect(containing).toHaveAttribute('aria-disabled', 'true')
    await expect(containing).toHaveAccessibleDescription('Já contém esta Habilidade')
    await containing.click({ force: true })
    await expect(picker).toBeVisible()

    await available.focus()
    await page.keyboard.press('Enter')
    const card = page.getByRole('region', { name: `Adicionar ${SKILL_NAME}?` })
    await expect(card).toContainText(`Objetivo: ${GOAL_TITLE}`)
    await expect(card.getByRole('button', { name: 'Trocar Objetivo' })).toBeVisible()
    await card.getByRole('button', { name: 'Trocar Objetivo' }).click()
    await expect(page.getByRole('group', { name: 'Objetivo' })).toBeVisible()
    await expect(
      page
        .getByRole('group', { name: 'Objetivo' })
        .getByRole('button', { name: GOAL_TITLE }),
    ).toHaveAttribute('aria-pressed', 'true')
    await page.getByRole('button', { name: GOAL_TITLE }).click()
    await page.getByRole('button', { name: 'Adicionar habilidade' }).click()

    await expect(
      page.getByRole('region', { name: `${SKILL_NAME} adicionada` }),
    ).toBeVisible()
    expect(backend.callsOf('confirmMentorSkillAdditionServer')[0]?.data).toMatchObject({
      goalId: ACTION_IDS.goal,
      confirmationId: ACTION_IDS.proposal,
    })
  })

  test('declines a proposal, keeps it declined after a reload and unblocks the composer', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installMentorActionsBackend(page, {
      proposal: buildProposal('remove_skill'),
      readsUntilFinal: 1,
    })
    await openMentorActionsPage(page)
    const card = page.getByRole('region', { name: `Remover ${SKILL_NAME}?` })
    await expect(card).toContainText(
      'Você pediu para retirar esta Habilidade do Objetivo.',
    )
    await expect(card).toContainText('Não há restauração.')

    await card.getByRole('button', { name: 'Recusar' }).click()

    const declined = page.getByRole('region', { name: 'Remoção recusada' })
    await expect(declined).toContainText(`${SKILL_NAME} permanece no Objetivo.`)
    await expect(declined).toContainText('Nenhuma alteração foi executada.')
    expect(backend.callsOf('declineMentorActionProposalServer')).toEqual([
      expect.objectContaining({
        method: 'POST',
        data: { sessionId: expect.any(String), proposalId: ACTION_IDS.proposal },
      }),
    ])
    expect(backend.callsOf('confirmMentorSkill')).toHaveLength(0)
    await expect(page.getByRole('textbox')).toBeEnabled({ timeout: 15_000 })

    await openMentorPage(page)
    await openMentorActionsPage(page)
    await expect(page.getByRole('region', { name: 'Remoção recusada' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Remover habilidade' })).toHaveCount(0)
  })

  test('shows the uncertain state after a lost response and verifies with the same confirmation', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installMentorActionsBackend(page, {
      proposal: buildProposal('add_skill'),
    })
    backend.enqueue({ kind: 'abort' })
    await openMentorActionsPage(page)

    await page.getByRole('button', { name: 'Adicionar habilidade' }).click()

    const uncertain = page.getByRole('region', {
      name: `Verificando adição de ${SKILL_NAME}`,
    })
    await expect(uncertain).toContainText('Resultado ainda não confirmado')
    await expect(uncertain.getByRole('button')).toHaveText(['Verificar resultado'])
    await expect(uncertain).not.toContainText('Não foi possível adicionar')

    await uncertain.getByRole('button', { name: 'Verificar resultado' }).click()

    await expect(
      page.getByRole('region', { name: `${SKILL_NAME} adicionada` }),
    ).toBeVisible()
    const confirmations = backend.callsOf('confirmMentorSkillAdditionServer')
    expect(confirmations).toHaveLength(2)
    expect(confirmations[1]?.data).toEqual(confirmations[0]?.data)
  })

  test('offers retry and decline after a safe failure and retries with the same data', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installMentorActionsBackend(page, {
      proposal: buildProposal('remove_skill'),
    })
    backend.enqueue({ kind: 'failure', statusCode: 503 })
    await openMentorActionsPage(page)

    await page.getByRole('button', { name: 'Remover habilidade' }).click()

    const failed = page.getByRole('region', {
      name: `Não foi possível remover ${SKILL_NAME}`,
    })
    await expect(failed).toContainText(
      'A remoção não foi concluída. Sua proposta foi preservada.',
    )
    await expect(failed.getByRole('button')).toHaveText(['Recusar', 'Tentar novamente'])

    await failed.getByRole('button', { name: 'Tentar novamente' }).click()

    await expect(
      page.getByRole('region', { name: `${SKILL_NAME} removida` }),
    ).toBeVisible()
    const confirmations = backend.callsOf('confirmMentorSkillRemovalServer')
    expect(confirmations).toHaveLength(2)
    expect(confirmations[0]).toMatchObject({
      method: 'POST',
      data: {
        goalId: ACTION_IDS.goal,
        confirmationId: ACTION_IDS.proposal,
        skillExperienceId: ACTION_IDS.experience,
      },
    })
    expect(confirmations[1]?.data).toEqual(confirmations[0]?.data)
  })

  test('shows a rejection without buttons', async ({ authenticatedPage: page }) => {
    const backend = await installMentorActionsBackend(page, {
      proposal: buildProposal('add_skill'),
    })
    backend.enqueue({
      kind: 'success',
      outcome: outcomeOf(buildProposal('add_skill'), {
        outcome: 'rejected',
        rejectionReason: 'goal_unavailable',
      }),
    })
    await openMentorActionsPage(page)

    await page.getByRole('button', { name: 'Adicionar habilidade' }).click()

    const rejected = page.getByRole('region', {
      name: `Não foi possível adicionar ${SKILL_NAME}`,
    })
    await expect(rejected).toContainText('Este Objetivo não está mais disponível.')
    await expect(rejected).toContainText('Nenhuma alteração foi executada.')
    await expect(rejected.getByRole('button')).toHaveCount(0)
    await expect(rejected.getByRole('link')).toHaveCount(0)
  })

  test('offers Tentar novamente when the conversation is not refreshed within the limit', async ({
    authenticatedPage: page,
  }) => {
    const backend = await installMentorActionsBackend(page, {
      proposal: buildProposal('add_skill'),
      readsUntilFinal: 1000,
    })
    await openMentorActionsPage(page)
    await page.getByRole('button', { name: 'Adicionar habilidade' }).click()
    await expect(
      page.getByRole('status').filter({ hasText: 'Atualizando a conversa…' }),
    ).toBeVisible()

    await expect(
      page.getByText('Ainda não foi possível atualizar a conversa.'),
    ).toBeVisible({ timeout: 20_000 })
    await expect(page.getByRole('textbox')).toBeDisabled()

    const readsBefore = backend.callsOf('getMentorSessionServer').length
    backend.finalizeOnNextRead()
    await page.getByRole('button', { name: 'Tentar novamente' }).click()
    expect(backend.callsOf('getMentorSessionServer').length).toBeGreaterThan(readsBefore)
  })

  test('renders a streamed action event as a card and keeps the conversation blocked', async ({
    authenticatedPage: page,
  }) => {
    await installMentorActionsBackend(page, {
      proposal: buildProposal('add_skill'),
      isLive: true,
    })
    await openMentorActionsPage(page)

    const card = page.getByRole('region', { name: `Adicionar ${SKILL_NAME}?` })
    await expect(card).toBeVisible()
    await expect(
      page.getByText('Preparei uma proposta para você confirmar.'),
    ).toBeVisible()
    await expect(page.getByRole('textbox')).toBeDisabled()
    await expect(page.getByText(BLOCK_REASON)).toBeVisible()
  })

  test('follows the Markdown links of an answer to the routed pages and keeps unknown paths as text', async ({
    authenticatedPage: page,
  }) => {
    await installMentorActionsBackend(page, {
      proposal: buildProposal('add_skill', { status: 'declined' }),
      answer: [
        'Ainda não encontrei Objetivos seus. [criar um Objetivo](/learning/goals/new).',
        `[Ver Habilidade](/learning/goals/${ACTION_IDS.goal}/skills/${ACTION_IDS.skill}).`,
        '[Página inventada](/learning/inventada).',
      ].join(' '),
    })
    await openMentorActionsPage(page)

    await expect(page.getByText('Página inventada')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Página inventada' })).toHaveCount(0)
    await expect(page.getByRole('link', { name: 'Ver Habilidade' })).toHaveAttribute(
      'href',
      `/learning/goals/${ACTION_IDS.goal}/skills/${ACTION_IDS.skill}`,
    )

    await page.getByRole('link', { name: 'criar um Objetivo' }).click()

    await expect(page).toHaveURL(new RegExp(`${ROUTES.learningGoalsNew}/?$`))
  })

  test('reaches the Skill page from Ver Habilidade', async ({
    authenticatedPage: page,
  }) => {
    await installMentorActionsBackend(page, {
      proposal: buildProposal('add_skill', { status: 'declined' }),
      answer: `[Ver Habilidade](/learning/goals/${ACTION_IDS.goal}/skills/${ACTION_IDS.skill}).`,
    })
    await openMentorActionsPage(page)

    await page.getByRole('link', { name: 'Ver Habilidade' }).click()

    await expect(page).toHaveURL(
      new RegExp(`/learning/goals/${ACTION_IDS.goal}/skills/${ACTION_IDS.skill}/?$`),
    )
  })

  test('stacks the card buttons at full width on a 390 px page', async ({
    authenticatedPage: page,
  }) => {
    await installMentorActionsBackend(page, {
      proposal: buildPickerProposal('remove_skill'),
    })
    await page.setViewportSize({ width: 390, height: 844 })
    await openMentorActionsPage(page)

    const picker = page.getByRole('group', { name: 'Objetivo' })
    for (const name of [GOAL_TITLE, OTHER_GOAL_TITLE]) {
      const box = await picker.getByRole('button', { name }).boundingBox()
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(44)
    }
    await picker.getByRole('button', { name: GOAL_TITLE }).click()
    const card = page.getByRole('region', { name: `Remover ${SKILL_NAME}?` })
    const decline = await card.getByRole('button', { name: 'Recusar' }).boundingBox()
    const confirm = await card
      .getByRole('button', { name: 'Remover habilidade' })
      .boundingBox()
    const cardBox = await card.boundingBox()
    if (!decline || !confirm || !cardBox) throw new Error('The card has no layout box')
    expect(confirm.y).toBeGreaterThan(decline.y + decline.height - 1)
    expect(decline.width).toBeGreaterThan(cardBox.width - 60)
    expect(confirm.width).toBeGreaterThan(cardBox.width - 60)
    expect(decline.height).toBeGreaterThanOrEqual(44)
    expect(confirm.height).toBeGreaterThanOrEqual(44)
    await expectNoHorizontalOverflow(page)
    await page.screenshot({
      path: '.playwright-cli/screenshots/shifu-104-page-390-remove-proposal.png',
    })
  })
})
