import streamlit as st
from database import supabase
from utils.dados import buscar_veiculos, buscar_clientes, buscar_catalogo_servicos, buscar_orcamentos, buscar_estoque_pecas, buscar_servicos
from utils.auth import registrar_log
from utils.imagens import converter_para_jpg_bytes
from datetime import date, datetime
import pandas as pd
import json
import time
import uuid
import re

st.set_page_config(layout="wide", page_title="Nova Ordem de Serviço | Sanini & Aimi")

editando_id = st.session_state.get("os_editando_id")
CHAVES_EDICAO_OS = ["os_editando_id", "os_editando_placa", "os_editando_data", "os_editando_pecas_originais"]

col_titulo, col_cancelar = st.columns([5, 1], vertical_alignment="center")
with col_titulo:
    st.title(f"Editando ordem de serviço Nº {editando_id}" if editando_id else "Emitir nova ordem de serviço", anchor=False)
with col_cancelar:
    if editando_id:
        if st.button("Cancelar edição", icon=":material/close:", width="stretch"):
            for k in CHAVES_EDICAO_OS:
                st.session_state.pop(k, None)
            st.session_state.lista_pecas = []
            st.session_state.lista_servicos_exec = []
            st.rerun()

df_veiculos = buscar_veiculos()
df_catalogo = buscar_catalogo_servicos()
df_orcamentos = buscar_orcamentos()
df_estoque = buscar_estoque_pecas()
lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []

col_esq, col_dir = st.columns([1, 1])
with col_esq:
    st.subheader("Dados gerais", anchor=False)
    if not lista_placas:
        st.warning("Cadastre um veículo primeiro.", icon=":material/warning:")
    else:
        placa_editando = st.session_state.get("os_editando_placa")
        idx_placa_os = lista_placas.index(placa_editando) if editando_id and placa_editando in lista_placas else 0
        placa_selecionada = st.selectbox("Veículo (placa) *", lista_placas, index=idx_placa_os, key="serv_placa_sel", disabled=bool(editando_id))

        # --- IMPORTAR DADOS DE UM ORÇAMENTO APROVADO (apenas ao criar uma OS nova) ---
        orc_vinculado_id = st.session_state.get("orcamento_vinculado_id")
        if editando_id:
            pass
        elif orc_vinculado_id:
            orc_vinc_row = df_orcamentos[df_orcamentos['id'] == orc_vinculado_id] if not df_orcamentos.empty else pd.DataFrame()
            with st.container(border=True):
                st.markdown(f"#### :material/link: Vinculado ao orçamento Nº {orc_vinculado_id}")
                if not orc_vinc_row.empty:
                    ov = orc_vinc_row.iloc[0]
                    st.caption(f"Valor orçado: R$ {float(ov['valor_total']):,.2f} · Data: {ov['data']}")
                if st.button("Desvincular orçamento", key="btn_desvincular_orc", icon=":material/link_off:", width="stretch"):
                    st.session_state.orcamento_vinculado_id = None
                    st.rerun()
        else:
            orc_disp = pd.DataFrame()
            if not df_orcamentos.empty:
                orc_disp = df_orcamentos[(df_orcamentos['placa_veiculo'] == placa_selecionada) & (df_orcamentos['status'] == 'Aprovado')]
                df_servicos_existentes = buscar_servicos()
                if not df_servicos_existentes.empty and 'orcamento_id' in df_servicos_existentes.columns:
                    ids_ja_vinculados = df_servicos_existentes['orcamento_id'].dropna().astype(int).tolist()
                    orc_disp = orc_disp[~orc_disp['id'].isin(ids_ja_vinculados)]
            if not orc_disp.empty:
                opcoes_orc = {"Nenhum (criar do zero)": None}
                for _, o in orc_disp.iterrows():
                    opcoes_orc[f"Orçamento Nº {o['id']} - R$ {float(o['valor_total']):,.2f} - {o['data']}"] = o['id']
                escolha_orc = st.selectbox("Importar de orçamento aprovado", list(opcoes_orc.keys()), key="sel_orc_importar")
                if opcoes_orc[escolha_orc] is not None and st.button("Importar dados deste orçamento", width="stretch", key="btn_importar_orc", icon=":material/download:"):
                    orc_sel = orc_disp[orc_disp['id'] == opcoes_orc[escolha_orc]].iloc[0]
                    try:
                        st.session_state.lista_pecas = json.loads(orc_sel.get('pecas_necessarias') or '[]')
                    except Exception:
                        st.session_state.lista_pecas = []
                    try:
                        st.session_state.lista_servicos_exec = json.loads(orc_sel.get('servicos_orcados') or '[]')
                    except Exception:
                        st.session_state.lista_servicos_exec = []
                    st.session_state["descricao_serv_txt"] = orc_sel.get('descricao_problema') or ''
                    st.session_state.orcamento_vinculado_id = int(orc_sel['id'])
                    st.toast(f"Dados do Orçamento Nº {orc_sel['id']} importados.", icon=":material/check_circle:")
                    st.rerun()

        data_default_os = date.today()
        if editando_id and st.session_state.get("os_editando_data"):
            try:
                data_default_os = datetime.strptime(st.session_state["os_editando_data"], "%Y-%m-%d").date()
            except Exception:
                pass
        data_serv = st.date_input("Data do serviço", data_default_os)
        descricao = st.text_area("Descrição da mão de obra", key="descricao_serv_txt")
        fotos = st.file_uploader("Anexar fotos (jpg, png, webp...)", accept_multiple_files=True)
        if editando_id:
            st.caption("Fotos e assinatura continuam sendo gerenciadas em Consultar OS → Gerenciar.")

