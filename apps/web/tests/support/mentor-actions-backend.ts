import type { Page, Route } from '@playwright/test'

import { ROUTES } from '../../src/constants/routes'
import { expect, navigateAuthenticatedPage } from '../playwright'
import {
  openMentorPage,
  serverFnExport,
  serverFnInput,
  SESSION_ID,
  SESSION_TITLE,
} from './mentor-memories-backend'

/**
 * Controlled, stateful backend for the SHIFU-104 confirmed-action suites. It answers
 * the BFF server functions with the post-mapping shapes the web layer consumes and the
 * response event stream with raw events, so it proves rendered contracts and outgoing
 * BFF requests, not real Learning or Intelligence persistence.
 */
export const ACTION_IDS = {
  learner: '01J7T8AC91Z5K8M4JQ8C2D6F51',
  answer: '01J7T8AC91Z5K8M4JQ8C2D6F52',
  proposal: '01J7T8AC91Z5K8M4JQ8C2D6F53',
  skill: '01J7T8AC91Z5K8M4JQ8C2D6F54',
  goal: '01J7T8AC91Z5K8M4JQ8C2D6F55',
  otherGoal: '01J7T8AC91Z5K8M4JQ8C2D6F56',
  experience: '01J7T8AC91Z5K8M4JQ8C2D6F57',
  otherExperience: '01J7T8AC91Z5K8M4JQ8C2D6F58',
  attempt: '01J7T8AC91Z5K8M4JQ8C2D6F59',
} as const

export const GOAL_TITLE = 'Aprender a programar'
export const OTHER_GOAL_TITLE = 'Construir meu portfólio'
export const SKILL_NAME = 'Funções em Python'
export const BLOCK_REASON = 'Confirme ou recuse a ação proposta para continuar.'
export const ADD_JUSTIFICATION =
  'Você pediu ao Mentor para adicionar esta Habilidade. Funções, parâmetros e retornos em Python.'

type Kind = 'add_skill' | 'remove_skill'

export type BackendProposal = {
  id: string
  sourceMessageId: string
  kind: Kind
  skillId: string
  skillName: string
  goalId: string | null
  goalTitle: string | null
  skillExperienceId: string | null
  candidateGoals: {
    goalId: string
    title: string
    containsSkill: boolean
    skillExperienceId: string | null
  }[]
  justification: string | null
  status: 'pending' | 'declined' | 'completed' | 'rejected'
  outcome: 'added' | 'already_present' | 'removed' | null
  rejectionReason: string | null
  resolvedGoalId: string | null
  resolvedSkillExperienceId: string | null
  createdAt: string
}

export type ConfirmationOutcome = {
  confirmationId: string
  operation: Kind
  outcome: 'added' | 'already_present' | 'removed' | 'rejected'
  rejectionReason: string | null
  goalId: string
  skillId: string | null
  skillExperienceId: string | null
}

/** What the next Learning confirmation answers: an outcome, a status code or a lost response. */
export type ConfirmationStep =
  | { kind: 'success'; outcome: ConfirmationOutcome }
  | { kind: 'failure'; statusCode: number }
  | { kind: 'abort' }

export type ActionCall = {
  exportName: string
  method: string
  data: Record<string, unknown>
}

export function buildProposal(
  kind: Kind,
  overrides: Partial<BackendProposal> = {},
): BackendProposal {
  return {
    id: ACTION_IDS.proposal,
    sourceMessageId: ACTION_IDS.learner,
    kind,
    skillId: ACTION_IDS.skill,
    skillName: SKILL_NAME,
    goalId: ACTION_IDS.goal,
    goalTitle: GOAL_TITLE,
    skillExperienceId: kind === 'remove_skill' ? ACTION_IDS.experience : null,
    candidateGoals: [],
    justification: kind === 'add_skill' ? ADD_JUSTIFICATION : null,
    status: 'pending',
    outcome: null,
    rejectionReason: null,
    resolvedGoalId: null,
    resolvedSkillExperienceId: null,
    createdAt: '2026-10-23T12:00:02Z',
    ...overrides,
  }
}

export function buildPickerProposal(kind: Kind): BackendProposal {
  return buildProposal(kind, {
    goalId: null,
    goalTitle: null,
    skillExperienceId: null,
    candidateGoals: [
      {
        goalId: ACTION_IDS.goal,
        title: GOAL_TITLE,
        containsSkill: kind === 'remove_skill',
        skillExperienceId: kind === 'remove_skill' ? ACTION_IDS.experience : null,
      },
      {
        goalId: ACTION_IDS.otherGoal,
        title: OTHER_GOAL_TITLE,
        containsSkill: true,
        skillExperienceId: ACTION_IDS.otherExperience,
      },
    ],
  })
}

