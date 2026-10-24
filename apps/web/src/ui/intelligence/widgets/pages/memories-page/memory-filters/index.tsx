import { useId } from 'react'

import type { LearnerMemoryCategory } from '@/core/intelligence/learner-memory'
import { LEARNER_MEMORY_CATEGORY_OPTIONS } from '@/ui/intelligence/constants/learner-memory-categories'
import { Button } from '@/ui/shadcn/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/ui/shadcn/dropdown-menu'
import { Input } from '@/ui/shadcn/input'
import { Tabs, TabsList, TabsTrigger } from '@/ui/shadcn/tabs'
import { Icon } from '@/ui/shared/widgets/components/icon'

import {
  MEMORY_SEARCH_MAX_LENGTH,
  type MemoryCategoryFilter,
  useMemoryFilters,
} from './use-memory-filters'

export type MemoryFiltersProps = {
  query: string
  category: LearnerMemoryCategory | null
  view: 'list' | 'map'
  /** Number shown on the "Todas" chip; null when the total is unknown. */
  totalCount: number | null
  onQueryChange: (query: string) => void
  onCategoryChange: (category: LearnerMemoryCategory | null) => void
  onViewChange: (view: 'list' | 'map') => void
}

const CHIP_CLASS_NAME =
  'min-h-11 gap-2 rounded-full border border-control-border px-3 text-sm font-normal'
const SELECTED_CHIP_CLASS_NAME =
  'border-jade-solid! bg-jade-tint! text-jade-text! hover:bg-jade-tint!'

export const MemoryFilters = (props: MemoryFiltersProps) => {
  const { category, totalCount, view, onViewChange } = props
  const searchId = useId()
  const { draftQuery, handleQueryInputChange, handleCategorySelect } =
    useMemoryFilters(props)
  const activeLabel =
    LEARNER_MEMORY_CATEGORY_OPTIONS.find((option) => option.category === category)
      ?.label ?? 'Todas'
  const allLabel = totalCount === null ? 'Todas' : `Todas · ${totalCount}`

  return (
    <div className='space-y-4'>
      <div className='flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between'>
        <div className='w-full lg:max-w-[25rem]'>
          <label
            className='mb-1 block text-sm font-semibold lg:sr-only'
            htmlFor={searchId}
          >
            Buscar memórias
          </label>
          <div className='relative'>
            <Icon
              name='search'
              className='pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground'
            />
            <Input
              className='pl-9'
              id={searchId}
              maxLength={MEMORY_SEARCH_MAX_LENGTH}
              onChange={(event) => handleQueryInputChange(event.currentTarget.value)}
              placeholder='Buscar memórias'
              type='search'
              value={draftQuery}
            />
          </div>
        </div>
        <div className='flex items-center gap-2 lg:justify-end'>
          <div className='flex flex-1 gap-2 lg:hidden'>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  className='min-w-0 flex-1 gap-2 border border-control-border text-foreground'
                  variant='ghost'
                  type='button'
                >
                  Categoria: {activeLabel}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align='start'>
                <DropdownMenuRadioGroup
                  onValueChange={(value) =>
                    handleCategorySelect(value as MemoryCategoryFilter)
                  }
                  value={category ?? 'all'}
                >
                  <DropdownMenuRadioItem value='all'>Todas</DropdownMenuRadioItem>
                  {LEARNER_MEMORY_CATEGORY_OPTIONS.map((option) => (
                    <DropdownMenuRadioItem key={option.category} value={option.category}>
                      {option.label}
                    </DropdownMenuRadioItem>
                  ))}
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenu>
            <Button
              className='min-w-0 flex-1 border border-control-border text-foreground'
              onClick={() => onViewChange(view === 'list' ? 'map' : 'list')}
              type='button'
              variant='ghost'
            >
              {view === 'list' ? 'Ver Mapa' : 'Ver Lista'}
            </Button>
          </div>
          <div className='hidden lg:block'>
            <Tabs
              onValueChange={(value) => onViewChange(value as 'list' | 'map')}
              value={view}
            >
              <TabsList aria-label='Visualização das memórias'>
                <TabsTrigger className='min-h-9 gap-2' value='list'>
                  <Icon name='list' className='mr-2 inline size-4' />
                  Lista
                </TabsTrigger>
                <TabsTrigger className='min-h-9 gap-2' value='map'>
                  <Icon name='network' className='mr-2 inline size-4' />
                  Mapa
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </div>
      </div>
      <fieldset className='hidden flex-wrap gap-2 lg:flex'>
        <legend className='sr-only'>Filtrar por categoria</legend>
        <Button
          aria-pressed={category === null}
          className={`${CHIP_CLASS_NAME} ${category === null ? SELECTED_CHIP_CLASS_NAME : ''}`}
          onClick={() => handleCategorySelect('all')}
          type='button'
          variant='ghost'
        >
          {allLabel}
        </Button>
        {LEARNER_MEMORY_CATEGORY_OPTIONS.map((option) => (
          <Button
            aria-pressed={category === option.category}
            className={`${CHIP_CLASS_NAME} ${category === option.category ? SELECTED_CHIP_CLASS_NAME : ''}`}
            key={option.category}
            onClick={() => handleCategorySelect(option.category)}
            type='button'
            variant='ghost'
          >
            <Icon name={option.icon} className='size-4' />
            {option.label}
          </Button>
        ))}
      </fieldset>
    </div>
  )
}
