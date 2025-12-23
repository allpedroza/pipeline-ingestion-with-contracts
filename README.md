# Pipeline Contracts

Framework para ingestão de pipelines de dados com **Data Contracts** e testes de integridade.

## 🎯 Objetivo

Este framework permite:

- **Criar contratos de dados rapidamente** com agente interativo guiado
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

# Setup com uv (recomendado - mais rápido)
./setup.sh
source .venv/bin/activate

# Ou usando make
make setup
source .venv/bin/activate

# Ou instalação tradicional com pip
pip install -e ".[dev]"
```

---

## 🤖 Contract Creator Agent (Novo!)

O **Contract Creator Agent** é um assistente interativo que guia você na criação de contratos de dados completos, **sem precisar conhecer a sintaxe YAML ou as especificações técnicas**.

### Por que usar o Agente?

| Modo Manual | Com o Agente |
|-------------|--------------|
| Precisa conhecer sintaxe YAML | Interface guiada passo-a-passo |
| Risco de erros de formatação | Validação automática |
| Precisa lembrar todos os campos | Perguntas guiadas garantem completude |
| Consultar documentação constantemente | Ajuda contextual em cada pergunta |

### Iniciando o Agente

```bash
# Via CLI principal
pipeline agent create

# Ou diretamente
contract-agent create

# Ou via make
make agent
```

### Fluxo Interativo

O agente guia você através de **3 seções** para garantir um contrato completo:

```
╔══════════════════════════════════════════════════════════════════╗
║           🗂️  ASSISTENTE DE CRIAÇÃO DE CONTRATOS DE DADOS         ║
╠══════════════════════════════════════════════════════════════════╣
║  Este assistente irá guiá-lo através do processo de criação      ║
║  de um contrato de dados completo.                               ║
╚══════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────┐
│  📋 SEÇÃO 1/3: METADADOS DO CONTRATO                             │
└──────────────────────────────────────────────────────────────────┘
  • Nome do contrato
  • Versão (semver)
  • Descrição e propósito
  • Owner/responsável
  • Domínio de negócio
  • Tags de categorização

┌──────────────────────────────────────────────────────────────────┐
│  📊 SEÇÃO 2/3: DEFINIÇÃO DOS CAMPOS                              │
└──────────────────────────────────────────────────────────────────┘
  Para cada campo:
  • Nome e tipo de dado
  • Nullable / Unique
  • Nível de qualidade (critical/warning/info)
  • Constraints específicos por tipo:
    - Numéricos: min/max value
    - Strings: min/max length, padrões (email, CPF, regex)
  • Valores permitidos (enum)

┌──────────────────────────────────────────────────────────────────┐
│  ✅ SEÇÃO 3/3: REGRAS DE INTEGRIDADE                             │
└──────────────────────────────────────────────────────────────────┘
  • Número mínimo de registros
  • Número máximo de registros
  • Freshness SLA (idade máxima dos dados)
```

### Exemplo de Sessão

```bash
$ pipeline agent create

Qual é o NOME do contrato? user_events

O nome é o identificador único do contrato.
Use snake_case (ex: 'user_events', 'order_items')

Qual é a VERSÃO do contrato? [1.0.0] 1.0.0

Descreva o PROPÓSITO deste contrato: Eventos de interação dos usuários

Quem é o RESPONSÁVEL (owner)? data-platform-team

Qual é o DOMÍNIO de negócio?
  1. customers
  2. commerce
  3. finance
  ...
Digite o número ou nome da opção: analytics

# ... continua para campos e integridade ...

═══════════════════════════════════════════════════════════════
📋 RESUMO DO CONTRATO: user_events
═══════════════════════════════════════════════════════════════

📌 METADADOS:
   Nome: user_events
   Versão: 1.0.0
   Descrição: Eventos de interação dos usuários
   Responsável: data-platform-team
   Domínio: analytics

📊 CAMPOS (3):

   1. event_id
      Tipo: string
      Nulo: ✗ | Único: ✓
      Restrições: pattern='^EVT-[A-Z0-9]{12}$'

   2. user_id
      Tipo: integer
      Nulo: ✗ | Único: ✗

   3. event_type
      Tipo: string
      Nulo: ✗ | Único: ✗
      Restrições: valores=['click', 'view', 'purchase']

✅ REGRAS DE INTEGRIDADE:
   • Mín. registros: 1000
   • Freshness: 1h

═══════════════════════════════════════════════════════════════

📄 Preview do arquivo YAML:
╭─────────────────────────────────────────────────────────────────╮
│ name: user_events                                               │
│ version: "1.0.0"                                                │
│ description: Eventos de interação dos usuários                  │
│ owner: data-platform-team                                       │
│ domain: analytics                                               │
│ ...                                                             │
╰─────────────────────────────────────────────────────────────────╯

Deseja salvar o contrato? [Y/n] y

✅ CONTRATO CRIADO COM SUCESSO!
Arquivo salvo em: contracts/user_events.yaml
```

### Comandos do Agente

```bash
# Criar novo contrato interativamente
pipeline agent create

# Criar em diretório específico
pipeline agent create --output-dir ./meus-contratos

