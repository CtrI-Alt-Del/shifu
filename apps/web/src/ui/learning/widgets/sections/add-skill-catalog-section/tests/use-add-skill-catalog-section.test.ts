import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { CatalogSkill } from '@/core/learning/catalog-skill'
import { useAddSkillToGoalAction } from '@/ui/learning/hooks/use-add-skill-to-goal-action'
import { useSkillCatalogQuery } from '@/ui/learning/hooks/use-skill-catalog-query'

import { useAddSkillCatalogSection } from '../use-add-skill-catalog-section'

vi.mock('@/ui/learning/hooks/use-skill-catalog-query', () => ({
  useSkillCatalogQuery: vi.fn(),
}))
vi.mock('@/ui/learning/hooks/use-add-skill-to-goal-action', () => ({
  useAddSkillToGoalAction: vi.fn(),
}))

const useSkillCatalogQueryMock = vi.mocked(useSkillCatalogQuery)
const useAddSkillToGoalActionMock = vi.mocked(useAddSkillToGoalAction)

const GOAL_ID = '01J00000000000000000000001'
const SKILL: CatalogSkill = {
  id: '01J00000000000000000000002',
  name: 'React',
  description: 'Criar interfaces',
  alreadyInGoal: false,
  skillExperienceId: null,
  foundations: [{ skillId: 'f1', name: 'JavaScript', status: 'missing' }],
}

const addSkillToGoalMock = vi.fn()
const resetAddSkillToGoalMock = vi.fn()
const loadMoreSkillsMock = vi.fn()
const retrySkillsMock = vi.fn()
const setSkillCatalogQueryMock = vi.fn()

function mockCatalog(overrides: Partial<ReturnType<typeof useSkillCatalogQuery>> = {}) {
  useSkillCatalogQueryMock.mockReturnValue({
    skills: [SKILL],
    skillsError: null,
    isLoadingSkills: false,
    isLoadingMoreSkills: false,
    hasMoreSkills: false,
    loadMoreSkills: loadMoreSkillsMock,
    retrySkills: retrySkillsMock,
    setSkillCatalogQuery: setSkillCatalogQueryMock,
    ...overrides,
  })
}

describe('useAddSkillCatalogSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCatalog()
    addSkillToGoalMock.mockResolvedValue([])
    useAddSkillToGoalActionMock.mockReturnValue({
      addSkillToGoalError: null,
      isAddingSkillToGoal: false,
      addSkillToGoal: addSkillToGoalMock,
      resetAddSkillToGoal: resetAddSkillToGoalMock,
    })
  })
  afterEach(cleanup)

  it('queries the catalog and prepares the add action for the Goal', () => {
    const { result } = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))

    expect(useSkillCatalogQueryMock).toHaveBeenCalledWith(GOAL_ID)
    expect(useAddSkillToGoalActionMock).toHaveBeenCalledWith(GOAL_ID)
    expect(result.current.skills).toEqual([SKILL])
    expect(result.current.selectedSkill).toBeNull()
    expect(result.current.dialogError).toBeNull()
    expect(result.current.catalogError).toBeNull()
    expect(result.current.isLoading).toBe(false)
    expect(result.current.hasMoreSkills).toBe(false)
  })

  it('reports loading for the first page and for further pages', () => {
    mockCatalog({ isLoadingSkills: true })
    const first = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))
    expect(first.result.current.isLoading).toBe(true)

    mockCatalog({ isLoadingMoreSkills: true, hasMoreSkills: true })
    const more = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))
    expect(more.result.current.isLoading).toBe(true)
    expect(more.result.current.hasMoreSkills).toBe(true)
  })

  it('exposes the catalog failure message and a generic one for a non-error rejection', () => {
    mockCatalog({ skillsError: new Error('Catálogo indisponível') })
    const failed = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))
    expect(failed.result.current.catalogError).toBe('Catálogo indisponível')

    mockCatalog({ skillsError: 'unexpected' as unknown as Error })
    const unknown = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))
    expect(unknown.result.current.catalogError).toBe(
      'Não foi possível carregar as Habilidades.',
    )
  })

  it('forwards the search text and the load more request to the catalog query', () => {
    const { result } = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))

    act(() => result.current.handleSearch('rea'))
    act(() => {
      void result.current.loadMoreSkills()
    })

    expect(setSkillCatalogQueryMock).toHaveBeenCalledWith('rea')
    expect(loadMoreSkillsMock).toHaveBeenCalledOnce()
  })

  it('exposes the catalog retry action', () => {
    const { result } = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))

    act(() => {
      void result.current.retrySkills()
    })

    expect(retrySkillsMock).toHaveBeenCalledOnce()
  })

  it('selects a Skill and clears an earlier dialog error', async () => {
    addSkillToGoalMock.mockRejectedValueOnce(new Error('Falhou'))
    const { result } = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))

    act(() => result.current.handleSkillSelect(SKILL))
    await act(async () => {
      await result.current.handleDialogSubmit([]).catch(() => undefined)
    })
    expect(result.current.dialogError).toBe('Falhou')

    act(() => result.current.handleSkillSelect(SKILL))
    expect(result.current.selectedSkill).toEqual(SKILL)
    expect(result.current.dialogError).toBeNull()
  })

  it('adds the selected Skill with the chosen foundations', async () => {
    const { result } = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))

    act(() => result.current.handleSkillSelect(SKILL))
    await act(() => result.current.handleDialogSubmit(['f1']))

    expect(addSkillToGoalMock).toHaveBeenCalledWith({
      skillId: SKILL.id,
      foundationSkillIds: ['f1'],
    })
    expect(result.current.dialogError).toBeNull()
  })

  it('does nothing when no Skill is selected', async () => {
    const { result } = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))

    await act(() => result.current.handleDialogSubmit(['f1']))

    expect(addSkillToGoalMock).not.toHaveBeenCalled()
  })

  it('keeps the Skill selected, shows the failure and rethrows it', async () => {
    addSkillToGoalMock.mockRejectedValueOnce(new Error('Não foi possível adicionar'))
    const { result } = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))

    act(() => result.current.handleSkillSelect(SKILL))
    let rejection: unknown = null
    await act(async () => {
      rejection = await result.current.handleDialogSubmit([]).catch((error) => error)
    })

    expect(rejection).toEqual(new Error('Não foi possível adicionar'))
    expect(result.current.dialogError).toBe('Não foi possível adicionar')
    expect(result.current.selectedSkill).toEqual(SKILL)
  })

  it('uses a default message for a rejection that is not an Error', async () => {
    addSkillToGoalMock.mockRejectedValueOnce('boom')
    const { result } = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))

    act(() => result.current.handleSkillSelect(SKILL))
    await act(async () => {
      await result.current.handleDialogSubmit([]).catch(() => undefined)
    })

    expect(result.current.dialogError).toBe('Erro ao adicionar habilidade')
  })

  it('closes the dialog, clears its error and resets the add action', async () => {
    addSkillToGoalMock.mockRejectedValueOnce(new Error('Falhou'))
    const { result } = renderHook(() => useAddSkillCatalogSection({ goalId: GOAL_ID }))

    act(() => result.current.handleSkillSelect(SKILL))
    await act(async () => {
      await result.current.handleDialogSubmit([]).catch(() => undefined)
    })
    act(() => result.current.handleDialogClose())

    expect(result.current.selectedSkill).toBeNull()
    expect(result.current.dialogError).toBeNull()
    expect(resetAddSkillToGoalMock).toHaveBeenCalledOnce()
  })
})
