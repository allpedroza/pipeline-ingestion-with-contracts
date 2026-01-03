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

from packaging.version import InvalidVersion, Version

from .contract_creator import ContractCreatorAgent
from ..contracts.registry import ContractRegistry
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
        self.registry = ContractRegistry()
        self.answers: dict[str, Any] = {}
        self.prefill_answers: dict[str, Any] = {}
        self._load_existing_contracts()

    def _load_existing_contracts(self) -> None:
        """Load existing contracts from the output directory if available."""
        if not self.output_dir.exists():
            return

        if not self.output_dir.is_dir():
            self.console.print(
                f"[yellow]Aviso: {self.output_dir} não é um diretório. Ignorando contratos existentes.[/yellow]"
            )
            return

        try:
            self.registry.load_from_directory(self.output_dir)
        except Exception as exc:  # pragma: no cover - log only
            self.console.print(
                f"[yellow]Aviso: não foi possível carregar contratos existentes em {self.output_dir}: {exc}[/yellow]"
            )

    def _get_version_default(self, contract_name: str | None) -> str:
        """Return the latest version found for the contract name, falling back to 1.0.0."""
        if not contract_name:
            return "1.0.0"

        versions: list[Version] = []
        for contract in self.registry.list_contracts():
            if contract.name != contract_name:
                continue
            try:
                versions.append(Version(contract.version))
            except InvalidVersion:
                continue

        if versions:
            latest_version = str(max(versions))
            self.console.print(
                f"[dim]Versão atual detectada para '{contract_name}': {latest_version}. Usando como padrão.[/dim]"
            )
            return latest_version

        return "1.0.0"

    def _prepare_metadata_questions(self) -> list[Question]:
        """Prepare metadata questions, injecting dynamic defaults when needed."""
        questions: list[Question] = []

        for question in CONTRACT_METADATA_QUESTIONS:
            question_copy = Question(
                key=question.key,
                prompt=question.prompt,
                question_type=question.question_type,
                help_text=question.help_text,
                choices=question.choices,
                default=question.default,
                validator=question.validator,
                error_message=question.error_message,
                condition=question.condition,
            )

            if question_copy.key == "version":
                question_copy.default = lambda ctx: self._get_version_default(ctx.get("name"))

            questions.append(question_copy)

        return questions

    def _ask_question(self, question: Question, context: dict) -> Any:
        """Ask a single question and return the answer."""
        # Check condition
        if question.condition and not question.condition(context):
            return None

        # Display help text if available
        if question.help_text:
            self.console.print(f"\n[dim]{question.help_text}[/dim]")

        prompt_text = f"[bold cyan]{question.prompt}[/bold cyan]"

        if question.key in context:
            default_value = context[question.key]
        else:
            default_value = (
                question.default(context)
                if callable(question.default)
                else question.default
            )

        try:
            if question.question_type == QuestionType.TEXT:
                while True:
                    answer = Prompt.ask(prompt_text, default=default_value or "")
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
                answer = Prompt.ask(prompt_text, default=default_value or "")
                return answer if answer else None

            elif question.question_type == QuestionType.NUMBER:
                return IntPrompt.ask(prompt_text, default=default_value)

            elif question.question_type == QuestionType.OPTIONAL_NUMBER:
                answer = Prompt.ask(
                    prompt_text,
                    default=str(default_value) if default_value else "",
                )
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
                default_bool = default_value if default_value is not None else False
                return Confirm.ask(prompt_text, default=default_bool)

            elif question.question_type == QuestionType.CHOICE:
                self.console.print(f"\n{prompt_text}")
                for i, choice in enumerate(question.choices or [], 1):
                    self.console.print(f"  [yellow]{i}[/yellow]. {choice}")

                while True:
                    choice_input = Prompt.ask(
                        "[dim]Digite o número ou nome da opção[/dim]",
                        default=default_value or "",
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

        return default_value

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
        questions = self._prepare_metadata_questions()
        return self._ask_questions(questions, self.prefill_answers)

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

    def _collect_fields(self, start_number: int = 1) -> list[dict]:
        """Collect all field definitions."""
        self.console.print(SECTION_FIELDS)

        fields = []
        field_number = start_number

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
        return self._ask_questions(INTEGRITY_QUESTIONS, self.prefill_answers)

    def _build_prefill_from_contract(self) -> None:
        """Populate prefill answers with the content of the loaded contract."""
        if not self.agent.contract_def:
            return

        contract = self.agent.contract_def

        self.prefill_answers.update(
            {
                "name": contract.name,
                "version": contract.version,
                "description": contract.description,
                "owner": contract.owner,
                "domain": contract.domain,
                "tags": ", ".join(contract.tags) if contract.tags else None,
                "has_min_rows": contract.min_rows is not None,
                "min_rows": contract.min_rows,
                "has_max_rows": contract.max_rows is not None,
                "max_rows": contract.max_rows,
                "has_freshness": contract.freshness_hours is not None,
                "freshness_hours": contract.freshness_hours,
            }
        )

    def _suggest_next_version(self, version: str) -> str:
        """Return the next patch version for a given version string."""
        try:
            parsed = Version(version)
            bumped = Version(f"{parsed.major}.{parsed.minor}.{parsed.micro + 1}")
            return str(bumped)
        except InvalidVersion:
            return version

    def _select_existing_contract(self) -> Optional[Any]:
        """Allow the user to load an existing contract as a starting point."""
        contracts = self.registry.list_contracts()
        if not contracts:
            return None

        self.console.print(
            "\n[bold]Contratos existentes foram encontrados. Deseja carregar um como base?[/bold]"
        )

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#")
        table.add_column("Nome")
        table.add_column("Versão")

        def _version_key(contract: Any) -> tuple[str, Version]:
            try:
                version_obj = Version(contract.version)
            except InvalidVersion:
                version_obj = Version("0")
            return (contract.name, version_obj)

        sorted_contracts = sorted(contracts, key=_version_key)

        for idx, contract in enumerate(sorted_contracts, 1):
            table.add_row(str(idx), contract.name, contract.version)

        self.console.print(table)

        if not Confirm.ask(
            "Deseja usar um contrato existente como ponto de partida?", default=True
        ):
            return None

        while True:
            selected = IntPrompt.ask(
                "Selecione o número do contrato para carregar", default=1
            )
            if 1 <= selected <= len(sorted_contracts):
                return sorted_contracts[selected - 1]

            self.console.print("[red]Número inválido. Tente novamente.[/red]")

    def _handle_existing_fields(self) -> int:
        """Show already loaded fields and ask whether to keep them."""
        if not self.agent.contract_def or not self.agent.contract_def.fields:
            return 1

        fields = self.agent.contract_def.fields

        field_table = Table(show_header=True, header_style="bold magenta")
        field_table.add_column("Campo")
        field_table.add_column("Tipo")
        field_table.add_column("Nulo")
        field_table.add_column("Único")

        for field in fields:
            field_table.add_row(
                field.name,
                field.data_type,
                "Sim" if field.nullable else "Não",
                "Sim" if field.unique else "Não",
            )

        self.console.print(
            "\n[bold]Campos carregados do contrato selecionado serão reutilizados:[/bold]"
        )
        self.console.print(field_table)

        keep_fields = Confirm.ask(
            "Deseja manter estes campos antes de adicionar novos?", default=True
        )

        if not keep_fields:
            self.agent.contract_def.fields = []
            return 1

        self.console.print(
            "[dim]Os campos existentes foram mantidos. Você pode adicionar novos se necessário.[/dim]"
        )

        return len(self.agent.contract_def.fields) + 1

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

            selected_contract = self._select_existing_contract()
            if selected_contract:
                self.agent.load_from_contract(selected_contract)
                self._build_prefill_from_contract()

                if Confirm.ask(
                    f"Deseja atualizar a versão de '{selected_contract.name}' agora?",
                    default=True,
                ):
                    suggested = self._suggest_next_version(selected_contract.version)
                    new_version = Prompt.ask(
                        "[bold cyan]Nova versão do contrato[/bold cyan]",
                        default=suggested,
                    )
                    if self.agent.contract_def:
                        self.agent.contract_def.version = new_version
                    self.prefill_answers["version"] = new_version
                else:
                    self.prefill_answers["version"] = selected_contract.version

            # Section 1: Metadata
            metadata = self._collect_metadata()
            self.agent.process_metadata(metadata)

            # Section 2: Fields
            start_number = self._handle_existing_fields()

            fields = self._collect_fields(start_number)
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
