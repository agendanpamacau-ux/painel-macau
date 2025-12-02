import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from google.oauth2 import service_account
from googleapiclient.discovery import build
import base64

# ============================================================
# VERSÃO DO SCRIPT
# ============================================================
SCRIPT_VERSION = "v1.7.0 (Tabela de Escalas Adicionada)"

# Configuração do Plotly
pio.templates.default = "plotly"

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Navio-Patrulha Macau",
    layout="wide",
    page_icon="logo_npamacau.png"
)

# FUNÇÃO PARA CARREGAR IMAGEM EM BASE64
def get_img_as_base64(file):
    try:
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

logo_b64 = get_img_as_base64("logo_npamacau.png")

# --- CSS global / TEMA AMEZIA ---
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@300;400;600;700&family=Poppins:wght@400;500;600;700&display=swap');

    :root {{
        /* Amezia Colors */
        --amezia-blue: #4099ff;
        --amezia-pink: #ff5370;
        --amezia-green: #2ed8b6;
        --amezia-orange: #ffb64d;
        --amezia-dark-bg: #1a2035;
        --amezia-dark-card: #202940;
        --amezia-light-bg: #f4f7f6;
        --amezia-light-card: #ffffff;
        --text-dark: #aab8c5;
        --text-light: #3e4b5b;
    }}

    * {{
        font-family: 'Nunito Sans', sans-serif;
    }}

    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600 !important;
    }}

    /* HEADER STYLE */
    header[data-testid="stHeader"] {{
        background-image: linear-gradient(to right, #4099ff, #73b4ff);
        color: white !important;
        height: 3.5rem !important;
    }}
    
    /* LOGO & TITLE INJECTION */
    header[data-testid="stHeader"]::before {{
        content: "";
        background-image: url("data:image/png;base64,{logo_b64}");
        background-size: contain;
        background-repeat: no-repeat;
        position: absolute;
        left: 60px;
        top: 50%;
        transform: translateY(-50%);
        width: 40px;
        height: 40px;
        z-index: 999;
        pointer-events: none;
    }}

    header[data-testid="stHeader"]::after {{
        content: "Navio-Patrulha Macau";
        position: absolute;
        left: 110px;
        top: 50%;
        transform: translateY(-50%);
        color: white;
        font-size: 1.2rem;
        font-weight: 700;
        font-family: 'Poppins', sans-serif;
        z-index: 999;
        pointer-events: none;
    }}
    
    @media (max-width: 600px) {{
        header[data-testid="stHeader"]::after {{
            content: "NPa Macau";
            font-size: 1rem;
            left: 100px;
        }}
    }}

    header[data-testid="stHeader"] button {{
        color: white !important;
    }}
    
    .block-container {{
        padding-top: 4rem !important;
    }}

    /* 
       Dark Mode Fix: Removed forced background on .stApp to allow Streamlit theme to take over.
    */

    /* Cards */
    div[data-testid="metric-container"] {{
        border-radius: 5px;
        padding: 1.5rem;
        transition: all 0.3s ease-in-out;
        position: relative;
        overflow: hidden;
    }}

    @media (prefers-color-scheme: dark) {{
        div[data-testid="metric-container"] {{
            background: var(--amezia-dark-card);
            box-shadow: 0 4px 24px 0 rgb(34 41 47 / 10%);
            color: var(--text-dark);
        }}
        /* Sidebar text fix */
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] p, 
        section[data-testid="stSidebar"] span {{
            color: #aab8c5 !important;
        }}
    }}

    @media (prefers-color-scheme: light) {{
        div[data-testid="metric-container"] {{
            background: var(--amezia-light-card);
            box-shadow: 0 1px 20px 0 rgba(69,90,100,0.08);
            color: var(--text-light);
        }}
    }}

    div[data-testid="metric-container"]:hover {{
        transform: translateY(-5px);
        box-shadow: 0 10px 30px -5px rgba(64, 153, 255, 0.3);
    }}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: #202940; 
    }}
    
    section[data-testid="stSidebar"] * {{
        color: #aab8c5 !important;
    }}
    
    section[data-testid="stSidebar"] h4 {{
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        color: #fff !important;
        margin-top: 1rem;
    }}

    /* NAV LATERAL */
    section[data-testid="stSidebar"] div[role="radiogroup"] {{
        display: flex;
        flex-direction: column;
        gap: 5px;
        margin-top: 10px;
    }}

    section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {{
        display: none !important;
    }}

    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        padding: 10px 15px;
        border-radius: 0px;
        cursor: pointer;
        font-weight: 500;
        transition: all 0.2s ease;
        border-left: 3px solid transparent;
        margin-left: 0;
        background: transparent !important;
    }}

    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: transparent !important;
        border-left: 3px solid var(--amezia-blue);
        padding-left: 18px;
    }}
    
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover span,
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover p {{
        color: var(--amezia-blue) !important;
    }}

    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {{
        background: transparent !important;
        border-left: 3px solid var(--amezia-blue);
        box-shadow: none;
    }}
    
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] span,
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] p {{
        color: var(--amezia-blue) !important;
        font-weight: 700;
    }}

    /* Dataframes */
    .stDataFrame {{
        border-radius: 5px;
    }}
    
    /* Agenda Card */
    .agenda-card {{
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 4px solid var(--amezia-blue);
        transition: transform 0.2s;
    }}

    @media (prefers-color-scheme: dark) {{
        .agenda-card {{
            background-color: var(--amezia-dark-card);
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }}
        .agenda-date {{
            background-color: rgba(0,0,0,0.2);
            color: #fff;
        }}
    }}

    @media (prefers-color-scheme: light) {{
        .agenda-card {{
            background-color: #fff;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }}
        .agenda-date {{
            background-color: #f4f7f6;
            color: #333;
        }}
    }}
    
    .agenda-date {{
        padding: 5px 10px;
        border-radius: 4px;
        font-weight: bold;
        font-family: monospace;
    }}

    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# 2. HELPERS E CONSTANTES
# ============================================================

HEADER_ROW = 2  # linha 3 na planilha

AGENDAS_OFICIAIS = {
    "📅 Agenda Permanente": "agenda.npamacau@gmail.com",
    "⚓ Agenda Eventual": "32e9bbd3bca994bdab0b3cd648f2cb4bc13b0cf312a6a2c5a763527a5c610917@group.calendar.google.com",
    "🎂 Aniversários OM": "9f856c62f2420cd3ce5173197855b6726dd0a73d159ba801afd4eddfcac651db@group.calendar.google.com",
    "🎉 Aniversários Tripulação": "8641c7fc86973e09bbb682f8841908cc9240b25b1990f179137dfa7d2b23b2da@group.calendar.google.com",
    "📋 Comissão": "ff1a7d8acb9ea68eed3ec9b0e279f2a91fb962e4faa9f7a3e7187fade00eb0d6@group.calendar.google.com",
    "🛠️ NSD": "d7d9199712991f81e35116b9ec1ed492ac672b72b7103a3a89fb3f66ae635fb7@group.calendar.google.com"
}

SERVICOS_CONSIDERADOS = [
    "Of / Supervisor",
    "Contramestre 08-12",
    "Contramestre 04-08",
    "Contramestre 00-04",
    "Fiel de CAv"
]

def parse_bool(value) -> bool:
    if pd.isna(value):
        return False
    s = str(value).strip().lower()
    return s in ("true", "1", "sim", "yes", "y", "x")


# ============================================================
# 3. CARGA DE DADOS
# ============================================================

@st.cache_data(ttl=600, show_spinner="Carregando dados...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Afastamento 2026", header=HEADER_ROW, ttl="10m")
    if "Nome" in df.columns:
        df = df.dropna(subset=["Nome"])
    df = df.reset_index(drop=True)
    return df

@st.cache_data(ttl=300)
def load_calendar_events(calendar_id: str) -> pd.DataFrame:
    try:
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/calendar.readonly"]
        )
        service = build("calendar", "v3", credentials=creds)
        now = datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=now, maxResults=30, singleEvents=True, orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        data = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "Sem título")
            try:
                dt_obj = pd.to_datetime(start)
                fmt = "%d/%m %H:%M" if "T" in start else "%d/%m"
                data_fmt = dt_obj.strftime(fmt)
            except Exception:
                data_fmt = start
            data.append({"Data": data_fmt, "Evento": summary})
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro de conexão. Verifique o arquivo secrets.toml. Detalhe: {e}")
    st.stop()


