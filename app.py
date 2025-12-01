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

APP_VERSION = "v1.10.0 - Mapeamento Estrito"

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
# 2. HELPERS E CONSTANTES
# ============================================================

HEADER_ROW = 2  # Linha 3 da planilha (índice 2)

def parse_bool(value) -> bool:
    """Converte checkbox/texto da planilha em booleano robusto."""
    if pd.isna(value):
        return False
    s = str(value).strip().lower()
    return s in ("true", "1", "sim", "yes", "y", "x")

def col_letter_to_index(col_letter: str) -> int:
    """
    Converte letra de coluna (A, B, ..., Z, AA...) para índice 0-based.
    Ex: A -> 0, I -> 8, AA -> 26
    """
    col_letter = col_letter.upper()
    result = 0
    for ch in col_letter:
        if not ch.isalpha():
            break
        result = result * 26 + (ord(ch) - ord('A') + 1)
    return result - 1  # 0-based

def get_col_name_strict(df: pd.DataFrame, letter: str):
    """
    Pega o nome da coluna baseando-se EXATAMENTE na posição da letra.
    Assume que o Pandas carregou as colunas vazias como 'Unnamed'.
    """
    idx = col_letter_to_index(letter)
    if idx < len(df.columns):
        return df.columns[idx]
    return None

# ============================================================
# 3. CARGA DE DADOS
# ============================================================

