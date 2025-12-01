import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Controle de ausências - NPaMacau",
    layout="wide",
    page_icon="⚓"
)
st.title("⚓ Controle de ausências - NPaMacau")

# --- CSS Moderno ---
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at top left, #0f172a 0, #020617 45%, #000 100%);
        color: #e5e7eb;
    }
    h1, h2, h3 {
        color: #e5e7eb !important;
    }
    div[data-testid="metric-container"] {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid #334155;
        border-radius: 10px;
        color: white;
    }
    /* Forçar texto branco nas métricas */
    div[data-testid="metric-container"] label {
        color: #94a3b8 !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# 2. CONSTANTES
# ============================================================

# Se os dados começam na linha 4 do Excel, o cabeçalho está na linha 3.
# Pandas usa base-0, então linha 3 = índice 2.
HEADER_ROW = 2 

COL = {
    "NUMERO": 0,    # A
    "POSTO": 1,     # B
    "NOME": 2,      # C
    "SERVICO": 3,   # D
    "EQMAN": 4,     # E
    "GVI": 5,       # F
    "INSP": 6,      # G
}

# Férias (I-J, L-M, O-P) -> Índices 8-9, 11-12, 14-15
FERIAS_PARES = [(8, 9), (11, 12), (14, 15)]

# Outras ausências (Y-Z, AD-AE, etc.)
AUSENCIAS_TRIOS = [
    (24, 25, 27), # Período 4
    (29, 30, 32), # Período 5
    (34, 35, 37), # Período 6
    (39, 40, 42), # Período 7
    (44, 45, 47), # Período 8
]

# ============================================================
# 3. FUNÇÕES AUXILIARES (CORRIGIDAS)
# ============================================================

def parse_bool(value) -> bool:
    if pd.isna(value): return False
    return str(value).strip().lower() in ("true", "1", "sim", "yes", "y", "x")

def parse_sheet_date(value):
    """
    CORREÇÃO CRÍTICA: Lida com anos de 2 dígitos e remove filtros agressivos.
    """
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT

    try:
        # Tenta converter string padrão
        ts = pd.to_datetime(value, dayfirst=True, errors='coerce')
        
        # Se falhar ou resultar em NaT
        if pd.isna(ts):
            return pd.NaT
        
        # CORREÇÃO DO ANO 1925 -> 2025
        # Se o Sheets mandar "25" e o Pandas ler "1925", nós corrigimos.
        if ts.year < 2000:
            ts = ts.replace(year=ts.year + 100)
            
        return ts
    except:
        return pd.NaT

# ============================================================
# 4. CARGA DE DADOS
# ============================================================

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lê a planilha. ttl=0 evita cache antigo enquanto você testa.
    df = conn.read(worksheet="Afastamento 2026", header=HEADER_ROW, ttl=0)
    
    # Limpeza básica de linhas vazias baseada no Nome (Coluna C / Index 2)
    # Garante que acessamos a coluna pelo índice numérico, independente do nome do cabeçalho
    if len(df.columns) > 2:
        df = df.dropna(subset=[df.columns[2]])
    
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro ao conectar. Detalhe: {e}")
    st.stop()

# ============================================================
# 5. PROCESSAMENTO (Transformar colunas em Eventos)
# ============================================================

def construir_eventos(df):
    lista = []
    
    # Itera sobre cada militar
    for idx, row in df.iterrows():
        # Captura dados básicos (usando iloc para garantir posição fixa)
        # Se a linha for menor que o esperado, ignora
        if len(row) < 7: continue
        
        posto = row.iloc[COL["POSTO"]]
        nome = row.iloc[COL["NOME"]]
        eqman = str(row.iloc[COL["EQMAN"]]) if pd.notnull(row.iloc[COL["EQMAN"]]) and str(row.iloc[COL["EQMAN"]]) != "-" else "Não"
        
        base_info = {
            "Posto": posto, 
            "Nome": nome, 
            "EqMan": eqman,
            "GVI": parse_bool(row.iloc[COL["GVI"]]),
            "IN": parse_bool(row.iloc[COL["INSP"]])
        }
        
        # --- Processar Férias ---
        for i_start, i_end in FERIAS_PARES:
            if len(row) > i_end:
                ini = parse_sheet_date(row.iloc[i_start])
                fim = parse_sheet_date(row.iloc[i_end])
                
                if pd.notnull(ini) and pd.notnull(fim):
                    lista.append({**base_info, "Inicio": ini, "Fim": fim, "Motivo": "FÉRIAS", "Tipo": "Férias"})

        # --- Processar Outras Ausências ---
        for i_start, i_end, i_motivo in AUSENCIAS_TRIOS:
            if len(row) > i_motivo:
                ini = parse_sheet_date(row.iloc[i_start])
                fim = parse_sheet_date(row.iloc[i_end])
                
                if pd.notnull(ini) and pd.notnull(fim):
                    motivo_raw = str(row.iloc[i_motivo])
                    motivo_real = motivo_raw if len(motivo_raw) > 2 and "nan" not in motivo_raw.lower() else "OUTROS"
                    lista.append({**base_info, "Inicio": ini, "Fim": fim, "Motivo": motivo_real.upper(), "Tipo": "Outros"})

    return pd.DataFrame(lista)

df_eventos = construir_eventos(df_raw)

# ============================================================
# 6. INTERFACE E DASHBOARD
# ============================================================

# Barra Lateral
st.sidebar.header("🕹️ Filtros")
data_selecionada = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_selecionada)

