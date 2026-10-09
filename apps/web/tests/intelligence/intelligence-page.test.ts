import { expect, navigateAuthenticatedPage, test } from '../playwright'
import { ROUTES } from '../../src/constants/routes'

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
    }>
    nextCursor: string | null
  }
  pendingLearnerMessageId: string | null
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
            },
          ],
          nextCursor: null,
        },
        pendingLearnerMessageId: `mentor-message-${index + 1}`,
      },
    ]),
  )
  const calls: MentorServerFunctionCall[] = []

  await bff.route(async (route) => {
    const request = route.request()
    const exportName = serverFnExport(request.url())
    const data = serverFnInput(request)
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
    authenticatedPage
      .getByRole('main')
      .filter({ hasText: 'Cada passo merece ser visto.' }),
  ).toBeVisible()
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
