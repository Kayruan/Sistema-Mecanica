import streamlit as st
from database import supabase
from utils.dados import (
    buscar_veiculos, buscar_clientes, buscar_servicos,
    COR_STATUS_PAGAMENTO, OPCOES_FORMA_PAGAMENTO,
)
from utils.paginacao import paginar
from utils.auth import registrar_log, eh_gerente
from utils.imagens import url_valida
import pandas as pd
from datetime import date

st.set_page_config(layout="wide", page_title="Contas a Receber | Sanini & Aimi")

if not eh_gerente():
    st.error("Acesso restrito a usuários com papel Gerente.", icon=":material/lock:")
    st.stop()

st.title("Contas a receber", anchor=False)
st.caption("Ordens de serviço finalizadas e assinadas pelo cliente, com pagamento pendente ou parcial.")

msg_sucesso_receber = st.session_state.pop("msg_sucesso_receber", None)
if msg_sucesso_receber:
    st.success(msg_sucesso_receber, icon=":material/check_circle:")

df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes()
df_servicos = buscar_servicos()

if df_servicos.empty:
    st.info("Nenhuma ordem de serviço registrada ainda.")
    st.stop()

if 'status_pagamento' not in df_servicos.columns:
    df_servicos['status_pagamento'] = 'Pendente'
if 'valor_pago' not in df_servicos.columns:
    df_servicos['valor_pago'] = 0.0
if 'status_os' not in df_servicos.columns:
    df_servicos['status_os'] = 'Em Andamento'

em_andamento_qtd = len(df_servicos[df_servicos['status_os'].fillna('Em Andamento') == 'Em Andamento'])
aguardando_assinatura_qtd = len(df_servicos[
    (df_servicos['status_os'].fillna('Em Andamento') == 'Finalizada')
    & (~df_servicos['assinatura_url'].apply(url_valida))
])
if em_andamento_qtd or aguardando_assinatura_qtd:
    st.caption(
        f":material/info: {em_andamento_qtd} OS em andamento e {aguardando_assinatura_qtd} finalizada(s) aguardando "
        "assinatura do cliente ainda não entram aqui — só aparecem depois de finalizadas e assinadas."
    )

df_pendentes = df_servicos[
    (df_servicos['status_pagamento'].fillna('Pendente') != 'Pago')
    & (df_servicos['status_os'].fillna('Em Andamento') == 'Finalizada')
    & (df_servicos['assinatura_url'].apply(url_valida))
].copy()

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    lista_placas = ["Todas"] + df_veiculos['placa'].tolist() if not df_veiculos.empty else ["Todas"]
    f_placa = st.selectbox("Placa", lista_placas)
with col_f2:
    lista_cli = ["Todos"] + df_clientes['nome'].tolist() if not df_clientes.empty else ["Todos"]
    f_cli = st.selectbox("Cliente", lista_cli)
with col_f3:
    f_data = st.date_input("Período (início e fim)", [])

if not df_pendentes.empty:
    if f_placa != "Todas":
        df_pendentes = df_pendentes[df_pendentes['placa_veiculo'] == f_placa]
    if f_cli != "Todos" and not df_clientes.empty and not df_veiculos.empty:
        id_cli = df_clientes[df_clientes['nome'] == f_cli]['id'].values[0]
        placas_cli = df_veiculos[df_veiculos['cliente_id'] == id_cli]['placa'].tolist()
        df_pendentes = df_pendentes[df_pendentes['placa_veiculo'].isin(placas_cli)]
    if len(f_data) == 2:
        df_pendentes['data_servico'] = pd.to_datetime(df_pendentes['data_servico']).dt.date
        df_pendentes = df_pendentes[(df_pendentes['data_servico'] >= f_data[0]) & (df_pendentes['data_servico'] <= f_data[1])]

valor_pago_col = pd.to_numeric(df_pendentes['valor_pago'], errors='coerce').fillna(0) if not df_pendentes.empty else pd.Series(dtype=float)
total_pendente = (df_pendentes['valor_total'] - valor_pago_col).clip(lower=0).sum() if not df_pendentes.empty else 0.0

with st.container(horizontal=True):
    st.metric("Ordens de serviço em aberto", len(df_pendentes), border=True)
    st.metric("Total a receber", f"R$ {total_pendente:,.2f}", border=True)

st.divider()

