# DoD — Definition of Done

Uma issue só pode ser movida para **Concluído** quando todos os critérios aplicáveis ao seu tipo estiverem atendidos e as evidências estiverem registradas no Jira e, quando houver Spec, na respectiva Evaluation. A conclusão deve ser verificável por alguém além de quem implementou.

Para entregas guiadas por Spec, os critérios e as evidências seguem [`documentation/sdd.md`](../sdd.md): cada `CA-*` recebe uma disposição e evidência rastreável (`EV-*`, `VM-*` ou verificação automatizada).

---

## User Stories

- [ ] Todos os critérios de aceitação foram implementados e verificados no fluxo do usuário
- [ ] Regras de negócio, dados, validações e comportamento de IA correspondem ao requisito aprovado
- [ ] Todas as Dev Tasks necessárias foram concluídas e vinculadas à história
- [ ] Validações automatizadas aplicáveis passaram; cenários negativos, falhas e recuperação estão cobertos por testes quando relevantes
- [ ] Validação integrada confirmou as fronteiras envolvidas (por exemplo, web, servidor e persistência), quando aplicável
- [ ] Fluxos visuais foram comparados às referências aprovadas e validados nos dispositivos e tamanhos de tela exigidos pela Spec, quando aplicável
- [ ] Achados de revisão foram resolvidos ou tiveram disposição e evidência registradas
- [ ] PR foi aprovado e integrado; verificações obrigatórias de CI passaram
- [ ] Spec e Evaluation foram atualizadas com resultado por critério, comandos executados, validações manuais e evidências, quando aplicável
- [ ] Jira registra o resultado da entrega e aponta para PR e evidências relevantes
- [ ] Product Owner confirmou os critérios de produto quando a issue exigir aceite explícito

## Dev Tasks

- [ ] Critérios de conclusão técnica definidos na issue foram atendidos
- [ ] Testes relevantes foram criados ou atualizados e passaram conforme as regras da camada afetada
- [ ] Verificações obrigatórias de build e CI passaram; erros introduzidos foram corrigidos
- [ ] Código foi revisado por outra pessoa e o PR foi aprovado e integrado
- [ ] Validação manual e captura de evidência foram concluídas quando exigidas pela Spec ou pelas regras da camada
- [ ] Documentação técnica foi atualizada quando necessária para operar ou manter a entrega
- [ ] Evaluation registra as verificações e evidências da task quando ela pertence a uma entrega guiada por Spec
- [ ] Jira registra o resultado, os comandos e verificações executados e links para PR ou evidências

## Tarefas de documentação ou trabalho sem código

- [ ] Entregável definido na issue foi produzido e está acessível no local acordado
- [ ] Resultado, decisões e links foram registrados na issue
- [ ] Decisões que alteram requisito ou arquitetura foram encaminhadas às fontes canônicas apropriadas
