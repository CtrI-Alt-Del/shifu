import { useEffect, useRef, useState } from 'react'
import type { ReactPracticeCommand } from '@/core/learning/react-practice-runner'
export type TerminalPanelProps = {
  transcript: string
  commands: readonly ReactPracticeCommand[]
  onRunCommand: (id: string) => Promise<void>
}
export function useTerminalPanel(props: TerminalPanelProps) {
  const terminalRef = useRef<HTMLDivElement | null>(null)
  const xtermRef = useRef<import('@xterm/xterm').Terminal | null>(null)
  const transcriptRef = useRef(props.transcript)
  transcriptRef.current = props.transcript
  const [command, setCommand] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [hasTerminalError, setHasTerminalError] = useState(false)
  useEffect(() => {
    let cancelled = false
    void import('@xterm/xterm')
      .then(({ Terminal }) => {
        if (cancelled || !terminalRef.current) return
        const terminal = new Terminal({
          disableStdin: true,
          convertEol: true,
          rows: 18,
          cols: 48,
          fontSize: 12,
          scrollback: 2000,
        })
        terminal.open(terminalRef.current)
        xtermRef.current = terminal
        terminal.write(transcriptRef.current)
      })
      .catch(() => {
        if (!cancelled) setHasTerminalError(true)
      })
    return () => {
      cancelled = true
      xtermRef.current?.dispose()
      xtermRef.current = null
    }
  }, [])
  useEffect(() => {
    xtermRef.current?.reset()
    xtermRef.current?.write(props.transcript)
  }, [props.transcript])
  async function handleRun() {
    const allowed = props.commands.find(
      (item) => [item.executable, ...item.arguments].join(' ') === command,
    )
    if (!allowed) {
      setError('Comando não permitido. Use exatamente um dos comandos listados.')
      return
    }
    setIsRunning(true)
    setError(null)
    try {
      await props.onRunCommand(allowed.id)
    } catch {
      setError('Não foi possível iniciar o comando. Sua resposta foi preservada.')
    } finally {
      setIsRunning(false)
    }
  }
  return {
    terminalRef,
    command,
    error,
    isRunning,
    hasTerminalError,
    handleCommandChange: setCommand,
    handleRun,
  }
}
