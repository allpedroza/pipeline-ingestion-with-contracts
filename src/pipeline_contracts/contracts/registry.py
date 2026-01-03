"""
Contract Registry - Central storage and management of data contracts.
"""

import json
from pathlib import Path
from typing import Iterator

import yaml
from packaging.version import InvalidVersion, Version

from pipeline_contracts.contracts.base import DataContract


class ContractRegistry:
    """
    Registry for managing data contracts.

    Provides:
    - CRUD operations for contracts
    - Loading from files (YAML/JSON)
    - Version management
    - Contract discovery
    """

    def __init__(self) -> None:
        self._contracts: dict[str, DataContract] = {}

    def register(self, contract: DataContract) -> None:
        """Register a contract in the registry."""
        key = f"{contract.name}:{contract.version}"
        if key in self._contracts:
            raise ValueError(f"Contract '{key}' already registered")
        self._contracts[key] = contract

    def get(self, name: str, version: str | None = None) -> DataContract | None:
        """
        Get a contract by name and optional version.

        If version is not specified, returns the latest version.
        """
        if version:
            return self._contracts.get(f"{name}:{version}")

        # Find latest version
        matching = [c for c in self._contracts.values() if c.name == name]
        if not matching:
            return None

        def version_key(contract: DataContract) -> Version:
            try:
                return Version(contract.version)
            except InvalidVersion:
                return Version("0")

        return max(matching, key=version_key)

    def list_contracts(self) -> list[DataContract]:
        """List all registered contracts."""
        return list(self._contracts.values())

    def list_names(self) -> list[str]:
        """List unique contract names."""
        return list(set(c.name for c in self._contracts.values()))

    def __iter__(self) -> Iterator[DataContract]:
        return iter(self._contracts.values())

    def __len__(self) -> int:
        return len(self._contracts)

    def __contains__(self, name: str) -> bool:
        return any(c.name == name for c in self._contracts.values())

    def load_from_file(self, path: Path | str) -> DataContract:
        """Load a contract from a YAML or JSON file."""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Contract file not found: {path}")

        content = path.read_text()

        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(content)
        elif path.suffix == ".json":
            data = json.loads(content)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        contract = DataContract.model_validate(data)
        self.register(contract)
        return contract

    def load_from_directory(self, directory: Path | str) -> list[DataContract]:
        """Load all contracts from a directory."""
        directory = Path(directory)

        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        contracts = []
        for pattern in ("*.yaml", "*.yml", "*.json"):
            for file_path in directory.glob(pattern):
                try:
                    contract = self.load_from_file(file_path)
                    contracts.append(contract)
                except Exception as e:
                    print(f"Warning: Failed to load {file_path}: {e}")

        return contracts

    def save_to_file(self, contract: DataContract, path: Path | str) -> None:
        """Save a contract to a YAML or JSON file."""
        path = Path(path)

        data = contract.model_dump(mode="json")

        if path.suffix in (".yaml", ".yml"):
            content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        elif path.suffix == ".json":
            content = json.dumps(data, indent=2)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def remove(self, name: str, version: str | None = None) -> bool:
        """Remove a contract from the registry."""
        if version:
            key = f"{name}:{version}"
            if key in self._contracts:
                del self._contracts[key]
                return True
            return False

        # Remove all versions
        keys_to_remove = [k for k in self._contracts if k.startswith(f"{name}:")]
        for key in keys_to_remove:
            del self._contracts[key]
        return len(keys_to_remove) > 0


# Global registry instance
_global_registry: ContractRegistry | None = None


def get_registry() -> ContractRegistry:
    """Get the global contract registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ContractRegistry()
    return _global_registry
