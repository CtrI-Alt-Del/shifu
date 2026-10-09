import {
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  BookOpen,
  Brain,
  ChevronRight,
  CircleAlert,
  Circle,
  CircleCheck,
  CircleDashed,
  CircleUserRound,
  Expand,
  History,
  Eye,
  EyeOff,
  GraduationCap,
  House,
  LoaderCircle,
  LockKeyhole,
  LogOut,
  Menu,
  MessageCircle,
  Mic,
  Minus,
  MoreHorizontal,
  Network,
  Paperclip,
  Pencil,
  Plus,
  RotateCcw,
  Sparkles,
  Target,
  Search,
  Trash2,
  Trophy,
  UserRound,
  type LucideIcon,
  X,
} from 'lucide-react'
import type { LucideProps } from 'lucide-react'

export type IconName =
  | 'arrow-left'
  | 'arrow-right'
  | 'arrow-up'
  | 'book-open'
  | 'brain'
  | 'chevron-right'
  | 'circle-alert'
  | 'circle'
  | 'circle-check'
  | 'circle-dashed'
  | 'expand'
  | 'history'
  | 'eye'
  | 'eye-off'
  | 'graduation-cap'
  | 'home'
  | 'loader-circle'
  | 'lock-keyhole'
  | 'log-out'
  | 'menu'
  | 'message-circle'
  | 'mic'
  | 'minus'
  | 'ellipsis'
  | 'network'
  | 'paperclip'
  | 'pencil'
  | 'plus'
  | 'rotate-ccw'
  | 'sparkles'
  | 'target'
  | 'search'
  | 'trash-2'
  | 'trophy'
  | 'user-circle'
  | 'user-round'
  | 'x'

const ICON_COMPONENTS: Record<IconName, LucideIcon> = {
  'arrow-left': ArrowLeft,
  'arrow-right': ArrowRight,
  'arrow-up': ArrowUp,
  'book-open': BookOpen,
  brain: Brain,
  'chevron-right': ChevronRight,
  'circle-alert': CircleAlert,
  circle: Circle,
  'circle-check': CircleCheck,
  'circle-dashed': CircleDashed,
  expand: Expand,
  history: History,
  eye: Eye,
  'eye-off': EyeOff,
  'graduation-cap': GraduationCap,
  home: House,
  'loader-circle': LoaderCircle,
  'lock-keyhole': LockKeyhole,
  'log-out': LogOut,
  menu: Menu,
  'message-circle': MessageCircle,
  mic: Mic,
  minus: Minus,
  ellipsis: MoreHorizontal,
  network: Network,
  paperclip: Paperclip,
  pencil: Pencil,
  plus: Plus,
  'rotate-ccw': RotateCcw,
  sparkles: Sparkles,
  target: Target,
  search: Search,
  'trash-2': Trash2,
  trophy: Trophy,
  'user-circle': CircleUserRound,
  'user-round': UserRound,
  x: X,
}

export type IconProps = Omit<LucideProps, 'name'> & {
  name: IconName
}

export const Icon = ({ name, ...props }: IconProps) => {
  const IconComponent = ICON_COMPONENTS[name]

  return <IconComponent {...props} aria-hidden='true' focusable='false' />
}
