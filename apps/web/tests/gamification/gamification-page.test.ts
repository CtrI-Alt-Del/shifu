import type { Achievement } from '@/core/gamification/achievement'
import type { AchievementsOverview } from '@/core/gamification/achievements-overview'

import { expect, navigateAuthenticatedPage, test } from '../playwright'

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

test('protects gamification and renders it for an active session', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, '/gamification/')

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Gamificação',
    }),
  ).toBeVisible()

  await authenticatedPage.context().clearCookies()
  await authenticatedPage.goto('/gamification/')

  await expect(authenticatedPage).toHaveURL(/\/login\/?$/)
})

test('renders the real level/XP header and the achievement grid grouped by family', async ({
  authenticatedPage,
}) => {
  let achievementsRequests = 0
  await authenticatedPage.route('**/_serverFn/**', async (route) => {
    const fn = serverFnExport(route.request().url())
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

  await navigateAuthenticatedPage(authenticatedPage, '/gamification/')

  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Gamificação',
    }),
  ).toBeVisible()

  await authenticatedPage.getByRole('tab', { name: 'Conquistas' }).click()

  // Real level/XP header, not the previous hardcoded mock numbers.
  await expect(authenticatedPage.getByText('02', { exact: true })).toBeVisible()
  await expect(authenticatedPage.getByText('290 XP')).toBeVisible()
  await expect(authenticatedPage.getByText('10 XP para o próximo nível')).toBeVisible()

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
  await expect(obtainedCard).toContainText('Conquistada')
  await expect(obtainedCard).toContainText('em')

  // Locked state: shown with criterion label and numeric progress.
  const lockedCard = authenticatedPage
    .getByRole('heading', { name: 'Explorador' })
    .locator('xpath=ancestor::article')
  await expect(lockedCard).toContainText('5 diagnósticos concluídos')
  await expect(lockedCard).toContainText('(1 de 5)')
  await expect(lockedCard).toContainText('Bloqueada')

  expect(achievementsRequests).toBe(1)
})

test('requests the practice calendar for the viewed month and blocks future months', async ({
  authenticatedPage,
}) => {
  const { current, previous } = calendarWindows()
  const calendarRequests: string[] = []
  await mockPracticeCalendar(authenticatedPage, current, previous, calendarRequests)

  await navigateAuthenticatedPage(authenticatedPage, '/gamification/')

  await expect(
    authenticatedPage.getByRole('tab', { name: 'Calendário' }),
  ).toHaveAttribute('aria-selected', 'true')
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

  await expect(authenticatedPage).toHaveURL(/\/gamification\/?$/)

  // Narrow viewport keeps all seven weekday columns (design.md section 9).
  // Asserted in this same session: the fixture signs in per test and extra
  // sign-ins in this file trip Identity's throttle.
  await authenticatedPage.setViewportSize({ width: 390, height: 844 })
  for (const label of ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']) {
    await expect(authenticatedPage.getByText(label, { exact: true })).toBeVisible()
  }
})
