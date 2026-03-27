#!/bin/bash

# Sai do script caso algum comando falhe
set -e

echo "======================================================"
echo "🔧 Configurando Storage Remoto de Teste no DVC..."
echo "======================================================"

# Adiciona/Atualiza o remote no DVC
dvc remote add -d teste_remote ssh://servidor@192.168.18.253/home/servidor/DVC_DATA_TEST/ --force

# Se caso precisar forçar um usuário específico do SSH descomente a linha abaixo:
# dvc remote modify teste_remote user servidor

echo ""
echo "======================================================"
echo "🚀 Iniciando ingestão do Dataset: Sinalização Horizontal"
echo "======================================================"

# Removemos espaços e caracteres especiais do nome (classificacao_sinalizacao_horizontal)
python rota.py ingest /home/victor/classificacao5/Classificacao/ "classificacao_sinalizacao_horizontal" \
    --projeto "Teste Automatizado" \
    --engenheiro "Victor" \
    --hardware "Workstation-Local" \
    --metodo-storage "DVC-SSH-MergerFS"

echo ""
echo "======================================================"
echo "🚀 Iniciando ingestão do Dataset: Sarjetas"
echo "======================================================"

# Removemos espaços do nome (classificacao_sarjetas)
python rota.py ingest /home/victor/sarjetas/ "classificacao_sarjetas" \
    --projeto "Teste Automatizado" \
    --engenheiro "Victor" \
    --hardware "Workstation-Local" \
    --metodo-storage "DVC-SSH-MergerFS"

echo ""
echo "======================================================"
echo "📋 Listando os datasets devidamente registrados"
echo "======================================================"
python rota.py list-data

echo ""
echo "✨ Teste concluído com sucesso!"
