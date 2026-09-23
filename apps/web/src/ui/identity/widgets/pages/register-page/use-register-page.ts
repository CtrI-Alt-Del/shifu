import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useForm } from '@tanstack/react-form'

import { useRegisterAccountAction } from '@/ui/identity/hooks/use-register-account-action'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

type RegisterFormValues = { displayName: string; email: string; password: string }

export function useRegisterPage() {
  const { registerAccount } = useRegisterAccountAction()
  const { navigateTo } = useNavigation()
  const [message, setMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const alertRef = useRef<HTMLDivElement>(null)
  const form = useForm({
    defaultValues: {
      displayName: '',
      email: '',
      password: '',
    } satisfies RegisterFormValues,
    onSubmit: () => undefined,
  })
  useEffect(() => {
    if (message) alertRef.current?.focus()
  }, [message])

  async function submit(values: RegisterFormValues) {
    if (isSubmitting) return
    const fields = validate(values)
    if (Object.keys(fields).length > 0) {
      for (const [name, error] of Object.entries(fields)) {
        form.setFieldMeta(name as keyof RegisterFormValues, (meta) => ({
          ...meta,
          errorMap: { onSubmit: error },
        }))
      }
      setMessage('Revise os campos destacados para continuar.')
      return
    }
    setIsSubmitting(true)
    setMessage(null)
    try {
      await registerAccount(values)
      await navigateTo('pendingConfirmation')
    } catch {
      setMessage('Não foi possível criar sua conta agora. Tente novamente.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    void submit({
      displayName: String(formData.get('displayName') ?? ''),
      email: String(formData.get('email') ?? ''),
      password: String(formData.get('password') ?? ''),
    })
  }

  return { alertRef, form, handleSubmit, isSubmitting, message }
}

function validate(values: RegisterFormValues): Record<string, string> {
  const fields: Record<string, string> = {}
  if (!values.displayName.trim()) fields.displayName = 'Informe seu nome.'
  if (!/^\S+@\S+\.\S+$/.test(values.email.trim()))
    fields.email = 'Informe um e-mail válido.'
  if (values.password.length < 8)
    fields.password = 'A senha deve ter pelo menos 8 caracteres.'
  return fields
}
