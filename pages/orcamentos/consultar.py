import streamlit as st
from database import supabase
from utils.dados import buscar_veiculos, buscar_clientes, buscar_orcamentos, buscar_catalogo_servicos, montar_veiculo_e_cliente, OPCOES_STATUS_ORCAMENTO, COR_STATUS_ORCAMENTO
from utils.paginacao import paginar
from utils.gerador_pdf import gerar_relatorio_orcamento
from utils.auth import registrar_log, usuario_atual
from utils.imagens import converter_para_jpg_bytes, url_valida
import pandas as pd
import json
import time

st.set_page_config(layout="wide", page_title="Consultar Orçamentos | Sanini & Aimi")
st.title("Consultar orçamentos", anchor=False)

msg_sucesso_orc = st.session_state.pop("msg_sucesso_orc", None)
if msg_sucesso_orc:
    st.success(msg_sucesso_orc, icon=":material/check_circle:")

df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes()
df_orcamentos = buscar_orcamentos()
df_catalogo = buscar_catalogo_servicos()
lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []

OPCOES_STATUS = OPCOES_STATUS_ORCAMENTO
COR_STATUS = COR_STATUS_ORCAMENTO


def _tipos_servico_do_orcamento(row):
    val = row.get('servicos_orcados', '')
    if val and str(val).startswith('['):
        try:
            return [s.get('Serviço', '') for s in json.loads(val)]
        except Exception:
            return []
    return []


@st.dialog("Ficha do orçamento", width="large")
def ver_detalhes_orcamento(row, veic, cli):
    st_atual = row.get('status', 'Pendente')
    st.markdown(f"## Orçamento Nº {row['id']}")
    with st.container(horizontal=True, vertical_alignment="center"):
        st.badge(st_atual, color=COR_STATUS.get(st_atual, "gray"))
        st.caption(f"Data: {row.get('data', '')}")
    st.divider()

    col_c, col_v = st.columns(2)
    with col_c:
        st.markdown("**:material/person: Cliente**")
        st.write(cli.get('nome', 'N/A'))
        st.caption(f"Tel: {cli.get('telefone', 'N/A')} · E-mail: {cli.get('email') or 'N/A'}")
        st.caption(f"CPF/CNPJ: {cli.get('cpf_cnpj') or 'N/A'} · Endereço: {cli.get('endereco') or 'N/A'}")
    with col_v:
        st.markdown("**:material/directions_car: Veículo**")
        st.write(f"{veic.get('marca', '')} {veic.get('modelo', '')} ({veic.get('ano', 'N/A')})")
        st.caption(f"Placa: {row.get('placa_veiculo', '')} · Chassi: {veic.get('chassi') or 'N/A'}")

    st.divider()
    st.markdown("**Problema relatado**")
    st.write(row.get('descricao_problema') or "Não informado")

    pecas_val = row.get('pecas_necessarias', '')
    if pecas_val and str(pecas_val).startswith('['):
        try:
            lista_p = json.loads(pecas_val)
            if lista_p:
                st.markdown("**:material/build: Peças**")
                st.dataframe(pd.DataFrame(lista_p), width="stretch", hide_index=True)
        except Exception:
            pass

    servicos_val = row.get('servicos_orcados', '')
    if servicos_val and str(servicos_val).startswith('['):
        try:
            lista_s = json.loads(servicos_val)
            if lista_s:
                st.markdown("**:material/construction: Serviços / mão de obra**")
                st.dataframe(pd.DataFrame(lista_s), width="stretch", hide_index=True)
        except Exception:
            pass

    st.divider()
    st.markdown(f"### Valor total: :green[R$ {float(row.get('valor_total', 0)):,.2f}]")

    if url_valida(row.get('assinatura_url')):
        st.divider()
        st.markdown("**:material/signature: Assinatura do cliente**")
        st.image(row['assinatura_url'], width=250)


