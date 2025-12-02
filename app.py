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

APP_VERSION = "v1.12.0 - Leitura por Grid Rígido"

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
# 2. HELPERS DE LEITURA (GRID SYSTEM)
# ============================================================

HEADER_ROW = 2  # Linha 3 do Excel (Indice 2)

def col_letter_to_index(col_letter: str) -> int:
    """
    Converte letra de coluna para índice zero-based.
    A -> 0, B -> 1, ... Y -> 24, AA -> 26
    """
    col_letter = col_letter.upper()
    result = 0
    for ch in col_letter:
        if not ch.isalpha():
            break
        result = result * 26 + (ord(ch) - ord('A') + 1)
    return result - 1

def get_cell_value(row_series: pd.Series, col_letter: str):
    """
    Pega o valor da célula usando a posição exata da letra (iloc).
    Ignora nomes de colunas, usa apenas a posição geométrica.
    """
    idx = col_letter_to_index(col_letter)
    if idx < len(row_series):
        return row_series.iloc[idx]
    return None

def parse_bool(value) -> bool:
    if pd.isna(value):
        return False
    s = str(value).strip().lower()
    return s in ("true", "1", "sim", "yes", "y", "x")

# ============================================================
# 3. CARGA DE DADOS
# ============================================================

@st.cache_data(ttl=600, show_spinner="Carregando dados (Modo Grid)...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Lemos a planilha inteira. O Pandas vai preencher colunas vazias com "Unnamed".
    # Isso é bom! Mantém a integridade da posição das colunas.
    df = conn.read(
        worksheet="Afastamento 2026",
        header=HEADER_ROW,
        ttl="10m"
    )
    
    # Removemos linhas vazias baseadas na Coluna C (Nome) - Indice 2
    # Usamos iloc para garantir que estamos olhando a coluna C
    idx_nome = col_letter_to_index("C")
    if idx_nome < len(df.columns):
        # Filtra onde a coluna C não é nula
        df = df[df.iloc[:, idx_nome].notna()]
    
    df = df.reset_index(drop=True)
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro de conexão. Verifique o secrets.toml. Detalhe: {e}")
    st.stop()

# ============================================================
# 3.1 MAPEAMENTO DE DADOS FIXOS
# ============================================================
# Vamos apenas definir as constantes de letra para usar depois
COL_POSTO = "B"
COL_NOME  = "C"
COL_SV    = "D"
COL_EQ    = "E"
COL_GVI   = "F"
COL_IN    = "G"

# ============================================================
# 3.2 MAPEAMENTO DE FÉRIAS (I-J, L-M, O-P)
# ============================================================
FERIAS_MAP = [
    ("I", "J"),
    ("L", "M"),
    ("O", "P")
]

# ============================================================
# 3.3 MAPEAMENTO DE AUSÊNCIAS (OUTROS + CURSOS)
# ============================================================
# (Inicio, Fim, Motivo, CategoriaBase)
# Seguindo estritamente sua lista:
AUSENCIAS_MAP = [
    ("Y",  "Z",  "AB", "Outros"), # Período 4
    ("AD", "AE", "AG", "Outros"), # Período 5 (AC vazia pulada no map, mas conta no indice)
    ("AI", "AJ", "AL", "Outros"), # Período 6
    ("AN", "AO", "AQ", "Curso"),  # Período 7
    ("AS", "AT", "AV", "Curso"),  # Período 8
    ("DH", "EL", "GW", "Curso"),  # Período 9 (Salto gigante de AW até DH respeitado)
    ("ID", "IE", "IG", "Curso"),  # Período 10
]

# ============================================================
# 4. PROCESSAMENTO DOS EVENTOS
# ============================================================

@st.cache_data(ttl=600)
def construir_eventos(df: pd.DataFrame) -> pd.DataFrame:
    eventos = []

    for _, row in df.iterrows():
        # Extração Posicional (Blindada contra nomes de coluna)
        posto  = get_cell_value(row, COL_POSTO)
        nome   = get_cell_value(row, COL_NOME)
        escala = get_cell_value(row, COL_SV)
        eq     = get_cell_value(row, COL_EQ)
        gvi    = get_cell_value(row, COL_GVI)
        nav    = get_cell_value(row, COL_IN)

        militar_info = {
            "Posto": str(posto) if pd.notna(posto) else "",
            "Nome": str(nome) if pd.notna(nome) else "",
            "Escala": str(escala) if pd.notna(escala) else "",
            "EqMan": str(eq) if pd.notna(eq) and str(eq).strip() not in ("-", "") else "Não",
            "GVI": parse_bool(gvi),
            "IN": parse_bool(nav),
        }

        # Helper para processar datas
        def processar_periodo(l_ini, l_fim, l_motivo, tipo_padrao):
            val_ini = get_cell_value(row, l_ini)
            val_fim = get_cell_value(row, l_fim)
            val_mot = get_cell_value(row, l_motivo) if l_motivo else None

            # Conversão
            ini = pd.to_datetime(val_ini, dayfirst=True, errors="coerce")
            fim = pd.to_datetime(val_fim, dayfirst=True, errors="coerce")

            if pd.notna(ini) and pd.notna(fim):
                # Corrige inversão
                if fim < ini: ini, fim = fim, ini
                
                dur = (fim - ini).days + 1
                
                # Validação simples (evitar datas 1900 ou vazias reais)
                if dur < 1 or dur > 365: return

                # Motivo
                motivo_texto = str(val_mot).strip() if val_mot and pd.notna(val_mot) else ""
                
                if motivo_texto and motivo_texto.lower() != "nan":
                    motivo_final = motivo_texto
                else:
                    # Se não tiver motivo escrito, usa o padrão do bloco
                    motivo_final = "CURSO" if tipo_padrao == "Curso" else (tipo_padrao if tipo_padrao != "Outros" else "AUSÊNCIA")

                eventos.append({
                    **militar_info,
                    "Inicio": ini,
                    "Fim": fim,
                    "Duracao_dias": dur,
                    "Motivo": motivo_final,
                    "Tipo": "Férias" if tipo_padrao == "Férias" else tipo_padrao
                })

        # 1. FÉRIAS
        for l_i, l_f in FERIAS_MAP:
            processar_periodo(l_i, l_f, None, "Férias")

        # 2. OUTROS / CURSOS
        for l_i, l_f, l_m, t_base in AUSENCIAS_MAP:
            processar_periodo(l_i, l_f, l_m, t_base)

    return pd.DataFrame(eventos)

df_eventos = construir_eventos(df_raw)

# ============================================================
# 5. EXPANSÃO POR DIA
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

# Filtros Lógicos
def filtrar_tripulacao_df(df, eq, nav, gvi):
    res = df.copy()
    # Indices fixos
    idx_eq = col_letter_to_index(COL_EQ)
    idx_in = col_letter_to_index(COL_IN)
    idx_gv = col_letter_to_index(COL_GVI)
    
    if eq:
        # EqMan não pode ser null, nem "-", nem "Não"
        res = res[res.iloc[:, idx_eq].notna() & (~res.iloc[:, idx_eq].astype(str).isin(["-", "Não"]))]
    if nav:
        res = res[res.iloc[:, idx_in].apply(parse_bool)]
    if gvi:
        res = res[res.iloc[:, idx_gv].apply(parse_bool)]
    return res

def filtrar_eventos_df(df, eq, nav, gvi):
    res = df.copy()
    if eq: res = res[res["EqMan"] != "Não"]
    if nav: res = res[res["IN"] == True]
    if gvi: res = res[res["GVI"] == True]
    return res

# ============================================================
# 6. LEITURA V2 (% FÉRIAS)
# ============================================================
@st.cache_data(ttl=600)
def load_percent_ferias_v2():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Lê sem header para pegar a célula exata por coordenada numérica
        df_v = conn.read(worksheet="Afastamento 2026", header=None, ttl="10m")
        # V2 = Linha index 1, Coluna index 21 (V)
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

# SELETOR DE DATA
data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

st.sidebar.markdown("<div class='sidebar-section'>Navegação</div>", unsafe_allow_html=True)
pagina = st.sidebar.radio("", [
    "Presentes", "Ausentes", "Linha do Tempo (Gantt)", 
    "Estatísticas & Análises", "Férias", "Cursos", "Log / Debug"
])

# ============================================================
# 8. DASHBOARD
# ============================================================

# Calculos Globais
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
    st.subheader(f"Presentes em {hoje.strftime('%d/%m/%Y')}")
    t_cont = st.container()
    st.markdown("#### Filtros")
    cf1, cf2, cf3 = st.columns(3)
    f_eq = cf1.checkbox("Apenas EqMan", key="p_eq")
    f_in = cf2.checkbox("Apenas IN", key="p_in")
    f_gv = cf3.checkbox("Apenas GVI", key="p_gv")

    # 1. Filtra a tripulação total
    df_filt = filtrar_tripulacao_df(df_raw, f_eq, f_in, f_gv)
    
    # 2. Descobre quem está ausente HOJE (com os mesmos filtros)
    nomes_aus = set()
    if not df_eventos.empty:
        aus_h = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
        aus_h = filtrar_eventos_df(aus_h, f_eq, f_in, f_gv)
        nomes_aus = set(aus_h["Nome"].unique())

    # 3. Presentes = Total Filtrado - Ausentes
    # Usamos grid fixo para pegar o nome
    idx_nome = col_letter_to_index(COL_NOME)
    if not df_filt.empty:
        # Pega a coluna de nomes pelo índice
        col_nomes_series = df_filt.iloc[:, idx_nome]
        df_pres = df_filt[~col_nomes_series.isin(nomes_aus)].copy()
    else:
        df_pres = pd.DataFrame()

    with t_cont:
        if df_pres.empty:
            st.info("Ninguém presente com estes filtros.")
        else:
            # Monta tabela de exibição pegando colunas por letra
            display_data = []
            for _, r in df_pres.iterrows():
                display_data.append({
                    "Posto": get_cell_value(r, COL_POSTO),
                    "Nome": get_cell_value(r, COL_NOME),
                    "Escala": get_cell_value(r, COL_SV),
                    "EqMan": get_cell_value(r, COL_EQ),
                    "GVI": "SIM" if parse_bool(get_cell_value(r, COL_GVI)) else "NÃO",
                    "IN": "SIM" if parse_bool(get_cell_value(r, COL_IN)) else "NÃO",
                })
            st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)

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
            st.info("Sem registro de ausências.")
        else:
            aus_h = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
            aus_h = filtrar_eventos_df(aus_h, f_eq, f_in, f_gv)
            
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
    st.subheader("Cronograma Anual")
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

        if not df_dias.empty:
            df_dias["Mes"] = df_dias["Data"].dt.to_period("M").dt.to_timestamp()
            df_l = df_dias.groupby("Mes")["Nome"].nunique().reset_index(name="Ausentes")
            fig_l = px.line(df_l, x="Mes", y="Ausentes", markers=True, title="Evolução Mensal")
            fig_l.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.8)")
            st.plotly_chart(fig_l, use_container_width=True)
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
            st.markdown("### Futuros / Atuais")
            if not fut.empty: st.dataframe(fut[["Posto", "Nome", "Motivo", "Inicio", "Fim"]], use_container_width=True)
            else: st.info("Nenhum.")
    else:
        st.info("Nenhum curso.")

