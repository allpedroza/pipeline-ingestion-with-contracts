"""
Pipeline Contracts - A framework for pipeline ingestion with data contracts and integrity testing.
"""

from pipeline_contracts.contracts.base import DataContract
from pipeline_contracts.contracts.registry import ContractRegistry
from pipeline_contracts.pipeline.base import Pipeline, PipelineStep
from pipeline_contracts.pipeline.runner import PipelineRunner
from pipeline_contracts.validation.validator import ContractValidator

__version__ = "0.1.0"

__all__ = [
    "DataContract",
    "ContractRegistry",
    "Pipeline",
    "PipelineStep",
    "PipelineRunner",
    "ContractValidator",
]
