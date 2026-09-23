import { ReactNode, useState } from 'react';
import { SearchSkillCatalogInput } from '../../components/search-skill-catalog-input';
import { SkillCatalogView } from '../../components/skill-catalog-view';
import { AddSkillFoundationsDialog } from '../../components/add-skill-foundations-dialog';
import { useSearchSkillCatalog } from '../../hooks/useSearchSkillCatalog';
import { useAddSkillToGoal } from '../../hooks/useAddSkillToGoal';
import type { CatalogSkill } from '../../../../services/learning';

interface AddSkillCatalogSectionProps {
	goalId: string;
}

export function AddSkillCatalogSection({
	goalId,
}: AddSkillCatalogSectionProps): ReactNode {
	const searchQuery = useSearchSkillCatalog(goalId);
	const addSkillMutation = useAddSkillToGoal(goalId);
	const [selectedSkill, setSelectedSkill] = useState<CatalogSkill | null>(null);
	const [dialogError, setDialogError] = useState<string | null>(null);

	const handleSearch = (query: string) => {
		searchQuery.setQuery(query);
	};

	const handleLoadMore = () => {
		if (searchQuery.data?.next_cursor) {
			searchQuery.setCursor(searchQuery.data.next_cursor);
		}
	};

	const handleSkillSelect = (skill: CatalogSkill) => {
		setSelectedSkill(skill);
		setDialogError(null);
	};

	const handleDialogClose = () => {
		setSelectedSkill(null);
		setDialogError(null);
		addSkillMutation.reset();
	};

	const handleDialogSubmit = async (
		selectedFoundationIds: string[]
	): Promise<void> => {
		try {
			await addSkillMutation.mutateAsync({
				skill_id: selectedSkill!.id,
				foundation_skill_ids: selectedFoundationIds,
			});
		} catch (error) {
			setDialogError(
				error instanceof Error
					? error.message
					: 'Erro ao adicionar habilidade'
			);
			throw error;
		}
	};

	return (
		<div className="w-full">
			<div className="mb-6">
				<h2 className="text-2xl font-semibold mb-4">Adicionar Habilidade</h2>
				<SearchSkillCatalogInput
					onSearch={handleSearch}
					placeholder="Procurar habilidade..."
					debounceMs={300}
				/>
			</div>

			<SkillCatalogView
				skills={searchQuery.data?.items ?? []}
				isLoading={searchQuery.isLoading}
				error={
					searchQuery.error
						? searchQuery.error.message
						: null
				}
				onSkillSelect={handleSkillSelect}
				onLoadMore={handleLoadMore}
				hasMore={!!searchQuery.data?.next_cursor}
			/>

			{selectedSkill && (
				<AddSkillFoundationsDialog
					skillName={selectedSkill.name}
					foundations={selectedSkill.foundations}
					isOpen={!!selectedSkill}
					isLoading={addSkillMutation.isPending}
					error={dialogError}
					onClose={handleDialogClose}
					onSubmit={handleDialogSubmit}
				/>
			)}
		</div>
	);
}
