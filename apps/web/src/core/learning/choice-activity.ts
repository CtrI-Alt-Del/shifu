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

export type ReactAdditionalFilePolicy = {
  allowedDirectories: readonly string[]
  allowedExtensions: readonly string[]
  maxFiles: number
}

export type ReactQuestion = {
  key: string
  kind: 'react'
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
  additionalFilePolicy: ReactAdditionalFilePolicy | null
  criteria: readonly { key: string; name: string; weightPercentage: number }[]
}

export type HtmlCssJsQuestion = {
  key: string
  kind: 'html_css_js'
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

export type ReactFastifyHttpMethod =
  | 'GET'
  | 'POST'
  | 'PUT'
  | 'PATCH'
  | 'DELETE'
  | 'HEAD'
  | 'OPTIONS'

export type ReactFastifyHttpExample = {
  key: string
  title: string
  method: ReactFastifyHttpMethod
  path: string
  body: string | null
}

export type ReactFastifyQuestion = Omit<ReactQuestion, 'kind' | 'entrypoint'> & {
  kind: 'react_fastify'
  frontendEntrypoint: string
  apiEntrypoint: string
  frontendCommandId: string
  apiCommandId: string
  httpExamples: readonly ReactFastifyHttpExample[]
}

export type FillBlanksSegment = {
  text: string | null
  blankKey: string | null
}

export type FillBlanksWord = {
  key: string
  word: string
}

export type FillBlanksQuestion = {
  key: string
  kind: 'fill_blanks'
  prompt: string
  contentLanguage: string
  segments: readonly FillBlanksSegment[]
  bank: readonly FillBlanksWord[]
}

export type TranslationQuestion = {
  key: string
  kind: 'translation'
  prompt: string
  sourceLanguage: string
  targetLanguage: string
  sourceText: string
  criteria: readonly { key: string; name: string; weightPercentage: number }[]
}

export type PairMatchingItem = {
  key: string
  text: string
}

export type PairMatchingQuestion = {
  key: string
  kind: 'pair_matching'
  prompt: string
  sourceLanguage: string
  targetLanguage: string
  words: readonly PairMatchingItem[]
  translations: readonly PairMatchingItem[]
}

export type ActivityQuestion =
  | ChoiceQuestion
  | CodeQuestion
  | ReactQuestion
  | HtmlCssJsQuestion
  | ReactFastifyQuestion
  | FillBlanksQuestion
  | TranslationQuestion
  | PairMatchingQuestion

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
  kind: 'javascript_stdin' | 'react' | 'html_css_js' | 'react_fastify'
  questionKey: string
  files: readonly { path: string; content: string }[]
}

export type FillBlanksPlacement = {
  blankKey: string
  wordKey: string
}

export type FillBlanksAnswer = {
  kind: 'fill_blanks'
  questionKey: string
  placements: readonly FillBlanksPlacement[]
}

export type TranslationAnswer = {
  kind: 'translation'
  questionKey: string
  text: string
}

export type PairMatchingPair = {
  wordKey: string
  translationKey: string
}

export type PairMatchingAnswer = {
  kind: 'pair_matching'
  questionKey: string
  pairs: readonly PairMatchingPair[]
}

export type PairMatchingOutcome = 'full' | 'partial' | 'incorrect'

export type ActivityAnswer =
  | ChoiceAnswer
  | CodeAnswer
  | FillBlanksAnswer
  | TranslationAnswer
  | PairMatchingAnswer

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
  correctBlankCount?: number
  blankCount?: number
  submittedText?: string
  submittedPairs?: readonly PairMatchingPair[]
  correctPairCount?: number
  totalPairCount?: number
  outcome?: PairMatchingOutcome
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
  kind: 'javascript_stdin' | 'react' | 'html_css_js' | 'react_fastify'
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

export type FillBlanksResultQuestion = {
  key: string
  kind: 'fill_blanks'
  prompt: string
  contentLanguage: string
  segments: readonly FillBlanksSegment[]
  bank: readonly FillBlanksWord[]
  placements: readonly FillBlanksPlacement[]
  score: number
  isCorrect: boolean
  correctBlankCount: number
  blankCount: number
  explanation: string
  expectedBlanks: readonly { blankKey: string; acceptedWords: readonly string[] }[]
}

export type TranslationResultQuestion = {
  key: string
  kind: 'translation'
  prompt: string
  score: number | null
  submittedText: string
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

export type PairMatchingResultQuestion = {
  key: string
  kind: 'pair_matching'
  prompt: string
  score: number
  submittedPairs: readonly PairMatchingPair[]
  correctPairCount: number
  totalPairCount: number
  outcome: PairMatchingOutcome
  explanation: string
  disclosedCorrectPairs?: readonly PairMatchingPair[]
}

export type ActivityResultQuestion =
  | ChoiceResultQuestion
  | CodeResultQuestion
  | FillBlanksResultQuestion
  | TranslationResultQuestion
  | PairMatchingResultQuestion

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
