# ROTA Data Registry 🛣️

Sistema de versionamento e gerenciamento de datasets para Machine Learning.

## Setup
1. Sincronize o ambiente: `uv sync`
2. Configure o storage: `bash scripts/setup_storage.sh`

## Uso
- **Ingerir:** `uv run rota.py ingest /origem nome_dataset`
- **Listar:** `uv run rota.py list-data`
- **Baixar:** `uv run rota.py download id_dataset /destino`
# data_registry_dvc
