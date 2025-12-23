"""Tests for contract validation."""

import pandas as pd
import pytest

from pipeline_contracts.contracts.base import DataContract, DataType, FieldContract
from pipeline_contracts.validation.validator import (
    ContractValidator,
    ValidationStatus,
)


class TestContractValidator:
    """Tests for ContractValidator."""

    def test_validate_valid_data(self, sample_user_contract, valid_user_data):
        """Test validation passes for valid data."""
        validator = ContractValidator(sample_user_contract)
        result = validator.validate(valid_user_data)

        assert result.status == ValidationStatus.PASSED
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_invalid_data(self, sample_user_contract, invalid_user_data):
        """Test validation fails for invalid data."""
        validator = ContractValidator(sample_user_contract)
        result = validator.validate(invalid_user_data)

        assert result.status == ValidationStatus.FAILED
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_validate_min_rows(self, sample_user_contract, empty_dataframe):
        """Test min_rows constraint."""
        validator = ContractValidator(sample_user_contract)
        result = validator.validate(empty_dataframe)

        assert result.status == ValidationStatus.FAILED
        assert any("min_rows" in e.check for e in result.errors)

    def test_validate_max_rows(self):
        """Test max_rows constraint."""
        contract = DataContract(
            name="small_table",
            version="1.0.0",
            max_rows=5,
            fields=[
                FieldContract(name="id", data_type=DataType.INTEGER),
            ],
        )

        large_data = pd.DataFrame({"id": range(10)})
        validator = ContractValidator(contract)
        result = validator.validate(large_data)

        assert result.status == ValidationStatus.FAILED
        assert any("max_rows" in e.check for e in result.errors)

    def test_validate_missing_required_column(self, sample_user_contract):
        """Test validation fails when required column is missing."""
        incomplete_data = pd.DataFrame(
            {
                "id": [1, 2],
                # Missing 'email' column
                "age": [25, 30],
                "status": ["active", "inactive"],
            }
        )

        validator = ContractValidator(sample_user_contract)
        result = validator.validate(incomplete_data)

        assert result.status == ValidationStatus.FAILED
        assert any("email" in (e.field or "") for e in result.errors)

    def test_validate_and_raise(self, sample_user_contract, invalid_user_data):
        """Test validate_and_raise raises exception for invalid data."""
        validator = ContractValidator(sample_user_contract)

        with pytest.raises(ValueError, match="Contract validation failed"):
            validator.validate_and_raise(invalid_user_data)

    def test_validate_and_raise_returns_data(
        self, sample_user_contract, valid_user_data
    ):
        """Test validate_and_raise returns data for valid input."""
        validator = ContractValidator(sample_user_contract)
        result = validator.validate_and_raise(valid_user_data)

        assert result is not None
        assert len(result) == len(valid_user_data)

    def test_validation_result_to_dict(self, sample_user_contract, valid_user_data):
        """Test ValidationResult.to_dict()."""
        validator = ContractValidator(sample_user_contract)
        result = validator.validate(valid_user_data)
        result_dict = result.to_dict()

        assert "contract_name" in result_dict
        assert "status" in result_dict
        assert "errors" in result_dict
        assert result_dict["is_valid"] is True

    def test_validate_type_coercion(self):
        """Test that type coercion works correctly."""
        contract = DataContract(
            name="coerce_test",
            version="1.0.0",
            fields=[
                FieldContract(name="value", data_type=DataType.INTEGER),
            ],
        )

        # Data with string numbers that should be coerced
        data = pd.DataFrame({"value": ["1", "2", "3"]})

        validator = ContractValidator(contract)
        result = validator.validate(data)

        assert result.is_valid is True

    def test_validate_nullable_field(self):
        """Test nullable field validation."""
        contract = DataContract(
            name="nullable_test",
            version="1.0.0",
            fields=[
                FieldContract(
                    name="optional_field",
                    data_type=DataType.STRING,
                    nullable=True,
                ),
            ],
        )

        data = pd.DataFrame({"optional_field": ["value", None, "another"]})

        validator = ContractValidator(contract)
        result = validator.validate(data)

        assert result.is_valid is True

    def test_validate_non_nullable_field_with_nulls(self):
        """Test non-nullable field with null values fails."""
        contract = DataContract(
            name="required_test",
            version="1.0.0",
            fields=[
                FieldContract(
                    name="required_field",
                    data_type=DataType.STRING,
                    nullable=False,
                ),
            ],
        )

        data = pd.DataFrame({"required_field": ["value", None, "another"]})

        validator = ContractValidator(contract)
        result = validator.validate(data)

        assert result.is_valid is False

    def test_validate_allowed_values(self):
        """Test allowed_values constraint."""
        contract = DataContract(
            name="enum_test",
            version="1.0.0",
            fields=[
                FieldContract(
                    name="status",
                    data_type=DataType.STRING,
                    allowed_values=["a", "b", "c"],
                ),
            ],
        )

        # Valid data
        valid_data = pd.DataFrame({"status": ["a", "b", "c"]})
        validator = ContractValidator(contract)
        assert validator.validate(valid_data).is_valid is True

        # Invalid data
        invalid_data = pd.DataFrame({"status": ["a", "b", "invalid"]})
        assert validator.validate(invalid_data).is_valid is False
