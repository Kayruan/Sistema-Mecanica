import json
import requests
import os
import tempfile
import io
from fpdf import FPDF
from PIL import Image

def processar_imagem_para_pdf(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            img = Image.open(io.BytesIO(response.content))
            if img.mode in ("RGBA", "P", "LA") or img.mode != "RGB":
                img = img.convert("RGB")
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            img.save(tmp_file, format="JPEG")
            tmp_file.close()
            return tmp_file.name
    except Exception as e:
        print(f"Erro ao processar imagem: {e}")
    return None

def formata_moeda(valor):
    """Transforma o número no formato brasileiro (Ex: 12.500,00)"""
    try:
        return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"

def _pagina_dossie_servico(pdf, s, dados_veiculo, placa):
        pdf.add_page()

        # --- CABEÇALHO (Maior) ---
        pdf.set_fill_color(30, 41, 59)
        pdf.rect(10, 10, 190, 25, 'F') # Caixa mais alta
        
        if os.path.exists("logo.png"):
            pdf.image("logo.png", x=13, y=13, w=20) # Logo ligeiramente maior
            x_texto = 35
            w_texto = 165
        else:
            x_texto = 10
            w_texto = 190

        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 17) # Fonte do título maior
        pdf.set_xy(x_texto, 15)
        pdf.cell(w_texto, 8, "ORDEM DE SERVICO - AUTOMECANICA", align='C', ln=True)
        pdf.set_font("Arial", 'I', 11) # Data maior
        pdf.set_xy(x_texto, 24)
        pdf.cell(w_texto, 5, f"Data: {s.get('data_servico', '')}", align='C', ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(14)
        
        # --- DADOS DO VEÍCULO (Maior) ---
        pdf.set_fill_color(241, 245, 249)
        pdf.rect(10, 39, 190, 32, 'F') # Caixa de dados maior
        pdf.set_xy(15, 42)
        pdf.set_font("Arial", 'B', 13) # Título do veículo maior
        pdf.cell(180, 8, f"VEICULO: {dados_veiculo.get('marca', '').upper()} {dados_veiculo.get('modelo', '').upper()} | PLACA: {placa}", ln=True)
        pdf.set_x(15)
        pdf.set_font("Arial", '', 12) # Fonte de dados maior
        pdf.cell(180, 6, f"Proprietario: {dados_veiculo.get('cliente_nome', 'N/A')}   |   Tel: {dados_veiculo.get('cliente_telefone', 'N/A')}", ln=True)
        pdf.set_x(15)
        pdf.cell(180, 6, f"Ano: {dados_veiculo.get('ano', 'N/A')}   |   Chassi: {dados_veiculo.get('chassi', 'N/A')}", ln=True)
        if s.get('orcamento_id'):
            pdf.set_x(15)
            pdf.cell(180, 6, f"Orcamento de origem: No {s.get('orcamento_id')}", ln=True)
        pdf.set_y(78)
        
        # --- DESCRIÇÃO ---
        pdf.set_font("Arial", 'B', 13)
        pdf.cell(0, 8, "MAO DE OBRA RELATADA:", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(0, 6, str(s.get('descricao_servico', '')))
        pdf.ln(6)
        
        # --- PEÇAS ---
        pecas_str = str(s.get('pecas_usadas', '')).strip()
        if pecas_str.startswith('['):
            pdf.set_font("Arial", 'B', 13)
            pdf.cell(0, 8, "PECAS E MATERIAIS UTILIZADOS:", ln=True)
            pdf.set_fill_color(226, 232, 240)
            pdf.set_font("Arial", 'B', 11) # Cabeçalho da tabela maior
            pdf.cell(95, 8, "  Descricao", border=1, fill=True)
            pdf.cell(20, 8, "Qtd", border=1, align='C', fill=True)
            pdf.cell(37, 8, "V. Unit (R$)", border=1, align='R', fill=True)
            pdf.cell(38, 8, "Subtotal (R$)", border=1, align='R', fill=True)
            pdf.ln()
            
            pdf.set_font("Arial", '', 11) # Texto da tabela maior
            try:
                lista_pecas = json.loads(pecas_str)
                for peca in lista_pecas:
                    desc = str(peca.get('Peça/Descrição', ''))
                    if desc:
                        pdf.cell(95, 8, f"  {desc[:45]}", border=1)
                        pdf.cell(20, 8, str(peca.get('Quantidade', '1')), border=1, align='C')
                        
                        # Usa a formatação visual correta
                        v_unit = formata_moeda(peca.get('Valor Unitário (R$)', 0))
                        subt = formata_moeda(peca.get('Subtotal', 0))
                        
                        pdf.cell(37, 8, f"{v_unit} ", border=1, align='R')
                        pdf.cell(38, 8, f"{subt} ", border=1, align='R')
                        pdf.ln()
            except:
                pass
        else:
            pdf.set_font("Arial", 'B', 13)
            pdf.cell(0, 8, "PECAS:", ln=True)
            pdf.set_font("Arial", '', 12)
            pdf.multi_cell(0, 6, pecas_str)

        pdf.ln(6)

        # --- SERVIÇOS EXECUTADOS ---
        servicos_str = str(s.get('servicos_executados', '') or '').strip()
        if servicos_str.startswith('['):
            try:
                lista_servicos = json.loads(servicos_str)
            except Exception:
                lista_servicos = []
            if lista_servicos:
                pdf.set_font("Arial", 'B', 13)
                pdf.cell(0, 8, "SERVICOS EXECUTADOS / MAO DE OBRA:", ln=True)
                pdf.set_fill_color(226, 232, 240)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(152, 8, "  Descricao do Servico", border=1, fill=True)
                pdf.cell(38, 8, "Valor (R$)", border=1, align='R', fill=True)
                pdf.ln()
                pdf.set_font("Arial", '', 11)
                for serv in lista_servicos:
                    desc = str(serv.get('Serviço', ''))
                    if desc:
                        pdf.cell(152, 8, f"  {desc[:75]}", border=1)
                        pdf.cell(38, 8, f"{formata_moeda(serv.get('Valor (R$)', 0))} ", border=1, align='R')
                        pdf.ln()
                pdf.ln(6)

        # --- RESUMO FINANCEIRO ---
        v_pecas = formata_moeda(s.get('valor_pecas', 0))
        v_mao = formata_moeda(s.get('valor_mao_de_obra', 0))
        v_tot = formata_moeda(s.get('valor_total', 0))
        
        pdf.set_font("Arial", '', 12)
        pdf.cell(150, 7, "Subtotal Pecas: ", align='R')
        pdf.cell(40, 7, f"R$ {v_pecas}", align='R', ln=True)
        pdf.cell(150, 7, "Subtotal Mao de Obra: ", align='R')
        pdf.cell(40, 7, f"R$ {v_mao}", align='R', ln=True)
        
        pdf.set_font("Arial", 'B', 14) # Total em destaque ainda maior
        pdf.set_text_color(255, 255, 255)
        pdf.set_fill_color(22, 101, 52)
        pdf.cell(150, 10, " TOTAL DO SERVICO: ", align='R', fill=True)
        pdf.cell(40, 10, f"R$ {v_tot} ", align='R', ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        
        # --- FOTOS PADRONIZADAS ---
        urls_fotos = s.get('urls_fotos', '')
        if urls_fotos:
            urls = [u.strip() for u in urls_fotos.split(',') if u.strip()]
            if urls:
                pdf.ln(8)
                pdf.set_font("Arial", 'B', 13)
                pdf.cell(0, 8, "REGISTRO FOTOGRAFICO:", ln=True)
                
                x_start = 10
                y_start = pdf.get_y()
                
                for i, url in enumerate(urls):
                    if i > 0 and i % 2 == 0:
                        y_start += 65 
                        x_start = 10
                        
                    if y_start + 65 > 270: 
                        pdf.add_page()
                        y_start = 20
                        x_start = 10
                    
                    caminho_temp = processar_imagem_para_pdf(url)
                    if caminho_temp:
                        pdf.image(caminho_temp, x=x_start, y=y_start, w=90, h=60)
                        os.remove(caminho_temp)

                    x_start += 95

                y_start += 65
                if y_start > 270:
                    pdf.add_page()
                    y_start = 20
                pdf.set_y(y_start)

        # --- ASSINATURA DO CLIENTE ---
        assinatura_url = s.get('assinatura_url')
        if assinatura_url:
            caminho_assin = processar_imagem_para_pdf(assinatura_url)
            if caminho_assin:
                pdf.ln(6)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 6, "Assinatura do Cliente:", ln=True)
                pdf.image(caminho_assin, x=15, w=60)
                os.remove(caminho_assin)


def gerar_relatorio_servico(placa, dados_veiculo, orcamentos, servicos):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for s in servicos:
        _pagina_dossie_servico(pdf, s, dados_veiculo, placa)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name


def gerar_dossies_servicos_lote(lista_itens):
    """Gera um único PDF com 1 dossiê completo (com fotos e assinatura) por item.
    lista_itens: lista de dicts com chaves 'servico', 'veiculo' e opcionalmente 'cliente'."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for item in lista_itens:
        s = item['servico']
        veic = dict(item.get('veiculo') or {})
        cli = item.get('cliente') or {}
        if cli:
            veic['cliente_nome'] = cli.get('nome') or veic.get('cliente_nome')
            veic['cliente_telefone'] = cli.get('telefone') or veic.get('cliente_telefone')
        placa = s.get('placa_veiculo') or veic.get('placa', '')
        _pagina_dossie_servico(pdf, s, veic, placa)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name


def gerar_relatorio_orcamento(lista_orcamentos):
    """Gera um PDF completo (1 pagina por orcamento) com dados do cliente, do veiculo,
    pecas e servicos orcados. lista_orcamentos: lista de dicts com chaves
    'orcamento', 'veiculo' e 'cliente'."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    cores_status = {
        "Aprovado": (22, 101, 52),
        "Pendente": (180, 83, 9),
        "Em Execução": (30, 64, 175),
        "Finalizado": (22, 101, 52),
        "Cancelado": (127, 29, 29),
    }

    for item in lista_orcamentos:
        orc = item.get("orcamento", {})
        veic = item.get("veiculo", {}) or {}
        cli = item.get("cliente", {}) or {}

        pdf.add_page()

        # --- CABEÇALHO ---
        pdf.set_fill_color(30, 41, 59)
        pdf.rect(10, 10, 190, 25, 'F')

        if os.path.exists("logo.png"):
            pdf.image("logo.png", x=13, y=13, w=20)
            x_texto = 35
            w_texto = 165
        else:
            x_texto = 10
            w_texto = 190

        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 17)
        pdf.set_xy(x_texto, 15)
        pdf.cell(w_texto, 8, f"ORCAMENTO No {orc.get('id', '')}", align='C', ln=True)
        pdf.set_font("Arial", 'I', 11)
        pdf.set_xy(x_texto, 24)
        pdf.cell(w_texto, 5, f"Data: {orc.get('data', '')}", align='C', ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(14)

        # --- STATUS ---
        status = orc.get('status', 'Pendente')
        cor_status = cores_status.get(status, (71, 85, 105))
        pdf.set_font("Arial", 'B', 11)
        pdf.set_fill_color(*cor_status)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, f" STATUS: {status.upper()} ", align='C', fill=True, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        # --- DADOS DO CLIENTE ---
        pdf.set_fill_color(241, 245, 249)
        pdf.rect(10, pdf.get_y(), 190, 24, 'F')
        y_cli = pdf.get_y()
        pdf.set_xy(15, y_cli + 3)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(180, 6, f"CLIENTE: {cli.get('nome', 'N/A')}", ln=True)
        pdf.set_x(15)
        pdf.set_font("Arial", '', 11)
        pdf.cell(180, 6, f"Tel: {cli.get('telefone', 'N/A')}   |   Email: {cli.get('email') or 'N/A'}", ln=True)
        pdf.set_x(15)
        pdf.cell(180, 6, f"CPF/CNPJ: {cli.get('cpf_cnpj') or 'N/A'}   |   Endereco: {cli.get('endereco') or 'N/A'}", ln=True)
        pdf.set_y(y_cli + 27)

        # --- DADOS DO VEÍCULO ---
        pdf.set_fill_color(226, 232, 240)
        pdf.rect(10, pdf.get_y(), 190, 16, 'F')
        y_veic = pdf.get_y()
        pdf.set_xy(15, y_veic + 3)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(180, 6, f"VEICULO: {str(veic.get('marca', '')).upper()} {str(veic.get('modelo', '')).upper()} ({veic.get('ano', 'N/A')})", ln=True)
        pdf.set_x(15)
        pdf.set_font("Arial", '', 11)
        pdf.cell(180, 6, f"Placa: {veic.get('placa', 'N/A')}   |   Chassi: {veic.get('chassi') or 'Nao informado'}", ln=True)
        pdf.set_y(y_veic + 19)
        pdf.ln(3)

        # --- DESCRIÇÃO DO PROBLEMA ---
        pdf.set_font("Arial", 'B', 13)
        pdf.cell(0, 8, "PROBLEMA RELATADO:", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(0, 6, str(orc.get('descricao_problema', '') or 'Nao informado'))
        pdf.ln(4)

        # --- PEÇAS ---
        pecas_str = str(orc.get('pecas_necessarias', '') or '').strip()
        if pecas_str.startswith('['):
            try:
                lista_pecas = json.loads(pecas_str)
            except Exception:
                lista_pecas = []
            if lista_pecas:
                pdf.set_font("Arial", 'B', 13)
                pdf.cell(0, 8, "PECAS NECESSARIAS:", ln=True)
                pdf.set_fill_color(226, 232, 240)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(95, 8, "  Descricao", border=1, fill=True)
                pdf.cell(20, 8, "Qtd", border=1, align='C', fill=True)
                pdf.cell(37, 8, "V. Unit (R$)", border=1, align='R', fill=True)
                pdf.cell(38, 8, "Subtotal (R$)", border=1, align='R', fill=True)
                pdf.ln()
                pdf.set_font("Arial", '', 11)
                for peca in lista_pecas:
                    desc = str(peca.get('Peça/Descrição', ''))
                    if desc:
                        pdf.cell(95, 8, f"  {desc[:45]}", border=1)
                        pdf.cell(20, 8, str(peca.get('Quantidade', '1')), border=1, align='C')
                        pdf.cell(37, 8, f"{formata_moeda(peca.get('Valor Unitário (R$)', 0))} ", border=1, align='R')
                        pdf.cell(38, 8, f"{formata_moeda(peca.get('Subtotal', 0))} ", border=1, align='R')
                        pdf.ln()
                pdf.ln(4)

        # --- SERVIÇOS / MÃO DE OBRA ---
        servicos_str = str(orc.get('servicos_orcados', '') or '').strip()
        if servicos_str.startswith('['):
            try:
                lista_servicos = json.loads(servicos_str)
            except Exception:
                lista_servicos = []
            if lista_servicos:
                pdf.set_font("Arial", 'B', 13)
                pdf.cell(0, 8, "SERVICOS / MAO DE OBRA:", ln=True)
                pdf.set_fill_color(226, 232, 240)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(152, 8, "  Descricao do Servico", border=1, fill=True)
                pdf.cell(38, 8, "Valor (R$)", border=1, align='R', fill=True)
                pdf.ln()
                pdf.set_font("Arial", '', 11)
                for serv in lista_servicos:
                    desc = str(serv.get('Serviço', ''))
                    if desc:
                        pdf.cell(152, 8, f"  {desc[:75]}", border=1)
                        pdf.cell(38, 8, f"{formata_moeda(serv.get('Valor (R$)', 0))} ", border=1, align='R')
                        pdf.ln()
                pdf.ln(4)

        # --- RESUMO FINANCEIRO ---
        v_pecas = formata_moeda(orc.get('valor_pecas', 0))
        v_mao = formata_moeda(orc.get('valor_mao_de_obra', 0))
        v_tot = formata_moeda(orc.get('valor_total', 0))

        pdf.set_font("Arial", '', 12)
        pdf.cell(150, 7, "Subtotal Pecas: ", align='R')
        pdf.cell(40, 7, f"R$ {v_pecas}", align='R', ln=True)
        pdf.cell(150, 7, "Subtotal Servicos/Mao de Obra: ", align='R')
        pdf.cell(40, 7, f"R$ {v_mao}", align='R', ln=True)

        pdf.set_font("Arial", 'B', 14)
        pdf.set_text_color(255, 255, 255)
        pdf.set_fill_color(22, 101, 52)
        pdf.cell(150, 10, " VALOR TOTAL DO ORCAMENTO: ", align='R', fill=True)
        pdf.cell(40, 10, f"R$ {v_tot} ", align='R', ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)

        pdf.ln(6)
        pdf.set_font("Arial", 'I', 9)
        pdf.multi_cell(0, 5, "Orcamento sujeito a alteracao apos diagnostico tecnico detalhado. Validade: 15 dias a partir da data de emissao.")

        assinatura_url = orc.get('assinatura_url')
        if assinatura_url:
            caminho_assin = processar_imagem_para_pdf(assinatura_url)
            if caminho_assin:
                pdf.ln(4)
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 6, "Assinatura do Cliente:", ln=True)
                pdf.image(caminho_assin, x=15, w=60)
                os.remove(caminho_assin)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name


def gerar_relatorio_macro(df_dados, cliente_filtro, placa_filtro, periodo_str, total_valor, titulo_personalizado="RELATORIO MACRO DE SERVICOS"):
    pdf = FPDF(orientation='L') 
    pdf.add_page()
    
    # --- CABEÇALHO DO MACRO COM LOGO ---
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(10, 10, 277, 28, 'F') # Caixa levemente maior para caber os filtros
    
    if os.path.exists("logo.png"):
        pdf.image("logo.png", x=13, y=13, w=20)
        x_texto = 35
        w_texto = 252
    else:
        x_texto = 10
        w_texto = 277

    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 16)
    pdf.set_xy(x_texto, 12)
    pdf.cell(w_texto, 7, titulo_personalizado, align='C', ln=True)
    
    # Exibição clara dos parâmetros do relatório
    pdf.set_font("Arial", 'I', 9)
    pdf.set_xy(x_texto, 20)
    info_filtros = f"Cliente: {cliente_filtro}   |   Placa: {placa_filtro}   |   Periodo: {periodo_str}"
    pdf.cell(w_texto, 5, info_filtros, align='C', ln=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(15)
    
    # Cabeçalho da Tabela
    pdf.set_fill_color(226, 232, 240)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(15, 10, "Nº", border=1, fill=True, align='C')
    pdf.cell(25, 10, "Data", border=1, fill=True, align='C')
    pdf.cell(30, 10, "Placa", border=1, fill=True, align='C')
    pdf.cell(92, 10, "Descricao Resumida", border=1, fill=True)
    pdf.cell(38, 10, "Pecas (R$)", border=1, fill=True, align='R')
    pdf.cell(38, 10, "M. Obra (R$)", border=1, fill=True, align='R')
    pdf.cell(39, 10, "Total (R$)", border=1, fill=True, align='R')
    pdf.ln()

    # Linhas
    pdf.set_font("Arial", '', 11)
    for idx, row in df_dados.iterrows():
        pdf.cell(15, 9, str(row.get('id', '')), border=1, align='C')
        pdf.cell(25, 9, str(row.get('data_servico', row.get('data', ''))), border=1, align='C')
        pdf.cell(30, 9, str(row['placa_veiculo']), border=1, align='C')
        desc = str(row.get('descricao_servico', row.get('descricao_problema', ''))).replace('\n', ' ')
        pdf.cell(92, 9, f" {desc[:50]}", border=1)

        pdf.cell(38, 9, f"{formata_moeda(row.get('valor_pecas', 0))} ", border=1, align='R')
        pdf.cell(38, 9, f"{formata_moeda(row.get('valor_mao_de_obra', row['valor_total']))} ", border=1, align='R')
        pdf.cell(39, 9, f"{formata_moeda(row['valor_total'])} ", border=1, align='R')
        pdf.ln()

    pdf.ln(8)
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(238, 10, "TOTAL DOS SELECIONADOS: ", align='R')
    pdf.set_text_color(22, 101, 52)
    pdf.cell(39, 10, f"R$ {formata_moeda(total_valor)}", align='R', ln=True)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name