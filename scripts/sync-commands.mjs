import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const rootDirectory = path.resolve(scriptDirectory, '..')
const promptsDirectory = path.join(rootDirectory, 'documentation', 'prompts')
const outputDirectories = [
  path.join(rootDirectory, '.cursor', 'commands'),
  path.join(rootDirectory, '.claude', 'commands'),
  path.join(rootDirectory, '.opencode', 'commands'),
]
const skillsDirectory = path.join(rootDirectory, '.agents', 'skills')
const generatedPromptPattern =
  /^<!-- Auto-generated from (documentation\/prompts\/[^ ]+)( \(symlink not available\))? -->$/m

function fail(message) {
  console.error(message)
  process.exit(1)
}

function relativePath(filePath) {
  return path.relative(rootDirectory, filePath).split(path.sep).join('/')
}

function readGeneratedPromptSource(filePath) {
  let content
  try {
    content = fs.readFileSync(filePath, 'utf8')
  } catch {
    return null
  }
  return content.match(generatedPromptPattern)?.[1] || null
}

function removeIfGenerated(filePath, source, reason) {
  fs.rmSync(filePath, { force: true })
  console.log('removed: ' + relativePath(filePath) + ' (' + reason + ': ' + source + ')')
}

function cleanupStaleGeneratedArtifacts() {
  for (const directory of outputDirectories) {
    if (!fs.existsSync(directory)) continue
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (!entry.name.endsWith('.md')) continue
      const destination = path.join(directory, entry.name)
      if (entry.isSymbolicLink()) {
        const source = fs.readlinkSync(destination)
        if (
          /^\.\.\/\.\.\/documentation\/prompts\/[^/]+\.md$/.test(source) &&
          !fs.existsSync(destination)
        ) {
          removeIfGenerated(destination, source, 'missing source')
        }
        continue
      }
      if (!entry.isFile()) continue
      const source = readGeneratedPromptSource(destination)
      if (source && !fs.existsSync(path.join(rootDirectory, source))) {
        removeIfGenerated(destination, source, 'missing source')
      }
    }
  }

  if (!fs.existsSync(skillsDirectory)) return
  for (const entry of fs.readdirSync(skillsDirectory, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue
    const skillDirectory = path.join(skillsDirectory, entry.name)
    const skillFile = path.join(skillDirectory, 'SKILL.md')
    if (!fs.existsSync(skillFile)) continue
    const source = readGeneratedPromptSource(skillFile)
    if (!source || fs.existsSync(path.join(rootDirectory, source))) continue
    fs.rmSync(skillFile, { force: true })
    try {
      fs.rmdirSync(skillDirectory)
    } catch {}
    console.log('removed: ' + relativePath(skillDirectory) + ' (missing source)')
  }
}

function linkOrCopy(source, destination) {
  const relativeSource = '../../' + relativePath(source)
  fs.rmSync(destination, { force: true })
  try {
    fs.symlinkSync(relativeSource, destination)
    console.log('linked:  ' + relativePath(destination) + ' -> ' + relativeSource)
  } catch {
    const content =
      '<!-- Auto-generated from ' +
      relativePath(source) +
      ' (symlink not available) -->\n\n' +
      fs.readFileSync(source, 'utf8')
    fs.writeFileSync(destination, content, 'utf8')
    console.log('copied:  ' + relativePath(destination) + ' <- ' + relativePath(source))
  }
}

function extractDescription(source) {
  const content = fs.readFileSync(source, 'utf8')
  const description = content.match(/^description:\s*(.*)$/m)?.[1] || ''
  if (!description) {
    fail("Missing description in '" + relativePath(source) + "'")
  }
  return description
}

function syncSkill(source, name, description) {
  const skillDirectory = path.join(skillsDirectory, name)
  const skillFile = path.join(skillDirectory, 'SKILL.md')
  fs.mkdirSync(skillDirectory, { recursive: true })
  const content =
    '---\n' +
    'name: ' +
    name +
    '\n' +
    'description: ' +
    description +
    '\n---\n\n' +
    '<!-- Auto-generated from ' +
    relativePath(source) +
    ' -->\n\n' +
    fs.readFileSync(source, 'utf8')
  fs.writeFileSync(skillFile, content, 'utf8')
  console.log('synced:  ' + relativePath(skillFile) + ' <- ' + relativePath(source))
}

if (!fs.existsSync(promptsDirectory)) {
  fail('Prompts directory not found: ' + promptsDirectory)
}

const prompts = fs
  .readdirSync(promptsDirectory)
  .filter(function isPrompt(fileName) {
    return fileName.endsWith('.md') && fileName !== 'README.md'
  })
  .sort()
  .map(function resolvePrompt(fileName) {
    return path.join(promptsDirectory, fileName)
  })
if (!prompts.length) {
  fail("No prompts found in 'documentation/prompts/*.md'")
}

for (const directory of outputDirectories) {
  fs.mkdirSync(directory, { recursive: true })
}
fs.mkdirSync(skillsDirectory, { recursive: true })
cleanupStaleGeneratedArtifacts()

for (const source of prompts) {
  const filename = path.basename(source)
  let name = filename.slice(0, -path.extname(filename).length)
  if (name.endsWith('-prompt')) name = name.slice(0, -'-prompt'.length)
  const description = extractDescription(source)
  for (const directory of outputDirectories) {
    linkOrCopy(source, path.join(directory, name + '.md'))
  }
  syncSkill(source, name, description)
}
