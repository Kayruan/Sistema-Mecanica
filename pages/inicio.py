import streamlit as st
from utils.dados import buscar_config_empresa

st.set_page_config(layout="wide", page_title="Início | Sanini & Aimi")

config_empresa = buscar_config_empresa()
nome_empresa = config_empresa.get("nome_empresa") or "Mecânica Sanini & Aimi"
instagram_link = config_empresa.get("instagram_link") or "https://instagram.com/mecanicasaniniaimi"
instagram_handle = "@" + instagram_link.rstrip("/").rsplit("/", 1)[-1]

st.title(f"Portal {nome_empresa}", anchor=False)
st.write("O seu centro de comando para gestão automotiva de alta performance.")

st.space("large")

# Seção institucional
col_hist, col_rede = st.columns([2, 1])

with col_hist:
    with st.container(border=True):
        st.markdown("### :material/emoji_events: Nossa história & missão")
        st.markdown("""
        A **Mecânica e Autopeças Sanini & Aimi** nasceu com o compromisso de entregar serviços de excelência, transparência e tecnologia para o seu veículo.

        Aliamos equipamentos modernos a uma equipe altamente capacitada para garantir a sua segurança e a performance do seu motor. Da revisão básica à retífica completa, nosso foco é a sua tranquilidade.
        """)
        st.caption(":material/location_on: Localizada no coração da cidade — atendimento de segunda a sexta.")

with col_rede:
    with st.container(border=True):
        st.markdown("### :material/photo_camera: Nossas redes")
        st.write("Acompanhe nosso trabalho e os serviços de excelência diariamente no Instagram.")
        st.link_button(f"Seguir {instagram_handle}", instagram_link, icon=":material/photo_camera:", width="stretch")

st.space("large")

# Atalhos rápidos (levam direto para a tela do módulo)
st.markdown("### :material/bolt: Acesso rápido")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    with st.container(border=True):
        st.markdown("#### :material/group: Clientes")
        st.caption("Cadastro e histórico de atendimento.")
        st.page_link("pages/cadastros/clientes.py", label="Acessar", icon=":material/arrow_forward:")
with c2:
    with st.container(border=True):
        st.markdown("#### :material/directions_car: Veículos")
        st.caption("Controle da frota atendida.")
        st.page_link("pages/cadastros/veiculos.py", label="Acessar", icon=":material/arrow_forward:")
with c3:
    with st.container(border=True):
        st.markdown("#### :material/list_alt: Orçamentos")
        st.caption("Emissão, aprovação e assinatura.")
        st.page_link("pages/orcamentos/consultar.py", label="Acessar", icon=":material/arrow_forward:")
with c4:
    with st.container(border=True):
        st.markdown("#### :material/build: Ordens de serviço")
        st.caption("Execução, fotos e dossiê técnico.")
        st.page_link("pages/servicos/consultar.py", label="Acessar", icon=":material/arrow_forward:")
with c5:
    with st.container(border=True):
        st.markdown("#### :material/inventory_2: Estoque")
        st.caption("Controle de peças e reposição.")
        st.page_link("pages/cadastros/estoque.py", label="Acessar", icon=":material/arrow_forward:")