# Listar tipos de dados suportados
pipeline agent list-types

# Listar padrões de validação disponíveis (email, CPF, etc.)
pipeline agent list-patterns

# Listar níveis de qualidade
pipeline agent list-quality-levels

# Ver exemplo completo de contrato
pipeline agent example
```

### Padrões Pré-definidos

O agente inclui padrões de validação prontos para uso:

| Padrão | Descrição | Exemplo |
|--------|-----------|---------|
| `email` | Endereço de email | user@example.com |
| `cpf` | CPF brasileiro | 123.456.789-00 |
| `cnpj` | CNPJ brasileiro | 12.345.678/0001-90 |
| `telefone` | Número de telefone | +55 11 99999-9999 |
| `cep` | CEP brasileiro | 01234-567 |
| `uuid` | UUID v4 | 550e8400-e29b-41d4-a716-446655440000 |
| `url` | URL válida | https://example.com |
| `custom` | Regex personalizado | Você define! |

### Uso Programático

```python
from pipeline_contracts import InteractiveContractSession
from pathlib import Path

# Sessão interativa
session = InteractiveContractSession(output_dir=Path("contracts"))
contract_path = session.run()

# Ou criação direta via dicionário
session = InteractiveContractSession(output_dir=Path("contracts"))
contract_path = session.run_from_dict({
    "name": "my_contract",
    "version": "1.0.0",
    "description": "Contract description",
    "owner": "my-team",
    "domain": "analytics",
    "fields": [
        {
            "name": "id",
            "data_type": "integer",
            "nullable": False,
            "unique": True,
        }
    ],
    "has_min_rows": True,
    "min_rows": 100,
})
```

---

## 🚀 Quick Start

### 1. Crie um Contrato com o Agente

```bash
pipeline agent create
# Siga as perguntas interativas...
```

### 2. Ou Defina Manualmente (YAML)

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

### 3. Valide seus Dados

```bash
pipeline validate contracts/users.yaml data/users.csv
```

### 4. Crie um Pipeline

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

---

## 📐 Arquitetura

```
pipeline-contracts/
├── src/pipeline_contracts/
│   ├── agents/              # 🤖 Contract Creator Agent
│   │   ├── contract_creator.py   # Core logic
│   │   ├── interactive_session.py # Terminal UI
│   │   ├── prompts.py            # Questions & patterns
│   │   └── cli.py                # Agent CLI
│   ├── contracts/           # Data Contracts
│   │   ├── base.py          # DataContract, FieldContract
│   │   └── registry.py      # ContractRegistry
│   ├── pipeline/            # Pipeline Framework
│   │   ├── base.py          # Pipeline, PipelineStep
│   │   ├── runner.py        # PipelineRunner
│   │   └── steps.py         # Built-in steps
│   ├── validation/          # Validation
│   │   └── validator.py     # ContractValidator
│   └── cli.py               # Main CLI
├── tests/                   # Testes
├── examples/                # Exemplos
├── Makefile                 # Comandos de desenvolvimento
└── setup.sh                 # Setup do ambiente
```

---

## 📋 Data Contracts

### Tipos de Dados Suportados

| Tipo | Descrição |
|------|-----------|
| `string` | Texto |
| `integer` | Números inteiros |
| `float` | Números decimais |
| `boolean` | Verdadeiro/Falso |
| `date` | Data (YYYY-MM-DD) |
| `datetime` | Data e hora |
| `array` | Lista de valores |
| `object` | Objeto complexo/JSON |

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

---

## 🔧 CLI & Makefile

### Comandos CLI

```bash
# Agente de contratos
pipeline agent create          # Criar contrato interativamente
pipeline agent list-types      # Listar tipos de dados
pipeline agent list-patterns   # Listar padrões de validação

# Validação
pipeline validate contract.yaml data.csv

# Visualização
pipeline show contract.yaml

# Inicialização
pipeline init ./my-project
```

### Comandos Make

```bash
make help       # Lista todos os comandos
make setup      # Setup completo do ambiente
make test       # Rodar testes
make lint       # Verificar código
make agent      # Iniciar agente de contratos
make clean      # Limpar arquivos temporários
```

---

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
        processed_data = data.copy()
        processed_data["new_column"] = "value"

        return StepResult(
            step_name=self.name,
            status=StepStatus.SUCCESS,
            data=processed_data,
        )
```

---

## 🧪 Testes

```bash
# Execute todos os testes
make test

# Com cobertura
make test-cov

# Ou diretamente
pytest tests/ -v
```

---

## 🛠️ Tecnologias

- **[Pydantic](https://docs.pydantic.dev/)**: Validação e serialização de modelos
- **[Pandera](https://pandera.readthedocs.io/)**: Validação de DataFrames
- **[Pandas](https://pandas.pydata.org/)**: Manipulação de dados
- **[Rich](https://rich.readthedocs.io/)**: Output formatado no terminal
- **[Typer](https://typer.tiangolo.com/)**: CLI interface
- **[uv](https://github.com/astral-sh/uv)**: Gerenciamento de ambiente (opcional)

---

## 📝 Licença

MIT License
