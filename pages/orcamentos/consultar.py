import streamlit as st
from database import supabase
from utils.dados import buscar_veiculos, buscar_clientes, buscar_orcamentos, buscar_catalogo_servicos, montar_veiculo_e_cliente
from utils.paginacao import paginar
from utils.gerador_pdf import gerar_relatorio_orcamento
import pandas as pd
import json
import time

st.set_page_config(layout="wide", page_title="Consultar Orçamentos | Sanini & Aimi")
st.title("📋 Consultar Orçamentos")

df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes()
df_orcamentos = buscar_orcamentos()
df_catalogo = buscar_catalogo_servicos()
lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []


def _tipos_servico_do_orcamento(row):
    val = row.get('servicos_orcados', '')
    if val and str(val).startswith('['):
        try:
            return [s.get('Serviço', '') for s in json.loads(val)]
        except Exception:
            return []
    return []


@st.dialog("📝 Ficha do Orçamento", width="large")
def ver_detalhes_orcamento(row, veic, cli):
    st_atual = row.get('status', 'Pendente')
    cor = "green" if st_atual == "Aprovado" else "orange" if st_atual == "Pendente" else "gray"
    st.markdown(f"## Orçamento Nº {row['id']}")
    st.markdown(f"**Status:** <span style='color:{cor};'>{st_atual}</span> &nbsp;|&nbsp; **Data:** {row.get('data', '')}", unsafe_allow_html=True)
    st.divider()

    col_c, col_v = st.columns(2)
    with col_c:
        st.markdown("**👤 Cliente**")
        st.write(cli.get('nome', 'N/A'))
        st.caption(f"Tel: {cli.get('telefone', 'N/A')} | E-mail: {cli.get('email') or 'N/A'}")
        st.caption(f"CPF/CNPJ: {cli.get('cpf_cnpj') or 'N/A'} | Endereço: {cli.get('endereco') or 'N/A'}")
    with col_v:
        st.markdown("**🚗 Veículo**")
        st.write(f"{veic.get('marca', '')} {veic.get('modelo', '')} ({veic.get('ano', 'N/A')})")
        st.caption(f"Placa: {row.get('placa_veiculo', '')} | Chassi: {veic.get('chassi') or 'N/A'}")

    st.divider()
    st.markdown("**Problema Relatado**")
    st.write(row.get('descricao_problema') or "Não informado")

    pecas_val = row.get('pecas_necessarias', '')
    if pecas_val and str(pecas_val).startswith('['):
        try:
            lista_p = json.loads(pecas_val)
            if lista_p:
                st.markdown("**🔧 Peças**")
                st.dataframe(pd.DataFrame(lista_p), use_container_width=True, hide_index=True)
        except Exception:
            pass

    servicos_val = row.get('servicos_orcados', '')
    if servicos_val and str(servicos_val).startswith('['):
        try:
            lista_s = json.loads(servicos_val)
            if lista_s:
                st.markdown("**🛠️ Serviços / Mão de Obra**")
                st.dataframe(pd.DataFrame(lista_s), use_container_width=True, hide_index=True)
        except Exception:
            pass

    st.divider()
    st.markdown(f"### Valor Total: <span style='color:green;'>R$ {float(row.get('valor_total', 0)):,.2f}</span>", unsafe_allow_html=True)

    if row.get('assinatura_url'):
        st.divider()
        st.markdown("**🖊️ Assinatura do Cliente**")
        st.image(row['assinatura_url'], width=250)


col_f1, col_f2, col_f3, col_f4 = st.columns(4)
with col_f1: f_placa = st.selectbox("Filtrar por Placa", ["Todas"] + lista_placas, key="f_orc_p")
with col_f2:
    cli_filtro = ["Todos"] + df_clientes['nome'].tolist() if not df_clientes.empty else ["Todos"]
    f_cliente = st.selectbox("Filtrar por Cliente", cli_filtro, key="f_orc_c")
with col_f3: f_data = st.date_input("Período (Início e Fim)", [], key="f_orc_d")
with col_f4:
    tipos_servico = ["Todos"] + df_catalogo['nome'].tolist() if not df_catalogo.empty else ["Todos"]
    f_tipo_servico = st.selectbox("Filtrar por Tipo de Serviço", tipos_servico, key="f_orc_tipo_serv")

