import {
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Award,
  BadgeCheck,
  BookOpen,
  Brain,
  Calendar,
  Check,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Clock3,
  CircleAlert,
  Circle,
  CircleCheck,
  CircleDashed,
  CircleUserRound,
  Copy,
  Expand,
  File,
  FileJson,
  FileSpreadsheet,
  FileText,
  FileType,
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
  ScrollText,
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
  | 'award'
  | 'badge-check'
  | 'book-open'
  | 'brain'
  | 'calendar'
  | 'check'
  | 'chevron-left'
  | 'chevron-right'
  | 'clipboard-check'
  | 'clock-3'
  | 'circle-alert'
  | 'circle'
  | 'circle-check'
  | 'circle-dashed'
  | 'copy'
  | 'expand'
  | 'file'
  | 'file-json'
  | 'file-spreadsheet'
  | 'file-text'
  | 'file-type'
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
  | 'scroll-text'
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
  award: Award,
  'badge-check': BadgeCheck,
  'book-open': BookOpen,
  brain: Brain,
  calendar: Calendar,
  check: Check,
  'chevron-left': ChevronLeft,
  'chevron-right': ChevronRight,
  'clipboard-check': ClipboardCheck,
  'clock-3': Clock3,
  'circle-alert': CircleAlert,
  circle: Circle,
  'circle-check': CircleCheck,
  'circle-dashed': CircleDashed,
  copy: Copy,
  expand: Expand,
  file: File,
  'file-json': FileJson,
  'file-spreadsheet': FileSpreadsheet,
  'file-text': FileText,
  'file-type': FileType,
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
  'scroll-text': ScrollText,
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
