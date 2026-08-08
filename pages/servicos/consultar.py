import streamlit as st
from database import supabase
from utils.dados import buscar_veiculos, buscar_clientes, buscar_servicos, montar_veiculo_e_cliente
from utils.paginacao import paginar
from utils.gerador_pdf import gerar_relatorio_servico
import pandas as pd
import json
import time
import uuid
import re

st.set_page_config(layout="wide", page_title="Ordens de Serviço | Sanini & Aimi")
st.title("📋 Consultar Ordens de Serviço")

df_veiculos = buscar_veiculos()
df_clientes = buscar_clientes()
df_servicos = buscar_servicos()
lista_placas = df_veiculos['placa'].tolist() if not df_veiculos.empty else []


@st.dialog("🛠️ Ficha da Ordem de Serviço", width="large")
def ver_detalhes_servico(row, veic, cli):
    st.markdown(f"## OS Nº {row['id']} &nbsp;|&nbsp; 🚗 {row['placa_veiculo']}")
    st.caption(f"Data: {row.get('data_servico', '')}")
    if row.get('orcamento_id'):
        st.caption(f"🔗 Originada do Orçamento Nº {int(row['orcamento_id'])}")
    st.divider()

    col_c, col_v = st.columns(2)
    with col_c:
        st.markdown("**👤 Cliente**")
        st.write(cli.get('nome', 'N/A'))
        st.caption(f"Tel: {cli.get('telefone', 'N/A')} | E-mail: {cli.get('email') or 'N/A'}")
    with col_v:
        st.markdown("**🚗 Veículo**")
        st.write(f"{veic.get('marca', '')} {veic.get('modelo', '')} ({veic.get('ano', 'N/A')})")
        st.caption(f"Chassi: {veic.get('chassi') or 'N/A'}")

    st.divider()
    st.markdown("**Mão de Obra Relatada**")
    st.write(row.get('descricao_servico') or "Não informado")

    pecas_val = row.get('pecas_usadas', '')
    if pecas_val and str(pecas_val).startswith('['):
        try:
            lista_p = json.loads(pecas_val)
            if lista_p:
                st.markdown("**🔧 Peças**")
                st.dataframe(pd.DataFrame(lista_p), use_container_width=True, hide_index=True)
        except Exception:
            pass

    servicos_val = row.get('servicos_executados', '')
    if servicos_val and str(servicos_val).startswith('['):
        try:
            lista_s = json.loads(servicos_val)
            if lista_s:
                st.markdown("**🛠️ Serviços / Mão de Obra**")
                st.dataframe(pd.DataFrame(lista_s), use_container_width=True, hide_index=True)
        except Exception:
            pass

    st.divider()
    st.markdown(f"### Valor Total: <span style='color:green;'>R$ {float(row.get('valor_total', 0)):,.2f}</span>", unsafe_allow_html=True)

    fotos_val = [u for u in str(row.get('urls_fotos', '') or '').split(',') if u.strip()]
    if fotos_val:
        st.divider()
        st.markdown("**📸 Registro Fotográfico**")
        cols_fotos = st.columns(min(4, len(fotos_val)))
        for i, url in enumerate(fotos_val):
            cols_fotos[i % len(cols_fotos)].image(url, use_container_width=True)

    if row.get('assinatura_url'):
        st.divider()
        st.markdown("**🖊️ Assinatura do Cliente**")
        st.image(row['assinatura_url'], width=250)


col_f1, col_f2, col_f3 = st.columns(3)
with col_f1: f_placa_serv = st.selectbox("Filtrar por Placa", ["Todas"] + lista_placas, key="f1_placa")
with col_f2:
    cli_filtro = ["Todos"] + df_clientes['nome'].tolist() if not df_clientes.empty else ["Todos"]
    f_cli_serv = st.selectbox("Filtrar por Cliente", cli_filtro, key="f1_cli")
with col_f3: f_data_serv = st.date_input("Período (Início e Fim)", [], key="f1_data")

busca_os = st.text_input("🔍 Buscar por placa, cliente ou descrição do serviço...")

