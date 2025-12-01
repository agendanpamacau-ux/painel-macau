import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Controle de ausências - NPaMacau",
    layout="wide",
    page_icon="⚓"
)
st.title("⚓ Controle de ausências - NPaMacau")

# --- CSS para visual mais moderno ---
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at top left, #0f172a 0, #020617 45%, #000 100%);
        color: #e5e7eb;
    }
    h1 {
        font-weight: 700 !important;
        color: #e5e7eb !important;
    }
    div[data-testid="metric-container"] {
        background: rgba(15, 23, 42, 0.85);
        border-radius: 0.9rem;
        padding: 1rem;
        border: 1px solid #1f2937;
        box-shadow: 0 10px 25px rgba(0,0,0,0.35);
    }
    button[data-baseweb="tab"] {
        font-weight: 600;
    }
    button[data-baseweb="tab"]:hover {
        background: #0f172a;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: #0f172a;
        color: #e5e7eb;
        border-bottom: 2px solid #38bdf8;
    }
    .stDataFrame {
        background: #020617;
        border-radius: 0.75rem;
        padding: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# 2. CONSTANTES E HELPERS
# ============================================================

HEADER_ROW = 2  # linha 3 na planilha

COL = {
    "NUMERO": 0,    # A
    "POSTO": 1,     # B
    "NOME": 2,      # C
    "SERVICO": 3,   # D - escala
    "EQMAN": 4,     # E
    "GVI": 5,       # F
    "INSP": 6,      # G
}

# Férias: (inicio_idx, fim_idx)
FERIAS_PARES = [
    (8, 9),   # I-J - Período 1
    (11, 12), # L-M - Período 2
    (14, 15)  # O-P - Período 3
]

# Outras ausências: (inicio_idx, fim_idx, motivo_idx)
AUSENCIAS_TRIOS = [
    (24, 25, 27),  # Y-Z, motivo AB - Período 4
    (29, 30, 32),  # AD-AE, motivo AG - Período 5
    (34, 35, 37),  # AI-AJ, motivo AL - Período 6
    (39, 40, 42),  # AN-AO, motivo AQ - Período 7
    (44, 45, 47),  # AS-AT, motivo AV - Período 8
]


def parse_bool(value) -> bool:
    """Converte checkbox/texto da planilha em booleano robusto."""
    if pd.isna(value):
        return False
    s = str(value).strip().lower()
    return s in ("true", "1", "sim", "yes", "y", "x")


def parse_sheet_date(value):
    """
    Converte valor do Google Sheets em datetime, aceitando:
    - datetime / Timestamp
    - número serial (ex: 45686)
    - string numérica ("45686")
    - string de data brasileira ("30/11/2025", "30/11/25")
    """
    if pd.isna(value) or value == "":
        return pd.NaT

    # já é datetime
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.normalize()

    # número serial (int/float)
    if isinstance(value, (int, float)):
        base = datetime(1899, 12, 30)  # base do Sheets/Excel
        dt = base + timedelta(days=float(value))
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    # string
    s = str(value).strip()
    if s == "":
        return pd.NaT

    # string numérica (ex: "45686")
    s_num = s.replace(".", "", 1)
    if s_num.isdigit():
        base = datetime(1899, 12, 30)
        dt = base + timedelta(days=float(s))
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    # tenta como data (formato BR)
    dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
    if pd.isna(dt):
        return pd.NaT

    return dt.normalize()


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

    # Remove linhas sem nome (coluna C / índice 2)
    if len(df.columns) > COL["NOME"]:
        df = df.dropna(subset=[df.columns[COL["NOME"]]])

    df = df.reset_index(drop=True)
    return df


try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro de conexão. Verifique o arquivo secrets.toml. Detalhe: {e}")
    st.stop()


# ============================================================
# 4. TRANSFORMAÇÃO EM LISTA DE EVENTOS (WIDE → LONG)
# ============================================================

@st.cache_data(ttl=600)
def construir_eventos(df_raw: pd.DataFrame) -> pd.DataFrame:
    eventos = []

    for _, row in df_raw.iterrows():
        posto = row.iloc[COL["POSTO"]]
        nome = row.iloc[COL["NOME"]]
        escala = row.iloc[COL["SERVICO"]] if len(row) > COL["SERVICO"] else ""
        eqman_raw = row.iloc[COL["EQMAN"]] if len(row) > COL["EQMAN"] else None
        gvi_raw = row.iloc[COL["GVI"]] if len(row) > COL["GVI"] else None
        insp_raw = row.iloc[COL["INSP"]] if len(row) > COL["INSP"] else None

        militar_info = {
            "Posto": posto,
            "Nome": nome,
            "Escala": escala,
            "EqMan": (
                eqman_raw if pd.notnull(eqman_raw) and str(eqman_raw) != "-" else "Não"
            ),
            "GVI": parse_bool(gvi_raw),
            "IN": parse_bool(insp_raw),
        }

        # --------- Bloco de Férias ----------
        for inicio_idx, fim_idx in FERIAS_PARES:
            if len(row) <= fim_idx:
                continue

            ini = parse_sheet_date(row.iloc[inicio_idx])
            fim = parse_sheet_date(row.iloc[fim_idx])

            if pd.notnull(ini) and pd.notnull(fim):
                if fim < ini:
                    ini, fim = fim, ini

                eventos.append({
                    **militar_info,
                    "Inicio": ini,
                    "Fim": fim,
                    "Motivo": "FÉRIAS",
                    "Tipo": "Férias"
                })

        # --------- Bloco de Outras Ausências ----------
        for ini_idx, fim_idx, mot_idx in AUSENCIAS_TRIOS:
            if len(row) <= mot_idx:
                continue

            ini = parse_sheet_date(row.iloc[ini_idx])
            fim = parse_sheet_date(row.iloc[fim_idx])
            motivo_texto = str(row.iloc[mot_idx])

            if pd.notnull(ini) and pd.notnull(fim):
                if fim < ini:
                    ini, fim = fim, ini

                motivo_real = (
                    motivo_texto.strip()
                    if len(motivo_texto) > 2
                    and "nan" not in motivo_texto.lower()
                    else "OUTROS"
                )

                eventos.append({
                    **militar_info,
                    "Inicio": ini,
                    "Fim": fim,
                    "Motivo": motivo_real,
                    "Tipo": "Outros"
                })

    df_eventos = pd.DataFrame(eventos)

    if not df_eventos.empty:
        df_eventos["Duracao_dias"] = (df_eventos["Fim"] - df_eventos["Inicio"]).dt.days + 1
        # Mantém só durações razoáveis (evita datas lixo gigantes)
        df_eventos = df_eventos[df_eventos["Duracao_dias"].between(1, 365)]

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
        if pd.isna(ev["Inicio"]) or pd.isna(ev["Fim"]):
            continue
        for data in pd.date_range(ev["Inicio"], ev["Fim"]):
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
# 6. BARRA LATERAL (FILTROS) – sem filtro de posto
# ============================================================

st.sidebar.header("🕹️ Centro de Controle")

data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

filtro_eqman = st.sidebar.checkbox("Apenas EqMan")
filtro_in = st.sidebar.checkbox("Apenas Inspetores Navais (IN)")
filtro_gvi = st.sidebar.checkbox("Apenas GVI/GP")

df_tripulacao_filtrada = df_raw.copy()

if filtro_eqman:
    df_tripulacao_filtrada = df_tripulacao_filtrada[
        (df_tripulacao_filtrada.iloc[:, COL["EQMAN"]].notnull()) &
        (df_tripulacao_filtrada.iloc[:, COL["EQMAN"]].astype(str) != "-")
    ]

if filtro_in:
    df_tripulacao_filtrada = df_tripulacao_filtrada[
        df_tripulacao_filtrada.iloc[:, COL["INSP"]].apply(parse_bool)
    ]

if filtro_gvi:
    df_tripulacao_filtrada = df_tripulacao_filtrada[
        df_tripulacao_filtrada.iloc[:, COL["GVI"]].apply(parse_bool)
    ]


# ============================================================
# 7. QUEM ESTÁ AUSENTE NA DATA DE REFERÊNCIA?
# ============================================================

if not df_eventos.empty:
    ausentes_hoje = df_eventos[
        (df_eventos["Inicio"] <= hoje) &
        (df_eventos["Fim"] >= hoje)
    ]

    if filtro_eqman:
        ausentes_hoje = ausentes_hoje[ausentes_hoje["EqMan"] != "Não"]
    if filtro_in:
        ausentes_hoje = ausentes_hoje[ausentes_hoje["IN"] == True]
    if filtro_gvi:
        ausentes_hoje = ausentes_hoje[ausentes_hoje["GVI"] == True]
else:
    ausentes_hoje = pd.DataFrame()

total_efetivo = len(df_tripulacao_filtrada)
total_ausentes = len(ausentes_hoje["Nome"].unique()) if not ausentes_hoje.empty else 0
total_presentes = total_efetivo - total_ausentes
percentual = (total_presentes / total_efetivo * 100) if total_efetivo > 0 else 0


# ============================================================
# 8. MÉTRICAS DE TOPO
# ============================================================

col1, col2, col3, col4 = st.columns(4)
col1.metric("Efetivo Total", total_efetivo)
col2.metric("A Bordo", total_presentes)
col3.metric("Ausentes", total_ausentes, delta_color="inverse")
col4.metric("Prontidão", f"{percentual:.1f}%")


# ============================================================
# 9. TABS PRINCIPAIS (incluindo aba só de Férias)
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Situação Diária",
    "📅 Linha do Tempo (Gantt)",
    "📊 Estatísticas & Análises",
    "🏖️ Férias"
])

