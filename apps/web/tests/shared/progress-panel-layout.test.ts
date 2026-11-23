import {
  GamificationTransportFixture,
  type ControlledRestResponses,
} from '../fixtures/gamification-transport-fixture'
import { ROUTES } from '@/constants/routes'
import type { GamificationOverview } from '@/core/gamification/overview'
import type { LearningPanorama } from '@/core/learning/learning-panorama'
import type { SkillEvolution } from '@/core/learning/skill-evolution'

import { expect, signInPassword, test } from '../playwright'

const SKILL_EXPERIENCE_ID = '01JTESTSKILLEXPERIENCE0001'
const OTHER_SKILL_EXPERIENCE_ID = '01JTESTSKILLEXPERIENCE0002'
const PANORAMA_PATH = '/learning/panorama'
const EVOLUTION_PATH = `/learning/panorama/skill-experiences/${SKILL_EXPERIENCE_ID}/evolution`
const OVERVIEW_PATH = '/gamification/overview'

// Mirrors the real `GET /learning/panorama` contract for an account with
// Objetivos, started experiences and one completed Habilidade.
const panorama: LearningPanorama = {
  hasGoals: true,
  completedSkillCount: 1,
  masteredCompetencyCount: 4,
  stageDistribution: {
    notStarted: 1,
    diagnosing: 1,
    learning: 2,
    completed: 1,
    goalCount: 2,
  },
  resumeItems: [
    {
      skillExperienceId: SKILL_EXPERIENCE_ID,
      goalId: '01JTESTGOAL00000000000001',
      goalTitle: 'Aprender a programar',
      skillId: '01JTESTSKILL0000000000001',
      skillName: 'Lógica de programação',
      status: 'learning',
      focusCompetencyName: 'Funções',
      lastSubmittedAt: '2026-09-14T14:02:00Z',
    },
  ],
  weeklyEvaluatedActivities: [
    { weekStart: '2026-07-27', count: 0 },
    { weekStart: '2026-08-03', count: 2 },
    { weekStart: '2026-08-10', count: 5 },
    { weekStart: '2026-08-17', count: 1 },
    { weekStart: '2026-08-24', count: 4 },
    { weekStart: '2026-08-31', count: 3 },
    { weekStart: '2026-09-07', count: 6 },
    { weekStart: '2026-09-14', count: 8 },
  ],
  evolutionOptions: [
    {
      skillExperienceId: SKILL_EXPERIENCE_ID,
      goalTitle: 'Aprender a programar',
      skillName: 'Lógica de programação',
      status: 'learning',
    },
    {
      skillExperienceId: OTHER_SKILL_EXPERIENCE_ID,
      goalTitle: 'Carreira em dados',
      skillName: 'Python para análise de dados',
      status: 'learning',
    },
  ],
  defaultEvolutionSkillExperienceId: SKILL_EXPERIENCE_ID,
  completedSkills: [
    {
      skillExperienceId: '01JTESTSKILLEXPERIENCE0003',
      goalId: '01JTESTGOAL00000000000001',
      goalTitle: 'Aprender a programar',
      skillId: '01JTESTSKILL0000000000003',
      skillName: 'Variáveis e tipos',
      finalResult: 91,
      completedOn: '2026-09-13',
    },
  ],
  recentMasteries: [
    {
      skillExperienceId: SKILL_EXPERIENCE_ID,
      goalId: '01JTESTGOAL00000000000001',
      goalTitle: 'Aprender a programar',
      skillId: '01JTESTSKILL0000000000001',
      skillName: 'Lógica de programação',
      competencyId: '01JTESTCOMPETENCY00000001',
      competencyName: 'Condicionais',
      masteredOn: '2026-09-12',
    },
  ],
}

const evolution: SkillEvolution = {
  skillExperienceId: SKILL_EXPERIENCE_ID,
  points: [
    {
      occurredAt: '2026-08-20T12:00:00Z',
      result: 42,
      isPartial: true,
      isBaseline: true,
    },
    {
      occurredAt: '2026-09-01T12:00:00Z',
      result: 55,
      isPartial: true,
      isBaseline: false,
    },
    {
      occurredAt: '2026-09-12T12:00:00Z',
      result: 71,
      isPartial: false,
      isBaseline: false,
    },
  ],
}

