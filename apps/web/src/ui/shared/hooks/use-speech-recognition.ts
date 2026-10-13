import { useCallback, useEffect, useRef, useState } from 'react'

export type SpeechRecognitionStatus =
  | 'idle'
  | 'preparing'
  | 'recording'
  | 'transcribing'
  | 'review'
  | 'error'
export type SpeechLanguageAvailability =
  | 'checking'
  | 'available'
  | 'downloadable'
  | 'downloading'
  | 'unavailable'
export type SpeechInstallationStatus = 'idle' | 'installing' | 'installed' | 'failed'

type NativeRecognition = {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  processLocally?: boolean
  onstart: (() => void) | null
  onend: (() => void) | null
  onnomatch: (() => void) | null
  onerror: ((event: { error: string }) => void) | null
  onresult:
    | ((event: {
        resultIndex: number
        results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>
      }) => void)
    | null
  start(): void
  stop(): void
  abort(): void
}
type NativeRecognitionConstructor = {
  new (): NativeRecognition
  available?(options: {
    langs: string[]
    processLocally: true
    quality: 'dictation'
  }): Promise<SpeechLanguageAvailability>
  install?(options: { langs: string[]; quality: 'dictation' }): Promise<boolean>
}
type RecognitionOperation = {
  recognition: NativeRecognition | null
  resolve(value: string | null): void
  deadline: ReturnType<typeof setTimeout> | null
  clock: ReturnType<typeof setInterval> | null
  results: Map<number, string>
  isFinishing: boolean
}
const NO_RECOGNITION_MESSAGE =
  'Não foi possível reconhecer o ditado. Tente novamente ou continue digitando.'
const UNAVAILABLE_MESSAGE = 'Ditado indisponível neste navegador. Continue digitando.'
const INSTALLATION_ERROR_MESSAGE =
  'Não foi possível instalar o pacote de idioma. Tente novamente ou continue digitando.'

function getRecognitionConstructor(): NativeRecognitionConstructor | undefined {
  if (typeof window === 'undefined') return undefined
  const browser = window as Window & {
    SpeechRecognition?: NativeRecognitionConstructor
    webkitSpeechRecognition?: NativeRecognitionConstructor
  }
  return browser.SpeechRecognition ?? browser.webkitSpeechRecognition
}