export function outcomeOf(
  proposal: BackendProposal,
  overrides: Partial<ConfirmationOutcome> = {},
): ConfirmationOutcome {
  return {
    confirmationId: proposal.id,
    operation: proposal.kind,
    outcome: proposal.kind === 'add_skill' ? 'added' : 'removed',
    rejectionReason: null,
    goalId: proposal.goalId ?? ACTION_IDS.goal,
    skillId: proposal.skillId,
    skillExperienceId: ACTION_IDS.experience,
    ...overrides,
  }
}

export type ActionsBackendOptions = {
  proposal: BackendProposal
  /** Extra plain text of the Mentor answer, such as Markdown links. */
  answer?: string
  /** Reads of the session detail after a confirmation before Intelligence records the outcome. */
  readsUntilFinal?: number
  /** Serves the proposal only through the response stream, as in a live answer. */
  isLive?: boolean
  goalDetail?: (state: { isAdded: boolean }) => unknown
}

export type ActionsBackend = {
  calls: ActionCall[]
  callsOf: (name: string) => ActionCall[]
  proposal: () => BackendProposal
  enqueue: (...steps: ConfirmationStep[]) => void
  /** Makes Intelligence record the pending outcome on the next session detail read. */
  finalizeOnNextRead: () => void
}

const ANSWER_TEXT = 'Preparei uma proposta para você confirmar.'

