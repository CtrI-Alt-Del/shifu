import type { GoalSkillDetail } from '@/core/learning/goal-detail'

import { GoalSkillRow } from './goal-skill-row'

export type GoalSkillListProps = { goalId: string; skills: readonly GoalSkillDetail[] }

export const GoalSkillList = ({ goalId, skills }: GoalSkillListProps) => (
  <ul aria-label='Habilidades do objetivo' className='space-y-3'>
    {skills.map((skill) => (
      <GoalSkillRow goalId={goalId} key={skill.skillExperienceId} skill={skill} />
    ))}
  </ul>
)