# ------------------------------------------------------------
# TAB 1 – SITUAÇÃO DIÁRIA
# ------------------------------------------------------------
with tab1:
    st.subheader(f"Ausentes em {hoje.strftime('%d/%m/%Y')}")

    if total_ausentes > 0:
        show_df = ausentes_hoje[["Posto", "Nome", "Motivo", "Fim"]].copy()
        show_df["Retorno"] = show_df["Fim"].dt.strftime("%d/%m/%Y")
        show_df = show_df.drop(columns=["Fim"])
        st.dataframe(show_df, use_container_width=True, hide_index=True)

        eqman_fora = ausentes_hoje[ausentes_hoje["EqMan"] != "Não"]
        if not eqman_fora.empty:
            st.error(
                "⚠️ Atenção! EqMan com desfalque: " +
                ", ".join(sorted(eqman_fora["Nome"].unique()))
            )

        gvi_fora = ausentes_hoje[ausentes_hoje["GVI"] == True]
        if not gvi_fora.empty:
            st.warning(
                "🚨 GVI/GP com desfalque: " +
                ", ".join(sorted(gvi_fora["Nome"].unique()))
            )

    else:
        st.success("Todo o efetivo está a bordo para os filtros atuais.")


# ------------------------------------------------------------
# TAB 2 – LINHA DO TEMPO (GANTT)
# ------------------------------------------------------------
with tab2:
    st.subheader("Planejamento Anual de Ausências")

    if df_eventos.empty:
        st.info("Planilha parece não ter datas preenchidas.")
    else:
        df_gantt = df_eventos.copy()

        if filtro_eqman:
            df_gantt = df_gantt[df_gantt["EqMan"] != "Não"]
        if filtro_in:
            df_gantt = df_gantt[df_gantt["IN"] == True]
        if filtro_gvi:
            df_gantt = df_gantt[df_gantt["GVI"] == True]

        if df_gantt.empty:
            st.info("Nenhum evento encontrado para os filtros atuais.")
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
                color="Motivo",
                hover_data=["Posto", "Escala", "EqMan", "GVI", "IN", "Tipo"],
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
            st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# TAB 3 – ESTATÍSTICAS E ANÁLISES
