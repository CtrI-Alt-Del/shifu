import { useMutation, UseMutationResult } from '@tanstack/react-query';
import { addSkillToGoal, AddSkillResponse } from '../../../services/learning';

interface AddSkillRequest {
	skill_id: string;
	foundation_skill_ids?: string[];
}

export function useAddSkillToGoal(
	goalId: string
): UseMutationResult<AddSkillResponse, Error, AddSkillRequest> {
	return useMutation({
		mutationFn: (request: AddSkillRequest) =>
			addSkillToGoal(
				goalId,
				request.skill_id,
				request.foundation_skill_ids ?? []
			),
	});
}
