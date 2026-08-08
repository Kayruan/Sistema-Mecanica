import streamlit as st
from database import supabase
from utils.dados import buscar_veiculos, buscar_catalogo_servicos, buscar_estoque_pecas
from datetime import date, datetime
import json
import time

st.set_page_config(layout="wide", page_title="Novo Orçamento | Sanini & Aimi")

editando_id = st.session_state.get("orc_editando_id")
CHAVES_EDICAO = ["orc_editando_id", "orc_editando_placa", "orc_editando_data", "orc_editando_status", "orc_editando_desc"]

col_titulo, col_cancelar = st.columns([5, 1])
with col_titulo:
    st.title(f"✏️ Editando Orçamento Nº {editando_id}" if editando_id else "➕ Emitir Novo Orçamento")
with col_cancelar:
    if editando_id:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔓 Cancelar Edição", use_container_width=True):
            for k in CHAVES_EDICAO:
                st.session_state.pop(k, None)
            st.session_state.lista_pecas_orc = []
            st.session_state.lista_servicos_orc = []
            st.rerun()

df_veiculos = buscar_veiculos()
df_catalogo = buscar_catalogo_servicos()
df_estoque = buscar_estoque_pecas()
lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []

if not lista_placas:
    st.warning("⚠️ Cadastre um veículo primeiro.")
