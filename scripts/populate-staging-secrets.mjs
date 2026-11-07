#!/usr/bin/env node
// Fill the two staging secrets in AWS Secrets Manager (shifu-staging/web and
// shifu-staging/server), and turn on Redis AUTH. See iac/README.md, step 4.
//
// Run it once, from a machine with the `shifu` AWS profile and the AWS CLI. It asks
// for the Inngest and Resend values, generates the rest, and removes its temporary
// files when it ends. No value is printed.
//
// It refuses to run when a secret already has a value, because new random values
// would replace BETTER_AUTH_SECRET, which must stay stable once Better Auth has used
// it. Pass --force only when you mean to replace every value.
import { execFileSync } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import readline from 'node:readline'
import { Writable } from 'node:stream'

const REGION = 'us-east-2'
const PROFILE = process.env.AWS_PROFILE || 'shifu'
const DB_INSTANCE = 'shifu-staging'
const REDIS_GROUP = 'shifu-staging'
const WEB_SECRET_ID = 'shifu-staging/web'
const SERVER_SECRET_ID = 'shifu-staging/server'
const DATABASE_NAME = 'shifu'
const AGENTOS_ROLE = 'shifu_agentos_runtime'

function fail(message) {
  console.error(message)
  process.exit(1)
}

function aws(args) {
  try {
    return execFileSync('aws', args, {
      encoding: 'utf8',
      env: { ...process.env, AWS_PROFILE: PROFILE, AWS_REGION: REGION },
      stdio: ['ignore', 'pipe', 'pipe'],
    }).trim()
  } catch (error) {
    // The message names the failed command, and the AWS CLI error follows. Neither
    // holds a secret value, because values are passed through files.
    const detail = String(error.stderr || error.message).trim()
    const subcommand = args.slice(0, 2).join(' ')
    return fail(`aws ${subcommand} failed:\n${detail}`)
  }
}

function awsJson(args) {
  return JSON.parse(aws([...args, '--output', 'json']))
}

function createPrompter() {
  let muted = false
  const output = new Writable({
    write(chunk, _encoding, callback) {
      if (!muted) process.stdout.write(chunk)
      callback()
    },
  })
  const rl = readline.createInterface({
    input: process.stdin,
    output,
    terminal: Boolean(process.stdin.isTTY),
  })

  // A line iterator also works when the answers are piped in, where the input ends
  // before the later questions are asked.
  const lines = rl[Symbol.asyncIterator]()

  async function ask(question, { hidden = false } = {}) {
    process.stdout.write(question)
    muted = hidden
    const { value, done } = await lines.next()
    muted = false
    if (hidden) process.stdout.write('\n')
    if (done) fail('The input ended before every value was given.')
    return value.trim()
  }

  return { ask, close: () => rl.close() }
}

async function askRequired(prompter, question, options) {
  const answer = await prompter.ask(question, options)
  if (!answer) fail(`${question.trim()} cannot be empty.`)
  return answer
}

