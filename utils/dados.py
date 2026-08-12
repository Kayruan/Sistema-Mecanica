import streamlit as st
from database import supabase
import pandas as pd

OPCOES_STATUS_ORCAMENTO = ["Pendente", "Aprovado", "Cancelado", "Finalizado"]
COR_STATUS_ORCAMENTO = {
    "Pendente": "orange",
    "Aprovado": "blue",
    "Cancelado": "gray",
    "Finalizado": "green",
}

OPCOES_STATUS_PAGAMENTO = ["Pendente", "Parcial", "Pago"]
COR_STATUS_PAGAMENTO = {"Pendente": "red", "Parcial": "orange", "Pago": "green"}
OPCOES_FORMA_PAGAMENTO = ["Dinheiro", "Pix", "Cartão", "Boleto"]

OPCOES_STATUS_OS = ["Em Andamento", "Finalizada"]
COR_STATUS_OS = {"Em Andamento": "blue", "Finalizada": "green"}

OPCOES_PAPEL_USUARIO = ["Funcionario", "Gerente"]


@st.cache_data(ttl=5)
def buscar_clientes(colunas="*"):
    resp = supabase.table("clientes").select(colunas).order("nome").execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


@st.cache_data(ttl=5)
def buscar_veiculos():
    resp = supabase.table("veiculos").select("*").execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


@st.cache_data(ttl=5)
def buscar_orcamentos():
    resp = supabase.table("orcamentos").select("*").order("data", desc=True).execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


@st.cache_data(ttl=5)
def buscar_servicos():
    resp = supabase.table("servicos_realizados").select("*").order("data_servico", desc=True).execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


@st.cache_data(ttl=5)
def buscar_catalogo_servicos():
    resp = supabase.table("catalogo_servicos").select("*").order("nome").execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


@st.cache_data(ttl=5)
def buscar_estoque_pecas():
    resp = supabase.table("estoque_pecas").select("*").order("nome").execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


@st.cache_data(ttl=5)
def buscar_usuarios():
    resp = supabase.table("usuarios").select("id, nome, usuario, papel, ativo, criado_em").order("nome").execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


@st.cache_data(ttl=5)
def buscar_log_atividades():
    resp = supabase.table("log_atividades").select("*").order("criado_em", desc=True).limit(1000).execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()


@st.cache_data(ttl=30)
def buscar_config_empresa():
    try:
        resp = supabase.table("configuracoes_admin").select("*").execute()
        return resp.data[0] if resp.data else {}
    except Exception:
        return {}


def montar_veiculo_e_cliente(df_veiculos, df_clientes, placa):
    """Retorna (dict_veiculo, dict_cliente) a partir da placa, prontos para PDFs e telas de detalhe."""
    veic_row = df_veiculos[df_veiculos['placa'] == placa]
    veic = veic_row.iloc[0].to_dict() if not veic_row.empty else {}
    cli = {}
    c_id = veic.get('cliente_id')
    if pd.notna(c_id):
        cli_row = df_clientes[df_clientes['id'] == c_id]
        if not cli_row.empty:
            cli = cli_row.iloc[0].to_dict()
    return veic, cli
