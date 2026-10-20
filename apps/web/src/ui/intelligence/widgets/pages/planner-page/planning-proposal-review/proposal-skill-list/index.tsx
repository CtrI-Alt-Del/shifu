import type { PlanningProposalSkill } from '@/core/intelligence/planning-session'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type ProposalSkillListProps = {
  skills: PlanningProposalSkill[]
}

export const ProposalSkillList = ({ skills }: ProposalSkillListProps) => (
  <ul
    aria-label='Habilidades sugeridas'
    className='overflow-hidden rounded-[10px] border border-border bg-surface-alt p-1.5'
  >
    {skills.map((skill, index) => (
      <li
        className={`flex gap-3 rounded-md px-4 py-3.5 ${
          index < skills.length - 1 ? 'border-b border-border' : ''
        }`}
        key={skill.skillId}
      >
        <span className='grid size-[34px] shrink-0 place-items-center rounded-md bg-jade-tint text-jade-text'>
          <Icon name='graduation-cap' size={16} />
        </span>
        <div className='flex min-w-0 flex-col gap-1'>
          <p className='text-[15px] font-medium leading-[1.35] text-foreground'>
            {skill.name}
          </p>
          <p className='text-[13px] leading-[1.45] text-secondary-foreground'>
            {skill.justification}
          </p>
        </div>
      </li>
    ))}
  </ul>
)
