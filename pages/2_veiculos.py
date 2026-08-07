import streamlit as st
from database import supabase
import pandas as pd
import re

if not st.session_state.get("logado"):
    st.warning("⚠️ Faça login.")
    st.stop()

st.title("🚗 Frota e Clientes")

def validar_placa(placa):
    padrao = re.compile(r'^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$')
    return bool(padrao.match(placa))

def validar_chassi(chassi):
    padrao = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')
    return bool(padrao.match(chassi))

aba1, aba2 = st.tabs(["📋 Gestão de Veículos (Cards)", "➕ Cadastrar Novo"])

# --- ABA 2: CADASTRO (Coloquei na aba 2 para focar a visualização na aba 1) ---
with aba2:
    with st.container(border=True):
        st.subheader("Preencha os dados do novo veículo")
        with st.form("form_novo", clear_on_submit=True):
            placa = st.text_input("Placa (Obrigatório) *", max_chars=7).upper().strip()
            
            c1, c2, c3 = st.columns(3)
            with c1:
                marca = st.text_input("Marca")
                modelo = st.text_input("Modelo")
            with c2:
                ano = st.number_input("Ano", min_value=1950, max_value=2030, step=1, value=2015)
                chassi = st.text_input("Número do Chassi", max_chars=17).upper().strip()
            with c3:
                cliente_nome = st.text_input("Proprietário")
                cliente_telefone = st.text_input("WhatsApp / Celular")

            if st.form_submit_button("Salvar Veículo", type="primary"):
                if not validar_placa(placa):
                    st.error("⚠️ Placa inválida!")
                elif chassi and not validar_chassi(chassi):
                    st.error("⚠️ Chassi inválido!")
                else:
                    dados = {"placa": placa, "marca": marca, "modelo": modelo, "ano": ano, 
                             "chassi": chassi, "cliente_nome": cliente_nome, "cliente_telefone": cliente_telefone}
                    try:
                        supabase.table("veiculos").insert(dados).execute()
                        st.success(f"✅ Veículo {placa} cadastrado! Vá para a primeira aba para visualizá-lo.")
                    except:
                        st.error("Erro: Placa já existe ou falha de conexão.")

# --- ABA 1: VISUALIZAÇÃO EM CARDS E EDIÇÃO ---
with aba1:
    busca = st.text_input("🔍 Buscar veículo por Placa, Cliente ou Modelo...")
    
    resp = supabase.table("veiculos").select("*").execute()
    if not resp.data:
        st.info("Nenhum veículo cadastrado ainda.")
    else:
        df = pd.DataFrame(resp.data)
        
        # Lógica de barra de pesquisa simples
        if busca:
            busca = busca.lower()
            mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(busca).any(), axis=1)
            df = df[mask]
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # GERAÇÃO DOS CARDS
        for index, row in df.iterrows():
            with st.container(border=True):
                col_info, col_acoes = st.columns([4, 1])
                
                with col_info:
                    st.markdown(f"### {row['marca']} {row['modelo']} ({row['ano']})")
                    st.markdown(f"**Placa:** `{row['placa']}` &nbsp;&nbsp;|&nbsp;&nbsp; **Chassi:** `{row['chassi'] or 'Não informado'}`")
                    st.markdown(f"👤 **{row['cliente_nome'] or 'Sem Nome'}** &nbsp;&nbsp;📞 {row['cliente_telefone'] or 'Sem Telefone'}")
                
                with col_acoes:
                    st.markdown("<br>", unsafe_allow_html=True)
                    # O popover abre um menu flutuante para edição sem sair da tela
                    with st.popover("⚙️ Gerenciar", use_container_width=True):
                        st.markdown("**Editar Cadastro**")
                        
                        # Placa e Chassi bloqueados (disabled=True)
                        edit_placa = st.text_input("Placa", value=row['placa'], disabled=True, key=f"p_{row['placa']}")
                        edit_chassi = st.text_input("Chassi", value=row['chassi'], disabled=True, key=f"c_{row['placa']}")
                        
                        edit_marca = st.text_input("Marca", value=row['marca'], key=f"m_{row['placa']}")
                        edit_mod = st.text_input("Modelo", value=row['modelo'], key=f"mod_{row['placa']}")
                        edit_ano = st.number_input("Ano", value=row['ano'], step=1, key=f"a_{row['placa']}")
                        edit_cli = st.text_input("Proprietário", value=row['cliente_nome'], key=f"cli_{row['placa']}")
                        edit_tel = st.text_input("Telefone", value=row['cliente_telefone'], key=f"tel_{row['placa']}")
                        
                        if st.button("💾 Salvar Alterações", key=f"btn_salvar_{row['placa']}", type="primary"):
                            novos_dados = {
                                "marca": edit_marca, "modelo": edit_mod, "ano": edit_ano, 
                                "cliente_nome": edit_cli, "cliente_telefone": edit_tel
                            }
                            supabase.table("veiculos").update(novos_dados).eq("placa", row['placa']).execute()
                            st.rerun() # Atualiza a tela na hora
                            
                        st.divider()
                        
                        if st.button("🗑️ Excluir Veículo", key=f"btn_excluir_{row['placa']}"):
                            supabase.table("veiculos").delete().eq("placa", row['placa']).execute()
                            st.rerun()