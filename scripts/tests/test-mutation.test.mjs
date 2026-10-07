import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  isProductionFile,
  parseArguments,
  selectMutationFiles,
} from '../test-mutation.mjs'

test('requires an explicit, unambiguous full-suite request', () => {
  assert.deepEqual(parseArguments([]), {
    all: false,
    dryRun: false,
    base: undefined,
    files: [],
  })
  assert.equal(parseArguments(['--all']).all, true)
  for (const args of [
    ['--all', '--base', 'main'],
    ['--files'],
    ['--base'],
    ['--unknown'],
  ]) {
    assert.throws(() => parseArguments(args))
  }
})

test('excludes generated files, declarations and test support', () => {
  for (const path of [
    'src/routeTree.gen.ts',
    'src/types.d.ts',
    'src/a/tests/a.test.ts',
    'src/a/fakers/a.ts',
  ]) {
    assert.equal(isProductionFile(path, 'src'), false)
  }
  assert.equal(isProductionFile('src/a/use-a.ts', 'src'), true)
})

test('test edits select only the owning production boundary', () => {
  const candidates = ['src/a/use-a.ts', 'src/a/view.tsx', 'src/b/view.tsx']
  assert.deepEqual(
    selectMutationFiles(candidates, ['src/a/tests/view.test.tsx'], 'src'),
    candidates.slice(0, 2),
  )
  assert.deepEqual(selectMutationFiles(candidates, ['README.md'], 'src'), [])
  assert.deepEqual(
    selectMutationFiles(candidates, ['src/b/view.tsx'], 'src'),
    candidates.slice(2),
  )
})

test('shared test setup requires explicit scope', () => {
  const candidates = ['src/a.ts', 'src/b.ts']
  assert.throws(
    () => selectMutationFiles(candidates, ['tests/setup.ts'], 'src'),
    /explicit --files/,
  )
})

test('Git discovery includes committed branch, staged, unstaged and untracked source changes', async () => {
  const { execFileSync } = await import('node:child_process')
  const { mkdtempSync, mkdirSync, writeFileSync, rmSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const { runMutation } = await import('../test-mutation.mjs')
  const root = mkdtempSync(join(tmpdir(), 'shifu-mutation-selector-'))
  const cwd = join(root, 'apps/web')
  function git(...args) {
    execFileSync('git', ['-C', root, ...args], { stdio: 'pipe' })
  }
  function write(name, value = 'export const value = 1') {
    writeFileSync(join(cwd, 'src', name), value)
  }
  const messages = []
  const originalLog = console.log
  try {
    mkdirSync(join(cwd, 'src'), { recursive: true })
    git('init', '-b', 'main')
    git('config', 'user.name', 'Selector test')
    git('config', 'user.email', 'selector@example.invalid')
    for (const name of ['branch.ts', 'staged.ts', 'dirty.ts', 'untouched.ts']) write(name)
    git('add', '.')
    git('commit', '-m', 'baseline')
    git('switch', '-c', 'codex/selection')
    write('branch.ts', 'export const value = 2')
    git('add', '.')
    git('commit', '-m', 'branch change')
    write('staged.ts', 'export const value = 2')
    git('add', '.')
    write('dirty.ts', 'export const value = 2')
    write('untracked.ts')
    console.log = (message) => messages.push(message)
    assert.equal(await runMutation(['--dry-run'], cwd), 0)
    assert.match(
      messages.at(-1),
      /src\/branch.ts, src\/dirty.ts, src\/staged.ts, src\/untracked.ts/,
    )
    assert.doesNotMatch(messages.at(-1), /untouched/)
    await assert.rejects(
      runMutation(['--files', '../../escape.ts', '--dry-run'], cwd),
      /eligible production/,
    )
    await assert.rejects(
      runMutation(['--base', '--output=escape', '--dry-run'], cwd),
      /argument/,
    )
    assert.equal(await runMutation(['--all', '--dry-run'], cwd), 0)
    assert.match(messages.at(-1), /untouched/)
  } finally {
    console.log = originalLog
    rmSync(root, { recursive: true, force: true })
  }
})
