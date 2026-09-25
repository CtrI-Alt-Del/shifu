import type { CompetencyDetail } from '@/core/learning/competency-detail'
import type {
  ChoiceActivityDetail,
  ChoiceAttemptDetail,
  ChoiceSubmission,
  ChoiceSubmissionResult,
} from '@/core/learning/choice-activity'
import type { GoalSummary } from '@/core/learning/goal-summary'
import { CurriculumGapError } from '@/core/learning/curriculum-gap-error'
import type { CreatedSkillExperience } from '@/core/learning/created-skill-experience'
import type {
  AvailableSkill,
  DiagnosticOverview,
  GoalDetail,
} from '@/core/learning/goal-detail'
import type { MaterialDetail } from '@/core/learning/material-detail'
import type { SkillCatalogPage } from '@/core/learning/skill-catalog-page'
import type { RestClient } from '@/core/shared/interfaces/rest-client'
import { learningActivityPath, learningAttemptsPath } from '@/constants/routes'

type ActivityIds = {
  goalId: string
  skillId: string
  competencyId: string
  activityId: string
}

type ActivityWire = {
  activity_id: string
  title: string
  difficulty: ChoiceActivityDetail['difficulty']
  questions: ChoiceActivityDetail['questions']
  can_submit: boolean
  latest_attempt_id?: string | null
  unresolved_attempt_id?: string | null
  is_diagnostic?: boolean
}

type AttemptWire = {
  attempt_id: string
  activity_id: string
  status: ChoiceAttemptDetail['status']
  submitted_at: string
  retry_allowed: boolean
  failure_message?: string | null
  score?: number | null
  progress_before?: number | null
  progress_after?: number | null
  status_before?: ChoiceAttemptDetail['statusBefore']
  status_after?: ChoiceAttemptDetail['statusAfter']
  next_action?: {
    competency_id: string
    activity_id: string
    difficulty: 'easy' | 'medium' | 'hard'
    type: 'new-activity' | 'reinforcement'
  } | null
  questions?: Array<{
    question_key: string
    prompt: string
    selected_option_keys: string[]
    score: number
    is_correct: boolean
    explanation: string
    disclosed_correct_option_keys?: string[]
  }>
}

function mapAttempt(wire: AttemptWire): ChoiceAttemptDetail {
  return {
    attemptId: wire.attempt_id,
    activityId: wire.activity_id,
    status: wire.status,
    submittedAt: wire.submitted_at,
    retryAllowed: wire.retry_allowed,
    failureMessage: wire.failure_message,
    score: wire.score,
    progressBefore: wire.progress_before,
    progressAfter: wire.progress_after,
    statusBefore: wire.status_before,
    statusAfter: wire.status_after,
    nextAction: wire.next_action
      ? {
          competencyId: wire.next_action.competency_id,
          activityId: wire.next_action.activity_id,
          difficulty: wire.next_action.difficulty,
          type: wire.next_action.type,
        }
      : wire.next_action,
    questions: wire.questions?.map((question) => ({
      key: question.question_key,
      prompt: question.prompt,
      submittedOptionKeys: question.selected_option_keys,
      score: question.score,
      isCorrect: question.is_correct,
      explanation: question.explanation,
      correctOptionKeys: question.disclosed_correct_option_keys,
    })),
  }
}

export type LearningService = ReturnType<typeof LearningService>

