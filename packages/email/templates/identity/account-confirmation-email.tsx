import { Button, Heading, Link, Section, Text, render } from 'react-email'

import { EmailLayout } from '../email-layout.js'

export type AccountConfirmationEmailProps = {
  actionUrl: string
  displayName: string
  expiresAt: string
}

export const ACCOUNT_CONFIRMATION_SUBJECT = 'Confirme seu e-mail no Shifu'

const ACCOUNT_CONFIRMATION_PREVIEW =
  'Confirme seu e-mail para concluir seu cadastro no Shifu.'

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

export const AccountConfirmationEmail = ({
  actionUrl,
  displayName,
  expiresAt,
}: AccountConfirmationEmailProps) => {
  return (
    <EmailLayout preview={ACCOUNT_CONFIRMATION_PREVIEW}>
      <Heading style={HEADING_STYLE}>Confirme seu e-mail</Heading>
      <Text style={TEXT_STYLE}>Olá, {displayName}!</Text>
      <Text style={TEXT_STYLE}>
        Recebemos um cadastro no Shifu. Confirme seu e-mail para concluir o cadastro e
        começar sua jornada de aprendizagem.
      </Text>
      <Section style={ACTION_SECTION_STYLE}>
        <Button href={actionUrl} style={BUTTON_STYLE}>
          Confirmar meu e-mail
        </Button>
      </Section>
      <Text style={NOTE_STYLE}>
        Por segurança, este link expira em <strong>{expiresAt}</strong>.
      </Text>
      <Text style={NOTE_STYLE}>
        Se o botão não funcionar, use o <Link href={actionUrl}>link de confirmação</Link>.
      </Text>
    </EmailLayout>
  )
}

export const renderAccountConfirmationEmail = async (
  props: AccountConfirmationEmailProps,
): Promise<{ subject: string; html: string }> => {
  return {
    subject: ACCOUNT_CONFIRMATION_SUBJECT,
    html: await render(<AccountConfirmationEmail {...props} />),
  }
}
