import {
  useHtmlCssJsQuestion,
  type HtmlCssJsQuestionProps,
} from './use-html-css-js-question'
import { ActivityQuestionHeader } from '../components/activity-question-header'
import { CodeEditor } from '@/ui/learning/widgets/components/code-editor'
import { CodeFileTree } from '@/ui/learning/widgets/components/code-file-tree'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Button } from '@/ui/shadcn/button'

export type { HtmlCssJsQuestionProps } from './use-html-css-js-question'

const STATUS_LABELS = {
  idle: 'Aguardando ambiente de prática',
  booting: 'Iniciando prévia e Terminal…',
  ready: 'Prévia pronta e atualizando com os arquivos',
  unavailable: 'Prática indisponível. Você ainda pode editar e avaliar a resposta.',
} as const

export const HtmlCssJsQuestion = (props: HtmlCssJsQuestionProps) => {
  const {
    displayFiles,
    editablePaths,
    selectedPath,
    practiceStatus,
    previewUrl,
    terminalText,
    practiceTab,
    isSaving,
    hasSaveError,
    hasFileError,
    hasAssessError,
    isAssessing,
    isFrozen,
    isDraftInvalidated,
    draftLoaded,
    handleAssess,
    handleFileChange,
    handleSelectFile,
    handleSelectPracticeTab,
  } = useHtmlCssJsQuestion(props)

  return (
    <section
      aria-label='Questão de HTML, CSS e JavaScript'
      className='flex min-h-0 min-w-0 flex-1 flex-col gap-3.5 lg:h-[calc(100dvh-7.25rem)] lg:flex-none lg:min-h-[28rem]'
    >
      <ActivityQuestionHeader
        activityTitle={props.activityTitle ?? 'Questão de HTML, CSS e JavaScript'}
        difficulty={props.difficulty}
        questionNumber={props.questionNumber}
        totalQuestions={props.totalQuestions}
        showQuestionProgress={!props.isDiagnostic}
      />
      <div className='grid min-h-0 min-w-0 flex-1 grid-cols-1 border border-border bg-card lg:grid-cols-[minmax(15rem,0.8fr)_minmax(20rem,1.7fr)_minmax(18rem,1.4fr)]'>
        <aside className='min-w-0 border-b border-border bg-surface-alt lg:min-h-0 lg:overflow-y-auto lg:border-b-0 lg:border-r'>
          <div className='border-b border-border px-4 py-3'>
            <h2 className='text-sm font-semibold'>Enunciado</h2>
          </div>
          <div className='space-y-4 p-4'>
            <QuestionPrompt
              id={`html-css-js-prompt-${props.question.key}`}
              prompt={props.question.prompt}
              size='result'
            />
            <section
              aria-labelledby={`html-css-js-rubric-${props.question.key}`}
              className='space-y-2 rounded-md bg-jade-tint p-3'
            >
              <h3
                id={`html-css-js-rubric-${props.question.key}`}
                className='text-sm font-semibold text-success'
              >
                Como será avaliado
              </h3>
              <p className='text-xs leading-5 text-foreground/80'>
                A avaliação usa os critérios e pesos definidos para esta questão. A prévia
                e o Terminal são apenas ferramentas de prática.
              </p>
              <ul aria-label='Critérios da rubrica' className='space-y-2'>
                {props.question.criteria.map((criterion) => (
                  <li
                    className='flex items-start justify-between gap-3 text-xs leading-5'
                    key={criterion.key}
                  >
                    <span className='min-w-0 break-words'>{criterion.name}</span>
                    <span className='shrink-0 font-mono'>
                      Peso {criterion.weightPercentage}%
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
          <div className='border-y border-border px-4 py-3'>
            <h3 className='text-sm font-semibold'>Arquivos iniciais</h3>
          </div>
          <div className='p-3'>
            <CodeFileTree
              files={displayFiles}
              selectedPath={selectedPath}
              editablePaths={editablePaths}
              readOnly={isFrozen}
              onSelectFile={handleSelectFile}
            />
          </div>
        </aside>

        <div className='flex min-h-0 min-w-0 flex-col border-b border-border lg:border-b-0 lg:border-r'>
          <div className='flex min-h-12 flex-wrap items-center justify-between gap-2 border-b border-border bg-muted px-3 py-2'>
            <span className='text-xs font-semibold'>Editor</span>
            <div className='flex items-center gap-3 text-xs' aria-live='polite'>
              {!draftLoaded ? <span>Verificando rascunho…</span> : null}
              {isSaving ? <span>Salvando rascunho…</span> : null}
              {hasSaveError ? (
                <span role='alert' className='text-selo-text'>
                  Não foi possível salvar o rascunho.
                </span>
              ) : null}
              {isDraftInvalidated ? (
                <span role='alert' className='text-selo-text'>
                  Este rascunho foi invalidado. Atualize a Atividade para continuar.
                </span>
              ) : null}
              {hasFileError ? (
                <span role='alert' className='text-selo-text'>
                  Os arquivos excedem o limite de prática.
                </span>
              ) : null}
            </div>
            {props.onAssess && !props.isDiagnostic ? (
              <Button
                className='mr-16 lg:mr-0'
                disabled={isFrozen || !draftLoaded}
                onClick={() => void handleAssess()}
                type='button'
              >
                {isAssessing ? 'Avaliando questão…' : 'Avaliar questão'}
              </Button>
            ) : null}
          </div>
          {hasAssessError ? (
            <p className='border-b border-border p-3 text-sm text-selo-text' role='alert'>
              Não foi possível avaliar a questão. Tente novamente.
            </p>
          ) : null}
          <div className='min-h-[28rem] min-w-0 flex-1 lg:min-h-0'>
            <CodeEditor
              files={displayFiles}
              editablePaths={editablePaths}
              readOnly={isFrozen}
              selectedPath={selectedPath}
              onFileChange={handleFileChange}
            />
          </div>
        </div>

        <section
          aria-label='Prática da página'
          className='flex min-h-[24rem] min-w-0 flex-col lg:min-h-0'
        >
          <div className='flex min-h-12 items-center border-b border-border bg-muted px-3'>
            <div
              role='tablist'
              aria-label='Prática'
              className='flex h-full items-stretch'
            >
              <Button
                id='html-preview-tab'
                role='tab'
                aria-controls='html-preview-panel'
                aria-selected={practiceTab === 'preview'}
                onClick={() => handleSelectPracticeTab('preview')}
                type='button'
                variant='ghost'
                className={`rounded-none ${practiceTab === 'preview' ? 'border-b-2 border-success text-foreground' : 'text-muted-foreground'}`}
              >
                Prévia
              </Button>
              <Button
                id='html-terminal-tab'
                role='tab'
                aria-controls='html-terminal-panel'
                aria-selected={practiceTab === 'terminal'}
                onClick={() => handleSelectPracticeTab('terminal')}
                type='button'
                variant='ghost'
                className={`rounded-none ${practiceTab === 'terminal' ? 'border-b-2 border-success text-foreground' : 'text-muted-foreground'}`}
              >
                Terminal
              </Button>
            </div>
          </div>
          <p
            className='border-b border-border px-3 py-2 text-xs text-muted-foreground'
            aria-live='polite'
          >
            {STATUS_LABELS[practiceStatus]}
          </p>
          {practiceTab === 'preview' ? (
            <div
              id='html-preview-panel'
              role='tabpanel'
              aria-labelledby='html-preview-tab'
              className='min-h-[22rem] flex-1 bg-page lg:min-h-0'
            >
              {previewUrl ? (
                <iframe
                  title='Prévia isolada da página'
                  src={previewUrl}
                  sandbox='allow-scripts'
                  referrerPolicy='no-referrer'
                  className='size-full min-h-[22rem] border-0 bg-white'
                />
              ) : (
                <p className='p-4 text-sm text-muted-foreground'>
                  A prévia será exibida aqui quando o ambiente isolado estiver pronto.
                  Você pode continuar editando e avaliar sua resposta.
                </p>
              )}
            </div>
          ) : (
            <div
              id='html-terminal-panel'
              role='tabpanel'
              aria-labelledby='html-terminal-tab'
              className='min-h-[22rem] flex-1 overflow-auto bg-page p-3 lg:min-h-0'
            >
              <div
                role='log'
                aria-live='polite'
                aria-label='Saída do Terminal de prática'
              >
                <pre className='whitespace-pre-wrap break-words font-mono text-xs leading-5 text-foreground'>
                  {terminalText || STATUS_LABELS[practiceStatus]}
                </pre>
              </div>
            </div>
          )}
          <p className='border-t border-border px-3 py-2 text-xs text-muted-foreground'>
            A prévia e a saída do Terminal não influenciam sua nota.
          </p>
        </section>
      </div>
    </section>
  )
}
