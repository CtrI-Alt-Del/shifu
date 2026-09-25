import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CircleCheck,
  ChevronRight,
  CircleAlert,
  CircleUserRound,
  Eye,
  EyeOff,
  GraduationCap,
  House,
  LoaderCircle,
  LockKeyhole,
  LogOut,
  Menu,
  RotateCcw,
  Sparkles,
  Target,
  Trophy,
  type LucideIcon,
  X,
} from 'lucide-react'
import type { LucideProps } from 'lucide-react'

export type IconName =
  | 'arrow-left'
  | 'arrow-right'
  | 'book-open'
  | 'circle-check'
  | 'chevron-right'
  | 'circle-alert'
  | 'eye'
  | 'eye-off'
  | 'graduation-cap'
  | 'home'
  | 'loader-circle'
  | 'lock-keyhole'
  | 'log-out'
  | 'menu'
  | 'rotate-ccw'
  | 'sparkles'
  | 'target'
  | 'trophy'
  | 'user-circle'
  | 'x'

const ICON_COMPONENTS: Record<IconName, LucideIcon> = {
  'arrow-left': ArrowLeft,
  'arrow-right': ArrowRight,
  'book-open': BookOpen,
  'circle-check': CircleCheck,
  'chevron-right': ChevronRight,
  'circle-alert': CircleAlert,
  eye: Eye,
  'eye-off': EyeOff,
  'graduation-cap': GraduationCap,
  home: House,
  'loader-circle': LoaderCircle,
  'lock-keyhole': LockKeyhole,
  'log-out': LogOut,
  menu: Menu,
  'rotate-ccw': RotateCcw,
  sparkles: Sparkles,
  target: Target,
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
