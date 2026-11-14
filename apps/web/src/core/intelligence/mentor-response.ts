import type { MentorActionProposal } from './mentor-action-proposal'
import type { MentorAttachmentSource } from './mentor-attachment'

export type MentorContextHint = {
  goalId: string | null
  skillId: string | null
  competencyId: string | null
  materialId: string | null
  activityId: string | null
}
export type MentorResponseStatus =
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled'
export type MentorWorkflowStep = 'summarize-context' | 'write-answer' | 'review-answer'
export type MentorResponseBlock = {
  blockKey: string
  ordinal: number
  intent: string | null
  content: string
  sources: MentorAttachmentSource[]
}
export type MentorResponseSnapshot = {
  progress?: MentorWorkflowStep | null
  attemptId: string
  learnerMessageId: string
  status: MentorResponseStatus
  blocks: MentorResponseBlock[]
  consultations: string[]
  lastSequence: number
  failureCode: string | null
}
export type MentorResponseEvent = {
  progress?: MentorWorkflowStep | null
  sessionId: string
  attemptId: string
  sequence: number
  kind:
    | 'status'
    | 'consultation'
    | 'block'
    | 'completed'
    | 'failed'
    | 'cancelled'
    | 'action'
  status: MentorResponseStatus
  block: MentorResponseBlock | null
  consultation: string | null
  actionProposal: MentorActionProposal | null
  failureCode: string | null
  createdAt: string
}
export type SubmitMentorMessageInput = {
  submissionKey: string
  content: string
  contextHint: MentorContextHint | null
  attachmentBatchId?: string
  attachmentIds?: string[]
}
