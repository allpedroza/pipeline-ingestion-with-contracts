"""
Pipeline Integrity Tests.

These tests verify the integrity of the pipeline framework by testing
end-to-end scenarios and ensuring data quality throughout the pipeline.
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from pipeline_contracts.contracts.base import DataContract, DataType, FieldContract
from pipeline_contracts.contracts.registry import ContractRegistry
from pipeline_contracts.pipeline.base import Pipeline
from pipeline_contracts.pipeline.runner import PipelineRunner, PipelineStatus
from pipeline_contracts.pipeline.steps import (
    ContractValidationStep,
    DataTransformStep,
    SourceReadStep,
    TargetWriteStep,
)
from pipeline_contracts.validation.validator import ContractValidator


class TestDataIntegrity:
    """Tests for data integrity throughout pipeline execution."""

    def test_data_not_mutated_during_validation(self):
        """Ensure validation doesn't mutate input data."""
        contract = DataContract(
            name="immutable_test",
            version="1.0.0",
            fields=[
                FieldContract(name="value", data_type=DataType.INTEGER),
            ],
        )

        original_data = pd.DataFrame({"value": [1, 2, 3]})
        original_copy = original_data.copy()

        validator = ContractValidator(contract)
        validator.validate(original_data)

        pd.testing.assert_frame_equal(original_data, original_copy)

    def test_data_lineage_preserved(self):
        """Test that data flows correctly through pipeline steps."""
        pipeline = Pipeline(name="lineage_test")

        def add_step_marker(step_name: str):
            def transform(df: pd.DataFrame) -> pd.DataFrame:
                df = df.copy()
                df[f"step_{step_name}"] = True
                return df

            return transform

        pipeline.add_steps(
            DataTransformStep(name="step1", transform=add_step_marker("1")),
            DataTransformStep(name="step2", transform=add_step_marker("2")),
            DataTransformStep(name="step3", transform=add_step_marker("3")),
        )

        input_data = pd.DataFrame({"id": [1, 2, 3]})
        runner = PipelineRunner(verbose=False)
        result = runner.run(pipeline, initial_data=input_data)

        assert result.is_success
        assert "step_1" in result.final_data.columns
        assert "step_2" in result.final_data.columns
        assert "step_3" in result.final_data.columns

    def test_row_count_preserved_without_filtering(self):
        """Test that row count is preserved when no filtering occurs."""
        contract = DataContract(
            name="row_test",
            version="1.0.0",
            fields=[
                FieldContract(name="id", data_type=DataType.INTEGER),
            ],
        )

        input_data = pd.DataFrame({"id": range(100)})

        pipeline = Pipeline(name="row_count_test")
        pipeline.add_steps(
            ContractValidationStep(name="validate", contract=contract),
            DataTransformStep(name="transform", transform=lambda df: df.copy()),
        )

        runner = PipelineRunner(verbose=False)
        result = runner.run(pipeline, initial_data=input_data)

        assert len(result.final_data) == 100


