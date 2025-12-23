"""
Base classes for pipeline definition.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd

from pipeline_contracts.contracts.base import DataContract


class StepStatus(str, Enum):
    """Status of a pipeline step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of executing a pipeline step."""

    step_name: str
    status: StepStatus
    data: pd.DataFrame | None = None
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class PipelineStep(ABC):
    """
    Abstract base class for pipeline steps.

    Each step can:
    - Transform data
    - Validate against contracts
    - Read from sources
    - Write to targets
    """

    def __init__(self, name: str, description: str | None = None) -> None:
        self.name = name
        self.description = description
        self.status = StepStatus.PENDING

    @abstractmethod
    def execute(self, data: pd.DataFrame | None, context: dict[str, Any]) -> StepResult:
        """Execute the step and return the result."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


@dataclass
class PipelineConfig:
    """Configuration for a pipeline."""

    name: str
    description: str | None = None
    source_contract: DataContract | None = None
    target_contract: DataContract | None = None
    fail_fast: bool = True  # Stop on first error
    dry_run: bool = False  # Don't write to targets


class Pipeline:
    """
    Data pipeline with contract validation.

    A pipeline consists of:
    - Source contract (input validation)
    - Steps (transformations, validations)
    - Target contract (output validation)
    """

    def __init__(
        self,
        name: str,
        description: str | None = None,
        source_contract: DataContract | None = None,
        target_contract: DataContract | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.source_contract = source_contract
        self.target_contract = target_contract
        self.steps: list[PipelineStep] = []
        self.created_at = datetime.utcnow()

    def add_step(self, step: PipelineStep) -> "Pipeline":
        """Add a step to the pipeline. Returns self for chaining."""
        self.steps.append(step)
        return self

    def add_steps(self, *steps: PipelineStep) -> "Pipeline":
        """Add multiple steps to the pipeline."""
        for step in steps:
            self.add_step(step)
        return self

    def get_step(self, name: str) -> PipelineStep | None:
        """Get a step by name."""
        for step in self.steps:
            if step.name == name:
                return step
        return None

    def __repr__(self) -> str:
        return f"Pipeline(name='{self.name}', steps={len(self.steps)})"

    def __len__(self) -> int:
        return len(self.steps)

    def __iter__(self):
        return iter(self.steps)
