import {
  ACHIEVEMENT_CODE_ICONS,
  ACHIEVEMENT_FAMILY_ICONS,
} from '@/ui/gamification/constants/achievement-presentation'
import { useFormatDate } from '@/ui/shared/hooks/use-format-date'
import type { IconName } from '@/ui/shared/widgets/components/icon'

import type { AchievementCardProps } from '.'

export function useAchievementCard({ achievement }: AchievementCardProps) {
  const { formatShortDate } = useFormatDate()
  const isLocked = achievement.state === 'locked'
  const isHistorical = achievement.state === 'historical'
  const progress =
    isLocked && achievement.progressCurrent !== null && achievement.progressTarget
      ? { current: achievement.progressCurrent, target: achievement.progressTarget }
      : null

  function getProgressLabel(current: number, target: number): string {
    switch (achievement.family) {
      case 'diagnosis':
        return `${current} de ${target} ${target === 1 ? 'Diagnóstico' : 'Diagnósticos'}`
      case 'mastery':
        return `${current} de ${target} ${target === 1 ? 'Competência' : 'Competências'}`
      case 'completion':
        return `${current} de ${target} ${target === 1 ? 'Habilidade' : 'Habilidades'}`
      case 'streak':
        return `Recorde: ${current} de ${target} ${target === 1 ? 'dia' : 'dias'}`
      case 'level':
        return `Nível atual: ${current} de ${target}`
    }
  }

  function getStatusIcon(): IconName {
    if (isLocked) return 'lock-keyhole'
    return isHistorical ? 'history' : 'circle-check'
  }

  function getStatusLabel(): string {
    if (isLocked) {
      return progress
        ? getProgressLabel(progress.current, progress.target)
        : 'Ainda não obtida'
    }
    const unlockedAt = achievement.unlockedAt
      ? ` em ${formatShortDate(achievement.unlockedAt)}`
      : ''
    return isHistorical ? `Histórica · obtida${unlockedAt}` : `Obtida${unlockedAt}`
  }

  return {
    isLocked,
    criterion: achievement.description || achievement.criterionLabel,
    medalIcon:
      ACHIEVEMENT_CODE_ICONS[achievement.code] ??
      ACHIEVEMENT_FAMILY_ICONS[achievement.family],
    statusIcon: getStatusIcon(),
    statusLabel: getStatusLabel(),
    progressPercentage: progress
      ? Math.min(100, Math.round((progress.current / progress.target) * 100))
      : null,
  }
}
