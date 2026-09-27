import { FileCode2, Folder, FolderOpen } from 'lucide-react'
import { Tree, TreeItem, TreeItemLabel } from '@/ui/shadcn/tree'
import { type CodeFileTreeProps, useCodeFileTree } from './use-code-file-tree'

export const CodeFileTree = (props: CodeFileTreeProps) => {
  const { tree } = useCodeFileTree(props)
  return (
    <Tree tree={tree} role='tree' aria-label='Arquivos do projeto' className='min-w-0'>
      {tree.getItems().map((item) => {
        const { path } = item.getItemData()
        const isEditable = Boolean(
          path && !props.readOnly && props.editablePaths?.includes(path),
        )
        return (
          <TreeItem key={item.getId()} item={item} className='w-full text-left'>
            <TreeItemLabel className='min-w-0 bg-transparent px-2 py-1.5 text-sm text-foreground hover:bg-transparent in-data-[selected=true]:bg-transparent in-data-[selected=true]:font-semibold in-data-[selected=true]:text-foreground in-data-[drag-target=true]:bg-transparent in-data-[search-match=true]:bg-transparent!'>
              {item.isFolder() ? (
                item.isExpanded() ? (
                  <FolderOpen
                    aria-hidden='true'
                    className='size-4 text-muted-foreground'
                  />
                ) : (
                  <Folder aria-hidden='true' className='size-4 text-muted-foreground' />
                )
              ) : (
                <FileCode2 aria-hidden='true' className='size-4 text-muted-foreground' />
              )}
              <span className='min-w-0 truncate'>{item.getItemName()}</span>
              {path ? (
                <span className='sr-only'>
                  {isEditable ? ' editável' : ' somente leitura'}
                </span>
              ) : null}
            </TreeItemLabel>
          </TreeItem>
        )
      })}
    </Tree>
  )
}
