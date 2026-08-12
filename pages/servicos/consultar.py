import streamlit as st
from database import supabase
from utils.dados import (
    buscar_veiculos, buscar_clientes, buscar_servicos, montar_veiculo_e_cliente,
    COR_STATUS_PAGAMENTO, COR_STATUS_OS, OPCOES_STATUS_OS,
)
from utils.auth import registrar_log, usuario_atual
from utils.imagens import converter_para_jpg_bytes, url_valida, lista_urls
from utils.paginacao import paginar
from utils.gerador_pdf import gerar_relatorio_servico
import pandas as pd
import json
import time
import uuid
import re

st.set_page_config(layout="wide", page_title="Ordens de Serviço | Sanini & Aimi")
st.title("Consultar ordens de serviço", anchor=False)

os_recem_registrada = st.session_state.pop("os_recem_registrada", None)
if os_recem_registrada:
    st.success(f"Ordem de serviço Nº {os_recem_registrada} registrada com sucesso.", icon=":material/check_circle:")

msg_sucesso_os = st.session_state.pop("msg_sucesso_os", None)
if msg_sucesso_os:
    st.success(msg_sucesso_os, icon=":material/check_circle:")

df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes()
df_servicos = buscar_servicos()
lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []


@st.dialog("Ficha da ordem de serviço", width="large")
def ver_detalhes_servico(row, veic, cli):
    st.markdown(f"## OS Nº {row['id']}  ·  {row['placa_veiculo']}")
    st.caption(f"Data: {row.get('data_servico', '')}")
    if pd.notna(row.get('orcamento_id')):
        st.caption(f":material/link: Originada do Orçamento Nº {int(row['orcamento_id'])}")
    st.divider()

    col_c, col_v = st.columns(2)
    with col_c:
        st.markdown("**:material/person: Cliente**")
        st.write(cli.get('nome', 'N/A'))
        st.caption(f"Tel: {cli.get('telefone', 'N/A')} · E-mail: {cli.get('email') or 'N/A'}")
    with col_v:
        st.markdown("**:material/directions_car: Veículo**")
        st.write(f"{veic.get('marca', '')} {veic.get('modelo', '')} ({veic.get('ano', 'N/A')})")
        st.caption(f"Chassi: {veic.get('chassi') or 'N/A'}")

    st.divider()
    st.markdown("**Mão de obra relatada**")
    st.write(row.get('descricao_servico') or "Não informado")

    pecas_val = row.get('pecas_usadas', '')
    if pecas_val and str(pecas_val).startswith('['):
        try:
            lista_p = json.loads(pecas_val)
            if lista_p:
                st.markdown("**:material/build: Peças**")
                st.dataframe(pd.DataFrame(lista_p), width="stretch", hide_index=True)
        except Exception:
            pass

    servicos_val = row.get('servicos_executados', '')
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

    fotos_val = lista_urls(row.get('urls_fotos'))
    if fotos_val:
        st.divider()
        st.markdown("**:material/photo_camera: Registro fotográfico**")
        cols_fotos = st.columns(min(4, len(fotos_val)))
        for i, url in enumerate(fotos_val):
            cols_fotos[i % len(cols_fotos)].image(url, width="stretch")

    if url_valida(row.get('assinatura_url')):
        st.divider()
        st.markdown("**:material/signature: Assinatura do cliente**")
        st.image(row['assinatura_url'], width=250)


