import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const rootDirectory = path.resolve(scriptDirectory, '..')
const sourceDirectory = path.join(rootDirectory, 'documentation', 'agents')
const codexDirectory = path.join(rootDirectory, '.codex')
const codexAgentsDirectory = path.join(codexDirectory, 'agents')
const opencodeAgentsDirectory = path.join(rootDirectory, '.opencode', 'agents')
const claudeAgentsDirectory = path.join(rootDirectory, '.claude', 'agents')
const codexConfigPath = path.join(codexDirectory, 'config.toml')
const currentBeginMarker = '# BEGIN GENERATED AGENTS - scripts/sync-agents.mjs'
const currentEndMarker = '# END GENERATED AGENTS - scripts/sync-agents.mjs'
const legacyBeginMarker = '# BEGIN GENERATED AGENTS - scripts/sync-agents.sh'
const legacyEndMarker = '# END GENERATED AGENTS - scripts/sync-agents.sh'
const namePattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

function fail(message) {
  console.error(message)
  process.exit(1)
}

function relativePath(filePath) {
  return path.relative(rootDirectory, filePath).split(path.sep).join('/')
}

function parseFrontmatter(agentPath) {
  const relativeAgentPath = relativePath(agentPath)
  const lines = fs.readFileSync(agentPath, 'utf8').split(/\r?\n/)
  if (!lines.length || lines[0].trim() !== '---') {
    fail('Missing YAML frontmatter in ' + relativeAgentPath)
  }

  const frontmatterEnd = lines.findIndex(function findEnd(line, index) {
    return index > 0 && line.trim() === '---'
  })
  if (frontmatterEnd === -1) {
    fail('Unclosed YAML frontmatter in ' + relativeAgentPath)
  }

  const metadata = {}
  for (const line of lines.slice(1, frontmatterEnd)) {
    const separatorIndex = line.indexOf(':')
    if (separatorIndex === -1) continue
    const key = line.slice(0, separatorIndex).trim()
    let value = line.slice(separatorIndex + 1).trim()
    while (
      value.length >= 2 &&
      ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'")))
    ) {
      value = value.slice(1, -1)
    }
    metadata[key] = value
  }

  const name = metadata.name || ''
  const description = metadata.description || ''
  const expectedName = path.basename(agentPath, path.extname(agentPath))
  if (!name) fail('Missing name in ' + relativeAgentPath)
  if (!description) fail('Missing description in ' + relativeAgentPath)
  if (name !== expectedName) {
    fail(
      "Agent name '" +
        name +
        "' must match filename '" +
        expectedName +
        "' in " +
        relativeAgentPath,
    )
  }
  if (!namePattern.test(name)) {
    fail("Invalid agent name '" + name + "' in " + relativeAgentPath)
  }

  const body = lines.slice(frontmatterEnd + 1).join('\n').trim() + '\n'
  if (!body.trim()) fail('Missing agent instructions in ' + relativeAgentPath)
  return { name, description, body, source: agentPath }
}

function writeIfChanged(filePath, content, managedToken) {
  if (fs.existsSync(filePath)) {
    const existingContent = fs.readFileSync(filePath, 'utf8')
    if (existingContent === content) {
      console.log('unchanged: ' + relativePath(filePath))
      return
    }
    if (managedToken && !existingContent.includes(managedToken)) {
      fail('Refusing to overwrite unmanaged file: ' + relativePath(filePath))
    }
  }

  fs.mkdirSync(path.dirname(filePath), { recursive: true })
  fs.writeFileSync(filePath, content, 'utf8')
  console.log('synced:    ' + relativePath(filePath))
}

function cleanupStale(directory, suffix, validNames) {
  if (!fs.existsSync(directory)) return
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (!entry.isFile() || !entry.name.endsWith(suffix)) continue
    const filePath = path.join(directory, entry.name)
    const name = entry.name.slice(0, -suffix.length)
    if (validNames.has(name)) continue
    const sample = fs.readFileSync(filePath, 'utf8').slice(0, 2048)
    if (!sample.includes('Auto-generated from documentation/agents/')) continue
    fs.unlinkSync(filePath)
    console.log('removed:   ' + relativePath(filePath))
  }
}

function removeGeneratedBlock(config, beginMarker, endMarker) {
  const beginCount = config.split(beginMarker).length - 1
  const endCount = config.split(endMarker).length - 1
  if (beginCount !== endCount) {
    fail('Unbalanced generated-agent markers in ' + relativePath(codexConfigPath))
  }
  if (!beginCount) return config

  const beginIndex = config.indexOf(beginMarker)
  const endIndex = config.indexOf(endMarker, beginIndex + beginMarker.length)
  const before = config.slice(0, beginIndex).trimEnd()
  const after = config.slice(endIndex + endMarker.length).replace(/^\n+/, '')
  return before + after
}

