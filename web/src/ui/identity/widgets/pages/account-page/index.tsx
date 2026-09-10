import { ModulePageHeader } from "@/ui/shared/widgets/components/module-page-header";

const accountSections = [
  { description: "Nome, e-mail e segurança da sua conta.", status: "Em preparação", title: "Dados da conta" },
  { description: "Ajuste o jeito que o Shifu acompanha seu ritmo.", status: "Em preparação", title: "Preferências de aprendizagem" },
  { description: "Entenda como seus dados participam da experiência.", status: "Disponível na próxima etapa", title: "Privacidade" },
] as const;

export const AccountPage = () => {
  return (
    <div className="space-y-10">
      <ModulePageHeader
        description="Seu espaço pessoal para acompanhar a conta, as preferências e a forma como você aprende."
        eyebrow="Módulo identidade"
        title="Minha conta"
      />

      <section className="flex flex-col gap-6 rounded-3xl border border-border bg-card p-7 shadow-card sm:flex-row sm:items-center sm:p-9">
        <div className="grid size-20 shrink-0 place-items-center rounded-3xl bg-accent font-serif text-3xl font-bold text-primary">AS</div>
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.14em] text-primary">Perfil do aprendiz</p>
          <h2 className="mt-2 font-serif text-3xl font-bold">Aprendiz Shifu</h2>
          <p className="mt-2 text-muted-foreground">Seu perfil está pronto para ganhar contexto ao longo da jornada.</p>
        </div>
      </section>

      <section>
        <p className="text-sm font-bold uppercase tracking-[0.14em] text-primary">Configurações</p>
        <h2 className="mt-2 font-serif text-2xl font-bold">Cuide do seu espaço</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          {accountSections.map((section) => (
            <article className="rounded-2xl border border-border bg-card p-6 shadow-card" key={section.title}>
              <h3 className="font-serif text-xl font-bold">{section.title}</h3>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">{section.description}</p>
              <p className="mt-6 text-xs font-bold uppercase tracking-[0.1em] text-primary">{section.status}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
};
