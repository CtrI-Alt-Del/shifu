import { useRef, useState } from 'react'

import type {
  PlanningGoalCreationRequest,
  PlanningProposal,
} from '@/core/intelligence/planning-session'

export type PlanningProposalReviewView = 'graph' | 'list'

export type PlanningProposalReviewProps = {
  planningId: string
  intent: string
  proposal: PlanningProposal
  isCancelling: boolean
  isRestarting: boolean
  restartErrorMessage: string | null
  goalCreationNotice: string | null
  onCancel: () => void
  onRestart: (initialIntent: string) => Promise<boolean>
  onCreateGoal: (request: PlanningGoalCreationRequest) => void
}

const TITLE_REQUIRED_MESSAGE = 'Informe um título para o Objetivo.'
const DESCRIPTION_REQUIRED_MESSAGE = 'Informe uma descrição para o Objetivo.'
const COUNT_WORDS = ['', 'uma', 'duas', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito']

export function usePlanningProposalReview(props: PlanningProposalReviewProps) {
  const { planningId, proposal, onCreateGoal, onRestart } = props
  const [view, setView] = useState<PlanningProposalReviewView>('graph')
  const [title, setTitle] = useState(proposal.title)
  const [description, setDescription] = useState(proposal.description)
  const [titleError, setTitleError] = useState<string | null>(null)
  const [descriptionError, setDescriptionError] = useState<string | null>(null)
  const [isRestartDialogOpen, setIsRestartDialogOpen] = useState(false)
  const titleRef = useRef<HTMLInputElement>(null)
  const descriptionRef = useRef<HTMLTextAreaElement>(null)
  const restartTriggerRef = useRef<HTMLButtonElement>(null)

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
