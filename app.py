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
# 1. CONFIGURAÇÃO DA PÁGINA (MOVIDO PARA O TOPO)
# ============================================================
st.set_page_config(
    page_title="Navio-Patrulha Macau",
    layout="wide",
    page_icon="logo_npamacau.png"
)

# ============================================================
# 🔒 2. SISTEMA DE LOGIN (MODERN MINIMALIST)
# ============================================================

# --- AUTH HELPERS (GLOBAL SCOPE) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1DDQ1eObEd5p2kfI4uCTpQvTT54TjpQtEeWNVAwQ0400/edit?usp=sharing"

def get_img_as_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

def normalize_nip(nip):
    """Remove pontos e espaços do NIP para comparação."""
    return str(nip).replace(".", "").replace(" ", "").strip()

def get_users_data():
    """Busca os dados dos usuários na planilha."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # TTL de 0 para sempre buscar dados frescos ao logar
        return conn.read(spreadsheet=SHEET_URL, ttl=0)
    except Exception as e:
        st.error(f"Erro ao ler dados da planilha: {e}")
        st.stop()

def update_password(nip, new_password):
    """Atualiza a senha do usuário na planilha."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = get_users_data()
        # Normaliza a coluna de NIP para garantir o match
        df['NIP_NORM'] = df.iloc[:, 3].apply(normalize_nip) # Coluna D é índice 3
        
        # Encontra o índice da linha
        user_idx = df[df['NIP_NORM'] == normalize_nip(nip)].index
        
        if not user_idx.empty:
            # Atualiza a senha (Coluna E é índice 4)
            df.iloc[user_idx[0], 4] = new_password
            
            # Remove a coluna temporária antes de salvar
            df_to_save = df.drop(columns=['NIP_NORM'])
            
            conn.update(spreadsheet=SHEET_URL, data=df_to_save)
            return True
        return False
    except Exception as e:
        st.error(f"Erro ao atualizar senha: {e}")
        return False

