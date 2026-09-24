import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  ACCOUNT_CONFIRMATION_SUBJECT,
  renderAccountConfirmationEmail,
} from '../templates/index.js'
import type { AccountConfirmationEmailProps } from '../templates/index.js'

const TEMPLATE_NAME = 'account-confirmation'
const TEMPLATE_VERSION = 1
const HTML_FILE_NAME = `${TEMPLATE_NAME}.html`
const MANIFEST_FILE_NAME = `${TEMPLATE_NAME}.manifest.json`

const PLACEHOLDERS = [
  { name: 'display_name', type: 'text' },
  { name: 'action_url', type: 'url' },
  { name: 'expires_at', type: 'text' },
] as const

const PLACEHOLDER_VALUES: AccountConfirmationEmailProps = {
  actionUrl: '{{action_url}}',
  displayName: '{{display_name}}',
  expiresAt: '{{expires_at}}',
}

const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const REPOSITORY_ROOT = resolve(PACKAGE_ROOT, '..', '..')
const OUTPUT_DIRECTORY = resolve(
  REPOSITORY_ROOT,
  'apps/server/src/shifu/communication/providers/email/template/generated',
)

const MANIFEST = {
  template: TEMPLATE_NAME,
  version: TEMPLATE_VERSION,
  subject: ACCOUNT_CONFIRMATION_SUBJECT,
  placeholders: PLACEHOLDERS,
}

class TemplateBuildError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'TemplateBuildError'
  }
}

function collectPlaceholderNames(html: string): Set<string> {
  const names = new Set<string>()
  const matches = html.matchAll(/\{\{([a-z][a-z0-9_]*)\}\}/g)

  for (const match of matches) {
    const name = match[1]
    if (name !== undefined) {
      names.add(name)
    }
  }

  return names
}

function validateRenderedContract(html: string): void {
  const declaredNames: Set<string> = new Set(PLACEHOLDERS.map(({ name }) => name))
  const renderedNames = collectPlaceholderNames(html)
  const missingNames = [...declaredNames].filter((name) => !renderedNames.has(name))
  const unknownNames = [...renderedNames].filter((name) => !declaredNames.has(name))

  if (missingNames.length > 0 || unknownNames.length > 0) {
    throw new TemplateBuildError(
      `Template placeholder mismatch. Missing: ${missingNames.join(', ') || 'none'}; ` +
        `unknown: ${unknownNames.join(', ') || 'none'}.`,
    )
  }

  if (!html.includes('lang="pt-BR"') || !html.includes('dir="ltr"')) {
    throw new TemplateBuildError(
      'Generated template must declare lang="pt-BR" and dir="ltr".',
    )
  }
}

async function buildTemplates(): Promise<void> {
  const rendered = await renderAccountConfirmationEmail(PLACEHOLDER_VALUES)

  if (rendered.subject !== MANIFEST.subject) {
    throw new TemplateBuildError('Rendered subject does not match the template manifest.')
  }

  validateRenderedContract(rendered.html)
  await mkdir(OUTPUT_DIRECTORY, { recursive: true })
  await writeFile(
    resolve(OUTPUT_DIRECTORY, HTML_FILE_NAME),
    `${rendered.html.trimEnd()}\n`,
    'utf8',
  )
  await writeFile(
    resolve(OUTPUT_DIRECTORY, MANIFEST_FILE_NAME),
    `${JSON.stringify(MANIFEST, null, 2)}\n`,
    'utf8',
  )
}

buildTemplates().catch((error: unknown) => {
  if (error instanceof Error) {
    console.error(error.message)
  } else {
    console.error(error)
  }
  process.exitCode = 1
})
