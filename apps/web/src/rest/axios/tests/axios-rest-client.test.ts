import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RestResponse } from '@/core/shared/responses/rest-response'

const { axiosCreate, request } = vi.hoisted(() => ({
  axiosCreate: vi.fn(),
  request: vi.fn(),
}))

vi.mock('axios', () => ({ default: { create: axiosCreate } }))
vi.mock('@/rest/axios/utils', () => ({ request }))

import { AxiosRestClient } from '../axios-rest-client'

describe('AxiosRestClient', () => {
  const client = { marker: 'client' }

  beforeEach(() => {
    vi.clearAllMocks()
    axiosCreate.mockReturnValue(client)
    request.mockResolvedValue({ isFailure: false, body: undefined })
  })

  it('applies defaults and maps every REST verb to the request adapter', async () => {
    const rest = AxiosRestClient()
    const signal = new AbortController().signal
    const formData = new FormData()
    formData.append('file', new File(['body'], 'a.txt', { type: 'text/plain' }))

    await rest.get('/get', { params: { cursor: 'next' }, headers: { 'X-Test': 'get' } })
    await rest.getFile('/file', { signal })
    await rest.post('/post', { value: 1 })
    await rest.postFormData('/form', formData, { signal })
    await rest.patch('/patch', { value: 2 })
    await rest.put('/put', { value: 3 })
    await rest.delete('/delete', { value: 4 })

    expect(axiosCreate).toHaveBeenCalledWith({
      baseURL: undefined,
      timeout: 15_000,
      withCredentials: true,
    })
    expect(request).toHaveBeenNthCalledWith(1, client, {
      method: 'get',
      url: '/get',
      params: { cursor: 'next' },
      headers: { 'X-Test': 'get' },
    })
    expect(request).toHaveBeenNthCalledWith(2, client, {
      method: 'get',
      url: '/file',
      params: undefined,
      headers: {},
      signal,
      responseType: 'arraybuffer',
    })
    expect(request).toHaveBeenNthCalledWith(3, client, {
      method: 'post',
      url: '/post',
      data: { value: 1 },
      headers: {},
    })
    expect(request).toHaveBeenNthCalledWith(4, client, {
      method: 'post',
      url: '/form',
      data: formData,
      headers: {},
      signal,
    })
    expect(request).toHaveBeenNthCalledWith(5, client, {
      method: 'patch',
      url: '/patch',
      data: { value: 2 },
      headers: {},
    })
    expect(request).toHaveBeenNthCalledWith(6, client, {
      method: 'put',
      url: '/put',
      data: { value: 3 },
      headers: {},
    })
    expect(request).toHaveBeenNthCalledWith(7, client, {
      method: 'delete',
      url: '/delete',
      data: { value: 4 },
      headers: {},
    })
  })

  it('preserves raw bytes when adapting a file response to Blob', async () => {
    const bytes = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
    request.mockResolvedValueOnce(
      new RestResponse({
        body: bytes.buffer,
        statusCode: 200,
        headers: { 'content-type': 'image/png' },
      }),
    )

    const response = await AxiosRestClient().getFile('/file')

    expect(response.body).toBeInstanceOf(Blob)
    expect([...new Uint8Array(await response.body.arrayBuffer())]).toEqual([...bytes])
  })

  it('allows callers to override credentials and merges request headers over defaults', async () => {
    const rest = AxiosRestClient('https://api.test', {
      withCredentials: false,
      defaultHeaders: { Authorization: 'Bearer default', 'X-Shared': 'default' },
    })
    await rest.get('/sessions', {
      headers: { Authorization: 'Bearer request', 'X-Request': 'yes' },
    })

    expect(axiosCreate).toHaveBeenCalledWith({
      baseURL: 'https://api.test',
      timeout: 15_000,
      withCredentials: false,
    })
    expect(request).toHaveBeenCalledWith(client, {
      method: 'get',
      url: '/sessions',
      params: undefined,
      headers: {
        Authorization: 'Bearer request',
        'X-Shared': 'default',
        'X-Request': 'yes',
      },
    })
  })
})
