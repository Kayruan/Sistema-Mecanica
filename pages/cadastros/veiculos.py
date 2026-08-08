import streamlit as st
from database import supabase
from utils.dados import buscar_veiculos, buscar_clientes
import pandas as pd
import re
import time

st.set_page_config(layout="wide", page_title="Veículos | Sanini & Aimi")
st.title("🚗 Cadastro de Veículos")


def validar_placa(placa):
    padrao = re.compile(r'^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$')
    return bool(padrao.match(placa))


def validar_chassi(chassi):
    if not chassi: return True  # Chassi opcional
    padrao = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')
    return bool(padrao.match(chassi))


df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes("id, nome, cpf_cnpj")

# Dicionário para facilitar o selectbox de clientes: "João Silva (Doc: ...)" -> id
if not df_clientes.empty:
    opcoes_clientes = {f"{row['nome']} (Doc: {row['cpf_cnpj'] or 'S/N'})": row['id'] for _, row in df_clientes.iterrows()}
else:
    opcoes_clientes = {}

aba1, aba2 = st.tabs(["📋 Consultar Veículos", "➕ Cadastrar Veículo"])

# --- ABA 2: CADASTRAR VEÍCULO ---
with aba2:
    if not opcoes_clientes:
        st.warning("⚠️ Você precisa cadastrar pelo menos um Cliente antes de registrar um veículo.")
    else:
        with st.container(border=True):
            st.subheader("Ficha do Veículo")
            with st.form("form_novo_veiculo", clear_on_submit=True):
                cliente_selecionado = st.selectbox("Selecione o Proprietário (Cliente) *", list(opcoes_clientes.keys()))

                c1, c2, c3 = st.columns(3)
                with c1:
                    placa = st.text_input("Placa (Obrigatório) *", max_chars=7, help="Ex: ABC1234 ou ABC1D23").upper().strip()
                    ano = st.number_input("Ano Fabricação", min_value=1950, max_value=2030, step=1, value=2015)
                with c2:
                    marca = st.text_input("Marca")
                    chassi = st.text_input("Número do Chassi", max_chars=17).upper().strip()
                with c3:
                    modelo = st.text_input("Modelo")

                st.markdown("<br>", unsafe_allow_html=True)
                submit = st.form_submit_button("💾 Cadastrar Veículo", type="primary", use_container_width=True)

                if submit:
                    if not validar_placa(placa):
                        st.error("⚠️ Placa inválida! Use o formato ABC1234 ou ABC1D23 (Sem espaços ou traços).")
                    elif not validar_chassi(chassi):
                        st.error("⚠️ Chassi inválido! Deve conter exatos 17 caracteres válidos.")
                    else:
                        dados_veiculo = {
                            "placa": placa, "marca": marca, "modelo": modelo,
                            "ano": ano, "chassi": chassi,
                            "cliente_id": opcoes_clientes[cliente_selecionado]
                        }
                        try:
                            supabase.table("veiculos").insert(dados_veiculo).execute()
                            st.cache_data.clear()
                            st.toast("✅ Veículo cadastrado com sucesso!")
                            time.sleep(0.8)
                            st.rerun()
                        except Exception:
                            st.error("Erro ao salvar: Placa já existente ou falha no banco.")

# --- ABA 1: GESTÃO DE VEÍCULOS ---
with aba1:
    busca_v = st.text_input("🔍 Buscar por Placa, Marca ou Modelo...")
    st.divider()

    if df_veiculos.empty:
        st.info("Nenhum veículo cadastrado ainda.")
    else:
        df_f = df_veiculos.copy()
        if busca_v:
            busca_v = busca_v.lower()
            mask = df_f.apply(lambda row: row.astype(str).str.lower().str.contains(busca_v).any(), axis=1)
            df_f = df_f[mask]

        for index, row in df_f.iterrows():
            with st.container(border=True):
                col_info, col_acoes = st.columns([5, 1])

                dono_nome = "Cliente não vinculado"
                if pd.notna(row.get('cliente_id')):
                    dono = df_clientes[df_clientes['id'] == row['cliente_id']]
                    if not dono.empty:
                        dono_nome = dono.iloc[0]['nome']
                elif row.get('cliente_nome'):
                    dono_nome = f"{row['cliente_nome']} (Cadastro Antigo)"

                with col_info:
                    st.markdown(f"### {row['marca']} {row['modelo']} ({row['ano']})")
                    st.markdown(f"**Placa:** `{row['placa']}` &nbsp;&nbsp;|&nbsp;&nbsp; **Chassi:** `{row['chassi'] or 'Não informado'}`")
                    st.write(f"👤 **Proprietário:** {dono_nome}")

                with col_acoes:
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.popover("⚙️ Gerenciar", use_container_width=True):
                        st.markdown("**Editar Cadastro**")

                        edit_marca = st.text_input("Marca", value=row['marca'], key=f"m_{row['placa']}")
                        edit_mod = st.text_input("Modelo", value=row['modelo'], key=f"mod_{row['placa']}")
                        edit_ano = st.number_input("Ano", value=row['ano'], step=1, key=f"a_{row['placa']}")

                        if st.button("💾 Salvar Alterações", key=f"upd_{row['placa']}", type="primary", use_container_width=True):
                            novos_dados = {"marca": edit_marca, "modelo": edit_mod, "ano": edit_ano}
                            supabase.table("veiculos").update(novos_dados).eq("placa", row['placa']).execute()
                            st.cache_data.clear()
                            st.toast("✅ Veículo Atualizado!")
                            time.sleep(0.5)
                            st.rerun()

                        st.divider()
                        if st.button("🗑️ Excluir", key=f"del_{row['placa']}", use_container_width=True):
                            supabase.table("veiculos").delete().eq("placa", row['placa']).execute()
                            st.cache_data.clear()
                            st.toast("🗑️ Veículo Excluído!")
                            time.sleep(0.5)
                            st.rerun()
