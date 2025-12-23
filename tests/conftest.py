"""Pytest configuration and fixtures."""

from datetime import datetime

import pandas as pd
import pytest

from pipeline_contracts.contracts.base import DataContract, DataType, FieldContract


@pytest.fixture
def sample_user_contract() -> DataContract:
    """Create a sample user contract for testing."""
    return DataContract(
        name="test_users",
        version="1.0.0",
        description="Test user contract",
        owner="test-team",
        fields=[
            FieldContract(
                name="id",
                data_type=DataType.INTEGER,
                nullable=False,
                unique=True,
            ),
            FieldContract(
                name="email",
                data_type=DataType.STRING,
                nullable=False,
                # Simple email pattern for testing
                pattern=r".+@.+\..+",
            ),
            FieldContract(
                name="age",
                data_type=DataType.FLOAT,  # Use float to handle NaN
                nullable=True,
                min_value=0,
                max_value=150,
            ),
            FieldContract(
                name="status",
                data_type=DataType.STRING,
                nullable=False,
                allowed_values=["active", "inactive"],
            ),
        ],
        min_rows=1,
        max_rows=1000,
    )


@pytest.fixture
def valid_user_data() -> pd.DataFrame:
    """Create valid user data for testing."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "email": ["a@b.com", "c@d.org", "e@f.net"],
            "age": [25, 30, None],
            "status": ["active", "inactive", "active"],
        }
    )


@pytest.fixture
def invalid_user_data() -> pd.DataFrame:
    """Create invalid user data for testing."""
    return pd.DataFrame(
        {
            "id": [1, 1, 3],  # Duplicate IDs
            "email": ["invalid", "c@d.org", "e@f.net"],  # Invalid email
            "age": [25, -5, 200],  # Invalid ages
            "status": ["active", "unknown", "active"],  # Invalid status
        }
    )


@pytest.fixture
def empty_dataframe() -> pd.DataFrame:
    """Create an empty DataFrame."""
    return pd.DataFrame(columns=["id", "email", "age", "status"])
