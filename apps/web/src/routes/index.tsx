import { createFileRoute } from '@tanstack/react-router'
import { Button } from '@/ui/shadcn/components/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/ui/shadcn/components/card'
import { Badge } from '@/ui/shadcn/components/badge'
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Flame,
  Layers,
  ShieldCheck,
  Sparkles,
  Trophy,
} from 'lucide-react'

export const Route = createFileRoute('/')({
  component: HomePage,
})

function HomePage() {
  return (
    <div className='mx-auto max-w-6xl px-4 py-8 sm:px-6 space-y-10'>
      {/* Hero Section */}
      <section className='border border-divider bg-surface p-6 sm:p-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 rounded-[2px]'>
        <div className='space-y-3 max-w-2xl'>
          <div className='flex items-center gap-2'>
            <span className='font-display text-xs tracking-widest text-selo-text uppercase'>
              Direção de Marca — Dojo
            </span>
            <span className='text-divider'>•</span>
            <Badge variant='selo'>MVP</Badge>
          </div>
          <h1 className='font-display text-3xl sm:text-4xl font-bold tracking-wide uppercase text-text-primary'>
            Assistente Virtual para Desenvolvimento de Habilidades
          </h1>
          <p className='text-text-secondary text-sm sm:text-base leading-relaxed'>
            Uma jornada de mentoria orientada a aprendizagem deliberada com IA consciente.
            O mentor guia, mas não entrega respostas prontas nem decide seu progresso.
          </p>
          <div className='pt-2 flex flex-wrap gap-3'>
            <Button variant='default'>
              Iniciar Diagnóstico
              <ArrowRight className='size-4' />
            </Button>
            <Button variant='outline'>Explorar Habilidades</Button>
          </div>
        </div>

        <div className='border border-divider bg-page p-5 rounded-[2px] w-full md:w-80 space-y-4'>
          <div className='flex items-center justify-between border-b border-divider pb-3'>
            <span className='font-display text-xs uppercase tracking-wider text-text-muted'>
              Estado do Sistema
            </span>
            <Badge variant='jade'>Operacional</Badge>
          </div>
          <div className='space-y-2 text-xs font-mono'>
            <div className='flex justify-between'>
              <span className='text-text-muted'>Framework</span>
              <span className='text-text-primary'>TanStack Start</span>
            </div>
            <div className='flex justify-between'>
              <span className='text-text-muted'>Roteamento</span>
              <span className='text-text-primary'>Type-Safe Router</span>
            </div>
            <div className='flex justify-between'>
              <span className='text-text-muted'>Estilos</span>
              <span className='text-text-primary'>Tailwind v4 (CSS Vars)</span>
            </div>
            <div className='flex justify-between'>
              <span className='text-text-muted'>Linter/Format</span>
              <span className='text-text-primary'>Biome</span>
            </div>
            <div className='flex justify-between'>
              <span className='text-text-muted'>Arquitetura</span>
              <span className='text-text-primary'>Clean Architecture</span>
            </div>
          </div>
        </div>
      </section>

      {/* Regra das Três Matizes (Princípio P1) */}
      <section className='space-y-4'>
        <div>
          <h2 className='font-display text-xl uppercase tracking-wider text-text-primary'>
            A Regra das Três Matizes
          </h2>
          <p className='text-xs text-text-muted'>
            Aprendizagem e gamificação nunca se misturam visualmente (Princípio P1 da
            especificação de design).
          </p>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-3 gap-4'>
          <Card className='border-jade-fill/30 bg-surface'>
            <CardHeader>
              <div className='flex items-center justify-between'>
                <Badge variant='jade'>Aprendizagem</Badge>
                <CheckCircle2 className='size-4 text-jade-solid' />
              </div>
              <CardTitle className='text-jade-text'>Jade</CardTitle>
              <CardDescription>
                Progresso, domínio comprovável, situação de competência e sucesso
                pedagógico.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className='bg-jade-tint p-3 rounded-[2px] border border-jade-fill/20 space-y-1'>
                <div className='flex justify-between text-xs font-mono'>
                  <span className='text-jade-text'>Competência Atual</span>
                  <span className='text-jade-solid font-semibold'>68% Domínio</span>
                </div>
                <div className='h-1.5 w-full bg-raised rounded-none overflow-hidden'>
                  <div className='h-full bg-jade-fill w-[68%]' />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className='border-selo-fill/30 bg-surface'>
            <CardHeader>
              <div className='flex items-center justify-between'>
                <Badge variant='selo'>Ação & Marca</Badge>
                <Sparkles className='size-4 text-selo-text' />
              </div>
              <CardTitle className='text-selo-text'>Selo</CardTitle>
              <CardDescription>
                Ação primária da tela, logotipo do Dojo, foco de atenção e feedback de
                erro.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className='bg-selo-tint p-3 rounded-[2px] border border-selo-fill/20 flex items-center justify-between'>
                <span className='text-xs font-mono text-selo-text'>
                  Ação Primária Única
                </span>
                <Button variant='default' size='sm'>
                  Continuar
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className='border-latao-fill/30 bg-surface'>
            <CardHeader>
              <div className='flex items-center justify-between'>
                <Badge variant='latao'>Gamificação</Badge>
                <Trophy className='size-4 text-latao-solid' />
              </div>
              <CardTitle className='text-latao-text'>Latão</CardTitle>
              <CardDescription>
                XP, nível de engajamento, dias de sequência, conquistas e recompensas.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className='bg-latao-tint p-3 rounded-[2px] border border-latao-fill/20 flex items-center justify-between text-xs font-mono'>
                <span className='text-latao-text flex items-center gap-1'>
                  <Flame className='size-3.5 text-latao-solid' /> Sequência
                </span>
                <span className='text-latao-solid font-semibold'>3 Dias Seguidos</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Áreas do Produto */}
      <section className='space-y-4'>
        <div>
          <h2 className='font-display text-xl uppercase tracking-wider text-text-primary'>
            Estrutura de Domínio da Aplicação
          </h2>
          <p className='text-xs text-text-muted'>
            Módulos de negócio modelados conforme a especificação do Shifu.
          </p>
        </div>

        <div className='grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4'>
          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2 text-base'>
                <ShieldCheck className='size-4 text-text-secondary' />
                Identity
              </CardTitle>
              <CardDescription>
                Autenticação, confirmação de conta, recuperação de senha e perfil do
                usuário.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2 text-base'>
                <Layers className='size-4 text-jade-solid' />
                Curriculum
              </CardTitle>
              <CardDescription>
                Habilidades, Competências, materiais pedagógicos e critérios de avaliação.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2 text-base'>
                <CheckCircle2 className='size-4 text-jade-solid' />
                Learning
              </CardTitle>
              <CardDescription>
                Diagnóstico inicial, trilhas ativas, submissão de código e evolução de
                domínio.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2 text-base'>
                <Bot className='size-4 text-selo-text' />
                Intelligence
              </CardTitle>
              <CardDescription>
                Mentor contextual por chat com IA consciente e controle estrito de cotas.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className='flex items-center gap-2 text-base'>
                <Trophy className='size-4 text-latao-solid' />
                Gamification
              </CardTitle>
              <CardDescription>
                Acúmulo de XP, progressão de nível, sequências de prática e conquistas.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>
    </div>
  )
}
