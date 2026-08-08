import streamlit as st
from utils.dados import buscar_config_empresa

st.set_page_config(layout="wide", page_title="Início | Sanini & Aimi")

config_empresa = buscar_config_empresa()
nome_empresa = config_empresa.get("nome_empresa") or "Mecânica Sanini & Aimi"
instagram_link = config_empresa.get("instagram_link") or "https://instagram.com/mecanicasaniniaimi"
instagram_handle = "@" + instagram_link.rstrip("/").rsplit("/", 1)[-1]

st.markdown(f"# 🏢 Portal {nome_empresa}")
st.write("O seu centro de comando para gestão automotiva de alta performance.")

st.markdown("<br>", unsafe_allow_html=True)

# Seção Institucional
col_hist, col_rede = st.columns([2, 1])

with col_hist:
    with st.container(border=True):
        st.markdown("### 🏆 Nossa História & Missão")
        st.markdown("""
        A **Mecânica e Autopeças Sanini & Aimi** nasceu com o compromisso de entregar serviços de excelência, transparência e tecnologia para o seu veículo.

        Aliamos equipamentos modernos a uma equipe altamente capacitada para garantir a sua segurança e a performance do seu motor. Da revisão básica à retífica completa, nosso foco é a sua tranquilidade.
        """)
        st.caption("📍 Localizada no coração da cidade - Atendimento de Seg a Sex.")

with col_rede:
    with st.container(border=True):
        st.markdown("### 📱 Nossas Redes")
        st.write("Acompanhe nosso trabalho e os serviços de excelência diariamente no Instagram.")
        st.markdown(f"""
        <a href="{instagram_link}" target="_blank" style="text-decoration: none;">
            <div style="background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); padding: 10px; border-radius: 8px; color: white; text-align: center; font-weight: bold; transition: 0.3s;">
                📸 Siga {instagram_handle}
            </div>
        </a>
        """, unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# Atalhos Rápidos (levam direto para a tela do módulo)
st.markdown("### 🚀 Acesso Rápido")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    with st.container(border=True):
        st.markdown("#### 👥 Clientes")
        st.caption("Cadastro e histórico de atendimento.")
        st.page_link("pages/cadastros/clientes.py", label="Acessar", icon="➡️")
with c2:
    with st.container(border=True):
        st.markdown("#### 🚗 Veículos")
        st.caption("Controle da frota atendida.")
        st.page_link("pages/cadastros/veiculos.py", label="Acessar", icon="➡️")
with c3:
    with st.container(border=True):
        st.markdown("#### 📝 Orçamentos")
        st.caption("Emissão, aprovação e assinatura.")
        st.page_link("pages/orcamentos/consultar.py", label="Acessar", icon="➡️")
with c4:
    with st.container(border=True):
        st.markdown("#### 🛠️ Ordens de Serviço")
        st.caption("Execução, fotos e dossiê técnico.")
        st.page_link("pages/servicos/consultar.py", label="Acessar", icon="➡️")
with c5:
    with st.container(border=True):
        st.markdown("#### 📦 Estoque")
        st.caption("Controle de peças e reposição.")
        st.page_link("pages/cadastros/estoque.py", label="Acessar", icon="➡️")
