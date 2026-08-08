import streamlit as st
from utils.dados import buscar_veiculos, buscar_clientes, buscar_orcamentos, buscar_servicos
import pandas as pd
import plotly.express as px
import json
from datetime import date, timedelta

st.set_page_config(layout="wide", page_title="Painel Gerencial | Sanini & Aimi")
st.title("📊 Painel de Controle e Métricas")

df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes("id, nome")
df_orcamentos = buscar_orcamentos()
df_servicos = buscar_servicos()

# --- BARRA LATERAL (FILTROS MACRO) ---
st.sidebar.header("🔍 Filtros do Painel")

lista_placas = ["Todas"] + df_veiculos['placa'].tolist() if not df_veiculos.empty else ["Todas"]
filtro_placa = st.sidebar.selectbox("Filtrar por Placa", lista_placas)

lista_cli = ["Todos"] + df_clientes['nome'].tolist() if not df_clientes.empty else ["Todos"]
filtro_cliente = st.sidebar.selectbox("Filtrar por Cliente", lista_cli)

st.sidebar.divider()
st.sidebar.markdown("**Período Analisado**")
col_d1, col_d2 = st.sidebar.columns(2)
filtro_inicio = col_d1.date_input("Início", date.today() - timedelta(days=30))
filtro_fim = col_d2.date_input("Fim", date.today())

# --- APLICAÇÃO DOS FILTROS AOS DATAFRAMES ---
df_orc_f = df_orcamentos.copy()
df_serv_f = df_servicos.copy()

if filtro_placa != "Todas":
    if not df_orc_f.empty: df_orc_f = df_orc_f[df_orc_f['placa_veiculo'] == filtro_placa]
    if not df_serv_f.empty: df_serv_f = df_serv_f[df_serv_f['placa_veiculo'] == filtro_placa]

if filtro_cliente != "Todos" and not df_clientes.empty and not df_veiculos.empty:
    id_cli = df_clientes[df_clientes['nome'] == filtro_cliente]['id'].values[0]
    placas_cli = df_veiculos[df_veiculos['cliente_id'] == id_cli]['placa'].tolist()
    if not df_orc_f.empty: df_orc_f = df_orc_f[df_orc_f['placa_veiculo'].isin(placas_cli)]
    if not df_serv_f.empty: df_serv_f = df_serv_f[df_serv_f['placa_veiculo'].isin(placas_cli)]

if not df_orc_f.empty:
    df_orc_f['data'] = pd.to_datetime(df_orc_f['data']).dt.date
    df_orc_f = df_orc_f[(df_orc_f['data'] >= filtro_inicio) & (df_orc_f['data'] <= filtro_fim)]

if not df_serv_f.empty:
    df_serv_f['data_servico'] = pd.to_datetime(df_serv_f['data_servico']).dt.date
    df_serv_f = df_serv_f[(df_serv_f['data_servico'] >= filtro_inicio) & (df_serv_f['data_servico'] <= filtro_fim)]

# --- MÉTRICAS SUPERIORES ---
col1, col2, col3, col4 = st.columns(4)

fat_total = df_serv_f['valor_total'].sum() if not df_serv_f.empty else 0.0

with col1: st.metric("👥 Clientes", len(df_clientes))
with col2: st.metric("📝 Orç. Filtrados", len(df_orc_f))
with col3: st.metric("🛠️ Ordens de Serviço", len(df_serv_f))
with col4: st.metric("💰 Faturamento Período", f"R$ {fat_total:,.2f}")

st.divider()

# --- GRÁFICOS ---
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("Status dos Orçamentos (Filtrado)")
    if not df_orc_f.empty:
        fig1 = px.pie(df_orc_f, names='status', hole=0.4, template="plotly_dark")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Nenhum orçamento no período/filtro.")

with col_g2:
    st.subheader("Evolução do Faturamento (Filtrado)")
    if not df_serv_f.empty:
        fig2 = px.bar(df_serv_f, x='data_servico', y='valor_total',
                      text_auto='.2s', template="plotly_dark", color_discrete_sequence=['#22c55e'])
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Nenhum serviço no período/filtro.")

st.divider()

# --- TIPOS DE SERVIÇO EXECUTADOS (MÃO DE OBRA) ---
st.subheader("🛠️ Tipos de Serviço Executados (Filtrado)")


def extrair_itens_servico(df):
    linhas = []
    for _, r in df.iterrows():
        val = r.get('servicos_executados', '')
        if val and str(val).startswith('['):
            try:
                for item in json.loads(val):
                    nome = item.get('Serviço', '')
                    if nome:
                        linhas.append({"Serviço": nome, "Valor (R$)": float(item.get('Valor (R$)', 0) or 0)})
            except Exception:
                pass
    return pd.DataFrame(linhas)


df_itens_servico = extrair_itens_servico(df_serv_f)

if df_itens_servico.empty:
    st.info("Nenhum serviço (mão de obra) itemizado no período/filtro selecionado.")
else:
    resumo_servicos = df_itens_servico.groupby("Serviço").agg(
        Quantidade=("Valor (R$)", "count"),
        Faturamento=("Valor (R$)", "sum"),
    ).reset_index().sort_values("Faturamento", ascending=False)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("**Faturamento por Tipo de Serviço**")
        fig3 = px.bar(resumo_servicos, x="Serviço", y="Faturamento", text_auto=".2s",
                      template="plotly_dark", color_discrete_sequence=['#3b82f6'])
        st.plotly_chart(fig3, use_container_width=True)
    with col_s2:
        st.markdown("**Quantidade de Execuções por Tipo**")
        fig4 = px.pie(resumo_servicos, names="Serviço", values="Quantidade", hole=0.4, template="plotly_dark")
        st.plotly_chart(fig4, use_container_width=True)

    st.dataframe(
        resumo_servicos.rename(columns={"Faturamento": "Faturamento (R$)"}),
        use_container_width=True, hide_index=True
    )
