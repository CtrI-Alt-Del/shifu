import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const webDirectory = path.resolve(scriptDirectory, '..')
const repositoryDirectory = path.resolve(webDirectory, '../..')
const defaultReportPath = path.join(webDirectory, 'coverage', 'coverage-final.json')
const thresholds = {
  lines: 85,
  statements: 85,
  functions: 85,
  branches: 80,
} as const
const metricNames = Object.keys(thresholds) as (keyof typeof thresholds)[]

type MetricName = keyof typeof thresholds
type CoverageMetric = { total: number; covered: number }
type Arguments = { base?: string; files?: string[]; reportPath: string }
type LineRange = { start: number; end: number }
type CoverageLocation = { start: { line: number }; end: { line: number } }
type CoverageEntry = {
  statementMap?: Record<string, CoverageLocation>
  s?: Record<string, number>
  fnMap?: Record<
    string,
    { decl?: CoverageLocation; loc?: CoverageLocation; location?: CoverageLocation }
  >
  f?: Record<string, number>
  branchMap?: Record<string, { locations?: CoverageLocation[]; loc?: CoverageLocation }>
  b?: Record<string, number[]>
  l?: Record<string, number>
}

function fail(message: string): never {
  console.error(`Coverage check failed: ${message}`)
  process.exit(1)
}

function usage(): never {
  console.error(
    'Usage: node --experimental-strip-types apps/web/scripts/check-changed-coverage.ts (--base <git-ref> | --files <repo-path...>) [--report <path>]',
  )
  process.exit(2)
}

function parseArguments(arguments_: string[]): Arguments {
  let base: string | undefined
  let files: string[] | undefined
  let reportPath = defaultReportPath

  for (let index = 0; index < arguments_.length; index += 1) {
    const argument = arguments_[index]
    if (argument === '--base') {
      if (base !== undefined || files !== undefined || !arguments_[index + 1]) usage()
      base = arguments_[index + 1]
      index += 1
      continue
    }
    if (argument === '--files') {
      if (base !== undefined || files !== undefined) usage()
      files = []
      while (arguments_[index + 1] && !arguments_[index + 1].startsWith('--')) {
        files.push(arguments_[index + 1])
        index += 1
      }
      if (files.length === 0) usage()
      continue
    }
    if (argument === '--report') {
      if (!arguments_[index + 1]) usage()
      reportPath = path.resolve(process.cwd(), arguments_[index + 1])
      index += 1
      continue
    }
    usage()
  }

  if ((base === undefined) === (files === undefined)) usage()
  return { base, files, reportPath }
}

function changedFiles(base: string): string[] {
  try {
    return execFileSync(
      'git',
      ['diff', '--name-only', '--diff-filter=ACMR', `${base}...HEAD`],
      { cwd: repositoryDirectory, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] },
    )
      .split(/\r?\n/)
      .filter(Boolean)
  } catch (error: unknown) {
    const detail = error instanceof Error ? error.message : String(error)
    fail(
      `could not discover tracked changes from ${base}...HEAD${detail ? `: ${detail}` : ''}`,
    )
  }
}

function changedLineRanges(base: string | undefined, filePath: string): LineRange[] {
  if (base === undefined) {
    return [{ start: 1, end: Number.MAX_SAFE_INTEGER }]
  }

  try {
    return execFileSync(
      'git',
      [
        'diff',
        '--unified=0',
        '--no-color',
        '--diff-filter=ACMR',
        `${base}...HEAD`,
        '--',
        filePath,
      ],
      { cwd: repositoryDirectory, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] },
    )
      .split(/\r?\n/)
      .flatMap((line): LineRange[] => {
        const match = /^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@/.exec(line)
        if (!match) return []
        const start = Number(match[1])
        const count = Number(match[2] ?? 1)
        return count > 0 ? [{ start, end: start + count - 1 }] : []
      })
  } catch (error: unknown) {
    const detail = error instanceof Error ? error.message : String(error)
    fail(
      `could not discover changed lines from ${base}...HEAD for ${filePath}${detail ? `: ${detail}` : ''}`,
    )
  }
}

function repositoryPath(input: string): string | null {
  const normalizedInput = input.replaceAll('\\', '/')
  const absolutePath = path.isAbsolute(normalizedInput)
    ? path.resolve(normalizedInput)
    : normalizedInput.startsWith('apps/web/')
      ? path.resolve(repositoryDirectory, normalizedInput)
      : path.resolve(webDirectory, normalizedInput)
  const relative = path.relative(repositoryDirectory, absolutePath)
  if (
    relative === '..' ||
    relative.startsWith(`..${path.sep}`) ||
    path.isAbsolute(relative)
  ) {
    return null
  }
  return relative.split(path.sep).join('/')
}

function isEligibleProductionFile(input: string): boolean {
  const relativePath = repositoryPath(input)
  if (!relativePath || !/^apps\/web\/src\/.*\.(?:ts|tsx)$/.test(relativePath))
    return false

  const sourcePath = relativePath.slice('apps/web/'.length)
  return (
    !sourcePath.includes('/tests/') &&
    !/\.(?:test|spec)\.(?:ts|tsx)$/.test(sourcePath) &&
    sourcePath !== 'src/routeTree.gen.ts'
  )
}

