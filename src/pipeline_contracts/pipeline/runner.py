"""
Pipeline Runner - Executes pipelines with logging and monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd
from rich.console import Console
from rich.table import Table

from pipeline_contracts.contracts.base import DataContract
from pipeline_contracts.pipeline.base import Pipeline, StepResult, StepStatus
from pipeline_contracts.pipeline.steps import ContractValidationStep
from pipeline_contracts.validation.validator import ContractValidator


class PipelineStatus(str, Enum):
    """Status of a pipeline execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # Some steps failed


@dataclass
class PipelineResult:
    """Result of executing a pipeline."""

    pipeline_name: str
    status: PipelineStatus
    step_results: list[StepResult] = field(default_factory=list)
    final_data: pd.DataFrame | None = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str | None = None

    @property
    def duration_ms(self) -> float:
        """Total pipeline execution time in milliseconds."""
        if self.completed_at is None:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds() * 1000

    @property
    def is_success(self) -> bool:
        """Check if pipeline completed successfully."""
        return self.status == PipelineStatus.SUCCESS

    def get_step_result(self, step_name: str) -> StepResult | None:
        """Get result of a specific step."""
        for result in self.step_results:
            if result.step_name == step_name:
                return result
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "pipeline_name": self.pipeline_name,
            "status": self.status.value,
            "is_success": self.is_success,
            "step_count": len(self.step_results),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "steps": [
                {
                    "name": r.step_name,
                    "status": r.status.value,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in self.step_results
            ],
        }


class PipelineRunner:
    """
    Executes pipelines with contract validation.

    Features:
    - Step-by-step execution
    - Source/target contract validation
    - Detailed logging with Rich
    - Fail-fast or continue-on-error modes
    - Dry run support
    """

    def __init__(
        self,
        fail_fast: bool = True,
        dry_run: bool = False,
        verbose: bool = True,
    ) -> None:
        self.fail_fast = fail_fast
        self.dry_run = dry_run
        self.verbose = verbose
        self.console = Console() if verbose else None

    def run(self, pipeline: Pipeline, initial_data: pd.DataFrame | None = None) -> PipelineResult:
        """
        Execute a pipeline.

        Args:
            pipeline: The pipeline to execute
            initial_data: Optional initial data (if not using a source step)

        Returns:
            PipelineResult with execution details
        """
        result = PipelineResult(
            pipeline_name=pipeline.name,
            status=PipelineStatus.RUNNING,
        )

        context: dict[str, Any] = {
            "dry_run": self.dry_run,
            "pipeline_name": pipeline.name,
        }

        current_data = initial_data

        self._log_start(pipeline)

        try:
            # Validate source contract if provided
            if pipeline.source_contract and current_data is not None:
                source_result = self._validate_contract(
                    "source", pipeline.source_contract, current_data
                )
                result.step_results.append(source_result)

                if source_result.status == StepStatus.FAILED and self.fail_fast:
                    result.status = PipelineStatus.FAILED
                    result.error = source_result.error
                    result.completed_at = datetime.utcnow()
                    self._log_result(result)
                    return result

            # Execute pipeline steps
            for step in pipeline.steps:
                self._log_step_start(step.name)

                step_result = step.execute(current_data, context)
                result.step_results.append(step_result)

                self._log_step_result(step_result)

                if step_result.status == StepStatus.FAILED:
                    if self.fail_fast:
                        result.status = PipelineStatus.FAILED
                        result.error = step_result.error
                        result.completed_at = datetime.utcnow()
                        self._log_result(result)
                        return result
                else:
                    # Update current data with step output
                    if step_result.data is not None:
                        current_data = step_result.data

            # Validate target contract if provided
            if pipeline.target_contract and current_data is not None:
                target_result = self._validate_contract(
                    "target", pipeline.target_contract, current_data
                )
                result.step_results.append(target_result)

                if target_result.status == StepStatus.FAILED:
                    result.status = PipelineStatus.FAILED
                    result.error = target_result.error
                    result.completed_at = datetime.utcnow()
                    self._log_result(result)
                    return result

            # Check for any failures
            failed_steps = [r for r in result.step_results if r.status == StepStatus.FAILED]
            if failed_steps:
                result.status = PipelineStatus.PARTIAL
            else:
                result.status = PipelineStatus.SUCCESS

            result.final_data = current_data
            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.utcnow()

        self._log_result(result)
        return result

    def _validate_contract(
        self, stage: str, contract: DataContract, data: pd.DataFrame
    ) -> StepResult:
        """Validate data against a contract."""
        step = ContractValidationStep(
            name=f"{stage}_contract_validation",
            contract=contract,
            fail_on_error=True,
        )
        return step.execute(data, {})

    def _log_start(self, pipeline: Pipeline) -> None:
        """Log pipeline start."""
        if not self.console:
            return

        self.console.print()
        self.console.rule(f"[bold blue]Pipeline: {pipeline.name}")
        if pipeline.description:
            self.console.print(f"[dim]{pipeline.description}[/dim]")
        self.console.print(f"Steps: {len(pipeline.steps)}")
        if self.dry_run:
            self.console.print("[yellow]DRY RUN MODE[/yellow]")
        self.console.print()

    def _log_step_start(self, step_name: str) -> None:
        """Log step start."""
        if not self.console:
            return
        self.console.print(f"  [dim]→[/dim] Running [bold]{step_name}[/bold]...")

    def _log_step_result(self, result: StepResult) -> None:
        """Log step result."""
        if not self.console:
            return

        status_styles = {
            StepStatus.SUCCESS: "[green]✓ SUCCESS[/green]",
            StepStatus.FAILED: "[red]✗ FAILED[/red]",
            StepStatus.SKIPPED: "[yellow]○ SKIPPED[/yellow]",
        }

        status_str = status_styles.get(result.status, str(result.status))
        self.console.print(f"    {status_str} ({result.duration_ms:.1f}ms)")

        if result.error:
            self.console.print(f"    [red]Error: {result.error}[/red]")

    def _log_result(self, result: PipelineResult) -> None:
        """Log final pipeline result."""
        if not self.console:
            return

        self.console.print()

        # Summary table
        table = Table(title="Pipeline Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value")

        status_styles = {
            PipelineStatus.SUCCESS: "[green]SUCCESS[/green]",
            PipelineStatus.FAILED: "[red]FAILED[/red]",
            PipelineStatus.PARTIAL: "[yellow]PARTIAL[/yellow]",
        }

        table.add_row("Status", status_styles.get(result.status, str(result.status)))
        table.add_row("Total Steps", str(len(result.step_results)))
        table.add_row(
            "Successful",
            str(len([r for r in result.step_results if r.status == StepStatus.SUCCESS])),
        )
        table.add_row(
            "Failed",
            str(len([r for r in result.step_results if r.status == StepStatus.FAILED])),
        )
        table.add_row("Duration", f"{result.duration_ms:.1f}ms")

        if result.final_data is not None:
            table.add_row("Output Rows", str(len(result.final_data)))

        self.console.print(table)

        if result.error:
            self.console.print(f"\n[red]Error: {result.error}[/red]")

        self.console.print()
