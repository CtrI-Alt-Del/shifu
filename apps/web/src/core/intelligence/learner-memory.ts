export const LEARNER_MEMORY_CATEGORIES = [
  'explanation_preference',
  'declared_knowledge',
  'interest_or_intention',
  'recurring_difficulty',
] as const

export type LearnerMemoryCategory = (typeof LEARNER_MEMORY_CATEGORIES)[number]

export type LearnerMemoryOrigin = {
  sessionId: string
  messageId: string | null
  conversationTitle: string | null
  isAvailable: boolean
  declaredAt: string
}

export type LearnerMemoryConcept = { key: string; label: string }

export type LearnerMemory = {
  id: string
  category: LearnerMemoryCategory
  content: string
  version: number
  createdAt: string
  updatedAt: string
  origins: LearnerMemoryOrigin[]
  concepts: LearnerMemoryConcept[]
}

export type MentorConversationMemoryItem = {
  id: string
  sourceMessageId: string
  kind: 'created' | 'updated'
  category: LearnerMemoryCategory
  memoryId: string | null
  content: string | null
  previousContent: string | null
  createdAt: string
}

export type ListLearnerMemoriesInput = {
  q?: string
  category?: LearnerMemoryCategory
}

export type EditLearnerMemoryInput = {
  content: string
  expectedVersion: number
}
