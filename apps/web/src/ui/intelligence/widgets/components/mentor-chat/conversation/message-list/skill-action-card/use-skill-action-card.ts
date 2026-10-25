import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { HTTP_STATUS_CODE } from '@/constants/http-status-code'
import { RestError } from '@/core/errors/rest-error'
import type {
  MentorActionCandidateGoal,
  MentorActionProposal,
  MentorActionRejectionReason,
} from '@/core/intelligence/mentor-action-proposal'
import type { MentorSkillActionOutcome } from '@/core/learning/mentor-skill-action-outcome'
import { useConfirmMentorSkillAdditionAction } from '@/ui/intelligence/hooks/use-confirm-mentor-skill-addition-action'
import { useConfirmMentorSkillRemovalAction } from '@/ui/intelligence/hooks/use-confirm-mentor-skill-removal-action'
import { useDeclineMentorActionProposalAction } from '@/ui/intelligence/hooks/use-decline-mentor-action-proposal-action'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import type {
  MentorActionCardProps,
  MentorActionCardTone,
} from '@/ui/intelligence/widgets/components/mentor-action-card'
import type { IconName } from '@/ui/shared/widgets/components/icon'

export type SkillActionCardDestination =
  | { kind: 'goal'; goalId: string }
  | { kind: 'skill'; goalId: string; skillId: string }

export type SkillActionCardAction = {
  key: string
  label: string
  variant: 'primary' | 'danger' | 'outline'
  disabled?: boolean
  handleSelect?: () => void
  destination?: SkillActionCardDestination
}

export type SkillActionCardPicker = {
  candidates: {
    goalId: string
    title: string
    isDisabled: boolean
    isSelected: boolean
  }[]
  hint: string
}

type Phase = 'idle' | 'processing' | 'failed' | 'uncertain'

type ConfirmationRequest =
  | {
      kind: 'add'
      goalId: string
      input: { confirmationId: string; skillId: string; justification: string }
    }
  | {
      kind: 'remove'
      goalId: string
      input: { confirmationId: string; skillExperienceId: string }
    }

type ResultState =
  | { kind: 'completed'; outcome: 'added' | 'already_present' | 'removed' }
  | { kind: 'rejected'; reason: MentorActionRejectionReason | null }
  | { kind: 'declined' }

const DEFAULT_ADD_JUSTIFICATION = 'Você pediu ao Mentor para adicionar esta Habilidade.'
const REMOVAL_REASON = 'Você pediu para retirar esta Habilidade do Objetivo.'
const REMOVAL_CONSEQUENCES =
  'Você perderá o diagnóstico, o progresso, o domínio, os conteúdos liberados, as tentativas, as avaliações, a justificativa e o resumo desta experiência. Não há restauração. O Objetivo e as outras Habilidades permanecem. Se adicionar novamente, começará do zero.'
const PROCESSING_RESULT = 'A confirmação está em andamento. Aguarde o resultado.'
const UNCERTAIN_RESULT =
  'Ainda não foi possível confirmar o resultado. Verifique a mesma confirmação antes de continuar.'
const NO_CHANGE_STATUS = 'Nenhuma alteração foi executada.'
const DECLINE_ERROR = 'Não foi possível recusar agora. Tente novamente.'
const REJECTION_REASON_TEXT: Record<MentorActionRejectionReason, string> = {
  goal_unavailable: 'Este Objetivo não está mais disponível.',
  skill_unavailable: 'Esta Habilidade não está mais disponível no Currículo.',
  experience_unavailable: 'Esta experiência já não está no Objetivo.',
}
const STEP_VIEW_KEYS = ['picker', 'proposal']

function describeIcon(
  kind: MentorActionProposal['kind'],
  isProposal: boolean,
): { name: IconName; tone: MentorActionCardTone } {
  if (kind === 'add_skill') return { name: 'graduation-cap', tone: 'jade' }
  return { name: 'trash-2', tone: isProposal ? 'danger' : 'muted' }
}

