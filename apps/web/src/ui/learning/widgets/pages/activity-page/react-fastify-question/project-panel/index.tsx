import type { ReactNode } from 'react'
import { CodeEditor } from '@/ui/learning/widgets/components/code-editor'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/ui/shadcn/tabs'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { CodeFileTree } from '@/ui/learning/widgets/components/code-file-tree'
import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
export type ProjectPanelProps = {
  statement: ReactNode
  onFileChange: (path: string, content: string) => void
  files: readonly { path: string; content: string }[]
  selectedPath: string
  editablePaths: readonly string[]
  readOnly: boolean
  canAddFile: boolean
  newFilePath: string
  policyText: string
  onSelectFile: (path: string) => void
  onNewFilePathChange: (path: string) => void
  onAddFile: () => void
}
export const ProjectPanel = (props: ProjectPanelProps) => (
  <>
    <Tabs
      defaultValue='statement'
      className='min-w-0 overflow-auto border-r border-border bg-surface-alt'
    >
      <TabsList className='w-full rounded-none border-x-0 border-t-0'>
        <TabsTrigger value='statement'>Enunciado</TabsTrigger>
        <TabsTrigger value='files'>Arquivos</TabsTrigger>
      </TabsList>
      <TabsContent value='statement' className='space-y-5 p-4'>
        {props.statement}
      </TabsContent>
      <TabsContent value='files'>
        <section aria-label='Arquivos do projeto' className='min-w-0 space-y-3 p-3'>
          <div className='flex items-center justify-between gap-2'>
            <h2 className='font-mono text-xs text-muted-foreground'>
              ARQUIVOS DO PROJETO
            </h2>
            {props.canAddFile ? (
              <Button
                variant='ghost'
                aria-label='Novo arquivo'
                onClick={props.onAddFile}
                className='min-h-11 min-w-11'
              >
                <Icon name='file-plus' aria-hidden='true' size={16} />
              </Button>
            ) : null}
          </div>
          {props.canAddFile ? (
            <label htmlFor='integrated-new-file' className='block space-y-1 text-xs'>
              Caminho do novo arquivo
              <Input
                id='integrated-new-file'
                className='min-h-11 font-mono text-xs'
                value={props.newFilePath}
                placeholder='src/components/Novo.tsx'
                onChange={(event) => props.onNewFilePathChange(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') props.onAddFile()
                }}
              />
            </label>
          ) : null}
          <CodeFileTree
            key={props.files.map((file) => file.path).join('\0')}
            files={props.files}
            selectedPath={props.selectedPath}
            editablePaths={props.editablePaths}
            readOnly={props.readOnly}
            onSelectFile={props.onSelectFile}
          />
          <p className='text-xs leading-5 text-muted-foreground'>{props.policyText}</p>
        </section>
      </TabsContent>
    </Tabs>
    <div className='h-[28rem] min-h-[28rem] min-w-0 overflow-hidden border-r border-border lg:h-full [&>section]:h-full'>
      <CodeEditor
        files={props.files}
        editablePaths={props.editablePaths}
        selectedPath={props.selectedPath}
        readOnly={props.readOnly}
        onFileChange={props.onFileChange}
      />
    </div>
  </>
)
