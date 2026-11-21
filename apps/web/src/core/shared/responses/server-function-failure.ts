export type ServerFunctionFailure = {
  kind: 'unauthorized' | 'invalid' | 'unavailable'
  statusCode: number
}
