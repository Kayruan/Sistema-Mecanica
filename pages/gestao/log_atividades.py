import streamlit as st
from utils.dados import buscar_log_atividades, buscar_usuarios
from utils.paginacao import paginar
from utils.auth import eh_gerente
import pandas as pd

st.set_page_config(layout="wide", page_title="Log de Atividades | Sanini & Aimi")

if not eh_gerente():
    st.error("Acesso restrito a usuários com papel Gerente.", icon=":material/lock:")
    st.stop()

st.title("Log de atividades", anchor=False)
st.caption("Auditoria das ações realizadas no sistema, com o responsável por cada uma.")

df_log = buscar_log_atividades()
df_usuarios = buscar_usuarios()

if df_log.empty:
    st.info("Nenhuma atividade registrada ainda.")
    st.stop()

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    lista_usuarios = ["Todos"] + df_usuarios['nome'].tolist() if not df_usuarios.empty else ["Todos"]
    f_usuario = st.selectbox("Usuário", lista_usuarios)
with col_f2:
    lista_entidades = ["Todas"] + sorted(df_log['entidade'].dropna().unique().tolist())
    f_entidade = st.selectbox("Tipo de registro", lista_entidades)
with col_f3:
    f_data = st.date_input("Período (início e fim)", [])

df_filtrado = df_log.copy()
df_filtrado['criado_em'] = pd.to_datetime(df_filtrado['criado_em'])

if f_usuario != "Todos":
    df_filtrado = df_filtrado[df_filtrado['usuario_nome'] == f_usuario]
if f_entidade != "Todas":
    df_filtrado = df_filtrado[df_filtrado['entidade'] == f_entidade]
if len(f_data) == 2:
    df_filtrado = df_filtrado[
        (df_filtrado['criado_em'].dt.date >= f_data[0]) & (df_filtrado['criado_em'].dt.date <= f_data[1])
    ]

st.markdown(f"**{len(df_filtrado)} registro(s) de atividade**")

ICONE_ACAO = {"criou": ":material/add_circle:", "editou": ":material/edit:", "excluiu": ":material/delete:"}
COR_ACAO = {"criou": "green", "editou": "blue", "excluiu": "red"}

df_pagina = paginar(df_filtrado, "log_atividades", por_pagina=20)

for _, row in df_pagina.iterrows():
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 4, 2], vertical_alignment="center")
        with c1:
            st.markdown(f"**:material/person: {row['usuario_nome']}**")
            st.caption(row['criado_em'].strftime("%d/%m/%Y %H:%M"))
        with c2:
            st.badge(row['acao'], icon=ICONE_ACAO.get(row['acao'], ":material/info:"), color=COR_ACAO.get(row['acao'], "gray"))
            st.write(f"{row['entidade'].capitalize()}" + (f" · {row['entidade_ref']}" if row.get('entidade_ref') else ""))
            if row.get('detalhes'):
                st.caption(row['detalhes'])
        with c3:
            pass
