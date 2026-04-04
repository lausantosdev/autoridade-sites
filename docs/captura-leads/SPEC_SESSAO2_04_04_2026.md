# SPEC — Sessão 2 (04/04/2026): Alinhamento da Home (React)

> **Atividade:** Captura de Leads — Frontend (React)
> **Plano associado:** `PLAN_CAPTURA_LEADS_04_04_2026.md`
> **Arquivos principais:** `frontend/src/components/ContactForm.jsx`, `frontend/src/index.css` (ou arquivos CSS locais)
> **Pré-requisito:** Sessão 1 (Subpáginas) concluída

---

## Objetivo da Sessão
O formulário de leads nas subpáginas e templates HTML estáticos (`page.html` e fallback do `index.html`) já possui a nova lógica UX: card isolado, botão cinza nativo com CSS `:valid` e JS validando campos vazios.

Porém, a **Home gerada pelo React** (`index.html` pós-processado pelo frontend) processa o próprio formulário via componente dinâmico. O objetivo desta sessão é replicar todas as convenções validadas na Sessão 1 dentro de `ContactForm.jsx`, eliminando o transbordo (`overflow`) móvel e padronizando a comunicação.

---

## Sumário de Fases

- [ ] Fase 1: Identificação e Limpeza do CSS local em `ContactForm.jsx`
- [ ] Fase 2: Implementação da estrutura HTML e classes base (`.lead-form`) no React
- [ ] Fase 3: Build e Teste do bundle (`npm run build` na pasta frontend)
- [ ] Fase 4: Validação E2E no SiteGen Builder local (`petvida.test`)

---

## Detalhamento das Fases

### Fase 1 — Limpeza Estrutural
- Localizar `frontend/src/components/ContactForm.jsx`.
- Remover atributos inlines ou dependências de CSS exclusivas do React que possam conflitar com o `widget.css`. 
- Atualizar títulos hardcoded (ex: `"Agende uma consulta agora!"`) para suportar a comunicação genérica aprovada: `"Fale Conosco"`.

### Fase 2 — Aplicação da Nova UX
- Renomear/inserir as classes `.lead-form`, `.lead-form-fields`, e `.lead-form-field` para manter compatibilidade exata.
- Garantir que ambos os `<input>` utilizem atributo `required`.
- Certificar-se que o botão acompanhe a classe responsável pela ativação verde (`.btn-whatsapp`).
- Testar comportamento `:valid` do CSS nativo portado do `widget.css`.

### Fase 3 & 4 — Build e Validação
- Executar build de versão de produção do React para reconstruir o `template-dist/` que abastece os geradores.
- Re-executar o gerador do SiteGen para testar o site e garantir que tanto Home quanto Subpáginas tenham visual **idêntico** da área de contato.
