import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SkillExperienceReference } from '@/core/learning/skill-experience-reference'
import type { SuggestedFoundation } from '@/core/learning/suggested-foundation'
import { useSkillExperiencesOfSkillQuery } from '@/ui/learning/hooks/use-skill-experiences-of-skill-query'

import { useAddSkillFoundationsDialog } from '../use-add-skill-foundations-dialog'

vi.mock('@/ui/learning/hooks/use-skill-experiences-of-skill-query', () => ({
  useSkillExperiencesOfSkillQuery: vi.fn(),
}))

const useSkillExperiencesOfSkillQueryMock = vi.mocked(useSkillExperiencesOfSkillQuery)

const GOAL_ID = '01J00000000000000000000001'
const OTHER_GOAL_ID = '01J00000000000000000000004'
const SECOND_OTHER_GOAL_ID = '01J00000000000000000000005'
const SKILL_ID = '01J00000000000000000000002'

const FOUNDATIONS: SuggestedFoundation[] = [
  { skillId: 'f1', name: 'HTML Basics', status: 'missing' },
  { skillId: 'f2', name: 'CSS Basics', status: 'missing' },
  { skillId: 'f3', name: 'JavaScript', status: 'present' },
]

function createExperience(
  overrides: Partial<SkillExperienceReference> = {},
): SkillExperienceReference {
  return {
    goalId: OTHER_GOAL_ID,
    goalTitle: 'Carreira em dados',
    skillExperienceId: '01J00000000000000000000006',
    skillId: SKILL_ID,
    status: 'completed',
    ...overrides,
  }
}

function mockLookup(experiences: SkillExperienceReference[]) {
  useSkillExperiencesOfSkillQueryMock.mockReturnValue({
    skillExperiencesOfSkill: experiences,
    skillExperiencesOfSkillError: null,
    isLoadingSkillExperiencesOfSkill: false,
  })
}

function setup(
  overrides: Partial<Parameters<typeof useAddSkillFoundationsDialog>[0]> = {},
) {
  const onClose = vi.fn()
  const onSubmit = vi.fn().mockResolvedValue(undefined)
  const rendered = renderHook(() =>
    useAddSkillFoundationsDialog({
      goalId: GOAL_ID,
      skillId: SKILL_ID,
      foundations: FOUNDATIONS,
      onClose,
      onSubmit,
      ...overrides,
    }),
  )
  return { ...rendered, onClose, onSubmit }
}

