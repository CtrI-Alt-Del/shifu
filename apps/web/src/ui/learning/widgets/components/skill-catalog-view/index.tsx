import { type ReactNode, useState } from 'react'

import type { CatalogSkill } from '@/core/learning/catalog-skill'

import { SkillFoundationRow } from '../skill-foundation-row'

type SkillCatalogViewProps = {
  skills: readonly CatalogSkill[]
  isLoading?: boolean
  error?: string | null
  onSkillSelect: (skill: CatalogSkill) => void
  onLoadMore?: () => void
  hasMore?: boolean
}

export function SkillCatalogView({
  skills,
  isLoading = false,
  error = null,
  onSkillSelect,
  onLoadMore,
  hasMore = false,
}: SkillCatalogViewProps): ReactNode {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const toggleExpand = (skillId: string) => {
    setExpandedId(expandedId === skillId ? null : skillId)
  }

  return (
    <div className='w-full'>
      {error && (
        <div className='mb-4 rounded border border-red-200 bg-red-50 p-4 text-red-800'>
          {error}
        </div>
      )}

      {isLoading && skills.length === 0 ? (
        <div className='py-8 text-center'>
          <div className='inline-block animate-spin'>⚙️</div>
          <p className='mt-2 text-gray-600'>Carregando habilidades...</p>
        </div>
      ) : skills.length === 0 ? (
        <div className='py-8 text-center text-gray-600'>
          <p>Nenhuma habilidade encontrada</p>
        </div>
      ) : (
        <div className='space-y-3'>
          {skills.map((skill) => (
            <div key={skill.id} className='rounded-lg border p-4 hover:bg-gray-50'>
              <div className='flex items-start justify-between'>
                <div className='flex-1'>
                  <h3 className='text-lg font-semibold'>{skill.name}</h3>
                  <p className='text-sm text-gray-600'>{skill.description}</p>
                </div>
                {skill.alreadyInGoal ? (
                  <span className='ml-4 whitespace-nowrap rounded bg-gray-200 px-4 py-2 text-gray-600'>
                    Adicionado
                  </span>
                ) : (
                  <button
                    type='button'
                    onClick={() => onSkillSelect(skill)}
                    className='ml-4 whitespace-nowrap rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700'
                  >
                    Adicionar
                  </button>
                )}
              </div>

              {skill.foundations.length > 0 && (
                <div className='mt-3 border-t pt-3'>
                  {skill.foundations.length === 1 ? (
                    <div className='mt-2'>
                      <p className='mb-2 text-sm text-gray-600'>Base sugerida:</p>
                      <SkillFoundationRow
                        skillId={skill.foundations[0].skillId}
                        name={skill.foundations[0].name}
                        status={skill.foundations[0].status}
                        isSelectable={false}
                      />
                    </div>
                  ) : (
                    <div>
                      <button
                        type='button'
                        onClick={() => toggleExpand(skill.id)}
                        className='text-sm text-blue-600 hover:underline'
                      >
                        {expandedId === skill.id
                          ? 'Ocultar bases'
                          : `Ver bases (${skill.foundations.length})`}
                      </button>
                      {expandedId === skill.id && (
                        <div className='mt-3 space-y-2'>
                          {skill.foundations.map((foundation) => (
                            <SkillFoundationRow
                              key={foundation.skillId}
                              skillId={foundation.skillId}
                              name={foundation.name}
                              status={foundation.status}
                              isSelectable={false}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {hasMore && onLoadMore && (
            <button
              type='button'
              onClick={onLoadMore}
              disabled={isLoading}
              className='w-full rounded border py-3 hover:bg-gray-50 disabled:opacity-50'
            >
              {isLoading ? 'Carregando...' : 'Carregar mais'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
