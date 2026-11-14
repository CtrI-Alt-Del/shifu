# Interface de exclusão — SHIFU-98

Fonte: Pencil design/shifu.pen, consulta MCP em 25/10/2026. Sem alterações na fonte.

| Referência | Estado | Viewport | Checker |
| --- | --- | --- | --- |
| references/y2vJij.png | Aba Excluir conta e cartão | 1440×900 | VM-02 |
| references/LbeWb.png | Confirmação | 1440×900 | VM-02 |
| Mesmas referências | Aba e modal adaptados | 390×844 | VM-02 |

Preservar shell atual e tokens do Shifu. Título Instrument Serif, corpo DM Sans. Superfícies bg-card/bg-muted, texto foreground/muted-foreground, bordas border-border/control-border, foco ring existente. Reutilizar Button, Dialog, Checkbox, Input, Label, Icon e Anchor, sem primitivos paralelos.

Adaptações desta entrega parcial: aviso explícito de indisponibilidade no cartão e modal; texto explica o efeito futuro após encerramento confirmado. Botão final danger desabilitado, conforme documentação/design.md seção 3.3, que prevalece sobre o contorno antigo do modal. Nenhuma promessa de exclusão realizada. Mobile em coluna, margem de 20px, ações de 44px, modal com rolagem interna e botões que cabem na largura. Manter link público de privacidade e contato existentes.

Capturas de implementação pertencem a apps/web/.playwright-cli/screenshots/, não a esta pasta.

O cabeçalho do modal segue a regra UI vigente: ícone semântico à esquerda do título e descrição, botão de fechar isolado no canto superior direito e separador antes do corpo. Esta composição substitui o cabeçalho antigo do quadro LbeWb. Fechar também descarta os campos locais. O aumento de altura no celular pode exigir rolagem interna, preservando o acesso aos controles.
