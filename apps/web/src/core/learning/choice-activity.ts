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

export type CodeQuestion = {
  key: string
  kind: 'javascript_stdin'
  prompt: string
  initialFiles: readonly { path: string; content: string; editable: boolean }[]
  entrypoint: string
  editablePaths: readonly string[]
  fixedDependencies: readonly { name: string; version: string }[]
  permittedCommands: readonly {
    id: string
    executable: string
    arguments: readonly string[]
  }[]
  criteria: readonly { key: string; name: string; weightPercentage: number }[]
}

export type ActivityQuestion = ChoiceQuestion | CodeQuestion

export type ChoiceActivityDetail = {
  activityId: string
  title: string
  difficulty: ActivityDifficulty
  questions: readonly ActivityQuestion[]
  activityRevision?: string | null
  canSubmit: boolean
  latestAttemptId: string | null
  unresolvedAttemptId: string | null
  isDiagnostic?: boolean
}

export type ChoiceAnswer = {
  kind?: ChoiceQuestionKind
  questionKey: string
  selectedOptionKeys: readonly string[]
}

export type CodeAnswer = {
  kind: 'javascript_stdin'
  questionKey: string
  files: readonly { path: string; content: string }[]
}

export type ActivityAnswer = ChoiceAnswer | CodeAnswer

export type PreliminaryQuestionResult = {
  status: 'conclusive' | 'inconclusive'
  score: number | null
  explanation?: string
  isCorrect?: boolean
  criteria?: readonly {
    key: string
    weightPercentage: number
    level: string
    commentId: string
    comment: string
  }[]
  submittedFiles?: readonly { path: string; content: string }[]
}

export type ChoiceSubmission = {
  submissionKey: string
  activityRevision?: string
  answers: readonly ActivityAnswer[]
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

export type CodeResultQuestion = {
  key: string
  kind: 'javascript_stdin'
  prompt: string
  score: number | null
  submittedFiles: readonly { path: string; content: string }[]
  criterionResults: readonly {
    key: string
    weightPercentage: number
    level: number | string
    commentId: string
    comment: string
  }[]
  conceptObservations: readonly {
    conceptId: string
    level: number | string
    observationId: string
  }[]
}

export type ActivityResultQuestion = ChoiceResultQuestion | CodeResultQuestion

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
  questions?: readonly ActivityResultQuestion[]
}
