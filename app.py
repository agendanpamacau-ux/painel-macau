import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from google.oauth2 import service_account
from googleapiclient.discovery import build
import base64
import os
from streamlit_echarts import st_echarts

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA (OBRIGATÓRIO SER O PRIMEIRO)
# ============================================================
st.set_page_config(
    page_title="Navio-Patrulha Macau",
    layout="wide",
    page_icon="logo_npamacau.png"
)

# ============================================================
# 🔒 2. SISTEMA DE LOGIN (VERSÃO FINAL)
# ============================================================
def check_password():
    """Retorna True se o usuário logar com sucesso."""

    # Verifica se as senhas foram carregadas corretamente
    if "passwords" not in st.secrets:
        st.error("🚫 Erro de Configuração")
        st.warning("O arquivo de senhas (.streamlit/secrets.toml) não foi detectado ou está mal formatado.")
        st.stop()

    def password_entered():
        """Verifica se a senha digitada bate com a do arquivo secrets.toml"""
        if st.session_state["username"] in st.secrets["passwords"] and \
           st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]:
            st.session_state["password_correct"] = True
            # Limpa a senha da memória por segurança
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Se a senha ainda não foi verificada ou está incorreta
    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        # Layout centralizado para o login
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.header("🔒 Acesso Restrito - NPa Macau")
            st.write("Identifique-se para acessar o painel.")
            
            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", on_change=password_entered, key="password")
            
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("😕 Usuário ou senha incorretos")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.info("Caso não possua acesso, contate o Encarregado da Divisão.")
        
        return False
    
    return True

# O COMANDO DE PARADA:
if not check_password():
    st.stop()

# ============================================================
# 🔓 FIM DO BLOQUEIO - O CÓDIGO DO APP COMEÇA AQUI
# ============================================================

# ============================================================
# HELPER: ECHARTS DONUT (GENERICO)
# ============================================================
def make_echarts_donut(data_list, title):
    options = {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {
            "top": "5%", 
            "left": "center",
            "textStyle": {"color": "#9ca3af"}
        },
        "series": [
            {
                "name": title,
                "type": "pie",
                "radius": ["40%", "70%"],
                "avoidLabelOverlap": False,
                "itemStyle": {
                    "borderRadius": 10,
                    "borderColor": "#fff",
                    "borderWidth": 2,
                },
                "label": {"show": False, "position": "center"},
                "emphasis": {
                    "label": {
                        "show": True, 
                        "fontSize": "24",
                        "fontWeight": "bold",
                        "formatter": "{b}\n{d}%"
                    }
                },
                "labelLine": {"show": False},
                "data": data_list,
            }
        ],
    }
    return options

# ============================================================
# HELPER: ECHARTS LINE
# ============================================================
def make_echarts_line(x_data, y_data):
    options = {
        "xAxis": {
            "type": "category",
            "data": x_data,
        },
        "yAxis": {"type": "value"},
        "series": [{"data": y_data, "type": "line"}],
        "tooltip": {"trigger": "axis"}
    }
    return options

# ============================================================
# HELPER: ECHARTS BAR
# ============================================================
def make_echarts_bar(x_data, y_data):
    options = {
        "xAxis": {
            "type": "category",
            "data": x_data,
            "axisLabel": {"interval": 0, "rotate": 30}
        },
        "yAxis": {"type": "value"},
        "series": [{"data": y_data, "type": "bar"}],
        "tooltip": {"trigger": "axis"}
    }
    return options

# ============================================================
# VERSÃO DO SCRIPT
# ============================================================
SCRIPT_VERSION = "v2.2 (Login Seguro)"