function loadCoverageReport(reportPath: string): Map<string, CoverageEntry> {
  if (!existsSync(reportPath)) fail(`coverage summary does not exist: ${reportPath}`)

  let summary: Record<string, unknown>
  try {
    const parsed: unknown = JSON.parse(readFileSync(reportPath, 'utf8'))
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      fail('coverage summary root must be a per-file object')
    }
    summary = parsed as Record<string, unknown>
  } catch (error: unknown) {
    fail(
      `coverage summary is not valid JSON: ${error instanceof Error ? error.message : String(error)}`,
    )
  }

  const byRepositoryPath = new Map<string, CoverageEntry>()
  for (const [reportedPath, entry] of Object.entries(summary)) {
    if (reportedPath === 'total') continue
    const relativePath = repositoryPath(reportedPath)
    if (!relativePath) continue
    if (byRepositoryPath.has(relativePath)) {
      fail(`coverage summary contains more than one entry for ${relativePath}`)
    }
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
      fail(`${relativePath}: coverage entry must be an object`)
    }
    byRepositoryPath.set(relativePath, entry as CoverageEntry)
  }
  return byRepositoryPath
}

function overlaps(location: CoverageLocation | undefined, ranges: LineRange[]): boolean {
  if (!location) return false
  return ranges.some(
    (range) => location.start.line <= range.end && location.end.line >= range.start,
  )
}

function metricForChangedLines(
  entry: CoverageEntry,
  filePath: string,
  metricName: MetricName,
  ranges: LineRange[],
): CoverageMetric {
  if (metricName === 'lines') {
    if (!entry.statementMap || !entry.s) {
      fail(`${filePath}: line coverage data is missing`)
    }
    const lineCoverage = new Map<number, number>()
    for (const [id, location] of Object.entries(entry.statementMap)) {
      const line = location.start.line
      lineCoverage.set(line, Math.max(lineCoverage.get(line) ?? 0, entry.s[id] ?? 0))
    }
    const changedLines = [...lineCoverage].filter(([line]) =>
      ranges.some((range) => line >= range.start && line <= range.end),
    )
    return {
      total: changedLines.length,
      covered: changedLines.filter(([, count]) => count > 0).length,
    }
  }

  if (metricName === 'statements') {
    if (!entry.statementMap || !entry.s) {
      fail(`${filePath}: statement coverage data is missing`)
    }
    const changedStatements = Object.entries(entry.s).filter(([id]) =>
      overlaps(entry.statementMap?.[id], ranges),
    )
    return {
      total: changedStatements.length,
      covered: changedStatements.filter(([, count]) => count > 0).length,
    }
  }

  if (metricName === 'functions') {
    if (!entry.fnMap || !entry.f) fail(`${filePath}: function coverage data is missing`)
    const changedFunctions = Object.entries(entry.f).filter(([id]) =>
      overlaps(
        entry.fnMap?.[id]?.decl ?? entry.fnMap?.[id]?.loc ?? entry.fnMap?.[id]?.location,
        ranges,
      ),
    )
    return {
      total: changedFunctions.length,
      covered: changedFunctions.filter(([, count]) => count > 0).length,
    }
  }

  if (!entry.branchMap || !entry.b) fail(`${filePath}: branch coverage data is missing`)
  const changedBranches = Object.entries(entry.b).flatMap(([id, counts]) => {
    const locations = entry.branchMap?.[id]?.locations
    const location = entry.branchMap?.[id]?.loc
    return counts.map((count, index) => ({
      count,
      location: locations?.[index] ?? location,
    }))
  })
  const relevantBranches = changedBranches.filter(({ location }) =>
    overlaps(location, ranges),
  )
  return {
    total: relevantBranches.length,
    covered: relevantBranches.filter(({ count }) => count > 0).length,
  }
}

function metricResult(
  metricName: MetricName,
  metric: CoverageMetric,
): { passed: boolean; display: string } {
  const threshold = thresholds[metricName]
  const passed = metric.total === 0 || metric.covered * 100 >= metric.total * threshold
  const ratio =
    metric.total === 0
      ? 'no measured items'
      : `${((metric.covered / metric.total) * 100).toFixed(1)}%`
  return {
    passed,
    display: `${metricName} ${metric.covered}/${metric.total} (${ratio}; >=${threshold}%)`,
  }
}

function main() {
  const { base, files, reportPath } = parseArguments(process.argv.slice(2))
  const sourceInputs =
    files !== undefined ? files : base !== undefined ? changedFiles(base) : usage()
  const sourceFiles = sourceInputs
    .filter(isEligibleProductionFile)
    .map(repositoryPath)
    .filter((filePath): filePath is string => filePath !== null)
  const changed = [...new Set(sourceFiles)].sort()

  if (changed.length === 0) {
    console.log('No changed eligible production Web source files.')
    return
  }

  const coverage = loadCoverageReport(reportPath)
  let failedFiles = 0

  for (const filePath of changed) {
    const entry = coverage.get(filePath)
    if (!entry) {
      console.error(`FAIL ${filePath}: missing from coverage summary`)
      failedFiles += 1
      continue
    }

    const ranges = changedLineRanges(base, filePath)
    const results = metricNames.map((metricName) => {
      const metric = metricForChangedLines(entry, filePath, metricName, ranges)
      return metricResult(metricName, metric)
    })
    const passed = results.every((result) => result.passed)
    console.log(
      `${passed ? 'PASS' : 'FAIL'} ${filePath}: ${results.map((result) => result.display).join('; ')}`,
    )
    if (!passed) failedFiles += 1
  }

  if (failedFiles > 0) {
    fail(
      `${failedFiles} of ${changed.length} changed eligible file(s) missed a threshold or coverage entry`,
    )
  }
  console.log(
    `Passed coverage thresholds for changed executable items in ${changed.length} eligible Web source file(s).`,
  )
}

main()
