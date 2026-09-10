import { HeadContent, Scripts } from "@tanstack/react-router";
import type { PropsWithChildren } from "react";

import { RestContextProvider } from "@/ui/shared/contexts/rest-context";
import { AppLayout } from "@/ui/shared/widgets/layouts/app-layout";

export type RootLayoutProps = PropsWithChildren;

export const RootLayout = ({ children }: RootLayoutProps) => {
  return (
    <html lang="pt-BR">
      <head>
        <HeadContent />
      </head>
      <body>
        <RestContextProvider>
          <AppLayout>{children}</AppLayout>
        </RestContextProvider>
        <Scripts />
      </body>
    </html>
  );
};
