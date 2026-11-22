import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useForm, useStore } from '@tanstack/react-form'
import { z } from 'zod'
import { AuthError } from '@/core/errors/auth-error'
import {
  ACCOUNT_APPEARANCES,
  type AccountAppearance,
} from '@/core/identity/account-appearance'
import type { ProfileFormProps } from './index'
import { useUpdateAccountProfileAction } from './use-update-account-profile-action'

type ProfileFormValues = {
  displayName: string
  timeZone: string
  appearance: AccountAppearance
}

const PROFILE_SCHEMA = z.object({
  displayName: z
    .string()
    .trim()
    .refine(
      (value) => [...value].length >= 1 && [...value].length <= 160,
      'Informe um nome com até 160 caracteres.',
    ),
  timeZone: z
    .string()
    .min(1, 'Selecione seu fuso horário.')
    .max(64)
    .refine(isTimeZone, 'Selecione um fuso horário válido.'),
  appearance: z.enum(ACCOUNT_APPEARANCES, 'Selecione uma aparência válida.'),
})

const APPEARANCE_LABELS: Record<AccountAppearance, string> = {
  dark: 'Escuro',
  light: 'Claro',
  system: 'Sistema',
}

const APPEARANCE_HELP: Record<AccountAppearance, string> = {
  dark: 'O Shifu usa o tema escuro em todos os seus dispositivos.',
  light: 'O Shifu usa o tema claro em todos os seus dispositivos.',
  system: 'O Shifu segue o tema claro ou escuro configurado em cada dispositivo.',
}

const APPEARANCE_OPTIONS = ACCOUNT_APPEARANCES.map((value) => ({
  value,
  label: APPEARANCE_LABELS[value],
}))

function isAccountAppearance(value: string | null): value is AccountAppearance {
  return ACCOUNT_APPEARANCES.some((appearance) => appearance === value)
}

function isTimeZone(value: string) {
  try {
    new Intl.DateTimeFormat('pt-BR', { timeZone: value })
    return true
  } catch {
    return false
  }
}

function detectTimeZone() {
  try {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
    return isTimeZone(timeZone) ? timeZone : ''
  } catch {
    return ''
  }
}

function createTimeZoneOptions(saved: string | null, detected: string) {
  const supported =
    (
      Intl as typeof Intl & { supportedValuesOf?: (key: string) => string[] }
    ).supportedValuesOf?.('timeZone') ?? []
  const values = [
    ...new Set(
      ['UTC', ...supported, saved, detected].filter(
        (value): value is string => Boolean(value) && isTimeZone(value as string),
      ),
    ),
  ].sort()
  return values.map((value) => ({
    value,
    label:
      value === 'UTC'
        ? 'Tempo universal coordenado · UTC'
        : `Fuso horário · ${value.replaceAll('_', ' ')}`,
  }))
}

export function useProfileForm({ profile }: ProfileFormProps) {
  const { isPending, refreshWarning, updateAccountProfile } =
    useUpdateAccountProfileAction()
  const [detectedTimeZone] = useState(detectTimeZone)
  const [message, setMessage] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState(false)
  const [errors, setErrors] = useState<{
    displayName?: string
    timeZone?: string
    appearance?: string
  }>({})
  const inFlightRef = useRef(false)
  const alertRef = useRef<HTMLParagraphElement>(null)
  const previousProfileRef = useRef(profile)
  const defaultValuesRef = useRef<ProfileFormValues>({
    displayName: profile.displayName,
    timeZone: profile.timeZone ?? detectedTimeZone,
    appearance: profile.appearance,
  })
  const form = useForm({
    defaultValues: defaultValuesRef.current,
    onSubmit: handleSave,
  })
  const values = useStore(form.store, (state) => state.values)
  const isDirty = useStore(form.store, (state) => state.isDirty)
  const timeZoneOptions = useMemo(
    () => createTimeZoneOptions(profile.timeZone, detectedTimeZone),
    [profile.timeZone, detectedTimeZone],
  )
  const isSuggestedTimeZone =
    profile.timeZone === null &&
    values.timeZone === detectedTimeZone &&
    Boolean(detectedTimeZone)

  useEffect(() => {
    const previous = previousProfileRef.current
    if (
      previous.displayName === profile.displayName &&
      previous.timeZone === profile.timeZone &&
      previous.appearance === profile.appearance
    )
      return
    previousProfileRef.current = profile
    if (!isDirty) {
      defaultValuesRef.current = {
        displayName: profile.displayName,
        timeZone: profile.timeZone ?? detectedTimeZone,
        appearance: profile.appearance,
      }
      form.reset(defaultValuesRef.current)
    }
  }, [profile, detectedTimeZone, form, isDirty])

  useEffect(() => {
    if (message && !isSuccess) alertRef.current?.focus()
  }, [message, isSuccess])

  async function handleSave({ value }: { value: ProfileFormValues }) {
    if (inFlightRef.current) return
    const parsed = PROFILE_SCHEMA.safeParse(value)
    setErrors({})
    setIsSuccess(false)
    if (!parsed.success) {
      const fields = parsed.error.flatten().fieldErrors
      setErrors({
        displayName: fields.displayName?.[0],
        timeZone: fields.timeZone?.[0],
        appearance: fields.appearance?.[0],
      })
      setMessage('Revise os campos destacados.')
      return
    }
    inFlightRef.current = true
    setMessage(null)
    try {
      const saved = await updateAccountProfile(parsed.data)
      defaultValuesRef.current = {
        displayName: saved.displayName,
        timeZone: saved.timeZone ?? '',
        appearance: saved.appearance,
      }
      form.reset(defaultValuesRef.current)
      setIsSuccess(true)
      setMessage('Perfil salvo.')
    } catch (error) {
      if (
        error instanceof AuthError &&
        (error.field === 'displayName' ||
          error.field === 'timeZone' ||
          error.field === 'appearance')
      )
        setErrors({ [error.field]: error.message })
      setMessage(
        error instanceof AuthError
          ? error.message
          : 'Não foi possível salvar o perfil agora. Tente novamente.',
      )
    } finally {
      inFlightRef.current = false
    }
  }
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    event.stopPropagation()
    if (!inFlightRef.current) await form.handleSubmit()
  }
  function handleDisplayNameChange(value: string) {
    form.setFieldValue('displayName', value)
  }
  function handleTimeZoneChange(value: string | null) {
    form.setFieldValue('timeZone', value ?? '')
  }
  function handleAppearanceChange(value: string | null) {
    if (isAccountAppearance(value)) form.setFieldValue('appearance', value)
  }
  return {
    alertRef,
    appearance: values.appearance,
    appearanceHelp: APPEARANCE_HELP[values.appearance],
    appearanceOptions: APPEARANCE_OPTIONS,
    displayName: values.displayName,
    email: profile.email,
    errors,
    isPending,
    isSuccess,
    isSuggestedTimeZone,
    message,
    refreshWarning,
    timeZone: values.timeZone,
    timeZoneOptions,
    handleAppearanceChange,
    handleDisplayNameChange,
    handleTimeZoneChange,
    handleSubmit,
  }
}
