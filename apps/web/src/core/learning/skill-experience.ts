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

export type StartingPointCoverage = 'complete' | 'partial' | 'unknown'

export type CompetencyCompletionOverview = {
  competencyId: string
  competencyName: string
  position: number
  initialProgress: number | null
  initialCoverage: StartingPointCoverage
  finalProgress: number
  masteredOn: string
}

export type SkillReviewOverview = {
  attemptCount: number
  latestScore: number | null
}

export type SkillCompletionOverview = {
  startedOn: string
  completedOn: string
  durationDays: number
  completedByDiagnosis: boolean
  learningActivityCount: number | null
  learningAttemptCount: number | null
  initialResult: number | null
  initialResultCoverage: StartingPointCoverage
  finalResult: number
  competencies: CompetencyCompletionOverview[]
  review: SkillReviewOverview
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
  completion: SkillCompletionOverview | null
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

const RECOMMENDATION_REASON_LABELS: Record<string, string> = {
  verification: 'Precisamos confirmar uma evidência inconclusiva.',
  coverage: 'Ainda faltam evidências para cobrir este Conceito.',
  practice: 'Uma nova prática pode fortalecer este Conceito.',
  hard_confirmation: 'Falta confirmar o aprendizado em uma Atividade difícil.',
  consolidation: 'Uma Atividade pode consolidar o domínio alcançado.',
  regression: 'O desempenho recente pede uma nova verificação.',
  prerequisite: 'Fortaleça primeiro um Conceito necessário para avançar.',
}

// The server sends a reason code; learners read a sentence, never the raw code.
export function recommendationReasonLabel(reason: string): string {
  return (
    RECOMMENDATION_REASON_LABELS[reason] ??
    'Há uma nova oportunidade de avançar nesta Competência.'
  )
}
