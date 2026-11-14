import {
  GamificationTransportFixture,
  type ControlledRestResponses,
} from '../fixtures/gamification-transport-fixture'
import { ROUTES } from '@/constants/routes'
import type { Achievement } from '@/core/gamification/achievement'
import type { AchievementsOverview } from '@/core/gamification/achievements-overview'
import type { GamificationOverview } from '@/core/gamification/overview'

import { expect, navigateAuthenticatedPage, signInPassword, test } from '../playwright'

function serverFnExport(url: string): string | null {
  const segment = new URL(url).pathname.split('/_serverFn/')[1]
  if (!segment) return null
  try {
    return JSON.parse(Buffer.from(segment, 'base64').toString('utf-8')).export
  } catch {
    return null
  }
}

// Mirrors the real `GET /gamification/achievements` contract and the fixed
// 12-entry catalog (apps/server/.../achievement_catalog.py), shaped like the
// real account used for VM-01/VM-02's manual evidence: three obtained
// achievements (one per reachable family) plus locked entries with derivable
// numeric progress, and the Sequência/Nível families still fully locked.
const achievements: Achievement[] = [
  {
    code: 'primeiro-passo',
    family: 'diagnosis',
    name: 'Primeiro Passo',
    description: 'Concluir o diagnóstico de uma Habilidade.',
    criterionLabel: '1 diagnóstico concluído',
    xpReward: 25,
    state: 'obtained',
    unlockedAt: '2026-01-02T00:00:00Z',
    progressCurrent: null,
    progressTarget: null,
  },
  {
    code: 'explorador',
    family: 'diagnosis',
    name: 'Explorador',
    description: 'Concluir o diagnóstico de cinco Habilidades distintas.',
    criterionLabel: '5 diagnósticos concluídos',
    xpReward: 75,
    state: 'locked',
    unlockedAt: null,
    progressCurrent: 1,
    progressTarget: 5,
  },
  {
    code: 'primeiro-dominio',
    family: 'mastery',
    name: 'Primeiro Domínio',
    description: 'Dominar uma Competência.',
    criterionLabel: '1 Competência dominada',
    xpReward: 25,
    state: 'obtained',
    unlockedAt: '2026-01-03T00:00:00Z',
    progressCurrent: null,
    progressTarget: null,
  },
  {
    code: 'em-evolucao',
    family: 'mastery',
    name: 'Em Evolução',
    description: 'Dominar dez Competências distintas.',
    criterionLabel: '10 Competências dominadas',
    xpReward: 100,
    state: 'locked',
    unlockedAt: null,
    progressCurrent: 1,
    progressTarget: 10,
  },
  {
    code: 'primeira-jornada',
    family: 'completion',
    name: 'Primeira Jornada',
    description: 'Concluir uma Habilidade.',
    criterionLabel: '1 Habilidade concluída',
    xpReward: 50,
    state: 'obtained',
    unlockedAt: '2026-01-04T00:00:00Z',
    progressCurrent: null,
    progressTarget: null,
  },
  {
    code: 'colecionador-de-habilidades',
    family: 'completion',
    name: 'Colecionador de Habilidades',
    description: 'Concluir cinco Habilidades distintas.',
    criterionLabel: '5 Habilidades concluídas',
    xpReward: 150,
    state: 'locked',
    unlockedAt: null,
    progressCurrent: 1,
    progressTarget: 5,
  },
  {
    code: 'consistencia-i',
    family: 'streak',
    name: 'Consistência I',
    description: 'Praticar por três dias consecutivos.',
    criterionLabel: '3 dias consecutivos',
    xpReward: 25,
    state: 'locked',
    unlockedAt: null,
    progressCurrent: 0,
    progressTarget: 3,
  },
  {
    code: 'consistencia-ii',
    family: 'streak',
    name: 'Consistência II',
    description: 'Praticar por sete dias consecutivos.',
    criterionLabel: '7 dias consecutivos',
    xpReward: 50,
    state: 'locked',
    unlockedAt: null,
    progressCurrent: 0,
    progressTarget: 7,
  },
  {
    code: 'consistencia-iii',
    family: 'streak',
    name: 'Consistência III',
    description: 'Praticar por trinta dias consecutivos.',
    criterionLabel: '30 dias consecutivos',
    xpReward: 150,
    state: 'locked',
    unlockedAt: null,
    progressCurrent: 0,
    progressTarget: 30,
  },
  {
    code: 'ascendente-i',
    family: 'level',
    name: 'Ascendente I',
    description: 'Alcançar o nível 5.',
    criterionLabel: 'nível 5',
    xpReward: 50,
    state: 'locked',
    unlockedAt: null,
    progressCurrent: 2,
    progressTarget: 5,
  },
  {
    code: 'ascendente-ii',
    family: 'level',
    name: 'Ascendente II',
    description: 'Alcançar o nível 10.',
    criterionLabel: 'nível 10',
    xpReward: 100,
    state: 'locked',
    unlockedAt: null,
    progressCurrent: 2,
    progressTarget: 10,
  },
  {
    code: 'ascendente-iii',
    family: 'level',
    name: 'Ascendente III',
    description: 'Alcançar o nível 20.',
    criterionLabel: 'nível 20',
    xpReward: 250,
    state: 'locked',
    unlockedAt: null,
    progressCurrent: 2,
    progressTarget: 20,
  },
]

