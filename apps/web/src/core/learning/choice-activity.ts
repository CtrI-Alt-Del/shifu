import type {
  ActivityDifficulty,
  ActivityRecommendation,
  CompetencyProgressStatus,
} from './competency-detail'

export type ChoiceQuestionKind = 'single_choice' | 'multiple_selection'
export type ChoiceAttemptStatus = 'pending' | 'failed' | 'completed'

export type ChoiceOption = {
  key: string
  text: string
}

export type ChoiceQuestion = {
  key: string
  kind: ChoiceQuestionKind
  prompt: string
  options: readonly ChoiceOption[]
}

export type ChoiceActivityDetail = {
  activityId: string
  title: string
  difficulty: ActivityDifficulty
  questions: readonly ChoiceQuestion[]
  canSubmit: boolean
  latestAttemptId: string | null
  unresolvedAttemptId: string | null
  isDiagnostic?: boolean
}

export type ChoiceAnswer = {
  questionKey: string
  selectedOptionKeys: readonly string[]
}

export type ChoiceSubmission = {
  submissionKey: string
  answers: readonly ChoiceAnswer[]
}

export type ChoiceSubmissionResult = {
  attemptId: string
  status: 'pending'
  resultUrl: string
  isDiagnostic?: boolean
}

export type ChoiceResultQuestion = {
  key: string
  prompt: string
  submittedOptionKeys: readonly string[]
  score: number
  isCorrect: boolean
  explanation: string
  correctOptionKeys?: readonly string[]
}

export type ChoiceAttemptDetail = {
  attemptId: string
  activityId: string
  status: ChoiceAttemptStatus
  submittedAt: string
  retryAllowed: boolean
  failureMessage?: string | null
  score?: number | null
  progressBefore?: number | null
  progressAfter?: number | null
  statusBefore?: CompetencyProgressStatus | null
  statusAfter?: CompetencyProgressStatus | null
  nextAction?: ActivityRecommendation | null
  questions?: readonly ChoiceResultQuestion[]
}
