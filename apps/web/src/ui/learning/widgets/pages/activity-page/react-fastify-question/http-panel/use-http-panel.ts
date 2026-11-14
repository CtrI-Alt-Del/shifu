import { useEffect, useRef, useState } from 'react'
import type {
  ReactFastifyHttpExample,
  ReactFastifyHttpMethod,
} from '@/core/learning/choice-activity'
import type {
  ReactFastifyPracticeRunner,
  ReactFastifyPracticeHttpResponse,
} from '@/core/learning/react-fastify-practice-runner'

export type HttpPanelProps = {
  examples: readonly ReactFastifyHttpExample[]
  isReady: boolean
  onRequest: ReactFastifyPracticeRunner['request']
}

export function useHttpPanel(props: HttpPanelProps) {
  const [method, setMethod] = useState<ReactFastifyHttpMethod>(
    props.examples[0]?.method ?? 'GET',
  )
  const [path, setPath] = useState(props.examples[0]?.path ?? '/api/')
  const [body, setBody] = useState(props.examples[0]?.body ?? '')
  const [response, setResponse] = useState<ReactFastifyPracticeHttpResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)
  const requestRef = useRef<AbortController | null>(null)
  const hasBody = method !== 'GET' && method !== 'HEAD'
  useEffect(
    () => () => {
      requestRef.current?.abort()
      requestRef.current = null
    },
    [],
  )
  function handleExample(example: ReactFastifyHttpExample) {
    setMethod(example.method)
    setPath(example.path)
    setBody(example.body ?? '')
  }
  async function handleSend() {
    if (!props.isReady) return
    requestRef.current?.abort()
    const controller = new AbortController()
    requestRef.current = controller
    setIsSending(true)
    setError(null)
    try {
      const result = await props.onRequest(
        { method, path, ...(hasBody ? { body } : {}) },
        controller.signal,
      )
      if (requestRef.current === controller && !controller.signal.aborted)
        setResponse(result)
    } catch {
      if (requestRef.current === controller && !controller.signal.aborted)
        setError(
          'Não foi possível enviar a requisição. Confira a rota e tente novamente.',
        )
    } finally {
      if (requestRef.current === controller) setIsSending(false)
    }
  }
  function handleCancel() {
    requestRef.current?.abort()
    requestRef.current = null
    setIsSending(false)
    setError('Requisição cancelada.')
  }
  return {
    method,
    path,
    body,
    response,
    error,
    isSending,
    hasBody,
    handleMethodChange: setMethod,
    handlePathChange: setPath,
    handleBodyChange: setBody,
    handleExample,
    handleSend,
    handleCancel,
  }
}
