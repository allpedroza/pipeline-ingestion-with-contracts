#!/bin/bash
#
# Script de setup do ambiente de desenvolvimento
# Usa uv para gerenciamento de ambiente virtual
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Pipeline Contracts - Environment Setup               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo

# Verificar se uv está instalado
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Erro: 'uv' não está instalado.${NC}"
    echo -e "${YELLOW}Instale com: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} uv encontrado: $(uv --version)"

# Criar ambiente virtual se não existir
if [ ! -d "$VENV_DIR" ]; then
    echo -e "\n${YELLOW}Criando ambiente virtual...${NC}"
    uv venv "$VENV_DIR"
    echo -e "${GREEN}✓${NC} Ambiente virtual criado em $VENV_DIR"
else
    echo -e "${GREEN}✓${NC} Ambiente virtual já existe"
fi

# Instalar dependências
echo -e "\n${YELLOW}Instalando dependências...${NC}"
uv pip install -e ".[dev]"
echo -e "${GREEN}✓${NC} Dependências instaladas"

# Instruções de ativação
echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Setup Completo!                         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "Para ativar o ambiente virtual:"
echo -e "  ${YELLOW}source .venv/bin/activate${NC}"
echo
echo -e "Comandos disponíveis após ativação:"
echo -e "  ${YELLOW}pipeline --help${NC}          - CLI principal"
echo -e "  ${YELLOW}contract-agent --help${NC}    - Agente de criação de contratos"
echo -e "  ${YELLOW}pytest${NC}                   - Executar testes"
echo
