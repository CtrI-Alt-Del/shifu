import {
  buildMentorAttachmentFilePath,
  buildMentorAttachmentUploadPath,
} from '../../src/constants/routes'
import { expect, signInPassword, test } from '../playwright'

const BATCH_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0B'
const SESSION_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0C'
const ATTACHMENT_ID = '01J7T8AC91Z5K8M4JQ8C2D6F0D'
const UPLOAD_KEY = 'e9cfaab2-fb57-40e6-96aa-e6d7afdd7259'

async function postTextFile(page: import('@playwright/test').Page) {
  return page.evaluate(
    async ({ path, uploadKey }) => {
      const formData = new FormData()
      formData.append(
        'file',
        new File(['anotação'], 'anotacao.txt', { type: 'text/plain' }),
      )
      formData.append('upload_key', uploadKey)
      const response = await fetch(path, { method: 'POST', body: formData })
      return {
        status: response.status,
        headers: Object.fromEntries(response.headers.entries()),
        body: await response.json(),
      }
    },
    { path: buildMentorAttachmentUploadPath(BATCH_ID), uploadKey: UPLOAD_KEY },
  )
}

test.describe('Mentor attachment BFF HTTP handlers', () => {
  test('rejects anonymous upload and file reads with private safe headers', async ({
    page,
  }) => {
    await page.goto('/api/auth/get-session')
    const upload = await postTextFile(page)
    const file = await page.evaluate(
      async ({ path }) => {
        const response = await fetch(path)
        return {
          status: response.status,
          headers: Object.fromEntries(response.headers.entries()),
          body: await response.json(),
        }
      },
      { path: buildMentorAttachmentFilePath(SESSION_ID, ATTACHMENT_ID) },
    )

    for (const response of [upload, file]) {
      expect(response.status).toBe(401)
      expect(response.headers['cache-control']).toBe('private, no-store')
      expect(response.headers['x-content-type-options']).toBe('nosniff')
      expect(response.headers.authorization).toBeUndefined()
      expect(response.headers['set-cookie']).toBeUndefined()
      expect(response.body).toEqual(expect.objectContaining({ code: 'unauthenticated' }))
    }
  })

  test('rejects malformed upload identifiers before forwarding a file', async ({
    page,
  }) => {
    await page.goto('/api/auth/get-session')
    const response = await page.evaluate(
      async ({ path }) => {
        const formData = new FormData()
        formData.append('file', new File(['texto'], 'notas.txt', { type: 'text/plain' }))
        formData.append('upload_key', 'malformed')
        const result = await fetch(path, { method: 'POST', body: formData })
        return {
          status: result.status,
          headers: Object.fromEntries(result.headers.entries()),
          body: await result.json(),
        }
      },
      { path: buildMentorAttachmentUploadPath('batch-inválido') },
    )

    expect(response.status).toBe(422)
    expect(response.headers['cache-control']).toBe('private, no-store')
    expect(response.headers['x-content-type-options']).toBe('nosniff')
    expect(response.body).toEqual(
      expect.objectContaining({ code: 'malformed_attachment' }),
    )
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

    test('keeps upload and binary read failures private without forwarding credentials', async ({
      page,
    }) => {
      const upload = await postTextFile(page)
      const file = await page.evaluate(
        async ({ path }) => {
          const response = await fetch(path)
          return {
            status: response.status,
            headers: Object.fromEntries(response.headers.entries()),
            body: await response.json(),
          }
        },
        { path: buildMentorAttachmentFilePath(SESSION_ID, ATTACHMENT_ID) },
      )

      for (const response of [upload, file]) {
        expect(response.status).toBe(404)
        expect(response.headers['cache-control']).toBe('private, no-store')
        expect(response.headers['x-content-type-options']).toBe('nosniff')
        expect(response.headers.authorization).toBeUndefined()
        expect(response.headers['set-cookie']).toBeUndefined()
        expect(response.body).toEqual(
          expect.objectContaining({ code: 'attachment_not_found' }),
        )
      }
    })
  })
})
