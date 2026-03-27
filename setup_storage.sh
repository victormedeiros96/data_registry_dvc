#!/bin/bash

# Este script configura a segurança de chaves SSH, o Registry do DVC e prepara o ambiente para trabalhar com o servidor Storage Central sem pedir senhas repetidamente.

set -e

# Cores
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}🚀  BEM-VINDO AO ASSISTENTE DE CONFIGURAÇÃO DE STORAGE DO ROTA  ${NC}"
echo -e "${CYAN}================================================================${NC}"
echo ""

# Pergunta Interativa
read -p "Digite o USUÁRIO SSH do servidor [ex: servidor]: " SSH_USER
SSH_USER=${SSH_USER:-servidor}

read -p "Digite o ENDEREÇO IP/HOSTNAME do servidor [ex: 192.168.18.253]: " SSH_IP
SSH_IP=${SSH_IP:-192.168.18.253}

read -p "Digite o CAMINHO ABSOLUTO da pasta do Storage lá no servidor [ex: /home/servidor/DVC_DATA_TEST/]: " SSH_FOLDER
SSH_FOLDER=${SSH_FOLDER:-/home/servidor/DVC_DATA_TEST/}

echo ""
echo -e "${YELLOW}>> Gerando/Verificando sua Chave de Segurança (SSH Key)...${NC}"
if [ ! -f ~/.ssh/id_ed25519 ]; then
    ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
    echo -e "${GREEN}Chave gerada com sucesso!${NC}"
else
    echo -e "${GREEN}Você já possui uma chave SSH configurada! Pulando etapa...${NC}"
fi

echo ""
echo -e "${YELLOW}>> Enviando sua chave pro servidor (Você deve digitar a senha UMA ÚLTIMA VEZ se pedida):${NC}"
echo "--------------------------------------------------------"
ssh-copy-id -i ~/.ssh/id_ed25519 "${SSH_USER}@${SSH_IP}"
echo "--------------------------------------------------------"

echo ""
echo -e "${YELLOW}>> Configurando o ambiente DVC para usar esse Storage...${NC}"
# Substitui e cria o controle do DVC apontando pra pasta requerida
dvc remote add -d default_remote "ssh://${SSH_USER}@${SSH_IP}${SSH_FOLDER}" --force
echo -e "${GREEN}Storage principal do DVC configurado em: ssh://${SSH_USER}@${SSH_IP}${SSH_FOLDER}!${NC}"

echo ""
echo -e "${CYAN}================================================================${NC}"
echo -e "${GREEN}✨ AMBIENTE TOTALMENTE CONFIGURADO! ✨${NC}"
echo -e "${CYAN}================================================================${NC}"
echo "Agora você pode usar as ferramentas de INGESTÃO e DOWNLOAD via UV:"
echo "👉 uv run rota.py ingest /caminho/pasta NOME_DATASET"
echo "👉 uv run rota.py download ID_NOVO"
echo "Aproveite a altíssima velocidade do DVC e do Hardlink! 🚀"
echo ""
