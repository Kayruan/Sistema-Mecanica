import streamlit as st
from utils.dados import buscar_veiculos, buscar_clientes, buscar_orcamentos, buscar_servicos, buscar_estoque_pecas
from utils.auth import eh_gerente
from utils.imagens import url_valida
import pandas as pd
import plotly.express as px
import json
from datetime import date, timedelta

st.set_page_config(layout="wide", page_title="Painel Gerencial | Sanini & Aimi")

if not eh_gerente():
    st.error("Acesso restrito a usuários com papel Gerente.", icon=":material/lock:")
    st.stop()

st.title("Painel de controle e métricas", anchor=False)

df_estoque_dash = buscar_estoque_pecas()
if not df_estoque_dash.empty:
    qtd_estoque_baixo = int((df_estoque_dash['quantidade'] <= df_estoque_dash['estoque_minimo']).sum())
    if qtd_estoque_baixo:
        st.warning(
            f":material/inventory_2: {qtd_estoque_baixo} peça(s) com estoque baixo ou zerado — veja em Cadastros → Estoque.",
            icon=":material/warning:",
        )

# Paleta alinhada ao tema em .streamlit/config.toml
CORES_CATEGORICAS = ["#60A5FA", "#34D399", "#A78BFA", "#F87171", "#FBBF24", "#38BDF8", "#FB923C", "#94A3B8"]
FUNDO_GRAFICO = "#1E293B"
FUNDO_PAPEL = "#0F172A"
COR_TEXTO = "#F1F5F9"
COR_GRADE = "#334155"


def estilizar(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=FUNDO_PAPEL,
        plot_bgcolor=FUNDO_GRAFICO,
        font=dict(color=COR_TEXTO, family="Inter, sans-serif"),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=COR_GRADE, zerolinecolor=COR_GRADE)
    fig.update_yaxes(gridcolor=COR_GRADE, zerolinecolor=COR_GRADE)
    return fig


df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes("id, nome")
df_orcamentos = buscar_orcamentos()
df_servicos = buscar_servicos()

# --- BARRA LATERAL (FILTROS MACRO) ---
st.sidebar.header("Filtros do painel")

lista_placas = ["Todas"] + df_veiculos['placa'].tolist() if not df_veiculos.empty else ["Todas"]
filtro_placa = st.sidebar.selectbox("Placa", lista_placas)

lista_cli = ["Todos"] + df_clientes['nome'].tolist() if not df_clientes.empty else ["Todos"]
filtro_cliente = st.sidebar.selectbox("Cliente", lista_cli)

st.sidebar.divider()
st.sidebar.markdown("**Período analisado**")
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
fat_total = df_serv_f['valor_total'].sum() if not df_serv_f.empty else 0.0

if not df_serv_f.empty:
    valor_pago_col = pd.to_numeric(df_serv_f.get('valor_pago', 0), errors='coerce').fillna(0)
    status_os_col = df_serv_f.get('status_os', 'Em Andamento').fillna('Em Andamento') if 'status_os' in df_serv_f.columns else pd.Series('Em Andamento', index=df_serv_f.index)
    assinada_col = df_serv_f.get('assinatura_url').apply(url_valida) if 'assinatura_url' in df_serv_f.columns else pd.Series(False, index=df_serv_f.index)
    cobravel = (status_os_col == 'Finalizada') & assinada_col
    a_receber = (df_serv_f.loc[cobravel, 'valor_total'] - valor_pago_col[cobravel]).clip(lower=0).sum()
    em_andamento_qtd_dash = int((status_os_col == 'Em Andamento').sum())
else:
    a_receber = 0.0
    em_andamento_qtd_dash = 0

# "Recebido no período": dinheiro que efetivamente entrou (pela data do recebimento, não da OS)
df_todos_serv = df_servicos.copy()
if not df_todos_serv.empty and 'data_pagamento' in df_todos_serv.columns:
    df_pagos_periodo = df_todos_serv[df_todos_serv['data_pagamento'].notna()].copy()
    df_pagos_periodo['data_pagamento'] = pd.to_datetime(df_pagos_periodo['data_pagamento']).dt.date
    df_pagos_periodo = df_pagos_periodo[
        (df_pagos_periodo['data_pagamento'] >= filtro_inicio) & (df_pagos_periodo['data_pagamento'] <= filtro_fim)
    ]
    if filtro_placa != "Todas":
        df_pagos_periodo = df_pagos_periodo[df_pagos_periodo['placa_veiculo'] == filtro_placa]
    recebido_periodo = pd.to_numeric(df_pagos_periodo['valor_pago'], errors='coerce').fillna(0).sum()
else:
    recebido_periodo = 0.0

ticket_medio = (fat_total / len(df_serv_f)) if not df_serv_f.empty else 0.0

with st.container(horizontal=True):
    st.metric("Clientes", len(df_clientes), border=True)
    st.metric("Orçamentos filtrados", len(df_orc_f), border=True)
    st.metric("Ordens de serviço", len(df_serv_f), border=True)
    st.metric("OS em andamento", em_andamento_qtd_dash, border=True)
    st.metric("Faturamento no período", f"R$ {fat_total:,.2f}", border=True, help="Valor total das OS realizadas no período, independente de já terem sido pagas.")
    st.metric("Recebido no período", f"R$ {recebido_periodo:,.2f}", border=True, help="Dinheiro efetivamente recebido no período (pela data do pagamento).")
    st.metric("A receber", f"R$ {a_receber:,.2f}", border=True, help="Saldo pendente de OS já finalizadas e assinadas.")
    st.metric("Ticket médio", f"R$ {ticket_medio:,.2f}", border=True)

st.divider()

# --- GRÁFICOS ---
col_g1, col_g2 = st.columns(2)

