import { vi } from 'vitest'
import type { ReactQuestionDraftStore } from '@/core/learning/react-question-draft/react-question-draft-store'

export function createReactDraftStoreMock(): ReactQuestionDraftStore {
  return {
    read: vi.fn().mockResolvedValue(null),
    write: vi.fn().mockResolvedValue(1),
    tombstone: vi.fn().mockResolvedValue(2),
    tombstoneActivity: vi.fn().mockResolvedValue(undefined),
    tombstoneStaleActivity: vi.fn().mockResolvedValue(undefined),
    subscribe: vi.fn(() => () => undefined),
    clearTombstone: vi.fn().mockResolvedValue(3),
  }
}
