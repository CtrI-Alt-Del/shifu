export const HTTP_STATUS_CODE = {
  ok: 200,
  created: 201,
  noContent: 204,
  redirect: 300,
  badRequest: 400,
  unauthorized: 401,
  forbidden: 403,
  notFound: 404,
  notAcceptable: 406,
  conflict: 409,
  serverError: 500,
} as const

export type HttpStatusCode = (typeof HTTP_STATUS_CODE)[keyof typeof HTTP_STATUS_CODE]
