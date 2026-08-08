import streamlit as st
import os
from dotenv import load_dotenv
from utils.dados import buscar_config_empresa

load_dotenv()


def obter_config(nome, padrao=None):
    valor = os.environ.get(nome)
    if valor:
        return valor
    try:
        return st.secrets.get(nome, padrao)
    except Exception:
        return padrao


ADMIN_USER = obter_config("ADMIN_USER", "admin")
ADMIN_PASSWORD = obter_config("ADMIN_PASSWORD", "admin123")

if "logado" not in st.session_state:
    st.session_state.logado = False


def fazer_login():
    if st.session_state.usuario == ADMIN_USER and st.session_state.senha == ADMIN_PASSWORD:
        st.session_state.logado = True
        st.toast("Acesso Liberado! Bem-vindo.", icon="🔓")
    else:
        st.error("Credenciais inválidas. Tente novamente.")


def fazer_logout():
    st.session_state.logado = False
    st.rerun()


# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.set_page_config(page_title="Sanini & Aimi | Gestão", page_icon="⚙️", layout="wide", initial_sidebar_state="expanded")

    config_empresa = buscar_config_empresa()
    nome_empresa = config_empresa.get("nome_empresa") or "Mecânica Sanini & Aimi"

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        with st.container(border=True):
            c_img, c_txt = st.columns([1, 4])
            with c_img:
                if os.path.exists("logo.png"):
                    st.image("logo.png", use_container_width=True)
                else:
                    st.markdown("<h1 style='text-align: center;'>⚙️</h1>", unsafe_allow_html=True)
            with c_txt:
                st.markdown(f"<h2 style='margin-bottom: 0px; color: #1e293b;'>{nome_empresa}</h2>", unsafe_allow_html=True)
                st.caption("Sistema de Gestão de Excelência")

            st.divider()

            with st.form("form_login"):
                st.text_input("Usuário do Sistema", key="usuario", placeholder="Digite seu usuário")
                st.text_input("Senha de Acesso", type="password", key="senha", placeholder="••••••••")

                st.markdown("<br>", unsafe_allow_html=True)
                submit = st.form_submit_button("Entrar no Sistema", use_container_width=True)
                if submit:
                    fazer_login()

# ==========================================
# APLICAÇÃO PRINCIPAL (NAVEGAÇÃO POR MÓDULOS)
# ==========================================
else:
    # --- INJEÇÃO DE CSS (DESIGN FUTURISTA E MODERNO) ---
    st.markdown("""
    <style>
        /* Estiliza os botões principais */
        div.stButton > button:first-child {
            background-color: #0f172a;
            color: white;
            border-radius: 8px;
            transition: all 0.3s ease;
            border: 1px solid #334155;
        }
        div.stButton > button:first-child:hover {
            background-color: #3b82f6;
            border-color: #60a5fa;
            transform: scale(1.02);
        }
        /* Estiliza os cards */
        div[data-testid="stVerticalBlock"] div[style*="border"] {
            border-radius: 12px !important;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1) !important;
            transition: all 0.3s ease;
        }
        div[data-testid="stVerticalBlock"] div[style*="border"]:hover {
            border-color: #3b82f6 !important;
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    config_empresa = buscar_config_empresa()
    nome_empresa = config_empresa.get("nome_empresa") or "Mecânica Sanini & Aimi"

    # Marca na barra lateral (acima do menu de navegação)
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", width=150)
    st.sidebar.markdown(f"### ⚙️ {nome_empresa}")
    st.sidebar.caption("Excelência Automotiva")
    st.sidebar.divider()
    if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
        fazer_logout()
    st.sidebar.divider()

    pagina_inicio = st.Page("pages/inicio.py", title="Início", icon="🏢", url_path="inicio", default=True)

    pagina_clientes = st.Page("pages/cadastros/clientes.py", title="Clientes", icon="👥", url_path="clientes")
    pagina_veiculos = st.Page("pages/cadastros/veiculos.py", title="Veículos", icon="🚗", url_path="veiculos")
    pagina_estoque = st.Page("pages/cadastros/estoque.py", title="Estoque", icon="📦", url_path="estoque")

    pagina_orc_consultar = st.Page("pages/orcamentos/consultar.py", title="Consultar Orçamentos", icon="📋", url_path="orcamentos-consultar")
    pagina_orc_novo = st.Page("pages/orcamentos/novo.py", title="Novo Orçamento", icon="➕", url_path="orcamentos-novo")
    pagina_orc_relatorios = st.Page("pages/orcamentos/relatorios.py", title="Relatórios", icon="📊", url_path="orcamentos-relatorios")

    pagina_os_consultar = st.Page("pages/servicos/consultar.py", title="Consultar Ordens de Serviço", icon="📋", url_path="os-consultar")
    pagina_os_nova = st.Page("pages/servicos/nova_os.py", title="Nova Ordem de Serviço", icon="➕", url_path="os-nova")
    pagina_os_catalogo = st.Page("pages/servicos/catalogo.py", title="Catálogo de Serviços", icon="🗂️", url_path="os-catalogo")
    pagina_os_relatorios = st.Page("pages/servicos/relatorios.py", title="Relatórios", icon="📊", url_path="os-relatorios")

    pagina_dashboard = st.Page("pages/gestao/dashboard.py", title="Painel Gerencial", icon="📊", url_path="dashboard")
    pagina_configuracoes = st.Page("pages/gestao/configuracoes.py", title="Configurações", icon="⚙️", url_path="configuracoes")

    pg = st.navigation({
        "🏢 Início": [pagina_inicio],
        "📇 Cadastros": [pagina_clientes, pagina_veiculos, pagina_estoque],
        "📝 Orçamentos": [pagina_orc_consultar, pagina_orc_novo, pagina_orc_relatorios],
        "🛠️ Ordens de Serviço": [pagina_os_consultar, pagina_os_nova, pagina_os_catalogo, pagina_os_relatorios],
        "📊 Gestão": [pagina_dashboard, pagina_configuracoes],
    }, expanded=True)

    pg.run()
