import { ActivityQuestionHeader } from '../components/activity-question-header'
import { CodeEditor } from '@/ui/learning/widgets/components/code-editor'
import { CodeFileTree } from '@/ui/learning/widgets/components/code-file-tree'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
import { useReactQuestion, type ReactQuestionProps } from './use-react-question'

export type { ReactQuestionProps } from './use-react-question'

export const ReactQuestion = (props: ReactQuestionProps) => {
  const {
    files,
    displayFiles,
    selectedPath,
    editorEditablePaths,
    additionalFilesCount,
    draftLoaded,
    isSaving,
    hasSaveError,
    isAssessing,
    hasAssessError,
    status,
    previewUrl,
    terminalText,
    newFilePath,
    hasFileError,
    isDraftInvalidated,
    totalSourceBytes,
    isFrozen,
    handleAddFile,
    handleAssess,
    handleFileChange,
    handleSelectFile,
    handleNewFilePathChange,
  } = useReactQuestion(props)
  const totalQuestions = props.totalQuestions || props.questionNumber
  const policy = props.question.additionalFilePolicy
  const canAddFile = Boolean(policy && !isFrozen && !isDraftInvalidated)
  return (
    <section
      aria-label='Questão React'
      className='mx-auto flex min-h-0 w-full max-w-[1440px] flex-1 flex-col gap-3 px-3 pb-4 sm:px-5 lg:h-[calc(100dvh-7.25rem)] lg:flex-none lg:px-6'
    >
      <ActivityQuestionHeader
        activityTitle={props.activityTitle ?? 'Questão React'}
        difficulty={props.difficulty}
        questionNumber={props.questionNumber}
        totalQuestions={totalQuestions}
        showQuestionProgress
      />
      <div className='flex flex-wrap items-center justify-between gap-2 border border-border bg-muted px-3 py-2 text-xs'>
        <p aria-live='polite' className='min-h-5 text-muted-foreground'>
          {props.isDiagnostic
            ? 'Diagnóstico não salva rascunhos.'
            : !draftLoaded
              ? 'Validando a Atividade…'
              : !props.isOnlineAuthority
                ? 'Conecte-se para validar e restaurar seu rascunho.'
                : isDraftInvalidated
                  ? 'Rascunho invalidado. Atualize a Atividade para validar novamente.'
                  : hasSaveError
                    ? 'Não foi possível salvar localmente. Sua resposta não foi enviada.'
                    : isSaving
                      ? 'Salvando neste navegador…'
                      : 'Rascunho salvo neste navegador'}
        </p>
        <span className='font-mono text-muted-foreground'>
          {(totalSourceBytes / 1024).toFixed(1)} / 256 KB
        </span>
      </div>
      <div className='grid min-h-0 flex-1 gap-3 overflow-y-auto lg:grid-cols-[minmax(15rem,0.9fr)_minmax(20rem,1.35fr)_minmax(16rem,1fr)] lg:overflow-hidden'>
        <aside className='flex min-h-[18rem] min-w-0 flex-col border border-border bg-surface-alt lg:min-h-0'>
          <div className='border-b border-border p-4'>
            <QuestionPrompt
              id={`react-question-prompt-${props.question.key}`}
              prompt={props.question.prompt}
              size='result'
            />
            <section
              aria-label='Critérios de avaliação'
              className='mt-4 space-y-2 rounded-md bg-jade-tint p-3'
            >
              <h2 className='text-sm font-semibold text-success'>Como será avaliado</h2>
              <ul className='space-y-2'>
                {props.question.criteria.map((criterion) => (
                  <li
                    key={criterion.key}
                    className='flex items-start justify-between gap-3 text-xs leading-5'
                  >
                    <span className='min-w-0 break-words'>{criterion.name}</span>
                    <span className='shrink-0 font-mono text-foreground/80'>
                      Peso {criterion.weightPercentage}%
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          </div>
          <div className='flex min-h-0 flex-1 flex-col p-3'>
            <div className='flex items-center justify-between gap-2 pb-2'>
              <h2 className='text-sm font-semibold'>Arquivos do projeto</h2>
              <span className='text-xs text-muted-foreground'>
                {files.length} arquivos editáveis
              </span>
            </div>
            <div className='min-h-24 flex-1 overflow-auto'>
              <CodeFileTree
                key={displayFiles.map((file) => file.path).join('\u0000')}
                files={displayFiles}
                selectedPath={selectedPath}
                editablePaths={editorEditablePaths}
                readOnly={isFrozen}
                onSelectFile={handleSelectFile}
              />
            </div>
            {canAddFile ? (
              <div className='space-y-2 border-t border-border pt-3'>
                <label
                  className='text-xs font-medium'
                  htmlFor='react-additional-file-path'
                >
                  Criar arquivo permitido
                </label>
                <div className='flex gap-2'>
                  <Input
                    id='react-additional-file-path'
                    aria-label='Caminho do novo arquivo'
                    value={newFilePath}
                    onChange={(event) => handleNewFilePathChange(event.target.value)}
                    placeholder='src/components/Novo.tsx'
                    disabled={isFrozen}
                    className='h-10 min-w-0 font-mono text-xs'
                  />
                  <Button
                    type='button'
                    variant='ghost'
                    onClick={handleAddFile}
                    disabled={isFrozen}
                    className='border border-control-border'
                  >
                    Criar
                  </Button>
                </div>
                <p className='text-xs leading-5 text-muted-foreground'>
                  {policy
                    ? `Pastas: ${policy.allowedDirectories.join(', ')} · extensões: ${policy.allowedExtensions.join(', ')} · ${additionalFilesCount}/${policy.maxFiles} arquivos adicionais`
                    : ''}
                </p>
              </div>
            ) : (
              <p className='border-t border-border pt-3 text-xs text-muted-foreground'>
                Esta questão não permite arquivos adicionais.
              </p>
            )}
          </div>
        </aside>
        <section
          aria-label='Editor de código'
          className='flex min-h-[22rem] min-w-0 flex-col border border-border bg-card lg:min-h-0'
        >
          <div className='flex min-h-11 items-center justify-between gap-3 border-b border-border px-3'>
            <span className='min-w-0 truncate font-mono text-xs text-muted-foreground'>
              {selectedPath || 'Nenhum arquivo'}
            </span>
            <Button
              type='button'
              disabled={
                isFrozen ||
                isDraftInvalidated ||
                !draftLoaded ||
                !props.isOnlineAuthority ||
                !props.onAssess
              }
              onClick={() => void handleAssess()}
            >
              {isAssessing ? 'Avaliando…' : 'Avaliar questão'}
            </Button>
          </div>
          {hasAssessError ? (
            <p
              role='alert'
              className='border-b border-border p-3 text-sm text-destructive'
            >
              Não foi possível avaliar a questão. Tente novamente.
            </p>
          ) : null}
          {hasFileError ? (
            <p
              role='alert'
              className='border-b border-border p-3 text-sm text-destructive'
            >
              Arquivo fora da política permitida ou limite de projeto excedido.
            </p>
          ) : null}
          <div className='min-h-[20rem] flex-1 lg:min-h-0'>
            <CodeEditor
              files={displayFiles}
              editablePaths={editorEditablePaths}
              readOnly={isFrozen || isDraftInvalidated || !draftLoaded}
              selectedPath={selectedPath}
              onFileChange={handleFileChange}
            />
          </div>
          <p className='border-t border-border px-3 py-2 text-xs text-muted-foreground'>
            A prévia e o Terminal servem para praticar. Eles não definem a avaliação.
          </p>
        </section>
        <div className='grid min-h-[24rem] gap-3 lg:min-h-0 lg:grid-rows-[minmax(12rem,1fr)_minmax(10rem,0.8fr)]'>
          <section
            aria-label='Prévia da aplicação React'
            className='flex min-h-[12rem] min-w-0 flex-col border border-border bg-card'
          >
            <div className='flex min-h-11 items-center justify-between border-b border-border px-3'>
              <h2 className='text-sm font-semibold'>Prévia</h2>
              <span className='text-xs text-muted-foreground'>
                {status === 'ready' && previewUrl ? 'Em execução' : 'Indisponível'}
              </span>
            </div>
            {previewUrl ? (
              <iframe
                title='Prévia isolada da aplicação React'
                src={previewUrl}
                sandbox='allow-scripts'
                referrerPolicy='no-referrer'
                className='min-h-0 flex-1 bg-white'
              />
            ) : (
              <p aria-live='polite' className='p-4 text-sm text-muted-foreground'>
                {status === 'booting'
                  ? 'Iniciando a prévia…'
                  : 'A prévia não está disponível. Você ainda pode editar e avaliar sua resposta.'}
              </p>
            )}
          </section>
          <section
            aria-label='Terminal de prática'
            className='flex min-h-[10rem] min-w-0 flex-col border border-border bg-card'
          >
            <div className='flex min-h-11 items-center justify-between border-b border-border px-3'>
              <h2 className='text-sm font-semibold'>Terminal</h2>
              <span className='text-xs text-muted-foreground'>
                {status === 'booting'
                  ? 'Iniciando'
                  : status === 'ready'
                    ? 'Pronto'
                    : 'Indisponível'}
              </span>
            </div>
            <pre
              aria-live='polite'
              role='log'
              className='min-h-0 flex-1 overflow-auto whitespace-pre-wrap p-3 font-mono text-xs text-foreground'
            >
              {terminalText || 'A saída da prática aparecerá aqui.'}
            </pre>
          </section>
        </div>
      </div>
    </section>
  )
}
