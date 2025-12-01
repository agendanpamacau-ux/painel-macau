import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Painel NPaMacau", layout="wide", page_icon="⚓")
st.title("⚓ Gestão de Efetivo - NPaMacau")

# --- 2. CARREGAR DADOS (SOMENTE ABA "Afastamento 2026") ---
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # O paramêtro 'worksheet' obriga o robô a ler SÓ essa aba.
    # header=2 indica que o título das colunas está na linha 3 do Excel
    df = conn.read(
        worksheet="Afastamento 2026", 
        header=2, 
        ttl="10m"
    )
    
    # Limpeza: Se a coluna de Nome estiver vazia, remove a linha
    # Procura coluna que contenha "Nome" ou "NOME"
    cols_nome = [c for c in df.columns if "NOME" in str(c).upper()]
    if cols_nome:
        df = df.dropna(subset=[cols_nome[0]])
        
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Erro ao ler a aba 'Afastamento 2026'. Verifique se o nome está idêntico no Google Sheets.\nDetalhe: {e}")
    st.stop()

# --- 3. SEPARAÇÃO DAS FATIAS (Conforme sua estrutura) ---
# A-G (0 a 7) -> Dados do Militar
# I-W (8 a 23) -> Férias 
# Y-AV (24 a 48) -> Outros Afastamentos

df_militar = df_raw.iloc[:, 0:7].copy()
df_ferias  = df_raw.iloc[:, 8:23].copy()
df_outros  = df_raw.iloc[:, 24:48].copy()

# Tenta renomear as colunas principais para facilitar
try:
    df_militar.columns = ['ID', 'Posto', 'Nome', 'Servico', 'EqMan', 'Gvi_GP', 'IN']
except:
    # Se der erro nos nomes, usa a 2ª coluna como Posto e 3ª como Nome por padrão
    pass

# --- 4. FILTROS NA BARRA LATERAL ---
st.sidebar.header("🕹️ Controle")
data_selecionada = st.sidebar.date_input("📅 Verificar situação em:", datetime.today())
hoje = pd.to_datetime(data_selecionada)

# Filtro de Posto
# Pega a coluna de Posto (assumindo ser a segunda coluna, índice 1)
col_posto = df_militar.columns[1] 
opcoes_posto = df_militar[col_posto].unique()
filtro_posto = st.sidebar.multiselect("Filtrar Posto/Graduação", options=opcoes_posto, default=opcoes_posto)

# --- 5. LÓGICA DE DETECÇÃO (O Cérebro do Robô) ---
def verificar_status(index):
    # --- VERIFICA FÉRIAS ---
    row_ferias = df_ferias.iloc[index]
    # Varre a linha procurando datas
    for i in range(len(row_ferias)-1):
        try:
            inicio = pd.to_datetime(row_ferias.iloc[i], dayfirst=True, errors='coerce')
            if pd.notnull(inicio):
                # Se achou inicio, vê se o próximo é o fim
                fim = pd.to_datetime(row_ferias.iloc[i+1], dayfirst=True, errors='coerce')
                if pd.notnull(fim):
                    if inicio <= hoje <= fim:
                        return "FÉRIAS", fim
        except:
            continue

    # --- VERIFICA OUTROS AFASTAMENTOS ---
    row_outros = df_outros.iloc[index]
    for i in range(len(row_outros)-1):
        try:
            inicio = pd.to_datetime(row_outros.iloc[i], dayfirst=True, errors='coerce')
            if pd.notnull(inicio):
                # Se achou inicio, vê se o próximo é o fim
                fim = pd.to_datetime(row_outros.iloc[i+1], dayfirst=True, errors='coerce')
                if pd.notnull(fim):
                    if inicio <= hoje <= fim:
                        # Tenta achar o motivo (geralmente 2 células à frente do início)
                        motivo = "AFASTADO"
                        if i+2 < len(row_outros):
                            txt = str(row_outros.iloc[i+2])
                            if len(txt) > 2 and "nan" not in txt.lower():
                                motivo = txt.upper()
                        return motivo, fim
        except:
            continue
            
    return "A BORDO", None

# Aplica a verificação para todo mundo
status_list = []
retorno_list = []

for i in range(len(df_militar)):
    s, r = verificar_status(i)
    status_list.append(s)
    retorno_list.append(r)

df_militar['Status'] = status_list
df_militar['Retorno'] = retorno_list

# --- 6. EXIBIÇÃO NO PAINEL ---
# Aplica o filtro de posto
df_final = df_militar[df_militar[col_posto].isin(filtro_posto)]

# Contadores
total = len(df_final)
ausentes = df_final[df_final['Status'] != "A BORDO"]
presentes = total - len(ausentes)

# Mostra os números grandes
c1, c2, c3 = st.columns(3)
c1.metric("Efetivo Listado", total)
c2.metric("A Bordo", presentes)
c3.metric("Ausentes", len(ausentes), delta_color="inverse")

st.markdown("---")

if not ausentes.empty:
    st.subheader(f"🚨 Ausentes em {hoje.strftime('%d/%m/%Y')}")
    # Formata a data de retorno para ler fácil
    df_show = ausentes.copy()
    df_show['Retorno'] = df_show['Retorno'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else "?")
    
    # Mostra tabela limpa (Nome, Posto, Status, Retorno)
    st.dataframe(
        df_show[[col_posto, df_militar.columns[2], 'Status', 'Retorno']], 
        use_container_width=True,
        hide_index=True
    )
else:
    st.success(f"Ninguém afastado na data de {hoje.strftime('%d/%m/%Y')}!")

# Expansor para ver a lista completa se quiser
with st.expander("Ver Tripulação Completa"):
    st.dataframe(df_final)
