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

const BCP_47_TAG = /^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$/
const SPEECH_LANGUAGES_BY_NAME: Record<string, string> = {
  portugues: 'pt-BR',
  portuguese: 'pt-BR',
  ingles: 'en-US',
  english: 'en-US',
  espanhol: 'es-ES',
  spanish: 'es-ES',
  frances: 'fr-FR',
  french: 'fr-FR',
  italiano: 'it-IT',
  italian: 'it-IT',
  alemao: 'de-DE',
  german: 'de-DE',
}
const UNRESOLVED_SPEECH_LANGUAGE = 'und'

function resolveSpeechLanguage(language: string): string | null {
  const trimmedLanguage = language.trim()
  if (BCP_47_TAG.test(trimmedLanguage)) return trimmedLanguage

  const name = trimmedLanguage
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
  return SPEECH_LANGUAGES_BY_NAME[name] ?? null
}

export function useTranslationQuestion(props: TranslationQuestionProps) {
  const { disabled, onChange, question, value } = props
  const speechLanguage = resolveSpeechLanguage(question.targetLanguage)
  const {
    status,
    error,
    elapsedSeconds,
    languageAvailability: recognitionAvailability,
    startRecognition,
    finishRecognition,
    cancelRecognition,
  } = useSpeechRecognition(speechLanguage ?? UNRESOLVED_SPEECH_LANGUAGE)
  const languageAvailability =
    speechLanguage === null ? 'unavailable' : recognitionAvailability
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
    if (disabled || speechLanguage === null) return

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
