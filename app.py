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

# 🔺 Versão do app – incremento a cada alteração de script
APP_VERSION = "v2.4.0"

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

    /* Tabs - estilo minimalista, sem efeito "vidro" nem retângulo */
    button[data-baseweb="tab"] {
        font-weight: 600;
        border-radius: 0 !important;
        padding: 0.4rem 1rem !important;
        margin-right: 0.3rem;
        border: none;
        background: transparent;
        color: #9ca3af;
    }
    button[data-baseweb="tab"]:hover {
        background: transparent;
        color: #e5e7eb;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: transparent;
        color: #e5e7eb;
        box-shadow: none;
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

# Cabeçalho: logo + título lado a lado
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image("logo_npamacau.png", width=80)
with col_title:
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

# Férias: colunas sem acento (como o Pandas costuma ler)
FERIAS_COLS = [
    ("Inicio",   "Fim"),    # Período 1
    ("Inicio.1", "Fim.1"),  # Período 2
    ("Inicio.2", "Fim.2"),  # Período 3
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
# 4. DESCOBRIR DINAMICAMENTE AS AUSÊNCIAS (INÍCIO/FIM/MOTIVO/CURSO)
# ============================================================

def descobrir_ausencias_triplets(df: pd.DataFrame):
    """
    Busca todas as colunas do tipo:
    'Início', 'FIm', e motivo (Motivo ou Curso).
    Retorna lista: [(col_ini, col_fim, col_mot, tipo_base), ...]
    onde tipo_base = 'Outros' para os 3 primeiros blocos e 'Curso' do 4º em diante.
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

        # Motivo pode ser "Motivo", "Curso" etc com mesmo sufixo
        candidatos_motivo = [
            f"Motivo{sufixo}",
            f"Curso{sufixo}",
            f"Motivo Curso{sufixo}"
        ]
        col_mot = None
        for c in candidatos_motivo:
            if c in df.columns:
                col_mot = c
                break

        if col_fim in df.columns and col_mot:
            ordem = df.columns.get_loc(col_ini)
            triplets.append((ordem, col_ini, col_fim, col_mot))

    # Ordena pela posição da coluna
    triplets.sort(key=lambda x: x[0])

    resultado = []
    for idx, (_, c_ini, c_fim, c_mot) in enumerate(triplets):
        tipo_base = "Outros" if idx < 3 else "Curso"   # 0,1,2 => Y–AL ; 3+ => AN em diante (cursos)
        resultado.append((c_ini, c_fim, c_mot, tipo_base))

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

        # --------- BLOCO DE FÉRIAS ----------
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

                # Decide TIPO FINAL (Curso ou Outros)
                tipo_final = tipo_base
                if motivo_texto and "curso" in motivo_texto.lower():
                    tipo_final = "Curso"

                # Decide MOTIVO REAL
                if tipo_final == "Curso":
                    if motivo_texto and "nan" not in motivo_texto.lower():
                        motivo_real = motivo_texto  # nome do curso
                    else:
                        motivo_real = "CURSO (não especificado)"
                else:
                    motivo_real = (
                        motivo_texto
                        if motivo_texto and "nan" not in motivo_texto.lower()
                        else "OUTROS"
                    )

                eventos.append({
                    **militar_info,
                    "Inicio": ini,
                    "Fim": fim,
                    "Duracao_dias": dur,
                    "Motivo": motivo_real,
                    "Tipo": tipo_final    # "Curso" ou "Outros"
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
# 7. FUNÇÕES DE FILTRO
# ============================================================

def filtrar_tripulacao(df: pd.DataFrame, apenas_eqman: bool, apenas_in: bool, apenas_gvi: bool) -> pd.DataFrame:
    res = df.copy()
    if apenas_eqman and "EqMan" in res.columns:
        res = res[(res["EqMan"].notna()) & (res["EqMan"].astype(str) != "-")]
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
# 8. DATA DE REFERÊNCIA (GLOBAL)
# ============================================================

st.sidebar.header("Parâmetros")
data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)


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
# 11. LEITURA DO % DE FÉRIAS (CÉLULA V2 via cabeçalho %DG)
# ============================================================

@st.cache_data(ttl=600)
def load_percent_ferias_v2():
    """
    Lê o valor da célula V2 da planilha Afastamento 2026 usando o cabeçalho "%DG".
    Faz:
      - lê a planilha com header=None;
      - procura na linha HEADER_ROW (2) a coluna cujo valor é "%DG";
      - lê a linha 1 (que é a linha 2 da planilha) nessa coluna.
    """
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_v = conn.read(
            worksheet="Afastamento 2026",
            header=None,
            ttl="10m"
        )

        header_row_idx = HEADER_ROW  # 2
        col_idx = None
        for j in range(df_v.shape[1]):
            val = df_v.iloc[header_row_idx, j]
            if str(val).strip() == "%DG":
                col_idx = j
                break

        if col_idx is None:
            return None

        valor = df_v.iloc[1, col_idx]  # linha 2 (index 1), mesma coluna

        if pd.isna(valor):
            return None

        s = str(valor).strip()
        if s.endswith("%"):
            s = s[:-1].strip()
        s = s.replace(",", ".")
        numero = float(s)

        if numero > 1:
            numero = numero / 100.0

        numero = max(0.0, min(1.0, numero))
        return numero

    except Exception:
        return None


# ============================================================
# 12. TABS PRINCIPAIS
# ============================================================

tab_presentes, tab_ausentes, tab_gantt, tab_stats, tab_ferias, tab_cursos, tab_log = st.tabs([
    "Presentes",
    "Ausentes",
    "Linha do Tempo (Gantt)",
    "Estatísticas & Análises",
    "Férias",
    "Cursos",
    "Log / Debug"
])

# ------------------------------------------------------------
# TAB 1 – PRESENTES
# ------------------------------------------------------------
with tab_presentes:
    st.subheader(f"Presentes a bordo em {hoje.strftime('%d/%m/%Y')}")

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

    st.markdown(f"Total de presentes (visão filtrada): **{len(df_presentes)}**")

    if df_presentes.empty:
        st.info("Nenhum militar presente para os filtros atuais.")
    else:
        tabela = df_presentes[["Posto", "Nome", "Serviço", "EqMan", "Gvi/GP", "IN"]].copy()
        tabela = tabela.rename(columns={"Gvi/GP": "GVI/GP"})

        # GVI/GP e IN como SIM / NÃO
        if "GVI/GP" in tabela.columns:
            tabela["GVI/GP"] = tabela["GVI/GP"].apply(lambda v: "SIM" if parse_bool(v) else "NÃO")
        if "IN" in tabela.columns:
            tabela["IN"] = tabela["IN"].apply(lambda v: "SIM" if parse_bool(v) else "NÃO")

        st.dataframe(tabela, use_container_width=True, hide_index=True)


# ------------------------------------------------------------
# TAB 2 – AUSENTES
# ------------------------------------------------------------
with tab_ausentes:
    st.subheader(f"Ausentes em {hoje.strftime('%d/%m/%Y')}")

    col_f1, col_f2, col_f3 = st.columns(3)
    apenas_eqman = col_f1.checkbox("Apenas EqMan", key="aus_eqman")
    apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="aus_in")
    apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="aus_gvi")

    if df_eventos.empty:
        st.info("Sem eventos de ausência registrados.")
    else:
        ausentes_hoje = df_eventos[
            (df_eventos["Inicio"] <= hoje) &
            (df_eventos["Fim"] >= hoje)
        ]
        ausentes_hoje = filtrar_eventos(ausentes_hoje, apenas_eqman, apenas_in, apenas_gvi)

        if ausentes_hoje.empty:
            st.success("Todo o efetivo está a bordo para os filtros atuais.")
        else:
            show_df = ausentes_hoje[["Posto", "Nome", "Motivo", "Tipo", "EqMan", "Fim"]].copy()
            show_df["Retorno"] = show_df["Fim"].dt.strftime("%d/%m/%Y")
            show_df = show_df.drop(columns=["Fim"])
            st.dataframe(show_df.drop(columns=["EqMan"]), use_container_width=True, hide_index=True)

            # Alertas EqMan
            eqman_fora = ausentes_hoje[ausentes_hoje["EqMan"] != "Não"]
            if not eqman_fora.empty:
                lista_eqman = sorted(
                    {f"{row['Posto']} {row['Nome']} ({row['EqMan']})" for _, row in eqman_fora.iterrows()}
                )
                st.error(
                    "⚠️ Atenção! EqMan com desfalque: " +
                    "; ".join(lista_eqman)
                )

            # Alertas GVI/GP
            gvi_fora = ausentes_hoje[ausentes_hoje["GVI"] == True]
            if not gvi_fora.empty:
                lista_gvi = sorted(
                    {f"{row['Posto']} {row['Nome']}" for _, row in gvi_fora.iterrows()}
                )
                st.warning(
                    "🚨 GVI/GP com desfalque: " +
                    "; ".join(lista_gvi)
                )


# ------------------------------------------------------------
# TAB 3 – LINHA DO TEMPO (GANTT)
# ------------------------------------------------------------
with tab_gantt:
    st.subheader("Planejamento Anual de Ausências")

    col_f1, col_f2, col_f3 = st.columns(3)
    apenas_eqman = col_f1.checkbox("Apenas EqMan", key="gantt_eqman")
    apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="gantt_in")
    apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="gantt_gvi")

    if df_eventos.empty:
        st.info("Planilha parece não ter datas preenchidas.")
    else:
        df_gantt = filtrar_eventos(df_eventos, apenas_eqman, apenas_in, apenas_gvi)

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
# TAB 4 – ESTATÍSTICAS & ANÁLISES
# ------------------------------------------------------------
with tab_stats:
    st.subheader("Visão Analítica de Ausências")

    col_f1, col_f2, col_f3 = st.columns(3)
    apenas_eqman = col_f1.checkbox("Apenas EqMan", key="stats_eqman")
    apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="stats_in")
    apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="stats_gvi")

    if df_eventos.empty:
        st.write("Sem dados suficientes para estatísticas.")
    else:
        df_evt = filtrar_eventos(df_eventos, apenas_eqman, apenas_in, apenas_gvi)

        if df_evt.empty:
            st.info("Nenhum evento para os filtros selecionados.")
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

                df_dias_filtrado = filtrar_dias(df_dias, apenas_eqman, apenas_in, apenas_gvi)

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
                    fig_mensal.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(15,23,42,0.8)",
                    )
                    st.plotly_chart(fig_mensal, use_container_width=True)
                else:
                    st.info("Sem dados diários para análise mensal com os filtros atuais.")


# ------------------------------------------------------------
# TAB 5 – FÉRIAS
# ------------------------------------------------------------
with tab_ferias:
    st.subheader("Férias cadastradas")

    col_f1, col_f2, col_f3 = st.columns(3)
    apenas_eqman = col_f1.checkbox("Apenas EqMan", key="fer_eqman")
    apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="fer_in")
    apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="fer_gvi")

    if df_eventos.empty:
        st.write("Sem dados de férias registrados.")
    else:
        df_ferias = df_eventos[df_eventos["Tipo"] == "Férias"].copy()
        df_ferias = filtrar_eventos(df_ferias, apenas_eqman, apenas_in, apenas_gvi)

        if df_ferias.empty:
            st.info("Nenhuma férias cadastrada na visão atual.")
        else:
            # 1) Tabela com todas as férias
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

            # 1 - Férias por escala
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

            # 2 - Férias por mês
            if not df_dias.empty:
                df_dias_ferias = df_dias[df_dias["Tipo"] == "Férias"].copy()
                df_dias_ferias = filtrar_dias(df_dias_ferias, apenas_eqman, apenas_in, apenas_gvi)

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
                    col_fx2.info("Sem dados diários suficientes para calcular férias por mês com os filtros atuais.")
            else:
                col_fx2.info("Sem expansão diária para análise mensal.")

            # 3 - Pizza com % de férias já gozadas (V2)
            st.markdown("---")
            st.subheader("Percentual de férias já gozadas (V2)")

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
                    title="Percentual médio de férias gozadas pela tripulação (V2)",
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
# TAB 6 – CURSOS
# ------------------------------------------------------------
with tab_cursos:
    st.subheader("Análises de Cursos")

    col_f1, col_f2, col_f3 = st.columns(3)
    apenas_eqman = col_f1.checkbox("Apenas EqMan", key="cur_eqman")
    apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="cur_in")
    apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="cur_gvi")

    if df_eventos.empty:
        st.write("Sem dados de cursos registrados.")
    else:
        df_cursos = df_eventos[df_eventos["Tipo"] == "Curso"].copy()
        df_cursos = filtrar_eventos(df_cursos, apenas_eqman, apenas_in, apenas_gvi)

        if df_cursos.empty:
            st.info("Nenhum curso cadastrado na visão atual.")
        else:
            # Realizados x em andamento/futuros
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
                    df_dias_cursos = filtrar_dias(df_dias_cursos, apenas_eqman, apenas_in, apenas_gvi)

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
                        col_g2.info("Sem dados diários suficientes para análise mensal de cursos com os filtros atuais.")
                else:
                    col_g2.info("Sem expansão diária para análise mensal de cursos.")


# ------------------------------------------------------------
# TAB 7 – LOG / DEBUG
# ------------------------------------------------------------
with tab_log:
    st.subheader("Log / Debug")

    st.markdown("### df_raw (dados brutos do Google Sheets)")
    st.write(f"Total de linhas em df_raw: **{len(df_raw)}**")
    st.write("Colunas disponíveis em df_raw:")
    st.write(list(df_raw.columns))

    st.write("Prévia de df_raw (primeiras 15 linhas):")
    st.dataframe(df_raw.head(15), use_container_width=True)

    st.markdown("---")
    st.markdown("### df_eventos (eventos gerados)")

    st.write(f"Total de eventos em df_eventos: **{len(df_eventos)}**")

    if not df_eventos.empty:
        st.dataframe(df_eventos.head(40), use_container_width=True)
        st.write("Anos em Inicio:", df_eventos["Inicio"].dt.year.unique())
        st.write("Anos em Fim:", df_eventos["Fim"].dt.year.unique())
        st.write("Tipos registrados:", df_eventos["Tipo"].unique())
    else:
        st.info("df_eventos está vazio. Verifique se as colunas de datas estão corretamente preenchidas na planilha.")


# ============================================================
# 13. RODAPÉ
# ============================================================
st.markdown("<hr style='border-color:#1f2937; margin-top:2rem;'/>", unsafe_allow_html=True)
st.markdown(
    f"<div style='text-align:center; color:#9ca3af; padding:0.5rem 0;'>"
    f"Created by <strong>Klismann Freitas</strong> · Versão {APP_VERSION}"
    f"</div>",
    unsafe_allow_html=True
)