df_filtrado_s = df_servicos.copy()
if not df_filtrado_s.empty:
    if f_placa_serv != "Todas": df_filtrado_s = df_filtrado_s[df_filtrado_s['placa_veiculo'] == f_placa_serv]
    if f_cli_serv != "Todos":
        id_cli = df_clientes[df_clientes['nome'] == f_cli_serv]['id'].values[0]
        placas_cli = df_veiculos[df_veiculos['cliente_id'] == id_cli]['placa'].tolist()
        df_filtrado_s = df_filtrado_s[df_filtrado_s['placa_veiculo'].isin(placas_cli)]
    if len(f_data_serv) == 2:
        df_filtrado_s['data_servico'] = pd.to_datetime(df_filtrado_s['data_servico']).dt.date
        df_filtrado_s = df_filtrado_s[(df_filtrado_s['data_servico'] >= f_data_serv[0]) & (df_filtrado_s['data_servico'] <= f_data_serv[1])]
    if busca_os:
        termo = busca_os.lower()

        def _bate_busca_os(row):
            v_row = df_veiculos[df_veiculos['placa'] == row['placa_veiculo']]
            cliente_txt = ""
            if not v_row.empty and not df_clientes.empty:
                c_id = v_row.iloc[0].get('cliente_id')
                c_row = df_clientes[df_clientes['id'] == c_id]
                if not c_row.empty:
                    cliente_txt = str(c_row.iloc[0]['nome'])
            campo = f"{row['placa_veiculo']} {cliente_txt} {row.get('descricao_servico', '')}".lower()
            return termo in campo

        df_filtrado_s = df_filtrado_s[df_filtrado_s.apply(_bate_busca_os, axis=1)]

st.divider()
if df_filtrado_s.empty:
    st.info("Nenhuma ordem de serviço registrada.")
