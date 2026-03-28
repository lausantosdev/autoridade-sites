---
description: Como criar um novo site SEO Local (AutoridadeSites)
---

# Workflow: Novo Site SEO Local

Este workflow ensina como utilizar o sistema de geração "Autoridade Sites" para criar sites institucionais otimizados com múltiplas páginas e locais para dominância regional em SEO.

O sistema gera páginas otimizadas utilizando a API do OpenRouter (DeepSeek) e salva tudo na pasta `output/{dominio}`.

---

## Opção 1: Via Interface Gráfica (Recomendado para o Usuário)

Use este método se quiser guiar o usuário visualmente.

1.  Certifique-se de que as dependências estão rodando e a licença OpenRouter está ativa (`.env` tem `OPENROUTER_API_KEY`).
2.  Iniciar o servidor FastAPI em background:
    ```bash
    python server.py
    ```
3.  O sistema estará rodando em `http://localhost:8000`. 
4.  Oriente o usuário a abrir o navegador no endereço informado e preencher os 5 passos:
    - Inserir **Dados da Empresa** (Nome, Domínio, Nicho/Categoria).
    - Importar um arquivo CSV do Google Keyword Planner ou colar as **Keywords** line-by-line.
    - Colar as **Cidades/Bairros** desejados.
    - Escolher a **Cor da Marca** (design premium será adaptado a essa cor).
    - Clicar em "Gerar" — o terminal fará o resto.
5.  O download do `.zip` completo estará disponível diretamente na tela após a finalização do progresso.
6.  Ao finalizar, caso o servidor não seja mais necessário, pressione `CTRL+C` no terminal.

---

## Opção 2: Via Terminal Automatizado (CLI - Recomendado para Agentes/IA)

Use este método para automatizar a criação sem precisar preencher um formulário no navegador.

### Passo 1: Configurar os Dados do Cliente
Edite o arquivo `config.yaml` na raiz do projeto (`c:\Users\ThinkPad T480\autoridade-sites`).
Altere todas as seções abaixo conforme o negócio:

```yaml
empresa:
  nome: "Nome da Empresa"
  dominio: "dominio.com.br"
  categoria: "Pintura Comercial" # Nicho para orientar a IA
  telefone_whatsapp: "5511999999999"
  telefone_ligar: "(11) 99999-9999"
  cor_marca: "#e11d48"

seo:
  palavras_chave:
    - Pintura Comercial Externa
    - Pintura de Fachadas
  locais:
    - São Paulo
    - Guarulhos
```

### Passo 2: Executar o Gerador (Pipeline)
Com o `config.yaml` salvo, execute o comando CLI que roda todos os passos do pipeline de uma vez:

// turbo
```bash
python generate.py
```

Isso fará com que o sistema realize automaticamente as etapas:
1.  **mix**: Produto Cartesiano de palavras + locais.
2.  **sitemap**: Geração de Site Map (`sitemap.xml`) e Mapa do Site (`mapa-do-site.html`).
3.  **topics**: Criar contexto nichado da categoria sem alucinações via DeepSeek.
4.  **pages**: Trabalhadores concorrentes (Worker Threads) batendo no OpenRouter para escrever os HTMLs otimizados.
5.  **validate**: Geração do relatório final do que foi entregue.

### Passo 3: Revisão
Os arquivos gerados cairão em `output/{dominio}`.
Verifique o report do `.md` focado em qualidade em `output/reports/{dominio}_report.md` para checar os custos ou avisos pendentes de entrega!
---

**IMPORTANTE:** O Template premium principal é injetado a partir da pasta `templates/`, e modificado automaticamente injetando apenas a formatação e as tags corretas. Para personalizações visuais estruturais do template *base*, altere `templates/index.html` ou `templates/css/style.css` ANTES da geração.
