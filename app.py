import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Painel NPaMacau", layout="wide", page_icon="⚓")
st.title("⚓ Gestão de Efetivo - NPaMacau")

# --- CARREGAMENTO DE DADOS ---
# header=2 significa que a linha 3 da planilha (índice 2) contém os títulos das colunas
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(worksheet="Afastamento 2026", header=2, ttl="10m")
    
    # Procura a coluna que tem 'Nome' ou 'NOME' para limpar linhas vazias
    col_nome = [c for c in df_raw.columns if "Nome" in str(c) or "NOME" in str(c)]
    if col_nome:
        df_raw = df_raw.dropna(subset=[col_nome[0]])
    return df_raw

try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao conectar na planilha: {e}")
    st.stop()

# --- SEPARAÇÃO DOS DADOS ---
# Fatiamento baseado na estrutura informada:
# A-G (0-6): Dados Militares | I-W (8-22): Férias | Y-AV (24-47): Outros
df_militar = df.iloc[:, 0:7].copy()
df_ferias  = df.iloc[:, 8:23].copy()
df_outros  = df.iloc[:, 24:48].copy()

# --- ANÁLISE DE STATUS ---
hoje = pd.to_datetime(datetime.today())

def verificar_status(row_idx):
    # 1. Verificar Férias (Bloco I-W)
    ferias_row = df_ferias.iloc[row_idx]
    for i in range(0, len(ferias_row.index) - 1):
        try:
            inicio = pd.to_datetime(ferias_row.iloc[i], dayfirst=True, errors='coerce')
            fim = pd.to_datetime(ferias_row.iloc[i+1], dayfirst=True, errors='coerce')
            if pd.notnull(inicio) and pd.notnull(fim):
                if inicio <= hoje <= fim:
                    return "FÉRIAS", fim
        except:
            continue

    # 2. Verificar Outros Afastamentos (Bloco Y-AV)
    outros_row = df_outros.iloc[row_idx]
    col_count = len(outros_row.index)
    for i in range(0, col_count - 2): # Varre procurando datas
        try:
            inicio = pd.to_datetime(outros_row.iloc[i], dayfirst=True, errors='coerce')
            fim = pd.to_datetime(outros_row.iloc[i+1], dayfirst=True, errors='coerce')
            
            if pd.notnull(inicio) and pd.notnull(fim):
                if inicio <= hoje <= fim:
                    # Tenta pegar o motivo (geralmente 2 colunas à frente do inicio)
                    motivo = "AFASTADO"
                    if i + 2 < col_count:
                        texto_motivo = str(outros_row.iloc[i+2])
                        if len(texto_motivo) > 2 and texto_motivo.lower() != "nan":
                            motivo = texto_motivo
                    return motivo.upper(), fim
        except:
            continue

    return "A BORDO", None

# Aplica a verificação
status_results = [verificar_status(i) for i in range(len(df_militar))]
df_militar['Status_Atual'] = [x[0] for x in status_results]
df_militar['Data_Retorno'] = [x[1] for x in status_results]

# --- DASHBOARD ---
# Filtros laterais
postos = df_militar.iloc[:, 1].unique() # Assume coluna B como Posto
filtro_posto = st.sidebar.multiselect("Filtrar Posto", postos, default=postos)

# Filtragem
col_posto_nome = df_militar.columns[1] # Nome da coluna de Posto
df_filtered = df_militar[df_militar[col_posto_nome].isin(filtro_posto)]

# KPIs
total = len(df_filtered)
ausentes = df_filtered[df_filtered['Status_Atual'] != "A BORDO"]
presentes = total - len(ausentes)

c1, c2, c3 = st.columns(3)
c1.metric("Efetivo Total", total)
c2.metric("A Bordo", presentes)
c3.metric("Ausentes", len(ausentes), delta_color="inverse")

st.divider()

# Tabela de Ausentes
if not ausentes.empty:
    st.subheader("🚨 Militares Ausentes Hoje")
    
    # Formata a data de retorno
    ausentes_view = ausentes.copy()
    ausentes_view['Data_Retorno'] = ausentes_view['Data_Retorno'].apply(
        lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else "-"
    )
    
    # Seleciona colunas principais (Posto, Nome, Status, Retorno)
    # Ajuste os índices 1 e 2 conforme os nomes reais das colunas Posto e Nome
    cols_to_show = [ausentes_view.columns[1], ausentes_view.columns[2], 'Status_Atual', 'Data_Retorno']
    st.dataframe(ausentes_view[cols_to_show], use_container_width=True)
else:
    st.success("Nenhum afastamento registrado para hoje no filtro selecionado.")

# Gráfico simples de distribuição
if not ausentes.empty:
    fig = px.pie(ausentes, names='Status_Atual', title='Motivos de Ausência')
    st.sidebar.plotly_chart(fig, use_container_width=True)