# ------------------------------------------------------------
# PÁGINA: LOG / DEBUG
# ------------------------------------------------------------
elif pagina == "Log / Debug":
    st.subheader("Diagnóstico de Colunas (Grid)")
    
    st.write(f"Colunas Totais Lidas: **{len(df_raw.columns)}**")
    
    st.write("### Teste de Posições (Grid Rígido)")
    debug_vals = []
    # Testar Y (Indice 24)
    idx_y = col_letter_to_index("Y")
    val_y = df_raw.iloc[0, idx_y] if idx_y < len(df_raw.columns) and len(df_raw)>0 else "Fora do Range"
    debug_vals.append({"Letra": "Y (Início P4)", "Indice": idx_y, "Valor Linha 0": str(val_y)})

    # Testar AB (Indice 27)
    idx_ab = col_letter_to_index("AB")
    val_ab = df_raw.iloc[0, idx_ab] if idx_ab < len(df_raw.columns) and len(df_raw)>0 else "Fora do Range"
    debug_vals.append({"Letra": "AB (Motivo P4)", "Indice": idx_ab, "Valor Linha 0": str(val_ab)})
    
    st.table(pd.DataFrame(debug_vals))

    st.write("### Primeiras 5 linhas do DF")
    st.dataframe(df_raw.head())

st.markdown("<hr/><div style='text-align:center; color:gray'>Versão 1.12 - Grid Fixo (Respeita Vazios)</div>", unsafe_allow_html=True)