# ============================================================
# 4. DESCOBRIR BLOCOS DE DATAS
# ============================================================

def descobrir_blocos_datas(df: pd.DataFrame):
    cols = list(df.columns)
    blocos = []
    for i, nome_col in enumerate(cols):
        n = str(nome_col)
        if not (n.startswith("Início") or n.startswith("Inicio")):
            continue
        j = None
        for idx2 in range(i + 1, len(cols)):
            n2 = str(cols[idx2])
            if n2.startswith("Fim") or n2.startswith("FIm"):
                j = idx2
                break
        if j is None:
            continue
        k = None
        tipo_base = "Férias"
        max_busca = min(j + 4, len(cols))
        for idx3 in range(j + 1, max_busca):
            n3 = str(cols[idx3])
            if "Motivo" in n3:
                k = idx3
                tipo_base = "Outros"
                break
            if "Curso" in n3:
                k = idx3
                tipo_base = "Curso"
                break
        col_ini = cols[i]
        col_fim = cols[j]
        col_mot = cols[k] if k is not None else None
        blocos.append((col_ini, col_fim, col_mot, tipo_base))
    return blocos

BLOCOS_DATAS = descobrir_blocos_datas(df_raw)

# ============================================================
# 5. PROCESSAMENTO DE STATUS
# ============================================================

