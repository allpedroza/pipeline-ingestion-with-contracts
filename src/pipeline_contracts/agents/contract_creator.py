"""
Contract Creator Agent

An intelligent agent that guides users through the process of creating
complete data contracts by asking all necessary questions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from ..contracts.base import DataContract, DataType, FieldContract, QualityLevel
from .prompts import COMMON_PATTERNS


@dataclass
class FieldDefinition:
    """Holds the definition of a field collected from user input."""
    name: str
    data_type: str
    description: str
    nullable: bool = False
    unique: bool = False
    quality_level: str = "critical"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[list[str]] = None


@dataclass
class ContractDefinition:
    """Holds the complete contract definition collected from user input."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    owner: str = ""
    domain: str = ""
    tags: list[str] = field(default_factory=list)
    fields: list[FieldDefinition] = field(default_factory=list)
    min_rows: Optional[int] = None
    max_rows: Optional[int] = None
    freshness_hours: Optional[int] = None


class ContractCreatorAgent:
    """
    Agent responsible for creating data contracts through guided questions.

    This agent abstracts all technical complexity of creating a data contract,
    ensuring that all necessary information is collected through a conversational
    interface.
    """

    def __init__(self):
        self.contract_def: Optional[ContractDefinition] = None
        self.current_field: Optional[dict] = None

    def process_metadata(self, answers: dict) -> None:
        """Process metadata answers and initialize contract definition."""
        previous_fields: list[FieldDefinition] = []
        previous_integrity: dict[str, Optional[int]] = {}

        if self.contract_def is not None:
            previous_fields = self.contract_def.fields
            previous_integrity = {
                "min_rows": self.contract_def.min_rows,
                "max_rows": self.contract_def.max_rows,
                "freshness_hours": self.contract_def.freshness_hours,
            }

        # Handle custom domain
        domain = answers.get("domain", "")
        if domain == "outro" and answers.get("domain_custom"):
            domain = answers["domain_custom"]

        # Parse tags
        tags = []
        if answers.get("tags"):
            tags = [t.strip() for t in answers["tags"].split(",") if t.strip()]

        self.contract_def = ContractDefinition(
            name=answers["name"],
            version=answers.get("version", "1.0.0"),
            description=answers.get("description", ""),
            owner=answers.get("owner", ""),
            domain=domain,
            tags=tags,
        )

        if previous_fields:
            self.contract_def.fields = previous_fields

        if previous_integrity:
            self.contract_def.min_rows = previous_integrity.get("min_rows")
            self.contract_def.max_rows = previous_integrity.get("max_rows")
            self.contract_def.freshness_hours = previous_integrity.get("freshness_hours")

    def process_field(self, answers: dict) -> FieldDefinition:
        """Process field answers and create a field definition."""
        # Handle pattern
        pattern = None
        if answers.get("has_pattern"):
            pattern_type = answers.get("pattern_type", "")
            if pattern_type == "custom":
                pattern = answers.get("custom_pattern")
            elif pattern_type in COMMON_PATTERNS:
                pattern = COMMON_PATTERNS[pattern_type]

        # Handle allowed values
        allowed_values = None
        if answers.get("has_allowed_values") and answers.get("allowed_values"):
            allowed_values = [
                v.strip() for v in answers["allowed_values"].split(",")
                if v.strip()
            ]

        # Handle numeric constraints
        min_value = None
        max_value = None
        if answers.get("has_min_value") and answers.get("min_value") is not None:
            min_value = float(answers["min_value"])
        if answers.get("has_max_value") and answers.get("max_value") is not None:
            max_value = float(answers["max_value"])

        # Handle string constraints
        min_length = None
        max_length = None
        if answers.get("has_min_length") and answers.get("min_length") is not None:
            min_length = int(answers["min_length"])
        if answers.get("has_max_length") and answers.get("max_length") is not None:
            max_length = int(answers["max_length"])

        field_def = FieldDefinition(
            name=answers["name"],
            data_type=answers["data_type"],
            description=answers.get("description", ""),
            nullable=answers.get("nullable", False),
            unique=answers.get("unique", False),
            quality_level=answers.get("quality_level", "critical"),
            min_value=min_value,
            max_value=max_value,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            allowed_values=allowed_values,
        )

        return field_def

    def add_field(self, field_def: FieldDefinition) -> None:
        """Add a field to the current contract definition."""
        if self.contract_def is None:
            raise ValueError("Contract metadata must be processed first")
        self.contract_def.fields.append(field_def)

    def process_integrity(self, answers: dict) -> None:
        """Process integrity/SLA answers."""
        if self.contract_def is None:
            raise ValueError("Contract metadata must be processed first")

        if answers.get("has_min_rows") and answers.get("min_rows") is not None:
            self.contract_def.min_rows = int(answers["min_rows"])

        if answers.get("has_max_rows") and answers.get("max_rows") is not None:
            self.contract_def.max_rows = int(answers["max_rows"])

        if answers.get("has_freshness") and answers.get("freshness_hours") is not None:
            self.contract_def.freshness_hours = int(answers["freshness_hours"])

    def load_from_contract(self, contract: DataContract) -> None:
        """Preload the agent with an existing contract for edition or duplication."""

        def _copy_field(field: FieldContract) -> FieldDefinition:
            return FieldDefinition(
                name=field.name,
                data_type=field.data_type.value,
                description=field.description or "",
                nullable=field.nullable,
                unique=field.unique,
                quality_level=field.quality_level.value,
                min_value=field.min_value,
                max_value=field.max_value,
                min_length=field.min_length,
                max_length=field.max_length,
                pattern=field.pattern,
                allowed_values=field.allowed_values,
            )

        fields = [_copy_field(field) for field in contract.fields]

        self.contract_def = ContractDefinition(
            name=contract.name,
            version=contract.version,
            description=contract.description or "",
            owner=contract.owner or "",
            domain=contract.domain or "",
            tags=contract.tags,
            fields=fields,
            min_rows=contract.min_rows,
            max_rows=contract.max_rows,
            freshness_hours=contract.freshness_hours,
        )

    def build_contract(self) -> DataContract:
        """Build a DataContract object from the collected definition."""
        if self.contract_def is None:
            raise ValueError("No contract definition available")

        fields = []
        for f in self.contract_def.fields:
            field_kwargs = {
                "name": f.name,
                "data_type": DataType(f.data_type),
                "description": f.description or None,
                "nullable": f.nullable,
                "unique": f.unique,
                "quality_level": QualityLevel(f.quality_level),
            }

            if f.min_value is not None:
                field_kwargs["min_value"] = f.min_value
            if f.max_value is not None:
                field_kwargs["max_value"] = f.max_value
            if f.min_length is not None:
                field_kwargs["min_length"] = f.min_length
            if f.max_length is not None:
                field_kwargs["max_length"] = f.max_length
            if f.pattern is not None:
                field_kwargs["pattern"] = f.pattern
            if f.allowed_values is not None:
                field_kwargs["allowed_values"] = f.allowed_values

            fields.append(FieldContract(**field_kwargs))

        contract = DataContract(
            name=self.contract_def.name,
            version=self.contract_def.version,
            description=self.contract_def.description or None,
            owner=self.contract_def.owner or None,
            domain=self.contract_def.domain or None,
            tags=self.contract_def.tags or [],
            fields=fields,
            min_rows=self.contract_def.min_rows,
            max_rows=self.contract_def.max_rows,
            freshness_hours=self.contract_def.freshness_hours,
        )

        return contract

    def to_yaml_dict(self) -> dict:
        """Convert the contract definition to a YAML-friendly dictionary."""
        if self.contract_def is None:
            raise ValueError("No contract definition available")

        contract_dict: dict[str, Any] = {
            "name": self.contract_def.name,
            "version": self.contract_def.version,
        }

        if self.contract_def.description:
            contract_dict["description"] = self.contract_def.description

        if self.contract_def.owner:
            contract_dict["owner"] = self.contract_def.owner

        if self.contract_def.domain:
            contract_dict["domain"] = self.contract_def.domain

        if self.contract_def.tags:
            contract_dict["tags"] = self.contract_def.tags

        # Fields
        if self.contract_def.fields:
            contract_dict["fields"] = []
            for f in self.contract_def.fields:
                field_dict: dict[str, Any] = {
                    "name": f.name,
                    "data_type": f.data_type,
                }

                if f.nullable:
                    field_dict["nullable"] = f.nullable
                else:
                    field_dict["nullable"] = False

                if f.unique:
                    field_dict["unique"] = f.unique

                if f.description:
                    field_dict["description"] = f.description

                if f.quality_level != "critical":
                    field_dict["quality_level"] = f.quality_level

                if f.min_value is not None:
                    field_dict["min_value"] = f.min_value

                if f.max_value is not None:
                    field_dict["max_value"] = f.max_value

                if f.min_length is not None:
                    field_dict["min_length"] = f.min_length

                if f.max_length is not None:
                    field_dict["max_length"] = f.max_length

                if f.pattern is not None:
                    field_dict["pattern"] = f.pattern

                if f.allowed_values is not None:
                    field_dict["allowed_values"] = f.allowed_values

                contract_dict["fields"].append(field_dict)

        # Integrity rules
        if self.contract_def.min_rows is not None:
            contract_dict["min_rows"] = self.contract_def.min_rows

        if self.contract_def.max_rows is not None:
            contract_dict["max_rows"] = self.contract_def.max_rows

        if self.contract_def.freshness_hours is not None:
            contract_dict["freshness_hours"] = self.contract_def.freshness_hours

        return contract_dict

    def save_to_yaml(self, output_path: Path) -> Path:
        """Save the contract to a YAML file."""
        contract_dict = self.to_yaml_dict()

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                contract_dict,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        return output_path

    def generate_summary(self) -> str:
        """Generate a human-readable summary of the contract."""
        if self.contract_def is None:
            return "Nenhum contrato definido."

        lines = [
            "=" * 60,
            f"📋 RESUMO DO CONTRATO: {self.contract_def.name}",
            "=" * 60,
            "",
            "📌 METADADOS:",
            f"   Nome: {self.contract_def.name}",
            f"   Versão: {self.contract_def.version}",
        ]

        if self.contract_def.description:
            lines.append(f"   Descrição: {self.contract_def.description}")

        if self.contract_def.owner:
            lines.append(f"   Responsável: {self.contract_def.owner}")

        if self.contract_def.domain:
            lines.append(f"   Domínio: {self.contract_def.domain}")

        if self.contract_def.tags:
            lines.append(f"   Tags: {', '.join(self.contract_def.tags)}")

        lines.extend(["", f"📊 CAMPOS ({len(self.contract_def.fields)}):", ""])

        for i, f in enumerate(self.contract_def.fields, 1):
            nullable_str = "✓" if f.nullable else "✗"
            unique_str = "✓" if f.unique else "✗"

            lines.append(f"   {i}. {f.name}")
            lines.append(f"      Tipo: {f.data_type}")
            lines.append(f"      Nulo: {nullable_str} | Único: {unique_str}")

            if f.description:
                lines.append(f"      Descrição: {f.description}")

            constraints = []
            if f.min_value is not None:
                constraints.append(f"min={f.min_value}")
            if f.max_value is not None:
                constraints.append(f"max={f.max_value}")
            if f.min_length is not None:
                constraints.append(f"min_len={f.min_length}")
            if f.max_length is not None:
                constraints.append(f"max_len={f.max_length}")
            if f.pattern:
                constraints.append(f"pattern='{f.pattern[:20]}...'")
            if f.allowed_values:
                constraints.append(f"valores={f.allowed_values}")

            if constraints:
                lines.append(f"      Restrições: {', '.join(constraints)}")

            lines.append("")

        # Integrity
        integrity_rules = []
        if self.contract_def.min_rows is not None:
            integrity_rules.append(f"Mín. registros: {self.contract_def.min_rows}")
        if self.contract_def.max_rows is not None:
            integrity_rules.append(f"Máx. registros: {self.contract_def.max_rows}")
        if self.contract_def.freshness_hours is not None:
            integrity_rules.append(f"Freshness: {self.contract_def.freshness_hours}h")

        if integrity_rules:
            lines.append("✅ REGRAS DE INTEGRIDADE:")
            for rule in integrity_rules:
                lines.append(f"   • {rule}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def get_questions_for_type(self, data_type: str) -> list[str]:
        """Get the list of relevant constraint questions based on data type."""
        base_constraints = ["nullable", "unique", "quality_level", "allowed_values"]

        if data_type in ("integer", "float"):
            return base_constraints + ["min_value", "max_value"]
        elif data_type == "string":
            return base_constraints + ["min_length", "max_length", "pattern"]
        else:
            return base_constraints

    def reset(self) -> None:
        """Reset the agent state for a new contract."""
        self.contract_def = None
        self.current_field = None