if (!fs.existsSync(sourceDirectory)) {
  fail('Agent source directory not found: ' + sourceDirectory)
}

fs.mkdirSync(codexAgentsDirectory, { recursive: true })
fs.mkdirSync(opencodeAgentsDirectory, { recursive: true })
fs.mkdirSync(claudeAgentsDirectory, { recursive: true })

const agents = fs
  .readdirSync(sourceDirectory)
  .filter(function isAgent(fileName) {
    return fileName.endsWith('-agent.md')
  })
  .sort()
  .map(function parseAgent(fileName) {
    return parseFrontmatter(path.join(sourceDirectory, fileName))
  })

if (!agents.length) {
  fail('No agent definitions found in documentation/agents/*-agent.md')
}

const validNames = new Set(agents.map(function getName(agent) { return agent.name }))
cleanupStale(codexAgentsDirectory, '.toml', validNames)
cleanupStale(opencodeAgentsDirectory, '.md', validNames)
cleanupStale(claudeAgentsDirectory, '.md', validNames)

const codexRoles = [currentBeginMarker]
for (const agent of agents) {
  const sourceRelative = relativePath(agent.source)
  const sandboxMode =
    agent.name.startsWith('judge-') || agent.name.endsWith('-reviewer-agent')
      ? 'read-only'
      : 'workspace-write'
  const codexRole =
    '# Auto-generated from ' +
    sourceRelative +
    '\nmodel_instructions_file = ' +
    JSON.stringify('../../' + sourceRelative) +
    '\nsandbox_mode = ' +
    JSON.stringify(sandboxMode) +
    '\n'
  writeIfChanged(
    path.join(codexAgentsDirectory, agent.name + '.toml'),
    codexRole,
    'Auto-generated from documentation/agents/',
  )

  codexRoles.push(
    '',
    '[agents.' + JSON.stringify(agent.name) + ']',
    'description = ' + JSON.stringify(agent.description),
    'config_file = ' + JSON.stringify('agents/' + agent.name + '.toml'),
  )

  let opencodeMode = 'subagent'
  let opencodePermissions = '  edit: allow\n  bash: allow\n  task: allow'
  if (agent.name === 'orchestrator-agent') {
    opencodeMode = 'primary'
  } else if (agent.name.startsWith('judge-')) {
    opencodePermissions = '  edit: deny\n  bash: deny\n  task: deny'
  } else if (agent.name.endsWith('-reviewer-agent')) {
    opencodePermissions = '  edit: deny\n  bash: allow\n  task: deny'
  } else if (agent.name === 'builder-agent') {
    opencodePermissions = '  edit: allow\n  bash: allow\n  task: deny'
  }

  const opencodeAgent =
    '---\n' +
    'description: ' +
    JSON.stringify(agent.description) +
    '\nmode: ' +
    opencodeMode +
    '\npermission:\n' +
    opencodePermissions +
    '\n---\n\n' +
    '<!-- Auto-generated from ' +
    sourceRelative +
    ' -->\n\n' +
    agent.body
  writeIfChanged(
    path.join(opencodeAgentsDirectory, agent.name + '.md'),
    opencodeAgent,
    'Auto-generated from documentation/agents/',
  )

  const claudeFields = [
    '---',
    'name: ' + agent.name,
    'description: ' + JSON.stringify(agent.description),
  ]
  if (agent.name.startsWith('judge-')) {
    claudeFields.push('tools: Read, Glob, Grep', 'permissionMode: plan')
  } else if (agent.name.endsWith('-reviewer-agent')) {
    claudeFields.push('disallowedTools: Write, Edit, Agent')
  } else if (agent.name === 'builder-agent') {
    claudeFields.push('disallowedTools: Agent')
  }
  claudeFields.push(
    '---',
    '',
    '<!-- Auto-generated from ' + sourceRelative + ' -->',
    '',
    agent.body.trimEnd(),
    '',
  )
  writeIfChanged(
    path.join(claudeAgentsDirectory, agent.name + '.md'),
    claudeFields.join('\n'),
    'Auto-generated from documentation/agents/',
  )
}

codexRoles.push('', currentEndMarker)
let existingConfig = fs.existsSync(codexConfigPath)
  ? fs.readFileSync(codexConfigPath, 'utf8')
  : ''
existingConfig = removeGeneratedBlock(
  existingConfig,
  legacyBeginMarker,
  legacyEndMarker,
)
existingConfig = removeGeneratedBlock(
  existingConfig,
  currentBeginMarker,
  currentEndMarker,
)
let newConfig = existingConfig.trimEnd()
if (newConfig) newConfig += '\n\n'
newConfig += codexRoles.join('\n') + '\n'
writeIfChanged(codexConfigPath, newConfig, '')
console.log('Configured agents for Codex, OpenCode and Claude Code.')
