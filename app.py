import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ============================================================
# 1. CONFIGURAÇÃO E DESIGN SYSTEM (CSS MODERNIZADO)
# ============================================================
st.set_page_config(
    page_title="NPaMacau | Command Center",
    layout="wide",
    page_icon="⚓"
)

# Paleta de Cores & Estilo
COLOR_BG = "#0f172a"        # Slate 900
COLOR_CARD = "#1e293b"      # Slate 800
COLOR_TEXT = "#f8fafc"      # Slate 50
COLOR_ACCENT = "#0ea5e9"    # Sky 500

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');

    .stApp {{
        background-color: {COLOR_BG};
        font-family: 'Inter', sans-serif;
    }}

    /* Tipografia */
    h1, h2, h3, h4 {{
        color: {COLOR_TEXT} !important;
        font-weight: 600 !important;
        letter-spacing: -0.5px;
    }}
    
    /* Sidebar (Menu Lateral) */
    section[data-testid="stSidebar"] {{
        background-color: #020617;
        border-right: 1px solid #334155;
    }}
    
    /* Menu de Navegação (Radio transformado em Botões) */
    .stRadio > div {{ background-color: transparent; }}
    .stRadio > div[role="radiogroup"] > label {{
        background-color: transparent !important;
        border: none;
        padding: 12px 15px;
        margin-bottom: 5px;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        color: #94a3b8 !important; /* Texto inativo */
        font-weight: 500;
        display: flex;
        align-items: center;
    }}
    
    /* Item Selecionado */
    .stRadio > div[role="radiogroup"] > label[data-checked="true"] {{
        background-color: rgba(14, 165, 233, 0.15) !important;
        color: {COLOR_ACCENT} !important;
        border-left: 4px solid {COLOR_ACCENT};
    }}
    
    .stRadio > div[role="radiogroup"] > label:hover {{
        background-color: rgba(255,255,255, 0.05) !important;
        color: white !important;
    }}

    /* Cards de Métricas */
    div[data-testid="metric-container"] {{
        background-color: {COLOR_CARD};
        border: 1px solid #334155;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}
    div[data-testid="metric-container"] label {{
        color: #64748b !important;
        font-size: 0.85rem;
    }}
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {{
        color: {COLOR_TEXT} !important;
    }}

    /* Tabelas */
    .stDataFrame {{
        background-color: {COLOR_CARD};
        border-radius: 12px;
        padding: 10px;
        border: 1px solid #334155;
    }}
    </style>
""", unsafe_allow_html=True)

# ============================================================
# 2. LOGICA DE DADOS (MANTENDO SUA LÓGICA ORIGINAL)
# ============================================================

HEADER_ROW = 2  # linha 3 na planilha

def parse_bool(value) -> bool:
    if pd.isna(value): return False
    s = str(value).strip().lower()
    return s in ("true", "1", "sim", "yes", "y", "x")

@st.cache_data(ttl=600, show_spinner="Sincronizando com Google Sheets...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Afastamento 2026", header=HEADER_ROW, ttl="10m")
    
    # Limpeza de linhas vazias pelo Nome
    if "Nome" in df.columns:
        df = df.dropna(subset=["Nome"])
    
    df = df.reset_index(drop=True)
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- Funções de Detecção Dinâmica (Preservadas do seu script) ---

def descobrir_ferias_pairs(df: pd.DataFrame):
    pairs = []
    for col in df.columns:
        if not str(col).startswith("Inicio"): continue
        # Verifica sufixo (.1, .2)
        sufixo = col[len("Inicio"):] if col != "Inicio" else ""
        col_ini = col
        col_fim = f"Fim{sufixo}"
        if col_fim in df.columns:
            ordem = df.columns.get_loc(col_ini)
            pairs.append((ordem, col_ini, col_fim))
    pairs.sort(key=lambda x: x[0])
    return [(c_ini, c_fim) for _, c_ini, c_fim in pairs]

def descobrir_ausencias_triplets(df: pd.DataFrame):
    triplets = []
    for col in df.columns:
        # Nota: Seu script usava "Início" com acento para ausências
        if not str(col).startswith("Início"): continue
        
        parts = col.split(".", 1)
        sufixo = f".{parts[1]}" if len(parts) > 1 else ""
        col_ini = col
        col_fim = f"FIm{sufixo}" # Note o "I" maiúsculo conforme sua planilha
        
        candidatos_motivo = [f"Motivo{sufixo}", f"Curso{sufixo}", f"Motivo Curso{sufixo}"]
        col_mot = next((c for c in candidatos_motivo if c in df.columns), None)
        
        if col_fim in df.columns and col_mot:
            ordem = df.columns.get_loc(col_ini)
            triplets.append((ordem, col_ini, col_fim, col_mot))
            
    triplets.sort(key=lambda x: x[0])
    # Lógica: 3 primeiros são Outros, do 4º em diante são Cursos
    return [(c_ini, c_fim, c_mot, "Outros" if idx < 3 else "Curso") for idx, (_, c_ini, c_fim, c_mot) in enumerate(triplets)]

AUSENCIAS_TRIPLETS = descobrir_ausencias_triplets(df_raw)

# --- Processamento de Eventos (Wide -> Long) ---

@st.cache_data(ttl=600)
def construir_eventos(df_raw: pd.DataFrame) -> pd.DataFrame:
    eventos = []
    ferias_pairs = descobrir_ferias_pairs(df_raw)

    for _, row in df_raw.iterrows():
        # Captura segura de dados
        posto  = row.get("Posto", "")
        nome   = row.get("Nome", "")
        escala = row.get("Serviço", "")
        eqman  = row.get("EqMan", "")
        gvi    = row.get("Gvi/GP", "")
        insp   = row.get("IN", "")

        militar_info = {
            "Posto": posto,
            "Nome": nome,
            "Escala": escala,
            "EqMan": eqman if pd.notna(eqman) and str(eqman) != "-" else "Não",
            "GVI": parse_bool(gvi),
            "IN": parse_bool(insp),
        }

        # 1. FÉRIAS
        for col_ini, col_fim in ferias_pairs:
            ini = pd.to_datetime(row.get(col_ini, pd.NaT), dayfirst=True, errors="coerce")
            fim = pd.to_datetime(row.get(col_fim, pd.NaT), dayfirst=True, errors="coerce")
            
            # Correção do ano 1925 -> 2025 (Bug do Sheets com 2 dígitos)
            if pd.notna(ini) and ini.year < 2000: ini = ini.replace(year=ini.year + 100)
            if pd.notna(fim) and fim.year < 2000: fim = fim.replace(year=fim.year + 100)

            if pd.notna(ini) and pd.notna(fim):
                if fim < ini: ini, fim = fim, ini
                dur = (fim - ini).days + 1
                if 1 <= dur <= 365:
                    eventos.append({
                        **militar_info, "Inicio": ini, "Fim": fim, "Duracao_dias": dur,
                        "Motivo": "FÉRIAS", "Tipo": "Férias"
                    })

        # 2. OUTRAS AUSÊNCIAS
        for col_ini, col_fim, col_mot, tipo_base in AUSENCIAS_TRIPLETS:
            ini = pd.to_datetime(row.get(col_ini, pd.NaT), dayfirst=True, errors="coerce")
            fim = pd.to_datetime(row.get(col_fim, pd.NaT), dayfirst=True, errors="coerce")
            motivo_texto = str(row.get(col_mot, "")).strip()

            # Correção do ano
            if pd.notna(ini) and ini.year < 2000: ini = ini.replace(year=ini.year + 100)
            if pd.notna(fim) and fim.year < 2000: fim = fim.replace(year=fim.year + 100)

            if pd.notna(ini) and pd.notna(fim):
                if fim < ini: ini, fim = fim, ini
                dur = (fim - ini).days + 1
                if 1 <= dur <= 365:
                    # Define Tipo Final
                    tipo_final = "Curso" if "curso" in motivo_texto.lower() else tipo_base
                    # Define Motivo Real
                    if tipo_final == "Curso":
                        motivo_real = motivo_texto if len(motivo_texto) > 2 else "CURSO"
                    else:
                        motivo_real = motivo_texto if len(motivo_texto) > 2 and "nan" not in motivo_texto.lower() else "OUTROS"

                    eventos.append({
                        **militar_info, "Inicio": ini, "Fim": fim, "Duracao_dias": dur,
                        "Motivo": motivo_real, "Tipo": tipo_final
                    })

    return pd.DataFrame(eventos)

df_eventos = construir_eventos(df_raw)

# --- Expansão por dia (para gráficos mensais) ---
@st.cache_data(ttl=600)
def expandir_eventos_por_dia(df_eventos):
    if df_eventos.empty: return pd.DataFrame()
    linhas = []
    for _, ev in df_eventos.iterrows():
        for data in pd.date_range(ev["Inicio"], ev["Fim"]):
            linhas.append({**ev, "Data": data}) # Copia tudo e adiciona a data
    return pd.DataFrame(linhas)

df_dias = expandir_eventos_por_dia(df_eventos)

# --- Funções de Filtro (Preservadas) ---
def filtrar_tripulacao(df, eq, inn, gv):
    res = df.copy()
    if eq and "EqMan" in res.columns: res = res[(res["EqMan"].notna()) & (res["EqMan"].astype(str) != "-")]
    if inn and "IN" in res.columns: res = res[res["IN"].apply(parse_bool)]
    if gv and "Gvi/GP" in res.columns: res = res[res["Gvi/GP"].apply(parse_bool)]
    return res

def filtrar_eventos(df, eq, inn, gv):
    res = df.copy()
    if eq: res = res[res["EqMan"] != "Não"]
    if inn: res = res[res["IN"] == True]
    if gv: res = res[res["GVI"] == True]
    return res

# ============================================================
# 3. INTERFACE DE NAVEGAÇÃO (SIDEBAR)
# ============================================================

with st.sidebar:
    # Logo e Identidade
    c1, c2 = st.columns([1, 4])
    with c1:
        try: st.image("logo_npamacau.png", use_container_width=True)
        except: st.write("⚓")
    with c2:
        st.markdown("<h3 style='margin:0; padding-top:5px;'>NPaMacau</h3>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Menu Principal (Substituindo as abas horizontais)
    # Removemos os emojis do texto para ficar minimalista
    menu_options = ["Situação Diária", "Cronograma", "Estatísticas", "Férias", "Cursos", "Log do Sistema"]
    selection = st.radio("Menu", menu_options, label_visibility="collapsed")
    
    st.markdown("---")
    
    # Filtros Globais
    st.markdown("### ⚙️ Parâmetros")
    data_ref = st.date_input("Data de Referência", datetime.today())
    hoje = pd.to_datetime(data_ref)
    
    st.markdown("### 🔎 Equipes")
    # Usando session_state para persistir filtros entre abas se necessário
    f_eqman = st.checkbox("Apenas EqMan")
    f_in = st.checkbox("Apenas Inspetores (IN)")
    f_gvi = st.checkbox("Apenas GVI/GP")

# ============================================================
# 4. CONTEÚDO DAS PÁGINAS (ADAPTADO DO SEU SCRIPT)
# ============================================================

# Cabeçalho da Página
col_tit, col_dt = st.columns([3, 1])
with col_tit:
    st.title(f"{selection}")
with col_dt:
    st.markdown(f"<div style='text-align:right; padding-top:10px; color:#64748b;'>{hoje.strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)


# --- PÁGINA: SITUAÇÃO DIÁRIA (Mesclando Presentes e Ausentes) ---
if selection == "Situação Diária":
    
    # Lógica de Cálculo
    df_trip = filtrar_tripulacao(df_raw, f_eqman, f_in, f_gvi)
    
    if not df_eventos.empty:
        ausentes_hoje = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
        ausentes_hoje = filtrar_eventos(ausentes_hoje, f_eqman, f_in, f_gvi)
        nomes_ausentes = set(ausentes_hoje["Nome"].unique())
    else:
        ausentes_hoje = pd.DataFrame()
        nomes_ausentes = set()
        
    df_presentes = df_trip[~df_trip["Nome"].isin(nomes_ausentes)].copy()
    
    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Efetivo Total", len(df_trip))
    k2.metric("A Bordo", len(df_presentes))
    k3.metric("Ausentes", len(nomes_ausentes), delta_color="inverse")
    prontidao = (len(df_presentes)/len(df_trip)*100) if len(df_trip) > 0 else 0
    k4.metric("Prontidão", f"{prontidao:.1f}%")
    
    st.markdown("---")
    
    # Sub-abas internas para organizar a tabela
    sub_tab1, sub_tab2 = st.tabs(["🔴 Ausentes", "🟢 Presentes"])
    
    with sub_tab1:
        if ausentes_hoje.empty:
            st.success("✅ Todo o efetivo selecionado está a bordo.")
        else:
            show_df = ausentes_hoje[["Posto", "Nome", "Motivo", "Tipo", "Fim"]].copy()
            show_df["Retorno"] = show_df["Fim"].dt.strftime("%d/%m/%Y")
            st.dataframe(show_df.drop(columns=["Fim"]), use_container_width=True, hide_index=True)
            
            # Alertas
            eqman_fora = ausentes_hoje[ausentes_hoje["EqMan"] != "Não"]
            if not eqman_fora.empty:
                st.error(f"⚠️ **Alerta EqMan:** {', '.join(eqman_fora['Nome'].unique())}")

    with sub_tab2:
        if df_presentes.empty:
            st.info("Ninguém presente para os filtros atuais.")
        else:
            cols_show = ["Posto", "Nome", "Serviço", "EqMan"]
            if "Gvi/GP" in df_presentes.columns: cols_show.append("Gvi/GP")
            st.dataframe(df_presentes[cols_show], use_container_width=True, hide_index=True)

# --- PÁGINA: CRONOGRAMA ---
elif selection == "Cronograma":
    if df_eventos.empty:
        st.info("Sem datas preenchidas na planilha.")
    else:
        df_gantt = filtrar_eventos(df_eventos, f_eqman, f_in, f_gvi)
        
        if df_gantt.empty:
            st.warning("Nenhum evento com os filtros atuais.")
        else:
            # Gráfico Gantt Moderno
            fig = px.timeline(
                df_gantt, x_start="Inicio", x_end="Fim", y="Nome", color="Motivo",
                hover_data=["Posto", "Tipo"], color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig.update_yaxes(autorange="reversed", title="")
            fig.update_xaxes(title="")
            fig.add_vline(x=hoje, line_width=2, line_dash="dash", line_color="#ef4444")
            
            # Ajuste de layout para fundo escuro
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(30, 41, 59, 0.5)",
                font=dict(color="#cbd5e1"),
                margin=dict(l=10, r=10, t=20, b=20),
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig, use_container_width=True)

# --- PÁGINA: ESTATÍSTICAS ---
elif selection == "Estatísticas":
    if df_eventos.empty:
        st.write("Sem dados.")
    else:
        df_evt = filtrar_eventos(df_eventos, f_eqman, f_in, f_gvi)
        
        if df_evt.empty:
            st.info("Sem dados para os filtros.")
        else:
            # Métricas
            c1, c2, c3 = st.columns(3)
            total_dias = df_evt["Duracao_dias"].sum()
            media_dias = df_evt.groupby("Nome")["Duracao_dias"].sum().mean()
            c1.metric("Dias de Ausência (Total)", int(total_dias))
            c2.metric("Média Dias/Militar", f"{media_dias:.1f}")
            
            st.markdown("### 🍩 Motivos de Ausência")
            df_motivos = df_evt.groupby("Motivo")["Duracao_dias"].sum().reset_index()
            
            # Gráfico de Rosca
            fig = px.pie(df_motivos, names="Motivo", values="Duracao_dias", hole=0.5)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"))
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### 🏆 Top 10 Ausentes")
            df_top = df_evt.groupby(["Nome", "Posto"])["Duracao_dias"].sum().reset_index().sort_values("Duracao_dias", ascending=False).head(10)
            
            fig_bar = px.bar(df_top, x="Nome", y="Duracao_dias", color="Posto")
            fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"))
            st.plotly_chart(fig_bar, use_container_width=True)

# --- PÁGINA: FÉRIAS ---
elif selection == "Férias":
    df_fer = df_eventos[df_eventos["Tipo"] == "Férias"]
    df_fer = filtrar_eventos(df_fer, f_eqman, f_in, f_gvi)
    
    c1, c2 = st.columns(2)
    c1.metric("Militares c/ Férias", df_fer["Nome"].nunique())
    c2.metric("Total Dias Férias", int(df_fer["Duracao_dias"].sum()))
    
    st.markdown("### 📅 Lista de Férias")
    if not df_fer.empty:
        tb = df_fer[["Posto", "Nome", "Inicio", "Fim", "Duracao_dias"]].copy()
        tb["Inicio"] = tb["Inicio"].dt.strftime("%d/%m/%Y")
        tb["Fim"] = tb["Fim"].dt.strftime("%d/%m/%Y")
        st.dataframe(tb.sort_values("Inicio"), use_container_width=True, hide_index=True)
        
    # Gráfico de Férias por Mês
    if not df_dias.empty:
        df_dias_fer = df_dias[(df_dias["Tipo"]=="Férias")].copy()
        df_dias_fer = filtrar_eventos(df_dias_fer, f_eqman, f_in, f_gvi) # Filtra linhas expandidas
        
        if not df_dias_fer.empty:
            df_dias_fer["Mes"] = df_dias_fer["Data"].dt.to_period("M").dt.to_timestamp()
            graf_mes = df_dias_fer.groupby("Mes")["Nome"].nunique().reset_index(name="Qtd")
            
            st.markdown("### 📊 Férias por Mês")
            fig_m = px.bar(graf_mes, x="Mes", y="Qtd")
            fig_m.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#fff"))
            st.plotly_chart(fig_m, use_container_width=True)

# --- PÁGINA: CURSOS ---
elif selection == "Cursos":
    df_cur = df_eventos[df_eventos["Tipo"] == "Curso"]
    df_cur = filtrar_eventos(df_cur, f_eqman, f_in, f_gvi)
    
    realizados = df_cur[df_cur["Fim"] < hoje]
    futuros = df_cur[df_cur["Fim"] >= hoje]
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 🎓 Futuros / Em Andamento")
        if not futuros.empty:
            tb = futuros[["Posto", "Nome", "Motivo", "Fim"]].copy()
            tb["Término"] = tb["Fim"].dt.strftime("%d/%m/%Y")
            st.dataframe(tb.drop(columns=["Fim"]), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum curso futuro.")

    with c2:
        st.markdown("### ✅ Realizados")
        if not realizados.empty:
            tb = realizados[["Posto", "Nome", "Motivo"]].copy()
            st.dataframe(tb, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum curso concluído.")

# --- PÁGINA: LOG DO SISTEMA ---
elif selection == "Log do Sistema":
    st.warning("Área técnica para verificação de dados brutos.")
    st.markdown("#### Planilha Original")
    st.dataframe(df_raw.head(50))
    st.markdown("#### Eventos Processados")
    st.dataframe(df_eventos)

# ============================================================
# 5. RODAPÉ
# ============================================================
st.markdown("---")
st.markdown("<div style='text-align:center; color:#475569; font-size:0.8rem;'>Navio-Patrulha Macau | Sistema de Controle de Efetivo</div>", unsafe_allow_html=True)
