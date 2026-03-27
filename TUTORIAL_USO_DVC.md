# 📦 ROTA Data Registry - Workflow de Teste (DVC + SSH)

Este tutorial serve como documentação de como o ambiente de Versionamento e Ingestão de Dados está estruturado, rodando localmente de forma otimizada e espelhando grandes quantidades de dados com alta velocidade para o nosso servidor central via SSH.

> **Objetivo**: Provar o funcionamento do fluxo de entrada (Ingest) e saída (Download) sem overhead e com total segurança da integridade.

---

## 1. Configurando a Segurança (Chave SSH)
Para o processo rodar utilizando o limite máximo de velocidade da rede com as dezenas de threads do DVC, não podemos engasgar na digitação de senhas a cada request de arquivo. Portanto, a chave SSH é obrigatória:

1. **Gerar a chave da sua máquina (sem senha de proteção interna):**
   ```bash
   ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
   ```

2. **Copiar a sua chave pública pro servidor Central:**
   ```bash
   ssh-copy-id -i ~/.ssh/id_ed25519 servidor@192.168.18.253
   ```
*(A partir desse momento a CLI não trava em nenhum processo).*

---

## 2. Instalando as Dependências Necessárias
O código usa um ecossistema Python moderno com DVC nativo e suporte cloud ativo.

```bash
# Caso o uv já esteja no ambiente configurado, basta:
uv sync

# Mas se estiver instalando no sistema via Pip (Workstation root):
pip install --break-system-packages "dvc[ssh]"
pip install --break-system-packages questionary typer
```

---

## 3. Realizando o DVC Ingest (Upload Rápido)
A ingestão foi reescrita utilizando **Hardlinks (os.link)**. Quando você injeta centenas de Gigabytes na registry e eles estão no mesmo disco da sua workstation:
* Copiar demoraria horas. Em nosso script leva **milissegundos**.
* E gasta exatamente **0 Bytes** adicionais.

Opcionalmente, o script base (`rota.py`) é capaz de engolir via questionário visual, porém para automações:

```bash
# Script de exemplo contido no projeto: teste_ingestao.sh
python rota.py ingest /home/victor/sarjetas/ "classificacao_sarjetas" \
    --projeto "Projeto-Validacao" \
    --engenheiro "O-Chefe" \
    --hardware "Workstation-A6000" \
    --metodo-storage "DVC-SSH-MergerFS"
```
✅ **Resultado**: DVC calcula hash instantaneamente via link físico, conecta pela sua chave nova, sobe tudo de forma assíncrona, e atrela ao Git.

---

## 4. Baixando Dados no Ambiente Target (DVC Get)
Para demonstrar que os dados não estão apenas armazenados no *Workspace* de quem subiu (cache local) e provar que o servidor SSH contém os binários, usamos o resgate de IDs:

1. **Onde achamos o ID exato injetado?**
   ```bash
   python rota.py list-data
   # Ele vai cuspir algo como: classificacao_sarjetas_20260327_160905
   ```

2. **Baixando:**
   *(Garantindo que a pasta recebedora está livre de conflitos anteriormente)*
   ```bash
   python rota.py download classificacao_sarjetas_20260327_160905 ./minha_pasta_alvo
   ```

✅ **Resultado**: Em poucos segundos a pasta `minha_pasta_alvo` nascerá com todos os arquivos binários originais, limpos, puxados das dezenas de conexões liberadas pela sua SSH Key. Tudo versionado pela nossa CLI!

---
> Elaborado por Antigravity AI. 🧙‍♂️