export const LearningService = (restClient: RestClient) => {
  return {
    async getAvailableSkills(accessToken: string): Promise<AvailableSkill[]> {
      const response = await restClient.get<{ skills: AvailableSkill[] }>(
        '/learning/available-skills',
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return response.body.skills
    },

    async createGoal(
      accessToken: string,
      input: { title: string; description: string; skillIds: string[] },
    ): Promise<{ goalId: string; skillIds: string[] }> {
      const response = await restClient.post<{
        goalId: string
        skillIds: string[]
        code?: string
      }>('/learning/goals', input, {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      if (response.statusCode === 409 && response._body?.code === 'curriculum_gap') {
        throw new CurriculumGapError()
      }
      if (response.isFailure) response.throwError()
      return response.body
    },

    async getGoalDetail(accessToken: string, goalId: string): Promise<GoalDetail> {
      const response = await restClient.get<GoalDetail>(
        `/learning/goals/${encodeURIComponent(goalId)}`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return response.body
    },

    async startSkill(
      accessToken: string,
      goalId: string,
      skillId: string,
    ): Promise<void> {
      const response = await restClient.post<{
        code?: string
        status?: 'diagnosing'
      }>(
        `/learning/goals/${encodeURIComponent(goalId)}/skills/${encodeURIComponent(skillId)}/start`,
        {},
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.statusCode === 409 && response._body?.code === 'curriculum_gap') {
        throw new CurriculumGapError()
      }
      if (response.isFailure) response.throwError()
    },

    async getDiagnostic(
      accessToken: string,
      goalId: string,
      skillId: string,
    ): Promise<DiagnosticOverview> {
      const response = await restClient.get<DiagnosticOverview>(
        `/learning/goals/${encodeURIComponent(goalId)}/skills/${encodeURIComponent(skillId)}/diagnostic`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return response.body
    },

    async retryDiagnosticEvaluation(
      accessToken: string,
      ids: ActivityIds & { attemptId: string },
    ): Promise<void> {
      const response = await restClient.post<unknown>(
        `${learningAttemptsPath(ids)}/${encodeURIComponent(ids.attemptId)}/retry`,
        {},
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
    },

    async getGoals(accessToken: string): Promise<GoalSummary[]> {
      const response = await restClient.get<{ goals: GoalSummary[] }>('/learning/goals', {
        headers: { Authorization: `Bearer ${accessToken}` },
      })

      if (response.isFailure) response.throwError()
      return response.body.goals
    },

    async getCompetencyDetail(
      accessToken: string,
      goalId: string,
      skillId: string,
      competencyId: string,
    ): Promise<CompetencyDetail> {
      const response = await restClient.get<CompetencyDetail>(
        `/learning/goals/${goalId}/skills/${skillId}/competencies/${competencyId}`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) response.throwError()

      return response.body
    },

    async getMaterialDetail(
      accessToken: string,
      ids: Omit<ActivityIds, 'activityId'> & { materialId: string },
    ): Promise<MaterialDetail> {
      const { goalId, skillId, competencyId, materialId } = ids
      const path = `/learning/goals/${encodeURIComponent(goalId)}/skills/${encodeURIComponent(skillId)}/competencies/${encodeURIComponent(competencyId)}/materials/${encodeURIComponent(materialId)}`
      const response = await restClient.get<MaterialDetail>(path, {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      if (response.isFailure) response.throwError()
      return response.body
    },

    async getChoiceActivity(
      accessToken: string,
      ids: ActivityIds,
    ): Promise<ChoiceActivityDetail> {
      const response = await restClient.get<ActivityWire>(learningActivityPath(ids), {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
      if (response.isFailure) response.throwError()
      const body = response.body

      return {
        activityId: body.activity_id,
        title: body.title,
        difficulty: body.difficulty,
        questions: body.questions,
        canSubmit: body.can_submit,
        latestAttemptId: body.latest_attempt_id ?? null,
        unresolvedAttemptId: body.unresolved_attempt_id ?? null,
        isDiagnostic: body.is_diagnostic ?? false,
      }
    },

    async submitChoiceActivity(
      accessToken: string,
      ids: ActivityIds,
      submission: ChoiceSubmission,
    ): Promise<ChoiceSubmissionResult> {
      const response = await restClient.post<{
        attempt_id: string
        status: 'pending'
        result_url: string
        is_diagnostic?: boolean
      }>(
        learningAttemptsPath(ids),
        {
          submission_key: submission.submissionKey,
          answers: submission.answers.map((answer) => ({
            question_key: answer.questionKey,
            selected_option_keys: answer.selectedOptionKeys,
          })),
        },
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return {
        attemptId: response.body.attempt_id,
        status: response.body.status,
        resultUrl: response.body.result_url,
        isDiagnostic: response.body.is_diagnostic ?? false,
      }
    },

    async getChoiceAttempt(
      accessToken: string,
      ids: ActivityIds & { attemptId: string },
    ): Promise<ChoiceAttemptDetail> {
      const response = await restClient.get<AttemptWire>(
        `${learningAttemptsPath(ids)}/${encodeURIComponent(ids.attemptId)}`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return mapAttempt(response.body)
    },

    async retryChoiceEvaluation(
      accessToken: string,
      ids: ActivityIds & { attemptId: string },
    ): Promise<void> {
      const response = await restClient.post<unknown>(
        `${learningAttemptsPath(ids)}/${encodeURIComponent(ids.attemptId)}/retry`,
        {},
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
    },

    async searchSkillCatalog(
      accessToken: string,
      goalId: string,
      params: { query?: string; cursor?: string; limit?: number },
    ): Promise<SkillCatalogPage> {
      const response = await restClient.get<SkillCatalogPage>(
        `/learning/goals/${encodeURIComponent(goalId)}/skills/catalog`,
        {
          params,
          headers: { Authorization: `Bearer ${accessToken}` },
        },
      )
      if (response.isFailure) response.throwError()
      return response.body
    },

    async addSkillToGoal(
      accessToken: string,
      goalId: string,
      skillId: string,
      foundationSkillIds: readonly string[],
    ): Promise<CreatedSkillExperience[]> {
      const response = await restClient.post<{ created: CreatedSkillExperience[] }>(
        `/learning/goals/${encodeURIComponent(goalId)}/skills`,
        { skill_id: skillId, foundation_skill_ids: foundationSkillIds },
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()
      return response.body.created
    },
  }
}