with col_dir:
    st.subheader("Peças e valores", anchor=False)
    if "lista_pecas" not in st.session_state: st.session_state.lista_pecas = []

    with st.container(border=True):
        opcoes_estoque_serv = ["Personalizado..."] + df_estoque['nome'].tolist() if not df_estoque.empty else ["Personalizado..."]
        p_sel_serv = st.selectbox("Peça", opcoes_estoque_serv, key="serv_peca_sel")
        if p_sel_serv != "Personalizado...":
            n_peca = p_sel_serv
            valor_padrao_peca_serv = float(df_estoque[df_estoque['nome'] == p_sel_serv]['valor_venda'].values[0])
            disponivel_serv = int(df_estoque[df_estoque['nome'] == p_sel_serv]['quantidade'].values[0])
            st.caption(f"Disponível em estoque: {disponivel_serv} un.")
        else:
            n_peca = st.text_input("Nome da peça")
            valor_padrao_peca_serv = 0.0

        c1, c2 = st.columns(2)
        with c1: n_qtd = st.number_input("Qtd", min_value=1, step=1)
        with c2: n_val = st.number_input("V. unitário", min_value=0.0, step=10.0, value=valor_padrao_peca_serv, key=f"serv_val_{p_sel_serv}")

        if st.button("Adicionar item", width="stretch", icon=":material/add:"):
            if n_peca:
                st.session_state.lista_pecas.append({
                    "Peça/Descrição": n_peca, "Quantidade": n_qtd,
                    "Valor Unitário (R$)": n_val, "Subtotal": n_qtd * n_val
                })
                st.rerun()

    total_pecas = sum(item['Subtotal'] for item in st.session_state.lista_pecas)
    for i, item in enumerate(st.session_state.lista_pecas):
        with st.container(border=True):
            c_i, c_d = st.columns([6, 1])
            with c_i:
                st.write(f"**{item['Peça/Descrição']}** · Qtd: {item['Quantidade']} · R$ {item['Subtotal']:.2f}")
            with c_d:
                if st.button("", key=f"del_i_{i}", icon=":material/delete:"):
                    st.session_state.lista_pecas.pop(i)
                    st.rerun()

    st.divider()
    st.markdown("**Serviços / mão de obra executados**")
    if "lista_servicos_exec" not in st.session_state: st.session_state.lista_servicos_exec = []

    with st.container(border=True):
        opcoes_cat = ["Personalizado..."] + df_catalogo['nome'].tolist() if not df_catalogo.empty else ["Personalizado..."]
        cs1, cs2 = st.columns([3, 2])
        with cs1:
            serv_escolhido = st.selectbox("Serviço", opcoes_cat, key="serv_exec_sel")
        if serv_escolhido != "Personalizado...":
            nome_serv = serv_escolhido
            valor_padrao_serv = float(df_catalogo[df_catalogo['nome'] == serv_escolhido]['valor_padrao'].values[0])
        else:
            nome_serv = st.text_input("Nome do serviço", key="serv_exec_nome")
            valor_padrao_serv = 0.0
        with cs2:
            valor_serv = st.number_input("Valor (R$)", min_value=0.0, step=10.0, value=valor_padrao_serv, key=f"serv_exec_val_{serv_escolhido}")

        if st.button("Adicionar serviço", width="stretch", key="btn_add_serv_exec", icon=":material/add:"):
            if nome_serv:
                st.session_state.lista_servicos_exec.append({"Serviço": nome_serv, "Valor (R$)": valor_serv})
                st.rerun()

    total_servicos = sum(item['Valor (R$)'] for item in st.session_state.lista_servicos_exec)
    for i, item in enumerate(st.session_state.lista_servicos_exec):
        with st.container(border=True):
            c_i, c_d = st.columns([6, 1])
            with c_i:
                st.write(f"**{item['Serviço']}** · R$ {item['Valor (R$)']:.2f}")
            with c_d:
                if st.button("", key=f"del_serv_exec_{i}", icon=":material/delete:"):
                    st.session_state.lista_servicos_exec.pop(i)
                    st.rerun()

    valor_mao_obra = total_servicos
    st.divider()
    st.markdown(f"### Valor final: :green[R$ {total_pecas + valor_mao_obra:.2f}]")

