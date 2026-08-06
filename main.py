import streamlit as st

st.set_page_config(page_title="Sistema Mecânica", page_icon="🔧", layout="wide")

st.title("🔧 Sistema de Gestão para Mecânica")
st.write("O ambiente está configurado e rodando perfeitamente!")

# Apenas um teste visual
col1, col2 = st.columns(2)
with col1:
    st.info("Próximo passo: Configurar Login")
with col2:
    st.success("Próximo passo: Conectar ao Banco de Dados")