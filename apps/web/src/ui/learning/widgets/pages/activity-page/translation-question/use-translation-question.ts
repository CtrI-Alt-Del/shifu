import { useEffect, useRef, useState } from 'react'

import type { ActivityDifficulty } from '@/core/learning/competency-detail'
import type { TranslationQuestion } from '@/core/learning/choice-activity'
import { useSpeechRecognition } from '@/ui/shared/hooks/use-speech-recognition'

export type TranslationQuestionProps = {
  isDiagnostic?: boolean
  activityTitle?: string
  difficulty?: ActivityDifficulty
  questionNumber: number
  totalQuestions: number
  question: TranslationQuestion
  value: string
  disabled?: boolean
  onChange: (text: string) => void
}

export function useTranslationQuestion(props: TranslationQuestionProps) {
  const { disabled, onChange, question, value } = props
  const {
    status,
    error,
    elapsedSeconds,
    languageAvailability,
    startRecognition,
    finishRecognition,
    cancelRecognition,
  } = useSpeechRecognition('pt-BR')
  const [pendingTranscript, setPendingTranscript] = useState<string | null>(null)
  const valueRef = useRef(value)
  const dictationGeneration = useRef(0)
  const questionKeyRef = useRef(question.key)

  useEffect(
    function trackCurrentValue() {
      valueRef.current = value
    },
    [value],
  )

  useEffect(
    function releaseDictationOnQuestionChange() {
      if (questionKeyRef.current === question.key) return

      questionKeyRef.current = question.key
      dictationGeneration.current += 1
      setPendingTranscript(null)
      cancelRecognition()
    },
    [cancelRecognition, question.key],
  )

  useEffect(
    function releaseDictationOnUnmount() {
      return function cleanupDictation() {
        cancelRecognition()
      }
    },
    [cancelRecognition],
  )

  function handleChangeText(text: string) {
    if (disabled) return

    onChange(text)
  }

  async function handleStartDictation() {
    if (disabled) return

    const generation = ++dictationGeneration.current
    const transcript = await startRecognition()
    if (generation !== dictationGeneration.current) return

    const trimmedTranscript = transcript?.trim()
    if (!trimmedTranscript) return

    if (valueRef.current.trim().length > 0) {
      setPendingTranscript(trimmedTranscript)
      return
    }

    onChange(trimmedTranscript)
  }

  function handleStopDictation() {
    finishRecognition()
  }

  function handleCancelDictation() {
    dictationGeneration.current += 1
    setPendingTranscript(null)
    cancelRecognition()
  }

  function handleConfirmReplace() {
    if (pendingTranscript === null) return

    onChange(pendingTranscript)
    setPendingTranscript(null)
  }

  function handleDeclineReplace() {
    setPendingTranscript(null)
  }

  return {
    status,
    error,
    elapsedSeconds,
    languageAvailability,
    pendingTranscript,
    handleChangeText,
    handleStartDictation,
    handleStopDictation,
    handleCancelDictation,
    handleConfirmReplace,
    handleDeclineReplace,
  }
}
