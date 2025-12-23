"""
Prompts and Questions for Contract Creator Agent

This module contains all the questions and prompts needed to gather
complete information for creating a data contract.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class QuestionType(str, Enum):
    """Types of questions the agent can ask."""
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    MULTI_CHOICE = "multi_choice"
    OPTIONAL_TEXT = "optional_text"
    OPTIONAL_NUMBER = "optional_number"


@dataclass
class Question:
    """Represents a question to be asked."""
    key: str
    prompt: str
    question_type: QuestionType
    help_text: Optional[str] = None
    choices: Optional[list[str]] = None
    default: Optional[Any] = None
    validator: Optional[Callable[[Any], bool]] = None
    error_message: Optional[str] = None
    condition: Optional[Callable[[dict], bool]] = None  # Show only if condition is True


# =============================================================================
# CONTRACT METADATA QUESTIONS
# =============================================================================

CONTRACT_METADATA_QUESTIONS = [
    Question(
        key="name",
        prompt="Qual é o NOME do contrato?",
        question_type=QuestionType.TEXT,
        help_text=(
            "O nome é o identificador único do contrato. "
            "Use snake_case (ex: 'user_events', 'order_items', 'customer_transactions')."
        ),
        validator=lambda x: len(x) > 0 and x.replace("_", "").isalnum(),
        error_message="O nome deve conter apenas letras, números e underscores.",
    ),
    Question(
        key="version",
        prompt="Qual é a VERSÃO do contrato?",
        question_type=QuestionType.TEXT,
        default="1.0.0",
        help_text=(
            "Use versionamento semântico (MAJOR.MINOR.PATCH). "
            "Ex: 1.0.0 para versão inicial, 1.1.0 para novas features, 2.0.0 para breaking changes."
        ),
    ),
    Question(
        key="description",
        prompt="Descreva o PROPÓSITO deste contrato:",
        question_type=QuestionType.TEXT,
        help_text=(
            "Uma descrição clara ajuda outros membros da equipe a entender "
            "para que este conjunto de dados é usado."
        ),
    ),
    Question(
        key="owner",
        prompt="Quem é o RESPONSÁVEL (owner) por este contrato?",
        question_type=QuestionType.TEXT,
        help_text=(
            "Pode ser o nome de uma equipe (ex: 'data-platform-team') "
            "ou pessoa (ex: 'maria.silva@empresa.com')."
        ),
    ),
    Question(
        key="domain",
        prompt="Qual é o DOMÍNIO de negócio?",
        question_type=QuestionType.CHOICE,
        choices=[
            "customers",
            "commerce",
            "finance",
            "marketing",
            "operations",
            "products",
            "analytics",
            "hr",
            "logistics",
            "outro",
        ],
        help_text=(
            "O domínio ajuda a organizar os contratos por área de negócio."
        ),
    ),
    Question(
        key="domain_custom",
        prompt="Especifique o domínio customizado:",
        question_type=QuestionType.TEXT,
        condition=lambda answers: answers.get("domain") == "outro",
    ),
    Question(
        key="tags",
        prompt="Quais TAGS deseja adicionar? (separadas por vírgula)",
        question_type=QuestionType.OPTIONAL_TEXT,
        help_text=(
            "Tags ajudam na categorização. Exemplos comuns:\n"
            "  - 'pii' para dados pessoais\n"
            "  - 'core' para dados críticos\n"
            "  - 'derived' para dados derivados\n"
            "  - 'raw' para dados brutos\n"
            "  - 'aggregated' para dados agregados"
        ),
    ),
]


# =============================================================================
# FIELD QUESTIONS
# =============================================================================

FIELD_START_QUESTIONS = [
    Question(
        key="add_field",
        prompt="Deseja adicionar um campo?",
        question_type=QuestionType.BOOLEAN,
        default=True,
    ),
]

FIELD_BASIC_QUESTIONS = [
    Question(
        key="name",
        prompt="Qual é o NOME do campo?",
        question_type=QuestionType.TEXT,
        help_text="Use snake_case (ex: 'user_id', 'created_at', 'total_amount').",
        validator=lambda x: len(x) > 0 and x.replace("_", "").isalnum(),
        error_message="O nome deve conter apenas letras, números e underscores.",
    ),
    Question(
        key="data_type",
        prompt="Qual é o TIPO DE DADO?",
        question_type=QuestionType.CHOICE,
        choices=[
            "string",
            "integer",
            "float",
            "boolean",
            "date",
            "datetime",
            "array",
            "object",
        ],
        help_text=(
            "Tipos disponíveis:\n"
            "  - string: texto\n"
            "  - integer: números inteiros\n"
            "  - float: números decimais\n"
            "  - boolean: verdadeiro/falso\n"
            "  - date: apenas data (YYYY-MM-DD)\n"
            "  - datetime: data e hora\n"
            "  - array: lista de valores\n"
            "  - object: objeto complexo/JSON"
        ),
    ),
    Question(
        key="description",
        prompt="Descreva o campo (propósito e uso):",
        question_type=QuestionType.TEXT,
        help_text="Uma boa descrição ajuda a documentar o significado do campo.",
    ),
]

FIELD_CONSTRAINTS_QUESTIONS = [
    Question(
        key="nullable",
        prompt="Este campo pode ser NULO/VAZIO?",
        question_type=QuestionType.BOOLEAN,
        default=False,
        help_text="Defina como 'Sim' se o campo pode não ter valor em alguns registros.",
    ),
    Question(
        key="unique",
        prompt="Os valores devem ser ÚNICOS (sem duplicatas)?",
        question_type=QuestionType.BOOLEAN,
        default=False,
        help_text="Use 'Sim' para identificadores únicos como IDs, emails únicos, etc.",
    ),
    Question(
        key="quality_level",
        prompt="Qual é o NÍVEL DE CRITICIDADE se a validação falhar?",
        question_type=QuestionType.CHOICE,
        choices=["critical", "warning", "info"],
        default="critical",
        help_text=(
            "Níveis de qualidade:\n"
            "  - critical: pipeline FALHA se houver violação\n"
            "  - warning: registra aviso, mas continua\n"
            "  - info: apenas informativo"
        ),
    ),
]

# Perguntas específicas para tipos numéricos (integer, float)
NUMERIC_CONSTRAINTS_QUESTIONS = [
    Question(
        key="has_min_value",
        prompt="Existe um VALOR MÍNIMO permitido?",
        question_type=QuestionType.BOOLEAN,
        default=False,
    ),
    Question(
        key="min_value",
        prompt="Qual é o VALOR MÍNIMO?",
        question_type=QuestionType.NUMBER,
        condition=lambda answers: answers.get("has_min_value", False),
    ),
    Question(
        key="has_max_value",
        prompt="Existe um VALOR MÁXIMO permitido?",
        question_type=QuestionType.BOOLEAN,
        default=False,
    ),
    Question(
        key="max_value",
        prompt="Qual é o VALOR MÁXIMO?",
        question_type=QuestionType.NUMBER,
        condition=lambda answers: answers.get("has_max_value", False),
    ),
]

# Perguntas específicas para strings
STRING_CONSTRAINTS_QUESTIONS = [
    Question(
        key="has_min_length",
        prompt="Existe um TAMANHO MÍNIMO para o texto?",
        question_type=QuestionType.BOOLEAN,
        default=False,
    ),
    Question(
        key="min_length",
        prompt="Qual é o TAMANHO MÍNIMO (em caracteres)?",
        question_type=QuestionType.NUMBER,
        condition=lambda answers: answers.get("has_min_length", False),
    ),
    Question(
        key="has_max_length",
        prompt="Existe um TAMANHO MÁXIMO para o texto?",
        question_type=QuestionType.BOOLEAN,
        default=False,
    ),
    Question(
        key="max_length",
        prompt="Qual é o TAMANHO MÁXIMO (em caracteres)?",
        question_type=QuestionType.NUMBER,
        condition=lambda answers: answers.get("has_max_length", False),
    ),
    Question(
        key="has_pattern",
        prompt="O campo deve seguir um PADRÃO/FORMATO específico? (ex: email, CPF, código)",
        question_type=QuestionType.BOOLEAN,
        default=False,
    ),
    Question(
        key="pattern_type",
        prompt="Qual tipo de padrão?",
        question_type=QuestionType.CHOICE,
        choices=[
            "email",
            "cpf",
            "cnpj",
            "telefone",
            "cep",
            "uuid",
            "url",
            "custom",
        ],
        condition=lambda answers: answers.get("has_pattern", False),
        help_text=(
            "Padrões comuns pré-definidos ou use 'custom' para regex personalizado."
        ),
    ),
    Question(
        key="custom_pattern",
        prompt="Digite a expressão regular (regex) do padrão:",
        question_type=QuestionType.TEXT,
        condition=lambda answers: answers.get("pattern_type") == "custom",
        help_text="Ex: ^[A-Z]{3}-[0-9]{4}$ para códigos como 'ABC-1234'",
    ),
]

# Perguntas para valores permitidos (todos os tipos)
ALLOWED_VALUES_QUESTIONS = [
    Question(
        key="has_allowed_values",
        prompt="Existe uma LISTA DE VALORES PERMITIDOS (enum)?",
        question_type=QuestionType.BOOLEAN,
        default=False,
        help_text="Use para campos como 'status', 'tipo', 'categoria' com valores fixos.",
    ),
    Question(
        key="allowed_values",
        prompt="Liste os valores permitidos (separados por vírgula):",
        question_type=QuestionType.TEXT,
        condition=lambda answers: answers.get("has_allowed_values", False),
        help_text="Ex: active, inactive, pending, cancelled",
    ),
]


# =============================================================================
# INTEGRITY/SLA QUESTIONS
# =============================================================================

INTEGRITY_QUESTIONS = [
    Question(
        key="has_min_rows",
        prompt="Existe um NÚMERO MÍNIMO de registros esperados?",
        question_type=QuestionType.BOOLEAN,
        default=False,
        help_text="Útil para detectar pipelines que retornam dados incompletos.",
    ),
    Question(
        key="min_rows",
        prompt="Qual é o número MÍNIMO de registros?",
        question_type=QuestionType.NUMBER,
        condition=lambda answers: answers.get("has_min_rows", False),
    ),
    Question(
        key="has_max_rows",
        prompt="Existe um NÚMERO MÁXIMO de registros esperados?",
        question_type=QuestionType.BOOLEAN,
        default=False,
        help_text="Útil para detectar duplicações ou explosões de dados.",
    ),
    Question(
        key="max_rows",
        prompt="Qual é o número MÁXIMO de registros?",
        question_type=QuestionType.NUMBER,
        condition=lambda answers: answers.get("has_max_rows", False),
    ),
    Question(
        key="has_freshness",
        prompt="Existe um SLA de FRESHNESS (idade máxima dos dados)?",
        question_type=QuestionType.BOOLEAN,
        default=False,
        help_text="Define quantas horas os dados podem ter antes de serem considerados desatualizados.",
    ),
    Question(
        key="freshness_hours",
        prompt="Qual é a idade MÁXIMA dos dados (em horas)?",
        question_type=QuestionType.NUMBER,
        condition=lambda answers: answers.get("has_freshness", False),
        help_text="Ex: 24 para dados diários, 1 para dados horários.",
    ),
]


# =============================================================================
# PATTERN DEFINITIONS
# =============================================================================

COMMON_PATTERNS = {
    "email": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    "cpf": r"^\d{3}\.\d{3}\.\d{3}-\d{2}$|^\d{11}$",
    "cnpj": r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$|^\d{14}$",
    "telefone": r"^\+?[\d\s\-\(\)]{10,}$",
    "cep": r"^\d{5}-?\d{3}$",
    "uuid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    "url": r"^https?://[^\s/$.?#].[^\s]*$",
}


# =============================================================================
# SUMMARY MESSAGES
# =============================================================================

WELCOME_MESSAGE = """
╔══════════════════════════════════════════════════════════════════╗
║           🗂️  ASSISTENTE DE CRIAÇÃO DE CONTRATOS DE DADOS         ║
╠══════════════════════════════════════════════════════════════════╣
║  Este assistente irá guiá-lo através do processo de criação      ║
║  de um contrato de dados completo, garantindo que todas as       ║
║  informações necessárias sejam coletadas.                        ║
║                                                                   ║
║  O contrato define:                                               ║
║    • Metadados (nome, versão, responsável, domínio)              ║
║    • Campos e seus tipos de dados                                 ║
║    • Regras de validação e qualidade                             ║
║    • SLAs de integridade                                          ║
╚══════════════════════════════════════════════════════════════════╝
"""

SECTION_METADATA = """
┌──────────────────────────────────────────────────────────────────┐
│  📋 SEÇÃO 1/3: METADADOS DO CONTRATO                             │
│  Vamos definir as informações gerais do contrato.                │
└──────────────────────────────────────────────────────────────────┘
"""

SECTION_FIELDS = """
┌──────────────────────────────────────────────────────────────────┐
│  📊 SEÇÃO 2/3: DEFINIÇÃO DOS CAMPOS                              │
│  Agora vamos definir cada campo/coluna do seu dataset.           │
└──────────────────────────────────────────────────────────────────┘
"""

SECTION_INTEGRITY = """
┌──────────────────────────────────────────────────────────────────┐
│  ✅ SEÇÃO 3/3: REGRAS DE INTEGRIDADE                             │
│  Por fim, vamos definir regras de SLA e integridade.             │
└──────────────────────────────────────────────────────────────────┘
"""

SUCCESS_MESSAGE = """
╔══════════════════════════════════════════════════════════════════╗
║  ✅ CONTRATO CRIADO COM SUCESSO!                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
