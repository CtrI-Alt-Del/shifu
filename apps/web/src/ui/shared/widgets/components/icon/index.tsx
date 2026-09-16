import {
  ArrowRight,
  BookOpen,
  CircleUserRound,
  GraduationCap,
  House,
  Menu,
  Sparkles,
  Trophy,
  type LucideIcon,
  X,
} from 'lucide-react'
import type { LucideProps } from 'lucide-react'

export type IconName =
  | 'arrow-right'
  | 'book-open'
  | 'graduation-cap'
  | 'home'
  | 'menu'
  | 'sparkles'
  | 'trophy'
  | 'user-circle'
  | 'x'

const ICON_COMPONENTS: Record<IconName, LucideIcon> = {
  'arrow-right': ArrowRight,
  'book-open': BookOpen,
  'graduation-cap': GraduationCap,
  home: House,
  menu: Menu,
  sparkles: Sparkles,
  trophy: Trophy,
  'user-circle': CircleUserRound,
  x: X,
}

export type IconProps = Omit<LucideProps, 'name'> & {
  name: IconName
}

export const Icon = ({ name, ...props }: IconProps) => {
  const IconComponent = ICON_COMPONENTS[name]

  return <IconComponent {...props} aria-hidden='true' focusable='false' />
}