# Filtros
if not df_raw.empty:
    todos_postos = df_raw.iloc[:, COL["POSTO"]].unique()
    filtro_posto = st.sidebar.multiselect("Filtrar Posto", todos_postos, default=todos_postos)
else:
    filtro_posto = []

filtro_eqman = st.sidebar.checkbox("Apenas EqMan")

# Aplicar filtros no Total de Efetivo (df_raw)
df_efetivo_filtrado = df_raw[df_raw.iloc[:, COL["POSTO"]].isin(filtro_posto)]
if filtro_eqman:
    df_efetivo_filtrado = df_efetivo_filtrado[
        (df_efetivo_filtrado.iloc[:, COL["EQMAN"]].notnull()) & 
        (df_efetivo_filtrado.iloc[:, COL["EQMAN"]].astype(str) != "-")
    ]

# Aplicar filtros nos Eventos (df_eventos)
if not df_eventos.empty:
    # 1. Filtra quem está fora HOJE
    ausentes_hoje = df_eventos[
        (df_eventos["Inicio"] <= hoje) & 
        (df_eventos["Fim"] >= hoje) &
        (df_eventos["Posto"].isin(filtro_posto))
    ]
    
    # 2. Filtra eventos gerais para o gráfico
    eventos_filtrados = df_eventos[df_eventos["Posto"].isin(filtro_posto)]

    if filtro_eqman:
        ausentes_hoje = ausentes_hoje[ausentes_hoje["EqMan"] != "Não"]
        eventos_filtrados = eventos_filtrados[eventos_filtrados["EqMan"] != "Não"]

else:
    ausentes_hoje = pd.DataFrame()
    eventos_filtrados = pd.DataFrame()

# Cálculos KPIs
total_efetivo = len(df_efetivo_filtrado)
total_ausentes = ausentes_hoje["Nome"].nunique()
total_presentes = total_efetivo - total_ausentes
percentual = (total_presentes / total_efetivo * 100) if total_efetivo > 0 else 0

# Exibição KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Efetivo Total", total_efetivo)
c2.metric("A Bordo", total_presentes)
c3.metric("Ausentes Hoje", total_ausentes, delta_color="inverse")
c4.metric("Prontidão", f"{percentual:.1f}%")

st.markdown("---")

# Abas
tab1, tab2, tab_debug = st.tabs(["📋 Situação Detalhada", "📅 Linha do Tempo", "🔧 Diagnóstico (Debug)"])

with tab1:
    st.subheader(f"Status em {hoje.strftime('%d/%m/%Y')}")
    if not ausentes_hoje.empty:
        # Prepara tabela bonita
        tabela = ausentes_hoje[["Posto", "Nome", "Motivo", "Fim"]].copy()
        tabela["Retorno Previsto"] = tabela["Fim"].dt.strftime("%d/%m/%Y")
        tabela = tabela.drop(columns=["Fim"])
        st.dataframe(tabela, use_container_width=True, hide_index=True)
        
        # Alerta EqMan
        eqman_fora = ausentes_hoje[ausentes_hoje["EqMan"] != "Não"]
        if not eqman_fora.empty:
            st.error(f"⚠️ Atenção Manobra! {len(eqman_fora)} membros da EqMan ausentes.")
    else:
        st.success("Nenhum militar ausente na data selecionada com os filtros atuais.")

with tab2:
    st.subheader("Cronograma Anual")
    if not eventos_filtrados.empty:
        fig = px.timeline(
            eventos_filtrados, 
            x_start="Inicio", 
            x_end="Fim", 
            y="Nome", 
            color="Motivo",
            hover_data=["Posto", "EqMan"],
            title="Visualização de Afastamentos"
        )
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=hoje, line_dash="dash", line_color="red", annotation_text="Hoje")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados de eventos para exibir no gráfico.")

with tab_debug:
    st.warning("Use esta aba para verificar se o robô está lendo as colunas certas.")
    st.write("Abaixo estão as primeiras 5 linhas EXATAMENTE como o sistema leu do Google Sheets:")
    st.dataframe(df_raw.head())
    
    st.write("---")
    st.write("Eventos detectados (Datas convertidas):")
    if not df_eventos.empty:
        st.dataframe(df_eventos)
    else:
        st.write("Nenhum evento (férias ou licença) foi detectado. Verifique o formato das datas na planilha.")