describe('useAddSkillFoundationsDialog', () => {
  beforeEach(() => {
    mockLookup([])
  })
  afterEach(cleanup)

  it('looks up the experiences of the selected Skill', () => {
    setup()

    expect(useSkillExperiencesOfSkillQueryMock).toHaveBeenCalledWith(SKILL_ID)
  })

  it('returns only the experiences that belong to other Goals', () => {
    mockLookup([
      createExperience({ goalId: GOAL_ID, goalTitle: 'Este Objetivo' }),
      createExperience({ skillExperienceId: 'exp-a' }),
      createExperience({
        goalId: SECOND_OTHER_GOAL_ID,
        goalTitle: 'Dados na prática',
        skillExperienceId: 'exp-b',
        status: 'learning',
      }),
    ])
    const { result } = setup()

    expect(result.current.otherGoalExperiences.map(({ goalTitle }) => goalTitle)).toEqual(
      ['Carreira em dados', 'Dados na prática'],
    )
  })

  it('returns no experiences when the Skill exists only in the destination Goal', () => {
    mockLookup([createExperience({ goalId: GOAL_ID })])
    const { result } = setup()

    expect(result.current.otherGoalExperiences).toEqual([])
  })

  it('returns no experiences while the lookup is loading or after it failed', () => {
    useSkillExperiencesOfSkillQueryMock.mockReturnValue({
      skillExperiencesOfSkill: [],
      skillExperiencesOfSkillError: new Error('lookup failed'),
      isLoadingSkillExperiencesOfSkill: false,
    })
    const { result } = setup()

    expect(result.current.otherGoalExperiences).toEqual([])
  })

  it('groups the foundations by status and describes the selection', () => {
    const { result } = setup()

    expect(result.current.hasFoundations).toBe(true)
    expect(result.current.missingFoundations.map(({ skillId }) => skillId)).toEqual([
      'f1',
      'f2',
    ])
    expect(result.current.presentFoundations.map(({ skillId }) => skillId)).toEqual([
      'f3',
    ])
    expect(result.current.description).toBe('Selecione as bases que deseja adicionar')
    expect(result.current.note).toBe('A Habilidade será adicionada como não iniciada.')
  })

  it('describes a Skill without suggested foundations', () => {
    const { result } = setup({ foundations: [] })

    expect(result.current.hasFoundations).toBe(false)
    expect(result.current.description).toBe(
      'Esta Habilidade não possui bases sugeridas no Currículo.',
    )
  })

  it('toggles the selection of a foundation and updates the note', () => {
    const { result } = setup()

    act(() => result.current.handleToggle('f1'))
    expect(result.current.isFoundationSelected('f1')).toBe(true)
    expect(result.current.isFoundationSelected('f2')).toBe(false)
    expect(result.current.note).toBe(
      'A Habilidade e as bases selecionadas serão adicionadas como não iniciadas.',
    )

    act(() => result.current.handleToggle('f1'))
    expect(result.current.isFoundationSelected('f1')).toBe(false)
    expect(result.current.note).toBe('A Habilidade será adicionada como não iniciada.')
  })

  it('submits the selected foundations, resets the selection and closes', async () => {
    const { result, onSubmit, onClose } = setup()

    act(() => result.current.handleToggle('f1'))
    act(() => result.current.handleToggle('f2'))
    await act(() => result.current.handleSubmit())

    expect(onSubmit).toHaveBeenCalledWith(['f1', 'f2'])
    expect(onClose).toHaveBeenCalledOnce()
    expect(result.current.isFoundationSelected('f1')).toBe(false)
    expect(result.current.isSubmitting).toBe(false)
  })

  it('submits without foundations when none is selected', async () => {
    const { result, onSubmit, onClose } = setup({ foundations: [] })

    await act(() => result.current.handleSubmit())

    expect(onSubmit).toHaveBeenCalledWith([])
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('submits even when the experiences lookup has not answered', async () => {
    useSkillExperiencesOfSkillQueryMock.mockReturnValue({
      skillExperiencesOfSkill: [],
      skillExperiencesOfSkillError: null,
      isLoadingSkillExperiencesOfSkill: true,
    })
    const { result, onSubmit } = setup()

    await act(() => result.current.handleSubmit())

    expect(onSubmit).toHaveBeenCalledOnce()
  })

  it('keeps the dialog open and the selection when the submission fails', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('rejected'))
    const { result, onClose } = setup({ onSubmit })

    act(() => result.current.handleToggle('f1'))
    await act(() => result.current.handleSubmit())

    expect(onClose).not.toHaveBeenCalled()
    expect(result.current.isFoundationSelected('f1')).toBe(true)
    expect(result.current.isSubmitting).toBe(false)
  })

  it('flags the pending submission and ignores a second submit', async () => {
    let resolveSubmit: () => void = () => undefined
    const onSubmit = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveSubmit = resolve
        }),
    )
    const { result, onClose } = setup({ onSubmit })

    let firstSubmit: Promise<void> = Promise.resolve()
    act(() => {
      firstSubmit = result.current.handleSubmit()
    })
    expect(result.current.isSubmitting).toBe(true)

    await act(() => result.current.handleSubmit())
    expect(onSubmit).toHaveBeenCalledOnce()

    await act(async () => {
      resolveSubmit()
      await firstSubmit
    })
    expect(result.current.isSubmitting).toBe(false)
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('returns focus to the element that was focused when the dialog mounted', () => {
    const opener = document.createElement('button')
    document.body.append(opener)
    opener.focus()
    const { result } = setup()
    document.body.focus()
    const event = new Event('focusout', { cancelable: true })

    act(() => result.current.handleCloseAutoFocus(event))

    expect(event.defaultPrevented).toBe(true)
    expect(opener).toHaveFocus()
    opener.remove()
  })

  it('does not fail when the opening element is gone', () => {
    const opener = document.createElement('button')
    document.body.append(opener)
    opener.focus()
    const { result } = setup()
    opener.remove()
    const event = new Event('focusout', { cancelable: true })

    act(() => result.current.handleCloseAutoFocus(event))

    expect(event.defaultPrevented).toBe(true)
    expect(document.body).toHaveFocus()
  })

  it('closes when the dialog asks to close', () => {
    const { result, onClose } = setup()

    act(() => result.current.handleOpenChange(true))
    expect(onClose).not.toHaveBeenCalled()

    act(() => result.current.handleOpenChange(false))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('does not close while a submission is pending', () => {
    const onSubmit = vi.fn(() => new Promise<void>(() => undefined))
    const { result, onClose } = setup({ onSubmit })

    act(() => {
      void result.current.handleSubmit()
    })
    act(() => result.current.handleOpenChange(false))

    expect(onClose).not.toHaveBeenCalled()
  })
})
