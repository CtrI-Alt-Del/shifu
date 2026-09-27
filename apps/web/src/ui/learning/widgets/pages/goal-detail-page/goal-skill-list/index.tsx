import type { GoalSkillDetail } from '@/core/learning/goal-detail'

import { GoalSkillRow } from './goal-skill-row'

export type GoalSkillListProps = {
  goalId: string
  skills: readonly GoalSkillDetail[]
  onRemoveSkill: (skill: GoalSkillDetail, trigger: HTMLButtonElement) => void
}

export const GoalSkillList = ({ goalId, skills, onRemoveSkill }: GoalSkillListProps) => (
  <ul
    aria-label='Habilidades do objetivo'
    className='divide-y divide-border overflow-hidden rounded-[10px] border border-border bg-surface-alt px-2'
  >
    {skills.map((skill) => (
      <GoalSkillRow
        goalId={goalId}
        key={skill.skillExperienceId}
        onRemove={(trigger) => onRemoveSkill(skill, trigger)}
        skill={skill}
      />
    ))}
  </ul>
)
