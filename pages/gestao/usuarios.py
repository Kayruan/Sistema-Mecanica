import streamlit as st
import bcrypt
from database import supabase
from utils.dados import buscar_usuarios, OPCOES_PAPEL_USUARIO
from utils.auth import eh_gerente, usuario_atual
import time

st.set_page_config(layout="wide", page_title="Usuários | Sanini & Aimi")

SENHA_MIN_LEN = 8

if not eh_gerente():
    st.error("Acesso restrito a usuários com papel Gerente.", icon=":material/lock:")
    st.stop()

st.title("Gerenciar usuários", anchor=False)
st.caption("Controle de acesso ao sistema: quem pode entrar e com qual nível de permissão.")

df_usuarios = buscar_usuarios()

aba1, aba2 = st.tabs(["Usuários cadastrados", "Novo usuário"])

with aba2:
    with st.container(border=True):
        st.subheader("Ficha do usuário", anchor=False)
        with st.form("form_novo_usuario", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nome = st.text_input("Nome completo *")
                login = st.text_input("Login (usuário) *")
            with c2:
                papel = st.selectbox("Papel", OPCOES_PAPEL_USUARIO)
                senha = st.text_input("Senha *", type="password", help=f"Mínimo de {SENHA_MIN_LEN} caracteres.")

            submit = st.form_submit_button("Cadastrar usuário", type="primary", width="stretch", icon=":material/person_add:")
            if submit:
                if not nome or not login or not senha:
                    st.error("Nome, login e senha são obrigatórios.", icon=":material/error:")
                elif len(senha) < SENHA_MIN_LEN:
                    st.error(f"A senha deve ter pelo menos {SENHA_MIN_LEN} caracteres.", icon=":material/error:")
                else:
                    senha_hash = bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                    try:
                        supabase.table("usuarios").insert({
                            "nome": nome, "usuario": login, "senha_hash": senha_hash, "papel": papel, "ativo": True,
                        }).execute()
                        st.cache_data.clear()
                        st.toast("Usuário cadastrado com sucesso.", icon=":material/check_circle:")
                        st.rerun()
                    except Exception:
                        st.error("Erro ao salvar: login já existente ou falha no banco.", icon=":material/error:")

with aba1:
    if df_usuarios.empty:
        st.info("Nenhum usuário cadastrado ainda.")
    else:
        for _, row in df_usuarios.iterrows():
            with st.container(border=True):
                c_inf, c_papel, c_acao = st.columns([4, 1.5, 2], vertical_alignment="center")
                with c_inf:
                    st.markdown(f"#### {row['nome']}")
                    st.caption(f"Login: `{row['usuario']}`")
                with c_papel:
                    st.badge(row['papel'], color="blue" if row['papel'] == "Gerente" else "gray")
                    st.badge("Ativo" if row['ativo'] else "Inativo", color="green" if row['ativo'] else "red")
                with c_acao:
                    eh_o_proprio = usuario_atual() and usuario_atual()["id"] == row['id']
                    if row['ativo']:
                        if st.button(
                            "Desativar", key=f"toggle_{row['id']}", icon=":material/block:", width="stretch",
                            disabled=eh_o_proprio, help="Você não pode desativar o seu próprio usuário." if eh_o_proprio else None,
                        ):
                            supabase.table("usuarios").update({"ativo": False}).eq("id", row['id']).execute()
                            st.cache_data.clear()
                            st.toast("Usuário desativado.", icon=":material/block:")
                            st.rerun()
                    else:
                        if st.button("Reativar", key=f"toggle_{row['id']}", icon=":material/check_circle:", width="stretch"):
                            supabase.table("usuarios").update({"ativo": True}).eq("id", row['id']).execute()
                            st.cache_data.clear()
                            st.toast("Usuário reativado.", icon=":material/check_circle:")
                            st.rerun()

                with st.expander("Trocar senha"):
                    nova_senha = st.text_input("Nova senha", type="password", key=f"npass_{row['id']}", help=f"Mínimo de {SENHA_MIN_LEN} caracteres.")
                    if st.button("Salvar nova senha", key=f"salvarpass_{row['id']}", icon=":material/save:"):
                        if not nova_senha:
                            st.error("Digite a nova senha.", icon=":material/error:")
                        elif len(nova_senha) < SENHA_MIN_LEN:
                            st.error(f"A senha deve ter pelo menos {SENHA_MIN_LEN} caracteres.", icon=":material/error:")
                        else:
                            novo_hash = bcrypt.hashpw(nova_senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                            supabase.table("usuarios").update({"senha_hash": novo_hash, "tentativas_falhas": 0, "bloqueado_ate": None}).eq("id", row['id']).execute()
                            st.toast("Senha atualizada.", icon=":material/check_circle:")
                            st.rerun()
