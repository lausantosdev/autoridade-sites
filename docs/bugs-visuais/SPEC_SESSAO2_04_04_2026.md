# SPEC — Sessão 2 (04/04/2026): Polimento Mobile e Validação B-05

> **Atividade:** Fechamento de Bugs de UI (Foco em Mobile Padding/Alinhamentos)
> **Pré-requisito:** Pipeline de geração funcionando e Site local rodando na porta 8080 (`output/petvida.test`)

---

## Sumário de Fases

- [ ] Fase 1: Validação visual rigorosa do B-05 (Hero mobile padding)
- [ ] Fase 2: Polimento final e Auditoria do Design Premium em todos os viewports
- [ ] Fase 3: Encerramento do ciclo de bugs visuais e Merge final

---

## Fase 1 — Validação do B-05 (Hero Mobile Padding)

### Contexto Recente

Na Sessão 1, o B-05 resultou num buraco branco excessivo no mobile, pois o `justify-content: center` dentro de um container com `min-h-screen` (812px no emulador de celular) forçava o conteúdo desproporcionalmente para baixo ao se adicionar um `padding-top`. 

O último fix alterou o `<style>` em `template-dist/index.html` para:
```css
@media (max-width: 768px) {
  main > section:first-of-type {
    justify-content: flex-start !important;
    padding-top: 8rem !important;
  }
}
```

### Ações:

1. Levantar o servidor (`python -m http.server 8080` em `output/petvida.test`).
2. Abrir aba ou pedir para o usuário analisar no Mobile Viewport a distância entre a base fixa do *Navbar* e a parte superior da *Badge*.
3. Espera-se uma margem controlada (em torno de 3~4rem a partir debaixo do navbar, dando um respiro adequado sem criar um grande vazio branco).
4. **Se reprovado**, ajustar iterativamente com `padding-top: 6rem !important` (ou usar `padding-top: max(6rem, 15vh)` se necessário).

**Status:** [ ]

---

## Fase 2 — Polimento Final

Uma vez validado o B-05, revisar se não houve quebras secundárias por conta da modificação do container:
- Checar Desktop Hero (`padding-top: 10rem` mantido?)
- O Navbar sobrepõe algum conteúdo importante?

**Status:** [ ]

---

## Ordem de Execução

```
Fase 1 (Validação) -> Ajustes iterativos (se necessários) -> Fase 2 (Auditoria Desktop/Mobile Geral) -> Conclusão
```
