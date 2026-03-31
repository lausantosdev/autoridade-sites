.PHONY: help install install-dev serve generate validate test clean

help: ## Mostra este menu de ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  Exemplo de uso:"
	@echo "    make install && cp config.example.yaml config.yaml && make serve"

install: ## Instala dependências de produção
	pip install -r requirements.txt

install-dev: ## Instala dependências de produção + desenvolvimento (pytest)
	pip install -r requirements.txt -r requirements-dev.txt

serve: ## Inicia o wizard (http://localhost:8000)
	python server.py

generate: ## Gera o site completo com config.yaml
	python generate.py

generate-home: ## Gera apenas a home page
	python generate.py --step home

generate-pages: ## Gera apenas as subpáginas SEO
	python generate.py --step pages

generate-image: ## Gera apenas a imagem hero
	python generate.py --step image

validate: ## Valida a qualidade do site gerado
	python generate.py --step validate

test: ## Roda todos os testes unitários
	pytest tests/ -v

test-cov: ## Roda os testes com relatório de cobertura
	pytest tests/ -v --cov=core --cov-report=term-missing

clean: ## Remove outputs, cache e uploads gerados
	rm -rf output/ cache/ uploads/ reports/