const overview: GamificationOverview = {
  level: 5,
  totalXp: 1240,
  currentLevelXp: 1000,
  nextLevelXp: 1500,
  xpForNextLevel: 260,
  levelPercentage: 48,
  streak: {
    streak: { current: 3, longest: 9 },
    currentMonth: Array.from({ length: 30 }, (_, index) => ({
      day: `2026-09-${String(index + 1).padStart(2, '0')}`,
      state: index === 14 ? ('today-pending' as const) : ('neutral' as const),
    })),
    today: '2026-09-15',
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
    nextAchievement: {
      achievementId: 'consistencia-iii',
      name: 'Consistência III',
      criterionLabel: '30 dias consecutivos',
      criterionKind: 'longest_streak',
      xpReward: 150,
      progressCurrent: 9,
      progressTarget: 30,
    },
  },
  weeklyXp: Array.from({ length: 12 }, (_, index) => ({
    weekStart: new Date(Date.UTC(2026, 5, 29 + index * 7)).toISOString().slice(0, 10),
    xp: (index % 4) * 40 + 20,
  })),
}

const serviceUnavailable = {
  status: 503,
  body: { code: 'service_unavailable', message: 'Serviço temporariamente indisponível.' },
}

function successResponses(): ControlledRestResponses {
  return {
    [PANORAMA_PATH]: { body: panorama },
    [EVOLUTION_PATH]: { body: evolution },
    [OVERVIEW_PATH]: { body: overview },
  }
}

