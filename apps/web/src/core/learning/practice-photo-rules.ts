export const PRACTICE_PHOTO_MAX_BYTES = 10 * 1024 * 1024
export const PRACTICE_PHOTO_MULTIPART_OVERHEAD_BYTES = 65_536
export const PRACTICE_PHOTO_MAX_BODY_BYTES =
  PRACTICE_PHOTO_MAX_BYTES + PRACTICE_PHOTO_MULTIPART_OVERHEAD_BYTES

export const PRACTICE_PHOTO_MEDIA_TYPES_BY_EXTENSION: Readonly<Record<string, string>> = {
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.webp': 'image/webp',
}

export const PRACTICE_PHOTO_ACCEPTED_MEDIA_TYPES: readonly string[] = [
  'image/jpeg',
  'image/png',
  'image/webp',
]

export const PRACTICE_PHOTO_ACCEPT_ATTRIBUTE =
  PRACTICE_PHOTO_ACCEPTED_MEDIA_TYPES.join(',')

export const PRACTICE_PHOTO_RULES_TEXT =
  'Formatos aceitos: JPEG, PNG ou WebP. Tamanho máximo: 10 MB por foto.'

export const PRACTICE_PHOTO_KEY_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/

export type PracticePhotoFileProblem = 'empty' | 'too-large' | 'unsupported'

export function getPracticePhotoExtension(filename: string): string {
  const separator = filename.lastIndexOf('.')
  return separator < 0 ? '' : filename.slice(separator).toLowerCase()
}

export function inspectPracticePhotoFile(file: {
  name: string
  size: number
  type: string
}): PracticePhotoFileProblem | null {
  const mediaType =
    PRACTICE_PHOTO_MEDIA_TYPES_BY_EXTENSION[getPracticePhotoExtension(file.name)]
  const declaredType = file.type.toLowerCase()
  if (
    !mediaType ||
    (declaredType !== '' &&
      declaredType !== mediaType &&
      !PRACTICE_PHOTO_ACCEPTED_MEDIA_TYPES.includes(declaredType))
  )
    return 'unsupported'
  if (file.size === 0) return 'empty'
  if (file.size > PRACTICE_PHOTO_MAX_BYTES) return 'too-large'
  return null
}
