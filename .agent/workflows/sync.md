---
description: Sincronizar status dos planos, sessões e roadmap após um commit no meio de uma sessão.
---
# Sincronização de Documentação (Meio de Sessão)

Sempre que o usuário chamar `@[/sync]`, você deve parar a execução de código e garantir que a base de conhecimento (documentação) do projeto reflita com precisão o que acabou de ser concluído e commitado.

 Siga estes passos na ordem:

1. **Entenda o Contexto Recente:** Analise rapidamente o que acabou de ser implementado e commitado antes da chamada deste workflow.
2. **Atualize o PLAN:**
   - Localize o plano correspondente (`docs/<atividade>/PLAN_*.md`).
   - Usando Replace File Content, altere `[ ]` para `[x]` nas fases que acabaram de ser concluídas.
3. **Atualize o SESSIONS_LOG:**
   - Vá ao arquivo `SESSIONS_LOG.md`.
   - Na entrada da sessão atual, adicione um bullet point documentando o que acabou de ser concluído de forma sucinta.
4. **Verifique Conclusão Total:**
   - Se *todas* as fases do Plano estiverem concluídas, abra o `ROADMAP.md` e mova a respectiva feature de `🔴 Em Progresso` para `🟢 Concluído/Entregue`.
   - Caso contrário, não altere o ROADMAP.

Retorne uma resposta curta e direta apenas confirmando quais documentos foram atualizados, sem alongar muito a conversa, para que o usuário possa voltar rapidamente ao desenvolvimento.