// Real Better Auth and concrete REST services: the selected upstream responses
// come from the controlled local proxy, never from _serverFn interception.
test.describe('Progresso panel routed in the browser', () => {
  async function openPanel(
    page: import('@playwright/test').Page,
    activeAccount: { email: string; ipAddress: string },
  ) {
    const signIn = await page.request.post('/api/auth/sign-in/identity', {
      data: { email: activeAccount.email, password: signInPassword },
      headers: { 'x-forwarded-for': activeAccount.ipAddress },
    })
    expect(signIn.status()).toBe(200)
    await page.goto(ROUTES.gamificationOverview)
    await expect(page).toHaveURL(/\/gamification\/overview\/?$/)
  }

  test('renders both sections and sends the Bearer token to every upstream path', async ({
    page,
    request,
    activeAccount,
  }) => {
    const transport = GamificationTransportFixture(request, activeAccount.accountId)
    await transport.register(successResponses())
    try {
      await openPanel(page, activeAccount)

      await expect(
        page.getByRole('heading', { level: 1, name: 'Progresso' }),
      ).toBeVisible()
      await expect(
        page.getByRole('heading', { level: 2, name: 'Aprendizagem' }),
      ).toBeVisible()
      await expect(
        page.getByRole('heading', { level: 2, name: 'Engajamento' }),
      ).toBeVisible()
      await expect(
        page.getByText('Sequência atual · recorde de 9 dias', { exact: true }),
      ).toBeVisible()
      await expect(page.getByText('Variáveis e tipos').first()).toBeVisible()

      for (const path of [PANORAMA_PATH, EVOLUTION_PATH, OVERVIEW_PATH]) {
        await expect
          .poll(
            async () =>
              (await transport.observations()).filter((entry) => entry.path === path)
                .length,
          )
          .toBeGreaterThan(0)
      }
      const observed = await transport.observations()
      for (const path of [PANORAMA_PATH, EVOLUTION_PATH, OVERVIEW_PATH]) {
        expect(observed).toEqual(
          expect.arrayContaining([
            {
              method: 'GET',
              path,
              authorization: true,
              cookie: false,
              bffMark: true,
              accountId: activeAccount.accountId,
              status: 200,
            },
          ]),
        )
      }
    } finally {
      await transport.dispose()
    }
  })

  test('keeps Engajamento when Learning fails and recovers Learning by retry', async ({
    page,
    request,
    activeAccount,
  }) => {
    const transport = GamificationTransportFixture(request, activeAccount.accountId)
    await transport.register({
      ...successResponses(),
      [PANORAMA_PATH]: serviceUnavailable,
    })
    try {
      await openPanel(page, activeAccount)

      const learning = page.getByRole('region', { name: 'Aprendizagem' })
      await expect(
        learning.getByRole('heading', {
          name: 'Não foi possível carregar sua aprendizagem',
        }),
      ).toBeVisible()
      await expect(
        page.getByText('Sequência atual · recorde de 9 dias', { exact: true }),
      ).toBeVisible()
      await expect(
        page.getByRole('region', { name: 'Engajamento' }).getByText('XP por semana'),
      ).toBeVisible()

      await transport.register(successResponses())
      await learning.getByRole('button', { name: 'Tentar novamente' }).click()

      await expect(learning.getByText('Variáveis e tipos').first()).toBeVisible()
      await expect(
        page.getByText('Sequência atual · recorde de 9 dias', { exact: true }),
      ).toBeVisible()
    } finally {
      await transport.dispose()
    }
  })

  test('keeps Aprendizagem when Gamification fails and recovers Engajamento by retry', async ({
    page,
    request,
    activeAccount,
  }) => {
    const transport = GamificationTransportFixture(request, activeAccount.accountId)
    await transport.register({
      ...successResponses(),
      [OVERVIEW_PATH]: serviceUnavailable,
    })
    try {
      await openPanel(page, activeAccount)

      const engagement = page.getByRole('region', { name: 'Engajamento' })
      await expect(
        engagement.getByRole('heading', {
          name: 'Não foi possível carregar seu engajamento',
        }),
      ).toBeVisible()
      await expect(
        page
          .getByRole('region', { name: 'Aprendizagem' })
          .getByText('Variáveis e tipos')
          .first(),
      ).toBeVisible()

      await transport.register(successResponses())
      await engagement.getByRole('button', { name: 'Tentar novamente' }).click()

      await expect(page.getByText('XP por semana').first()).toBeVisible()
      await expect(
        page.getByText('Sequência atual · recorde de 9 dias', { exact: true }),
      ).toBeVisible()
    } finally {
      await transport.dispose()
    }
  })

  const charts: {
    title: string
    section: string
    before: 'switch' | 'select'
  }[] = [
    {
      title: 'Atividades avaliadas por semana',
      section: 'Aprendizagem',
      before: 'switch',
    },
    { title: 'Evolução de uma Habilidade', section: 'Aprendizagem', before: 'select' },
    { title: 'XP por semana', section: 'Engajamento', before: 'switch' },
  ]

  for (const chart of charts) {
    test(`moves between the points of "${chart.title}" with the arrow keys and switches to its table`, async ({
      page,
      request,
      activeAccount,
    }) => {
      const transport = GamificationTransportFixture(request, activeAccount.accountId)
      await transport.register(successResponses())
      try {
        await openPanel(page, activeAccount)

        const card = page
          .getByRole('region', { name: chart.section })
          .getByRole('region', { name: chart.title })
        await expect(card).toBeVisible()
        const surface = card.getByRole('application', { name: chart.title })
        await expect(surface).toBeVisible()

        // The chart is one tab stop: Tab from the control before it (the
        // Habilidade select of the evolution card, or the Gráfico / Tabela switch
        // of the others, with the history link ahead of it in the header) lands on it.
        const previous = {
          switch: card.getByRole('tab', { name: 'Gráfico' }),
          select: card.getByRole('combobox'),
        }[chart.before]
        await previous.focus()
        await page.keyboard.press('Tab')
        await expect(surface).toBeFocused()

        const tooltip = card.getByRole('status')
        await page.keyboard.press('ArrowRight')
        await expect(tooltip).not.toBeEmpty()
        const first = (await tooltip.textContent()) ?? ''
        await page.keyboard.press('ArrowRight')
        await expect.poll(async () => (await tooltip.textContent()) ?? '').not.toBe(first)
        const second = (await tooltip.textContent()) ?? ''
        await page.keyboard.press('ArrowLeft')
        await expect.poll(async () => (await tooltip.textContent()) ?? '').toBe(first)
        expect(second).not.toBe('')

        await card.getByRole('tab', { name: 'Tabela' }).click()
        const table = card.getByRole('table', { name: chart.title })
        await expect(table).toBeVisible()
        await expect(table.getByRole('row')).not.toHaveCount(1)
        await expect(surface).toHaveCount(0)

        await card.getByRole('tab', { name: 'Gráfico' }).click()
        await expect(surface).toBeVisible()
        await expect(table).toHaveCount(0)
      } finally {
        await transport.dispose()
      }
    })
  }

  test('stacks every block at 390 px without horizontal page overflow', async ({
    page,
    request,
    activeAccount,
  }) => {
    const transport = GamificationTransportFixture(request, activeAccount.accountId)
    await transport.register(successResponses())
    try {
      await page.setViewportSize({ width: 390, height: 844 })
      await openPanel(page, activeAccount)

      await expect(
        page.getByRole('region', { name: 'Engajamento' }).getByText('XP por semana'),
      ).toBeVisible()
      await expect(
        page.getByRole('navigation', { name: 'Seções do progresso' }).getByRole('link', {
          name: 'Histórico de XP',
        }),
      ).toBeAttached()

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      )
      expect(overflow).toBeLessThanOrEqual(0)
    } finally {
      await transport.dispose()
    }
  })
})
