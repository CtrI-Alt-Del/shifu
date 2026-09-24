import type { SkillExperienceStatus } from '@/core/learning/goal-detail'
import type { IconName } from '@/ui/shared/widgets/components/icon'

export const SKILL_STATUS_PRESENTATION: Record<
  SkillExperienceStatus,
  { iconName: IconName; label: string; className: string }
> = {
  'not-started': {
    iconName: 'circle-dashed',
    label: 'Não iniciada',
    className: 'text-muted-foreground',
  },
  diagnosing: {
    iconName: 'search',
    label: 'Em diagnóstico',
    className: 'text-muted-foreground',
  },
  learning: {
    iconName: 'circle',
    label: 'Em aprendizado',
    className: 'text-success',
  },
  completed: {
    iconName: 'circle-check',
    label: 'Concluída',
    className: 'text-success',
  },
}
