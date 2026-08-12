import streamlit as st
import os
import bcrypt
from datetime import datetime, timedelta, timezone
from database import supabase
from utils.dados import buscar_config_empresa
from utils.auth import eh_gerente

MAX_TENTATIVAS_LOGIN = 5
BLOQUEIO_MINUTOS = 15

if "logado" not in st.session_state:
    st.session_state.logado = False


def fazer_login():
    resp = supabase.table("usuarios").select("*").eq("usuario", st.session_state.usuario).eq("ativo", True).execute()
    usuarios = resp.data
    if not usuarios:
        st.error("Credenciais inválidas. Tente novamente.")
        return

    usuario_row = usuarios[0]
    bloqueado_ate = usuario_row.get("bloqueado_ate")
    if bloqueado_ate:
        expira = datetime.fromisoformat(bloqueado_ate.replace("Z", "+00:00"))
        agora = datetime.now(timezone.utc)
        if expira > agora:
            minutos_restantes = max(1, int((expira - agora).total_seconds() // 60) + 1)
            st.error(f"Conta temporariamente bloqueada por excesso de tentativas. Tente novamente em {minutos_restantes} min.")
            return

    if bcrypt.checkpw(st.session_state.senha.encode("utf-8"), usuario_row["senha_hash"].encode("utf-8")):
        supabase.table("usuarios").update({"tentativas_falhas": 0, "bloqueado_ate": None}).eq("id", usuario_row["id"]).execute()
        st.session_state.logado = True
        st.session_state.usuario_atual = {
            "id": usuario_row["id"], "nome": usuario_row["nome"],
            "usuario": usuario_row["usuario"], "papel": usuario_row["papel"],
        }
        st.toast(f"Acesso liberado! Bem-vindo, {usuario_row['nome']}.", icon=":material/lock_open:")
    else:
        novas_tentativas = int(usuario_row.get("tentativas_falhas") or 0) + 1
        dados_atualizacao = {"tentativas_falhas": novas_tentativas}
        bloqueou_agora = novas_tentativas >= MAX_TENTATIVAS_LOGIN
        if bloqueou_agora:
            dados_atualizacao["bloqueado_ate"] = (datetime.now(timezone.utc) + timedelta(minutes=BLOQUEIO_MINUTOS)).isoformat()
            dados_atualizacao["tentativas_falhas"] = 0
        supabase.table("usuarios").update(dados_atualizacao).eq("id", usuario_row["id"]).execute()
        if bloqueou_agora:
            st.error(f"Muitas tentativas incorretas. Conta bloqueada por {BLOQUEIO_MINUTOS} minutos.")
        else:
            st.error("Credenciais inválidas. Tente novamente.")


def fazer_logout():
    st.session_state.logado = False
    st.session_state.pop("usuario_atual", None)
    st.rerun()


# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.set_page_config(page_title="Sanini & Aimi | Gestão", page_icon=":material/settings:", layout="wide", initial_sidebar_state="expanded")

    config_empresa = buscar_config_empresa()
    nome_empresa = config_empresa.get("nome_empresa") or "Mecânica Sanini & Aimi"

    st.space("large")
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        with st.container(border=True):
            c_img, c_txt = st.columns([1, 4], vertical_alignment="center")
            with c_img:
                if os.path.exists("logo.png"):
                    st.image("logo.png", width="stretch")
                else:
                    st.markdown(":material/settings:", text_alignment="center")
            with c_txt:
                st.markdown(f"### {nome_empresa}")
                st.caption("Sistema de gestão de excelência")

            st.divider()

            with st.form("form_login"):
                st.text_input("Usuário do sistema", key="usuario", placeholder="Digite seu usuário", icon=":material/person:")
                st.text_input("Senha de acesso", type="password", key="senha", placeholder="••••••••", icon=":material/lock:")

                submit = st.form_submit_button("Entrar no sistema", type="primary", width="stretch")
                if submit:
                    fazer_login()

# ==========================================
# APLICAÇÃO PRINCIPAL (NAVEGAÇÃO POR MÓDULOS)
# ==========================================
else:
    # --- EFEITOS DE TRANSIÇÃO (cores/bordas vêm do tema em .streamlit/config.toml) ---
    # Seletor baseado em data-testid="stElementContainer", que envolve todo elemento
    # do Streamlit — mais estável entre versões do que nomes de classe internos.
    st.markdown("""
    <style>
        div[data-testid="stElementContainer"] button {
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        div[data-testid="stElementContainer"] button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 10px -2px rgb(59 130 246 / 0.35);
        }
    </style>
    """, unsafe_allow_html=True)

    config_empresa = buscar_config_empresa()
    nome_empresa = config_empresa.get("nome_empresa") or "Mecânica Sanini & Aimi"

    # Marca na barra lateral (acima do menu de navegação)
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", width=150)
    st.sidebar.markdown(f"### {nome_empresa}")
    st.sidebar.caption("Excelência automotiva")
    usuario_logado = st.session_state.get("usuario_atual", {})
    st.sidebar.markdown(f":material/person: **{usuario_logado.get('nome', '')}**")
    st.sidebar.caption(usuario_logado.get("papel", ""))
    st.sidebar.divider()
    if st.sidebar.button("Sair do sistema", icon=":material/logout:", width="stretch"):
        fazer_logout()
    st.sidebar.divider()

    pagina_inicio = st.Page("pages/inicio.py", title="Início", icon=":material/home:", url_path="inicio", default=True)

    pagina_clientes = st.Page("pages/cadastros/clientes.py", title="Clientes", icon=":material/group:", url_path="clientes")
    pagina_veiculos = st.Page("pages/cadastros/veiculos.py", title="Veículos", icon=":material/directions_car:", url_path="veiculos")
    pagina_estoque = st.Page("pages/cadastros/estoque.py", title="Estoque", icon=":material/inventory_2:", url_path="estoque")
    pagina_historico = st.Page("pages/cadastros/historico.py", title="Histórico do veículo", icon=":material/history:", url_path="historico")

    pagina_orc_consultar = st.Page("pages/orcamentos/consultar.py", title="Consultar orçamentos", icon=":material/list_alt:", url_path="orcamentos-consultar")
    pagina_orc_novo = st.Page("pages/orcamentos/novo.py", title="Novo orçamento", icon=":material/add_circle:", url_path="orcamentos-novo")
    pagina_orc_relatorios = st.Page("pages/orcamentos/relatorios.py", title="Relatórios", icon=":material/analytics:", url_path="orcamentos-relatorios")

    pagina_os_consultar = st.Page("pages/servicos/consultar.py", title="Consultar ordens de serviço", icon=":material/list_alt:", url_path="os-consultar")
    pagina_os_nova = st.Page("pages/servicos/nova_os.py", title="Nova ordem de serviço", icon=":material/add_circle:", url_path="os-nova")
    pagina_os_catalogo = st.Page("pages/servicos/catalogo.py", title="Catálogo de serviços", icon=":material/folder:", url_path="os-catalogo")
    pagina_os_relatorios = st.Page("pages/servicos/relatorios.py", title="Relatórios", icon=":material/analytics:", url_path="os-relatorios")

    pagina_dashboard = st.Page("pages/gestao/dashboard.py", title="Painel gerencial", icon=":material/query_stats:", url_path="dashboard")
    pagina_contas_receber = st.Page("pages/gestao/contas_a_receber.py", title="Contas a receber", icon=":material/payments:", url_path="contas-a-receber")
    pagina_usuarios = st.Page("pages/gestao/usuarios.py", title="Usuários", icon=":material/manage_accounts:", url_path="usuarios")
    pagina_log_atividades = st.Page("pages/gestao/log_atividades.py", title="Log de atividades", icon=":material/history_edu:", url_path="log-atividades")
    pagina_configuracoes = st.Page("pages/gestao/configuracoes.py", title="Configurações", icon=":material/settings:", url_path="configuracoes")

    paginas_navegacao = {
        "Início": [pagina_inicio],
        "Cadastros": [pagina_clientes, pagina_veiculos, pagina_estoque, pagina_historico],
        "Orçamentos": [pagina_orc_consultar, pagina_orc_novo, pagina_orc_relatorios],
        "Ordens de serviço": [pagina_os_consultar, pagina_os_nova, pagina_os_catalogo, pagina_os_relatorios],
    }
    if eh_gerente():
        paginas_navegacao["Gestão"] = [
            pagina_dashboard, pagina_contas_receber, pagina_usuarios, pagina_log_atividades, pagina_configuracoes,
        ]

    pg = st.navigation(paginas_navegacao, expanded=False)

    pg.run()
