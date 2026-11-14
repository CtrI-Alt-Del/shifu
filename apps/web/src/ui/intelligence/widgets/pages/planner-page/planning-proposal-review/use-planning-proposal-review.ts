import { useRef, useState } from 'react'

import type {
  PlanningGoalCreationRequest,
  PlanningProposal,
} from '@/core/intelligence/planning-session'

export type PlanningProposalReviewView = 'graph' | 'list'

export type GoalCreationStatus = 'idle' | 'creating' | 'failed' | 'uncertain'

export type GoalCreationState = {
  status: GoalCreationStatus
  /** Reason reported by the backend on a failure; the generic copy applies without it. */
  message: string | null
}

export const IDLE_GOAL_CREATION: GoalCreationState = { status: 'idle', message: null }

export type GoalCreationNotice = {
  tone: 'processing' | 'failure' | 'uncertain'
  title: string
  support: string
}

export type PlanningProposalReviewProps = {
  planningId: string
  intent: string
  proposal: PlanningProposal
  isCancelling: boolean
  isRestarting: boolean
  restartErrorMessage: string | null
  goalCreation: GoalCreationState
  onCancel: () => void
  onRestart: (initialIntent: string) => Promise<boolean>
  onCreateGoal: (request: PlanningGoalCreationRequest) => void
}

const TITLE_REQUIRED_MESSAGE = 'Informe um título para o Objetivo.'
const DESCRIPTION_REQUIRED_MESSAGE = 'Informe uma descrição para o Objetivo.'
const COUNT_WORDS = ['', 'uma', 'duas', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito']
const CREATE_GOAL_LABELS: Record<GoalCreationStatus, string> = {
  idle: 'Criar objetivo',
  creating: 'Criando objetivo…',
  failed: 'Tentar criar objetivo',
  uncertain: 'Verificar resultado',
}
const GOAL_CREATION_NOTICES: Record<
  Exclude<GoalCreationStatus, 'idle'>,
  GoalCreationNotice
> = {
  creating: {
    tone: 'processing',
    title: 'Criando seu objetivo…',
    support: 'Estamos salvando o objetivo e as habilidades que você confirmou.',
  },
  failed: {
    tone: 'failure',
    title: 'Não foi possível criar o objetivo',
    support: 'Sua proposta foi mantida. Tente criar o objetivo novamente.',
  },
  uncertain: {
    tone: 'uncertain',
    title: 'Não conseguimos confirmar a criação do objetivo',
    support:
      'A resposta não chegou. Verifique o resultado antes de tentar de novo: a mesma confirmação não cria outro objetivo.',
  },
}

export function usePlanningProposalReview(props: PlanningProposalReviewProps) {
  const { planningId, proposal, goalCreation, onCreateGoal, onRestart } = props
  const [view, setView] = useState<PlanningProposalReviewView>('graph')
  const [title, setTitle] = useState(proposal.title)
  const [description, setDescription] = useState(proposal.description)
  const [titleError, setTitleError] = useState<string | null>(null)
  const [descriptionError, setDescriptionError] = useState<string | null>(null)
  const [isRestartDialogOpen, setIsRestartDialogOpen] = useState(false)
  // One key per review: retries, double clicks and recoveries replay the same confirmation.
  const [confirmationKey] = useState(() => crypto.randomUUID())
  const titleRef = useRef<HTMLInputElement>(null)
  const descriptionRef = useRef<HTMLTextAreaElement>(null)
  const restartTriggerRef = useRef<HTMLButtonElement>(null)
  const isFrozen =
    goalCreation.status === 'creating' || goalCreation.status === 'uncertain'

  function handleViewChange(value: string) {
    if (value === 'graph' || value === 'list') setView(value)
  }

  function handleTitleChange(value: string) {
    setTitle(value)
    if (titleError && value.trim()) setTitleError(null)
  }

  function handleDescriptionChange(value: string) {
    setDescription(value)
    if (descriptionError && value.trim()) setDescriptionError(null)
  }

  function handleCreateGoal() {
    if (goalCreation.status === 'creating') return
    const trimmedTitle = title.trim()
    const trimmedDescription = description.trim()
    setTitleError(trimmedTitle ? null : TITLE_REQUIRED_MESSAGE)
    setDescriptionError(trimmedDescription ? null : DESCRIPTION_REQUIRED_MESSAGE)
    if (!trimmedTitle) {
      titleRef.current?.focus()
      return
    }
    if (!trimmedDescription) {
      descriptionRef.current?.focus()
      return
    }
    onCreateGoal({
      planningId,
      confirmationKey,
      title: trimmedTitle,
      description: trimmedDescription,
      proposal,
    })
  }

  function handleOpenRestart() {
    setIsRestartDialogOpen(true)
  }

  function handleCloseRestart() {
    setIsRestartDialogOpen(false)
  }

  async function handleSubmitRestart(initialIntent: string) {
    const restarted = await onRestart(initialIntent)
    if (restarted) setIsRestartDialogOpen(false)
  }

  return {
    view,
    title,
    description,
    titleError,
    descriptionError,
    relationSummary: relationSummaryFor(proposal.skills.length),
    isRestartDialogOpen,
    isFrozen,
    createGoalLabel: CREATE_GOAL_LABELS[goalCreation.status],
    goalCreationNotice: goalCreationNoticeFor(goalCreation),
    titleRef,
    descriptionRef,
    restartTriggerRef,
    handleViewChange,
    handleTitleChange,
    handleDescriptionChange,
    handleCreateGoal,
    handleOpenRestart,
    handleCloseRestart,
    handleSubmitRestart,
  }
}

export type PlanningProposalReviewController = ReturnType<
  typeof usePlanningProposalReview
>

function relationSummaryFor(skillCount: number): string {
  if (skillCount <= 1) {
    return 'Esta habilidade sustenta o objetivo. Você escolhe por onde começar.'
  }
  const count = COUNT_WORDS[skillCount] ?? String(skillCount)
  return `As ${count} habilidades se complementam. Você escolhe por onde começar.`
}

function goalCreationNoticeFor(state: GoalCreationState): GoalCreationNotice | null {
  if (state.status === 'idle') return null
  const notice = GOAL_CREATION_NOTICES[state.status]
  if (state.status === 'failed' && state.message) {
    return { ...notice, support: `${state.message} Sua proposta foi mantida.` }
  }
  return notice
}
