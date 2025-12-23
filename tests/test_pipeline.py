"""Tests for pipeline execution."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from pipeline_contracts.contracts.base import DataContract, DataType, FieldContract
from pipeline_contracts.pipeline.base import Pipeline, StepStatus
from pipeline_contracts.pipeline.runner import PipelineRunner, PipelineStatus
from pipeline_contracts.pipeline.steps import (
    ContractValidationStep,
    DataTransformStep,
    SourceReadStep,
    TargetWriteStep,
)


class TestPipelineStep:
    """Tests for pipeline steps."""

    def test_source_read_step_csv(self, valid_user_data):
        """Test reading CSV file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as f:
            valid_user_data.to_csv(f.name, index=False)
            temp_path = Path(f.name)

        try:
            step = SourceReadStep(
                name="read_csv",
                source_path=temp_path,
                source_type="csv",
            )
            result = step.execute(None, {})

            assert result.status == StepStatus.SUCCESS
            assert result.data is not None
            assert len(result.data) == len(valid_user_data)
        finally:
            temp_path.unlink()

    def test_source_read_step_with_custom_reader(self):
        """Test reading with custom reader function."""
        custom_data = pd.DataFrame({"col": [1, 2, 3]})

        step = SourceReadStep(
            name="custom_read",
            reader=lambda: custom_data.copy(),
        )
        result = step.execute(None, {})

        assert result.status == StepStatus.SUCCESS
        assert len(result.data) == 3

    def test_source_read_step_file_not_found(self):
        """Test reading non-existent file."""
        step = SourceReadStep(
            name="read_missing",
            source_path=Path("/nonexistent/file.csv"),
            source_type="csv",
        )
        result = step.execute(None, {})

        assert result.status == StepStatus.FAILED
        assert result.error is not None

    def test_contract_validation_step_success(
        self, sample_user_contract, valid_user_data
    ):
        """Test successful validation step."""
        step = ContractValidationStep(
            name="validate",
            contract=sample_user_contract,
        )
        result = step.execute(valid_user_data, {})

        assert result.status == StepStatus.SUCCESS
        assert "validation_result" in result.metadata

    def test_contract_validation_step_failure(
        self, sample_user_contract, invalid_user_data
    ):
        """Test failed validation step."""
        step = ContractValidationStep(
            name="validate",
            contract=sample_user_contract,
            fail_on_error=True,
        )
        result = step.execute(invalid_user_data, {})

        assert result.status == StepStatus.FAILED
        assert result.error is not None

    def test_data_transform_step(self, valid_user_data):
        """Test data transformation step."""

        def double_age(df: pd.DataFrame) -> pd.DataFrame:
            df = df.copy()
            df["age"] = df["age"].fillna(0) * 2
            return df

        step = DataTransformStep(
            name="transform",
            transform=double_age,
        )
        result = step.execute(valid_user_data, {})

        assert result.status == StepStatus.SUCCESS
        assert result.data["age"].iloc[0] == valid_user_data["age"].iloc[0] * 2

    def test_target_write_step_csv(self, valid_user_data):
        """Test writing CSV file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "output.csv"

            step = TargetWriteStep(
                name="write_csv",
                target_path=target_path,
                target_type="csv",
            )
            result = step.execute(valid_user_data, {})

            assert result.status == StepStatus.SUCCESS
            assert target_path.exists()

            # Verify content
            written_data = pd.read_csv(target_path)
            assert len(written_data) == len(valid_user_data)

    def test_target_write_step_dry_run(self, valid_user_data):
        """Test dry run skips writing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "output.csv"

            step = TargetWriteStep(
                name="write_csv",
                target_path=target_path,
                target_type="csv",
            )
            result = step.execute(valid_user_data, {"dry_run": True})

            assert result.status == StepStatus.SKIPPED
            assert not target_path.exists()


class TestPipeline:
    """Tests for Pipeline class."""

    def test_create_pipeline(self):
        """Test creating a pipeline."""
        pipeline = Pipeline(
            name="test_pipeline",
            description="A test pipeline",
        )
        assert pipeline.name == "test_pipeline"
        assert len(pipeline.steps) == 0

    def test_add_step(self, sample_user_contract):
        """Test adding a step to pipeline."""
        pipeline = Pipeline(name="test")
        step = ContractValidationStep(
            name="validate",
            contract=sample_user_contract,
        )
        pipeline.add_step(step)

        assert len(pipeline.steps) == 1
        assert pipeline.get_step("validate") is not None

    def test_add_steps_chaining(self, sample_user_contract, valid_user_data):
        """Test adding multiple steps with chaining."""
        pipeline = Pipeline(name="test")
        pipeline.add_steps(
            ContractValidationStep(name="step1", contract=sample_user_contract),
            DataTransformStep(name="step2", transform=lambda df: df),
        )

        assert len(pipeline.steps) == 2


