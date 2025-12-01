import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Navio-Patrula Macau",
    layout="wide",
    page_icon="⚓"
)

# Logo + título
col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    # Arquivo logo_npamacau.png deve estar na mesma pasta do app.py
    st.image("logo_npamacau.png", width=90)
with col_titulo:
    st.title("Navio-Patrula Macau")

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
# 2. HELPERS E CONSTANTES
# ============================================================

HEADER_ROW = 2  # linha 3 na planilha

def parse_bool(value) -> bool:
    """Converte checkbox/texto da planilha em booleano robusto."""
    if pd.isna(value):
        return False
    s = str(value).strip().lower()
    return s in ("true", "1", "sim", "yes", "y", "x")


# Férias ainda são aquelas colunas sem acento, como já vimos:
FERIAS_COLS = [
    ("Inicio",   "Fim"),    # Período 1 (I-J)
    ("Inicio.1", "Fim.1"),  # Período 2 (L-M)
    ("Inicio.2", "Fim.2"),  # Período 3 (O-P)
]


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
# 4. DESCOBRIR DINAMICAMENTE AS AUSÊNCIAS (INÍCIO/FIM/MOTIVO)
#    – OUTRAS AUSÊNCIAS x CURSOS
# ============================================================

def descobrir_ausencias_triplets(df: pd.DataFrame):
    """
    Busca todas as colunas de ausências do tipo:
    'Início', 'FIm', 'Motivo', 'Início.1', 'FIm.1', 'Motivo.1', ...
    Retorna uma lista ordenada: [(col_ini, col_fim, col_mot, tipo), ...]
    onde tipo é 'Outros' para os 3 primeiros blocos e 'Curso' do 4º em diante.
    """
    triplets = []

    for col in df.columns:
        if not col.startswith("Início"):
            continue

        # Sufixo: "", ".1", ".2", ...
        parts = col.split(".", 1)
        if len(parts) == 1:
            sufixo = ""
        else:
            sufixo = f".{parts[1]}"

        col_ini = col
        col_fim = f"FIm{sufixo}"
        col_mot = f"Motivo{sufixo}"

        if col_fim in df.columns and col_mot in df.columns:
            ordem = df.columns.get_loc(col_ini)
            triplets.append((ordem, col_ini, col_fim, col_mot))

    # Ordena pela posição da coluna
    triplets.sort(key=lambda x: x[0])

    resultado = []
    for idx, (_, c_ini, c_fim, c_mot) in enumerate(triplets):
        tipo = "Outros" if idx < 3 else "Curso"   # 0,1,2 = Y–AL; 3+ = AN em diante (cursos)
        resultado.append((c_ini, c_fim, c_mot, tipo))

    return resultado


AUSENCIAS_TRIPLETS = descobrir_ausencias_triplets(df_raw)


# ============================================================
# 5. TRANSFORMAÇÃO EM EVENTOS (WIDE → LONG)
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
            "EqMan": eqman if pd.notna(eqman) and str(eqman) != "-" else "Não",
            "GVI": parse_bool(gvi),
            "IN": parse_bool(insp),
        }

        # --------- Bloco de Férias ----------
        for col_ini, col_fim in FERIAS_COLS:
            if col_ini not in df_raw.columns or col_fim not in df_raw.columns:
                continue

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

        # --------- Bloco de Outras Ausências + Cursos ----------
        for col_ini, col_fim, col_mot, tipo in AUSENCIAS_TRIPLETS:
            ini = pd.to_datetime(row.get(col_ini, pd.NaT), dayfirst=True, errors="coerce")
            fim = pd.to_datetime(row.get(col_fim, pd.NaT), dayfirst=True, errors="coerce")
            motivo_texto = str(row.get(col_mot, "")).strip()

            if pd.notna(ini) and pd.notna(fim):
                if fim < ini:
                    ini, fim = fim, ini
                dur = (fim - ini).days + 1
                if dur < 1 or dur > 365:
                    continue

                # Para ambos: se motivo vier vazio, vira OUTROS
                motivo_real = motivo_texto if motivo_texto and "nan" not in motivo_texto.lower() else "OUTROS"

                eventos.append({
                    **militar_info,
                    "Inicio": ini,
                    "Fim": fim,
                    "Duracao_dias": dur,
                    "Motivo": motivo_real,
                    "Tipo": tipo  # "Outros" ou "Curso"
                })

    df_eventos = pd.DataFrame(eventos)
    return df_eventos


df_eventos = construir_eventos(df_raw)


# ============================================================
# 6. EXPANSÃO POR DIA (PARA ANÁLISE MENSAL/DIÁRIA)
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
# 7. BARRA LATERAL (FILTROS)
# ============================================================

st.sidebar.header("🕹️ Centro de Controle")

data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

filtro_eqman = st.sidebar.checkbox("Apenas EqMan")
filtro_in = st.sidebar.checkbox("Apenas Inspetores Navais (IN)")
filtro_gvi = st.sidebar.checkbox("Apenas GVI/GP")

df_tripulacao_filtrada = df_raw.copy()

if filtro_eqman and "EqMan" in df_tripulacao_filtrada.columns:
    df_tripulacao_filtrada = df_tripulacao_filtrada[
        (df_tripulacao_filtrada["EqMan"].notna()) &
        (df_tripulacao_filtrada["EqMan"].astype(str) != "-")
    ]

