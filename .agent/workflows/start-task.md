---
description: Inicia a arquitetura determinística de agentes (Carrega o framework e prepara a Etapa Zero)
---

Sempre que este workflow for chamado, um agente "limpo" assume a postura de "Gemini Agent (Executor)" sob o framework de controle restrito. Siga os passos na ordem:

1. **Bootstrap (Obrigatório):** Utilize a ferramenta `view_file` para ler imediatamente o arquivo `AGENT.md` na raiz do projeto. Ele contém os seus limites, as tags mecânicas e o fluxo que você deve respeitar (CYCLE FLOW).
2. **Carregamento de Memória Dinâmica:** Utilize a ferramenta `view_file` para ler o arquivo `.agent/memory/context.md`. É lá que moram as restrições em andamento desta máquina.
3. **Aguardar Instrução:** Encerre sua ação (não crie planos e nem modifique nada) e escreva para o usuário que a injeção do framework foi concluída com sucesso. 
4. Peça ao usuário para informar a **User Story** para que você possa redigir o `spec.md` inicial.
