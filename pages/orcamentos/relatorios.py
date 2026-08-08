import streamlit as st
from database import supabase
from utils.dados import buscar_veiculos, buscar_clientes, buscar_orcamentos, buscar_catalogo_servicos
from utils.gerador_pdf import gerar_relatorio_macro
import pandas as pd
import json

st.set_page_config(layout="wide", page_title="Relatórios de Orçamentos | Sanini & Aimi")
st.title("📊 Relatórios Consolidados de Orçamentos")
st.write("Filtre os orçamentos, selecione os desejados e exporte com formatação executiva.")

df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes()
df_orcamentos = buscar_orcamentos()
df_catalogo = buscar_catalogo_servicos()
lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []


def _tipos_servico_do_orcamento(row):
    val = row.get('servicos_orcados', '')
    if val and str(val).startswith('['):
        try:
            return [s.get('Serviço', '') for s in json.loads(val)]
        except Exception:
            return []
    return []


c_m1, c_m2, c_m3, c_m4 = st.columns(4)
with c_m1: f_placa_m = st.selectbox("Filtrar Placa", ["Todas"] + lista_placas, key="fm_orc_p")
with c_m2: f_cli_m = st.selectbox("Filtrar Cliente", ["Todos"] + df_clientes['nome'].tolist() if not df_clientes.empty else ["Todos"], key="fm_orc_c")
with c_m3: f_data_m = st.date_input("Período", [], key="fm_orc_d")
with c_m4:
    tipos_servico_m = ["Todos"] + df_catalogo['nome'].tolist() if not df_catalogo.empty else ["Todos"]
    f_tipo_servico_m = st.selectbox("Tipo de Serviço", tipos_servico_m, key="fm_orc_tipo_serv")

df_macro_orc = df_orcamentos.copy()
if not df_macro_orc.empty:
    if f_placa_m != "Todas": df_macro_orc = df_macro_orc[df_macro_orc['placa_veiculo'] == f_placa_m]
    if f_cli_m != "Todos":
        id_cli = df_clientes[df_clientes['nome'] == f_cli_m]['id'].values[0]
        placas_cli = df_veiculos[df_veiculos['cliente_id'] == id_cli]['placa'].tolist()
        df_macro_orc = df_macro_orc[df_macro_orc['placa_veiculo'].isin(placas_cli)]
    if len(f_data_m) == 2:
        df_macro_orc['data'] = pd.to_datetime(df_macro_orc['data']).dt.date
        df_macro_orc = df_macro_orc[(df_macro_orc['data'] >= f_data_m[0]) & (df_macro_orc['data'] <= f_data_m[1])]
    if f_tipo_servico_m != "Todos":
        df_macro_orc = df_macro_orc[df_macro_orc.apply(lambda r: f_tipo_servico_m in _tipos_servico_do_orcamento(r), axis=1)]

st.divider()
if df_macro_orc.empty:
    st.info("Nenhum orçamento encontrado para os filtros.")
else:
    c_b1, c_b2, _ = st.columns([2, 2, 6])
    if c_b1.button("☑️ Selecionar Todos", use_container_width=True, key="btn_all_orc"):
        for i in df_macro_orc['id']: st.session_state[f"chk_orc_{i}"] = True
        st.rerun()
    if c_b2.button("☐ Limpar Seleção", use_container_width=True, key="btn_none_orc"):
        for i in df_macro_orc['id']: st.session_state[f"chk_orc_{i}"] = False
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    ids_sel_orc = []
    for _, row in df_macro_orc.iterrows():
        aid = row['id']
        if f"chk_orc_{aid}" not in st.session_state: st.session_state[f"chk_orc_{aid}"] = True

        with st.container(border=True):
            cc1, cc2, cc3 = st.columns([0.5, 6, 2])
            if cc1.checkbox("", key=f"chk_orc_{aid}"): ids_sel_orc.append(aid)
            with cc2:
                st.markdown(f"**🚗 {row['placa_veiculo']}** | 📅 {row['data']} | **Status:** {row.get('status', 'Pendente')}")
                st.caption(str(row.get('descricao_problema', ''))[:80])
            with cc3:
                v_t = row.get('valor_total', 0)
                st.markdown(f"<h5 style='color:green;'>R$ {float(v_t):,.2f}</h5>", unsafe_allow_html=True)

    df_exp_orc = df_macro_orc[df_macro_orc['id'].isin(ids_sel_orc)]
    if not df_exp_orc.empty:
        st.divider()
        tot_orc = df_exp_orc['valor_total'].sum()
        st.markdown(f"### Total Selecionado: <span style='color:green;'>R$ {tot_orc:,.2f}</span>", unsafe_allow_html=True)
        ex1, ex2 = st.columns(2)

        df_excel = df_exp_orc[['id', 'data', 'placa_veiculo', 'status', 'valor_pecas', 'valor_mao_de_obra', 'valor_total', 'descricao_problema']].copy()
        df_excel.columns = ['Nº', 'Data', 'Placa', 'Status', 'Valor Peças (R$)', 'Mão de Obra (R$)', 'Valor Total (R$)', 'Descrição do Problema']

        csv = df_excel.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        ex1.download_button("📊 Exportar Planilha (Excel)", data=csv, file_name='relatorio_orcamentos.csv', mime='text/csv', use_container_width=True)

        if ex2.button("📄 Emitir Relatório Consolidado (PDF)", use_container_width=True, type="primary"):
            periodo_texto = f"{f_data_m[0]} até {f_data_m[1]}" if len(f_data_m) == 2 else "Todo o Período"
            df_pdf_prep = df_exp_orc.copy()
            df_pdf_prep['data_servico'] = df_pdf_prep['data']
            df_pdf_prep['valor_pecas'] = df_pdf_prep.get('valor_pecas', 0.0)
            df_pdf_prep['valor_mao_de_obra'] = df_pdf_prep.get('valor_mao_de_obra', df_pdf_prep['valor_total'])
            df_pdf_prep['descricao_servico'] = df_pdf_prep['descricao_problema']

            path = gerar_relatorio_macro(
                df_pdf_prep,
                cliente_filtro=f_cli_m,
                placa_filtro=f_placa_m,
                periodo_str=periodo_texto,
                total_valor=tot_orc,
                titulo_personalizado="RELATORIO DE ORCAMENTOS"
            )
            with open(path, "rb") as f:
                st.download_button("📥 Baixar Relatório Consolidado", data=f, file_name="Relatorio_Consolidado_Orcamentos.pdf", mime="application/pdf", use_container_width=True)
