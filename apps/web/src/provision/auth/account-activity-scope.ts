import { AsyncLocalStorage } from 'node:async_hooks'
import { createHash } from 'node:crypto'
import { AppError } from '@/core/errors/app-error'
import type { Pool, PoolClient } from 'pg'

const ACTIVITY_LOCK_TIMEOUT = '5s'
const ACTIVITY_LOCK_KEY_PREFIX = 'shifu:account-activity:v1:'

type ActiveAccountActivity = {
  accountId: string
  client: PoolClient
  isInvalid: boolean
}

export class AccountActivityScope {
  private readonly activeActivity = new AsyncLocalStorage<ActiveAccountActivity>()

  constructor(private readonly activityPool: Pool) {}

  async withSharedActivity<Result>(
    accountId: string,
    action: () => Promise<Result>,
  ): Promise<Result> {
    const activeActivity = this.activeActivity.getStore()
    if (activeActivity) {
      if (activeActivity.accountId !== accountId || activeActivity.isInvalid) {
        throw new AppError('Não foi possível validar o acesso agora. Tente novamente.')
      }
      return action()
    }

    const lockKey = getActivityLockKey(accountId)
    let client: PoolClient
    try {
      client = await this.activityPool.connect()
    } catch {
      throw new AppError('Não foi possível validar o acesso agora. Tente novamente.')
    }
    const activity: ActiveAccountActivity = { accountId, client, isInvalid: false }
    let hasLock = false
    let releaseError: Error | undefined

    try {
      await client.query("SELECT set_config('lock_timeout', $1, false)", [
        ACTIVITY_LOCK_TIMEOUT,
      ])
      await client.query('SELECT pg_advisory_lock_shared($1::bigint)', [lockKey])
      hasLock = true
      return await this.activeActivity.run(activity, action)
    } catch (error) {
      if (isLockTimeout(error)) {
        throw new AppError('Não foi possível validar o acesso agora. Tente novamente.')
      }
      if (activity.isInvalid) releaseError = toError(error)
      throw error
    } finally {
      if (hasLock && !activity.isInvalid) {
        try {
          const result = await client.query(
            'SELECT pg_advisory_unlock_shared($1::bigint) AS unlocked',
            [lockKey],
          )
          if (result.rows[0]?.unlocked !== true) {
            activity.isInvalid = true
            releaseError = new Error('Account activity lock was not held.')
          }
        } catch (error) {
          activity.isInvalid = true
          releaseError = toError(error)
        }
      }

      if (!activity.isInvalid) {
        try {
          await client.query("SELECT set_config('lock_timeout', '0', false)")
        } catch (error) {
          activity.isInvalid = true
          releaseError = toError(error)
        }
      }

      if (activity.isInvalid && !releaseError) {
        releaseError = new Error('Account activity connection is invalid.')
      }

      client.release(releaseError)
    }
  }

  createPinnedAuthPool(authPool: Pool): Pool {
    return new Proxy(authPool, {
      get: (target, property, receiver) => {
        if (property === 'query') {
          return (...args: unknown[]) => {
            const activity = this.activeActivity.getStore()
            const query = activity
              ? (activity.client.query.bind(activity.client) as (
                  ...values: unknown[]
                ) => unknown)
              : (target.query.bind(target) as (...values: unknown[]) => unknown)

            if (activity?.isInvalid) {
              throw new AppError(
                'Não foi possível validar o acesso agora. Tente novamente.',
              )
            }
            return activity ? runTrackedQuery(activity, query, args) : query(...args)
          }
        }

        if (property === 'connect') {
          return (...args: unknown[]) => {
            const activity = this.activeActivity.getStore()
            if (!activity) {
              const connect = target.connect.bind(target) as (
                ...values: unknown[]
              ) => unknown
              return connect(...args)
            }
            if (activity.isInvalid) {
              throw new AppError(
                'Não foi possível validar o acesso agora. Tente novamente.',
              )
            }

            const client = createBorrowedClient(activity)
            const callback = args[0]
            if (typeof callback === 'function') {
              queueMicrotask(() => {
                callback(null, client, (error?: Error | boolean) => {
                  if (error) activity.isInvalid = true
                })
              })
              return undefined
            }
            return Promise.resolve(client)
          }
        }

        const value = Reflect.get(target, property, receiver) as unknown
        return typeof value === 'function' ? value.bind(target) : value
      },
    })
  }
}

function getActivityLockKey(accountId: string): string {
  const bytes = createHash('sha256')
    .update(`${ACTIVITY_LOCK_KEY_PREFIX}${accountId}`, 'utf8')
    .digest()
    .subarray(0, 8)
  return BigInt.asIntN(64, bytes.readBigUInt64BE()).toString()
}

function createBorrowedClient(activity: ActiveAccountActivity): PoolClient {
  return new Proxy(activity.client, {
    get: (target, property, receiver) => {
      if (property === 'query') {
        const query = target.query.bind(target) as (...values: unknown[]) => unknown
        return (...args: unknown[]) => {
          if (activity.isInvalid) {
            throw new AppError(
              'Não foi possível validar o acesso agora. Tente novamente.',
            )
          }
          return runTrackedQuery(activity, query, args)
        }
      }
      if (property === 'release') {
        return (error?: Error | boolean) => {
          if (error) activity.isInvalid = true
        }
      }
      const value = Reflect.get(target, property, receiver) as unknown
      return typeof value === 'function' ? value.bind(target) : value
    },
  })
}

function runTrackedQuery(
  activity: ActiveAccountActivity,
  query: (...values: unknown[]) => unknown,
  args: unknown[],
): unknown {
  const queryArgs = [...args]
  const callbackIndex = queryArgs.length - 1
  const callback = queryArgs[callbackIndex]
  if (typeof callback === 'function') {
    queryArgs[callbackIndex] = (...callbackArgs: unknown[]) => {
      if (callbackArgs[0]) activity.isInvalid = true
      Reflect.apply(callback, undefined, callbackArgs)
    }
  }

  try {
    const result = query(...queryArgs)
    if (isPromise(result)) {
      return result.catch((error: unknown) => {
        activity.isInvalid = true
        throw error
      })
    }
    return result
  } catch (error) {
    activity.isInvalid = true
    throw error
  }
}

function isPromise(value: unknown): value is Promise<unknown> {
  return typeof value === 'object' && value !== null && 'then' in value
}

function isLockTimeout(error: unknown): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    error.code === '55P03'
  )
}

function toError(error: unknown): Error {
  return error instanceof Error ? error : new Error('Account activity connection failed.')
}
