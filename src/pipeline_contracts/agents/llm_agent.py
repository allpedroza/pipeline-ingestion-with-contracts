"""
LLM-based Contract Creator Agent

Uses Claude to intelligently create data contracts from natural language descriptions.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

# System prompt for the contract creator agent
SYSTEM_PROMPT = """Você é um especialista em Data Contracts e engenharia de dados. Sua função é ajudar usuários a criar contratos de dados completos e bem estruturados.

## Seu Conhecimento

Você conhece profundamente a estrutura de Data Contracts:

### Metadados do Contrato
- name: identificador único (snake_case)
- version: versionamento semântico (ex: "1.0.0")
- description: descrição do propósito
- owner: equipe ou pessoa responsável
- domain: domínio de negócio (customers, commerce, finance, marketing, operations, products, analytics, hr, logistics)
- tags: lista de tags para categorização (ex: pii, core, derived, raw)

### Campos (fields)
Cada campo possui:
- name: nome do campo (snake_case)
- data_type: string, integer, float, boolean, date, datetime, array, object
- nullable: true/false (pode ser nulo?)
- unique: true/false (valores únicos?)
- description: descrição do campo
- quality_level: critical (falha pipeline), warning (apenas aviso), info (informativo)

Constraints específicos por tipo:
- Numéricos (integer, float): min_value, max_value
- Strings: min_length, max_length, pattern (regex)
- Todos: allowed_values (lista de valores permitidos)

### Regras de Integridade
- min_rows: número mínimo de registros esperados
- max_rows: número máximo de registros esperados
- freshness_hours: idade máxima dos dados em horas (SLA)

### Padrões de Validação Comuns
- Email: ^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$
- CPF: ^\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}$|^\\d{11}$
- CNPJ: ^\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}$|^\\d{14}$
- UUID: ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$
- URL: ^https?://[^\\s/$.?#].[^\\s]*$
- CEP: ^\\d{5}-?\\d{3}$
- Telefone: ^\\+?[\\d\\s\\-\\(\\)]{10,}$

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

## Formato de Resposta

Quando gerar um contrato, use exatamente este formato YAML:

```yaml
name: nome_do_contrato
version: "1.0.0"
description: Descrição clara do contrato
owner: equipe-responsavel
domain: dominio
tags:
  - tag1
  - tag2

fields:
  - name: campo1
    data_type: tipo
    nullable: false
    unique: true
    description: Descrição do campo

  - name: campo2
    data_type: tipo
    nullable: true
    description: Descrição do campo

min_rows: 1
freshness_hours: 24
```

Sempre inclua TODOS os campos necessários, com descrições claras e constraints apropriados."""


@dataclass
class LLMConfig:
    """Configuration for the LLM agent."""
    model: str = "claude-3-5-haiku-latest"
    max_tokens: int = 4096
    temperature: float = 0.3


class LLMContractAgent:
    """
    LLM-powered agent for creating data contracts through natural conversation.

    Uses Claude to understand natural language descriptions and generate
    complete, well-structured data contracts.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[LLMConfig] = None,
    ):
        """
        Initialize the LLM Contract Agent.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
            config: LLM configuration options.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key não encontrada. Configure ANTHROPIC_API_KEY ou passe api_key."
            )

        self.config = config or LLMConfig()
        self.conversation_history: list[dict] = []
        self._client = None

    @property
    def client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "Biblioteca 'anthropic' não instalada. "
                    "Instale com: pip install anthropic"
                )
        return self._client

    def chat(self, user_message: str) -> str:
        """
        Send a message and get a response from the agent.

        Args:
            user_message: The user's message.

        Returns:
            The agent's response.
        """
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=SYSTEM_PROMPT,
            messages=self.conversation_history,
        )

        assistant_message = response.content[0].text

        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message,
        })

        return assistant_message

    def extract_yaml_from_response(self, response: str) -> Optional[str]:
        """
        Extract YAML content from a response that may contain markdown code blocks.

        Args:
            response: The full response text.

        Returns:
            The extracted YAML content, or None if not found.
        """
        import re

        # Try to find YAML in code blocks
        yaml_pattern = r"```yaml\s*([\s\S]*?)```"
        matches = re.findall(yaml_pattern, response)

        if matches:
            return matches[-1].strip()  # Return the last YAML block

        # Try generic code blocks
        code_pattern = r"```\s*([\s\S]*?)```"
        matches = re.findall(code_pattern, response)

        for match in reversed(matches):
            # Check if it looks like YAML
            if "name:" in match and "fields:" in match:
                return match.strip()

        return None

    def parse_contract(self, yaml_content: str) -> dict:
        """
        Parse YAML content into a contract dictionary.

        Args:
            yaml_content: The YAML string.

        Returns:
            The parsed contract as a dictionary.
        """
        return yaml.safe_load(yaml_content)

    def save_contract(self, yaml_content: str, output_path: Path) -> Path:
        """
        Save the contract to a YAML file.

        Args:
            yaml_content: The YAML content to save.
            output_path: The path to save to.

        Returns:
            The path where the contract was saved.
        """
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Parse and re-dump to ensure proper formatting
        contract_dict = self.parse_contract(yaml_content)

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                contract_dict,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return output_path

    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self.conversation_history = []

    def get_contract_from_description(self, description: str) -> tuple[str, str]:
        """
        Generate a contract from a natural language description in one shot.

        Args:
            description: Natural language description of the desired contract.

        Returns:
            Tuple of (full_response, yaml_content).
        """
        prompt = f"""Crie um Data Contract completo para o seguinte caso de uso:

{description}

Por favor, gere um contrato YAML completo com todos os campos necessários,
tipos de dados apropriados, constraints de validação e regras de integridade.
Inclua sugestões de campos comuns para este domínio que o usuário possa ter esquecido."""

        response = self.chat(prompt)
        yaml_content = self.extract_yaml_from_response(response)

        return response, yaml_content or ""