export async function installMentorActionsBackend(
  page: Page,
  options: ActionsBackendOptions,
): Promise<ActionsBackend> {
  const calls: ActionCall[] = []
  const queue: ConfirmationStep[] = []
  let proposal = options.proposal
  let remainingReads = Number.POSITIVE_INFINITY
  let pendingOutcome: ConfirmationOutcome | null = null
  let isAdded = false
  const readsUntilFinal = options.readsUntilFinal ?? 2
  const session = {
    id: SESSION_ID,
    title: SESSION_TITLE,
    createdAt: '2026-10-23T12:00:00Z',
    updatedAt: '2026-10-23T12:00:05Z',
    lastActivityAt: '2026-10-23T12:00:05Z',
  }

  function fulfillJson(route: Route, result: unknown) {
    return route.fulfill({
      body: JSON.stringify({ result }),
      contentType: 'application/json',
      status: 200,
    })
  }

  function applyOutcome(outcome: ConfirmationOutcome) {
    proposal =
      outcome.outcome === 'rejected'
        ? { ...proposal, status: 'rejected', rejectionReason: outcome.rejectionReason }
        : {
            ...proposal,
            status: 'completed',
            outcome: outcome.outcome,
            resolvedGoalId: outcome.goalId,
            resolvedSkillExperienceId: outcome.skillExperienceId,
          }
  }

  function detail() {
    if (pendingOutcome) {
      remainingReads -= 1
      if (remainingReads <= 0) {
        applyOutcome(pendingOutcome)
        pendingOutcome = null
      }
    }
    const answer = options.answer ?? ANSWER_TEXT
    return {
      session,
      messages: {
        items: [
          {
            id: ACTION_IDS.learner,
            sessionId: SESSION_ID,
            role: 'learner',
            content:
              proposal.kind === 'add_skill'
                ? 'Adicione Funções em Python ao meu Objetivo'
                : 'Remova Funções em Python deste Objetivo',
            createdAt: '2026-10-23T12:00:00Z',
            inReplyToMessageId: null,
            attachments: [],
          },
          ...(options.isLive
            ? []
            : [
                {
                  id: ACTION_IDS.answer,
                  sessionId: SESSION_ID,
                  role: 'mentor',
                  content: answer,
                  createdAt: '2026-10-23T12:00:02Z',
                  inReplyToMessageId: ACTION_IDS.learner,
                  attachments: [],
                },
              ]),
        ],
        nextCursor: null,
      },
      pendingLearnerMessageId: options.isLive ? ACTION_IDS.learner : null,
      response: options.isLive
        ? {
            attemptId: ACTION_IDS.attempt,
            learnerMessageId: ACTION_IDS.learner,
            status: 'processing',
            blocks: [],
            consultations: [],
            lastSequence: 1,
            failureCode: null,
            progress: null,
          }
        : null,
      summary: { current: null, failureAfterMessageId: null },
      memoryItems: [],
      actionItems: options.isLive && proposal.status === 'pending' ? [] : [proposal],
    }
  }

  await page.route(
    /\/api\/intelligence\/mentor-sessions\/[^/]+\/events/,
    async (route) => {
      const event = (sequence: number, overrides: Record<string, unknown>) =>
        `id: ${sequence}\nevent: mentor.response\ndata: ${JSON.stringify({
          session_id: SESSION_ID,
          attempt_id: ACTION_IDS.attempt,
          sequence,
          kind: 'status',
          status: 'processing',
          block: null,
          consultation: null,
          progress: null,
          failure_code: null,
          created_at: '2026-10-23T12:00:02Z',
          ...overrides,
        })}\n\n`
      options.isLive = false
      await route.fulfill({
        body: [
          event(2, {
            kind: 'block',
            block: {
              block_key: 'proposal',
              ordinal: 0,
              intent: proposal.kind,
              content: ANSWER_TEXT,
            },
          }),
          event(3, {
            kind: 'action',
            action_proposal: {
              id: proposal.id,
              source_message_id: proposal.sourceMessageId,
              kind: proposal.kind,
              skill_id: proposal.skillId,
              skill_name: proposal.skillName,
              goal_id: proposal.goalId,
              goal_title: proposal.goalTitle,
              skill_experience_id: proposal.skillExperienceId,
              candidate_goals: proposal.candidateGoals.map((candidate) => ({
                goal_id: candidate.goalId,
                title: candidate.title,
                contains_skill: candidate.containsSkill,
                skill_experience_id: candidate.skillExperienceId,
              })),
              justification: proposal.justification,
              status: proposal.status,
              outcome: proposal.outcome,
              rejection_reason: proposal.rejectionReason,
              resolved_goal_id: proposal.resolvedGoalId,
              resolved_skill_experience_id: proposal.resolvedSkillExperienceId,
              created_at: proposal.createdAt,
            },
          }),
          event(4, { kind: 'completed', status: 'completed' }),
        ].join(''),
        contentType: 'text/event-stream',
        headers: { 'Cache-Control': 'no-store' },
        status: 200,
      })
    },
  )

  await page.route('**/_serverFn/**', async (route) => {
    const request = route.request()
    const exportName = serverFnExport(request.url()) ?? ''
    const data = serverFnInput(request)

    if (exportName.startsWith('getAchievements_')) {
      await fulfillJson(route, {
        kind: 'success',
        overview: { level: 1, totalXp: 0, xpForNextLevel: 100, achievements: [] },
      })
      return
    }
    if (exportName.includes('listMentorSessionsServer')) {
      await fulfillJson(route, { items: [session], nextCursor: null })
      return
    }
    if (exportName.includes('getMentorSessionServer')) {
      calls.push({ exportName, method: request.method(), data })
      await fulfillJson(route, detail())
      return
    }
    if (exportName.includes('getGoalDetail') && options.goalDetail) {
      calls.push({ exportName, method: request.method(), data })
      await fulfillJson(route, {
        kind: 'success',
        detail: options.goalDetail({ isAdded }),
      })
      return
    }
    if (exportName.includes('declineMentorActionProposalServer')) {
      calls.push({ exportName, method: request.method(), data })
      proposal = { ...proposal, status: 'declined' }
      await fulfillJson(route, { kind: 'success', proposal })
      return
    }
    if (
      exportName.includes('confirmMentorSkillAdditionServer') ||
      exportName.includes('confirmMentorSkillRemovalServer')
    ) {
      calls.push({ exportName, method: request.method(), data })
      const step: ConfirmationStep = queue.shift() ?? {
        kind: 'success',
        outcome: outcomeOf(proposal),
      }
      if (step.kind === 'abort') {
        await route.abort('failed')
        return
      }
      if (step.kind === 'failure') {
        await fulfillJson(route, { kind: 'failure', statusCode: step.statusCode })
        return
      }
      // Learning answers at once; Intelligence records the outcome later (outcome job).
      pendingOutcome = step.outcome
      remainingReads = readsUntilFinal
      if (step.outcome.outcome === 'added') isAdded = true
      await fulfillJson(route, { kind: 'success', outcome: step.outcome })
      return
    }
    await route.fallback()
  })

  return {
    calls,
    callsOf: (name) => calls.filter((call) => call.exportName.includes(name)),
    proposal: () => proposal,
    enqueue: (...steps) => {
      queue.push(...steps)
    },
    finalizeOnNextRead: () => {
      remainingReads = 1
    },
  }
}

export async function openMentorActionsPage(page: Page) {
  await openMentorPage(page, { session: SESSION_ID })
  await expect(page.getByRole('heading', { level: 1, name: SESSION_TITLE })).toBeVisible()
}

export async function openMentorActionsFab(
  page: Page,
  route: string = ROUTES.gamification,
) {
  await navigateAuthenticatedPage(page, route)
  await page.getByRole('button', { name: 'Abrir Mentor' }).click()
  await page.getByRole('button', { name: 'Histórico de conversas' }).click()
  await page.getByRole('button', { name: SESSION_TITLE, exact: true }).click()
  await expect(page.getByRole('heading', { level: 1, name: SESSION_TITLE })).toBeVisible()
}
