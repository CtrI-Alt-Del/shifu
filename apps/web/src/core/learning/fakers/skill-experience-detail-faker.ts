import { faker } from '@faker-js/faker'

import type {
  SkillCompletionOverview,
  SkillExperienceDetail,
} from '@/core/learning/skill-experience'

export class SkillExperienceDetailFaker {
  static fake(overrides: Partial<SkillExperienceDetail> = {}): SkillExperienceDetail {
    const competencyId = fakeUlid()
    const activityId = fakeUlid()
    return {
      goalId: fakeUlid(),
      skillId: fakeUlid(),
      skillName: faker.lorem.words(2),
      skillStatus: 'learning',
      overallResult: faker.number.int({ min: 0, max: 100 }),
      overallCoverageComplete: false,
      focusCompetencyId: competencyId,
      focusCompetencyName: faker.lorem.words(3),
      competencies: [
        {
          competencyId,
          competencyName: faker.lorem.words(3),
          position: 1,
          progress: faker.number.int({ min: 0, max: 100 }),
          coverageComplete: false,
          status: 'learning',
          availability: 'available',
          isFocus: true,
        },
      ],
      recommendation: {
        competencyId,
        competencyName: faker.lorem.words(3),
        activityId,
        activityTitle: faker.lorem.words(4),
        difficulty: 'medium',
        type: 'new-activity',
        reason: faker.lorem.sentence(),
        targetConceptName: null,
        materialId: null,
        gap: null,
      },
      recommendationGap: null,
      evaluation: null,
      completion: null,
      ...overrides,
    }
  }

  // The default values follow the "Evolução" boards of the completed Skill.
  static fakeCompletion(
    overrides: Partial<SkillCompletionOverview> = {},
  ): SkillCompletionOverview {
    return {
      startedOn: '2026-09-02',
      completedOn: '2026-09-13',
      durationDays: 11,
      completedByDiagnosis: false,
      learningActivityCount: 14,
      learningAttemptCount: 22,
      initialResult: 64,
      initialResultCoverage: 'complete',
      finalResult: 91,
      competencies: [
        {
          competencyId: fakeUlid(),
          competencyName: 'Variáveis e tipos',
          position: 1,
          initialProgress: 92,
          initialCoverage: 'complete',
          finalProgress: 96,
          masteredOn: '2026-09-04',
        },
        {
          competencyId: fakeUlid(),
          competencyName: 'Condicionais',
          position: 2,
          initialProgress: 88,
          initialCoverage: 'complete',
          finalProgress: 93,
          masteredOn: '2026-09-06',
        },
        {
          competencyId: fakeUlid(),
          competencyName: 'Estruturas de repetição',
          position: 3,
          initialProgress: 46,
          initialCoverage: 'complete',
          finalProgress: 89,
          masteredOn: '2026-09-10',
        },
        {
          competencyId: fakeUlid(),
          competencyName: 'Funções',
          position: 4,
          initialProgress: 30,
          initialCoverage: 'complete',
          finalProgress: 86,
          masteredOn: '2026-09-13',
        },
      ],
      review: { attemptCount: 3, latestScore: 85 },
      ...overrides,
    }
  }

  static fakeMany(count = 10): SkillExperienceDetail[] {
    return Array.from({ length: count }, () => SkillExperienceDetailFaker.fake())
  }
}

function fakeUlid(): string {
  return faker.string.alphanumeric({ length: 26, casing: 'upper' })
}
