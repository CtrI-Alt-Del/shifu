import type { CompetencyDetail } from '@/core/learning/competency-detail'
import type { SkillExperienceDetail } from '@/core/learning/skill-experience'
import type {
  ChoiceActivityDetail,
  ChoiceAttemptDetail,
  ChoiceSubmission,
  ChoiceSubmissionResult,
  ActivityAnswer,
  ActivityQuestion,
  ActivityResultQuestion,
  PreliminaryQuestionResult,
} from '@/core/learning/choice-activity'
import type { GoalSummary } from '@/core/learning/goal-summary'
import { CurriculumGapError } from '@/core/learning/curriculum-gap-error'
import type { CreatedSkillExperience } from '@/core/learning/created-skill-experience'
import type {
  AvailableSkill,
  DiagnosticOverview,
  DiagnosticSubmissionItem,
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
  activity_revision?: string | null
  questions: Array<
    | {
        key: string
        kind: 'single_choice' | 'multiple_selection'
        prompt: string
        options: { key: string; text: string }[]
      }
    | {
        key: string
        kind: 'javascript_stdin'
        prompt: string
        initial_files: { path: string; content: string; editable: boolean }[]
        entrypoint: string
        editable_paths: string[]
        fixed_dependencies: { name: string; version: string }[]
        permitted_commands: { id: string; executable: string; arguments: string[] }[]
        criteria: { key: string; name: string; weight_percentage: number }[]
      }
  >
  can_submit: boolean
  latest_attempt_id?: string | null
  unresolved_attempt_id?: string | null
  is_diagnostic?: boolean
}

function mapActivityQuestion(
  question: ActivityWire['questions'][number],
): ActivityQuestion {
  if (question.kind !== 'javascript_stdin') return question

  return {
    key: question.key,
    kind: question.kind,
    prompt: question.prompt,
    initialFiles: question.initial_files,
    entrypoint: question.entrypoint,
    editablePaths: question.editable_paths,
    fixedDependencies: question.fixed_dependencies,
    permittedCommands: question.permitted_commands,
    criteria: question.criteria.map((criterion) => ({
      key: criterion.key,
      name: criterion.name,
      weightPercentage: criterion.weight_percentage,
    })),
  }
}

