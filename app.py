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
SCRIPT_VERSION = "v2.1 (Full - Menu Limpo + Data Local)"

# Use tema escuro moderno no Plotly
pio.templates.default = "plotly_dark"

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS
# ============================================================
st.set_page_config(
    page_title="Navio-Patrulha Macau",
    layout="wide",
    page_icon="logo_npamacau.png"
)

# --- CSS PERSONALIZADO (Design System) ---
st.markdown(
    """
    <style>
    /* Importa Fonte Raleway e Inter */
    @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@700&family=Inter:wght@400;500;600&display=swap');

    /* Reset Geral */
    * { font-family: 'Inter', sans-serif; }
    .stApp { 
        background: radial-gradient(circle at top left, #020617 0, #020617 40%, #000 100%);
        color: #f8fafc; 
    }

    /* TÍTULO PRINCIPAL (RALEWAY) - Solicitado no item 1 */
    h1 {
        font-family: 'Raleway', sans-serif !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    /* Outros Títulos */
    h2, h3, h4 { color: #f1f5f9 !important; }

    /* --- SIDEBAR CUSTOMIZADA --- */
    section[data-testid="stSidebar"] {
        background-color: #020617;
        border-right: 1px solid #1e293b;
    }
    
    /* ESCONDER BOLINHAS DOS RADIO BUTTONS (Item 2) */
    div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }
    div[role="radiogroup"] label {
        padding: 12px 16px;
        margin-bottom: 4px;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s;
        color: #94a3b8 !important; /* Texto inativo */
        font-weight: 500;
        display: flex;
        align-items: center;
        width: 100%;
    }
    /* Hover no item do menu */
    div[role="radiogroup"] label:hover {
        background-color: rgba(255,255,255, 0.05);
        color: #f8fafc !important;
    }
    /* Item Selecionado */
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: rgba(14, 165, 233, 0.15); /* Azul translúcido */
        color: #38bdf8 !important; /* Azul claro */
        border-left: 4px solid #38bdf8;
        font-weight: 600;
    }

    /* --- COMPONENTES --- */
    /* Cards */
    div[data-testid="metric-container"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    div[data-testid="metric-container"] label { color: #64748b !important; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #f8fafc !important; }

    /* Tabelas */
    .stDataFrame { 
        background-color: #020617;
        border: 1px solid #334155; 
        border-radius: 8px; 
        padding: 5px;
    }

    /* Inputs e Checkboxes */
    .stCheckbox label { color: #e2e8f0 !important; }
    .stDateInput label { color: #94a3b8 !important; }
    
    /* Card Agenda */
    .agenda-card {
        background: #1e293b; 
        border-left: 4px solid #0ea5e9;
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 10px;
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .agenda-date {
        background: #0f172a; 
        padding: 5px 10px; 
        border-radius: 6px;
        color: #94a3b8; 
        font-family: monospace; 
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# CABEÇALHO (Logo + Título Raleway)
c_logo, c_text = st.columns([1, 6])
with c_logo:
    try: 
        st.image("logo_npamacau.png", width=75)
    except: 
        st.write("⚓")
with c_text:
    st.markdown("<h1>Navio-Patrulha Macau</h1>", unsafe_allow_html=True)

# ============================================================
# 2. CONSTANTES E CONFIGURAÇÕES
# ============================================================
HEADER_ROW = 2  # Linha 3 na planilha (índice 2 no Python)

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
    if pd.isna(value): return False
    return str(value).strip().lower() in ("true", "1", "sim", "yes", "y", "x")

# ============================================================
# 3. CARGA DE DADOS (Conexões)
# ============================================================
@st.cache_data(ttl=600, show_spinner="Carregando dados da planilha...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Afastamento 2026", header=HEADER_ROW, ttl="10m")
    # Limpeza básica: remove linhas onde o nome está vazio
    if "Nome" in df.columns: 
        df = df.dropna(subset=["Nome"])
    return df.reset_index(drop=True)

@st.cache_data(ttl=300)
def load_calendar_events(calendar_id):
    """Carrega eventos do Google Calendar usando credenciais de serviço."""
    try:
        # Reconstrói as credenciais a partir do segredo do Streamlit
        creds = service_account.Credentials.from_service_account_info(
            dict(st.secrets["connections"]["gsheets"]),
            scopes=['https://www.googleapis.com/auth/calendar.readonly']
        )
        service = build('calendar', 'v3', credentials=creds)
        
        now = datetime.utcnow().isoformat() + 'Z'
        res = service.events().list(
            calendarId=calendar_id, 
            timeMin=now, 
            maxResults=30, 
            singleEvents=True, 
            orderBy='startTime'
        ).execute()
        
        data = []
        for e in res.get('items', []):
            start = e['start'].get('dateTime', e['start'].get('date'))
            summary = e.get('summary', 'Sem Título')
            try:
                dt = pd.to_datetime(start)
                # Formatação inteligente: se tem hora, mostra hora. Se não, só data.
                fmt = "%d/%m %H:%M" if 'T' in start else "%d/%m"
                d_fmt = dt.strftime(fmt)
            except: 
                d_fmt = start
            data.append({"Data": d_fmt, "Evento": summary})
            
        return pd.DataFrame(data)
    except Exception as e:
        # Retorna DataFrame vazio em caso de erro (ex: falta de permissão)
        return pd.DataFrame()

# Carrega a planilha principal ao iniciar
try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro Crítico de Conexão: {e}")
    st.stop()

# ============================================================
# 4. PROCESSAMENTO DE DADOS (Detectar Blocos e Criar Eventos)
# ============================================================
def descobrir_blocos(df):
    """Varre as colunas para identificar os trios (Início, Fim, Motivo)."""
    cols = list(df.columns)
    blocos = []
    
    for i, nome in enumerate(cols):
        n = str(nome)
        # Procura coluna de Início
        if not (n.startswith("Início") or n.startswith("Inicio")): continue
        
        # Procura Fim correspondente à direita
        j = next((x for x in range(i+1, len(cols)) if str(cols[x]).startswith("Fim") or str(cols[x]).startswith("FIm")), None)
        if j is None: continue
        
        # Procura Motivo ou Curso nas proximidades
        k = None
        tipo = "Férias" # Padrão para os primeiros blocos
        
        # Tenta achar motivo nas 4 colunas seguintes ao fim
        for x in range(j+1, min(j+4, len(cols))):
            nx = str(cols[x])
            if "Motivo" in nx: 
                k, tipo = x, "Outros"
                break
            if "Curso" in nx: 
                k, tipo = x, "Curso"
                break
                
        blocos.append((cols[i], cols[j], cols[k] if k else None, tipo))
    return blocos

BLOCOS = descobrir_blocos(df_raw)

@st.cache_data(ttl=600)
def construir_eventos(df, blocos):
    """Transforma a planilha larga em uma lista vertical de eventos."""
    evts = []
    for _, row in df.iterrows():
        # Dados do Militar
        base = {
            "Posto": row.get("Posto"), 
            "Nome": row.get("Nome"), 
            "Escala": row.get("Serviço"),
            "EqMan": str(row.get("EqMan")) if pd.notna(row.get("EqMan")) and str(row.get("EqMan"))!="-" else "Não",
            "GVI": parse_bool(row.get("Gvi/GP")), 
            "IN": parse_bool(row.get("IN"))
        }
        
        # Processa cada bloco de datas encontrado
        for c_ini, c_fim, c_mot, tipo_base in blocos:
            ini = pd.to_datetime(row.get(c_ini, pd.NaT), dayfirst=True, errors='coerce')
            fim = pd.to_datetime(row.get(c_fim, pd.NaT), dayfirst=True, errors='coerce')
            
            if pd.isna(ini) or pd.isna(fim): continue
            
            # Correção do Bug do Ano 1925 (Sheets envia 2 digitos)
            if ini.year < 2000: ini = ini.replace(year=ini.year+100)
            if fim.year < 2000: fim = fim.replace(year=fim.year+100)
            
            if fim < ini: ini, fim = fim, ini
            
            dur = (fim - ini).days + 1
            if dur < 1 or dur > 730: continue # Ignora erros de data absurdos

            # Definição do Motivo Real
            if tipo_base == "Férias":
                mot, tipo = "Férias", "Férias"
            else:
                txt = str(row.get(c_mot, "")).strip() if c_mot else ""
                # Se tem a palavra "curso" no motivo, classifica como Curso
                tipo = "Curso" if "curso" in txt.lower() else tipo_base
                # Se o texto for válido, usa ele. Senão usa o genérico.
                mot = txt if len(txt) > 2 and "nan" not in txt.lower() else ("CURSO" if tipo=="Curso" else "OUTROS")
            
            evts.append({
                **base, 
                "Inicio": ini, "Fim": fim, 
                "Duracao_dias": dur, 
                "Motivo": mot, "MotivoAgrupado": mot, 
                "Tipo": tipo
            })
            
    return pd.DataFrame(evts)

df_eventos = construir_eventos(df_raw, BLOCOS)

def filtrar_dados(df, eq, inn, gv):
    """Aplica os filtros de equipe ao DataFrame."""
    res = df.copy()
    if eq:
        if "EqMan" in res.columns: res = res[(res["EqMan"].notna()) & (res["EqMan"]!="Não")]
    if inn: 
        if "IN" in res.columns: res = res[res["IN"]==True]
    if gv: 
        if "GVI" in res.columns: res = res[res["GVI"]==True]
        elif "Gvi/GP" in res.columns: res = res[res["Gvi/GP"].apply(parse_bool)]
    return res

# ============================================================
# 5. BARRA LATERAL (MENU DE NAVEGAÇÃO)
# ============================================================
with st.sidebar:
    st.markdown("### Navegação")
    # Menu limpo sem bolinhas (Item 4 do pedido)
    pagina = st.radio(
        "Menu",
        [
            "Presentes",
            "Ausentes",
            "Agenda do Navio",
            "Linha do Tempo",
            "Estatísticas & Análises",
            "Férias",
            "Cursos",
            "Log / Debug"
        ],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption(f"Versão: {SCRIPT_VERSION}")

# ============================================================
# 6. PÁGINAS DO APLICATIVO
# ============================================================

# --------------------------------------------------------
# PÁGINA: PRESENTES
# --------------------------------------------------------
if pagina == "Presentes":
    st.subheader("Lista de Presentes")
    
    # Item 3: Data e Filtros na própria aba (Container)
    with st.container():
        col_dt, col_filt = st.columns([1, 2])
        
        with col_dt:
            # Data de referência LOCAL
            data_ref = st.date_input("📅 Data de Referência", datetime.today())
            hoje = pd.to_datetime(data_ref)
            
        with col_filt:
            st.markdown("###### Filtros de Equipe")
            c1, c2, c3 = st.columns(3)
            f_eq = c1.checkbox("Apenas EqMan", key="p_eq")
            f_in = c2.checkbox("Apenas IN", key="p_in")
            f_gv = c3.checkbox("Apenas GVI", key="p_gv")
            
    st.markdown("---")

    # Lógica de Filtragem
    df_trip = filtrar_dados(df_raw, f_eq, f_in, f_gv)
    
    aus = pd.DataFrame()
    if not df_eventos.empty:
        # Filtra eventos que ocorrem na data selecionada
        aus = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
        aus = filtrar_dados(aus, f_eq, f_in, f_gv)
    
    # Quem está na lista de ausentes hoje?
    nomes_aus = set(aus["Nome"].unique()) if not aus.empty else set()
    # Quem sobra é quem está presente
    pres = df_trip[~df_trip["Nome"].isin(nomes_aus)]

    # KPIs Rápidos
    k1, k2 = st.columns(2)
    k1.metric("Efetivo Total (Filtro)", len(df_trip))
    k2.metric("Presentes a Bordo", len(pres))

    if pres.empty:
        st.info("Ninguém presente com os filtros selecionados.")
    else:
        # Prepara Tabela
        cols_show = ["Posto", "Nome", "Serviço", "EqMan", "Gvi/GP", "IN"]
        # Ajusta para não dar erro se coluna não existir
        cols_validas = [c for c in cols_show if c in pres.columns]
        
        show = pres[cols_validas].copy()
        
        # Formatar booleanos visualmente
        if "Gvi/GP" in show.columns:
            show["Gvi/GP"] = show["Gvi/GP"].apply(lambda x: "Sim" if parse_bool(x) else "Não")
        if "IN" in show.columns:
            show["IN"] = show["IN"].apply(lambda x: "Sim" if parse_bool(x) else "Não")
            
        st.dataframe(show, use_container_width=True, hide_index=True)

# --------------------------------------------------------
# PÁGINA: AUSENTES
# --------------------------------------------------------
elif pagina == "Ausentes":
    st.subheader("Lista de Ausentes")
    
    # Item 3: Data e Filtros na própria aba
    with st.container():
        col_dt, col_filt = st.columns([1, 2])
        with col_dt:
            data_ref = st.date_input("📅 Data de Referência", datetime.today())
            hoje = pd.to_datetime(data_ref)
        with col_filt:
            st.markdown("###### Filtros de Equipe")
            c1, c2, c3 = st.columns(3)
            f_eq = c1.checkbox("Apenas EqMan", key="a_eq")
            f_in = c2.checkbox("Apenas IN", key="a_in")
            f_gv = c3.checkbox("Apenas GVI", key="a_gv")
    
    st.markdown("---")

    if df_eventos.empty:
        st.info("Sem eventos registrados na planilha.")
    else:
        # Filtra eventos ativos na data
        aus = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
        # Aplica filtro de equipe
        aus = filtrar_dados(aus, f_eq, f_in, f_gv)

        st.metric("Total de Ausentes", len(aus))

        if aus.empty:
            st.success("Todo o efetivo está a bordo na data selecionada.")
        else:
            # Tabela
            show = aus[["Posto", "Nome", "Motivo", "Fim"]].copy()
            show["Retorno Previsto"] = show["Fim"].dt.strftime("%d/%m/%Y")
            st.dataframe(show.drop(columns=["Fim"]), use_container_width=True, hide_index=True)
            
            # Alertas Especiais
            eq_out = aus[aus["EqMan"]!="Não"]
            if not eq_out.empty:
                st.error(f"⚠️ **Alerta EqMan:** {', '.join(sorted(eq_out['Nome'].unique()))}")

# --------------------------------------------------------
# PÁGINA: AGENDA DO NAVIO
# --------------------------------------------------------
elif pagina == "Agenda do Navio":
    st.subheader("📅 Agenda do Navio (Google Calendar)")
    
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        # Seletor usando as agendas fixas
        nome_ag = st.selectbox("Selecione a Agenda:", list(AGENDAS_OFICIAIS.keys()))
        id_ag = AGENDAS_OFICIAIS[nome_ag]
    with col_btn:
        st.write("")
        st.write("")
        if st.button("🔄 Atualizar"): 
            load_calendar_events.clear()
            st.rerun()
            
    df_cal = load_calendar_events(id_ag)
    
    if df_cal.empty:
        st.info("Nenhum evento futuro encontrado nesta agenda (ou calendário vazio).")
    else:
        st.markdown("---")
        # Layout de Cards para Agenda
        for _, row in df_cal.iterrows():
            st.markdown(
                f"""
                <div class="agenda-card">
                    <div style="font-weight:600; color:#f8fafc; font-size:1.1rem;">{row['Evento']}</div>
                    <div class="agenda-date">{row['Data']}</div>
                </div>
                """, unsafe_allow_html=True
            )

# --------------------------------------------------------
# PÁGINA: LINHA DO TEMPO (GANTT)
# --------------------------------------------------------
elif pagina == "Linha do Tempo":
    st.subheader("Cronograma Anual de Afastamentos")
    
    # Filtros locais
    c1, c2, c3 = st.columns(3)
    f_eq = c1.checkbox("EqMan", key="g_eq")
    f_in = c2.checkbox("IN", key="g_in")
    f_gv = c3.checkbox("GVI", key="g_gv")
    
    if df_eventos.empty:
        st.info("Sem dados de datas na planilha.")
    else:
        gantt = filtrar_dados(df_eventos, f_eq, f_in, f_gv)
        
        if gantt.empty:
            st.info("Sem eventos para o filtro selecionado.")
        else:
            hoje_g = datetime.today()
            # Gráfico Gantt
            fig = px.timeline(
                gantt, 
                x_start="Inicio", x_end="Fim", y="Nome", 
                color="MotivoAgrupado",
                hover_data=["Posto", "Escala", "Tipo"], 
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig.update_yaxes(autorange="reversed") # Nomes de cima para baixo
            # Linha vertical indicando "Hoje"
            fig.add_vline(x=hoje_g, line_width=2, line_dash="dash", line_color="#38bdf8")
            
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", 
                plot_bgcolor="rgba(255,255,255,0.05)", 
                font=dict(color="#cbd5e1"),
                margin=dict(t=20, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------
# PÁGINA: ESTATÍSTICAS
# --------------------------------------------------------
elif pagina == "Estatísticas & Análises":
    st.subheader("Analytics e Indicadores")
    
    # Filtros para estatísticas
    c1, c2, c3 = st.columns(3)
    f_eq = c1.checkbox("EqMan", key="s_eq")
    f_in = c2.checkbox("IN", key="s_in")
    f_gv = c3.checkbox("GVI", key="s_gv")
    
    evt = df_eventos.copy()
    if not evt.empty:
        evt = filtrar_dados(evt, f_eq, f_in, f_gv)
        
        k1, k2 = st.columns(2)
        k1.metric("Dias de Ausência (Soma)", int(evt["Duracao_dias"].sum()))
        if len(evt) > 0:
            media = evt.groupby('Nome')['Duracao_dias'].sum().mean()
            k2.metric("Média Dias/Militar", f"{media:.1f}")
        
        st.markdown("---")
        
        # Gráfico de Pizza (Motivos)
        grp = evt.groupby("MotivoAgrupado")["Duracao_dias"].sum().reset_index().sort_values("Duracao_dias", ascending=False)
        
        fig = px.pie(grp, names="MotivoAgrupado", values="Duracao_dias", hole=0.5)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", 
            font=dict(color="#fff"),
            title="Distribuição por Motivo (Dias Totais)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para exibir.")

# --------------------------------------------------------
# PÁGINA: FÉRIAS
# --------------------------------------------------------
elif pagina == "Férias":
    st.subheader("Controle de Férias")
    
    # Filtros
    c1, c2, c3 = st.columns(3)
    f_eq = c1.checkbox("EqMan", key="f_eq")
    f_in = c2.checkbox("IN", key="f_in")
    f_gv = c3.checkbox("GVI", key="f_gv")

    if df_eventos.empty: 
        st.write("Sem dados.")
    else:
        fer = df_eventos[df_eventos["Tipo"]=="Férias"].copy()
        fer = filtrar_dados(fer, f_eq, f_in, f_gv)
        
        if fer.empty: 
            st.info("Nenhuma férias encontrada.")
        else:
            # Tabela Formatada
            tb = fer[["Posto", "Nome", "Escala", "Inicio", "Fim", "Duracao_dias"]].copy()
            tb["Início"] = tb["Inicio"].dt.strftime("%d/%m/%Y")
            tb["Término"] = tb["Fim"].dt.strftime("%d/%m/%Y")
            st.dataframe(tb.drop(columns=["Inicio","Fim"]).rename(columns={"Duracao_dias":"Dias"}).sort_values("Início"), use_container_width=True, hide_index=True)
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            c1.metric("Militares c/ Férias", fer["Nome"].nunique())
            c2.metric("Total Dias de Férias", int(fer["Duracao_dias"].sum()))

# --------------------------------------------------------
# PÁGINA: CURSOS
# --------------------------------------------------------
elif pagina == "Cursos":
    st.subheader("Controle de Cursos")
    
    c1, c2, c3 = st.columns(3)
    f_eq = c1.checkbox("EqMan", key="c_eq")
    f_in = c2.checkbox("IN", key="c_in")
    f_gv = c3.checkbox("GVI", key="c_gv")

    if df_eventos.empty: 
        st.write("Sem dados.")
    else:
        cur = df_eventos[df_eventos["Tipo"]=="Curso"].copy()
        cur = filtrar_dados(cur, f_eq, f_in, f_gv)
        
        if cur.empty: 
            st.info("Nenhum curso encontrado.")
        else:
            hj = datetime.today()
            real = cur[cur["Fim"] < hj]
            fut = cur[cur["Fim"] >= hj]
            
            col_fut, col_real = st.columns(2)
            
            with col_fut:
                st.markdown("#### 🎓 Futuros / Em Andamento")
                if not fut.empty:
                    ti = fut[["Posto", "Nome", "Motivo", "Inicio", "Fim"]].copy()
                    ti["Início"] = ti["Inicio"].dt.strftime("%d/%m")
                    ti["Término"] = ti["Fim"].dt.strftime("%d/%m")
                    st.dataframe(ti.drop(columns=["Inicio","Fim"]), use_container_width=True, hide_index=True)
                else: st.info("Nenhum.")
                
            with col_real:
                st.markdown("#### ✅ Já Realizados")
                if not real.empty:
                    tr = real[["Posto", "Nome", "Motivo", "Inicio", "Fim"]].copy()
                    tr["Início"] = tr["Inicio"].dt.strftime("%d/%m")
                    st.dataframe(tr.drop(columns=["Inicio","Fim"]), use_container_width=True, hide_index=True)
                else: st.info("Nenhum.")

# --------------------------------------------------------
# PÁGINA: LOG / DEBUG
# --------------------------------------------------------
elif pagina == "Log / Debug":
    st.subheader("Área Técnica (Debug)")
    st.write(f"Total Linhas Brutas: {len(df_raw)}")
    with st.expander("Ver Planilha Bruta"):
        st.dataframe(df_raw.head(20))
    
    st.write(f"Blocos de Datas Detectados: {len(BLOCOS)}")
    st.write(BLOCOS)
    
    st.write(f"Total Eventos Gerados: {len(df_eventos)}")
    with st.expander("Ver Eventos Processados"):
        st.dataframe(df_eventos)

# ============================================================
# 12. RODAPÉ
# ============================================================
st.markdown("<hr style='border-color:#1e293b; margin-top:3rem;'/>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div style='text-align:center; color:#64748b; padding:1rem; font-size:0.8rem;'>
        Navio-Patrulha Macau • Controle de Efetivo & Agenda • {SCRIPT_VERSION}
    </div>
    """,
    unsafe_allow_html=True
)
