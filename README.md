# Pipeline Contracts

Framework para ingestão de pipelines de dados com **Data Contracts** e testes de integridade.
**Nova feature: LLM Agent criador de Data Contract**

## 🎯 Objetivo

Este framework permite:

- **Definir contratos de dados** (schemas, regras de qualidade, metadados)
- **Validar dados** contra contratos usando Pandera
- **Construir pipelines** modulares com múltiplos steps
- **Executar testes de integridade** automatizados
- **Monitorar execução** com logging detalhado

## 📦 Instalação

```bash
# Clone o repositório
git clone https://github.com/allpedroza/pipeline-ingestion-with-contracts.git
cd pipeline-ingestion-with-contracts

# Instale em modo de desenvolvimento
pip install -e ".[dev]"
```

## 🚀 Quick Start

### 1. Defina um Data Contract (YAML)

```yaml
# contracts/users.yaml
name: users
version: "1.0.0"
description: User data contract
owner: data-team

fields:
  - name: user_id
    data_type: integer
    nullable: false
    unique: true

  - name: email
    data_type: string
    nullable: false
    pattern: "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"

  - name: status
    data_type: string
    nullable: false
    allowed_values: [active, inactive, pending]

min_rows: 1
```

### 2. Crie um Pipeline

```python
from pipeline_contracts import Pipeline, PipelineRunner, ContractRegistry
from pipeline_contracts.pipeline.steps import (
    SourceReadStep,
    ContractValidationStep,
    DataTransformStep,
    TargetWriteStep,
)

# Carregue o contrato
registry = ContractRegistry()
contract = registry.load_from_file("contracts/users.yaml")

# Crie o pipeline
pipeline = Pipeline(
    name="user_ingestion",
    source_contract=contract,
)

pipeline.add_steps(
    SourceReadStep(
        name="read_csv",
        source_path="data/users.csv",
        source_type="csv",
    ),
    ContractValidationStep(
        name="validate",
        contract=contract,
    ),
    DataTransformStep(
        name="transform",
        transform=lambda df: df.assign(processed=True),
    ),
    TargetWriteStep(
        name="write_output",
        target_path="output/users_processed.csv",
        target_type="csv",
    ),
)

# Execute
runner = PipelineRunner(verbose=True)
result = runner.run(pipeline)

print(f"Status: {result.status}")
print(f"Rows: {len(result.final_data)}")
```

### 3. Use a CLI

```bash
# Valide dados contra um contrato
pipeline validate contracts/users.yaml data/users.csv

# Veja detalhes de um contrato
pipeline show contracts/users.yaml

# Inicialize um novo projeto
pipeline init ./my-project
```

## 📐 Arquitetura

```
pipeline-contracts/
├── src/pipeline_contracts/
│   ├── contracts/           # Data Contracts
│   │   ├── base.py          # DataContract, FieldContract
│   │   └── registry.py      # ContractRegistry
│   ├── pipeline/            # Pipeline Framework
│   │   ├── base.py          # Pipeline, PipelineStep
│   │   ├── runner.py        # PipelineRunner
│   │   └── steps.py         # Built-in steps
│   ├── validation/          # Validation
│   │   └── validator.py     # ContractValidator
│   └── cli.py               # CLI interface
├── tests/                   # Testes
│   ├── test_contracts.py
│   ├── test_validation.py
│   ├── test_pipeline.py
│   └── test_integrity.py    # Testes de integridade
└── examples/                # Exemplos
    ├── contracts/
    ├── data/
    └── sample_pipeline.py
```

## 📋 Data Contracts

### Tipos de Dados Suportados

| Tipo | Descrição |
|------|-----------|
| `string` | Texto |
| `integer` | Números inteiros |
| `float` | Números decimais |
| `boolean` | Verdadeiro/Falso |
| `date` | Data |
| `datetime` | Data e hora |

### Constraints Disponíveis

| Constraint | Tipos | Descrição |
|------------|-------|-----------|
| `nullable` | Todos | Permite valores nulos |
| `unique` | Todos | Valores devem ser únicos |
| `min_value` | integer, float | Valor mínimo |
| `max_value` | integer, float | Valor máximo |
| `min_length` | string | Tamanho mínimo |
| `max_length` | string | Tamanho máximo |
| `pattern` | string | Regex pattern |
| `allowed_values` | Todos | Lista de valores permitidos |

### Quality Levels

```yaml
fields:
  - name: age
    data_type: integer
    quality_level: warning  # critical (default), warning, info
```

- **critical**: Pipeline falha se violado
- **warning**: Log de aviso, pipeline continua
- **info**: Apenas informativo

## 🔧 Pipeline Steps

### Built-in Steps

| Step | Descrição |
|------|-----------|
| `SourceReadStep` | Lê dados de CSV, JSON, Parquet |
| `ContractValidationStep` | Valida dados contra contrato |
| `DataTransformStep` | Aplica transformação customizada |
| `TargetWriteStep` | Escreve dados para arquivo |

### Custom Steps

```python
from pipeline_contracts.pipeline.base import PipelineStep, StepResult, StepStatus

class MyCustomStep(PipelineStep):
    def execute(self, data, context):
        # Sua lógica aqui
        processed_data = data.copy()
        processed_data["new_column"] = "value"

        return StepResult(
            step_name=self.name,
            status=StepStatus.SUCCESS,
            data=processed_data,
        )
```

## 🧪 Testes

```bash
# Execute todos os testes
pytest

# Com cobertura
pytest --cov=pipeline_contracts

# Apenas testes de integridade
pytest tests/test_integrity.py -v
```

### Tipos de Testes

1. **Unit Tests**: Testam componentes isolados
2. **Integration Tests**: Testam fluxos completos
3. **Integrity Tests**: Verificam integridade dos dados

## 🔄 Execução do Pipeline

### Modos de Execução

```python
# Fail Fast (padrão): Para na primeira falha
runner = PipelineRunner(fail_fast=True)

# Continue on Error: Continua mesmo com falhas
runner = PipelineRunner(fail_fast=False)

# Dry Run: Não escreve em targets
runner = PipelineRunner(dry_run=True)

# Silent: Sem output no console
runner = PipelineRunner(verbose=False)
```

### Resultado da Execução

```python
result = runner.run(pipeline)

print(result.status)        # SUCCESS, FAILED, PARTIAL
print(result.is_success)    # True/False
print(result.duration_ms)   # Tempo de execução
print(result.final_data)    # DataFrame final
print(result.step_results)  # Resultados por step
```

## 📊 Exemplo Completo

Veja o exemplo completo em `examples/sample_pipeline.py`:

```bash
python examples/sample_pipeline.py
```

## 🛠️ Tecnologias

- **[Pydantic](https://docs.pydantic.dev/)**: Validação e serialização de modelos
- **[Pandera](https://pandera.readthedocs.io/)**: Validação de DataFrames
- **[Pandas](https://pandas.pydata.org/)**: Manipulação de dados
- **[Rich](https://rich.readthedocs.io/)**: Output formatado no terminal
- **[Typer](https://typer.tiangolo.com/)**: CLI interface

## 📝 Licença

MIT License
