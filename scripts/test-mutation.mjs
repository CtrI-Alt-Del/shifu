import { execFileSync, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

export function parseArguments(args) {
  const options = { all: false, dryRun: false, base: undefined, files: [] }
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index]
    if (argument === '--') continue
    if (argument === '--all') options.all = true
    else if (argument === '--dry-run') options.dryRun = true
    else if (
      argument === '--base' &&
      args[index + 1] &&
      !args[index + 1].startsWith('--')
    )
      options.base = args[++index]
    else if (argument === '--files') {
      while (args[index + 1] && !args[index + 1].startsWith('--')) {
        options.files.push(args[++index])
      }
      if (!options.files.length)
        throw new Error('--files requires package-relative paths')
    } else throw new Error(`Unknown or incomplete argument: ${argument}`)
  }
  if (
    (options.all && (options.base || options.files.length)) ||
    (options.base && options.files.length)
  ) {
    throw new Error('Choose only one of --all, --base or --files')
  }
  return options
}

function git(root, args) {
  return execFileSync('git', ['-C', root, ...args], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim()
}

function nulPaths(output) {
  return output.split('\0').filter(Boolean)
}

export function isProductionFile(path, sourceRoot) {
  return (
    path.startsWith(`${sourceRoot}/`) &&
    /\.tsx?$/.test(path) &&
    !/(^|\/)(tests?|__tests__|fakers|fixtures)(\/|$)/.test(path) &&
    !/\.(test|spec|gen|d)\.[cm]?[jt]sx?$/.test(path) &&
    !/(^|\/)generated\//.test(path)
  )
}

export function selectMutationFiles(candidates, changed, sourceRoot) {
  const selected = new Set()
  for (const path of changed) {
    if (candidates.includes(path)) selected.add(path)
    const testBoundary = path.match(/^(.*?)\/(?:tests|__tests__)\//)
    if (testBoundary) {
      for (const candidate of candidates) {
        if (candidate.startsWith(`${testBoundary[1]}/`)) selected.add(candidate)
      }
    }
    if (
      /^(vitest\.config\.|stryker\.config\.|tsconfig|package\.json|tests\/setup)/.test(
        path,
      )
    ) {
      throw new Error(
        'Shared test/configuration changes require explicit --files; CI uses --all',
      )
    }
  }
  return [...selected].filter((path) => isProductionFile(path, sourceRoot)).sort()
}

function defaultBase(root) {
  const branch = git(root, ['branch', '--show-current'])
  if (branch === 'main') return 'HEAD'
  for (const reference of ['origin/main', 'main']) {
    try {
      return git(root, ['merge-base', 'HEAD', reference])
    } catch {
      // A clone may have only one local branch; HEAD still includes working changes.
    }
  }
  throw new Error('No main reference available; supply --base explicitly')
}

export async function runMutation(args, cwd = process.cwd()) {
  const options = parseArguments(args)
  const root = git(cwd, ['rev-parse', '--show-toplevel'])
  const packagePath = relative(root, cwd).split(sep).join('/')
  const sourceRoot = { 'apps/web': 'src' }[packagePath]
  if (!sourceRoot) throw new Error('Run test:mutation from apps/web')
  const prefix = `${packagePath}/`
  const tracked = nulPaths(
    git(root, [
      'ls-files',
      '-z',
      '--cached',
      '--others',
      '--exclude-standard',
      '--',
      packagePath,
    ]),
  )
  const candidates = [...new Set(tracked)]
    .map((path) => path.slice(prefix.length))
    .filter(
      (path) => isProductionFile(path, sourceRoot) && existsSync(resolve(cwd, path)),
    )
  let selected
  if (options.all) selected = candidates
  else if (options.files.length) {
    selected = options.files.map((path) =>
      relative(cwd, resolve(cwd, path)).split(sep).join('/'),
    )
    for (const path of selected) {
      if (!candidates.includes(path) || /[*?{}[\],!]/.test(path)) {
        throw new Error(`Not an eligible production file: ${path}`)
      }
    }
  } else {
    const base = git(root, [
      'rev-parse',
      '--verify',
      '--end-of-options',
      `${options.base ?? defaultBase(root)}^{commit}`,
    ])
    const changed = nulPaths(git(root, ['diff', '--name-only', '-z', base, '--']))
    changed.push(
      ...nulPaths(git(root, ['ls-files', '--others', '--exclude-standard', '-z'])),
    )
    const local = changed
      .filter((path) => path.startsWith(prefix))
      .map((path) => path.slice(prefix.length))
    // Workspace dependency and compiler changes can affect every source file in this package.
    if (
      changed.some((path) =>
        ['pnpm-lock.yaml', 'pnpm-workspace.yaml', 'package.json'].includes(path),
      )
    ) {
      local.push('package.json')
    }
    selected = selectMutationFiles(candidates, local, sourceRoot)
  }
  if (!selected.length) {
    console.log(
      'Mutation testing not applicable: no affected production files. Use --files for an explicit scope.',
    )
    return 0
  }
  console.log(
    `Mutation scope (${options.all ? 'full' : 'scoped'}): ${selected.join(', ')}`,
  )
  for (const path of selected) {
    if (/[*?{}[\],!]/.test(path))
      throw new Error(`Unsupported glob characters in path: ${path}`)
  }
  if (options.dryRun) return 0
  const result = spawnSync(
    process.execPath,
    [
      resolve(cwd, 'node_modules/@stryker-mutator/core/bin/stryker.js'),
      'run',
      'stryker.config.mjs',
      '--mutate',
      selected.join(','),
    ],
    { cwd, stdio: 'inherit' },
  )
  if (result.error) throw result.error
  return result.status ?? 1
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    process.exitCode = await runMutation(process.argv.slice(2))
  } catch (error) {
    console.error(error.message)
    process.exitCode = 1
  }
}
