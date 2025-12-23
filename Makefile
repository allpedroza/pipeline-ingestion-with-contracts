.PHONY: setup install dev test lint format clean help venv agent

# Variáveis
VENV := .venv
PYTHON := $(VENV)/bin/python
UV := uv

# Detectar SO
ifeq ($(OS),Windows_NT)
	ACTIVATE := $(VENV)/Scripts/activate
else
	ACTIVATE := $(VENV)/bin/activate
endif

help: ## Mostra esta mensagem de ajuda
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║         Pipeline Contracts - Comandos Disponíveis          ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

venv: ## Cria o ambiente virtual com uv
	@echo "Criando ambiente virtual..."
	$(UV) venv $(VENV)
	@echo "✓ Ambiente virtual criado em $(VENV)"

setup: venv install ## Setup completo: cria venv e instala dependências
	@echo ""
	@echo "✓ Setup completo!"
	@echo "  Ative o ambiente com: source $(ACTIVATE)"

install: ## Instala o pacote e dependências de desenvolvimento
	@echo "Instalando dependências..."
	$(UV) pip install -e ".[dev]"
	@echo "✓ Dependências instaladas"

sync: ## Sincroniza dependências (atualiza para versões mais recentes)
	$(UV) pip install --upgrade -e ".[dev]"

test: ## Executa os testes com pytest
	$(PYTHON) -m pytest tests/ -v

test-cov: ## Executa testes com cobertura
	$(PYTHON) -m pytest tests/ -v --cov=src/pipeline_contracts --cov-report=term-missing

lint: ## Executa o linter (ruff)
	$(PYTHON) -m ruff check src/ tests/

lint-fix: ## Executa o linter e corrige automaticamente
	$(PYTHON) -m ruff check src/ tests/ --fix

format: ## Formata o código com ruff
	$(PYTHON) -m ruff format src/ tests/

typecheck: ## Executa verificação de tipos com mypy
	$(PYTHON) -m mypy src/

check: lint typecheck ## Executa lint e typecheck

agent: ## Inicia o agente de criação de contratos
	$(PYTHON) -m pipeline_contracts.agents.cli create

agent-help: ## Mostra ajuda do agente
	$(PYTHON) -m pipeline_contracts.agents.cli --help

validate: ## Valida um contrato (uso: make validate CONTRACT=path/to/contract.yaml DATA=path/to/data.csv)
	$(PYTHON) -m pipeline_contracts.cli validate $(CONTRACT) $(DATA)

clean: ## Remove arquivos temporários e cache
	@echo "Limpando arquivos temporários..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Limpeza concluída"

clean-venv: ## Remove o ambiente virtual
	@echo "Removendo ambiente virtual..."
	rm -rf $(VENV)
	@echo "✓ Ambiente virtual removido"

reset: clean clean-venv setup ## Reset completo: limpa tudo e recria o ambiente