@st.dialog("Gerenciar orçamento", width="large")
def gerenciar_orcamento(row):
    st_atual = row.get('status', 'Pendente')
    idx = OPCOES_STATUS.index(st_atual) if st_atual in OPCOES_STATUS else 0
    novo_st = st.selectbox("Status", OPCOES_STATUS, index=idx, key=f"st_{row['id']}")
    if st.button("Salvar status", key=f"btn_st_{row['id']}", type="primary", icon=":material/save:"):
        supabase.table("orcamentos").update({"status": novo_st}).eq("id", row['id']).execute()
        registrar_log("editou", "orcamento", row['id'], f"status -> {novo_st}")
        st.cache_data.clear()
        st.session_state["msg_sucesso_orc"] = f"Status do orçamento Nº {row['id']} atualizado para {novo_st}."
        st.rerun()

    st.divider()
    if st.button("Editar orçamento", key=f"edit_{row['id']}", icon=":material/edit:"):
        try:
            st.session_state.lista_pecas_orc = json.loads(row.get('pecas_necessarias') or '[]')
        except Exception:
            st.session_state.lista_pecas_orc = []
        try:
            st.session_state.lista_servicos_orc = json.loads(row.get('servicos_orcados') or '[]')
        except Exception:
            st.session_state.lista_servicos_orc = []
        st.session_state["orc_editando_id"] = int(row['id'])
        st.session_state["orc_editando_placa"] = row['placa_veiculo']
        st.session_state["orc_editando_data"] = str(row.get('data'))
        st.session_state["orc_editando_status"] = row.get('status', 'Pendente')
        st.session_state["orc_editando_desc"] = row.get('descricao_problema') or ''
        st.switch_page("pages/orcamentos/novo.py")

    st.divider()
    if st.button("Gerar PDF deste orçamento", key=f"gen_pdf_{row['id']}", icon=":material/picture_as_pdf:"):
        veic_pdf, cli_pdf = montar_veiculo_e_cliente(df_veiculos, df_clientes, row['placa_veiculo'])
        caminho_pdf_ind = gerar_relatorio_orcamento(
            [{"orcamento": row, "veiculo": veic_pdf, "cliente": cli_pdf}],
            emitido_por=(usuario_atual() or {}).get("nome"),
        )
        with open(caminho_pdf_ind, "rb") as f_ind:
            st.download_button("Baixar PDF", data=f_ind, file_name=f"Orcamento_{row['id']}_{row['placa_veiculo']}.pdf", mime="application/pdf", key=f"pdf_ind_{row['id']}", icon=":material/download:")

    st.divider()
    st.markdown("**:material/signature: Assinatura do cliente**")
    versao_upload_assin_orc = st.session_state.get(f"assin_orc_ver_{row['id']}", 0)
    if url_valida(row.get('assinatura_url')):
        st.image(row['assinatura_url'], width=200)
        st.caption("Assinatura registrada.")
        nova_assinatura_orc = st.file_uploader("Substituir assinatura (qualquer imagem)", key=f"assin_orc_{row['id']}_{versao_upload_assin_orc}")
    else:
        st.caption("Nenhuma assinatura anexada ainda.")
        nova_assinatura_orc = st.file_uploader("Anexar assinatura (qualquer imagem)", key=f"assin_orc_{row['id']}_{versao_upload_assin_orc}")
    if st.button("Salvar assinatura", key=f"btnassin_orc_{row['id']}", icon=":material/save:"):
        if nova_assinatura_orc:
            try:
                jpg_bytes = converter_para_jpg_bytes(nova_assinatura_orc)
            except Exception:
                st.error("Não foi possível processar essa imagem. Tente outro arquivo.", icon=":material/error:")
                st.stop()
            nome_arq = f"assinatura_orcamento_{row['id']}_{time.time()}.jpg"
            supabase.storage.from_("fotos_mecanica").upload(nome_arq, jpg_bytes)
            url_assin = supabase.storage.from_("fotos_mecanica").get_public_url(nome_arq)
            supabase.table("orcamentos").update({"assinatura_url": url_assin}).eq("id", row['id']).execute()
            st.cache_data.clear()
            st.session_state[f"assin_orc_ver_{row['id']}"] = versao_upload_assin_orc + 1
            st.success("Assinatura salva com sucesso.", icon=":material/check_circle:")
            st.image(jpg_bytes, width=200)
            st.caption("Feche e reabra este painel para ver a assinatura atualizada na ficha.")
        else:
            st.warning("Selecione uma imagem antes de salvar.", icon=":material/warning:")

    st.divider()
    if st.button("Excluir orçamento", key=f"del_{row['id']}", icon=":material/delete:"):
        supabase.table("orcamentos").delete().eq("id", row['id']).execute()
        registrar_log("excluiu", "orcamento", row['id'])
        st.cache_data.clear()
        st.session_state["msg_sucesso_orc"] = "Orçamento excluído."
        st.rerun()


