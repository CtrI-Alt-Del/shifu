export const HTTP_STATUS_CODE = {
  badRequest: 400,
  conflict: 409,
  forbidden: 403,
  notFound: 404,
  payloadTooLarge: 413,
  serviceUnavailable: 503,
  tooManyRequests: 429,
  unauthorized: 401,
  unprocessableEntity: 422,
} as const
