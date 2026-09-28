import { Button, Heading, Section, Text, render } from 'react-email'

import { EmailLayout } from '../email-layout.js'

export type PasswordRecoveryEmailProps = {
  actionUrl: string
  expiresAt: string
}

export const PASSWORD_RECOVERY_SUBJECT = 'Redefina sua senha no Shifu'

const PASSWORD_RECOVERY_PREVIEW = 'Use o link para criar uma nova senha no Shifu.'

const ACTION_SECTION_STYLE = {
  margin: '28px 0',
  textAlign: 'center' as const,
}

const BUTTON_STYLE = {
  backgroundColor: '#1d1b18',
  borderRadius: '8px',
  color: '#ffffff',
  display: 'inline-block',
  fontSize: '16px',
  fontWeight: '700',
  lineHeight: '24px',
  padding: '12px 22px',
  textDecoration: 'none',
}

const HEADING_STYLE = {
  color: '#1d1b18',
  fontFamily: 'Georgia, Times New Roman, serif',
  fontSize: '30px',
  lineHeight: '36px',
  margin: '0 0 20px',
}

const TEXT_STYLE = {
  color: '#35312b',
  fontSize: '16px',
  lineHeight: '24px',
  margin: '0 0 16px',
}

const NOTE_STYLE = {
  color: '#5f5b54',
  fontSize: '14px',
  lineHeight: '21px',
  margin: '0 0 16px',
}

export const PasswordRecoveryEmail = ({
  actionUrl,
  expiresAt,
}: PasswordRecoveryEmailProps) => {
  return (
    <EmailLayout preview={PASSWORD_RECOVERY_PREVIEW}>
      <Heading style={HEADING_STYLE}>Redefina sua senha</Heading>
      <Text style={TEXT_STYLE}>
        Recebemos uma solicitação para redefinir a senha da sua conta no Shifu.
      </Text>
      <Text style={TEXT_STYLE}>
        Use o botão abaixo para criar uma nova senha. Este link é válido por uma hora e
        pode ser usado uma única vez.
      </Text>
      <Section style={ACTION_SECTION_STYLE}>
        <Button href={actionUrl} style={BUTTON_STYLE}>
          Redefinir minha senha
        </Button>
      </Section>
      <Text style={NOTE_STYLE}>
        Por segurança, este link expira em <strong>{expiresAt}</strong>.
      </Text>
      <Text style={NOTE_STYLE}>
        Se você não solicitou a redefinição, ignore este e-mail.
      </Text>
    </EmailLayout>
  )
}

export const renderPasswordRecoveryEmail = async (
  props: PasswordRecoveryEmailProps,
): Promise<{ subject: string; html: string }> => {
  return {
    subject: PASSWORD_RECOVERY_SUBJECT,
    html: await render(<PasswordRecoveryEmail {...props} />),
  }
}