else:
    st.markdown(
        f"**{len(df_filtrado_s)} ordem(ns) de serviço filtrada(s) — Valor total: "
        f"R$ {df_filtrado_s['valor_total'].sum():,.2f}**"
    )
    st.divider()

    df_pagina = paginar(df_filtrado_s, "os_consultar", por_pagina=10)

    for _, row in df_pagina.iterrows():
        placa = row['placa_veiculo']
        n_txt, cli_tel, cli_email = "Sem Nome", "", ""
        veic_row = df_veiculos[df_veiculos['placa'] == placa]
        if not veic_row.empty:
            c_id = veic_row.iloc[0].get('cliente_id')
            if pd.notna(c_id):
                cli_row = df_clientes[df_clientes['id'] == c_id]
                if not cli_row.empty:
                    n_txt = cli_row.iloc[0]['nome']
                    cli_tel = str(cli_row.iloc[0].get('telefone', ''))
                    cli_email = str(cli_row.iloc[0].get('email', ''))

        with st.container(border=True):
            c_inf, c_val, c_btn = st.columns([5, 2, 2])
            with c_inf:
                orc_ref = row.get('orcamento_id')
                vinculo_txt = f" &nbsp;|&nbsp; 🔗 Orçamento Nº {int(orc_ref)}" if pd.notna(orc_ref) else ""
                st.markdown(f"**OS Nº {row['id']} — 🚗 {row['placa_veiculo']}** | 👤 {n_txt} | 📅 {row['data_servico']}{vinculo_txt}")
                st.write(f"*{str(row['descricao_servico'])[:100]}...*")
            with c_val:
                st.markdown("**Total:**")
                st.markdown(f"<h4 style='color: green;'>R$ {row['valor_total']:,.2f}</h4>", unsafe_allow_html=True)
            with c_btn:
                if st.button("🔍 Ver Detalhes", key=f"ver_os_{row['id']}", use_container_width=True):
                    veic_det, cli_det = montar_veiculo_e_cliente(df_veiculos, df_clientes, placa)
                    ver_detalhes_servico(row.to_dict(), veic_det, cli_det)
                with st.popover("⚙️ Opções", use_container_width=True):
                    if st.button("📄 Emitir Dossiê Técnico (PDF)", key=f"pdf_{row['id']}", use_container_width=True):
                        veic = df_veiculos[df_veiculos['placa'] == row['placa_veiculo']].iloc[0].to_dict()
                        veic['cliente_nome'] = n_txt
                        veic['cliente_telefone'] = cli_tel
                        orcs = supabase.table("orcamentos").select("*").eq("placa_veiculo", row['placa_veiculo']).execute().data
                        caminho_pdf = gerar_relatorio_servico(row['placa_veiculo'], veic, orcs, [row.to_dict()])
                        with open(caminho_pdf, "rb") as pdf_file:
                            st.download_button("📥 Baixar Arquivo", data=pdf_file, file_name=f"OS_{row['placa_veiculo']}.pdf", mime="application/pdf", use_container_width=True)
                    if cli_tel:
                        clean_tel = "".join(filter(str.isdigit, cli_tel))
                        st.link_button("💬 WhatsApp", f"https://wa.me/{clean_tel}", use_container_width=True)
                    if cli_email:
                        st.link_button("📧 E-mail", f"mailto:{cli_email}", use_container_width=True)

                    st.divider()
                    st.markdown("**📸 Fotos do Serviço**")
                    fotos_atuais = [u for u in str(row.get('urls_fotos', '') or '').split(',') if u.strip()]
                    if fotos_atuais:
                        for idx_foto, url_foto in enumerate(fotos_atuais):
                            fc1, fc2 = st.columns([4, 1])
                            fc1.image(url_foto, width=120)
                            if fc2.button("🗑️", key=f"delfoto_{row['id']}_{idx_foto}"):
                                restantes = [u for j, u in enumerate(fotos_atuais) if j != idx_foto]
                                supabase.table("servicos_realizados").update({"urls_fotos": ",".join(restantes)}).eq("id", row['id']).execute()
                                st.cache_data.clear()
                                st.rerun()
                    else:
                        st.caption("Nenhuma foto registrada ainda.")
                    novas_fotos = st.file_uploader("Adicionar fotos", accept_multiple_files=True, key=f"addfoto_{row['id']}")
                    if st.button("📤 Anexar Fotos ao Registro", key=f"btnfoto_{row['id']}", use_container_width=True):
                        if novas_fotos:
                            urls_novas = []
                            fotos_com_falha = []
                            for foto in novas_fotos:
                                try:
                                    nome_seguro = re.sub(r'[^A-Za-z0-9._-]', '_', foto.name)
                                    nome_arquivo = f"{row['placa_veiculo']}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}_{nome_seguro}"
                                    supabase.storage.from_("fotos_mecanica").upload(nome_arquivo, foto.getvalue())
                                    urls_novas.append(supabase.storage.from_("fotos_mecanica").get_public_url(nome_arquivo))
                                except Exception as e:
                                    fotos_com_falha.append(f"{foto.name} ({e})")
                            if fotos_com_falha:
                                st.warning("⚠️ Não foi possível enviar: " + "; ".join(fotos_com_falha))
                            supabase.table("servicos_realizados").update({"urls_fotos": ",".join(fotos_atuais + urls_novas)}).eq("id", row['id']).execute()
                            st.cache_data.clear()
                            st.toast("✅ Fotos adicionadas!")
                            time.sleep(0.5)
                            st.rerun()

                    st.divider()
                    st.markdown("**🖊️ Assinatura do Cliente**")
                    if row.get('assinatura_url'):
                        st.image(row['assinatura_url'], width=200)
                        st.caption("Assinatura registrada.")
                        nova_assinatura = st.file_uploader("Substituir assinatura", type=['png', 'jpg', 'jpeg'], key=f"assin_{row['id']}")
                    else:
                        st.caption("Nenhuma assinatura anexada ainda.")
                        nova_assinatura = st.file_uploader("Anexar assinatura (foto/imagem)", type=['png', 'jpg', 'jpeg'], key=f"assin_{row['id']}")
                    if st.button("💾 Salvar Assinatura", key=f"btnassin_{row['id']}", use_container_width=True):
                        if nova_assinatura:
                            ext = nova_assinatura.name.split('.')[-1]
                            nome_arq = f"assinatura_servico_{row['id']}_{time.time()}.{ext}"
                            supabase.storage.from_("fotos_mecanica").upload(nome_arq, nova_assinatura.getvalue())
                            url_assin = supabase.storage.from_("fotos_mecanica").get_public_url(nome_arq)
                            supabase.table("servicos_realizados").update({"assinatura_url": url_assin}).eq("id", row['id']).execute()
                            st.cache_data.clear()
                            st.toast("✅ Assinatura registrada!")
                            time.sleep(0.5)
                            st.rerun()

                    st.divider()
                    if st.button("🗑️ Excluir", key=f"dels_{row['id']}", use_container_width=True):
                        supabase.table("servicos_realizados").delete().eq("id", row['id']).execute()
                        st.cache_data.clear()
                        st.toast("🗑️ Excluído!")
                        time.sleep(0.5)
                        st.rerun()