const overview: AchievementsOverview = {
  level: 2,
  totalXp: 290,
  xpForNextLevel: 10,
  achievements,
}

// Mirrors the real `GET /gamification/overview` contract. `Visão geral` is the
// area's default tab, so this query runs on load for every test in this file.
const gamificationOverview: GamificationOverview = {
  level: 5,
  totalXp: 1240,
  currentLevelXp: 1000,
  nextLevelXp: 1500,
  xpForNextLevel: 260,
  levelPercentage: 48,
  streak: {
    streak: { current: 3, longest: 9 },
    lastSevenDays: [
      { day: '2026-09-09', state: 'neutral' },
      { day: '2026-09-10', state: 'missed' },
      { day: '2026-09-11', state: 'practiced' },
      { day: '2026-09-12', state: 'current-streak' },
      { day: '2026-09-13', state: 'current-streak' },
      { day: '2026-09-14', state: 'current-streak' },
      { day: '2026-09-15', state: 'today-pending' },
    ],
    today: '2026-09-15',
    isTodayPending: true,
  },
  achievements: {
    recent: [
      {
        achievementId: 'primeira-jornada',
        name: 'Primeira Jornada',
        criterionLabel: '1 Habilidade concluída',
        xpReward: 50,
        achievedAt: '2026-09-13T12:00:00Z',
      },
    ],
    obtainedCount: 3,
    catalogCount: 12,
  },
}

const overviewPayload = JSON.stringify({
  result: { kind: 'success', overview: gamificationOverview },
})

type CalendarWindow = { year: number; month: number }

// TanStack encodes server-fn GET input as a structured payload, so the month
// arrives as `"k":["year","month"],"v":[{"s":2026},{"s":10}]` rather than as a
// plain query string.
function requestedWindow(url: string): CalendarWindow | null {
  const payload = new URL(url).searchParams.get('payload')
  if (!payload) return null
  const keys = payload.match(/"k":\["year","month"\]/)
  if (!keys) return null
  const scalars = [...payload.matchAll(/"s":(\d+)/g)].map((match) => Number(match[1]))
  if (scalars.length < 2) return null
  return { year: scalars[0], month: scalars[1] }
}

