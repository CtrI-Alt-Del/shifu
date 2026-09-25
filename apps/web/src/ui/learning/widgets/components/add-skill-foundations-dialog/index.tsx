import { type ReactNode, useState } from 'react'

import type { SuggestedFoundation } from '@/core/learning/suggested-foundation'

import { SkillFoundationRow } from '../skill-foundation-row'

type AddSkillFoundationsDialogProps = {
  skillName: string
  foundations: readonly SuggestedFoundation[]
  isOpen: boolean
  isLoading?: boolean
  error?: string | null
  onClose: () => void
  onSubmit: (selectedFoundationIds: readonly string[]) => Promise<void>
}

export function AddSkillFoundationsDialog({
  skillName,
  foundations,
  isOpen,
  isLoading = false,
  error = null,
  onClose,
  onSubmit,
}: AddSkillFoundationsDialogProps): ReactNode {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleToggle = (skillId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(skillId)) {
        next.delete(skillId)
      } else {
        next.add(skillId)
      }
      return next
    })
  }

  const handleSubmit = async () => {
    setIsSubmitting(true)
    try {
      await onSubmit(Array.from(selectedIds))
      setSelectedIds(new Set())
      onClose()
    } catch (_err) {
      // Error is handled by parent via error prop
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen) {
    return null
  }

  const missingFoundations = foundations.filter((f) => f.status === 'missing')
  const presentFoundations = foundations.filter((f) => f.status === 'present')

  return (
    <div className='fixed inset-0 bg-black/50 flex items-center justify-center z-50'>
      <div className='bg-white rounded-lg shadow-lg max-w-lg w-full mx-4'>
        <div className='border-b p-6'>
          <h2 className='text-xl font-semibold'>Adicionar: {skillName}</h2>
          <p className='text-sm text-gray-600 mt-2'>
            Selecione as bases que deseja adicionar
          </p>
        </div>

        <div className='p-6 max-h-96 overflow-y-auto'>
          {isLoading ? (
            <div className='text-center py-8'>
              <div className='inline-block animate-spin'>⚙️</div>
              <p className='text-gray-600 mt-2'>Carregando...</p>
            </div>
          ) : error ? (
            <div className='p-4 bg-red-50 border border-red-200 rounded text-red-800'>
              {error}
            </div>
          ) : foundations.length === 0 ? (
            <div className='text-center py-8 text-gray-600'>
              <p>Nenhuma base sugerida para esta habilidade</p>
            </div>
          ) : (
            <>
              {missingFoundations.length > 0 && (
                <div className='mb-6'>
                  <h3 className='font-semibold text-sm mb-3 text-gray-700'>
                    Bases ausentes ({missingFoundations.length})
                  </h3>
                  <div className='space-y-2'>
                    {missingFoundations.map((foundation) => (
                      <SkillFoundationRow
                        key={foundation.skillId}
                        skillId={foundation.skillId}
                        name={foundation.name}
                        status='missing'
                        isSelectable={true}
                        isSelected={selectedIds.has(foundation.skillId)}
                        onToggle={handleToggle}
                      />
                    ))}
                  </div>
                </div>
              )}

              {presentFoundations.length > 0 && (
                <div>
                  <h3 className='font-semibold text-sm mb-3 text-gray-700'>
                    Bases já presentes ({presentFoundations.length})
                  </h3>
                  <div className='space-y-2'>
                    {presentFoundations.map((foundation) => (
                      <SkillFoundationRow
                        key={foundation.skillId}
                        skillId={foundation.skillId}
                        name={foundation.name}
                        status='present'
                        isSelectable={false}
                      />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className='border-t p-6 flex justify-end gap-3'>
          <button
            type='button'
            onClick={onClose}
            disabled={isSubmitting}
            className='px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50'
          >
            Cancelar
          </button>
          <button
            type='button'
            onClick={handleSubmit}
            disabled={isSubmitting || selectedIds.size === 0}
            className='px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50'
          >
            {isSubmitting ? 'Adicionando...' : 'Adicionar'}
          </button>
        </div>
      </div>
    </div>
  )
}