class TestPipelineRunner:
    """Tests for PipelineRunner."""

    def test_run_simple_pipeline(self, sample_user_contract, valid_user_data):
        """Test running a simple pipeline."""
        pipeline = Pipeline(name="simple_pipeline")
        pipeline.add_step(
            DataTransformStep(
                name="passthrough",
                transform=lambda df: df,
            )
        )

        runner = PipelineRunner(verbose=False)
        result = runner.run(pipeline, initial_data=valid_user_data)

        assert result.status == PipelineStatus.SUCCESS
        assert result.is_success is True
        assert result.final_data is not None

    def test_run_pipeline_with_validation(
        self, sample_user_contract, valid_user_data
    ):
        """Test running pipeline with contract validation."""
        pipeline = Pipeline(
            name="validated_pipeline",
            source_contract=sample_user_contract,
        )
        pipeline.add_step(
            DataTransformStep(
                name="passthrough",
                transform=lambda df: df,
            )
        )

        runner = PipelineRunner(verbose=False)
        result = runner.run(pipeline, initial_data=valid_user_data)

        assert result.status == PipelineStatus.SUCCESS

    def test_run_pipeline_fail_fast(self, sample_user_contract, invalid_user_data):
        """Test fail-fast behavior."""
        pipeline = Pipeline(name="fail_fast_pipeline")
        pipeline.add_steps(
            ContractValidationStep(
                name="validate",
                contract=sample_user_contract,
            ),
            DataTransformStep(
                name="should_not_run",
                transform=lambda df: df,
            ),
        )

        runner = PipelineRunner(fail_fast=True, verbose=False)
        result = runner.run(pipeline, initial_data=invalid_user_data)

        assert result.status == PipelineStatus.FAILED
        # Only validation step should have run
        assert len(result.step_results) == 1

    def test_run_pipeline_dry_run(self, valid_user_data):
        """Test dry run mode."""
        pipeline = Pipeline(name="dry_run_pipeline")

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "output.csv"
            pipeline.add_step(
                TargetWriteStep(
                    name="write",
                    target_path=target_path,
                    target_type="csv",
                )
            )

            runner = PipelineRunner(dry_run=True, verbose=False)
            result = runner.run(pipeline, initial_data=valid_user_data)

            assert result.status == PipelineStatus.SUCCESS
            assert not target_path.exists()

    def test_pipeline_result_to_dict(self, valid_user_data):
        """Test PipelineResult.to_dict()."""
        pipeline = Pipeline(name="dict_test")
        pipeline.add_step(
            DataTransformStep(name="step", transform=lambda df: df)
        )

        runner = PipelineRunner(verbose=False)
        result = runner.run(pipeline, initial_data=valid_user_data)
        result_dict = result.to_dict()

        assert "pipeline_name" in result_dict
        assert "status" in result_dict
        assert "steps" in result_dict
        assert len(result_dict["steps"]) == 1

    def test_full_pipeline_integration(self, sample_user_contract, valid_user_data):
        """Test complete pipeline with multiple steps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create input file
            input_path = Path(temp_dir) / "input.csv"
            valid_user_data.to_csv(input_path, index=False)

            output_path = Path(temp_dir) / "output.csv"

            # Create pipeline
            pipeline = Pipeline(
                name="integration_test",
                source_contract=sample_user_contract,
            )

            def transform(df):
                df = df.copy()
                df["processed"] = True
                return df

            pipeline.add_steps(
                SourceReadStep(
                    name="read",
                    source_path=input_path,
                    source_type="csv",
                ),
                ContractValidationStep(
                    name="validate",
                    contract=sample_user_contract,
                ),
                DataTransformStep(
                    name="transform",
                    transform=transform,
                ),
                TargetWriteStep(
                    name="write",
                    target_path=output_path,
                    target_type="csv",
                ),
            )

            runner = PipelineRunner(verbose=False)
            result = runner.run(pipeline)

            assert result.status == PipelineStatus.SUCCESS
            assert output_path.exists()
            assert "processed" in result.final_data.columns
