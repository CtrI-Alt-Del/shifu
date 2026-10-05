import { faker } from '@faker-js/faker'

import type { SkillExperienceDetail } from '@/core/learning/skill-experience'

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
