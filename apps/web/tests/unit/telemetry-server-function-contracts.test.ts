import { act, renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  access: vi.fn(),
  publishMainPageEntered: vi.fn(),
  getGoalDetail: vi.fn(),
  getGoals: vi.fn(),
  searchSkillCatalog: vi.fn(),
  startPlanning: vi.fn(),
  addSkillToGoal: vi.fn(),
  removeSkill: vi.fn(),
  deleteGoal: vi.fn(),
  getAvailableSkills: vi.fn(),
  createGoal: vi.fn(),
  getChoiceAttempt: vi.fn(),
  retryChoiceEvaluation: vi.fn(),
  getSkillExperienceDetail: vi.fn(),
  getDiagnostic: vi.fn(),
  startSkill: vi.fn(),
  completeDiagnostic: vi.fn(),
  retryDiagnosticEvaluation: vi.fn(),
  getMaterialDetail: vi.fn(),
  getCompetencyDetail: vi.fn(),
  getChoiceActivity: vi.fn(),
  submitChoiceActivity: vi.fn(),
  submitDiagnosticActivity: vi.fn(),
  submitDiagnostic: vi.fn(),
  previewActivityQuestion: vi.fn(),
  listAchievements: vi.fn(),
  getPracticeCalendar: vi.fn(),
  abandonDiagnostic: vi.fn(),
}))

vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => {
    let validate = (data: unknown) => data
    const builder = {
      middleware: () => builder,
      validator: (next: (data: unknown) => unknown) => {
        validate = next
        return builder
      },
      handler:
        (handler: (input: unknown) => unknown) =>
        async (input: { data?: unknown; context?: unknown } = {}) =>
          handler({
            data: validate(input.data),
            context: input.context ?? {
              requestId: '11111111-1111-4111-8111-111111111111',
              telemetry: { emit: vi.fn() },
            },
          }),
    }
    return builder
  },
}))

vi.mock('@/start', () => ({ serverFunctionTelemetryMiddleware: {} }))
vi.mock('@tanstack/react-router', () => ({
  redirect: ({ to }: { to: string }) => {
    throw new Error(`redirect:${to}`)
  },
}))
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://shifu.test'),
}))
vi.mock('@/constants/server-env', () => ({
  SERVER_ENV: { shifuServerAppUrl: 'http://api.test' },
}))
vi.mock('@/provision/auth/better-auth/better-auth-config', () => ({
  BetterAuthConfig: () => ({ identityURL: 'http://api.test' }),
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({
    getCurrentAccess: mocks.access,
    publishMainPageEntered: mocks.publishMainPageEntered,
  }),
}))
vi.mock('@/rest/axios/server-request-client', () => ({
  createServerRequestClient: vi.fn(() => ({})),
}))
vi.mock('@/provision/learning/goal-detail-provider', () => ({
  GoalDetailProvider: () => ({ getGoalDetail: mocks.getGoalDetail }),
}))
vi.mock('@/rest/services/learning-service', () => ({
  LearningService: () => ({
    getGoals: mocks.getGoals,
    searchSkillCatalog: mocks.searchSkillCatalog,
    addSkillToGoal: mocks.addSkillToGoal,
    removeSkill: mocks.removeSkill,
    deleteGoal: mocks.deleteGoal,
    getAvailableSkills: mocks.getAvailableSkills,
    createGoal: mocks.createGoal,
    getChoiceAttempt: mocks.getChoiceAttempt,
    getSkillExperienceDetail: mocks.getSkillExperienceDetail,
    retryChoiceEvaluation: mocks.retryChoiceEvaluation,
    getDiagnostic: mocks.getDiagnostic,
    startSkill: mocks.startSkill,
    completeDiagnostic: mocks.completeDiagnostic,
    retryDiagnosticEvaluation: mocks.retryDiagnosticEvaluation,
    getMaterialDetail: mocks.getMaterialDetail,
    getCompetencyDetail: mocks.getCompetencyDetail,
    getChoiceActivity: mocks.getChoiceActivity,
    submitChoiceActivity: mocks.submitChoiceActivity,
    submitDiagnosticActivity: mocks.submitDiagnosticActivity,
    submitDiagnostic: mocks.submitDiagnostic,
    previewActivityQuestion: mocks.previewActivityQuestion,
    abandonDiagnostic: mocks.abandonDiagnostic,
  }),
}))
vi.mock('@/rest/services/gamification-service', () => ({
  GamificationService: () => ({
    listAchievements: mocks.listAchievements,
    getPracticeCalendar: mocks.getPracticeCalendar,
  }),
}))
vi.mock('@/rest/services/intelligence-service', () => ({
  IntelligenceService: () => ({ startPlanning: mocks.startPlanning }),
}))