if filtro_in and "IN" in df_tripulacao_filtrada.columns:
    df_tripulacao_filtrada = df_tripulacao_filtrada[
        df_tripulacao_filtrada["IN"].apply(parse_bool)
    ]

if filtro_gvi and "Gvi/GP" in df_tripulacao_filtrada.columns:
    df_tripulacao_filtrada = df_tripulacao_filtrada[
        df_tripulacao_filtrada["Gvi/GP"].apply(parse_bool)
    ]


# ============================================================
# 8. QUEM ESTÁ AUSENTE NA DATA DE REFERÊNCIA?
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
# 9. MÉTRICAS DE TOPO
# ============================================================

col1, col2, col3, col4 = st.columns(4)
col1.metric("Efetivo Total", total_efetivo)
col2.metric("A Bordo", total_presentes)
col3.metric("Ausentes", total_ausentes, delta_color="inverse")
col4.metric("Prontidão", f"{percentual:.1f}%")


# ============================================================
# 10. TABS PRINCIPAIS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 Situação Diária",
    "📅 Linha do Tempo (Gantt)",
    "📊 Estatísticas & Análises",
    "🏖️ Férias",
    "🛠 Log / Debug"
])

# ------------------------------------------------------------
# TAB 1 – SITUAÇÃO DIÁRIA
# ------------------------------------------------------------
with tab1:
    st.subheader(f"Ausentes em {hoje.strftime('%d/%m/%Y')}")

    if total_ausentes > 0:
        show_df = ausentes_hoje[["Posto", "Nome", "Motivo", "Tipo", "Fim"]].copy()
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

            # Gráfico de motivos – pizza (inclui Férias, Outros, Curso etc)
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
    st.subheader("Férias cadastradas")

    if df_eventos.empty:
        st.write("Sem dados de férias registrados.")
    else:
        df_ferias = df_eventos[df_eventos["Tipo"] == "Férias"].copy()

        if df_ferias.empty:
            st.info("Nenhuma férias cadastrada na planilha.")
        else:
            # ===== 1) TABELA COM TODAS AS FÉRIAS =====
            tabela_ferias = df_ferias[["Posto", "Nome", "Escala", "Inicio", "Fim", "Duracao_dias"]].copy()
            tabela_ferias["Início"] = tabela_ferias["Inicio"].dt.strftime("%d/%m/%Y")
            tabela_ferias["Término"] = tabela_ferias["Fim"].dt.strftime("%d/%m/%Y")
            tabela_ferias = tabela_ferias.drop(columns=["Inicio", "Fim"])
            tabela_ferias = tabela_ferias.rename(columns={"Duracao_dias": "Dias"})

            # Ordena por Nome e Início
            tabela_ferias = tabela_ferias.sort_values(by=["Nome", "Início"])

            st.markdown("### 📋 Todos os períodos de férias registrados")
            st.dataframe(tabela_ferias, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("Análises Específicas de Férias")

            # ===== 2) KPIs DE FÉRIAS =====
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


# ------------------------------------------------------------
# TAB 5 – LOG / DEBUG
# ------------------------------------------------------------
with tab5:
    st.subheader("Log / Debug")

    st.markdown("### 🔹 df_raw (dados brutos do Google Sheets)")
    st.write(f"Total de linhas em df_raw: **{len(df_raw)}**")
    st.write("Colunas disponíveis em df_raw:")
    st.write(list(df_raw.columns))

    st.write("Prévia de df_raw (primeiras 15 linhas):")
    st.dataframe(df_raw.head(15), use_container_width=True)

    st.markdown("---")
    st.markdown("### 🔹 Mapeamento de Ausências (Início/FIm/Motivo)")

    if AUSENCIAS_TRIPLETS:
        debug_rows = []
        for idx, (c_ini, c_fim, c_mot, tipo) in enumerate(AUSENCIAS_TRIPLETS, start=1):
            debug_rows.append(
                {"Bloco": idx, "Col_Inicio": c_ini, "Col_Fim": c_fim, "Col_Motivo": c_mot, "Tipo": tipo}
            )
        st.dataframe(pd.DataFrame(debug_rows), use_container_width=True)
    else:
        st.info("Nenhum trio Início/FIm/Motivo encontrado.")

    st.markdown("---")
    st.markdown("### 🔹 df_eventos (eventos gerados)")

    st.write(f"Total de eventos em df_eventos: **{len(df_eventos)}**")

    if not df_eventos.empty:
        df_evt_preview = df_eventos.copy()
        st.dataframe(df_evt_preview.head(30), use_container_width=True)
        st.write("Anos em Inicio:", df_eventos["Inicio"].dt.year.unique())
        st.write("Anos em Fim:", df_eventos["Fim"].dt.year.unique())
        st.write("Tipos registrados:", df_eventos["Tipo"].unique())
    else:
        st.info("df_eventos está vazio. Verifique se as colunas de datas estão corretamente preenchidas na planilha.")


# ============================================================
# 11. RODAPÉ
# ============================================================
st.markdown("<hr style='border-color:#1f2937; margin-top:2rem;'/>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center; color:#9ca3af; padding:0.5rem 0;'>"
    "Created by <strong>Klismann Freitas</strong>"
    "</div>",
    unsafe_allow_html=True
)
