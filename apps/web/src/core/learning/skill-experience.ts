import type {
  ActivityDifficulty,
  ActivityRecommendationType,
  CompetencyAvailability,
  CompetencyProgressStatus,
} from '@/core/learning/competency-detail'

export type SkillExperienceStatus =
  | 'not-started'
  | 'diagnosing'
  | 'learning'
  | 'completed'

export type SkillEvaluationStatus = 'pending' | 'failed'

export type SkillCompetencySummary = {
  competencyId: string
  competencyName: string
  position: number
  progress: number | null
  coverageComplete: boolean
  status: CompetencyProgressStatus | null
  availability: CompetencyAvailability
  isFocus: boolean
}

export type SkillRecommendation = {
  competencyId: string
  competencyName: string
  activityId: string
  activityTitle: string
  difficulty: ActivityDifficulty
  type: ActivityRecommendationType
  reason: string
  targetConceptName: string | null
  materialId: string | null
  gap: string | null
}

export type SkillEvaluationState = {
  evaluationId: string
  attemptId: string
  activityId: string
  competencyId: string
  status: SkillEvaluationStatus
}

export type SkillExperienceDetail = {
  goalId: string
  skillId: string
  skillName: string
  skillStatus: SkillExperienceStatus
  overallResult: number | null
  overallCoverageComplete: boolean
  focusCompetencyId: string | null
  focusCompetencyName: string | null
  competencies: SkillCompetencySummary[]
  recommendation: SkillRecommendation | null
  recommendationGap: string | null
  evaluation: SkillEvaluationState | null
}

export const SKILL_STATUS_LABELS: Record<SkillExperienceStatus, string> = {
  'not-started': 'Não iniciada',
  diagnosing: 'Em diagnóstico',
  learning: 'Em aprendizado',
  completed: 'Concluída',
}

export const COMPETENCY_STATUS_LABELS: Record<CompetencyProgressStatus, string> = {
  learning: 'Em aprendizagem',
  developing: 'Em desenvolvimento',
  proficient: 'Proficiente',
  mastered: 'Dominada',
}

export const DIFFICULTY_LABELS: Record<ActivityDifficulty, string> = {
  easy: 'Fácil',
  medium: 'Média',
  hard: 'Difícil',
}

export const RECOMMENDATION_TYPE_LABELS: Record<ActivityRecommendationType, string> = {
  'new-activity': 'Atividade nova',
  reinforcement: 'Reforço',
}
