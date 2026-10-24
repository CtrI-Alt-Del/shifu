import { useNavigate, useRouteContext, useSearch } from '@tanstack/react-router'
import { useState } from 'react'

import { ROUTES } from '@/constants/routes'
import type { LearnerMemoryCategory } from '@/core/intelligence/learner-memory'

import { useEditLearnerMemoryAction } from './use-edit-learner-memory-action'
import { useLearnerMemoriesQuery } from './use-learner-memories-query'
import { useLearnerMemoryQuery } from './use-learner-memory-query'
import { useRemoveLearnerMemoryAction } from './use-remove-learner-memory-action'

type MemoriesSearchPatch = {
  q?: string
  category?: LearnerMemoryCategory
  view?: 'list' | 'map'
  memory?: string
}

export type MemoriesListStatus =
  | 'loading'
  | 'error'
  | 'empty'
  | 'empty-filtered'
  | 'ready'
export type MemoriesSidePanelStatus =
  | 'none'
  | 'loading'
  | 'error'
  | 'not-found'
  | 'details'
  | 'edit'
  | 'removed'

export function useMemoriesPage() {
  const navigate = useNavigate()
  const { email } = useRouteContext({ from: '/intelligence/memories/' })
  const {
    q,
    category,
    view,
    memory: selectedMemoryId,
  } = useSearch({
    from: '/intelligence/memories/',
  })
  const { memories, memoriesError, isLoadingMemories, refetchMemories } =
    useLearnerMemoriesQuery(email, { q, category })
  const listedMemory = memories.find((memory) => memory.id === selectedMemoryId)
  const { fetchedMemory, isMemoryNotFound, isLoadingMemory, memoryError, refetchMemory } =
    useLearnerMemoryQuery(
      email,
      selectedMemoryId ?? null,
      !isLoadingMemories && !memoriesError && !listedMemory,
    )
  const { isEditingLearnerMemory, editLearnerMemory } = useEditLearnerMemoryAction(email)
  const { isRemovingLearnerMemory, removeLearnerMemory } =
    useRemoveLearnerMemoryAction(email)
  const [editingMemoryId, setEditingMemoryId] = useState<string | null>(null)
  const [editError, setEditError] = useState<string | null>(null)
  const [hasEditConflict, setHasEditConflict] = useState(false)
  const [deletingMemoryId, setDeletingMemoryId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [isRemovedNoticeVisible, setIsRemovedNoticeVisible] = useState(false)

  const selectedMemory = listedMemory ?? fetchedMemory
  const hasActiveFilters = Boolean(q) || Boolean(category)
  const isEditing = Boolean(selectedMemory) && editingMemoryId === selectedMemory?.id
  const isDeleteDialogOpen =
    Boolean(selectedMemory) && deletingMemoryId === selectedMemory?.id
  const conflictContent = isEditing && hasEditConflict ? selectedMemory?.content : null
  const totalCount =
    category || isLoadingMemories || memoriesError ? null : memories.length
  const listStatus: MemoriesListStatus = memoriesError
    ? 'error'
    : isLoadingMemories
      ? 'loading'
      : memories.length > 0
        ? 'ready'
        : hasActiveFilters
          ? 'empty-filtered'
          : 'empty'
  const sidePanelStatus: MemoriesSidePanelStatus = selectedMemory
    ? isEditing
      ? 'edit'
      : 'details'
    : isRemovedNoticeVisible && !selectedMemoryId
      ? 'removed'
      : !selectedMemoryId
        ? 'none'
        : isMemoryNotFound
          ? 'not-found'
          : memoryError
            ? 'error'
            : 'loading'

  function updateSearch(patch: MemoriesSearchPatch) {
    void navigate({
      to: ROUTES.intelligenceMemories,
      search: { q, category, view, memory: selectedMemoryId, ...patch },
      replace: true,
    })
  }

  function resetEditing() {
    setEditingMemoryId(null)
    setEditError(null)
    setHasEditConflict(false)
  }

  function handleQueryChange(query: string) {
    updateSearch({ q: query || undefined })
  }

  function handleCategoryChange(nextCategory: LearnerMemoryCategory | null) {
    updateSearch({ category: nextCategory ?? undefined })
  }

  function handleViewChange(nextView: 'list' | 'map') {
    updateSearch({ view: nextView })
  }

  function handleClearFilters() {
    updateSearch({ q: undefined, category: undefined })
  }

  function handleSelectMemory(memoryId: string) {
    resetEditing()
    setDeletingMemoryId(null)
    setIsRemovedNoticeVisible(false)
    updateSearch({ memory: memoryId })
  }

  function handleCloseDetails() {
    resetEditing()
    setDeletingMemoryId(null)
    updateSearch({ memory: undefined })
  }

  function handleRetry() {
    void refetchMemories()
    if (selectedMemoryId && !listedMemory) void refetchMemory()
  }

  function handleStartEdit() {
    if (!selectedMemory) return
    resetEditing()
    setEditingMemoryId(selectedMemory.id)
  }

  function handleCancelEdit() {
    if (isEditingLearnerMemory) return
    resetEditing()
  }

  async function handleSaveEdit(content: string) {
    if (!selectedMemory || isEditingLearnerMemory) return
    setEditError(null)
    try {
      const result = await editLearnerMemory({
        memoryId: selectedMemory.id,
        content,
        expectedVersion: selectedMemory.version,
      })
      if (result.kind === 'ok') {
        resetEditing()
      } else if (result.kind === 'conflict') {
        setHasEditConflict(true)
      } else if (result.kind === 'invalid') {
        setHasEditConflict(false)
        setEditError('O conteúdo da memória deve ter entre 1 e 280 caracteres.')
      } else {
        resetEditing()
        setIsRemovedNoticeVisible(true)
        updateSearch({ memory: undefined })
      }
    } catch {
      setEditError('Não foi possível salvar a memória. Tente novamente.')
    }
  }

  function handleRequestDelete() {
    if (!selectedMemory) return
    setDeleteError(null)
    setDeletingMemoryId(selectedMemory.id)
  }

  function handleCancelDelete() {
    if (isRemovingLearnerMemory) return
    setDeletingMemoryId(null)
    setDeleteError(null)
  }

  async function handleConfirmDelete() {
    if (!deletingMemoryId || isRemovingLearnerMemory) return
    setDeleteError(null)
    try {
      await removeLearnerMemory(deletingMemoryId)
      setDeletingMemoryId(null)
      resetEditing()
      setIsRemovedNoticeVisible(true)
      updateSearch({ memory: undefined })
    } catch {
      setDeleteError('Não foi possível excluir a memória. Tente novamente.')
    }
  }

  return {
    memories,
    selectedMemory,
    query: q ?? '',
    category: category ?? null,
    view,
    totalCount,
    listStatus,
    sidePanelStatus,
    isLoadingSelectedMemory: isLoadingMemory,
    isSaving: isEditingLearnerMemory,
    saveError: editError,
    conflictContent: conflictContent ?? null,
    isDeleteDialogOpen,
    isDeleting: isRemovingLearnerMemory,
    deleteError,
    handleQueryChange,
    handleCategoryChange,
    handleViewChange,
    handleClearFilters,
    handleSelectMemory,
    handleCloseDetails,
    handleRetry,
    handleStartEdit,
    handleCancelEdit,
    handleSaveEdit,
    handleRequestDelete,
    handleCancelDelete,
    handleConfirmDelete,
  }
}
