import {
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  BookOpen,
  Brain,
  Calendar,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Compass,
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
  List,
  LoaderCircle,
  Lock,
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
  Puzzle,
  RotateCcw,
  ScrollText,
  SlidersHorizontal,
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
  | 'calendar'
  | 'check'
  | 'chevron-left'
  | 'chevron-right'
  | 'clock-3'
  | 'compass'
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
  | 'list'
  | 'loader-circle'
  | 'lock'
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
  | 'puzzle'
  | 'rotate-ccw'
  | 'scroll-text'
  | 'sliders-horizontal'
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
  calendar: Calendar,
  check: Check,
  'chevron-left': ChevronLeft,
  'chevron-right': ChevronRight,
  'clock-3': Clock3,
  compass: Compass,
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
  list: List,
  'loader-circle': LoaderCircle,
  lock: Lock,
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
  puzzle: Puzzle,
  'rotate-ccw': RotateCcw,
  'scroll-text': ScrollText,
  'sliders-horizontal': SlidersHorizontal,
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