export function useSpeechRecognition(language = 'pt-BR') {
  const [status, setStatus] = useState<SpeechRecognitionStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [languageAvailability, setLanguageAvailability] =
    useState<SpeechLanguageAvailability>('checking')
  const [installationStatus, setInstallationStatus] =
    useState<SpeechInstallationStatus>('idle')
  const [installationError, setInstallationError] = useState<string | null>(null)
  const operation = useRef<RecognitionOperation | null>(null)
  const installationGeneration = useRef(0)
  const installationPending = useRef(false)
  const mounted = useRef(false)

  const terminate = useCallback(function terminate(
    nextStatus: SpeechRecognitionStatus,
    message: string | null = null,
    text: string | null = null,
    shouldAbort = true,
  ) {
    let terminationError = message
    const current = operation.current
    operation.current = null
    if (current) {
      if (current.deadline !== null) clearTimeout(current.deadline)
      if (current.clock !== null) clearInterval(current.clock)
      const recognition = current.recognition
      if (recognition) {
        recognition.onstart = null
        recognition.onend = null
        recognition.onnomatch = null
        recognition.onerror = null
        recognition.onresult = null
        if (shouldAbort) {
          try {
            recognition.abort()
          } catch {
            terminationError = terminationError ?? NO_RECOGNITION_MESSAGE
          }
        }
      }
      current.results.clear()
      current.resolve(text)
    }
    if (mounted.current) {
      setStatus(nextStatus)
      setError(terminationError)
    }
  }, [])

  const cancelRecognition = useCallback(
    function cancelRecognition() {
      installationGeneration.current += 1
      if (installationPending.current) {
        installationPending.current = false
        if (mounted.current) {
          setInstallationStatus('idle')
          setInstallationError(null)
        }
      }
      terminate('idle')
    },
    [terminate],
  )

  useEffect(
    function observeCapabilities() {
      mounted.current = true
      let ignored = false
      const Constructor = getRecognitionConstructor()
      async function checkAvailability() {
        try {
          if (!Constructor?.available || !('processLocally' in new Constructor())) {
            if (!ignored) setLanguageAvailability('unavailable')
            return
          }
          const available = await Constructor.available({
            langs: [language],
            processLocally: true,
            quality: 'dictation',
          })
          if (!ignored) setLanguageAvailability(available)
        } catch {
          if (!ignored) setLanguageAvailability('unavailable')
        }
      }
      void checkAvailability()
      window.addEventListener('pagehide', cancelRecognition)
      return function cleanupRecognition() {
        ignored = true
        mounted.current = false
        installationGeneration.current += 1
        window.removeEventListener('pagehide', cancelRecognition)
        cancelRecognition()
      }
    },
    [cancelRecognition, language],
  )

  async function startRecognition(): Promise<string | null> {
    if (operation.current) return null
    const Constructor = getRecognitionConstructor()
    if (!Constructor?.available) {
      setStatus('error')
      setError(UNAVAILABLE_MESSAGE)
      return null
    }
    let resolveResult: (value: string | null) => void = () => undefined
    const result = new Promise<string | null>(function waitForFinalResult(resolve) {
      resolveResult = resolve
    })
    const current: RecognitionOperation = {
      recognition: null,
      resolve: resolveResult,
      deadline: null,
      clock: null,
      results: new Map(),
      isFinishing: false,
    }
    operation.current = current
    setStatus('preparing')
    setError(null)
    setElapsedSeconds(0)
    current.deadline = setTimeout(function failStartDeadline() {
      if (operation.current === current)
        terminate(
          'error',
          'Não foi possível iniciar o ditado. Tente novamente ou continue digitando.',
        )
    }, 30_000)
    try {
      const recognition = new Constructor()
      current.recognition = recognition
      if (!('processLocally' in recognition)) {
        terminate('error', UNAVAILABLE_MESSAGE)
        return result
      }
      const available = await Constructor.available({
        langs: [language],
        processLocally: true,
        quality: 'dictation',
      })
      if (operation.current !== current) return result
      setLanguageAvailability(available)
      if (available !== 'available') {
        terminate('error', UNAVAILABLE_MESSAGE)
        return result
      }
      recognition.lang = language
      recognition.processLocally = true
      recognition.continuous = true
      recognition.interimResults = false
      recognition.maxAlternatives = 1
      recognition.onstart = function handleStart() {
        if (
          operation.current !== current ||
          current.clock !== null ||
          current.isFinishing
        )
          return
        if (current.deadline !== null) clearTimeout(current.deadline)
        current.deadline = null
        setStatus('recording')
        const startedAt = Date.now()
        current.clock = setInterval(function updateDuration() {
          setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000))
        }, 1000)
      }
      recognition.onresult = function handleResults(event) {
        if (operation.current !== current) return
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const segment = event.results[index]
          if (segment.isFinal) current.results.set(index, segment[0].transcript)
        }
      }
      recognition.onend = function handleEnd() {
        if (operation.current !== current) return
        const text = [...current.results.entries()]
          .sort(([left], [right]) => left - right)
          .map(([, part]) => part.trim())
          .join(' ')
          .trim()
        terminate(
          text ? 'review' : 'error',
          text ? null : NO_RECOGNITION_MESSAGE,
          text || null,
          false,
        )
      }
      recognition.onnomatch = function handleNoMatch() {
        if (operation.current === current) terminate('error', NO_RECOGNITION_MESSAGE)
      }
      recognition.onerror = function handleError(event) {
        if (operation.current !== current) return
        const message = ['not-allowed', 'service-not-allowed'].includes(event.error)
          ? 'Permissão do microfone negada. Você pode continuar digitando.'
          : event.error === 'audio-capture'
            ? 'Não foi possível usar o microfone. Tente novamente ou continue digitando.'
            : NO_RECOGNITION_MESSAGE
        terminate('error', message)
      }
      recognition.start()
    } catch {
      if (operation.current === current) terminate('error', NO_RECOGNITION_MESSAGE)
    }
    return result
  }

  function finishRecognition() {
    const current = operation.current
    if (!current?.recognition || current.isFinishing) return
    current.isFinishing = true
    if (current.deadline !== null) clearTimeout(current.deadline)
    if (current.clock !== null) clearInterval(current.clock)
    current.clock = null
    setStatus('transcribing')
    current.deadline = setTimeout(function failFinishDeadline() {
      if (operation.current === current)
        terminate(
          'error',
          'Não foi possível concluir o ditado. Tente novamente ou continue digitando.',
        )
    }, 10_000)
    try {
      current.recognition.stop()
    } catch {
      terminate('error', NO_RECOGNITION_MESSAGE)
    }
  }

  async function installLanguagePack() {
    const Constructor = getRecognitionConstructor()
    if (!Constructor?.install || operation.current || installationPending.current) return
    const generation = ++installationGeneration.current
    installationPending.current = true
    setInstallationStatus('installing')
    setInstallationError(null)
    try {
      const installed = await Constructor.install({
        langs: [language],
        quality: 'dictation',
      })
      if (!mounted.current || generation !== installationGeneration.current) return
      if (!installed) {
        setInstallationStatus('failed')
        setInstallationError(INSTALLATION_ERROR_MESSAGE)
        return
      }
      const available = await Constructor.available?.({
        langs: [language],
        processLocally: true,
        quality: 'dictation',
      })
      if (!mounted.current || generation !== installationGeneration.current) return
      setLanguageAvailability(available ?? 'unavailable')
      if (available !== 'available') {
        setInstallationStatus('failed')
        setInstallationError(INSTALLATION_ERROR_MESSAGE)
        return
      }
      setInstallationStatus('installed')
    } catch {
      if (mounted.current && generation === installationGeneration.current) {
        setInstallationStatus('failed')
        setInstallationError(INSTALLATION_ERROR_MESSAGE)
      }
    } finally {
      if (generation === installationGeneration.current)
        installationPending.current = false
    }
  }

  return {
    status,
    error,
    elapsedSeconds,
    languageAvailability,
    installationStatus,
    installationError,
    canInstallLanguage:
      ['downloadable', 'downloading'].includes(languageAvailability) &&
      Boolean(getRecognitionConstructor()?.install),
    startRecognition,
    finishRecognition,
    cancelRecognition,
    installLanguagePack,
  }
}