def check_password():
    """Retorna True se o usuário logar com sucesso."""

    # --- 1. CONFIGURAÇÃO E CONEXÃO ---
    # (SHEET_URL e Helpers agora estão no escopo global)
    
    # --- 3. LÓGICA DE LOGIN ---

    # --- 3. LÓGICA DE LOGIN ---
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    if not st.session_state["password_correct"]:
        
        # --- CSS (MANTIDO DO DESIGN ANTERIOR) ---
        st.markdown(
            """
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@1,400;1,600&display=swap');

            /* Global Reset & Font */
            * {
                font-family: 'Inter', sans-serif;
            }

            /* App Background - Naval Dark */
            .stApp {
                background-color: #f1f5f9;
                background-image: radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 80%);
                background-attachment: fixed;
                background-size: cover;
            }

            /* Login Card - Target the Form */
            [data-testid="stForm"] {
                background-color: rgba(255, 255, 255, 0.8) !important; /* 80% Translucent */
                backdrop-filter: blur(24px);
                -webkit-backdrop-filter: blur(24px);
                border-radius: 20px;
                padding: 48px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.6);
                text-align: center;
            }

            /* Logo Effect */
            [data-testid="stImage"] img {
                filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.3)); /* Dark shadow */
                transition: transform 0.3s ease;
            }
            [data-testid="stImage"] img:hover {
                transform: scale(1.05);
            }

            /* Title & Text */
            .login-title {
                font-family: 'Inter', sans-serif;
                font-size: 1.5rem;
                font-weight: 700;
                color: #0f172a;
                margin-top: 10px;
                margin-bottom: 2px; /* Reduced spacing */
                letter-spacing: -0.02em;
                text-align: center;
            }
            .login-motto {
                font-family: 'Playfair Display', serif;
                font-size: 1.1rem;
                color: #334155; /* Slightly darker slate */
                font-weight: 600;
                margin-bottom: 32px;
                text-align: center;
                font-style: italic;
                letter-spacing: 0.02em;
            }

            /* Inputs */
            .stTextInput input {
                background-color: #f8fafc !important;
                border: 1px solid #e2e8f0 !important;
                color: #334155 !important;
                border-radius: 8px;
                padding: 0 16px !important;
                font-size: 0.95rem;
                height: 50px !important;
                line-height: 50px !important;
                transition: all 0.2s;
            }
            .stTextInput input:focus {
                background-color: #f8fafc !important; /* Mantém a mesma cor de fundo */
                border-color: #e2e8f0 !important;     /* Mantém a mesma cor de borda */
                box-shadow: none !important;
                outline: none !important;
                caret-color: #0f172a !important;
            }
            /* Target parent wrapper to override Streamlit defaults */
            div[data-baseweb="input"]:focus-within {
                border-color: #e2e8f0 !important;
                box-shadow: none !important;
                background-color: #f8fafc !important;
            }
            .stTextInput label {
                color: #475569 !important;
                font-weight: 600;
                font-size: 0.85rem;
                margin-bottom: 6px;
            }

            /* Button Styling - Target ONLY the Submit Button Container */
            div[data-testid="stForm"] .stButton button {
                background: #2563eb !important; /* Vibrant Blue */
                color: white !important;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 0.95rem;
                letter-spacing: 0.02em;
                transition: all 0.2s ease;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
                
                /* Exact sizing to match inputs */
                height: 50px !important;
                padding: 0 !important;
                line-height: 50px !important;
                display: flex;
                align-items: center;
                justify-content: center;
                width: 100% !important;
                margin-top: 8px;
            }
            div[data-testid="stForm"] .stButton button:hover {
                background: #1d4ed8 !important; /* Darker Blue */
                transform: translateY(-1px);
                box-shadow: 0 8px 16px rgba(37, 99, 235, 0.3);
            }

            /* Hide Streamlit Elements */
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .block-container {padding-top: 5rem !important;}
            
            /* Footer/Contact */
            .contact-info {
                margin-top: 24px;
                color: #94a3b8;
                font-size: 0.75rem;
                text-align: center;
            }
            </style>
            """, 
            unsafe_allow_html=True
        )

        # Ajuste das colunas para centralizar o card
        # Como o layout agora é WIDE desde o início, usamos colunas laterais maiores para centralizar
        # [3, 2, 3] -> O meio ocupa 2/8 = 25% da tela. Em 1920px ~= 480px.
        col1, col2, col3 = st.columns([3, 2, 3])
        
        with col2:
            
            # Se estiver no fluxo de troca de senha
            if st.session_state.get("change_password_mode"):
                with st.form("change_password_form"):
                    st.markdown("### 🔒 Criar Nova Senha")
                    st.info("É seu primeiro acesso ou sua senha expirou. Crie uma nova senha.")
                    
                    new_pass = st.text_input("Nova Senha", type="password")
                    confirm_pass = st.text_input("Confirmar Nova Senha", type="password")
                    
                    if st.form_submit_button("DEFINIR SENHA", use_container_width=True):
                        if new_pass != confirm_pass:
                            st.error("As senhas não coincidem.")
                        elif len(new_pass) < 6:
                            st.error("A senha deve ter pelo menos 6 caracteres.")
                        elif new_pass == "mudar123":
                            st.error("Você não pode usar a senha padrão.")
                        else:
                            # Tenta atualizar
                            if update_password(st.session_state["temp_nip"], new_pass):
                                st.success("Senha atualizada com sucesso! Faça login novamente.")
                                st.session_state["change_password_mode"] = False
                                del st.session_state["temp_nip"]
                                # Rerun para voltar ao login
                                st.rerun()
                            else:
                                st.error("Erro ao atualizar senha. Tente novamente.")

            else:
                # Fluxo Normal de Login
                with st.form("login_form"):
                    # 1. IMAGEM
                    import os
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    img_path = os.path.join(current_dir, "logo_npamacau.png")
                    
                    # 1. IMAGEM (Centralizada Mobile-First)
                    import os
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    img_path = os.path.join(current_dir, "logo_npamacau.png")
                    
                    # Usa container flex para centralizar
                    if os.path.exists(img_path):
                        st.markdown(
                            f"""
                            <div style="display: flex; justify-content: center; margin-bottom: 1rem;">
                                <img src="data:image/png;base64,{get_img_as_base64(img_path)}" width="160" style="max-width: 100%; height: auto;">
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown("""<div style="text-align: center; font-size: 80px; color: #1e293b;">⚓</div>""", unsafe_allow_html=True)

                    # 2. TÍTULOS
                    st.markdown(
                        """
                        <div class="login-title">NAVIO-PATRULHA MACAU</div>
                        <div class="login-motto">"O nosso repouso é a batalha"</div>
                        """, 
                        unsafe_allow_html=True
                    )

                    username_input = st.text_input("NIP (com ou sem pontos)", key="username_input")
                    password_input = st.text_input("Senha", type="password", key="password_input")
                    
                    submit_clicked = st.form_submit_button("ENTRAR", use_container_width=True)
                
                if submit_clicked:
                    df = get_users_data()
                    
                    # Normaliza input e coluna do banco
                    input_nip_norm = normalize_nip(username_input)
                    
                    # Assume que NIP é a 4ª coluna (índice 3) e Senha a 5ª (índice 4)
                    # Ajuste conforme a planilha real se necessário
                    try:
                        # Cria coluna temporária para busca
                        df['NIP_NORM'] = df.iloc[:, 3].apply(normalize_nip)
                        
                        user_row = df[df['NIP_NORM'] == input_nip_norm]
                        
                        if not user_row.empty:
                            stored_password = str(user_row.iloc[0, 4]).strip()
                            
                            if password_input == stored_password:
                                # Verifica se é senha padrão
                                if stored_password == "mudar123":
                                    st.session_state["change_password_mode"] = True
                                    st.session_state["temp_nip"] = username_input
                                    st.rerun()
                                else:
                                    st.session_state["password_correct"] = True
                                    st.session_state["username"] = username_input # Guarda o NIP logado
                                    
                                    # Captura Posto (col B -> index 1) e Nome (col C -> index 2) para saudação
                                    # Ajuste os índices conforme a estrutura real da planilha se necessário
                                    try:
                                        st.session_state["user_posto"] = str(user_row.iloc[0, 1]).strip()
                                        st.session_state["user_nome"] = str(user_row.iloc[0, 2]).strip()
                                    except:
                                        pass
                                        
                                    st.rerun()
                            else:
                                st.error("Senha incorreta.")
                        else:
                            st.error("NIP não encontrado.")
                            
                    except Exception as e:
                        st.error(f"Erro ao processar login: {e}")

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
    """
    Gera um gráfico de pizza estilo 'Donut' (usado em Prontidão e Visão Analítica).
    data_list: lista de dicts [{'value': 10, 'name': 'A'}, ...]
    title: Nome da série
    """
    options = {
        "tooltip": {
            "trigger": "item", 
            "formatter": "{b}: {c} ({d}%)",
            "backgroundColor": "rgba(50, 50, 50, 0.9)",
            "borderColor": "#777",
            "textStyle": {"color": "#fff"}
        },
        "legend": {
            "top": "5%", 
            "left": "center",
            "textStyle": {"color": "#9ca3af"} # Cor cinza claro para ser legível em dark/light
        },
        "series": [
            {
                "name": title,
                "type": "pie",
                "radius": ["40%", "70%"],
                "avoidLabelOverlap": True, # Evita sobreposição
                "itemStyle": {
                    "borderRadius": 10,
                    "borderColor": "#fff",
                    "borderWidth": 2,
                },
                "label": {
                    "show": True, 
                    "position": "outside",
                    "formatter": "{b}: {d}%", # Nome: Porcentagem
                    # "color": "#fff" # REMOVIDO: Deixar automático (cor da série) ou cinza
                },
                "emphasis": {
                    "label": {
                        "show": True, 
                        "fontSize": "16", 
                        "fontWeight": "bold"
                    }
                },
                "labelLine": {
                    "show": True,
                    # "lineStyle": {"color": "#fff"} # REMOVIDO: Deixar automático
                },
                "data": data_list,
            }
        ],
    }
    return options



# ============================================================
# HELPER: ECHARTS LINE
# ============================================================
def make_echarts_line(x_data, y_data):
    """
    Gera um gráfico de linha simples.
    x_data: lista de categorias
    y_data: lista de valores
    """
    options = {
        "xAxis": {
            "type": "category",
            "data": x_data,
        },
        "yAxis": {"type": "value"},
        "series": [{
            "data": y_data, 
            "type": "line",
            "label": {
                "show": True, 
                "position": "top",
                "color": "inherit", # Garante que use a cor da série ou texto legível
                "fontSize": 12
            }
        }],
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(50, 50, 50, 0.9)",
            "borderColor": "#777",
            "textStyle": {"color": "#fff"}
        }
    }
    return options

# ============================================================
# HELPER: ECHARTS BAR
# ============================================================
def make_echarts_bar(x_data, y_data):
    """
    Gera um gráfico de barras simples.
    x_data: lista de categorias
    y_data: lista de valores
    """
    options = {
        "xAxis": {
            "type": "category",
            "data": x_data,
            "axisLabel": {"interval": 0, "rotate": 30}
        },
        "yAxis": {"type": "value"},
        "series": [{
            "data": y_data, 
            "type": "bar",
            "label": {
                "show": True, 
                "position": "top",
                "color": "inherit",
                "fontSize": 12
            }
        }],
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(50, 50, 50, 0.9)",
            "borderColor": "#777",
            "textStyle": {"color": "#fff"}
        }
    }
    return options

# ============================================================
# VERSÃO DO SCRIPT
# ============================================================
SCRIPT_VERSION = "v2.1 (Ícones Atualizados)"

# Configuração do Plotly
pio.templates.default = "plotly_dark"

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA (JÁ EXECUTADO NO TOPO)
# ============================================================
# st.set_page_config(...) -> Removido daqui

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
# 2. HELPERS E CONSTANTES
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

AGENDA_COLORS = {
    "Agenda Permanente": "#4099ff", # Blue
    "Agenda Eventual": "#ff5370",   # Pink
    "Aniversários OM": "#ffb64d",   # Orange
    "Aniversários Tripulação": "#2ed8b6", # Green
    "Comissão": "#a3a3a3",          # Grey
    "NSD": "#7367f0"                # Purple
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
URL_LOTACAO = "https://docs.google.com/spreadsheets/d/1c2l7-LlFsxMqzI4JkX6IDQ7I7w-v202YaSJU2gpkrx4/edit?usp=sharing"
URL_TABELA_SERVICO = "https://docs.google.com/spreadsheets/d/1xWS42Q4WjKB5ERd8kXBXShzWzVa8fUtgo1bFdhTxE7E/edit?usp=sharing"

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
# 3. CARGA DE DADOS
# ============================================================

@st.cache_data(ttl=600, show_spinner="Carregando dados de efetivo...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Afastamento 2026", header=HEADER_ROW, ttl="10m")
    if "Nome" in df.columns:
        df = df.dropna(subset=["Nome"])
        
    # --- LOGICA GRUPOS DE CONFLITO ---
    col_jm = None
    for c in df.columns:
        if any(x in str(c).lower() for x in ["grupo", "conflito", "jm", "j.m."]):
             col_jm = c
             break
    
    if col_jm:
        df = df.rename(columns={col_jm: "ConflictGroup"})
        # Parse content: "Gp A, Gp B" -> ["Gp A", "Gp B"]
        def parse_groups(val):
            if pd.isna(val) or str(val).strip() == "":
                return []
            # Split por virgula ou ponto virgula
            s = str(val).replace(";", ",")
            parts = [p.strip() for p in s.split(",") if p.strip()]
            return parts
        df["ConflictGroup"] = df["ConflictGroup"].apply(parse_groups)
    else:
        df["ConflictGroup"] = df.apply(lambda x: [], axis=1)

    df = df.reset_index(drop=True)
    return df

@st.cache_data(ttl=3600, show_spinner="Carregando aniversariantes...")
def load_aniversarios():
    """Carrega dados de aniversários"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL_ANIVERSARIOS, ttl="1h")
    
    # Selecionar colunas B (Posto), E (Nome), H (Aniversário)
    # Assumindo que o header está na linha 1 (padrão)
    # Se B é a 2ª coluna, E a 5ª, H a 8ª.
    # Vamos tentar pegar pelo nome se possível, ou pelo índice se os nomes variarem.
    # O usuário disse: B (Posto e graduação), E (Nome de guerra), H (Aniversários)
    
    # Mapeamento seguro por índice (0-based: B=1, E=4, H=7)
    # Mas o read() retorna um DF com headers. Vamos assumir que os headers existem.
    # Se não, teríamos que ler sem header. Vamos assumir que tem header.
    
    # Filtrar colunas de interesse
    # Precisamos identificar os nomes das colunas.
    # Vamos pegar todas e renomear/filtrar depois.
    
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
    cols_keep = ["TERMO DE VIAGEM", "DATA INÍCIO", "DATA TÉRMINO", "DIAS DE MAR", "MILHAS NAVEGADAS", "ANO"]
    existing_cols = [c for c in cols_keep if c in df.columns]
    df = df[existing_cols]
    
    # Conversão de numéricos
    if "DIAS DE MAR" in df.columns:
        df["DIAS DE MAR"] = pd.to_numeric(df["DIAS DE MAR"], errors='coerce').fillna(0)
    if "MILHAS NAVEGADAS" in df.columns:
        df["MILHAS NAVEGADAS"] = pd.to_numeric(df["MILHAS NAVEGADAS"], errors='coerce').fillna(0)
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

@st.cache_data(ttl=0, show_spinner="Carregando Tabela do Dia...")
def load_tabela_servico_dia():
    """Carrega as abas TABELA 1, 2 e 3 para encontrar a escala do dia."""
    conn = st.connection("gsheets", type=GSheetsConnection)
    sheets = ["TABELA 1", "TABELA 2", "TABELA 3"]
    data = {}
    for sheet in sheets:
        try:
            # Lê sem header para pegar posições exatas (A1 é 0,0)
            df = conn.read(spreadsheet=URL_TABELA_SERVICO, worksheet=sheet, header=None, ttl=0)
            data[sheet] = df
        except Exception as e:
            print(f"Erro ao ler {sheet}: {e}")
    return data




@st.cache_data(ttl=3600, show_spinner="Carregando cardápio...")
def load_cardapio():
    """Carrega dados do cardápio semanal"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lê sem cabeçalho para pegar a estrutura exata
    df = conn.read(spreadsheet=URL_CARDAPIO, header=None, ttl="1h")
    return df



@st.cache_data(ttl=600, show_spinner="Carregando Tabela de Lotação...")
def load_lotacao_data():
    """Carrega dados da Tabela de Lotação com layout fixo (hardcoded)"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lê sem header para pegar pela posição
    df = conn.read(spreadsheet=URL_LOTACAO, header=None, ttl="10m")
    
    # 1. Seleção de Colunas por Posição
    # Coluna 0 -> Especialidade
    # Coluna -3 -> TL
    # Coluna -2 -> EF
    # Coluna -1 -> D
    try:
        df_selected = df.iloc[:, [0, -3, -2, -1]].copy()
        df_selected.columns = ["Especialidade", "TL", "EF", "D"]
        
        # 2. Filtragem de Linhas
        # Remove linhas onde Especialidade é nula ou contém "Total" (case insensitive)
        df_selected = df_selected.dropna(subset=["Especialidade"])
        df_selected = df_selected[~df_selected["Especialidade"].astype(str).str.contains("Total", case=False, na=False)]
        
        # Remove cabeçalhos perdidos (ex: se a linha tiver o texto 'Especialidade' ou 'TL')
        df_selected = df_selected[df_selected["Especialidade"] != "Especialidade"]
        
        # Opcional: Filtrar linhas vazias ou irrelevantes que possam ter sobrado
        df_selected = df_selected[df_selected["Especialidade"].astype(str).str.strip() != ""]

        # 3. Conversão de Tipos
        numeric_cols = ["TL", "EF", "D"]
        for col in numeric_cols:
            df_selected[col] = pd.to_numeric(df_selected[col], errors='coerce').fillna(0).astype(int)
            
        # 4. Cálculo de Status (Recalculado para garantir)
        def get_status(d):
            if d < 0: return "Déficit"
            elif d > 0: return "Excesso"
            return "Completo"
        df_selected["Status"] = df_selected["D"].apply(get_status)
        
        return df_selected
        
    except Exception as e:
        st.error(f"Erro ao processar estrutura da planilha: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_calendar_events(calendar_id: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    try:
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/calendar.readonly"]
        )
        service = build("calendar", "v3", credentials=creds)
        
        if not start_date:
            start_date = datetime.utcnow().isoformat() + "Z"
            
        # Parâmetros da query
        query_params = {
            "calendarId": calendar_id,
            "timeMin": start_date,
            "singleEvents": True,
            "orderBy": "startTime"
        }
        
        if end_date:
            query_params["timeMax"] = end_date
        else:
            query_params["maxResults"] = 30 # Limite padrão se não houver data fim
            
        events_result = service.events().list(**query_params).execute()
        events = events_result.get("items", [])
        data = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "Sem título")
            description = event.get("description", "")
            try:
                dt_obj = pd.to_datetime(start)
                fmt = "%d/%m %H:%M" if "T" in start else "%d/%m"
                # Ajuste fuso visual se tiver hora
                if "T" in start:
                    dt_obj = dt_obj - timedelta(hours=3)
                data_fmt = dt_obj.strftime(fmt)
            except Exception:
                data_fmt = start
            data.append({"Data": data_fmt, "Evento": summary, "Descricao": description})
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_events_today_all_calendars():
    """Busca eventos de HOJE em todas as agendas configuradas."""
    all_events = []
    
    try:
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/calendar.readonly"]
        )
        service = build("calendar", "v3", credentials=creds)
        
        # Intervalo de HOJE (00:00 até 23:59:59)
        # Ajuste de fuso horário pode ser necessário dependendo do servidor, 
        # mas UTC costuma funcionar bem se o calendário tiver timezone configurado.
        # Vamos pegar o dia corrente UTC.
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat() + "Z"
        
        for nome_agenda, cal_id in AGENDAS_OFICIAIS.items():
            try:
                events_result = service.events().list(
                    calendarId=cal_id, 
                    timeMin=start_of_day, 
                    timeMax=end_of_day,
                    singleEvents=True, 
                    orderBy="startTime"
                ).execute()
                
                items = events_result.get("items", [])
                color = AGENDA_COLORS.get(nome_agenda, "#999999")
                
                for item in items:
                    start = item["start"].get("dateTime", item["start"].get("date"))
                    summary = item.get("summary", "Sem título")
                    description = item.get("description", "")
                    
                    # Formatação de hora
                    try:
                        dt_obj = pd.to_datetime(start)
                        # Se tiver T, é datetime (tem hora). Se não, é dia inteiro.
                        if "T" in start:
                            # Ajuste fuso -3h para exibição (gambiarra visual simples)
                            dt_obj = dt_obj - timedelta(hours=3)
                            time_str = dt_obj.strftime("%H:%M")
                        else:
                            time_str = ""
                    except:
                        time_str = ""
                        
                    all_events.append({
                        "Agenda": nome_agenda,
                        "Evento": summary,
                        "Descricao": description,
                        "Hora": time_str,
                        "Cor": color,
                        "StartRaw": start
                    })
            except Exception as e:
                print(f"Erro ao ler agenda {nome_agenda}: {e}")
                continue
                
        # Ordenar por horário
        all_events.sort(key=lambda x: x["StartRaw"])
        
    except Exception as e:
        st.error(f"Erro ao conectar API Calendar: {e}")
        return []
        
    return all_events

