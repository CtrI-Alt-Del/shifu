import type { ReactNode } from 'react'

type SearchSkillCatalogInputProps = {
  onSearch: (query: string) => void
  placeholder?: string
}

export function SearchSkillCatalogInput({
  onSearch,
  placeholder = 'Procurar habilidade...',
}: SearchSkillCatalogInputProps): ReactNode {
  return (
    <div className='w-full'>
      <input
        type='text'
        onChange={(e) => onSearch(e.target.value)}
        placeholder={placeholder}
        className='w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
      />
    </div>
  )
}
