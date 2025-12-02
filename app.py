import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ============================================================
# VERSÃO DO SCRIPT
# ============================================================
SCRIPT_VERSION = "v0.4.0"

# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Navio-Patrulha Macau",
    layout="wide",
    page_icon="logo_npamacau.png"
)

# --- CSS global / tema minimalista claro ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

    * {
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .stApp {
        background: #f3f4f6;
        color: #111827;
    }

    h1, h2, h3, h4 {
        color: #111827 !important;
        letter-spacing: 0.02em;
    }

    h1 {
        font-family: 'Poppins', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-weight: 600 !important;
    }

    /* Cards de métricas */
    div[data-testid="metric-container"] {
        background: #ffffff;
        border-radius: 0.9rem;
        padding: 1rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
    }

    div[data-testid="metric-container"] > label {
        color: #6b7280 !important;
        font-size: 0.80rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .stDataFrame {
        background: #ffffff;
        border-radius: 0.75rem;
        padding: 0.5rem;
    }

    /* NAV LATERAL (radio estilizado como texto) */
    div.nav-container > div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
    }

    /* Esconde o "círculo" do radio (vários alvos possíveis) */
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

    /* Estilo base do texto da aba (segundo filho) */
    div.nav-container div[role="radio"] > div:nth-child(2) {
        color: #6b7280;
        font-weight: 500;
        font-size: 0.92rem;
        cursor: pointer;
        padding: 0.1rem 0;
    }

    /* Hover da aba */
    div.nav-container div[role="radio"]:hover > div:nth-child(2) {
        color: #111827;
    }

    /* Aba selecionada: sublinhado minimalista */
    div.nav-container div[role="radio"][aria-checked="true"] > div:nth-child(2) {
        color: #111827;
        text-decoration: underline;
        text-decoration-thickness: 2px;
        text-underline-offset: 0.25rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Cabeçalho: logo + título lado a lado
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image("logo_npamacau.png", width=70)
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
# 4. DESCOBRIR BLOCOS DE DATAS (GENÉRICO, RESPEITANDO JANELA)
# ============================================================

def descobrir_blocos_datas(df: pd.DataFrame):
    """
    Identifica blocos de ausência com base na estrutura:

      Início / Inicio  → Fim / FIm → [D] → [Motivo ou Curso (próximas 3 colunas)]

    Regras:
      - Procura 'Fim' / 'FIm' logo à direita.
      - Depois procura 'Motivo' ou 'Curso' apenas nas PRÓXIMAS 3 colunas.
      - Se não achar motivo/curso próximo ⇒ Tipo_base = "Férias"
      - Se achar 'Motivo' ⇒ Tipo_base = "Outros"
      - Se achar 'Curso' ⇒ Tipo_base = "Curso"

    Retorna lista de tuplas:
      (col_inicio, col_fim, col_motivo_ou_curso_ou_None, tipo_base)
    """
    cols = list(df.columns)
    blocos = []

    for i, nome_col in enumerate(cols):
        n = str(nome_col)

        # Aceita "Início" (com acento) e "Inicio" (sem acento)
        if not (n.startswith("Início") or n.startswith("Inicio")):
            continue

        # 1) Encontrar Fim ou FIm mais próximo à direita
        j = None
        for idx2 in range(i + 1, len(cols)):
            n2 = str(cols[idx2])
            if n2.startswith("Fim") or n2.startswith("FIm"):
                j = idx2
                break
        if j is None:
            continue

        # 2) Procurar Motivo ou Curso apenas nas próximas 3 colunas (janela curta)
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

            if pd.isna(ini) or pd.isna(fim):
                continue

            # Garante ini <= fim
            if fim < ini:
                ini, fim = fim, ini

            dur = (fim - ini).days + 1
            if dur < 1 or dur > 365*2:
                continue

            # Decide motivo e tipo
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

            # Motivo agrupado (para gráficos / linha do tempo / ausentes)
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
                "Motivo": motivo_real,          # nome completo (curso etc)
                "MotivoAgrupado": motivo_agr,   # Férias / Curso / Disp Médica / etc
                "Tipo": tipo_final              # Férias / Curso / Outros
            })

    df_eventos = pd.DataFrame(eventos)
    return df_eventos

df_eventos = construir_eventos(df_raw, BLOCOS_DATAS)


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
                "MotivoAgrupado": ev["MotivoAgrupado"],
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
# 8. PARÂMETROS (SIDEBAR) + NAVEGAÇÃO LATERAL
# ============================================================

st.sidebar.header("Parâmetros")
data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