@st.dialog("Gerenciar ordem de serviço", width="large")
def gerenciar_servico(row, n_txt, cli_tel, cli_email, cli_doc=""):
    status_os_atual = row.get('status_os') or 'Em Andamento'
    status_pag_atual = row.get('status_pagamento') or 'Pendente'
    with st.container(horizontal=True):
        st.badge(status_os_atual, icon=":material/build_circle:", color=COR_STATUS_OS.get(status_os_atual, "gray"))
        st.badge(status_pag_atual, icon=":material/payments:", color=COR_STATUS_PAGAMENTO.get(status_pag_atual, "gray"))
    st.caption("O controle de pagamento é feito em Gestão → Contas a receber.")

    with st.container(horizontal=True):
        if status_os_atual == "Em Andamento":
            if st.button("Editar peças e serviços", key=f"editaros_{row['id']}", icon=":material/edit:"):
                try:
                    st.session_state.lista_pecas = json.loads(row.get('pecas_usadas') or '[]')
                except Exception:
                    st.session_state.lista_pecas = []
                try:
                    st.session_state.lista_servicos_exec = json.loads(row.get('servicos_executados') or '[]')
                except Exception:
                    st.session_state.lista_servicos_exec = []
                st.session_state["os_editando_id"] = int(row['id'])
                st.session_state["os_editando_placa"] = row['placa_veiculo']
                st.session_state["os_editando_data"] = str(row.get('data_servico'))
                st.session_state["os_editando_pecas_originais"] = row.get('pecas_usadas') or '[]'
                st.session_state["descricao_serv_txt"] = row.get('descricao_servico') or ''
                st.switch_page("pages/servicos/nova_os.py")
            if st.button("Finalizar ordem de serviço", key=f"finalizaros_{row['id']}", icon=":material/task_alt:", type="primary"):
                supabase.table("servicos_realizados").update({"status_os": "Finalizada"}).eq("id", row['id']).execute()
                registrar_log("editou", "servico", row['id'], "status_os -> Finalizada")
                if pd.notna(row.get('orcamento_id')):
                    supabase.table("orcamentos").update({"status": "Finalizado"}).eq("id", int(row['orcamento_id'])).execute()
                    registrar_log("editou", "orcamento", int(row['orcamento_id']), "status -> Finalizado (OS finalizada)")
                st.cache_data.clear()
                st.session_state["msg_sucesso_os"] = f"OS Nº {row['id']} finalizada."
                st.rerun()
        else:
            st.caption("OS finalizada. Peças e serviços não podem mais ser editados.")
            if st.button("Reabrir para edição", key=f"reabriros_{row['id']}", icon=":material/lock_open:"):
                supabase.table("servicos_realizados").update({"status_os": "Em Andamento"}).eq("id", row['id']).execute()
                registrar_log("editou", "servico", row['id'], "status_os -> Em Andamento")
                st.cache_data.clear()
                st.session_state["msg_sucesso_os"] = f"OS Nº {row['id']} reaberta para edição."
                st.rerun()

    if status_os_atual == "Em Andamento":
        if not url_valida(row.get('assinatura_url')):
            st.info("Ao finalizar e registrar a assinatura do cliente, a OS aparece em Contas a Receber.", icon=":material/info:")

    st.divider()
    if st.button("Emitir dossiê técnico (PDF)", key=f"pdf_{row['id']}", icon=":material/picture_as_pdf:"):
        veic = df_veiculos[df_veiculos['placa'] == row['placa_veiculo']].iloc[0].to_dict()
        veic['cliente_nome'] = n_txt
        veic['cliente_telefone'] = cli_tel
        veic['cliente_documento'] = cli_doc
        orcs = supabase.table("orcamentos").select("*").eq("placa_veiculo", row['placa_veiculo']).execute().data
        caminho_pdf = gerar_relatorio_servico(
            row['placa_veiculo'], veic, orcs, [row],
            emitido_por=(usuario_atual() or {}).get("nome"),
        )
        with open(caminho_pdf, "rb") as pdf_file:
            st.download_button("Baixar arquivo", data=pdf_file, file_name=f"OS_{row['id']}_{row['placa_veiculo']}.pdf", mime="application/pdf", icon=":material/download:")

    with st.container(horizontal=True):
        if cli_tel:
            clean_tel = "".join(filter(str.isdigit, cli_tel))
            st.link_button("WhatsApp", f"https://wa.me/{clean_tel}", icon=":material/chat:")
        if cli_email:
            st.link_button("E-mail", f"mailto:{cli_email}", icon=":material/mail:")

    st.divider()
    st.markdown("**:material/photo_camera: Fotos do serviço**")
    fotos_atuais = lista_urls(row.get('urls_fotos'))
    if fotos_atuais:
        for idx_foto, url_foto in enumerate(fotos_atuais):
            fc1, fc2 = st.columns([4, 1])
            fc1.image(url_foto, width=120)
            if fc2.button("", key=f"delfoto_{row['id']}_{idx_foto}", icon=":material/delete:"):
                restantes = [u for j, u in enumerate(fotos_atuais) if j != idx_foto]
                supabase.table("servicos_realizados").update({"urls_fotos": ",".join(restantes)}).eq("id", row['id']).execute()
                st.cache_data.clear()
                st.rerun()
    else:
        st.caption("Nenhuma foto registrada ainda.")
    versao_upload_foto = st.session_state.get(f"fotos_ver_{row['id']}", 0)
    novas_fotos = st.file_uploader("Adicionar fotos", accept_multiple_files=True, key=f"addfoto_{row['id']}_{versao_upload_foto}")
    if st.button("Anexar fotos ao registro", key=f"btnfoto_{row['id']}", icon=":material/upload:"):
        if novas_fotos:
            urls_novas = []
            fotos_com_falha = []
            for foto in novas_fotos:
                try:
                    try:
                        conteudo_foto = converter_para_jpg_bytes(foto)
                        extensao_foto = "jpg"
                    except Exception:
                        conteudo_foto = foto.getvalue()
                        extensao_foto = foto.name.split('.')[-1] if '.' in foto.name else "bin"
                    nome_seguro = re.sub(r'[^A-Za-z0-9._-]', '_', foto.name.rsplit('.', 1)[0])
                    nome_arquivo = f"{row['placa_veiculo']}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}_{nome_seguro}.{extensao_foto}"
                    supabase.storage.from_("fotos_mecanica").upload(nome_arquivo, conteudo_foto)
                    urls_novas.append(supabase.storage.from_("fotos_mecanica").get_public_url(nome_arquivo))
                except Exception as e:
                    fotos_com_falha.append(f"{foto.name} ({e})")
            if fotos_com_falha:
                st.warning("Não foi possível enviar: " + "; ".join(fotos_com_falha), icon=":material/warning:")
            supabase.table("servicos_realizados").update({"urls_fotos": ",".join(fotos_atuais + urls_novas)}).eq("id", row['id']).execute()
            st.cache_data.clear()
            st.session_state[f"fotos_ver_{row['id']}"] = versao_upload_foto + 1
            if urls_novas:
                st.success(f"{len(urls_novas)} foto(s) adicionada(s) com sucesso.", icon=":material/check_circle:")
                st.caption("Feche e reabra este painel para ver as fotos atualizadas na ficha.")
        else:
            st.warning("Selecione ao menos uma foto antes de anexar.", icon=":material/warning:")

    st.divider()
    st.markdown("**:material/signature: Assinatura do cliente**")
    versao_upload_assin = st.session_state.get(f"assin_ver_{row['id']}", 0)
    if url_valida(row.get('assinatura_url')):
        st.image(row['assinatura_url'], width=200)
        st.caption("Assinatura registrada.")
        nova_assinatura = st.file_uploader("Substituir assinatura (qualquer imagem)", key=f"assin_{row['id']}_{versao_upload_assin}")
    else:
        st.caption("Nenhuma assinatura anexada ainda.")
        nova_assinatura = st.file_uploader("Anexar assinatura (qualquer imagem)", key=f"assin_{row['id']}_{versao_upload_assin}")
    if st.button("Salvar assinatura", key=f"btnassin_{row['id']}", icon=":material/save:"):
        if nova_assinatura:
            try:
                jpg_bytes = converter_para_jpg_bytes(nova_assinatura)
            except Exception:
                st.error("Não foi possível processar essa imagem. Tente outro arquivo.", icon=":material/error:")
                st.stop()
            nome_arq = f"assinatura_servico_{row['id']}_{time.time()}.jpg"
            supabase.storage.from_("fotos_mecanica").upload(nome_arq, jpg_bytes)
            url_assin = supabase.storage.from_("fotos_mecanica").get_public_url(nome_arq)
            supabase.table("servicos_realizados").update({"assinatura_url": url_assin}).eq("id", row['id']).execute()
            st.cache_data.clear()
            st.session_state[f"assin_ver_{row['id']}"] = versao_upload_assin + 1
            st.success("Assinatura salva com sucesso.", icon=":material/check_circle:")
            st.image(jpg_bytes, width=200)
            st.caption("Feche e reabra este painel para ver a assinatura atualizada na ficha.")
        else:
            st.warning("Selecione uma imagem antes de salvar.", icon=":material/warning:")

    st.divider()
    if st.button("Excluir ordem de serviço", key=f"dels_{row['id']}", icon=":material/delete:"):
        supabase.table("servicos_realizados").delete().eq("id", row['id']).execute()
        registrar_log("excluiu", "servico", row['id'])
        st.cache_data.clear()
        st.session_state["msg_sucesso_os"] = "Ordem de serviço excluída."
        st.rerun()


