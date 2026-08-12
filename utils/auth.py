import streamlit as st
from database import supabase


def usuario_atual():
    """Retorna o dict {'id', 'nome', 'usuario', 'papel'} do usuário logado, ou None."""
    return st.session_state.get("usuario_atual")


def eh_gerente():
    usuario = usuario_atual()
    return bool(usuario) and usuario.get("papel") == "Gerente"


def registrar_log(acao, entidade, entidade_ref=None, detalhes=None):
    """Grava uma linha em log_atividades associada ao usuário logado na sessão atual."""
    usuario = usuario_atual()
    if not usuario:
        return
    supabase.table("log_atividades").insert({
        "usuario_id": usuario["id"],
        "usuario_nome": usuario["nome"],
        "acao": acao,
        "entidade": entidade,
        "entidade_ref": str(entidade_ref) if entidade_ref is not None else None,
        "detalhes": detalhes,
    }).execute()