st.sidebar.markdown("#### Navegação")
with st.sidebar.container():
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    pagina = st.radio(
        label="Seções",
        options=[
            "Presentes",
            "Ausentes",
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
col2.metric("A Bordo (global)", total_presentes_global)
col3.metric("Ausentes (global)", total_ausentes_global, delta_color="inverse")
col4.metric("Prontidão (global)", f"{percentual_global:.1f}%")


# ============================================================
# 10. FUNÇÃO PARA GRÁFICO DE PIZZA MODERNO
# ============================================================

def grafico_pizza_motivos(df_motivos_dias, titulo):
    fig = px.pie(
        df_motivos_dias,
        names="MotivoAgrupado",
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
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(
            family="'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            color="#111827"
        )
    )
    return fig


# ============================================================
# 11. CONTEÚDO PRINCIPAL (PÁGINAS)
# ============================================================

# --------------------------------------------------------
# PÁGINA – PRESENTES
# --------------------------------------------------------
if pagina == "Presentes":
    st.subheader(f"Presentes a bordo em {hoje.strftime('%d/%m/%Y')}")

    content_container = st.container()
    filters_container = st.container()

    with content_container:
        # Vamos calcular primeiro, para depois mostrar filtros abaixo da tabela
        # (como você pediu, mas mantendo a lógica clara)
        col_info = st.empty()

        # Filtros (render depois da tabela, mas precisamos deles antes)
    with filters_container:
        st.markdown("##### Filtros")
        col_f1, col_f2, col_f3 = st.columns(3)
        apenas_eqman = col_f1.checkbox("Apenas EqMan", key="pres_eqman")
        apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="pres_in")
        apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="pres_gvi")

    # Agora sim, conteúdo com base nos filtros
    with content_container:
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
            # Converter GVI/GP e IN para SIM / Não
            tabela["GVI/GP"] = tabela["Gvi/GP"].apply(lambda v: "Sim" if parse_bool(v) else "Não")
            tabela["IN"] = tabela["IN"].apply(lambda v: "Sim" if parse_bool(v) else "Não")
            tabela = tabela.drop(columns=["Gvi/GP"])
            st.dataframe(tabela, use_container_width=True, hide_index=True)

        # Gráfico de barra para Prontidão (aba Presentes, visão filtrada)
        st.markdown("##### Prontidão (visão filtrada)")
        total_filtrado = len(df_trip)
        if total_filtrado > 0:
            presentes_filtrado = len(df_presentes)
            pront_pct = presentes_filtrado / total_filtrado * 100
            df_pr = pd.DataFrame({
                "Indicador": ["Prontidão"],
                "Percentual": [pront_pct]
            })
            fig_pr = px.bar(
                df_pr,
                x="Percentual",
                y="Indicador",
                orientation="h",
                range_x=[0, 100],
                text="Percentual",
            )
            fig_pr.update_traces(
                texttemplate="%{x:.1f}%",
                textposition="inside"
            )
            fig_pr.update_layout(
                height=140,
                margin=dict(l=60, r=20, t=30, b=20),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#ffffff",
                xaxis=dict(title="%"),
                yaxis=dict(title=""),
                font=dict(color="#111827")
            )
            st.plotly_chart(fig_pr, use_container_width=True)
        else:
            st.info("Não há efetivo na visão atual para calcular a prontidão.")


# --------------------------------------------------------
# PÁGINA – AUSENTES
# --------------------------------------------------------
elif pagina == "Ausentes":
    st.subheader(f"Ausentes em {hoje.strftime('%d/%m/%Y')}")

    content_container = st.container()
    filters_container = st.container()

    with filters_container:
        st.markdown("##### Filtros")
        col_f1, col_f2, col_f3 = st.columns(3)
        apenas_eqman = col_f1.checkbox("Apenas EqMan", key="aus_eqman")
        apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="aus_in")
        apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="aus_gvi")

    with content_container:
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
                # Motivo exibido: "Férias" / "Curso" / Motivo normal (Disp Médica, Luto, etc)
                temp = ausentes_hoje.copy()
                temp["MotivoExib"] = temp.apply(
                    lambda r: "Férias" if r["Tipo"] == "Férias"
                    else ("Curso" if r["Tipo"] == "Curso" else str(r["Motivo"])),
                    axis=1
                )
                show_df = temp[["Posto", "Nome", "MotivoExib", "Fim"]].copy()
                show_df["Retorno"] = show_df["Fim"].dt.strftime("%d/%m/%Y")
                show_df = show_df.drop(columns=["Fim"])
                show_df = show_df.rename(columns={"MotivoExib": "Motivo"})

                st.dataframe(show_df, use_container_width=True, hide_index=True)

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


