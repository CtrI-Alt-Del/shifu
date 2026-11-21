import type { PairMatchingQuestion } from '@/core/learning/choice-activity'

export class PairMatchingQuestionFaker {
  /** Three pairs; the translations are listed in a different order than the words. */
  static fake(overrides: Partial<PairMatchingQuestion> = {}): PairMatchingQuestion {
    return {
      key: 'pairs-1',
      kind: 'pair_matching',
      prompt: 'Associe cada palavra à sua tradução.',
      sourceLanguage: 'en-US',
      targetLanguage: 'pt-BR',
      words: [
        { key: 'w-3f9a21c4', text: 'dog' },
        { key: 'w-b07d5e18', text: 'house' },
        { key: 'w-5c1e9a73', text: 'water' },
      ],
      translations: [
        { key: 't-91c7d3fa', text: 'casa' },
        { key: 't-0a6b4e25', text: 'água' },
        { key: 't-e2480b6d', text: 'cachorro' },
      ],
      ...overrides,
    }
  }
}
