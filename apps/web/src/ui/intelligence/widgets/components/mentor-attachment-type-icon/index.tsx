import { Icon, type IconName } from '@/ui/shared/widgets/components/icon'

export type MentorAttachmentTypeIconProps = {
  mediaType: string
}

const MEDIA_TYPE_ICONS: Record<string, IconName> = {
  'application/pdf': 'file-type',
  'application/json': 'file-json',
  'text/csv': 'file-spreadsheet',
  'text/plain': 'file-text',
}

export const MentorAttachmentTypeIcon = ({
  mediaType,
}: MentorAttachmentTypeIconProps) => (
  <Icon
    className='size-5 shrink-0 text-muted-foreground'
    name={MEDIA_TYPE_ICONS[mediaType] ?? 'file'}
  />
)