async function mockPracticeCalendar(
  page: Parameters<typeof navigateAuthenticatedPage>[0],
  current: CalendarWindow,
  previous: CalendarWindow,
  seen: string[],
) {
  const pad = (value: number) => String(value).padStart(2, '0')
  await page.route('**/_serverFn/**', async (route) => {
    const url = decodeURIComponent(route.request().url())
    const fn = serverFnExport(route.request().url())
    if (fn?.startsWith('getOverview_')) {
      await route.fulfill({
        body: overviewPayload,
        contentType: 'application/json',
        status: 200,
      })
      return
    }
    if (fn?.startsWith('getAchievements_')) {
      // The page hook runs this query on both tabs; leaving it live lets a
      // real auth failure bounce the session to /login mid-test.
      await route.fulfill({
        body: JSON.stringify({ result: { kind: 'success', overview } }),
        contentType: 'application/json',
        status: 200,
      })
      return
    }
    if (!fn?.startsWith('getPracticeCalendar_')) {
      await route.fallback()
      return
    }
    seen.push(url)
    const requested = requestedWindow(route.request().url())
    const isPrevious =
      requested?.year === previous.year && requested?.month === previous.month
    const window = isPrevious ? previous : current
    const lastDay = new Date(Date.UTC(window.year, window.month, 0)).getUTCDate()
    await route.fulfill({
      body: JSON.stringify({
        result: {
          kind: 'success',
          calendar: {
            year: window.year,
            month: window.month,
            today: `${current.year}-${pad(current.month)}-01`,
            days: Array.from({ length: lastDay }, (_, index) => ({
              day: `${window.year}-${pad(window.month)}-${pad(index + 1)}`,
              state: index === 0 ? 'practiced' : 'neutral',
            })),
            streak: { current: 1, longest: 3 },
            earliestPracticeDate: `${previous.year}-${pad(previous.month)}-01`,
          },
        },
      }),
      contentType: 'application/json',
      status: 200,
    })
  })
}

function calendarWindows() {
  const now = new Date()
  const current = { year: now.getFullYear(), month: now.getMonth() + 1 }
  const shifted = new Date(Date.UTC(current.year, current.month - 2, 1))
  const previous = {
    year: shifted.getUTCFullYear(),
    month: shifted.getUTCMonth() + 1,
  }
  return { current, previous }
}

test('protects gamification and redirects its root to Visão geral', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamification)

  await expect(authenticatedPage).toHaveURL(/\/gamification\/overview\/?$/)
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Gamificação',
    }),
  ).toBeVisible()
  const navigation = authenticatedPage.getByRole('navigation', {
    name: 'Seções da gamificação',
  })
  await expect(navigation.getByRole('link')).toHaveText([
    'Visão geral',
    'Calendário',
    'Conquistas',
    'Histórico de XP',
  ])
  await expect(navigation.getByRole('link', { name: 'Visão geral' })).toHaveAttribute(
    'aria-current',
    'page',
  )

  await authenticatedPage.context().clearCookies()
  await authenticatedPage.goto(ROUTES.gamificationCalendar)

  await expect(authenticatedPage).toHaveURL(/\/login\/?$/)
})

