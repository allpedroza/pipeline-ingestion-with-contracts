"""
Contract Validator - Validates data against contracts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd
import pandera as pa
from pandera.errors import SchemaErrors

from pipeline_contracts.contracts.base import DataContract, QualityLevel


class ValidationStatus(str, Enum):
    """Validation result status."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class ValidationError:
    """Details of a validation error."""

    field: str | None
    check: str
    message: str
    quality_level: QualityLevel
    failed_values: list[Any] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of validating data against a contract."""

    contract_name: str
    contract_version: str
    status: ValidationStatus
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    row_count: int = 0
    validated_at: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no critical errors)."""
        return self.status in (ValidationStatus.PASSED, ValidationStatus.WARNING)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "contract_name": self.contract_name,
            "contract_version": self.contract_version,
            "status": self.status.value,
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "row_count": self.row_count,
            "validated_at": self.validated_at.isoformat(),
            "duration_ms": self.duration_ms,
            "errors": [
                {
                    "field": e.field,
                    "check": e.check,
                    "message": e.message,
                    "quality_level": e.quality_level.value,
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "field": w.field,
                    "check": w.check,
                    "message": w.message,
                    "quality_level": w.quality_level.value,
                }
                for w in self.warnings
            ],
        }


class ContractValidator:
    """
    Validates data against data contracts.

    Supports:
    - Schema validation (types, nullability, uniqueness)
    - Quality checks (ranges, patterns, allowed values)
    - Custom validations
    - Detailed error reporting
    """

    def __init__(self, contract: DataContract) -> None:
        self.contract = contract
        self._schema = contract.to_pandera_schema()

    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """
        Validate a DataFrame against the contract.

        Returns a ValidationResult with details of any violations.
        """
        start_time = datetime.utcnow()
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        # Check required columns exist
        required_columns = {f.name for f in self.contract.fields if not f.nullable}
        missing_columns = required_columns - set(data.columns)
        for col in missing_columns:
            errors.append(
                ValidationError(
                    field=col,
                    check="column_exists",
                    message=f"Required column '{col}' is missing",
                    quality_level=QualityLevel.CRITICAL,
                )
            )

        # Run Pandera validation
        try:
            self._schema.validate(data, lazy=True)
        except SchemaErrors as e:
            for error_dict in e.failure_cases.to_dict("records"):
                field_contract = self.contract.get_field(str(error_dict.get("column", "")))
                quality_level = (
                    field_contract.quality_level if field_contract else QualityLevel.CRITICAL
                )

                validation_error = ValidationError(
                    field=error_dict.get("column"),
                    check=str(error_dict.get("check", "unknown")),
                    message=str(error_dict.get("failure_case", "Validation failed")),
                    quality_level=quality_level,
                )

                if quality_level == QualityLevel.CRITICAL:
                    errors.append(validation_error)
                else:
                    warnings.append(validation_error)

        # Additional contract-level validations
        if self.contract.min_rows is not None and len(data) < self.contract.min_rows:
            errors.append(
                ValidationError(
                    field=None,
                    check="min_rows",
                    message=f"Row count {len(data)} is below minimum {self.contract.min_rows}",
                    quality_level=QualityLevel.CRITICAL,
                )
            )

        if self.contract.max_rows is not None and len(data) > self.contract.max_rows:
            errors.append(
                ValidationError(
                    field=None,
                    check="max_rows",
                    message=f"Row count {len(data)} exceeds maximum {self.contract.max_rows}",
                    quality_level=QualityLevel.CRITICAL,
                )
            )

        # Determine overall status
        if errors:
            status = ValidationStatus.FAILED
        elif warnings:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.PASSED

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds() * 1000

        return ValidationResult(
            contract_name=self.contract.name,
            contract_version=self.contract.version,
            status=status,
            errors=errors,
            warnings=warnings,
            row_count=len(data),
            validated_at=start_time,
            duration_ms=duration,
        )

    def validate_and_raise(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Validate data and raise exception if validation fails.

        Returns the validated DataFrame if successful.
        """
        result = self.validate(data)
        if not result.is_valid:
            error_messages = [f"- {e.field}: {e.message}" for e in result.errors]
            raise ValueError(
                f"Contract validation failed for '{self.contract.name}':\n"
                + "\n".join(error_messages)
            )
        return data
