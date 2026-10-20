export type MentorSummaryMarker = {
  version: number
  boundaryMessageId: string
  coveredMessageCount: number
  completedAt: string
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
