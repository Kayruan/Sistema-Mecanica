import streamlit as st
from database import supabase
from utils.dados import buscar_estoque_pecas
import time

st.set_page_config(layout="wide", page_title="Estoque | Sanini & Aimi")
st.title("📦 Controle de Estoque de Peças")
st.markdown("Cadastre as peças de uso frequente, acompanhe as quantidades disponíveis e receba alerta quando o estoque estiver baixo.")

df_estoque = buscar_estoque_pecas()

aba1, aba2 = st.tabs(["📦 Itens em Estoque", "➕ Cadastrar Peça"])

# --- ABA 2: CADASTRAR PEÇA ---
with aba2:
    with st.container(border=True):
        st.subheader("Ficha da Peça")
        with st.form("form_nova_peca_estoque", clear_on_submit=True):
            nome_peca = st.text_input("Nome da Peça *")
            c1, c2, c3 = st.columns(3)
            with c1: qtd_inicial = st.number_input("Quantidade Inicial", min_value=0, step=1)
            with c2: valor_venda = st.number_input("Valor de Venda Sugerido (R$)", min_value=0.0, step=10.0)
            with c3: estoque_min = st.number_input("Estoque Mínimo (alerta)", min_value=0, step=1, value=1)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("💾 Cadastrar Peça", type="primary", use_container_width=True):
                if not nome_peca:
                    st.error("⚠️ O campo Nome da Peça é obrigatório.")
                else:
                    supabase.table("estoque_pecas").insert({
                        "nome": nome_peca, "quantidade": int(qtd_inicial),
                        "valor_venda": float(valor_venda), "estoque_minimo": int(estoque_min)
                    }).execute()
                    st.cache_data.clear()
                    st.toast("✅ Peça cadastrada no estoque!")
                    time.sleep(0.6)
                    st.rerun()

# --- ABA 1: ITENS EM ESTOQUE ---
with aba1:
    busca_estoque = st.text_input("🔍 Buscar peça por nome...")
    st.divider()

    if df_estoque.empty:
        st.info("Nenhuma peça cadastrada no estoque ainda. Vá para a aba 'Cadastrar Peça'.")
    else:
        df_f_estoque = df_estoque.copy()
        if busca_estoque:
            df_f_estoque = df_f_estoque[df_f_estoque['nome'].str.contains(busca_estoque, case=False, na=False)]

        qtd_baixo = int((df_estoque['quantidade'] <= df_estoque['estoque_minimo']).sum())
        if qtd_baixo:
            st.warning(f"⚠️ {qtd_baixo} peça(s) com estoque baixo ou zerado — reponha o quanto antes.")

        if df_f_estoque.empty:
            st.warning("Nenhuma peça encontrada para esta busca.")
        else:
            for _, row in df_f_estoque.iterrows():
                estoque_baixo = row['quantidade'] <= row['estoque_minimo']
                with st.container(border=True):
                    c_info, c_qtd, c_btn = st.columns([4, 2, 1])
                    with c_info:
                        st.markdown(f"### 🔧 {row['nome']}")
                        st.caption(f"Valor de venda sugerido: R$ {row['valor_venda']:,.2f} | Estoque mínimo: {row['estoque_minimo']}")
                    with c_qtd:
                        st.markdown("<br>", unsafe_allow_html=True)
                        cor_qtd = "#dc2626" if estoque_baixo else "#16a34a"
                        st.markdown(f"<h3 style='color:{cor_qtd};'>{row['quantidade']} un.</h3>", unsafe_allow_html=True)
                        if estoque_baixo:
                            st.markdown("<span style='color:#dc2626;'>⚠️ Estoque Baixo</span>", unsafe_allow_html=True)
                    with c_btn:
                        st.markdown("<br>", unsafe_allow_html=True)
                        with st.popover("⚙️ Gerenciar", use_container_width=True):
                            st.markdown("**Ajustar Estoque**")
                            ajuste = st.number_input("Quantidade a somar (use negativo para retirar)", step=1, value=0, key=f"ajuste_{row['id']}")
                            if st.button("💾 Aplicar Ajuste", key=f"btn_ajuste_{row['id']}", type="primary", use_container_width=True):
                                nova_qtd = max(0, int(row['quantidade']) + int(ajuste))
                                supabase.table("estoque_pecas").update({"quantidade": nova_qtd}).eq("id", row['id']).execute()
                                st.cache_data.clear()
                                st.toast("✅ Estoque atualizado!")
                                time.sleep(0.5)
                                st.rerun()

                            st.divider()
                            st.markdown("**Editar Cadastro**")
                            e_nome = st.text_input("Nome", value=row['nome'], key=f"n_est_{row['id']}")
                            e_valor = st.number_input("Valor de Venda (R$)", value=float(row['valor_venda']), min_value=0.0, step=10.0, key=f"v_est_{row['id']}")
                            e_min = st.number_input("Estoque Mínimo", value=int(row['estoque_minimo']), min_value=0, step=1, key=f"m_est_{row['id']}")
                            if st.button("💾 Salvar Alterações", key=f"upd_est_{row['id']}", use_container_width=True):
                                supabase.table("estoque_pecas").update({
                                    "nome": e_nome, "valor_venda": float(e_valor), "estoque_minimo": int(e_min)
                                }).eq("id", row['id']).execute()
                                st.cache_data.clear()
                                st.toast("✅ Peça atualizada!")
                                time.sleep(0.5)
                                st.rerun()

                            st.divider()
                            if st.button("🗑️ Excluir do Estoque", key=f"del_est_{row['id']}", use_container_width=True):
                                supabase.table("estoque_pecas").delete().eq("id", row['id']).execute()
                                st.cache_data.clear()
                                st.toast("🗑️ Removida do estoque!")
                                time.sleep(0.5)
                                st.rerun()
