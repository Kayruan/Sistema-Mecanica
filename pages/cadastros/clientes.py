import streamlit as st
from database import supabase
from utils.dados import buscar_clientes
from utils.auth import registrar_log
import time

st.set_page_config(layout="wide", page_title="Clientes | Sanini & Aimi")
st.title("Carteira de clientes", anchor=False)
st.markdown("Gerencie os dados, contatos e endereços da sua carteira de clientes.")

msg_sucesso_cli = st.session_state.pop("msg_sucesso_cli", None)
if msg_sucesso_cli:
    st.success(msg_sucesso_cli, icon=":material/check_circle:")

df_clientes = buscar_clientes()

aba1, aba2 = st.tabs(["Consultar clientes", "Cadastrar cliente"])


@st.dialog("Editar cliente", width="large")
def editar_cliente(row):
    e_nome = st.text_input("Nome", value=row['nome'], key=f"n_{row['id']}")
    e_tel = st.text_input("Telefone", value=row['telefone'], key=f"t_{row['id']}")
    e_email = st.text_input("E-mail", value=row['email'], key=f"m_{row['id']}")
    e_doc = st.text_input("CPF/CNPJ", value=row['cpf_cnpj'], key=f"d_{row['id']}")
    e_end = st.text_input("Endereço", value=row['endereco'], key=f"e_{row['id']}")

    with st.container(horizontal=True):
        if st.button("Salvar alterações", key=f"upd_{row['id']}", type="primary", icon=":material/save:"):
            update_data = {
                "nome": e_nome, "telefone": e_tel, "email": e_email,
                "cpf_cnpj": e_doc, "endereco": e_end
            }
            supabase.table("clientes").update(update_data).eq("id", row['id']).execute()
            registrar_log("editou", "cliente", row['nome'])
            st.cache_data.clear()
            st.session_state["msg_sucesso_cli"] = f"Cliente {e_nome} atualizado."
            st.rerun()
        if st.button("Excluir cliente", key=f"del_{row['id']}", icon=":material/delete:"):
            supabase.table("clientes").delete().eq("id", row['id']).execute()
            registrar_log("excluiu", "cliente", row['nome'])
            st.cache_data.clear()
            st.session_state["msg_sucesso_cli"] = "Cliente excluído."
            st.rerun()


# --- ABA 2: CADASTRAR NOVO CLIENTE ---
with aba2:
    with st.container(border=True):
        st.subheader("Ficha de cadastro", anchor=False)
        with st.form("form_novo_cliente", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome completo / razão social *")
                email = st.text_input("E-mail")
            with col2:
                telefone = st.text_input("WhatsApp / telefone *")
                cpf_cnpj = st.text_input("CPF ou CNPJ")

            endereco = st.text_input("Endereço completo (rua, número, bairro, cidade)")

            submit = st.form_submit_button("Cadastrar cliente", type="primary", width="stretch", icon=":material/save:")

            if submit and (time.time() - st.session_state.get("cli_ultimo_envio", 0) > 5):
                st.session_state["cli_ultimo_envio"] = time.time()
                if not nome or not telefone:
                    st.error("Os campos Nome e Telefone são obrigatórios.", icon=":material/error:")
                else:
                    dados_cli = {
                        "nome": nome, "telefone": telefone,
                        "email": email, "cpf_cnpj": cpf_cnpj, "endereco": endereco
                    }
                    supabase.table("clientes").insert(dados_cli).execute()
                    registrar_log("criou", "cliente", nome)
                    st.cache_data.clear()
                    st.session_state["msg_sucesso_cli"] = f"Cliente {nome} cadastrado com sucesso."
                    st.rerun()

# --- ABA 1: GESTÃO COM CARDS E BUSCA INTELIGENTE ---
with aba1:
    busca = st.text_input("Buscar cliente por nome, CPF ou telefone", icon=":material/search:")

    if df_clientes.empty:
        st.info("Nenhum cliente cadastrado. Vá para a aba \"Cadastrar cliente\".")
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
                with st.container(border=True, key=f"card_cli_{row['id']}"):
                    c_info, c_btn = st.columns([5, 1], vertical_alignment="center")

                    with c_info:
                        st.markdown(f"#### {row['nome']}")
                        st.write(f":material/call: {row['telefone'] or 'N/A'}  &nbsp;&nbsp; :material/mail: {row['email'] or 'N/A'}")
                        st.caption(f"CPF/CNPJ: {row['cpf_cnpj'] or 'N/A'}  ·  Endereço: {row['endereco'] or 'N/A'}")

                    with c_btn:
                        if st.button("Gerenciar", key=f"manage_{row['id']}", icon=":material/settings:", width="stretch"):
                            editar_cliente(row)
