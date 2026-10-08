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

test('protects gamification and renders it for an active session', async ({
  authenticatedPage,
}) => {
  await navigateAuthenticatedPage(authenticatedPage, '/gamification/')
  await expect(
    authenticatedPage.getByRole('heading', {
      level: 1,
      name: 'Cada passo merece ser visto.',
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
      name: 'Cada passo merece ser visto.',
    }),
  ).toBeVisible()

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
