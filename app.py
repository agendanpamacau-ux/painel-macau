import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Navio-Patrulha Macau",
    layout="wide",
    page_icon="logo_npamacau.png"
)

APP_VERSION = "v1.11.0 - Mapeamento Compacto"

# --- CSS global / tema ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@600;700&display=swap');

    * {
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at top left, #020617 0, #020617 40%, #000 100%);
        color: #e5e7eb;
    }

    h1, h2, h3, h4 {
        color: #e5e7eb !important;
        letter-spacing: 0.03em;
    }

    /* Título com fonte Raleway em negrito */
    h1 {
        font-family: 'Raleway', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-weight: 700 !important;
    }

    div[data-testid="metric-container"] {
        background: rgba(15, 23, 42, 0.9);
        border-radius: 0.9rem;
        padding: 1rem;
        border: 1px solid #1f2937;
        box-shadow: 0 12px 30px rgba(0,0,0,0.45);
    }

    div[data-testid="metric-container"] > label {
        color: #9ca3af !important;
        font-size: 0.80rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .stDataFrame {
        background: #020617;
        border-radius: 0.75rem;
        padding: 0.5rem;
    }

    section[data-testid="stSidebar"] img {
        display: block;
        margin: 0.5rem auto 0.5rem auto;
    }

    .sidebar-title {
        text-align: center;
        font-weight: 600;
        margin-top: 0.3rem;
        margin-bottom: 0.4rem;
    }
    .sidebar-section {
        margin-top: 0.8rem;
        margin-bottom: 0.4rem;
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #9ca3af;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <h1 style="margin-top:0.2rem; margin-bottom:0.2rem;">
        Navio-Patrulha Macau
    </h1>
    """,
    unsafe_allow_html=True
)

# ============================================================
# 2. HELPERS E MAPEAMENTO DE COLUNAS
# ============================================================

HEADER_ROW = 2  # Linha 3 da planilha

def col_generator():
    """
    Gera a sequência EXATA de colunas que contêm dados, pulando as vazias.
    Baseado na estrutura fornecida:
    A-G (Dados Pessoais) -> H (Pula)
    I-W (Férias) -> X (Pula)
    Y-AB (P4) -> AC (Pula)
    AD-AG (P5) -> AH (Pula)
    AI-AL (P6) -> AM (Pula)
    AN-AQ (P7) -> AR (Pula)
    AS-AV (P8) -> AW (Pula) ... Grande Salto ...
    DH-GW (P9) -> IC (Pula)
    ID-IG (P10)
    """
    # Helper para converter range de letras em lista
    def char_range(c1, c2):
        """Gera range de colunas simples (ex: A-Z). Não lida com AA, AB complexos aqui por simplicidade, 
           vamos listar blocos explicitamente se forem complexos."""
        for c in range(ord(c1), ord(c2) + 1):
            yield chr(c)

    # Lista ordenada das colunas VÁLIDAS (que o Pandas vai ler)
    valid_cols = []
    
    # Bloco A até G
    valid_cols.extend(list(char_range('A', 'G')))
    
    # Bloco I até W
    valid_cols.extend(list(char_range('I', 'W')))
    
    # Bloco Y até AB
    valid_cols.extend(['Y', 'Z', 'AA', 'AB'])
    
    # Bloco AD até AG
    valid_cols.extend(['AD', 'AE', 'AF', 'AG'])
    
    # Bloco AI até AL
    valid_cols.extend(['AI', 'AJ', 'AK', 'AL'])
    
    # Bloco AN até AQ
    valid_cols.extend(['AN', 'AO', 'AP', 'AQ'])
    
    # Bloco AS até AV
    valid_cols.extend(['AS', 'AT', 'AU', 'AV'])
    
    # Bloco P9: DH até GW (DH, EL, FR, GW) - LISTA EXPLÍCITA POIS SÃO COLUNAS ESPARSAS
    # Nota: Entre AW e DH existe um abismo. O Pandas vai colar DH logo após AV.
    # O user listou: DH (Início), EL (Fim), FR (Diff), GW (Curso)
    valid_cols.extend(['DH', 'EL', 'FR', 'GW'])
    
    # Bloco P10: ID até IG (ID, IE, IF, IG)
    valid_cols.extend(['ID', 'IE', 'IF', 'IG'])
    
    return valid_cols

# Criamos um mapa: Letra Excel -> Índice Inteiro no DataFrame Compactado
# Ex: 'A' -> 0, 'I' -> 7 (pois H pulou), 'DH' -> 39 (após todos os pulos)
VALID_COLUMNS_ORDER = col_generator()
COL_MAP = {letter: idx for idx, letter in enumerate(VALID_COLUMNS_ORDER)}

def get_col_name_compact(df: pd.DataFrame, letter: str):
    """
    Retorna o nome da coluna no DataFrame baseado no Mapa Compacto.
    """
    if letter not in COL_MAP:
        return None
    
    idx_real = COL_MAP[letter]
    
    # Proteção: se o índice calculado for maior que as colunas que vieram
    if idx_real < len(df.columns):
        return df.columns[idx_real]
    return None

def parse_bool(value) -> bool:
    if pd.isna(value): return False
    s = str(value).strip().lower()
    return s in ("true", "1", "sim", "yes", "y", "x")

# ============================================================
# 3. CARGA DE DADOS
# ============================================================

@st.cache_data(ttl=600, show_spinner="Carregando dados...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Afastamento 2026", header=HEADER_ROW, ttl="10m")
    
    # Tenta achar a coluna Nome (C)
    c_nome = get_col_name_compact(df, "C")
    if c_nome:
        df = df.dropna(subset=[c_nome])
    
    df = df.reset_index(drop=True)
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro ao ler planilha. Detalhe: {e}")
    st.stop()

# ============================================================
# 3.1 CONFIGURAÇÃO DOS BLOCOS DE AUSÊNCIA
# ============================================================

# Férias (Inicio, Fim)
FERIAS_CONFIG = [("I", "J"), ("L", "M"), ("O", "P")]

# Outros / Cursos (Inicio, Fim, Motivo, Categoria)
AUSENCIAS_CONFIG = [
    ("Y",  "Z",  "AB", "Outros"), # P4
    ("AD", "AE", "AG", "Outros"), # P5
    ("AI", "AJ", "AL", "Outros"), # P6
    ("AN", "AO", "AQ", "Curso"),  # P7
    ("AS", "AT", "AV", "Curso"),  # P8
    ("DH", "EL", "GW", "Curso"),  # P9 (Gap Grande)
    ("ID", "IE", "IG", "Curso"),  # P10
]

# ============================================================
# 4. TRANSFORMAÇÃO EM EVENTOS
# ============================================================

@st.cache_data(ttl=600)
def construir_eventos(df: pd.DataFrame) -> pd.DataFrame:
    eventos = []

    # Identificar colunas fixas usando o mapa compacto
    c_posto = get_col_name_compact(df, "B")
    c_nome  = get_col_name_compact(df, "C")
    c_sv    = get_col_name_compact(df, "D")
    c_eq    = get_col_name_compact(df, "E")
    c_gvi   = get_col_name_compact(df, "F")
    c_in    = get_col_name_compact(df, "G")

    for _, row in df.iterrows():
        posto  = row.get(c_posto, "")
        nome   = row.get(c_nome, "")
        
        militar_info = {
            "Posto": str(posto),
            "Nome": str(nome),
            "Escala": str(row.get(c_sv, "")),
            "EqMan": str(row.get(c_eq, "")) if pd.notna(row.get(c_eq)) and str(row.get(c_eq)) not in ("-", "") else "Não",
            "GVI": parse_bool(row.get(c_gvi)),
            "IN": parse_bool(row.get(c_in)),
        }

        # Função Helper
        def add_evt(letra_ini, letra_fim, letra_mot, tipo_base):
            c_i = get_col_name_compact(df, letra_ini)
            c_f = get_col_name_compact(df, letra_fim)
            c_m = get_col_name_compact(df, letra_mot) if letra_mot else None
            
            val_ini = row.get(c_i) if c_i else None
            val_fim = row.get(c_f) if c_f else None
            val_mot = row.get(c_m) if c_m else None

            ini = pd.to_datetime(val_ini, dayfirst=True, errors="coerce")
            fim = pd.to_datetime(val_fim, dayfirst=True, errors="coerce")

            if pd.notna(ini) and pd.notna(fim):
                if fim < ini: ini, fim = fim, ini
                dur = (fim - ini).days + 1
                
                if ini.year < 2020 or dur > 365: return 

                motivo_txt = str(val_mot).strip()
                if not motivo_txt or motivo_txt.lower() == "nan":
                    motivo_real = "CURSO" if tipo_base == "Curso" else "AUSÊNCIA"
                else:
                    motivo_real = motivo_txt

                eventos.append({
                    **militar_info,
                    "Inicio": ini,
                    "Fim": fim,
                    "Duracao_dias": dur,
                    "Motivo": motivo_real,
                    "Tipo": "Férias" if tipo_base == "Férias" else tipo_base
                })

        # Processar Férias
        for l_i, l_f in FERIAS_CONFIG:
            add_evt(l_i, l_f, None, "Férias")
            
        # Processar Outros/Cursos
        for l_i, l_f, l_m, tipo in AUSENCIAS_CONFIG:
            add_evt(l_i, l_f, l_m, tipo)

    return pd.DataFrame(eventos)

df_eventos = construir_eventos(df_raw)

# ============================================================
# 5. EXPANSÃO E FILTROS
# ============================================================

@st.cache_data(ttl=600)
def expandir_eventos_por_dia(df_evt: pd.DataFrame) -> pd.DataFrame:
    if df_evt.empty: return pd.DataFrame()
    linhas = []
    for _, ev in df_evt.iterrows():
        for data in pd.date_range(ev["Inicio"], ev["Fim"]):
            linhas.append({
                "Data": data,
                "Nome": ev["Nome"],
                "Posto": ev["Posto"],
                "Tipo": ev["Tipo"],
                "Motivo": ev["Motivo"]
            })
    return pd.DataFrame(linhas)

df_dias = expandir_eventos_por_dia(df_eventos)

def filtrar_eventos(df, eq, nav, gvi):
    res = df.copy()
    if eq: res = res[res["EqMan"] != "Não"]
    if nav: res = res[res["IN"] == True]
    if gvi: res = res[res["GVI"] == True]
    return res

def filtrar_tripulacao(df, eq, nav, gvi):
    res = df.copy()
    c_eq = get_col_name_compact(df, "E")
    c_in = get_col_name_compact(df, "G")
    c_gv = get_col_name_compact(df, "F")
    
    if eq and c_eq: res = res[(res[c_eq].notna()) & (res[c_eq].astype(str) != "-") & (res[c_eq].astype(str) != "Não")]
    if nav and c_in: res = res[res[c_in].apply(parse_bool)]
    if gvi and c_gv: res = res[res[c_gv].apply(parse_bool)]
    return res

# ============================================================
# 6. LEITURA V2 (% Férias)
# ============================================================
@st.cache_data(ttl=600)
def load_percent_ferias_v2():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_v = conn.read(worksheet="Afastamento 2026", header=None, ttl="10m")
        # Coluna V é índice 21 no Excel.
        # Mas aqui, como H foi pulada no header=None?
        # header=None geralmente lê tudo. Vamos tentar índice fixo 21.
        val = df_v.iloc[1, 21]
        if pd.isna(val): return None
        s = str(val).replace(",", ".").replace("%", "").strip()
        num = float(s)
        if num > 1: num /= 100.0
        return num
    except:
        return None

# ============================================================
# 7. INTERFACE
# ============================================================
st.sidebar.image("logo_npamacau.png", width=140)
st.sidebar.markdown("<div class='sidebar-title'>Parâmetros</div>", unsafe_allow_html=True)

data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

if hoje.year < 2026 and "Afastamento 2026" in str(df_raw.columns):
    st.sidebar.warning("Atenção: Data atual (2025) < Data Planilha (2026).")

st.sidebar.markdown("<div class='sidebar-section'>Navegação</div>", unsafe_allow_html=True)
pagina = st.sidebar.radio("", [
    "Presentes", "Ausentes", "Linha do Tempo (Gantt)", 
    "Estatísticas & Análises", "Férias", "Cursos", "Log / Debug"
])

# ============================================================
# 8. DASHBOARD
# ============================================================
if not df_eventos.empty:
    ausentes_globais = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
else:
    ausentes_globais = pd.DataFrame()

total_efetivo = len(df_raw)
total_aus = ausentes_globais["Nome"].nunique() if not ausentes_globais.empty else 0
total_pres = total_efetivo - total_aus
prontidao = (total_pres / total_efetivo * 100) if total_efetivo > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Efetivo Total", total_efetivo)
c2.metric("A Bordo", total_pres)
c3.metric("Ausentes", total_aus, delta_color="inverse")
c4.metric("Prontidão", f"{prontidao:.1f}%")

# ------------------------------------------------------------
# PÁGINA: PRESENTES
# ------------------------------------------------------------
if pagina == "Presentes":
    st.subheader(f"Presentes a bordo em {hoje.strftime('%d/%m/%Y')}")
    t_cont = st.container()
    st.markdown("#### Filtros")
    cf1, cf2, cf3 = st.columns(3)
    f_eq = cf1.checkbox("Apenas EqMan", key="p_eq")
    f_in = cf2.checkbox("Apenas IN", key="p_in")
    f_gv = cf3.checkbox("Apenas GVI", key="p_gv")

    df_filt = filtrar_tripulacao(df_raw, f_eq, f_in, f_gv)
    
    nomes_aus = set()
    if not df_eventos.empty:
        aus_h = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
        aus_h = filtrar_eventos(aus_h, f_eq, f_in, f_gv)
        nomes_aus = set(aus_h["Nome"].unique())

    c_nome = get_col_name_compact(df_raw, "C")
    if c_nome:
        df_pres = df_filt[~df_filt[c_nome].isin(nomes_aus)].copy()
    else:
        df_pres = df_filt.copy()

    with t_cont:
        if df_pres.empty:
            st.info("Ninguém presente para estes filtros.")
        else:
            # Selecionar colunas
            col_letras = ["B", "C", "D", "E", "F", "G"]
            cols_final = []
            for l in col_letras:
                n = get_col_name_compact(df_raw, l)
                if n: cols_final.append(n)
            
            df_show = df_pres[cols_final].copy()
            # Renomear com base no que achou
            renames = {}
            if get_col_name_compact(df_raw, "B"): renames[get_col_name_compact(df_raw, "B")] = "Posto"
            if get_col_name_compact(df_raw, "C"): renames[get_col_name_compact(df_raw, "C")] = "Nome"
            if get_col_name_compact(df_raw, "D"): renames[get_col_name_compact(df_raw, "D")] = "Escala"
            if get_col_name_compact(df_raw, "E"): renames[get_col_name_compact(df_raw, "E")] = "EqMan"
            if get_col_name_compact(df_raw, "F"): renames[get_col_name_compact(df_raw, "F")] = "GVI"
            if get_col_name_compact(df_raw, "G"): renames[get_col_name_compact(df_raw, "G")] = "IN"
            
            df_show = df_show.rename(columns=renames)
            if "GVI" in df_show.columns: df_show["GVI"] = df_show["GVI"].apply(lambda x: "SIM" if parse_bool(x) else "NÃO")
            if "IN" in df_show.columns: df_show["IN"] = df_show["IN"].apply(lambda x: "SIM" if parse_bool(x) else "NÃO")
            
            st.dataframe(df_show, use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# PÁGINA: AUSENTES
# ------------------------------------------------------------
elif pagina == "Ausentes":
    st.subheader(f"Ausentes em {hoje.strftime('%d/%m/%Y')}")
    t_cont = st.container()
    st.markdown("#### Filtros")
    cf1, cf2, cf3 = st.columns(3)
    f_eq = cf1.checkbox("Apenas EqMan", key="a_eq")
    f_in = cf2.checkbox("Apenas IN", key="a_in")
    f_gv = cf3.checkbox("Apenas GVI", key="a_gv")

    with t_cont:
        if df_eventos.empty:
            st.info("Sem eventos.")
        else:
            aus_h = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
            aus_h = filtrar_eventos(aus_h, f_eq, f_in, f_gv)
            
            if aus_h.empty:
                st.success("Todos a bordo.")
            else:
                show = aus_h[["Posto", "Nome", "Motivo", "Tipo", "Fim"]].copy()
                show["Retorno"] = show["Fim"].dt.strftime("%d/%m/%Y")
                show = show.drop(columns=["Fim"])
                st.dataframe(show, use_container_width=True, hide_index=True)
                
                # Alertas
                if "EqMan" in aus_h.columns:
                    eqs = aus_h[aus_h["EqMan"]!="Não"]
                    if not eqs.empty:
                        nomes = sorted({f"{r['Posto']} {r['Nome']} ({r['EqMan']})" for _,r in eqs.iterrows()})
                        st.error(f"⚠️ EqMan Desfalcada: {'; '.join(nomes)}")

# ------------------------------------------------------------
# PÁGINA: GANTT
# ------------------------------------------------------------
elif pagina == "Linha do Tempo (Gantt)":
    st.subheader("Cronograma")
    if not df_eventos.empty:
        fig = px.timeline(df_eventos, x_start="Inicio", x_end="Fim", y="Nome", color="Tipo", hover_data=["Motivo"], title="Ausências")
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=hoje, line_dash="dash", line_color="red")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados.")

# ------------------------------------------------------------
# PÁGINA: ESTATISTICAS
# ------------------------------------------------------------
elif pagina == "Estatísticas & Análises":
    st.subheader("Análises")
    if not df_eventos.empty:
        df_c = df_eventos.copy()
        df_c["Motivo"] = df_c["Motivo"].apply(lambda x: "CURSO" if str(x).upper().startswith("CURSO") else x)
        df_p = df_c.groupby("Motivo")["Duracao_dias"].sum().reset_index()
        fig = px.pie(df_p, names="Motivo", values="Duracao_dias", hole=0.4, title="Dias de Ausência por Motivo")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados.")

# ------------------------------------------------------------
# PÁGINA: FÉRIAS
# ------------------------------------------------------------
elif pagina == "Férias":
    st.subheader("Férias")
    df_f = df_eventos[df_eventos["Tipo"]=="Férias"].copy()
    if not df_f.empty:
        df_f["Início"] = df_f["Inicio"].dt.strftime("%d/%m/%Y")
        df_f["Fim"] = df_f["Fim"].dt.strftime("%d/%m/%Y")
        st.dataframe(df_f[["Posto", "Nome", "Início", "Fim", "Duracao_dias"]], use_container_width=True)
    else:
        st.info("Nenhuma férias.")
    
    st.markdown("---")
    pct = load_percent_ferias_v2()
    if pct is not None:
        fig = px.pie(names=["Gozadas", "Restantes"], values=[pct, 1-pct], hole=0.5, title="Meta de Férias (V2)")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# PÁGINA: CURSOS
# ------------------------------------------------------------
elif pagina == "Cursos":
    st.subheader("Cursos")
    df_c = df_eventos[df_eventos["Tipo"]=="Curso"].copy()
    if not df_c.empty:
        real = df_c[df_c["Fim"]<hoje]
        fut = df_c[df_c["Fim"]>=hoje]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Realizados")
            if not real.empty: st.dataframe(real[["Posto", "Nome", "Motivo", "Fim"]], use_container_width=True)
            else: st.info("Nenhum.")
        with c2:
            st.markdown("### Futuros")
            if not fut.empty: st.dataframe(fut[["Posto", "Nome", "Motivo", "Inicio", "Fim"]], use_container_width=True)
            else: st.info("Nenhum.")
    else:
        st.info("Nenhum curso.")

# ------------------------------------------------------------
# PÁGINA: LOG / DEBUG
# ------------------------------------------------------------
elif pagina == "Log / Debug":
    st.subheader("Diagnóstico de Colunas")
    st.write(f"Total de Colunas Lidas: **{len(df_raw.columns)}**")
    
    st.write("### Teste de Mapeamento Compacto")
    debug_list = []
    # Testar colunas críticas
    test_keys = ["I", "Y", "DH", "ID", "GW", "IG"]
    for k in test_keys:
        real_name = get_col_name_compact(df_raw, k)
        sample = df_raw[real_name].iloc[0] if real_name and not df_raw.empty else "N/A"
        debug_list.append({"Letra Excel": k, "Nome Coluna Pandas": real_name, "Amostra Dado": str(sample)})
    
    st.table(pd.DataFrame(debug_list))
    st.write("### Colunas Brutas do DataFrame")
    st.write(list(df_raw.columns))

st.markdown("<hr/><div style='text-align:center; color:gray'>Versão 1.11 - Mapeamento Compacto</div>", unsafe_allow_html=True)
