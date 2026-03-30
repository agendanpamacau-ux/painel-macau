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
from streamlit_echarts import st_echarts, JsCode
import streamlit.components.v1 as components

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
        "toolbox": {"feature": {"saveAsImage": {"title": "Salvar Imagem"}}},
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
                "radius": ["25%", "45%"],
                "center": ["50%", "55%"],
                "avoidLabelOverlap": True, # Evita sobreposição
                "itemStyle": {
                    "borderRadius": 10,
                    "borderColor": "#fff",
                    "borderWidth": 2,
                },
                "label": {
                    "show": True, 
                    "position": "outside",
                    "formatter": "{b}\n{c} ({d}%)", # Quebra a linha para poupar espaço horizontal
                    "margin": 10,
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
                    "length": 15,    # Reduz o tamanho da primeira linha da legenda
                    "length2": 15    # Reduz o tamanho da segunda linha da legenda
                },
                "data": data_list,
            }
        ],
    }
    return options



# ============================================================
# HELPER: ECHARTS LINE
# ============================================================
def make_echarts_line(x_data, y_data, integer=False):
    """
    Gera um gráfico de linha simples.
    x_data: lista de categorias
    y_data: lista de valores
    integer: se True, formata valores como inteiros (para quantitativos)
    """
    if integer:
        y_data_fmt = [str(int(float(y))) if pd.notna(y) else "0" for y in y_data]
    else:
        y_data_fmt = [f"{float(y):.2f}" if pd.notna(y) else "0.00" for y in y_data]
    
    options = {
        "toolbox": {"feature": {"saveAsImage": {"title": "Salvar Imagem"}}},
        "grid": {"containLabel": True, "left": "5%", "right": "5%", "top": "15%", "bottom": "15%"},
        "xAxis": {
            "type": "category",
            "data": x_data,
        },
        "yAxis": {"type": "value"},
        "series": [{
            "data": y_data_fmt, 
            "type": "line",
            "label": {
                "show": True, 
                "position": "top",
                "color": "inherit", 
                "fontSize": 12,
                "formatter": "{c}"
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
def make_echarts_bar(x_data, y_data, integer=True):
    """
    Gera um gráfico de barras simples.
    x_data: lista de categorias
    y_data: lista de valores
    integer: se True, formata valores como inteiros (padrão para barras)
    """
    if integer:
        y_data_fmt = [int(float(y)) if pd.notna(y) else 0 for y in y_data]
    else:
        y_data_fmt = [round(float(y), 2) if pd.notna(y) else 0.0 for y in y_data]
    
    options = {
        "toolbox": {"feature": {"saveAsImage": {"title": "Salvar Imagem"}}},
        "grid": {"containLabel": True, "left": "5%", "right": "5%", "top": "15%", "bottom": "15%"},
        "xAxis": {
            "type": "category",
            "data": x_data,
            "axisLabel": {"interval": 0, "rotate": 30}
        },
        "yAxis": {"type": "value"},
        "series": [{
            "data": y_data_fmt, 
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
# HELPER: ECHARTS GROUPED BAR
# ============================================================
def make_echarts_grouped_bar(x_data, series_list):
    """
    Gera um gráfico de barras agrupadas.
    x_data: lista de categorias (ex: meses)
    series_list: lista de dicts [{"name": "Serviço", "data": [...]}, ...]
    """
    colors = ["#4099ff", "#ff5370", "#2ed8b6", "#ffb64d", "#a3a3a3", "#7367f0", "#e83e8c"]
    series = []
    for i, s in enumerate(series_list):
        series.append({
            "name": s["name"],
            "type": "bar",
            "data": [int(v) for v in s["data"]],
            "label": {
                "show": True,
                "position": "top",
                "fontSize": 10
            },
            "itemStyle": {"color": colors[i % len(colors)]}
        })
    options = {
        "toolbox": {"feature": {"saveAsImage": {"title": "Salvar Imagem"}}},
        "legend": {"data": [s["name"] for s in series_list], "top": "0%"},
        "xAxis": {
            "type": "category",
            "data": x_data,
            "axisLabel": {"interval": 0, "rotate": 30}
        },
        "yAxis": {"type": "value"},
        "series": series,
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(50, 50, 50, 0.9)",
            "borderColor": "#777",
            "textStyle": {"color": "#fff"}
        },
        "grid": {"containLabel": True, "left": "5%", "right": "5%", "top": "15%", "bottom": "15%"}
    }
    return options

# ============================================================
# HELPER: ECHARTS DUAL LINE (Meta vs Realizado)
# ============================================================
def make_echarts_dual_line(x_data, y_meta, y_real, label_meta="Meta", label_real="Realizado"):
    """
    Gera um gráfico de 2 linhas sobrepostas (meta vs realizado).
    """
    y_meta_fmt = [f"{float(y):.1f}" if pd.notna(y) else "0.0" for y in y_meta]
    y_real_fmt = [f"{float(y):.1f}" if pd.notna(y) else "0.0" for y in y_real]
    options = {
        "toolbox": {"feature": {"saveAsImage": {"title": "Salvar Imagem"}}},
        "legend": {"data": [label_meta, label_real], "top": "0%"},
        "xAxis": {
            "type": "category",
            "data": x_data,
        },
        "yAxis": {"type": "value", "axisLabel": {"formatter": "{value}%"}},
        "series": [
            {
                "name": label_meta,
                "data": y_meta_fmt,
                "type": "line",
                "lineStyle": {"type": "dashed", "color": "#ffb64d"},
                "itemStyle": {"color": "#ffb64d"},
                "label": {"show": True, "position": "top", "fontSize": 11, "formatter": "{c}%"}
            },
            {
                "name": label_real,
                "data": y_real_fmt,
                "type": "line",
                "lineStyle": {"color": "#4099ff"},
                "itemStyle": {"color": "#4099ff"},
                "label": {"show": True, "position": "bottom", "fontSize": 11, "formatter": "{c}%"}
            }
        ],
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(50, 50, 50, 0.9)",
            "borderColor": "#777",
            "textStyle": {"color": "#fff"}
        },
        "grid": {"containLabel": True, "left": "5%", "right": "5%", "top": "12%", "bottom": "15%"}
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
URL_ADESTRAMENTO = "https://docs.google.com/spreadsheets/d/1F2aovawDlvuTGbMn2EDHMYXVAX4eFn49w0MxWd-EkWs/edit?usp=sharing"
URL_LOTACAO = "https://docs.google.com/spreadsheets/d/1c2l7-LlFsxMqzI4JkX6IDQ7I7w-v202YaSJU2gpkrx4/edit?usp=sharing"
URL_TABELA_SERVICO = "https://docs.google.com/spreadsheets/d/1xWS42Q4WjKB5ERd8kXBXShzWzVa8fUtgo1bFdhTxE7E/edit?usp=sharing"
URL_AUSENCIAS = "https://docs.google.com/spreadsheets/d/1BLBVdAUfJ4sYH2qLRTXs122L89HGCTrPPuxM8KK7_sU/edit?usp=sharing"

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
    Parser para datas de aniversário.
    Aceita datetime objects, strings como '6nov.' ou '15/03'.
    Retorna uma data com o ano corrente.
    """
    if pd.isna(val) or str(val).strip() == "":
        return pd.NaT
    
    ano_atual = (datetime.utcnow() - timedelta(hours=3)).year
    
    # Se já for datetime/Timestamp, extrai dia e mês
    if isinstance(val, (datetime, pd.Timestamp)):
        try:
            return datetime(ano_atual, val.month, val.day)
        except:
            return pd.NaT
    
    s = str(val).strip().lower().replace(".", "")
    
    # Tenta parse direto (ex: 2024-03-15 ou 15/03/2024)
    try:
        dt = pd.to_datetime(val, dayfirst=True)
        return datetime(ano_atual, dt.month, dt.day)
    except:
        pass
    
    # Mapa de meses para formato '6nov'
    meses = {
        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12
    }
    
    try:
        import re
        match = re.match(r"(\d+)([a-zç]+)", s)
        if match:
            dia = int(match.group(1))
            mes_str = match.group(2)
            if mes_str in meses:
                mes = meses[mes_str]
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


def parse_grupos(val):
    """
    Analisa o conteúdo da célula de grupos (coluna JM).
    Pode conter múltiplos grupos (ex: listbox com separador).
    Retorna uma lista de strings normalizadas.
    """
    if isinstance(val, list):
        return val
    if pd.isna(val) or str(val).strip() == "":
        return []
    
    s_val = str(val).strip()
    # Listbox do Google Sheets geralmente separa por vírgula ou nova linha.
    # Vamos tratar ambos.
    s_val = s_val.replace("\n", ",").replace(";", ",")
    items = [x.strip() for x in s_val.split(",") if x.strip()]
    return items

# ============================================================
# 3. CARGA DE DADOS
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
    df = conn.read(spreadsheet=URL_ANIVERSARIOS, worksheet="TRIPULAÇÃO", header=6, ttl="1h")
    
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

@st.cache_data(ttl=0, show_spinner="Carregando dados de Mar...")
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

@st.cache_data(ttl=600, show_spinner="Carregando metas de férias...")
def load_metas():
    """Carrega dados da aba Metas da planilha de ausências.
    Coluna A (linhas 2-13): meses (Jan-Dez)
    Coluna B (linhas 2-13): meta % acumulada
    Coluna C (linha 1): ano de referência
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=URL_AUSENCIAS, worksheet="Metas", header=None, ttl="10m")
        if df is None or df.empty:
            return pd.DataFrame(), None
        # Ano de referência: célula C1 (index [0, 2])
        ano_ref = None
        try:
            ano_ref = int(float(df.iloc[0, 2]))
        except:
            pass
        # Metas: linhas 2-13 (index 1-12), coluna A=mês, B=meta %
        meses = []
        metas = []
        for i in range(1, 13):
            if i < len(df):
                meses.append(str(df.iloc[i, 0]).strip())
                val = df.iloc[i, 1]
                # Trata valores percentuais (pode vir como 0.05 ou 5 ou "5%")
                try:
                    v = float(str(val).replace("%", "").replace(",", ".").strip())
                    if v <= 1:
                        v = v * 100
                    metas.append(round(v, 1))
                except:
                    metas.append(0.0)
        df_metas = pd.DataFrame({"Mes": meses, "Meta": metas})
        return df_metas, ano_ref
    except Exception as e:
        print(f"Erro ao carregar metas: {e}")
        return pd.DataFrame(), None

@st.cache_data(ttl=600, show_spinner="Carregando datas importantes...")
def load_datas_importantes():
    """Carrega dados da aba Datas_importantes da planilha de ausências.
    A partir da linha 3 (header na linha 2 -> header=1).
    Coluna A: Nome do Evento
    Coluna B: Data Início
    Coluna C: Data Fim
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=URL_AUSENCIAS, worksheet="Datas_importantes", header=None, ttl="10m")
        if df is None or df.empty:
            return pd.DataFrame()
        
        eventos = []
        # Linha 1 = index 0. Linha 2 = index 1. Os dados começam na linha 3 (index 2).
        for i in range(2, len(df)):
            try:
                nome = df.iloc[i, 0]
                dt_inicio_str = df.iloc[i, 1]
                dt_fim_str = df.iloc[i, 2]
                
                if pd.notna(nome) and str(nome).strip() != "" and pd.notna(dt_inicio_str):
                    dt_inicio = pd.to_datetime(dt_inicio_str, dayfirst=True, errors='coerce')
                    dt_fim = pd.to_datetime(dt_fim_str, dayfirst=True, errors='coerce') if pd.notna(dt_fim_str) else dt_inicio
                    if pd.notna(dt_inicio):
                        eventos.append({
                            "Evento": str(nome).strip(),
                            "Inicio": dt_inicio.date(),
                            "Fim": dt_fim.date() if pd.notna(dt_fim) else dt_inicio.date()
                        })
            except Exception as e_row:
                continue
                    
        return pd.DataFrame(eventos)
    except Exception as e:
        print(f"Erro ao carregar datas importantes: {e}")
        return pd.DataFrame()

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

@st.cache_data(ttl=3600, show_spinner="Carregando tempo de bordo...")
def load_tempo_bordo():
    """Carrega dados de tempo de embarque da planilha de Tripulação."""
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Header na linha 7 (index 6). Dados começam na 8.
    df = conn.read(spreadsheet=URL_ANIVERSARIOS, worksheet="TRIPULAÇÃO", header=6, ttl="1h")
    
    # Coluna P é index 15. Vamos pegar pelo nome se possível, ou index fallback.
    # Se header=7 lê a linha 8 como header. A coluna P deve ter um título.
    # Se não tiver, acessamos por iloc.
    col_data = None
    if len(df.columns) > 15:
        col_data = df.iloc[:, 15] # Coluna P
    
    if col_data is None:
        return pd.DataFrame()
        
    return pd.DataFrame({"DataEmbarque": col_data})

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

        # Lógica para encontrar a coluna grupos de forma robusta
        cols_lower = [str(c).lower().strip() for c in row.index]
        grupos_val = []
        
        # Lógica para encontrar a coluna grupos de forma robusta
        # USER REQUEST: Coluna 66 (index 65, 0-based)
        grupos_val = []
        
        try:
            # Tenta encontrar coluna que contém 'conflito' ou 'grupo'
            found_col = None
            for c in row.index:
                c_str = str(c).lower()
                if "conflito" in c_str or "grupo" in c_str:
                    found_col = c
                    break
            
            if found_col:
                grupos_val = row[found_col]
            else:
                # Fallback para o index 65 (Coluna 66 - JM segundo usuario, mas index numerico)
                grupos_val = row.iloc[65]
        except:
             grupos_val = []

        militar_info = {
            "Posto": posto,
            "Nome": nome,
            "Escala": escala,
            "EqMan": eqman,
            "GVI": gvi,
            "IN": insp,
            "Grupos": parse_grupos(grupos_val), 
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
# 6. LÓGICA DE CONFLITOS (NOVO)
# ============================================================
def detectar_conflitos(df_eventos):
    """
    Detecta conflitos de férias entre militares do mesmo grupo.
    Retorna um DataFrame com os conflitos.
    """
    if df_eventos.empty:
        return pd.DataFrame()

    # Considera TODOS os eventos de ausência (Férias, Cursos, Licenças, etc.)
    df_ausencias = df_eventos.copy()
    
    conflict_data = []

    # Explode por grupo para comparar dentro de cada grupo
    # Cada linha será (Pessoa, Grupo, DataIni, DataFim)
    df_exploded = df_ausencias.explode("Grupos")
    df_exploded = df_exploded.dropna(subset=["Grupos"])
    
    # Remove strings vazias que possam ter sobrado
    df_exploded = df_exploded[df_exploded["Grupos"] != ""]
    
    # Agrupa por Grupo
    for grupo, group_df in df_exploded.groupby("Grupos"):
        # Itera pares para achar overlap
        # Otimização: ordenar por data início
        group_df = group_df.sort_values("Inicio")
        records = group_df.to_dict("records")
        
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                p1 = records[i]
                p2 = records[j]
                
                # Se nomes são iguais, não é conflito
                if p1["Nome"] == p2["Nome"]:
                    continue
                    
                # Overlap Check
                if (p1["Inicio"] <= p2["Fim"]) and (p2["Inicio"] <= p1["Fim"]):
                    # Calcula dias de sobreposição
                    start_overlap = max(p1["Inicio"], p2["Inicio"])
                    end_overlap = min(p1["Fim"], p2["Fim"])
                    days_overlap = (end_overlap - start_overlap).days + 1
                    
                    periodo_conflito = f"{start_overlap.strftime('%d/%m')} - {end_overlap.strftime('%d/%m')}"
                    # Inclui o motivo da ausência ao lado do nome
                    motivo_1 = p1.get("MotivoAgrupado", "Ausente")
                    motivo_2 = p2.get("MotivoAgrupado", "Ausente")
                    
                    conflict_data.append({
                        "Grupo": grupo,
                        "Militar 1": f"{p1['Posto']} {p1['Nome']} ({motivo_1})",
                        "Militar 2": f"{p2['Posto']} {p2['Nome']} ({motivo_2})",
                        "Período Conflito": periodo_conflito,
                        "Dias Conflito": days_overlap
                    })

    return pd.DataFrame(conflict_data)


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
    "Adestramento": "cursos.svg",
    "Tabela de Serviço": "icons8-tick-box-50.svg",
    "Tabela de Lotação": "icons8-directory-50.svg",
    "Dados Pessoais": "pessoal.svg",
    "Inspeção de Saúde": "saude.svg",
    "Organograma": "organograma.svg",
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
    
    # Auto-collapse sidebar on mobile
    components.html(
        """
        <script>
        const doc = window.parent.document;
        doc.addEventListener('click', function(e) {
            // Find if the click happened on a sidebar radio label
            if (e.target.closest('[data-testid="stSidebar"] div[role="radiogroup"] label')) {
                if (doc.documentElement.clientWidth <= 768) {
                    setTimeout(function() {
                        const closeBtn = doc.querySelector('button[kind="headerNoPadding"][data-testid="baseButton-headerNoPadding"]') || 
                                         doc.querySelector('[data-testid="stSidebarCollapseButton"] button');
                        if (closeBtn) closeBtn.click();
                        else {
                            const escEvent = new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true });
                            doc.dispatchEvent(escEvent);
                        }
                    }, 100);
                }
            }
        });
        </script>
        """,
        height=0, width=0
    )
    
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
            opt_aus_mes = make_echarts_line(x_dates_aus, df_aus_mes["Militares"].tolist(), integer=True)
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
                    # Limita as datas ao mês selecionado
                    ultimo_dia_mes = end_date - timedelta(days=1)
                    _meses_abrev = {1:"JAN",2:"FEV",3:"MAR",4:"ABR",5:"MAI",6:"JUN",7:"JUL",8:"AGO",9:"SET",10:"OUT",11:"NOV",12:"DEZ"}
                    ini_clamp = tabela_mes["Inicio"].clip(lower=pd.Timestamp(start_date))
                    fim_clamp = tabela_mes["Fim"].clip(upper=pd.Timestamp(ultimo_dia_mes))
                    tabela_mes["Período"] = ini_clamp.dt.day.astype(str).str.zfill(2) + " a " + fim_clamp.dt.day.astype(str).str.zfill(2) + fim_clamp.dt.month.map(_meses_abrev)
                    tabela_mes = tabela_mes.rename(columns={"MotivoAgrupado": "Motivo"})
                    tabela_mes = tabela_mes[["Posto", "Nome", "Motivo", "Período"]]
                    tabela_mes = tabela_mes.sort_values(by=["Nome"])
                    st.dataframe(tabela_mes, use_container_width=True, hide_index=True)
                
                df_aus_dia = (df_dias_mes.groupby("Data")["Nome"].nunique().reset_index(name="Militares"))
                
                st.markdown(f"##### Ausências diárias em {sel_mes_nome_aus}/{sel_ano_aus}")
                x_dates_dia = df_aus_dia["Data"].dt.strftime("%d/%m").tolist()
                opt_aus_dia = make_echarts_line(x_dates_dia, df_aus_dia["Militares"].tolist(), integer=True)
                st_echarts(options=opt_aus_dia, height="400px")
        else:
             st.info("Sem dados para gerar gráficos com os filtros atuais.")
    else:
        st.info("Sem dados de ausências para gerar gráficos.")

    st.markdown("---")
    
    # --- CONFLITOS DE AUSÊNCIA POR GRUPO (MOVIDO DA ABA FÉRIAS) ---
    st.markdown("### Conflitos de Ausência por Grupo")
    df_conflitos = detectar_conflitos(df_eventos)
    
    if not df_conflitos.empty:
        # Formata e exibe
        st.warning(f"Foram detectados {len(df_conflitos)} conflitos coincidentes entre militares do mesmo grupo.")
        
        # Ordena por Grupo e Militar 1
        df_conflitos = df_conflitos.sort_values(["Grupo", "Militar 1"])
        
        st.dataframe(
            df_conflitos,
            column_config={
                "Grupo": st.column_config.TextColumn("Grupo de Conflito"),
                "Militar 1": st.column_config.TextColumn("Militar 1"),
                "Militar 2": st.column_config.TextColumn("Militar 2"),
                "Período Conflito": st.column_config.TextColumn("Período Coincidente"),
                "Dias Conflito": st.column_config.NumberColumn("Dias", format="%d"),
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("Não foram detectados conflitos de ausência entre militares do mesmo grupo.")

    st.markdown("---")
    
    # --- AVISO DE DATAS IMPORTANTES (MOVIDO PARA O FINAL) ---
    df_importantes = load_datas_importantes()
    
    if not df_importantes.empty and not df_eventos.empty:
        # Verifica conflitos entre eventos_importantes e ausentes_futuros
        hoje = datetime.today().date()
        conflitos_importantes = []
        
        for _, evento_imp in df_importantes.iterrows():
            nome_evento = evento_imp["Evento"]
            ini_evento = evento_imp["Inicio"]
            fim_evento = evento_imp["Fim"]
            
            # Só avisa de eventos que ainda não passaram
            if fim_evento >= hoje:
                # Extrai apenas as datas para comparação
                mask_intersecao = (df_eventos["Inicio"].dt.date <= fim_evento) & (df_eventos["Fim"].dt.date >= ini_evento)
                ausentes_no_evento = df_eventos[mask_intersecao]
                
                if not ausentes_no_evento.empty:
                    # Agrupar nomes com seus respectivos motivos
                    ausentes_lista = []
                    for _, row_aus in ausentes_no_evento.iterrows():
                        nome = str(row_aus["Nome"]).strip()
                        motivo = str(row_aus["MotivoAgrupado"]).strip() if "MotivoAgrupado" in row_aus else "N/I"
                        if nome and nome != "nan":
                            ausentes_lista.append(f"{nome} ({motivo})")
                    
                    # Remover duplicatas mantendo a ordem (caso a mesma pessoa tenha 2 eventos no período)
                    ausentes_unicos = []
                    for ausente in ausentes_lista:
                        if ausente not in ausentes_unicos:
                            ausentes_unicos.append(ausente)
                            
                    if len(ausentes_unicos) > 0:
                        qtd = len(ausentes_unicos)
                        str_periodo = f"{ini_evento.strftime('%d/%m/%Y')} a {fim_evento.strftime('%d/%m/%Y')}" if ini_evento != fim_evento else f"{ini_evento.strftime('%d/%m/%Y')}"
                        str_nomes = ", ".join(ausentes_unicos)
                        
                        conflitos_importantes.append(f"**{nome_evento}** ({str_periodo}): {qtd} militar(es) ausente(s) - {str_nomes}")
        
        if conflitos_importantes:
            st.error("AVISO: Conflito com Datas Importantes! Existem militares ausentes durante os seguintes eventos:")
            for aviso in conflitos_importantes:
                st.write(f"- {aviso}")
        else:
            st.success("Não há militares com ausências previstas para períodos de datas importantes.")


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
            opt_ano = make_echarts_line(df_por_ano["ANO"].astype(str).tolist(), df_por_ano["DIAS DE MAR"].tolist(), integer=True)
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
                        opt_mes_mar = make_echarts_line(df_completo["Mês"].tolist(), df_completo["DIAS DE MAR"].tolist(), integer=True)
                        st_echarts(options=opt_mes_mar, height="400px")
                        
                        with st.expander("Ver dados brutos do ano selecionado"):
                            st.dataframe(df_mar_ano[["TERMO DE VIAGEM", "DATA INÍCIO", "DATA TÉRMINO", "DIAS DE MAR", "MILHAS NAVEGADAS"]], use_container_width=True)
                    else:
                        st.warning("Coluna 'DATA INÍCIO' não encontrada ou inválida.")
                else:
                    st.info(f"Sem dados de dias de mar para o ano {ano_sel_mar}.")
            st.markdown("---")
    
            
            # Filtro por Período Personalizado
            st.subheader("Consulta por Período")
            col_p1, col_p2 = st.columns(2)
            data_ini_mar = col_p1.date_input("Data Início", value=datetime(datetime.today().year, 1, 1), key="mar_ini", format="DD/MM/YYYY")
            data_fim_mar = col_p2.date_input("Data Fim", value=datetime.today(), key="mar_fim", format="DD/MM/YYYY")
            
            dt_ini_mar = pd.to_datetime(data_ini_mar)
            dt_fim_mar = pd.to_datetime(data_fim_mar)
            
            if "DATA INÍCIO" in df_mar.columns:
                mask_periodo = (
                    (df_mar["DATA INÍCIO"] >= dt_ini_mar) & 
                    (df_mar["DATA INÍCIO"] <= dt_fim_mar)
                )
                df_mar_periodo = df_mar[mask_periodo].copy()
                
                if df_mar_periodo.empty:
                    st.info(f"Sem registros de dias de mar no período selecionado.")
                else:
                    total_dias_periodo = df_mar_periodo["DIAS DE MAR"].sum()
                    total_milhas_periodo = df_mar_periodo["MILHAS NAVEGADAS"].sum()
                    total_comissoes = len(df_mar_periodo)
                    
                    cp1, cp2, cp3 = st.columns(3)
                    cp1.metric("Dias de Mar (período)", f"{int(total_dias_periodo)}")
                    cp2.metric("Milhas Navegadas (período)", f"{int(total_milhas_periodo)}")
                    cp3.metric("Comissões (período)", total_comissoes)
                    
                    with st.expander("Ver dados do período"):
                        df_show_periodo = df_mar_periodo[["TERMO DE VIAGEM", "DATA INÍCIO", "DATA TÉRMINO", "DIAS DE MAR", "MILHAS NAVEGADAS"]].copy()
                        st.dataframe(df_show_periodo, use_container_width=True, hide_index=True)
            else:
                st.warning("Coluna 'DATA INÍCIO' não encontrada para filtro por período.")

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
                    col_a3.metric("Média de dias de férias por militar", f"{media_dias_ferias:.1f}")
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
    
                    
                    # --- GRÁFICO 1: % de militares de férias por mês ---
                    if not df_dias.empty:
                        df_dias_ferias = df_dias[df_dias["Tipo"] == "Férias"].copy()
                        if not df_dias_ferias.empty:
                            df_dias_ferias["Mes"] = df_dias_ferias["Data"].dt.to_period("M").dt.to_timestamp()
                            df_mes_ferias = (df_dias_ferias[["Mes", "Nome"]].drop_duplicates()
                                             .groupby("Mes")["Nome"].nunique().reset_index(name="Militares"))
                            total_efetivo_ferias = df_raw["Nome"].nunique()
                            df_mes_ferias["Perc"] = (df_mes_ferias["Militares"] / total_efetivo_ferias * 100).round(1)

                            st.markdown("##### % de militares de férias por mês")
                            x_mes_ferias = df_mes_ferias["Mes"].dt.strftime("%b/%Y").tolist()
                            # Formata labels como percentual
                            y_perc_fmt = [f"{v:.1f}" for v in df_mes_ferias["Perc"].tolist()]
                            opt_perc_ferias = {
                                "xAxis": {"type": "category", "data": x_mes_ferias, "axisLabel": {"interval": 0, "rotate": 30}},
                                "yAxis": {"type": "value", "axisLabel": {"formatter": "{value}%"}},
                                "series": [{"data": y_perc_fmt, "type": "bar",
                                    "label": {"show": True, "position": "top", "fontSize": 12, "formatter": "{c}%"},
                                    "itemStyle": {"color": "#4099ff"}
                                }],
                                "tooltip": {"trigger": "axis", "backgroundColor": "rgba(50,50,50,0.9)", "borderColor": "#777", "textStyle": {"color": "#fff"}}
                            }
                            st_echarts(options=opt_perc_ferias, height="400px")

                            st.markdown("---")
    

                            # --- GRÁFICO 2: Férias por serviço por mês (barras agrupadas) ---
                            st.markdown("##### Militares de férias por serviço (por mês)")
                            servicos_filtro = SERVICOS_CONSIDERADOS
                            df_dias_ferias_srv = df_dias_ferias[df_dias_ferias["Escala"].isin(servicos_filtro)].copy()
                            if not df_dias_ferias_srv.empty:
                                # Agrupar por mês e serviço
                                df_srv_mes = (df_dias_ferias_srv[["Mes", "Nome", "Escala"]].drop_duplicates()
                                              .groupby(["Mes", "Escala"])["Nome"].nunique().reset_index(name="Militares"))
                                meses_unicos = sorted(df_srv_mes["Mes"].unique())
                                mapa_meses_abrev = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
                                x_meses = [mapa_meses_abrev.get(m.month, str(m.month)) + "/" + str(m.year) for m in meses_unicos]
                                series_srv = []
                                for srv in servicos_filtro:
                                    vals = []
                                    for m in meses_unicos:
                                        v = df_srv_mes[(df_srv_mes["Mes"] == m) & (df_srv_mes["Escala"] == srv)]["Militares"].sum()
                                        vals.append(int(v))
                                    series_srv.append({"name": srv, "data": vals})
                                opt_grouped = make_echarts_grouped_bar(x_meses, series_srv)
                                st_echarts(options=opt_grouped, height="500px")
                            else:
                                st.info("Sem dados de férias para os serviços considerados.")

                            st.markdown("---")
    

                            # --- GRÁFICO 3: % férias gozadas vs Meta ---
                            st.markdown("##### % de férias gozadas vs Meta")
                            try:
                                df_metas, ano_ref_metas = load_metas()
                                if not df_metas.empty and ano_ref_metas:
                                    st.caption(f"Ano de referência: **{ano_ref_metas}**")
                                    # Calcular % realizado acumulado por mês
                                    # Usar df_dias_ferias filtrado pelo ano de referência
                                    df_ferias_ano = df_dias_ferias[df_dias_ferias["Data"].dt.year == ano_ref_metas].copy()
                                    mapa_meses_nome = {1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
                                                       7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}
                                    total_efetivo_meta = df_raw["Nome"].nunique()
                                    # Total de dias de férias esperado (30 dias/militar em média)
                                    total_dias_esperado = total_efetivo_meta * 30

                                    # Calcular dias de férias acumulados por mês
                                    realizado_acum = []
                                    dias_acumulados = 0
                                    for mes_num in range(1, 13):
                                        dias_mes = len(df_ferias_ano[df_ferias_ano["Data"].dt.month == mes_num])
                                        dias_acumulados += dias_mes
                                        perc = (dias_acumulados / total_dias_esperado * 100) if total_dias_esperado > 0 else 0
                                        realizado_acum.append(round(perc, 1))

                                    x_metas = df_metas["Mes"].tolist()
                                    y_metas = df_metas["Meta"].tolist()
                                    opt_metas = make_echarts_dual_line(x_metas, y_metas, realizado_acum, "Meta", "Realizado")
                                    st_echarts(options=opt_metas, height="400px")
                                else:
                                    st.info("Não foi possível carregar as metas de férias.")
                            except Exception as e:
                                st.warning(f"Erro ao carregar gráfico de metas: {e}")
                        else:
                            st.info("Sem dados diários suficientes para gerar gráficos de férias.")

                    st.markdown("---")
    

    elif pagina == "Adestramento":
        st.subheader("Adestramento")
        content_container = st.container()
        with content_container:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                
                # Lendo as abas usando header=None para navegar explicitamente por índices de linhas e colunas
                df_ofi = conn.read(spreadsheet=URL_ADESTRAMENTO, worksheet="GERAL - OFICIAIS", header=None, ttl="10m")
                df_pra = conn.read(spreadsheet=URL_ADESTRAMENTO, worksheet="GERAL - PRAÇAS", header=None, ttl="10m")
                df_pqs = conn.read(spreadsheet=URL_ADESTRAMENTO, worksheet="PQS", header=None, ttl="10m")
                
                # --- PARSER - OFICIAIS ---
                # Cursos = linha 7 (index 6), colunas D:AE (3:31)
                cursos_ofi = [str(c).strip() for c in df_ofi.iloc[6, 3:31].tolist()]
                # Requisitos = linha 3 (index 2)
                req_ofi = [int(float(x)) if pd.notna(x) and str(x).strip() != "" else 0 for x in df_ofi.iloc[2, 3:31].tolist()]
                
                militares_ofi = []
                for i in range(7, len(df_ofi)):
                    ng = str(df_ofi.iloc[i, 1]).strip()
                    if not ng or ng.lower() == "nan":
                        continue
                    nc = str(df_ofi.iloc[i, 2]).strip()
                    mil = {"guerra": ng, "completo": nc, "cursos": []}
                    for j in range(3, 31):
                        val = str(df_ofi.iloc[i, j]).strip()
                        if val == "1" or val == "1.0":
                            # Verifica se a coluna tem um nome de curso válido antes de mapear
                            if j-3 < len(cursos_ofi) and cursos_ofi[j-3].lower() != "nan":
                                mil["cursos"].append(cursos_ofi[j-3])
                    militares_ofi.append(mil)
                    
                totais_ofi = [0] * len(cursos_ofi)
                for mil in militares_ofi:
                    for c in mil["cursos"]:
                        if c in cursos_ofi:
                            idx = cursos_ofi.index(c)
                            totais_ofi[idx] += 1
                            
                # --- PARSER - PRAÇAS ---
                # Cursos = linha 7 (index 6), colunas D:BH (3:60)
                cursos_pra = [str(c).strip() for c in df_pra.iloc[6, 3:60].tolist()]
                # Requisitos = linha 3 (index 2)
                req_pra = [int(float(x)) if pd.notna(x) and str(x).strip() != "" else 0 for x in df_pra.iloc[2, 3:60].tolist()]
                
                militares_pra = []
                for i in range(7, len(df_pra)):
                    ng = str(df_pra.iloc[i, 1]).strip()
                    if not ng or ng.lower() == "nan":
                        continue
                    nc = str(df_pra.iloc[i, 2]).strip()
                    mil = {"guerra": ng, "completo": nc, "cursos": []}
                    for j in range(3, 60):
                        if j < len(df_pra.columns):
                            val = str(df_pra.iloc[i, j]).strip()
                            if val == "1" or val == "1.0":
                                if j-3 < len(cursos_pra) and cursos_pra[j-3].lower() != "nan":
                                    mil["cursos"].append(cursos_pra[j-3])
                    militares_pra.append(mil)
                    
                totais_pra = [0] * len(cursos_pra)
                for mil in militares_pra:
                    for c in mil["cursos"]:
                        if c in cursos_pra:
                            idx = cursos_pra.index(c)
                            totais_pra[idx] += 1
                            
                # Agrupando todos os dados de cursos para as listas matemáticas
                dados_cursos = []
                for i, c in enumerate(cursos_ofi):
                    if c and c.lower() != "nan" and c != "":
                        dados_cursos.append({"Curso": c, "Real": totais_ofi[i], "Requisito": req_ofi[i]})
                for i, c in enumerate(cursos_pra):
                    if c and c.lower() != "nan" and c != "":
                        dados_cursos.append({"Curso": c, "Real": totais_pra[i], "Requisito": req_pra[i]})
                        
                # Classificadores Matemáticos 
                deficit = [d for d in dados_cursos if d["Real"] < d["Requisito"]]
                excesso = [d for d in dados_cursos if d["Real"] > d["Requisito"]]
                rmc     = [d for d in dados_cursos if d["Real"] == d["Requisito"] and d["Requisito"] > 0]
                
                # --- VISÃO GLOBAL ---
                tab_estatistica, tab_militar, tab_pqs = st.tabs(["Estatísticas RMC", "Pesquisa por Militar", "Qualificação PQS"])
                
                with tab_estatistica:
                    st.markdown("### Situação Global dos Cursos")
                    
                    df_grafico = pd.DataFrame(dados_cursos)
                    df_grafico = df_grafico[df_grafico["Requisito"] > 0] # Filtra os invalidos
                    df_grafico = df_grafico.sort_values(by="Requisito", ascending=False).head(20) # Top 20 para o grafico de barras
                    
                    if not df_grafico.empty:
                        opt_bar = make_echarts_grouped_bar(
                            x_data=df_grafico["Curso"].tolist(),
                            series_list=[
                                {"name": "Realizados", "data": df_grafico["Real"].tolist()},
                                {"name": "Requisito", "data": df_grafico["Requisito"].tolist()}
                            ]
                        )
                        st_echarts(options=opt_bar, height="450px")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander("Revelar Painel de Cursos (Déficit, Excesso e RMC)"):
                        df_deficit = pd.DataFrame(deficit)
                        df_excesso = pd.DataFrame(excesso)
                        df_rmc = pd.DataFrame(rmc)
                        
                        tb_c1, tb_c2, tb_c3 = st.columns(3)
                        
                        with tb_c1:
                            st.markdown("#### Déficit")
                            if not df_deficit.empty:
                                st.dataframe(df_deficit, use_container_width=True, hide_index=True)
                            else:
                                st.info("Nenhum curso em déficit.")
                                
                        with tb_c2:
                            st.markdown("#### Excesso")
                            if not df_excesso.empty:
                                st.dataframe(df_excesso, use_container_width=True, hide_index=True)
                            else:
                                st.info("Nenhum curso em excesso.")
                                
                        with tb_c3:
                            st.markdown("#### Dentro da RMC")
                            if not df_rmc.empty:
                                st.dataframe(df_rmc, use_container_width=True, hide_index=True)
                            else:
                                st.info("Nenhum curso encontrado exato na RMC.")

                with tab_militar:
                    st.markdown("### Histórico do Militar")
                    # Unifica as listas iteráveis para o dropdown
                    todos_militares = militares_ofi + militares_pra
                    opcoes_nomes = [f"{m['guerra']} - {m['completo']}" for m in todos_militares]
                    
                    selecionado = st.selectbox("Selecione o militar:", opcoes_nomes)
                    if selecionado:
                        militar_obj = next((m for m in todos_militares if f"{m['guerra']} - {m['completo']}" == selecionado), None)
                        if militar_obj:
                            st.markdown(f"**Cursos concluídos ({len(militar_obj['cursos'])})**")
                            for c in militar_obj["cursos"]:
                                st.write(f"- {c}")
                                
                with tab_pqs:
                    st.markdown("### Qualificação PQS")
                    
                    if df_pqs.shape[1] > 19:
                        col_t = df_pqs.iloc[1:, 19].dropna().astype(str).str.strip().str.upper()
                        concluidos = len(col_t[col_t == "CONCLUÍDO"])
                        qualificando = len(col_t[col_t == "QUALIFICANDO"])
                        
                        if concluidos == 0 and qualificando == 0:
                            st.info("Sem dados estatísticos de PQS na coluna T.")
                        else:
                            opt_pqs = make_echarts_donut(
                                data_list=[
                                    {"value": concluidos, "name": "Concluído"},
                                    {"value": qualificando, "name": "Qualificando"}
                                ],
                                title="Status de Qualificação"
                            )
                            st_echarts(options=opt_pqs, height="450px")
                    else:
                        st.error("A aba PQS não possui a Coluna T.")
                    
            except Exception as e:
                st.error(f"Erro ao carregar os dados de Adestramento: {e}")

    elif pagina == "Tabela de Serviço":
        st.subheader("Tabela de Serviço")
        
        tab_dia, tab_analise = st.tabs(["Tabela do Dia", "Análise"])
        
        with tab_dia:
            st.markdown("### Escala do Dia")
            
            # Carregar dados
            data_sheets = load_tabela_servico_dia()
            
            # Data de hoje (UTC-3)
            hoje = (datetime.utcnow() - timedelta(hours=3)).date()
            # hoje = datetime(2025, 12, 11).date() # DEBUG
            
            found_matches = []
            
            if data_sheets:
                for sheet_name, df in data_sheets.items():
                    # Layout CONFIRMED by debug:
                    # Block 1: Date at Row 5 (Index 4), Col B (Index 1). Daily Service: Rows 7-10 (Indices 6-9), Col C (Index 2). Room: Row 14 (Index 13).
                    # Block 2: Date at Row 16 (Index 15), Col B (Index 1). Daily Service: Rows 18-21 (Indices 17-20), Col C (Index 2). Room: Row 25 (Index 24).
                    # Block 3: Date at Row 27 (Index 26), Col B (Index 1). Daily Service: Rows 29-32 (Indices 28-31), Col C (Index 2). Room: Row 36 (Index 35).
                    
                    blocks = [
                        {"date_idx": 4,  "daily_start": 6,  "daily_end": 10, "room_idx": 13},
                        {"date_idx": 15, "daily_start": 17, "daily_end": 21, "room_idx": 24},
                        {"date_idx": 26, "daily_start": 28, "daily_end": 32, "room_idx": 35}
                    ]
                    
                    for block in blocks:
                        d_idx = block["date_idx"]
                        
                        if d_idx < len(df):
                            # Date is in Column B (index 1)
                            val = df.iloc[d_idx, 1] if df.shape[1] > 1 else None
                            
                            # Parse date
                            dt_val = None
                            try:
                                if isinstance(val, str):
                                    val_clean = val.strip()
                                    dt_val = pd.to_datetime(val_clean, dayfirst=True, errors='coerce').date()
                                elif isinstance(val, (datetime, pd.Timestamp)):
                                    dt_val = val.date()
                            except:
                                pass
                            
                            if dt_val == hoje:
                                # Found a match! Extract data.
                                match_data = {}
                                match_data["sheet_name"] = sheet_name
                                
                                # Extract Header Info
                                dia_semana = ""
                                regime = ""
                                rotina = ""
                                por_do_sol = ""
                                
                                if d_idx > 0:
                                    try:
                                        dia_semana = str(df.iloc[d_idx - 1, 1]).strip() # Col B
                                        regime = str(df.iloc[d_idx - 1, 3]).strip()     # Col D
                                    except:
                                        pass
                                
                                try:
                                    rotina = str(df.iloc[d_idx, 3]).strip()         # Col D
                                    por_do_sol = str(df.iloc[d_idx, 4]).strip()     # Col E
                                    
                                    # Sanitize Pôr do Sol error from Sheets
                                    if "ERROR" in por_do_sol or "Exception" in por_do_sol or por_do_sol == "-" or por_do_sol == "":
                                        # Calculate locally
                                        por_do_sol = calculate_sunset(hoje)
                                except:
                                    pass
                                
                                match_data["header"] = {
                                    "dia_semana": dia_semana,
                                    "regime": regime,
                                    "rotina": rotina,
                                    "por_do_sol": por_do_sol
                                }

                                # Extract Daily Service
                                s_start = block["daily_start"]
                                s_end = block["daily_end"]
                                servico_diario = []
                                if s_end <= len(df) and df.shape[1] > 2:
                                    servico_diario = df.iloc[s_start : s_end, 2].tolist()
                                match_data["servico_diario"] = servico_diario
                                
                                # Extract Room Service
                                r_idx = block["room_idx"]
                                servico_quarto = []
                                if r_idx < len(df) and df.shape[1] > 4:
                                    servico_quarto = df.iloc[r_idx, 2:5].tolist()
                                match_data["servico_quarto"] = servico_quarto
                                
                                found_matches.append(match_data)
                
                # Logic to handle matches
                if len(found_matches) > 1:
                    st.warning(f"Há mais de uma tabela com a data cadastrada ({hoje.strftime('%d/%m/%Y')}). Por favor, verifique a planilha.")
                elif len(found_matches) == 1:
                    match = found_matches[0]
                    
                    # CSS for Cards (Dark Gray in Dark Mode, White in Light Mode)
                    st.markdown("""
                    <style>
                        /* Base Card Style */
                        .service-card, .service-card-room, .header-info-card {
                            /* 
                               Use a semi-transparent white background.
                               - In Dark Mode (Dark BG): Renders as Dark Gray (Lightens the background).
                               - In Light Mode (White BG): Renders as White (Invisible change).
                            */
                            background-color: rgba(255, 255, 255, 0.07); 
                            color: var(--text-color);
                            border-radius: 5px;
                            padding: 15px;
                            margin-bottom: 10px;
                            transition: transform 0.2s;
                            border: 1px solid rgba(128, 128, 128, 0.2);
                            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                        }
                        
                        /* Specific Stripes */
                        .service-card { border-left: 5px solid #3b82f6; } /* Blue */
                        .service-card-room { border-left: 5px solid #10b981; } /* Green */
                        .header-info-card { border-left: 5px solid #f59e0b; text-align: center; } /* Amber */

                        /* Text Styles */
                        .service-title, .header-label {
                            color: var(--text-color);
                            opacity: 0.8;
                            font-size: 0.85rem;
                            text-transform: uppercase;
                            letter-spacing: 0.05em;
                            font-weight: 600;
                            margin-bottom: 5px;
                        }
                        .service-value, .header-val {
                            color: var(--text-color);
                            font-size: 1.1rem;
                            font-weight: 500;
                        }
                        .service-time, .service-time-inline {
                            color: var(--text-color);
                            opacity: 0.7;
                            font-size: 0.8rem;
                        }
                        .service-header-inline {
                            display: flex;
                            align-items: baseline;
                            gap: 10px;
                            margin-bottom: 5px;
                        }
                    </style>
                    """, unsafe_allow_html=True)

                    st.markdown(f"### Escala de Hoje ({hoje.strftime('%d/%m/%Y')})")
                    st.caption(f"Fonte: {match['sheet_name']}")
                    
                    # --- HEADER INFO ---
                    h = match["header"]
                    c_h1, c_h2, c_h3, c_h4 = st.columns(4)
                    with c_h1:
                        st.markdown(f"""
                        <div class="header-info-card">
                            <div class="header-label">Dia da Semana</div>
                            <div class="header-val">{h['dia_semana']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c_h2:
                        st.markdown(f"""
                        <div class="header-info-card">
                            <div class="header-label">Regime</div>
                            <div class="header-val">{h['regime']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c_h3:
                        st.markdown(f"""
                        <div class="header-info-card">
                            <div class="header-label">Rotina</div>
                            <div class="header-val">{h['rotina']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c_h4:
                        st.markdown(f"""
                        <div class="header-info-card">
                            <div class="header-label">Pôr do Sol</div>
                            <div class="header-val">{h['por_do_sol']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("---")
    

                    # --- SERVIÇO DIÁRIO ---
                    st.markdown("#### Serviço Diário")
                    labels_diario = ["Oficial / Sup", "Fiel de Cav", "Conferente", "Rancheiro"]
                    servico_diario = match["servico_diario"]
                    
                    cd1, cd2 = st.columns(2)
                    
                    for i, item in enumerate(servico_diario):
                        label = labels_diario[i] if i < len(labels_diario) else "Outro"
                        if pd.notna(item) and str(item).strip() != "":
                            col_to_use = cd1 if i % 2 == 0 else cd2
                            with col_to_use:
                                    # Format Name and CPF
                                    name_part = str(item)
                                    cpf_part = ""
                                    if "CPF:" in name_part:
                                        parts = name_part.split("CPF:")
                                        name_part = parts[0].strip()
                                        cpf_part = "CPF: " + parts[1].strip()
                                    
                                    st.markdown(f"""
                                    <div class="service-card">
                                        <div class="service-title">{label}</div>
                                        <div class="service-value">
                                            <div style="font-weight: bold;">{name_part}</div>
                                            <div style="font-size: 0.85em; opacity: 0.7; margin-top: 2px;">{cpf_part}</div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                    st.markdown("---")
    
                    
                    # --- SERVIÇO DE QUARTO ---
                    st.markdown("#### Serviço de Quarto")
                    labels_quarto = [
                        ("1º QUARTO", "08:00 - 12:00 / 20:00 - 24:00"),
                        ("2º QUARTO", "12:00 - 16:00 / 00:00 - 04:00"),
                        ("3º QUARTO", "16:00 - 20:00 / 04:00 - 08:00")
                    ]
                    servico_quarto = match["servico_quarto"]
                    
                    for i, item in enumerate(servico_quarto):
                        label_info = labels_quarto[i] if i < len(labels_quarto) else ("Outro", "")
                        label_title = label_info[0]
                        label_time = label_info[1]
                        
                        if pd.notna(item) and str(item).strip() != "":
                            # Format Name and CPF
                            name_part = str(item)
                            cpf_part = ""
                            if "CPF:" in name_part:
                                parts = name_part.split("CPF:")
                                name_part = parts[0].strip()
                                cpf_part = "CPF: " + parts[1].strip()

                            st.markdown(f"""
                            <div class="service-card-room">
                                <div class="service-header-inline">
                                    <div class="service-title">{label_title}</div>
                                    <div class="service-time-inline">{label_time}</div>
                                </div>
                                <div class="service-value">
                                    <div style="font-weight: bold;">{name_part}</div>
                                    <div style="font-size: 0.85em; opacity: 0.7; margin-top: 2px;">{cpf_part}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                
                else:
                    # No matches found
                    st.info(f"Nenhuma escala encontrada para a data de hoje ({hoje.strftime('%d/%m/%Y')}) nas abas verificadas.")
            else:
                st.error("Erro ao carregar dados da Tabela de Serviço.")

        with tab_analise:
            st.markdown("### Análise de Escalas")
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
                            
                        # Tradução do 'idem' no Jantar para o Almoço
                        jantar_val = str(day_data.get("Jantar", "")).strip().lower()
                        if "idem" in jantar_val and day_data.get("Almoço"):
                            day_data["Jantar"] = day_data["Almoço"]
                        
                        structured_data.append(day_data)
                        
                    df_menu = pd.DataFrame(structured_data)
                    
                    # --- CSS GLOBAL CARDÁPIO ---
                    st.markdown("""
                    <style>
                        .card-menu {
                            background-color: rgba(255, 255, 255, 0.07);
                            color: var(--text-color);
                            border-radius: 5px;
                            padding: 15px;
                            margin-bottom: 15px;
                            transition: transform 0.2s;
                            border: 1px solid rgba(128, 128, 128, 0.2);
                            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                            border-left: 5px solid #f97316; /* Orange */
                            min-height: 150px; /* Garante tamanho uniforme */
                            display: flex;
                            flex-direction: column;
                            justify-content: center;
                        }
                        .card-title {
                            color: var(--text-color);
                            opacity: 0.8;
                            font-size: 0.85rem;
                            text-transform: uppercase;
                            letter-spacing: 0.05em;
                            font-weight: 600;
                            margin-bottom: 5px;
                        }
                        .card-value {
                            color: var(--text-color);
                            font-size: 1.1rem;
                            font-weight: 500;
                        }
                    </style>
                    """, unsafe_allow_html=True)

                    # --- VISÃO DIÁRIA ---
                    st.markdown("### Cardápio do Dia")
                    hoje_date = (datetime.utcnow() - timedelta(hours=3)).date()
                    
                    # Filtra para hoje (compara apenas a data)
                    df_hoje = df_menu[df_menu["Data"].dt.date == hoje_date]
                    
                    if not df_hoje.empty:
                        row = df_hoje.iloc[0]
                        c1, c2, c3, c4 = st.columns(4)
                        
                        with c1:
                            val = row["Café da Manhã"] if pd.notna(row["Café da Manhã"]) else "-"
                            st.markdown(f'<div class="card-menu"><div class="card-title">Café da Manhã</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)
                        with c2:
                            val = row["Almoço"] if pd.notna(row["Almoço"]) else "-"
                            st.markdown(f'<div class="card-menu"><div class="card-title">Almoço</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)
                        with c3:
                            val = row["Jantar"] if pd.notna(row["Jantar"]) else "-"
                            st.markdown(f'<div class="card-menu"><div class="card-title">Jantar</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)
                        with c4:
                            val = row["Ceia"] if pd.notna(row["Ceia"]) else "-"
                            st.markdown(f'<div class="card-menu"><div class="card-title">Ceia</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)
                    else:
                        st.info(f"Não há cardápio cadastrado para hoje ({hoje_date.strftime('%d/%m/%Y')}).")
                    
                    st.markdown("---")

                    # --- VISÃO DE AMANHÃ ---
                    st.markdown("### Cardápio de Amanhã")
                    amanha_date = hoje_date + timedelta(days=1)
                    df_amanha = df_menu[df_menu["Data"].dt.date == amanha_date]
                    
                    if not df_amanha.empty:
                        row_am = df_amanha.iloc[0]
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            val = row_am["Café da Manhã"] if pd.notna(row_am["Café da Manhã"]) else "-"
                            st.markdown(f'<div class="card-menu" style="border-left-color: #3b82f6;"><div class="card-title">Café da Manhã</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)
                        with c2:
                            val = row_am["Almoço"] if pd.notna(row_am["Almoço"]) else "-"
                            st.markdown(f'<div class="card-menu" style="border-left-color: #3b82f6;"><div class="card-title">Almoço</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)
                        with c3:
                            val = row_am["Jantar"] if pd.notna(row_am["Jantar"]) else "-"
                            st.markdown(f'<div class="card-menu" style="border-left-color: #3b82f6;"><div class="card-title">Jantar</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)
                        with c4:
                            val = row_am["Ceia"] if pd.notna(row_am["Ceia"]) else "-"
                            st.markdown(f'<div class="card-menu" style="border-left-color: #3b82f6;"><div class="card-title">Ceia</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)
                    else:
                        st.info(f"Não há cardápio cadastrado para amanhã ({amanha_date.strftime('%d/%m/%Y')}).")
                    
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
                # Colunas esperadas: D (Posto), G (Nome), M (Data Nascimento DD/MM/AAAA)
                
                # Ajuste de índices (0-based): D=3, G=6, M=12
                # Cria um DF limpo
                dados_niver = []
                
                # Itera sobre as linhas (pulando header se necessário, mas o read já deve ter tratado)
                for idx, row in df_niver_raw.iterrows():
                    try:
                        posto = row.iloc[3]
                        nome = row.iloc[6]
                        data_str = row.iloc[12]  # Coluna M
                        
                        if pd.notna(nome) and str(nome).strip() != "" and pd.notna(data_str):
                            # Parse da data de nascimento completa
                            dt_nasc = pd.to_datetime(data_str, dayfirst=True, errors='coerce')
                            if pd.isna(dt_nasc):
                                dt_nasc = parse_aniversario_date(data_str)
                            
                            if pd.notna(dt_nasc):
                                ano_atual = (datetime.utcnow() - timedelta(hours=3)).year
                                idade = ano_atual - dt_nasc.year
                                dt_niver = datetime(ano_atual, dt_nasc.month, dt_nasc.day)
                                dados_niver.append({
                                    "Posto": posto,
                                    "Nome": nome,
                                    "DataOriginal": data_str,
                                    "Data": dt_niver,
                                    "Dia": dt_niver.day,
                                    "Mês": dt_niver.month,
                                    "Idade": idade
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
                    # CSS for Aniversários Cards
                    st.markdown("""
                    <style>
                        .card-niver {
                            background-color: rgba(255, 255, 255, 0.07);
                            color: var(--text-color);
                            border-radius: 5px;
                            padding: 15px;
                            margin-bottom: 10px;
                            transition: transform 0.2s;
                            border: 1px solid rgba(128, 128, 128, 0.2);
                            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                            border-left: 5px solid #ec4899; /* Pink */
                            min-height: 150px;
                            display: flex;
                            flex-direction: column;
                            justify-content: center;
                        }
                        /* Reuse .card-title and .card-value if already defined, but define here to be safe if tabs are separate */
                        .card-title {
                            color: var(--text-color);
                            opacity: 0.8;
                            font-size: 0.85rem;
                            text-transform: uppercase;
                            letter-spacing: 0.05em;
                            font-weight: 600;
                            margin-bottom: 5px;
                        }
                        .card-value {
                            color: var(--text-color);
                            font-size: 1.1rem;
                            font-weight: 500;
                        }
                    </style>
                    """, unsafe_allow_html=True)

                    with c2:
                        if aniversariantes_dia.empty:
                            val = "Ninguém hoje"
                        else:
                            lista_nomes = [f"{row['Posto']} {row['Nome']} ({row['Idade']} anos)" for _, row in aniversariantes_dia.iterrows()]
                            val = ", ".join(lista_nomes)
                        
                        st.markdown(f"""
                        <div class="card-niver">
                            <div class="card-title">Aniversariantes do Dia</div>
                            <div class="card-value">{val}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with c3:
                        val = f"{ultimo['Posto']} {ultimo['Nome']} ({ultimo['Dia']:02d}/{ultimo['Mês']:02d}) - {ultimo['Idade']} anos"
                        st.markdown(f"""
                        <div class="card-niver">
                            <div class="card-title">Último Aniversariante</div>
                            <div class="card-value">{val}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with c4:
                        val = f"{proximo['Posto']} {proximo['Nome']} ({proximo['Dia']:02d}/{proximo['Mês']:02d}) - {proximo['Idade']} anos"
                        st.markdown(f"""
                        <div class="card-niver">
                            <div class="card-title">Próximo Aniversariante</div>
                            <div class="card-value">{val}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
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
                            df_show.sort_values(["Mês", "Dia"])[["Posto", "Nome", "Data Aniversário", "Idade"]],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info(f"Nenhum aniversariante encontrado em {sel_mes_nome}.")

        except Exception as e:
            st.error(f"Erro ao carregar aniversários: {e}")

    elif pagina == "Tabela de Lotação":
        st.subheader("Tabela de Lotação")
        
        try:
            df_lotacao = load_lotacao_data()
            
            if df_lotacao.empty:
                st.error("Não foi possível carregar a tabela de lotação.")
            else:
                # 1. KPIs
                tl_total = df_lotacao["TL"].sum()
                ef_total = df_lotacao["EF"].sum()
                d_total = df_lotacao["D"].sum()
                
                col_k1, col_k2, col_k3 = st.columns(3)
                col_k1.metric("Lotação Total (TL)", int(tl_total))
                col_k2.metric("Efetivo Atual (EF)", int(ef_total))
                col_k3.metric("Balanço Geral", int(d_total), delta=int(d_total), delta_color="normal")
                
                st.markdown("---")
    
                
                # 2. Listas de Faltas e Excessos
                col_list1, col_list2 = st.columns(2)
                
                with col_list1:
                    st.markdown("##### Faltas (Déficit)")
                    df_deficit = df_lotacao[df_lotacao["D"] < 0].sort_values("D")
                    if df_deficit.empty:
                        st.success("Nenhuma falta registrada.")
                    else:
                        # Mostra como tabela limpa
                        st.dataframe(
                            df_deficit[["Especialidade", "D"]], 
                            use_container_width=True, 
                            hide_index=True
                        )
                        
                with col_list2:
                    st.markdown("##### Excessos")
                    df_excess = df_lotacao[df_lotacao["D"] > 0].sort_values("D", ascending=False)
                    if df_excess.empty:
                        st.info("Nenhum excesso registrado.")
                    else:
                        st.dataframe(
                            df_excess[["Especialidade", "D"]], 
                            use_container_width=True, 
                            hide_index=True
                        )
                
                st.markdown("---")
    
                
                # 3. Gráficos Donut (ECharts)
                st.markdown("### Análise Gráfica")
                col_g1, col_g2, col_g3 = st.columns(3)
                
                with col_g1:
                    st.markdown("##### Panorama das Especialidades")
                    # Conta quantos estão em cada status
                    status_counts = df_lotacao["Status"].value_counts().reset_index()
                    status_counts.columns = ["Status", "Count"]
                    
                    # Prepara dados para o Donut
                    data_status = []
                    for _, row in status_counts.iterrows():
                        data_status.append({"value": int(row["Count"]), "name": row["Status"]})
                        
                    opt_status = make_echarts_donut(data_status, "Status")
                    st_echarts(options=opt_status, height="400px")
                    
                with col_g2:
                    st.markdown("##### Taxa de Ocupação Global")
                    # TL vs EF Global
                    # Se EF > TL, ocupação é > 100% (Excesso Global)
                    # Vamos mostrar: Ocupado vs Vago (se houver vaga)
                    
                    vagas_aberto = max(0, tl_total - ef_total)
                    ocupado = min(ef_total, tl_total) # O que cabe na lotação
                    excesso_global = max(0, ef_total - tl_total) # O que transborda
                    
                    data_ocupacao = [
                        {"value": int(ocupado), "name": "Ocupado"},
                        {"value": int(vagas_aberto), "name": "Vago"}
                    ]
                    
                    if excesso_global > 0:
                        data_ocupacao.append({"value": int(excesso_global), "name": "Excesso Global"})
                        
                    opt_ocupacao = make_echarts_donut(data_ocupacao, "Ocupação")
                    st_echarts(options=opt_ocupacao, height="400px")
                    
                with col_g3:
                    st.markdown("##### Tempo de Bordo")
                    try:
                        df_tempo = load_tempo_bordo()
                        if not df_tempo.empty:
                            hoje = datetime.utcnow() - timedelta(hours=3)
                            
                            def calc_anos(val):
                                dt = parse_sheet_date(val)
                                if pd.isna(dt): return None
                                diff = hoje - dt
                                return diff.days / 365.25
                            
                            df_tempo["Anos"] = df_tempo["DataEmbarque"].apply(calc_anos)
                            df_tempo = df_tempo.dropna(subset=["Anos"])
                            
                            menos_1 = (df_tempo["Anos"] < 1).sum()
                            entre_1_2 = ((df_tempo["Anos"] >= 1) & (df_tempo["Anos"] < 2)).sum()
                            mais_2 = (df_tempo["Anos"] >= 2).sum()
                            
                            data_donut = [
                                {"value": int(menos_1), "name": "Menos de 1 ano"},
                                {"value": int(entre_1_2), "name": "1 a 2 anos"},
                                {"value": int(mais_2), "name": "Mais de 2 anos"}
                            ]
                            
                            opt_donut = make_echarts_donut(data_donut, "Tempo Bordo")
                            st_echarts(options=opt_donut, height="400px")
                        else:
                            st.info("Sem dados de tempo de bordo.")
                    except Exception as e:
                        st.error(f"Erro no gráfico: {e}")

                st.markdown("---")
    
                
                # 4. Gráfico de Barras (ECharts)
                st.markdown("### Detalhamento por Especialidade")
                
                if "Especialidade" in df_lotacao.columns:
                    df_grouped = df_lotacao.groupby("Especialidade")[["TL", "EF", "D"]].sum().reset_index()
                    df_chart = df_grouped.sort_values("D", ascending=True)
                    
                    # Preparar dados para ECharts
                    x_data = df_chart["Especialidade"].tolist()
                    y_data = []
                    
                    for val in df_chart["D"].tolist():
                        val_int = int(val)
                        color = "#a3a3a3"
                        if val_int < 0: color = "#ff5370"
                        elif val_int > 0: color = "#2ed8b6"
                        
                        y_data.append({
                            "value": val_int,
                            "itemStyle": {"color": color},
                            "label": {
                                "show": True, 
                                "position": "top" if val_int >= 0 else "bottom",
                                "formatter": "{c}"
                            }
                        })
                    
                    options = {
                        "tooltip": {
                            "trigger": "axis",
                            "axisPointer": {"type": "shadow"},
                            "backgroundColor": "rgba(50, 50, 50, 0.9)",
                            "borderColor": "#777",
                            "textStyle": {"color": "#fff"}
                        },
                        "xAxis": {
                            "type": "category",
                            "data": x_data,
                            "axisLabel": {"interval": 0, "rotate": 45}
                        },
                        "yAxis": {"type": "value"},
                        "series": [
                            {
                                "data": y_data, 
                                "type": "bar",
                                "name": "Diferença"
                            }
                        ],
                        "grid": {
                            "left": "3%",
                            "right": "4%",
                            "bottom": "15%", # Espaço para labels rotacionados
                            "containLabel": True
                        }
                    }
                    
                    st_echarts(options=options, height="500px")
                
                st.markdown("---")
    
                
                # 5. Tabela Completa
                st.markdown("### Tabela Completa")
                
                # Styling
                def style_d(v):
                    if isinstance(v, (int, float)):
                        if v < 0: return "color: #ff5370; font-weight: bold;"
                        elif v > 0: return "color: #2ed8b6; font-weight: bold;"
                    return "color: #a3a3a3;"
                
                st.dataframe(
                    df_lotacao.style.map(style_d, subset=["D"]),
                    use_container_width=True,
                    hide_index=True
                )
                
        except Exception as e:
            st.error(f"Erro ao processar Tabela de Lotação: {e}")

    elif pagina == "Dados Pessoais":
        st.subheader("Dados Pessoais")
        st.markdown("Selecione um militar para visualizar todas as informações cadastradas.")
        
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # Lê com o header correto para garantir nomes de colunas (linha 7 = header index 6)
            df_trip = conn.read(spreadsheet=URL_ANIVERSARIOS, worksheet="TRIPULAÇÃO", header=6, ttl="10m")
            
            # Formata nomes das colunas
            df_trip.columns = [str(c).strip() for c in df_trip.columns]
            
            # A coluna de Nome está no índice 5 (F), Nome de Guerra no 6 (G) e Posto no índice 3 (D)
            if len(df_trip.columns) > 5:
                nome_col = df_trip.columns[5]
                
                df_trip = df_trip.dropna(subset=[nome_col])
                df_trip = df_trip[df_trip[nome_col].astype(str).str.strip() != ""]
                
                # Prepara opções para o selectbox
                opcoes_militar = []
                for idx, row in df_trip.iterrows():
                    nome_completo = str(row.iloc[5]).strip()
                    nome_guerra = str(row.iloc[6]).strip() if len(row) > 6 else ""
                    posto = str(row.iloc[3]).strip()
                    
                    # Usa o Nome de Guerra se disponível para o selectbox, ou o Nome
                    nome_exibir = nome_guerra if nome_guerra and nome_guerra.lower() != "nan" else nome_completo
                    
                    if posto and posto.lower() != "nan":
                        desc = f"{posto} {nome_exibir}"
                    else:
                        desc = nome_exibir
                    opcoes_militar.append((idx, desc))
                
                # Selectbox
                opcoes_desc = [opt[1] for opt in opcoes_militar]
                selecionado = st.selectbox("Buscar Militar:", opcoes_desc)
                
                if selecionado:
                    st.markdown("---")
                    # Acha o index correspondente
                    idx_militar = next(opt[0] for opt in opcoes_militar if opt[1] == selecionado)
                    dados_militar = df_trip.loc[idx_militar]
                    
                    # Nome em destaque
                    st.markdown(f"### {selecionado}")
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Exibir em duas colunas para layout mais limpo
                    col1, col2 = st.columns(2)
                    
                    # Filtra colunas indesejadas que o pandas possa ter puxado vazias (ex: 'Unnamed: X')
                    colunas_validas = [c for c in df_trip.columns if "Unnamed" not in str(c)]
                    
                    meio = len(colunas_validas) // 2
                    
                    for i, col_name in enumerate(colunas_validas):
                        val = dados_militar[col_name]
                        # Limpa valores nulos do pandas para exibição ("-")
                        if pd.isna(val) or str(val).strip() == "" or str(val).strip().lower() == "nan":
                            val_str = "-"
                        else:
                            val_str = str(val).strip()
                            # Se a coluna for de data (ex: Nascimento), tentar formatar bonito se parecer data
                            if "data" in str(col_name).lower():
                                try:
                                    dt = pd.to_datetime(val_str, dayfirst=True)
                                    val_str = dt.strftime("%d/%m/%Y")
                                except:
                                    pass
                                    
                        # Coloca alternado nas colunas
                        t_col = col1 if i < meio else col2
                        with t_col:
                            st.markdown(f"**{col_name}:** {val_str}")
            else:
                st.error("Planilha incompleta ou a coluna 'Nome' não está no local esperado (Coluna G).")
                
        except Exception as e:
            st.error(f"Erro ao carregar dados da tripulação: {e}")

    elif pagina == "Inspeção de Saúde":
        st.subheader("Inspeção de Saúde")
        
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # Lê aba de tripulação
            df_trip = conn.read(spreadsheet=URL_ANIVERSARIOS, worksheet="TRIPULAÇÃO", header=6, ttl="10m")
            
            dados_is = []
            hoje = (datetime.utcnow() - timedelta(hours=3)).date()
            
            for idx, row in df_trip.iterrows():
                try:
                    posto = str(row.iloc[3]).strip() if len(row) > 3 else ""
                    nome_completo = str(row.iloc[5]).strip() if len(row) > 5 else ""
                    nome_guerra = str(row.iloc[6]).strip() if len(row) > 6 else ""
                    is_str = str(row.iloc[10]).strip() if len(row) > 10 else ""
                    
                    if not nome_completo or nome_completo.lower() == "nan":
                        continue
                        
                    nome_exibir = nome_guerra if nome_guerra and nome_guerra.lower() != "nan" else nome_completo
                    if posto and posto.lower() != "nan":
                        desc = f"{posto} {nome_exibir}"
                    else:
                        desc = nome_exibir
                        
                    if pd.notna(is_str) and is_str != "" and is_str.lower() != "nan":
                        # Tenta converter
                        dt_is = pd.to_datetime(is_str, dayfirst=True, errors='coerce')
                        if pd.notna(dt_is):
                            dados_is.append({
                                "Militar": desc,
                                "DataOriginal": is_str,
                                "DataIS": dt_is.date(),
                                "DiasDiff": (dt_is.date() - hoje).days
                            })
                except Exception as loop_e:
                    continue
                    
            if not dados_is:
                st.info("Nenhuma data de inspeção de saúde encontrada na planilha.")
            else:
                df_is = pd.DataFrame(dados_is)
                
                # 1. Vencidos (DiasDiff < 0)
                vencidos = df_is[df_is["DiasDiff"] < 0].sort_values("DiasDiff")
                
                # 2. Próximo a vencer (DiasDiff >= 0), min DiasDiff
                futuros = df_is[df_is["DiasDiff"] >= 0].sort_values("DiasDiff")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### Inspeções Vencidas")
                    if vencidos.empty:
                        st.success("Nenhuma inspeção de saúde vencida. Todos regulares!")
                    else:
                        st.error(f"**{len(vencidos)}** militar(es) com a IS vencida.")
                        for _, v in vencidos.iterrows():
                            st.markdown(f"- **{v['Militar']}** (venceu em {v['DataIS'].strftime('%d/%m/%Y')})")
                            
                with col2:
                    st.markdown("### Próxima a Vencer")
                    if futuros.empty:
                        st.info("Nenhuma próxima inspeção cadastrada.")
                    else:
                        prox = futuros.iloc[0]
                        dias = prox['DiasDiff']
                        if dias == 0:
                            vence_str = "hoje!"
                        elif dias == 1:
                            vence_str = "amanhã!"
                        else:
                            vence_str = f"em {dias} dias ({prox['DataIS'].strftime('%d/%m/%Y')})."
                        st.warning(f"**{prox['Militar']}** vence {vence_str}")
                
                st.markdown("---")
                
                # Busca por ano
                st.markdown("### Busca por Ano")
                anos_disponiveis = df_is["DataIS"].apply(lambda x: x.year).unique().tolist()
                anos_disponiveis.sort()
                
                if not anos_disponiveis:
                    st.info("Nenhum ano cadastrado.")
                else:
                    indice_padrao = anos_disponiveis.index(hoje.year) if hoje.year in anos_disponiveis else len(anos_disponiveis)-1
                    ano_selecionado = st.selectbox("Selecione o ano de validade:", anos_disponiveis, index=indice_padrao)
                    
                    df_ano = df_is[df_is["DataIS"].apply(lambda x: x.year) == ano_selecionado].sort_values("DataIS")
                    if df_ano.empty:
                        st.info(f"Nenhum militar com a IS validada até {ano_selecionado}.")
                    else:
                        st.write(f"Militares cujo vencimento da IS ocorre em **{ano_selecionado}**:")
                        df_display = df_ano[["Militar", "DataOriginal"]].copy()
                        df_display.columns = ["Militar", "Validade (IS)"]
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
                        
        except Exception as e:
            st.error(f"Erro ao carregar os dados de Inspeção de Saúde: {e}")

    elif pagina == "Organograma":
        st.subheader("Organograma do Navio")
        
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # Lê aba de tripulação
            df_trip = conn.read(spreadsheet=URL_ANIVERSARIOS, worksheet="TRIPULAÇÃO", header=6, ttl="10m")
            
            tripulantes = []
            
            # Formata colunas para evitar erros de espaço em branco (Padrão mantido do app.py)
            df_trip.columns = [str(c).strip() for c in df_trip.columns]
            
            for idx, row in df_trip.iterrows():
                try:
                    # Índices: Posto=3 (D), Nome=5 (F), Nome de Guerra=6 (G), Divisão=16 (Q)
                    if len(row) > 16:
                        posto = str(row.iloc[3]).strip()
                        nome_completo = str(row.iloc[5]).strip()
                        nome_guerra = str(row.iloc[6]).strip()
                        divisao = str(row.iloc[16]).strip().lower()
                        situacao = str(row.iloc[17]).strip().lower() if len(row) > 17 else ""
                        
                        if not nome_completo or nome_completo.lower() == "nan":
                            continue
                            
                        nome_exibir = nome_guerra if nome_guerra and nome_guerra.lower() != "nan" else nome_completo
                        
                        if posto and posto.lower() != "nan":
                            desc = f"{posto} {nome_exibir}"
                        else:
                            desc = nome_exibir
                            
                        if "destacado" in situacao:
                            desc += " (Destacado)"
                            
                        tripulantes.append({
                            "Nome": desc,
                            "Divisao": divisao
                        })
                except Exception:
                    continue
                    
            if len(tripulantes) >= 2:
                comandante = tripulantes[0]
                imediato = tripulantes[1]
                
                # Exclui comandante e imediato da lista de divisões
                outros = tripulantes[2:]
                
                div_arm = [t for t in outros if "arm" in t["Divisao"]]
                div_ope = [t for t in outros if "ope" in t["Divisao"]]
                div_maq = [t for t in outros if "maq" in t["Divisao"]]
                
                # CSS do Organograma
                st.markdown("""
                <style>
                    .org-node {
                        background-color: rgba(255, 255, 255, 0.07);
                        border: 1px solid rgba(128, 128, 128, 0.2);
                        border-radius: 8px;
                        padding: 15px;
                        text-align: center;
                        margin: 10px auto;
                        width: 90%;
                        font-weight: 600;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        transition: transform 0.2s;
                    }
                    .org-node:hover {
                        transform: scale(1.02);
                    }
                    .cmd-node { width: 50%; max-width: 300px; border-top: 4px solid #f97316; }
                    .imed-node { width: 50%; max-width: 300px; border-top: 4px solid #3b82f6; }
                    .arm-node { border-left: 4px solid #ef4444; }
                    .ope-node { border-left: 4px solid #10b981; }
                    .maq-node { border-left: 4px solid #8b5cf6; }
                    .div-title {
                        text-align: center;
                        font-size: 1.1rem;
                        font-weight: 600;
                        margin-bottom: 15px;
                        color: var(--text-color);
                        opacity: 0.9;
                        border-bottom: 2px solid rgba(128,128,128,0.2);
                        padding-bottom: 5px;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                # Renderiza Comandante
                st.markdown(f'<div class="org-node cmd-node">Comandante<br><span style="font-weight:normal;font-size:0.9em;opacity:0.8;">{comandante["Nome"]}</span></div>', unsafe_allow_html=True)
                
                # Linha conectora vertical
                st.markdown("<div style='text-align: center; font-size: 24px; color: var(--text-color); opacity: 0.4;'>↓</div>", unsafe_allow_html=True)
                
                # Renderiza Imediato
                st.markdown(f'<div class="org-node imed-node">Imediato<br><span style="font-weight:normal;font-size:0.9em;opacity:0.8;">{imediato["Nome"]}</span></div>', unsafe_allow_html=True)
                
                st.markdown("<div style='text-align: center; font-size: 24px; color: var(--text-color); opacity: 0.4; margin-bottom: 30px;'>↓</div>", unsafe_allow_html=True)
                
                # Branch out (3 Divisions)
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    st.markdown('<div class="div-title" style="border-bottom-color: #ef4444;">Divisão de Armamento</div>', unsafe_allow_html=True)
                    for m in div_arm:
                        st.markdown(f'<div class="org-node arm-node" style="font-size:0.9em; font-weight:normal;">{m["Nome"]}</div>', unsafe_allow_html=True)
                        
                with c2:
                    st.markdown('<div class="div-title" style="border-bottom-color: #10b981;">Divisão de Operações</div>', unsafe_allow_html=True)
                    for m in div_ope:
                        st.markdown(f'<div class="org-node ope-node" style="font-size:0.9em; font-weight:normal;">{m["Nome"]}</div>', unsafe_allow_html=True)
                        
                with c3:
                    st.markdown('<div class="div-title" style="border-bottom-color: #8b5cf6;">Divisão de Máquinas</div>', unsafe_allow_html=True)
                    for m in div_maq:
                        st.markdown(f'<div class="org-node maq-node" style="font-size:0.9em; font-weight:normal;">{m["Nome"]}</div>', unsafe_allow_html=True)
                        
            else:
                st.warning("Não há tripulantes suficientes listados para montar o organograma.")
                
        except Exception as e:
            st.error(f"Erro ao carregar dados do Organograma: {e}")

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

        st.markdown("---")
    
        st.markdown("---")
    
        st.markdown("### 🎂 O QUE O APP ESTÁ LENDO AGORA (URL_ANIVERSARIOS default)")
        try:
            df_niver_debug = load_aniversarios()
            st.write(f"**Shape:** {df_niver_debug.shape}")
            st.write(f"**Colunas ({len(df_niver_debug.columns)}):**")
            for i, col in enumerate(df_niver_debug.columns):
                st.write(f"- Índice {i} (Coluna {chr(65+i)}): `{col}`")
            
            st.write("**Primeiras 10 linhas da planilha carregada:**")
            st.dataframe(df_niver_debug.head(10), use_container_width=True)
            
            st.warning("""
            **Por que os aniversários não aparecem?**
            Se você não estiver vendo uma coluna com as Datas de Nascimento (ex: "Data de Nascimento", "Aniversário", etc), 
            é porque a planilha lida acima é a aba INCORRETA (ou a URL é de outra planilha).
            Use a ferramenta de Investigação abaixo para encontrar a aba correta!
            """)
        except Exception as e:
            st.error(f"Erro ao carregar URL_ANIVERSARIOS padrão: {e}")

        st.markdown("---")
    
        st.markdown("### 🔍 Investigador de Planilhas Google (Encontre sua Aba!)")
        st.info("O Streamlit lê por padrão a PRIMEIRA ABA da planilha. Se os aniversários estiverem na segunda aba (ex: 'Aniversários'), você precisa testar aqui.")
        
        test_url = st.text_input("URL da Planilha", value=URL_ANIVERSARIOS, key="test_url")
        test_sheet = st.text_input("Nome da Aba (Worksheet) - Deixe em branco para a primeira aba", value="TRIPULAÇÃO", key="test_sheet")
        test_header = st.number_input("Linha de Cabeçalho (Ex: se o cabeçalho está na linha 8, digite 7)", value=6, min_value=0, max_value=20, key="test_header")
        
        if st.button("Testar Carga de Planilha"):
            with st.spinner("Carregando..."):
                try:
                    conn_test = st.connection("gsheets", type=GSheetsConnection)
                    kwargs = {"spreadsheet": test_url, "header": test_header, "ttl": 0}
                    if test_sheet.strip():
                        kwargs["worksheet"] = test_sheet.strip()
                    else:
                        st.warning("Nenhum nome de aba informado. Lendo a aba padrão (primeira).")
                        
                    df_test = conn_test.read(**kwargs)
                    st.success(f"Sucesso! Aba carregada com {df_test.shape[0]} linhas e {df_test.shape[1]} colunas.")
                    st.write("**Lista de Colunas encontradas:**")
                    for i, col in enumerate(df_test.columns):
                        st.write(f"- Índice {i} (Coluna {chr(65+i)}): `{col}`")
                    st.write("**Dados Carregados:**")
                    st.dataframe(df_test.head(15), use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao carregar: O nome da aba está correto? Detalhes do erro: {e}")



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
