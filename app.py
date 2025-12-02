import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ============================================================
# VERSÃO DO SCRIPT
# ============================================================
SCRIPT_VERSION = "v0.6.1 (Agendas Oficiais + Stripe/Looker UI)"

# Use tema CLARO moderno no Plotly (Looker / Stripe style)
pio.templates.default = "plotly_white"

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Navio-Patrulha Macau",
    layout="wide",
    page_icon="logo_npamacau.png"
)

# --- CSS global / tema Stripe + Looker (sidebar escura, conteúdo claro) ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@600;700&family=Inter:wght@400;500;600&display=swap');

    * {
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Fundo geral: claro, tipo Looker Studio */
    .stApp {
        background: #f5f7fb;
        color: #111827;
    }

    h1, h2, h3, h4 {
        color: #111827 !important;
        letter-spacing: 0.02em;
    }

    h1 {
        font-family: 'Raleway', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-weight: 700 !important;
    }

    /* Cabeçalho principal: linha sutil, estilo Stripe */
    .main > div:nth-child(1) {
        padding-top: 0.5rem;
    }

    /* Cards de métricas (estilo Stripe cards) */
    div[data-testid="metric-container"] {
        background: #ffffff;
        border-radius: 0.9rem;
        padding: 1rem 1.2rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
    }

    div[data-testid="metric-container"] > label {
        color: #6b7280 !important;
        font-size: 0.80rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    div[data-testid="metric-container"] > div[data-testid="stMetricValue"] {
        color: #111827 !important;
    }

    /* Dataframes como cartões claros */
    .stDataFrame {
        background: #ffffff;
        border-radius: 0.75rem;
        padding: 0.25rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 8px 22px rgba(15,23,42,0.05);
    }

    /* Sidebar escura estilo Stripe */
    section[data-testid="stSidebar"] {
        background: #020617;
        border-right: 1px solid #0f172a;
    }

    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] h4 {
        color: #e5e7eb !important;
    }

    section[data-testid="stSidebar"] label {
        color: #cbd5f5 !important;
    }

    section[data-testid="stSidebar"] .stDateInput > label {
        color: #e5e7eb !important;
    }

    /* Botões / checkboxes na sidebar */
    section[data-testid="stSidebar"] .stCheckbox > label,
    section[data-testid="stSidebar"] .stRadio > label,
    section[data-testid="stSidebar"] .stSelectbox > label {
        color: #e5e7eb !important;
    }

    /* NAV LATERAL (NAVEGAÇÃO ENTRE PÁGINAS)
       - Usa st.radio, mas esconde o "botão" e deixa só o texto com estilo */
    div.nav-container > div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
    }

    /* Esconde o círculo do radio e o ícone */
    div.nav-container div[role="radio"] > div:first-child {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    div.nav-container div[role="radio"] svg {
        display: none !important;
    }

    /* Item de navegação (texto) */
    div.nav-container div[role="radio"] {
        padding: 0.30rem 0.60rem;
        border-radius: 0.5rem;
        cursor: pointer;
    }

    div.nav-container div[role="radio"] > div:nth-child(2) {
        color: #9ca3af;
        font-weight: 500;
        font-size: 0.92rem;
    }

    div.nav-container div[role="radio"]:hover {
        background: rgba(15,23,42,0.9);
    }
    div.nav-container div[role="radio"]:hover > div:nth-child(2) {
        color: #e5e7eb;
    }

    /* Aba selecionada: linha azul à esquerda + sublinhado */
    div.nav-container div[role="radio"][aria-checked="true"] {
        background: linear-gradient(90deg, rgba(99,91,255,0.18), transparent);
        border-left: 3px solid #635bff;  /* cor Stripe */
    }
    div.nav-container div[role="radio"][aria-checked="true"] > div:nth-child(2) {
        color: #f9fafb;
        text-decoration: underline;
        text-decoration-thickness: 2px;
        text-underline-offset: 0.28rem;
    }

    /* Cards de evento / agenda */
    .agenda-card {
        background-color: #ffffff;
        border-left: 4px solid #635bff;
        padding: 14px 16px;
        border-radius: 10px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 10px 25px rgba(15,23,42,0.08);
        transition: transform 0.12s ease, box-shadow 0.12s ease;
    }
    .agenda-card:hover {
        transform: translateX(4px);
        box-shadow: 0 14px 32px rgba(15,23,42,0.14);
    }
    .agenda-date {
        background-color: #eff3ff;
        padding: 5px 12px;
        border-radius: 999px;
        color: #374151;
        font-size: 0.85rem;
        font-family: monospace;
        white-space: nowrap;
    }

    /* Separadores (---) um pouco mais discretos */
    hr {
        border: none;
        border-top: 1px solid #e5e7eb;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Cabeçalho: logo + título lado a lado
col_logo, col_title = st.columns([1, 5])
with col_logo:
    try:
        st.image("logo_npamacau.png", width=80)
    except:
        st.write("⚓")  # Fallback se a imagem não existir
with col_title:
    st.markdown(
        """
        <h1 style="margin-top:0.15rem; margin-bottom:0.2rem;">
            Navio-Patrulha Macau
        </h1>
        """,
        unsafe_allow_html=True
    )

# ============================================================
# 2. CONFIGURAÇÕES FIXAS (AGENDAS E COLUNAS)
# ============================================================

HEADER_ROW = 2  # linha 3 na planilha

# --- LISTA OFICIAL DE AGENDAS DO NAVIO ---
AGENDAS_OFICIAIS = {
    "📅 Agenda Permanente": "agenda.npamacau@gmail.com",
    "⚓ Agenda Eventual": "32e9bbd3bca994bdab0b3cd648f2cb4bc13b0cf312a6a2c5a763527a5c610917@group.calendar.google.com",
    "🎂 Aniversários OM": "9f856c62f2420cd3ce5173197855b6726dd0a73d159ba801afd4eddfcac651db@group.calendar.google.com",
    "🎉 Aniversários Tripulação": "8641c7fc86973e09bbb682f8841908cc9240b25b1990f179137dfa7d2b23b2da@group.calendar.google.com",
    "📋 Comissão": "ff1a7d8acb9ea68eed3ec9b0e279f2a91fb962e4faa9f7a3e7187fade00eb0d6@group.calendar.google.com",
    "🛠️ NSD": "d7d9199712991f81e35116b9ec1ed492ac672b72b7103a3a89fb3f66ae635fb7@group.calendar.google.com"
}

def parse_bool(value) -> bool:
    """Converte checkbox/texto da planilha em booleano robusto."""
    if pd.isna(value):
        return False
    s = str(value).strip().lower()
    return s in ("true", "1", "sim", "yes", "y", "x")


# ============================================================
# 3. CARGA DE DADOS (SHEETS + CALENDAR)
# ============================================================

@st.cache_data(ttl=600, show_spinner="Carregando dados da planilha...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Afastamento 2026", header=HEADER_ROW, ttl="10m")
    if "Nome" in df.columns:
        df = df.dropna(subset=["Nome"])
    df = df.reset_index(drop=True)
    return df

@st.cache_data(ttl=300)
def load_calendar_events(calendar_id):
    """Carrega próximos eventos do Google Calendar da agenda escolhida."""
    try:
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        service = build('calendar', 'v3', credentials=creds)
        
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=30,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        data = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Sem Título')
            try:
                dt_obj = pd.to_datetime(start)
                fmt = "%d/%m %H:%M" if 'T' in start else "%d/%m"
                data_fmt = dt_obj.strftime(fmt)
            except:
                data_fmt = start
            data.append({"Data": data_fmt, "Evento": summary})
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# Inicialização
try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro de conexão. Verifique o arquivo secrets.toml. Detalhe: {e}")
    st.stop()


# ============================================================
# 4. PROCESSAMENTO DE DADOS (PLANILHA)
# ============================================================

def descobrir_blocos_datas(df: pd.DataFrame):
    """
    Descobre blocos (Início, Fim, Motivo/Curso) dinamicamente.
    """
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
        blocos.append((cols[i], cols[j], cols[k] if k else None, tipo_base))
    return blocos

BLOCOS_DATAS = descobrir_blocos_datas(df_raw)

@st.cache_data(ttl=600)
def construir_eventos(df_raw: pd.DataFrame, blocos) -> pd.DataFrame:
    eventos = []
    for _, row in df_raw.iterrows():
        posto = row.get("Posto", "")
        nome = row.get("Nome", "")
        escala = row.get("Serviço", "")
        eqman = str(row.get("EqMan", "")) if pd.notna(row.get("EqMan")) and str(row.get("EqMan")) != "-" else "Não"
        
        militar_info = {
            "Posto": posto,
            "Nome": nome,
            "Escala": escala,
            "EqMan": eqman,
            "GVI": parse_bool(row.get("Gvi/GP", "")),
            "IN": parse_bool(row.get("IN", ""))
        }

        for col_ini, col_fim, col_mot, tipo_base in blocos:
            ini = pd.to_datetime(row.get(col_ini, pd.NaT), dayfirst=True, errors="coerce")
            fim = pd.to_datetime(row.get(col_fim, pd.NaT), dayfirst=True, errors="coerce")

            if pd.isna(ini) or pd.isna(fim):
                continue
            if fim < ini:
                ini, fim = fim, ini
            
            # Correção de ano com 2 dígitos (ex.: 25 -> 2025)
            if ini.year < 2000:
                ini = ini.replace(year=ini.year + 100)
            if fim.year < 2000:
                fim = fim.replace(year=fim.year + 100)

            dur = (fim - ini).days + 1
            if dur < 1 or dur > 365 * 2:
                continue

            if tipo_base == "Férias":
                motivo_real = "Férias"
                tipo_final = "Férias"
                motivo_agrupado = "Férias"
            else:
                motivo_texto = str(row.get(col_mot, "")).strip() if col_mot else ""
                if tipo_base == "Curso":
                    # Aqui mantemos o nome do curso no campo Motivo,
                    # mas agrupamos como "Curso" em MotivoAgrupado
                    motivo_real = (
                        motivo_texto
                        if motivo_texto and "nan" not in motivo_texto.lower()
                        else "Curso"
                    )
                    tipo_final = "Curso"
                    motivo_agrupado = "Curso"
                else:
                    if motivo_texto and "nan" not in motivo_texto.lower():
                        motivo_real = motivo_texto
                    else:
                        motivo_real = "OUTROS"
                    tipo_final = "Outros"
                    motivo_agrupado = motivo_real if motivo_real != "OUTROS" else "Outros"

            eventos.append({
                **militar_info,
                "Inicio": ini,
                "Fim": fim,
                "Duracao_dias": dur,
                "Motivo": motivo_real,
                "MotivoAgrupado": motivo_agrupado,
                "Tipo": tipo_final
            })
    return pd.DataFrame(eventos)

df_eventos = construir_eventos(df_raw, BLOCOS_DATAS)

@st.cache_data(ttl=600)
def expandir_eventos_por_dia(df_eventos: Pd.DataFrame) -> pd.DataFrame:
    if df_eventos.empty:
        return pd.DataFrame()
    linhas = []
    for _, ev in df_eventos.iterrows():
        for data in pd.date_range(ev["Inicio"], ev["Fim"]):
            linhas.append({**ev, "Data": data})
    return pd.DataFrame(linhas)

df_dias = expandir_eventos_por_dia(df_eventos)

# Filtros Globais
def filtrar_dados(df, eq, inn, gv):
    res = df.copy()
    if eq:
        if "EqMan" in res.columns:
            res = res[(res["EqMan"].notna()) & (res["EqMan"] != "Não")]
    if inn:
        if "IN" in res.columns:
            res = res[res["IN"] == True]
    if gv:
        if "GVI" in res.columns:
            res = res[res["GVI"] == True]
        elif "Gvi/GP" in res.columns:
            res = res[res["Gvi/GP"].apply(parse_bool)]
    return res

def filtrar_eventos(df, eq, inn, gv):
    """Filtro específico para df_eventos."""
    return filtrar_dados(df, eq, inn, gv)

# ============================================================
# 5. PARÂMETROS E NAVEGAÇÃO
# ============================================================

st.sidebar.header("Parâmetros")
data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

st.sidebar.markdown("#### Navegação")
with st.sidebar.container():
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    pagina = st.radio(
        label="Seções",
        options=[
            "Situação Diária",
            "Agenda do Navio",
            "Presentes",
            "Ausentes",
            "Linha do Tempo",
            "Estatísticas & Análises",
            "Férias",
            "Cursos",
            "Log / Debug"
        ],
        index=0,
        label_visibility="collapsed",
        key="pagina_radio"
    )
    st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 6. MÉTRICAS GLOBAIS
# ============================================================

if not df_eventos.empty:
    ausentes_hoje_global = df_eventos[
        (df_eventos["Inicio"] <= hoje) &
        (df_eventos["Fim"] >= hoje)
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
# 7. FUNÇÕES GRÁFICAS (LOOKER / STRIPE STYLE)
# ============================================================

def grafico_pizza_motivos(df_motivos_dias, titulo):
    fig = px.pie(
        df_motivos_dias,
        names="MotivoAgrupado",
        values="Duracao_dias",
        hole=0.5
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>%{value} dias (%{percent})<extra></extra>"
    )
    fig.update_layout(
        title=titulo,
        showlegend=True,
        legend_title_text="Motivo",
        margin=dict(t=60, b=20, l=0, r=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter",
            color="#111827"
        )
    )
    return fig


# ============================================================
# 8. PÁGINAS DO SISTEMA
# ============================================================

# --- SITUAÇÃO DIÁRIA ---
if pagina == "Situação Diária":
    st.subheader(f"Visão Geral em {hoje.strftime('%d/%m/%Y')}")
    
    c_f1, c_f2, c_f3 = st.columns(3)
    f_eq = c_f1.checkbox("Apenas EqMan")
    f_in = c_f2.checkbox("Apenas Inspetores")
    f_gv = c_f3.checkbox("Apenas GVI")

    df_trip = filtrar_dados(df_raw, f_eq, f_in, f_gv)
    
    aus = pd.DataFrame()
    if not df_eventos.empty:
        aus = df_eventos[
            (df_eventos["Inicio"] <= hoje) &
            (df_eventos["Fim"] >= hoje)
        ]
        aus = filtrar_dados(aus, f_eq, f_in, f_gv)
    
    nomes_aus = set(aus["Nome"].unique()) if not aus.empty else set()
    pres = df_trip[~df_trip["Nome"].isin(nomes_aus)]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Efetivo", len(df_trip))
    k2.metric("A Bordo", len(pres))
    k3.metric("Ausentes", len(nomes_aus), delta_color="inverse")
    pront = (len(pres) / len(df_trip) * 100) if len(df_trip) > 0 else 0
    k4.metric("Prontidão", f"{pront:.1f}%")
    
    st.markdown("---")
    
    col_aus, col_pres = st.columns(2)
    
    with col_aus:
        st.markdown("### Ausentes")
        if aus.empty:
            st.success("Ninguém ausente.")
        else:
            show = aus[["Posto", "Nome", "Motivo", "Fim"]].copy()
            show["Retorno"] = show["Fim"].dt.strftime("%d/%m")
            st.dataframe(show.drop(columns=["Fim"]), use_container_width=True, hide_index=True)
            
            eq_out = aus[aus["EqMan"] != "Não"]
            if not eq_out.empty:
                st.error(
                    "⚠️ EqMan com desfalque: " +
                    ", ".join(sorted(eq_out["Nome"].unique()))
                )

    with col_pres:
        st.markdown("### Presentes")
        if pres.empty:
            st.info("Ninguém presente.")
        else:
            cols = ["Posto", "Nome", "Serviço", "EqMan"]
            st.dataframe(pres[cols], use_container_width=True, hide_index=True)

# --- AGENDA DO NAVIO ---
elif pagina == "Agenda do Navio":
    st.subheader("Agenda do Navio (Google Calendar)")
    
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        nome_agenda = st.selectbox("Selecione a Agenda:", list(AGENDAS_OFICIAIS.keys()))
        selected_id = AGENDAS_OFICIAIS[nome_agenda]
    with col_btn:
        st.write("")
        st.write("")
        if st.button("🔄 Atualizar"):
            load_calendar_events.clear()
            st.rerun()
            
    if selected_id:
        df_cal = load_calendar_events(selected_id)
        
        if df_cal.empty:
            st.info(f"Nenhum evento futuro encontrado na agenda '{nome_agenda}'.")
            st.markdown(
                f"<small>ID verificado: `{selected_id[:15]}...`</small>",
                unsafe_allow_html=True
            )
        else:
            st.markdown("---")
            for _, row in df_cal.iterrows():
                st.markdown(
                    f"""
                    <div class="agenda-card">
                        <div style="font-weight: 600; color: #111827; font-size: 1.02rem;">
                            {row['Evento']}
                        </div>
                        <div class="agenda-date">
                            {row['Data']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

# --- PRESENTES (Detalhado) ---
elif pagina == "Presentes":
    st.subheader("Lista Detalhada de Presentes")
    
    c_f1, c_f2, c_f3 = st.columns(3)
    f_eq = c_f1.checkbox("EqMan", key="p_eq")
    f_in = c_f2.checkbox("Inspetores", key="p_in")
    f_gv = c_f3.checkbox("GVI", key="p_gv")
    
    df_trip = filtrar_dados(df_raw, f_eq, f_in, f_gv)
    aus = pd.DataFrame()
    if not df_eventos.empty:
        aus = df_eventos[
            (df_eventos["Inicio"] <= hoje) &
            (df_eventos["Fim"] >= hoje)
        ]
    names_aus = set(aus["Nome"].unique()) if not aus.empty else set()
    pres = df_trip[~df_trip["Nome"].isin(names_aus)]
    
    st.metric("Total Presente", len(pres))
    if not pres.empty:
        st.dataframe(
            pres[["Posto", "Nome", "Serviço", "EqMan", "Gvi/GP", "IN"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Ninguém presente para os filtros selecionados.")

# --- AUSENTES (Detalhado) ---
elif pagina == "Ausentes":
    st.subheader("Lista Detalhada de Ausentes")
    
    c1, c2, c3 = st.columns(3)
    apenas_eqman = c1.checkbox("Apenas EqMan", key="aus_eq")
    apenas_in = c2.checkbox("Apenas Inspetores", key="aus_in")
    apenas_gvi = c3.checkbox("Apenas GVI/GP", key="aus_gv")

    if df_eventos.empty:
        st.info("Sem eventos.")
    else:
        aus = df_eventos[
            (df_eventos["Inicio"] <= hoje) &
            (df_eventos["Fim"] >= hoje)
        ]
        aus = filtrar_eventos(aus, apenas_eqman, apenas_in, apenas_gvi)

        if aus.empty:
            st.success("Todo o efetivo a bordo.")
        else:
            temp = aus.copy()
            temp["MotivoExib"] = temp.apply(
                lambda r: "Férias" if r["Tipo"] == "Férias"
                else ("Curso" if r["Tipo"] == "Curso"
                      else str(r["Motivo"])),
                axis=1
            )
            show = temp[["Posto", "Nome", "MotivoExib", "Fim"]].copy()
            show["Retorno"] = show["Fim"].dt.strftime("%d/%m/%Y")
            st.dataframe(
                show.drop(columns=["Fim"]).rename(columns={"MotivoExib": "Motivo"}),
                use_container_width=True,
                hide_index=True
            )

            eq_fora = aus[aus["EqMan"] != "Não"]
            if not eq_fora.empty:
                st.error(
                    "⚠️ EqMan com desfalque: " +
                    "; ".join(sorted(
                        {f"{r.Posto} {r.Nome} ({r.EqMan})" for _, r in eq_fora.iterrows()}
                    ))
                )
            
            gv_fora = aus[aus["GVI"] == True]
            if not gv_fora.empty:
                st.warning(
                    "🚨 GVI/GP com desfalque: " +
                    "; ".join(sorted(
                        {f"{r.Posto} {r.Nome}" for _, r in gv_fora.iterrows()}
                    ))
                )

# --- LINHA DO TEMPO ---
elif pagina == "Linha do Tempo":
    st.subheader("Cronograma Anual de Ausências")

    with st.container():
        st.markdown("##### Filtros")
        c1, c2, c3 = st.columns(3)
        apenas_eqman = c1.checkbox("Apenas EqMan", key="gan_eq")
        apenas_in = c2.checkbox("Apenas Inspetores", key="gan_in")
        apenas_gvi = c3.checkbox("Apenas GVI/GP", key="gan_gv")

    if df_eventos.empty:
        st.info("Sem datas.")
    else:
        gantt = filtrar_eventos(df_eventos, apenas_eqman, apenas_in, apenas_gvi)
        if gantt.empty:
            st.info("Sem eventos para o filtro.")
        else:
            fig = px.timeline(
                gantt,
                x_start="Inicio",
                x_end="Fim",
                y="Nome",
                color="MotivoAgrupado",
                hover_data=["Posto", "Escala", "EqMan", "Tipo"],
                title="Cronograma"
            )
            fig.update_yaxes(autorange="reversed")
            fig.add_vline(
                x=hoje,
                line_width=2,
                line_dash="dash",
                line_color="#f97316"
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#111827")
            )
            st.plotly_chart(fig, use_container_width=True)

# --- ESTATÍSTICAS ---
elif pagina == "Estatísticas & Análises":
    st.subheader("Estatísticas & Análises")

    with st.container():
        st.markdown("##### Filtros")
        c1, c2, c3 = st.columns(3)
        apenas_eqman = c1.checkbox("Apenas EqMan", key="sta_eq")
        apenas_in = c2.checkbox("Apenas Inspetores", key="sta_in")
        apenas_gvi = c3.checkbox("Apenas GVI/GP", key="sta_gv")

    if df_eventos.empty:
        st.write("Sem dados.")
    else:
        evt = filtrar_eventos(df_eventos, apenas_eqman, apenas_in, apenas_gvi)
        if evt.empty:
            st.info("Sem eventos para os filtros atuais.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Dias Totais de Ausência", int(evt["Duracao_dias"].sum()))
            c2.metric("Média de Dias por Militar", f"{evt.groupby('Nome')['Duracao_dias'].sum().mean():.1f}")
            fer_evt = evt[evt["Tipo"] == "Férias"]
            c3.metric(
                "Média de Dias de Férias",
                f"{fer_evt.groupby('Nome')['Duracao_dias'].sum().mean():.1f}" if not fer_evt.empty else "0"
            )
            
            st.markdown("---")
            grp = (
                evt.groupby("MotivoAgrupado")["Duracao_dias"]
                .sum()
                .reset_index()
                .sort_values("Duracao_dias", ascending=False)
            )
            st.plotly_chart(
                grafico_pizza_motivos(grp, "Proporção de Dias de Ausência por Motivo"),
                use_container_width=True
            )
            
            st.markdown("---")
            st.subheader("Top 10 Militares por Dias de Ausência")
            top = (
                evt.groupby(["Nome", "Posto"])["Duracao_dias"]
                .sum()
                .reset_index()
                .sort_values("Duracao_dias", ascending=False)
                .head(10)
            )
            fig = px.bar(
                top,
                x="Nome",
                y="Duracao_dias",
                color="Posto",
                title="Top 10 – Dias de Ausência por Militar",
                labels={"Duracao_dias": "Dias de ausência"}
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#111827")
            )
            st.plotly_chart(fig, use_container_width=True)

# --- FÉRIAS ---
elif pagina == "Férias":
    st.subheader("Controle de Férias")

    with st.container():
        st.markdown("##### Filtros")
        c1, c2, c3 = st.columns(3)
        apenas_eqman = c1.checkbox("Apenas EqMan", key="fer_eq")
        apenas_in = c2.checkbox("Apenas Inspetores", key="fer_in")
        apenas_gvi = c3.checkbox("Apenas GVI/GP", key="fer_gv")

    if df_eventos.empty:
        st.write("Sem dados.")
    else:
        fer = df_eventos[df_eventos["Tipo"] == "Férias"].copy()
        fer = filtrar_eventos(fer, apenas_eqman, apenas_in, apenas_gvi)
        if fer.empty:
            st.info("Nenhuma férias para os filtros atuais.")
        else:
            tb = fer[["Posto", "Nome", "Escala", "Inicio", "Fim", "Duracao_dias"]].copy()
            tb["Início"] = tb["Inicio"].dt.strftime("%d/%m/%Y")
            tb["Término"] = tb["Fim"].dt.strftime("%d/%m/%Y")
            tb = tb.drop(columns=["Inicio", "Fim"]).rename(columns={"Duracao_dias": "Dias"})
            st.dataframe(tb, use_container_width=True, hide_index=True)
            
            c1, c2 = st.columns(2)
            c1.metric("Militares com férias cadastradas", fer["Nome"].nunique())
            c2.metric("Total de dias de férias", int(fer["Duracao_dias"].sum()))

# --- CURSOS ---
elif pagina == "Cursos":
    st.subheader("Controle de Cursos")

    with st.container():
        st.markdown("##### Filtros")
        c1, c2, c3 = st.columns(3)
        apenas_eqman = c1.checkbox("Apenas EqMan", key="cur_eq")
        apenas_in = c2.checkbox("Apenas Inspetores", key="cur_in")
        apenas_gvi = c3.checkbox("Apenas GVI/GP", key="cur_gv")

    if df_eventos.empty:
        st.write("Sem dados.")
    else:
        cur = df_eventos[df_eventos["Tipo"] == "Curso"].copy()
        cur = filtrar_eventos(cur, apenas_eqman, apenas_in, apenas_gvi)
        if cur.empty:
            st.info("Nenhum curso cadastrado para os filtros atuais.")
        else:
            real = cur[cur["Fim"] < hoje]
            fut = cur[cur["Fim"] >= hoje]
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### Cursos já realizados")
                if not real.empty:
                    tr = real[["Posto", "Nome", "Motivo", "Inicio", "Fim"]].copy()
                    tr["Início"] = tr["Inicio"].dt.strftime("%d/%m")
                    tr["Término"] = tr["Fim"].dt.strftime("%d/%m")
                    tr = tr.drop(columns=["Inicio", "Fim"])
                    st.dataframe(tr, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum curso concluído até a data de referência.")

            with c2:
                st.markdown("### Cursos em andamento / futuros")
                if not fut.empty:
                    ti = fut[["Posto", "Nome", "Motivo", "Inicio", "Fim"]].copy()
                    ti["Início"] = ti["Inicio"].dt.strftime("%d/%m")
                    ti["Término"] = ti["Fim"].dt.strftime("%d/%m")
                    ti = ti.drop(columns=["Inicio", "Fim"])
                    st.dataframe(ti, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum curso em andamento ou futuro.")

# --- LOG ---
elif pagina == "Log / Debug":
    st.subheader("Log / Debug")
    st.write(f"Linhas brutas em df_raw: {len(df_raw)}")
    st.dataframe(df_raw.head(), use_container_width=True)
    st.write("Blocos de Datas detectados:")
    st.write(BLOCOS_DATAS)
    st.write(f"Eventos processados: {len(df_eventos)}")
    st.dataframe(df_eventos.head(), use_container_width=True)


# ============================================================
# 12. RODAPÉ
# ============================================================
st.markdown("<hr style='border-color:#e5e7eb; margin-top:2rem;'/>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div style='text-align:center; color:#6b7280; padding:0.5rem 0; font-size:0.85rem;'>
        Created by <strong>Klismann Freitas</strong> • Versão do painel: <strong>{SCRIPT_VERSION}</strong>
    </div>
    """,
    unsafe_allow_html=True
)
