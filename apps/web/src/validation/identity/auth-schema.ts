import { z } from 'zod'

export const signInSchema = z.object({
  email: z.string().email('Insira um e-mail válido'),
  password: z.string().min(8, 'A senha deve conter no mínimo 8 caracteres'),
})

export type SignInInput = z.infer<typeof signInSchema>

export const signUpSchema = z
  .object({
    name: z.string().min(2, 'O nome deve conter pelo menos 2 caracteres'),
    email: z.string().email('Insira um e-mail válido'),
    password: z.string().min(8, 'A senha deve conter no mínimo 8 caracteres'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'As senhas não coincidem',
    path: ['confirmPassword'],
  })

export type SignUpInput = z.infer<typeof signUpSchema>
