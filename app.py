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

# 🔺 Sempre que você pedir alteração no app, eu subo a versão
APP_VERSION = "v1.8.0"

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

    /* Centralizar e aumentar imagem da sidebar */
    section[data-testid="stSidebar"] img {
        display: block;
        margin: 0.5rem auto 0.5rem auto;
    }

    /* Sidebar: deixar menu mais organizado */
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

# Cabeçalho: apenas título (sem brasão ao lado)
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

HEADER_ROW = 2  # linha 3 na planilha

def parse_bool(value) -> bool:
    """Converte checkbox/texto da planilha em booleano robusto."""
    if pd.isna(value):
        return False
    s = str(value).strip().lower()
    return s in ("true", "1", "sim", "yes", "y", "x")

def col_letter_to_index(col_letter: str) -> int:
    """
    Converte letra de coluna (A, B, ..., Z, AA, AB, ...) para índice 0-based.
    Leva em conta TODAS as colunas, inclusive colunas em branco.
    """
    col_letter = col_letter.upper()
    result = 0
    for ch in col_letter:
        if not ch.isalpha():
            break
        result = result * 26 + (ord(ch) - ord('A') + 1)
    return result - 1  # 0-based

def get_col_name(df: pd.DataFrame, letter: str):
    """
    Retorna o nome da coluna do DataFrame correspondente à letra da planilha.
    Ex.: letter = "AQ" → pega o df.columns[índice de AQ].
    Funciona mesmo se o cabeçalho estiver vazio (Unnamed: ...).
    """
    idx = col_letter_to_index(letter)
    cols = list(df.columns)
    if 0 <= idx < len(cols):
        return cols[idx]
    return None

# ============================================================
# 3. CARGA DE DADOS
# ============================================================

@st.cache_data(ttl=600, show_spinner="Carregando dados da planilha...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)

    df = conn.read(
        worksheet="Afastamento 2026",
        header=HEADER_ROW,
        ttl="10m"
    )

    # Remove linhas sem nome (coluna "Nome")
    if "Nome" in df.columns:
        df = df.dropna(subset=["Nome"])

    df = df.reset_index(drop=True)
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro de conexão. Verifique o arquivo secrets.toml. Detalhe: {e}")
    st.stop()

# ============================================================
# 3.1 MAPEAMENTO EXPLÍCITO – FÉRIAS (I–J, L–M, O–P)
# ============================================================

FERIAS_COLS = []
for ini_letter, fim_letter in [("I", "J"), ("L", "M"), ("O", "P")]:
    c_ini = get_col_name(df_raw, ini_letter)
    c_fim = get_col_name(df_raw, fim_letter)
    if c_ini and c_fim:
        FERIAS_COLS.append((c_ini, c_fim))

# ============================================================
# 3.2 MAPEAMENTO EXPLÍCITO – OUTRAS AUSÊNCIAS E CURSOS
# ============================================================

AUSENCIAS_TRIPLETS = []
# 4,5,6 – outras ausências (Disp Médica, Destaque, etc.)
# 7,8,9,10 – cursos
for ini_letter, fim_letter, tipo_letter, tipo_base in [
    ("Y",  "Z",  "AB", "Outros"),  # período 4
    ("AD", "AE", "AG", "Outros"),  # período 5
    ("AI", "AJ", "AL", "Outros"),  # período 6
    ("AN", "AO", "AQ", "Curso"),   # período 7
    ("AS", "AT", "AV", "Curso"),   # período 8
    ("DH", "EL", "GW", "Curso"),   # período 9
    ("ID", "IE", "IG", "Curso"),   # período 10
]:
    c_ini  = get_col_name(df_raw, ini_letter)
    c_fim  = get_col_name(df_raw, fim_letter)
    c_tipo = get_col_name(df_raw, tipo_letter)
    if c_ini and c_fim and c_tipo:
        AUSENCIAS_TRIPLETS.append((c_ini, c_fim, c_tipo, tipo_base))

# ============================================================
# 4. TRANSFORMAÇÃO EM EVENTOS (WIDE → LONG)
# ============================================================

@st.cache_data(ttl=600)
def construir_eventos(df_raw: pd.DataFrame) -> pd.DataFrame:
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
            # EqMan é texto com função (OLP, Líder, etc.) ou vazio/- → tratamos como "Não"
            "EqMan": eqman if pd.notna(eqman) and str(eqman).strip() not in ("-", "") else "Não",
            "GVI": parse_bool(gvi),
            "IN": parse_bool(insp),
        }

        # --------- BLOCO DE FÉRIAS ----------
        for col_ini, col_fim in FERIAS_COLS:
            ini = pd.to_datetime(row.get(col_ini, pd.NaT), dayfirst=True, errors="coerce")
            fim = pd.to_datetime(row.get(col_fim, pd.NaT), dayfirst=True, errors="coerce")

            if pd.notna(ini) and pd.notna(fim):
                if fim < ini:
                    ini, fim = fim, ini
                dur = (fim - ini).days + 1
                if 1 <= dur <= 365:
                    eventos.append({
                        **militar_info,
                        "Inicio": ini,
                        "Fim": fim,
                        "Duracao_dias": dur,
                        "Motivo": "FÉRIAS",
                        "Tipo": "Férias"
                    })

        # --------- BLOCO DE OUTRAS AUSÊNCIAS + CURSOS ----------
        for col_ini, col_fim, col_mot, tipo_base in AUSENCIAS_TRIPLETS:
            ini = pd.to_datetime(row.get(col_ini, pd.NaT), dayfirst=True, errors="coerce")
            fim = pd.to_datetime(row.get(col_fim, pd.NaT), dayfirst=True, errors="coerce")
            motivo_texto = str(row.get(col_mot, "")).strip()

            if pd.notna(ini) and pd.notna(fim):
                if fim < ini:
                    ini, fim = fim, ini
                dur = (fim - ini).days + 1
                if dur < 1 or dur > 365:
                    continue

                tipo_final = tipo_base  # "Outros" ou "Curso"

                # Motivo:
                # - para OUTROS: texto da listbox (Disp Médica, Destaque, etc) ou "OUTROS"
                # - para CURSO: texto da listbox (C-ESP-..., C-EXP-...) ou "CURSO"
                if motivo_texto and "nan" not in motivo_texto.lower():
                    motivo_real = motivo_texto
                else:
                    motivo_real = "CURSO" if tipo_final == "Curso" else "OUTROS"

                eventos.append({
                    **militar_info,
                    "Inicio": ini,
                    "Fim": fim,
                    "Duracao_dias": dur,
                    "Motivo": motivo_real,
                    "Tipo": tipo_final
                })

    df_eventos = pd.DataFrame(eventos)
    return df_eventos