function mapAnswer(answer: ActivityAnswer) {
  if (answer.kind === 'javascript_stdin') {
    return { kind: answer.kind, question_key: answer.questionKey, files: answer.files }
  }
  return {
    kind: answer.kind ?? 'single_choice',
    question_key: answer.questionKey,
    selected_option_keys: answer.selectedOptionKeys,
  }
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
  questions?: Array<
    | {
        question_key: string
        prompt: string
        selected_option_keys: string[]
        score: number
        is_correct: boolean
        explanation: string
        disclosed_correct_option_keys?: string[]
      }
    | {
        question_key: string
        kind: 'javascript_stdin'
        prompt: string
        submitted_files: { path: string; content: string }[]
        score: number | null
        criterion_results: {
          key: string
          weight_percentage: number
          level: number | string
          comment_id: string
          comment: string
        }[]
        concept_observations: {
          concept_id: string
          level: number | string
          observation_id: string
        }[]
      }
  >
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
    questions: wire.questions?.map((question): ActivityResultQuestion => {
      if ('kind' in question && question.kind === 'javascript_stdin') {
        return {
          key: question.question_key,
          kind: question.kind,
          prompt: question.prompt,
          score: question.score,
          submittedFiles: question.submitted_files,
          criterionResults: question.criterion_results.map((criterion) => ({
            key: criterion.key,
            weightPercentage: criterion.weight_percentage,
            level: criterion.level,
            commentId: criterion.comment_id,
            comment: criterion.comment,
          })),
          conceptObservations: question.concept_observations.map((observation) => ({
            conceptId: observation.concept_id,
            level: observation.level,
            observationId: observation.observation_id,
          })),
        }
      }
      if (!('selected_option_keys' in question)) {
        throw new Error('Resposta de questão desconhecida.')
      }
      return {
        key: question.question_key,
        prompt: question.prompt,
        submittedOptionKeys: question.selected_option_keys,
        score: question.score,
        isCorrect: question.is_correct,
        explanation: question.explanation,
        correctOptionKeys: question.disclosed_correct_option_keys,
      }
    }),
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
      entryKey: string,
    ): Promise<{ diagnosticRunId: string; status: 'diagnosing' }> {
      const response = await restClient.post<{
        code?: string
        status: 'diagnosing'
        diagnosticRunId: string
      }>(
        `/learning/goals/${encodeURIComponent(goalId)}/skills/${encodeURIComponent(skillId)}/start`,
        { entry_key: entryKey },
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.statusCode === 409 && response._body?.code === 'curriculum_gap') {
        throw new CurriculumGapError()
      }
      if (response.isFailure) response.throwError()

      return response.body
    },

    async abandonDiagnostic(
      accessToken: string,
      goalId: string,
      skillId: string,
      diagnosticRunId: string,
    ): Promise<void> {
      const response = await restClient.post<unknown>(
        `/learning/goals/${encodeURIComponent(goalId)}/skills/${encodeURIComponent(skillId)}/diagnostic/abandon`,
        {},
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            'X-Diagnostic-Run-Id': diagnosticRunId,
          },
        },
      )
      if (response.isFailure) response.throwError()
    },

    async completeDiagnostic(
      accessToken: string,
      goalId: string,
      skillId: string,
      diagnosticRunId: string,
    ): Promise<{ status: 'learning' | 'completed' }> {
      const response = await restClient.post<{
        status: 'learning' | 'completed'
      }>(
        `/learning/goals/${encodeURIComponent(goalId)}/skills/${encodeURIComponent(skillId)}/diagnostic/complete`,
        {},
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            'X-Diagnostic-Run-Id': diagnosticRunId,
          },
        },
      )
      if (response.isFailure) response.throwError()

      return response.body
    },

    async getDiagnostic(
      accessToken: string,
      goalId: string,
      skillId: string,
      diagnosticRunId?: string,
    ): Promise<DiagnosticOverview> {
      const response = await restClient.get<DiagnosticOverview>(
        `/learning/goals/${encodeURIComponent(goalId)}/skills/${encodeURIComponent(skillId)}/diagnostic`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            ...(diagnosticRunId ? { 'X-Diagnostic-Run-Id': diagnosticRunId } : {}),
          },
        },
      )
      if (response.isFailure) response.throwError()

      return {
        ...response.body,
        activitySequence: response.body.activitySequence ?? [],
        initialRecommendation: response.body.initialRecommendation ?? null,
        initialRecommendationGap: response.body.initialRecommendationGap ?? null,
      }
    },

    async submitDiagnostic(
      accessToken: string,
      goalId: string,
      skillId: string,
      diagnosticRunId: string,
      submission: { submissionKey: string; items: DiagnosticSubmissionItem[] },
    ): Promise<{ status: 'pending'; replayed: boolean }> {
      const response = await restClient.post<{
        status: 'pending'
        replayed: boolean
      }>(
        `/learning/goals/${encodeURIComponent(goalId)}/skills/${encodeURIComponent(skillId)}/diagnostic/submissions`,
        {
          submission_key: submission.submissionKey,
          items: submission.items.map((item) => ({
            competency_id: item.competencyId,
            activity_id: item.activityId,
            activity_revision: item.activityRevision,
            answers: item.answers.map(mapAnswer),
          })),
        },
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            'X-Diagnostic-Run-Id': diagnosticRunId,
          },
        },
      )
      if (response.isFailure) response.throwError()

      return response.body
    },

    async retryDiagnosticEvaluation(
      accessToken: string,
      ids: ActivityIds & { attemptId: string },
      diagnosticRunId?: string,
    ): Promise<void> {
      const response = await restClient.post<unknown>(
        `${learningAttemptsPath(ids)}/${encodeURIComponent(ids.attemptId)}/retry`,
        {},
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            ...(diagnosticRunId ? { 'X-Diagnostic-Run-Id': diagnosticRunId } : {}),
          },
        },
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

    async getSkillExperienceDetail(
      accessToken: string,
      goalId: string,
      skillId: string,
    ): Promise<SkillExperienceDetail> {
      const response = await restClient.get<SkillExperienceDetail>(
        `/learning/goals/${goalId}/skills/${skillId}`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()

      return response.body
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
      diagnosticRunId?: string,
    ): Promise<ChoiceActivityDetail> {
      const response = await restClient.get<ActivityWire>(learningActivityPath(ids), {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          ...(diagnosticRunId ? { 'X-Diagnostic-Run-Id': diagnosticRunId } : {}),
        },
      })
      if (response.isFailure) response.throwError()

      const body = response.body

      return {
        activityId: body.activity_id,
        title: body.title,
        difficulty: body.difficulty,
        activityRevision: body.activity_revision,
        questions: body.questions.map(mapActivityQuestion),
        canSubmit: body.can_submit,
        latestAttemptId: body.latest_attempt_id ?? null,
        unresolvedAttemptId: body.unresolved_attempt_id ?? null,
        isDiagnostic: body.is_diagnostic ?? false,
      }
    },

    async previewActivityQuestion(
      accessToken: string,
      ids: ActivityIds,
      questionKey: string,
      activityRevision: string,
      answer: ActivityAnswer,
    ): Promise<PreliminaryQuestionResult> {
      const response = await restClient.post<{
        status: 'conclusive' | 'inconclusive'
        score?: number | null
        explanation?: string
        is_correct?: boolean
        criteria?: {
          key: string
          weight_percentage: number
          level: string
          comment_id: string
          comment: string
        }[]
        submitted_files?: { path: string; content: string }[]
      }>(
        `${learningActivityPath(ids)}/questions/${encodeURIComponent(questionKey)}/preliminary-evaluations`,
        { activity_revision: activityRevision, answer: mapAnswer(answer) },
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (response.isFailure) response.throwError()

      const body = response.body
      return {
        status: body.status,
        score: body.score ?? null,
        explanation: body.explanation,
        isCorrect: body.is_correct,
        criteria: body.criteria?.map((criterion) => ({
          key: criterion.key,
          weightPercentage: criterion.weight_percentage,
          level: criterion.level,
          commentId: criterion.comment_id,
          comment: criterion.comment,
        })),
        submittedFiles: body.submitted_files,
      }
    },

    async submitChoiceActivity(
      accessToken: string,
      ids: ActivityIds,
      submission: ChoiceSubmission,
      diagnosticRunId?: string,
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
          ...(submission.activityRevision
            ? { activity_revision: submission.activityRevision }
            : {}),
          answers: submission.answers.map((answer) =>
            submission.activityRevision
              ? mapAnswer(answer)
              : {
                  question_key: answer.questionKey,
                  selected_option_keys:
                    'selectedOptionKeys' in answer ? answer.selectedOptionKeys : [],
                },
          ),
        },
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            ...(diagnosticRunId ? { 'X-Diagnostic-Run-Id': diagnosticRunId } : {}),
          },
        },
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

    async deleteGoal(accessToken: string, goalId: string): Promise<void> {
      const response = await restClient.delete<void>(
        `/learning/goals/${goalId}`,
        undefined,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) response.throwError()
    },

    async removeSkill(
      accessToken: string,
      goalId: string,
      skillId: string,
    ): Promise<void> {
      const response = await restClient.delete<void>(
        `/learning/goals/${encodeURIComponent(goalId)}/skills/${encodeURIComponent(skillId)}`,
        undefined,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) response.throwError()
    },
  }
}
