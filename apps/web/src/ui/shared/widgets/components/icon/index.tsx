import {
  ArrowRight,
  BookOpen,
  CircleUserRound,
  GraduationCap,
  House,
  Sparkles,
  Trophy,
  type LucideIcon,
} from 'lucide-react'
import type { LucideProps } from 'lucide-react'

export type IconName =
  | 'arrow-right'
  | 'book-open'
  | 'graduation-cap'
  | 'home'
  | 'sparkles'
  | 'trophy'
  | 'user-circle'

const ICON_COMPONENTS: Record<IconName, LucideIcon> = {
  'arrow-right': ArrowRight,
  'book-open': BookOpen,
  'graduation-cap': GraduationCap,
  home: House,
  sparkles: Sparkles,
  trophy: Trophy,
  'user-circle': CircleUserRound,
}

export type IconProps = Omit<LucideProps, 'name'> & {
  name: IconName
}

export const Icon = ({ name, ...props }: IconProps) => {
  const IconComponent = ICON_COMPONENTS[name]

  return <IconComponent {...props} aria-hidden='true' focusable='false' />
}
