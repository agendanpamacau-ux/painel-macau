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

APP_VERSION = "v1.9.0 - Correção de Colunas"

# --- CSS global / tema ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@600;700&display=swap');
    * { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .stApp { background: radial-gradient(circle at top left, #020617 0, #020617 40%, #000 100%); color: #e5e7eb; }
    h1, h2, h3, h4 { color: #e5e7eb !important; letter-spacing: 0.03em; }
    h1 { font-family: 'Raleway', sans-serif !important; font-weight: 700 !important; }
    div[data-testid="metric-container"] {
        background: rgba(15, 23, 42, 0.9);
        border-radius: 0.9rem;
        padding: 1rem;
        border: 1px solid #1f2937;
        box-shadow: 0 12px 30px rgba(0,0,0,0.45);
    }
    div[data-testid="metric-container"] > label { color: #9ca3af !important; font-size: 0.80rem; text-transform: uppercase; }
    .stDataFrame { background: #020617; border-radius: 0.75rem; padding: 0.5rem; }
    section[data-testid="stSidebar"] img { display: block; margin: 0.5rem auto; }
    .sidebar-title { text-align: center; font-weight: 600; margin: 0.3rem 0; }
    .sidebar-section { margin-top: 0.8rem; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; color: #9ca3af; }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("""<h1 style="margin-top:0.2rem; margin-bottom:0.2rem;">Navio-Patrulha Macau</h1>""", unsafe_allow_html=True)

# ============================================================
# 2. HELPERS E CONSTANTES DE COLUNAS
# ============================================================

HEADER_ROW = 2  # linha 3 na planilha

# LISTA DE COLUNAS QUE SABEMOS QUE ESTÃO VAZIAS NA PLANILHA
# O script vai verificar se elas sumiram e ajustar o índice.
COLUNAS_VAZIAS_ESPERADAS = ["H", "X", "AC", "AH", "AM", "AR", "AW", "IC"]

def parse_bool(value) -> bool:
    if pd.isna(value): return False
    s = str(value).strip().lower()
    return s in ("true", "1", "sim", "yes", "y", "x")

def col_letter_to_index(col_letter: str) -> int:
    """Converte letra (A, B... Z, AA...) para índice 0-based."""
    col_letter = col_letter.upper()
    result = 0
    for ch in col_letter:
        if not ch.isalpha(): break
        result = result * 26 + (ord(ch) - ord('A') + 1)
    return result - 1

def get_col_name_ajustado(df: pd.DataFrame, letter: str):
    """
    Tenta pegar o nome da coluna de forma inteligente.
    Se o DataFrame 'engoliu' as colunas vazias, recalculamos o índice.
    """
    indice_teorico = col_letter_to_index(letter)
    
    # Verifica quantas colunas vazias (que vêm ANTES desta letra) 
    # deveriam existir.
    desconto = 0
    colunas_presentes = len(df.columns)
    
    # Se o DF tem muito menos colunas do que o índice teórico (ex: IG é ~240),
    # é sinal que as vazias foram dropadas.
    # Vamos contar quantas vazias existem antes da nossa letra alvo.
    for vazia in COLUNAS_VAZIAS_ESPERADAS:
        idx_vazia = col_letter_to_index(vazia)
        if idx_vazia < indice_teorico:
            desconto += 1
            
    # TENTATIVA 1: Índice original (caso o Pandas tenha lido as colunas vazias como "Unnamed")
    if 0 <= indice_teorico < colunas_presentes:
        col_name = df.columns[indice_teorico]
        # Se a coluna não parece "Unnamed", pode ser a certa.
        # Mas se for "Unnamed", e a nossa letra alvo NÃO é uma das vazias, então está certo.
        pass

    # TENTATIVA 2: Índice Ajustado (Descontando as vazias que sumiram)
    indice_ajustado = indice_teorico - desconto
    
    # Heurística: Vamos usar o índice ajustado se o índice original estourar o tamanho
    # ou se o usuário explicitamente pediu essa lógica. 
    # Vamos testar o ajustado primeiro se o DF parecer "compacto".
    
    idx_final = indice_teorico
    
    # Se a coluna H (idx 7) sumiu, o item I (idx 8) virou idx 7.
    # Vamos verificar se a coluna no indice ajustado faz sentido? Difícil sem ver o conteúdo.
    # Vamos assumir o ajuste se o número total de colunas for menor que o esperado para IG.
    idx_IG = col_letter_to_index("IG")
    if colunas_presentes < idx_IG: 
        idx_final = indice_ajustado

    if 0 <= idx_final < colunas_presentes:
        return df.columns[idx_final]
    
    return None

# ============================================================
# 3. CARGA DE DADOS
# ============================================================

@st.cache_data(ttl=600, show_spinner="Carregando dados...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lê tudo a partir da linha de cabeçalho
    df = conn.read(worksheet="Afastamento 2026", header=HEADER_ROW, ttl="10m")
    
    # Remove linhas totalmente vazias de Nome
    if "Nome" in df.columns:
        df = df.dropna(subset=["Nome"])
    
    df = df.reset_index(drop=True)
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro de conexão. Verifique o secrets.toml. Detalhe: {e}")
    st.stop()

# ============================================================
# 3.1 MAPEAMENTO CORRIGIDO (FÉRIAS, OUTROS, CURSOS)
# ============================================================

# Lista de tuplas: (Coluna Inicio, Coluna Fim)
MAPA_FERIAS = [
    ("I", "J"),  # Período 1
    ("L", "M"),  # Período 2
    ("O", "P"),  # Período 3
]

FERIAS_COLS = []
for ini, fim in MAPA_FERIAS:
    c_ini = get_col_name_ajustado(df_raw, ini)
    c_fim = get_col_name_ajustado(df_raw, fim)
    if c_ini and c_fim:
        FERIAS_COLS.append((c_ini, c_fim))

# Lista de tuplas: (Inicio, Fim, Motivo/Curso, Categoria)
# Inclui os períodos "estranhos" (DH-EL, ID-IE)
MAPA_AUSENCIAS = [
    ("Y",  "Z",  "AB", "Outros"),  # Período 4
    ("AD", "AE", "AG", "Outros"),  # Período 5
    ("AI", "AJ", "AL", "Outros"),  # Período 6
    ("AN", "AO", "AQ", "Curso"),   # Período 7
    ("AS", "AT", "AV", "Curso"),   # Período 8
    ("DH", "EL", "GW", "Curso"),   # Período 9 (Salto grande de colunas)
    ("ID", "IE", "IG", "Curso"),   # Período 10
]

AUSENCIAS_TRIPLETS = []
for ini, fim, mot, cat in MAPA_AUSENCIAS:
    c_ini = get_col_name_ajustado(df_raw, ini)
    c_fim = get_col_name_ajustado(df_raw, fim)
    c_mot = get_col_name_ajustado(df_raw, mot)
    
    # Só adiciona se encontrou todas as colunas
    if c_ini and c_fim and c_mot:
        AUSENCIAS_TRIPLETS.append((c_ini, c_fim, c_mot, cat))

# ============================================================
# 4. TRANSFORMAÇÃO E EVENTOS
# ============================================================

@st.cache_data(ttl=600)
def construir_eventos(df: pd.DataFrame) -> pd.DataFrame:
    eventos = []
    
    # Identificar colunas fixas (A-G)
    # Se tiver deslocamento, o nome da coluna pode não ser "Nome" exato se tiver header duplicado
    # Vamos tentar achar pelo nome padrão primeiro
    col_posto = "Posto" if "Posto" in df.columns else df.columns[col_letter_to_index("B")]
    col_nome  = "Nome"  if "Nome"  in df.columns else df.columns[col_letter_to_index("C")]
    col_sv    = "Serviço" if "Serviço" in df.columns else get_col_name_ajustado(df, "D")
    col_eq    = "EqMan" if "EqMan" in df.columns else get_col_name_ajustado(df, "E")
    col_gvi   = "Gvi/GP" if "Gvi/GP" in df.columns else get_col_name_ajustado(df, "F")
    col_in    = "IN" if "IN" in df.columns else get_col_name_ajustado(df, "G")

    for _, row in df.iterrows():
        posto = row.get(col_posto, "")
        nome  = row.get(col_nome, "")
        
        militar_info = {
            "Posto": posto,
            "Nome": nome,
            "Escala": str(row.get(col_sv, "")),
            "EqMan": str(row.get(col_eq, "")) if pd.notna(row.get(col_eq)) else "Não",
            "GVI": parse_bool(row.get(col_gvi)),
            "IN": parse_bool(row.get(col_in)),
        }
        
        # Helper interno para processar datas
        def add_evento(ini_val, fim_val, motivo_str, tipo_evt):
            ini = pd.to_datetime(ini_val, dayfirst=True, errors="coerce")
            fim = pd.to_datetime(fim_val, dayfirst=True, errors="coerce")
            
            if pd.notna(ini) and pd.notna(fim):
                if fim < ini: ini, fim = fim, ini
                dur = (fim - ini).days + 1
                
                # Validação básica de ano (opcional, remove 1900 se for erro de excel)
                if ini.year < 2020 or dur > 365: return

                if motivo_str and str(motivo_str).lower() != "nan":
                    motivo_real = str(motivo_str).strip()
                else:
                    motivo_real = "CURSO" if tipo_evt == "Curso" else (tipo_evt if tipo_evt != "Outros" else "AUSÊNCIA")

                eventos.append({
                    **militar_info,
                    "Inicio": ini,
                    "Fim": fim,
                    "Duracao_dias": dur,
                    "Motivo": motivo_real,
                    "Tipo": tipo_evt
                })

        # FÉRIAS
        for c_i, c_f in FERIAS_COLS:
            add_evento(row.get(c_i), row.get(c_f), "FÉRIAS", "Férias")
            
        # OUTROS / CURSOS
        for c_i, c_f, c_m, tipo_base in AUSENCIAS_TRIPLETS:
            add_evento(row.get(c_i), row.get(c_f), row.get(c_m), tipo_base)
            
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

# ============================================================
# INTERFACE SIDEBAR E PÁGINAS (Resumo)
# ============================================================
st.sidebar.image("logo_npamacau.png", width=140)
st.sidebar.markdown("<div class='sidebar-title'>Parâmetros</div>", unsafe_allow_html=True)

# DATA PADRÃO AJUSTADA PARA 2026 PARA TESTE
data_ref = st.sidebar.date_input("Data de Referência", datetime(2026, 1, 15))
hoje = pd.to_datetime(data_ref)

pagina = st.sidebar.radio("Menu", ["Resumo do Dia", "Lista de Ausentes", "Férias", "Cursos", "Debug Colunas"])

# FILTRAGEM DE AUSENTES HOJE
if not df_eventos.empty:
    ausentes_hoje = df_eventos[(df_eventos["Inicio"] <= hoje) & (df_eventos["Fim"] >= hoje)]
else:
    ausentes_hoje = pd.DataFrame()

# ------------------------------------------------------------
# PÁGINA: DEBUG COLUNAS (Para você verificar o mapeamento)
# ------------------------------------------------------------
if pagina == "Debug Colunas":
    st.title("Diagnóstico de Colunas")
    st.info("Verifique abaixo se o script está 'lendo' a coluna certa da planilha.")
    
    st.write(f"Total de colunas no DataFrame carregado: **{len(df_raw.columns)}**")
    
    st.markdown("### Teste de Mapeamento")
    
    debug_data = []
    # Testar algumas chaves
    testes = [
        ("I", "Início Férias 1"),
        ("J", "Fim Férias 1"),
        ("Y", "Início Período 4"),
        ("DH", "Início Período 9 (Longe)"),
        ("EL", "Fim Período 9 (Longe)")
    ]
    
    for letra, desc in testes:
        col_name = get_col_name_ajustado(df_raw, letra)
        # Pegar valores de exemplo (primeiros 3 não nulos)
        exemplo = ""
        if col_name and col_name in df_raw.columns:
            vals = df_raw[col_name].dropna().head(3).tolist()
            exemplo = str(vals)
        
        debug_data.append({
            "Letra Excel": letra,
            "Descrição": desc,
            "Nome no DataFrame (Lido)": col_name,
            "Amostra de dados": exemplo
        })
        
    st.table(pd.DataFrame(debug_data))
    
    st.markdown("---")
    st.write("### Primeiras 5 linhas do DF Bruto")
    st.dataframe(df_raw.head())

# ------------------------------------------------------------
# PÁGINA: RESUMO DO DIA
# ------------------------------------------------------------
elif pagina == "Resumo do Dia":
    st.title(f"Situação em {hoje.strftime('%d/%m/%Y')}")
    
    col1, col2 = st.columns(2)
    total_efetivo = len(df_raw)
    qtd_ausentes = ausentes_hoje["Nome"].nunique() if not ausentes_hoje.empty else 0
    qtd_presentes = total_efetivo - qtd_ausentes
    
    col1.metric("Presentes", qtd_presentes)
    col2.metric("Ausentes", qtd_ausentes, delta_color="inverse")
    
    st.markdown("### Quem está fora?")
    if not ausentes_hoje.empty:
        st.dataframe(
            ausentes_hoje[["Posto", "Nome", "Motivo", "Tipo", "Fim"]]
            .rename(columns={"Fim": "Retorno Previsto"}),
            use_container_width=True, hide_index=True
        )
    else:
        st.success("Todo o efetivo a bordo!")

# ------------------------------------------------------------
# PÁGINA: LISTA DE AUSENTES (Completa)
# ------------------------------------------------------------
elif pagina == "Lista de Ausentes":
    st.title("Lista Detalhada de Ausências")
    st.dataframe(ausentes_hoje, use_container_width=True)

# ------------------------------------------------------------
# PÁGINA: FÉRIAS
# ------------------------------------------------------------
elif pagina == "Férias":
    st.title("Controle de Férias")
    df_f = df_eventos[df_eventos["Tipo"] == "Férias"]
    if df_f.empty:
        st.info("Nenhuma férias detectada.")
    else:
        st.dataframe(df_f[["Posto", "Nome", "Inicio", "Fim", "Duracao_dias"]], use_container_width=True)

# ------------------------------------------------------------
# PÁGINA: CURSOS
# ------------------------------------------------------------
elif pagina == "Cursos":
    st.title("Controle de Cursos")
    df_c = df_eventos[df_eventos["Tipo"] == "Curso"]
    if df_c.empty:
        st.info("Nenhum curso detectado.")
    else:
        st.dataframe(df_c[["Posto", "Nome", "Motivo", "Inicio", "Fim"]], use_container_width=True)

st.markdown("<hr/><div style='text-align:center; color:gray'>Versão corrigida com mapeamento de colunas vazias</div>", unsafe_allow_html=True)
