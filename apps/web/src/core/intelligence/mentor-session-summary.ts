export type MentorSummaryMarker = {
  version: number
  boundaryMessageId: string
  coveredMessageCount: number
  completedAt: string
  /** Learner message whose answer run produced the summary; null when unknown. */
  afterMessageId: string | null
}

export type MentorSessionSummaryState = {
  current: MentorSummaryMarker | null
  failureAfterMessageId: string | null
}

export type MentorSessionSummaryContent = {
  version: number
  text: string
  coveredMessageCount: number
  firstMessageId: string
}
