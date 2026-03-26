#!/bin/bash
# CONFIGURAÇÕES DO SERVIDOR (Edite aqui!)
REMOTE_URL="ssh://usuario@ip-do-servidor:/mnt/storage_total"
REMOTE_NAME="storage-central"

echo "🔧 Configurando DVC Remote em: $REMOTE_URL"
dvc remote add -d $REMOTE_NAME $REMOTE_URL --force

echo "⚡ Ativando otimizações de filesystem (reflink/hardlink)..."
dvc config cache.type reflink,hardlink
dvc config cache.protected true

echo "✅ Setup concluído!"
