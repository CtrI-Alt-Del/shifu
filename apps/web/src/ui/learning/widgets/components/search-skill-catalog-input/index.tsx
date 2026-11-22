import type { ReactNode } from 'react'

import { Input } from '@/ui/shadcn/input'

type SearchSkillCatalogInputProps = {
  onSearch: (query: string) => void
  placeholder?: string
}

export function SearchSkillCatalogInput({
  onSearch,
  placeholder = 'Buscar no Currículo',
}: SearchSkillCatalogInputProps): ReactNode {
  return (
    <div className='w-full'>
      <Input
        aria-label={placeholder}
        className='px-4 text-[15px]'
        onChange={(e) => onSearch(e.target.value)}
        placeholder={placeholder}
        type='text'
      />
    </div>
  )
}
