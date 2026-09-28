# DoR — Definition of Ready

Uma User Story ou Dev Task pode entrar em Sprint quando todos os critérios aplicáveis ao seu tipo estiverem satisfeitos. A issue deve registrar o escopo, as dependências e como o time decidirá se o trabalho foi concluído.

Os requisitos de produto continuam no PRD canônico do Confluence. Para mudanças de comportamento, a Spec local define o contrato de implementação; consulte [`documentation/sdd.md`](../sdd.md).

---

## User Stories

- [ ] Escrita no formato `Como <usuário>, quero <funcionalidade> para <motivação>`, usando os conceitos e nomes do domínio Shifu
- [ ] Campo **Requisito** aponta para a página ou seção relevante do PRD canônico no Confluence
- [ ] Vinculada ao épico correto no Jira
- [ ] Regras de negócio e comportamentos esperados estão descritos na issue, incluindo os de IA quando aplicável
- [ ] Dados envolvidos estão definidos: campos, tipos, origem e validações
- [ ] Critérios de aceitação verificáveis estão descritos no formato `Dado / Quando / Então`
- [ ] Dependências, decisões pendentes e limites de escopo estão registrados
- [ ] Protótipo ou referência do Pencil está aprovado quando a entrega altera uma interface
- [ ] Estimativa foi atribuída pelo time durante o planejamento
- [ ] Dev Tasks necessárias foram criadas, vinculadas à história e estimadas individualmente
- [ ] Não há bloqueador ou dependência externa sem responsável e plano de resolução
- [ ] Para mudança de comportamento, os `RP-*` e `JN-*` aplicáveis foram identificados e a Spec local está planejada; ela deve estar `ready` antes da implementação

## Dev Tasks

- [ ] Título descreve a entrega de forma clara e objetiva
- [ ] Objetivo, escopo e exclusões estão descritos na issue
- [ ] Camada ou responsabilidade está identificada (por exemplo, `web`, `server`, persistência, IA ou infraestrutura)
- [ ] Critérios de conclusão técnica são observáveis e verificáveis
- [ ] Vínculo com a User Story correspondente está definido no Jira (por exemplo, relação `blocks`, conforme o fluxo da entrega)
- [ ] Campo **Requisito** aponta para o PRD canônico quando a task implementa um requisito de produto
- [ ] Estratégia de validação e evidências esperadas estão definidas, incluindo testes automatizados aplicáveis
- [ ] Dependências, referências de design e decisões pendentes estão registradas
- [ ] Estimativa foi atribuída individualmente pelo time
- [ ] Responsável e Sprint estão definidos antes do início do trabalho
- [ ] Task tem tamanho adequado para ser concluída e validada dentro da Sprint
- [ ] Não existe outra Dev Task cobrindo o mesmo escopo e não há bloqueadores sem plano de resolução
