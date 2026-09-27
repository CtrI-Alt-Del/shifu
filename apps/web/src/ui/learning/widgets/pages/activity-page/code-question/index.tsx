import type { CSSProperties } from 'react'
import { CodeEditor } from '@/ui/learning/widgets/components/code-editor'
import { CodeFileTree } from '@/ui/learning/widgets/components/code-file-tree'
import { Button } from '@/ui/shadcn/button'
import { ActivityQuestionHeader } from '../components/activity-question-header'
import { CodeTerminal } from './code-terminal'
import { PanelResizeHandle } from './panel-resize-handle'
import { type CodeQuestionProps, useCodeQuestion } from './use-code-question'
import './code-question.css'

export type { CodeQuestionProps } from './use-code-question'

export const CodeQuestion = (props: CodeQuestionProps) => {
  const {
    files,
    editablePaths,
    hasAssessError,
    isAssessing,
    isFrozen,
    runner,
    selectedPanel,
    selectedPath,
    sidebarWidth,
    editorWidth,
    resizeValues,
    workspaceRef,
    editorGridRef,
    handleAssess,
    handleFileChange,
    handleSelectFile,
    handleSelectPanel,
    handleResizePointerDown,
    handleResizePointerMove,
    handleResizePointerEnd,
    handleResizeKeyDown,
  } = useCodeQuestion(props)
  const questionNumber = props.questionNumber ?? 1
  const totalQuestions = props.totalQuestions ?? questionNumber
  return (
    <section
      aria-label='Questão de código'
      className='flex min-h-0 min-w-0 flex-1 flex-col gap-3.5 lg:h-[calc(100dvh-7.25rem)] lg:flex-none lg:min-h-[28rem]'
    >
      <ActivityQuestionHeader
        activityTitle={props.activityTitle ?? 'Questão de código'}
        difficulty={props.difficulty}
        questionNumber={questionNumber}
        totalQuestions={totalQuestions}
      />
      <div
        ref={workspaceRef}
        data-read-only={Boolean(props.readOnly)}
        className='code-question-workspace grid min-h-0 min-w-0 flex-1 border border-border bg-card lg:grid-rows-[minmax(0,1fr)]'
        style={{ '--sidebar-width': `${sidebarWidth}px` } as CSSProperties}
      >
        <aside className='flex min-w-0 flex-col border-b border-border bg-surface-alt lg:min-h-0 lg:border-r lg:border-b-0'>
          <div className='flex h-[52px] shrink-0 items-center border-b border-border bg-muted px-4'>
            <span className='font-mono text-[10px] font-semibold tracking-wide text-muted-foreground'>
              ESPAÇO DE CÓDIGO
            </span>
          </div>
          <div
            className='flex h-[42px] shrink-0 items-stretch border-b border-border bg-muted px-2'
            role='tablist'
            aria-label='Informações da questão'
          >
            <Button
              id='activity-question-prompt-tab'
              role='tab'
              aria-controls='activity-question-panel'
              aria-selected={selectedPanel === 'prompt'}
              type='button'
              variant='ghost'
              className={`relative !min-h-0 h-[42px] rounded-none px-2 text-xs after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 ${selectedPanel === 'prompt' ? 'after:bg-success text-foreground' : 'after:bg-transparent text-muted-foreground'}`}
              onClick={() => handleSelectPanel('prompt')}
            >
              Enunciado
            </Button>
            <Button
              id='activity-question-files-tab'
              role='tab'
              aria-controls='activity-question-panel'
              aria-selected={selectedPanel === 'files'}
              type='button'
              variant='ghost'
              className={`relative !min-h-0 h-[42px] rounded-none px-2 text-xs after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 ${selectedPanel === 'files' ? 'after:bg-success text-foreground' : 'after:bg-transparent text-muted-foreground'}`}
              onClick={() => handleSelectPanel('files')}
            >
              Arquivos
            </Button>
          </div>
          <div
            id='activity-question-panel'
            role='tabpanel'
            aria-labelledby={
              selectedPanel === 'prompt'
                ? 'activity-question-prompt-tab'
                : 'activity-question-files-tab'
            }
            className='min-h-0 flex-1 space-y-4 overflow-y-auto p-4'
          >
            {selectedPanel === 'prompt' ? (
              <>
                <p className='whitespace-pre-wrap text-[13px] leading-5 text-foreground/80'>
                  {props.question.prompt}
                </p>
                <div className='space-y-2 rounded-md bg-jade-tint p-3'>
                  <h2 className='text-sm font-semibold text-success'>
                    Como será avaliado
                  </h2>
                  <p className='text-xs leading-5 text-foreground/80'>
                    Sua avaliação usa a rubrica desta questão. A prática no Terminal ajuda
                    a testar sua solução.
                  </p>
                </div>
              </>
            ) : (
              <CodeFileTree
                files={files}
                selectedPath={selectedPath}
                editablePaths={editablePaths}
                readOnly={isFrozen}
                onSelectFile={handleSelectFile}
              />
            )}
          </div>
        </aside>
        {!props.readOnly ? (
          <PanelResizeHandle
            label='Redimensionar enunciado e editor'
            {...resizeValues.sidebar}
            onPointerDown={(event) => handleResizePointerDown('sidebar', event)}
            onPointerMove={(event) => handleResizePointerMove('sidebar', event)}
            onPointerUp={handleResizePointerEnd}
            onPointerCancel={handleResizePointerEnd}
            onKeyDown={(event) => handleResizeKeyDown('sidebar', event)}
          />
        ) : null}
        <div className='flex min-h-0 min-w-0 flex-col'>
          <div className='flex min-h-[52px] shrink-0 items-center justify-end border-b border-border bg-muted px-4'>
            {!props.readOnly ? (
              <Button
                type='button'
                disabled={isFrozen}
                className='lg:!min-h-0 lg:h-10 lg:px-4 lg:text-sm'
                onClick={() => void handleAssess()}
              >
                {isAssessing ? 'Avaliando questão…' : 'Avaliar questão'}
              </Button>
            ) : null}
          </div>
          {hasAssessError ? (
            <p
              role='alert'
              className='shrink-0 border-b border-border p-3 text-sm text-destructive'
            >
              Não foi possível avaliar a questão. Tente novamente.
            </p>
          ) : null}
          <div
            ref={editorGridRef}
            data-read-only={Boolean(props.readOnly)}
            className='code-question-editor-grid grid min-h-0 min-w-0 flex-1 lg:grid-rows-[minmax(0,1fr)]'
            style={
              {
                '--editor-left': editorWidth === null ? '55fr' : `${editorWidth}px`,
                '--editor-right': editorWidth === null ? '45fr' : '1fr',
              } as CSSProperties
            }
          >
            <CodeEditor
              files={files}
              editablePaths={editablePaths}
              readOnly={isFrozen}
              selectedPath={selectedPath}
              onFileChange={handleFileChange}
            />
            {!props.readOnly ? (
              <PanelResizeHandle
                label='Redimensionar editor e terminal'
                {...resizeValues.editor}
                onPointerDown={(event) => handleResizePointerDown('editor', event)}
                onPointerMove={(event) => handleResizePointerMove('editor', event)}
                onPointerUp={handleResizePointerEnd}
                onPointerCancel={handleResizePointerEnd}
                onKeyDown={(event) => handleResizeKeyDown('editor', event)}
              />
            ) : null}
            {!props.readOnly ? (
              <div className='min-h-[28rem] min-w-0 border-t border-border lg:min-h-0 lg:overflow-hidden lg:border-t-0 lg:border-l'>
                <CodeTerminal runner={runner} />
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  )
}
