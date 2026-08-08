import streamlit as st
from database import supabase
from utils.dados import buscar_veiculos, buscar_clientes, buscar_catalogo_servicos, buscar_orcamentos, buscar_estoque_pecas
from datetime import date
import pandas as pd
import json
import time
import uuid
import re

st.set_page_config(layout="wide", page_title="Nova Ordem de Serviço | Sanini & Aimi")
st.title("➕ Emitir Nova Ordem de Serviço")

df_veiculos = buscar_veiculos()
df_catalogo = buscar_catalogo_servicos()
df_orcamentos = buscar_orcamentos()
df_estoque = buscar_estoque_pecas()
lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []

col_esq, col_dir = st.columns([1, 1])
with col_esq:
    st.subheader("Dados Gerais")
    if not lista_placas:
        st.warning("Cadastre um veículo primeiro.")
    else:
        placa_selecionada = st.selectbox("Veículo (Placa) *", lista_placas, key="serv_placa_sel")

        # --- IMPORTAR DADOS DE UM ORÇAMENTO APROVADO ---
        orc_vinculado_id = st.session_state.get("orcamento_vinculado_id")
        if orc_vinculado_id:
            orc_vinc_row = df_orcamentos[df_orcamentos['id'] == orc_vinculado_id] if not df_orcamentos.empty else pd.DataFrame()
            with st.container(border=True):
                st.markdown(f"#### 🔗 Vinculado ao Orçamento Nº {orc_vinculado_id}")
                if not orc_vinc_row.empty:
                    ov = orc_vinc_row.iloc[0]
                    st.caption(f"Valor orçado: R$ {float(ov['valor_total']):,.2f} | Data: {ov['data']}")
                if st.button("🔓 Desvincular Orçamento", key="btn_desvincular_orc", use_container_width=True):
                    st.session_state.orcamento_vinculado_id = None
                    st.rerun()
        else:
            orc_disp = pd.DataFrame()
            if not df_orcamentos.empty:
                orc_disp = df_orcamentos[(df_orcamentos['placa_veiculo'] == placa_selecionada) & (df_orcamentos['status'] == 'Aprovado')]
            if not orc_disp.empty:
                opcoes_orc = {"Nenhum (criar do zero)": None}
                for _, o in orc_disp.iterrows():
                    opcoes_orc[f"Orçamento Nº {o['id']} - R$ {float(o['valor_total']):,.2f} - {o['data']}"] = o['id']
                escolha_orc = st.selectbox("📥 Importar de Orçamento Aprovado", list(opcoes_orc.keys()), key="sel_orc_importar")
                if opcoes_orc[escolha_orc] is not None and st.button("📥 Importar Dados deste Orçamento", use_container_width=True, key="btn_importar_orc"):
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
                    st.toast(f"✅ Dados do Orçamento Nº {orc_sel['id']} importados!")
                    time.sleep(0.6)
                    st.rerun()

        data_serv = st.date_input("Data do Serviço", date.today())
        descricao = st.text_area("Descrição da Mão de Obra", key="descricao_serv_txt")
        fotos = st.file_uploader("📸 Anexar Fotos (Aceita jpg, png, webp...)", accept_multiple_files=True)

