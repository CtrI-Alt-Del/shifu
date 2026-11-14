import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

// Test-integrity check: a test file is allowed only for a use case, controller,
// job, workflow (in-process, with mocked agents), hook, widget, page, layout or
// API handler, or an explicitly documented domain/preparation/capability/security
// conformance boundary. Anything else is a violation.
//
//   node scripts/check-test-integrity.mjs          fail on any other test file
//   node scripts/check-test-integrity.mjs --list   also print every allowed file

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const rootDirectory = path.resolve(scriptDirectory, '..')
const serverTests = path.join(rootDirectory, 'apps', 'server', 'tests')
const webSource = path.join(rootDirectory, 'apps', 'web', 'src')
const webTests = path.join(rootDirectory, 'apps', 'web', 'tests')
const ignoredDirectories = new Set([
  'node_modules',
  '__pycache__',
  '.venv',
  '.playwright-cli',
  'dist',
  'build',
])

// First matching rule wins. Paths are relative to the app and use "/".
const serverRules = [
  ['use case', /^tests\/[^/]+\/core\/use_cases\//],
  ['domain conformance', /^tests\/[^/]+\/core\/domain\/test_[a-z0-9_]+\.py$/],
  [
    'preparation',
    /^tests\/intelligence\/preparation\/test_prepare_planning_indexes\.py$/,
  ],
  ['capability', /^tests\/intelligence\/capabilities\/test_planning_capabilities\.py$/],
  ['use case', /^tests\/core\/[^/]+\/use_cases\//],
  ['api handler', /^tests\/(?:[^/]+\/)?rest\/handlers\//],
  ['controller', /^tests\/(?:[^/]+\/)?rest\//],
  ['controller', /^tests\/[^/]+\/server\/.*_controller\.py$/],
  ['workflow', /^tests\/[^/]+\/ai\/workflows\/test_[a-z0-9_]+_workflow\.py$/],
  ['job', /^tests\/messaging\/inngest\/jobs\//],
  ['job', /^tests\/(?!shared\/)[^/]+\/messaging\//],
]

const webSourceRules = [
  [
    'security contract',
    /^rest\/security\/tests\/server-request-origin-contract\.test\.ts$/,
  ],
  ['api handler', /(?:^|\/)routes\/api\//],
  ['page', /(?:^|\/)routes\//],
  ['layout', /(?:^|\/)widgets\/layouts\//],
  ['page', /(?:^|\/)widgets\/pages\//],
  ['widget', /(?:^|\/)widgets\//],
  ['hook', /(?:^|\/)(?:hooks|contexts)\//],
  ['hook', /\/use-[^/]+\.test\.tsx?$/],
]

const webBrowserRules = [
  ['api handler', /-api-handler\.test\.ts$/],
  ['api handler', /-route-handlers?\.test\.ts$/],
  ['api handler', /-auth-api\.test\.ts$/],
  ['api handler', /-api\.test\.ts$/],
  ['layout', /-layout\.test\.ts$/],
  ['page', /-page\.test\.ts$/],
]

function relativePath(base, filePath) {
  return path.relative(base, filePath).split(path.sep).join('/')
}

function collect(directory, matches) {
  if (!fs.existsSync(directory)) {
    return []
  }
  const files = []
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (ignoredDirectories.has(entry.name)) {
      continue
    }
    const entryPath = path.join(directory, entry.name)
    if (entry.isDirectory()) {
      files.push(...collect(entryPath, matches))
    } else if (matches(entry.name)) {
      files.push(entryPath)
    }
  }
  return files
}

function classify(rules, relative) {
  const rule = rules.find(([, pattern]) => pattern.test(relative))
  return rule ? rule[0] : null
}

function checkServer() {
  const files = collect(
    serverTests,
    (name) => /^test_.*\.py$/.test(name) || /_test\.py$/.test(name),
  )
  return files.map((filePath) => {
    const relative = relativePath(path.join(rootDirectory, 'apps', 'server'), filePath)
    return {
      file: `apps/server/${relative}`,
      kind: classify(serverRules, relative),
      reason:
        'server tests require a use-case, controller, job, workflow, API-handler or documented domain/preparation/capability boundary',
    }
  })
}

function checkWeb() {
  const isTest = (name) => /\.(?:test|spec)\.tsx?$/.test(name)
  const sourceFiles = collect(webSource, isTest).map((filePath) => {
    const relative = relativePath(webSource, filePath)
    const inTestsDirectory = relative.split('/').slice(0, -1).includes('tests')
    return {
      file: `apps/web/src/${relative}`,
      kind: inTestsDirectory ? classify(webSourceRules, relative) : null,
      reason: inTestsDirectory
        ? 'web tests require an owning UI/API boundary or the documented server-request security contract'
        : 'web unit tests must live in a tests/ directory next to their owner',
    }
  })
  const browserFiles = collect(webTests, isTest).map((filePath) => {
    const relative = relativePath(webTests, filePath)
    return {
      file: `apps/web/tests/${relative}`,
      kind: classify(webBrowserRules, relative.split('/').at(-1)),
      reason:
        'browser tests must be named for a page, layout or API handler (*-page, *-layout, *-api, *-api-handler)',
    }
  })
  return [...sourceFiles, ...browserFiles]
}

const results = [...checkServer(), ...checkWeb()].sort((left, right) =>
  left.file.localeCompare(right.file),
)
const violations = results.filter((result) => result.kind === null)

if (process.argv.includes('--list')) {
  for (const result of results.filter((item) => item.kind !== null)) {
    console.log(`${result.kind.padEnd(11)} ${result.file}`)
  }
}

if (violations.length > 0) {
  console.error(
    `Test integrity failed: ${violations.length} test file(s) are not allowed.`,
  )
  for (const violation of violations) {
    console.error(`  ${violation.file}\n    ${violation.reason}`)
  }
  process.exit(1)
}

console.log(`Test integrity passed: ${results.length} test file(s) checked.`)
