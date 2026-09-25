import type { ReactNode } from 'react'
import { Body, Container, Head, Hr, Html, Preview, Section, Text } from 'react-email'

export type EmailLayoutProps = {
  children: ReactNode
  preview: string
}

const BODY_STYLE = {
  backgroundColor: '#f6f4ef',
  color: '#1d1b18',
  fontFamily: 'Arial, Helvetica, sans-serif',
  margin: '0',
  padding: '32px 16px',
}

const CONTAINER_STYLE = {
  margin: '0 auto',
  maxWidth: '600px',
  width: '100%',
}

const CARD_STYLE = {
  backgroundColor: '#ffffff',
  border: '1px solid #e4e0d7',
  borderRadius: '12px',
  padding: '36px 32px',
}

const BRAND_STYLE = {
  color: '#1d1b18',
  fontFamily: 'Georgia, Times New Roman, serif',
  fontSize: '24px',
  fontWeight: '700',
  letterSpacing: '-0.02em',
  margin: '0 0 28px',
}

const DIVIDER_STYLE = {
  borderColor: '#e4e0d7',
  margin: '28px 0 20px',
}

const FOOTER_STYLE = {
  color: '#5f5b54',
  fontSize: '12px',
  lineHeight: '18px',
  margin: '0',
}

export const EmailLayout = ({ preview, children }: EmailLayoutProps) => {
  return (
    <Html lang='pt-BR' dir='ltr'>
      <Head />
      <Preview>{preview}</Preview>
      <Body lang='pt-BR' dir='ltr' style={BODY_STYLE}>
        <Container style={CONTAINER_STYLE}>
          <Section style={CARD_STYLE}>
            <Text style={BRAND_STYLE}>Shifu</Text>
            {children}
            <Hr style={DIVIDER_STYLE} />
            <Text style={FOOTER_STYLE}>
              Esta é uma mensagem automática do Shifu. Se você não solicitou esta ação,
              ignore este e-mail.
            </Text>
          </Section>
        </Container>
      </Body>
    </Html>
  )
}
