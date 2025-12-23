"""
Interactive Session for LLM-based Contract Creation

Provides a terminal-based chat interface for creating data contracts
using Claude as the AI assistant.
"""

import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .llm_agent import LLMContractAgent, LLMConfig


WELCOME_MESSAGE = """
╔══════════════════════════════════════════════════════════════════╗
║        🤖 AGENTE IA PARA CRIAÇÃO DE CONTRATOS DE DADOS           ║
╠══════════════════════════════════════════════════════════════════╣
║  Este agente usa Claude (IA) para criar contratos de dados       ║
║  a partir de descrições em linguagem natural.                    ║
║                                                                   ║
║  Como usar:                                                       ║
║    • Descreva seu caso de uso em português                       ║
║    • O agente sugere campos e configurações                      ║
║    • Refine através de conversa natural                          ║
║    • Salve o contrato quando estiver satisfeito                  ║
║                                                                   ║
║  Comandos especiais:                                              ║
║    /salvar  - Salva o último contrato gerado                     ║
║    /reset   - Reinicia a conversa                                ║
║    /sair    - Encerra a sessão                                   ║
╚══════════════════════════════════════════════════════════════════╝
"""

EXAMPLE_PROMPTS = """
💡 Exemplos de como iniciar:

  • "Preciso de um contrato para dados de pedidos de e-commerce"
  • "Crie um contrato para eventos de clique no site"
  • "Quero validar dados de cadastro de clientes com CPF e email"
  • "Dados de transações financeiras com valores e timestamps"
"""


class LLMContractSession:
    """
    Interactive terminal session for LLM-based contract creation.

    Provides a chat interface where users can describe their needs
    in natural language and the AI generates appropriate contracts.
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-haiku-latest",
    ):
        """
        Initialize the LLM contract session.

        Args:
            output_dir: Directory to save generated contracts.
            api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var).
            model: Model to use (default: claude-3-5-haiku-latest).
        """
        self.console = Console()
        self.output_dir = output_dir or Path("contracts")
        self.last_yaml: Optional[str] = None
        self.last_contract_name: Optional[str] = None

        # Initialize agent
        try:
            config = LLMConfig(model=model)
            self.agent = LLMContractAgent(api_key=api_key, config=config)
        except ValueError as e:
            self.console.print(f"[red]Erro: {e}[/red]")
            self.console.print(
                "\n[yellow]Configure sua API key:[/yellow]\n"
                "  export ANTHROPIC_API_KEY='sua-chave-aqui'\n"
            )
            raise

    def _display_response(self, response: str) -> None:
        """Display the agent's response with markdown formatting."""
        self.console.print()
        md = Markdown(response)
        self.console.print(md)
        self.console.print()

    def _extract_and_store_yaml(self, response: str) -> bool:
        """Extract YAML from response and store it."""
        yaml_content = self.agent.extract_yaml_from_response(response)
        if yaml_content:
            self.last_yaml = yaml_content
            # Try to extract contract name
            try:
                import yaml
                contract = yaml.safe_load(yaml_content)
                self.last_contract_name = contract.get("name", "contract")
            except Exception:
                self.last_contract_name = "contract"
            return True
        return False

    def _save_contract(self) -> Optional[Path]:
        """Save the last generated contract."""
        if not self.last_yaml:
            self.console.print(
                "[yellow]Nenhum contrato gerado ainda. "
                "Descreva seu caso de uso primeiro.[/yellow]"
            )
            return None

        # Determine filename
        default_name = f"{self.last_contract_name}.yaml"
        filename = Prompt.ask(
            "[bold cyan]Nome do arquivo[/bold cyan]",
            default=default_name,
        )

        output_path = self.output_dir / filename

        try:
            saved_path = self.agent.save_contract(self.last_yaml, output_path)
            self.console.print(
                f"\n[green]✅ Contrato salvo em: {saved_path}[/green]\n"
            )
            return saved_path
        except Exception as e:
            self.console.print(f"[red]Erro ao salvar: {e}[/red]")
            return None

    def _handle_command(self, command: str) -> bool:
        """
        Handle special commands.

        Returns:
            True if should continue, False if should exit.
        """
        cmd = command.lower().strip()

        if cmd in ("/sair", "/exit", "/quit"):
            self.console.print("\n[yellow]Até logo! 👋[/yellow]\n")
            return False

        elif cmd in ("/salvar", "/save"):
            self._save_contract()
            return True

        elif cmd in ("/reset", "/clear"):
            self.agent.reset_conversation()
            self.last_yaml = None
            self.last_contract_name = None
            self.console.print(
                "\n[green]✓ Conversa reiniciada.[/green]\n"
            )
            return True

        elif cmd in ("/help", "/ajuda"):
            self.console.print(EXAMPLE_PROMPTS)
            return True

        return True

    def run(self) -> Optional[Path]:
        """
        Run the interactive LLM session.

        Returns:
            Path to the last saved contract, or None.
        """
        self.console.print(WELCOME_MESSAGE)
        self.console.print(EXAMPLE_PROMPTS)

        saved_path = None

        try:
            while True:
                # Get user input
                user_input = Prompt.ask("\n[bold green]Você[/bold green]")

                if not user_input.strip():
                    continue

                # Check for commands
                if user_input.startswith("/"):
                    if not self._handle_command(user_input):
                        break
                    continue

                # Show thinking indicator
                with self.console.status("[bold blue]Pensando...[/bold blue]"):
                    response = self.agent.chat(user_input)

                # Display response
                self._display_response(response)

                # Check if response contains a contract
                if self._extract_and_store_yaml(response):
                    self.console.print(
                        "[dim]💾 Contrato detectado! Use /salvar para salvar.[/dim]"
                    )

        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]Sessão encerrada.[/yellow]")

        # Offer to save before exiting if there's an unsaved contract
        if self.last_yaml:
            if Confirm.ask(
                "\n[bold]Deseja salvar o último contrato antes de sair?[/bold]",
                default=True,
            ):
                saved_path = self._save_contract()

        return saved_path

    def generate_from_description(self, description: str) -> tuple[str, Optional[Path]]:
        """
        Generate a contract from a description (non-interactive mode).

        Args:
            description: Natural language description of the contract.

        Returns:
            Tuple of (response_text, saved_path or None).
        """
        self.console.print(
            f"\n[bold blue]Gerando contrato para:[/bold blue] {description}\n"
        )

        with self.console.status("[bold blue]Gerando contrato...[/bold blue]"):
            response, yaml_content = self.agent.get_contract_from_description(
                description
            )

        self._display_response(response)

        if yaml_content:
            self.last_yaml = yaml_content
            try:
                import yaml
                contract = yaml.safe_load(yaml_content)
                self.last_contract_name = contract.get("name", "contract")
            except Exception:
                self.last_contract_name = "contract"

            if Confirm.ask(
                "\n[bold]Deseja salvar este contrato?[/bold]",
                default=True,
            ):
                return response, self._save_contract()

        return response, None
