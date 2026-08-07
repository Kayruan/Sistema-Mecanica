import streamlit as st

st.set_page_config(page_title="AutoMecânica System", page_icon="🏢", layout="wide")

if "logado" not in st.session_state:
    st.session_state.logado = False

def fazer_login():
    if st.session_state.usuario == "admin" and st.session_state.senha == "admin123":
        st.session_state.logado = True
    else:
        st.error("Usuário ou senha incorretos!")

def fazer_logout():
    st.session_state.logado = False

if not st.session_state.logado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_img, col_txt, col_vazia = st.columns([1, 2, 1])
    
    with col_txt:
        # st.image("logo.png", width=150) # Descomente quando tiver a logo
        st.title("🏢 AutoMecânica System")
        st.caption("CNPJ: 00.000.000/0001-00 | Gestão Inteligente")
        st.divider()
        
        with st.form("form_login"):
            st.text_input("Usuário", key="usuario")
            st.text_input("Senha", type="password", key="senha")
            st.form_submit_button("Entrar no Sistema", on_click=fazer_login, use_container_width=True)
else:
    # --- TELA DE BOAS VINDAS (ESTILO HUB) ---
    st.sidebar.markdown("### 🏢 AutoMecânica")
    st.sidebar.caption("CNPJ: 00.000.000/0001-00")
    st.sidebar.divider()
    
    st.markdown("## 👋 Olá, bem-vindo de volta!")
    st.write("Visão geral rápida e atalhos do sistema.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Criando Cards de Atalho com containers
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.container(border=True):
            st.markdown("### 📊 Dashboard")
            st.write("Acompanhe o faturamento e métricas.")
            st.info("Acesse pelo menu lateral 👈")
            
    with col2:
        with st.container(border=True):
            st.markdown("### 📝 Orçamentos")
            st.write("Gere novos orçamentos para clientes.")
            st.info("Acesse pelo menu lateral 👈")
            
    with col3:
        with st.container(border=True):
            st.markdown("### 🛠️ Serviços & PDF")
            st.write("Imprima Dossiês e Ordens de Serviço.")
            st.info("Acesse pelo menu lateral 👈")

    st.divider()
    st.button("Sair do Sistema", on_click=fazer_logout)