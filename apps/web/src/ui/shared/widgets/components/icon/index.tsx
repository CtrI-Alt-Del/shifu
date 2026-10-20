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
  ShieldAlert,
  Trash2,
  TriangleAlert,
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
  | 'shield-alert'
  | 'trash-2'
  | 'triangle-alert'
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
  'shield-alert': ShieldAlert,
  'trash-2': Trash2,
  'triangle-alert': TriangleAlert,
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
