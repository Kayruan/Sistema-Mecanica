import streamlit as st
from database import supabase
from utils.gerador_pdf import gerar_relatorio_servico
from datetime import date
import pandas as pd
import json

if not st.session_state.get("logado"):
    st.warning("⚠️ Faça login.")
    st.stop()

st.title("🛠️ Serviços e Dossiês")

@st.cache_data(ttl=10)
def buscar_dados():
    veic = supabase.table("veiculos").select("*").execute().data
    servs = supabase.table("servicos_realizados").select("*").order("id", desc=True).execute().data
    return pd.DataFrame(veic), pd.DataFrame(servs)

df_veiculos, df_servicos = buscar_dados()
lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []

aba1, aba2 = st.tabs(["📋 Histórico e Gerar PDF", "➕ Registrar Novo Serviço"])

# --- ABA 2: NOVO SERVIÇO (SISTEMA DINÂMICO DE ITENS) ---
with aba2:
    st.subheader("Registrar Manutenção")
    
    placa_selecionada = st.selectbox("Veículo (Placa) *", lista_placas)
    data_serv = st.date_input("Data do Serviço", date.today())
    descricao = st.text_area("Descrição da Mão de Obra")
    
    st.divider()
    st.markdown("### ⚙️ Adicionar Peças e Materiais")
    
    # Variável na sessão para guardar os itens na memória antes de salvar no banco
    if "lista_pecas" not in st.session_state:
        st.session_state.lista_pecas = []

    # Formulário visual para adicionar item
    with st.container(border=True):
        col_p1, col_p2, col_p3, col_p4 = st.columns([4, 1, 2, 2])
        with col_p1: n_peca = st.text_input("Nome da Peça")
        with col_p2: n_qtd = st.number_input("Qtd", min_value=1, step=1)
        with col_p3: n_val = st.number_input("V. Unitário (R$)", min_value=0.0, step=10.0)
        with col_p4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Adicionar Peça", use_container_width=True):
                if n_peca:
                    st.session_state.lista_pecas.append({
                        "Peça/Descrição": n_peca, "Quantidade": n_qtd, 
                        "Valor Unitário (R$)": n_val, "Subtotal": n_qtd * n_val
                    })
                    st.rerun()

    # Mostra os itens adicionados como cardzinhos na tela
    total_pecas = 0.0
    for i, item in enumerate(st.session_state.lista_pecas):
        with st.container(border=True):
            ci, cd = st.columns([6, 1])
            with ci:
                st.write(f"🔧 **{item['Peça/Descrição']}** | Qtd: {item['Quantidade']} | Subtotal: **R$ {item['Subtotal']:.2f}**")
            with cd:
                if st.button("🗑️", key=f"del_item_{i}"):
                    st.session_state.lista_pecas.pop(i)
                    st.rerun()
        total_pecas += item['Subtotal']
        
    st.divider()
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1: valor_mao_obra = st.number_input("Valor Mão de Obra (R$)", min_value=0.0, step=10.0)
    with col_f2: st.metric("Total de Peças", f"R$ {total_pecas:.2f}")
    with col_f3: st.metric("VALOR FINAL DO SERVIÇO", f"R$ {total_pecas + valor_mao_obra:.2f}")
        
    fotos = st.file_uploader("📸 Anexar Fotos (Serão impressas no PDF)", accept_multiple_files=True, type=['jpg', 'png'])
    
    if st.button("💾 Salvar Serviço Completo", type="primary", use_container_width=True):
        urls_salvas = []
        if fotos:
            for foto in fotos:
                nome_arquivo = f"{placa_selecionada}_{foto.name}"
                try:
                    supabase.storage.from_("fotos_mecanica").upload(nome_arquivo, foto.getvalue())
                    urls_salvas.append(supabase.storage.from_("fotos_mecanica").get_public_url(nome_arquivo))
                except:
                    pass 
        
        dados_servico = {
            "placa_veiculo": placa_selecionada, "data_servico": str(data_serv),
            "descricao_servico": descricao, "pecas_usadas": json.dumps(st.session_state.lista_pecas), 
            "valor_mao_de_obra": valor_mao_obra, "valor_pecas": float(total_pecas),
            "urls_fotos": ",".join(urls_salvas)
        }
        supabase.table("servicos_realizados").insert(dados_servico).execute()
        st.session_state.lista_pecas = [] # Limpa a lista após salvar
        st.success("✅ Serviço registrado! Vá para a aba de Histórico.")

# --- ABA 1: HISTÓRICO E PDF (CARDS ELEGANTES) ---
with aba1:
    col_fil1, col_fil2 = st.columns(2)
    with col_fil1:
        f_placa_serv = st.selectbox("Buscar por Placa", ["Todas"] + lista_placas)
    with col_fil2:
        f_data_serv = st.date_input("Filtrar por Período", [])
        
    df_filtrado_s = df_servicos.copy()
    if not df_filtrado_s.empty:
        if f_placa_serv != "Todas":
            df_filtrado_s = df_filtrado_s[df_filtrado_s['placa_veiculo'] == f_placa_serv]
        if len(f_data_serv) == 2:
            df_filtrado_s['data_servico'] = pd.to_datetime(df_filtrado_s['data_servico']).dt.date
            df_filtrado_s = df_filtrado_s[(df_filtrado_s['data_servico'] >= f_data_serv[0]) & (df_filtrado_s['data_servico'] <= f_data_serv[1])]

    if df_filtrado_s.empty:
        st.info("Nenhum serviço registrado para os filtros aplicados.")
    else:
        st.write("### Ordens de Serviço")
        
        for index, row in df_filtrado_s.iterrows():
            with st.container(border=True):
                c_inf, c_val, c_btn = st.columns([3, 1, 1])
                
                with c_inf:
                    st.markdown(f"**🚗 Placa: {row['placa_veiculo']}** &nbsp;&nbsp;|&nbsp;&nbsp; 📅 Data: {row['data_servico']}")
                    st.write(f"*{str(row['descricao_servico'])[:80]}...*")
                
                with c_val:
                    st.markdown(f"**Total:**")
                    st.markdown(f"<h4 style='color: green;'>R$ {row['valor_total']:,.2f}</h4>", unsafe_allow_html=True)
                
                with c_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.popover("⚙️ Opções", use_container_width=True):
                        # Botão de Gerar PDF Individual deste serviço
                        if st.button("📄 Gerar PDF (Este Serviço)", key=f"pdf_{row['id']}"):
                            with st.spinner("Gerando PDF..."):
                                veic = df_veiculos[df_veiculos['placa'] == row['placa_veiculo']].iloc[0].to_dict()
                                orcs = supabase.table("orcamentos").select("*").eq("placa_veiculo", row['placa_veiculo']).execute().data
                                caminho_pdf = gerar_relatorio_servico(row['placa_veiculo'], veic, orcs, [row.to_dict()])
                                
                                with open(caminho_pdf, "rb") as pdf_file:
                                    st.download_button("📥 Clique aqui para Baixar", data=pdf_file, file_name=f"OS_{row['placa_veiculo']}.pdf", mime="application/pdf", type="primary")
                        
                        st.divider()
                        if st.button("🗑️ Excluir Serviço", key=f"dels_{row['id']}"):
                            supabase.table("servicos_realizados").delete().eq("id", row['id']).execute()
                            st.rerun()