col_f1, col_f2, col_f3 = st.columns(3)
with col_f1: f_placa_serv = st.selectbox("Placa", ["Todas"] + lista_placas, key="f1_placa")
with col_f2:
    cli_filtro = ["Todos"] + df_clientes['nome'].tolist() if not df_clientes.empty else ["Todos"]
    f_cli_serv = st.selectbox("Cliente", cli_filtro, key="f1_cli")
with col_f3: f_data_serv = st.date_input("Período (início e fim)", [], key="f1_data")

f_status_os = st.pills("Status da OS", OPCOES_STATUS_OS, selection_mode="multi", key="f1_status_os")

busca_os = st.text_input("Buscar por número, placa, cliente ou descrição do serviço", icon=":material/search:")

df_filtrado_s = df_servicos.copy()
if not df_filtrado_s.empty:
    if f_placa_serv != "Todas": df_filtrado_s = df_filtrado_s[df_filtrado_s['placa_veiculo'] == f_placa_serv]
    if f_cli_serv != "Todos":
        id_cli = df_clientes[df_clientes['nome'] == f_cli_serv]['id'].values[0]
        placas_cli = df_veiculos[df_veiculos['cliente_id'] == id_cli]['placa'].tolist()
        df_filtrado_s = df_filtrado_s[df_filtrado_s['placa_veiculo'].isin(placas_cli)]
    if len(f_data_serv) == 2:
        df_filtrado_s['data_servico'] = pd.to_datetime(df_filtrado_s['data_servico']).dt.date
        df_filtrado_s = df_filtrado_s[(df_filtrado_s['data_servico'] >= f_data_serv[0]) & (df_filtrado_s['data_servico'] <= f_data_serv[1])]
    if f_status_os:
        df_filtrado_s = df_filtrado_s[df_filtrado_s['status_os'].fillna('Em Andamento').isin(f_status_os)]
    if busca_os:
        termo = busca_os.lower()

        def _bate_busca_os(row):
            v_row = df_veiculos[df_veiculos['placa'] == row['placa_veiculo']]
            cliente_txt = ""
            if not v_row.empty and not df_clientes.empty:
                c_id = v_row.iloc[0].get('cliente_id')
                c_row = df_clientes[df_clientes['id'] == c_id]
                if not c_row.empty:
                    cliente_txt = str(c_row.iloc[0]['nome'])
            campo = f"{row['id']} {row['placa_veiculo']} {cliente_txt} {row.get('descricao_servico', '')}".lower()
            return termo in campo

        df_filtrado_s = df_filtrado_s[df_filtrado_s.apply(_bate_busca_os, axis=1)]

