import { faker } from '@faker-js/faker'

import {
  LEARNER_MEMORY_CATEGORIES,
  type LearnerMemory,
  type LearnerMemoryOrigin,
  type MentorConversationMemoryItem,
} from '../learner-memory'

const ULID_FIRST_CHARACTERS = '01234567'
const ULID_CHARACTERS = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'

function fakeUlid() {
  return (
    faker.string.fromCharacters(ULID_FIRST_CHARACTERS, 1) +
    faker.string.fromCharacters(ULID_CHARACTERS, 25)
  )
}

export class LearnerMemoryFaker {
  static fakeOrigin(overrides: Partial<LearnerMemoryOrigin> = {}): LearnerMemoryOrigin {
    return {
      sessionId: fakeUlid(),
      messageId: fakeUlid(),
      conversationTitle: faker.lorem.words(3),
      isAvailable: true,
      declaredAt: faker.date.recent().toISOString(),
      ...overrides,
    }
  }

  static fake(overrides: Partial<LearnerMemory> = {}): LearnerMemory {
    const createdAt = faker.date.recent({ days: 30 })
    return {
      id: fakeUlid(),
      category: faker.helpers.arrayElement(LEARNER_MEMORY_CATEGORIES),
      content: faker.lorem.sentence(),
      version: 1,
      createdAt: createdAt.toISOString(),
      updatedAt: createdAt.toISOString(),
      origins: [LearnerMemoryFaker.fakeOrigin()],
      concepts: [],
      ...overrides,
    }
  }

  static fakeMany(count = 8, overrides: Partial<LearnerMemory> = {}): LearnerMemory[] {
    return Array.from({ length: count }, () => LearnerMemoryFaker.fake(overrides))
  }

  static fakeConversationItem(
    overrides: Partial<MentorConversationMemoryItem> = {},
  ): MentorConversationMemoryItem {
    return {
      id: fakeUlid(),
      sourceMessageId: fakeUlid(),
      kind: 'created',
      category: faker.helpers.arrayElement(LEARNER_MEMORY_CATEGORIES),
      memoryId: fakeUlid(),
      content: faker.lorem.sentence(),
      previousContent: null,
      createdAt: faker.date.recent().toISOString(),
      ...overrides,
    }
  }
}
