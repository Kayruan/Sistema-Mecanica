import streamlit as st
from database import supabase
from utils.dados import buscar_estoque_pecas
import time

st.set_page_config(layout="wide", page_title="Estoque | Sanini & Aimi")
st.title("Controle de estoque de peças", anchor=False)
st.markdown("Cadastre as peças de uso frequente, acompanhe as quantidades disponíveis e receba alerta quando o estoque estiver baixo.")

df_estoque = buscar_estoque_pecas()

aba1, aba2 = st.tabs(["Itens em estoque", "Cadastrar peça"])


@st.dialog("Gerenciar peça", width="large")
def gerenciar_peca(row):
    st.markdown("**Ajustar estoque**")
    ajuste = st.number_input("Quantidade a somar (use negativo para retirar)", step=1, value=0, key=f"ajuste_{row['id']}")
    if st.button("Aplicar ajuste", key=f"btn_ajuste_{row['id']}", type="primary", icon=":material/sync_alt:"):
        nova_qtd = max(0, int(row['quantidade']) + int(ajuste))
        supabase.table("estoque_pecas").update({"quantidade": nova_qtd}).eq("id", row['id']).execute()
        st.cache_data.clear()
        st.toast("Estoque atualizado.", icon=":material/check_circle:")
        st.rerun()

    st.divider()
    st.markdown("**Editar cadastro**")
    e_nome = st.text_input("Nome", value=row['nome'], key=f"n_est_{row['id']}")
    e_valor = st.number_input("Valor de venda (R$)", value=float(row['valor_venda']), min_value=0.0, step=10.0, key=f"v_est_{row['id']}")
    e_min = st.number_input("Estoque mínimo", value=int(row['estoque_minimo']), min_value=0, step=1, key=f"m_est_{row['id']}")

    with st.container(horizontal=True):
        if st.button("Salvar alterações", key=f"upd_est_{row['id']}", icon=":material/save:"):
            supabase.table("estoque_pecas").update({
                "nome": e_nome, "valor_venda": float(e_valor), "estoque_minimo": int(e_min)
            }).eq("id", row['id']).execute()
            st.cache_data.clear()
            st.toast("Peça atualizada.", icon=":material/check_circle:")
            st.rerun()
        if st.button("Excluir do estoque", key=f"del_est_{row['id']}", icon=":material/delete:"):
            supabase.table("estoque_pecas").delete().eq("id", row['id']).execute()
            st.cache_data.clear()
            st.toast("Removida do estoque.", icon=":material/delete:")
            st.rerun()


# --- ABA 2: CADASTRAR PEÇA ---
with aba2:
    with st.container(border=True):
        st.subheader("Ficha da peça", anchor=False)
        with st.form("form_nova_peca_estoque", clear_on_submit=True):
            nome_peca = st.text_input("Nome da peça *")
            c1, c2, c3 = st.columns(3)
            with c1: qtd_inicial = st.number_input("Quantidade inicial", min_value=0, step=1)
            with c2: valor_venda = st.number_input("Valor de venda sugerido (R$)", min_value=0.0, step=10.0)
            with c3: estoque_min = st.number_input("Estoque mínimo (alerta)", min_value=0, step=1, value=1)

            submit_peca = st.form_submit_button("Cadastrar peça", type="primary", width="stretch", icon=":material/save:")
            if submit_peca and (time.time() - st.session_state.get("peca_ultimo_envio", 0) > 5):
                st.session_state["peca_ultimo_envio"] = time.time()
                if not nome_peca:
                    st.error("O campo Nome da Peça é obrigatório.", icon=":material/error:")
                else:
                    supabase.table("estoque_pecas").insert({
                        "nome": nome_peca, "quantidade": int(qtd_inicial),
                        "valor_venda": float(valor_venda), "estoque_minimo": int(estoque_min)
                    }).execute()
                    st.cache_data.clear()
                    st.toast("Peça cadastrada no estoque.", icon=":material/check_circle:")
                    st.rerun()

# --- ABA 1: ITENS EM ESTOQUE ---
with aba1:
    busca_estoque = st.text_input("Buscar peça por nome", icon=":material/search:")

    if df_estoque.empty:
        st.info("Nenhuma peça cadastrada no estoque ainda. Vá para a aba \"Cadastrar peça\".")
    else:
        df_f_estoque = df_estoque.copy()
        if busca_estoque:
            df_f_estoque = df_f_estoque[df_f_estoque['nome'].str.contains(busca_estoque, case=False, na=False)]

        qtd_baixo = int((df_estoque['quantidade'] <= df_estoque['estoque_minimo']).sum())
        if qtd_baixo:
            st.warning(f"{qtd_baixo} peça(s) com estoque baixo ou zerado — reponha o quanto antes.", icon=":material/warning:")

        if df_f_estoque.empty:
            st.warning("Nenhuma peça encontrada para esta busca.")
        else:
            for _, row in df_f_estoque.iterrows():
                estoque_baixo = row['quantidade'] <= row['estoque_minimo']
                with st.container(border=True):
                    c_info, c_qtd, c_btn = st.columns([4, 2, 1], vertical_alignment="center")
                    with c_info:
                        st.markdown(f"#### {row['nome']}")
                        st.caption(f"Valor de venda sugerido: R$ {row['valor_venda']:,.2f}  ·  Estoque mínimo: {row['estoque_minimo']}")
                    with c_qtd:
                        if estoque_baixo:
                            st.markdown(f":red[**{row['quantidade']} un.**]")
                            st.badge("Estoque baixo", icon=":material/warning:", color="red")
                        else:
                            st.markdown(f":green[**{row['quantidade']} un.**]")
                    with c_btn:
                        if st.button("Gerenciar", key=f"manage_est_{row['id']}", icon=":material/settings:", width="stretch"):
                            gerenciar_peca(row)
