import json
import requests
import os
import tempfile
from fpdf import FPDF

def gerar_relatorio_servico(placa, dados_veiculo, orcamentos, servicos):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    for s in servicos:
        pdf.add_page()
        
        # --- CABEÇALHO CORPORATIVO MODONO ---
        # Caixa de fundo escuro para o título principal
        pdf.set_fill_color(30, 41, 59) # Azul escuro profissional
        pdf.rect(10, 10, 190, 20, 'F')
        
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 15)
        pdf.set_xy(10, 13)
        pdf.cell(190, 8, "ORDEM DE SERVICO - AUTOMECANICA", align='C', ln=True)
        
        pdf.set_font("Arial", 'I', 9)
        pdf.set_xy(10, 21)
        pdf.cell(190, 5, f"Data de Emissao: {s.get('data_servico', '')}", align='C', ln=True)
        
        pdf.set_text_color(0, 0, 0) # Reseta a cor para preto
        pdf.ln(12)
        
        # --- BLOCO DE DADOS DO VEÍCULO (Elegante e Destacado) ---
        pdf.set_fill_color(241, 245, 249) # Fundo cinza claro bem limpo
        pdf.rect(10, 35, 190, 28, 'F')
        
        pdf.set_xy(15, 38)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(180, 6, f"VEICULO: {dados_veiculo.get('marca', '').upper()} {dados_veiculo.get('modelo', '').upper()}", ln=True)
        
        pdf.set_x(15)
        pdf.set_font("Arial", '', 10)
        pdf.cell(180, 5, f"Placa: {placa}   |   Ano: {dados_veiculo.get('ano', 'N/A')}   |   Chassi: {dados_veiculo.get('chassi', 'N/A')}", ln=True)
        
        pdf.set_x(15)
        pdf.cell(180, 5, f"Proprietario: {dados_veiculo.get('cliente_nome', 'N/A')}   |   Tel: {dados_veiculo.get('cliente_telefone', 'N/A')}", ln=True)
        
        pdf.set_y(70)
        
        # --- DESCRIÇÃO ---
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 8, "MAO DE OBRA RELATADA:", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 5, str(s.get('descricao_servico', '')))
        pdf.ln(5)
        
        # --- TABELA DE PEÇAS ---
        pecas_str = str(s.get('pecas_usadas', '')).strip()
        
        if pecas_str.startswith('['):
            pdf.set_font("Arial", 'B', 11)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(0, 8, "PECAS E MATERIAIS UTILIZADOS:", ln=True)
            pdf.set_text_color(0, 0, 0)
            
            pdf.set_fill_color(226, 232, 240)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(95, 7, "  Descricao", border=1, fill=True)
            pdf.cell(20, 7, "Qtd", border=1, align='C', fill=True)
            pdf.cell(37, 7, "V. Unit (R$)", border=1, align='R', fill=True)
            pdf.cell(38, 7, "Subtotal (R$)", border=1, align='R', fill=True)
            pdf.ln()
            
            pdf.set_font("Arial", '', 9)
            try:
                lista_pecas = json.loads(pecas_str)
                for peca in lista_pecas:
                    desc = str(peca.get('Peça/Descrição', ''))
                    if desc:
                        pdf.cell(95, 6, f"  {desc[:45]}", border=1)
                        pdf.cell(20, 6, str(peca.get('Quantidade', '1')), border=1, align='C')
                        pdf.cell(37, 6, f"{float(peca.get('Valor Unitário (R$)', 0)):.2f} ", border=1, align='R')
                        pdf.cell(38, 6, f"{float(peca.get('Subtotal', 0)):.2f} ", border=1, align='R')
                        pdf.ln()
            except Exception:
                pass
        else:
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, "PECAS:", ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 5, pecas_str)
            
        pdf.ln(4)
        
        # --- RESUMO FINANCEIRO ---
        pdf.set_font("Arial", '', 10)
        pdf.cell(155, 6, "Subtotal Pecas: ", align='R')
        pdf.cell(35, 6, f"R$ {float(s.get('valor_pecas', 0)):.2f}", align='R', ln=True)
        pdf.cell(155, 6, "Subtotal Mao de Obra: ", align='R')
        pdf.cell(35, 6, f"R$ {float(s.get('valor_mao_de_obra', 0)):.2f}", align='R', ln=True)
        
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(255, 255, 255)
        pdf.set_fill_color(22, 101, 52) # Verde escuro corporativo
        pdf.cell(155, 8, " TOTAL DO SERVICO: ", align='R', fill=True)
        pdf.cell(35, 8, f"R$ {float(s.get('valor_total', 0)):.2f} ", align='R', ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        
        # --- CORREÇÃO DEFINITIVA DAS FOTOS ---
        urls_fotos = s.get('urls_fotos', '')
        if urls_fotos:
            urls = [u.strip() for u in urls_fotos.split(',') if u.strip()]
            if urls:
                pdf.ln(8)
                pdf.set_font("Arial", 'B', 11)
                pdf.set_text_color(30, 41, 59)
                pdf.cell(0, 8, "REGISTRO FOTOGRAFICO:", ln=True)
                pdf.set_text_color(0, 0, 0)
                
                x_start = 15
                y_start = pdf.get_y()
                
                for i, url in enumerate(urls):
                    if i > 0 and i % 2 == 0:
                        y_start += 65
                        x_start = 15
                        
                    if y_start + 60 > 270:
                        pdf.add_page()
                        y_start = 20
                        x_start = 15
                    
                    caminho_temp = None
                    try:
                        # Garante que a URL pública do Supabase seja acessada corretamente
                        response = requests.get(url, timeout=15)
                        if response.status_code == 200:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                tmp_file.write(response.content)
                                caminho_temp = tmp_file.name
                            
                            pdf.image(caminho_temp, x=x_start, y=y_start, w=85, h=60)
                            x_start += 90
                    except Exception as e:
                        print(f"Erro ao carregar imagem: {e}")
                    finally:
                        if caminho_temp and os.path.exists(caminho_temp):
                            try:
                                os.remove(caminho_temp)
                            except:
                                pass
                        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name