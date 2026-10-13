import type { RestResponse } from '@/core/shared/responses/rest-response'
export interface RestStreamClient {
  getStream(
    url: string,
    options: { headers: Record<string, string>; signal: AbortSignal },
  ): Promise<RestResponse<ReadableStream<Uint8Array>>>
}
