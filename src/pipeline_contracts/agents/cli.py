"""
CLI for Contract Creator Agent

Provides command-line interface for the interactive contract creation agent.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .interactive_session import InteractiveContractSession

app = typer.Typer(
    name="contract-agent",
    help="Agente interativo para criação de contratos de dados",
    add_completion=False,
)

console = Console()


@app.command("create")
def create_contract(
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Diretório de saída para o contrato (padrão: ./contracts)",
    ),
) -> None:
    """
    Inicia uma sessão interativa para criar um novo contrato de dados.

    O agente irá guiá-lo através de todas as perguntas necessárias
    para criar um contrato completo e bem documentado.
    """
    output_path = output_dir or Path("contracts")

    session = InteractiveContractSession(output_dir=output_path)
    result = session.run()

    if result:
        console.print(f"\n[bold green]✅ Contrato criado com sucesso![/bold green]")
        console.print(f"[dim]Arquivo: {result}[/dim]")
    else:
        raise typer.Exit(code=1)


@app.command("list-patterns")
def list_patterns() -> None:
    """
    Lista os padrões de validação pré-definidos disponíveis.

    Esses padrões podem ser usados para validar campos do tipo string.
    """
    from .prompts import COMMON_PATTERNS

    console.print("\n[bold]📋 Padrões de Validação Disponíveis:[/bold]\n")

    for name, pattern in COMMON_PATTERNS.items():
        console.print(f"  [cyan]{name}[/cyan]")
        console.print(f"    Regex: [dim]{pattern}[/dim]\n")


@app.command("list-types")
def list_types() -> None:
    """
    Lista os tipos de dados suportados para campos.
    """
    types_info = {
        "string": "Texto de qualquer tamanho",
        "integer": "Números inteiros (ex: 1, 42, -10)",
        "float": "Números decimais (ex: 3.14, -0.5)",
        "boolean": "Verdadeiro ou Falso",
        "date": "Apenas data (formato: YYYY-MM-DD)",
        "datetime": "Data e hora (formato: YYYY-MM-DD HH:MM:SS)",
        "array": "Lista de valores",
        "object": "Objeto complexo (JSON)",
    }

    console.print("\n[bold]📊 Tipos de Dados Suportados:[/bold]\n")

    for type_name, description in types_info.items():
        console.print(f"  [cyan]{type_name}[/cyan]")
        console.print(f"    {description}\n")


@app.command("list-quality-levels")
def list_quality_levels() -> None:
    """
    Lista os níveis de qualidade disponíveis para validação.
    """
    levels = {
        "critical": (
            "🔴 Pipeline FALHA se a validação não passar. "
            "Use para campos essenciais."
        ),
        "warning": (
            "🟡 Registra aviso no log, mas pipeline continua. "
            "Use para campos importantes mas não críticos."
        ),
        "info": (
            "🔵 Apenas registra informação. "
            "Use para monitoramento e métricas."
        ),
    }

    console.print("\n[bold]✅ Níveis de Qualidade:[/bold]\n")

    for level, description in levels.items():
        console.print(f"  [bold]{level}[/bold]")
        console.print(f"    {description}\n")


@app.command("example")
def show_example() -> None:
    """
    Mostra um exemplo completo de contrato de dados.
    """
    example_yaml = """
name: user_events
version: "1.0.0"
description: Eventos de interação dos usuários com a plataforma
owner: data-platform-team
domain: analytics
tags:
  - events
  - user-behavior
  - core

fields:
  - name: event_id
    data_type: string
    nullable: false
    unique: true
    pattern: "^EVT-[A-Z0-9]{12}$"
    description: Identificador único do evento

  - name: user_id
    data_type: integer
    nullable: false
    description: ID do usuário que gerou o evento

  - name: event_type
    data_type: string
    nullable: false
    allowed_values: [page_view, click, purchase, signup, logout]
    description: Tipo do evento

  - name: event_timestamp
    data_type: datetime
    nullable: false
    description: Data e hora do evento

  - name: page_url
    data_type: string
    nullable: true
    max_length: 2048
    description: URL da página onde o evento ocorreu

  - name: value
    data_type: float
    nullable: true
    min_value: 0
    quality_level: warning
    description: Valor monetário associado ao evento (se aplicável)

min_rows: 1000
freshness_hours: 1
"""

    console.print("\n[bold]📄 Exemplo de Contrato de Dados:[/bold]")
    console.print(example_yaml)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