test('renders the catalog header and the achievement grid grouped by family', async ({
  authenticatedPage,
}) => {
  let achievementsRequests = 0
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const fn = serverFnExport(route.request().url())
    if (fn?.startsWith('getOverview_')) {
      await route.fulfill({
        body: overviewPayload,
        contentType: 'application/json',
        status: 200,
      })
      return
    }
    if (fn?.startsWith('getAchievements_')) {
      achievementsRequests += 1
      await route.fulfill({
        body: JSON.stringify({ result: { kind: 'success', overview } }),
        contentType: 'application/json',
        status: 200,
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamificationOverview)

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Gamificação',
    }),
  ).toBeVisible()

  const achievementsLink = authenticatedPage
    .getByRole('navigation', { name: 'Seções da gamificação' })
    .getByRole('link', { name: 'Conquistas' })
  await achievementsLink.click()

  await expect(authenticatedPage).toHaveURL(/\/gamification\/achievements\/?$/)
  await expect(achievementsLink).toHaveAttribute('aria-current', 'page')

  // Catalog header with the obtained count across the active catalog.
  await expect(
    authenticatedPage.getByRole('heading', { level: 2, name: 'Conquistas' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('3 de 12 obtidas')).toBeVisible()

  // Grouped by family.
  for (const familyLabel of [
    'Diagnóstico',
    'Domínio',
    'Conclusão',
    'Sequência',
    'Nível',
  ]) {
    await expect(
      authenticatedPage.getByRole('heading', { name: familyLabel, exact: true }),
    ).toBeVisible()
  }

  // Obtained state: shown with its unlock date.
  const obtainedCard = authenticatedPage
    .getByRole('heading', { name: 'Primeiro Passo' })
    .locator('xpath=ancestor::article')
  await expect(obtainedCard).toContainText('+25 XP')
  await expect(obtainedCard).toContainText(/Obtida em \d{1,2} \w{3} \d{4}/)

  // Locked state: shown with criterion label and numeric progress.
  const lockedCard = authenticatedPage
    .getByRole('heading', { name: 'Explorador' })
    .locator('xpath=ancestor::article')
  await expect(lockedCard).toContainText(
    'Concluir o diagnóstico de cinco Habilidades distintas.',
  )
  await expect(lockedCard).toContainText('1 de 5 Diagnósticos')

  expect(achievementsRequests).toBe(1)
})

test('lands on Visão geral, renders the overview and opens Conquistas from its shortcut', async ({
  authenticatedPage,
}) => {
  const overviewRequests: string[] = []
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const fn = serverFnExport(route.request().url())
    if (fn?.startsWith('getOverview_')) {
      overviewRequests.push(route.request().url())
      await route.fulfill({
        body: overviewPayload,
        contentType: 'application/json',
        status: 200,
      })
      return
    }
    if (fn?.startsWith('getAchievements_')) {
      // The shortcut below opens the Conquistas page, which runs this query;
      // leaving it live lets a real auth failure bounce the session to /login.
      await route.fulfill({
        body: JSON.stringify({ result: { kind: 'success', overview } }),
        contentType: 'application/json',
        status: 200,
      })
      return
    }
    await route.fallback()
  })

  await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamificationOverview)

  await expect(
    authenticatedPage
      .getByRole('navigation', { name: 'Seções da gamificação' })
      .getByRole('link', { name: 'Visão geral' }),
  ).toHaveAttribute('aria-current', 'page')

  await expect(
    authenticatedPage.getByRole('heading', { level: 3, name: 'Nível 5' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('1.240 XP', { exact: true })).toBeVisible()
  await expect(
    authenticatedPage.getByText('260 XP para alcançar o nível 6'),
  ).toBeVisible()
  await expect(
    authenticatedPage.getByRole('progressbar', { name: 'Progresso para o nível 6' }),
  ).toHaveAttribute('aria-valuenow', '48')

  await expect(authenticatedPage.getByText('Recorde: 9 dias')).toBeVisible()
  await expect(
    authenticatedPage
      .getByRole('list', { name: 'Últimos sete dias' })
      .getByRole('listitem'),
  ).toHaveCount(7)
  await expect(authenticatedPage.getByText('3 de 12 obtidas')).toBeVisible()
  await expect(authenticatedPage.getByText('Primeira Jornada')).toBeVisible()

  // The upstream GET /gamification/overview is issued inside the SSR process
  // and is not observable here; the server-function export is.
  await expect.poll(() => overviewRequests.length, { timeout: 10_000 }).toBe(1)

  // Keyboard activation of the shortcut, per RP-13.
  const shortcut = authenticatedPage.getByRole('link', {
    name: 'Ver todas as conquistas',
  })
  await shortcut.focus()
  await authenticatedPage.keyboard.press('Enter')

  await expect(authenticatedPage).toHaveURL(/\/gamification\/achievements\/?$/)
  await expect(
    authenticatedPage
      .getByRole('navigation', { name: 'Seções da gamificação' })
      .getByRole('link', { name: 'Conquistas' }),
  ).toHaveAttribute('aria-current', 'page')
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Diagnóstico', exact: true }),
  ).toBeVisible()
})