def get_status_em_data(row, data_ref, blocos_cols):
    """
    Verifica o status de uma pessoa (row) em uma data específica.
    Retorna 'Presente' ou o motivo do afastamento.
    """
    for col_ini, col_fim, col_mot, tipo_base in blocos_cols:
        ini = row[col_ini]
        fim = row[col_fim]
        
        if pd.isna(ini) or pd.isna(fim):
            continue
            
        try:
            # Tenta converter para datetime
            dt_ini = pd.to_datetime(ini, dayfirst=True, errors='coerce')
            dt_fim = pd.to_datetime(fim, dayfirst=True, errors='coerce')
            
            if pd.isna(dt_ini) or pd.isna(dt_fim):
                continue
                
            if dt_ini <= data_ref <= dt_fim:
                motivo = tipo_base
                if col_mot and col_mot in row.index and not pd.isna(row[col_mot]):
                    motivo = str(row[col_mot])
                return motivo
        except:
            continue
            
    return "Presente"

# ============================================================
# 6. INTERFACE PRINCIPAL
# ============================================================

def main():
    # --- SIDEBAR ---
    with st.sidebar:
        st.image("logo_npamacau.png", width=100)
        st.title("Navegação")
        
        options = ["Presentes", "Ausentes", "Linha do Tempo", "Estatísticas", "Férias", "Cursos", "Tabela de Serviço"]
        
        # Estilo customizado para radio buttons já aplicado no CSS global
        pagina = st.radio("Ir para:", options, label_visibility="collapsed")
        
        st.markdown("---")
        
        # Filtros Globais (apenas se necessário, mas o usuário pediu para mover para baixo das tabelas)
        # Vamos manter vazio aqui por enquanto, conforme solicitado.

    # --- PÁGINAS ---
    
    # -------------------------------------------------------
    # ABA: PRESENTES
    # -------------------------------------------------------
    if pagina == "Presentes":
        st.subheader("Visão Geral - Presentes")
        
        col_date, _ = st.columns([1, 3])
        data_selecionada = col_date.date_input("Data de Referência", value=datetime.now())
        data_ref = pd.to_datetime(data_selecionada)
        
        # Processar dados para a data selecionada
        lista_presentes = []
        lista_ausentes = []
        
        for _, row in df_raw.iterrows():
            status = get_status_em_data(row, data_ref, BLOCOS_DATAS)
            info = row.to_dict()
            info["Status"] = status
            if status == "Presente":
                lista_presentes.append(info)
            else:
                lista_ausentes.append(info)
                
        df_presentes = pd.DataFrame(lista_presentes)
        
        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Efetivo", len(df_raw))
        c2.metric("Presentes", len(df_presentes))
        c3.metric("Ausentes", len(lista_ausentes))
        
        # Container para a tabela (aparece antes dos filtros visualmente)
        table_container = st.container()
        
        # Filtros (Abaixo da tabela conforme pedido)
        st.markdown("---")
        st.markdown("#### Filtros")
        f_col1, f_col2 = st.columns(2)
        
        # Obter valores dos filtros
        filtro_nome = f_col1.text_input("Filtrar por Nome")
        opcoes_posto = sorted(df_raw["Posto/Grad"].unique()) if "Posto/Grad" in df_raw.columns else []
        filtro_posto = f_col2.multiselect("Filtrar por Posto/Grad", opcoes_posto)
        
        # Aplicar filtros
        if not df_presentes.empty:
            df_filtered = df_presentes.copy()
            
            if filtro_nome:
                df_filtered = df_filtered[df_filtered["Nome"].astype(str).str.contains(filtro_nome, case=False, na=False)]
            
            if filtro_posto:
                df_filtered = df_filtered[df_filtered["Posto/Grad"].isin(filtro_posto)]
            
            # Renderizar tabela no container (topo)
            with table_container:
                if not df_filtered.empty:
                    cols_show = ["Posto/Grad", "Nome", "GVI/GP", "EqMan"]
                    cols_show = [c for c in cols_show if c in df_filtered.columns]
                    st.dataframe(df_filtered[cols_show], use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum resultado para os filtros selecionados.")
        else:
            with table_container:
                st.info("Ninguém presente nesta data.")
        
    # -------------------------------------------------------
    # ABA: AUSENTES
    # -------------------------------------------------------
    elif pagina == "Ausentes":
        st.subheader("Pessoal Ausente")
        
        # Visão Diária vs Mensal
        tipo_visao = st.radio("Tipo de Visão", ["Diária", "Mensal"], horizontal=True)
        
        if tipo_visao == "Diária":
            col_date, _ = st.columns([1, 3])
            data_selecionada = col_date.date_input("Data de Referência", value=datetime.now())
            data_ref = pd.to_datetime(data_selecionada)
            
            lista_ausentes = []
            for _, row in df_raw.iterrows():
                status = get_status_em_data(row, data_ref, BLOCOS_DATAS)
                if status != "Presente":
                    info = row.to_dict()
                    info["Motivo"] = status
                    lista_ausentes.append(info)
            
            df_ausentes = pd.DataFrame(lista_ausentes)
            
            if not df_ausentes.empty:
                cols_show = ["Posto/Grad", "Nome", "Motivo"]
                cols_show = [c for c in cols_show if c in df_ausentes.columns]
                st.dataframe(df_ausentes[cols_show], use_container_width=True, hide_index=True)
            else:
                st.success("Todos presentes!")
                
        else: # Mensal
            col_mes, col_ano = st.columns(2)
            meses_dict = {
                "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
                "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
            }
            mes_sel_nome = col_mes.selectbox("Selecione o Mês", list(meses_dict.keys()), index=datetime.now().month - 1)
            ano_sel = col_ano.number_input("Selecione o Ano", min_value=2024, max_value=2030, value=datetime.now().year)
            
            mes_sel = meses_dict[mes_sel_nome]
            
            # Container para a tabela
            table_container = st.container()
            
            # Filtros para Ausentes (Mensal)
            st.markdown("---")
            st.markdown("#### Filtros")
            f_col1, f_col2 = st.columns(2)
            filtro_nome_aus = f_col1.text_input("Filtrar por Nome", key="filt_aus_nome")
            opcoes_posto_aus = sorted(df_raw["Posto/Grad"].unique()) if "Posto/Grad" in df_raw.columns else []
            filtro_posto_aus = f_col2.multiselect("Filtrar por Posto/Grad", opcoes_posto_aus, key="filt_aus_posto")

            # Gerar tabela de ausências do mês
            days_in_month = pd.Period(f"{ano_sel}-{mes_sel}-01").days_in_month
            dates = [datetime(ano_sel, mes_sel, d) for d in range(1, days_in_month+1)]
            
            data_matrix = []
            for d in dates:
                for _, row in df_raw.iterrows():
                    # Aplicar filtros ANTES de processar (otimização) ou DEPOIS
                    # Vamos filtrar depois para manter a lógica de "status no dia"
                    status = get_status_em_data(row, d, BLOCOS_DATAS)
                    if status != "Presente":
                        data_matrix.append({
                            "Data": d.strftime("%d/%m/%Y"),
                            "Nome": row.get("Nome", ""),
                            "Posto/Grad": row.get("Posto/Grad", ""),
                            "Motivo": status
                        })
            
            df_ausentes_mes = pd.DataFrame(data_matrix)
            
            # Aplicar filtros no DataFrame resultante
            if not df_ausentes_mes.empty:
                if filtro_nome_aus:
                    df_ausentes_mes = df_ausentes_mes[df_ausentes_mes["Nome"].astype(str).str.contains(filtro_nome_aus, case=False, na=False)]
                if filtro_posto_aus:
                    df_ausentes_mes = df_ausentes_mes[df_ausentes_mes["Posto/Grad"].isin(filtro_posto_aus)]

            with table_container:
                if not df_ausentes_mes.empty:
                    st.dataframe(df_ausentes_mes, use_container_width=True, hide_index=True)
                else:
                    if not data_matrix: # Se não tinha nada antes do filtro
                        st.info("Nenhuma ausência registrada neste mês.")
                    else:
                        st.info("Nenhum resultado para os filtros selecionados.")

    # -------------------------------------------------------
    # ABA: LINHA DO TEMPO
    # -------------------------------------------------------
    elif pagina == "Linha do Tempo":
        st.subheader("Linha do Tempo de Afastamentos")
        
        # Preparar dados para Gantt
        gantt_data = []
        for _, row in df_raw.iterrows():
            nome = row.get("Nome", "Sem Nome")
            posto = row.get("Posto/Grad", "")
            full_name = f"{posto} {nome}" if posto else nome
            
            for col_ini, col_fim, col_mot, tipo_base in BLOCOS_DATAS:
                ini = row[col_ini]
                fim = row[col_fim]
                if pd.isna(ini) or pd.isna(fim):
                    continue
                try:
                    dt_ini = pd.to_datetime(ini, dayfirst=True)
                    dt_fim = pd.to_datetime(fim, dayfirst=True)
                    
                    motivo = tipo_base
                    if col_mot and col_mot in row.index and not pd.isna(row[col_mot]):
                        motivo = str(row[col_mot])
                        
                    gantt_data.append({
                        "Task": full_name,
                        "Start": dt_ini,
                        "Finish": dt_fim,
                        "Resource": motivo
                    })
                except:
                    continue
                    
        if gantt_data:
            df_gantt = pd.DataFrame(gantt_data)
            # Ordenar para manter ordem original (reversa para aparecer de cima para baixo)
            df_gantt = df_gantt.iloc[::-1] 
            
            fig = px.timeline(df_gantt, x_start="Start", x_end="Finish", y="Task", color="Resource", title="Gantt Chart")
            fig.update_yaxes(autorange="reversed") # Ensure top-to-bottom
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")

    # -------------------------------------------------------
    # ABA: ESTATÍSTICAS
    # -------------------------------------------------------
    elif pagina == "Estatísticas":
        st.subheader("Estatísticas e Análises")
        # Exemplo simples
        if "Posto/Grad" in df_raw.columns:
            fig = px.pie(df_raw, names="Posto/Grad", title="Distribuição por Posto/Grad")
            st.plotly_chart(fig)
        else:
            st.info("Dados insuficientes para estatísticas.")

    # -------------------------------------------------------
    # ABA: FÉRIAS / CURSOS
    # -------------------------------------------------------
    elif pagina == "Férias":
        st.subheader("Programação de Férias")
        # Filtrar apenas blocos de férias
        # (Simplificado para exibir tabela bruta ou filtrada)
        st.dataframe(df_raw, use_container_width=True)
        
    elif pagina == "Cursos":
        st.subheader("Cursos Agendados")
        st.dataframe(df_raw, use_container_width=True)

    # -------------------------------------------------------
    # ABA: TABELA (NOVA)
    # -------------------------------------------------------
    # -------------------------------------------------------
    # ABA: TABELA DE SERVIÇO
    # -------------------------------------------------------
    elif pagina == "Tabela de Serviço":
        st.subheader("Tabela de Serviço - Análise de Escalas")

        # --- SEÇÃO 1: VISÃO DIÁRIA ---
        st.markdown("#### Escala Diária")
        col_d1, _ = st.columns([1, 3])
        data_ref_diaria = col_d1.date_input("Data de Referência", value=datetime.now(), key="data_ref_escala")
        dt_ref = pd.to_datetime(data_ref_diaria)

        # Identificar coluna de Escala/Serviço
        col_escala = None
        possiveis = ["Escala", "Serviço", "Função", "Setor", "Divisão"]
        for c in possiveis:
            if c in df_raw.columns:
                col_escala = c
                break
        
        target_col = col_escala if col_escala else "Posto/Grad"

        if not col_escala and "Posto/Grad" not in df_raw.columns:
            st.error("Não foi possível identificar a coluna de Escala/Serviço para cálculo.")
        else:
            # Calcular escala para o dia selecionado
            daily_data = []
            for servico in SERVICOS_CONSIDERADOS:
                # Filtrar pessoas desse serviço
                people_in_service = df_raw[df_raw[target_col].astype(str).str.contains(servico, case=False, regex=False)]
                if people_in_service.empty:
                     people_in_service = df_raw[df_raw[target_col].astype(str) == servico]

                total = len(people_in_service)
                
                # Contar ausentes no dia
                absent = 0
                for _, person in people_in_service.iterrows():
                    status = get_status_em_data(person, dt_ref, BLOCOS_DATAS)
                    if status != "Presente":
                        absent += 1
                
                available = max(0, total - absent)
                scale_val = max(0, available - 1)
                
                daily_data.append({
                    "Serviço": servico,
                    "Escala": f"{scale_val}x1"
                })
            
            df_daily = pd.DataFrame(daily_data)
            st.dataframe(df_daily, use_container_width=False, hide_index=True, width=400)

            st.markdown("---")

            # --- SEÇÃO 2: VISÃO MENSAL ---
            st.markdown("#### Escala Mensal")
            
            col1, col2 = st.columns(2)
            meses_dict = {
                "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
                "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
            }
            now = datetime.now()
            sel_mes_nome = col1.selectbox("Mês", list(meses_dict.keys()), index=now.month-1, key="mes_escala")
            sel_ano = col2.number_input("Ano", value=now.year, min_value=2020, max_value=2030, key="ano_escala")
            sel_mes = meses_dict[sel_mes_nome]
            
            # Gerar dias do mês
            days_in_month = pd.Period(f"{sel_ano}-{sel_mes}-01").days_in_month
            dates = [datetime(sel_ano, sel_mes, d) for d in range(1, days_in_month+1)]
            
            data_matrix = []
            
            for d in dates:
                row_data = {"Dia": d.strftime("%d/%m")} # Dias do mês na primeira coluna
                
                for servico in SERVICOS_CONSIDERADOS:
                    people_in_service = df_raw[df_raw[target_col].astype(str).str.contains(servico, case=False, regex=False)]
                    if people_in_service.empty:
                         people_in_service = df_raw[df_raw[target_col].astype(str) == servico]

                    total = len(people_in_service)
                    
                    absent = 0
                    for _, person in people_in_service.iterrows():
                        status = get_status_em_data(person, d, BLOCOS_DATAS)
                        if status != "Presente":
                            absent += 1
                    
                    available = max(0, total - absent)
                    scale_val = max(0, available - 1)
                    
                    row_data[servico] = f"{scale_val}x1"
                
                data_matrix.append(row_data)
            
            df_tabela = pd.DataFrame(data_matrix)
            st.dataframe(df_tabela, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