busca_orc = st.text_input("🔍 Buscar por placa, cliente ou descrição do problema...")

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
            campo = f"{row['placa_veiculo']} {cliente_txt} {row.get('descricao_problema', '')}".lower()
            return termo in campo

        df_filtrado = df_filtrado[df_filtrado.apply(_bate_busca, axis=1)]

st.divider()
if df_filtrado.empty:
    st.info("Nenhum orçamento encontrado com os filtros aplicados.")
else:
    cb1, cb2, _ = st.columns([2, 2, 6])
    if cb1.button("☑️ Selecionar Todos", use_container_width=True, key="btn_all_orc1"):
        for i in df_filtrado['id']: st.session_state[f"chk_orc1_{i}"] = True
        st.rerun()
    if cb2.button("☐ Limpar Seleção", use_container_width=True, key="btn_none_orc1"):
        for i in df_filtrado['id']: st.session_state[f"chk_orc1_{i}"] = False
        st.rerun()

    ids_selecionados = [i for i in df_filtrado['id'] if st.session_state.get(f"chk_orc1_{i}", False)]

    st.markdown(
        f"**{len(df_filtrado)} orçamento(s) filtrado(s) — Valor total: "
        f"R$ {df_filtrado['valor_total'].sum():,.2f}**"
    )
    st.divider()

    df_pagina = paginar(df_filtrado, "orc_consultar", por_pagina=10)

    for _, row in df_pagina.iterrows():
        cliente_txt = "Sem Nome"
        veic_row = df_veiculos[df_veiculos['placa'] == row['placa_veiculo']] if not df_veiculos.empty else pd.DataFrame()
        if not veic_row.empty and not df_clientes.empty:
            c_id = veic_row.iloc[0].get('cliente_id')
            c_row = df_clientes[df_clientes['id'] == c_id]
            if not c_row.empty: cliente_txt = c_row.iloc[0]['nome']

        with st.container(border=True):
            c_chk, c_inf, c_status, c_acao = st.columns([0.4, 4, 1, 1])
            with c_chk:
                st.markdown("<br>", unsafe_allow_html=True)
                st.checkbox("", key=f"chk_orc1_{row['id']}")
            with c_inf:
                st.markdown(f"### 📝 Orçamento Nº {row['id']} &nbsp;|&nbsp; 🚗 {row['placa_veiculo']} &nbsp;|&nbsp; 👤 {cliente_txt}")
                st.write(f"**Data:** {row['data']} | **Problema:** {row.get('descricao_problema', '')}")

                pecas_val = row.get('pecas_necessarias', '')
                if pecas_val and str(pecas_val).startswith('['):
                    try:
                        lista_p = json.loads(pecas_val)
                        p_str = ", ".join([f"{p.get('Quantidade', 1)}x {p.get('Peça/Descrição', '')}" for p in lista_p])
                        st.caption(f"**Peças:** {p_str}")
                    except Exception:
                        st.caption(f"**Peças:** {pecas_val}")
                else:
                    st.caption(f"**Peças:** {pecas_val or 'N/A'}")

                servicos_val = row.get('servicos_orcados', '')
                if servicos_val and str(servicos_val).startswith('['):
                    try:
                        lista_s = json.loads(servicos_val)
                        s_str = ", ".join([f"{s.get('Serviço', '')} (R$ {s.get('Valor (R$)', 0):.2f})" for s in lista_s])
                        st.caption(f"**Serviços:** {s_str or 'N/A'}")
                    except Exception:
                        pass

                v_tot = row.get('valor_total', 0)
                st.markdown(f"**Valor Estimado:** <span style='color:green;'>R$ {float(v_tot):,.2f}</span>", unsafe_allow_html=True)
            with c_status:
                st.markdown("<br>", unsafe_allow_html=True)
                st_atual = row.get('status', 'Pendente')
                cor = "green" if st_atual == "Aprovado" else "orange" if st_atual == "Pendente" else "gray"
                st.markdown(f"<h4 style='color: {cor};'>{st_atual}</h4>", unsafe_allow_html=True)
            with c_acao:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔍 Ver Detalhes", key=f"ver_{row['id']}", use_container_width=True):
                    veic_det, cli_det = montar_veiculo_e_cliente(df_veiculos, df_clientes, row['placa_veiculo'])
                    ver_detalhes_orcamento(row.to_dict(), veic_det, cli_det)
                with st.popover("⚙️ Gerenciar", use_container_width=True):
                    opcoes = ["Pendente", "Aprovado", "Em Execução", "Finalizado", "Cancelado"]
                    idx = opcoes.index(st_atual) if st_atual in opcoes else 0
                    novo_st = st.selectbox("Status", opcoes, index=idx, key=f"st_{row['id']}")
                    if st.button("💾 Salvar Status", key=f"btn_st_{row['id']}", type="primary", use_container_width=True):
                        supabase.table("orcamentos").update({"status": novo_st}).eq("id", row['id']).execute()
                        st.cache_data.clear()
                        st.toast("✅ Status Atualizado!")
                        time.sleep(0.5); st.rerun()

                    st.divider()
                    if st.button("✏️ Editar Orçamento", key=f"edit_{row['id']}", use_container_width=True):
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
                    if st.button("📄 Gerar PDF deste Orçamento", key=f"gen_pdf_{row['id']}", use_container_width=True):
                        veic_pdf, cli_pdf = montar_veiculo_e_cliente(df_veiculos, df_clientes, row['placa_veiculo'])
                        caminho_pdf_ind = gerar_relatorio_orcamento([{"orcamento": row.to_dict(), "veiculo": veic_pdf, "cliente": cli_pdf}])
                        with open(caminho_pdf_ind, "rb") as f_ind:
                            st.download_button("📥 Baixar PDF", data=f_ind, file_name=f"Orcamento_{row['id']}.pdf", mime="application/pdf", key=f"pdf_ind_{row['id']}", use_container_width=True)

                    st.divider()
                    st.markdown("**🖊️ Assinatura do Cliente**")
                    if row.get('assinatura_url'):
                        st.image(row['assinatura_url'], width=200)
                        st.caption("Assinatura registrada.")
                        nova_assinatura_orc = st.file_uploader("Substituir assinatura", type=['png', 'jpg', 'jpeg'], key=f"assin_orc_{row['id']}")
                    else:
                        st.caption("Nenhuma assinatura anexada ainda.")
                        nova_assinatura_orc = st.file_uploader("Anexar assinatura (foto/imagem)", type=['png', 'jpg', 'jpeg'], key=f"assin_orc_{row['id']}")
                    if st.button("💾 Salvar Assinatura", key=f"btnassin_orc_{row['id']}", use_container_width=True):
                        if nova_assinatura_orc:
                            ext = nova_assinatura_orc.name.split('.')[-1]
                            nome_arq = f"assinatura_orcamento_{row['id']}_{time.time()}.{ext}"
                            supabase.storage.from_("fotos_mecanica").upload(nome_arq, nova_assinatura_orc.getvalue())
                            url_assin = supabase.storage.from_("fotos_mecanica").get_public_url(nome_arq)
                            supabase.table("orcamentos").update({"assinatura_url": url_assin}).eq("id", row['id']).execute()
                            st.cache_data.clear()
                            st.toast("✅ Assinatura registrada!")
                            time.sleep(0.5)
                            st.rerun()
                    st.divider()
                    if st.button("🗑️ Excluir", key=f"del_{row['id']}", use_container_width=True):
                        supabase.table("orcamentos").delete().eq("id", row['id']).execute()
                        st.cache_data.clear()
                        st.toast("🗑️ Orçamento Excluído!"); time.sleep(0.5); st.rerun()

    st.divider()
    if ids_selecionados:
        st.markdown(f"**{len(ids_selecionados)} orçamento(s) selecionado(s).**")
        if st.button(f"🖨️ Emitir Orçamentos Selecionados ({len(ids_selecionados)})", type="primary", use_container_width=True, key="btn_print_sel_orc1"):
            lote = []
            for oid in ids_selecionados:
                orc_row = df_filtrado[df_filtrado['id'] == oid].iloc[0].to_dict()
                veic_pdf, cli_pdf = montar_veiculo_e_cliente(df_veiculos, df_clientes, orc_row['placa_veiculo'])
                lote.append({"orcamento": orc_row, "veiculo": veic_pdf, "cliente": cli_pdf})
            caminho_lote = gerar_relatorio_orcamento(lote)
            with open(caminho_lote, "rb") as f_lote:
                st.download_button("📥 Baixar PDF dos Selecionados", data=f_lote, file_name="Orcamentos_Selecionados.pdf", mime="application/pdf", use_container_width=True)
    else:
        st.caption("Marque a caixa ao lado de cada orçamento (ou use \"Selecionar Todos\" para imprimir todos os que você filtrou acima).")