# --------------------------------------------------------
# PÁGINA – LINHA DO TEMPO
# --------------------------------------------------------
elif pagina == "Linha do Tempo":
    st.subheader("Planejamento Anual de Ausências")

    content_container = st.container()
    filters_container = st.container()

    with filters_container:
        st.markdown("##### Filtros")
        col_f1, col_f2, col_f3 = st.columns(3)
        apenas_eqman = col_f1.checkbox("Apenas EqMan", key="gantt_eqman")
        apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="gantt_in")
        apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="gantt_gvi")

    with content_container:
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
                    color="MotivoAgrupado",   # legenda: Férias / Curso / Disp Médica / etc
                    hover_data=["Posto", "Escala", "EqMan", "GVI", "IN", "MotivoAgrupado"],
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
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    font=dict(color="#111827")
                )
                st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------------
# PÁGINA – ESTATÍSTICAS & ANÁLISES
# --------------------------------------------------------
elif pagina == "Estatísticas & Análises":
    st.subheader("Visão Analítica de Ausências")

    content_container = st.container()
    filters_container = st.container()

    with filters_container:
        st.markdown("##### Filtros")
        col_f1, col_f2, col_f3 = st.columns(3)
        apenas_eqman = col_f1.checkbox("Apenas EqMan", key="stats_eqman")
        apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="stats_in")
        apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="stats_gvi")

    with content_container:
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

                df_ferias_evt = df_evt[df_evt["Tipo"] == "Férias"].copy()
                media_dias_ferias = (
                    df_ferias_evt.groupby("Nome")["Duracao_dias"].sum().mean()
                    if not df_ferias_evt.empty else 0
                )

                col_a1.metric("Dias de ausência (total)", int(total_dias_ausencia))
                col_a2.metric("Média de dias de ausência por militar", f"{media_dias_por_militar:.1f}")
                col_a3.metric("Média de dias de FÉRIAS por militar", f"{media_dias_ferias:.1f}")

                st.markdown("---")

                # Gráfico de motivos – donut moderno (usando MotivoAgrupado)
                df_motivos_dias = (
                    df_evt.groupby("MotivoAgrupado")["Duracao_dias"]
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
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    font=dict(color="#111827")
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
                            paper_bgcolor="#ffffff",
                            plot_bgcolor="#ffffff",
                            font=dict(color="#111827")
                        )
                        st.plotly_chart(fig_mensal, use_container_width=True)
                    else:
                        st.info("Sem dados diários para análise mensal com os filtros atuais.")


# --------------------------------------------------------
# PÁGINA – FÉRIAS
# --------------------------------------------------------
elif pagina == "Férias":
    st.subheader("Férias cadastradas")

    content_container = st.container()
    filters_container = st.container()

    with filters_container:
        st.markdown("##### Filtros")
        col_f1, col_f2, col_f3 = st.columns(3)
        apenas_eqman = col_f1.checkbox("Apenas EqMan", key="fer_eqman")
        apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="fer_in")
        apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="fer_gvi")

    with content_container:
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
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    font=dict(color="#111827")
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
                            paper_bgcolor="#ffffff",
                            plot_bgcolor="#ffffff",
                            font=dict(color="#111827")
                        )
                        col_fx2.plotly_chart(fig_mes_ferias, use_container_width=True)
                    else:
                        col_fx2.info("Sem dados diários suficientes para calcular férias por mês com os filtros atuais.")
                else:
                    col_fx2.info("Sem expansão diária para análise mensal.")

                st.markdown("---")
                st.subheader("% de férias gozadas (tripulação)")

                if "%DG" in df_raw.columns:
                    media_percentual = df_raw["%DG"].mean(skipna=True)
                    if pd.notna(media_percentual):
                        if media_percentual <= 1:
                            perc_gozado = media_percentual * 100
                        else:
                            perc_gozado = media_percentual
                        perc_nao = max(0.0, 100.0 - perc_gozado)

                        df_pizza_ferias = pd.DataFrame({
                            "Categoria": ["Gozado", "Não gozado"],
                            "Valor": [perc_gozado, perc_nao]
                        })

                        fig_pizza_ferias = px.pie(
                            df_pizza_ferias,
                            names="Categoria",
                            values="Valor",
                            hole=0.5
                        )
                        fig_pizza_ferias.update_traces(
                            textposition="inside",
                            textinfo="percent+label",
                            hovertemplate="<b>%{label}</b><br>%{value:.1f}%<extra></extra>"
                        )
                        fig_pizza_ferias.update_layout(
                            title="Distribuição de férias gozadas x não gozadas (média da tripulação)",
                            paper_bgcolor="#ffffff",
                            plot_bgcolor="#ffffff",
                            margin=dict(t=60, b=20, l=0, r=0),
                            font=dict(color="#111827")
                        )
                        st.plotly_chart(fig_pizza_ferias, use_container_width=True)
                    else:
                        st.info("Não foi possível calcular a média da coluna %DG.")
                else:
                    st.info("Coluna %DG não encontrada na planilha para cálculo do percentual de férias gozadas.")


