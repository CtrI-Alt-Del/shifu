import { faker } from '@faker-js/faker'

import type {
  PlanningProposal,
  PlanningQuestion,
  PlanningQuestionBatch,
  PlanningSession,
} from '@/core/intelligence/planning-session'

const ULID_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'

export class PlanningQuestionFaker {
  static fake(overrides: Partial<PlanningQuestion> = {}): PlanningQuestion {
    return {
      id: faker.string.alphanumeric({ length: 6 }),
      text: `${faker.lorem.sentence().replace(/\.$/, '')}?`,
      kind: 'single',
      options: [
        { id: 'a', text: faker.word.words(2), exclusive: false },
        { id: 'b', text: faker.word.words(2), exclusive: false },
        { id: 'c', text: faker.word.words(2), exclusive: false },
        { id: 'nao-sei', text: 'Não sei', exclusive: true },
      ],
      ...overrides,
    }
  }
}

export class PlanningSessionFaker {
  static fakeId(): string {
    return `0${faker.string.fromCharacters(ULID_ALPHABET, 25)}`
  }

  static fakeBatch(
    overrides: Partial<PlanningQuestionBatch> = {},
  ): PlanningQuestionBatch {
    return {
      id: faker.string.alphanumeric({ length: 8 }),
      questions: [
        PlanningQuestionFaker.fake(),
        PlanningQuestionFaker.fake({ kind: 'multiple' }),
        PlanningQuestionFaker.fake(),
      ],
      ...overrides,
    }
  }

  static fakeProposal(overrides: Partial<PlanningProposal> = {}): PlanningProposal {
    const skillId = PlanningSessionFaker.fakeId()
    const foundationSkillId = PlanningSessionFaker.fakeId()
    return {
      title: faker.lorem.words(3),
      description: faker.lorem.sentence(),
      skills: [
        { skillId, name: faker.word.words(2), justification: faker.lorem.sentence() },
        {
          skillId: foundationSkillId,
          name: faker.word.words(2),
          justification: faker.lorem.sentence(),
        },
      ],
      relations: [{ skillId, foundationSkillId }],
      ...overrides,
    }
  }

  static fake(overrides: Partial<PlanningSession> = {}): PlanningSession {
    const now = new Date().toISOString()
    return {
      id: PlanningSessionFaker.fakeId(),
      status: 'interview',
      intent: faker.lorem.sentence(),
      generation: 1,
      createdAt: now,
      updatedAt: now,
      operation: null,
      consultedCurriculum: true,
      batch: PlanningSessionFaker.fakeBatch(),
      answeredBatchCount: 0,
      proposal: null,
      message: null,
      failureCode: null,
      ...overrides,
    }
  }
}