export function useSkillActionCard(proposal: MentorActionProposal) {
  const mentor = useMentorContext()
  const queryClient = useQueryClient()
  const { confirmSkillAddition } = useConfirmMentorSkillAdditionAction()
  const { confirmSkillRemoval } = useConfirmMentorSkillRemovalAction()
  const { declineActionProposal, isPending: isDeclining } =
    useDeclineMentorActionProposalAction()
  const [phase, setPhase] = useState<Phase>('idle')
  const [selectedGoalId, setSelectedGoalId] = useState<string | null>(null)
  const [isChangingGoal, setIsChangingGoal] = useState(false)
  const [localOutcome, setLocalOutcome] = useState<MentorSkillActionOutcome | null>(null)
  const [isLocallyDeclined, setIsLocallyDeclined] = useState(false)
  const [declineError, setDeclineError] = useState<string | null>(null)
  const lockedRequest = useRef<ConfirmationRequest | null>(null)
  const isConfirming = useRef(false)
  const resultRef = useRef<HTMLDivElement | null>(null)
  const titleRef = useRef<HTMLHeadingElement | null>(null)

  const isAddition = proposal.kind === 'add_skill'
  const skillName = proposal.skillName
  const isFixedDestination = proposal.goalId !== null
  const effectiveGoalId =
    lockedRequest.current?.goalId ?? proposal.goalId ?? selectedGoalId
  const effectiveCandidate: MentorActionCandidateGoal | null =
    proposal.candidateGoals.find((candidate) => candidate.goalId === effectiveGoalId) ??
    null
  const goalTitle = proposal.goalTitle ?? effectiveCandidate?.title ?? null

  function resolveResult(): ResultState | null {
    // Learning's own answer is the truth, even over a decline stored by Intelligence.
    if (localOutcome) {
      const { outcome, rejectionReason } = localOutcome
      return outcome === 'rejected'
        ? { kind: 'rejected', reason: rejectionReason }
        : { kind: 'completed', outcome }
    }
    if (proposal.status === 'declined') return { kind: 'declined' }
    if (proposal.status === 'rejected')
      return { kind: 'rejected', reason: proposal.rejectionReason }
    if (proposal.status === 'completed' && proposal.outcome)
      return { kind: 'completed', outcome: proposal.outcome }
    if (isLocallyDeclined) return { kind: 'declined' }
    return null
  }
  const result = resolveResult()
  const isPicking =
    !result &&
    phase === 'idle' &&
    !isFixedDestination &&
    (selectedGoalId === null || isChangingGoal)
  const viewKey = result
    ? result.kind === 'completed'
      ? `completed:${result.outcome}`
      : result.kind
    : phase === 'idle'
      ? isPicking
        ? 'picker'
        : 'proposal'
      : phase

  const previousViewKey = useRef(viewKey)
  useEffect(() => {
    if (previousViewKey.current === viewKey) return
    previousViewKey.current = viewKey
    const target = STEP_VIEW_KEYS.includes(viewKey) ? titleRef : resultRef
    target.current?.focus()
  }, [viewKey])

  function buildRequest(): ConfirmationRequest | null {
    const goalId = proposal.goalId ?? selectedGoalId
    if (!goalId) return null
    if (isAddition)
      return {
        kind: 'add',
        goalId,
        input: {
          confirmationId: proposal.id,
          skillId: proposal.skillId,
          justification: proposal.justification ?? DEFAULT_ADD_JUSTIFICATION,
        },
      }
    const skillExperienceId =
      proposal.skillExperienceId ??
      proposal.candidateGoals.find((candidate) => candidate.goalId === goalId)
        ?.skillExperienceId ??
      null
    if (!skillExperienceId) return null
    return {
      kind: 'remove',
      goalId,
      input: { confirmationId: proposal.id, skillExperienceId },
    }
  }

  function invalidateObjectiveQueries(goalId: string) {
    void queryClient.invalidateQueries({ queryKey: ['learning', 'goal-detail', goalId] })
    void queryClient.invalidateQueries({ queryKey: ['learning', 'home-goals'] })
  }

  async function handleConfirm() {
    if (isConfirming.current || isDeclining) return
    const request = lockedRequest.current ?? buildRequest()
    if (!request) return
    // The first confirmation locks the Objective; retry and verify resend the same data.
    lockedRequest.current = request
    isConfirming.current = true
    setPhase('processing')
    try {
      const outcome =
        request.kind === 'add'
          ? await confirmSkillAddition(request.goalId, request.input)
          : await confirmSkillRemoval(request.goalId, request.input)
      setLocalOutcome(outcome)
      setPhase('idle')
      if (outcome.outcome !== 'rejected') invalidateObjectiveQueries(outcome.goalId)
      mentor.onActionResolved(proposal.id)
    } catch (error) {
      const isSafeFailure =
        error instanceof RestError &&
        error.statusCode === HTTP_STATUS_CODE.serviceUnavailable
      setPhase(isSafeFailure ? 'failed' : 'uncertain')
    } finally {
      isConfirming.current = false
    }
  }

  async function handleDecline() {
    const sessionId = mentor.selectedSessionId
    if (!sessionId || isConfirming.current || isDeclining) return
    setDeclineError(null)
    try {
      await declineActionProposal(sessionId, proposal.id)
      setIsLocallyDeclined(true)
      mentor.onActionResolved(proposal.id)
    } catch (error) {
      if (error instanceof RestError && error.statusCode === HTTP_STATUS_CODE.conflict) {
        // An outcome already exists, so the conversation is re-read to show it.
        mentor.onActionResolved(proposal.id)
        return
      }
      setDeclineError(DECLINE_ERROR)
    }
  }

  function handleSelectGoal(goalId: string) {
    setSelectedGoalId(goalId)
    setIsChangingGoal(false)
  }

  function handleChangeGoal() {
    setIsChangingGoal(true)
  }

  const destination = goalTitle ? `Objetivo: ${goalTitle}` : undefined
  const resolvedGoalId =
    localOutcome?.goalId ?? proposal.resolvedGoalId ?? effectiveGoalId ?? null
  type CardView = Pick<
    MentorActionCardProps,
    | 'icon'
    | 'title'
    | 'isTitleVisible'
    | 'destination'
    | 'reason'
    | 'consequences'
    | 'result'
    | 'statusText'
  > & {
    actions: SkillActionCardAction[]
    picker: SkillActionCardPicker | null
    swap: { label: string; handleSelect: () => void } | null
  }

  function buildView(): CardView {
    const noActions: SkillActionCardAction[] = []
    const recuse: SkillActionCardAction = {
      key: 'decline',
      label: 'Recusar',
      variant: 'outline',
      disabled: isDeclining,
      handleSelect: () => void handleDecline(),
    }
    if (result?.kind === 'completed') {
      const destinationLink: SkillActionCardDestination | null = resolvedGoalId
        ? result.outcome === 'already_present'
          ? { kind: 'skill', goalId: resolvedGoalId, skillId: proposal.skillId }
          : { kind: 'goal', goalId: resolvedGoalId }
        : null
      const link: SkillActionCardAction[] = destinationLink
        ? [
            {
              key: 'view',
              label:
                result.outcome === 'already_present' ? 'Ver Habilidade' : 'Ver Objetivo',
              variant: 'outline',
              destination: destinationLink,
            },
          ]
        : noActions
      if (result.outcome === 'removed')
        return {
          icon: describeIcon(proposal.kind, false),
          title: `${skillName} removida`,
          result:
            'A experiência e seu histórico foram removidos. O Objetivo permanece disponível.',
          statusText: 'Remoção concluída',
          actions: link,
          picker: null,
          swap: null,
          destination,
        }
      if (result.outcome === 'already_present')
        return {
          icon: describeIcon(proposal.kind, false),
          title: `${skillName} já está no Objetivo`,
          result: 'Sua experiência existente foi mantida.',
          statusText: 'Nenhuma Habilidade duplicada.',
          actions: link,
          picker: null,
          swap: null,
          destination,
        }
      return {
        icon: describeIcon(proposal.kind, false),
        title: `${skillName} adicionada`,
        result:
          'A Habilidade começa como não iniciada. A justificativa pode ser consultada no Objetivo.',
        statusText: 'Adição concluída',
        actions: link,
        picker: null,
        swap: null,
        destination,
      }
    }
    if (result?.kind === 'rejected')
      return {
        icon: describeIcon(proposal.kind, false),
        title: isAddition
          ? `Não foi possível adicionar ${skillName}`
          : `Não foi possível remover ${skillName}`,
        result: result.reason ? REJECTION_REASON_TEXT[result.reason] : undefined,
        statusText: NO_CHANGE_STATUS,
        actions: noActions,
        picker: null,
        swap: null,
        destination,
      }
    if (result?.kind === 'declined')
      return {
        icon: describeIcon(proposal.kind, false),
        title: isAddition ? 'Adição recusada' : 'Remoção recusada',
        result: isAddition
          ? `${skillName} não foi adicionada ao Objetivo.`
          : `${skillName} permanece no Objetivo.`,
        statusText: NO_CHANGE_STATUS,
        actions: noActions,
        picker: null,
        swap: null,
        destination,
      }
    if (phase === 'processing')
      return {
        icon: describeIcon(proposal.kind, false),
        title: isAddition ? `Adicionando ${skillName}` : `Removendo ${skillName}`,
        result: PROCESSING_RESULT,
        statusText: isAddition ? 'Adicionando habilidade…' : 'Removendo habilidade…',
        actions: noActions,
        picker: null,
        swap: null,
        destination,
      }
    if (phase === 'uncertain')
      return {
        icon: describeIcon(proposal.kind, false),
        title: isAddition
          ? `Verificando adição de ${skillName}`
          : `Verificando remoção de ${skillName}`,
        result: UNCERTAIN_RESULT,
        statusText: 'Resultado ainda não confirmado',
        actions: [
          {
            key: 'verify',
            label: 'Verificar resultado',
            variant: 'primary',
            handleSelect: () => void handleConfirm(),
          },
        ],
        picker: null,
        swap: null,
        destination,
      }
    if (phase === 'failed')
      return {
        icon: describeIcon(proposal.kind, false),
        title: isAddition
          ? `Não foi possível adicionar ${skillName}`
          : `Não foi possível remover ${skillName}`,
        result: isAddition
          ? 'A adição não foi concluída. Sua proposta foi preservada.'
          : 'A remoção não foi concluída. Sua proposta foi preservada.',
        statusText: 'Tente novamente com a mesma confirmação.',
        actions: [
          recuse,
          {
            key: 'retry',
            label: 'Tentar novamente',
            variant: 'primary',
            handleSelect: () => void handleConfirm(),
          },
        ],
        picker: null,
        swap: null,
        destination,
      }
    const proposalTitle = isAddition ? `Adicionar ${skillName}?` : `Remover ${skillName}?`
    if (isPicking)
      return {
        icon: describeIcon(proposal.kind, true),
        title: proposalTitle,
        actions: [recuse],
        picker: {
          candidates: proposal.candidateGoals.map((candidate) => ({
            goalId: candidate.goalId,
            title: candidate.title,
            isDisabled: isAddition && candidate.containsSkill,
            isSelected: candidate.goalId === selectedGoalId,
          })),
          hint: isAddition
            ? 'Escolha um Objetivo para revisar a proposta de adição.'
            : 'Escolha um Objetivo para revisar a proposta de remoção.',
        },
        swap: null,
      }
    const confirm: SkillActionCardAction = isAddition
      ? {
          key: 'confirm',
          label: 'Adicionar habilidade',
          variant: 'primary',
          disabled: isDeclining,
          handleSelect: () => void handleConfirm(),
        }
      : {
          key: 'confirm',
          label: 'Remover habilidade',
          variant: 'danger',
          disabled: isDeclining,
          handleSelect: () => void handleConfirm(),
        }
    return {
      icon: describeIcon(proposal.kind, true),
      title: proposalTitle,
      destination,
      reason: isAddition
        ? (proposal.justification ?? DEFAULT_ADD_JUSTIFICATION)
        : REMOVAL_REASON,
      consequences: isAddition ? undefined : REMOVAL_CONSEQUENCES,
      result: declineError ?? undefined,
      actions: [recuse, confirm],
      picker: null,
      swap:
        isFixedDestination || lockedRequest.current
          ? null
          : { label: 'Trocar Objetivo', handleSelect: handleChangeGoal },
    }
  }

  const view = buildView()

  return { ...view, resultRef, titleRef, handleSelectGoal }
}