test('requests the practice calendar for the viewed month and blocks future months', async ({
  authenticatedPage,
}) => {
  const { current, previous } = calendarWindows()
  const calendarRequests: string[] = []
  await mockPracticeCalendar(authenticatedPage, current, previous, calendarRequests)

  await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamificationCalendar)

  await expect(
    authenticatedPage
      .getByRole('navigation', { name: 'Seções da gamificação' })
      .getByRole('link', { name: 'Calendário' }),
  ).toHaveAttribute('aria-current', 'page')
  await expect(authenticatedPage.getByText('Maior sequência: 3 dias')).toBeVisible()

  expect(calendarRequests.length).toBeGreaterThan(0)
  expect(requestedWindow(calendarRequests[0])).toEqual(current)

  await expect(
    authenticatedPage.getByRole('button', { name: 'Próximo mês' }),
  ).toBeDisabled()

  await authenticatedPage.getByRole('button', { name: 'Mês anterior' }).focus()
  await authenticatedPage.keyboard.press('Enter')

  await expect.poll(() => calendarRequests.length, { timeout: 10_000 }).toBeGreaterThan(1)
  const latest = calendarRequests[calendarRequests.length - 1]
  expect(requestedWindow(latest)).toEqual(previous)

  // Changing the viewed month stays on the calendar route.
  await expect(authenticatedPage).toHaveURL(/\/gamification\/calendar\/?$/)

  // Narrow viewport keeps all seven weekday columns (design.md section 9).
  // Asserted in this same session: the fixture signs in per test and extra
  // sign-ins in this file trip Identity's throttle.
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })
  for (const label of ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']) {
    await expect(authenticatedPage.getByText(label, { exact: true })).toBeVisible()
  }
})

test('invokes the XP history server function and renders its records newest first', async ({
  authenticatedPage,
}) => {
  const historyRequests: string[] = []
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const fn = serverFnExport(route.request().url())
    if (fn?.startsWith('getOverview_')) {
      await route.fulfill({
        body: overviewPayload,
        contentType: 'application/json',
        status: 200,
      })
      return
    }
    if (!fn?.startsWith('getXpHistory_')) {
      await route.fallback()
      return
    }
    // The upstream GET /gamification/xp-history runs inside the SSR process
    // and isn't observable here, but the server-function call itself is:
    // pin its method so a regression to POST/PUT would fail this suite.
    expect(route.request().method()).toBe('GET')
    historyRequests.push(route.request().url())
    await route.fulfill({
      body: JSON.stringify({
        result: {
          kind: 'success',
          history: {
            totalXp: 160,
            entries: [
              {
                id: '01SHF000000000000000GRANTA',
                amount: 60,
                source: 'diagnosis',
                title: 'Lógica de programação',
                detail: 'Diagnóstico concluído',
                occurredAt: '2026-09-11T12:00:00Z',
                grantedAt: '2026-09-13T12:00:00Z',
              },
              {
                id: '01SHF000000000000000GRANTB',
                amount: 100,
                source: 'skill-completion',
                title: 'Estruturas de dados',
                detail: 'Habilidade concluída',
                occurredAt: '2026-09-02T12:00:00Z',
                grantedAt: '2026-09-02T12:00:00Z',
              },
            ],
          },
        },
      }),
      contentType: 'application/json',
      status: 200,
    })
  })

  await navigateAuthenticatedPage(authenticatedPage, ROUTES.gamificationOverview)

  // Keyboard activation, per RP-13.
  const historyLink = authenticatedPage
    .getByRole('navigation', { name: 'Seções da gamificação' })
    .getByRole('link', { name: 'Histórico de XP' })
  await historyLink.focus()
  await authenticatedPage.keyboard.press('Enter')

  await expect(authenticatedPage).toHaveURL(/\/gamification\/xp-history\/?$/)
  await expect(historyLink).toHaveAttribute('aria-current', 'page')
  await expect(
    authenticatedPage.getByRole('heading', { name: 'Histórico de XP' }),
  ).toBeVisible()
  await expect(authenticatedPage.getByText('160 XP')).toBeVisible()

  const records = authenticatedPage.getByRole('region', { name: 'Registros de XP' })
  const rows = records.getByRole('listitem')
  await expect(rows).toHaveCount(2)
  await expect(rows.nth(0)).toContainText('Lógica de programação')
  await expect(rows.nth(0)).toContainText('+60 XP')
  await expect(rows.nth(1)).toContainText('Estruturas de dados')

  // The upstream GET /gamification/xp-history is issued inside the SSR
  // process and is not observable here; the server-function export is.
  await expect.poll(() => historyRequests.length, { timeout: 10_000 }).toBe(1)
})

