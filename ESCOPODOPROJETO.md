Data Registry: Memorial Descritivo e Especificação Técnica

## 1. Introdução e Motivação
No cenário de Visão Computacional aplicado a infraestrutura rodoviária (Mestrado Unipampa / Nova Rota do Oeste), o gerenciamento de datasets apresenta três desafios críticos:
1.  **Volume e Escala:** Imagens de alta resolução e vídeos de inspeção superam rapidamente a capacidade de HDs individuais (limite de 12TB).
2.  **Redundância Oculta:** Coletas em diferentes períodos no mesmo trecho geram imagens idênticas, que ocupam espaço desnecessário se não houver desduplicação.
3.  **Rastreabilidade (Data Drift):** Modelos de Deep Learning (YOLOv11/PyTorch) são sensíveis a mudanças no dataset. É vital saber exatamente qual "snapshot" de dados treinou qual modelo.

O **ROTA Data Registry** resolve isso unindo o controle de versão de código (Git) com o controle de versão de dados (DVC) em um storage unificado (MergerFS).

---

## 2. Decisões Arquiteturais e Justificativas

### 2.1 Por que DVC (Data Version Control)?
Diferente do Git LFS, o DVC não armazena os binários dentro do servidor Git. Ele cria arquivos de ponteiro (`.dvc`) que contêm hashes MD5.
* **Vantagem:** Permite que o repositório Git permaneça leve (KBs), enquanto os TBs de dados residem em qualquer storage SSH, S3 ou local.
* **Desduplicação:** Se duas coletas diferentes contêm a mesma imagem, o DVC armazena apenas uma cópia física no storage, economizando espaço de forma transparente.

### 2.2 Por que MergerFS no Servidor de 12TB+?
Para expandir o storage além do limite físico de um HD sem a complexidade ou o risco de um RAID 0.
* **Escolha:** MergerFS (FUSE-based).
* **Motivação:** Permite unir HDs de tamanhos e sistemas de arquivos diferentes. Se um disco falhar, os dados nos outros discos permanecem legíveis. Diferente do LVM, não exige formatação, permitindo aproveitar HDs que já possuam dados.
* **Política de Escrita (`mfs`):** Garante que o disco com mais espaço livre receba os novos datasets, equilibrando o desgaste e o preenchimento.

### 2.3 Por que Nomenclatura com Timestamps?
Em ambientes de pesquisa e produção, o nome do dataset (ex: `trecho-norte`) é insuficiente.
* **Regra:** `nome-projeto_YYYYMMDD_HHMMSS`.
* **Motivação:** Garante **imutabilidade**. Nunca sobrescrevemos um dado. Se uma nova filtragem for feita no mesmo trecho, ela ganha um novo timestamp. Isso permite que a CLI funcione como um sistema de consulta temporal (Time-Travel).

### 2.4 Por que `uv` para Gestão de Ambiente?
* **Motivação:** Como usuário de **Arch Linux**, a velocidade e a isolação são prioridades. O `uv` (escrito em Rust) resolve dependências em milissegundos e garante que a CLI `rota.py` tenha um ambiente reprodutível em qualquer workstation (ThinkStation PX ou servidores da Unipampa).

---

## 3. Especificação do Fluxo de Dados (Pipeline)

### 3.1 Ingestão (Ingest)
1.  **Hash:** O DVC varre a pasta local e gera hashes para cada arquivo.
2.  **Referenciamento:** Cria-se o arquivo `.dvc` e um `.json` de metadados.
3.  **Transferência:** `dvc push` via SSH para o pool MergerFS.
4.  **Versionamento:** O Git commita os ponteiros.
5.  **Limpeza:** Opcionalmente, remove-se a origem para liberar o SSD da workstation.

### 3.2 Recuperação (Download/Pull)
1.  **Consulta:** O usuário busca via `list-data` usando filtros parciais (ex: `202603`).
2.  **Linkagem Inteligente:** Ao baixar, se o sistema de arquivos suportar (XFS/BTRFS), o DVC usa **reflinks**. O arquivo aparece na pasta de treino instantaneamente sem ocupar espaço extra se já estiver no cache local.

---

## 4. Estrutura de Metadados (`.json`)
Cada dataset é acompanhado de um arquivo JSON para facilitar futuras integrações com bancos de dados (ex: MongoDB/PostgreSQL):
```json
{
  "dataset_id": "nome-projeto_20260325_120000",
  "projeto": "Nova Rota do Oeste / ANTT",
  "engenheiro": "Victor Medeiros",
  "origem_fisica": "/home/victor/inspecao/video01",
  "hardware_ingest": "ThinkStation-PX-A6000",
  "metodo_storage": "DVC-SSH-MergerFS"
}
```

---

## 5. Manutenção e Escalabilidade
* **Adição de Disco:** Para adicionar mais 12TB, basta plugar o HD, montar e adicionar o path ao `/etc/fstab` do MergerFS. O DVC reconhecerá o aumento de espaço automaticamente.
* **Garbage Collection:** O comando `dvc gc` deve ser executado periodicamente no servidor para remover arquivos "órfãos" (hashes que não pertencem a nenhum commit de Git atual).

---

## 6. Próximos Passos de Desenvolvimento (Roadmap)
1.  **Dashboard Web:** Interface simples em Streamlit para visualizar as miniaturas (thumbnails) dos datasets registrados.
2.  **Integridade Automatizada:** Script semanal para verificar se todos os hashes no Git possuem correspondentes físicos no storage SSH.
3.  **Pre-fetch para Treino:** Função para baixar múltiplos datasets simultaneamente preparando o ambiente para treinos de longa duração (YOLOv11).

---

### Conclusão
Este projeto transforma a "bagunça de arquivos" em um **Sistema de Gestão de Ativos de Dados** escalável, seguro e auditável, essencial para o sucesso do mestrado e para a governança de dados na Nova Rota do Oeste.
