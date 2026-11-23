/** Share of the monthly AI quota that the answer behind one Mentor message spent. */
export type MentorMessageAiUsage = {
  messageId: string
  /** The attempt that wrote the answer, which keys the live answer before it is stored. */
  attemptId: string
  /** Percentage of the monthly limit, rounded up to two decimals. */
  percentage: number
}
