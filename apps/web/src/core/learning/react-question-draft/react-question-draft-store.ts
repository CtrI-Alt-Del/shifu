export type ReactQuestionDraftKey = {
  accountId: string
  goalId: string
  skillId: string
  competencyId: string
  activityId: string
  questionKey: string
  activityRevision: string
}

export type ReactQuestionDraft = ReactQuestionDraftKey & {
  schemaVersion: 1
  files: readonly { path: string; content: string }[]
  generation: number
  savedAt: number
  tombstone: boolean
}

export type ReactQuestionDraftStore = {
  read(key: ReactQuestionDraftKey): Promise<ReactQuestionDraft | null>
  write(
    key: ReactQuestionDraftKey,
    files: readonly { path: string; content: string }[],
    expectedGeneration: number,
  ): Promise<number>
  tombstone(key: ReactQuestionDraftKey): Promise<number>
  tombstoneActivity(accountId: string, activityId: string): Promise<void>
  tombstoneStaleActivity(
    key: Pick<
      ReactQuestionDraftKey,
      'accountId' | 'goalId' | 'skillId' | 'competencyId' | 'activityId'
    >,
    activityRevision: string,
    activeQuestionKeys: readonly string[],
  ): Promise<void>
  subscribe(
    key: ReactQuestionDraftKey,
    listener: (event: { generation: number; tombstone: boolean }) => void,
  ): () => void
  clearTombstone(
    key: ReactQuestionDraftKey,
    files: readonly { path: string; content: string }[],
    expectedGeneration: number,
  ): Promise<number>
}

// Frontend project drafts share the version-one React IndexedDB record format.
// These aliases let HTML/CSS/JavaScript reuse generations and tombstones without
// migrating or dropping draft records already saved by React questions.
export type FrontendQuestionDraftKey = ReactQuestionDraftKey
export type FrontendQuestionDraft = ReactQuestionDraft
export type FrontendQuestionDraftStore = ReactQuestionDraftStore

const FORBIDDEN_ADDITIONAL_FILES = new Set([
  'package.json',
  'package-lock.json',
  'pnpm-lock.yaml',
  'yarn.lock',
  'bun.lock',
  'bun.lockb',
  'npm-shrinkwrap.json',
  'tsconfig.json',
  'deno.json',
  'deno.jsonc',
  'vite.config.js',
  'vite.config.ts',
  'webpack.config.js',
  'webpack.config.ts',
])

export function isValidReactQuestionDraft(
  value: unknown,
  key: ReactQuestionDraftKey,
): value is ReactQuestionDraft {
  if (!value || typeof value !== 'object') return false
  const draft = value as Partial<ReactQuestionDraft>
  return (
    draft.schemaVersion === 1 &&
    draft.accountId === key.accountId &&
    draft.goalId === key.goalId &&
    draft.skillId === key.skillId &&
    draft.competencyId === key.competencyId &&
    draft.activityId === key.activityId &&
    draft.questionKey === key.questionKey &&
    draft.activityRevision === key.activityRevision &&
    Number.isSafeInteger(draft.generation) &&
    (draft.generation ?? 0) > 0 &&
    Number.isFinite(draft.savedAt) &&
    typeof draft.tombstone === 'boolean' &&
    Array.isArray(draft.files) &&
    draft.files.every(
      (file) =>
        Boolean(file) &&
        typeof file.path === 'string' &&
        typeof file.content === 'string',
    )
  )
}

export function nextReactQuestionDraftGeneration(value: unknown) {
  return typeof value === 'number' &&
    Number.isSafeInteger(value) &&
    value >= 0 &&
    value < Number.MAX_SAFE_INTEGER
    ? value + 1
    : 1
}

export function validateReactAdditionalFile(
  path: string,
  files: readonly { path: string }[],
  policy: {
    allowedDirectories: readonly string[]
    allowedExtensions: readonly string[]
    maxFiles: number
  } | null,
  initialPaths: readonly string[] = [],
  isCreating = true,
) {
  if (!policy || !path || path.length > 240 || path.includes('\\') || path.includes('\0'))
    return false
  const segments = path.split('/')
  if (
    segments.some(
      (part) => !part || part === '.' || part === '..' || part.startsWith('.'),
    )
  )
    return false
  if (
    segments.some(
      (part) => part.length > 64 || !/^[A-Za-z0-9_-][A-Za-z0-9._-]*$/.test(part),
    )
  )
    return false
  const directory = segments.slice(0, -1).join('/')
  const extension = path.slice(path.lastIndexOf('.')).toLowerCase()
  const fileName = segments.at(-1)?.toLowerCase() ?? ''
  if (
    FORBIDDEN_ADDITIONAL_FILES.has(fileName) ||
    (fileName.startsWith('tsconfig.') && fileName.endsWith('.json')) ||
    fileName.includes('.config.') ||
    segments.some((part) => ['.git', 'node_modules'].includes(part.toLowerCase()))
  )
    return false
  if (
    !policy.allowedDirectories.some(
      (allowed) => directory === allowed || directory.startsWith(`${allowed}/`),
    )
  )
    return false
  if (
    !policy.allowedExtensions.includes(extension) ||
    files.some(
      ({ path: existingPath }) =>
        existingPath === path ||
        existingPath.startsWith(`${path}/`) ||
        path.startsWith(`${existingPath}/`),
    )
  )
    return false
  const additionalCount = files.filter((file) => !initialPaths.includes(file.path)).length
  return isCreating
    ? additionalCount < policy.maxFiles
    : additionalCount <= policy.maxFiles
}