import { enterMainPageMiddleware } from '@/middlewares/enter-main-page-middleware'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'
import { getGoalDetail as getGoalDetailServerFunction } from '@/provision/learning/get-goal-detail'
import { useHomeGoalsQuery } from '@/ui/intelligence/hooks/use-home-goals-query'
import { useStartPlanningAction } from '@/ui/intelligence/hooks/use-start-planning-action'
import { useSkillCatalogQuery } from '@/ui/learning/hooks/use-skill-catalog-query'
import { useAddSkillToGoalAction } from '@/ui/learning/hooks/use-add-skill-to-goal-action'
import { abandonDiagnosticAction as abandonDiagnosticServerFunction } from '@/ui/learning/hooks/use-diagnostic-leave-guard'
import { useRemoveSkillAction } from '@/ui/learning/hooks/use-remove-skill-action'
import {
  getActivityAction as getActivityServerFunction,
  previewActivityQuestionAction as previewActivityServerFunction,
  submitActivityAction as submitActivityServerFunction,
  submitDiagnosticAction as submitDiagnosticServerFunction,
} from '@/ui/learning/widgets/pages/activity-page/use-activity-page'
import {
  getAvailableSkillsAction as getAvailableSkillsServerFunction,
  createGoalAction as createGoalServerFunction,
} from '@/ui/learning/widgets/pages/goal-create-page/use-goal-create-page'
import { useDeleteGoalAction } from '@/ui/learning/widgets/pages/goal-detail-page/use-delete-goal-action'
import {
  getChoiceAttemptAction as getChoiceAttemptServerFunction,
  retryChoiceEvaluationAction as retryChoiceEvaluationServerFunction,
} from '@/ui/learning/widgets/pages/choice-result-page/use-choice-result-page'
import {
  getSkillExperienceAction as getSkillExperienceServerFunction,
  retrySkillEvaluationAction as retrySkillEvaluationServerFunction,
} from '@/ui/learning/widgets/pages/skill-page/use-skill-experience'
import {
  completeDiagnosticAction as completeDiagnosticServerFunction,
  getDiagnosticAction as getDiagnosticServerFunction,
  retryDiagnosticAction as retryDiagnosticServerFunction,
  startSkillAction as startSkillServerFunction,
} from '@/ui/learning/widgets/pages/skill-page/use-skill-page'
import { getMaterialDetailAction as getMaterialDetailServerFunction } from '@/ui/learning/widgets/pages/material-page/use-material-page'
import { getCompetencyDetailAction as getCompetencyDetailServerFunction } from '@/ui/learning/widgets/pages/competency-detail-page/use-competency-detail-page'
import { useAchievementsQuery } from '@/ui/gamification/widgets/pages/gamification-page/use-achievements-query'
import { usePracticeCalendarQuery } from '@/ui/gamification/widgets/pages/gamification-page/calendar-tab-panel/use-practice-calendar-query'
import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import { CurriculumGapError } from '@/core/learning/curriculum-gap-error'

type TestServerFunction = (input?: {
  data?: unknown
  context?: unknown
}) => Promise<unknown>

const asTestServerFunction = (fn: unknown) => fn as TestServerFunction
const enterMainPageMiddlewareForTest = enterMainPageMiddleware as unknown as (input: {
  context: unknown
}) => Promise<unknown>
const requireAuthMiddlewareForTest = requireAuthMiddleware as unknown as (input: {
  context: unknown
}) => Promise<unknown>
const abandonDiagnosticAction = asTestServerFunction(abandonDiagnosticServerFunction)
const completeDiagnosticAction = asTestServerFunction(completeDiagnosticServerFunction)
const createGoalAction = asTestServerFunction(createGoalServerFunction)
const getActivityAction = asTestServerFunction(getActivityServerFunction)
const getAvailableSkillsAction = asTestServerFunction(getAvailableSkillsServerFunction)
const getChoiceAttemptAction = asTestServerFunction(getChoiceAttemptServerFunction)
const getCompetencyDetailAction = asTestServerFunction(getCompetencyDetailServerFunction)
const getDiagnosticAction = asTestServerFunction(getDiagnosticServerFunction)
const getGoalDetail = asTestServerFunction(getGoalDetailServerFunction)
const getMaterialDetailAction = asTestServerFunction(getMaterialDetailServerFunction)
const getSkillExperienceAction = asTestServerFunction(getSkillExperienceServerFunction)
const previewActivityQuestionAction = asTestServerFunction(previewActivityServerFunction)
const retryChoiceEvaluationAction = asTestServerFunction(
  retryChoiceEvaluationServerFunction,
)
const retryDiagnosticAction = asTestServerFunction(retryDiagnosticServerFunction)
const retrySkillEvaluationAction = asTestServerFunction(
  retrySkillEvaluationServerFunction,
)
const startSkillAction = asTestServerFunction(startSkillServerFunction)
const submitActivityAction = asTestServerFunction(submitActivityServerFunction)
const submitDiagnosticAction = asTestServerFunction(submitDiagnosticServerFunction)

const context = {
  requestId: '11111111-1111-4111-8111-111111111111',
  telemetry: { emit: vi.fn() },
}
const access = {
  accountId: 'account-1',
  accessToken: 'access-token',
  displayName: 'Aluno',
  email: 'student@example.test',
  timeZone: 'America/Sao_Paulo',
}
const ids = {
  goalId: '01J00000000000000000000001',
  skillId: '01J00000000000000000000002',
  competencyId: '01J00000000000000000000003',
  activityId: '01J00000000000000000000004',
  attemptId: '01J00000000000000000000006',
  diagnosticRunId: '11111111-1111-4111-8111-111111111111',
}

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client }, children)
}

