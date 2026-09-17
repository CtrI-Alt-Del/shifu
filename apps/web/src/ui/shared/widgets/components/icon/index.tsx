import {
  ArrowRight,
  BookOpen,
  CircleAlert,
  CircleUserRound,
  Eye,
  EyeOff,
  GraduationCap,
  House,
  LoaderCircle,
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
  | 'circle-alert'
  | 'eye'
  | 'eye-off'
  | 'graduation-cap'
  | 'home'
  | 'loader-circle'
  | 'menu'
  | 'sparkles'
  | 'trophy'
  | 'user-circle'
  | 'x'

const ICON_COMPONENTS: Record<IconName, LucideIcon> = {
  'arrow-right': ArrowRight,
  'book-open': BookOpen,
  'circle-alert': CircleAlert,
  eye: Eye,
  'eye-off': EyeOff,
  'graduation-cap': GraduationCap,
  home: House,
  'loader-circle': LoaderCircle,
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
