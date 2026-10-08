import { useEffect, useRef, useState } from 'react'
import type {
  CodePracticeEvent,
  CodePracticeRunner,
  CodePracticeStatus,
} from '@/core/learning/code-practice-runner'

export type CodeTerminalProps = {
  runner: CodePracticeRunner | null
}

const STATUS_TEXT: Record<CodePracticeStatus, string> = {
  idle: 'Aguardando prática',
  booting: 'Iniciando prática',
  'waiting-input': '',
  running: 'Prática em andamento',
  ready: 'Prática pronta',
  unavailable: 'Prática indisponível',
}

export function useCodeTerminal(props: CodeTerminalProps) {
  const [status, setStatus] = useState<CodePracticeStatus>('idle')
  const [transcript, setTranscript] = useState('')
  const terminalElementRef = useRef<HTMLDivElement>(null)
  const terminalRef = useRef<import('@xterm/xterm').Terminal | null>(null)
  const inputRef = useRef('')
  const currentRunIdRef = useRef<number | null>(null)

  useEffect(() => {
    let cancelled = false
    let fit: import('@xterm/addon-fit').FitAddon | null = null
    let resizeObserver: ResizeObserver | null = null
    let fitFrame: number | null = null
    let pendingSize: { width: number; height: number } | null = null
    let lastFittedSize: { width: number; height: number } | null = null
    void Promise.all([import('@xterm/xterm'), import('@xterm/addon-fit')]).then(
      ([{ Terminal }, { FitAddon }]) => {
        if (cancelled || !terminalElementRef.current) return

        const terminal = new Terminal({
          convertEol: true,
          cursorBlink: true,
          fontSize: 13,
          theme: { background: '#1d1e22', foreground: '#f4f2ec' },
        })
        fit = new FitAddon()
        terminal.loadAddon(fit)
        terminal.open(terminalElementRef.current)
        terminalRef.current = terminal
        fit.fit()
        terminal.onData((data) => {
          if (data === '\r') {
            const value = inputRef.current
            inputRef.current = ''
            terminal.write('\r\n')
            if (value.trim()) void props.runner?.sendStdin(value)
            terminal.write('> ')
          } else if (data === '\u007f') {
            if (inputRef.current.length) {
              inputRef.current = inputRef.current.slice(0, -1)
              terminal.write('\b \b')
            }
          } else if (data >= ' ' && data !== '\u007f') {
            inputRef.current += data
            terminal.write(data)
          }
        })
        resizeObserver = new ResizeObserver((entries) => {
          const entry = entries[0]
          if (!entry) return

          pendingSize = {
            width: entry.contentRect.width,
            height: entry.contentRect.height,
          }
          if (fitFrame !== null) return

          fitFrame = window.requestAnimationFrame(() => {
            fitFrame = null
            const size = pendingSize
            pendingSize = null
            if (
              cancelled ||
              !size ||
              (lastFittedSize?.width === size.width &&
                lastFittedSize.height === size.height)
            ) {
              return
            }

            fit?.fit()
            lastFittedSize = size
          })
        })
        resizeObserver.observe(terminalElementRef.current)
      },
    )
    return () => {
      cancelled = true
      resizeObserver?.disconnect()
      if (fitFrame !== null) window.cancelAnimationFrame(fitFrame)
      fitFrame = null
      pendingSize = null
      terminalRef.current?.dispose()
      terminalRef.current = null
    }
  }, [props.runner])

  useEffect(() => {
    if (!props.runner) return
    return props.runner.subscribe((event: CodePracticeEvent) => {
      setStatus(event.status)
      if (currentRunIdRef.current !== event.runId) {
        currentRunIdRef.current = event.runId
        setTranscript('')
        terminalRef.current?.reset()
      }
      if (event.text) {
        setTranscript((current) => (current + event.text).slice(-1_048_576))
        terminalRef.current?.write(event.text.replaceAll('\n', '\r\n'))
      }
      if (event.status === 'waiting-input' || event.status === 'ready') {
        terminalRef.current?.write('> ')
      }
    })
  }, [props.runner])

  return {
    status,
    statusText: STATUS_TEXT[status],
    terminalElementRef,
    transcript,
  }
}
