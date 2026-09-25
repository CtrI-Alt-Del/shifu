import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'

import type { AvailableSkill } from '@/core/learning/goal-detail'
import { COMPETENCY_DETAIL_ID_PATTERN } from '@/core/learning/competency-detail'
import { CurriculumGapError } from '@/core/learning/curriculum-gap-error'
import { BetterAuthConfig } from '@/provision/auth/better-auth/better-auth-config'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { AxiosRestClient } from '@/rest/axios/axios-rest-client'
import { LearningService } from '@/rest/services/learning-service'

type ActionFailure = {
  kind: 'unauthorized' | 'invalid' | 'unavailable' | 'curriculum-gap'
}

export const getAvailableSkillsAction = createServerFn({ method: 'GET' }).handler(
  async (): Promise<AvailableSkill[] | ActionFailure> => {
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      return await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).getAvailableSkills(access.accessToken)
    } catch {
      return { kind: 'unavailable' }
    }
  },
)

export const createGoalAction = createServerFn({ method: 'POST' })
  .validator((input: { title: string; description: string; skillIds: string[] }) => input)
  .handler(async ({ data }): Promise<{ goalId: string } | ActionFailure> => {
    if (
      !data.title.trim() ||
      !data.description.trim() ||
      !data.skillIds.every((id) => COMPETENCY_DETAIL_ID_PATTERN.test(id))
    )
      return { kind: 'invalid' }
    try {
      const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
      if (!access) return { kind: 'unauthorized' }
      return await LearningService(
        AxiosRestClient(BetterAuthConfig().identityURL, { withCredentials: false }),
      ).createGoal(access.accessToken, data)
    } catch (error) {
      if (error instanceof CurriculumGapError) return { kind: 'curriculum-gap' }
      return { kind: 'unavailable' }
    }
  })

export function useGoalCreatePage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [selectedSkillIds, setSelectedSkillIds] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submissionError, setSubmissionError] = useState<string | null>(null)
  const skillsQuery = useQuery({
    queryKey: ['learning', 'available-skills'],
    queryFn: async () => {
      const result = await getAvailableSkillsAction()
      if ('kind' in result) throw result
      return result
    },
    retry: false,
  })

  function handleToggleSkill(skillId: string) {
    setSelectedSkillIds((current) =>
      current.includes(skillId)
        ? current.filter((id) => id !== skillId)
        : [...current, skillId],
    )
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!title.trim() || !description.trim() || isSubmitting) return
    setIsSubmitting(true)
    setSubmissionError(null)
    const result = await createGoalAction({
      data: {
        title: title.trim(),
        description: description.trim(),
        skillIds: selectedSkillIds,
      },
    })
    setIsSubmitting(false)
    if ('kind' in result) {
      setSubmissionError(
        result.kind === 'unauthorized'
          ? 'Sua sessão expirou. Entre novamente para criar o Objetivo.'
          : result.kind === 'curriculum-gap'
            ? 'Uma das Habilidades escolhidas ainda não tem cobertura suficiente no Currículo. Revise a seleção; seus dados continuam aqui.'
            : 'Não foi possível criar o Objetivo. Seus dados continuam aqui; tente novamente.',
      )
      return
    }
    await navigate({ to: '/learning/goals/$goalId', params: { goalId: result.goalId } })
  }

  return {
    title,
    description,
    selectedSkillIds,
    skills: skillsQuery.data ?? [],
    isLoadingSkills: skillsQuery.isPending,
    hasSkillsError: skillsQuery.isError,
    isSubmitting,
    submissionError,
    setTitle,
    setDescription,
    handleToggleSkill,
    handleRetrySkills: skillsQuery.refetch,
    handleSubmit,
  }
}
