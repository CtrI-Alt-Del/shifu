type MentorAttachmentPreviewProps = {
  filename: string
  src: string
  mediaType: string
}

export const MentorAttachmentPreview = ({
  filename,
  src,
  mediaType,
}: MentorAttachmentPreviewProps) => (
  <div className='min-w-0 max-w-full overflow-hidden rounded-md bg-surface'>
    <img
      alt={`Prévia de ${filename}`}
      className='max-h-64 max-w-full object-contain'
      src={src}
      data-media-type={mediaType}
    />
  </div>
)
