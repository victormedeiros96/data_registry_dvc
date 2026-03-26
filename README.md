# ROTA Data Registry 🛣️

Sistema inteligente de versionamento e gestão de datasets rodoviários para Machine Learning.

## Setup 🚀

1.  **Sincronize o ambiente:** `uv sync`
2.  **Configure o storage inicial:** `bash scripts/setup_storage.sh`
3.  **Configuração Local:** Edite o arquivo `config.toml` gerado na primeira execução para definir seus padrões.

## Uso da CLI 🛠️

A CLI automática utiliza um sistema de **Wizard/Assistente**. Caso os parâmetros opcionais não sejam passados, a ferramenta perguntará interativamente.

-   **Ingerir Dados:**
    ```bash
    uv run rota.py ingest /caminho/pasta nome_projeto
    ```
-   **Listagem Visual:**
    ```bash
    uv run rota.py list-data
    ```
-   **Remoção Interativa (Git/DVC):**
    ```bash
    uv run rota.py remove
    ```
-   **Verificação de Integridade:**
    ```bash
    uv run rota.py verify
    ```
-   **Pre-fetch para Treino YOLO:**
    ```bash
    uv run rota.py prefetch "query_ou_data" --target ./ready_folder
    ```

## Dashboard 📊

Visualize e filtre seus datasets através do navegador:
```bash
uv run streamlit run dashboard.py
```

---
*Mestrado Unipampa / Nova Rota do Oeste*
