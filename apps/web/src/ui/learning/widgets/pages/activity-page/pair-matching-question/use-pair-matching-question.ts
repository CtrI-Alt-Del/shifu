import { type KeyboardEvent, useRef, useState } from 'react'

import type {
  PairMatchingPair,
  PairMatchingQuestion,
} from '@/core/learning/choice-activity'
import type { ActivityDifficulty } from '@/core/learning/competency-detail'
import { languageLabel } from '@/core/learning/language-label'
import { pairMatchingItemText } from '@/core/learning/pair-matching-item-text'

export type PairMatchingQuestionProps = {
  isDiagnostic?: boolean
  activityTitle?: string
  difficulty?: ActivityDifficulty
  questionNumber: number
  totalQuestions: number
  question: PairMatchingQuestion
  pairs: readonly PairMatchingPair[]
  disabled?: boolean
  onChange: (pairs: readonly PairMatchingPair[]) => void
}

export function usePairMatchingQuestion({
  disabled = false,
  onChange,
  pairs,
  question,
}: PairMatchingQuestionProps) {
  const [selectedWordKey, setSelectedWordKey] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')
  const wordButtons = useRef(new Map<string, HTMLButtonElement>())
  const wordText = (key: string) => pairMatchingItemText(question.words, key)
  const translationText = (key: string) =>
    pairMatchingItemText(question.translations, key)
  const translationKeyByWord = new Map(
    pairs.map((pair) => [pair.wordKey, pair.translationKey]),
  )
  const wordKeyByTranslation = new Map(
    pairs.map((pair) => [pair.translationKey, pair.wordKey]),
  )
  const pairNumber = (wordKey: string) =>
    question.words.findIndex((word) => word.key === wordKey) + 1
  const orderedPairs = [...pairs].sort(
    (first, second) => pairNumber(first.wordKey) - pairNumber(second.wordKey),
  )
  const isComplete = pairs.length === question.words.length
  const sourceLanguageLabel = languageLabel(question.sourceLanguage)
  const targetLanguageLabel = languageLabel(question.targetLanguage)

  function registerWordButton(wordKey: string) {
    return (element: HTMLButtonElement | null) => {
      if (element) wordButtons.current.set(wordKey, element)
      else wordButtons.current.delete(wordKey)
    }
  }

  function handleSelectWord(wordKey: string) {
    if (disabled) return
    if (selectedWordKey === wordKey) {
      setSelectedWordKey(null)
      setAnnouncement(`Seleção de ${wordText(wordKey)} cancelada.`)
      return
    }
    if (translationKeyByWord.has(wordKey)) {
      onChange(pairs.filter((pair) => pair.wordKey !== wordKey))
      setAnnouncement(
        `Par de ${wordText(wordKey)} removido. ${wordText(wordKey)} selecionada. Escolha a nova tradução.`,
      )
    } else {
      setAnnouncement(`${wordText(wordKey)} selecionada. Escolha a tradução.`)
    }
    setSelectedWordKey(wordKey)
  }

  function handleSelectTranslation(translationKey: string) {
    if (disabled) return
    if (selectedWordKey === null) {
      setAnnouncement('Selecione primeiro uma palavra.')
      return
    }
    const replaced = wordKeyByTranslation.get(translationKey)
    onChange([
      ...pairs.filter(
        (pair) =>
          pair.wordKey !== selectedWordKey && pair.translationKey !== translationKey,
      ),
      { wordKey: selectedWordKey, translationKey },
    ])
    setAnnouncement(
      `Par formado: ${wordText(selectedWordKey)} com ${translationText(translationKey)}.` +
        (replaced && replaced !== selectedWordKey
          ? ` O par de ${wordText(replaced)} foi desfeito.`
          : ''),
    )
    setSelectedWordKey(null)
  }

  function handleRemovePair(wordKey: string) {
    if (disabled) return
    onChange(pairs.filter((pair) => pair.wordKey !== wordKey))
    if (selectedWordKey === wordKey) setSelectedWordKey(null)
    setAnnouncement(`Par de ${wordText(wordKey)} removido.`)
    // The remove button unmounts with its pair, so keyboard focus moves to the word.
    wordButtons.current.get(wordKey)?.focus()
  }

  function handleClearSelection() {
    if (selectedWordKey === null) return
    setSelectedWordKey(null)
    setAnnouncement('Seleção cancelada.')
  }

  function handleKeyDown(event: KeyboardEvent) {
    if (event.key === 'Escape') handleClearSelection()
  }

  return {
    selectedWordKey,
    announcement,
    isComplete,
    orderedPairs,
    sourceLanguageLabel,
    targetLanguageLabel,
    wordText,
    translationText,
    translationKeyByWord,
    wordKeyByTranslation,
    pairNumber,
    registerWordButton,
    handleSelectWord,
    handleSelectTranslation,
    handleRemovePair,
    handleClearSelection,
    handleKeyDown,
  }
}
