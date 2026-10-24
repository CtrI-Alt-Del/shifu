import type { TelemetryProvider } from './telemetry-provider'

export type RequestTelemetryContext = Readonly<{
  requestId: string
  telemetry: TelemetryProvider
}>

declare module '@tanstack/react-router' {
  interface Register {
    server: {
      requestContext: RequestTelemetryContext
    }
  }
}