# Configuração do Plotly
pio.templates.default = "plotly_dark"

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

    * {{ font-family: 'Nunito Sans', sans-serif; }}
    h1, h2, h3, h4, h5, h6 {{ font-family: 'Poppins', sans-serif !important; font-weight: 600 !important; }}

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
        left: 60px; top: 50%; transform: translateY(-50%);
        width: 40px; height: 40px;
        z-index: 999; pointer-events: none;
    }}

    header[data-testid="stHeader"]::after {{
        content: "Navio-Patrulha Macau";
        position: absolute;
        left: 110px; top: 50%; transform: translateY(-50%);
        color: white; font-size: 1.2rem; font-weight: 700;
        font-family: 'Poppins', sans-serif;
        z-index: 999; pointer-events: none;
    }}
     
    @media (max-width: 600px) {{
        header[data-testid="stHeader"]::after {{
            content: "NPa Macau"; font-size: 1rem; left: 100px;
        }}
    }}

    header[data-testid="stHeader"] button {{ color: white !important; }}
     
    .block-container {{ padding-top: 4rem !important; }}

    /* Cards */
    div[data-testid="metric-container"] {{
        border-radius: 5px; padding: 1.5rem;
        transition: all 0.3s ease-in-out; position: relative; overflow: hidden;
    }}

    @media (prefers-color-scheme: dark) {{
        div[data-testid="metric-container"] {{
            background: var(--amezia-dark-card);
            box-shadow: 0 4px 24px 0 rgb(34 41 47 / 10%);
            color: var(--text-dark);
        }}
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] p, 
        section[data-testid="stSidebar"] span {{ color: #aab8c5 !important; }}
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
    section[data-testid="stSidebar"] {{ background-color: #202940; }}
    section[data-testid="stSidebar"] * {{ color: #aab8c5 !important; }}
    section[data-testid="stSidebar"] h4 {{ font-size: 1.2rem !important; font-weight: 700 !important; color: #fff !important; margin-top: 1rem; }}

    /* NAV LATERAL */
    section[data-testid="stSidebar"] div[role="radiogroup"] {{ display: flex; flex-direction: column; gap: 5px; margin-top: 10px; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {{ display: none !important; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        padding: 10px 15px; border-radius: 0px; cursor: pointer; font-weight: 500;
        transition: all 0.2s ease; border-left: 3px solid transparent; margin-left: 0; background: transparent !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: transparent !important; border-left: 3px solid var(--amezia-blue); padding-left: 18px;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {{
        background: transparent !important; border-left: 3px solid var(--amezia-blue); box-shadow: none; padding-left: 18px;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover p {{ color: var(--amezia-blue) !important; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] p {{ color: var(--amezia-blue) !important; font-weight: 700 !important; }}
     
    /* Center Metrics */
    div[data-testid="stMetric"] {{ text-align: center !important; justify-content: center !important; align-items: center !important; display: flex; flex-direction: column; }}
    div[data-testid="stMetricLabel"] {{ justify-content: center !important; width: 100%; display: flex; }}
    div[data-testid="stMetricValue"] {{ justify-content: center !important; width: 100%; display: flex; }}

    /* Dataframes */
    .stDataFrame {{ border-radius: 5px; }}
     
    /* Agenda Card */
    .agenda-card {{
        padding: 15px; border-radius: 5px; margin-bottom: 15px;
        display: flex; justify-content: space-between; align-items: center;
        border-left: 4px solid var(--amezia-blue); transition: transform 0.2s;
    }}
    @media (prefers-color-scheme: dark) {{
        .agenda-card {{ background-color: #202940 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.2); color: #ffffff !important; }}
        .agenda-date {{ background-color: rgba(255,255,255,0.1) !important; color: #ffffff !important; }}
    }}
    @media (prefers-color-scheme: light) {{
        .agenda-card {{ background-color: #fff !important; box-shadow: 0 2px 10px rgba(0,0,0,0.05); color: #333 !important; }}
        .agenda-date {{ background-color: #f4f7f6 !important; color: #333 !important; }}
    }}
    .agenda-date {{ padding: 5px 10px; border-radius: 4px; font-weight: bold; font-family: monospace; }}
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# 3. HELPERS E CONSTANTES
# ============================================================

HEADER_ROW = 2  # linha 3 na planilha principal

AGENDAS_OFICIAIS = {
    "Agenda Permanente": "agenda.npamacau@gmail.com",
    "Agenda Eventual": "32e9bbd3bca994bdab0b3cd648f2cb4bc13b0cf312a6a2c5a763527a5c610917@group.calendar.google.com",
    "Aniversários OM": "9f856c62f2420cd3ce5173197855b6726dd0a73d159ba801afd4eddfcac651db@group.calendar.google.com",
    "Aniversários Tripulação": "8641c7fc86973e09bbb682f8841908cc9240b25b1990f179137dfa7d2b23b2da@group.calendar.google.com",
    "Comissão": "ff1a7d8acb9ea68eed3ec9b0e279f2a91fb962e4faa9f7a3e7187fade00eb0d6@group.calendar.google.com",
    "NSD": "d7d9199712991f81e35116b9ec1ed492ac672b72b7103a3a89fb3f66ae635fb7@group.calendar.google.com"
}

SERVICOS_CONSIDERADOS = [
    "Oficial / Supervisor",
    "Contramestre 08-12",
    "Contramestre 04-08",
    "Contramestre 00-04",
    "Fiel de CAv"
]

# NOVA URL para Dias de Mar
URL_DIAS_MAR = "https://docs.google.com/spreadsheets/d/1CEVh0EQsnINcuVP4-RbS3KgfAQNKXCwAszbqjDq8phU/edit?usp=sharing"
URL_CARDAPIO = "https://docs.google.com/spreadsheets/d/1i3veE6cj4-h9toh_DIjm8vcyz4kJ0DoKpJDrA2Xn77s/edit?usp=sharing"
URL_ANIVERSARIOS = "https://docs.google.com/spreadsheets/d/1mcQlXU_sRYwqmBCHkL3qX1GS6bivUqIGqGVVCvZLc0U/edit?usp=sharing"

def parse_bool(value) -> bool:
    """
    Função ROBUSTA para detectar True/1.
    Lida com int, float (1.0), string '1', '1.0', 'true', 'sim'.
    """
    if pd.isna(value) or value == "":
        return False
     
    # 1. Se já for booleano
    if isinstance(value, bool):
        return value
     
    # 2. Se for número (int ou float)
    if isinstance(value, (int, float)):
        return value > 0
     
    # 3. Tratamento de String (caso venha '1', '1.0', 'True')
    s = str(value).strip().lower()
     
    # Remove .0 caso venha como texto "1.0"
    if s.endswith(".0"):
        s = s[:-2]
         
    return s in ("true", "1", "sim", "yes", "y", "x", "s", "ok", "v", "checked")

def parse_aniversario_date(val):
    """
    Parser para datas de aniversário no formato '6nov.' ou '15jan.'
    Retorna uma data com o ano corrente.
    """
    if pd.isna(val) or str(val).strip() == "":
        return pd.NaT
         
    s = str(val).strip().lower().replace(".", "")
     
    # Mapa de meses
    meses = {
        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12
    }
     
    try:
        # Tenta extrair dia e mês (ex: 6nov -> dia 6, mes nov)
        # Regex simples ou split manual
        import re
        match = re.match(r"(\d+)([a-zç]+)", s)
        if match:
            dia = int(match.group(1))
            mes_str = match.group(2)
             
            if mes_str in meses:
                mes = meses[mes_str]
                ano_atual = (datetime.utcnow() - timedelta(hours=3)).year
                return datetime(ano_atual, mes, dia)
    except:
        pass
         
    return pd.NaT

def parse_sheet_date(val):
    """
    Tenta converter valor para data, assumindo DD/MM ou DD/MM/YY ou DD/MM/YYYY.
    Se não tiver ano (DD/MM), assume o ano atual (2025).
    """
    if pd.isna(val) or str(val).strip() == "":
        return pd.NaT
     
    val_str = str(val).strip()
     
    # Tenta converter direto (formato padrão do pandas/sheets)
    try:
        dt = pd.to_datetime(val_str, dayfirst=True, errors='coerce')
        if pd.notna(dt):
            # Correção ano 2 dígitos (ex: 25 -> 2025)
            if dt.year < 2000:
                dt = dt.replace(year=dt.year + 100)
            return dt
    except:
        pass

    # Tenta formato DD/MM explicitamente
    try:
        # Adiciona o ano atual se for apenas DD/MM
        # Assume ano 2025 para este painel específico (Afastamento 2026 tem dados de 25 e 26)
        # Melhor estratégia: Tentar parser com ano atual
        dt = datetime.strptime(val_str, "%d/%m")
        # Substitui pelo ano corrente ou um ano padrão (2025 neste contexto)
        dt = dt.replace(year=(datetime.utcnow() - timedelta(hours=3)).year) 
        return pd.to_datetime(dt)
    except:
        pass
         
    return pd.NaT

# ============================================================
# 4. CARGA DE DADOS
# ============================================================

@st.cache_data(ttl=600, show_spinner="Carregando dados de efetivo...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Afastamento 2026", header=HEADER_ROW, ttl="10m")
    if "Nome" in df.columns:
        df = df.dropna(subset=["Nome"])
    df = df.reset_index(drop=True)
    return df

@st.cache_data(ttl=3600, show_spinner="Carregando aniversariantes...")
def load_aniversarios():
    """Carrega dados de aniversários"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL_ANIVERSARIOS, ttl="1h")
    return df

def parse_mar_date(val, ano):
    """
    Parser específico para Dias de Mar.
    Se a data for DD/MM, acopla o ANO da linha.
    """
    if pd.isna(val) or str(val).strip() == "":
        return pd.NaT
     
    s_val = str(val).strip()
     
    # 1. Tenta parse direto (ex: 15/02/2024)
    try:
        dt = pd.to_datetime(s_val, dayfirst=True)
        # Se o ano for 1900 (comum quando se passa só dia/mês), tenta corrigir com o ANO da linha
        if dt.year == 1900 and pd.notna(ano) and int(ano) > 1900:
            return dt.replace(year=int(ano))
        return dt
    except:
        pass
         
    # 2. Tenta concatenar com o ANO (ex: 15/02 + 2024 -> 15/02/2024)
    if pd.notna(ano) and int(ano) > 1900:
        try:
            full_date = f"{s_val}/{int(ano)}"
            return pd.to_datetime(full_date, dayfirst=True)
        except:
            pass
             
    return pd.NaT

@st.cache_data(ttl=600, show_spinner="Carregando dados de Mar...")
def load_dias_mar():
    """Carrega dados da planilha separada de Dias de Mar"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Header na linha 8 (index 7)
    df = conn.read(spreadsheet=URL_DIAS_MAR, header=7, ttl="10m")
     
    # Limpeza: Remove linhas onde "TERMO DE VIAGEM" está vazio
    if "TERMO DE VIAGEM" in df.columns:
        df = df.dropna(subset=["TERMO DE VIAGEM"])
     
    # Seleciona apenas colunas relevantes se existirem
    cols_desejadas = ["TERMO DE VIAGEM", "DATA INÍCIO", "DATA TÉRMINO", "ANO", "DIAS DE MAR", "MILHAS NAVEGADAS", "SOMA"]
    cols_existentes = [c for c in cols_desejadas if c in df.columns]
    df = df[cols_existentes]
         
    # Conversão de tipos BLINDADA
    numeric_cols = ["DIAS DE MAR", "MILHAS NAVEGADAS"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
             
    # Conversão especial para ANO (forçar Inteiro)
    if "ANO" in df.columns:
        df["ANO"] = pd.to_numeric(df["ANO"], errors='coerce').fillna(0).astype(int)
             
    # Conversão de datas com parser customizado
    date_cols = ["DATA INÍCIO", "DATA TÉRMINO"]
    for col in date_cols:
        if col in df.columns and "ANO" in df.columns:
            df[col] = df.apply(lambda row: parse_mar_date(row[col], row["ANO"]), axis=1)
        elif col in df.columns:
            # Fallback se não tiver coluna ANO
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
             
    return df

@st.cache_data(ttl=3600, show_spinner="Carregando cardápio...")
def load_cardapio():
    """Carrega dados do cardápio semanal"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lê sem cabeçalho para pegar a estrutura exata
    df = conn.read(spreadsheet=URL_CARDAPIO, header=None, ttl="1h")
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
    # Carregamento dos dados de mar é feito sob demanda na aba para economizar recurso inicial
except Exception as e:
    st.error(f"Erro de conexão principal: {e}")
    st.stop()


# ============================================================
# 5. DESCOBRIR BLOCOS DE DATAS
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
# 6. TRANSFORMAÇÃO EM EVENTOS (WIDE → LONG)
# ============================================================

@st.cache_data(ttl=600)
def construir_eventos(df_raw: pd.DataFrame, blocos) -> pd.DataFrame:
    eventos = []
    for _, row in df_raw.iterrows():
        posto  = row.get("Posto", "")
        nome   = row.get("Nome", "")
        escala = row.get("Serviço", "")
         
        eqman_val = row.get("EqMan", "")
        eqman = str(eqman_val) if pd.notna(eqman_val) and str(eqman_val) != "-" else "Não"
         
        gvi = parse_bool(row.get("Gvi/GP", ""))
        insp = parse_bool(row.get("IN", ""))

        militar_info = {
            "Posto": posto,
            "Nome": nome,
            "Escala": escala,
            "EqMan": eqman,
            "GVI": gvi,
            "IN": insp,
        }

        for col_ini, col_fim, col_mot, tipo_base in blocos:
            ini = parse_sheet_date(row.get(col_ini))
            fim = parse_sheet_date(row.get(col_fim))

            if pd.isna(ini) or pd.isna(fim):
                continue
             
            if fim < ini:
                ini, fim = fim, ini
                 
            dur = (fim - ini).days + 1
            if dur < 1 or dur > 365 * 2:
                continue

            if tipo_base == "Férias":
                motivo_real = "Férias"
                tipo_final = "Férias"
            else:
                motivo_texto = str(row.get(col_mot, "")).strip()
                if tipo_base == "Curso":
                    motivo_real = motivo_texto if motivo_texto and "nan" not in motivo_texto.lower() else "CURSO (não especificado)"
                    tipo_final = "Curso"
                else:
                    motivo_real = motivo_texto if motivo_texto and "nan" not in motivo_texto.lower() else "OUTROS"
                    tipo_final = "Outros"

            if tipo_final == "Férias":
                motivo_agr = "Férias"
            elif tipo_final == "Curso":
                motivo_agr = "Curso"
            else:
                motivo_agr = motivo_real

            eventos.append({
                **militar_info,
                "Inicio": ini,
                "Fim": fim,
                "Duracao_dias": dur,
                "Motivo": motivo_real,
                "MotivoAgrupado": motivo_agr,
                "Tipo": tipo_final
            })
    return pd.DataFrame(eventos)

df_eventos = construir_eventos(df_raw, BLOCOS_DATAS)


# ============================================================
# 7. EXPANSÃO POR DIA
# ============================================================

@st.cache_data(ttl=600)
def expandir_eventos_por_dia(df_eventos: pd.DataFrame) -> pd.DataFrame:
    if df_eventos.empty:
        return pd.DataFrame()
    linhas = []
    for _, ev in df_eventos.iterrows():
        ini = ev["Inicio"]
        fim = ev["Fim"]
        if pd.isna(ini) or pd.isna(fim):
            continue
        for data in pd.date_range(ini, fim):
            linhas.append({
                "Data": data,
                "Posto": ev["Posto"],
                "Nome": ev["Nome"],
                "Escala": ev["Escala"],
                "EqMan": ev["EqMan"],
                "GVI": ev["GVI"],
                "IN": ev["IN"],
                "Motivo": ev["Motivo"],
                "MotivoAgrupado": ev["MotivoAgrupado"],
                "Tipo": ev["Tipo"]
            })
    return pd.DataFrame(linhas)

df_dias = expandir_eventos_por_dia(df_eventos)

# ============================================================
# 7.1 HELPER PARA STATUS EM DATA (NOVO)
# ============================================================

def get_status_em_data(row, data_ref, blocos_cols):
    for col_ini, col_fim, col_mot, tipo_base in blocos_cols:
        ini = parse_sheet_date(row.get(col_ini))
        fim = parse_sheet_date(row.get(col_fim))
         
        if pd.isna(ini) or pd.isna(fim): continue
         
        if ini <= data_ref <= fim:
            motivo = tipo_base
            if col_mot and col_mot in row.index and not pd.isna(row[col_mot]):
                motivo = str(row[col_mot])
            return motivo
             
    return "Presente"


# ============================================================
# 8. FUNÇÕES DE FILTRO E GRÁFICOS
# ============================================================

def filtrar_tripulacao(df: pd.DataFrame, apenas_eqman: bool, apenas_in: bool, apenas_gvi: bool) -> pd.DataFrame:
    res = df.copy()
    if apenas_eqman and "EqMan" in res.columns:
        res = res[(res["EqMan"].notna()) & (res["EqMan"].astype(str) != "Não") & (res["EqMan"].astype(str) != "-")]
    if apenas_in and "IN" in res.columns:
        res = res[res["IN"].apply(parse_bool)]
    if apenas_gvi and "Gvi/GP" in res.columns:
        res = res[res["Gvi/GP"].apply(parse_bool)]
    return res

def filtrar_eventos(df: pd.DataFrame, apenas_eqman: bool, apenas_in: bool, apenas_gvi: bool) -> pd.DataFrame:
    res = df.copy()
    if apenas_eqman:
        res = res[res["EqMan"] != "Não"]
    if apenas_in:
        res = res[res["IN"] == True]
    if apenas_gvi:
        res = res[res["GVI"] == True]
    return res

def filtrar_dias(df: pd.DataFrame, apenas_eqman: bool, apenas_in: bool, apenas_gvi: bool) -> pd.DataFrame:
    res = df.copy()
    if apenas_eqman:
        res = res[res["EqMan"] != "Não"]
    if apenas_in:
        res = res[res["IN"] == True]
    if apenas_gvi:
        res = res[res["GVI"] == True]
    return res

AMEZIA_COLORS = ["#4099ff", "#ff5370", "#2ed8b6", "#ffb64d", "#a3a3a3"]

def update_fig_layout(fig, title=None):
    layout_args = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="'Nunito Sans', sans-serif", size=12),
        margin=dict(t=60, b=20, l=20, r=20),
        colorway=AMEZIA_COLORS
    )
    if title: layout_args["title"] = title
    fig.update_layout(**layout_args)
    return fig


# ============================================================
# 9. PARÂMETROS (SIDEBAR) + NAVEGAÇÃO
# ============================================================

st.sidebar.markdown("## HOME")

# Função para carregar SVG como base64
def get_svg_as_base64(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            svg = f.read()
        return base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    except: return ""

# ICONES ATUALIZADOS
ICON_MAP = {
    "Presentes": "presentes.svg",
    "Ausentes": "ausentes.svg",
    "Cardápio": "cardapio.svg",
    "Dias de Mar": "mar2.svg", 
    "Aniversários": "aniversario.svg",
    "Agenda do Navio": "agenda.svg",
    "Linha do Tempo": "linha_tempo.svg",
    "Equipes Operativas": "equipe_operativa.svg",
    "Estatísticas & Análises": "analise.svg",
    "Férias": "icons8-sun-50.svg",
    "Cursos": "cursos.svg",
    "Tabela de Serviço": "icons8-tick-box-50.svg",
    "Log / Debug": "log.svg"
}

css_icons = ""
folder_path = os.path.join(os.path.dirname(__file__), "assets")
options = list(ICON_MAP.keys())

for i, option in enumerate(options):
    icon_filename = ICON_MAP[option]
    # Assume que o usuário salvará os arquivos como .svg se não tiverem extensão no dicionário
    if not icon_filename.endswith(".svg"):
        icon_filename += ".svg"
         
    full_path = os.path.join(folder_path, icon_filename)
    b64 = get_svg_as_base64(full_path)
    if b64:
        css_icons += f"""
        div[role="radiogroup"] > label:nth-child({i+1}) [data-testid="stMarkdownContainer"] > p {{
            display: flex; align-items: center;
        }}
        div[role="radiogroup"] > label:nth-child({i+1}) [data-testid="stMarkdownContainer"] > p::before {{
            content: ""; display: inline-block; width: 24px; height: 24px; margin-right: 10px;
            background-color: currentColor;
            -webkit-mask-image: url('data:image/svg+xml;base64,{b64}');
            mask-image: url('data:image/svg+xml;base64,{b64}');
            -webkit-mask-size: contain; mask-size: contain;
            -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;
            -webkit-mask-position: center; mask-position: center;
        }}
        """

if css_icons:
    st.markdown(f"<style>{css_icons}</style>", unsafe_allow_html=True)

with st.sidebar.container():
    pagina = st.radio(
        label="Seções",
        options=options,
        index=0,
        label_visibility="collapsed",
        key="pagina_radio"
    )

# ============================================================
# 10. MÉTRICAS GLOBAIS
# ============================================================

def exibir_metricas_globais(data_referencia):
    hoje_ref = pd.to_datetime(data_referencia)
    if not df_eventos.empty:
        ausentes_hoje_global = df_eventos[
            (df_eventos["Inicio"] <= hoje_ref) & (df_eventos["Fim"] >= hoje_ref)
        ]
    else:
        ausentes_hoje_global = pd.DataFrame()

    total_efetivo_global = len(df_raw)
    total_ausentes_global = len(ausentes_hoje_global["Nome"].unique()) if not ausentes_hoje_global.empty else 0
    total_presentes_global = total_efetivo_global - total_ausentes_global
    percentual_global = (total_presentes_global / total_efetivo_global * 100) if total_efetivo_global > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Efetivo Total", total_efetivo_global)
    col2.metric("A Bordo (global)", total_presentes_global)
    col3.metric("Ausentes (global)", total_ausentes_global, delta_color="inverse")
    col4.metric("Prontidão (global)", f"{percentual_global:.1f}%")


# ============================================================
# 11. PÁGINAS
# ============================================================

hoje_padrao = datetime.today()

# --------------------------------------------------------
# PRESENTES
# --------------------------------------------------------
if pagina == "Presentes":
    st.subheader("Presentes a bordo")
    metrics_placeholder = st.container()
    table_placeholder = st.container()
    st.markdown("---")
    st.markdown("##### Filtros & Data")
    col_f1, col_f2, col_f3, col_data = st.columns([1.5, 1.5, 1.5, 2])
    apenas_eqman = col_f1.checkbox("Apenas EqMan", key="pres_eqman")
    apenas_in    = col_f2.checkbox("Apenas IN", key="pres_in")
    apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="pres_gvi")
    data_ref = col_data.date_input("Data de Referência", hoje_padrao, key="data_pres", format="DD/MM/YYYY")
    hoje = pd.to_datetime(data_ref)

    with metrics_placeholder:
        exibir_metricas_globais(hoje)
        st.markdown("---")

    with table_placeholder:
        df_trip = filtrar_tripulacao(df_raw, apenas_eqman, apenas_in, apenas_gvi)
        if not df_eventos.empty:
            ausentes_hoje = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
            ausentes_hoje = filtrar_eventos(ausentes_hoje, apenas_eqman, apenas_in, apenas_gvi)
            nomes_ausentes = set(ausentes_hoje["Nome"].unique())
        else:
            nomes_ausentes = set()

        df_presentes = df_trip[~df_trip["Nome"].isin(nomes_ausentes)].copy()
        st.markdown(f"Total de presentes (visão filtrada): **{len(df_presentes)}**")

        if df_presentes.empty:
            st.info("Nenhum militar presente para os filtros atuais.")
        else:
            tabela = df_presentes[["Posto", "Nome", "Serviço", "EqMan", "Gvi/GP", "IN"]].copy()
            if "Gvi/GP" in tabela.columns:
                tabela["GVI/GP"] = tabela["Gvi/GP"].apply(lambda v: "Sim" if parse_bool(v) else "Não")
            if "IN" in tabela.columns:
                tabela["IN"] = tabela["IN"].apply(lambda v: "Sim" if parse_bool(v) else "Não")
            if "Gvi/GP" in tabela.columns:
                tabela = tabela.drop(columns=["Gvi/GP"])
            st.dataframe(tabela, use_container_width=True, hide_index=True)

        st.markdown("##### Prontidão (visão filtrada)")
        total_filtrado = len(df_trip)
        if total_filtrado > 0:
            presentes_filtrado = len(df_presentes)
            pront_pct = presentes_filtrado / total_filtrado * 100
             
            # ECHARTS DONUT PRONTIDÃO
            data_prontidao = [
                {"value": presentes_filtrado, "name": "Presentes"},
                {"value": total_filtrado - presentes_filtrado, "name": "Ausentes"}
            ]
            opt_prontidao = make_echarts_donut(data_prontidao, "Prontidão")
            st_echarts(options=opt_prontidao, height="500px")
        else:
            st.info("Não há efetivo na visão atual para calcular a prontidão.")

# --------------------------------------------------------
# AUSENTES
# --------------------------------------------------------
elif pagina == "Ausentes":
    st.subheader("Ausentes por dia")
    col_d1, _ = st.columns([2, 4])
    data_ref = col_d1.date_input("Data de Referência", hoje_padrao, key="data_aus_tab", format="DD/MM/YYYY")
    hoje = pd.to_datetime(data_ref)
    table_placeholder = st.empty()
    st.markdown("<br>", unsafe_allow_html=True)
    col_f_spacer1, col_f_content, col_f_spacer2 = st.columns([1, 4, 1])
    with col_f_content:
        c_f1, c_f2, c_f3 = st.columns(3)
        apenas_eqman = c_f1.checkbox("Apenas EqMan", key="aus_eqman_tab")
        apenas_in    = c_f2.checkbox("Apenas IN", key="aus_in_tab")
        apenas_gvi   = c_f3.checkbox("Apenas GVI/GP", key="aus_gvi_tab")

    if df_eventos.empty:
        table_placeholder.info("Sem eventos de ausência registrados.")
    else:
        ausentes_hoje = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
        ausentes_hoje = filtrar_eventos(ausentes_hoje, apenas_eqman, apenas_in, apenas_gvi)
        with table_placeholder.container():
            if ausentes_hoje.empty:
                st.success("Todo o efetivo está a bordo para os filtros atuais.")
            else:
                temp = ausentes_hoje.copy()
                temp["MotivoExib"] = temp.apply(
                    lambda r: "Férias" if r["Tipo"] == "Férias"
                    else ("Curso" if r["Tipo"] == "Curso" else str(r["Motivo"])),
                    axis=1
                )
                show_df = temp[["Posto", "Nome", "MotivoExib", "Fim"]].copy()
                show_df["Retorno"] = show_df["Fim"].dt.strftime("%d/%m/%Y")
                show_df = show_df.drop(columns=["Fim"])
                show_df = show_df.rename(columns={"MotivoExib": "Motivo"})
                st.dataframe(show_df, use_container_width=True, hide_index=True)

    st.markdown("---")
     
    if not df_dias.empty:
        df_dias_filt = filtrar_dias(df_dias, apenas_eqman, apenas_in, apenas_gvi)
         
        if not df_dias_filt.empty:
            st.subheader("Quantidade de militares ausentes por mês")
            df_dias_filt["Mes"] = df_dias_filt["Data"].dt.to_period("M").dt.to_timestamp()
            df_aus_mes = (df_dias_filt[["Mes", "Nome"]].drop_duplicates().groupby("Mes")["Nome"].nunique().reset_index(name="Militares"))
             
            st.markdown("##### Ausentes por mês (Geral)")
            # Format dates for x-axis
            x_dates_aus = df_aus_mes["Mes"].dt.strftime("%b/%Y").tolist()
            opt_aus_mes = make_echarts_line(x_dates_aus, df_aus_mes["Militares"].tolist())
            st_echarts(options=opt_aus_mes, height="400px")
             
            st.markdown("---")
             
            st.subheader("Militares ausentes por dia (Mês Específico)")
             
            col_sel_m, col_sel_a, _ = st.columns([1, 1, 2])
            meses_dict = {
                "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
                "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
            }
            now = (datetime.utcnow() - timedelta(hours=3))
            sel_mes_nome_aus = col_sel_m.selectbox("Mês", list(meses_dict.keys()), index=now.month-1, key="mes_aus_graf")
            sel_ano_aus = col_sel_a.number_input("Ano", value=now.year, min_value=2020, max_value=2030, key="ano_aus_graf")
            sel_mes_aus = meses_dict[sel_mes_nome_aus]
             
            start_date = datetime(sel_ano_aus, sel_mes_aus, 1)
            if sel_mes_aus == 12:
                end_date = datetime(sel_ano_aus + 1, 1, 1)
            else:
                end_date = datetime(sel_ano_aus, sel_mes_aus + 1, 1)
                 
            df_dias_mes = df_dias_filt[
                (df_dias_filt["Data"] >= start_date) & 
                (df_dias_filt["Data"] < end_date)
            ].copy()
             
            if df_dias_mes.empty:
                st.info(f"Sem registros de ausência para {sel_mes_nome_aus}/{sel_ano_aus}.")
            else:
                ausentes_mes_evt = df_eventos[
                    (df_eventos["Inicio"] < end_date) &
                    (df_eventos["Fim"] >= start_date)
                ].copy()
                 
                ausentes_mes_evt = filtrar_eventos(ausentes_mes_evt, apenas_eqman, apenas_in, apenas_gvi)
                 
                if not ausentes_mes_evt.empty:
                    tabela_mes = ausentes_mes_evt[["Posto", "Nome", "MotivoAgrupado", "Inicio", "Fim"]].copy()
                    tabela_mes["Início"] = tabela_mes["Inicio"].dt.strftime("%d/%m")
                    tabela_mes["Fim"] = tabela_mes["Fim"].dt.strftime("%d/%m")
                    tabela_mes = tabela_mes.drop(columns=["Inicio", "Fim"])
                    tabela_mes = tabela_mes.sort_values(by=["Nome"])
                    st.dataframe(tabela_mes, use_container_width=True, hide_index=True)
                 
                df_aus_dia = (df_dias_mes.groupby("Data")["Nome"].nunique().reset_index(name="Militares"))
                 
                st.markdown(f"##### Ausências diárias em {sel_mes_nome_aus}/{sel_ano_aus}")
                x_dates_dia = df_aus_dia["Data"].dt.strftime("%d/%m").tolist()
                opt_aus_dia = make_echarts_line(x_dates_dia, df_aus_dia["Militares"].tolist())
                st_echarts(options=opt_aus_dia, height="400px")
        else:
             st.info("Sem dados para gerar gráficos com os filtros atuais.")
    else:
        st.info("Sem dados de ausências para gerar gráficos.")

# --------------------------------------------------------
# NOVO: DIAS DE MAR
# --------------------------------------------------------
elif pagina == "Dias de Mar":
    st.subheader("Dias de Mar e Milhas Navegadas")
     
    try:
        df_mar = load_dias_mar()
         
        if df_mar.empty:
            st.info("Planilha de Dias de Mar vazia ou não encontrada.")
        else:
            # Cálculos Gerais
            total_dias_mar = df_mar["DIAS DE MAR"].sum()
            total_milhas = df_mar["MILHAS NAVEGADAS"].sum()
             
            # Médias por Ano
            # Agrupa por ANO e soma, depois tira a média dos anos
            df_por_ano = df_mar.groupby("ANO")[["DIAS DE MAR", "MILHAS NAVEGADAS"]].sum().reset_index()
            media_dias_ano = df_por_ano["DIAS DE MAR"].mean()
            media_milhas_ano = df_por_ano["MILHAS NAVEGADAS"].mean()

            # Exibir Cards
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Dias de Mar", f"{total_dias_mar:,.1f}")
            c2.metric("Total Milhas", f"{total_milhas:,.0f}")
            c3.metric("Média Dias/Ano", f"{media_dias_ano:,.1f}")
            c4.metric("Média Milhas/Ano", f"{media_milhas_ano:,.0f}")
             
            st.markdown("---")
             
            # Gráfico 1: Dias de Mar por Ano (LINHA)
            st.markdown("##### Dias de Mar por Ano")
            opt_ano = make_echarts_line(df_por_ano["ANO"].astype(str).tolist(), df_por_ano["DIAS DE MAR"].tolist())
            st_echarts(options=opt_ano, height="400px")
             
            st.markdown("---")
             
            # Gráfico 2: Detalhamento Mensal (LINHA)
            st.subheader("Detalhamento Mensal")
             
            # Seletor de Ano
            # Ordena os anos e converte para int para exibir bonito no selectbox
            anos_disponiveis = sorted(df_mar["ANO"].unique().astype(int), reverse=True)
            if anos_disponiveis:
                ano_sel_mar = st.selectbox("Selecione o Ano", anos_disponiveis)
                 
                # Filtrar dados do ano
                df_mar_ano = df_mar[df_mar["ANO"] == ano_sel_mar].copy()
                 
                if not df_mar_ano.empty:
                    # Extrair Mês da Data de Início
                    if "DATA INÍCIO" in df_mar_ano.columns:
                        # Garante que DATA INÍCIO é datetime
                        # (Já tratado no load_dias_mar, mas mantemos verificação de segurança se necessário, 
                        # porém sem re-parse forçado que pode ignorar o ano customizado)
                        # df_mar_ano["DATA INÍCIO"] = pd.to_datetime(df_mar_ano["DATA INÍCIO"], dayfirst=True, errors='coerce')
                         
                        # Agrupar por mês (ordenado por número do mês para gráfico correto)
                        df_mar_ano["Mês_Num"] = df_mar_ano["DATA INÍCIO"].dt.month
                         
                        # Agrupamento e soma
                        df_mensal_mar = df_mar_ano.groupby("Mês_Num")["DIAS DE MAR"].sum().reset_index()
                         
                        # --- CRIA O DATAFRAME COM TODOS OS 12 MESES ---
                        todos_meses = pd.DataFrame({'Mês_Num': range(1, 13)})
                        df_completo = pd.merge(todos_meses, df_mensal_mar, on='Mês_Num', how='left').fillna(0)
                         
                        # Mapear número para nome para o eixo X
                        mapa_meses = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
                        df_completo["Mês"] = df_completo["Mês_Num"].map(mapa_meses)
                         
                        st.markdown(f"##### Dias de Mar em {ano_sel_mar} (por mês de início da comissão)")
                        opt_mes_mar = make_echarts_line(df_completo["Mês"].tolist(), df_completo["DIAS DE MAR"].tolist())
                        st_echarts(options=opt_mes_mar, height="400px")
                         
                        with st.expander("Ver dados brutos do ano selecionado"):
                            st.dataframe(df_mar_ano[["TERMO DE VIAGEM", "DATA INÍCIO", "DATA TÉRMINO", "DIAS DE MAR", "MILHAS NAVEGADAS"]], use_container_width=True)
                    else:
                        st.warning("Coluna 'DATA INÍCIO' não encontrada ou inválida.")
                else:
                    st.info(f"Sem dados de dias de mar para o ano {ano_sel_mar}.")

    except Exception as e:
        st.error(f"Erro ao processar Dias de Mar: {e}")


# --------------------------------------------------------
# OUTRAS PÁGINAS (Usam Data Padrão Hoje)
# --------------------------------------------------------
else:
    hoje = pd.to_datetime(hoje_padrao)
     
    if pagina == "Agenda do Navio":
        st.subheader("Agenda do Navio (Google Calendar)")
        col_sel, col_btn = st.columns([3, 1])
        with col_sel:
            nome_agenda = st.selectbox("Selecione a Agenda:", list(AGENDAS_OFICIAIS.keys()))
            selected_id = AGENDAS_OFICIAIS[nome_agenda]
        with col_btn:
            st.write("")
            st.write("")
            if st.button("Atualizar eventos"):
                load_calendar_events.clear()
                st.rerun()
        if selected_id:
            df_cal = load_calendar_events(selected_id)
            if df_cal.empty:
                st.info(f"Nenhum evento futuro encontrado na agenda **{nome_agenda}**.")
            else:
                st.markdown("---")
                for _, row in df_cal.iterrows():
                    st.markdown(
                        f"""<div class="agenda-card"><div style="font-weight: 600; font-size: 1.05rem;">{row['Evento']}</div><div class="agenda-date">{row['Data']}</div></div>""",
                        unsafe_allow_html=True
                    )

    elif pagina == "Linha do Tempo":
        st.subheader("Planejamento Anual de Ausências")
        content_container = st.container()
        with content_container:
            if df_eventos.empty:
                st.info("Planilha parece não ter datas preenchidas.")
            else:
                df_gantt = df_eventos.copy()
                if df_gantt.empty:
                    st.info("Nenhum evento encontrado.")
                else:
                    ordem_nomes = df_raw["Nome"].unique().tolist()
                    df_gantt["Nome"] = pd.Categorical(df_gantt["Nome"], categories=ordem_nomes, ordered=True)
                    df_gantt = df_gantt.sort_values("Nome")
                    min_data = df_gantt["Inicio"].min()
                    max_data = df_gantt["Fim"].max()
                    ano_min = min_data.year if pd.notnull(min_data) else 2025
                    ano_max = max_data.year if pd.notnull(max_data) else 2026
                    fig = px.timeline(
                        df_gantt, x_start="Inicio", x_end="Fim", y="Nome", color="MotivoAgrupado",
                        hover_data=["Posto", "Escala", "EqMan", "GVI", "IN", "MotivoAgrupado"],
                        color_discrete_sequence=AMEZIA_COLORS
                    )
                    chart_height = max(600, len(ordem_nomes) * 30)
                    fig.update_yaxes(autorange="reversed", categoryorder="array", categoryarray=ordem_nomes, type='category', showgrid=True, tickmode='array', tickvals=ordem_nomes)
                    fig.add_trace(px.scatter(y=ordem_nomes, x=[min_data]*len(ordem_nomes), opacity=0).data[0])
                    fig.data[-1].showlegend = False
                    fig.update_xaxes(range=[datetime(ano_min, 1, 1), datetime(ano_max, 12, 31)])
                    fig.add_vline(x=hoje, line_width=2, line_dash="dash", line_color="#ff5370")
                    update_fig_layout(fig, title="Cronograma de Ausências")
                    fig.update_layout(plot_bgcolor="rgba(255,255,255,0.05)", height=chart_height)
                    st.plotly_chart(fig, use_container_width=True)

    elif pagina == "Equipes Operativas":
        st.subheader("Equipes Operativas")
        col_eq1, col_eq2, col_eq3 = st.columns(3)
        with col_eq1:
            st.markdown("### GVI/GP")
            df_gvi = df_raw[df_raw["Gvi/GP"].apply(parse_bool)].copy()
            if df_gvi.empty:
                st.info("Nenhum militar no GVI/GP.")
            else:
                st.dataframe(df_gvi[["Posto", "Nome"]], use_container_width=True, hide_index=True)
                st.markdown(f"**Total:** {len(df_gvi)}")
        with col_eq2:
            st.markdown("### Inspetores Navais")
            df_in = df_raw[df_raw["IN"].apply(parse_bool)].copy()
            if df_in.empty:
                st.info("Nenhum Inspetor Naval.")
            else:
                st.dataframe(df_in[["Posto", "Nome"]], use_container_width=True, hide_index=True)
                st.markdown(f"**Total:** {len(df_in)}")
        with col_eq3:
            st.markdown("### EqMan")
            df_eqman = df_raw[(df_raw["EqMan"].notna()) & (df_raw["EqMan"] != "Não") & (df_raw["EqMan"] != "-")].copy()
            if df_eqman.empty:
                st.info("Nenhum militar na EqMan.")
            else:
                st.dataframe(df_eqman[["Posto", "Nome", "EqMan"]], use_container_width=True, hide_index=True)
                st.markdown(f"**Total:** {len(df_eqman)}")

    elif pagina == "Estatísticas & Análises":
        st.subheader("Visão Analítica de Ausências")
        content_container = st.container()
        with content_container:
            if df_eventos.empty:
                st.write("Sem dados suficientes para estatísticas.")
            else:
                df_evt = df_eventos.copy()
                if df_evt.empty:
                    st.info("Nenhum evento.")
                else:
                    col_a1, col_a2, col_a3 = st.columns(3)
                    total_dias_ausencia = df_evt["Duracao_dias"].sum()
                    media_dias_por_militar = df_evt.groupby("Nome")["Duracao_dias"].sum().mean()
                    df_ferias_evt = df_evt[df_evt["Tipo"] == "Férias"].copy()
                    media_dias_ferias = (df_ferias_evt.groupby("Nome")["Duracao_dias"].sum().mean() if not df_ferias_evt.empty else 0)
                    col_a1.metric("Dias de ausência (total)", int(total_dias_ausencia))
                    col_a2.metric("Média de dias de ausência por militar", f"{media_dias_por_militar:.1f}")
                    col_a3.metric("Média de dias de FÉRIAS por militar", f"{media_dias_ferias:.1f}")
                    st.markdown("---")
                    df_motivos_dias = (df_evt.groupby("MotivoAgrupado")["Duracao_dias"].sum().reset_index().sort_values("Duracao_dias", ascending=False))
                     
                    # ECHARTS DONUT (VISÃO ANALÍTICA)
                    data_motivos = [
                        {"value": row["Duracao_dias"], "name": row["MotivoAgrupado"]}
                        for _, row in df_motivos_dias.iterrows()
                    ]
                    opt_motivos = make_echarts_donut(data_motivos, "Motivos de Ausência")
                    st_echarts(options=opt_motivos, height="600px")
                     
                    st.markdown("---")
                     
                    df_top10 = (df_evt.groupby(["Nome", "Posto"])["Duracao_dias"].sum().reset_index().sort_values("Duracao_dias", ascending=False).head(10))
                    st.markdown("##### Top 10 – Dias de ausência por militar")
                    opt_top10 = make_echarts_bar(df_top10["Nome"].tolist(), df_top10["Duracao_dias"].tolist())
                    st_echarts(options=opt_top10, height="500px")
                    if not df_dias.empty:
                        st.markdown("---")
                        st.subheader("Média de militares ausentes por dia (por mês)")
                        df_dias_filtrado = df_dias.copy()
                        if not df_dias_filtrado.empty:
                            df_diario = (df_dias_filtrado.groupby("Data")["Nome"].nunique().reset_index(name="Ausentes"))
                            df_diario["Mes"] = df_diario["Data"].dt.to_period("M").dt.to_timestamp()
                            df_mensal = (df_diario.groupby("Mes")["Ausentes"].mean().reset_index(name="Media_ausentes_dia"))
                            st.markdown("##### Média de Ausentes por Dia – por Mês")
                            # Format dates for x-axis
                            x_dates = df_mensal["Mes"].dt.strftime("%b/%Y").tolist()
                            opt_mensal = make_echarts_line(x_dates, df_mensal["Media_ausentes_dia"].tolist())
                            st_echarts(options=opt_mensal, height="400px")
                        else:
                            st.info("Sem dados diários para análise mensal.")

    elif pagina == "Férias":
        st.subheader("Férias cadastradas")
        content_container = st.container()
        with content_container:
            if df_eventos.empty:
                st.write("Sem dados de férias registrados.")
            else:
                df_ferias = df_eventos[df_eventos["Tipo"] == "Férias"].copy()
                 
                # 1. GRÁFICO DE ROSCA (PRIMEIRA INFORMAÇÃO)
                st.markdown("### % de férias gozadas (tripulação)")
                if "%DG" in df_raw.columns:
                    media_percentual = df_raw["%DG"].mean(skipna=True)
                    if pd.notna(media_percentual):
                        if media_percentual <= 1:
                            perc_gozado = media_percentual * 100
                        else:
                            perc_gozado = media_percentual
                        perc_nao = max(0.0, 100.0 - perc_gozado)
                         
                        # ECHARTS DONUT
                        data_ferias = [
                            {"value": round(perc_gozado, 1), "name": "Gozado"},
                            {"value": round(perc_nao, 1), "name": "Não gozado"}
                        ]
                        opt_ferias = make_echarts_donut(data_ferias, "Férias Gozadas")
                        st_echarts(options=opt_ferias, height="400px")
                    else:
                        st.info("Não foi possível calcular a média da coluna %DG.")
                else:
                    st.info("Coluna %DG não encontrada na planilha para cálculo do percentual de férias gozadas.")
                 
                st.markdown("---")

                if df_ferias.empty:
                    st.info("Nenhuma férias cadastrada.")
                else:
                    # 2. CARDS DE PESQUISA
                    c_search1, c_search2 = st.columns(2)
                     
                    with c_search1:
                        st.markdown("#### Buscar por Militar")
                        # Cria lista combinada Posto + Nome para facilitar busca
                        # Usa df_raw para garantir que todos apareçam na lista, mesmo sem férias
                        df_raw_temp = df_raw.copy()
                        if "Posto" in df_raw_temp.columns and "Nome" in df_raw_temp.columns:
                            df_raw_temp["PostoNome"] = df_raw_temp["Posto"].astype(str) + " " + df_raw_temp["Nome"].astype(str)
                            opts_militares = sorted(df_raw_temp["PostoNome"].unique().tolist())
                             
                            sel_militar = st.selectbox("Selecione o Militar", ["Selecione..."] + opts_militares, key="search_mil_ferias")
                             
                            if sel_militar != "Selecione...":
                                # Filtra df_ferias
                                df_ferias["PostoNome"] = df_ferias["Posto"].astype(str) + " " + df_ferias["Nome"].astype(str)
                                res_militar = df_ferias[df_ferias["PostoNome"] == sel_militar].copy()
                                 
                                if not res_militar.empty:
                                    res_militar["Início"] = res_militar["Inicio"].dt.strftime("%d/%m/%Y")
                                    res_militar["Término"] = res_militar["Fim"].dt.strftime("%d/%m/%Y")
                                    st.dataframe(res_militar[["Início", "Término", "Duracao_dias"]].rename(columns={"Duracao_dias": "Dias"}), use_container_width=True, hide_index=True)
                                else:
                                    st.info("Nenhum período de férias encontrado para este militar.")
                        else:
                            st.error("Colunas Posto/Nome não encontradas.")

                    with c_search2:
                        st.markdown("#### Buscar por Mês/Ano")
                        c_m, c_a = st.columns(2)
                        meses_dict = {
                            "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
                            "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
                        }
                        hoje_br = datetime.utcnow() - timedelta(hours=3)
                        sel_mes_nome = c_m.selectbox("Mês", list(meses_dict.keys()), index=hoje_br.month-1, key="ferias_mes_search")
                        sel_ano = c_a.number_input("Ano", value=hoje_br.year, min_value=2020, max_value=2030, key="ferias_ano_search")
                         
                        sel_mes = meses_dict[sel_mes_nome]
                         
                        # Lógica de sobreposição de datas
                        import calendar
                        last_day = calendar.monthrange(sel_ano, sel_mes)[1]
                        start_of_month = datetime(sel_ano, sel_mes, 1)
                        end_of_month = datetime(sel_ano, sel_mes, last_day, 23, 59, 59)
                         
                        # Filtro: Inicio das férias <= Fim do Mês E Fim das férias >= Inicio do Mês
                        mask = (df_ferias["Inicio"] <= end_of_month) & (df_ferias["Fim"] >= start_of_month)
                        res_mes = df_ferias[mask].copy()
                         
                        if not res_mes.empty:
                             res_mes["Início"] = res_mes["Inicio"].dt.strftime("%d/%m/%Y")
                             res_mes["Término"] = res_mes["Fim"].dt.strftime("%d/%m/%Y")
                             st.dataframe(res_mes[["Posto", "Nome", "Início", "Término"]], use_container_width=True, hide_index=True)
                        else:
                            st.info(f"Ninguém de férias em {sel_mes_nome}/{sel_ano}.")

                    st.markdown("---")
                     
                    # 3. MÉTRICAS GERAIS E GRÁFICOS
                    col_f1m, col_f2m, col_f3m = st.columns(3)
                    total_militares_com_ferias = df_ferias["Nome"].nunique()
                    dias_totais_ferias = df_ferias["Duracao_dias"].sum()
                    total_efetivo = df_raw["Nome"].nunique()
                    restam_cadastrar = max(0, total_efetivo - total_militares_com_ferias)
                    col_f1m.metric("Militares com férias", total_militares_com_ferias)
                    col_f2m.metric("Dias totais", int(dias_totais_ferias))
                    col_f3m.metric("Restam cadastrar", restam_cadastrar)
                     
                    st.markdown("---")
                     
                    col_fx1, col_fx2 = st.columns(2)
                    df_escala = (df_ferias.groupby("Escala")["Nome"].nunique().reset_index(name="Militares").sort_values("Militares", ascending=False))
                    with col_fx1:
                        st.markdown("##### Militares de férias por serviço")
                        opt_escala = make_echarts_bar(df_escala["Escala"].tolist(), df_escala["Militares"].tolist())
                        st_echarts(options=opt_escala, height="500px")
                     
                    if not df_dias.empty:
                        df_dias_ferias = df_dias[df_dias["Tipo"] == "Férias"].copy()
                        if not df_dias_ferias.empty:
                            df_dias_ferias["Mes"] = df_dias_ferias["Data"].dt.to_period("M").dt.to_timestamp()
                            df_mes_ferias = (df_dias_ferias[["Mes", "Nome"]].drop_duplicates().groupby("Mes")["Nome"].nunique().reset_index(name="Militares"))
                            with col_fx2:
                                st.markdown("##### Quantidade de militares de férias por mês")
                                x_mes_ferias = df_mes_ferias["Mes"].dt.strftime("%b/%Y").tolist()
                                opt_mes_ferias = make_echarts_bar(x_mes_ferias, df_mes_ferias["Militares"].tolist())
                                st_echarts(options=opt_mes_ferias, height="500px")
                        else:
                            col_fx2.info("Sem dados diários suficientes para calcular férias por mês.")

    elif pagina == "Cursos":
        st.subheader("Análises de Cursos")
        content_container = st.container()
        with content_container:
            if df_eventos.empty:
                st.write("Sem dados de cursos registrados.")
            else:
                df_cursos = df_eventos[df_eventos["Tipo"] == "Curso"].copy()
                if df_cursos.empty:
                    st.info("Nenhum curso cadastrado.")
                else:
                    realizados = df_cursos[df_cursos["Fim"] < hoje].copy()
                    inscritos  = df_cursos[df_cursos["Fim"] >= hoje].copy()
                    col_c1, col_c2 = st.columns(2)
                    with col_c1:
                        st.markdown("### Cursos realizados")
                        if realizados.empty:
                            st.info("Nenhum curso finalizado até a data de referência.")
                        else:
                            t_real = realizados[["Posto", "Nome", "Motivo", "Inicio", "Fim", "Duracao_dias"]].copy()
                            t_real["Início"] = t_real["Inicio"].dt.strftime("%d/%m/%Y")
                            t_real["Término"] = t_real["Fim"].dt.strftime("%d/%m/%Y")
                            t_real = t_real.drop(columns=["Inicio", "Fim"])
                            t_real = t_real.rename(columns={"Motivo": "Curso", "Duracao_dias": "Dias"})
                            t_real = t_real.sort_values(by=["Nome", "Início"])
                            st.dataframe(t_real, use_container_width=True, hide_index=True)
                    with col_c2:
                        st.markdown("### Cursos em andamento / futuros")
                        if inscritos.empty:
                            st.info("Nenhum militar com curso em andamento ou futuro.")
                        else:
                            t_insc = inscritos[["Posto", "Nome", "Motivo", "Inicio", "Fim", "Duracao_dias"]].copy()
                            t_insc["Início"] = t_insc["Inicio"].dt.strftime("%d/%m/%Y")
                            t_insc["Término"] = t_insc["Fim"].dt.strftime("%d/%m/%Y")
                            t_insc = t_insc.drop(columns=["Inicio", "Fim"])
                            t_insc = t_insc.rename(columns={"Motivo": "Curso", "Duracao_dias": "Dias"})
                            t_insc = t_insc.sort_values(by=["Início", "Nome"])
                            st.dataframe(t_insc, use_container_width=True, hide_index=True)
                    st.markdown("---")
                    st.subheader("Estatísticas dos cursos realizados")
                    if realizados.empty:
                        st.info("Ainda não há cursos concluídos para gerar estatísticas.")
                    else:
                        col_k1, col_k2, col_k3 = st.columns(3)
                        total_cursos_realizados = len(realizados)
                        militares_com_curso = realizados["Nome"].nunique()
                        cursos_diferentes = realizados["Motivo"].nunique()
                        col_k1.metric("Cursos realizados (eventos)", total_cursos_realizados)
                        col_k2.metric("Militares que já realizaram curso", militares_com_curso)
                        col_k3.metric("Tipos diferentes de cursos", cursos_diferentes)
                        st.markdown("---")
                        col_g1, col_g2 = st.columns(2)
                        df_cursos_freq = (realizados.groupby("Motivo")["Nome"].nunique().reset_index(name="Militares").sort_values("Militares", ascending=False))
                        with col_g1:
                            st.markdown("##### Cursos realizados")
                            opt_cursos_freq = make_echarts_bar(df_cursos_freq["Motivo"].tolist(), df_cursos_freq["Militares"].tolist())
                            st_echarts(options=opt_cursos_freq, height="500px")
                        if not df_dias.empty:
                            df_dias_cursos = df_dias[df_dias["Tipo"] == "Curso"].copy()
                            if not df_dias_cursos.empty:
                                df_dias_cursos["Mes"] = df_dias_cursos["Data"].dt.to_period("M").dt.to_timestamp()
                                df_curso_mes = (df_dias_cursos[["Mes", "Nome"]].drop_duplicates().groupby("Mes")["Nome"].nunique().reset_index(name="Militares"))
                                with col_g2:
                                    st.markdown("##### Militares em curso por mês")
                                    x_curso_mes = df_curso_mes["Mes"].dt.strftime("%b/%Y").tolist()
                                    opt_curso_mes = make_echarts_line(x_curso_mes, df_curso_mes["Militares"].tolist())
                                    st_echarts(options=opt_curso_mes, height="400px")
                            else:
                                col_g2.info("Sem dados diários suficientes para análise mensal de cursos.")

    elif pagina == "Tabela de Serviço":
        st.subheader("Tabela de Serviço - Análise de Escalas")
        st.markdown("#### Escala Diária")
        col_escala_container, _ = st.columns([1, 3])
        with col_escala_container:
            data_ref_diaria = st.date_input("Data de Referência", value=(datetime.utcnow() - timedelta(hours=3)), key="data_ref_escala", format="DD/MM/YYYY")
            dt_ref = pd.to_datetime(data_ref_diaria)
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
                daily_data = []
                for servico in SERVICOS_CONSIDERADOS:
                    people_in_service = df_raw[df_raw[target_col].astype(str).str.contains(servico, case=False, regex=False)]
                    if people_in_service.empty:
                          people_in_service = df_raw[df_raw[target_col].astype(str) == servico]
                    total = len(people_in_service)
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
                def color_scale_daily(val):
                    if isinstance(val, str):
                        if "0x1" in val or "1x1" in val:
                            return "color: #ff5370; font-weight: bold"
                        elif "2x1" in val:
                            return "color: #ffb64d; font-weight: bold"
                        elif "3x1" in val or "4x1" in val or "5x1" in val or "6x1" in val:
                             return "color: #2ed8b6; font-weight: bold"
                    return ""
                st.dataframe(df_daily.style.map(color_scale_daily, subset=["Escala"]), use_container_width=True, hide_index=True)
                st.markdown("---")
        st.markdown("#### Escala Mensal")
        col_mes_sel, col_ano_sel = st.columns(2)
        meses_dict = {
            "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
            "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
        }
        now = (datetime.utcnow() - timedelta(hours=3))
        sel_mes_nome = col_mes_sel.selectbox("Mês", list(meses_dict.keys()), index=now.month-1, key="mes_escala")
        sel_ano = col_ano_sel.number_input("Ano", value=now.year, min_value=2020, max_value=2030, key="ano_escala")
        sel_mes = meses_dict[sel_mes_nome]
        days_in_month = pd.Period(f"{sel_ano}-{sel_mes}-01").days_in_month
        dates = [datetime(sel_ano, sel_mes, d) for d in range(1, days_in_month+1)]
        data_matrix = []
        for d in dates:
            row_data = {"Dia": d.strftime("%d/%m")}
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
        def color_scale_monthly(val):
            if isinstance(val, str):
                if "0x1" in val or "1x1" in val:
                    return "color: #ff5370; font-weight: bold"
                elif "2x1" in val:
                    return "color: #ffb64d; font-weight: bold"
                elif "3x1" in val or "4x1" in val or "5x1" in val or "6x1" in val:
                        return "color: #2ed8b6; font-weight: bold"
            return ""
        st.dataframe(df_tabela.style.map(color_scale_monthly), use_container_width=True, hide_index=True)
        st.markdown("---")
        st.markdown("#### Militares fora da escala")
        df_fora_escala = df_raw[df_raw[target_col].astype(str).str.contains("não concorre", case=False, na=False)].copy()
        if df_fora_escala.empty:
            st.info("Todos os militares estão alocados em alguma escala considerada.")
        else:
            st.write(f"Total de militares que não concorrem à escala: **{len(df_fora_escala)}**")
            st.dataframe(df_fora_escala[["Posto", "Nome", target_col]], use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### Componentes das Escalas")
        cols_srv = st.columns(len(SERVICOS_CONSIDERADOS))
        tabs_escalas = st.tabs(SERVICOS_CONSIDERADOS)
        for i, servico in enumerate(SERVICOS_CONSIDERADOS):
            with tabs_escalas[i]:
                people = df_raw[df_raw[target_col].astype(str).str.contains(servico, case=False, regex=False)]
                if people.empty:
                    people = df_raw[df_raw[target_col].astype(str) == servico]
                if not people.empty:
                    st.write(f"**Total:** {len(people)}")
                    st.dataframe(people[["Posto", "Nome"]], use_container_width=True, hide_index=True)
                else:
                    st.info(f"Ninguém cadastrado como {servico}.")

    elif pagina == "Cardápio":
        st.subheader("Cardápio Semanal")
         
        try:
            df_cardapio_raw = load_cardapio()
             
            if df_cardapio_raw.empty:
                st.info("Não foi possível carregar o cardápio.")
            else:
                # Processamento dos dados
                # Datas estão na linha 2 (index 1), colunas B a I (index 1 a 8)
                # Refeições estão nas linhas 4 a 7 (index 3 a 6)
                 
                try:
                    # Extrair datas
                    raw_dates = df_cardapio_raw.iloc[1, 1:9].values
                     
                    # Extrair refeições
                    # Linha 4: Café da Manhã
                    # Linha 5: Almoço
                    # Linha 6: Jantar
                    # Linha 7: Ceia
                    meals_data = {
                        "Café da Manhã": df_cardapio_raw.iloc[3, 1:9].values,
                        "Almoço": df_cardapio_raw.iloc[4, 1:9].values,
                        "Jantar": df_cardapio_raw.iloc[5, 1:9].values,
                        "Ceia": df_cardapio_raw.iloc[6, 1:9].values
                    }
                     
                    # Construir DataFrame estruturado
                    structured_data = []
                    for i, date_val in enumerate(raw_dates):
                        # Parse da data
                        date_obj = pd.NaT
                        if pd.notna(date_val):
                            try:
                                # Tenta DD/MM/YYYY
                                date_obj = pd.to_datetime(str(date_val).strip(), dayfirst=True, errors='coerce')
                            except:
                                pass
                         
                        day_data = {"Data": date_obj, "DataStr": str(date_val)}
                        for meal_name, meal_vals in meals_data.items():
                            day_data[meal_name] = meal_vals[i] if i < len(meal_vals) else ""
                         
                        structured_data.append(day_data)
                         
                    df_menu = pd.DataFrame(structured_data)
                     
                    # --- VISÃO DIÁRIA ---
                    st.markdown("### Cardápio do Dia")
                    hoje_date = (datetime.utcnow() - timedelta(hours=3)).date()
                     
                    # Filtra para hoje (compara apenas a data)
                    df_hoje = df_menu[df_menu["Data"].dt.date == hoje_date]
                     
                    if not df_hoje.empty:
                        row = df_hoje.iloc[0]
                        c1, c2, c3, c4 = st.columns(4)
                         
                        with c1:
                            st.markdown(f"**Café da Manhã**")
                            st.info(row["Café da Manhã"] if pd.notna(row["Café da Manhã"]) else "-")
                         
                        with c2:
                            st.markdown(f"**Almoço**")
                            st.success(row["Almoço"] if pd.notna(row["Almoço"]) else "-")
                         
                        with c3:
                            st.markdown(f"**Jantar**")
                            st.warning(row["Jantar"] if pd.notna(row["Jantar"]) else "-")
                         
                        with c4:
                            st.markdown(f"**Ceia**")
                            st.error(row["Ceia"] if pd.notna(row["Ceia"]) else "-")
                    else:
                        st.info(f"Não há cardápio cadastrado para hoje ({hoje_date.strftime('%d/%m/%Y')}).")
                     
                    st.markdown("---")
                     
                    # --- VISÃO SEMANAL ---
                    st.markdown("### Visão Semanal")
                     
                    # Prepara tabela para exibição (Data como coluna ou index)
                    df_display = df_menu.copy()
                    # Formata data para exibição
                    DIAS_PT = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}
                    df_display["Dia"] = df_display["Data"].apply(lambda x: f"{x.day:02d}/{x.month:02d} ({DIAS_PT[x.weekday()]})" if pd.notna(x) else "Data Inválida")
                     
                    # Seleciona colunas
                    cols_show = ["Dia", "Café da Manhã", "Almoço", "Jantar", "Ceia"]
                    st.dataframe(df_display[cols_show], use_container_width=True, hide_index=True)
                     
                except Exception as e:
                    st.error(f"Erro ao processar estrutura do cardápio: {e}")
                    st.dataframe(df_cardapio_raw.head(10))

        except Exception as e:
            st.error(f"Erro ao carregar cardápio: {e}")

    elif pagina == "Aniversários":
        st.subheader("Aniversariantes")
         
        try:
            df_niver_raw = load_aniversarios()
             
            if df_niver_raw.empty:
                st.info("Não foi possível carregar a lista de aniversariantes.")
            else:
                # Processar dados
                # Colunas esperadas: B (Posto), E (Nome), H (Aniversário)
                # Vamos tentar identificar pelo index se os nomes não baterem, mas assumiremos nomes primeiro ou index como fallback.
                 
                # Ajuste de índices (0-based): B=1, E=4, H=7
                # Cria um DF limpo
                dados_niver = []
                 
                # Itera sobre as linhas (pulando header se necessário, mas o read já deve ter tratado)
                for idx, row in df_niver_raw.iterrows():
                    # Tenta pegar valores por posição para garantir (já que nomes podem mudar)
                    try:
                        posto = row.iloc[1]
                        nome = row.iloc[4]
                        data_str = row.iloc[7]
                         
                        if pd.notna(nome) and str(nome).strip() != "" and pd.notna(data_str):
                            dt_niver = parse_aniversario_date(data_str)
                            if pd.notna(dt_niver):
                                dados_niver.append({
                                    "Posto": posto,
                                    "Nome": nome,
                                    "DataOriginal": data_str,
                                    "Data": dt_niver,
                                    "Dia": dt_niver.day,
                                    "Mês": dt_niver.month
                                })
                    except:
                        continue
                         
                df_aniversarios = pd.DataFrame(dados_niver)
                 
                if df_aniversarios.empty:
                    st.info("Nenhum aniversariante encontrado ou erro no processamento das datas.")
                else:
                    # Métricas
                    hoje_dt = (datetime.utcnow() - timedelta(hours=3))
                    mes_atual = hoje_dt.month
                    dia_atual = hoje_dt.day
                     
                    aniversariantes_mes = df_aniversarios[df_aniversarios["Mês"] == mes_atual]
                    aniversariantes_dia = df_aniversarios[(df_aniversarios["Mês"] == mes_atual) & (df_aniversarios["Dia"] == dia_atual)]
                     
                    # Próximo e Último
                    # Cria uma coluna com a data de aniversário no ano corrente
                    df_aniversarios["DataCorrente"] = df_aniversarios.apply(
                        lambda x: x["Data"].replace(year=hoje_dt.year), axis=1
                    )
                     
                    # Ordena por data
                    df_aniversarios = df_aniversarios.sort_values("DataCorrente")
                     
                    # Próximo: data >= hoje
                    proximos = df_aniversarios[df_aniversarios["DataCorrente"] >= hoje_dt.replace(hour=0, minute=0, second=0, microsecond=0)]
                    if proximos.empty:
                        # Se não tem mais este ano, pega o primeiro do ano (que será ano que vem na prática)
                        proximo = df_aniversarios.iloc[0]
                    else:
                        proximo = proximos.iloc[0]
                         
                    # Último: data < hoje
                    anteriores = df_aniversarios[df_aniversarios["DataCorrente"] < hoje_dt.replace(hour=0, minute=0, second=0, microsecond=0)]
                    if anteriores.empty:
                        # Se não tem anteriores este ano, pega o último do ano
                        ultimo = df_aniversarios.iloc[-1]
                    else:
                        ultimo = anteriores.iloc[-1]
                     
                    # Cards
                    c1, c2, c3, c4 = st.columns(4)
                     
                    c1.metric("Aniversariantes do Mês", len(aniversariantes_mes))
                    c2.markdown("**Aniversariantes do Dia**")
                    if aniversariantes_dia.empty:
                        c2.info("Não há militares aniversariando hoje.")
                    else:
                        lista_nomes = [f"{row['Posto']} {row['Nome']}" for _, row in aniversariantes_dia.iterrows()]
                        c2.success(f"{', '.join(lista_nomes)}")
                     
                    c3.markdown("**Último Aniversariante**")
                    c3.info(f"{ultimo['Posto']} {ultimo['Nome']} ({ultimo['Dia']:02d}/{ultimo['Mês']:02d})")
                     
                    c4.markdown("**Próximo Aniversariante**")
                    c4.success(f"{proximo['Posto']} {proximo['Nome']} ({proximo['Dia']:02d}/{proximo['Mês']:02d})")
                     
                    st.markdown("---")
                     
                    # Filtros e Tabela
                    st.subheader("Pesquisar Aniversariantes")
                     
                    meses_dict = {
                        "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
                        "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12,
                        "Todos": 0
                    }
                     
                    sel_mes_nome = st.selectbox("Filtrar por Mês", list(meses_dict.keys()), index=list(meses_dict.values()).index(mes_atual))
                    sel_mes_num = meses_dict[sel_mes_nome]
                     
                    if sel_mes_num != 0:
                        df_show = df_aniversarios[df_aniversarios["Mês"] == sel_mes_num].copy()
                    else:
                        df_show = df_aniversarios.copy()
                         
                    if not df_show.empty:
                        # Formatar data para exibição
                        df_show["Data Aniversário"] = df_show.apply(lambda x: f"{x['Dia']:02d}/{x['Mês']:02d}", axis=1)
                        st.dataframe(
                            df_show.sort_values(["Mês", "Dia"])[["Posto", "Nome", "Data Aniversário"]],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info(f"Nenhum aniversariante encontrado em {sel_mes_nome}.")

        except Exception as e:
            st.error(f"Erro ao carregar aniversários: {e}")

    elif pagina == "Log / Debug":
        st.subheader("Log / Debug")
         
        # --- NEW DEBUG SECTION FOR CHECKBOXES ---
        st.markdown("### 🔍 Diagnóstico de Colunas GVI e IN")
        st.info("Use esta seção para verificar como o Python está lendo os valores das checkboxes.")
         
        cols_debug = []
        if "Gvi/GP" in df_raw.columns: cols_debug.append("Gvi/GP")
        if "IN" in df_raw.columns: cols_debug.append("IN")
         
        if cols_debug:
            st.write("Valores únicos encontrados nas colunas:")
            for col in cols_debug:
                unique_vals = df_raw[col].unique()
                st.write(f"**{col}:** {unique_vals}")
                 
            st.markdown("##### Teste da função `parse_bool`:")
            test_val = st.text_input("Digite um valor para testar se é True/False (ex: 'Sim', 'TRUE', 'x'):")
            if test_val:
                res = parse_bool(test_val)
                st.write(f"O valor '{test_val}' é considerado: **{res}**")
        else:
            st.error("Colunas Gvi/GP ou IN não encontradas na planilha.")
             
        st.markdown("---")
        st.markdown("### df_raw (dados brutos do Google Sheets)")
        st.write(f"Total de linhas em df_raw: **{len(df_raw)}**")
        st.write("Colunas disponíveis em df_raw:")
        st.write(list(df_raw.columns))
        st.write("Prévia de df_raw (primeiras 15 linhas):")
        st.dataframe(df_raw.head(15), use_container_width=True)
        st.markdown("---")
        st.markdown("### Blocos de datas detectados")
        if BLOCOS_DATAS:
            debug_blocos = []
            for idx, (c_ini, c_fim, c_mot, tipo_base) in enumerate(BLOCOS_DATAS, start=1):
                debug_blocos.append({"Bloco": idx, "Col_Inicio": c_ini, "Col_Fim": c_fim, "Col_Motivo/Curso": c_mot, "Tipo_base": tipo_base})
            st.dataframe(pd.DataFrame(debug_blocos), use_container_width=True)
        else:
            st.info("Nenhum bloco de datas detectado.")
        st.markdown("---")
        st.markdown("### df_eventos (eventos gerados)")
        st.write(f"Total de eventos em df_eventos: **{len(df_eventos)}**")
        if not df_eventos.empty:
            st.dataframe(df_eventos.head(40), use_container_width=True)
            st.write("Anos em Inicio:", df_eventos["Inicio"].dt.year.unique())
            st.write("Anos em Fim:", df_eventos["Fim"].dt.year.unique())
            st.write("Tipos registrados:", df_eventos["Tipo"].unique())
            st.write("Motivos agrupados:", df_eventos["MotivoAgrupado"].unique())
        else:
            st.info("df_eventos está vazio. Verifique se as colunas de datas estão corretamente preenchidas na planilha.")


# ============================================================
# 12. RODAPÉ
# ============================================================
st.markdown("<hr style='border-color: rgba(148, 163, 184, 0.2); margin-top:2rem;'/>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div style='text-align:center; color:#94a3b8; padding:0.5rem 0; font-size:0.85rem;'>
    Created by <strong>Klismann Freitas</strong> - Versão do painel: <strong>{SCRIPT_VERSION}</strong>
    </div>
    """,
    unsafe_allow_html=True
)