else:
    col_esq, col_dir = st.columns([1, 1])
    with col_esq:
        st.subheader("Dados Gerais")
        placa_editando = st.session_state.get("orc_editando_placa")
        idx_placa = lista_placas.index(placa_editando) if editando_id and placa_editando in lista_placas else 0
        placa_selecionada = st.selectbox("Veículo (Placa) *", lista_placas, index=idx_placa, key="orc_placa")

        data_default = date.today()
        if editando_id and st.session_state.get("orc_editando_data"):
            try:
                data_default = datetime.strptime(st.session_state["orc_editando_data"], "%Y-%m-%d").date()
            except Exception:
                pass
        data_orcamento = st.date_input("Data do Orçamento", data_default, key="orc_data")

        opcoes_status = ["Pendente", "Aprovado", "Em Execução", "Finalizado", "Cancelado"]
        status_editando = st.session_state.get("orc_editando_status")
        idx_status = opcoes_status.index(status_editando) if editando_id and status_editando in opcoes_status else 0
        status = st.selectbox("Status Atual", opcoes_status, index=idx_status, key="orc_st")

        descricao = st.text_area("Descrição do Problema Relatado", value=st.session_state.get("orc_editando_desc", ""), key="orc_desc")

    with col_dir:
        st.subheader("Peças Necessárias e Valores")
        if "lista_pecas_orc" not in st.session_state:
            st.session_state.lista_pecas_orc = []

        with st.container(border=True):
            opcoes_estoque = ["Personalizado..."] + df_estoque['nome'].tolist() if not df_estoque.empty else ["Personalizado..."]
            p_sel = st.selectbox("Peça", opcoes_estoque, key="o_peca_sel")
            if p_sel != "Personalizado...":
                n_peca = p_sel
                valor_padrao_peca = float(df_estoque[df_estoque['nome'] == p_sel]['valor_venda'].values[0])
                disponivel = int(df_estoque[df_estoque['nome'] == p_sel]['quantidade'].values[0])
                st.caption(f"📦 Disponível em estoque: {disponivel} un.")
            else:
                n_peca = st.text_input("Nome da Peça", key="o_peca")
                valor_padrao_peca = 0.0

            c1, c2 = st.columns(2)
            with c1: n_qtd = st.number_input("Qtd", min_value=1, step=1, key="o_qtd")
            with c2: n_val = st.number_input("V. Unitário", min_value=0.0, step=10.0, value=valor_padrao_peca, key=f"o_val_{p_sel}")

            if st.button("➕ Adicionar Peça", use_container_width=True, key="btn_add_peca_orc"):
                if n_peca:
                    st.session_state.lista_pecas_orc.append({
                        "Peça/Descrição": n_peca, "Quantidade": n_qtd,
                        "Valor Unitário (R$)": n_val, "Subtotal": n_qtd * n_val
                    })
                    st.rerun()

        total_pecas = sum(item['Subtotal'] for item in st.session_state.lista_pecas_orc)
        for i, item in enumerate(st.session_state.lista_pecas_orc):
            with st.container(border=True):
                c_i, c_d = st.columns([6, 1])
                with c_i:
                    st.write(f"🔧 **{item['Peça/Descrição']}** | Qtd: {item['Quantidade']} | R$ {item['Subtotal']:.2f}")
                with c_d:
                    if st.button("🗑️", key=f"del_orc_i_{i}"):
                        st.session_state.lista_pecas_orc.pop(i)
                        st.rerun()

        st.divider()
        st.markdown("**Serviços / Mão de Obra Orçados**")
        if "lista_servicos_orc" not in st.session_state: st.session_state.lista_servicos_orc = []

        with st.container(border=True):
            opcoes_cat = ["Personalizado..."] + df_catalogo['nome'].tolist() if not df_catalogo.empty else ["Personalizado..."]
            os1, os2 = st.columns([3, 2])
            with os1:
                serv_escolhido_orc = st.selectbox("Serviço", opcoes_cat, key="orc_serv_sel")
            if serv_escolhido_orc != "Personalizado...":
                nome_serv_orc = serv_escolhido_orc
                valor_padrao_orc = float(df_catalogo[df_catalogo['nome'] == serv_escolhido_orc]['valor_padrao'].values[0])
            else:
                nome_serv_orc = st.text_input("Nome do Serviço", key="orc_serv_nome")
                valor_padrao_orc = 0.0
            with os2:
                valor_serv_orc = st.number_input("Valor (R$)", min_value=0.0, step=10.0, value=valor_padrao_orc, key=f"orc_serv_val_{serv_escolhido_orc}")

            if st.button("➕ Adicionar Serviço", use_container_width=True, key="btn_add_serv_orc"):
                if nome_serv_orc:
                    st.session_state.lista_servicos_orc.append({"Serviço": nome_serv_orc, "Valor (R$)": valor_serv_orc})
                    st.rerun()

        total_servicos = sum(item['Valor (R$)'] for item in st.session_state.lista_servicos_orc)
        for i, item in enumerate(st.session_state.lista_servicos_orc):
            with st.container(border=True):
                c_i, c_d = st.columns([6, 1])
                with c_i:
                    st.write(f"🛠️ **{item['Serviço']}** | R$ {item['Valor (R$)']:.2f}")
                with c_d:
                    if st.button("🗑️", key=f"del_serv_orc_{i}"):
                        st.session_state.lista_servicos_orc.pop(i)
                        st.rerun()

        valor_mao_obra = total_servicos
        st.divider()
        total_geral = total_pecas + valor_mao_obra
        st.markdown(f"### Valor Final Estimado: <span style='color:green;'>R$ {total_geral:,.2f}</span>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    label_botao = "💾 Salvar Alterações" if editando_id else "💾 Emitir Orçamento"
    if st.button(label_botao, type="primary", use_container_width=True):
        dados = {
            "placa_veiculo": placa_selecionada,
            "data": str(data_orcamento),
            "descricao_problema": descricao,
            "pecas_necessarias": json.dumps(st.session_state.lista_pecas_orc),
            "servicos_orcados": json.dumps(st.session_state.lista_servicos_orc),
            "valor_pecas": float(total_pecas),
            "valor_mao_de_obra": float(valor_mao_obra),
            "valor_total": float(total_geral),
            "status": status
        }
        if editando_id:
            supabase.table("orcamentos").update(dados).eq("id", editando_id).execute()
            mensagem = "✅ Orçamento atualizado com sucesso!"
        else:
            supabase.table("orcamentos").insert(dados).execute()
            mensagem = "✅ Orçamento emitido com sucesso!"

        st.session_state.lista_pecas_orc = []
        st.session_state.lista_servicos_orc = []
        st.session_state.pop("orc_desc", None)
        for k in CHAVES_EDICAO:
            st.session_state.pop(k, None)
        st.cache_data.clear()
        st.toast(mensagem)
        time.sleep(0.6)
        if editando_id:
            st.switch_page("pages/orcamentos/consultar.py")
        else:
            st.rerun()
