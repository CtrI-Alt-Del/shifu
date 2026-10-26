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
  FilePlus2,
  FileSpreadsheet,
  FileText,
  FileType,
  Flag,
  Flame,
  Footprints,
  History,
  Eye,
  EyeOff,
  GitFork,
  GraduationCap,
  House,
  Info,
  Layers,
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
  TrendingUp,
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
  | 'compass'
  | 'circle-alert'
  | 'circle'
  | 'circle-check'
  | 'circle-dashed'
  | 'copy'
  | 'expand'
  | 'file'
  | 'file-plus'
  | 'file-json'
  | 'file-spreadsheet'
  | 'file-text'
  | 'file-type'
  | 'flag'
  | 'flame'
  | 'footprints'
  | 'history'
  | 'eye'
  | 'eye-off'
  | 'git-fork'
  | 'graduation-cap'
  | 'home'
  | 'info'
  | 'layers'
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
  | 'trending-up'
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
  compass: Compass,
  'circle-alert': CircleAlert,
  circle: Circle,
  'circle-check': CircleCheck,
  'circle-dashed': CircleDashed,
  copy: Copy,
  expand: Expand,
  file: File,
  'file-plus': FilePlus2,
  'file-json': FileJson,
  'file-spreadsheet': FileSpreadsheet,
  'file-text': FileText,
  'file-type': FileType,
  flag: Flag,
  flame: Flame,
  footprints: Footprints,
  history: History,
  eye: Eye,
  'eye-off': EyeOff,
  'git-fork': GitFork,
  'graduation-cap': GraduationCap,
  home: House,
  info: Info,
  layers: Layers,
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
  'trending-up': TrendingUp,
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
