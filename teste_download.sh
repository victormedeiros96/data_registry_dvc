#!/bin/bash

# Sai se houver erros
set -e

echo "======================================================"
echo "🧹 Limpando o cache local para simular uma máquina nova..."
echo "======================================================"
rm -rf .dvc/cache
rm -rf teste_download_sinalizacao
rm -rf teste_download_sarjetas
echo "Cache do DVC local apagado! Os dados agora precisam vir da Nuvem (SSH 192.168.18.253)."

echo ""
echo "======================================================"
echo "📦 Baixando Dataset 1: Sinalização Horizontal"
echo "======================================================"
python rota.py download classificacao_sinalizacao_horizontal_20260327_160859 ./teste_download_sinalizacao

echo ""
echo "======================================================"
echo "📦 Baixando Dataset 2: Sarjetas"
echo "======================================================"
python rota.py download classificacao_sarjetas_20260327_160905 ./teste_download_sarjetas

echo ""
echo "======================================================"
echo "📋 Verificando o resultado:"
echo "======================================================"
ls -lh teste_download_sinalizacao
ls -lh teste_download_sarjetas
echo ""
echo "✨ Download testado com sucesso a partir do servidor remoto!"
