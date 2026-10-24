import { Link } from '@tanstack/react-router'

import type { MentorActionProposal } from '@/core/intelligence/mentor-action-proposal'
import { ROUTES } from '@/constants/routes'
import { MentorActionCard } from '@/ui/intelligence/widgets/components/mentor-action-card'
import { Button } from '@/ui/shadcn/button'
import { ObjectivePicker } from './objective-picker'
import { useSkillActionCard } from './use-skill-action-card'

export type SkillActionCardProps = { proposal: MentorActionProposal }

export const SkillActionCard = ({ proposal }: SkillActionCardProps) => {
  const {
    icon,
    title,
    isTitleVisible,
    destination,
    reason,
    consequences,
    result,
    statusText,
    actions,
    picker,
    swap,
    resultRef,
    titleRef,
    handleSelectGoal,
  } = useSkillActionCard(proposal)

  return (
    <MentorActionCard
      actions={actions.map(({ destination: target, handleSelect, ...action }) => ({
        ...action,
        onSelect: handleSelect,
        renderLink: target
          ? (className) =>
              target.kind === 'skill' ? (
                <Link
                  className={className}
                  params={{ goalId: target.goalId, skillId: target.skillId }}
                  to={ROUTES.learningSkill}
                >
                  {action.label}
                </Link>
              ) : (
                <Link
                  className={className}
                  params={{ goalId: target.goalId }}
                  to={ROUTES.learningGoal}
                >
                  {action.label}
                </Link>
              )
          : undefined,
      }))}
      consequences={consequences}
      destination={destination}
      icon={icon}
      isTitleVisible={isTitleVisible}
      reason={reason}
      result={result}
      resultRef={resultRef}
      statusText={statusText}
      title={title}
      titleRef={titleRef}
    >
      {picker ? (
        <ObjectivePicker
          candidates={picker.candidates}
          hint={picker.hint}
          onSelect={handleSelectGoal}
        />
      ) : null}
      {swap ? (
        <Button
          className='self-start -ml-2 px-2 text-foreground! underline underline-offset-4'
          onClick={swap.handleSelect}
          type='button'
          variant='ghost'
        >
          {swap.label}
        </Button>
      ) : null}
    </MentorActionCard>
  )
}