function encode(value) {
  return encodeURIComponent(value).replace(
    /[!'()*]/g,
    (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`,
  )
}

function secretHasValue(secretId) {
  const description = awsJson([
    'secretsmanager',
    'describe-secret',
    '--secret-id',
    secretId,
  ])
  return Object.keys(description.VersionIdsToStages ?? {}).length > 0
}

function storeSecret(secretId, directory, name, values) {
  const filePath = path.join(directory, `${name}.json`)
  fs.writeFileSync(filePath, JSON.stringify(values), { mode: 0o600 })
  const versionId = aws([
    'secretsmanager',
    'put-secret-value',
    '--secret-id',
    secretId,
    '--secret-string',
    `file://${filePath}`,
    '--query',
    'VersionId',
    '--output',
    'text',
  ])
  console.log(`${secretId}: stored version ${versionId}`)
}

async function main() {
  const force = process.argv.includes('--force')

  if (!force) {
    const filled = [WEB_SECRET_ID, SERVER_SECRET_ID].filter(secretHasValue)
    if (filled.length > 0) {
      fail(
        `${filled.join(' and ')} already has a value. Stop here unless you mean to replace ` +
          'every value, including BETTER_AUTH_SECRET. Run again with --force to replace them.',
      )
    }
  }

  const prompter = createPrompter()
  const inngestEventKey = await askRequired(prompter, 'Inngest event key: ', {
    hidden: true,
  })
  const inngestSigningKey = await askRequired(prompter, 'Inngest signing key: ', {
    hidden: true,
  })
  const resendApiKey = await askRequired(prompter, 'Resend API key: ', { hidden: true })
  const resendFrom = await askRequired(prompter, 'Resend sender address: ')
  prompter.close()

  const generated = {
    betterAuthSecret: randomBytes(48).toString('base64'),
    bffSecret: randomBytes(32).toString('hex'),
    hmacKey: randomBytes(32).toString('hex'),
    agentosPassword: randomBytes(24).toString('hex'),
    redisToken: randomBytes(32).toString('hex'),
    // URL-safe base64 with padding, the format the server decodes.
    communicationKey: randomBytes(32)
      .toString('base64')
      .replace(/\+/g, '-')
      .replace(/\//g, '_'),
  }

  const dbInstance = awsJson([
    'rds',
    'describe-db-instances',
    '--db-instance-identifier',
    DB_INSTANCE,
  ]).DBInstances[0]
  const rdsHost = dbInstance.Endpoint.Address
  const masterSecretArn = dbInstance.MasterUserSecret?.SecretArn
  if (!masterSecretArn) fail('The RDS instance has no AWS-managed master secret.')

  const redisHost = awsJson([
    'elasticache',
    'describe-replication-groups',
    '--replication-group-id',
    REDIS_GROUP,
  ]).ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint.Address

  const master = JSON.parse(
    aws([
      'secretsmanager',
      'get-secret-value',
      '--secret-id',
      masterSecretArn,
      '--query',
      'SecretString',
      '--output',
      'text',
    ]),
  )

  // Everything above only reads or generates. The next call is the first change.
  // A cache with no AUTH token accepts SET only after a ROTATE added the token, so
  // the same token goes through both steps. ROTATE adds it, SET makes it required.
  for (const strategy of ['ROTATE', 'SET']) {
    aws([
      'elasticache',
      'modify-replication-group',
      '--replication-group-id',
      REDIS_GROUP,
      '--auth-token',
      generated.redisToken,
      '--auth-token-update-strategy',
      strategy,
      '--apply-immediately',
    ])
    aws([
      'elasticache',
      'wait',
      'replication-group-available',
      '--replication-group-id',
      REDIS_GROUP,
    ])
  }
  console.log('Redis AUTH is on.')

  const adminLogin = `${encode(master.username)}:${encode(master.password)}`
  const webValues = {
    BETTER_AUTH_DATABASE_URL: `postgresql://${adminLogin}@${rdsHost}:5432/${DATABASE_NAME}?sslmode=no-verify`,
    BETTER_AUTH_SECRET: generated.betterAuthSecret,
    SHIFU_BFF_SHARED_SECRET: generated.bffSecret,
  }
  const serverValues = {
    DATABASE_URL: `postgresql+psycopg://${adminLogin}@${rdsHost}:5432/${DATABASE_NAME}?sslmode=require`,
    AGENTOS_DATABASE_URL: `postgresql+psycopg://${AGENTOS_ROLE}:${encode(generated.agentosPassword)}@${rdsHost}:5432/${DATABASE_NAME}?sslmode=require`,
    REDIS_URL: `rediss://:${encode(generated.redisToken)}@${redisHost}:6379/0`,
    INNGEST_EVENT_KEY: inngestEventKey,
    INNGEST_SIGNING_KEY: inngestSigningKey,
    SHIFU_RESEND_API_KEY: resendApiKey,
    SHIFU_RESEND_FROM: resendFrom,
    SHIFU_BFF_SHARED_SECRET: generated.bffSecret,
    SHIFU_COMMUNICATION_ENCRYPTION_KEYS: generated.communicationKey,
    DIAGNOSTIC_REVISION_HMAC_KEY: generated.hmacKey,
  }

  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'shifu-secrets-'))
  fs.chmodSync(directory, 0o700)
  try {
    storeSecret(WEB_SECRET_ID, directory, 'web', webValues)
    storeSecret(SERVER_SECRET_ID, directory, 'server', serverValues)
  } finally {
    fs.rmSync(directory, { recursive: true, force: true })
  }

  console.log('Done. The temporary files are removed.')
}

await main()
