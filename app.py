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
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Navio-Patrulha Macau",
    layout="wide",
    page_icon="logo_npamacau.png"
)

# ============================================================
# 🔒 2. SISTEMA DE LOGIN (COM DIAGNÓSTICO)
# ============================================================
def check_password():
    """Retorna True se o usuário logar com sucesso."""

    # --- BLOCO DE DIAGNÓSTICO DE ERRO ---
    if "passwords" not in st.secrets:
        st.error("🚫 Erro de Leitura das Senhas")
        
        # Modo Detetive: Mostra onde o Python está procurando
        st.markdown("### 🕵️ Diagnóstico Automático")
        pasta_atual = os.getcwd()
        st.write(f"**O App está rodando na pasta:** `{pasta_atual}`")
        
        st.write("**Conteúdo desta pasta:**")
        arquivos = os.listdir(pasta_atual)
        st.code(arquivos)
        
        if ".streamlit" in arquivos:
            st.success("✅ Pasta `.streamlit` encontrada!")
            st.write("**Conteúdo de dentro da pasta .streamlit:**")
            try:
                caminho_secrets = os.path.join(pasta_atual, ".streamlit")
                arquivos_secrets = os.listdir(caminho_secrets)
                st.code(arquivos_secrets)
                
                if "secrets.toml" in arquivos_secrets:
                    st.warning("⚠️ O arquivo `secrets.toml` existe, mas o Streamlit não leu. Pode ser erro de digitação dentro dele.")
                    st.write("Verifique se a primeira linha do arquivo é exatamente: `[passwords]`")
                else:
                    st.error("❌ A pasta existe, mas o arquivo `secrets.toml` NÃO está dentro dela.")
            except Exception as e:
                st.error(f"Erro ao tentar abrir a pasta: {e}")
        else:
            st.error("❌ A pasta `.streamlit` NÃO foi encontrada na raiz do projeto. Verifique se ela tem o PONTO no início.")
            
        st.info("Dica: A estrutura correta na barra lateral esquerda deve ser:\n\n- .streamlit\n  - secrets.toml\n- app.py")
        st.stop()
    # -------------------------------------

    def password_entered():
        if st.session_state["username"] in st.secrets["passwords"] and \
           st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.markdown("""<style>.block-container {padding-top: 5rem;}</style>""", unsafe_allow_html=True)
        st.header("🔒 Acesso Restrito - NPa Macau")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("😕 Usuário ou senha incorretos")
        return False
    return True

if not check_password():
    st.stop()

# ============================================================
# 🔓 FIM DO BLOQUEIO - O CÓDIGO DO APP CONTINUA NORMALMENTE
# ============================================================

# ============================================================
# HELPER: ECHARTS DONUT
# ============================================================
def make_echarts_donut(data_list, title):
    options = {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {"top": "5%", "left": "center", "textStyle": {"color": "#9ca3af"}},
        "series": [{
            "name": title, "type": "pie", "radius": ["40%", "70%"],
            "avoidLabelOverlap": False,
            "itemStyle": {"borderRadius": 10, "borderColor": "#fff", "borderWidth": 2},
            "label": {"show": False, "position": "center"},
            "emphasis": {"label": {"show": True, "fontSize": "24", "fontWeight": "bold", "formatter": "{b}\n{d}%"}},
            "labelLine": {"show": False}, "data": data_list,
        }],
    }
    return options

# ============================================================
# HELPER: ECHARTS LINE
# ============================================================
def make_echarts_line(x_data, y_data):
    options = {
        "xAxis": {"type": "category", "data": x_data},
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
        "xAxis": {"type": "category", "data": x_data, "axisLabel": {"interval": 0, "rotate": 30}},
        "yAxis": {"type": "value"},
        "series": [{"data": y_data, "type": "bar"}],
        "tooltip": {"trigger": "axis"}
    }
    return options

SCRIPT_VERSION = "v2.2 (Login Seguro)"
pio.templates.default = "plotly_dark"

def get_img_as_base64(file):
    try:
        with open(file, "rb") as f: data = f.read()
        return base64.b64encode(data).decode()
    except: return ""

