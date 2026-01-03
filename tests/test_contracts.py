"""Tests for data contracts."""

import tempfile
from pathlib import Path

import pytest
import yaml

from pipeline_contracts.agents.interactive_session import InteractiveContractSession
from pipeline_contracts.contracts.base import (
    DataContract,
    DataType,
    FieldContract,
    QualityLevel,
)
from pipeline_contracts.contracts.registry import ContractRegistry


class TestFieldContract:
    """Tests for FieldContract."""

    def test_create_basic_field(self):
        """Test creating a basic field contract."""
        field = FieldContract(
            name="test_field",
            data_type=DataType.STRING,
        )
        assert field.name == "test_field"
        assert field.data_type == DataType.STRING
        assert field.nullable is False
        assert field.unique is False

    def test_create_field_with_constraints(self):
        """Test creating a field with constraints."""
        field = FieldContract(
            name="age",
            data_type=DataType.INTEGER,
            nullable=True,
            min_value=0,
            max_value=150,
            quality_level=QualityLevel.WARNING,
        )
        assert field.min_value == 0
        assert field.max_value == 150
        assert field.quality_level == QualityLevel.WARNING

    def test_to_pandera_column(self):
        """Test converting field to Pandera column."""
        field = FieldContract(
            name="email",
            data_type=DataType.STRING,
            nullable=False,
            pattern=r"^[\w\.\-]+@[\w\.\-]+\.\w+$",
        )
        column = field.to_pandera_column()
        assert column.name == "email"
        assert column.nullable is False


class TestDataContract:
    """Tests for DataContract."""

    def test_create_basic_contract(self):
        """Test creating a basic contract."""
        contract = DataContract(
            name="test_contract",
            version="1.0.0",
        )
        assert contract.name == "test_contract"
        assert contract.version == "1.0.0"
        assert len(contract.fields) == 0

    def test_add_field(self, sample_user_contract):
        """Test adding a field to contract."""
        new_field = FieldContract(
            name="new_field",
            data_type=DataType.STRING,
        )
        sample_user_contract.add_field(new_field)
        assert sample_user_contract.get_field("new_field") is not None

    def test_add_duplicate_field_raises(self, sample_user_contract):
        """Test that adding duplicate field raises error."""
        duplicate = FieldContract(
            name="id",
            data_type=DataType.INTEGER,
        )
        with pytest.raises(ValueError, match="already exists"):
            sample_user_contract.add_field(duplicate)

    def test_get_field(self, sample_user_contract):
        """Test getting a field by name."""
        field = sample_user_contract.get_field("email")
        assert field is not None
        assert field.data_type == DataType.STRING

    def test_get_nonexistent_field(self, sample_user_contract):
        """Test getting a nonexistent field returns None."""
        assert sample_user_contract.get_field("nonexistent") is None

    def test_to_pandera_schema(self, sample_user_contract):
        """Test converting contract to Pandera schema."""
        schema = sample_user_contract.to_pandera_schema()
        assert "id" in schema.columns
        assert "email" in schema.columns


class TestContractRegistry:
    """Tests for ContractRegistry."""

    def test_register_contract(self, sample_user_contract):
        """Test registering a contract."""
        registry = ContractRegistry()
        registry.register(sample_user_contract)
        assert sample_user_contract.name in registry

    def test_register_duplicate_raises(self, sample_user_contract):
        """Test that registering duplicate contract raises error."""
        registry = ContractRegistry()
        registry.register(sample_user_contract)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(sample_user_contract)

    def test_get_contract(self, sample_user_contract):
        """Test getting a contract."""
        registry = ContractRegistry()
        registry.register(sample_user_contract)
        retrieved = registry.get("test_users")
        assert retrieved is not None
        assert retrieved.name == sample_user_contract.name

    def test_get_with_version(self, sample_user_contract):
        """Test getting a contract with specific version."""
        registry = ContractRegistry()
        registry.register(sample_user_contract)
        retrieved = registry.get("test_users", "1.0.0")
        assert retrieved is not None

    def test_get_returns_latest_version(self):
        """Registry should return the numerically latest version when none is provided."""
        registry = ContractRegistry()
        older = DataContract(name="orders", version="1.2.0")
        newer = DataContract(name="orders", version="1.10.0")
        registry.register(older)
        registry.register(newer)

        retrieved = registry.get("orders")

        assert retrieved is not None
        assert retrieved.version == "1.10.0"

    def test_list_contracts(self, sample_user_contract):
        """Test listing all contracts."""
        registry = ContractRegistry()
        registry.register(sample_user_contract)
        contracts = registry.list_contracts()
        assert len(contracts) == 1

    def test_load_from_yaml_file(self):
        """Test loading contract from YAML file."""
        contract_data = {
            "name": "yaml_contract",
            "version": "1.0.0",
            "fields": [
                {"name": "id", "data_type": "integer", "nullable": False},
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(contract_data, f)
            temp_path = Path(f.name)

        try:
            registry = ContractRegistry()
            contract = registry.load_from_file(temp_path)
            assert contract.name == "yaml_contract"
            assert len(contract.fields) == 1
        finally:
            temp_path.unlink()

    def test_remove_contract(self, sample_user_contract):
        """Test removing a contract."""
        registry = ContractRegistry()
        registry.register(sample_user_contract)
        assert registry.remove("test_users") is True
        assert sample_user_contract.name not in registry

    def test_remove_nonexistent_contract(self):
        """Test removing nonexistent contract returns False."""
        registry = ContractRegistry()
        assert registry.remove("nonexistent") is False


def test_interactive_session_prefills_latest_version(tmp_path: Path):
    """Interactive agent should suggest the latest available contract version."""
    existing_contracts = [
        {
            "name": "orders",
            "version": "1.0.0",
            "fields": [{"name": "id", "data_type": "integer", "nullable": False}],
        },
        {
            "name": "orders",
            "version": "2.1.0",
            "fields": [{"name": "id", "data_type": "integer", "nullable": False}],
        },
    ]

    for idx, contract in enumerate(existing_contracts):
        path = tmp_path / f"orders_v{idx}.yaml"
        path.write_text(yaml.dump(contract))

    session = InteractiveContractSession(output_dir=tmp_path)

    assert session._get_version_default("orders") == "2.1.0"
