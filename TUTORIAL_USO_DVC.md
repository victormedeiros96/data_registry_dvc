# 📦 ROTA Data Registry - Guia de Deploy e Uso

Este repositório configura de forma otimizada um **Data Registry** escalável de ponta a ponta. Usamos **DVC** sobre SSH para armazenar terabytes de imagens com consumo nativo do HD em tempo zero (usando Hardlinks). 
Todo o ecossistema é encapsulado pelo **UV**.

---

## 🚀 1. Configurando o Ambiente em 1 Instante
Nós montamos um Script Assistente super simples! Ele interativamente te pergunta os dados do Servidor de Arquivos (Storage), cria a camada de segurança automaticamente e destrava o DVC na sua máquina para trabalhar sem burocracias.

1. **Faça o Clone do projeto e instale as dependências pelo UV**:
   ```bash
   git clone https://github.com/victormedeiros96/data_registry_dvc.git
   cd data_registry_dvc
   uv sync
   ```

2. **Rode o Assistente de Configuração (Apenas a primeira vez!)**:
   ```bash
   chmod +x setup_storage.sh
   ./setup_storage.sh
   ```
   *O assistente irá solicitar o IP do seu Servidor (ex: `192.168.18.253`), o caminho no disco e vai autenticar a sua chave pública lá. Insira a senha apenas uma única vez quando ele pedir.*

---

## 💾 2. Ingerindo Arquivos (Zero-Copy Upload)
Com o armazenamento destravado, mande os dados pro servidor! Nós aplicamos uma otimização monstruosa usando `os.link`. Subir pastas de dezenas de GB é agora um processo praticamente instantâneo na sua Workstation, sem estourar o limite de armazenamento temporário!

Comando padrão (usando `uv run` para isolamento de ambiente):
```bash
uv run rota.py ingest /caminho/para/pasta_local NOME_DATASET_FACIL
```

**Exemplo Prático**:
```bash
uv run rota.py ingest /home/victor/sarjetas/ "classificacao_sarjetas"
```
O DVC atrela o dataset a um hash inviolável, envia (Push) dezenas de conexões simétricas em background lá para o seu servidor *Storage* sem engasgos de senha, e ainda faz o Commit no `.dvc` direto em seu Git Log!

---

## 📥 3. Recuperando os Dados (Download)
Prove ao seu Diretor que a ferramenta bate o ponto! Ninguém vai baixar dados velhos ou mal referenciados.

1. **Ache o ID exato injetado na ferramenta:**
   ```bash
   uv run rota.py list-data
   ```

2. **Faça o Download assíncrono hiper-rápido:**
   ```bash
   uv run rota.py download ID_DO_DATASET ./meu_novo_experimento_local
   ```
   Você já tem 100% dos dados brutos espelhados no diretório `meu_novo_experimento_local` com apenas esse comando, prontinho para colocar pro YOLO!

---
> Ferramenta otimizada em hardlinks, fluxos de SSH puro e ecossistema `UV`. 🧙‍♂️
