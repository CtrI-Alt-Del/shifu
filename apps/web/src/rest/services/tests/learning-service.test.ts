import { describe, expect, it, vi } from 'vitest'

import type { RestClient } from '@/core/shared/interfaces/rest-client'
import { RestResponse } from '@/core/shared/responses/rest-response'
import type { TranslationAnswer } from '@/core/learning/choice-activity'
import { LearningService } from '../learning-service'

const IDS = {
  goalId: 'goal-1',
  skillId: 'skill-1',
  competencyId: 'competency-1',
  activityId: 'activity-1',
}

function restClientStub(get: unknown, post?: unknown): RestClient {
  return {
    get: vi.fn().mockResolvedValue(get),
    post: vi.fn().mockResolvedValue(post),
    getFile: vi.fn(),
    postFormData: vi.fn(),
    patch: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  } as unknown as RestClient
}

describe('LearningService translation mapping', () => {
  it('maps a translation question from the Activity wire response', async () => {
    const restClient = restClientStub(
      new RestResponse({
        statusCode: 200,
        body: {
          activity_id: IDS.activityId,
          title: 'Tradução',
          difficulty: 'medium',
          activity_revision: 'revision-1',
          can_submit: true,
          questions: [
            {
              key: 'translation-1',
              kind: 'translation',
              prompt: 'Traduza o texto.',
              source_language: 'pt-BR',
              target_language: 'en-US',
              source_text: 'Bom dia',
              criteria: [
                { key: 'semantic_preservation', name: 'Sentido', weight_percentage: 70 },
              ],
            },
          ],
        },
      }),
    )

    const activity = await LearningService(restClient).getChoiceActivity('token', IDS)

    expect(activity.questions).toEqual([
      {
        key: 'translation-1',
        kind: 'translation',
        prompt: 'Traduza o texto.',
        sourceLanguage: 'pt-BR',
        targetLanguage: 'en-US',
        sourceText: 'Bom dia',
        criteria: [
          { key: 'semantic_preservation', name: 'Sentido', weightPercentage: 70 },
        ],
      },
    ])
  })

  it('maps a translation answer to its wire shape when requesting preliminary feedback', async () => {
    const restClient = restClientStub(
      undefined,
      new RestResponse({
        statusCode: 200,
        body: { status: 'conclusive', score: 100, submitted_text: 'Good morning' },
      }),
    )
    const answer: TranslationAnswer = {
      kind: 'translation',
      questionKey: 'translation-1',
      text: 'Good morning',
    }

    const result = await LearningService(restClient).previewActivityQuestion(
      'token',
      IDS,
      'translation-1',
      'revision-1',
      answer,
    )

    expect(restClient.post).toHaveBeenCalledWith(
      expect.stringContaining('/preliminary-evaluations'),
      {
        activity_revision: 'revision-1',
        answer: {
          kind: 'translation',
          question_key: 'translation-1',
          text: 'Good morning',
        },
      },
      expect.anything(),
    )
    expect(result.submittedText).toBe('Good morning')
  })

  it('maps a translation result question from the Attempt wire response', async () => {
    const restClient = restClientStub(
      new RestResponse({
        statusCode: 200,
        body: {
          attempt_id: 'attempt-1',
          activity_id: IDS.activityId,
          status: 'completed',
          submitted_at: '2026-11-17T00:00:00Z',
          retry_allowed: false,
          questions: [
            {
              question_key: 'translation-1',
              kind: 'translation',
              prompt: 'Traduza o texto.',
              submitted_text: 'Good morning',
              score: 100,
              criterion_results: [
                {
                  key: 'semantic_preservation',
                  weight_percentage: 70,
                  level: 100,
                  comment_id: 'comment-1',
                  comment: 'Sentido preservado.',
                },
              ],
              concept_observations: [],
            },
          ],
        },
      }),
    )

    const attempt = await LearningService(restClient).getChoiceAttempt('token', {
      ...IDS,
      attemptId: 'attempt-1',
    })

    expect(attempt.questions).toEqual([
      {
        key: 'translation-1',
        kind: 'translation',
        prompt: 'Traduza o texto.',
        score: 100,
        submittedText: 'Good morning',
        criterionResults: [
          {
            key: 'semantic_preservation',
            weightPercentage: 70,
            level: 100,
            commentId: 'comment-1',
            comment: 'Sentido preservado.',
          },
        ],
        conceptObservations: [],
      },
    ])
  })
})
