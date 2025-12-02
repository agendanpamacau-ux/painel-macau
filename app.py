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

APP_VERSION = "v1.14.0 - Detecção por Nome Exato"

# --- CSS global / tema ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@600;700&display=swap');

    * { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .stApp { background: radial-gradient(circle at top left, #020617 0, #020617 40%, #000 100%); color: #e5e7eb; }
    h1, h2, h3, h4 { color: #e5e7eb !important; }
    h1 { font-family: 'Raleway', sans-serif !important; font-weight: 700 !important; }
    div[data-testid="metric-container"] {
        background: rgba(15, 23, 42, 0.9);
        border-radius: 0.9rem;
        padding: 1rem;
        border: 1px solid #1f2937;
        box-shadow: 0 12px 30px rgba(0,0,0,0.45);
    }
    .stDataFrame { background: #020617; border-radius: 0.75rem; padding: 0.5rem; }
    
    /* Tabs estilo botão */
    button[data-baseweb="tab"] {
        border-radius: 999px !important;
        padding: 0.4rem 1rem !important;
        margin-right: 0.3rem; 
        background-color: transparent;
        border: 1px solid #1f2937;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: #1e293b;
        border-color: #38bdf8;
        color: #38bdf8;
    }
    </style>
    """,
    unsafe_allow_html=True
)

col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image("logo_npamacau.png", width=90)
with col_title:
    st.markdown("<h1>Navio-Patrulha Macau</h1>", unsafe_allow_html=True)

# ============================================================
# 2. CARGA DE DADOS
# ============================================================

HEADER_ROW = 2  # Linha 3 do Excel (Indice 2)

@st.cache_data(ttl=600, show_spinner="Carregando e processando cabeçalhos...")
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lê com cabeçalho normal. O Pandas vai renomear duplicatas para Inicio.1, Início.2, etc.
    df = conn.read(worksheet="Afastamento 2026", header=HEADER_ROW, ttl="10m")
    
    # Remove linhas vazias baseadas no Nome
    if "Nome" in df.columns:
        df = df.dropna(subset=["Nome"])
    
    df = df.reset_index(drop=True)
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# ============================================================
# 3. LÓGICA DE DETECÇÃO DINÂMICA (A CORREÇÃO)
# ============================================================

def descobrir_colunas(df):
    """
    Analisa os nomes das colunas carregadas pelo Pandas e encontra os pares.
    Baseado no seu cabeçalho:
    - Férias: "Inicio" (sem acento) e "Fim" (m minúsculo)
    - Ausências: "Início" (com acento) e "FIm" (I maiúsculo)
    """
    ferias_cols = []
    ausencias_triplets = [] # (Inicio, Fim, Motivo, Tipo)
    
    cols = df.columns.tolist()
    
    for col in cols:
        # 1. DETECTAR FÉRIAS (Inicio / Fim)
        if col.startswith("Inicio") and not col.startswith("Início"): 
            # É férias (sem acento)
            # Descobre o sufixo (ex: .1, .2)
            parts = col.split(".")
            sufixo = "." + parts[1] if len(parts) > 1 else ""
            
            par_fim = f"Fim{sufixo}"
            
            if par_fim in df.columns:
                ferias_cols.append((col, par_fim))

        # 2. DETECTAR AUSÊNCIAS (Início / FIm)
        elif col.startswith("Início"):
            # É ausência (com acento)
            parts = col.split(".")
            sufixo = "." + parts[1] if len(parts) > 1 else ""
            
            # SEU CABEÇALHO USA 'FIm' (I maiúsculo) PARA AUSÊNCIAS
            par_fim = f"FIm{sufixo}" 
            
            if par_fim in df.columns:
                # Tenta achar o motivo ou curso correspondente com o mesmo sufixo
                col_motivo = None
                tipo_detectado = "Outros" # Default
                
                # Lista de possíveis nomes para a coluna de motivo/curso
                candidatos = [
                    f"Motivo{sufixo}", 
                    f"Curso{sufixo}", 
                    f"Motivo Curso{sufixo}",
                    f"AB{sufixo}", # Caso extremo de leitura errada
                    f"AG{sufixo}"
                ]
                
                for cand in candidatos:
                    if cand in df.columns:
                        col_motivo = cand
                        # Se o nome da coluna tiver "Curso", classificamos como curso
                        if "Curso" in cand or "curso" in cand:
                            tipo_detectado = "Curso"
                        break
                
                # Se não achou motivo especifico pelo sufixo, tenta pela proximidade (índice)
                if not col_motivo:
                    idx_fim = df.columns.get_loc(par_fim)
                    # O motivo costuma ser a coluna logo após o 'D' (duração). Fim + 2.
                    if idx_fim + 2 < len(df.columns):
                        col_motivo = df.columns[idx_fim + 2]
                
                ausencias_triplets.append((col, par_fim, col_motivo, tipo_detectado))

    return ferias_cols, ausencias_triplets

# Executa a descoberta
FERIAS_DETECTADAS, AUSENCIAS_DETECTADAS = descobrir_colunas(df_raw)

# ============================================================
# 4. CONSTRUÇÃO DOS EVENTOS
# ============================================================

def parse_bool(value) -> bool:
    if pd.isna(value): return False
    return str(value).strip().lower() in ("true", "1", "sim", "yes", "y", "x")

@st.cache_data(ttl=600)
def processar_eventos(df, ferias_cols, ausencias_triplets):
    eventos = []
    
    for _, row in df.iterrows():
        # Dados do Militar
        nome = row.get("Nome")
        if pd.isna(nome) or str(nome).strip() == "": continue
        
        eq = row.get("EqMan", "")
        eq = str(eq) if pd.notna(eq) and str(eq) != "-" else "Não"
        
        militar = {
            "Posto": row.get("Posto", ""),
            "Nome": nome,
            "Escala": row.get("Serviço", ""),
            "EqMan": eq,
            "GVI": parse_bool(row.get("Gvi/GP")),
            "IN": parse_bool(row.get("IN"))
        }

        # Helper para adicionar
        def add(ini_val, fim_val, mot_val, tipo):
            ini = pd.to_datetime(ini_val, dayfirst=True, errors='coerce')
            fim = pd.to_datetime(fim_val, dayfirst=True, errors='coerce')
            
            if pd.notna(ini) and pd.notna(fim):
                if fim < ini: ini, fim = fim, ini
                dur = (fim - ini).days + 1
                if dur < 1 or dur > 365 or ini.year < 2020: return
                
                mot_txt = str(mot_val).strip() if pd.notna(mot_val) else ""
                if not mot_txt or mot_txt.lower() == "nan":
                    # Tenta inferir se é curso pelo Tipo base
                    if tipo == "Curso": real_mot = "CURSO"
                    else: real_mot = "AUSÊNCIA"
                else:
                    real_mot = mot_txt
                
                # Refinamento final do tipo
                final_type = "Curso" if ("curso" in real_mot.lower() or tipo == "Curso") else "Outros"
                if tipo == "Férias": final_type = "Férias"

                eventos.append({
                    **militar,
                    "Inicio": ini, "Fim": fim, "Duracao_dias": dur,
                    "Motivo": real_mot, "Tipo": final_type
                })

        # 1. Processar Férias
        for c_ini, c_fim in ferias_cols:
            add(row.get(c_ini), row.get(c_fim), "FÉRIAS", "Férias")
            
        # 2. Processar Ausências/Cursos
        for c_ini, c_fim, c_mot, tipo_base in ausencias_triplets:
            add(row.get(c_ini), row.get(c_fim), row.get(c_mot) if c_mot else None, tipo_base)
            
    return pd.DataFrame(eventos)

df_eventos = processar_eventos(df_raw, FERIAS_DETECTADAS, AUSENCIAS_DETECTADAS)

# ============================================================
# 5. EXPANSÃO POR DIA
# ============================================================
@st.cache_data(ttl=600)
def expandir(df_evt):
    if df_evt.empty: return pd.DataFrame()
    rows = []
    for _, e in df_evt.iterrows():
        for d in pd.date_range(e["Inicio"], e["Fim"]):
            rows.append({
                "Data": d, "Nome": e["Nome"], "Posto": e["Posto"],
                "Tipo": e["Tipo"], "Motivo": e["Motivo"],
                "EqMan": e["EqMan"], "IN": e["IN"], "GVI": e["GVI"]
            })
    return pd.DataFrame(rows)

df_dias = expandir(df_eventos)

# ============================================================
# 6. FILTROS E INTERFACE
# ============================================================

st.sidebar.header("Parâmetros")
data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

# Filtros Globais para aplicar nas abas
def aplicar_filtros(df, eq, nav, gvi):
    res = df.copy()
    if eq: res = res[res["EqMan"] != "Não"]
    if nav: res = res[res["IN"] == True]
    if gvi: res = res[res["GVI"] == True]
    return res

# Abas
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🟢 Presentes", "📋 Ausentes", "📅 Gantt", "📊 Stats", "🏖️ Férias", "🎓 Cursos", "🛠 Debug"
])

# MÉTRICAS GERAIS (Topo)
if not df_eventos.empty:
    aus_h = df_eventos[(df_eventos["Inicio"]<=hoje) & (df_eventos["Fim"]>=hoje)]
else: aus_h = pd.DataFrame()

total_efetivo = len(df_raw)
total_aus = aus_h["Nome"].nunique() if not aus_h.empty else 0
total_pres = total_efetivo - total_aus
prontidao = (total_pres/total_efetivo*100) if total_efetivo > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Efetivo", total_efetivo)
c2.metric("A Bordo", total_pres)
c3.metric("Ausentes", total_aus, delta_color="inverse")
c4.metric("Prontidão", f"{prontidao:.1f}%")

# --- TAB 1: PRESENTES ---
with tab1:
    st.subheader("Presentes")
    cf1, cf2, cf3 = st.columns(3)
    feq = cf1.checkbox("EqMan", key="p1")
    fin = cf2.checkbox("IN", key="p2")
    fgv = cf3.checkbox("GVI", key="p3")
    
    # 1. Base filtrada
    trip_filtrada = aplicar_filtros(df_raw, feq, fin, fgv)
    
    # 2. Ausentes filtrados
    aus_filtrados = aplicar_filtros(aus_h, feq, fin, fgv)
    nomes_fora = set(aus_filtrados["Nome"].unique()) if not aus_filtrados.empty else set()
    
    # 3. Presentes
    if "Nome" in trip_filtrada.columns:
        df_pres = trip_filtrada[~trip_filtrada["Nome"].isin(nomes_fora)].copy()
        
        # Selecionar colunas principais
        cols_show = ["Posto", "Nome", "Serviço", "EqMan", "Gvi/GP", "IN"]
        cols_show = [c for c in cols_show if c in df_pres.columns]
        
        # Formatar bools
        if "Gvi/GP" in df_pres.columns: df_pres["Gvi/GP"] = df_pres["Gvi/GP"].apply(lambda x: "SIM" if parse_bool(x) else "NÃO")
        if "IN" in df_pres.columns: df_pres["IN"] = df_pres["IN"].apply(lambda x: "SIM" if parse_bool(x) else "NÃO")
        
        st.dataframe(df_pres[cols_show], use_container_width=True, hide_index=True)
    else:
        st.error("Coluna 'Nome' não encontrada.")

# --- TAB 2: AUSENTES ---
with tab2:
    st.subheader("Ausentes")
    ck1, ck2, ck3 = st.columns(3)
    feq2 = ck1.checkbox("EqMan", key="a1")
    fin2 = ck2.checkbox("IN", key="a2")
    fgv2 = ck3.checkbox("GVI", key="a3")
    
    if not aus_h.empty:
        aus_filt = aplicar_filtros(aus_h, feq2, fin2, fgv2)
        if not aus_filt.empty:
            view = aus_filt[["Posto", "Nome", "Motivo", "Tipo", "Fim"]].copy()
            view["Retorno"] = view["Fim"].dt.strftime("%d/%m/%Y")
            st.dataframe(view.drop(columns=["Fim"]), use_container_width=True, hide_index=True)
            
            # Alertas
            if "EqMan" in aus_filt.columns:
                eqs = aus_filt[aus_filt["EqMan"]!="Não"]
                if not eqs.empty:
                    st.error(f"⚠️ EqMan Desfalcada: {', '.join(eqs['Nome'].unique())}")
        else:
            st.success("Todos a bordo (neste filtro).")
    else:
        st.success("Todos a bordo.")

# --- TAB 3: GANTT ---
with tab3:
    st.subheader("Linha do Tempo")
    if not df_eventos.empty:
        fig = px.timeline(df_eventos, x_start="Inicio", x_end="Fim", y="Nome", color="Tipo", title="Cronograma Geral")
        fig.update_yaxes(autorange="reversed")
        fig.add_vline(x=hoje, line_dash="dash", line_color="red")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 4: ESTATISTICAS ---
with tab4:
    if not df_eventos.empty:
        c1, c2 = st.columns(2)
        pie_df = df_eventos.groupby("Motivo")["Duracao_dias"].sum().reset_index()
        fig_pie = px.pie(pie_df, values="Duracao_dias", names="Motivo", title="Dias Totais por Motivo", hole=0.4)
        c1.plotly_chart(fig_pie, use_container_width=True)
        
        if not df_dias.empty:
            df_dias["Mes"] = df_dias["Data"].dt.to_period("M").dt.to_timestamp()
            line_df = df_dias.groupby("Mes")["Nome"].nunique().reset_index(name="Qtd")
            fig_line = px.line(line_df, x="Mes", y="Qtd", title="Evolução de Ausências")
            c2.plotly_chart(fig_line, use_container_width=True)

# --- TAB 5: FÉRIAS ---
with tab5:
    df_f = df_eventos[df_eventos["Tipo"]=="Férias"]
    if not df_f.empty:
        st.dataframe(df_f[["Posto", "Nome", "Inicio", "Fim", "Duracao_dias"]], use_container_width=True)
    else: st.info("Sem férias.")

# --- TAB 6: CURSOS ---
with tab6:
    df_c = df_eventos[df_eventos["Tipo"]=="Curso"]
    if not df_c.empty:
        st.dataframe(df_c[["Posto", "Nome", "Motivo", "Inicio", "Fim"]], use_container_width=True)
    else: st.info("Sem cursos.")

# --- TAB 7: DEBUG ---
with tab7:
    st.write("### Colunas Identificadas Automaticamente")
    
    st.write("**Pares de Férias (Inicio / Fim - sem acento):**")
    st.write(FERIAS_DETECTADAS)
    
    st.write("**Trios de Ausência (Início / FIm / Motivo - com acento e I maiúsculo):**")
    st.write(AUSENCIAS_DETECTADAS)
    
    st.write("### Colunas Brutas do DataFrame")
    st.write(list(df_raw.columns))