class TestContractIntegrity:
    """Tests for contract integrity and version management."""

    def test_contract_version_uniqueness(self):
        """Test that same contract+version cannot be registered twice."""
        registry = ContractRegistry()

        contract_v1 = DataContract(
            name="versioned",
            version="1.0.0",
            fields=[FieldContract(name="id", data_type=DataType.INTEGER)],
        )

        registry.register(contract_v1)

        duplicate = DataContract(
            name="versioned",
            version="1.0.0",
            fields=[FieldContract(name="different", data_type=DataType.STRING)],
        )

        with pytest.raises(ValueError, match="already registered"):
            registry.register(duplicate)

    def test_contract_versioning(self):
        """Test multiple versions of same contract."""
        registry = ContractRegistry()

        contract_v1 = DataContract(
            name="evolving",
            version="1.0.0",
            fields=[FieldContract(name="id", data_type=DataType.INTEGER)],
        )

        contract_v2 = DataContract(
            name="evolving",
            version="2.0.0",
            fields=[
                FieldContract(name="id", data_type=DataType.INTEGER),
                FieldContract(name="new_field", data_type=DataType.STRING),
            ],
        )

        registry.register(contract_v1)
        registry.register(contract_v2)

        # Get specific version
        v1 = registry.get("evolving", "1.0.0")
        v2 = registry.get("evolving", "2.0.0")

        assert len(v1.fields) == 1
        assert len(v2.fields) == 2

        # Get latest version (should be v2)
        latest = registry.get("evolving")
        assert latest.version == "2.0.0"

    def test_contract_yaml_roundtrip(self):
        """Test that contracts survive YAML serialization."""
        original = DataContract(
            name="roundtrip_test",
            version="1.0.0",
            description="Test contract",
            owner="test-team",
            fields=[
                FieldContract(
                    name="id",
                    data_type=DataType.INTEGER,
                    nullable=False,
                    unique=True,
                ),
                FieldContract(
                    name="value",
                    data_type=DataType.FLOAT,
                    min_value=0.0,
                    max_value=100.0,
                ),
            ],
            min_rows=1,
            max_rows=1000,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "contract.yaml"

            # Save
            registry = ContractRegistry()
            registry.register(original)
            registry.save_to_file(original, file_path)

            # Load
            new_registry = ContractRegistry()
            loaded = new_registry.load_from_file(file_path)

            # Verify
            assert loaded.name == original.name
            assert loaded.version == original.version
            assert loaded.description == original.description
            assert loaded.min_rows == original.min_rows
            assert len(loaded.fields) == len(original.fields)


class TestPipelineIntegrity:
    """Tests for pipeline execution integrity."""

    def test_failed_step_stops_pipeline(self):
        """Test that pipeline stops on failed step in fail-fast mode."""
        executed_steps = []

        def track_step(name: str):
            def transform(df: pd.DataFrame) -> pd.DataFrame:
                executed_steps.append(name)
                return df.copy()

            return transform

        def failing_transform(df: pd.DataFrame) -> pd.DataFrame:
            executed_steps.append("failing")
            raise ValueError("Intentional failure")

        pipeline = Pipeline(name="fail_test")
        pipeline.add_steps(
            DataTransformStep(name="step1", transform=track_step("step1")),
            DataTransformStep(name="fail", transform=failing_transform),
            DataTransformStep(name="step3", transform=track_step("step3")),
        )

        runner = PipelineRunner(fail_fast=True, verbose=False)
        result = runner.run(pipeline, initial_data=pd.DataFrame({"id": [1]}))

        assert result.status == PipelineStatus.FAILED
        assert "step1" in executed_steps
        assert "failing" in executed_steps
        assert "step3" not in executed_steps

    def test_source_target_contract_validation(self):
        """Test both source and target contracts are validated."""
        source_contract = DataContract(
            name="source",
            version="1.0.0",
            fields=[
                FieldContract(name="input_val", data_type=DataType.INTEGER),
            ],
        )

        target_contract = DataContract(
            name="target",
            version="1.0.0",
            fields=[
                FieldContract(name="input_val", data_type=DataType.INTEGER),
                FieldContract(name="output_val", data_type=DataType.INTEGER),
            ],
        )

        def add_output(df: pd.DataFrame) -> pd.DataFrame:
            df = df.copy()
            df["output_val"] = df["input_val"] * 2
            return df

        pipeline = Pipeline(
            name="dual_contract_test",
            source_contract=source_contract,
            target_contract=target_contract,
        )
        pipeline.add_step(DataTransformStep(name="transform", transform=add_output))

        input_data = pd.DataFrame({"input_val": [1, 2, 3]})

        runner = PipelineRunner(verbose=False)
        result = runner.run(pipeline, initial_data=input_data)

        assert result.is_success
        assert "output_val" in result.final_data.columns

    def test_pipeline_idempotency(self):
        """Test that running same pipeline twice produces same results."""
        contract = DataContract(
            name="idempotent",
            version="1.0.0",
            fields=[
                FieldContract(name="value", data_type=DataType.INTEGER),
            ],
        )

        def deterministic_transform(df: pd.DataFrame) -> pd.DataFrame:
            df = df.copy()
            df["doubled"] = df["value"] * 2
            return df

        pipeline = Pipeline(name="idempotent_test")
        pipeline.add_steps(
            ContractValidationStep(name="validate", contract=contract),
            DataTransformStep(name="transform", transform=deterministic_transform),
        )

        input_data = pd.DataFrame({"value": [1, 2, 3, 4, 5]})

        runner = PipelineRunner(verbose=False)

        result1 = runner.run(pipeline, initial_data=input_data.copy())
        result2 = runner.run(pipeline, initial_data=input_data.copy())

        pd.testing.assert_frame_equal(result1.final_data, result2.final_data)

    def test_end_to_end_file_processing(self):
        """Test complete file-to-file pipeline."""
        contract = DataContract(
            name="file_test",
            version="1.0.0",
            fields=[
                FieldContract(name="id", data_type=DataType.INTEGER),
                FieldContract(name="name", data_type=DataType.STRING),
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.csv"
            output_path = Path(temp_dir) / "output.csv"

            # Create input
            input_data = pd.DataFrame(
                {
                    "id": [1, 2, 3],
                    "name": ["Alice", "Bob", "Charlie"],
                }
            )
            input_data.to_csv(input_path, index=False)

            # Create pipeline
            pipeline = Pipeline(name="file_e2e")
            pipeline.add_steps(
                SourceReadStep(name="read", source_path=input_path, source_type="csv"),
                ContractValidationStep(name="validate", contract=contract),
                DataTransformStep(
                    name="upper",
                    transform=lambda df: df.assign(name=df["name"].str.upper()),
                ),
                TargetWriteStep(
                    name="write", target_path=output_path, target_type="csv"
                ),
            )

            runner = PipelineRunner(verbose=False)
            result = runner.run(pipeline)

            assert result.is_success
            assert output_path.exists()

            # Verify output
            output_data = pd.read_csv(output_path)
            assert output_data["name"].tolist() == ["ALICE", "BOB", "CHARLIE"]
