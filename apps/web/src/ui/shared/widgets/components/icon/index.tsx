import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  ChevronRight,
  CircleAlert,
  Circle,
  CircleCheck,
  CircleDashed,
  CircleUserRound,
  Eye,
  EyeOff,
  GraduationCap,
  House,
  LoaderCircle,
  LockKeyhole,
  LogOut,
  Menu,
  Minus,
  MoreHorizontal,
  Network,
  Plus,
  RotateCcw,
  Sparkles,
  Target,
  Search,
  Trash2,
  Trophy,
  type LucideIcon,
  X,
} from 'lucide-react'
import type { LucideProps } from 'lucide-react'

export type IconName =
  | 'arrow-left'
  | 'arrow-right'
  | 'book-open'
  | 'chevron-right'
  | 'circle-alert'
  | 'circle'
  | 'circle-check'
  | 'circle-dashed'
  | 'eye'
  | 'eye-off'
  | 'graduation-cap'
  | 'home'
  | 'loader-circle'
  | 'lock-keyhole'
  | 'log-out'
  | 'menu'
  | 'minus'
  | 'ellipsis'
  | 'network'
  | 'plus'
  | 'rotate-ccw'
  | 'sparkles'
  | 'target'
  | 'search'
  | 'trash-2'
  | 'trophy'
  | 'user-circle'
  | 'x'

const ICON_COMPONENTS: Record<IconName, LucideIcon> = {
  'arrow-left': ArrowLeft,
  'arrow-right': ArrowRight,
  'book-open': BookOpen,
  'chevron-right': ChevronRight,
  'circle-alert': CircleAlert,
  circle: Circle,
  'circle-check': CircleCheck,
  'circle-dashed': CircleDashed,
  eye: Eye,
  'eye-off': EyeOff,
  'graduation-cap': GraduationCap,
  home: House,
  'loader-circle': LoaderCircle,
  'lock-keyhole': LockKeyhole,
  'log-out': LogOut,
  menu: Menu,
  minus: Minus,
  ellipsis: MoreHorizontal,
  network: Network,
  plus: Plus,
  'rotate-ccw': RotateCcw,
  sparkles: Sparkles,
  target: Target,
  search: Search,
  'trash-2': Trash2,
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
