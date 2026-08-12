import streamlit as st
from database import supabase
from utils.dados import buscar_catalogo_servicos
import time

st.set_page_config(layout="wide", page_title="Catálogo de Serviços | Sanini & Aimi")
st.title("Catálogo de serviços", anchor=False)
st.caption("Cadastre os tipos de serviço mais comuns (ex: Solda R$ 500, Usinagem R$ 100). O valor padrão pode ser ajustado na hora de montar cada orçamento ou serviço.")

df_catalogo = buscar_catalogo_servicos()

with st.container(border=True):
    with st.form("form_novo_catalogo", clear_on_submit=True):
        cc1, cc2 = st.columns([3, 1])
        with cc1: nome_cat = st.text_input("Nome do serviço")
        with cc2: valor_cat = st.number_input("Valor padrão (R$)", min_value=0.0, step=10.0)
        submit_cat = st.form_submit_button("Adicionar ao catálogo", type="primary", width="stretch", icon=":material/add:")
        if submit_cat and (time.time() - st.session_state.get("cat_ultimo_envio", 0) > 5):
            st.session_state["cat_ultimo_envio"] = time.time()
            if nome_cat:
                supabase.table("catalogo_servicos").insert({"nome": nome_cat, "valor_padrao": valor_cat}).execute()
                st.cache_data.clear()
                st.toast("Serviço adicionado ao catálogo.", icon=":material/check_circle:")
                st.rerun()

if df_catalogo.empty:
    st.info("Nenhum serviço cadastrado no catálogo ainda.")
else:
    for _, r in df_catalogo.iterrows():
        with st.container(border=True):
            rc1, rc2, rc3 = st.columns([4, 2, 1], vertical_alignment="center")
            with rc1: st.write(f"**{r['nome']}**")
            with rc2: st.markdown(f":green[R$ {r['valor_padrao']:,.2f}]")
            with rc3:
                if st.button("", key=f"del_cat_{r['id']}", icon=":material/delete:"):
                    supabase.table("catalogo_servicos").delete().eq("id", r['id']).execute()
                    st.cache_data.clear()
                    st.toast("Removido do catálogo.", icon=":material/delete:")
                    st.rerun()
