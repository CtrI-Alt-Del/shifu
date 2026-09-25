import type { SkillExperienceStatus } from '@/core/learning/goal-detail'
export const SKILL_STATUS_PRESENTATION: Record<
  SkillExperienceStatus,
  { label: string; className: string }
> = {
  'not-started': {
    label: 'Não iniciada',
    className: 'text-muted-foreground',
  },
  diagnosing: {
    label: 'Em diagnóstico',
    className: 'text-muted-foreground',
  },
  learning: {
    label: 'Em aprendizado',
    className: 'text-success',
  },
  completed: {
    label: 'Concluída',
    className: 'text-success',
  },
}