with col_dir:
    st.subheader("Peças e Valores")
    if "lista_pecas" not in st.session_state: st.session_state.lista_pecas = []

    with st.container(border=True):
        opcoes_estoque_serv = ["Personalizado..."] + df_estoque['nome'].tolist() if not df_estoque.empty else ["Personalizado..."]
        p_sel_serv = st.selectbox("Peça", opcoes_estoque_serv, key="serv_peca_sel")
        if p_sel_serv != "Personalizado...":
            n_peca = p_sel_serv
            valor_padrao_peca_serv = float(df_estoque[df_estoque['nome'] == p_sel_serv]['valor_venda'].values[0])
            disponivel_serv = int(df_estoque[df_estoque['nome'] == p_sel_serv]['quantidade'].values[0])
            st.caption(f"📦 Disponível em estoque: {disponivel_serv} un.")
        else:
            n_peca = st.text_input("Nome da Peça")
            valor_padrao_peca_serv = 0.0

        c1, c2 = st.columns(2)
        with c1: n_qtd = st.number_input("Qtd", min_value=1, step=1)
        with c2: n_val = st.number_input("V. Unitário", min_value=0.0, step=10.0, value=valor_padrao_peca_serv, key=f"serv_val_{p_sel_serv}")

        if st.button("➕ Adicionar Item", use_container_width=True):
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
                st.write(f"🔧 **{item['Peça/Descrição']}** | Qtd: {item['Quantidade']} | R$ {item['Subtotal']:.2f}")
            with c_d:
                if st.button("🗑️", key=f"del_i_{i}"):
                    st.session_state.lista_pecas.pop(i)
                    st.rerun()

    st.divider()
    st.markdown("**Serviços / Mão de Obra Executados**")
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
            nome_serv = st.text_input("Nome do Serviço", key="serv_exec_nome")
            valor_padrao_serv = 0.0
        with cs2:
            valor_serv = st.number_input("Valor (R$)", min_value=0.0, step=10.0, value=valor_padrao_serv, key=f"serv_exec_val_{serv_escolhido}")

        if st.button("➕ Adicionar Serviço", use_container_width=True, key="btn_add_serv_exec"):
            if nome_serv:
                st.session_state.lista_servicos_exec.append({"Serviço": nome_serv, "Valor (R$)": valor_serv})
                st.rerun()

    total_servicos = sum(item['Valor (R$)'] for item in st.session_state.lista_servicos_exec)
    for i, item in enumerate(st.session_state.lista_servicos_exec):
        with st.container(border=True):
            c_i, c_d = st.columns([6, 1])
            with c_i:
                st.write(f"🛠️ **{item['Serviço']}** | R$ {item['Valor (R$)']:.2f}")
            with c_d:
                if st.button("🗑️", key=f"del_serv_exec_{i}"):
                    st.session_state.lista_servicos_exec.pop(i)
                    st.rerun()

    valor_mao_obra = total_servicos
    st.divider()
    st.markdown(f"### Valor Final: <span style='color:green;'>R$ {total_pecas + valor_mao_obra:.2f}</span>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
if st.button("💾 Registrar Ordem de Serviço", type="primary", use_container_width=True) and lista_placas:
    urls_salvas = []
    fotos_com_falha = []
    for foto in (fotos or []):
        try:
            nome_seguro = re.sub(r'[^A-Za-z0-9._-]', '_', foto.name)
            nome_arquivo = f"{placa_selecionada}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}_{nome_seguro}"
            supabase.storage.from_("fotos_mecanica").upload(nome_arquivo, foto.getvalue())
            urls_salvas.append(supabase.storage.from_("fotos_mecanica").get_public_url(nome_arquivo))
        except Exception as e:
            fotos_com_falha.append(f"{foto.name} ({e})")

    if fotos_com_falha:
        st.warning("⚠️ Não foi possível enviar: " + "; ".join(fotos_com_falha) + ". A Ordem de Serviço será salva mesmo assim, sem essas fotos.")

    orc_vinculado = st.session_state.get("orcamento_vinculado_id")
    dados_servico = {
        "placa_veiculo": placa_selecionada, "data_servico": str(data_serv),
        "descricao_servico": descricao, "pecas_usadas": json.dumps(st.session_state.lista_pecas),
        "servicos_executados": json.dumps(st.session_state.lista_servicos_exec),
        "valor_mao_de_obra": float(valor_mao_obra), "valor_pecas": float(total_pecas),
        "urls_fotos": ",".join(urls_salvas), "orcamento_id": orc_vinculado
    }
    supabase.table("servicos_realizados").insert(dados_servico).execute()
    if orc_vinculado:
        supabase.table("orcamentos").update({"status": "Finalizado"}).eq("id", orc_vinculado).execute()

    # Baixa automática no estoque das peças utilizadas
    if not df_estoque.empty:
        for item_peca in st.session_state.lista_pecas:
            match_estoque = df_estoque[df_estoque['nome'] == item_peca['Peça/Descrição']]
            if not match_estoque.empty:
                est_id = match_estoque.iloc[0]['id']
                nova_qtd = max(0, int(match_estoque.iloc[0]['quantidade']) - int(item_peca['Quantidade']))
                supabase.table("estoque_pecas").update({"quantidade": nova_qtd}).eq("id", est_id).execute()

    st.session_state.lista_pecas = []
    st.session_state.lista_servicos_exec = []
    st.session_state.pop("descricao_serv_txt", None)
    st.session_state["orcamento_vinculado_id"] = None
    st.cache_data.clear()
    st.toast("✅ Ordem de Serviço registrada com sucesso!" + (f" (Orçamento Nº {orc_vinculado} finalizado)" if orc_vinculado else ""))
    time.sleep(0.8)
    st.rerun()