with col_g1:
    with st.container(border=True):
        st.subheader("Status dos orçamentos", anchor=False)
        if not df_orc_f.empty:
            fig1 = px.pie(df_orc_f, names='status', hole=0.55, color_discrete_sequence=CORES_CATEGORICAS)
            fig1.update_traces(textinfo="percent+label", marker=dict(line=dict(color=FUNDO_PAPEL, width=3)))
            st.plotly_chart(estilizar(fig1), width="stretch")
        else:
            st.info("Nenhum orçamento no período/filtro.")

with col_g2:
    with st.container(border=True):
        st.subheader("Evolução do faturamento", anchor=False)
        if not df_serv_f.empty:
            fig2 = px.bar(df_serv_f, x='data_servico', y='valor_total',
                          text_auto='.2s', color_discrete_sequence=[CORES_CATEGORICAS[1]])
            fig2.update_traces(marker=dict(cornerradius=6))
            st.plotly_chart(estilizar(fig2), width="stretch")
        else:
            st.info("Nenhum serviço no período/filtro.")

st.divider()

# --- TIPOS DE SERVIÇO EXECUTADOS (MÃO DE OBRA) ---
st.subheader("Tipos de serviço executados", anchor=False)


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
        with st.container(border=True):
            st.markdown("**Faturamento por tipo de serviço**")
            fig3 = px.bar(resumo_servicos, x="Serviço", y="Faturamento", text_auto=".2s",
                          color="Serviço", color_discrete_sequence=CORES_CATEGORICAS)
            fig3.update_traces(marker=dict(cornerradius=6))
            fig3.update_layout(showlegend=False)
            st.plotly_chart(estilizar(fig3), width="stretch")
    with col_s2:
        with st.container(border=True):
            st.markdown("**Quantidade de execuções por tipo**")
            fig4 = px.pie(resumo_servicos, names="Serviço", values="Quantidade", hole=0.55, color_discrete_sequence=CORES_CATEGORICAS)
            fig4.update_traces(textinfo="percent+label", marker=dict(line=dict(color=FUNDO_PAPEL, width=3)))
            st.plotly_chart(estilizar(fig4), width="stretch")

    with st.container(border=True):
        st.dataframe(
            resumo_servicos.rename(columns={"Faturamento": "Faturamento (R$)"}),
            width="stretch", hide_index=True
        )

st.divider()

# --- INDICADORES AVANÇADOS DE GESTÃO ---
st.subheader("Indicadores avançados", anchor=False)

col_i1, col_i2 = st.columns(2)

with col_i1:
    with st.container(border=True):
        st.markdown("**Funil de conversão de orçamentos**")
        if df_orc_f.empty:
            st.info("Nenhum orçamento no período/filtro.")
        else:
            ordem_funil = ["Pendente", "Aprovado", "Finalizado", "Cancelado"]
            contagem_status = df_orc_f['status'].value_counts().reindex(ordem_funil).fillna(0).astype(int)
            df_funil = contagem_status.reset_index()
            df_funil.columns = ["Status", "Quantidade"]
            fig5 = px.funnel(df_funil, x="Quantidade", y="Status", color_discrete_sequence=[CORES_CATEGORICAS[0]])
            st.plotly_chart(estilizar(fig5), width="stretch")

with col_i2:
    with st.container(border=True):
        st.markdown("**Veículos mais atendidos**")
        if df_serv_f.empty:
            st.info("Nenhum serviço no período/filtro.")
        else:
            ranking_veic = df_serv_f['placa_veiculo'].value_counts().head(10).reset_index()
            ranking_veic.columns = ["Placa", "Ordens de serviço"]
            fig6 = px.bar(ranking_veic, x="Ordens de serviço", y="Placa", orientation="h",
                          text_auto=True, color_discrete_sequence=[CORES_CATEGORICAS[2]])
            fig6.update_traces(marker=dict(cornerradius=6))
            fig6.update_layout(yaxis=dict(categoryorder="total ascending"))
            st.plotly_chart(estilizar(fig6), width="stretch")

with st.container(border=True):
    st.markdown("**Clientes recorrentes vs. novos**")
    if df_servicos.empty or df_veiculos.empty or df_clientes.empty:
        st.info("Sem dados suficientes para calcular clientes recorrentes/novos.")
    else:
        df_serv_cli = df_servicos.copy()
        df_serv_cli['data_servico'] = pd.to_datetime(df_serv_cli['data_servico']).dt.date
        df_serv_cli = df_serv_cli.merge(
            df_veiculos[['placa', 'cliente_id']], left_on='placa_veiculo', right_on='placa', how='left'
        )
        df_serv_cli = df_serv_cli.dropna(subset=['cliente_id'])

        primeira_visita = df_serv_cli.groupby('cliente_id')['data_servico'].min().rename('primeira_visita')
        total_visitas = df_serv_cli.groupby('cliente_id')['data_servico'].count().rename('total_visitas')
        resumo_cli = pd.concat([primeira_visita, total_visitas], axis=1)

        clientes_no_periodo = df_serv_cli[
            (df_serv_cli['data_servico'] >= filtro_inicio) & (df_serv_cli['data_servico'] <= filtro_fim)
        ]['cliente_id'].unique()
        resumo_periodo = resumo_cli.loc[resumo_cli.index.isin(clientes_no_periodo)]

        novos = int((resumo_periodo['primeira_visita'] >= filtro_inicio).sum())
        recorrentes = int((resumo_periodo['total_visitas'] > 1).sum())

        c_rec1, c_rec2 = st.columns(2)
        c_rec1.metric("Clientes novos no período", novos, border=True)
        c_rec2.metric("Clientes recorrentes no período", recorrentes, border=True)