@st.cache_data(ttl=600, show_spinner="Carregando dados da planilha...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)

    # Carrega a planilha. O Pandas geralmente mantém colunas vazias como "Unnamed: X"
    df = conn.read(
        worksheet="Afastamento 2026",
        header=HEADER_ROW,
        ttl="10m"
    )

    # Identificar a coluna "Nome" (Coluna C -> índice 2)
    # Se o cabeçalho estiver vazio na coluna C, pegamos pelo índice
    c_nome_idx = col_letter_to_index("C")
    
    if "Nome" in df.columns:
        df = df.dropna(subset=["Nome"])
    elif len(df.columns) > c_nome_idx:
        # Pega o nome da coluna no índice 2, seja ele qual for
        nome_col = df.columns[c_nome_idx]
        df = df.dropna(subset=[nome_col])

    df = df.reset_index(drop=True)
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro de conexão. Verifique o arquivo secrets.toml. Detalhe: {e}")
    st.stop()

# ============================================================
# 3.1 MAPEAMENTO: COLUNAS FIXAS (A-G)
# ============================================================

# Mapeamos diretamente pelo índice da letra para garantir
C_POSTO  = get_col_name_strict(df_raw, "B")
C_NOME   = get_col_name_strict(df_raw, "C")
C_SV     = get_col_name_strict(df_raw, "D")
C_EQMAN  = get_col_name_strict(df_raw, "E")
C_GVI    = get_col_name_strict(df_raw, "F")
C_IN     = get_col_name_strict(df_raw, "G")

# ============================================================
# 3.2 MAPEAMENTO: FÉRIAS (I-J, L-M, O-P)
# ============================================================

FERIAS_COLS = []
# Pares (Início, Fim)
for ini_l, fim_l in [("I", "J"), ("L", "M"), ("O", "P")]:
    c_ini = get_col_name_strict(df_raw, ini_l)
    c_fim = get_col_name_strict(df_raw, fim_l)
    if c_ini and c_fim:
        FERIAS_COLS.append((c_ini, c_fim))

# ============================================================
# 3.3 MAPEAMENTO: OUTROS E CURSOS (Periodos 4 a 10)
# ============================================================

AUSENCIAS_CONFIG = [
    # (Inicio, Fim, Motivo, CategoriaBase)
    ("Y",  "Z",  "AB", "Outros"), # P4
    ("AD", "AE", "AG", "Outros"), # P5
    ("AI", "AJ", "AL", "Outros"), # P6
    ("AN", "AO", "AQ", "Curso"),  # P7
    ("AS", "AT", "AV", "Curso"),  # P8
    ("DH", "EL", "GW", "Curso"),  # P9
    ("ID", "IE", "IG", "Curso"),  # P10
]

AUSENCIAS_TRIPLETS = []
for ini_l, fim_l, mot_l, cat_base in AUSENCIAS_CONFIG:
    c_ini = get_col_name_strict(df_raw, ini_l)
    c_fim = get_col_name_strict(df_raw, fim_l)
    c_mot = get_col_name_strict(df_raw, mot_l)
    
    if c_ini and c_fim and c_mot:
        AUSENCIAS_TRIPLETS.append((c_ini, c_fim, c_mot, cat_base))

# ============================================================
# 4. TRANSFORMAÇÃO EM EVENTOS
# ============================================================

@st.cache_data(ttl=600)
def construir_eventos(df: pd.DataFrame) -> pd.DataFrame:
    eventos = []

    for _, row in df.iterrows():
        # Extração segura dos dados básicos
        posto  = row[C_POSTO] if C_POSTO else ""
        nome   = row[C_NOME]  if C_NOME  else ""
        escala = row[C_SV]    if C_SV    else ""
        eq_val = row[C_EQMAN] if C_EQMAN else ""
        gvi_val= row[C_GVI]   if C_GVI   else ""
        in_val = row[C_IN]    if C_IN    else ""

        militar_info = {
            "Posto": str(posto),
            "Nome": str(nome),
            "Escala": str(escala),
            "EqMan": str(eq_val) if pd.notna(eq_val) and str(eq_val).strip() not in ("-", "") else "Não",
            "GVI": parse_bool(gvi_val),
            "IN": parse_bool(in_val),
        }

        # Função interna para adicionar evento
        def add_evt(val_ini, val_fim, val_motivo, tipo_evento):
            ini = pd.to_datetime(val_ini, dayfirst=True, errors="coerce")
            fim = pd.to_datetime(val_fim, dayfirst=True, errors="coerce")
            
            # Validação de data válida
            if pd.notna(ini) and pd.notna(fim):
                # Corrige data invertida
                if fim < ini:
                    ini, fim = fim, ini
                
                dur = (fim - ini).days + 1
                
                # Filtro de sanidade (datas muito antigas ou duração absurda)
                if ini.year < 2020 or dur > 365:
                    return

                # Tratamento do Motivo
                motivo_txt = str(val_motivo).strip()
                if not motivo_txt or motivo_txt.lower() == "nan":
                    motivo_real = "CURSO" if tipo_evento == "Curso" else "AUSÊNCIA"
                else:
                    motivo_real = motivo_txt

                eventos.append({
                    **militar_info,
                    "Inicio": ini,
                    "Fim": fim,
                    "Duracao_dias": dur,
                    "Motivo": motivo_real,
                    "Tipo": tipo_evento
                })

        # Processar Férias
        for c_ini, c_fim in FERIAS_COLS:
            add_evt(row.get(c_ini), row.get(c_fim), "FÉRIAS", "Férias")

        # Processar Outros/Cursos
        for c_ini, c_fim, c_mot, cat in AUSENCIAS_TRIPLETS:
            add_evt(row.get(c_ini), row.get(c_fim), row.get(c_mot), cat)

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

def filtrar_tripulacao(df, eq, nav, gvi):
    res = df.copy()
    if eq and C_EQMAN:
        res = res[(res[C_EQMAN].notna()) & (res[C_EQMAN].astype(str) != "-") & (res[C_EQMAN].astype(str) != "Não")]
    if nav and C_IN:
        res = res[res[C_IN].apply(parse_bool)]
    if gvi and C_GVI:
        res = res[res[C_GVI].apply(parse_bool)]
    return res

def filtrar_eventos(df, eq, nav, gvi):
    res = df.copy()
    if eq: res = res[res["EqMan"] != "Não"]
    if nav: res = res[res["IN"] == True]
    if gvi: res = res[res["GVI"] == True]
    return res

# ============================================================
# 6. LÓGICA DE V2 (% DE FÉRIAS)
# ============================================================
@st.cache_data(ttl=600)
def load_percent_ferias_v2():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_v = conn.read(worksheet="Afastamento 2026", header=None, ttl="10m")
        # Coluna V é índice 21 estrito
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

# SELETOR DE DATA - PADRÃO NO DIA DE HOJE
# ---------------------------------------------------------------------
# IMPORTANTE: Se você estiver testando a planilha de 2026 hoje (em 2025),
# você PRECISA mudar esta data no App para 2026 para ver os dados.
# ---------------------------------------------------------------------
data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

# Aviso Visual caso a data seja 2025 e a planilha 2026
if hoje.year < 2026 and "Afastamento 2026" in str(df_raw.columns):
    st.sidebar.warning("Atenção: Data de referência é 2025, mas a planilha é 2026. Mude a data para ver os futuros ausentes.")

st.sidebar.markdown("<div class='sidebar-section'>Navegação</div>", unsafe_allow_html=True)
pagina = st.sidebar.radio("", [
    "Presentes", "Ausentes", "Linha do Tempo (Gantt)", 
    "Estatísticas & Análises", "Férias", "Cursos", "Log / Debug"
])

# ============================================================
# 8. DASHBOARD
# ============================================================

# Cálculo Global
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
    
    tabela_container = st.container()
    st.markdown("#### Filtros")
    cf1, cf2, cf3 = st.columns(3)
    f_eq = cf1.checkbox("Apenas EqMan", key="p_eq")
    f_in = cf2.checkbox("Apenas IN", key="p_in")
    f_gv = cf3.checkbox("Apenas GVI", key="p_gv")

    df_filt = filtrar_tripulacao(df_raw, f_eq, f_in, f_gv)
    
    # Quem está ausente hoje (filtrado)
    ausentes_nomes = set()
    if not df_eventos.empty:
        aus_hoje = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
        aus_hoje = filtrar_eventos(aus_hoje, f_eq, f_in, f_gv)
        ausentes_nomes = set(aus_hoje["Nome"].unique())

    # Presentes = Tripulação Filtrada - Ausentes
    if C_NOME:
        df_presentes = df_filt[~df_filt[C_NOME].isin(ausentes_nomes)].copy()
    else:
        df_presentes = df_filt.copy()

    with tabela_container:
        if df_presentes.empty:
            st.info("Ninguém presente com estes filtros.")
        else:
            cols_show = [c for c in [C_POSTO, C_NOME, C_SV, C_EQMAN, C_GVI, C_IN] if c]
            df_show = df_presentes[cols_show].copy()
            # Renomear para ficar bonito
            rename_map = {
                C_POSTO: "Posto", C_NOME: "Nome", C_SV: "Escala",
                C_EQMAN: "EqMan", C_GVI: "GVI", C_IN: "IN"
            }
            df_show = df_show.rename(columns=rename_map)
            
            # Formatando Bool
            if "GVI" in df_show.columns: df_show["GVI"] = df_show["GVI"].apply(lambda x: "SIM" if parse_bool(x) else "NÃO")
            if "IN" in df_show.columns:  df_show["IN"]  = df_show["IN"].apply(lambda x: "SIM" if parse_bool(x) else "NÃO")
            
            st.dataframe(df_show, use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# PÁGINA: AUSENTES
# ------------------------------------------------------------
elif pagina == "Ausentes":
    st.subheader(f"Ausentes em {hoje.strftime('%d/%m/%Y')}")
    
    tabela_container = st.container()
    st.markdown("#### Filtros")
    cf1, cf2, cf3 = st.columns(3)
    f_eq = cf1.checkbox("Apenas EqMan", key="a_eq")
    f_in = cf2.checkbox("Apenas IN", key="a_in")
    f_gv = cf3.checkbox("Apenas GVI", key="a_gv")

    with tabela_container:
        if df_eventos.empty:
            st.info("Nenhum evento registrado na planilha.")
        else:
            aus_hoje = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
            aus_hoje = filtrar_eventos(aus_hoje, f_eq, f_in, f_gv)

            if aus_hoje.empty:
                st.success("Todos a bordo.")
            else:
                show_aus = aus_hoje[["Posto", "Nome", "Motivo", "Tipo", "Fim"]].copy()
                show_aus["Retorno"] = show_aus["Fim"].dt.strftime("%d/%m/%Y")
                show_aus = show_aus.drop(columns=["Fim"])
                st.dataframe(show_aus, use_container_width=True, hide_index=True)

                # Alertas
                if "EqMan" in aus_hoje.columns:
                    eq_fora = aus_hoje[aus_hoje["EqMan"] != "Não"]
                    if not eq_fora.empty:
                        nomes = sorted({f"{r['Posto']} {r['Nome']} ({r['EqMan']})" for _,r in eq_fora.iterrows()})
                        st.error(f"⚠️ EqMan Desfalcada: {'; '.join(nomes)}")

# ------------------------------------------------------------
# PÁGINA: GANTT
# ------------------------------------------------------------
elif pagina == "Linha do Tempo (Gantt)":
    st.subheader("Cronograma Anual")
    if df_eventos.empty:
        st.info("Sem dados.")
    else:
        fig = px.timeline(
            df_eventos, x_start="Inicio", x_end="Fim", y="Nome", color="Tipo",
            hover_data=["Motivo", "Posto"], title="Ausências"
        )
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=hoje, line_dash="dash", line_color="red")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)")
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# PÁGINA: ESTATÍSTICAS
# ------------------------------------------------------------
elif pagina == "Estatísticas & Análises":
    st.subheader("Estatísticas")
    if df_eventos.empty:
        st.info("Sem dados.")
    else:
        # Pizza Motivos
        df_evt_clean = df_eventos.copy()
        df_evt_clean["Motivo"] = df_evt_clean["Motivo"].apply(lambda x: "CURSO" if str(x).upper().startswith("CURSO") else x)
        
        df_pie = df_evt_clean.groupby("Motivo")["Duracao_dias"].sum().reset_index()
        fig_pie = px.pie(df_pie, names="Motivo", values="Duracao_dias", hole=0.4, title="Dias de Ausência por Motivo")
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie, use_container_width=True)

        # Gráfico Mensal
        if not df_dias.empty:
            df_dias["Mes"] = df_dias["Data"].dt.to_period("M").dt.to_timestamp()
            df_line = df_dias.groupby("Mes")["Nome"].nunique().reset_index(name="Ausentes")
            fig_line = px.line(df_line, x="Mes", y="Ausentes", markers=True, title="Média de Ausentes por Mês")
            fig_line.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)")
            st.plotly_chart(fig_line, use_container_width=True)