col_f1, col_f2, col_f3 = st.columns(3)
with col_f1: f_placa = st.selectbox("Placa", ["Todas"] + lista_placas, key="f_orc_p")
with col_f2:
    cli_filtro = ["Todos"] + df_clientes['nome'].tolist() if not df_clientes.empty else ["Todos"]
    f_cliente = st.selectbox("Cliente", cli_filtro, key="f_orc_c")
with col_f3:
    tipos_servico = ["Todos"] + df_catalogo['nome'].tolist() if not df_catalogo.empty else ["Todos"]
    f_tipo_servico = st.selectbox("Tipo de serviço", tipos_servico, key="f_orc_tipo_serv")

f_data = st.date_input("Período (início e fim)", [], key="f_orc_d")

f_status = st.pills("Status", OPCOES_STATUS, selection_mode="multi", key="f_orc_status")

busca_orc = st.text_input("Buscar por número, placa, cliente ou descrição do problema", icon=":material/search:")

df_filtrado = df_orcamentos.copy()
if not df_filtrado.empty:
    if f_placa != "Todas": df_filtrado = df_filtrado[df_filtrado['placa_veiculo'] == f_placa]
    if f_cliente != "Todos":
        id_cli = df_clientes[df_clientes['nome'] == f_cliente]['id'].values[0]
        placas_cli = df_veiculos[df_veiculos['cliente_id'] == id_cli]['placa'].tolist()
        df_filtrado = df_filtrado[df_filtrado['placa_veiculo'].isin(placas_cli)]
    if len(f_data) == 2:
        df_filtrado['data'] = pd.to_datetime(df_filtrado['data']).dt.date
        df_filtrado = df_filtrado[(df_filtrado['data'] >= f_data[0]) & (df_filtrado['data'] <= f_data[1])]
    if f_tipo_servico != "Todos":
        df_filtrado = df_filtrado[df_filtrado.apply(lambda r: f_tipo_servico in _tipos_servico_do_orcamento(r), axis=1)]
    if f_status:
        df_filtrado = df_filtrado[df_filtrado['status'].isin(f_status)]
    if busca_orc:
        termo = busca_orc.lower()

        def _bate_busca(row):
            v_row = df_veiculos[df_veiculos['placa'] == row['placa_veiculo']]
            cliente_txt = ""
            if not v_row.empty and not df_clientes.empty:
                c_id = v_row.iloc[0].get('cliente_id')
                c_row = df_clientes[df_clientes['id'] == c_id]
                if not c_row.empty:
                    cliente_txt = str(c_row.iloc[0]['nome'])
            campo = f"{row['id']} {row['placa_veiculo']} {cliente_txt} {row.get('descricao_problema', '')}".lower()
            return termo in campo

        df_filtrado = df_filtrado[df_filtrado.apply(_bate_busca, axis=1)]

if df_filtrado.empty:
    st.info("Nenhum orçamento encontrado com os filtros aplicados.")
