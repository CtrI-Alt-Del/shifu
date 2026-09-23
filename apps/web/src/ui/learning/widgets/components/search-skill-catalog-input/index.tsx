import { type ReactNode, useState } from 'react'
import { useEffect } from 'react'

interface SearchSkillCatalogInputProps {
  onSearch: (query: string) => void
  placeholder?: string
  debounceMs?: number
}

export function SearchSkillCatalogInput({
  onSearch,
  placeholder = 'Procurar habilidade...',
  debounceMs = 300,
}: SearchSkillCatalogInputProps): ReactNode {
  const [query, setQuery] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => {
      onSearch(query)
    }, debounceMs)

    return () => clearTimeout(timer)
  }, [query, onSearch, debounceMs])

  return (
    <div className='w-full'>
      <input
        type='text'
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
        className='w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'
      />
    </div>
  )
}
