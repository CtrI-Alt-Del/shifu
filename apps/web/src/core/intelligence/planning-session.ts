export type PlanningSessionStatus =
  | 'processing'
  | 'interview'
  | 'proposal'
  | 'out-of-scope'
  | 'unsupported'
  | 'validation-failed'
  | 'failed'
export type PlanningOperationKind = 'start' | 'answer' | 'restart' | 'retry'
export type PlanningOperationStage =
  | 'analyzing'
  | 'retrieving'
  | 'interviewing'
  | 'composing'
export type PlanningQuestionKind = 'single' | 'multiple'
export type PlanningOption = {
  id: string
  text: string
  exclusive: boolean
}
export type PlanningQuestion = {
  id: string
  text: string
  kind: PlanningQuestionKind
  options: PlanningOption[]
}
export type PlanningQuestionBatch = {
  id: string
  questions: PlanningQuestion[]
}
export type PlanningOperation = {
  kind: PlanningOperationKind
  startedAt: string
  stage: PlanningOperationStage | null
}
export type PlanningProposalSkill = {
  skillId: string
  name: string
  justification: string
}
export type PlanningSkillRelation = {
  skillId: string
  foundationSkillId: string
}
export type PlanningProposal = {
  title: string
  description: string
  skills: PlanningProposalSkill[]
  relations: PlanningSkillRelation[]
}
export type PlanningSession = {
  id: string
  status: PlanningSessionStatus
  intent: string
  generation: number
  createdAt: string
  updatedAt: string
  operation: PlanningOperation | null
  consultedCurriculum: boolean
  batch: PlanningQuestionBatch | null
  answeredBatchCount: number
  proposal: PlanningProposal | null
  message: string | null
  failureCode: string | null
}
export type PlanningGoalCreationRequest = {
  planningId: string
  /** Generated once per review; the same key replays the same confirmation. */
  confirmationKey: string
  title: string
  description: string
  proposal: PlanningProposal
}

export type PlanningGoalCreation = {
  goalId: string
  replayed: boolean
}

export const PLANNING_GOAL_TITLE_MAX_LENGTH = 240
export const PLANNING_GOAL_DESCRIPTION_MAX_LENGTH = 4000
export const CONFIRMATION_KEY_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
export type PlanningAnswer = {
  questionId: string
  optionIds: string[]
}
export type PlanningAnswersSubmission = {
  batchId: string
  answers: PlanningAnswer[]
}
export type PlanningFailureKind =
  | 'unauthorized'
  | 'not-found'
  | 'conflict'
  | 'invalid-request'
  | 'unavailable'
export type PlanningFailure = {
  kind: PlanningFailureKind
  message?: string
}

export const PLANNING_ID_PATTERN = /^[0-7][0-9A-HJKMNP-TV-Z]{25}$/
export const PLANNING_INTENT_MAX_LENGTH = 4000

const PLANNING_FAILURE_KINDS: readonly PlanningFailureKind[] = [
  'unauthorized',
  'not-found',
  'conflict',
  'invalid-request',
  'unavailable',
]

export function isPlanningFailure(value: unknown): value is PlanningFailure {
  return (
    typeof value === 'object' &&
    value !== null &&
    'kind' in value &&
    typeof value.kind === 'string' &&
    (PLANNING_FAILURE_KINDS as readonly string[]).includes(value.kind)
  )
}
