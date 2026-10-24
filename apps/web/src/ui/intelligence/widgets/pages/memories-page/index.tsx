import { ConfirmationDialog } from '@/ui/shared/widgets/components/confirmation-dialog'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { MemoriesFeedback } from './memories-feedback'
import { MemoryDetails } from './memory-details'
import { MemoryEditForm } from './memory-edit-form'
import { MemoryFilters } from './memory-filters'
import { MemoryList } from './memory-list'
import { MemoryMap } from './memory-map'
import { MemoryRemovedNotice } from './memory-removed-notice'
import { useMemoriesPage } from './use-memories-page'

export const MemoriesPage = () => {
  const {
    memories,
    selectedMemory,
    query,
    category,
    view,
    totalCount,
    listStatus,
    sidePanelStatus,
    saveError,
    conflictContent,
    isSaving,
    isDeleteDialogOpen,
    isDeleting,
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
  } = useMemoriesPage()
  const selectedMemoryId = selectedMemory?.id ?? null

  return (
    <div className='mx-auto w-full max-w-7xl space-y-6'>
      <header className='space-y-2'>
        <Anchor
          className='inline-flex min-h-11 items-center gap-2 text-sm text-muted-foreground hover:text-foreground'
          route='intelligence'
        >
          <Icon name='arrow-left' className='size-4' />
          Voltar ao Mentor
        </Anchor>
        <h1 className='font-serif text-3xl font-normal'>Memórias</h1>
        <p className='text-muted-foreground'>
          O que o Mentor lembra para adaptar as explicações a você.
        </p>
      </header>
      <MemoryFilters
        category={category}
        onCategoryChange={handleCategoryChange}
        onQueryChange={handleQueryChange}
        onViewChange={handleViewChange}
        query={query}
        totalCount={totalCount}
        view={view}
      />
      <div className='grid gap-5 lg:grid-cols-[minmax(0,1fr)_26.5rem] lg:items-start'>
        <div className='min-w-0'>
          {listStatus !== 'ready' ? (
            <MemoriesFeedback
              onClearFilters={handleClearFilters}
              onRetry={handleRetry}
              status={listStatus}
            />
          ) : view === 'map' ? (
            <MemoryMap
              memories={memories}
              onSelectMemory={handleSelectMemory}
              selectedMemoryId={selectedMemoryId}
            />
          ) : (
            <MemoryList
              memories={memories}
              onSelectMemory={handleSelectMemory}
              selectedMemoryId={selectedMemoryId}
            />
          )}
        </div>
        {sidePanelStatus === 'none' ? null : (
          <aside aria-label='Painel da memória' className='min-w-0'>
            {sidePanelStatus === 'details' && selectedMemory ? (
              <MemoryDetails
                memory={selectedMemory}
                onClose={handleCloseDetails}
                onDelete={handleRequestDelete}
                onEdit={handleStartEdit}
              />
            ) : sidePanelStatus === 'edit' && selectedMemory ? (
              <MemoryEditForm
                conflictContent={conflictContent}
                isSaving={isSaving}
                key={selectedMemory.id}
                memory={selectedMemory}
                onCancel={handleCancelEdit}
                onSave={(content) => void handleSaveEdit(content)}
                saveError={saveError}
              />
            ) : sidePanelStatus === 'removed' ? (
              <MemoryRemovedNotice />
            ) : (
              <MemoriesFeedback
                onClearFilters={handleClearFilters}
                onRetry={handleRetry}
                status={
                  sidePanelStatus === 'not-found'
                    ? 'not-found'
                    : sidePanelStatus === 'error'
                      ? 'error'
                      : 'loading'
                }
              />
            )}
          </aside>
        )}
      </div>
      <ConfirmationDialog
        actionClassName='min-h-9! px-3! text-sm'
        cancelLabel='Manter memória'
        confirmLabel='Excluir memória'
        description='O Mentor deixará de usar esta memória. Mensagens, anexos e resumos antigos não vão recriá-la automaticamente.'
        error={deleteError}
        icon='trash-2'
        isOpen={isDeleteDialogOpen}
        isSubmitting={isDeleting}
        itemName={selectedMemory?.content}
        onCancel={handleCancelDelete}
        onConfirm={() => void handleConfirmDelete()}
        title='Excluir esta memória?'
      />
    </div>
  )
}
