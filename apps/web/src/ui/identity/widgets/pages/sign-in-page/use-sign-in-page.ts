import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useForm, useStore } from '@tanstack/react-form'

import { AuthError } from '@/core/errors/auth-error'
import { useSignInAction } from '@/ui/identity/hooks/use-sign-in-action'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

export type SignInPageStatus =
  | 'idle'
  | 'submitting'
  | 'invalid'
  | 'throttled'
  | 'unavailable'

type SignInFormValues = {
  email: string
  password: string
}

export function useSignInPage() {
  const { signIn } = useSignInAction()
  const { navigateTo } = useNavigation()
  const [isPasswordVisible, setPasswordVisible] = useState(false)
  const [status, setStatus] = useState<SignInPageStatus>('idle')
  const [message, setMessage] = useState<string | null>(null)
  const alertRef = useRef<HTMLDivElement>(null)

  const isSubmitting = status === 'submitting'

  const form = useForm({
    defaultValues: {
      email: '',
      password: '',
    } satisfies SignInFormValues,
    onSubmit: async ({ value }: { value: SignInFormValues }) => {
      setStatus('submitting')
      setMessage(null)

      try {
        const result = await signIn(value)
        await navigateTo(result.redirectTo)
      } catch (error) {
        if (error instanceof AuthError) {
          setStatus(
            error.statusCode === 429
              ? 'throttled'
              : error.kind === 'authentication-rejected'
                ? 'invalid'
                : 'unavailable',
          )
          setMessage(error.message)
          if (error.kind === 'authentication-rejected') {
            form.setFieldValue('password', '')
          }
          return
        }

        setStatus('unavailable')
        setMessage('Não foi possível entrar agora. Tente novamente.')
      }
    },
  })
  const values = useStore(form.store, (state) => state.values)

  useEffect(() => {
    if (message) alertRef.current?.focus()
  }, [message])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    event.stopPropagation()
    if (isSubmitting) return
    await form.handleSubmit()
  }

  return {
    alertRef,
    email: values.email,
    form,
    isPasswordVisible,
    isSubmitting,
    message,
    password: values.password,
    setEmail: (value: string) => form.setFieldValue('email', value),
    setPassword: (value: string) => form.setFieldValue('password', value),
    setPasswordVisible,
    status,
    submit,
  }
}
