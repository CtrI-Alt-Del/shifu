import { ActivityQuestionHeader } from '../components/activity-question-header'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Button } from '@/ui/shadcn/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/ui/shadcn/tabs'
import { ProjectPanel } from './project-panel'
import { PreviewPanel } from './preview-panel'
import { HttpPanel } from './http-panel'
import { TerminalPanel } from './terminal-panel'
import {
  useReactFastifyQuestion,
  type ReactFastifyQuestionProps,
} from './use-react-fastify-question'
export type { ReactFastifyQuestionProps } from './use-react-fastify-question'
export const ReactFastifyQuestion = (props: ReactFastifyQuestionProps) => {
  const {
    draftLoaded,
    isDraftInvalidated,
    hasSaveError,
    isSaving,
    totalSourceBytes,
    isFrozen,
    hasFileError,
    hasAssessError,
    displayFiles,
    selectedPath,
    editorEditablePaths,
    newFilePath,
    additionalFilesCount,
    frontendStatus,
    apiStatus,
    previewUrl,
    terminalText,
    handleAssess,
    handleSelectFile,
    handleNewFilePathChange,
    handleAddFile,
    handleFileChange,
    handleRequest,
    handleRunCommand,
  } = useReactFastifyQuestion(props)
  const policy = props.question.additionalFilePolicy
  return (
    <section
      aria-label='Questão React + Fastify'
      className='mx-auto flex min-w-0 w-full max-w-7xl flex-col gap-3 pb-4'
    >
      <ActivityQuestionHeader
        activityTitle={props.activityTitle ?? 'React + Fastify'}
        difficulty={props.difficulty}
        questionNumber={props.questionNumber}
        totalQuestions={props.totalQuestions}
        showQuestionProgress
      />
      <div className='border border-border bg-card'>
        <div className='flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-2'>
          <output className='text-xs text-muted-foreground'>
            {!draftLoaded
              ? 'Validando a Atividade…'
              : !props.isOnlineAuthority
                ? 'Conecte-se para validar seu rascunho.'
                : isDraftInvalidated
                  ? 'Rascunho invalidado. Atualize a Atividade.'
                  : hasSaveError
                    ? 'Falha ao salvar. Há risco de perda ao sair.'
                    : isSaving
                      ? 'Salvando neste navegador…'
                      : 'Rascunho salvo neste navegador'}{' '}
            · {(totalSourceBytes / 1024).toFixed(1)} / 256 KB
          </output>
          <Button
            disabled={
              isFrozen ||
              isDraftInvalidated ||
              !draftLoaded ||
              !props.isOnlineAuthority ||
              !props.onAssess
            }
            onClick={() => void handleAssess()}
          >
            Avaliar questão
          </Button>
        </div>
        {hasFileError ? (
          <p role='alert' className='p-3 text-sm text-selo-text'>
            Arquivo fora da política permitida ou limite do projeto excedido.
          </p>
        ) : null}
        {hasAssessError ? (
          <p role='alert' className='p-3 text-sm text-selo-text'>
            Não foi possível avaliar. Tente novamente.
          </p>
        ) : null}
        <div className='grid min-w-0 lg:h-[calc(100dvh-15rem)] lg:min-h-[32rem] lg:grid-cols-[minmax(14rem,0.65fr)_minmax(20rem,1.3fr)_minmax(20rem,1.15fr)]'>
          <ProjectPanel
            files={displayFiles}
            selectedPath={selectedPath}
            editablePaths={editorEditablePaths}
            readOnly={isFrozen || isDraftInvalidated || !draftLoaded}
            canAddFile={Boolean(policy && !isFrozen && !isDraftInvalidated)}
            newFilePath={newFilePath}
            policyText={
              policy
                ? `Pastas: ${policy.allowedDirectories.join(', ')}. Extensões: ${policy.allowedExtensions.join(', ')}. ${additionalFilesCount}/${policy.maxFiles} adicionais.`
                : 'Esta questão não permite arquivos adicionais.'
            }
            onSelectFile={handleSelectFile}
            onNewFilePathChange={handleNewFilePathChange}
            onAddFile={handleAddFile}
            onFileChange={handleFileChange}
            statement={
              <>
                <p className='font-mono text-xs text-jade-text'>
                  REACT + FASTIFY · PROJETO INTEGRADO
                </p>
                <QuestionPrompt
                  id={`integrated-prompt-${props.question.key}`}
                  prompt={props.question.prompt}
                  size='result'
                />
                <section
                  aria-label='Critérios de avaliação'
                  className='space-y-3 rounded-md bg-jade-tint p-4'
                >
                  <h2 className='text-sm font-semibold text-jade-text'>
                    Como será avaliado
                  </h2>
                  <p className='text-xs leading-5'>
                    A rubrica avalia os arquivos enviados, incluindo os adicionais
                    permitidos. Use a prévia e o painel HTTP para experimentar.
                  </p>
                  <ul className='space-y-2'>
                    {props.question.criteria.map((criterion) => (
                      <li
                        key={criterion.key}
                        className='flex justify-between gap-3 text-xs'
                      >
                        <span>{criterion.name}</span>
                        <span className='shrink-0 font-mono'>
                          Peso {criterion.weightPercentage}%
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              </>
            }
          />
          <Tabs
            defaultValue='preview'
            className='flex min-h-96 min-w-0 flex-col overflow-hidden'
          >
            <TabsList className='w-full justify-start rounded-none border-x-0 border-t-0'>
              <TabsTrigger value='preview'>Prévia</TabsTrigger>
              <TabsTrigger value='http'>HTTP</TabsTrigger>
              <TabsTrigger value='terminal'>Terminal</TabsTrigger>
            </TabsList>
            <TabsContent value='preview' className='min-h-0 flex-1 overflow-auto'>
              <PreviewPanel
                frontendStatus={frontendStatus}
                apiStatus={apiStatus}
                previewUrl={previewUrl}
              />
            </TabsContent>
            <TabsContent value='http' className='overflow-auto'>
              <HttpPanel
                examples={props.question.httpExamples}
                isReady={apiStatus === 'ready'}
                onRequest={handleRequest}
              />
            </TabsContent>
            <TabsContent value='terminal' className='overflow-auto'>
              <TerminalPanel
                transcript={terminalText}
                commands={props.question.permittedCommands}
                onRunCommand={handleRunCommand}
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </section>
  )
}
