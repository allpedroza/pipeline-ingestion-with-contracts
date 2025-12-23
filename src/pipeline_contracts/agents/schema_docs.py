"""
Schema Documentation Generator

Generates documentation and prompts dynamically from the Pydantic models,
ensuring the LLM agent always has the current contract structure.
"""

from typing import Any, get_type_hints

from ..contracts.base import DataContract, DataType, FieldContract, QualityLevel
from .prompts import COMMON_PATTERNS


def get_enum_values(enum_class: type) -> list[str]:
    """Extract all values from an enum class."""
    return [e.value for e in enum_class]


def get_field_info(model_class: type, field_name: str) -> dict[str, Any]:
    """Extract field information from a Pydantic model."""
    field = model_class.model_fields.get(field_name)
    if not field:
        return {}

    info = {
        "name": field_name,
        "description": field.description or "",
        "required": field.is_required(),
        "default": field.default if field.default is not None else None,
    }

    # Get type annotation
    hints = get_type_hints(model_class)
    if field_name in hints:
        info["type"] = str(hints[field_name])

    return info


def generate_contract_schema_docs() -> str:
    """Generate documentation for the DataContract schema from Pydantic models."""

    lines = []

    # Data Types
    lines.append("### Tipos de Dados Suportados (DataType)")
    lines.append("")
    for dt in DataType:
        desc = {
            "string": "Texto/caracteres",
            "integer": "Números inteiros",
            "float": "Números decimais",
            "boolean": "Verdadeiro/Falso",
            "date": "Data (YYYY-MM-DD)",
            "datetime": "Data e hora (YYYY-MM-DD HH:MM:SS)",
            "array": "Lista/Array de valores",
            "object": "Objeto complexo/JSON",
        }.get(dt.value, dt.value)
        lines.append(f"- **{dt.value}**: {desc}")
    lines.append("")

    # Quality Levels
    lines.append("### Níveis de Qualidade (QualityLevel)")
    lines.append("")
    for ql in QualityLevel:
        desc = {
            "critical": "Pipeline FALHA se a validação não passar",
            "warning": "Registra aviso, mas pipeline continua",
            "info": "Apenas informativo, para monitoramento",
        }.get(ql.value, ql.value)
        lines.append(f"- **{ql.value}**: {desc}")
    lines.append("")

    # DataContract fields
    lines.append("### Estrutura do DataContract")
    lines.append("")
    lines.append("Campos do contrato principal:")
    lines.append("")

    for field_name, field_info in DataContract.model_fields.items():
        if field_name in ("created_at", "updated_at"):
            continue  # Skip auto-generated fields

        required = "OBRIGATÓRIO" if field_info.is_required() else "opcional"
        default = ""
        if field_info.default is not None and not field_info.is_required():
            default = f" (padrão: {field_info.default})"

        desc = field_info.description or ""
        lines.append(f"- **{field_name}** [{required}]{default}: {desc}")

    lines.append("")

    # FieldContract fields
    lines.append("### Estrutura do FieldContract (cada campo)")
    lines.append("")
    lines.append("Para cada campo do dataset:")
    lines.append("")

    for field_name, field_info in FieldContract.model_fields.items():
        required = "OBRIGATÓRIO" if field_info.is_required() else "opcional"
        default = ""
        if field_info.default is not None and not field_info.is_required():
            if field_info.default != "":
                default = f" (padrão: {field_info.default})"

        desc = field_info.description or ""
        lines.append(f"- **{field_name}** [{required}]{default}: {desc}")

    return "\n".join(lines)


def generate_patterns_docs() -> str:
    """Generate documentation for available validation patterns."""
    lines = ["### Padrões de Validação Pré-definidos", ""]

    for name, pattern in COMMON_PATTERNS.items():
        lines.append(f"- **{name}**: `{pattern}`")

    return "\n".join(lines)


def generate_example_contract() -> str:
    """Generate an example contract YAML."""
    return """```yaml
name: exemplo_contrato
version: "1.0.0"
description: Descrição clara do propósito do contrato
owner: nome-da-equipe
domain: dominio_de_negocio
tags:
  - tag1
  - tag2

fields:
  - name: id
    data_type: integer
    nullable: false
    unique: true
    description: Identificador único

  - name: email
    data_type: string
    nullable: false
    pattern: "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\\\.[a-zA-Z0-9-.]+$"
    max_length: 255
    description: Email do usuário

  - name: status
    data_type: string
    nullable: false
    allowed_values: [ativo, inativo, pendente]
    description: Status do registro

  - name: valor
    data_type: float
    nullable: true
    min_value: 0
    quality_level: warning
    description: Valor monetário

  - name: created_at
    data_type: datetime
    nullable: false
    description: Data de criação

min_rows: 1
max_rows: 1000000
freshness_hours: 24
```"""


def generate_system_prompt() -> str:
    """
    Generate the complete system prompt for the LLM agent.

    This function dynamically generates the prompt from the actual
    Pydantic models, ensuring consistency between code and documentation.
    """

    schema_docs = generate_contract_schema_docs()
    patterns_docs = generate_patterns_docs()
    example = generate_example_contract()

    prompt = f"""Você é um especialista em Data Contracts e engenharia de dados. Sua função é ajudar usuários a criar contratos de dados completos e bem estruturados.

## Seu Conhecimento

Você conhece profundamente a estrutura de Data Contracts definida neste sistema:

{schema_docs}

{patterns_docs}

## Domínios de Negócio Comuns

Domínios sugeridos para categorização:
- customers (clientes)
- commerce (e-commerce, vendas)
- finance (financeiro)
- marketing
- operations (operações)
- products (produtos)
- analytics
- hr (recursos humanos)
- logistics (logística)

## Seu Comportamento

1. Quando o usuário descrever um caso de uso, você deve:
   - Inferir os campos típicos para aquele domínio
   - Sugerir tipos de dados apropriados
   - Adicionar constraints relevantes (patterns para emails, min/max para valores, etc.)
   - Sugerir campos comuns que o usuário pode ter esquecido

2. Sempre pergunte sobre:
   - Owner/responsável pelo contrato
   - Se há campos sensíveis (PII)
   - SLAs de freshness se aplicável

3. Forneça o contrato em formato YAML válido dentro de um bloco de código.

4. Seja proativo em sugerir melhorias e boas práticas.

5. Use os padrões de validação pré-definidos quando apropriado (email, cpf, cnpj, etc.)

## Formato de Resposta

Quando gerar um contrato, use exatamente este formato YAML:

{example}

Sempre inclua TODOS os campos necessários, com descrições claras e constraints apropriados.

## Regras Importantes

1. O campo `name` é OBRIGATÓRIO e deve ser em snake_case
2. O campo `data_type` é OBRIGATÓRIO para cada field
3. Use `nullable: false` para campos que não podem ser nulos
4. Use `unique: true` para identificadores únicos
5. Adicione `description` em todos os campos para documentação
6. Use `quality_level: warning` para campos não-críticos
7. Sempre sugira `min_rows` e `freshness_hours` quando fizer sentido para o caso de uso"""

    return prompt


# Cached prompt for performance
_CACHED_PROMPT: str | None = None


def get_system_prompt() -> str:
    """Get the system prompt, using cache if available."""
    global _CACHED_PROMPT
    if _CACHED_PROMPT is None:
        _CACHED_PROMPT = generate_system_prompt()
    return _CACHED_PROMPT


def refresh_system_prompt() -> str:
    """Force regeneration of the system prompt."""
    global _CACHED_PROMPT
    _CACHED_PROMPT = generate_system_prompt()
    return _CACHED_PROMPT
