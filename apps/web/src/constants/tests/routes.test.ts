import { describe, expect, it } from 'vitest'

import {
  buildMentorAttachmentFilePath,
  buildMentorAttachmentUploadPath,
  buildMentorResponseEventsPath,
  learningActivityPath,
  learningAttemptPath,
  learningAttemptsPath,
  learningDiagnosticResultPath,
} from '../routes'

describe('route builders', () => {
  const ids = {
    goalId: 'goal/1',
    skillId: 'skill 2',
    competencyId: 'competency?3',
    activityId: 'activity#4',
  }

  it('encodes learning identifiers in activity, attempt, attempts, and result routes', () => {
    const activity =
      '/learning/goals/goal%2F1/skills/skill%202/competencies/competency%3F3/activities/activity%234'
    expect(learningActivityPath(ids)).toBe(activity)
    expect(learningAttemptPath({ ...ids, attemptId: 'attempt/5' })).toBe(
      `${activity}/attempts/attempt%2F5`,
    )
    expect(learningAttemptsPath(ids)).toBe(`${activity}/attempts`)
    expect(learningDiagnosticResultPath(ids)).toBe(
      '/learning/goals/goal%2F1/skills/skill%202/diagnostic/result',
    )
  })

  it('encodes mentor session, batch, and attachment identifiers', () => {
    expect(buildMentorResponseEventsPath('session/1')).toBe(
      '/api/intelligence/mentor-sessions/session%2F1/events',
    )
    expect(buildMentorAttachmentUploadPath('batch/2')).toBe(
      '/api/intelligence/mentor-attachment-batches/batch%2F2/attachments',
    )
    expect(buildMentorAttachmentFilePath('session/1', 'attachment 3')).toBe(
      '/api/intelligence/mentor-sessions/session%2F1/attachments/attachment%203/file',
    )
  })
})