# ------------------------------------------------------------
with tab3:
    st.subheader("Visão Analítica de Ausências")

    if df_eventos.empty:
        st.write("Sem dados suficientes para estatísticas.")
    else:
        df_evt = df_eventos.copy()
        if filtro_eqman:
            df_evt = df_evt[df_evt["EqMan"] != "Não"]
        if filtro_in:
            df_evt = df_evt[df_evt["IN"] == True]
        if filtro_gvi:
            df_evt = df_evt[df_evt["GVI"] == True]

        if df_evt.empty:
            st.info("Nenhum evento para os filtros selecionados.")
        else:
            col_a1, col_a2, col_a3, col_a4 = st.columns(4)

            total_dias_ausencia = df_evt["Duracao_dias"].sum()
            media_dias_por_militar = df_evt.groupby("Nome")["Duracao_dias"].sum().mean()

            df_ferias = df_evt[df_evt["Tipo"] == "Férias"].copy()
            media_dias_ferias = (
                df_ferias.groupby("Nome")["Duracao_dias"].sum().mean()
                if not df_ferias.empty else 0
            )

            top_mais_ausentes = (
                df_evt.groupby("Nome")["Duracao_dias"].sum()
                .sort_values(ascending=False)
                .head(1)
            )
            if not top_mais_ausentes.empty:
                nome_top = top_mais_ausentes.index[0]
                dias_top = int(top_mais_ausentes.iloc[0])
                resumo_top = f"{nome_top} ({dias_top} dias)"
            else:
                resumo_top = "-"

            col_a1.metric("Dias de ausência (total)", int(total_dias_ausencia))
            col_a2.metric("Média de dias de ausência por militar", f"{media_dias_por_militar:.1f}")
            col_a3.metric("Média de dias de FÉRIAS por militar", f"{media_dias_ferias:.1f}")
            col_a4.metric("Militar mais ausente (dias)", resumo_top)

            st.markdown("---")

            col_b1, col_b2 = st.columns(2)

            # Gráfico de motivos – pizza
            df_motivos_dias = (
                df_evt.groupby("Motivo")["Duracao_dias"]
                .sum()
                .reset_index()
                .sort_values("Duracao_dias", ascending=False)
            )
            fig_motivos = px.pie(
                df_motivos_dias,
                names="Motivo",
                values="Duracao_dias",
                title="Proporção de Dias de Ausência por Motivo"
            )
            col_b1.plotly_chart(fig_motivos, use_container_width=True)

            # Ausência por posto – barra
            df_posto_dias = (
                df_evt.groupby("Posto")["Duracao_dias"]
                .sum()
                .reset_index()
                .sort_values("Duracao_dias", ascending=False)
            )
            fig_posto = px.bar(
                df_posto_dias,
                x="Posto",
                y="Duracao_dias",
                title="Dias de Ausência por Posto",
                labels={"Duracao_dias": "Dias de ausência"}
            )
            col_b2.plotly_chart(fig_posto, use_container_width=True)

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
            st.plotly_chart(fig_top10, use_container_width=True)

            if not df_dias.empty:
                st.markdown("---")
                st.subheader("Média de militares ausentes por dia (por mês)")

                df_dias_filtrado = df_dias.copy()
                if filtro_eqman:
                    df_dias_filtrado = df_dias_filtrado[df_dias_filtrado["EqMan"] != "Não"]
                if filtro_in:
                    df_dias_filtrado = df_dias_filtrado[df_dias_filtrado["IN"] == True]
                if filtro_gvi:
                    df_dias_filtrado = df_dias_filtrado[df_dias_filtrado["GVI"] == True]

                if not df_dias_filtrado.empty:
                    df_diario = (
                        df_dias_filtrado.groupby("Data")["Nome"]
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
                    st.plotly_chart(fig_mensal, use_container_width=True)
                else:
                    st.info("Sem dados diários para análise mensal com os filtros atuais.")


# ------------------------------------------------------------
# TAB 4 – SOMENTE FÉRIAS
# ------------------------------------------------------------
with tab4:
    st.subheader("Análises Específicas de Férias")

    if df_eventos.empty:
        st.write("Sem dados de férias registrados.")
    else:
        df_ferias = df_eventos[df_eventos["Tipo"] == "Férias"].copy()

        if df_ferias.empty:
            st.info("Nenhuma férias cadastrada na planilha.")
        else:
            # KPIs férias
            col_f1, col_f2 = st.columns(2)
            total_militares_com_ferias = df_ferias["Nome"].nunique()
            dias_totais_ferias = df_ferias["Duracao_dias"].sum()

            col_f1.metric("Militares com férias cadastradas", total_militares_com_ferias)
            col_f2.metric("Dias totais de férias", int(dias_totais_ferias))

            st.markdown("---")

            col_fx1, col_fx2 = st.columns(2)

            # 1 - Quantidade de militares de férias por escala
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
            col_fx1.plotly_chart(fig_escala, use_container_width=True)

            # 2 - Quantidade de militares de férias por mês
            if not df_dias.empty:
                df_dias_ferias = df_dias[df_dias["Tipo"] == "Férias"].copy()
                if not df_dias_ferias.empty:
                    df_dias_ferias["Mes"] = df_dias_ferias["Data"].dt.to_period("M").dt.to_timestamp()
                    # Um militar conta 1 vez por mês, mesmo que fique o mês inteiro
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
                    col_fx2.plotly_chart(fig_mes_ferias, use_container_width=True)
                else:
                    col_fx2.info("Sem dados diários suficientes para calcular férias por mês.")
            else:
                col_fx2.info("Sem expansão diária para análise mensal.")
