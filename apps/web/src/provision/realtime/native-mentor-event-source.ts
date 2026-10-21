import { buildMentorResponseEventsPath } from '@/constants/routes'
export const NativeMentorEventSource = (
  sessionId: string,
  afterSequence: number,
): EventSource =>
  new EventSource(
    `${buildMentorResponseEventsPath(sessionId)}?after_sequence=${afterSequence}`,
  )