label_botao_os = "Salvar alterações" if editando_id else "Registrar ordem de serviço"
clique_registrar = st.button(label_botao_os, type="primary", width="stretch", icon=":material/save:")
ultimo_envio = st.session_state.get("os_ultimo_envio", 0)
if clique_registrar and lista_placas and (time.time() - ultimo_envio > 5):
    st.session_state["os_ultimo_envio"] = time.time()
    urls_salvas = []
    fotos_com_falha = []
    for foto in (fotos or []):
        try:
            try:
                conteudo_foto = converter_para_jpg_bytes(foto)
                extensao_foto = "jpg"
            except Exception:
                conteudo_foto = foto.getvalue()
                extensao_foto = foto.name.split('.')[-1] if '.' in foto.name else "bin"
            nome_seguro = re.sub(r'[^A-Za-z0-9._-]', '_', foto.name.rsplit('.', 1)[0])
            nome_arquivo = f"{placa_selecionada}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}_{nome_seguro}.{extensao_foto}"
            supabase.storage.from_("fotos_mecanica").upload(nome_arquivo, conteudo_foto)
            urls_salvas.append(supabase.storage.from_("fotos_mecanica").get_public_url(nome_arquivo))
        except Exception as e:
            fotos_com_falha.append(f"{foto.name} ({e})")

    if fotos_com_falha:
        st.warning("Não foi possível enviar: " + "; ".join(fotos_com_falha) + ". A Ordem de Serviço será salva mesmo assim, sem essas fotos.", icon=":material/warning:")

    dados_servico = {
        "data_servico": str(data_serv),
        "descricao_servico": descricao, "pecas_usadas": json.dumps(st.session_state.lista_pecas),
        "servicos_executados": json.dumps(st.session_state.lista_servicos_exec),
        "valor_mao_de_obra": float(valor_mao_obra), "valor_pecas": float(total_pecas),
    }

    # Ajusta o estoque pela DIFERENÇA entre peças antigas e novas (evita descontar duas vezes ao editar)
    pecas_originais = []
    if editando_id:
        try:
            pecas_originais = json.loads(st.session_state.get("os_editando_pecas_originais") or "[]")
        except Exception:
            pecas_originais = []
    if not df_estoque.empty:
        for item_peca in pecas_originais:
            match_estoque = df_estoque[df_estoque['nome'] == item_peca['Peça/Descrição']]
            if not match_estoque.empty:
                est_id = match_estoque.iloc[0]['id']
                nova_qtd = int(match_estoque.iloc[0]['quantidade']) + int(item_peca['Quantidade'])
                supabase.table("estoque_pecas").update({"quantidade": nova_qtd}).eq("id", est_id).execute()
                df_estoque.loc[df_estoque['id'] == est_id, 'quantidade'] = nova_qtd
        for item_peca in st.session_state.lista_pecas:
            match_estoque = df_estoque[df_estoque['nome'] == item_peca['Peça/Descrição']]
            if not match_estoque.empty:
                est_id = match_estoque.iloc[0]['id']
                nova_qtd = max(0, int(match_estoque.iloc[0]['quantidade']) - int(item_peca['Quantidade']))
                supabase.table("estoque_pecas").update({"quantidade": nova_qtd}).eq("id", est_id).execute()
                df_estoque.loc[df_estoque['id'] == est_id, 'quantidade'] = nova_qtd

    if editando_id:
        if urls_salvas:
            fotos_atuais_edicao = supabase.table("servicos_realizados").select("urls_fotos").eq("id", editando_id).execute().data
            existentes = (fotos_atuais_edicao[0].get('urls_fotos') or '') if fotos_atuais_edicao else ''
            dados_servico["urls_fotos"] = ",".join([u for u in existentes.split(',') if u.strip()] + urls_salvas)
        supabase.table("servicos_realizados").update(dados_servico).eq("id", editando_id).execute()
        registrar_log("editou", "servico", editando_id)
        st.session_state["msg_sucesso_os"] = f"Ordem de serviço Nº {editando_id} atualizada."
        for k in CHAVES_EDICAO_OS:
            st.session_state.pop(k, None)
    else:
        orc_vinculado = st.session_state.get("orcamento_vinculado_id")
        dados_servico["placa_veiculo"] = placa_selecionada
        dados_servico["urls_fotos"] = ",".join(urls_salvas)
        dados_servico["orcamento_id"] = orc_vinculado
        nova_os = supabase.table("servicos_realizados").insert(dados_servico).execute()
        registrar_log("criou", "servico", nova_os.data[0]['id'] if nova_os.data else placa_selecionada)
        # O orçamento só vira "Finalizado" quando a OS vinculada for finalizada (não ao simplesmente abrir a OS).
        st.session_state["orcamento_vinculado_id"] = None
        st.session_state["os_recem_registrada"] = nova_os.data[0]['id'] if nova_os.data else None

    st.session_state.lista_pecas = []
    st.session_state.lista_servicos_exec = []
    st.session_state.pop("descricao_serv_txt", None)
    st.cache_data.clear()
    st.switch_page("pages/servicos/consultar.py")