if df_filtrado_s.empty:
    st.info("Nenhuma ordem de serviço registrada.")
else:
    st.markdown(
        f"**{len(df_filtrado_s)} ordem(ns) de serviço filtrada(s) — Valor total: "
        f"R$ {df_filtrado_s['valor_total'].sum():,.2f}**"
    )

    df_pagina = paginar(df_filtrado_s, "os_consultar", por_pagina=10)

    for _, row in df_pagina.iterrows():
        placa = row['placa_veiculo']
        n_txt, cli_tel, cli_email, cli_doc = "Sem nome", "", "", ""
        veic_row = df_veiculos[df_veiculos['placa'] == placa]
        if not veic_row.empty:
            c_id = veic_row.iloc[0].get('cliente_id')
            if pd.notna(c_id):
                cli_row = df_clientes[df_clientes['id'] == c_id]
                if not cli_row.empty:
                    n_txt = cli_row.iloc[0]['nome']
                    cli_tel = str(cli_row.iloc[0].get('telefone', ''))
                    cli_email = str(cli_row.iloc[0].get('email', ''))
                    cli_doc = str(cli_row.iloc[0].get('cpf_cnpj', '') or '')

        with st.container(border=True, key=f"card_os_{row['id']}"):
            c_inf, c_val, c_btn = st.columns([5, 2, 2], vertical_alignment="center")
            with c_inf:
                orc_ref = row.get('orcamento_id')
                vinculo_txt = f"  ·  :material/link: Orçamento Nº {int(orc_ref)}" if pd.notna(orc_ref) else ""
                st.markdown(f"**OS Nº {row['id']} — {row['placa_veiculo']}**  ·  {n_txt}  ·  {row['data_servico']}{vinculo_txt}")
                st.write(f"*{str(row['descricao_servico'])[:100]}...*")
                status_os_card = row.get('status_os') or 'Em Andamento'
                status_pag = row.get('status_pagamento') or 'Pendente'
                with st.container(horizontal=True):
                    st.badge(status_os_card, color=COR_STATUS_OS.get(status_os_card, "gray"))
                    st.badge(status_pag, color=COR_STATUS_PAGAMENTO.get(status_pag, "gray"))
            with c_val:
                st.markdown("Total")
                st.markdown(f"#### :green[R$ {row['valor_total']:,.2f}]")
            with c_btn:
                if st.button("Ver detalhes", key=f"ver_os_{row['id']}", icon=":material/visibility:", width="stretch"):
                    veic_det, cli_det = montar_veiculo_e_cliente(df_veiculos, df_clientes, placa)
                    ver_detalhes_servico(row.to_dict(), veic_det, cli_det)
                if st.button("Gerenciar", key=f"manage_os_{row['id']}", icon=":material/settings:", width="stretch"):
                    gerenciar_servico(row.to_dict(), n_txt, cli_tel, cli_email, cli_doc)
