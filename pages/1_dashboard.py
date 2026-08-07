import streamlit as st
from database import supabase
import pandas as pd
from datetime import date, timedelta

if not st.session_state.get("logado"):
    st.warning("⚠️ Faça login na página principal.")
    st.stop()

st.title("📊 Painel de Controle")
st.markdown("Acompanhamento de métricas e faturamento em tempo real.")

@st.cache_data(ttl=10)
def carregar_dados():
    v = supabase.table("veiculos").select("*").execute().data
    o = supabase.table("orcamentos").select("*").execute().data
    s = supabase.table("servicos_realizados").select("*").execute().data
    return pd.DataFrame(v), pd.DataFrame(o), pd.DataFrame(s)

df_veiculos, df_orcamentos, df_servicos = carregar_dados()

# --- BARRA LATERAL (FILTROS OTIMIZADOS) ---
st.sidebar.header("🔍 Filtros")

placas = ["Todas"] + df_veiculos['placa'].tolist() if not df_veiculos.empty else ["Todas"]
filtro_placa = st.sidebar.selectbox("Placa do Veículo", placas)

clientes = ["Todos"] + df_veiculos['cliente_nome'].dropna().unique().tolist() if not df_veiculos.empty else ["Todos"]
filtro_cliente = st.sidebar.selectbox("Cliente", clientes)

st.sidebar.divider()
st.sidebar.markdown("**Período dos Serviços/Orçamentos**")
col_dt1, col_dt2 = st.sidebar.columns(2)
# Define últimos 30 dias como padrão visual
filtro_inicio = col_dt1.date_input("Início", date.today() - timedelta(days=30))
filtro_fim = col_dt2.date_input("Fim", date.today())

# --- APLICAÇÃO DOS FILTROS ---
if filtro_placa != "Todas":
    df_veiculos = df_veiculos[df_veiculos['placa'] == filtro_placa]
    if not df_orcamentos.empty: df_orcamentos = df_orcamentos[df_orcamentos['placa_veiculo'] == filtro_placa]
    if not df_servicos.empty: df_servicos = df_servicos[df_servicos['placa_veiculo'] == filtro_placa]

if filtro_cliente != "Todos":
    placas_cli = df_veiculos[df_veiculos['cliente_nome'] == filtro_cliente]['placa'].tolist()
    if not df_orcamentos.empty: df_orcamentos = df_orcamentos[df_orcamentos['placa_veiculo'].isin(placas_cli)]
    if not df_servicos.empty: df_servicos = df_servicos[df_servicos['placa_veiculo'].isin(placas_cli)]

# Filtro de datas preciso
if not df_orcamentos.empty:
    df_orcamentos['data'] = pd.to_datetime(df_orcamentos['data']).dt.date
    df_orcamentos = df_orcamentos[(df_orcamentos['data'] >= filtro_inicio) & (df_orcamentos['data'] <= filtro_fim)]
if not df_servicos.empty:
    df_servicos['data_servico'] = pd.to_datetime(df_servicos['data_servico']).dt.date
    df_servicos = df_servicos[(df_servicos['data_servico'] >= filtro_inicio) & (df_servicos['data_servico'] <= filtro_fim)]

# --- CARDS SUPERIORES ---
st.markdown("<br>", unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)

fat_total = df_servicos['valor_total'].sum() if not df_servicos.empty else 0.0
orc_pend = len(df_orcamentos[df_orcamentos['status'] == 'Pendente']) if not df_orcamentos.empty else 0

with col1:
    with st.container(border=True):
        st.metric("🚗 Veículos Atendidos", len(df_veiculos))
with col2:
    with st.container(border=True):
        st.metric("📝 Orç. Pendentes", orc_pend)
with col3:
    with st.container(border=True):
        st.metric("🛠️ Serviços Realizados", len(df_servicos))
with col4:
    with st.container(border=True):
        st.metric("💰 Faturamento Bruto", f"R$ {fat_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("<br>", unsafe_allow_html=True)

# --- GRÁFICOS ELEGANTES ---
col_g1, col_g2 = st.columns(2)

with col_g1:
    with st.container(border=True):
        st.subheader("Status dos Orçamentos")
        if not df_orcamentos.empty:
            st.bar_chart(df_orcamentos['status'].value_counts(), color="#FF4B4B")
        else:
            st.info("Nenhum dado no período.")

with col_g2:
    with st.container(border=True):
        st.subheader("Faturamento Diário")
        if not df_servicos.empty:
            # Agrupa por data e usa gráfico de barras, mais fácil de ler que linhas vazias
            df_fat = df_servicos.groupby('data_servico')['valor_total'].sum()
            st.bar_chart(df_fat, color="#009900")
        else:
            st.info("Nenhum serviço no período.")