// A no-stub, real-backend variant of the test above was tried and reverted:
// `authenticatedPage` only fakes the route-protection middleware, it never
// creates a real BetterAuth session, so achievements/calendar/xp-history
// (which each check real auth independently) get rejected by the real
// backend and the pages' session-rejected effect bounces the whole page to
// /login mid-test. Reaching the real controller properly would need a
// dedicated controlled upstream (the `tests/support/mentor-stream-upstream.mjs`
// pattern); that is more infrastructure than this one gap currently justifies.

// Real Better Auth and concrete REST services. The selected upstream responses
// are controlled by the opt-in local proxy, not by _serverFn interception.
test.describe('Gamification routed REST transport', () => {
  for (const operation of [
    {
      path: ROUTES.gamificationOverview,
      endpoint: '/gamification/overview',
      visible: '260 XP para alcançar o nível 6',
      error: 'Não foi possível carregar sua visão geral',
    },
    {
      path: ROUTES.gamificationAchievements,
      endpoint: '/gamification/achievements',
      visible: '3 de 12 obtidas',
      error: 'Não foi possível carregar suas conquistas',
    },
    {
      path: ROUTES.gamificationCalendar,
      endpoint: 'calendar',
      visible: 'Maior sequência: 3 dias',
      error: 'Não foi possível carregar seu calendário',
    },
    {
      path: ROUTES.gamificationXpHistory,
      endpoint: '/gamification/xp-history',
      visible: '160 XP',
      error: 'Não foi possível carregar seu histórico',
    },
  ]) {
    for (const fails of [false, true]) {
      test(`${operation.endpoint} ${fails ? 'exposes a failed HTTP response' : 'maps authenticated HTTP data'}`, async ({
        page,
        request,
        activeAccount,
      }) => {
        const transport = GamificationTransportFixture(request, activeAccount.accountId)
        const now = new Date()
        const year = now.getFullYear()
        const month = now.getMonth() + 1
        const calendarPath = `/gamification/calendar?year=${year}&month=${month}`
        const endpoint =
          operation.endpoint === 'calendar' ? calendarPath : operation.endpoint
        const responses: ControlledRestResponses = {
          '/gamification/overview': { body: gamificationOverview },
          '/gamification/achievements': { body: overview },
          [calendarPath]: {
            body: {
              year,
              month,
              today: `${year}-${String(month).padStart(2, '0')}-01`,
              days: [],
              streak: { current: 1, longest: 3 },
              earliestPracticeDate: null,
            },
          },
          '/gamification/xp-history': { body: { totalXp: 160, entries: [] } },
        }
        if (fails)
          responses[endpoint] = {
            status: 503,
            body: {
              code: 'service_unavailable',
              message: 'Serviço temporariamente indisponível.',
            },
          }
        await transport.register(responses)
        try {
          const signIn = await page.request.post('/api/auth/sign-in/identity', {
            data: { email: activeAccount.email, password: signInPassword },
            headers: { 'x-forwarded-for': activeAccount.ipAddress },
          })
          expect(signIn.status()).toBe(200)
          await page.goto(operation.path)
          await expect(page).toHaveURL(new RegExp(`${operation.path}/?$`))
          if (fails)
            await expect(
              page.getByRole('heading', { name: operation.error }),
            ).toBeVisible()
          else
            await expect(
              page.getByText(operation.visible, { exact: true }).first(),
            ).toBeVisible()
          await expect
            .poll(
              async () =>
                (await transport.observations()).filter(
                  (entry) => entry.path === endpoint,
                ).length,
            )
            .toBeGreaterThan(0)
          const observed = (await transport.observations()).filter(
            (entry) => entry.path === endpoint,
          )
          expect(observed).toEqual(
            expect.arrayContaining([
              {
                method: 'GET',
                path: endpoint,
                authorization: true,
                cookie: false,
                bffMark: true,
                accountId: activeAccount.accountId,
                status: fails ? 503 : 200,
              },
            ]),
          )
        } finally {
          await transport.dispose()
        }
      })
    }
  }
})
