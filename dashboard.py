import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.set_page_config(page_title="ROTA Data Registry", layout="wide")

st.title("🛣️ ROTA Data Registry - Gestão de Datasets")
st.markdown("Interface para visualização dos datasets e pipelines versionados com DVC.")

# Carregar metadados da pasta data
data_dir = Path("data")
datasets = []

if data_dir.exists():
    for meta_file in data_dir.glob("*.json"):
        try:
            with open(meta_file, "r") as f:
                data = json.load(f)
                
                # Para manter compatibilidade com versões antigas do rota.py
                dataset_id = data.get("dataset_id", data.get("dataset_name", meta_file.stem))
                
                datasets.append({
                    "ID": dataset_id,
                    "Data/Hora": data.get("timestamp", meta_file.stem.split('_')[-2:] if '_' in meta_file.stem else ["N/A"])[0],
                    "Projeto": data.get("projeto", "N/A"),
                    "Engenheiro": data.get("engenheiro", data.get("user", "N/A")),
                    "Origem": data.get("origem_fisica", data.get("original_path", "N/A")),
                    "Hardware": data.get("hardware_ingest", "N/A"),
                    "Storage": data.get("metodo_storage", "N/A"),
                })
        except Exception as e:
            st.error(f"Erro ao ler {meta_file.name}: {e}")

if datasets:
    df = pd.DataFrame(datasets)
    
    # Filtros
    st.sidebar.header("🔍 Filtros")
    filtro_projeto = st.sidebar.multiselect("Filtrar por Projeto", df["Projeto"].unique())
    filtro_eng = st.sidebar.multiselect("Filtrar por Engenheiro", df["Engenheiro"].unique())
    
    if filtro_projeto:
        df = df[df["Projeto"].isin(filtro_projeto)]
    if filtro_eng:
        df = df[df["Engenheiro"].isin(filtro_eng)]
        
    st.markdown(f"**Total de Datasets Encontrados:** {len(df)}")
    
    # Exibir Tabela
    st.dataframe(df, use_container_width=True)
else:
    st.info("Nenhum dataset registrado. Use o CLI `rota.py ingest` para adicionar dados.")

st.markdown("---")
st.caption("Mestrado Unipampa / Nova Rota do Oeste")