@st.dialog("Gerenciar pagamento", width="large")
def gerenciar_pagamento(row, n_txt):
    valor_pago_atual = float(row.get('valor_pago') or 0)
    valor_total = float(row['valor_total'])
    valor_restante_atual = max(0.0, valor_total - valor_pago_atual)
    status_pag = row.get('status_pagamento') or 'Pendente'

    st.markdown(f"#### OS Nº {row['id']} — {row['placa_veiculo']}  ·  {n_txt}")
    st.badge(status_pag, color=COR_STATUS_PAGAMENTO.get(status_pag, "gray"))

    with st.container(horizontal=True):
        st.metric("Valor total", f"R$ {valor_total:,.2f}", border=True)
        st.metric("Já pago", f"R$ {valor_pago_atual:,.2f}", border=True)
        st.metric("Restante", f"R$ {valor_restante_atual:,.2f}", border=True)

    st.divider()
    st.markdown("**Registrar recebimento**")
    valor_recebido_agora = st.number_input(
        "Valor recebido agora (R$)", min_value=0.0, max_value=valor_restante_atual,
        value=valor_restante_atual, step=10.0, key=f"vlrreceb_{row['id']}",
    )
    forma_pag = st.selectbox("Forma de pagamento", OPCOES_FORMA_PAGAMENTO, key=f"formareceb_{row['id']}")
    data_pag = st.date_input("Data do recebimento", value=date.today(), key=f"datareceb_{row['id']}")

    if st.button("Registrar recebimento", key=f"btnreceb_{row['id']}", icon=":material/save:", type="primary"):
        novo_valor_pago = min(valor_total, valor_pago_atual + valor_recebido_agora)
        if novo_valor_pago >= valor_total - 0.01:
            novo_status = "Pago"
        elif novo_valor_pago > 0:
            novo_status = "Parcial"
        else:
            novo_status = "Pendente"

        supabase.table("servicos_realizados").update({
            "status_pagamento": novo_status,
            "valor_pago": novo_valor_pago,
            "forma_pagamento": forma_pag,
            "data_pagamento": data_pag.isoformat(),
        }).eq("id", row['id']).execute()
        registrar_log("editou", "servico", row['id'], f"pagamento -> {novo_status} (recebido R$ {valor_recebido_agora:,.2f})")
        st.cache_data.clear()
        restante_novo = max(0.0, valor_total - novo_valor_pago)
        if novo_status == "Pago":
            st.session_state["msg_sucesso_receber"] = f"OS Nº {row['id']} quitada."
        else:
            st.session_state["msg_sucesso_receber"] = (
                f"Recebimento de R$ {valor_recebido_agora:,.2f} registrado na OS Nº {row['id']}. "
                f"Restam R$ {restante_novo:,.2f} pendentes."
            )
        st.rerun()


if df_pendentes.empty:
    st.success("Nenhuma pendência de pagamento encontrada para os filtros selecionados.", icon=":material/check_circle:")
else:
    df_pagina = paginar(df_pendentes, "contas_receber", por_pagina=10)

    for _, row in df_pagina.iterrows():
        placa = row['placa_veiculo']
        n_txt = "Sem nome"
        veic_row = df_veiculos[df_veiculos['placa'] == placa]
        if not veic_row.empty:
            c_id = veic_row.iloc[0].get('cliente_id')
            if pd.notna(c_id):
                cli_row = df_clientes[df_clientes['id'] == c_id]
                if not cli_row.empty:
                    n_txt = cli_row.iloc[0]['nome']

        valor_pago = float(row.get('valor_pago') or 0)
        valor_restante = max(0.0, float(row['valor_total']) - valor_pago)
        status_pag = row.get('status_pagamento') or 'Pendente'

        with st.container(border=True, key=f"card_receber_{row['id']}"):
            c_inf, c_val, c_btn = st.columns([4, 2, 2], vertical_alignment="center")
            with c_inf:
                st.markdown(f"**OS Nº {row['id']} — {placa}**  ·  {n_txt}  ·  {row['data_servico']}")
                st.badge(status_pag, color=COR_STATUS_PAGAMENTO.get(status_pag, "gray"))
            with c_val:
                st.markdown("Restante")
                st.markdown(f"#### :red[R$ {valor_restante:,.2f}]")
                st.caption(f"Total: R$ {row['valor_total']:,.2f} · Pago: R$ {valor_pago:,.2f}")
            with c_btn:
                if st.button("Gerenciar pagamento", key=f"pagar_{row['id']}", icon=":material/payments:", width="stretch"):
                    gerenciar_pagamento(row.to_dict(), n_txt)
