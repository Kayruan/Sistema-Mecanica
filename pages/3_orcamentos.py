import streamlit as st
from database import supabase
import pandas as pd
from datetime import date, timedelta

if not st.session_state.get("logado"):
    st.warning("⚠️ Faça login na página principal.")
    st.stop()

st.title("📝 Gestão de Orçamentos")

@st.cache_data(ttl=10)
def carregar_dados():
    veiculos = supabase.table("veiculos").select("placa, cliente_nome").execute().data
    orcamentos = supabase.table("orcamentos").select("*").order("id", desc=True).execute().data
    return pd.DataFrame(veiculos), pd.DataFrame(orcamentos)

df_veiculos, df_orcamentos = carregar_dados()
lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []

if not lista_placas:
    st.info("Cadastre um veículo primeiro.")
    st.stop()

aba1, aba2 = st.tabs(["📋 Meus Orçamentos (Gestão)", "➕ Novo Orçamento"])

# --- ABA 2: CRIAR NOVO (Formulário limpo) ---
with aba2:
    with st.container(border=True):
        st.subheader("Gerar Novo Orçamento")
        with st.form("form_novo_orcamento", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                placa_selecionada = st.selectbox("Veículo (Placa) *", lista_placas)
                data_orcamento = st.date_input("Data", date.today())
            with col2:
                valor = st.number_input("Valor Total Estimado (R$)", min_value=0.0, step=10.0)
                status = st.selectbox("Status Atual", ["Pendente", "Aprovado", "Em Execução", "Finalizado", "Cancelado"])
                
            descricao = st.text_area("Descrição do Problema Relatado")
            pecas = st.text_area("Peças Necessárias (Lista simples)")
            
            if st.form_submit_button("Salvar Orçamento", type="primary"):
                dados = {
                    "placa_veiculo": placa_selecionada, "data": str(data_orcamento),
                    "descricao_problema": descricao, "pecas_necessarias": pecas,
                    "valor_total": valor, "status": status
                }
                supabase.table("orcamentos").insert(dados).execute()
                st.success("✅ Orçamento salvo! Vá para a primeira aba para visualizá-lo.")

# --- ABA 1: GESTÃO COM CARDS E FILTROS AVANÇADOS ---
with aba1:
    # Filtros em linha para economizar espaço
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        placas_filtro = ["Todas"] + lista_placas
        f_placa = st.selectbox("Filtrar por Placa", placas_filtro)
    with col_f2:
        clientes_filtro = ["Todos"] + df_veiculos['cliente_nome'].dropna().unique().tolist()
        f_cliente = st.selectbox("Filtrar por Cliente", clientes_filtro)
    with col_f3:
        f_data = st.date_input("Período", [])

    # Aplicando filtros
    df_filtrado = df_orcamentos.copy()
    if not df_filtrado.empty:
        if f_placa != "Todas":
            df_filtrado = df_filtrado[df_filtrado['placa_veiculo'] == f_placa]
        if f_cliente != "Todos":
            placas_do_cliente = df_veiculos[df_veiculos['cliente_nome'] == f_cliente]['placa'].tolist()
            df_filtrado = df_filtrado[df_filtrado['placa_veiculo'].isin(placas_do_cliente)]
        if len(f_data) == 2:
            df_filtrado['data'] = pd.to_datetime(df_filtrado['data']).dt.date
            df_filtrado = df_filtrado[(df_filtrado['data'] >= f_data[0]) & (df_filtrado['data'] <= f_data[1])]

    st.divider()

    if df_filtrado.empty:
        st.info("Nenhum orçamento encontrado com estes filtros.")
    else:
        # GERAÇÃO DOS CARDS DE ORÇAMENTO
        for index, row in df_filtrado.iterrows():
            # Busca o nome do cliente cruzando com a tabela de veículos
            nome_cli = df_veiculos[df_veiculos['placa'] == row['placa_veiculo']]['cliente_nome'].values
            cliente_txt = nome_cli[0] if len(nome_cli) > 0 else "Sem Nome"
            
            with st.container(border=True):
                c_info, c_status, c_acao = st.columns([3, 1, 1])
                
                with c_info:
                    st.markdown(f"### 🚗 {row['placa_veiculo']} &nbsp;&nbsp;|&nbsp;&nbsp; 👤 {cliente_txt}")
                    st.write(f"**Data:** {row['data']} | **Problema:** {row['descricao_problema']}")
                    st.markdown(f"**Valor Estimado:** R$ {row['valor_total']:,.2f}")
                
                with c_status:
                    st.markdown("<br>", unsafe_allow_html=True)
                    # Exibe o status com uma cor baseada na palavra
                    cor = "green" if row['status'] == "Aprovado" else "orange" if row['status'] == "Pendente" else "gray"
                    st.markdown(f"<h4 style='color: {cor};'>{row['status']}</h4>", unsafe_allow_html=True)
                
                with c_acao:
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.popover("⚙️ Gerenciar", use_container_width=True):
                        st.markdown("**Atualizar Status**")
                        opcoes_status = ["Pendente", "Aprovado", "Em Execução", "Finalizado", "Cancelado"]
                        idx_atual = opcoes_status.index(row['status']) if row['status'] in opcoes_status else 0
                        novo_st = st.selectbox("Status", opcoes_status, index=idx_atual, key=f"st_{row['id']}")
                        
                        if st.button("💾 Salvar Status", key=f"btn_st_{row['id']}", type="primary"):
                            supabase.table("orcamentos").update({"status": novo_st}).eq("id", row['id']).execute()
                            st.rerun()
                            
                        st.divider()
                        if st.button("🗑️ Excluir", key=f"del_{row['id']}"):
                            supabase.table("orcamentos").delete().eq("id", row['id']).execute()
                            st.rerun()