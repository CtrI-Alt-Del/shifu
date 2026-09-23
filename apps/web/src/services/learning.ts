export interface CatalogFoundation {
	skill_id: string;
	name: string;
	status: 'present' | 'missing';
}

export interface CatalogSkill {
	id: string;
	name: string;
	description: string;
	already_in_goal: boolean;
	skill_experience_id: string | null;
	foundations: CatalogFoundation[];
}

export interface SearchCatalogResponse {
	items: CatalogSkill[];
	next_cursor: string | null;
}

export interface SkillExperience {
	id: string;
	skill_id: string;
	status: string;
}

export interface AddSkillResponse {
	created: SkillExperience[];
}

export async function searchSkillCatalog(
	goalId: string,
	query?: string,
	cursor?: string,
	limit: number = 20
): Promise<SearchCatalogResponse> {
	const params = new URLSearchParams();
	if (query) params.set('query', query);
	if (cursor) params.set('cursor', cursor);
	params.set('limit', String(limit));

	const response = await fetch(
		`/api/learning/goals/${goalId}/skills/catalog?${params}`,
		{
			method: 'GET',
			headers: {
				'Content-Type': 'application/json',
			},
		}
	);

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.message || 'Failed to search skill catalog');
	}

	return response.json();
}

export async function addSkillToGoal(
	goalId: string,
	skillId: string,
	foundationSkillIds: string[] = []
): Promise<AddSkillResponse> {
	const response = await fetch(
		`/api/learning/goals/${goalId}/skills`,
		{
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				skill_id: skillId,
				foundation_skill_ids: foundationSkillIds,
			}),
		}
	);

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.message || 'Failed to add skill to goal');
	}

	return response.json();
}