describe('server functions that carry request telemetry context', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.access.mockResolvedValue(access)
    mocks.publishMainPageEntered.mockResolvedValue(undefined)
    mocks.getGoalDetail.mockResolvedValue({ goalId: ids.goalId, title: 'Objetivo' })
    mocks.getGoals.mockResolvedValue([])
    mocks.searchSkillCatalog.mockResolvedValue({ items: [], nextCursor: null })
    mocks.startPlanning.mockResolvedValue({ created_at: '2026-01-01', id: 'planning-1' })
    mocks.addSkillToGoal.mockResolvedValue({ skillExperienceId: 'experience-1' })
    mocks.removeSkill.mockResolvedValue(undefined)
    mocks.deleteGoal.mockResolvedValue({ ok: true })
    mocks.getAvailableSkills.mockResolvedValue([])
    mocks.createGoal.mockResolvedValue({ goalId: ids.goalId })
    mocks.getChoiceAttempt.mockResolvedValue({ status: 'completed' })
    mocks.retryChoiceEvaluation.mockResolvedValue(undefined)
    mocks.getSkillExperienceDetail.mockResolvedValue({ skillName: 'React' })
    mocks.getDiagnostic.mockResolvedValue({ status: 'diagnosing' })
    mocks.startSkill.mockResolvedValue({ diagnosticRunId: ids.diagnosticRunId })
    mocks.completeDiagnostic.mockResolvedValue(undefined)
    mocks.retryDiagnosticEvaluation.mockResolvedValue(undefined)
    mocks.getMaterialDetail.mockResolvedValue({ materialId: 'material-1' })
    mocks.getCompetencyDetail.mockResolvedValue({ competencyId: ids.competencyId })
    mocks.listAchievements.mockResolvedValue({ achievements: [] })
    mocks.getPracticeCalendar.mockResolvedValue({ days: [] })
    mocks.abandonDiagnostic.mockResolvedValue(undefined)
    mocks.getChoiceActivity.mockResolvedValue({ activityId: ids.activityId })
    mocks.submitChoiceActivity.mockResolvedValue({ status: 'submitted' })
    mocks.submitDiagnosticActivity.mockResolvedValue({
      status: 'pending',
      replayed: false,
    })
    mocks.submitDiagnostic.mockResolvedValue({ status: 'pending', replayed: false })
    mocks.previewActivityQuestion.mockResolvedValue({ correct: true })
  })

  it('propagates the request ID through authenticated middleware and redirects anonymous access', async () => {
    await expect(enterMainPageMiddlewareForTest({ context })).resolves.toMatchObject({
      displayName: access.displayName,
    })
    expect(mocks.access).toHaveBeenCalledWith(expect.any(Request), context.requestId)
    expect(mocks.publishMainPageEntered).toHaveBeenCalledWith(access, context.requestId)

    mocks.access.mockResolvedValueOnce(null)
    await expect(requireAuthMiddlewareForTest({ context })).rejects.toThrow(
      'redirect:/login',
    )
  })

  it('covers goal-detail validation, success and auth failure paths', async () => {
    await expect(
      getGoalDetail({ data: { goalId: 'invalid' }, context }),
    ).resolves.toEqual({
      kind: 'invalid-request',
    })
    await expect(
      getGoalDetail({ data: { goalId: ids.goalId }, context }),
    ).resolves.toEqual({ kind: 'success', detail: expect.any(Object) })

    mocks.access.mockResolvedValueOnce(null)
    await expect(
      getGoalDetail({ data: { goalId: ids.goalId }, context }),
    ).resolves.toEqual({ kind: 'unauthorized' })
  })

  it('executes the learning, intelligence and gamification server consumers', async () => {
    const { result: planning } = renderHook(() => useStartPlanningAction(), {
      wrapper: wrapper(),
    })
    await act(async () => planning.current.startPlanning('aprender React'))

    renderHook(() => useHomeGoalsQuery(), {
      wrapper: wrapper(),
    })
    await waitFor(() => expect(mocks.access).toHaveBeenCalled())

    const { result: addSkill } = renderHook(() => useAddSkillToGoalAction(ids.goalId), {
      wrapper: wrapper(),
    })
    await act(async () =>
      addSkill.current.addSkillToGoal({ skillId: ids.skillId, foundationSkillIds: [] }),
    )

    const { result: removeSkill } = renderHook(
      () => useRemoveSkillAction({ goalId: ids.goalId, skillId: ids.skillId }),
      { wrapper: wrapper() },
    )
    await act(async () => removeSkill.current.removeSkill())

    const { result: deleteGoal } = renderHook(() => useDeleteGoalAction(ids.goalId), {
      wrapper: wrapper(),
    })
    await act(async () => deleteGoal.current.deleteGoal())

    await expect(getAvailableSkillsAction({ context })).resolves.toEqual([])
    await expect(
      createGoalAction({
        data: { title: 'Objetivo', description: 'Descrição', skillIds: [ids.skillId] },
        context,
      }),
    ).resolves.toEqual({ goalId: ids.goalId })

    const routeInput = {
      goalId: ids.goalId,
      skillId: ids.skillId,
      competencyId: ids.competencyId,
      activityId: ids.activityId,
      attemptId: ids.attemptId,
    }
    const activityInput = {
      goalId: ids.goalId,
      skillId: ids.skillId,
      competencyId: ids.competencyId,
      activityId: ids.activityId,
    }
    const choiceAnswer = {
      questionKey: 'question-1',
      kind: 'single_choice',
      selectedOptionKeys: [],
    }
    await expect(getChoiceAttemptAction({ data: routeInput, context })).resolves.toEqual({
      status: 'completed',
    })
    await expect(
      retryChoiceEvaluationAction({ data: routeInput, context }),
    ).resolves.toEqual({
      ok: true,
    })
    await expect(
      getSkillExperienceAction({
        data: { goalId: ids.goalId, skillId: ids.skillId },
        context,
      }),
    ).resolves.toEqual({ skillName: 'React' })
    await expect(
      retrySkillEvaluationAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          competencyId: ids.competencyId,
          activityId: ids.activityId,
          attemptId: ids.attemptId,
        },
        context,
      }),
    ).resolves.toEqual({ ok: true })
    await expect(
      getDiagnosticAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          diagnosticRunId: ids.diagnosticRunId,
        },
        context,
      }),
    ).resolves.toEqual({ status: 'diagnosing' })
    await expect(
      startSkillAction({
        data: { goalId: ids.goalId, skillId: ids.skillId, entryKey: 'entry-1' },
        context,
      }),
    ).resolves.toEqual({ diagnosticRunId: ids.diagnosticRunId })
    await expect(
      completeDiagnosticAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          diagnosticRunId: ids.diagnosticRunId,
        },
        context,
      }),
    ).resolves.toEqual({ ok: true })
    await expect(
      retryDiagnosticAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          diagnosticRunId: ids.diagnosticRunId,
          competencyId: ids.competencyId,
          activityId: ids.activityId,
          attemptId: ids.attemptId,
        },
        context,
      }),
    ).resolves.toEqual({ ok: true })
    await expect(
      getMaterialDetailAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          competencyId: ids.competencyId,
          materialId: ids.activityId,
        },
        context,
      }),
    ).resolves.toEqual({ materialId: 'material-1' })
    await expect(
      getCompetencyDetailAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          competencyId: ids.competencyId,
        },
        context,
      }),
    ).resolves.toEqual({ competencyId: ids.competencyId })
    await expect(getActivityAction({ data: activityInput, context })).resolves.toEqual({
      activityId: ids.activityId,
      accountId: access.accountId,
    })
    await expect(
      submitActivityAction({
        data: {
          ...activityInput,
          submission: { submissionKey: 'submission-1', answers: [choiceAnswer] },
        },
        context,
      }),
    ).resolves.toEqual({ status: 'submitted' })
    await expect(
      submitDiagnosticAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          diagnosticRunId: ids.diagnosticRunId,
          submission: {
            submissionKey: ids.diagnosticRunId,
            items: [
              {
                competencyId: ids.competencyId,
                activityId: ids.activityId,
                activityRevision: '1',
                answers: [choiceAnswer],
              },
            ],
          },
        },
        context,
      }),
    ).resolves.toEqual({ status: 'pending', replayed: false })
    await expect(
      previewActivityQuestionAction({
        data: {
          ...activityInput,
          questionKey: choiceAnswer.questionKey,
          activityRevision: '1',
          answer: choiceAnswer,
        },
        context,
      }),
    ).resolves.toEqual({ correct: true })

    const { result: achievements } = renderHook(() => useAchievementsQuery(), {
      wrapper: wrapper(),
    })
    await waitFor(() => expect(achievements.current.isLoadingOverview).toBe(false))
    const { result: calendar } = renderHook(() => usePracticeCalendarQuery(2026, 10), {
      wrapper: wrapper(),
    })
    await waitFor(() => expect(calendar.current.isLoadingCalendar).toBe(false))
  })

  it('returns the unavailable result when abandoning a diagnostic without access', async () => {
    mocks.access.mockResolvedValueOnce(null)
    await expect(
      abandonDiagnosticAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          diagnosticRunId: ids.diagnosticRunId,
        },
        context,
      }),
    ).resolves.toEqual({ kind: 'unavailable' })
  })

  it('covers validation and provider result mappings for telemetry server functions', async () => {
    await expect(getActivityAction({ data: null, context })).resolves.toEqual({
      kind: 'invalid-request',
    })
    await expect(getActivityAction({ data: {}, context })).resolves.toEqual({
      kind: 'invalid-request',
    })
    await expect(submitActivityAction({ data: {}, context })).resolves.toEqual({
      kind: 'invalid-request',
    })
    await expect(submitDiagnosticAction({ data: {}, context })).resolves.toEqual({
      kind: 'invalid-request',
    })
    await expect(previewActivityQuestionAction({ data: {}, context })).resolves.toEqual({
      kind: 'invalid-request',
    })
    mocks.access.mockResolvedValueOnce(null)
    await expect(
      submitActivityAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          competencyId: ids.competencyId,
          activityId: ids.activityId,
          submission: {
            submissionKey: 'submission-1',
            answers: [
              {
                questionKey: 'question-1',
                kind: 'single_choice',
                selectedOptionKeys: [],
              },
            ],
          },
        },
        context,
      }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    await expect(getChoiceAttemptAction({ data: {}, context })).resolves.toEqual({
      kind: 'invalid-request',
    })
    await expect(retryChoiceEvaluationAction({ data: {}, context })).resolves.toEqual({
      kind: 'invalid-request',
    })
    await expect(
      getSkillExperienceAction({
        data: { goalId: 'bad', skillId: ids.skillId },
        context,
      }),
    ).resolves.toEqual({ kind: 'not-found' })
    await expect(
      retrySkillEvaluationAction({ data: { goalId: 'bad' }, context }),
    ).resolves.toEqual({ kind: 'not-found' })
    await expect(
      getDiagnosticAction({ data: { goalId: 'bad' }, context }),
    ).resolves.toEqual({
      kind: 'not-found',
    })
    await expect(startSkillAction({ data: { goalId: 'bad' }, context })).resolves.toEqual(
      {
        kind: 'not-found',
      },
    )
    mocks.access.mockResolvedValueOnce(null)
    await expect(completeDiagnosticAction({ data: {}, context })).resolves.toEqual({
      kind: 'unauthorized',
    })
    await expect(
      retryDiagnosticAction({ data: { goalId: 'bad' }, context }),
    ).resolves.toEqual({
      kind: 'not-found',
    })
    await expect(getMaterialDetailAction({ data: {}, context })).resolves.toEqual({
      kind: 'invalid-request',
    })
    await expect(getCompetencyDetailAction({ data: {}, context })).resolves.toEqual({
      kind: 'invalid-request',
    })

    mocks.abandonDiagnostic.mockRejectedValueOnce(
      new AuthError('unavailable', 'identity unavailable', { statusCode: 503 }),
    )
    await expect(abandonDiagnosticAction({ data: { ...ids }, context })).resolves.toEqual(
      { kind: 'unavailable' },
    )
    mocks.abandonDiagnostic.mockRejectedValueOnce(new RestError('stale', 409))
    await expect(abandonDiagnosticAction({ data: { ...ids }, context })).resolves.toEqual(
      { kind: 'stale' },
    )
    mocks.abandonDiagnostic.mockRejectedValueOnce(new Error('down'))
    await expect(abandonDiagnosticAction({ data: { ...ids }, context })).resolves.toEqual(
      { kind: 'unavailable' },
    )

    mocks.access.mockResolvedValue(access)
    mocks.getGoalDetail.mockRejectedValueOnce(
      new AuthError('authentication-rejected', 'expired', { statusCode: 401 }),
    )
    await expect(
      getGoalDetail({ data: { goalId: ids.goalId }, context }),
    ).resolves.toEqual({
      kind: 'unauthorized',
      statusCode: 401,
    })
    mocks.getGoalDetail.mockRejectedValueOnce(
      new AuthError('unavailable', 'down', { statusCode: 503 }),
    )
    await expect(
      getGoalDetail({ data: { goalId: ids.goalId }, context }),
    ).resolves.toEqual({
      kind: 'unavailable',
      statusCode: 503,
    })
    for (const [statusCode, kind] of [
      [401, 'unauthorized'],
      [403, 'forbidden'],
      [404, 'not-found'],
      [422, 'invalid-request'],
      [500, 'unavailable'],
    ] as const) {
      mocks.getGoalDetail.mockRejectedValueOnce(new RestError('failure', statusCode))
      await expect(
        getGoalDetail({ data: { goalId: ids.goalId }, context }),
      ).resolves.toMatchObject({
        kind,
      })
    }
    mocks.getGoalDetail.mockRejectedValueOnce(new Error('down'))
    await expect(
      getGoalDetail({ data: { goalId: ids.goalId }, context }),
    ).resolves.toEqual({
      kind: 'unavailable',
    })
  })

  it('covers authorization and dependency failures in the telemetry consumers', async () => {
    const routeInput = {
      goalId: ids.goalId,
      skillId: ids.skillId,
      competencyId: ids.competencyId,
      activityId: ids.activityId,
      attemptId: ids.attemptId,
    }

    mocks.access.mockResolvedValue(null)
    await expect(
      getGoalDetail({ data: { goalId: ids.goalId }, context }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    await expect(getAvailableSkillsAction({ context })).resolves.toEqual({
      kind: 'unauthorized',
    })
    await expect(
      createGoalAction({
        data: { title: 'Objetivo', description: 'Descrição', skillIds: [ids.skillId] },
        context,
      }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    await expect(getChoiceAttemptAction({ data: routeInput, context })).resolves.toEqual({
      kind: 'unauthorized',
    })
    await expect(
      retryChoiceEvaluationAction({ data: routeInput, context }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    await expect(
      getSkillExperienceAction({
        data: { goalId: ids.goalId, skillId: ids.skillId },
        context,
      }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    await expect(
      retrySkillEvaluationAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          competencyId: ids.competencyId,
          activityId: ids.activityId,
          attemptId: ids.attemptId,
        },
        context,
      }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    await expect(
      getDiagnosticAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          diagnosticRunId: ids.diagnosticRunId,
        },
        context,
      }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    await expect(
      startSkillAction({
        data: { goalId: ids.goalId, skillId: ids.skillId, entryKey: 'entry-1' },
        context,
      }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    await expect(
      completeDiagnosticAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          diagnosticRunId: ids.diagnosticRunId,
        },
        context,
      }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    await expect(
      retryDiagnosticAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          diagnosticRunId: ids.diagnosticRunId,
          competencyId: ids.competencyId,
          activityId: ids.activityId,
          attemptId: ids.attemptId,
        },
        context,
      }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    await expect(
      getMaterialDetailAction({
        data: { ...routeInput, materialId: ids.activityId },
        context,
      }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    await expect(
      getCompetencyDetailAction({ data: routeInput, context }),
    ).resolves.toEqual({ kind: 'unauthorized' })

    const { result: planning } = renderHook(() => useStartPlanningAction(), {
      wrapper: wrapper(),
    })
    await act(async () => {
      planning.current.startPlanning('aprender React')
    })
    await waitFor(() => expect(planning.current.error).toBeTruthy())

    mocks.access.mockClear()
    renderHook(() => useHomeGoalsQuery(), {
      wrapper: wrapper(),
    })
    await waitFor(() => expect(mocks.access).toHaveBeenCalled())

    const { result: catalog } = renderHook(() => useSkillCatalogQuery(ids.goalId), {
      wrapper: wrapper(),
    })
    await waitFor(() => expect(catalog.current.isLoadingSkills).toBe(false))

    const { result: addSkill } = renderHook(() => useAddSkillToGoalAction(ids.goalId), {
      wrapper: wrapper(),
    })
    await expect(
      addSkill.current.addSkillToGoal({ skillId: ids.skillId, foundationSkillIds: [] }),
    ).rejects.toThrow()
    const { result: removeSkill } = renderHook(
      () => useRemoveSkillAction({ goalId: ids.goalId, skillId: ids.skillId }),
      { wrapper: wrapper() },
    )
    await expect(removeSkill.current.removeSkill()).rejects.toThrow()
    const { result: deleteGoal } = renderHook(() => useDeleteGoalAction(ids.goalId), {
      wrapper: wrapper(),
    })
    await expect(deleteGoal.current.deleteGoal()).rejects.toThrow()

    mocks.access.mockResolvedValue(access)
    mocks.listAchievements.mockRejectedValue(
      new AuthError('authentication-rejected', 'expired', { statusCode: 401 }),
    )
    const { result: unauthorizedAchievements } = renderHook(
      () => useAchievementsQuery(),
      { wrapper: wrapper() },
    )
    await waitFor(() =>
      expect(unauthorizedAchievements.current.isLoadingOverview).toBe(false),
    )
    mocks.listAchievements.mockRejectedValue(new RestError('forbidden', 403))
    const { result: forbiddenAchievements } = renderHook(() => useAchievementsQuery(), {
      wrapper: wrapper(),
    })
    await waitFor(() =>
      expect(forbiddenAchievements.current.isLoadingOverview).toBe(false),
    )
    mocks.listAchievements.mockRejectedValue(new Error('down'))
    const { result: failedAchievements } = renderHook(() => useAchievementsQuery(), {
      wrapper: wrapper(),
    })
    await waitFor(() => expect(failedAchievements.current.isLoadingOverview).toBe(false))

    mocks.getPracticeCalendar.mockRejectedValue(
      new AuthError('authentication-rejected', 'expired', { statusCode: 401 }),
    )
    const { result: unauthorizedCalendar } = renderHook(
      () => usePracticeCalendarQuery(2026, 10),
      { wrapper: wrapper() },
    )
    await waitFor(() =>
      expect(unauthorizedCalendar.current.isLoadingCalendar).toBe(false),
    )
    mocks.getPracticeCalendar.mockRejectedValue(new RestError('forbidden', 403))
    const { result: forbiddenCalendar } = renderHook(
      () => usePracticeCalendarQuery(2026, 10),
      { wrapper: wrapper() },
    )
    await waitFor(() => expect(forbiddenCalendar.current.isLoadingCalendar).toBe(false))

    mocks.access.mockResolvedValueOnce(null)
    const { result: anonymousAchievements } = renderHook(() => useAchievementsQuery(), {
      wrapper: wrapper(),
    })
    await waitFor(() =>
      expect(anonymousAchievements.current.isLoadingOverview).toBe(false),
    )
    mocks.access.mockResolvedValueOnce(null)
    const { result: anonymousCalendar } = renderHook(
      () => usePracticeCalendarQuery(2026, 11),
      { wrapper: wrapper() },
    )
    await waitFor(() => expect(anonymousCalendar.current.isLoadingCalendar).toBe(false))

    mocks.access.mockResolvedValue(access)
    mocks.listAchievements.mockRejectedValue(
      new AuthError('unavailable', 'down', { statusCode: 503 }),
    )
    const { result: unavailableAchievements } = renderHook(() => useAchievementsQuery(), {
      wrapper: wrapper(),
    })
    await waitFor(() =>
      expect(unavailableAchievements.current.isLoadingOverview).toBe(false),
    )
    mocks.listAchievements.mockRejectedValue(new RestError('unauthorized', 401))
    const { result: unauthorizedRestAchievements } = renderHook(
      () => useAchievementsQuery(),
      {
        wrapper: wrapper(),
      },
    )
    await waitFor(() =>
      expect(unauthorizedRestAchievements.current.isLoadingOverview).toBe(false),
    )
    mocks.getPracticeCalendar.mockRejectedValue(
      new AuthError('unavailable', 'down', { statusCode: 503 }),
    )
    const { result: unavailableCalendar } = renderHook(
      () => usePracticeCalendarQuery(2026, 12),
      { wrapper: wrapper() },
    )
    await waitFor(() => expect(unavailableCalendar.current.isLoadingCalendar).toBe(false))
    mocks.getPracticeCalendar.mockRejectedValue(new RestError('unauthorized', 401))
    const { result: unauthorizedRestCalendar } = renderHook(
      () => usePracticeCalendarQuery(2026, 13),
      { wrapper: wrapper() },
    )
    await waitFor(() =>
      expect(unauthorizedRestCalendar.current.isLoadingCalendar).toBe(false),
    )
  })

  it('maps service failures to stable action results', async () => {
    mocks.getChoiceAttempt.mockRejectedValue(new RestError('Unauthorized', 401))
    await expect(
      getChoiceAttemptAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          competencyId: ids.competencyId,
          activityId: ids.activityId,
          attemptId: ids.attemptId,
        },
        context,
      }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    mocks.getChoiceAttempt.mockRejectedValue(new RestError('Missing', 404))
    await expect(
      getChoiceAttemptAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          competencyId: ids.competencyId,
          activityId: ids.activityId,
          attemptId: ids.attemptId,
        },
        context,
      }),
    ).resolves.toEqual({ kind: 'not-found' })
    mocks.getChoiceAttempt.mockRejectedValue(new Error('down'))
    await expect(
      getChoiceAttemptAction({
        data: {
          goalId: ids.goalId,
          skillId: ids.skillId,
          competencyId: ids.competencyId,
          activityId: ids.activityId,
          attemptId: ids.attemptId,
        },
        context,
      }),
    ).resolves.toEqual({ kind: 'unavailable' })

    mocks.getSkillExperienceDetail.mockRejectedValue(new RestError('Unauthorized', 401))
    await expect(
      getSkillExperienceAction({
        data: { goalId: ids.goalId, skillId: ids.skillId },
        context,
      }),
    ).resolves.toEqual({ kind: 'unauthorized' })
    mocks.getSkillExperienceDetail.mockRejectedValue(new RestError('Missing', 404))
    await expect(
      getSkillExperienceAction({
        data: { goalId: ids.goalId, skillId: ids.skillId },
        context,
      }),
    ).resolves.toEqual({ kind: 'not-found' })
    mocks.getSkillExperienceDetail.mockRejectedValue(new Error('down'))
    await expect(
      getSkillExperienceAction({
        data: { goalId: ids.goalId, skillId: ids.skillId },
        context,
      }),
    ).resolves.toEqual({ kind: 'unavailable' })

    mocks.createGoal.mockRejectedValue(new CurriculumGapError())
    await expect(
      createGoalAction({
        data: { title: 'Objetivo', description: 'Descrição', skillIds: [ids.skillId] },
        context,
      }),
    ).resolves.toEqual({ kind: 'curriculum-gap' })
    mocks.createGoal.mockRejectedValue(new Error('down'))
    await expect(
      createGoalAction({
        data: { title: 'Objetivo', description: 'Descrição', skillIds: [ids.skillId] },
        context,
      }),
    ).resolves.toEqual({ kind: 'unavailable' })
    await expect(
      createGoalAction({ data: { title: '', description: '', skillIds: [] }, context }),
    ).resolves.toEqual({ kind: 'invalid' })

    mocks.getAvailableSkills.mockRejectedValue(new Error('down'))
    await expect(getAvailableSkillsAction({ context })).resolves.toEqual({
      kind: 'unavailable',
    })
  })

  it('covers telemetry action failures across Learning handlers', async () => {
    const routeInput = {
      goalId: ids.goalId,
      skillId: ids.skillId,
      competencyId: ids.competencyId,
      activityId: ids.activityId,
      attemptId: ids.attemptId,
    }
    const materialInput = { ...routeInput, materialId: ids.activityId }
    const competencyInput = {
      goalId: ids.goalId,
      skillId: ids.skillId,
      competencyId: ids.competencyId,
    }
    const diagnosticInput = {
      goalId: ids.goalId,
      skillId: ids.skillId,
      diagnosticRunId: ids.diagnosticRunId,
    }

    for (const error of [
      new AuthError('unavailable', 'down', { statusCode: 503 }),
      new RestError('unauthorized', 401),
      new RestError('missing', 404),
      new RestError('busy', 429),
      new Error('down'),
    ]) {
      mocks.getMaterialDetail.mockRejectedValueOnce(error)
      await expect(
        getMaterialDetailAction({ data: materialInput, context }),
      ).resolves.toBeTruthy()
      mocks.getCompetencyDetail.mockRejectedValueOnce(error)
      await expect(
        getCompetencyDetailAction({ data: competencyInput, context }),
      ).resolves.toBeTruthy()
    }

    for (const action of [getSkillExperienceAction, retrySkillEvaluationAction]) {
      for (const error of [
        new RestError('unauthorized', 401),
        new RestError('missing', 404),
        new Error('down'),
      ]) {
        if (action === getSkillExperienceAction) {
          mocks.getSkillExperienceDetail.mockRejectedValueOnce(error)
          await expect(
            action({ data: { goalId: ids.goalId, skillId: ids.skillId }, context }),
          ).resolves.toBeTruthy()
        } else {
          mocks.retryChoiceEvaluation.mockRejectedValueOnce(error)
          await expect(
            action({
              data: {
                goalId: ids.goalId,
                skillId: ids.skillId,
                competencyId: ids.competencyId,
                activityId: ids.activityId,
                attemptId: ids.attemptId,
              },
              context,
            }),
          ).resolves.toBeTruthy()
        }
      }
    }

    for (const error of [
      new RestError('unauthorized', 401),
      new RestError('missing', 404),
      new RestError('stale', 409),
      new Error('down'),
    ]) {
      mocks.getDiagnostic.mockRejectedValueOnce(error)
      await expect(
        getDiagnosticAction({ data: diagnosticInput, context }),
      ).resolves.toBeTruthy()
    }
    for (const error of [
      new CurriculumGapError(),
      new RestError('unauthorized', 401),
      new RestError('missing', 404),
      new Error('down'),
    ]) {
      mocks.startSkill.mockRejectedValueOnce(error)
      await expect(
        startSkillAction({
          data: { ...diagnosticInput, entryKey: 'entry-1' },
          context,
        }),
      ).resolves.toBeTruthy()
    }
    for (const error of [
      new RestError('unauthorized', 401),
      new RestError('missing', 404),
      new Error('down'),
    ]) {
      mocks.completeDiagnostic.mockRejectedValueOnce(error)
      await expect(
        completeDiagnosticAction({ data: diagnosticInput, context }),
      ).resolves.toBeTruthy()
      mocks.retryDiagnosticEvaluation.mockRejectedValueOnce(error)
      await expect(
        retryDiagnosticAction({ data: { ...routeInput, ...diagnosticInput }, context }),
      ).resolves.toBeTruthy()
    }

    for (const error of [
      new AuthError('unavailable', 'down', { statusCode: 503 }),
      new RestError('unauthorized', 401),
      new RestError('missing', 404),
      new RestError('stale', 409),
      new RestError('busy', 429),
      new Error('down'),
    ]) {
      mocks.retryChoiceEvaluation.mockRejectedValueOnce(error)
      await expect(
        retryChoiceEvaluationAction({ data: routeInput, context }),
      ).resolves.toBeTruthy()
    }

    mocks.getChoiceActivity.mockRejectedValueOnce(
      new AuthError('unavailable', 'down', { statusCode: 503 }),
    )
    await expect(getActivityAction({ data: routeInput, context })).resolves.toBeTruthy()
    mocks.getChoiceActivity.mockRejectedValueOnce(new RestError('unauthorized', 401))
    await expect(getActivityAction({ data: routeInput, context })).resolves.toBeTruthy()
    mocks.getChoiceActivity.mockRejectedValueOnce(new RestError('missing', 404))
    await expect(getActivityAction({ data: routeInput, context })).resolves.toBeTruthy()
    mocks.getChoiceActivity.mockRejectedValueOnce(new RestError('busy', 429))
    await expect(getActivityAction({ data: routeInput, context })).resolves.toBeTruthy()
    mocks.getChoiceActivity.mockRejectedValueOnce(new RestError('entry required', 409))
    await expect(getActivityAction({ data: routeInput, context })).resolves.toMatchObject(
      {
        diagnosticEntryRequired: true,
      },
    )
    mocks.getChoiceActivity.mockRejectedValueOnce(new Error('down'))
    await expect(getActivityAction({ data: routeInput, context })).resolves.toBeTruthy()

    mocks.getChoiceActivity.mockRejectedValueOnce(new RestError('diagnostic', 409))
    mocks.getDiagnostic.mockResolvedValueOnce({
      status: 'diagnosing',
      pendingAttemptId: ids.attemptId,
      nextCompetencyId: ids.competencyId,
      nextActivityId: ids.activityId,
    })
    await expect(
      getActivityAction({
        data: { ...routeInput, diagnosticRunId: ids.diagnosticRunId },
        context,
      }),
    ).resolves.toEqual({ kind: 'unavailable', diagnosticProcessing: true })
    mocks.getChoiceActivity.mockRejectedValueOnce(new RestError('diagnostic', 409))
    mocks.getDiagnostic.mockResolvedValueOnce({ readyToComplete: true })
    await expect(
      getActivityAction({
        data: { ...routeInput, diagnosticRunId: ids.diagnosticRunId },
        context,
      }),
    ).resolves.toEqual({ kind: 'unavailable', diagnosticProcessing: true })
    mocks.getChoiceActivity.mockRejectedValueOnce(new RestError('diagnostic', 409))
    mocks.getDiagnostic.mockRejectedValueOnce(new RestError('stale', 409))
    await expect(
      getActivityAction({
        data: { ...routeInput, diagnosticRunId: ids.diagnosticRunId },
        context,
      }),
    ).resolves.toMatchObject({ diagnosticRunStale: true })
    mocks.getChoiceActivity.mockRejectedValueOnce(new RestError('diagnostic', 409))
    mocks.getDiagnostic.mockResolvedValueOnce({ status: 'completed' })
    await expect(
      getActivityAction({
        data: { ...routeInput, diagnosticRunId: ids.diagnosticRunId },
        context,
      }),
    ).resolves.toMatchObject({ statusCode: 409 })
  })
})
