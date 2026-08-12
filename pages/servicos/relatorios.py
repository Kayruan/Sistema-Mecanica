import streamlit as st
from database import supabase
from utils.dados import buscar_veiculos, buscar_clientes, buscar_servicos, buscar_config_empresa, montar_veiculo_e_cliente
from utils.gerador_pdf import gerar_relatorio_macro, gerar_dossies_servicos_lote
from utils.auth import usuario_atual
from urllib.parse import quote
import pandas as pd

st.set_page_config(layout="wide", page_title="Relatórios de OS | Sanini & Aimi")
st.title("Relatórios consolidados de ordens de serviço", anchor=False)
st.write("Filtre as ordens de serviço, selecione as desejadas e exporte com formatação executiva.")

df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes("id, nome, telefone, email")
df_servicos = buscar_servicos()
lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []


def nome_empresa_atual():
    config = buscar_config_empresa()
    return config.get("nome_empresa") or "nossa oficina"


c_m1, c_m2, c_m3 = st.columns(3)
with c_m1: f_placa_m = st.selectbox("Placa", ["Todas"] + lista_placas, key="fm_serv_p")
with c_m2: f_cli_m = st.selectbox("Cliente", ["Todos"] + df_clientes['nome'].tolist() if not df_clientes.empty else ["Todos"], key="fm_serv_c")
with c_m3: f_data_m = st.date_input("Período", [], key="fm_serv_d")

df_macro = df_servicos.copy()
if not df_macro.empty:
    if f_placa_m != "Todas": df_macro = df_macro[df_macro['placa_veiculo'] == f_placa_m]
    if f_cli_m != "Todos":
        id_cli = df_clientes[df_clientes['nome'] == f_cli_m]['id'].values[0]
        placas_cli = df_veiculos[df_veiculos['cliente_id'] == id_cli]['placa'].tolist()
        df_macro = df_macro[df_macro['placa_veiculo'].isin(placas_cli)]
    if len(f_data_m) == 2:
        df_macro['data_servico'] = pd.to_datetime(df_macro['data_servico']).dt.date
        df_macro = df_macro[(df_macro['data_servico'] >= f_data_m[0]) & (df_macro['data_servico'] <= f_data_m[1])]

if df_macro.empty:
    st.info("Nenhum dado encontrado para os filtros.")
else:
    c_b1, c_b2, _ = st.columns([2, 2, 6])
    if c_b1.button("Selecionar todos", width="stretch", key="btn_all_s", icon=":material/select_all:"):
        for i in df_macro['id']: st.session_state[f"chk_s_{i}"] = True
        st.rerun()
    if c_b2.button("Limpar seleção", width="stretch", key="btn_none_s", icon=":material/deselect:"):
        for i in df_macro['id']: st.session_state[f"chk_s_{i}"] = False
        st.rerun()

    ids_sel_s = []
    for _, row in df_macro.iterrows():
        aid = row['id']
        if f"chk_s_{aid}" not in st.session_state: st.session_state[f"chk_s_{aid}"] = True

        with st.container(border=True):
            cc1, cc2, cc3 = st.columns([0.5, 6, 2], vertical_alignment="center")
            if cc1.checkbox("Selecionar", key=f"chk_s_{aid}", label_visibility="collapsed"): ids_sel_s.append(aid)
            with cc2:
                st.markdown(f"**{row['placa_veiculo']}**  ·  {row['data_servico']}")
                st.caption(str(row['descricao_servico'])[:70])
            with cc3:
                st.markdown(f"##### :green[R$ {row['valor_total']:,.2f}]")

    df_exp_s = df_macro[df_macro['id'].isin(ids_sel_s)]
    if not df_exp_s.empty:
        tot_s = df_exp_s['valor_total'].sum()
        st.markdown(f"### Total selecionado: :green[R$ {tot_s:,.2f}]")
        ex1, ex2, ex3 = st.columns(3)

        df_excel_s = df_exp_s[['id', 'data_servico', 'placa_veiculo', 'valor_pecas', 'valor_mao_de_obra', 'valor_total', 'descricao_servico']].copy()
        df_excel_s.columns = ['Nº', 'Data', 'Placa', 'Valor Peças (R$)', 'Mão de Obra (R$)', 'Valor Total (R$)', 'Descrição do Serviço']

        csv = df_excel_s.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        ex1.download_button("Exportar planilha Excel", data=csv, file_name='relatorio_servicos.csv', mime='text/csv', icon=":material/download:")

        if ex2.button("Emitir relatório consolidado (PDF)", type="primary", icon=":material/picture_as_pdf:"):
            periodo_texto = f"{f_data_m[0]} até {f_data_m[1]}" if len(f_data_m) == 2 else "Todo o Período"
            path = gerar_relatorio_macro(
                df_exp_s,
                cliente_filtro=f_cli_m,
                placa_filtro=f_placa_m,
                periodo_str=periodo_texto,
                total_valor=tot_s,
                titulo_personalizado="RELATORIO MACRO DE SERVICOS",
                emitido_por=(usuario_atual() or {}).get("nome"),
            )
            with open(path, "rb") as f:
                st.download_button("Baixar relatório consolidado", data=f, file_name="Relatorio_Consolidado_Servicos.pdf", mime="application/pdf", icon=":material/download:")

        if ex3.button("Emitir dossiê técnico completo (com fotos)", icon=":material/photo_library:"):
            itens_dossie = []
            for _, row_d in df_exp_s.iterrows():
                veic_d, cli_d = montar_veiculo_e_cliente(df_veiculos, df_clientes, row_d['placa_veiculo'])
                itens_dossie.append({"servico": row_d.to_dict(), "veiculo": veic_d, "cliente": cli_d})
            caminho_dossie = gerar_dossies_servicos_lote(itens_dossie, emitido_por=(usuario_atual() or {}).get("nome"))
            with open(caminho_dossie, "rb") as f_dos:
                st.download_button("Baixar dossiê técnico completo", data=f_dos, file_name="Dossies_Tecnicos_Servicos.pdf", mime="application/pdf", icon=":material/download:")

        st.divider()
        st.markdown("**:material/chat: Central de envio (WhatsApp)**")
        st.caption("Um link pronto por cliente, com mensagem já preenchida — basta clicar para abrir o WhatsApp e enviar.")
        nome_empresa_wpp = nome_empresa_atual()
        clientes_unicos = {}
        for _, row_w in df_exp_s.iterrows():
            veic_w, cli_w = montar_veiculo_e_cliente(df_veiculos, df_clientes, row_w['placa_veiculo'])
            if not cli_w:
                continue
            tel_w = "".join(filter(str.isdigit, str(cli_w.get('telefone', '') or '')))
            if not tel_w:
                continue
            info = clientes_unicos.setdefault(cli_w['id'], {"nome": cli_w.get('nome', 'Cliente'), "telefone": tel_w, "placas": set()})
            info["placas"].add(row_w['placa_veiculo'])

        if not clientes_unicos:
            st.info("Nenhum cliente com telefone cadastrado entre os serviços selecionados.")
        else:
            for cid, info in clientes_unicos.items():
                placas_txt = ", ".join(sorted(info["placas"]))
                mensagem = (f"Olá {info['nome']}! Aqui é da {nome_empresa_wpp}. "
                            f"Segue o registro do(s) serviço(s) realizado(s) no seu veículo ({placas_txt}). "
                            f"Qualquer dúvida estamos à disposição!")
                link = f"https://wa.me/{info['telefone']}?text={quote(mensagem)}"
                st.link_button(f"Enviar para {info['nome']} ({placas_txt})", link, icon=":material/send:", width="stretch")
