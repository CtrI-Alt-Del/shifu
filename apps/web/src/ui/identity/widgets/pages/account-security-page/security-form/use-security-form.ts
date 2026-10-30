import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useForm, useStore } from '@tanstack/react-form'
import { z } from 'zod'
import { AuthError } from '@/core/errors/auth-error'
import { useChangeAccountPasswordAction } from './use-change-account-password-action'

const PASSWORD_SCHEMA = z.object({
  currentPassword: z.string().min(1, 'Informe sua senha atual.'),
  newPassword: z
    .string()
    .refine(
      (value) => [...value].length >= 8,
      'A nova senha deve ter pelo menos 8 caracteres.',
    ),
})

export function useSecurityForm() {
  const { isPending, changeAccountPassword } = useChangeAccountPasswordAction()
  const [isPasswordVisible, setIsPasswordVisible] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [isSuccess, setIsSuccess] = useState(false)
  const [errors, setErrors] = useState<{
    currentPassword?: string
    newPassword?: string
  }>({})
  const inFlightRef = useRef(false)
  const alertRef = useRef<HTMLParagraphElement>(null)
  const form = useForm({
    defaultValues: { currentPassword: '', newPassword: '' },
    onSubmit: handleChange,
  })
  const values = useStore(form.store, (state) => state.values)
  useEffect(
    () =>
      function clearSecretsOnHide() {
        form.reset()
        setIsPasswordVisible(false)
      },
    [form],
  )
  useEffect(() => {
    if (message) alertRef.current?.focus()
  }, [message])
  async function handleChange({
    value,
  }: {
    value: { currentPassword: string; newPassword: string }
  }) {
    if (inFlightRef.current) return
    const parsed = PASSWORD_SCHEMA.safeParse(value)
    setErrors({})
    setIsSuccess(false)
    if (!parsed.success) {
      const fields = parsed.error.flatten().fieldErrors
      setErrors({
        currentPassword: fields.currentPassword?.[0],
        newPassword: fields.newPassword?.[0],
      })
      setMessage('Revise os campos destacados.')
      return
    }
    inFlightRef.current = true
    setMessage(null)
    try {
      await changeAccountPassword(parsed.data)
      setIsSuccess(true)
      setMessage('Senha alterada. Os outros acessos foram encerrados. Este continua.')
    } catch (error) {
      if (error instanceof AuthError && error.kind === 'invalid-current-password')
        setErrors({ currentPassword: error.message })
      if (error instanceof AuthError && error.field === 'newPassword')
        setErrors({ newPassword: error.message })
      setMessage(
        error instanceof AuthError
          ? error.message
          : 'Não foi possível confirmar a troca. Sua senha pode ter sido alterada. Este acesso continua disponível.',
      )
    } finally {
      form.reset()
      setIsPasswordVisible(false)
      inFlightRef.current = false
    }
  }
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    event.stopPropagation()
    if (!inFlightRef.current) await form.handleSubmit()
  }
  function handleCurrentPasswordChange(value: string) {
    form.setFieldValue('currentPassword', value)
  }
  function handleNewPasswordChange(value: string) {
    form.setFieldValue('newPassword', value)
  }
  function handleTogglePasswordVisibility() {
    setIsPasswordVisible((value) => !value)
  }
  return {
    alertRef,
    currentPassword: values.currentPassword,
    newPassword: values.newPassword,
    errors,
    isPending,
    isSuccess,
    isPasswordVisible,
    message,
    handleCurrentPasswordChange,
    handleNewPasswordChange,
    handleTogglePasswordVisibility,
    handleSubmit,
  }
}
