import * as TabsPrimitive from '@radix-ui/react-tabs'
import type { ComponentProps } from 'react'

export const Tabs = TabsPrimitive.Root

export const TabsList = ({
  className = '',
  ...props
}: ComponentProps<typeof TabsPrimitive.List>) => (
  <TabsPrimitive.List
    className={`inline-flex min-h-11 gap-1 rounded-md border border-control-border bg-muted p-1 ${className}`}
    {...props}
  />
)

export const TabsTrigger = ({
  className = '',
  ...props
}: ComponentProps<typeof TabsPrimitive.Trigger>) => (
  <TabsPrimitive.Trigger
    className={`min-h-9 rounded px-3 text-sm font-semibold text-muted-foreground transition-colors data-[state=active]:bg-card data-[state=active]:text-foreground ${className}`}
    {...props}
  />
)

export const TabsContent = TabsPrimitive.Content
