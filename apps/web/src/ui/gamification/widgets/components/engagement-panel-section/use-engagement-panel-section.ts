import type { AchievementCriterionKind } from '@/core/gamification/overview'
import type { CalendarDay } from '@/core/gamification/practice-calendar'
import { ACHIEVEMENT_CODE_ICONS } from '@/ui/gamification/constants/achievement-presentation'
import { useGamificationOverviewQuery } from '@/ui/gamification/hooks/use-gamification-overview-query'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import type { ChartDatum } from '@/ui/shared/widgets/components/chart-frame'
import type { IconName } from '@/ui/shared/widgets/components/icon'

export type EngagementPanelSectionState = 'loading' | 'error' | 'success'

export type RecentAchievementView = {
  id: string
  name: string
  criterionLabel: string
  xpLabel: string
  achievedOn: string
  icon: IconName
}

export type NextAchievementView = {
  name: string
  criterionLabel: string
  progressLabel: string
  progressPercentage: number
  hint: string
}

// What each criterion is measured from, so the next achievement always says
// which of the learner's own numbers the progress comes from.
const NEXT_ACHIEVEMENT_HINTS: Record<AchievementCriterionKind, string> = {
  diagnostics_completed: 'Baseada nos seus diagnósticos concluídos.',
  competencies_mastered: 'Baseada nas suas Competências dominadas.',
  skills_completed: 'Baseada nas suas Habilidades concluídas.',
  longest_streak: 'Baseada no seu recorde de sequência.',
  level: 'Baseada no seu nível.',
}

export function useEngagementPanelSection() {
  const {
    overview,
    overviewError,
    isLoadingOverview,
    isFetchingOverview,
    refetchOverview,
  } = useGamificationOverviewQuery()
  const { formatMonthLabel, formatCompactDayLabel, formatShortDate } = useFormatDate()

  const state: EngagementPanelSectionState = isLoadingOverview
    ? 'loading'
    : overviewError || !overview
      ? 'error'
      : 'success'

  const isReady = state === 'success' && overview !== null

  // The month is read from the server's local "today", never from the
  // browser clock, so the card names the month its days belong to.
  const monthLabel = isReady ? formatMonthName(overview.streak.today) : ''
  const monthDays: CalendarDay[] = isReady ? overview.streak.currentMonth : []

  const recentAchievements: RecentAchievementView[] = isReady
    ? overview.achievements.recent.map((achievement) => ({
        id: achievement.achievementId,
        name: achievement.name,
        criterionLabel: achievement.criterionLabel,
        xpLabel: `+${achievement.xpReward} XP`,
        achievedOn: formatShortDate(achievement.achievedAt),
        icon: ACHIEVEMENT_CODE_ICONS[achievement.achievementId] ?? 'trophy',
      }))
    : []

  const next = isReady ? overview.achievements.nextAchievement : null
  const nextAchievement: NextAchievementView | null = next
    ? {
        name: next.name,
        criterionLabel: next.criterionLabel,
        progressLabel: `${next.progressCurrent} de ${next.progressTarget}`,
        progressPercentage:
          next.progressTarget > 0
            ? Math.round((next.progressCurrent / next.progressTarget) * 100)
            : 0,
        hint: NEXT_ACHIEVEMENT_HINTS[next.criterionKind],
      }
    : null

  const weeklyXp: ChartDatum[] = isReady
    ? overview.weeklyXp.map((week) => ({
        key: week.weekStart,
        label: formatCompactDayLabel(week.weekStart),
        value: week.xp,
        valueLabel: `${week.xp} XP`,
      }))
    : []

  // The design writes "Novembro de 2026"; the shared helper omits the "de".
  function formatMonthName(isoDate: string): string {
    const [name, year] = formatMonthLabel(
      Number(isoDate.slice(0, 4)),
      Number(isoDate.slice(5, 7)),
    ).split(' ')
    return `${name} de ${year}`
  }

  function handleRetry() {
    void refetchOverview()
  }

  return {
    state,
    monthLabel,
    monthDays,
    recentAchievements,
    nextAchievement,
    weeklyXp,
    isRetrying: isFetchingOverview && !isLoadingOverview,
    handleRetry,
  }
}
