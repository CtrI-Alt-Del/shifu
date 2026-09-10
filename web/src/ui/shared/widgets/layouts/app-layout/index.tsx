import type { PropsWithChildren } from "react";

import { Anchor } from "@/ui/shared/widgets/components/anchor";
import { Icon } from "@/ui/shared/widgets/components/icon";
import { isSidebarItemActive, useAppLayout } from "./use-app-layout";

export type AppLayoutProps = PropsWithChildren;

export const AppLayout = ({ children }: AppLayoutProps) => {
  const { pathname, primaryItems, secondaryItems } = useAppLayout();

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-[1600px]">
        <aside className="hidden w-72 shrink-0 flex-col border-r border-border bg-sidebar px-5 py-7 lg:flex">
          <div className="flex items-center gap-3 px-3">
            <span className="grid size-10 place-items-center rounded-xl bg-primary text-lg text-primary-foreground shadow-brand">
              <Icon name="sparkles" />
            </span>
            <div>
              <p className="font-serif text-2xl font-bold tracking-tight text-primary">
                Shifu
              </p>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                Aprender melhor
              </p>
            </div>
          </div>

          <nav aria-label="Navegação principal" className="mt-12 space-y-1">
            {primaryItems.map((item) => {
              const isActive = isSidebarItemActive(pathname, item.route);

              return (
                <Anchor
                  aria-current={isActive ? "page" : undefined}
                  className={`flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-semibold transition-colors ${
                    isActive
                      ? "bg-accent text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                  key={item.route}
                  route={item.route}
                >
                  <Icon className="text-lg" name={item.icon} />
                  {item.label}
                </Anchor>
              );
            })}
          </nav>

          <div className="mt-auto border-t border-border pt-5">
            {secondaryItems.map((item) => (
              <Anchor
                className="flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-semibold text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                key={item.route}
                route={item.route}
              >
                <Icon className="text-lg" name={item.icon} />
                {item.label}
              </Anchor>
            ))}
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="border-b border-border bg-card">
            <div className="flex min-h-20 items-center justify-between gap-4 px-5 sm:px-8">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">
                  Espaço do aprendiz
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Seu caminho de aprendizagem em um só lugar.
                </p>
              </div>
              <div className="hidden items-center gap-3 sm:flex">
                <span className="size-2 rounded-full bg-success" />
                <span className="text-sm font-semibold text-muted-foreground">
                  Tudo certo
                </span>
              </div>
            </div>
            <nav
              aria-label="Navegação móvel"
              className="flex gap-2 overflow-x-auto border-t border-border px-5 py-3 lg:hidden sm:px-8"
            >
              {primaryItems.map((item) => {
                const isActive = isSidebarItemActive(pathname, item.route);

                return (
                  <Anchor
                    aria-current={isActive ? "page" : undefined}
                    className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold ${
                      isActive
                        ? "bg-accent text-primary"
                        : "text-muted-foreground hover:bg-muted"
                    }`}
                    key={item.route}
                    route={item.route}
                  >
                    <Icon name={item.icon} />
                    {item.label}
                  </Anchor>
                );
              })}
            </nav>
          </header>

          <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-5 py-8 sm:px-8 lg:px-10">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
};