df_eventos = construir_eventos(df_raw)

# ============================================================
# 5. EXPANSÃO POR DIA (PARA ANÁLISE MENSAL/DIÁRIA)
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
                "Tipo": ev["Tipo"]
            })

    df_dias = pd.DataFrame(linhas)
    return df_dias

df_dias = expandir_eventos_por_dia(df_eventos)

# ============================================================
# 6. FUNÇÕES DE FILTRO
# ============================================================

def filtrar_tripulacao(df: pd.DataFrame, apenas_eqman: bool, apenas_in: bool, apenas_gvi: bool) -> pd.DataFrame:
    res = df.copy()
    if apenas_eqman and "EqMan" in res.columns:
        res = res[(res["EqMan"].notna()) & (res["EqMan"].astype(str) != "-") & (res["EqMan"].astype(str) != "Não")]
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

# ============================================================
# 7. LEITURA DO % DE FÉRIAS (CÉLULA V2)
# ============================================================

@st.cache_data(ttl=600)
def load_percent_ferias_v2():
    """Lê o valor da célula V2 da planilha Afastamento 2026 para usar na aba Férias."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_v = conn.read(
            worksheet="Afastamento 2026",
            header=None,
            ttl="10m"
        )
        # Coluna V é a 22ª (A=0 → V=21)
        valor = df_v.iloc[1, 21]

        if pd.isna(valor):
            return None

        s = str(valor).strip()
        if s.endswith("%"):
            s = s[:-1].strip()
        s = s.replace(",", ".")
        numero = float(s)

        # Se vier como 40 e não 0.4:
        if numero > 1:
            numero = numero / 100.0

        numero = max(0.0, min(1.0, numero))
        return numero

    except Exception:
        return None

# ============================================================
# 8. SIDEBAR – LOGO, PARÂMETROS E MENU LATERAL
# ============================================================

# Brasão na lateral, maior e centralizado
st.sidebar.image("logo_npamacau.png", width=140)
st.sidebar.markdown("<div class='sidebar-title'>Parâmetros</div>", unsafe_allow_html=True)

data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

st.sidebar.markdown("<div class='sidebar-section'>Navegação</div>", unsafe_allow_html=True)
pagina = st.sidebar.radio(
    "",
    [
        "Presentes",
        "Ausentes",
        "Linha do Tempo (Gantt)",
        "Estatísticas & Análises",
        "Férias",
        "Cursos",
        "Log / Debug",
    ]
)

# ============================================================
# 9. MÉTRICAS GLOBAIS (SEM FILTRO)
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
col2.metric("A Bordo", total_presentes_global)
col3.metric("Ausentes", total_ausentes_global, delta_color="inverse")
col4.metric("Prontidão", f"{percentual_global:.1f}%")

# ============================================================
# 10. FUNÇÃO PARA GRÁFICO DE PIZZA MODERNO
# ============================================================

def grafico_pizza_motivos(df_motivos_dias, titulo):
    fig = px.pie(
        df_motivos_dias,
        names="Motivo",
        values="Duracao_dias",
        hole=0.45,
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
        uniformtext_minsize=12,
        uniformtext_mode='hide',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            color="#e5e7eb"
        )
    )
    return fig

# ============================================================
# 11. PÁGINAS (MENU LATERAL)
# ============================================================

# ------------------------------------------------------------
# PÁGINA: PRESENTES
# ------------------------------------------------------------
if pagina == "Presentes":
    st.subheader(f"Presentes a bordo em {hoje.strftime('%d/%m/%Y')}")

    # Queremos a tabela acima dos filtros → usamos containers
    tabela_container = st.container()
    filtros_container = st.container()

    with filtros_container:
        st.markdown("#### Filtros")
        col_f1, col_f2, col_f3 = st.columns(3)
        apenas_eqman = col_f1.checkbox("Apenas EqMan", key="pres_eqman")
        apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="pres_in")
        apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="pres_gvi")

    df_trip = filtrar_tripulacao(df_raw, apenas_eqman, apenas_in, apenas_gvi)

    if not df_eventos.empty:
        ausentes_hoje = df_eventos[
            (df_eventos["Inicio"] <= hoje) &
            (df_eventos["Fim"] >= hoje)
        ]
        ausentes_hoje = filtrar_eventos(ausentes_hoje, apenas_eqman, apenas_in, apenas_gvi)
        nomes_ausentes = set(ausentes_hoje["Nome"].unique())
    else:
        nomes_ausentes = set()

    df_presentes = df_trip[~df_trip["Nome"].isin(nomes_ausentes)].copy()

    with tabela_container:
        st.markdown(f"Total de presentes (visão filtrada): **{len(df_presentes)}**")

        if df_presentes.empty:
            st.info("Nenhum militar presente para os filtros atuais.")
        else:
            colunas_desejadas = [c for c in ["Posto", "Nome", "Serviço", "EqMan", "Gvi/GP", "IN"] if c in df_presentes.columns]
            tabela = df_presentes[colunas_desejadas].copy()
            if "Gvi/GP" in tabela.columns:
                tabela = tabela.rename(columns={"Gvi/GP": "GVI/GP"})

            # GVI/GP e IN como SIM / NÃO
            if "GVI/GP" in tabela.columns:
                tabela["GVI/GP"] = tabela["GVI/GP"].apply(lambda v: "SIM" if parse_bool(v) else "NÃO")
            if "IN" in tabela.columns:
                tabela["IN"] = tabela["IN"].apply(lambda v: "SIM" if parse_bool(v) else "NÃO")

            st.dataframe(tabela, use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# PÁGINA: AUSENTES
# ------------------------------------------------------------
elif pagina == "Ausentes":
    st.subheader(f"Ausentes em {hoje.strftime('%d/%m/%Y')}")

    tabela_container = st.container()
    filtros_container = st.container()

    with filtros_container:
        st.markdown("#### Filtros")
        col_f1, col_f2, col_f3 = st.columns(3)
        apenas_eqman = col_f1.checkbox("Apenas EqMan", key="aus_eqman")
        apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="aus_in")
        apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="aus_gvi")

    with tabela_container:
        if df_eventos.empty:
            st.info("Sem eventos de ausência registrados.")
        else:
            try:
                ausentes_hoje = df_eventos[
                    (df_eventos["Inicio"] <= hoje) &
                    (df_eventos["Fim"] >= hoje)
                ]
                ausentes_hoje = filtrar_eventos(ausentes_hoje, apenas_eqman, apenas_in, apenas_gvi)

                if ausentes_hoje.empty:
                    st.success("Todo o efetivo está a bordo para os filtros atuais.")
                else:
                    colunas_desejadas = [c for c in ["Posto", "Nome", "Motivo", "Tipo", "EqMan", "Fim"]
                                         if c in ausentes_hoje.columns]
                    show_df = ausentes_hoje[colunas_desejadas].copy()

                    if "Fim" in show_df.columns:
                        show_df["Retorno"] = show_df["Fim"].dt.strftime("%d/%m/%Y")
                        show_df = show_df.drop(columns=["Fim"])

                    if "EqMan" in show_df.columns:
                        tabela_aus = show_df.drop(columns=["EqMan"])
                    else:
                        tabela_aus = show_df

                    st.dataframe(tabela_aus, use_container_width=True, hide_index=True)

                    # Alertas EqMan
                    if "EqMan" in ausentes_hoje.columns:
                        eqman_fora = ausentes_hoje[ausentes_hoje["EqMan"] != "Não"]
                    else:
                        eqman_fora = pd.DataFrame()

                    if not eqman_fora.empty:
                        lista_eqman = sorted(
                            {f"{row['Posto']} {row['Nome']} ({row['EqMan']})" for _, row in eqman_fora.iterrows()}
                        )
                        st.error(
                            "⚠️ Atenção! EqMan com desfalque: " +
                            "; ".join(lista_eqman)
                        )

                    # Alertas GVI/GP
                    if "GVI" in ausentes_hoje.columns:
                        gvi_fora = ausentes_hoje[ausentes_hoje["GVI"] == True]
                    else:
                        gvi_fora = pd.DataFrame()

                    if not gvi_fora.empty:
                        lista_gvi = sorted(
                            {f"{row['Posto']} {row['Nome']}" for _, row in gvi_fora.iterrows()}
                        )
                        st.warning(
                            "🚨 GVI/GP com desfalque: " +
                            "; ".join(lista_gvi)
                        )
            except Exception as e:
                st.error(f"Ocorreu um erro ao montar a lista de ausentes: {e}")

# ------------------------------------------------------------
# PÁGINA: LINHA DO TEMPO (GANTT)
# ------------------------------------------------------------
elif pagina == "Linha do Tempo (Gantt)":
    st.subheader("Planejamento Anual de Ausências")

    if df_eventos.empty:
        st.info("Planilha parece não ter datas preenchidas.")
    else:
        df_gantt = df_eventos.copy()

        if df_gantt.empty:
            st.info("Nenhum evento encontrado.")
        else:
            min_data = df_gantt["Inicio"].min()
            max_data = df_gantt["Fim"].max()
            ano_min = min_data.year if pd.notnull(min_data) else 2025
            ano_max = max_data.year if pd.notnull(max_data) else 2026

            fig = px.timeline(
                df_gantt,
                x_start="Inicio",
                x_end="Fim",
                y="Nome",
                color="Tipo",  # Férias, Curso, Outros
                hover_data=["Posto", "Escala", "EqMan", "GVI", "IN", "Motivo"],
                title="Cronograma de Ausências"
            )
            fig.update_yaxes(autorange="reversed")
            fig.update_xaxes(
                range=[
                    datetime(ano_min, 1, 1),
                    datetime(ano_max, 12, 31)
                ]
            )
            fig.add_vline(
                x=hoje,
                line_width=2,
                line_dash="dash",
                line_color="red"
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.8)",
            )
            st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# PÁGINA: ESTATÍSTICAS & ANÁLISES
# ------------------------------------------------------------
elif pagina == "Estatísticas & Análises":
    st.subheader("Visão Analítica de Ausências (visão global)")

    if df_eventos.empty:
        st.write("Sem dados suficientes para estatísticas.")
    else:
        df_evt = df_eventos.copy()

        if df_evt.empty:
            st.info("Nenhum evento encontrado.")
        else:
            col_a1, col_a2, col_a3 = st.columns(3)

            total_dias_ausencia = df_evt["Duracao_dias"].sum()
            media_dias_por_militar = df_evt.groupby("Nome")["Duracao_dias"].sum().mean()

            df_ferias = df_evt[df_evt["Tipo"] == "Férias"].copy()
            media_dias_ferias = (
                df_ferias.groupby("Nome")["Duracao_dias"].sum().mean()
                if not df_ferias.empty else 0
            )

            col_a1.metric("Dias de ausência (total)", int(total_dias_ausencia))
            col_a2.metric("Média de dias de ausência por militar", f"{media_dias_por_militar:.1f}")
            col_a3.metric("Média de dias de FÉRIAS por militar", f"{media_dias_ferias:.1f}")

            st.markdown("---")

            # Para o gráfico de pizza, qualquer motivo que comece com "CURSO" vira "CURSO"
            df_evt_plot = df_evt.copy()
            df_evt_plot["Motivo"] = df_evt_plot["Motivo"].apply(
                lambda m: "CURSO" if isinstance(m, str) and m.upper().startswith("CURSO") else m
            )

            df_motivos_dias = (
                df_evt_plot.groupby("Motivo")["Duracao_dias"]
                .sum()
                .reset_index()
                .sort_values("Duracao_dias", ascending=False)
            )
            fig_motivos = grafico_pizza_motivos(df_motivos_dias, "Proporção de Dias de Ausência por Motivo")
            st.plotly_chart(fig_motivos, use_container_width=True)

            st.markdown("---")

            st.subheader("Top 10 militares com mais dias de ausência (qualquer motivo)")
            df_top10 = (
                df_evt.groupby(["Nome", "Posto"])["Duracao_dias"]
                .sum()
                .reset_index()
                .sort_values("Duracao_dias", ascending=False)
                .head(10)
            )
            fig_top10 = px.bar(
                df_top10,
                x="Nome",
                y="Duracao_dias",
                color="Posto",
                title="Top 10 – Dias de ausência por militar",
                labels={"Duracao_dias": "Dias de ausência"}
            )
            fig_top10.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.8)",
            )
            st.plotly_chart(fig_top10, use_container_width=True)

            if not df_dias.empty:
                st.markdown("---")
                st.subheader("Média de militares ausentes por dia (por mês)")

                df_diario = (
                    df_dias.groupby("Data")["Nome"]
                    .nunique()
                    .reset_index(name="Ausentes")
                )
                df_diario["Mes"] = df_diario["Data"].dt.to_period("M").dt.to_timestamp()
                df_mensal = (
                    df_diario.groupby("Mes")["Ausentes"]
                    .mean()
                    .reset_index(name="Media_ausentes_dia")
                )

                fig_mensal = px.line(
                    df_mensal,
                    x="Mes",
                    y="Media_ausentes_dia",
                    markers=True,
                    title="Média de Ausentes por Dia – por Mês",
                    labels={"Mes": "Mês", "Media_ausentes_dia": "Média de ausentes/dia"}
                )
                fig_mensal.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.8)",
                )
                st.plotly_chart(fig_mensal, use_container_width=True)
            else:
                st.info("Sem dados diários para análise mensal.")

# ------------------------------------------------------------
# PÁGINA: FÉRIAS
# ------------------------------------------------------------
elif pagina == "Férias":
    st.subheader("Férias cadastradas")

    if df_eventos.empty:
        st.write("Sem dados de férias registrados.")
    else:
        df_ferias = df_eventos[df_eventos["Tipo"] == "Férias"].copy()

        if df_ferias.empty:
            st.info("Nenhuma férias cadastrada.")
        else:
            tabela_ferias = df_ferias[["Posto", "Nome", "Escala", "Inicio", "Fim", "Duracao_dias"]].copy()
            tabela_ferias["Início"] = tabela_ferias["Inicio"].dt.strftime("%d/%m/%Y")
            tabela_ferias["Término"] = tabela_ferias["Fim"].dt.strftime("%d/%m/%Y")
            tabela_ferias = tabela_ferias.drop(columns=["Inicio", "Fim"])
            tabela_ferias = tabela_ferias.rename(columns={"Duracao_dias": "Dias"})
            tabela_ferias = tabela_ferias.sort_values(by=["Nome", "Início"])

            st.markdown("### Todos os períodos de férias registrados")
            st.dataframe(tabela_ferias, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Análises Específicas de Férias")

            col_f1m, col_f2m = st.columns(2)
            total_militares_com_ferias = df_ferias["Nome"].nunique()
            dias_totais_ferias = df_ferias["Duracao_dias"].sum()

            col_f1m.metric("Militares com férias cadastradas", total_militares_com_ferias)
            col_f2m.metric("Dias totais de férias", int(dias_totais_ferias))

            st.markdown("---")

            col_fx1, col_fx2 = st.columns(2)

            # Férias por escala
            df_escala = (
                df_ferias.groupby("Escala")["Nome"]
                .nunique()
                .reset_index(name="Militares")
                .sort_values("Militares", ascending=False)
            )
            fig_escala = px.bar(
                df_escala,
                x="Escala",
                y="Militares",
                title="Quantidade de militares com férias por escala",
                labels={"Militares": "Militares em férias (no ano)"}
            )
            fig_escala.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(15,23,42,0.8)",
            )
            col_fx1.plotly_chart(fig_escala, use_container_width=True)

            # Férias por mês
            if not df_dias.empty:
                df_dias_ferias = df_dias[df_dias["Tipo"] == "Férias"].copy()
                if not df_dias_ferias.empty:
                    df_dias_ferias["Mes"] = df_dias_ferias["Data"].dt.to_period("M").dt.to_timestamp()
                    df_mes_ferias = (
                        df_dias_ferias[["Mes", "Nome"]]
                        .drop_duplicates()
                        .groupby("Mes")["Nome"]
                        .nunique()
                        .reset_index(name="Militares")
                    )
                    fig_mes_ferias = px.bar(
                        df_mes_ferias,
                        x="Mes",
                        y="Militares",
                        title="Quantidade de militares com férias previstas por mês",
                        labels={"Mes": "Mês", "Militares": "Militares com férias no mês"}
                    )
                    fig_mes_ferias.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(15,23,42,0.8)",
                    )
                    col_fx2.plotly_chart(fig_mes_ferias, use_container_width=True)
                else:
                    col_fx2.info("Sem dados diários suficientes para calcular férias por mês.")
            else:
                col_fx2.info("Sem expansão diária para análise mensal.")

            # Gráfico de pizza com % de férias já gozadas (V2)
            st.markdown("---")
            st.subheader("Percentual de férias já gozadas")

            perc_ferias = load_percent_ferias_v2()
            if perc_ferias is not None:
                df_pct = pd.DataFrame({
                    "Status": ["Gozadas", "Restantes"],
                    "Valor": [perc_ferias, 1 - perc_ferias]
                })

                fig_pct = px.pie(
                    df_pct,
                    names="Status",
                    values="Valor",
                    hole=0.45
                )
                fig_pct.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                    hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>"
                )
                fig_pct.update_layout(
                    title="Percentual de férias já gozadas (V2)",
                    showlegend=True,
                    margin=dict(t=60, b=20, l=0, r=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(
                        family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                        color="#e5e7eb"
                    )
                )
                st.plotly_chart(fig_pct, use_container_width=True)
            else:
                st.info("Não foi possível ler o valor de V2. Verifique se a célula contém o percentual de férias.")

# ------------------------------------------------------------
# PÁGINA: CURSOS
# ------------------------------------------------------------
elif pagina == "Cursos":
    st.subheader("Análises de Cursos (visão global)")

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

            # Cursos já realizados
            with col_c1:
                st.markdown("### Cursos já realizados")
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

            # Cursos em andamento / futuros
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

                # Cursos mais frequentes
                df_cursos_freq = (
                    realizados.groupby("Motivo")["Nome"]
                    .nunique()
                    .reset_index(name="Militares")
                    .sort_values("Militares", ascending=False)
                )
                fig_cursos_freq = px.bar(
                    df_cursos_freq,
                    x="Motivo",
                    y="Militares",
                    title="Cursos mais frequentes (militares que já realizaram)",
                    labels={"Motivo": "Curso", "Militares": "Militares"}
                )
                fig_cursos_freq.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(15,23,42,0.8)",
                )
                col_g1.plotly_chart(fig_cursos_freq, use_container_width=True)

                # Militares em curso por mês
                if not df_dias.empty:
                    df_dias_cursos = df_dias[df_dias["Tipo"] == "Curso"].copy()

                    if not df_dias_cursos.empty:
                        df_dias_cursos["Mes"] = df_dias_cursos["Data"].dt.to_period("M").dt.to_timestamp()
                        df_curso_mes = (
                            df_dias_cursos[["Mes", "Nome"]]
                            .drop_duplicates()
                            .groupby("Mes")["Nome"]
                            .nunique()
                            .reset_index(name="Militares")
                        )
                        fig_curso_mes = px.line(
                            df_curso_mes,
                            x="Mes",
                            y="Militares",
                            markers=True,
                            title="Militares em curso por mês",
                            labels={"Mes": "Mês", "Militares": "Militares em curso"}
                        )
                        fig_curso_mes.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(15,23,42,0.8)",
                        )
                        col_g2.plotly_chart(fig_curso_mes, use_container_width=True)
                    else:
                        col_g2.info("Sem dados diários suficientes para análise mensal de cursos.")
                else:
                    col_g2.info("Sem expansão diária para análise mensal de cursos.")

# ------------------------------------------------------------
# PÁGINA: LOG / DEBUG
# ------------------------------------------------------------
elif pagina == "Log / Debug":
    st.subheader("Log / Debug")

    st.markdown("### df_raw (dados brutos do Google Sheets)")
    st.write(f"Total de linhas em df_raw: **{len(df_raw)}**")
    st.write("Colunas disponíveis em df_raw:")
    st.write(list(df_raw.columns))

    st.write("Prévia de df_raw (primeiras 15 linhas):")
    st.dataframe(df_raw.head(15), use_container_width=True)

    st.markdown("---")
    st.markdown("### Mapeamento de Ausências (Férias, Outras Ausências, Cursos)")

    # Mostrar mapeamento de férias
    debug_ferias = []
    for idx, (c_ini, c_fim) in enumerate(FERIAS_COLS, start=1):
        debug_ferias.append({"Bloco": idx, "Tipo": "Férias", "Col_Inicio": c_ini, "Col_Fim": c_fim})
    if debug_ferias:
        st.dataframe(pd.DataFrame(debug_ferias), use_container_width=True)
    else:
        st.info("Nenhum bloco de férias mapeado.")

    # Mapeamento de ausências (Outros + Curso)
    st.markdown("#### Ausências / Cursos")
    debug_rows = []
    for idx, (c_ini, c_fim, c_mot, tipo_base) in enumerate(AUSENCIAS_TRIPLETS, start=1):
        debug_rows.append(
            {"Bloco": idx, "Col_Inicio": c_ini, "Col_Fim": c_fim, "Col_Tipo/Motivo": c_mot, "Tipo_base": tipo_base}
        )
    if debug_rows:
        st.dataframe(pd.DataFrame(debug_rows), use_container_width=True)
    else:
        st.info("Nenhum bloco de ausência/cursos mapeado.")

    st.markdown("---")
    st.markdown("### df_eventos (eventos gerados)")

    st.write(f"Total de eventos em df_eventos: **{len(df_eventos)}**")

    if not df_eventos.empty:
        st.dataframe(df_eventos.head(40), use_container_width=True)
        st.write("Anos em Inicio:", df_eventos["Inicio"].dt.year.unique())
        st.write("Anos em Fim:", df_eventos["Fim"].dt.year.unique())
        st.write("Tipos registrados:", df_eventos["Tipo"].unique())
    else:
        st.info("df_eventos está vazio. Verifique se as colunas de datas e ausências estão corretamente preenchidas na planilha.")

# ============================================================
# 12. RODAPÉ
# ============================================================
st.markdown("<hr style='border-color:#1f2937; margin-top:2rem;'/>", unsafe_allow_html=True)
st.markdown(
    f"<div style='text-align:center; color:#9ca3af; padding:0.5rem 0;'>"
    f"Created by <strong>Klismann Freitas</strong> · Versão {APP_VERSION}"
    f"</div>",
    unsafe_allow_html=True
)
