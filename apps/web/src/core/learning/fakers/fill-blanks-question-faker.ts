import type {
  FillBlanksQuestion,
  FillBlanksResultQuestion,
} from '@/core/learning/choice-activity'

export class FillBlanksQuestionFaker {
  /** Three blanks, a distractor ("go") and a repeated word ("day"). */
  static fake(overrides: Partial<FillBlanksQuestion> = {}): FillBlanksQuestion {
    return {
      key: 'fill-1',
      kind: 'fill_blanks',
      prompt: 'Complete o texto com as palavras do banco.',
      contentLanguage: 'en',
      segments: [
        { text: 'She ', blankKey: null },
        { text: null, blankKey: 'b1' },
        { text: ' to school and ', blankKey: null },
        { text: null, blankKey: 'b2' },
        { text: ' her homework every ', blankKey: null },
        { text: null, blankKey: 'b3' },
        { text: '.', blankKey: null },
      ],
      bank: [
        { key: 'w1', word: 'goes' },
        { key: 'w2', word: 'walks' },
        { key: 'w3', word: 'does' },
        { key: 'w4', word: 'day' },
        { key: 'w5', word: 'day' },
        { key: 'w6', word: 'go' },
      ],
      ...overrides,
    }
  }

  static fakeResult(
    overrides: Partial<FillBlanksResultQuestion> = {},
  ): FillBlanksResultQuestion {
    const question = FillBlanksQuestionFaker.fake()
    return {
      key: question.key,
      kind: 'fill_blanks',
      prompt: question.prompt,
      contentLanguage: question.contentLanguage,
      segments: question.segments,
      bank: question.bank,
      placements: [
        { blankKey: 'b1', wordKey: 'w1' },
        { blankKey: 'b2', wordKey: 'w6' },
        { blankKey: 'b3', wordKey: 'w4' },
      ],
      score: 66.67,
      isCorrect: false,
      correctBlankCount: 2,
      blankCount: 3,
      explanation: 'Quase lá. Revise a forma do verbo.',
      expectedBlanks: [],
      ...overrides,
    }
  }
}
