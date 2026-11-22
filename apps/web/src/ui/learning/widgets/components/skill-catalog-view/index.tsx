import { motion } from 'motion/react'
import { type ReactNode, useState } from 'react'

import type { CatalogSkill } from '@/core/learning/catalog-skill'

import { ENTRANCE_ROW } from '@/constants/motion-variants'
import { Button } from '@/ui/shadcn/button'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { SkillFoundationRow } from '../skill-foundation-row'

type SkillCatalogViewProps = {
  skills: readonly CatalogSkill[]
  isLoading?: boolean
  error?: string | null
  onSkillSelect: (skill: CatalogSkill) => void
  onLoadMore?: () => void
  onRetry?: () => void
  hasMore?: boolean
}

export function SkillCatalogView({
  skills,
  isLoading = false,
  error = null,
  onSkillSelect,
  onLoadMore,
  onRetry,
  hasMore = false,
}: SkillCatalogViewProps): ReactNode {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const toggleExpand = (skillId: string) => {
    setExpandedId(expandedId === skillId ? null : skillId)
  }

  return (
    <div className='w-full'>
      {error && (
        <div
          className='mb-4 rounded-xl border border-selo-text bg-surface-alt p-4 text-selo-text'
          role='alert'
        >
          <p>{error}</p>
          {onRetry ? (
            <Button
              className='mt-3 border-control-border! text-foreground! focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring'
              onClick={onRetry}
              type='button'
              variant='outline'
            >
              Tentar novamente
            </Button>
          ) : null}
        </div>
      )}

      {isLoading && skills.length === 0 ? (
        <output className='block py-8 text-center'>
          <p className='text-muted-foreground'>Carregando habilidades...</p>
        </output>
      ) : skills.length === 0 ? (
        <div className='py-8 text-center text-muted-foreground'>
          <p>Nenhuma habilidade encontrada</p>
        </div>
      ) : (
        <MotionEntrance className='space-y-3'>
          {skills.map((skill) => (
            <motion.div
              key={skill.id}
              className='rounded-xl border border-border bg-surface-alt px-4 py-4 sm:px-5'
              variants={ENTRANCE_ROW}
            >
              <div className='flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4'>
                <div className='flex-1'>
                  <h3 className='text-base font-semibold text-foreground'>
                    {skill.name}
                  </h3>
                  <p className='mt-1 text-sm text-secondary-foreground'>
                    {skill.description}
                  </p>
                </div>
                {skill.alreadyInGoal ? (
                  <span className='whitespace-nowrap rounded-md bg-muted px-4 py-2 text-sm text-muted-foreground'>
                    Adicionado
                  </span>
                ) : (
                  <Button
                    className='whitespace-nowrap'
                    onClick={() => onSkillSelect(skill)}
                    type='button'
                  >
                    Adicionar
                  </Button>
                )}
              </div>

              {skill.foundations.length > 0 && (
                <div className='mt-3 border-t border-border pt-3'>
                  {skill.foundations.length === 1 ? (
                    <div className='mt-2'>
                      <p className='mb-2 text-sm text-muted-foreground'>Base sugerida:</p>
                      <SkillFoundationRow
                        skillId={skill.foundations[0].skillId}
                        name={skill.foundations[0].name}
                        status={skill.foundations[0].status}
                        isSelectable={false}
                      />
                    </div>
                  ) : (
                    <div>
                      <Button
                        className='px-0 text-sm font-medium underline underline-offset-2'
                        onClick={() => toggleExpand(skill.id)}
                        type='button'
                        variant='ghost'
                      >
                        {expandedId === skill.id
                          ? 'Ocultar bases'
                          : `Ver bases (${skill.foundations.length})`}
                      </Button>
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
            </motion.div>
          ))}

          {hasMore && onLoadMore && (
            <Button
              className='w-full border-control-border! text-foreground!'
              disabled={isLoading}
              onClick={onLoadMore}
              type='button'
              variant='outline'
            >
              {isLoading ? 'Carregando...' : 'Carregar mais'}
            </Button>
          )}
        </MotionEntrance>
      )}
    </div>
  )
}
