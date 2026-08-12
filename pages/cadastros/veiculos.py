import streamlit as st
from database import supabase
from utils.dados import buscar_veiculos, buscar_clientes
from utils.auth import registrar_log
import pandas as pd
import re
import time

st.set_page_config(layout="wide", page_title="Veículos | Sanini & Aimi")
st.title("Cadastro de veículos", anchor=False)

msg_sucesso_veic = st.session_state.pop("msg_sucesso_veic", None)
if msg_sucesso_veic:
    st.success(msg_sucesso_veic, icon=":material/check_circle:")


def validar_placa(placa):
    padrao = re.compile(r'^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$')
    return bool(padrao.match(placa))


def validar_chassi(chassi):
    if not chassi: return True  # Chassi opcional
    padrao = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')
    return bool(padrao.match(chassi))


df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes("id, nome, cpf_cnpj")

# Dicionário para facilitar o selectbox de clientes: "João Silva (CPF/CNPJ: ...)" -> id
if not df_clientes.empty:
    opcoes_clientes = {f"{row['nome']} (CPF/CNPJ: {row['cpf_cnpj'] or 'S/N'})": row['id'] for _, row in df_clientes.iterrows()}
else:
    opcoes_clientes = {}

aba1, aba2 = st.tabs(["Consultar veículos", "Cadastrar veículo"])


@st.dialog("Editar veículo", width="large")
def editar_veiculo(row):
    edit_marca = st.text_input("Marca", value=row['marca'], key=f"m_{row['placa']}")
    edit_mod = st.text_input("Modelo", value=row['modelo'], key=f"mod_{row['placa']}")
    edit_ano = st.number_input("Ano", value=row['ano'], step=1, key=f"a_{row['placa']}")

    with st.container(horizontal=True):
        if st.button("Salvar alterações", key=f"upd_{row['placa']}", type="primary", icon=":material/save:"):
            novos_dados = {"marca": edit_marca, "modelo": edit_mod, "ano": edit_ano}
            supabase.table("veiculos").update(novos_dados).eq("placa", row['placa']).execute()
            registrar_log("editou", "veiculo", row['placa'])
            st.cache_data.clear()
            st.session_state["msg_sucesso_veic"] = f"Veículo {row['placa']} atualizado."
            st.rerun()
        if st.button("Excluir veículo", key=f"del_{row['placa']}", icon=":material/delete:"):
            supabase.table("veiculos").delete().eq("placa", row['placa']).execute()
            registrar_log("excluiu", "veiculo", row['placa'])
            st.cache_data.clear()
            st.session_state["msg_sucesso_veic"] = "Veículo excluído."
            st.rerun()


# --- ABA 2: CADASTRAR VEÍCULO ---
with aba2:
    if not opcoes_clientes:
        st.warning("Você precisa cadastrar pelo menos um cliente antes de registrar um veículo.", icon=":material/warning:")
    else:
        with st.container(border=True):
            st.subheader("Ficha do veículo", anchor=False)
            with st.form("form_novo_veiculo", clear_on_submit=True):
                cliente_selecionado = st.selectbox("Selecione o proprietário (cliente) *", list(opcoes_clientes.keys()))

                c1, c2, c3 = st.columns(3)
                with c1:
                    placa = st.text_input("Placa (obrigatório) *", max_chars=7, help="Ex: ABC1234 ou ABC1D23").upper().strip()
                    ano = st.number_input("Ano de fabricação", min_value=1950, max_value=2030, step=1, value=2015)
                with c2:
                    marca = st.text_input("Marca")
                    chassi = st.text_input("Número do chassi", max_chars=17).upper().strip()
                with c3:
                    modelo = st.text_input("Modelo")

                submit = st.form_submit_button("Cadastrar veículo", type="primary", width="stretch", icon=":material/save:")

                if submit and (time.time() - st.session_state.get("veic_ultimo_envio", 0) > 5):
                    st.session_state["veic_ultimo_envio"] = time.time()
                    if not validar_placa(placa):
                        st.error("Placa inválida. Use o formato ABC1234 ou ABC1D23 (sem espaços ou traços).", icon=":material/error:")
                    elif not validar_chassi(chassi):
                        st.error("Chassi inválido. Deve conter exatos 17 caracteres válidos.", icon=":material/error:")
                    else:
                        dados_veiculo = {
                            "placa": placa, "marca": marca, "modelo": modelo,
                            "ano": ano, "chassi": chassi,
                            "cliente_id": opcoes_clientes[cliente_selecionado]
                        }
                        try:
                            supabase.table("veiculos").insert(dados_veiculo).execute()
                            registrar_log("criou", "veiculo", placa)
                            st.cache_data.clear()
                            st.session_state["msg_sucesso_veic"] = f"Veículo {placa} cadastrado com sucesso."
                            st.rerun()
                        except Exception:
                            st.error("Erro ao salvar: placa já existente ou falha no banco.", icon=":material/error:")

# --- ABA 1: GESTÃO DE VEÍCULOS ---
with aba1:
    busca_v = st.text_input("Buscar por placa, marca ou modelo", icon=":material/search:")

    if df_veiculos.empty:
        st.info("Nenhum veículo cadastrado ainda.")
    else:
        df_f = df_veiculos.copy()
        if busca_v:
            busca_v = busca_v.lower()
            mask = df_f.apply(lambda row: row.astype(str).str.lower().str.contains(busca_v).any(), axis=1)
            df_f = df_f[mask]

        for index, row in df_f.iterrows():
            with st.container(border=True, key=f"card_veic_{row['placa']}"):
                col_info, col_acoes = st.columns([5, 1], vertical_alignment="center")

                dono_nome = "Cliente não vinculado"
                if pd.notna(row.get('cliente_id')):
                    dono = df_clientes[df_clientes['id'] == row['cliente_id']]
                    if not dono.empty:
                        dono_nome = dono.iloc[0]['nome']
                elif row.get('cliente_nome'):
                    dono_nome = f"{row['cliente_nome']} (cadastro antigo)"

                with col_info:
                    st.markdown(f"#### {row['marca']} {row['modelo']} ({row['ano']})")
                    st.markdown(f"Placa: `{row['placa']}`  ·  Chassi: `{row['chassi'] or 'Não informado'}`")
                    st.write(f":material/person: {dono_nome}")

                with col_acoes:
                    if st.button("Histórico", key=f"hist_{row['placa']}", icon=":material/history:", width="stretch"):
                        st.session_state["historico_placa_selecionada"] = row['placa']
                        st.switch_page("pages/cadastros/historico.py")
                    if st.button("Gerenciar", key=f"manage_{row['placa']}", icon=":material/settings:", width="stretch"):
                        editar_veiculo(row)