# --------------------------------------------------------
# PÁGINA – CURSOS
# --------------------------------------------------------
elif pagina == "Cursos":
    st.subheader("Análises de Cursos")

    content_container = st.container()
    filters_container = st.container()

    with filters_container:
        st.markdown("##### Filtros")
        col_f1, col_f2, col_f3 = st.columns(3)
        apenas_eqman = col_f1.checkbox("Apenas EqMan", key="cur_eqman")
        apenas_in    = col_f2.checkbox("Apenas Inspetores Navais (IN)", key="cur_in")
        apenas_gvi   = col_f3.checkbox("Apenas GVI/GP", key="cur_gvi")

    with content_container:
        if df_eventos.empty:
            st.write("Sem dados de cursos registrados.")
        else:
            df_cursos = df_eventos[df_eventos["Tipo"] == "Curso"].copy()
            df_cursos = filtrar_eventos(df_cursos, apenas_eqman, apenas_in, apenas_gvi)

            if df_cursos.empty:
                st.info("Nenhum curso cadastrado na visão atual.")
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
                        paper_bgcolor="#ffffff",
                        plot_bgcolor="#ffffff",
                        font=dict(color="#111827")
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
                                paper_bgcolor="#ffffff",
                                plot_bgcolor="#ffffff",
                                font=dict(color="#111827")
                            )
                            col_g2.plotly_chart(fig_curso_mes, use_container_width=True)
                        else:
                            col_g2.info("Sem dados diários suficientes para análise mensal de cursos com os filtros atuais.")
                    else:
                        col_g2.info("Sem expansão diária para análise mensal de cursos.")


# --------------------------------------------------------
# PÁGINA – LOG / DEBUG
# --------------------------------------------------------
elif pagina == "Log / Debug":
    st.subheader("Log / Debug")

    st.markdown("### df_raw (dados brutos do Google Sheets)")
    st.write(f"Total de linhas em df_raw: **{len(df_raw)}**")
    st.write("Colunas disponíveis em df_raw:")
    st.write(list(df_raw.columns))

    st.write("Prévia de df_raw (primeiras 15 linhas):")
    st.dataframe(df_raw.head(15), use_container_width=True)

    st.markdown("---")
    st.markdown("### Blocos de datas detectados (Início/Inicio → Fim/FIm → [Motivo/Curso])")

    if BLOCOS_DATAS:
        debug_blocos = []
        for idx, (c_ini, c_fim, c_mot, tipo_base) in enumerate(BLOCOS_DATAS, start=1):
            debug_blocos.append({
                "Bloco": idx,
                "Col_Inicio": c_ini,
                "Col_Fim": c_fim,
                "Col_Motivo/Curso": c_mot,
                "Tipo_base": tipo_base
            })
        st.dataframe(pd.DataFrame(debug_blocos), use_container_width=True)
    else:
        st.info("Nenhum bloco de datas detectado.")

    st.markdown("---")
    st.markdown("### df_eventos (eventos gerados)")

    st.write(f"Total de eventos em df_eventos: **{len(df_eventos)}**")

    if not df_eventos.empty:
        st.dataframe(df_eventos.head(40), use_container_width=True)
        st.write("Anos em Inicio:", df_eventos["Inicio"].dt.year.unique())
        st.write("Anos em Fim:", df_eventos["Fim"].dt.year.unique())
        st.write("Tipos registrados:", df_eventos["Tipo"].unique())
        st.write("Motivos agrupados:", df_eventos["MotivoAgrupado"].unique())
    else:
        st.info("df_eventos está vazio. Verifique se as colunas de datas estão corretamente preenchidas na planilha.")


# ============================================================
# 12. RODAPÉ
# ============================================================
st.markdown("<hr style='border-color:#e5e7eb; margin-top:2rem;'/>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div style='text-align:center; color:#6b7280; padding:0.5rem 0; font-size:0.85rem;'>
        Created by <strong>Klismann Freitas</strong> • Versão do painel: <strong>{SCRIPT_VERSION}</strong>
    </div>
    """,
    unsafe_allow_html=True
)
