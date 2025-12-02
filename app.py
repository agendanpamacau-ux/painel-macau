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
SCRIPT_VERSION = "v0.5.0 (Com Agenda)"

# Use tema escuro moderno no Plotly
pio.templates.default = "plotly_dark"

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Navio-Patrulha Macau",
    layout="wide",
    page_icon="logo_npamacau.png"
)

# --- CSS global / tema dark profissional ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@600;700&family=Inter:wght@400;500;600&display=swap');

    * {
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at top left, #020617 0, #020617 40%, #020617 60%, #000 100%);
        color: #e5e7eb;
    }

    h1, h2, h3, h4 {
        color: #f9fafb !important;
        letter-spacing: 0.03em;
    }

    h1 {
        font-family: 'Raleway', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-weight: 700 !important;
    }

    /* Cards de métricas */
    div[data-testid="metric-container"] {
        background: rgba(15,23,42,0.95);
        border-radius: 0.9rem;
        padding: 1rem;
        border: 1px solid #1f2937;
        box-shadow: 0 14px 40px rgba(0,0,0,0.55);
    }

    div[data-testid="metric-container"] > label {
        color: #9ca3af !important;
        font-size: 0.80rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* Dataframes */
    .stDataFrame {
        background: #020617;
        border-radius: 0.75rem;
        padding: 0.25rem;
        border: 1px solid #1f2937;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #020617;
        border-right: 1px solid #111827;
    }

    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] h4 {
        color: #e5e7eb !important;
    }

    /* Labels da sidebar */
    section[data-testid="stSidebar"] label {
        color: #d1d5db !important;
    }

    /* Inputs da sidebar */
    section[data-testid="stSidebar"] .stDateInput > label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #9ca3af !important;
    }

    /* NAV LATERAL (radio estilizado como menu vertical) */
    div.nav-container > div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
    }

    /* Esconde o "círculo" do radio */
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

    /* Estilo base da aba (texto) */
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

    /* Hover */
    div.nav-container div[role="radio"]:hover {
        background: rgba(15,23,42,0.9);
    }
    div.nav-container div[role="radio"]:hover > div:nth-child(2) {
        color: #e5e7eb;
    }

    /* Aba selecionada: barra à esquerda + sublinhado */
    div.nav-container div[role="radio"][aria-checked="true"] {
        background: linear-gradient(90deg, rgba(56,189,248,0.18), transparent);
        border-left: 3px solid #38bdf8;
    }
    div.nav-container div[role="radio"][aria-checked="true"] > div:nth-child(2) {
        color: #f9fafb;
        text-decoration: underline;
        text-decoration-thickness: 2px;
        text-underline-offset: 0.28rem;
    }

    /* Botões / checkboxes / etc em dark mode */
    .stCheckbox > label, .stRadio > label, .stSelectbox > label {
        color: #e5e7eb !important;
    }

    /* Gráficos ocupando bem o espaço */
    .js-plotly-plot {
        border-radius: 0.75rem;
        box-shadow: 0 14px 45px rgba(0,0,0,0.65);
    }
    
    /* CARD AGENDA GOOGLE */
    .agenda-card {
        background-color: #1e293b;
        border-left: 4px solid #38bdf8;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .agenda-date {
        background-color: #0f172a;
        padding: 5px 12px;
        border-radius: 6px;
        color: #cbd5e1;
        font-size: 0.9rem;
        font-family: monospace;
        white-space: nowrap;
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
        st.write("⚓") # Fallback se a imagem não existir
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
# 2. HELPERS E CONSTANTES
# ============================================================

HEADER_ROW = 2  # linha 3 na planilha

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

# --- CONEXÃO COM GOOGLE CALENDAR ---
@st.cache_data(ttl=3600)
def get_calendar_list():
    try:
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        service = build('calendar', 'v3', credentials=creds)
        calendar_list = service.calendarList().list().execute()
        items = calendar_list.get('items', [])
        return {item['summary']: item['id'] for item in items}
    except Exception:
        return {}

@st.cache_data(ttl=300)
def load_calendar_events(calendar_id):
    try:
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        service = build('calendar', 'v3', credentials=creds)
        
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=now,
            maxResults=30, singleEvents=True, orderBy='startTime'
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
            except: data_fmt = start
            data.append({"Data": data_fmt, "Evento": summary})
            
        return pd.DataFrame(data)
    except: return pd.DataFrame()

# Inicialização dos dados
try:
    df_raw = load_data()
    dict_agendas = get_calendar_list()
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
# 5. TRANSFORMAÇÃO EM EVENTOS (WIDE → LONG)
# ============================================================

@st.cache_data(ttl=600)
def construir_eventos(df_raw: pd.DataFrame, blocos) -> pd.DataFrame:
    eventos = []

    for _, row in df_raw.iterrows():
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

        for col_ini, col_fim, col_mot, tipo_base in blocos:
            ini_raw = row.get(col_ini, pd.NaT)
            fim_raw = row.get(col_fim, pd.NaT)

            ini = pd.to_datetime(ini_raw, dayfirst=True, errors="coerce")
            fim = pd.to_datetime(fim_raw, dayfirst=True, errors="coerce")

            if pd.isna(ini) or pd.isna(fim): continue

            # Correção ano
            if ini.year < 2000: ini = ini.replace(year=ini.year + 100)
            if fim.year < 2000: fim = fim.replace(year=fim.year + 100)

            if fim < ini: ini, fim = fim, ini

            dur = (fim - ini).days + 1
            if dur < 1 or dur > 365*2: continue

            if tipo_base == "Férias":
                motivo_real = "Férias"
                tipo_final = "Férias"
            else:
                motivo_texto = ""
                if col_mot is not None:
                    motivo_texto = str(row.get(col_mot, "")).strip()

                if tipo_base == "Curso":
                    if motivo_texto and "nan" not in motivo_texto.lower():
                        motivo_real = motivo_texto
                    else:
                        motivo_real = "CURSO (não especificado)"
                    tipo_final = "Curso"
                else:
                    if motivo_texto and "nan" not in motivo_texto.lower():
                        motivo_real = motivo_texto
                    else:
                        motivo_real = "OUTROS"
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

    df_eventos = pd.DataFrame(eventos)
    return df_eventos

df_eventos = construir_eventos(df_raw, BLOCOS_DATAS)


# ============================================================
# 6. EXPANSÃO POR DIA
# ============================================================

@st.cache_data(ttl=600)
def expandir_eventos_por_dia(df_eventos: pd.DataFrame) -> pd.DataFrame:
    if df_eventos.empty: return pd.DataFrame()
    linhas = []
    for _, ev in df_eventos.iterrows():
        ini = ev["Inicio"]
        fim = ev["Fim"]
        if pd.isna(ini) or pd.isna(fim): continue
        for data in pd.date_range(ini, fim):
            linhas.append({
                "Data": data, "Posto": ev["Posto"], "Nome": ev["Nome"],
                "Escala": ev["Escala"], "EqMan": ev["EqMan"], "GVI": ev["GVI"],
                "IN": ev["IN"], "Motivo": ev["Motivo"], "MotivoAgrupado": ev["MotivoAgrupado"],
                "Tipo": ev["Tipo"]
            })
    return pd.DataFrame(linhas)

df_dias = expandir_eventos_por_dia(df_eventos)


# ============================================================
# 7. FUNÇÕES DE FILTRO
# ============================================================

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

def filtrar_dias(df, eq, inn, gv):
    res = df.copy()
    if eq: res = res[res["EqMan"] != "Não"]
    if inn: res = res[res["IN"] == True]
    if gv: res = res[res["GVI"] == True]
    return res


# ============================================================
# 8. PARÂMETROS E NAVEGAÇÃO
# ============================================================

st.sidebar.header("Parâmetros")
data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

st.sidebar.markdown("#### Navegação")
with st.sidebar.container():
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    # AQUI ESTÁ A NOVA OPÇÃO "Agenda"
    pagina = st.radio(
        label="Seções",
        options=[
            "Presentes",
            "Ausentes",
            "Agenda", 
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
# 9. MÉTRICAS GLOBAIS
# ============================================================

if not df_eventos.empty:
    ausentes_hoje_global = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
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
# 10. FUNÇÕES GRÁFICAS
# ============================================================

def grafico_pizza_motivos(df_motivos_dias, titulo):
    fig = px.pie(df_motivos_dias, names="MotivoAgrupado", values="Duracao_dias", hole=0.5)
    fig.update_traces(textposition="inside", textinfo="percent+label", hovertemplate="<b>%{label}</b><br>%{value} dias (%{percent})<extra></extra>")
    fig.update_layout(title=titulo, showlegend=True, legend_title_text="Motivo", margin=dict(t=60, b=20, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.9)", font=dict(family="Inter", color="#e5e7eb"))
    return fig


# ============================================================
# 11. PÁGINAS DO SISTEMA
# ============================================================

# --- PRESENTES ---
if pagina == "Presentes":
    st.subheader(f"Presentes a bordo em {hoje.strftime('%d/%m/%Y')}")
    
    with st.container():
        st.markdown("##### Filtros")
        c1, c2, c3 = st.columns(3)
        apenas_eqman = c1.checkbox("Apenas EqMan", key="pres_eq")
        apenas_in = c2.checkbox("Apenas Inspetores", key="pres_in")
        apenas_gvi = c3.checkbox("Apenas GVI/GP", key="pres_gv")

    df_trip = filtrar_tripulacao(df_raw, apenas_eqman, apenas_in, apenas_gvi)
    aus_hj = pd.DataFrame()
    if not df_eventos.empty:
        aus_hj = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
        aus_hj = filtrar_eventos(aus_hj, apenas_eqman, apenas_in, apenas_gvi)
    
    nomes_aus = set(aus_hj["Nome"].unique()) if not aus_hj.empty else set()
    df_pres = df_trip[~df_trip["Nome"].isin(nomes_aus)].copy()

    st.markdown(f"Total presente (filtrado): **{len(df_pres)}**")
    if df_pres.empty:
        st.info("Ninguém presente.")
    else:
        tabela = df_pres[["Posto", "Nome", "Serviço", "EqMan", "Gvi/GP", "IN"]].copy()
        tabela["GVI/GP"] = tabela["Gvi/GP"].apply(lambda v: "Sim" if parse_bool(v) else "Não")
        tabela["IN"] = tabela["IN"].apply(lambda v: "Sim" if parse_bool(v) else "Não")
        st.dataframe(tabela.drop(columns=["Gvi/GP"]), use_container_width=True, hide_index=True)

    # Prontidão Filtrada
    if len(df_trip) > 0:
        pront_pct = len(df_pres) / len(df_trip) * 100
        df_pr = pd.DataFrame({"Indicador": ["Prontidão"], "Percentual": [pront_pct]})
        fig = px.bar(df_pr, x="Percentual", y="Indicador", orientation="h", range_x=[0, 100], text="Percentual")
        fig.update_traces(texttemplate="%{x:.1f}%", textposition="inside")
        fig.update_layout(height=160, margin=dict(l=60,r=20,t=30,b=20), paper_bgcolor="rgba(15,23,42,0.9)", plot_bgcolor="rgba(15,23,42,0.9)", font=dict(color="#e5e7eb"))
        st.plotly_chart(fig, use_container_width=True)

# --- AUSENTES ---
elif pagina == "Ausentes":
    st.subheader(f"Ausentes em {hoje.strftime('%d/%m/%Y')}")
    
    with st.container():
        st.markdown("##### Filtros")
        c1, c2, c3 = st.columns(3)
        apenas_eqman = c1.checkbox("Apenas EqMan", key="aus_eq")
        apenas_in = c2.checkbox("Apenas Inspetores", key="aus_in")
        apenas_gvi = c3.checkbox("Apenas GVI/GP", key="aus_gv")

    if df_eventos.empty:
        st.info("Sem eventos.")
    else:
        aus = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
        aus = filtrar_eventos(aus, apenas_eqman, apenas_in, apenas_gvi)

        if aus.empty:
            st.success("Todo o efetivo a bordo.")
        else:
            temp = aus.copy()
            temp["MotivoExib"] = temp.apply(lambda r: "Férias" if r["Tipo"]=="Férias" else ("Curso" if r["Tipo"]=="Curso" else str(r["Motivo"])), axis=1)
            show = temp[["Posto", "Nome", "MotivoExib", "Fim"]].copy()
            show["Retorno"] = show["Fim"].dt.strftime("%d/%m/%Y")
            st.dataframe(show.drop(columns=["Fim"]).rename(columns={"MotivoExib":"Motivo"}), use_container_width=True, hide_index=True)

            eq_fora = aus[aus["EqMan"]!="Não"]
            if not eq_fora.empty:
                st.error(f"⚠️ **EqMan:** {'; '.join(sorted({f'{r.Posto} {r.Nome} ({r.EqMan})' for _,r in eq_fora.iterrows()}))}")
            
            gv_fora = aus[aus["GVI"]==True]
            if not gv_fora.empty:
                st.warning(f"🚨 **GVI/GP:** {'; '.join(sorted({f'{r.Posto} {r.Nome}' for _,r in gv_fora.iterrows()}))}")

# --- AGENDA DO NAVIO (NOVA ABA) ---
elif pagina == "Agenda":
    st.subheader("📅 Agenda do Navio (Google Calendar)")
    
    col_sel, col_btn = st.columns([3, 1])
    
    with col_sel:
        if not dict_agendas:
            st.warning("Nenhuma agenda detectada. Verifique se compartilhou com o e-mail do robô.")
            selected_id = None
        else:
            nome_agenda = st.selectbox("Selecione a Agenda:", list(dict_agendas.keys()))
            selected_id = dict_agendas[nome_agenda]
            
    with col_btn:
        st.write("") 
        st.write("")
        if st.button("🔄 Atualizar"):
            load_calendar_events.clear()
            st.rerun()
            
    if selected_id:
        df_cal = load_calendar_events(selected_id)
        
        if df_cal.empty:
            st.info("Nenhum evento futuro encontrado nesta agenda.")
        else:
            st.markdown("---")
            for _, row in df_cal.iterrows():
                st.markdown(
                    f"""
                    <div class="agenda-card">
                        <div style="font-weight: 600; color: #f8fafc; font-size: 1.1rem;">
                            {row['Evento']}
                        </div>
                        <div class="agenda-date">
                            {row['Data']}
                        </div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

# --- LINHA DO TEMPO ---
elif pagina == "Linha do Tempo":
    st.subheader("Cronograma Anual")
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
            fig = px.timeline(gantt, x_start="Inicio", x_end="Fim", y="Nome", color="MotivoAgrupado",
                              hover_data=["Posto", "Escala", "EqMan", "Tipo"], title="Cronograma")
            fig.update_yaxes(autorange="reversed")
            fig.add_vline(x=hoje, line_width=2, line_dash="dash", line_color="#f97316")
            fig.update_layout(paper_bgcolor="rgba(15,23,42,0.9)", plot_bgcolor="rgba(15,23,42,0.9)", font=dict(color="#e5e7eb"))
            st.plotly_chart(fig, use_container_width=True)

# --- ESTATÍSTICAS ---
elif pagina == "Estatísticas & Análises":
    st.subheader("Analytics")
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
        if evt.empty: st.info("Vazio.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Dias Totais", int(evt["Duracao_dias"].sum()))
            c2.metric("Média/Militar", f"{evt.groupby('Nome')['Duracao_dias'].sum().mean():.1f}")
            fer_evt = evt[evt["Tipo"]=="Férias"]
            c3.metric("Média Férias", f"{fer_evt.groupby('Nome')['Duracao_dias'].sum().mean():.1f}" if not fer_evt.empty else "0")
            
            st.markdown("---")
            grp = evt.groupby("MotivoAgrupado")["Duracao_dias"].sum().reset_index().sort_values("Duracao_dias", ascending=False)
            st.plotly_chart(grafico_pizza_motivos(grp, "Proporção por Motivo"), use_container_width=True)
            
            st.markdown("---")
            st.subheader("Top 10 Ausentes")
            top = evt.groupby(["Nome", "Posto"])["Duracao_dias"].sum().reset_index().sort_values("Duracao_dias", ascending=False).head(10)
            fig = px.bar(top, x="Nome", y="Duracao_dias", color="Posto", title="Top 10")
            fig.update_layout(paper_bgcolor="rgba(15,23,42,0.9)", plot_bgcolor="rgba(15,23,42,0.9)", font=dict(color="#e5e7eb"))
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

    if df_eventos.empty: st.write("Sem dados.")
    else:
        fer = df_eventos[df_eventos["Tipo"]=="Férias"].copy()
        fer = filtrar_eventos(fer, apenas_eqman, apenas_in, apenas_gvi)
        if fer.empty: st.info("Vazio.")
        else:
            tb = fer[["Posto", "Nome", "Escala", "Inicio", "Fim", "Duracao_dias"]].copy()
            tb["Início"] = tb["Inicio"].dt.strftime("%d/%m/%Y")
            tb["Término"] = tb["Fim"].dt.strftime("%d/%m/%Y")
            st.dataframe(tb.drop(columns=["Inicio","Fim"]).rename(columns={"Duracao_dias":"Dias"}), use_container_width=True, hide_index=True)
            
            c1, c2 = st.columns(2)
            c1.metric("Militares c/ Férias", fer["Nome"].nunique())
            c2.metric("Total Dias", int(fer["Duracao_dias"].sum()))

# --- CURSOS ---
elif pagina == "Cursos":
    st.subheader("Controle de Cursos")
    with st.container():
        st.markdown("##### Filtros")
        c1, c2, c3 = st.columns(3)
        apenas_eqman = c1.checkbox("Apenas EqMan", key="cur_eq")
        apenas_in = c2.checkbox("Apenas Inspetores", key="cur_in")
        apenas_gvi = c3.checkbox("Apenas GVI/GP", key="cur_gv")

    if df_eventos.empty: st.write("Sem dados.")
    else:
        cur = df_eventos[df_eventos["Tipo"]=="Curso"].copy()
        cur = filtrar_eventos(cur, apenas_eqman, apenas_in, apenas_gvi)
        if cur.empty: st.info("Vazio.")
        else:
            real = cur[cur["Fim"] < hoje]
            fut = cur[cur["Fim"] >= hoje]
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### Já Realizados")
                if not real.empty:
                    tr = real[["Posto", "Nome", "Motivo", "Inicio", "Fim"]].copy()
                    tr["Início"] = tr["Inicio"].dt.strftime("%d/%m")
                    st.dataframe(tr.drop(columns=["Inicio","Fim"]), use_container_width=True, hide_index=True)
                else: st.info("Nenhum.")
            with c2:
                st.markdown("### Em Andamento / Futuros")
                if not fut.empty:
                    ti = fut[["Posto", "Nome", "Motivo", "Inicio", "Fim"]].copy()
                    ti["Início"] = ti["Inicio"].dt.strftime("%d/%m")
                    ti["Término"] = ti["Fim"].dt.strftime("%d/%m")
                    st.dataframe(ti.drop(columns=["Inicio","Fim"]), use_container_width=True, hide_index=True)
                else: st.info("Nenhum.")

# --- LOG ---
elif pagina == "Log / Debug":
    st.subheader("Debug")
    st.write("Linhas Brutas:", len(df_raw))
    st.dataframe(df_raw.head())
    st.write("Blocos de Datas:", BLOCOS_DATAS)
    st.write("Eventos Processados:", len(df_eventos))
    st.dataframe(df_eventos.head())

# ============================================================
# 12. RODAPÉ
# ============================================================
st.markdown("<hr style='border-color:#111827; margin-top:2rem;'/>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div style='text-align:center; color:#9ca3af; padding:0.5rem 0; font-size:0.85rem;'>
        Created by <strong>Klismann Freitas</strong> • Versão do painel: <strong>{SCRIPT_VERSION}</strong>
    </div>
    """,
    unsafe_allow_html=True
)
