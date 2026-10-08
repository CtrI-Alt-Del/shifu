import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { extname, isAbsolute, resolve } from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const WEB_ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)))
const REPOSITORY_ROOT = resolve(WEB_ROOT, '../..')
const COVERAGE_PATH = resolve(WEB_ROOT, 'coverage/coverage-final.json')
const SOURCE_PREFIX = 'apps/web/src/'
const MINIMUMS = { statements: 85, functions: 85, branches: 80, lines: 85 }

function parseArguments(args) {
  const options = {
    base: 'origin/main',
    reportOnly: false,
    selectors: [],
  }

  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index]
    if (argument === '--base') {
      options.base = args[++index]
      if (!options.base) throw new Error('--base requires a Git commit or ref')
    } else if (argument === '--report-only') {
      options.reportOnly = true
    } else if (argument === '--') {
      options.selectors.push(...args.slice(index + 1))
      break
    } else if (argument.startsWith('-')) {
      throw new Error(`Unknown option: ${argument}`)
    } else {
      options.selectors.push(argument)
    }
  }

  if (options.reportOnly && options.selectors.length > 0) {
    throw new Error('--report-only cannot be combined with test selectors')
  }
  return options
}

function runGit(args, allowFailure = false) {
  const result = spawnSync('git', args, {
    cwd: REPOSITORY_ROOT,
    encoding: 'utf8',
  })
  if (result.error) throw result.error
  if (result.status !== 0 && !allowFailure) {
    throw new Error(result.stderr.trim() || `git ${args.join(' ')} failed`)
  }
  return result.stdout
}

function isProductionSource(path) {
  if (!path.startsWith(SOURCE_PREFIX)) return false
  if (!['.ts', '.tsx'].includes(extname(path))) return false
  if (path.endsWith('.d.ts') || path === `${SOURCE_PREFIX}routeTree.gen.ts`) {
    return false
  }
  if (path.includes('/tests/') || /\.(test|spec)\.tsx?$/.test(path)) return false
  return true
}

function parseChangedFiles(diff) {
  const files = new Map()
  for (const section of diff.split(/^diff --git /m).slice(1)) {
    const path = section.match(/^\+\+\+ b\/(.+)$/m)?.[1]
    if (!path || !isProductionSource(path)) continue

    const lines = files.get(path) ?? new Set()
    for (const match of section.matchAll(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@/gm)) {
      const start = Number(match[1])
      const count = match[2] === undefined ? 1 : Number(match[2])
      for (let line = start; line < start + count; line += 1) lines.add(line)
    }
    if (lines.size > 0) files.set(path, lines)
  }
  return files
}

function findChangedFiles(base) {
  if (!runGit(['rev-parse', '--verify', `${base}^{commit}`], true).trim()) {
    throw new Error(`Git base '${base}' was not found; pass --base with a fetched commit`)
  }

  const files = parseChangedFiles(
    runGit([
      'diff',
      '--no-ext-diff',
      '--no-color',
      '--unified=0',
      base,
      '--',
      'apps/web/src',
    ]),
  )
  const untracked = runGit([
    'ls-files',
    '--others',
    '--exclude-standard',
    '--',
    'apps/web/src',
  ])
  for (const path of untracked.split('\n').filter(isProductionSource)) {
    const lines = readFileSync(resolve(REPOSITORY_ROOT, path), 'utf8').split('\n')
    files.set(path, new Set(lines.map((_, index) => index + 1)))
  }
  return files
}

function overlapsChangedLines(location, changedLines) {
  const start = location?.start?.line
  if (!start) return false
  const end = location.end?.line ?? start
  for (let line = start; line <= end; line += 1) {
    if (changedLines.has(line)) return true
  }
  return false
}

function measureLocations(locations, counts, changedLines) {
  let covered = 0
  let total = 0
  for (const [key, location] of Object.entries(locations ?? {})) {
    if (!overlapsChangedLines(location, changedLines)) continue
    total += 1
    if ((counts[key] ?? 0) > 0) covered += 1
  }
  return { covered, total }
}

