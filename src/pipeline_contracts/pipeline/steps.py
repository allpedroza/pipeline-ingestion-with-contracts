"""
Built-in pipeline steps.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from pipeline_contracts.contracts.base import DataContract
from pipeline_contracts.pipeline.base import PipelineStep, StepResult, StepStatus
from pipeline_contracts.validation.validator import ContractValidator


class SourceReadStep(PipelineStep):
    """
    Step to read data from a source.

    Supports:
    - CSV files
    - JSON files
    - Parquet files
    - Custom readers
    """

    def __init__(
        self,
        name: str,
        source_path: Path | str | None = None,
        source_type: str = "csv",
        reader: Callable[[], pd.DataFrame] | None = None,
        read_options: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(name, description)
        self.source_path = Path(source_path) if source_path else None
        self.source_type = source_type
        self.reader = reader
        self.read_options = read_options or {}

    def execute(self, data: pd.DataFrame | None, context: dict[str, Any]) -> StepResult:
        """Read data from the source."""
        start_time = datetime.utcnow()

        try:
            if self.reader:
                df = self.reader()
            elif self.source_path:
                df = self._read_file()
            else:
                raise ValueError("Either source_path or reader must be provided")

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000

            return StepResult(
                step_name=self.name,
                status=StepStatus.SUCCESS,
                data=df,
                duration_ms=duration,
                metadata={"row_count": len(df), "column_count": len(df.columns)},
            )

        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000

            return StepResult(
                step_name=self.name,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=duration,
            )

    def _read_file(self) -> pd.DataFrame:
        """Read data from a file based on source type."""
        if not self.source_path:
            raise ValueError("source_path is required")

        readers = {
            "csv": pd.read_csv,
            "json": pd.read_json,
            "parquet": pd.read_parquet,
            "excel": pd.read_excel,
        }

        reader_func = readers.get(self.source_type)
        if not reader_func:
            raise ValueError(f"Unsupported source type: {self.source_type}")

        return reader_func(self.source_path, **self.read_options)


class ContractValidationStep(PipelineStep):
    """
    Step to validate data against a contract.
    """

    def __init__(
        self,
        name: str,
        contract: DataContract,
        fail_on_error: bool = True,
        description: str | None = None,
    ) -> None:
        super().__init__(name, description)
        self.contract = contract
        self.fail_on_error = fail_on_error
        self.validator = ContractValidator(contract)

    def execute(self, data: pd.DataFrame | None, context: dict[str, Any]) -> StepResult:
        """Validate data against the contract."""
        start_time = datetime.utcnow()

        if data is None:
            return StepResult(
                step_name=self.name,
                status=StepStatus.FAILED,
                error="No data to validate",
                duration_ms=0,
            )

        try:
            result = self.validator.validate(data)

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000

            if not result.is_valid and self.fail_on_error:
                error_msg = "; ".join([f"{e.field}: {e.message}" for e in result.errors])
                return StepResult(
                    step_name=self.name,
                    status=StepStatus.FAILED,
                    data=data,
                    error=error_msg,
                    duration_ms=duration,
                    metadata={"validation_result": result.to_dict()},
                )

            return StepResult(
                step_name=self.name,
                status=StepStatus.SUCCESS,
                data=data,
                duration_ms=duration,
                metadata={"validation_result": result.to_dict()},
            )

        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000

            return StepResult(
                step_name=self.name,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=duration,
            )


class DataTransformStep(PipelineStep):
    """
    Step to transform data using a custom function.
    """

    def __init__(
        self,
        name: str,
        transform: Callable[[pd.DataFrame], pd.DataFrame],
        description: str | None = None,
    ) -> None:
        super().__init__(name, description)
        self.transform = transform

    def execute(self, data: pd.DataFrame | None, context: dict[str, Any]) -> StepResult:
        """Apply transformation to data."""
        start_time = datetime.utcnow()

        if data is None:
            return StepResult(
                step_name=self.name,
                status=StepStatus.FAILED,
                error="No data to transform",
                duration_ms=0,
            )

        try:
            transformed = self.transform(data)

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000

            return StepResult(
                step_name=self.name,
                status=StepStatus.SUCCESS,
                data=transformed,
                duration_ms=duration,
                metadata={
                    "input_rows": len(data),
                    "output_rows": len(transformed),
                },
            )

        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000

            return StepResult(
                step_name=self.name,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=duration,
            )


class TargetWriteStep(PipelineStep):
    """
    Step to write data to a target.

    Supports:
    - CSV files
    - JSON files
    - Parquet files
    - Custom writers
    """

    def __init__(
        self,
        name: str,
        target_path: Path | str | None = None,
        target_type: str = "csv",
        writer: Callable[[pd.DataFrame], None] | None = None,
        write_options: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> None:
        super().__init__(name, description)
        self.target_path = Path(target_path) if target_path else None
        self.target_type = target_type
        self.writer = writer
        self.write_options = write_options or {}

    def execute(self, data: pd.DataFrame | None, context: dict[str, Any]) -> StepResult:
        """Write data to the target."""
        start_time = datetime.utcnow()

        if data is None:
            return StepResult(
                step_name=self.name,
                status=StepStatus.FAILED,
                error="No data to write",
                duration_ms=0,
            )

        # Skip write in dry run mode
        if context.get("dry_run", False):
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000
            return StepResult(
                step_name=self.name,
                status=StepStatus.SKIPPED,
                data=data,
                duration_ms=duration,
                metadata={"reason": "dry_run"},
            )

        try:
            if self.writer:
                self.writer(data)
            elif self.target_path:
                self._write_file(data)
            else:
                raise ValueError("Either target_path or writer must be provided")

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000

            return StepResult(
                step_name=self.name,
                status=StepStatus.SUCCESS,
                data=data,
                duration_ms=duration,
                metadata={"row_count": len(data)},
            )

        except Exception as e:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000

            return StepResult(
                step_name=self.name,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=duration,
            )

    def _write_file(self, data: pd.DataFrame) -> None:
        """Write data to a file based on target type."""
        if not self.target_path:
            raise ValueError("target_path is required")

        # Create parent directories
        self.target_path.parent.mkdir(parents=True, exist_ok=True)

        writers = {
            "csv": lambda df, path, **opts: df.to_csv(path, index=False, **opts),
            "json": lambda df, path, **opts: df.to_json(path, **opts),
            "parquet": lambda df, path, **opts: df.to_parquet(path, **opts),
        }

        writer_func = writers.get(self.target_type)
        if not writer_func:
            raise ValueError(f"Unsupported target type: {self.target_type}")

        writer_func(data, self.target_path, **self.write_options)
