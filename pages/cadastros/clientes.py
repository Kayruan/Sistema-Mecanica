import streamlit as st
from database import supabase
from utils.dados import buscar_clientes
import time

st.set_page_config(layout="wide", page_title="Clientes | Sanini & Aimi")
st.title("👥 Carteira de Clientes")
st.markdown("Gerencie os dados, contatos e endereços da sua carteira de clientes.")

df_clientes = buscar_clientes()

aba1, aba2 = st.tabs(["📋 Consultar Clientes", "➕ Cadastrar Cliente"])

# --- ABA 2: CADASTRAR NOVO CLIENTE ---
with aba2:
    with st.container(border=True):
        st.subheader("Ficha de Cadastro")
        with st.form("form_novo_cliente", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome Completo / Razão Social *")
                email = st.text_input("E-mail")
            with col2:
                telefone = st.text_input("WhatsApp / Telefone *")
                cpf_cnpj = st.text_input("CPF ou CNPJ")

            endereco = st.text_input("Endereço Completo (Rua, Número, Bairro, Cidade)")

            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("💾 Cadastrar Cliente", type="primary", use_container_width=True)

            if submit:
                if not nome or not telefone:
                    st.error("⚠️ Os campos Nome e Telefone são obrigatórios.")
                else:
                    dados_cli = {
                        "nome": nome, "telefone": telefone,
                        "email": email, "cpf_cnpj": cpf_cnpj, "endereco": endereco
                    }
                    supabase.table("clientes").insert(dados_cli).execute()
                    st.cache_data.clear()
                    st.toast("✅ Cliente cadastrado com sucesso!")
                    time.sleep(0.8)
                    st.rerun()

# --- ABA 1: GESTÃO COM CARDS E BUSCA INTELIGENTE ---
with aba1:
    busca = st.text_input("🔍 Buscar cliente por Nome, CPF ou Telefone...")
    st.divider()

    if df_clientes.empty:
        st.info("Nenhum cliente cadastrado. Vá para a aba 'Cadastrar Cliente'.")
    else:
        df_filtrado = df_clientes.copy()
        if busca:
            busca = busca.lower()
            mask = df_filtrado.apply(lambda row: row.astype(str).str.lower().str.contains(busca).any(), axis=1)
            df_filtrado = df_filtrado[mask]

        if df_filtrado.empty:
            st.warning("Nenhum cliente encontrado para esta busca.")
        else:
            for index, row in df_filtrado.iterrows():
                with st.container(border=True):
                    c_info, c_btn = st.columns([5, 1])

                    with c_info:
                        st.markdown(f"### 👤 {row['nome']}")
                        st.write(f"📞 **Tel:** {row['telefone'] or 'N/A'} &nbsp;&nbsp;|&nbsp;&nbsp; ✉️ **E-mail:** {row['email'] or 'N/A'}")
                        st.caption(f"**CPF/CNPJ:** {row['cpf_cnpj'] or 'N/A'} &nbsp;&nbsp;|&nbsp;&nbsp; **Endereço:** {row['endereco'] or 'N/A'}")

                    with c_btn:
                        st.markdown("<br>", unsafe_allow_html=True)
                        with st.popover("⚙️ Gerenciar", use_container_width=True):
                            st.markdown("**Editar Cadastro**")
                            e_nome = st.text_input("Nome", value=row['nome'], key=f"n_{row['id']}")
                            e_tel = st.text_input("Telefone", value=row['telefone'], key=f"t_{row['id']}")
                            e_email = st.text_input("E-mail", value=row['email'], key=f"m_{row['id']}")
                            e_doc = st.text_input("CPF/CNPJ", value=row['cpf_cnpj'], key=f"d_{row['id']}")
                            e_end = st.text_input("Endereço", value=row['endereco'], key=f"e_{row['id']}")

                            if st.button("💾 Salvar Alterações", key=f"upd_{row['id']}", type="primary", use_container_width=True):
                                update_data = {
                                    "nome": e_nome, "telefone": e_tel, "email": e_email,
                                    "cpf_cnpj": e_doc, "endereco": e_end
                                }
                                supabase.table("clientes").update(update_data).eq("id", row['id']).execute()
                                st.cache_data.clear()
                                st.toast("✅ Atualizado!")
                                time.sleep(0.5)
                                st.rerun()

                            st.divider()
                            if st.button("🗑️ Excluir Cliente", key=f"del_{row['id']}", use_container_width=True):
                                supabase.table("clientes").delete().eq("id", row['id']).execute()
                                st.cache_data.clear()
                                st.toast("🗑️ Cliente Excluído!")
                                time.sleep(0.5)
                                st.rerun()