# ------------------------------------------------------------
# PÁGINA: FÉRIAS
# ------------------------------------------------------------
elif pagina == "Férias":
    st.subheader("Controle de Férias")
    df_f = df_eventos[df_eventos["Tipo"] == "Férias"].copy()
    if df_f.empty:
        st.info("Nenhuma férias lançada.")
    else:
        df_f["Início"] = df_f["Inicio"].dt.strftime("%d/%m/%Y")
        df_f["Fim"] = df_f["Fim"].dt.strftime("%d/%m/%Y")
        st.dataframe(df_f[["Posto", "Nome", "Início", "Fim", "Duracao_dias"]], use_container_width=True)
    
    st.markdown("---")
    pct = load_percent_ferias_v2()
    if pct is not None:
        fig_g = px.pie(names=["Gozadas", "Restantes"], values=[pct, 1-pct], hole=0.5, title="Meta de Férias (V2)")
        fig_g.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_g, use_container_width=True)

# ------------------------------------------------------------
# PÁGINA: CURSOS
# ------------------------------------------------------------
elif pagina == "Cursos":
    st.subheader("Controle de Cursos")
    df_c = df_eventos[df_eventos["Tipo"] == "Curso"].copy()
    if df_c.empty:
        st.info("Nenhum curso lançado.")
    else:
        passados = df_c[df_c["Fim"] < hoje]
        futuros = df_c[df_c["Fim"] >= hoje]
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Realizados")
            if not passados.empty:
                st.dataframe(passados[["Posto", "Nome", "Motivo", "Fim"]], use_container_width=True)
            else: st.info("Nenhum.")
            
        with c2:
            st.markdown("### Futuros / Atuais")
            if not futuros.empty:
                st.dataframe(futuros[["Posto", "Nome", "Motivo", "Inicio", "Fim"]], use_container_width=True)
            else: st.info("Nenhum.")

# ------------------------------------------------------------
# PÁGINA: DEBUG
# ------------------------------------------------------------
elif pagina == "Log / Debug":
    st.subheader("Diagnóstico Técnico")
    
    st.write("### Colunas Detectadas (Indices Reais)")
    cols_info = {f"Indice {i}": col for i, col in enumerate(df_raw.columns)}
    st.json(cols_info, expanded=False)

    st.write("### Verificação de Colunas Críticas")
    # Testar I (Férias) e Y (Periodo 4)
    teste_cols = [
        ("I (Férias 1)", get_col_name_strict(df_raw, "I")),
        ("Y (Periodo 4)", get_col_name_strict(df_raw, "Y")),
        ("DH (Periodo 9)", get_col_name_strict(df_raw, "DH"))
    ]
    st.table(pd.DataFrame(teste_cols, columns=["Letra", "Nome Lido no Pandas"]))
    
    st.write("### Amostra de Dados (Primeiras 5 linhas)")
    st.dataframe(df_raw.head())

st.markdown("<hr/><div style='text-align:center; color:gray'>Versão Corrigida: Mapeamento Estrito</div>", unsafe_allow_html=True)
