import type { APIResponse, Page } from '@playwright/test'

import {
  buildAttemptPracticePhotoPath,
  buildPracticePhotoPath,
} from '../../src/constants/routes'
import { expect, signInPassword, test } from '../playwright'

const IDS = {
  goalId: '01J7T8AC91Z5K8M4JQ8C2D6F0B',
  skillId: '01J7T8AC91Z5K8M4JQ8C2D6F0C',
  competencyId: '01J7T8AC91Z5K8M4JQ8C2D6F0D',
  activityId: '01J7T8AC91Z5K8M4JQ8C2D6F0E',
}
const ATTEMPT_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0F'
const UPLOAD_KEY = 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259'
const MAX_PHOTO_BYTES = 10 * 1024 * 1024
const DRAFT_PHOTO_PATH = buildPracticePhotoPath({ ...IDS, recordKey: 'cuts' })
const ATTEMPT_PHOTO_PATH = buildAttemptPracticePhotoPath({
  ...IDS,
  attemptId: ATTEMPT_ID,
  photoId: '01J7T8AC91Z5K8M4JQ8C2D6F0G',
})

async function putPhoto(
  page: Page,
  path: string,
  options: { name?: string; type?: string; uploadKey?: string; bytes?: number } = {},
) {
  return page.evaluate(
    async ({ path, name, type, uploadKey, bytes }) => {
      const formData = new FormData()
      const content = new Uint8Array(bytes)
      // JPEG signature, so the server reaches its ownership check before decoding.
      if (bytes >= 3) content.set([0xff, 0xd8, 0xff])
      formData.append('file', new File([content], name, { type }))
      formData.append('upload_key', uploadKey)
      const response = await fetch(path, { method: 'PUT', body: formData })
      return {
        status: response.status,
        headers: Object.fromEntries(response.headers.entries()),
        body: await response.json(),
      }
    },
    {
      path,
      name: options.name ?? 'cortes.jpg',
      type: options.type ?? 'image/jpeg',
      uploadKey: options.uploadKey ?? UPLOAD_KEY,
      bytes: options.bytes ?? 8,
    },
  )
}

async function getJson(page: Page, path: string) {
  return page.evaluate(async (target) => {
    const response = await fetch(target)
    return {
      status: response.status,
      headers: Object.fromEntries(response.headers.entries()),
      body: await response.json(),
    }
  }, path)
}

function expectPrivateHeaders(headers: Record<string, string>) {
  expect(headers['cache-control']).toBe('private, no-store')
  expect(headers['x-content-type-options']).toBe('nosniff')
  expect(headers.authorization).toBeUndefined()
  expect(headers['set-cookie']).toBeUndefined()
}

async function responseBody(response: APIResponse) {
  return response.json() as Promise<{ code: string }>
}

test.describe('Practice photo BFF HTTP handlers', () => {
  test('rejects anonymous upload and reads with private safe headers', async ({
    page,
  }) => {
    await page.goto('/api/auth/get-session')
    const upload = await putPhoto(page, DRAFT_PHOTO_PATH)
    const draftRead = await getJson(page, DRAFT_PHOTO_PATH)
    const attemptRead = await getJson(page, ATTEMPT_PHOTO_PATH)

    for (const response of [upload, draftRead, attemptRead]) {
      expect(response.status).toBe(401)
      expectPrivateHeaders(response.headers)
      expect(response.body).toEqual(expect.objectContaining({ code: 'unauthenticated' }))
    }
  })

  test('rejects malformed identifiers and upload keys before forwarding a file', async ({
    page,
  }) => {
    await page.goto('/api/auth/get-session')
    const malformedActivity = await putPhoto(
      page,
      buildPracticePhotoPath({ ...IDS, activityId: 'invalido', recordKey: 'cuts' }),
    )
    const malformedKey = await putPhoto(page, DRAFT_PHOTO_PATH, {
      uploadKey: 'malformed',
    })
    const malformedRead = await getJson(
      page,
      buildPracticePhotoPath({ ...IDS, recordKey: 'a b' }),
    )

    expect(malformedActivity.status).toBe(422)
    expect(malformedKey.status).toBe(422)
    for (const response of [malformedActivity, malformedKey]) {
      expectPrivateHeaders(response.headers)
      expect(response.body).toEqual(expect.objectContaining({ code: 'malformed_photo' }))
    }
    expect(malformedRead.status).toBe(404)
    expect(malformedRead.body).toEqual(
      expect.objectContaining({ code: 'photo_not_found' }),
    )
  })

  test('rejects an unsupported or empty file and a photo above 10 MB', async ({
    page,
  }) => {
    await page.goto('/api/auth/get-session')
    const unsupported = await putPhoto(page, DRAFT_PHOTO_PATH, {
      name: 'nota.pdf',
      type: 'application/pdf',
    })
    const empty = await putPhoto(page, DRAFT_PHOTO_PATH, { bytes: 0 })
    const tooLarge = await putPhoto(page, DRAFT_PHOTO_PATH, {
      bytes: MAX_PHOTO_BYTES + 1,
    })

    expect(unsupported.status).toBe(422)
    expect(unsupported.body).toEqual(
      expect.objectContaining({ code: 'unsupported_photo' }),
    )
    expect(empty.status).toBe(422)
    expect(empty.body).toEqual(expect.objectContaining({ code: 'malformed_photo' }))
    expect(tooLarge.status).toBe(413)
    expect(tooLarge.body).toEqual(expect.objectContaining({ code: 'photo_too_large' }))
    for (const response of [unsupported, empty, tooLarge])
      expectPrivateHeaders(response.headers)
  })

  test('rejects a cross-origin upload before authenticating', async ({
    accountRequest,
  }) => {
    const response = await accountRequest.put(DRAFT_PHOTO_PATH, {
      headers: { origin: 'https://attacker.example' },
      multipart: {
        file: {
          name: 'cortes.jpg',
          mimeType: 'image/jpeg',
          buffer: Buffer.from('bytes'),
        },
        upload_key: UPLOAD_KEY,
      },
    })

    expect(response.status()).toBe(403)
    expect(response.headers()['cache-control']).toBe('private, no-store')
    expect((await responseBody(response)).code).toBe('same_origin_required')
  })

  test.describe('authenticated missing-resource failures', () => {
    test.beforeEach(async ({ page, activeAccount }) => {
      const signIn = await page.request.post('/api/auth/sign-in/identity', {
        data: { email: activeAccount.email, password: signInPassword },
        headers: { 'x-forwarded-for': activeAccount.ipAddress },
      })
      expect(signIn.status()).toBe(200)
      await page.goto('/api/auth/get-session')
    })

    test('keeps upload and photo reads private when the Activity does not belong to the learner', async ({
      page,
    }) => {
      const upload = await putPhoto(page, DRAFT_PHOTO_PATH)
      const draftRead = await getJson(page, DRAFT_PHOTO_PATH)
      const attemptRead = await getJson(page, ATTEMPT_PHOTO_PATH)

      for (const response of [upload, draftRead, attemptRead]) {
        expect(response.status).toBe(404)
        expectPrivateHeaders(response.headers)
        expect(response.body).toEqual(
          expect.objectContaining({ code: 'photo_not_found' }),
        )
      }
    })
  })
})
