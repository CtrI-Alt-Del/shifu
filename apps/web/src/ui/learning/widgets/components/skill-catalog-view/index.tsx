import { type ReactNode, useState } from 'react'
import { SkillFoundationRow } from '../skill-foundation-row'

interface CatalogFoundation {
  skillId: string
  name: string
  status: 'present' | 'missing'
}

interface CatalogSkillItem {
  id: string
  name: string
  description: string
  already_in_goal: boolean
  skill_experience_id: string | null
  foundations: CatalogFoundation[]
}

interface SkillCatalogViewProps {
  skills: CatalogSkillItem[]
  isLoading?: boolean
  error?: string | null
  onSkillSelect: (skill: CatalogSkillItem) => void
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
        <div className='p-4 bg-red-50 border border-red-200 rounded text-red-800 mb-4'>
          {error}
        </div>
      )}

      {isLoading && skills.length === 0 ? (
        <div className='text-center py-8'>
          <div className='inline-block animate-spin'>⚙️</div>
          <p className='text-gray-600 mt-2'>Carregando habilidades...</p>
        </div>
      ) : skills.length === 0 ? (
        <div className='text-center py-8 text-gray-600'>
          <p>Nenhuma habilidade encontrada</p>
        </div>
      ) : (
        <div className='space-y-3'>
          {skills.map((skill) => (
            <div key={skill.id} className='border rounded-lg p-4 hover:bg-gray-50'>
              <div className='flex items-start justify-between'>
                <div className='flex-1'>
                  <h3 className='font-semibold text-lg'>{skill.name}</h3>
                  <p className='text-gray-600 text-sm'>{skill.description}</p>
                </div>
                {!skill.already_in_goal && (
                  <button type="button"
                    onClick={() => onSkillSelect(skill)}
                    className='ml-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 whitespace-nowrap'
                  >
                    Adicionar
                  </button>
                )}
                {skill.already_in_goal && (
                  <span className='ml-4 px-4 py-2 bg-gray-200 text-gray-600 rounded whitespace-nowrap'>
                    Adicionado
                  </span>
                )}
              </div>

              {skill.foundations.length > 0 && (
                <div className='mt-3 pt-3 border-t'>
                  {skill.foundations.length === 1 ? (
                    <div className='mt-2'>
                      <p className='text-sm text-gray-600 mb-2'>Base sugerida:</p>
                      <SkillFoundationRow
                        skillId={skill.foundations[0].skillId}
                        name={skill.foundations[0].name}
                        status={skill.foundations[0].status}
                        isSelectable={false}
                      />
                    </div>
                  ) : (
                    <div>
                      <button type="button"
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
            <button type="button"
              onClick={onLoadMore}
              disabled={isLoading}
              className='w-full py-3 border rounded hover:bg-gray-50 disabled:opacity-50'
            >
              {isLoading ? 'Carregando...' : 'Carregar mais'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