else:
    cb1, cb2, _ = st.columns([2, 2, 6])
    if cb1.button("Selecionar todos", width="stretch", key="btn_all_orc1", icon=":material/select_all:"):
        for i in df_filtrado['id']: st.session_state[f"chk_orc1_{i}"] = True
        st.rerun()
    if cb2.button("Limpar seleção", width="stretch", key="btn_none_orc1", icon=":material/deselect:"):
        for i in df_filtrado['id']: st.session_state[f"chk_orc1_{i}"] = False
        st.rerun()

    ids_selecionados = [i for i in df_filtrado['id'] if st.session_state.get(f"chk_orc1_{i}", False)]

    st.markdown(
        f"**{len(df_filtrado)} orçamento(s) filtrado(s) — Valor total: "
        f"R$ {df_filtrado['valor_total'].sum():,.2f}**"
    )

    df_pagina = paginar(df_filtrado, "orc_consultar", por_pagina=10)

    for _, row in df_pagina.iterrows():
        cliente_txt = "Sem nome"
        veic_row = df_veiculos[df_veiculos['placa'] == row['placa_veiculo']] if not df_veiculos.empty else pd.DataFrame()
        if not veic_row.empty and not df_clientes.empty:
            c_id = veic_row.iloc[0].get('cliente_id')
            c_row = df_clientes[df_clientes['id'] == c_id]
            if not c_row.empty: cliente_txt = c_row.iloc[0]['nome']

        with st.container(border=True, key=f"card_orc_{row['id']}"):
            c_chk, c_inf, c_status, c_acao = st.columns([0.4, 4, 1, 1.4], vertical_alignment="center")
            with c_chk:
                st.checkbox("Selecionar", key=f"chk_orc1_{row['id']}", label_visibility="collapsed")
            with c_inf:
                st.markdown(f"#### Orçamento Nº {row['id']}  ·  {row['placa_veiculo']}  ·  {cliente_txt}")
                st.write(f"Data: {row['data']}  ·  {row.get('descricao_problema', '')}")

                pecas_val = row.get('pecas_necessarias', '')
                if pecas_val and str(pecas_val).startswith('['):
                    try:
                        lista_p = json.loads(pecas_val)
                        p_str = ", ".join([f"{p.get('Quantidade', 1)}x {p.get('Peça/Descrição', '')}" for p in lista_p])
                        st.caption(f"Peças: {p_str}")
                    except Exception:
                        st.caption(f"Peças: {pecas_val}")
                else:
                    st.caption(f"Peças: {pecas_val or 'N/A'}")

                servicos_val = row.get('servicos_orcados', '')
                if servicos_val and str(servicos_val).startswith('['):
                    try:
                        lista_s = json.loads(servicos_val)
                        s_str = ", ".join([f"{s.get('Serviço', '')} (R$ {s.get('Valor (R$)', 0):.2f})" for s in lista_s])
                        st.caption(f"Serviços: {s_str or 'N/A'}")
                    except Exception:
                        pass

                v_tot = row.get('valor_total', 0)
                st.markdown(f"**Valor estimado:** :green[R$ {float(v_tot):,.2f}]")
            with c_status:
                st_atual = row.get('status', 'Pendente')
                st.badge(st_atual, color=COR_STATUS.get(st_atual, "gray"))
            with c_acao:
                if st.button("Ver detalhes", key=f"ver_{row['id']}", icon=":material/visibility:", width="stretch"):
                    veic_det, cli_det = montar_veiculo_e_cliente(df_veiculos, df_clientes, row['placa_veiculo'])
                    ver_detalhes_orcamento(row.to_dict(), veic_det, cli_det)
                if st.button("Gerenciar", key=f"manage_{row['id']}", icon=":material/settings:", width="stretch"):
                    gerenciar_orcamento(row.to_dict())

    if ids_selecionados:
        st.markdown(f"**{len(ids_selecionados)} orçamento(s) selecionado(s).**")
        if st.button(f"Emitir orçamentos selecionados ({len(ids_selecionados)})", type="primary", width="stretch", key="btn_print_sel_orc1", icon=":material/print:"):
            lote = []
            for oid in ids_selecionados:
                orc_row = df_filtrado[df_filtrado['id'] == oid].iloc[0].to_dict()
                veic_pdf, cli_pdf = montar_veiculo_e_cliente(df_veiculos, df_clientes, orc_row['placa_veiculo'])
                lote.append({"orcamento": orc_row, "veiculo": veic_pdf, "cliente": cli_pdf})
            caminho_lote = gerar_relatorio_orcamento(lote, emitido_por=(usuario_atual() or {}).get("nome"))
            with open(caminho_lote, "rb") as f_lote:
                st.download_button("Baixar PDF dos selecionados", data=f_lote, file_name="Orcamentos_Selecionados.pdf", mime="application/pdf", icon=":material/download:")
    else:
        st.caption("Marque a caixa ao lado de cada orçamento (ou use \"Selecionar todos\") para imprimir todos os que você filtrou acima.")