function measureBranches(branchMap, counts, changedLines) {
  let covered = 0
  let total = 0
  for (const [key, branch] of Object.entries(branchMap ?? {})) {
    const locations = branch.locations?.length
      ? branch.locations
      : [{ start: { line: branch.line }, end: { line: branch.line } }]
    if (
      !changedLines.has(branch.line) &&
      !overlapsChangedLines(branch.loc, changedLines) &&
      !locations.some((location) => overlapsChangedLines(location, changedLines))
    ) {
      continue
    }
    for (let index = 0; index < locations.length; index += 1) {
      total += 1
      if ((counts[key]?.[index] ?? 0) > 0) covered += 1
    }
  }
  return { covered, total }
}

function measureLines(statementMap, counts, changedLines) {
  const executableLines = new Map()
  for (const [key, location] of Object.entries(statementMap ?? {})) {
    for (
      let line = location.start.line;
      line <= (location.end?.line ?? location.start.line);
      line += 1
    ) {
      if (!changedLines.has(line)) continue
      executableLines.set(
        line,
        Math.max(executableLines.get(line) ?? 0, counts[key] ?? 0),
      )
    }
  }
  return {
    covered: [...executableLines.values()].filter((count) => count > 0).length,
    total: executableLines.size,
  }
}

function resolveCoverageEntry(coverage, path) {
  const absolutePath = resolve(REPOSITORY_ROOT, path)
  return Object.entries(coverage).find(([key, entry]) =>
    [key, entry.path].filter(Boolean).some((candidate) => {
      const paths = isAbsolute(candidate)
        ? [resolve(candidate)]
        : [resolve(WEB_ROOT, candidate), resolve(REPOSITORY_ROOT, candidate)]
      return paths.includes(absolutePath)
    }),
  )?.[1]
}

function checkCoverage(files) {
  if (!existsSync(COVERAGE_PATH)) {
    throw new Error(`Coverage report missing: ${COVERAGE_PATH}`)
  }
  const coverage = JSON.parse(readFileSync(COVERAGE_PATH, 'utf8'))
  let passed = true

  for (const [path, changedLines] of files) {
    console.log(`\n${path}`)
    const entry = resolveCoverageEntry(coverage, path)
    if (!entry) {
      console.error('  FAIL: changed source file is missing from the coverage report')
      passed = false
      continue
    }

    const results = {
      statements: measureLocations(entry.statementMap, entry.s ?? {}, changedLines),
      functions: measureLocations(
        Object.fromEntries(
          Object.entries(entry.fnMap ?? {}).map(([key, value]) => [
            key,
            value.loc ?? value,
          ]),
        ),
        entry.f ?? {},
        changedLines,
      ),
      branches: measureBranches(entry.branchMap, entry.b ?? {}, changedLines),
      lines: measureLines(entry.statementMap, entry.s ?? {}, changedLines),
    }
    for (const [name, result] of Object.entries(results)) {
      if (result.total === 0) {
        console.log(`  ${name}: n/a (no changed executable locations)`)
        continue
      }
      const percentage = (result.covered / result.total) * 100
      const metThreshold = percentage + Number.EPSILON >= MINIMUMS[name]
      console.log(
        `  ${name}: ${metThreshold ? 'PASS' : 'FAIL'} ${result.covered}/${result.total} ` +
          `(${percentage.toFixed(2)}%; minimum ${MINIMUMS[name]}%)`,
      )
      if (!metThreshold) passed = false
    }
  }

  console.log(`\nChanged-code coverage ${passed ? 'passed' : 'failed'}.`)
  return passed
}

function runCoverage(files, selectors) {
  const args =
    selectors.length > 0
      ? ['exec', 'vitest', 'run', '--coverage', ...selectors]
      : [
          'exec',
          'vitest',
          'related',
          ...[...files.keys()].map((path) => path.slice('apps/web/'.length)),
          '--run',
          '--coverage',
        ]
  const result = spawnSync('pnpm', args, { cwd: WEB_ROOT, stdio: 'inherit' })
  if (result.error) throw result.error
  if (result.status !== 0)
    throw new Error(`Vitest coverage failed with exit code ${result.status}`)
}

try {
  const options = parseArguments(process.argv.slice(2))
  const files = findChangedFiles(options.base)
  if (files.size === 0) {
    console.log('Changed-code coverage: no Web production source changes.')
  } else {
    if (!options.reportOnly) runCoverage(files, options.selectors)
    if (!checkCoverage(files)) process.exitCode = 1
  }
} catch (error) {
  console.error(error.message)
  process.exitCode = 1
}
