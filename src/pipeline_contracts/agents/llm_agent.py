"""
LLM-based Contract Creator Agent

Uses Claude to intelligently create data contracts from natural language descriptions.
The system prompt is generated dynamically from the actual Pydantic models,
ensuring consistency between code and documentation.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from .schema_docs import get_system_prompt


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

    The system prompt is generated dynamically from the Pydantic models
    (DataContract, FieldContract, DataType, QualityLevel), ensuring the
    LLM always has accurate information about the current schema structure.
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
        # Get system prompt dynamically from schema
        self._system_prompt = get_system_prompt()

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

    @property
    def system_prompt(self) -> str:
        """Get the system prompt (generated from schema)."""
        return self._system_prompt

    def refresh_system_prompt(self) -> None:
        """Refresh the system prompt from the current schema."""
        from .schema_docs import refresh_system_prompt
        self._system_prompt = refresh_system_prompt()

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
            system=self._system_prompt,
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
