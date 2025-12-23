"""
Interactive Session for Contract Creation

Provides a terminal-based interactive session for creating data contracts
through a guided question-and-answer flow.
"""

from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from .contract_creator import ContractCreatorAgent
from .prompts import (
    ALLOWED_VALUES_QUESTIONS,
    CONTRACT_METADATA_QUESTIONS,
    FIELD_BASIC_QUESTIONS,
    FIELD_CONSTRAINTS_QUESTIONS,
    INTEGRITY_QUESTIONS,
    NUMERIC_CONSTRAINTS_QUESTIONS,
    SECTION_FIELDS,
    SECTION_INTEGRITY,
    SECTION_METADATA,
    STRING_CONSTRAINTS_QUESTIONS,
    SUCCESS_MESSAGE,
    WELCOME_MESSAGE,
    Question,
    QuestionType,
)


class InteractiveContractSession:
    """
    Manages an interactive terminal session for creating data contracts.

    This class handles all user interaction, collecting answers through
    Rich prompts and delegating contract building to the ContractCreatorAgent.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.console = Console()
        self.agent = ContractCreatorAgent()
        self.output_dir = output_dir or Path("contracts")
        self.answers: dict[str, Any] = {}

    def _ask_question(self, question: Question, context: dict) -> Any:
        """Ask a single question and return the answer."""
        # Check condition
        if question.condition and not question.condition(context):
            return None

        # Display help text if available
        if question.help_text:
            self.console.print(f"\n[dim]{question.help_text}[/dim]")

        prompt_text = f"[bold cyan]{question.prompt}[/bold cyan]"

        try:
            if question.question_type == QuestionType.TEXT:
                while True:
                    answer = Prompt.ask(prompt_text, default=question.default or "")
                    if question.validator:
                        if question.validator(answer):
                            return answer
                        else:
                            self.console.print(
                                f"[red]❌ {question.error_message or 'Valor inválido'}[/red]"
                            )
                    else:
                        return answer

            elif question.question_type == QuestionType.OPTIONAL_TEXT:
                answer = Prompt.ask(prompt_text, default=question.default or "")
                return answer if answer else None

            elif question.question_type == QuestionType.NUMBER:
                return IntPrompt.ask(prompt_text, default=question.default)

            elif question.question_type == QuestionType.OPTIONAL_NUMBER:
                answer = Prompt.ask(prompt_text, default=str(question.default) if question.default else "")
                if answer:
                    try:
                        return int(answer)
                    except ValueError:
                        try:
                            return float(answer)
                        except ValueError:
                            return None
                return None

            elif question.question_type == QuestionType.BOOLEAN:
                default_bool = question.default if question.default is not None else False
                return Confirm.ask(prompt_text, default=default_bool)

            elif question.question_type == QuestionType.CHOICE:
                self.console.print(f"\n{prompt_text}")
                for i, choice in enumerate(question.choices or [], 1):
                    self.console.print(f"  [yellow]{i}[/yellow]. {choice}")

                while True:
                    choice_input = Prompt.ask(
                        "[dim]Digite o número ou nome da opção[/dim]",
                        default=question.default or "",
                    )

                    # Try to parse as number
                    try:
                        idx = int(choice_input) - 1
                        if 0 <= idx < len(question.choices or []):
                            return question.choices[idx]
                    except ValueError:
                        pass

                    # Try to match by name
                    if choice_input in (question.choices or []):
                        return choice_input

                    self.console.print("[red]❌ Opção inválida. Tente novamente.[/red]")

            elif question.question_type == QuestionType.MULTI_CHOICE:
                self.console.print(f"\n{prompt_text}")
                for i, choice in enumerate(question.choices or [], 1):
                    self.console.print(f"  [yellow]{i}[/yellow]. {choice}")

                answer = Prompt.ask(
                    "[dim]Digite os números separados por vírgula[/dim]",
                    default="",
                )

                if not answer:
                    return []

                selected = []
                for item in answer.split(","):
                    item = item.strip()
                    try:
                        idx = int(item) - 1
                        if 0 <= idx < len(question.choices or []):
                            selected.append(question.choices[idx])
                    except ValueError:
                        if item in (question.choices or []):
                            selected.append(item)

                return selected

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Operação cancelada pelo usuário.[/yellow]")
            raise

        return question.default

    def _ask_questions(self, questions: list[Question], context: Optional[dict] = None) -> dict:
        """Ask a list of questions and collect answers."""
        answers = context.copy() if context else {}

        for question in questions:
            answer = self._ask_question(question, answers)
            if answer is not None:
                answers[question.key] = answer

        return answers

    def _collect_metadata(self) -> dict:
        """Collect contract metadata through interactive questions."""
        self.console.print(SECTION_METADATA)
        return self._ask_questions(CONTRACT_METADATA_QUESTIONS)

    def _collect_field(self, field_number: int) -> Optional[dict]:
        """Collect a single field definition."""
        self.console.print(
            f"\n[bold magenta]── Campo #{field_number} ──[/bold magenta]"
        )

        # Basic field info
        answers = self._ask_questions(FIELD_BASIC_QUESTIONS)

        # Common constraints
        answers.update(self._ask_questions(FIELD_CONSTRAINTS_QUESTIONS, answers))

        # Type-specific constraints
        data_type = answers.get("data_type", "")

        if data_type in ("integer", "float"):
            answers.update(self._ask_questions(NUMERIC_CONSTRAINTS_QUESTIONS, answers))

        if data_type == "string":
            answers.update(self._ask_questions(STRING_CONSTRAINTS_QUESTIONS, answers))

        # Allowed values (for all types)
        answers.update(self._ask_questions(ALLOWED_VALUES_QUESTIONS, answers))

        return answers

    def _collect_fields(self) -> list[dict]:
        """Collect all field definitions."""
        self.console.print(SECTION_FIELDS)

        fields = []
        field_number = 1

        while True:
            if field_number > 1:
                add_more = Confirm.ask(
                    "\n[bold cyan]Deseja adicionar mais um campo?[/bold cyan]",
                    default=True,
                )
                if not add_more:
                    break
            else:
                self.console.print(
                    "\n[dim]Vamos começar definindo os campos do seu dataset.[/dim]"
                )

            field_def = self._collect_field(field_number)
            if field_def:
                fields.append(field_def)
                self.console.print(
                    f"[green]✓ Campo '{field_def['name']}' adicionado![/green]"
                )
                field_number += 1

        return fields

    def _collect_integrity(self) -> dict:
        """Collect integrity/SLA rules."""
        self.console.print(SECTION_INTEGRITY)
        return self._ask_questions(INTEGRITY_QUESTIONS)

    def _show_summary(self) -> None:
        """Display the contract summary."""
        summary = self.agent.generate_summary()
        self.console.print(f"\n{summary}")

    def _show_yaml_preview(self) -> None:
        """Show a preview of the YAML that will be generated."""
        import yaml

        yaml_dict = self.agent.to_yaml_dict()
        yaml_str = yaml.dump(
            yaml_dict,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        self.console.print("\n[bold]📄 Preview do arquivo YAML:[/bold]\n")
        self.console.print(Panel(yaml_str, title="contract.yaml", border_style="blue"))

    def run(self) -> Optional[Path]:
        """
        Run the interactive contract creation session.

        Returns:
            Path to the created contract file, or None if cancelled.
        """
        try:
            # Welcome message
            self.console.print(WELCOME_MESSAGE)

            # Confirm start
            if not Confirm.ask("\n[bold]Deseja iniciar a criação de um novo contrato?[/bold]", default=True):
                self.console.print("[yellow]Operação cancelada.[/yellow]")
                return None

            # Section 1: Metadata
            metadata = self._collect_metadata()
            self.agent.process_metadata(metadata)

            # Section 2: Fields
            fields = self._collect_fields()
            for field_answers in fields:
                field_def = self.agent.process_field(field_answers)
                self.agent.add_field(field_def)

            # Section 3: Integrity
            integrity = self._collect_integrity()
            self.agent.process_integrity(integrity)

            # Show summary
            self._show_summary()

            # Show YAML preview
            self._show_yaml_preview()

            # Confirm save
            if not Confirm.ask("\n[bold]Deseja salvar o contrato?[/bold]", default=True):
                self.console.print("[yellow]Contrato não salvo.[/yellow]")
                return None

            # Determine output path
            contract_name = self.agent.contract_def.name
            default_filename = f"{contract_name}.yaml"
            filename = Prompt.ask(
                "[bold cyan]Nome do arquivo[/bold cyan]",
                default=default_filename,
            )

            output_path = self.output_dir / filename

            # Save contract
            saved_path = self.agent.save_to_yaml(output_path)

            self.console.print(SUCCESS_MESSAGE)
            self.console.print(f"[green]Arquivo salvo em: {saved_path}[/green]")

            return saved_path

        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]Operação cancelada pelo usuário.[/yellow]")
            return None

    def run_from_dict(self, data: dict) -> Path:
        """
        Create a contract from a dictionary (non-interactive mode).

        This is useful for programmatic contract creation or testing.

        Args:
            data: Dictionary with contract data

        Returns:
            Path to the created contract file.
        """
        # Process metadata
        self.agent.process_metadata(data)

        # Process fields
        for field_data in data.get("fields", []):
            field_def = self.agent.process_field(field_data)
            self.agent.add_field(field_def)

        # Process integrity
        self.agent.process_integrity(data)

        # Determine output path
        contract_name = self.agent.contract_def.name
        output_path = self.output_dir / f"{contract_name}.yaml"

        # Save contract
        return self.agent.save_to_yaml(output_path)
