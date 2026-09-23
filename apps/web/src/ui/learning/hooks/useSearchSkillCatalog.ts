import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { searchSkillCatalog, SearchCatalogResponse } from '../../../services/learning';

export function useSearchSkillCatalog(
	goalId: string
): UseQueryResult<SearchCatalogResponse> & {
	setQuery: (query: string) => void;
	setCursor: (cursor: string | null) => void;
	query: string;
	cursor: string | null;
} {
	const [query, setQuery] = useState('');
	const [cursor, setCursor] = useState<string | null>(null);
	const [debouncedQuery, setDebouncedQuery] = useState('');

	useEffect(() => {
		const timer = setTimeout(() => {
			setDebouncedQuery(query);
			setCursor(null);
		}, 300);

		return () => clearTimeout(timer);
	}, [query]);

	const queryResult = useQuery({
		queryKey: ['skill-catalog', goalId, debouncedQuery, cursor],
		queryFn: () =>
			searchSkillCatalog(goalId, debouncedQuery || undefined, cursor || undefined, 20),
	});

	return {
		...queryResult,
		data: queryResult.data ?? { items: [], next_cursor: null },
		setQuery,
		setCursor,
		query,
		cursor,
	};
}
