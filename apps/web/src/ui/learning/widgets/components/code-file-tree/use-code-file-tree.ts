import { useEffect, useMemo } from 'react'
import {
  hotkeysCoreFeature,
  selectionFeature,
  syncDataLoaderFeature,
} from '@headless-tree/core'
import { useTree } from '@headless-tree/react'

export type CodeFileTreeProps = {
  files: readonly { path: string }[]
  selectedPath: string
  editablePaths?: readonly string[]
  readOnly?: boolean
  onSelectFile: (path: string) => void
}

type FileItem = { name: string; children: string[]; path?: string }

export function useCodeFileTree(props: CodeFileTreeProps) {
  const items = useMemo(() => {
    const nodes: Record<string, FileItem> = {
      root: { name: 'Arquivos', children: [] },
    }
    for (const file of props.files) {
      const segments = file.path.split('/')
      let parentId = 'root'
      for (const [index, name] of segments.entries()) {
        const path = segments.slice(0, index + 1).join('/')
        const isFile = index === segments.length - 1
        const id = `${isFile ? 'file' : 'folder'}:${path}`
        if (!nodes[id])
          nodes[id] = { name, children: [], path: isFile ? file.path : undefined }
        if (!nodes[parentId].children.includes(id)) nodes[parentId].children.push(id)
        parentId = id
      }
    }
    return nodes
  }, [props.files])
  const tree = useTree<FileItem>({
    rootItemId: 'root',
    initialState: {
      expandedItems: Object.keys(items).filter((id) => id.startsWith('folder:')),
      selectedItems: props.selectedPath ? [`file:${props.selectedPath}`] : [],
    },
    getItemName: (item) => item.getItemData().name,
    isItemFolder: (item) => item.getItemData().children.length > 0,
    dataLoader: {
      getItem: (id) => items[id],
      getChildren: (id) => items[id].children,
    },
    onPrimaryAction: (item) => {
      const path = item.getItemData().path
      if (path) {
        item.getTree().setSelectedItems([item.getId()])
        props.onSelectFile(path)
      }
    },
    features: [syncDataLoaderFeature, selectionFeature, hotkeysCoreFeature],
  })

  useEffect(() => {
    tree.setSelectedItems(props.selectedPath ? [`file:${props.selectedPath}`] : [])
  }, [props.selectedPath, tree])

  return { tree }
}
