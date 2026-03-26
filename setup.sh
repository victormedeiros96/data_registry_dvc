#!/bin/bash

# ROTA Data Registry - Setup Script 🚀
# Este script instala as dependências básicas (uv), configura o ambiente virtual e instala as libs do projeto.

set -e # Aborta em caso de erro

echo "--- 🔍 Verificando Pré-requisitos ---"

# 1. Verificar Curl
if ! command -v curl &> /dev/null; then
    echo "❌ Erro: 'curl' não encontrado. Por favor, instale o curl primeiro."
    exit 1
fi

# 2. Instalar UV (Gestor de pacotes ultra-rápido)
if ! command -v uv &> /dev/null; then
    echo "📦 Instalando 'uv' (Astral)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Adiciona ao PATH para a sessão atual
    source $HOME/.cargo/env
else
    echo "✅ 'uv' já está instalado."
fi

# 3. Sincronizar Projeto (Cria .venv e instala DVC[ssh], Typer, Streamlit, etc.)
echo "🏗️  Configurando ambiente virtual e dependências..."
uv sync

# 4. Inicializar DVC (se necessário)
if [ ! -d ".dvc" ]; then
    echo "🗄️  Inicializando DVC no repositório local..."
    uv run dvc init --no-scm || echo "⚠️  DVC já inicializado ou requer permissão."
fi

echo "--- ✨ Setup Concluído com Sucesso! ---"
echo "Para começar a usar, você pode:"
echo "1. Ativar o ambiente: source .venv/bin/activate"
echo "2. Ingerir dados: uv run rota.py ingest /caminho/pasta nome_projeto"
echo "3. Abrir o dashboard: uv run streamlit run dashboard.py"
echo "---------------------------------------"