logo_b64 = get_img_as_base64("logo_npamacau.png")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@300;400;600;700&family=Poppins:wght@400;500;600;700&display=swap');
    :root {{ --amezia-blue: #4099ff; --amezia-pink: #ff5370; --amezia-green: #2ed8b6; --amezia-orange: #ffb64d; --amezia-dark-bg: #1a2035; --amezia-dark-card: #202940; --amezia-light-bg: #f4f7f6; --amezia-light-card: #ffffff; --text-dark: #aab8c5; --text-light: #3e4b5b; }}
    * {{ font-family: 'Nunito Sans', sans-serif; }}
    h1, h2, h3, h4, h5, h6 {{ font-family: 'Poppins', sans-serif !important; font-weight: 600 !important; }}
    header[data-testid="stHeader"] {{ background-image: linear-gradient(to right, #4099ff, #73b4ff); color: white !important; height: 3.5rem !important; }}
    header[data-testid="stHeader"]::before {{ content: ""; background-image: url("data:image/png;base64,{logo_b64}"); background-size: contain; background-repeat: no-repeat; position: absolute; left: 60px; top: 50%; transform: translateY(-50%); width: 40px; height: 40px; z-index: 999; pointer-events: none; }}
    header[data-testid="stHeader"]::after {{ content: "Navio-Patrulha Macau"; position: absolute; left: 110px; top: 50%; transform: translateY(-50%); color: white; font-size: 1.2rem; font-weight: 700; font-family: 'Poppins', sans-serif; z-index: 999; pointer-events: none; }}
    @media (max-width: 600px) {{ header[data-testid="stHeader"]::after {{ content: "NPa Macau"; font-size: 1rem; left: 100px; }} }}
    header[data-testid="stHeader"] button {{ color: white !important; }}
    .block-container {{ padding-top: 4rem !important; }}
    div[data-testid="metric-container"] {{ border-radius: 5px; padding: 1.5rem; transition: all 0.3s ease-in-out; position: relative; overflow: hidden; }}
    @media (prefers-color-scheme: dark) {{ div[data-testid="metric-container"] {{ background: var(--amezia-dark-card); box-shadow: 0 4px 24px 0 rgb(34 41 47 / 10%); color: var(--text-dark); }} section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span {{ color: #aab8c5 !important; }} }}
    @media (prefers-color-scheme: light) {{ div[data-testid="metric-container"] {{ background: var(--amezia-light-card); box-shadow: 0 1px 20px 0 rgba(69,90,100,0.08); color: var(--text-light); }} }}
    div[data-testid="metric-container"]:hover {{ transform: translateY(-5px); box-shadow: 0 10px 30px -5px rgba(64, 153, 255, 0.3); }}
    section[data-testid="stSidebar"] {{ background-color: #202940; }}
    section[data-testid="stSidebar"] * {{ color: #aab8c5 !important; }}
    section[data-testid="stSidebar"] h4 {{ font-size: 1.2rem !important; font-weight: 700 !important; color: #fff !important; margin-top: 1rem; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] {{ display: flex; flex-direction: column; gap: 5px; margin-top: 10px; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {{ display: none !important; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{ padding: 10px 15px; border-radius: 0px; cursor: pointer; font-weight: 500; transition: all 0.2s ease; border-left: 3px solid transparent; margin-left: 0; background: transparent !important; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{ background: transparent !important; border-left: 3px solid var(--amezia-blue); padding-left: 18px; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {{ background: transparent !important; border-left: 3px solid var(--amezia-blue); box-shadow: none; padding-left: 18px; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover p {{ color: var(--amezia-blue) !important; }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] p {{ color: var(--amezia-blue) !important; font-weight: 700 !important; }}
    div[data-testid="stMetric"] {{ text-align: center !important; justify-content: center !important; align-items: center !important; display: flex; flex-direction: column; }}
    div[data-testid="stMetricLabel"] {{ justify-content: center !important; width: 100%; display: flex; }}
    div[data-testid="stMetricValue"] {{ justify-content: center !important; width: 100%; display: flex; }}
    .stDataFrame {{ border-radius: 5px; }}
    .agenda-card {{ padding: 15px; border-radius: 5px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid var(--amezia-blue); transition: transform 0.2s; }}
    @media (prefers-color-scheme: dark) {{ .agenda-card {{ background-color: #202940 !important; box-shadow: 0 4px 6px rgba(0,0,0,0.2); color: #ffffff !important; }} .agenda-date {{ background-color: rgba(255,255,255,0.1) !important; color: #ffffff !important; }} }}
    @media (prefers-color-scheme: light) {{ .agenda-card {{ background-color: #fff !important; box-shadow: 0 2px 10px rgba(0,0,0,0.05); color: #333 !important; }} .agenda-date {{ background-color: #f4f7f6 !important; color: #333 !important; }} }}
    .agenda-date {{ padding: 5px 10px; border-radius: 4px; font-weight: bold; font-family: monospace; }}
    </style>
    """, unsafe_allow_html=True
)

HEADER_ROW = 2
AGENDAS_OFICIAIS = {
    "Agenda Permanente": "agenda.npamacau@gmail.com",
    "Agenda Eventual": "32e9bbd3bca994bdab0b3cd648f2cb4bc13b0cf312a6a2c5a763527a5c610917@group.calendar.google.com",
    "Aniversários OM": "9f856c62f2420cd3ce5173197855b6726dd0a73d159ba801afd4eddfcac651db@group.calendar.google.com",
    "Aniversários Tripulação": "8641c7fc86973e09bbb682f8841908cc9240b25b1990f179137dfa7d2b23b2da@group.calendar.google.com",
    "Comissão": "ff1a7d8acb9ea68eed3ec9b0e279f2a91fb962e4faa9f7a3e7187fade00eb0d6@group.calendar.google.com",
    "NSD": "d7d9199712991f81e35116b9ec1ed492ac672b72b7103a3a89fb3f66ae635fb7@group.calendar.google.com"
}
SERVICOS_CONSIDERADOS = ["Oficial / Supervisor", "Contramestre 08-12", "Contramestre 04-08", "Contramestre 00-04", "Fiel de CAv"]
URL_DIAS_MAR = "https://docs.google.com/spreadsheets/d/1CEVh0EQsnINcuVP4-RbS3KgfAQNKXCwAszbqjDq8phU/edit?usp=sharing"
URL_CARDAPIO = "https://docs.google.com/spreadsheets/d/1i3veE6cj4-h9toh_DIjm8vcyz4kJ0DoKpJDrA2Xn77s/edit?usp=sharing"
URL_ANIVERSARIOS = "https://docs.google.com/spreadsheets/d/1mcQlXU_sRYwqmBCHkL3qX1GS6bivUqIGqGVVCvZLc0U/edit?usp=sharing"

def parse_bool(value) -> bool:
    if pd.isna(value) or value == "": return False
    if isinstance(value, bool): return value
    if isinstance(value, (int, float)): return value > 0
    s = str(value).strip().lower()
    if s.endswith(".0"): s = s[:-2]
    return s in ("true", "1", "sim", "yes", "y", "x", "s", "ok", "v", "checked")

def parse_aniversario_date(val):
    if pd.isna(val) or str(val).strip() == "": return pd.NaT
    s = str(val).strip().lower().replace(".", "")
    meses = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
    try:
        import re
        match = re.match(r"(\d+)([a-zç]+)", s)
        if match:
            dia, mes_str = int(match.group(1)), match.group(2)
            if mes_str in meses: return datetime((datetime.utcnow() - timedelta(hours=3)).year, meses[mes_str], dia)
    except: pass
    return pd.NaT

def parse_sheet_date(val):
    if pd.isna(val) or str(val).strip() == "": return pd.NaT
    val_str = str(val).strip()
    try:
        dt = pd.to_datetime(val_str, dayfirst=True, errors='coerce')
        if pd.notna(dt):
            if dt.year < 2000: dt = dt.replace(year=dt.year + 100)
            return dt
    except: pass
    try:
        dt = datetime.strptime(val_str, "%d/%m")
        dt = dt.replace(year=(datetime.utcnow() - timedelta(hours=3)).year)
        return pd.to_datetime(dt)
    except: pass
    return pd.NaT

@st.cache_data(ttl=600, show_spinner="Carregando dados de efetivo...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Afastamento 2026", header=HEADER_ROW, ttl="10m")
    if "Nome" in df.columns: df = df.dropna(subset=["Nome"])
    return df.reset_index(drop=True)

@st.cache_data(ttl=3600, show_spinner="Carregando aniversariantes...")
def load_aniversarios():
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(spreadsheet=URL_ANIVERSARIOS, ttl="1h")

def parse_mar_date(val, ano):
    if pd.isna(val) or str(val).strip() == "": return pd.NaT
    s_val = str(val).strip()
    try:
        dt = pd.to_datetime(s_val, dayfirst=True)
        if dt.year == 1900 and pd.notna(ano) and int(ano) > 1900: return dt.replace(year=int(ano))
        return dt
    except: pass
    if pd.notna(ano) and int(ano) > 1900:
        try: return pd.to_datetime(f"{s_val}/{int(ano)}", dayfirst=True)
        except: pass
    return pd.NaT

@st.cache_data(ttl=600, show_spinner="Carregando dados de Mar...")
def load_dias_mar():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL_DIAS_MAR, header=7, ttl="10m")
    if "TERMO DE VIAGEM" in df.columns: df = df.dropna(subset=["TERMO DE VIAGEM"])
    cols_desejadas = ["TERMO DE VIAGEM", "DATA INÍCIO", "DATA TÉRMINO", "ANO", "DIAS DE MAR", "MILHAS NAVEGADAS", "SOMA"]
    df = df[[c for c in cols_desejadas if c in df.columns]]
    for col in ["DIAS DE MAR", "MILHAS NAVEGADAS"]:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if "ANO" in df.columns: df["ANO"] = pd.to_numeric(df["ANO"], errors='coerce').fillna(0).astype(int)
    for col in ["DATA INÍCIO", "DATA TÉRMINO"]:
        if col in df.columns and "ANO" in df.columns: df[col] = df.apply(lambda row: parse_mar_date(row[col], row["ANO"]), axis=1)
        elif col in df.columns: df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
    return df

@st.cache_data(ttl=3600, show_spinner="Carregando cardápio...")
def load_cardapio():
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(spreadsheet=URL_CARDAPIO, header=None, ttl="1h")

@st.cache_data(ttl=300)
def load_calendar_events(calendar_id: str) -> pd.DataFrame:
    try:
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/calendar.readonly"])
        service = build("calendar", "v3", credentials=creds)
        now = datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(calendarId=calendar_id, timeMin=now, maxResults=30, singleEvents=True, orderBy="startTime").execute()
        events = events_result.get("items", [])
        data = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "Sem título")
            try:
                dt_obj = pd.to_datetime(start)
                fmt = "%d/%m %H:%M" if "T" in start else "%d/%m"
                data_fmt = dt_obj.strftime(fmt)
            except: data_fmt = start
            data.append({"Data": data_fmt, "Evento": summary})
        return pd.DataFrame(data)
    except: return pd.DataFrame()

try: df_raw = load_data()
except Exception as e: st.error(f"Erro de conexão principal: {e}"); st.stop()

def descobrir_blocos_datas(df: pd.DataFrame):
    cols, blocos = list(df.columns), []
    for i, nome_col in enumerate(cols):
        n = str(nome_col)
        if not (n.startswith("Início") or n.startswith("Inicio")): continue
        j = None
        for idx2 in range(i + 1, len(cols)):
            n2 = str(cols[idx2])
            if n2.startswith("Fim") or n2.startswith("FIm"): j = idx2; break
        if j is None: continue
        k, tipo_base = None, "Férias"
        for idx3 in range(j + 1, min(j + 4, len(cols))):
            n3 = str(cols[idx3])
            if "Motivo" in n3: k, tipo_base = idx3, "Outros"; break
            if "Curso" in n3: k, tipo_base = idx3, "Curso"; break
        blocos.append((cols[i], cols[j], cols[k] if k is not None else None, tipo_base))
    return blocos

BLOCOS_DATAS = descobrir_blocos_datas(df_raw)

@st.cache_data(ttl=600)
def construir_eventos(df_raw: pd.DataFrame, blocos) -> pd.DataFrame:
    eventos = []
    for _, row in df_raw.iterrows():
        posto, nome, escala = row.get("Posto", ""), row.get("Nome", ""), row.get("Serviço", "")
        eqman_val = row.get("EqMan", "")
        eqman = str(eqman_val) if pd.notna(eqman_val) and str(eqman_val) != "-" else "Não"
        militar_info = {"Posto": posto, "Nome": nome, "Escala": escala, "EqMan": eqman, "GVI": parse_bool(row.get("Gvi/GP", "")), "IN": parse_bool(row.get("IN", ""))}
        for col_ini, col_fim, col_mot, tipo_base in blocos:
            ini, fim = parse_sheet_date(row.get(col_ini)), parse_sheet_date(row.get(col_fim))
            if pd.isna(ini) or pd.isna(fim): continue
            if fim < ini: ini, fim = fim, ini
            dur = (fim - ini).days + 1
            if dur < 1 or dur > 365 * 2: continue
            if tipo_base == "Férias": motivo_real, tipo_final = "Férias", "Férias"
            else:
                motivo_texto = str(row.get(col_mot, "")).strip()
                tipo_final = "Curso" if tipo_base == "Curso" else "Outros"
                motivo_real = motivo_texto if motivo_texto and "nan" not in motivo_texto.lower() else ("CURSO (não especificado)" if tipo_final == "Curso" else "OUTROS")
            motivo_agr = "Férias" if tipo_final == "Férias" else ("Curso" if tipo_final == "Curso" else motivo_real)
            eventos.append({**militar_info, "Inicio": ini, "Fim": fim, "Duracao_dias": dur, "Motivo": motivo_real, "MotivoAgrupado": motivo_agr, "Tipo": tipo_final})
    return pd.DataFrame(eventos)

df_eventos = construir_eventos(df_raw, BLOCOS_DATAS)

@st.cache_data(ttl=600)
def expandir_eventos_por_dia(df_eventos: pd.DataFrame) -> pd.DataFrame:
    if df_eventos.empty: return pd.DataFrame()
    linhas = []
    for _, ev in df_eventos.iterrows():
        if pd.isna(ev["Inicio"]) or pd.isna(ev["Fim"]): continue
        for data in pd.date_range(ev["Inicio"], ev["Fim"]):
            linhas.append({"Data": data, "Posto": ev["Posto"], "Nome": ev["Nome"], "Escala": ev["Escala"], "EqMan": ev["EqMan"], "GVI": ev["GVI"], "IN": ev["IN"], "Motivo": ev["Motivo"], "MotivoAgrupado": ev["MotivoAgrupado"], "Tipo": ev["Tipo"]})
    return pd.DataFrame(linhas)

df_dias = expandir_eventos_por_dia(df_eventos)

def get_status_em_data(row, data_ref, blocos_cols):
    for col_ini, col_fim, col_mot, tipo_base in blocos_cols:
        ini, fim = parse_sheet_date(row.get(col_ini)), parse_sheet_date(row.get(col_fim))
        if pd.isna(ini) or pd.isna(fim): continue
        if ini <= data_ref <= fim:
            return str(row[col_mot]) if col_mot and col_mot in row.index and not pd.isna(row[col_mot]) else tipo_base
    return "Presente"

def filtrar_tripulacao(df: pd.DataFrame, eqman: bool, nav: bool, gvi: bool) -> pd.DataFrame:
    res = df.copy()
    if eqman and "EqMan" in res.columns: res = res[(res["EqMan"].notna()) & (res["EqMan"].astype(str) != "Não") & (res["EqMan"].astype(str) != "-")]
    if nav and "IN" in res.columns: res = res[res["IN"].apply(parse_bool)]
    if gvi and "Gvi/GP" in res.columns: res = res[res["Gvi/GP"].apply(parse_bool)]
    return res

def filtrar_eventos(df: pd.DataFrame, eqman: bool, nav: bool, gvi: bool) -> pd.DataFrame:
    res = df.copy()
    if eqman: res = res[res["EqMan"] != "Não"]
    if nav: res = res[res["IN"] == True]
    if gvi: res = res[res["GVI"] == True]
    return res

def filtrar_dias(df: pd.DataFrame, eqman: bool, nav: bool, gvi: bool) -> pd.DataFrame:
    res = df.copy()
    if eqman: res = res[res["EqMan"] != "Não"]
    if nav: res = res[res["IN"] == True]
    if gvi: res = res[res["GVI"] == True]
    return res

def update_fig_layout(fig, title=None):
    layout_args = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(family="'Nunito Sans', sans-serif", size=12), margin=dict(t=60, b=20, l=20, r=20), colorway=AMEZIA_COLORS)
    if title: layout_args["title"] = title
    fig.update_layout(**layout_args)
    return fig

st.sidebar.markdown("## HOME")
def get_svg_as_base64(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f: return base64.b64encode(f.read().encode("utf-8")).decode("utf-8")
    except: return ""

ICON_MAP = {"Presentes": "presentes.svg", "Ausentes": "ausentes.svg", "Cardápio": "cardapio.svg", "Dias de Mar": "mar2.svg", "Aniversários": "aniversario.svg", "Agenda do Navio": "agenda.svg", "Linha do Tempo": "linha_tempo.svg", "Equipes Operativas": "equipe_operativa.svg", "Estatísticas & Análises": "analise.svg", "Férias": "icons8-sun-50.svg", "Cursos": "cursos.svg", "Tabela de Serviço": "icons8-tick-box-50.svg", "Log / Debug": "log.svg"}
css_icons = ""
folder_path = os.path.join(os.path.dirname(__file__), "assets")
options = list(ICON_MAP.keys())
for i, option in enumerate(options):
    icon_filename = ICON_MAP[option] if ICON_MAP[option].endswith(".svg") else ICON_MAP[option] + ".svg"
    b64 = get_svg_as_base64(os.path.join(folder_path, icon_filename))
    if b64:
        css_icons += f"""div[role="radiogroup"] > label:nth-child({i+1}) [data-testid="stMarkdownContainer"] > p {{ display: flex; align-items: center; }} div[role="radiogroup"] > label:nth-child({i+1}) [data-testid="stMarkdownContainer"] > p::before {{ content: ""; display: inline-block; width: 24px; height: 24px; margin-right: 10px; background-color: currentColor; -webkit-mask-image: url('data:image/svg+xml;base64,{b64}'); mask-image: url('data:image/svg+xml;base64,{b64}'); -webkit-mask-size: contain; mask-size: contain; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat; -webkit-mask-position: center; mask-position: center; }}"""
if css_icons: st.markdown(f"<style>{css_icons}</style>", unsafe_allow_html=True)

with st.sidebar.container():
    pagina = st.radio(label="Seções", options=options, index=0, label_visibility="collapsed", key="pagina_radio")

def exibir_metricas_globais(data_referencia):
    hoje_ref = pd.to_datetime(data_referencia)
    ausentes = df_eventos[(df_eventos["Inicio"] <= hoje_ref) & (df_eventos["Fim"] >= hoje_ref)] if not df_eventos.empty else pd.DataFrame()
    total = len(df_raw)
    total_aus = len(ausentes["Nome"].unique()) if not ausentes.empty else 0
    total_pres = total - total_aus
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Efetivo Total", total); c2.metric("A Bordo (global)", total_pres); c3.metric("Ausentes (global)", total_aus, delta_color="inverse"); c4.metric("Prontidão (global)", f"{(total_pres/total*100 if total>0 else 0):.1f}%")

hoje_padrao = datetime.today()
if pagina == "Presentes":
    st.subheader("Presentes a bordo")
    metrics_placeholder = st.container()
    table_placeholder = st.container()
    st.markdown("---")
    st.markdown("##### Filtros & Data")
    c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.5, 2])
    f_eqman, f_in, f_gvi = c1.checkbox("Apenas EqMan"), c2.checkbox("Apenas IN"), c3.checkbox("Apenas GVI/GP")
    hoje = pd.to_datetime(c4.date_input("Data de Referência", hoje_padrao, format="DD/MM/YYYY"))
    with metrics_placeholder: exibir_metricas_globais(hoje); st.markdown("---")
    with table_placeholder:
        df_trip = filtrar_tripulacao(df_raw, f_eqman, f_in, f_gvi)
        ausentes = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)] if not df_eventos.empty else pd.DataFrame()
        ausentes = filtrar_eventos(ausentes, f_eqman, f_in, f_gvi)
        presentes = df_trip[~df_trip["Nome"].isin(set(ausentes["Nome"].unique()))].copy() if not ausentes.empty else df_trip.copy()
        st.markdown(f"Total de presentes (visão filtrada): **{len(presentes)}**")
        if presentes.empty: st.info("Nenhum militar presente.")
        else:
            tabela = presentes[["Posto", "Nome", "Serviço", "EqMan", "Gvi/GP", "IN"]].copy()
            for col in ["Gvi/GP", "IN"]: 
                if col in tabela.columns: tabela[col] = tabela[col].apply(lambda v: "Sim" if parse_bool(v) else "Não")
            if "Gvi/GP" in tabela.columns: tabela = tabela.drop(columns=["Gvi/GP"])
            st.dataframe(tabela, use_container_width=True, hide_index=True)
        st.markdown("##### Prontidão (visão filtrada)")
        if len(df_trip) > 0:
            st_echarts(options=make_echarts_donut([{"value": len(presentes), "name": "Presentes"}, {"value": len(df_trip)-len(presentes), "name": "Ausentes"}], "Prontidão"), height="500px")
        else: st.info("Sem efetivo.")

elif pagina == "Ausentes":
    st.subheader("Ausentes por dia")
    hoje = pd.to_datetime(st.date_input("Data de Referência", hoje_padrao, format="DD/MM/YYYY"))
    c1, c2, c3 = st.columns(3)
    f_eqman, f_in, f_gvi = c1.checkbox("Apenas EqMan", key="a1"), c2.checkbox("Apenas IN", key="a2"), c3.checkbox("Apenas GVI/GP", key="a3")
    if df_eventos.empty: st.info("Sem eventos.")
    else:
        ausentes = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
        ausentes = filtrar_eventos(ausentes, f_eqman, f_in, f_gvi)
        if ausentes.empty: st.success("Todo o efetivo a bordo.")
        else:
            ausentes["Motivo"] = ausentes.apply(lambda r: "Férias" if r["Tipo"] == "Férias" else ("Curso" if r["Tipo"] == "Curso" else str(r["Motivo"])), axis=1)
            show = ausentes[["Posto", "Nome", "Motivo", "Fim"]].copy()
            show["Retorno"] = show["Fim"].dt.strftime("%d/%m/%Y")
            st.dataframe(show.drop(columns=["Fim"]), use_container_width=True, hide_index=True)
    st.markdown("---")
    if not df_dias.empty:
        dias_filt = filtrar_dias(df_dias, f_eqman, f_in, f_gvi)
        if not dias_filt.empty:
            dias_filt["Mes"] = dias_filt["Data"].dt.to_period("M").dt.to_timestamp()
            aus_mes = dias_filt[["Mes", "Nome"]].drop_duplicates().groupby("Mes")["Nome"].nunique().reset_index(name="Militares")
            st.markdown("##### Ausentes por mês (Geral)")
            st_echarts(options=make_echarts_line(aus_mes["Mes"].dt.strftime("%b/%Y").tolist(), aus_mes["Militares"].tolist()), height="400px")

elif pagina == "Dias de Mar":
    st.subheader("Dias de Mar e Milhas Navegadas")
    try:
        df_mar = load_dias_mar()
        if df_mar.empty: st.info("Planilha vazia.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            df_ano = df_mar.groupby("ANO")[["DIAS DE MAR", "MILHAS NAVEGADAS"]].sum().reset_index()
            c1.metric("Total Dias", f"{df_mar['DIAS DE MAR'].sum():,.1f}"); c2.metric("Total Milhas", f"{df_mar['MILHAS NAVEGADAS'].sum():,.0f}")
            c3.metric("Média Dias/Ano", f"{df_ano['DIAS DE MAR'].mean():,.1f}"); c4.metric("Média Milhas/Ano", f"{df_ano['MILHAS NAVEGADAS'].mean():,.0f}")
            st.markdown("---"); st.markdown("##### Dias de Mar por Ano")
            st_echarts(options=make_echarts_line(df_ano["ANO"].astype(str).tolist(), df_ano["DIAS DE MAR"].tolist()), height="400px")
            st.markdown("---"); st.subheader("Detalhamento Mensal")
            anos = sorted(df_mar["ANO"].unique().astype(int), reverse=True)
            if anos:
                sel_ano = st.selectbox("Selecione o Ano", anos)
                df_sel = df_mar[df_mar["ANO"] == sel_ano].copy()
                if "DATA INÍCIO" in df_sel.columns:
                    df_sel["Mês_Num"] = df_sel["DATA INÍCIO"].dt.month
                    df_mes = df_sel.groupby("Mês_Num")["DIAS DE MAR"].sum().reset_index()
                    todos = pd.DataFrame({'Mês_Num': range(1, 13)})
                    final = pd.merge(todos, df_mes, on='Mês_Num', how='left').fillna(0)
                    mapa = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
                    final["Mês"] = final["Mês_Num"].map(mapa)
                    st.markdown(f"##### Dias de Mar em {sel_ano}")
                    st_echarts(options=make_echarts_line(final["Mês"].tolist(), final["DIAS DE MAR"].tolist()), height="400px")
                    with st.expander("Ver dados brutos"): st.dataframe(df_sel[["TERMO DE VIAGEM", "DATA INÍCIO", "DATA TÉRMINO", "DIAS DE MAR", "MILHAS NAVEGADAS"]], use_container_width=True)
    except Exception as e: st.error(f"Erro: {e}")

else:
    hoje = pd.to_datetime(hoje_padrao)
    if pagina == "Agenda do Navio":
        st.subheader("Agenda do Navio")
        c1, c2 = st.columns([3, 1])
        nome = c1.selectbox("Selecione a Agenda:", list(AGENDAS_OFICIAIS.keys()))
        if c2.button("Atualizar"): load_calendar_events.clear(); st.rerun()
        df = load_calendar_events(AGENDAS_OFICIAIS[nome])
        if df.empty: st.info("Nenhum evento.")
        else: 
            st.markdown("---")
            for _, r in df.iterrows(): st.markdown(f"""<div class="agenda-card"><div style="font-weight: 600;">{r['Evento']}</div><div class="agenda-date">{r['Data']}</div></div>""", unsafe_allow_html=True)
    
    elif pagina == "Linha do Tempo":
        st.subheader("Planejamento Anual")
        if df_eventos.empty: st.info("Sem dados.")
        else:
            df_g = df_eventos.copy()
            df_g["Nome"] = pd.Categorical(df_g["Nome"], categories=df_raw["Nome"].unique().tolist(), ordered=True)
            df_g = df_g.sort_values("Nome")
            fig = px.timeline(df_g, x_start="Inicio", x_end="Fim", y="Nome", color="MotivoAgrupado", color_discrete_sequence=AMEZIA_COLORS)
            fig.update_yaxes(autorange="reversed")
            fig.add_vline(x=hoje, line_width=2, line_dash="dash", line_color="#ff5370")
            update_fig_layout(fig, "Cronograma")
            st.plotly_chart(fig, use_container_width=True)

    elif pagina == "Equipes Operativas":
        st.subheader("Equipes Operativas")
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown("### GVI/GP"); df = df_raw[df_raw["Gvi/GP"].apply(parse_bool)]; st.dataframe(df[["Posto", "Nome"]], hide_index=True); st.write(f"Total: {len(df)}")
        with c2: st.markdown("### Inspetores"); df = df_raw[df_raw["IN"].apply(parse_bool)]; st.dataframe(df[["Posto", "Nome"]], hide_index=True); st.write(f"Total: {len(df)}")
        with c3: st.markdown("### EqMan"); df = df_raw[(df_raw["EqMan"].notna()) & (df_raw["EqMan"]!="Não") & (df_raw["EqMan"]!="-")]; st.dataframe(df[["Posto", "Nome", "EqMan"]], hide_index=True); st.write(f"Total: {len(df)}")

    elif pagina == "Estatísticas & Análises":
        st.subheader("Visão Analítica")
        if df_eventos.empty: st.write("Sem dados.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Dias ausência (total)", int(df_eventos["Duracao_dias"].sum()))
            c2.metric("Média dias/militar", f"{df_eventos.groupby('Nome')['Duracao_dias'].sum().mean():.1f}")
            c3.metric("Média férias/militar", f"{(df_eventos[df_eventos['Tipo']=='Férias'].groupby('Nome')['Duracao_dias'].sum().mean() if not df_eventos[df_eventos['Tipo']=='Férias'].empty else 0):.1f}")
            st.markdown("---")
            motivos = df_eventos.groupby("MotivoAgrupado")["Duracao_dias"].sum().reset_index()
            st_echarts(options=make_echarts_donut([{"value": r["Duracao_dias"], "name": r["MotivoAgrupado"]} for _, r in motivos.iterrows()], "Motivos"), height="600px")

    elif pagina == "Férias":
        st.subheader("Férias")
        if not df_eventos.empty and "%DG" in df_raw.columns:
            media = df_raw["%DG"].mean()
            pg = media * 100 if media <= 1 else media
            st.markdown("### % Gozado")
            st_echarts(options=make_echarts_donut([{"value": round(pg, 1), "name": "Gozado"}, {"value": round(max(0, 100-pg), 1), "name": "Não"}], "Férias"), height="400px")
        st.markdown("---")
        df_fer = df_eventos[df_eventos["Tipo"]=="Férias"].copy()
        if df_fer.empty: st.info("Sem férias.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                df_raw["PN"] = df_raw["Posto"].astype(str) + " " + df_raw["Nome"].astype(str)
                mil = st.selectbox("Militar", ["..."] + sorted(df_raw["PN"].unique()))
                if mil != "...":
                    df_fer["PN"] = df_fer["Posto"].astype(str) + " " + df_fer["Nome"].astype(str)
                    res = df_fer[df_fer["PN"]==mil].copy()
                    if not res.empty:
                        res["Inicio"] = res["Inicio"].dt.strftime("%d/%m")
                        res["Fim"] = res["Fim"].dt.strftime("%d/%m")
                        st.dataframe(res[["Inicio", "Fim", "Duracao_dias"]], hide_index=True)
                    else: st.info("Sem férias cadastradas.")
            with c2:
                meses = {"Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12}
                mes_n = st.selectbox("Mês", list(meses.keys()), index=datetime.now().month-1)
                ano = st.number_input("Ano", value=datetime.now().year)
                ini_m = datetime(ano, meses[mes_n], 1)
                import calendar
                fim_m = datetime(ano, meses[mes_n], calendar.monthrange(ano, meses[mes_n])[1])
                res = df_fer[(df_fer["Inicio"] <= fim_m) & (df_fer["Fim"] >= ini_m)].copy()
                if not res.empty:
                    res["Inicio"] = res["Inicio"].dt.strftime("%d/%m")
                    res["Fim"] = res["Fim"].dt.strftime("%d/%m")
                    st.dataframe(res[["Posto", "Nome", "Inicio", "Fim"]], hide_index=True)
                else: st.info("Ninguém de férias.")

    elif pagina == "Cursos":
        st.subheader("Cursos")
        if df_eventos.empty: st.info("Sem cursos.")
        else:
            cursos = df_eventos[df_eventos["Tipo"]=="Curso"].copy()
            real = cursos[cursos["Fim"] < hoje].copy()
            insc = cursos[cursos["Fim"] >= hoje].copy()
            c1, c2 = st.columns(2)
            with c1: 
                st.markdown("### Realizados")
                if not real.empty: 
                    real["Fim"] = real["Fim"].dt.strftime("%d/%m")
                    st.dataframe(real[["Posto", "Nome", "Motivo", "Fim"]], hide_index=True)
                else: st.info("Nenhum.")
            with c2: 
                st.markdown("### Em andamento")
                if not insc.empty: 
                    insc["Inicio"] = insc["Inicio"].dt.strftime("%d/%m")
                    st.dataframe(insc[["Posto", "Nome", "Motivo", "Inicio"]], hide_index=True)
                else: st.info("Nenhum.")

    elif pagina == "Tabela de Serviço":
        st.subheader("Tabela de Serviço")
        dt = pd.to_datetime(st.date_input("Data Ref.", datetime.now()))
        col_tgt = next((c for c in ["Escala", "Serviço", "Função"] if c in df_raw.columns), "Posto/Grad")
        data = []
        for srv in SERVICOS_CONSIDERADOS:
            ppl = df_raw[df_raw[col_tgt].astype(str).str.contains(srv, case=False, regex=False)]
            if ppl.empty: ppl = df_raw[df_raw[col_tgt].astype(str)==srv]
            tot = len(ppl)
            aus = sum(1 for _, p in ppl.iterrows() if get_status_em_data(p, dt, BLOCOS_DATAS) != "Presente")
            disp = max(0, tot - aus)
            data.append({"Serviço": srv, "Escala": f"{max(0, disp-1)}x1"})
        def color(v): return "color: #ff5370" if "0x1" in v or "1x1" in v else ("color: #ffb64d" if "2x1" in v else "color: #2ed8b6")
        st.dataframe(pd.DataFrame(data).style.map(color, subset=["Escala"]), hide_index=True)

    elif pagina == "Cardápio":
        st.subheader("Cardápio")
        df = load_cardapio()
        if df.empty: st.info("Erro ao carregar.")
        else:
            dates = df.iloc[1, 1:9].values
            meals = {"Café": df.iloc[3, 1:9].values, "Almoço": df.iloc[4, 1:9].values, "Jantar": df.iloc[5, 1:9].values, "Ceia": df.iloc[6, 1:9].values}
            data = []
            for i, d in enumerate(dates):
                try: dt = pd.to_datetime(str(d).strip(), dayfirst=True, errors='coerce')
                except: dt = pd.NaT
                row = {"Data": dt, "Dia": f"{dt.day}/{dt.month}" if pd.notna(dt) else str(d)}
                for k, v in meals.items(): row[k] = v[i] if i < len(v) else ""
                data.append(row)
            menu = pd.DataFrame(data)
            hoje_menu = menu[menu["Data"].dt.date == datetime.now().date()]
            if not hoje_menu.empty:
                r = hoje_menu.iloc[0]
                c1, c2, c3, c4 = st.columns(4)
                c1.info(f"**Café:** {r['Café']}"); c2.success(f"**Almoço:** {r['Almoço']}"); c3.warning(f"**Jantar:** {r['Jantar']}"); c4.error(f"**Ceia:** {r['Ceia']}")
            else: st.info("Sem cardápio para hoje.")
            st.markdown("---")
            st.dataframe(menu[["Dia", "Café", "Almoço", "Jantar", "Ceia"]], hide_index=True)

    elif pagina == "Aniversários":
        st.subheader("Aniversários")
        df = load_aniversarios()
        if df.empty: st.info("Erro.")
        else:
            lst = []
            for _, r in df.iterrows():
                try: 
                    dt = parse_aniversario_date(r.iloc[7])
                    if pd.notna(dt): lst.append({"Posto": r.iloc[1], "Nome": r.iloc[4], "Data": dt, "Mês": dt.month, "Dia": dt.day})
                except: continue
            df_n = pd.DataFrame(lst)
            if df_n.empty: st.info("Sem dados.")
            else:
                hoje = datetime.now()
                mes = df_n[df_n["Mês"]==hoje.month]
                dia = df_n[(df_n["Mês"]==hoje.month) & (df_n["Dia"]==hoje.day)]
                st.metric("Aniversariantes Mês", len(mes))
                if not dia.empty: st.success(f"Hoje: {', '.join([r['Posto']+' '+r['Nome'] for _, r in dia.iterrows()])}")
                else: st.info("Ninguém hoje.")
                st.markdown("---")
                m_sel = st.selectbox("Mês", list({"Jan":1,"Fev":2,"Mar":3,"Abr":4,"Mai":5,"Jun":6,"Jul":7,"Ago":8,"Set":9,"Out":10,"Nov":11,"Dez":12}.keys()))
                res = df_n[df_n["Mês"]=={"Jan":1,"Fev":2,"Mar":3,"Abr":4,"Mai":5,"Jun":6,"Jul":7,"Ago":8,"Set":9,"Out":10,"Nov":11,"Dez":12}[m_sel]]
                if not res.empty: 
                    res["Dia"] = res["Dia"].apply(lambda x: f"{x:02d}")
                    st.dataframe(res[["Dia", "Posto", "Nome"]].sort_values("Dia"), hide_index=True)
                else: st.info("Ninguém.")

    elif pagina == "Log / Debug":
        st.subheader("Debug")
        st.write("Dados brutos:", df_raw.head())

st.markdown("<hr/><div style='text-align:center'>NPa Macau</div>", unsafe_allow_html=True)
