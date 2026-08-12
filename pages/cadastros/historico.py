import streamlit as st
from utils.dados import (
    buscar_veiculos, buscar_clientes, buscar_orcamentos, buscar_servicos, montar_veiculo_e_cliente,
    COR_STATUS_ORCAMENTO, COR_STATUS_PAGAMENTO,
)
from utils.gerador_pdf import gerar_relatorio_historico_veiculo
from utils.auth import usuario_atual
from utils.imagens import url_valida, lista_urls
import pandas as pd
import json

st.set_page_config(layout="wide", page_title="Histórico do Veículo | Sanini & Aimi")
st.title("Histórico do veículo", anchor=False)
st.caption("Linha do tempo com todos os orçamentos e ordens de serviço já registrados para o veículo.")

df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes()
df_orcamentos = buscar_orcamentos()
df_servicos = buscar_servicos()

lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []

if not lista_placas:
    st.info("Nenhum veículo cadastrado ainda.")
    st.stop()

placa_pre_selecionada = st.session_state.pop("historico_placa_selecionada", None)
idx_placa = lista_placas.index(placa_pre_selecionada) if placa_pre_selecionada in lista_placas else 0
placa_selecionada = st.selectbox("Veículo (placa)", lista_placas, index=idx_placa, key="hist_placa_sel")

veic, cli = montar_veiculo_e_cliente(df_veiculos, df_clientes, placa_selecionada)

with st.container(border=True):
    st.markdown(f"#### {veic.get('marca', '')} {veic.get('modelo', '')} ({veic.get('ano', 'N/A')})")
    st.write(f"Placa: `{placa_selecionada}`  ·  Chassi: `{veic.get('chassi') or 'Não informado'}`")
    if cli:
        st.write(f":material/person: {cli.get('nome', 'N/A')}  ·  {cli.get('telefone', 'N/A')}")
    else:
        st.write(":material/person_off: Cliente não vinculado")

eventos = []
if not df_orcamentos.empty:
    for _, row in df_orcamentos[df_orcamentos['placa_veiculo'] == placa_selecionada].iterrows():
        eventos.append({"tipo": "orcamento", "data": str(row.get('data', '')), "row": row})
if not df_servicos.empty:
    for _, row in df_servicos[df_servicos['placa_veiculo'] == placa_selecionada].iterrows():
        eventos.append({"tipo": "servico", "data": str(row.get('data_servico', '')), "row": row})

eventos.sort(key=lambda e: e["data"], reverse=True)

col_ftipo, col_fperiodo = st.columns([1.5, 2])
with col_ftipo:
    f_tipo_hist = st.segmented_control(
        "Tipo de registro", ["Todos", "Orçamentos", "Serviços"], default="Todos", key="hist_f_tipo",
    )
with col_fperiodo:
    f_periodo_hist = st.date_input("Período (início e fim)", [], key="hist_f_periodo")

if f_tipo_hist == "Orçamentos":
    eventos = [e for e in eventos if e["tipo"] == "orcamento"]
elif f_tipo_hist == "Serviços":
    eventos = [e for e in eventos if e["tipo"] == "servico"]

if len(f_periodo_hist) == 2:
    eventos = [
        e for e in eventos
        if e["data"] and f_periodo_hist[0].isoformat() <= e["data"][:10] <= f_periodo_hist[1].isoformat()
    ]

if not eventos:
    st.info("Nenhum orçamento ou ordem de serviço encontrado para os filtros selecionados.")
else:
    col_cont, col_pdf = st.columns([4, 1.5], vertical_alignment="center")
    col_cont.markdown(f"**{len(eventos)} registro(s) no histórico**")
    with col_pdf:
        if st.button("Imprimir histórico (PDF)", icon=":material/picture_as_pdf:", width="stretch"):
            caminho_hist_pdf = gerar_relatorio_historico_veiculo(
                placa_selecionada, veic, cli, eventos,
                emitido_por=(usuario_atual() or {}).get("nome"),
            )
            with open(caminho_hist_pdf, "rb") as f_hist:
                st.download_button(
                    "Baixar PDF do histórico", data=f_hist,
                    file_name=f"Historico_{placa_selecionada}.pdf", mime="application/pdf",
                    icon=":material/download:",
                )

    for ev in eventos:
        row = ev["row"]
        chave_evento = f"{ev['tipo']}_{row['id']}"
        with st.container(border=True, key=f"card_{chave_evento}"):
            c1, c2, c3 = st.columns([1.3, 4, 1.7], vertical_alignment="center")
            with c1:
                if ev["tipo"] == "orcamento":
                    st.badge("Orçamento", icon=":material/list_alt:", color="blue")
                    st.caption(f"Nº {row['id']}")
                else:
                    st.badge("Ordem de serviço", icon=":material/build:", color="green")
                    st.caption(f"Nº {row['id']}")
            with c2:
                st.write(f"**{ev['data']}**")
                if ev["tipo"] == "orcamento":
                    st.caption(str(row.get('descricao_problema', ''))[:120])
                    st_atual = row.get('status', 'Pendente')
                    st.badge(st_atual, color=COR_STATUS_ORCAMENTO.get(st_atual, "gray"))
                else:
                    st.caption(str(row.get('descricao_servico', ''))[:120])
                    if pd.notna(row.get('orcamento_id')):
                        st.caption(f":material/link: Originada do Orçamento Nº {int(row['orcamento_id'])}")
                    status_pag = row.get('status_pagamento') or 'Pendente'
                    st.badge(status_pag, color=COR_STATUS_PAGAMENTO.get(status_pag, "gray"))
            with c3:
                st.markdown(f"##### :green[R$ {float(row.get('valor_total', 0)):,.2f}]")

            with st.expander("Ver detalhes", key=f"exp_{chave_evento}"):
                if ev["tipo"] == "orcamento":
                    pecas_val = row.get('pecas_necessarias', '')
                    servicos_val = row.get('servicos_orcados', '')
                else:
                    pecas_val = row.get('pecas_usadas', '')
                    servicos_val = row.get('servicos_executados', '')

                if pecas_val and str(pecas_val).startswith('['):
                    try:
                        lista_p = json.loads(pecas_val)
                        if lista_p:
                            st.markdown("**:material/build: Peças**")
                            st.dataframe(pd.DataFrame(lista_p), width="stretch", hide_index=True, key=f"df_pecas_{chave_evento}")
                    except Exception:
                        pass

                if servicos_val and str(servicos_val).startswith('['):
                    try:
                        lista_s = json.loads(servicos_val)
                        if lista_s:
                            st.markdown("**:material/construction: Serviços / mão de obra**")
                            st.dataframe(pd.DataFrame(lista_s), width="stretch", hide_index=True, key=f"df_servicos_{chave_evento}")
                    except Exception:
                        pass

                if ev["tipo"] == "servico":
                    fotos_val = lista_urls(row.get('urls_fotos'))
                    if fotos_val:
                        st.markdown("**:material/photo_camera: Registro fotográfico**")
                        cols_fotos = st.columns(min(4, len(fotos_val)))
                        for i, url in enumerate(fotos_val):
                            cols_fotos[i % len(cols_fotos)].image(url, width="stretch")

                if url_valida(row.get('assinatura_url')):
                    st.markdown("**:material/signature: Assinatura do cliente**")
                    st.image(row['assinatura_url'], width=200)
