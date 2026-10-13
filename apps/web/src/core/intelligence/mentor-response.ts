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
export type MentorWorkflowStep = 'write-answer' | 'review-answer'
export type MentorResponseBlock = {
  blockKey: string
  ordinal: number
  intent: string | null
  content: string
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
  kind: 'status' | 'consultation' | 'block' | 'completed' | 'failed' | 'cancelled'
  status: MentorResponseStatus
  block: MentorResponseBlock | null
  consultation: string | null
  failureCode: string | null
  createdAt: string
}
export type SubmitMentorMessageInput = {
  submissionKey: string
  content: string
  contextHint: MentorContextHint | null
}
