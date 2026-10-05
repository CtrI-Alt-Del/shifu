import { faker } from '@faker-js/faker'

import type { DiagnosticOverview } from '@/core/learning/goal-detail'

export class DiagnosticOverviewFaker {
  static fake(overrides: Partial<DiagnosticOverview> = {}): DiagnosticOverview {
    return {
      status: 'learning',
      runState: 'settled',
      readyToComplete: false,
      nextCompetencyId: null,
      nextActivityId: null,
      pendingAttemptId: null,
      pendingAttemptStatus: null,
      focusCompetencyId: null,
      competencies: [],
      initialOverallResult: faker.number.int({ min: 0, max: 100 }),
      overallCoverageComplete: false,
      directCompletion: false,
      ...overrides,
    }
  }

  static fakeMany(count = 10): DiagnosticOverview[] {
    return Array.from({ length: count }, () => DiagnosticOverviewFaker.fake())
  }
}
