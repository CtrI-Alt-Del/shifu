import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  ACCOUNT_CONFIRMATION_SUBJECT,
  PASSWORD_RECOVERY_SUBJECT,
  renderAccountConfirmationEmail,
  renderPasswordRecoveryEmail,
} from '../templates/index.js'
import type {
  AccountConfirmationEmailProps,
  PasswordRecoveryEmailProps,
} from '../templates/index.js'

type TemplatePlaceholder = {
  name: string
  type: 'text' | 'url'
}

type RenderedTemplate = {
  subject: string
  html: string
}

type TemplateManifest = {
  template: string
  version: number
  subject: string
  placeholders: readonly TemplatePlaceholder[]
}

type TemplateDefinition = TemplateManifest & {
  render: () => Promise<RenderedTemplate>
}

const ACCOUNT_CONFIRMATION_PLACEHOLDERS = [
  { name: 'display_name', type: 'text' },
  { name: 'action_url', type: 'url' },
  { name: 'expires_at', type: 'text' },
] as const

const ACCOUNT_CONFIRMATION_PLACEHOLDER_VALUES: AccountConfirmationEmailProps = {
  actionUrl: '{{action_url}}',
  displayName: '{{display_name}}',
  expiresAt: '{{expires_at}}',
}

const PASSWORD_RECOVERY_PLACEHOLDERS = [
  { name: 'action_url', type: 'url' },
  { name: 'expires_at', type: 'text' },
] as const

const PASSWORD_RECOVERY_PLACEHOLDER_VALUES: PasswordRecoveryEmailProps = {
  actionUrl: '{{action_url}}',
  expiresAt: '{{expires_at}}',
}

const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..')
const REPOSITORY_ROOT = resolve(PACKAGE_ROOT, '..', '..')
const OUTPUT_DIRECTORY = resolve(
  REPOSITORY_ROOT,
  'apps/server/src/shifu/communication/providers/email/template/generated',
)

const TEMPLATES: readonly TemplateDefinition[] = [
  {
    template: 'account-confirmation',
    version: 1,
    subject: ACCOUNT_CONFIRMATION_SUBJECT,
    placeholders: ACCOUNT_CONFIRMATION_PLACEHOLDERS,
    render: () => renderAccountConfirmationEmail(ACCOUNT_CONFIRMATION_PLACEHOLDER_VALUES),
  },
  {
    template: 'password-recovery',
    version: 1,
    subject: PASSWORD_RECOVERY_SUBJECT,
    placeholders: PASSWORD_RECOVERY_PLACEHOLDERS,
    render: () => renderPasswordRecoveryEmail(PASSWORD_RECOVERY_PLACEHOLDER_VALUES),
  },
]

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

function validateManifest(manifest: TemplateManifest): void {
  if (!/^[a-z][a-z0-9-]*$/.test(manifest.template)) {
    throw new TemplateBuildError(
      `Template name must be kebab-case: ${manifest.template}.`,
    )
  }

  if (!Number.isInteger(manifest.version) || manifest.version < 1) {
    throw new TemplateBuildError(
      `Template version must be a positive integer: ${manifest.template}.`,
    )
  }

  if (manifest.subject.trim().length === 0) {
    throw new TemplateBuildError(
      `Template subject must not be empty: ${manifest.template}.`,
    )
  }

  const placeholderNames = manifest.placeholders.map(({ name }) => name)
  if (new Set(placeholderNames).size !== placeholderNames.length) {
    throw new TemplateBuildError(
      `Template manifest contains duplicate placeholders: ${manifest.template}.`,
    )
  }
}

function validateRenderedContract(html: string, manifest: TemplateManifest): void {
  const declaredNames: Set<string> = new Set(
    manifest.placeholders.map(({ name }) => name),
  )
  const renderedNames = collectPlaceholderNames(html)
  const missingNames = [...declaredNames].filter((name) => !renderedNames.has(name))
  const unknownNames = [...renderedNames].filter((name) => !declaredNames.has(name))

  if (missingNames.length > 0 || unknownNames.length > 0) {
    throw new TemplateBuildError(
      `${manifest.template} placeholder mismatch. Missing: ${missingNames.join(', ') || 'none'}; ` +
        `unknown: ${unknownNames.join(', ') || 'none'}.`,
    )
  }

  if (!html.includes('lang="pt-BR"') || !html.includes('dir="ltr"')) {
    throw new TemplateBuildError(
      `${manifest.template} must declare lang="pt-BR" and dir="ltr".`,
    )
  }
}

async function buildTemplate(template: TemplateDefinition): Promise<void> {
  validateManifest(template)
  const rendered = await template.render()

  if (rendered.subject !== template.subject) {
    throw new TemplateBuildError(
      `Rendered subject does not match the ${template.template} manifest.`,
    )
  }

  validateRenderedContract(rendered.html, template)
  await mkdir(OUTPUT_DIRECTORY, { recursive: true })
  await writeFile(
    resolve(OUTPUT_DIRECTORY, `${template.template}.html`),
    `${rendered.html.trimEnd()}\n`,
    'utf8',
  )
  await writeFile(
    resolve(OUTPUT_DIRECTORY, `${template.template}.manifest.json`),
    `${JSON.stringify(
      {
        template: template.template,
        version: template.version,
        subject: template.subject,
        placeholders: template.placeholders,
      },
      null,
      2,
    )}\n`,
    'utf8',
  )
}

async function buildTemplates(): Promise<void> {
  for (const template of TEMPLATES) {
    await buildTemplate(template)
  }
}

buildTemplates().catch((error: unknown) => {
  if (error instanceof Error) {
    console.error(error.message)
  } else {
    console.error(error)
  }
  process.exitCode = 1
})
