#!/usr/bin/env python3
"""
Sample Pipeline - Demonstrates the pipeline contracts framework.

This example shows:
1. Loading data contracts from YAML files
2. Creating a pipeline with multiple steps
3. Validating data against contracts
4. Transforming data
5. Running the pipeline with full logging

Usage:
    python examples/sample_pipeline.py
"""

from pathlib import Path

import pandas as pd

from pipeline_contracts import (
    ContractRegistry,
    DataContract,
    Pipeline,
    PipelineRunner,
)
from pipeline_contracts.contracts.base import DataType, FieldContract
from pipeline_contracts.pipeline.steps import (
    ContractValidationStep,
    DataTransformStep,
    SourceReadStep,
    TargetWriteStep,
)

# Paths
EXAMPLES_DIR = Path(__file__).parent
CONTRACTS_DIR = EXAMPLES_DIR / "contracts"
DATA_DIR = EXAMPLES_DIR / "data"
OUTPUT_DIR = EXAMPLES_DIR / "output"


def create_enriched_users_contract() -> DataContract:
    """Create a contract for the enriched users output."""
    return DataContract(
        name="enriched_users",
        version="1.0.0",
        description="Enriched user data with derived fields",
        owner="data-platform-team",
        domain="customers",
        fields=[
            FieldContract(
                name="user_id",
                data_type=DataType.INTEGER,
                nullable=False,
                unique=True,
            ),
            FieldContract(
                name="email",
                data_type=DataType.STRING,
                nullable=False,
            ),
            FieldContract(
                name="name",
                data_type=DataType.STRING,
                nullable=False,
            ),
            FieldContract(
                name="age",
                data_type=DataType.INTEGER,
                nullable=True,
            ),
            FieldContract(
                name="country",
                data_type=DataType.STRING,
                nullable=True,
            ),
            FieldContract(
                name="status",
                data_type=DataType.STRING,
                nullable=False,
            ),
            FieldContract(
                name="created_at",
                data_type=DataType.DATETIME,
                nullable=False,
            ),
            # Derived fields
            FieldContract(
                name="email_domain",
                data_type=DataType.STRING,
                nullable=False,
                description="Email domain extracted from email",
            ),
            FieldContract(
                name="age_group",
                data_type=DataType.STRING,
                nullable=True,
                allowed_values=["young", "adult", "senior", "unknown"],
                description="Age group classification",
            ),
        ],
        min_rows=1,
    )


def enrich_users(df: pd.DataFrame) -> pd.DataFrame:
    """Transform function to enrich user data."""
    # Extract email domain
    df["email_domain"] = df["email"].str.split("@").str[1]

    # Classify age groups
    def classify_age(age):
        if pd.isna(age):
            return "unknown"
        elif age < 25:
            return "young"
        elif age < 55:
            return "adult"
        else:
            return "senior"

    df["age_group"] = df["age"].apply(classify_age)

    return df


def run_user_ingestion_pipeline():
    """Run the complete user ingestion pipeline."""
    print("=" * 60)
    print("User Ingestion Pipeline Demo")
    print("=" * 60)

    # Load contracts
    registry = ContractRegistry()
    source_contract = registry.load_from_file(CONTRACTS_DIR / "users.yaml")
    target_contract = create_enriched_users_contract()

    print(f"\nSource Contract: {source_contract.name} v{source_contract.version}")
    print(f"Target Contract: {target_contract.name} v{target_contract.version}")

    # Create pipeline
    pipeline = Pipeline(
        name="user_ingestion",
        description="Ingest, validate, and enrich user data",
        source_contract=source_contract,
        target_contract=target_contract,
    )

    # Add steps
    pipeline.add_steps(
        SourceReadStep(
            name="read_users",
            source_path=DATA_DIR / "users_valid.csv",
            source_type="csv",
            description="Read user data from CSV",
        ),
        ContractValidationStep(
            name="validate_source",
            contract=source_contract,
            description="Validate against source contract",
        ),
        DataTransformStep(
            name="enrich_data",
            transform=enrich_users,
            description="Add derived fields",
        ),
        ContractValidationStep(
            name="validate_target",
            contract=target_contract,
            description="Validate against target contract",
        ),
        TargetWriteStep(
            name="write_output",
            target_path=OUTPUT_DIR / "enriched_users.csv",
            target_type="csv",
            description="Write enriched data to CSV",
        ),
    )

    # Run pipeline
    runner = PipelineRunner(fail_fast=True, verbose=True)
    result = runner.run(pipeline)

    # Print summary
    print("\n" + "=" * 60)
    print("Pipeline Execution Summary")
    print("=" * 60)
    print(f"Status: {result.status.value}")
    print(f"Duration: {result.duration_ms:.2f}ms")
    print(f"Steps executed: {len(result.step_results)}")

    if result.final_data is not None:
        print(f"\nOutput data preview:")
        print(result.final_data.head().to_string())

    return result


def run_validation_demo():
    """Demonstrate contract validation with invalid data."""
    print("\n" + "=" * 60)
    print("Contract Validation Demo (with invalid data)")
    print("=" * 60)

    # Load contract
    registry = ContractRegistry()
    contract = registry.load_from_file(CONTRACTS_DIR / "users.yaml")

    # Create simple validation pipeline
    pipeline = Pipeline(
        name="validation_demo",
        description="Demonstrate validation failures",
    )

    pipeline.add_steps(
        SourceReadStep(
            name="read_invalid_users",
            source_path=DATA_DIR / "users_invalid.csv",
            source_type="csv",
        ),
        ContractValidationStep(
            name="validate",
            contract=contract,
            fail_on_error=True,
        ),
    )

    # Run with fail_fast=False to see all errors
    runner = PipelineRunner(fail_fast=True, verbose=True)
    result = runner.run(pipeline)

    print(f"\nValidation result: {result.status.value}")
    if result.error:
        print(f"Error details: {result.error}")

    return result


def run_dry_run_demo():
    """Demonstrate dry run mode."""
    print("\n" + "=" * 60)
    print("Dry Run Demo (no writes)")
    print("=" * 60)

    registry = ContractRegistry()
    source_contract = registry.load_from_file(CONTRACTS_DIR / "users.yaml")

    pipeline = Pipeline(
        name="dry_run_demo",
        description="Dry run demonstration",
    )

    pipeline.add_steps(
        SourceReadStep(
            name="read_users",
            source_path=DATA_DIR / "users_valid.csv",
            source_type="csv",
        ),
        ContractValidationStep(
            name="validate",
            contract=source_contract,
        ),
        TargetWriteStep(
            name="write_output",
            target_path=OUTPUT_DIR / "dry_run_output.csv",
            target_type="csv",
        ),
    )

    # Run in dry run mode
    runner = PipelineRunner(dry_run=True, verbose=True)
    result = runner.run(pipeline)

    print(f"\nDry run complete. No files were written.")
    return result


if __name__ == "__main__":
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Run demos
    run_user_ingestion_pipeline()
    run_validation_demo()
    run_dry_run_demo()

    print("\n" + "=" * 60)
    print("All demos completed!")
    print("=" * 60)
