"""
CLI interface for Pipeline Contracts.
"""

from pathlib import Path

import typer
from rich.console import Console

from pipeline_contracts.contracts.registry import ContractRegistry
from pipeline_contracts.agents.cli import app as agent_app

app = typer.Typer(
    name="pipeline",
    help="Pipeline ingestion framework with data contracts",
)
console = Console()

# Add the agent subcommand
app.add_typer(agent_app, name="agent", help="Agente interativo para criação de contratos")


@app.command()
def validate(
    contract_path: Path = typer.Argument(..., help="Path to contract YAML/JSON file"),
    data_path: Path = typer.Argument(..., help="Path to data file (CSV/JSON/Parquet)"),
) -> None:
    """Validate a data file against a contract."""
    import pandas as pd

    from pipeline_contracts.validation.validator import ContractValidator

    # Load contract
    registry = ContractRegistry()
    contract = registry.load_from_file(contract_path)
    console.print(f"[green]Loaded contract:[/green] {contract.name} v{contract.version}")

    # Load data
    if data_path.suffix == ".csv":
        data = pd.read_csv(data_path)
    elif data_path.suffix == ".json":
        data = pd.read_json(data_path)
    elif data_path.suffix == ".parquet":
        data = pd.read_parquet(data_path)
    else:
        console.print(f"[red]Unsupported file format: {data_path.suffix}[/red]")
        raise typer.Exit(1)

    console.print(f"[green]Loaded data:[/green] {len(data)} rows, {len(data.columns)} columns")

    # Validate
    validator = ContractValidator(contract)
    result = validator.validate(data)

    # Print result
    console.print()
    if result.is_valid:
        console.print(f"[green]✓ Validation PASSED[/green] ({result.duration_ms:.1f}ms)")
    else:
        console.print(f"[red]✗ Validation FAILED[/red] ({result.duration_ms:.1f}ms)")
        for error in result.errors:
            console.print(f"  - {error.field}: {error.message}")

    if result.warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  - {warning.field}: {warning.message}")


@app.command()
def init(
    path: Path = typer.Argument(
        Path("."),
        help="Directory to initialize",
    ),
) -> None:
    """Initialize a new pipeline contracts project."""
    contracts_dir = path / "contracts"
    pipelines_dir = path / "pipelines"
    data_dir = path / "data"

    contracts_dir.mkdir(parents=True, exist_ok=True)
    pipelines_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create sample contract
    sample_contract = """name: sample_users
version: "1.0.0"
description: Sample user data contract
owner: data-team
domain: users

fields:
  - name: id
    data_type: integer
    nullable: false
    unique: true
    description: Unique user identifier

  - name: email
    data_type: string
    nullable: false
    pattern: "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\\\.[a-zA-Z0-9-.]+$"
    description: User email address

  - name: age
    data_type: integer
    nullable: true
    min_value: 0
    max_value: 150
    description: User age in years

  - name: status
    data_type: string
    nullable: false
    allowed_values:
      - active
      - inactive
      - pending
    description: User account status

min_rows: 1
"""

    contract_file = contracts_dir / "sample_users.yaml"
    contract_file.write_text(sample_contract)

    console.print(f"[green]✓ Initialized project at {path}[/green]")
    console.print(f"  - Created {contracts_dir}")
    console.print(f"  - Created {pipelines_dir}")
    console.print(f"  - Created {data_dir}")
    console.print(f"  - Created sample contract: {contract_file}")


@app.command()
def show(
    contract_path: Path = typer.Argument(..., help="Path to contract YAML/JSON file"),
) -> None:
    """Show details of a contract."""
    from rich.table import Table

    registry = ContractRegistry()
    contract = registry.load_from_file(contract_path)

    # Contract info
    console.print()
    console.print(f"[bold]{contract.name}[/bold] v{contract.version}")
    if contract.description:
        console.print(f"[dim]{contract.description}[/dim]")
    console.print()

    if contract.owner:
        console.print(f"Owner: {contract.owner}")
    if contract.domain:
        console.print(f"Domain: {contract.domain}")
    if contract.tags:
        console.print(f"Tags: {', '.join(contract.tags)}")

    # Fields table
    console.print()
    table = Table(title="Fields")
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Nullable")
    table.add_column("Constraints")

    for field in contract.fields:
        constraints = []
        if field.unique:
            constraints.append("unique")
        if field.min_value is not None:
            constraints.append(f"min={field.min_value}")
        if field.max_value is not None:
            constraints.append(f"max={field.max_value}")
        if field.pattern:
            constraints.append(f"pattern")
        if field.allowed_values:
            constraints.append(f"enum({len(field.allowed_values)})")

        table.add_row(
            field.name,
            field.data_type.value,
            "✓" if field.nullable else "✗",
            ", ".join(constraints) if constraints else "-",
        )

    console.print(table)

    # Quality rules
    if contract.min_rows or contract.max_rows or contract.freshness_hours:
        console.print()
        console.print("[bold]Quality Rules:[/bold]")
        if contract.min_rows:
            console.print(f"  - Minimum rows: {contract.min_rows}")
        if contract.max_rows:
            console.print(f"  - Maximum rows: {contract.max_rows}")
        if contract.freshness_hours:
            console.print(f"  - Freshness: {contract.freshness_hours} hours")


if __name__ == "__main__":
    app()
