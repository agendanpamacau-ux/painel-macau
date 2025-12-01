import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel NPaMacau", layout="wide", page_icon="⚓")
st.title("⚓ Dashboard de Comando - NPaMacau")

# --- 2. CARREGAMENTO E LIMPEZA ---
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # header=2 considera a linha 3 como cabeçalho. Dados começam na 4.
    df = conn.read(worksheet="Afastamento 2026", header=2, ttl="10m")
    
    # Remove linhas vazias baseadas na Coluna C (Nome) - Índice 2
    # Ajuste o índice se o Pandas ler colunas extras vazias antes do A
    # Assumindo A=0, B=1, C=2...
    if len(df.columns) > 2:
        df = df.dropna(subset=[df.columns[2]]) 
        
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro de conexão. Verifique o arquivo secrets.toml. Detalhe: {e}")
    st.stop()

# --- 3. PROCESSAMENTO INTELIGENTE (Wide to Long) ---
# Vamos transformar a planilha "larga" em uma lista vertical de eventos
# Isso permite criar gráficos e estatísticas globais

lista_eventos = []

# Mapeamento fixo baseado na sua descrição
# Colunas (0-based no Python):
# A=0, B=1, C=2 ... I=8 ... Y=24 ...
col_posto = df_raw.columns[1] # Coluna B
col_nome  = df_raw.columns[2] # Coluna C
col_eqman = df_raw.columns[4] # Coluna E
col_gvi   = df_raw.columns[5] # Coluna F
col_in    = df_raw.columns[6] # Coluna G

for index, row in df_raw.iterrows():
    militar_info = {
        "Posto": row.iloc[1],
        "Nome": row.iloc[2],
        "EqMan": row.iloc[4] if pd.notnull(row.iloc[4]) and str(row.iloc[4]) != "-" else "Não",
        "GVI": True if str(row.iloc[5]) == "True" else False, # Coluna F
        "IN": True if str(row.iloc[6]) == "True" else False,  # Coluna G
    }

    # --- BLOCO DE FÉRIAS (I até W) ---
    # Período 1 (I-J), Período 2 (L-M), Período 3 (O-P)
    # Índices: I=8, J=9 | L=11, M=12 | O=14, P=15
    pares_ferias = [(8, 9), (11, 12), (14, 15)]
    
    for inicio_idx, fim_idx in pares_ferias:
        try:
            ini = pd.to_datetime(row.iloc[inicio_idx], dayfirst=True, errors='coerce')
            fim = pd.to_datetime(row.iloc[fim_idx], dayfirst=True, errors='coerce')
            
            if pd.notnull(ini) and pd.notnull(fim):
                lista_eventos.append({**militar_info, "Inicio": ini, "Fim": fim, "Motivo": "FÉRIAS", "Tipo": "Férias"})
        except: pass

    # --- BLOCO DE OUTRAS AUSÊNCIAS (Y até AV) ---
    # Padrão: Inicio, Fim, Dif, Motivo, [Espaço]
    # Y(24)-Z(25) Motivo=AB(27)
    # AD(29)-AE(30) Motivo=AG(32)
    # AI(34)-AJ(35) Motivo=AL(37)
    # AN(39)-AO(40) Motivo=AQ(42)
    # AS(44)-AT(45) Motivo=AV(47)
    
    trios_ausencia = [
        (24, 25, 27), # Período 4
        (29, 30, 32), # Período 5
        (34, 35, 37), # Período 6
        (39, 40, 42), # Período 7
        (44, 45, 47)  # Período 8
    ]

    for ini_idx, fim_idx, mot_idx in trios_ausencia:
        try:
            ini = pd.to_datetime(row.iloc[ini_idx], dayfirst=True, errors='coerce')
            fim = pd.to_datetime(row.iloc[fim_idx], dayfirst=True, errors='coerce')
            motivo_texto = str(row.iloc[mot_idx])
            
            if pd.notnull(ini) and pd.notnull(fim):
                motivo_real = motivo_texto if len(motivo_texto) > 2 and "nan" not in motivo_texto.lower() else "OUTROS"
                lista_eventos.append({**militar_info, "Inicio": ini, "Fim": fim, "Motivo": motivo_real, "Tipo": "Outros"})
        except: pass

# Cria DataFrame de Eventos (Long Format)
df_eventos = pd.DataFrame(lista_eventos)

# --- 4. BARRA LATERAL (FILTROS) ---
st.sidebar.header("🕹️ Centro de Controle")
data_ref = st.sidebar.date_input("Data de Referência", datetime.today())
hoje = pd.to_datetime(data_ref)

# Filtro de Posto
todos_postos = df_raw.iloc[:, 1].unique()
filtro_posto = st.sidebar.multiselect("Filtrar Posto", todos_postos, default=todos_postos)

# Filtro de Equipes
filtro_eqman = st.sidebar.checkbox("Apenas EqMan")
filtro_in = st.sidebar.checkbox("Apenas Inspetores Navais (IN)")