try:
    df_raw = load_data()
    # Carregamento dos dados de mar é feito sob demanda na aba para economizar recurso inicial
except Exception as e:
    st.error(f"Erro de conexão principal: {e}")
    st.stop()


# ============================================================
# HELPER: SUNSET CALCULATION (NOAA)
# ============================================================
def calculate_sunset(date_obj, lat=-5.79448, lng=-35.211):
    """
    Calcula o horário do pôr do sol para uma data e coordenadas (Natal, RN).
    Retorna string "HH:MM".
    Algoritmo simplificado baseado no NOAA.
    """
    try:
        import math
        
        # Dia do ano
        day_of_year = date_obj.timetuple().tm_yday
        
        # Conversão para radianos
        rad = math.pi / 180.0
        
        # Declinação do sol
        gamma = (2 * math.pi / 365) * (day_of_year - 1 + (12 - 12) / 24)
        eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma) \
                 - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
        decl = 0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma) \
               - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma) \
               - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma)
        
        # Hora do ângulo horário
        ha = math.acos(math.cos(90.833 * rad) / (math.cos(lat * rad) * math.cos(decl)) \
             - math.tan(lat * rad) * math.tan(decl))
        
        # Hora UTC do pôr do sol (em minutos)
        sunset_utc = 720 - 4 * lng - eqtime + (ha / rad) * 4
        
        # Ajuste para UTC-3 (Brasília)
        sunset_local = sunset_utc / 60 - 3
        
        # Formatação
        hour = int(sunset_local)
        minute = int((sunset_local - hour) * 60)
        
        return f"{hour:02d}:{minute:02d}"
    except Exception as e:
        print(f"Erro ao calcular pôr do sol: {e}")
        return "17:30" # Fallback seguro

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
# 5. TRANSFORMAÇÃO EM EVENTOS (WIDE → LONG)
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
        
        # Capture conflict groups
        c_groups = row.get("ConflictGroup", [])
        if not isinstance(c_groups, list):
             c_groups = []

        militar_info = {
            "Posto": posto,
            "Nome": nome,
            "Escala": escala,
            "EqMan": eqman,
            "GVI": gvi,
            "IN": insp,
            "ConflictGroup": c_groups
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
# 5.1 DETECÇÃO DE CONFLITOS DE GRUPO (NOVO)
# ============================================================

def detect_conflicts(df_evt):
    """
    Detecta conflitos onde militares do mesmo 'ConflictGroup'
    estão ausentes simultaneamente.
    Retorna lista de conflitos.
    """
    if df_evt.empty:
        return []
        
    # Explodir ConflictGroup para analisar por grupo
    # Copia para não alterar o original
    df_exp = df_evt.copy()
    
    # Se ConflictGroup não existir ou não for lista, garantir
    if "ConflictGroup" not in df_exp.columns:
        return []

    # Explode
    df_exploded = df_exp.explode("ConflictGroup")
    # Remover nulos ou vazios no grupo
    df_exploded = df_exploded[df_exploded["ConflictGroup"].notna() & (df_exploded["ConflictGroup"] != "")]
    
    conflicts = []
    
    # Agrupar por ConflictGroup
    for group_name, group_df in df_exploded.groupby("ConflictGroup"):
        # Se tiver menos de 2 pessoas nesse grupo com ausência, não tem conflito interno
        if len(group_df) < 2:
            continue
            
        # Comparar pares
        # Ordenar por data
        group_df = group_df.sort_values("Inicio")
        
        # Iterar para achar interseções
        # Como é N^2 no pior caso do grupo, e o grupo é pequeno, ok.
        records = group_df.to_dict('records')
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                p1 = records[i]
                p2 = records[j]
                
                # Se for a mesma pessoa (caso ela tenha 2 ausências), ignorar ou marcar?
                # Regra: conflito entre militares diferentes
                if p1["Nome"] == p2["Nome"]:
                    continue
                
                # Checar overlap
                # Overlap se start1 <= end2 AND start2 <= end1
                if p1["Inicio"] <= p2["Fim"] and p2["Inicio"] <= p1["Fim"]:
                    # Achou overlap
                    overlap_start = max(p1["Inicio"], p2["Inicio"])
                    overlap_end = min(p1["Fim"], p2["Fim"])
                    
                    conflicts.append({
                        "Group": group_name,
                        "Person1": p1,
                        "Person2": p2,
                        "OverlapStart": overlap_start,
                        "OverlapEnd": overlap_end
                    })
                    
    return conflicts


# ============================================================
# 6. EXPANSÃO POR DIA
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
                "Tipo": ev["Tipo"],
                "ConflictGroup": ev.get("ConflictGroup", [])
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
# 7. FUNÇÕES DE FILTRO E GRÁFICOS
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
# 8. PARÂMETROS (SIDEBAR) + NAVEGAÇÃO
# ============================================================

st.sidebar.markdown("## HOME")
if "user_nome" in st.session_state:
    # Exibe saudação: Olá, CT Klismann
    posto = st.session_state.get("user_posto", "")
    nome = st.session_state.get("user_nome", "")
    st.sidebar.markdown(f"<div style='margin-bottom: 20px; color: #aab8c5; font-size: 0.9rem;'>Olá, <b>{posto} {nome}</b></div>", unsafe_allow_html=True)

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
    "Tabela de Lotação": "icons8-directory-50.svg",
    "Trocar Senha": "icons8-lock-50.svg",
    "Log / Debug": "log.svg",
    "Sair": "icons8-external-link-50.svg"
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

    st.markdown("---")
    
    # Lógica de Logout via Menu
    if pagina == "Sair":
        st.session_state.clear()
        st.rerun()

# ============================================================
# 9. MÉTRICAS GLOBAIS
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
# 10. PÁGINAS
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
    st.subheader("Ausentes")
    
    # --- SEÇÃO 1: AUSENTES HOJE (FIXO) ---
    st.markdown("### Ausentes Hoje")
    
    # Data de hoje fixa
    hoje = datetime.today()
    st.markdown(f"**Data de Referência:** {hoje.strftime('%d/%m/%Y')}")
    
    col_f_spacer1, col_f_content, col_f_spacer2 = st.columns([1, 4, 1])
    with col_f_content:
        c_f1, c_f2, c_f3 = st.columns(3)
        apenas_eqman = c_f1.checkbox("Apenas EqMan", key="aus_eqman_hoje")
        apenas_in    = c_f2.checkbox("Apenas IN", key="aus_in_hoje")
        apenas_gvi   = c_f3.checkbox("Apenas GVI/GP", key="aus_gvi_hoje")

    if not df_eventos.empty:
        ausentes_hoje = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
        ausentes_hoje = filtrar_eventos(ausentes_hoje, apenas_eqman, apenas_in, apenas_gvi)
        
        if not ausentes_hoje.empty:
            df_show = ausentes_hoje[["Posto", "Nome", "Motivo", "Inicio", "Fim", "Duracao_dias"]].copy()
            df_show["Inicio"] = df_show["Inicio"].dt.strftime("%d/%m/%Y")
            df_show["Fim"] = df_show["Fim"].dt.strftime("%d/%m/%Y")
            st.dataframe(df_show, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum ausente hoje (com os filtros selecionados).")
    else:
        st.info("Não há dados de eventos processados.")

    st.markdown("---")

    # --- SEÇÃO 2: AUSENTES POR PERÍODO ---
    st.markdown("### Ausentes por Período")
    col_p1, col_p2 = st.columns(2)
    data_ini_p = col_p1.date_input("Início do Período", hoje_padrao, key="data_aus_ini", format="DD/MM/YYYY")
    data_fim_p = col_p2.date_input("Fim do Período", hoje_padrao + timedelta(days=30), key="data_aus_fim", format="DD/MM/YYYY")
    
    dt_ini = pd.to_datetime(data_ini_p)
    dt_fim = pd.to_datetime(data_fim_p)

    if not df_eventos.empty:
        # Filtra eventos que têm intersecção com o período selecionado
        mask_periodo = (df_eventos["Inicio"] <= dt_fim) & (df_eventos["Fim"] >= dt_ini)
        ausentes_periodo = df_eventos[mask_periodo]
        ausentes_periodo = filtrar_eventos(ausentes_periodo, apenas_eqman, apenas_in, apenas_gvi)

        if not ausentes_periodo.empty:
            df_show_p = ausentes_periodo[["Posto", "Nome", "Motivo", "Inicio", "Fim", "Duracao_dias"]].copy()
            df_show_p["Inicio"] = df_show_p["Inicio"].dt.strftime("%d/%m/%Y")
            df_show_p["Fim"] = df_show_p["Fim"].dt.strftime("%d/%m/%Y")
            st.dataframe(df_show_p, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum ausente neste período (com os filtros selecionados).")
    else:
        st.info("Não há dados de eventos processados.")

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
# NOVO: TROCAR SENHA
# --------------------------------------------------------
elif pagina == "Trocar Senha":
    st.subheader("Trocar Senha")
    
    # Verifica se o usuário está logado (deve estar, mas por segurança)
    current_user_nip = st.session_state.get("username")
    
    if not current_user_nip:
        st.error("Você precisa estar logado para trocar a senha.")
    else:
        with st.form("change_own_password_form"):
            st.info(f"Alterando senha para o NIP: {current_user_nip}")
            
            current_pass_input = st.text_input("Senha Atual", type="password")
            new_pass = st.text_input("Nova Senha", type="password")
            confirm_pass = st.text_input("Confirmar Nova Senha", type="password")
            
            if st.form_submit_button("ATUALIZAR SENHA", use_container_width=True):
                # 1. Validar senha atual
                df = get_users_data()
                df['NIP_NORM'] = df.iloc[:, 3].apply(normalize_nip)
                user_row = df[df['NIP_NORM'] == normalize_nip(current_user_nip)]
                
                if user_row.empty:
                    st.error("Erro: Usuário não encontrado na base.")
                else:
                    stored_password = str(user_row.iloc[0, 4]).strip()
                    
                    if current_pass_input != stored_password:
                        st.error("A senha atual está incorreta.")
                    elif new_pass != confirm_pass:
                        st.error("As novas senhas não coincidem.")
                    elif len(new_pass) < 6:
                        st.error("A nova senha deve ter pelo menos 6 caracteres.")
                    elif new_pass == "mudar123":
                        st.error("Você não pode usar a senha padrão.")
                    else:
                        # Tudo ok, atualizar
                        if update_password(current_user_nip, new_pass):
                            st.success("Senha atualizada com sucesso! Você será deslogado em instantes.")
                            import time
                            time.sleep(2)
                            st.session_state.clear()
                            st.rerun()
                        else:
                            st.error("Erro ao atualizar senha no banco de dados.")

# --------------------------------------------------------
# OUTRAS PÁGINAS (Usam Data Padrão Hoje)
# --------------------------------------------------------
else:
    hoje = pd.to_datetime(hoje_padrao)
    
    if pagina == "Agenda do Navio":
        st.subheader("Agenda do Navio (Google Calendar)")
        
        # --- SEÇÃO DE EVENTOS DE HOJE ---
        st.markdown("##### Eventos de Hoje")
        events_today = get_events_today_all_calendars()
        
        if not events_today:
            st.info("Nenhum evento programado para hoje.")
        else:
            for ev in events_today:
                # Lógica de display do horário: se vazio, display:none
                time_display_style = "display: block;" if ev['Hora'] else "display: none;"
                
                st.markdown(
                    f"""
                    <details style="
                        margin-bottom: 10px; 
                        background-color: rgba(255,255,255,0.05); 
                        border-radius: 6px;
                        border-left: 5px solid {ev['Cor']};
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    ">
                        <summary style="
                            padding: 12px 15px; 
                            cursor: pointer;
                            display: flex; 
                            align-items: center;
                            list-style: none; /* Remove triângulo padrão */
                        ">
                            <div style="
                                font-weight: bold; 
                                font-family: monospace; 
                                margin-right: 8px; 
                                color: {ev['Cor']};
                                min-width: 55px;
                                {time_display_style}
                            ">{ev['Hora']}</div>
                            <div style="font-weight: 500; font-size: 1rem;">
                                {ev['Evento']}
                                <div style="font-size: 0.75rem; color: #888; margin-top: 2px;">{ev['Agenda']}</div>
                            </div>
                        </summary>
                        <div style="
                            padding: 10px 15px; 
                            border-top: 1px solid rgba(255,255,255,0.1);
                            font-size: 0.9rem;
                            color: #ccc;
                            white-space: pre-wrap;
                        ">
                            {ev['Descricao'] if ev['Descricao'] else '<i>Sem descrição.</i>'}
                        </div>
                    </details>
                    """,
                    unsafe_allow_html=True
                )
        
        st.markdown("---")
        
        col_sel, col_btn = st.columns([2, 2])
        with col_sel:
            nome_agenda = st.selectbox("Selecione a Agenda:", list(AGENDAS_OFICIAIS.keys()))
            selected_id = AGENDAS_OFICIAIS[nome_agenda]
        
        with col_btn:
            # Seletores de Mês e Ano
            c_mes, c_ano = st.columns([1.5, 1])
            meses_dict = {
                "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
                "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
            }
            now = datetime.now()
            with c_mes:
                sel_mes_nome = st.selectbox("Mês", list(meses_dict.keys()), index=now.month-1, key="ag_mes")
            with c_ano:
                sel_ano = st.number_input("Ano", value=now.year, min_value=2024, max_value=2030, key="ag_ano")
            
            # Botão de atualização manual (opcional, mas bom para forçar refresh)
            # st.button("Atualizar") -> O cache cuida disso, ou podemos por um botão se quiser.

        if selected_id:
            # Calcular start e end dates para o filtro
            sel_mes = meses_dict[sel_mes_nome]
            dt_start = datetime(sel_ano, sel_mes, 1)
            if sel_mes == 12:
                dt_end = datetime(sel_ano + 1, 1, 1)
            else:
                dt_end = datetime(sel_ano, sel_mes + 1, 1)
            
            # Converter para ISO format UTC (aproximado)
            # Adicionando Z para indicar UTC
            start_str = dt_start.isoformat() + "Z"
            end_str = dt_end.isoformat() + "Z"

            df_cal = load_calendar_events(selected_id, start_date=start_str, end_date=end_str)
            
            if df_cal.empty:
                st.info(f"Nenhum evento encontrado em **{nome_agenda}** para {sel_mes_nome}/{sel_ano}.")
            else:
                st.markdown("---")
                cal_color = AGENDA_COLORS.get(nome_agenda, "#999999")
                
                for _, row in df_cal.iterrows():
                    # Extrair hora se houver (formato DD/MM HH:MM)
                    hora_display = ""
                    data_display = row['Data']
                    descricao = row.get('Descricao', '')
                    
                    # Tenta separar hora da data se possível, ou exibe data completa
                    # O helper load_calendar_events retorna 'Data' já formatada.
                    # Vamos manter simples: Data na esquerda (onde ficava a hora)
                    
                    st.markdown(
                        f"""
                        <details style="
                            margin-bottom: 10px; 
                            background-color: rgba(255,255,255,0.05); 
                            border-radius: 6px;
                            border-left: 5px solid {cal_color};
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        ">
                            <summary style="
                                padding: 12px 15px; 
                                cursor: pointer;
                                display: flex; 
                                align-items: center;
                                list-style: none;
                            ">
                                <div style="
                                    font-weight: bold; 
                                    font-family: monospace; 
                                    margin-right: 8px; 
                                    color: {cal_color};
                                    min-width: 70px;
                                ">{data_display}</div>
                                <div style="font-weight: 500; font-size: 1rem;">
                                    {row['Evento']}
                                </div>
                            </summary>
                            <div style="
                                padding: 10px 15px; 
                                border-top: 1px solid rgba(255,255,255,0.1);
                                font-size: 0.9rem;
                                color: #ccc;
                                white-space: pre-wrap;
                            ">
                                {descricao if descricao else '<i>Sem descrição.</i>'}
                            </div>
                        </details>
                        """,
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
                    
                    # df_top10 = (df_evt.groupby(["Nome", "Posto"])["Duracao_dias"].sum().reset_index().sort_values("Duracao_dias", ascending=False).head(10))
                    # st.markdown("##### Top 10 – Dias de ausência por militar")
                    # opt_top10 = make_echarts_bar(df_top10["Nome"].tolist(), df_top10["Duracao_dias"].tolist())
                    # st_echarts(options=opt_top10, height="500px")
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
        
        # --- CONFLITOS DE GRUPO (NOVO) ---
        conflicts_found = detect_conflicts(df_eventos)
        if conflicts_found:
            with st.expander(f"⚠️ CONFLITOS DE GRUPO DETECTADOS ({len(conflicts_found)})", expanded=True):
                st.write("Atenção: Os seguintes militares do mesmo grupo de conflito possuem ausências coincidentes.")
                for c in conflicts_found:
                    p1 = c['Person1']
                    p2 = c['Person2']
                    # Validar se timestamps validos
                    try:
                        d_start = c['OverlapStart'].strftime('%d/%m/%Y')
                        d_end = c['OverlapEnd'].strftime('%d/%m/%Y')
                    except:
                        d_start = str(c['OverlapStart'])
                        d_end = str(c['OverlapEnd'])
                    
                    st.markdown(
                        f"""
                        <div style="
                            padding: 10px; border: 1px solid #ff4b4b; border-radius: 5px; 
                            background-color: rgba(255, 75, 75, 0.1); margin-bottom: 10px;
                        ">
                            <span style="color: #ff4b4b; font-weight: bold;">🔴 Grupo {c['Group']}</span><br>
                            <b>{p1['Posto']} {p1['Nome']}</b> <i>({p1['Tipo']})</i> ⚡ 
                            <b>{p2['Posto']} {p2['Nome']}</b> <i>({p2['Tipo']})</i><br>
                            📅 <b>Período de Coincidência:</b> {d_start} a {d_end}
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
        # ---------------------------------
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
        st.subheader("Tabela de Serviço")
        
        tab_serv_ops = st.tabs(["Análise", "Tabela do Dia"])
        
        # --- SUB-ABA 1: ANÁLISE (EXISTENTE) ---
        with tab_serv_ops[0]:
            content_container = st.container()
            with content_container:
                if df_eventos.empty:
                    st.write("Sem registros para análise de serviço.")
                else:
                    st.markdown("##### Visão Geral de Escalas")
                    # Remove vazios
                    df_escala_limpa = df_raw[df_raw["Serviço"] != ""].copy()
                    
                    if df_escala_limpa.empty:
                        st.info("Nenhuma escala definida na coluna 'Serviço'.")
                    else:
                        escala_counts = df_escala_limpa["Serviço"].value_counts().reset_index()
                        escala_counts.columns = ["Escala", "Qtd"]
                        
                        col_s1, col_s2, col_s3 = st.columns(3)
                        total_em_escala = escala_counts["Qtd"].sum()
                        tipos_escala = len(escala_counts)
                        
                        # Calcula "Não Concorre"
                        # Considera que quem não tem escala definida ou está explicitamente marcado
                        total_efetivo = len(df_raw)
                        # Assumindo que quem tem "Serviço" preenchido concorre
                        nao_concorre_count = total_efetivo - total_em_escala
                        
                        # Listar quem não concorre
                        df_nao_concorre = df_raw[
                            (df_raw["Serviço"].isna()) | 
                            (df_raw["Serviço"] == "") | 
                            (df_raw["Serviço"] == "-")
                        ]
                        # Re-calcula count baseado no filtro explícito para ser preciso
                        nao_concorre_real_count = len(df_nao_concorre)
                        
                        col_s1.metric("Total em escala", total_em_escala)
                        col_s2.metric("Tipos de escala", tipos_escala)
                        col_s3.metric("Não concorre", nao_concorre_real_count)
                        
                        st.markdown("---")
                        
                        c_esc_graf, c_nao_conc = st.columns([2, 1])
                        
                        with c_esc_graf:
                            st.markdown("##### Distribuição por Escala")
                            opt_escala_dist = make_echarts_bar(escala_counts["Escala"].tolist(), escala_counts["Qtd"].tolist())
                            st_echarts(options=opt_escala_dist, height="400px")
                            
                        with c_nao_conc:
                            st.markdown("##### Quem não concorre")
                            if df_nao_concorre.empty:
                                st.info("Todos concorrem.")
                            else:
                                st.dataframe(df_nao_concorre[["Posto", "Nome"]], use_container_width=True, hide_index=True)

        # --- SUB-ABA 2: TABELA DO DIA (NOVA) ---
        with tab_serv_ops[1]:
            st.markdown("### Serviço Diário")
            
            # 1. Carregar dados
            data_sheets = load_tabela_servico_dia()
            
            if not data_sheets:
                st.error("Não foi possível carregar as tabelas de serviço.")
            else:
                # 2. Identificar qual tabela é de HOJE (dia da semana)
                # Mapeamento Dia Semana (0=Seg, 6=Dom) -> Nome na Planilha ou Lógica
                # Observando a estrutura, parece que TABELA 1 = Seg-Qui (Rotina 1) ??
                # Ou a planilha tem dias específicos.
                # O requisito diz: "identificar o dia de hoje e carregar a tabela correspondente"
                # Vamos procurar a data de hoje nas células C3 (linha 2, col 2) de cada aba, conforme inspeção anterior?
                # Ajuste: O usuário mencionou que a data está na C3.
                
                hoje_dia = datetime.now().date()
                tabela_hoje = None
                nome_aba_hoje = ""
                
                # Procura nas 3 tabelas
                found = False
                for sheet_name, df_sheet in data_sheets.items():
                    # Tenta ler C3 (row 2, col 2)
                    try:
                        val_c3 = df_sheet.iloc[2, 2] # C3
                        # Tenta converter para data
                        if isinstance(val_c3, datetime):
                            date_val = val_c3.date()
                        else:
                            # Tentar parse string
                            date_val = pd.to_datetime(val_c3, dayfirst=True, errors='coerce').date()
                        
                        if date_val == hoje_dia:
                            tabela_hoje = df_sheet
                            nome_aba_hoje = sheet_name
                            found = True
                            break
                    except:
                        continue
                
                # FALLBACK PARA TESTE (se não encontrar data exata, pega a TABELA 1 como padrão ou exibe aviso)
                # Remova este fallback em produção se for estrito.
                if not found:
                    st.warning(f"Não foi encontrada uma tabela com a data de hoje ({hoje_dia.strftime('%d/%m/%Y')}) na célula C3. Exibindo TABELA 1 como exemplo.")
                    tabela_hoje = data_sheets.get("TABELA 1")
                    nome_aba_hoje = "TABELA 1 (Exemplo)"

                if tabela_hoje is not None:
                    # --- PROCESSAMENTO EXIBIÇÃO ---
                    # HEADER INFO
                    # DIA DA SEMANA: G3 (0, 6) -> row 2, col 6
                    # REGIME: C4 (row 3, col 2)
                    # ROTINA: G4 (row 3, col 6)
                    # POR DO SOL: J3 (row 2, col 9)
                    
                    try:
                        dia_sem = str(tabela_hoje.iloc[2, 6]).strip()
                        regime  = str(tabela_hoje.iloc[3, 2]).strip()
                        rotina  = str(tabela_hoje.iloc[3, 6]).strip()
                        p_sol_raw   = tabela_hoje.iloc[2, 9]
                        
                        # Tratamento de erro no Pôr do Sol
                        # Se vier algo como "#ERROR!" ou Exception, mostrar "-" ou calcular
                        s_sol = str(p_sol_raw)
                        if "ERROR" in s_sol or "Exception" in s_sol:
                            # Tenta calcular
                            p_sol = calculate_sunset(datetime.now()) + "*"
                        else:
                            # Tenta formatar se for datetime/time
                            if isinstance(p_sol_raw, (datetime, pd.Timestamp)):
                                p_sol = p_sol_raw.strftime("%H:%M")
                            elif isinstance(p_sol_raw, time): # type: ignore
                                p_sol = p_sol_raw.strftime("%H:%M")
                            else:
                                p_sol = s_sol
                                
                    except Exception as e:
                        st.error(f"Erro ao ler cabeçalho da tabela: {e}")
                        dia_sem, regime, rotina, p_sol = "-", "-", "-", "-"
                    
                    # CARDS DE CABEÇALHO
                    # Estilo clean sem emojis, cartas claras em light mode
                    
                    # CSS específico para cards
                    st.markdown("""
                    <style>
                    .serv-card {
                        background-color: var(--secondary-background-color);
                        padding: 15px;
                        border-radius: 8px;
                        border-left: 4px solid #4099ff;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                        color: var(--text-color);
                    }
                    .serv-card h4 {
                        margin: 0;
                        font-size: 0.8rem;
                        color: #888;
                        text-transform: uppercase;
                    }
                    .serv-card p {
                        margin: 5px 0 0 0;
                        font-size: 1.1rem;
                        font-weight: 600;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    c_h1, c_h2, c_h3, c_h4 = st.columns(4)
                    c_h1.markdown(f"<div class='serv-card'><h4>DIA DA SEMANA</h4><p>{dia_sem}</p></div>", unsafe_allow_html=True)
                    c_h2.markdown(f"<div class='serv-card' style='border-left-color: #ff5370;'><h4>REGIME</h4><p>{regime}</p></div>", unsafe_allow_html=True)
                    c_h3.markdown(f"<div class='serv-card' style='border-left-color: #2ed8b6;'><h4>ROTINA</h4><p>{rotina}</p></div>", unsafe_allow_html=True)
                    c_h4.markdown(f"<div class='serv-card' style='border-left-color: #ffb64d;'><h4>PÔR DO SOL</h4><p>{p_sol}</p></div>", unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # LAYOUT DE SERVIÇO
                    # Serviço Diário (C7:G21 aprox) e Serviço de Quarto (H7:L21)
                    # Vamos pegar range dinâmico ou fixo conforme observado
                    # Diário: Col C (função) e G (nome) das linhas 7 a 26
                    # Quarto: Col H (Horário/Função) e L (Nome)
                    
                    # Função Helper para extrair bloco
                    def get_servico_block(df, row_start, row_end, col_func, col_nome):
                        items = []
                        for r in range(row_start, row_end + 1):
                            if r >= len(df): break
                            func = str(df.iloc[r, col_func]).strip()
                            nome = str(df.iloc[r, col_nome]).strip()
                            
                            # Ignorar vazios ou placeholders
                            if not func or func in ["nan", "None", "-"]: continue
                            if not nome or nome in ["nan", "None"]: nome = "-"
                            
                            items.append({"Função": func, "Militar": nome})
                        return pd.DataFrame(items)

                    # Ajuste de índices (0-based)
                    # Excel row 7 = index 6
                    
                    # SERVIÇO DIÁRIO
                    st.markdown("##### Serviço Diário")
                    # Assumindo range observado na estrutura: Row 7 até 26, Cols C(2) e G(6)
                    df_diario_tbl = get_servico_block(tabela_hoje, 6, 25, 2, 6)
                    
                    if not df_diario_tbl.empty:
                         # Estilização custom html para tabela limpa
                         html_tbl = "<table style='width:100%; border-collapse: collapse;'>"
                         for _, row in df_diario_tbl.iterrows():
                             html_tbl += f"""
                             <tr style='border-bottom: 1px solid rgba(128,128,128,0.2);'>
                                <td style='padding: 8px; font-weight: bold; width: 40%; color: #4099ff;'>{row['Função']}</td>
                                <td style='padding: 8px;'>{row['Militar']}</td>
                             </tr>
                             """
                         html_tbl += "</table>"
                         st.markdown(html_tbl, unsafe_allow_html=True)
                    else:
                        st.info("Não detectado.")
                        
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # SERVIÇO DE QUARTO
                    st.markdown("##### Serviço de Quarto")
                    # Assumindo range: Row 7 até 26, Cols H(7) e L(11) ??
                    # Precisa confirmar colunas. H=7, I=8, J=9, K=10, L=11.
                    df_quarto_tbl = get_servico_block(tabela_hoje, 6, 25, 7, 11)
                    
                    if not df_quarto_tbl.empty:
                         html_tbl_2 = "<table style='width:100%; border-collapse: collapse;'>"
                         for _, row in df_quarto_tbl.iterrows():
                             html_tbl_2 += f"""
                             <tr style='border-bottom: 1px solid rgba(128,128,128,0.2);'>
                                <td style='padding: 8px; font-weight: bold; width: 40%; color: #2ed8b6;'>{row['Função']}</td>
                                <td style='padding: 8px;'>{row['Militar']}</td>
                             </tr>
                             """
                         html_tbl_2 += "</table>"
                         st.markdown(html_tbl_2, unsafe_allow_html=True)
                    else:
                        st.info("Não detectado.")

    elif pagina == "Cardápio":
        st.subheader("Cardápio Semanal")
        df_cardapio = load_cardapio()
        
        if df_cardapio.empty:
            st.info("Cardápio não disponível.")
        else:
            # Assumindo layout simples: Dia na col A, Refeição col B, Prato col C...
            # Ou apenas exibir como tabela colorida
            st.dataframe(df_cardapio, use_container_width=True, hide_index=True)

    elif pagina == "Aniversários":
        st.subheader("Aniversariantes")
        
        # Carrega dados específicos (Posto, Nome, Data)
        df_aniversarios = load_aniversarios()
        
        # Se a função retornar vazio ou estrutura errada, tentar pegar do df_raw se tiver coluna Aniversário
        # Assumindo que load_aniversarios já retorna estrutura correta.
        # Vamos re-implementar load_aniversarios para ser robusto no topo ou usar lógica aqui?
        # A função load_aniversarios está placeholder no topo, vamos aprimorar a lógica de parsing aqui se necessário.
        
        # Se df_aniversarios estiver vazio ou incompleto, tentamos extrair do df_raw se tiver info de data nascimento
        # Mas o requisito pede uma planilha separada URL_ANIVERSARIOS.
        
        if df_aniversarios.empty:
             st.info("Não foi possível carregar a lista de aniversários.")
        else:
            # Tentar identificar colunas (B, E, H) -> indices 1, 4, 7
            # O dataframe vem com tudo. Select por indice.
            try:
                # Copia colunas de interesse (assumindo indices fixos da planilha original de aniver)
                # O read() traz apenas dados preenchidos
                # Vamos pegar colunas pelo nome se existirem, ou indice.
                # Assumindo que a planilha tem cabeçalho na linha 1
                
                # Se colunas não identificadas, pega por iloc
                if len(df_aniversarios.columns) >= 8:
                    df_niver = df_aniversarios.iloc[:, [1, 4, 7]].copy()
                    df_niver.columns = ["Posto", "Nome", "Data"]
                else:
                    # Fallback
                    df_niver = df_aniversarios.copy()
                
                # Drop na
                df_niver = df_niver.dropna()
                
                # Parse Data
                def parse_niver_date(v):
                    if pd.isna(v): return pd.NaT
                    s = str(v).strip()
                    # Formatos possiveis DD/MM/YYYY ou DD/MM
                    try:
                        dt = pd.to_datetime(s, dayfirst=True)
                        # Ignorar ano para calculo de aniversario, mas precisa de um ano base
                        # Retorna (mes, dia)
                        return dt
                    except:
                        return pd.NaT
                
                df_niver["DataObj"] = df_niver["Data"].apply(parse_niver_date)
                df_niver = df_niver.dropna(subset=["DataObj"])
                
                hoje_n = datetime.today()
                
                # Proximos aniversarios (nos proximos 30 dias)
                df_niver["Dia"] = df_niver["DataObj"].dt.day
                df_niver["Mes"] = df_niver["DataObj"].dt.month
                
                # Lógica de "próximos": considera virada de ano
                def dias_para_niver(row):
                    niver_este_ano = datetime(hoje_n.year, int(row["Mes"]), int(row["Dia"]))
                    if niver_este_ano < hoje_n.replace(hour=0, minute=0, second=0, microsecond=0):
                        niver_prox_ano = datetime(hoje_n.year + 1, int(row["Mes"]), int(row["Dia"]))
                        delta = (niver_prox_ano - hoje_n).days
                    else:
                        delta = (niver_este_ano - hoje_n).days
                    return delta
                
                df_niver["DiasPara"] = df_niver.apply(dias_para_niver, axis=1)
                df_niver = df_niver.sort_values("DiasPara")
                
                # Filtra próximos 45 dias
                df_proximos = df_niver[df_niver["DiasPara"] <= 45].copy()
                
                if df_proximos.empty:
                    st.info("Nenhum aniversário nos próximos 45 dias.")
                else:
                    st.markdown("##### Próximos Aniversariantes (45 dias)")
                    for _, row in df_proximos.iterrows():
                        msg_dias = "Hoje!" if row['DiasPara'] <= 0 else f"em {int(row['DiasPara'])} dias"
                        color_ico = "#ff5370" if row['DiasPara'] <= 0 else "#4099ff"
                        
                        st.markdown(
                            f"""
                            <div style="
                                display: flex; align-items: center; justify-content: space-between;
                                background-color: rgba(255,255,255,0.05);
                                padding: 10px 15px; border-radius: 8px; margin-bottom: 8px;
                                border-left: 4px solid {color_ico};
                            ">
                                <div>
                                    <div style="font-weight: bold; font-size: 1rem;">{row['Posto']} {row['Nome']}</div>
                                    <div style="font-size: 0.85rem; color: #888;">{int(row['Dia']):02d}/{int(row['Mes']):02d}</div>
                                </div>
                                <div style="
                                    background-color: {color_ico}; color: white;
                                    padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;
                                ">
                                    {msg_dias}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    
                    with st.expander("Ver lista completa"):
                        st.dataframe(df_niver[["Posto", "Nome", "Data"]], use_container_width=True, hide_index=True)
                        
            except Exception as e:
                st.error(f"Erro ao processar aniversários: {e}")
    elif pagina == "Tabela de Lotação":
        st.subheader("Tabela de Lotação")
        
        # Carrega dados com função específica (estrutura fixa)
        df_lotacao = load_lotacao_data()
        
        if df_lotacao.empty:
            st.info("Tabela de Lotação não encontrada ou vazia.")
        else:
            # KPIS
            tl_total = df_lotacao["TL"].sum()
            ef_total = df_lotacao["EF"].sum()
            gap_total = df_lotacao["D"].sum()
            
            c_l1, c_l2, c_l3 = st.columns(3)
            c_l1.metric("Lotação Total (TL)", tl_total)
            c_l2.metric("Efetivo Atual (EF)", ef_total)
            c_l3.metric("Balanço Geral", gap_total, delta_color="normal") # normal: red if negative, green if pos
            
            st.markdown("---")
            
            col_l_graf, col_l_tab = st.columns([1, 2])
            
            with col_l_graf:
                # Gráfico de barras divergentes (Déficit/Excesso) por Especialidade
                st.markdown("##### Déficit/Excesso por Especialidade")
                
                # Prepara dados para ECharts Bar (com cores condicionais se possível ou simples)
                # simplificado: Ordenar por GAP
                df_chart_lot = df_lotacao.sort_values("D", ascending=True) # Mostrar maiores deficits primeiro
                
                # Echarts precisa de lists
                x_data = df_chart_lot["Especialidade"].tolist()
                y_data = df_chart_lot["D"].tolist()
                
                # Cores customizadas na serie? 
                # ECharts permite itemStyle function ou array. 
                # Vamos usar um bar chart simples, mas com coloração visual via JS callback seria ideal.
                # Aqui simplificamos: barras comuns. O valor negativo aparece para baixo? Echarts Bar padrao sim.
                
                opt_lotacao = {
                    "tooltip": {"trigger": "axis"},
                    "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
                    "xAxis": {
                        "type": "value",
                        "position": "top",
                        "splitLine": {"lineStyle": {"type": "dashed"}}
                    },
                    "yAxis": {
                        "type": "category",
                        "axisTick": {"show": False},
                        "data": x_data
                    },
                    "series": [
                        {
                            "name": "Diferença",
                            "type": "bar",
                            "stack": "Total",
                            "label": {"show": True},
                            "data": [
                                {
                                    "value": val,
                                    "itemStyle": {"color": "#ff5370" if val < 0 else "#2ed8b6"}
                                } 
                                for val in y_data
                            ]
                        }
                    ]
                }
                st_echarts(options=opt_lotacao, height="600px")

            with col_l_tab:
                st.markdown("##### Detalhamento")
                
                # Style simples na tabela
                st.dataframe(
                    df_lotacao.style.applymap(
                        lambda v: 'color: #ff5370; font-weight: bold;' if isinstance(v, (int, float)) and v < 0 else 
                                  ('color: #2ed8b6; font-weight: bold;' if isinstance(v, (int, float)) and v > 0 else ''),
                        subset=['D']
                    ).format({"TL": "{:.0f}", "EF": "{:.0f}", "D": "{:.0f}"}),
                    use_container_width=True,
                    height=600
                )

    elif pagina == "Log / Debug":
        st.subheader("Logs e Debug")
        st.write("Estado da Sessão:")
        st.write(st.session_state)
        
        if st.checkbox("Mostrar DataFrame Bruto (df_raw)"):
            st.dataframe(df_raw)
            
        if st.checkbox("Mostrar Eventos Processados (df_eventos)"):
            st.dataframe(df_eventos)
            
        if st.checkbox("Mostrar Blocos de Datas Detectados"):
            st.write(BLOCOS_DATAS)

    # --- FOOTER ---
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; font-size: 0.8rem;'>"
        "AMEZIA © 2025 - Sistema de Gestão de Efetivo<br>"
        "Desenvolvido para apoio à decisão."
        "</div>", 
        unsafe_allow_html=True
    )
