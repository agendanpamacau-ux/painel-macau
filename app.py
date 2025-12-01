import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Painel NPaMacau",
    layout="wide",
    page_icon="⚓"
)
st.title("⚓ Dashboard de Comando - NPaMacau")


# ============================================================
# 2. CONSTANTES E HELPERS
# ============================================================

# Linha de cabeçalho na planilha (0-based para o pandas)
HEADER_ROW = 2  # linha 3 da planilha

# Índices de colunas (0-based) — de acordo com a tua descrição
COL = {
    "NUMERO": 0,    # A
    "POSTO": 1,     # B
    "NOME": 2,      # C
    "SERVICO": 3,   # D
    "EQMAN": 4,     # E
    "GVI": 5,       # F (checkbox)
    "INSP": 6,      # G (checkbox)
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


def safe_to_datetime(value):
    """Converte para datetime (dia primeiro) com segurança."""
    return pd.to_datetime(value, dayfirst=True, errors="coerce")


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
        eqman_raw = row.iloc[COL["EQMAN"]] if len(row) > COL["EQMAN"] else None
        gvi_raw = row.iloc[COL["GVI"]] if len(row) > COL["GVI"] else None
        insp_raw = row.iloc[COL["INSP"]] if len(row) > COL["INSP"] else None

        militar_info = {
            "Posto": posto,
            "Nome": nome,
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
            ini = safe_to_datetime(row.iloc[inicio_idx])
            fim = safe_to_datetime(row.iloc[fim_idx])
            if pd.notnull(ini) and pd.notnull(fim):
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
            ini = safe_to_datetime(row.iloc[ini_idx])
            fim = safe_to_datetime(row.iloc[fim_idx])
            motivo_texto = str(row.iloc[mot_idx])

            if pd.notnull(ini) and pd.notnull(fim):
                motivo_real = (motivo_texto.strip()
                               if len(motivo_texto) > 2
                               and "nan" not in motivo_texto.lower()
                               else "OUTROS")
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

    return df_eventos


df_eventos = construir_eventos(df_raw)


# ============================================================
# 5. EXPANSÃO POR DIA (PARA ANÁLISE MENSAL/DIÁRIA)
# ============================================================

@st.cache_data(ttl=600)
def expandir_eventos_por_dia(df_eventos: pd.DataFrame) -> pd.DataFrame:
    """
    Cria um DataFrame com uma linha por dia de ausência por militar.
    Útil para análise diária/mensal (média de ausentes/dia etc.).
    """
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
# 6. BARRA LATERAL (FILTROS)
# ============================================================

st.sidebar.header("🕹️ Centro de Controle")

data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

# Filtro de posto
todos_postos = df_raw.iloc[:, COL["POSTO"]].dropna().unique()
filtro_posto = st.sidebar.multiselect(
    "Filtrar Posto",
    options=sorted(todos_postos),
    default=sorted(todos_postos)
)

# Filtros especiais
filtro_eqman = st.sidebar.checkbox("Apenas EqMan")
filtro_in = st.sidebar.checkbox("Apenas Inspetores Navais (IN)")
filtro_gvi = st.sidebar.checkbox("Apenas GVI/GP")

# Aplica filtro de efetivo (df_raw)
df_tripulacao_filtrada = df_raw[df_raw.iloc[:, COL["POSTO"]].isin(filtro_posto)].copy()

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
        (df_eventos["Fim"] >= hoje) &
        (df_eventos["Posto"].isin(filtro_posto))
    ]

    if filtro_eqman:
        ausentes_hoje = ausentes_hoje[ausentes_hoje["EqMan"] != "Não"]
    if filtro_in:
        ausentes_hoje = ausentes_hoje[ausentes_hoje["IN"] == True]
    if filtro_gvi:
        ausentes_hoje = ausentes_hoje[ausentes_hoje["GVI"] == True]
else:
    ausentes_hoje = pd.DataFrame()

# KPIs básicos
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
# 9. TABS PRINCIPAIS
# ============================================================

tab1, tab2, tab3 = st.tabs([
    "📋 Situação Diária",
    "📅 Linha do Tempo (Gantt)",
    "📊 Estatísticas & Análises"
])

# ------------------------------------------------------------
# TAB 1 – SITUAÇÃO DIÁRIA
# ------------------------------------------------------------
with tab1:
    st.subheader(f"Status em {hoje.strftime('%d/%m/%Y')}")

    if total_ausentes > 0:
        show_df = ausentes_hoje[["Posto", "Nome", "Motivo", "Fim"]].copy()
        show_df["Retorno"] = show_df["Fim"].dt.strftime("%d/%m/%Y")
        show_df = show_df.drop(columns=["Fim"])
        st.dataframe(show_df, use_container_width=True, hide_index=True)

        # Alerta EqMan
        eqman_fora = ausentes_hoje[ausentes_hoje["EqMan"] != "Não"]
        if not eqman_fora.empty:
            st.error(
                "⚠️ Atenção! EqMan com desfalque: " +
                ", ".join(sorted(eqman_fora["Nome"].unique()))
            )

        # Alerta GVI
        gvi_fora = ausentes_hoje[ausentes_hoje["GVI"] == True]
        if not gvi_fora.empty:
            st.warning(
                "🚨 GVI/GP com desfalque: " +
                ", ".join(sorted(gvi_fora["Nome"].unique()))
            )

    else:
        st.success("Todo o efetivo selecionado está a bordo.")


# ------------------------------------------------------------
# TAB 2 – LINHA DO TEMPO (GANTT)
# ------------------------------------------------------------
with tab2:
    st.subheader("Planejamento Anual de Ausências")

    if df_eventos.empty:
        st.info("Planilha parece não ter datas preenchidas.")
    else:
        df_gantt = df_eventos[df_eventos["Posto"].isin(filtro_posto)].copy()

        if filtro_eqman:
            df_gantt = df_gantt[df_gantt["EqMan"] != "Não"]
        if filtro_in:
            df_gantt = df_gantt[df_gantt["IN"] == True]
        if filtro_gvi:
            df_gantt = df_gantt[df_gantt["GVI"] == True]

        if df_gantt.empty:
            st.info("Nenhum evento encontrado para os filtros atuais.")
        else:
            fig = px.timeline(
                df_gantt,
                x_start="Inicio",
                x_end="Fim",
                y="Nome",
                color="Motivo",
                hover_data=["Posto", "EqMan", "GVI", "IN", "Tipo"],
                title="Cronograma de Ausências"
            )
            fig.update_yaxes(autorange="reversed")

            # Linha vertical no dia selecionado
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
        # Filtrar df_eventos de acordo com filtros laterais
        df_evt = df_eventos[df_eventos["Posto"].isin(filtro_posto)].copy()
        if filtro_eqman:
            df_evt = df_evt[df_evt["EqMan"] != "Não"]
        if filtro_in:
            df_evt = df_evt[df_evt["IN"] == True]
        if filtro_gvi:
            df_evt = df_evt[df_evt["GVI"] == True]

        # Se ainda tiver algo:
        if df_evt.empty:
            st.info("Nenhum evento para os filtros selecionados.")
        else:
            # ---- KPIs analíticos ----
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

            # ---- Gráficos principais ----
            col_b1, col_b2 = st.columns(2)

            # 1) Distribuição de motivos (por dias)
            df_motivos_dias = (
                df_evt.groupby("Motivo")["Duracao_dias"]
                .sum()
                .reset_index()
                .sort_values("Duracao_dias", ascending=False)
            )
            fig_motivos = px.bar(
                df_motivos_dias,
                x="Motivo",
                y="Duracao_dias",
                title="Dias de Ausência por Motivo",
                labels={"Duracao_dias": "Dias de ausência"}
            )
            col_b1.plotly_chart(fig_motivos, use_container_width=True)

            # 2) Volume de ausências por Posto (por dias)
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

            # ---- TOP 10 mais ausentes ----
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

            # ---- Análise mensal (média de ausentes/dia) ----
            if not df_dias.empty:
                st.markdown("---")
                st.subheader("Média de militares ausentes por dia (por mês)")

                # Aplica filtros também na visão diária
                df_dias_filtrado = df_dias[df_dias["Posto"].isin(filtro_posto)].copy()
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
