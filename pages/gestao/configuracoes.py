import streamlit as st
from database import supabase
from utils.dados import buscar_config_empresa
import time

st.set_page_config(layout="wide", page_title="Configurações | Sanini & Aimi")
st.title("⚙️ Configurações da Empresa")
st.markdown("Dados institucionais exibidos no portal e usados nos relatórios em PDF.")

config = buscar_config_empresa()

with st.container(border=True):
    with st.form("config_full"):
        c1, c2 = st.columns(2)
        with c1:
            nome_empresa = st.text_input("Nome da Empresa", value=config.get("nome_empresa") or "")
            cnpj = st.text_input("CNPJ", value=config.get("cnpj") or "")
            whatsapp = st.text_input("WhatsApp", value=config.get("whatsapp_empresa") or "")
            telefone = st.text_input("Telefone de Contato", value=config.get("telefone_contato") or "")
        with c2:
            email = st.text_input("E-mail", value=config.get("email_empresa") or "")
            instagram = st.text_input("Link do Instagram", value=config.get("instagram_link") or "")
            temas = ["Escuro", "Claro"]
            tema_atual = config.get("tema_sistema") or "Escuro"
            tema = st.selectbox("Tema do Sistema", temas, index=temas.index(tema_atual) if tema_atual in temas else 0)
            nova_logo = st.file_uploader("Alterar Logo da Mecânica", type=["png"])

        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button("💾 Salvar Configurações da Empresa", type="primary", use_container_width=True)

        if submit:
            dados = {
                "nome_empresa": nome_empresa,
                "cnpj": cnpj,
                "whatsapp_empresa": whatsapp,
                "telefone_contato": telefone,
                "email_empresa": email,
                "instagram_link": instagram,
                "tema_sistema": tema,
            }
            if config.get("id"):
                supabase.table("configuracoes_admin").update(dados).eq("id", config["id"]).execute()
            else:
                supabase.table("configuracoes_admin").insert(dados).execute()

            if nova_logo is not None:
                with open("logo.png", "wb") as f:
                    f.write(nova_logo.getbuffer())

            st.cache_data.clear()
            st.toast("✅ Configurações atualizadas!")
            time.sleep(0.6)
            st.rerun()
