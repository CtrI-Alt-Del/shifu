import type { DiagnosticSubmissionItem } from '@/core/learning/goal-detail'

type DiagnosticRun = {
  diagnosticRunId: string
  answers: Map<string, DiagnosticSubmissionItem>
  submissionKey: string | null
  submitted: boolean
  sequence: { competencyId: string; activityId: string }[]
}

const diagnosticRuns = new Map<string, DiagnosticRun>()

function getKey(goalId: string, skillId: string) {
  return `${goalId}:${skillId}`
}

export function getDiagnosticRun(goalId: string, skillId: string): DiagnosticRun | null {
  return diagnosticRuns.get(getKey(goalId, skillId)) ?? null
}

export function setDiagnosticRun(
  goalId: string,
  skillId: string,
  diagnosticRunId: string,
): DiagnosticRun {
  const current = getDiagnosticRun(goalId, skillId)
  if (current?.diagnosticRunId === diagnosticRunId) return current

  const run = {
    diagnosticRunId,
    answers: new Map<string, DiagnosticSubmissionItem>(),
    submissionKey: null,
    submitted: false,
    sequence: [],
  }
  diagnosticRuns.set(getKey(goalId, skillId), run)
  return run
}

export function setDiagnosticSequence(
  goalId: string,
  skillId: string,
  diagnosticRunId: string,
  sequence: { competencyId: string; activityId: string }[],
): void {
  const run = getDiagnosticRun(goalId, skillId)
  if (run?.diagnosticRunId === diagnosticRunId) run.sequence = sequence
}

export function stageDiagnosticActivity(
  goalId: string,
  skillId: string,
  diagnosticRunId: string,
  item: DiagnosticSubmissionItem,
): void {
  const run = getDiagnosticRun(goalId, skillId)
  if (!run || run.diagnosticRunId !== diagnosticRunId || run.submitted) return

  run.answers.set(`${item.competencyId}:${item.activityId}`, item)
}

export function prepareDiagnosticSubmission(
  goalId: string,
  skillId: string,
  diagnosticRunId: string,
  sequence: readonly { competencyId: string; activityId: string }[],
): { submissionKey: string; items: DiagnosticSubmissionItem[] } | null {
  const run = getDiagnosticRun(goalId, skillId)
  if (!run || run.diagnosticRunId !== diagnosticRunId || !sequence.length) return null

  const items = sequence.map((entry) =>
    run.answers.get(`${entry.competencyId}:${entry.activityId}`),
  )
  if (items.some((item) => !item)) return null

  run.submissionKey ??= globalThis.crypto.randomUUID()
  return { submissionKey: run.submissionKey, items: items as DiagnosticSubmissionItem[] }
}

export function markDiagnosticSubmitted(
  goalId: string,
  skillId: string,
  diagnosticRunId: string,
): void {
  const run = getDiagnosticRun(goalId, skillId)
  if (run?.diagnosticRunId === diagnosticRunId) run.submitted = true
}

export function clearDiagnosticRun(goalId: string, skillId: string): void {
  diagnosticRuns.delete(getKey(goalId, skillId))
}