# Aplicar Filtros no DataFrame Principal (df_raw) para contagem total
df_tripulacao_filtrada = df_raw[df_raw.iloc[:, 1].isin(filtro_posto)]
if filtro_eqman:
    # Filtra onde a coluna E (índice 4) não é traço nem vazia
    df_tripulacao_filtrada = df_tripulacao_filtrada[
        (df_tripulacao_filtrada.iloc[:, 4].notnull()) & (df_tripulacao_filtrada.iloc[:, 4].astype(str) != "-")
    ]
if filtro_in:
    df_tripulacao_filtrada = df_tripulacao_filtrada[df_tripulacao_filtrada.iloc[:, 6].astype(str) == "True"]

# --- 5. LÓGICA DE STATUS DO DIA ---
# Quem está fora HOJE baseado na lista de eventos?
if not df_eventos.empty:
    ausentes_hoje = df_eventos[
        (df_eventos['Inicio'] <= hoje) & 
        (df_eventos['Fim'] >= hoje) & 
        (df_eventos['Posto'].isin(filtro_posto))
    ]
    # Aplicar filtros de equipe na lista de ausentes também
    if filtro_eqman:
        ausentes_hoje = ausentes_hoje[ausentes_hoje['EqMan'] != "Não"]
    if filtro_in:
        ausentes_hoje = ausentes_hoje[ausentes_hoje['IN'] == True]
else:
    ausentes_hoje = pd.DataFrame()

# Cálculos de KPI
total_efetivo = len(df_tripulacao_filtrada)
total_ausentes = len(ausentes_hoje['Nome'].unique()) if not ausentes_hoje.empty else 0
total_presentes = total_efetivo - total_ausentes
percentual = (total_presentes / total_efetivo * 100) if total_efetivo > 0 else 0

# --- 6. VISUALIZAÇÃO (TABS) ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Efetivo Total", total_efetivo)
col2.metric("A Bordo", total_presentes)
col3.metric("Ausentes", total_ausentes, delta_color="inverse")
col4.metric("Prontidão", f"{percentual:.1f}%")

tab1, tab2, tab3 = st.tabs(["📋 Situação Diária", "📅 Linha do Tempo (Gantt)", "📊 Estatísticas"])

with tab1:
    st.subheader(f"Status em {hoje.strftime('%d/%m/%Y')}")
    if total_ausentes > 0:
        # Tabela bonitinha
        show_df = ausentes_hoje[['Posto', 'Nome', 'Motivo', 'Fim']].copy()
        show_df['Retorno'] = show_df['Fim'].apply(lambda x: x.strftime('%d/%m/%Y'))
        show_df = show_df.drop(columns=['Fim'])
        st.dataframe(show_df, use_container_width=True, hide_index=True)
        
        # Alerta EqMan
        eqman_fora = ausentes_hoje[ausentes_hoje['EqMan'] != "Não"]
        if not eqman_fora.empty:
            st.error(f"⚠️ Atenção! {len(eqman_fora)} membros da EqMan ausentes: {', '.join(eqman_fora['Nome'].tolist())}")
    else:
        st.success("Todo o efetivo selecionado está a bordo.")

with tab2:
    st.subheader("Planejamento Anual")
    # Filtra eventos apenas dos postos selecionados para não poluir o gráfico
    if not df_eventos.empty:
        df_gantt = df_eventos[df_eventos['Posto'].isin(filtro_posto)].copy()
        
        if not df_gantt.empty:
            fig = px.timeline(
                df_gantt, 
                x_start="Inicio", 
                x_end="Fim", 
                y="Nome", 
                color="Motivo",
                hover_data=["Posto", "EqMan"],
                title="Cronograma de Ausências"
            )
            fig.update_yaxes(autorange="reversed") # Nomes de cima para baixo
            # Linha vertical no dia selecionado
            fig.add_vline(x=hoje.timestamp() * 1000, line_width=2, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum evento futuro encontrado para os filtros atuais.")
    else:
        st.info("Planilha parece não ter datas preenchidas.")

with tab3:
    st.subheader("Análise de Dados")
    col_a, col_b = st.columns(2)
    
    if not df_eventos.empty:
        # Gráfico 1: Pizza de Motivos
        fig_pie = px.pie(df_eventos, names='Motivo', title='Distribuição de Motivos de Ausência (Ano Todo)')
        col_a.plotly_chart(fig_pie, use_container_width=True)
        
        # Gráfico 2: Ausências por Posto
        # Conta quantos eventos cada posto tem
        ausencias_por_posto = df_eventos.groupby('Posto').size().reset_index(name='Quantidade')
        fig_bar = px.bar(ausencias_por_posto, x='Posto', y='Quantidade', title='Volume de Ausências por Posto')
        col_b.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.write("Sem dados suficientes para estatísticas.")
