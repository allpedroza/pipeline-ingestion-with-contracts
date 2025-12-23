"""
Base classes for defining data contracts.

Data contracts define the expected schema, quality rules, and metadata
for data flowing through pipelines.
"""

from datetime import datetime
from enum import Enum
from typing import Any

import pandera as pa
from pydantic import BaseModel, Field


class DataType(str, Enum):
    """Supported data types for contract fields."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    ARRAY = "array"
    OBJECT = "object"


class QualityLevel(str, Enum):
    """Quality level requirements for data."""

    CRITICAL = "critical"  # Must pass, pipeline fails otherwise
    WARNING = "warning"  # Should pass, logs warning if fails
    INFO = "info"  # Informational, logged but doesn't affect pipeline


class FieldContract(BaseModel):
    """Contract definition for a single field/column."""

    name: str = Field(..., description="Field name")
    data_type: DataType = Field(..., description="Expected data type")
    nullable: bool = Field(default=False, description="Whether null values are allowed")
    unique: bool = Field(default=False, description="Whether values must be unique")
    description: str | None = Field(default=None, description="Field description")

    # Quality constraints
    min_value: float | int | None = Field(default=None, description="Minimum value (numeric)")
    max_value: float | int | None = Field(default=None, description="Maximum value (numeric)")
    min_length: int | None = Field(default=None, description="Minimum length (string)")
    max_length: int | None = Field(default=None, description="Maximum length (string)")
    pattern: str | None = Field(default=None, description="Regex pattern (string)")
    allowed_values: list[Any] | None = Field(default=None, description="List of allowed values")

    # Quality level for this field's constraints
    quality_level: QualityLevel = Field(
        default=QualityLevel.CRITICAL, description="Quality level for constraint violations"
    )

    def to_pandera_column(self) -> pa.Column:
        """Convert field contract to Pandera column for validation."""
        checks = []

        # Type mapping
        dtype_map = {
            DataType.STRING: str,
            DataType.INTEGER: int,
            DataType.FLOAT: float,
            DataType.BOOLEAN: bool,
            DataType.DATE: "datetime64[ns]",
            DataType.DATETIME: "datetime64[ns]",
        }

        dtype = dtype_map.get(self.data_type, object)

        # Add checks based on constraints
        if self.min_value is not None:
            checks.append(pa.Check.ge(self.min_value))
        if self.max_value is not None:
            checks.append(pa.Check.le(self.max_value))
        if self.min_length is not None:
            checks.append(pa.Check.str_length(min_value=self.min_length))
        if self.max_length is not None:
            checks.append(pa.Check.str_length(max_value=self.max_length))
        if self.pattern is not None:
            checks.append(pa.Check.str_matches(self.pattern))
        if self.allowed_values is not None:
            checks.append(pa.Check.isin(self.allowed_values))

        return pa.Column(
            dtype=dtype,
            nullable=self.nullable,
            unique=self.unique,
            checks=checks if checks else None,
            name=self.name,
        )


class DataContract(BaseModel):
    """
    Data Contract definition for a dataset/table.

    A data contract specifies:
    - Schema (fields and their types)
    - Quality rules and constraints
    - Metadata (owner, version, SLAs)
    """

    # Identity
    name: str = Field(..., description="Contract name (unique identifier)")
    version: str = Field(default="1.0.0", description="Contract version (semver)")
    description: str | None = Field(default=None, description="Contract description")

    # Schema
    fields: list[FieldContract] = Field(default_factory=list, description="Field definitions")

    # Metadata
    owner: str | None = Field(default=None, description="Data owner (team/person)")
    domain: str | None = Field(default=None, description="Business domain")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")

    # Quality
    freshness_hours: int | None = Field(
        default=None, description="Maximum age of data in hours"
    )
    min_rows: int | None = Field(default=None, description="Minimum expected row count")
    max_rows: int | None = Field(default=None, description="Maximum expected row count")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_pandera_schema(self) -> pa.DataFrameSchema:
        """Convert data contract to Pandera DataFrameSchema for validation."""
        columns = {field.name: field.to_pandera_column() for field in self.fields}

        checks = []
        if self.min_rows is not None:
            checks.append(pa.Check(lambda df: len(df) >= self.min_rows))  # type: ignore
        if self.max_rows is not None:
            checks.append(pa.Check(lambda df: len(df) <= self.max_rows))  # type: ignore

        return pa.DataFrameSchema(
            columns=columns,
            checks=checks if checks else None,
            strict=False,  # Allow extra columns
            coerce=True,  # Attempt type coercion
        )

    def get_field(self, name: str) -> FieldContract | None:
        """Get a field contract by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None

    def add_field(self, field: FieldContract) -> None:
        """Add a field to the contract."""
        if self.get_field(field.name) is not None:
            raise ValueError(f"Field '{field.name}' already exists in contract")
        self.fields.append(field)
        self.updated_at = datetime.utcnow()
