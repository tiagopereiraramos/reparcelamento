
#!/usr/bin/env python3
"""
Criador de Planilhas de Exemplo para Teste RPA Sienge
Gera planilhas Excel simulando todos os cenários do PDD

Desenvolvido em Português Brasileiro
"""

import pandas as pd
from datetime import datetime, date, timedelta
import os
from pathlib import Path

def criar_planilha_cliente_adimplente():
    """
    Cenário 1: Cliente adimplente - PODE REPARCELAR
    - Sem parcelas CT vencidas
    - Parcelas normais em dia ou com poucos atrasos
    """
    data_hoje = date.today()
    data_vencida = data_hoje - timedelta(days=15)  # 15 dias atrás
    data_futura = data_hoje + timedelta(days=30)   # 30 dias à frente
    
    dados = []
    
    # Parcelas pagas/em dia
    for i in range(1, 10):
        dados.append({
            'Título': '12345678',
            'Parcela/Sequencial': f'{i:03d}',
            'Parcela/Condição': 'Normal',
            'Cód. empresa': '001',
            'Empresa': 'CONSTRUTORA TESTE LTDA',
            'Cód. centro de custo': '100',
            'Centro de custo': 'VENDAS',
            'Documento': 'PM',  # Parcela Mensal
            'Nº documento': f'PM{i:03d}',
            'Cód. cliente': '12345',
            'Cliente': 'CLIENTE ADIMPLENTE TESTE',
            'Status da parcela': 'Aberto',
            'Tipo condição': 'PM',
            'Data vencimento': data_futura + timedelta(days=i*30),
            'Valor original': 2500.00,
            'Indexador': 'IPCA',
            'Correção monetária': 0.00,
            'Juros contratuais': 0.00,
            'Valor atualizado': 2500.00,
            'Taxa administrativa': 0.00,
            'Seguro': 0.00,
            'Valor corrigido': 2500.00,
            'Data base de juros': data_hoje,
            'Juros %': 8.0,
            'Tipo de juros': 'Fixo',
            'Data base correção': data_hoje,
            'Data correção': data_hoje,
            'Dias para desconto VP': 0,
            'Juros VP %': 0.0,
            'Valor presente': 2500.00,
            'Valor desconto comercial': 0.00,
            'Dias de atraso': 0,
            'Multa %': 0.0,
            'Juros de mora': 0.00,
            'Valor de acréscimo': 0.00,
            'Valor a receber': 2500.00,
            'Data da baixa': None,
            'Valor da baixa': 0.00,
            'Recebimento líquido': 0.00
        })
    
    # 1 parcela com pouco atraso (mas não CT)
    dados.append({
        'Título': '12345678',
        'Parcela/Sequencial': '010',
        'Parcela/Condição': 'Normal',
        'Cód. empresa': '001',
        'Empresa': 'CONSTRUTORA TESTE LTDA',
        'Cód. centro de custo': '100',
        'Centro de custo': 'VENDAS',
        'Documento': 'PM',
        'Nº documento': 'PM010',
        'Cód. cliente': '12345',
        'Cliente': 'CLIENTE ADIMPLENTE TESTE',
        'Status da parcela': 'Aberto',
        'Tipo condição': 'PM',
        'Data vencimento': data_vencida,
        'Valor original': 2500.00,
        'Indexador': 'IPCA',
        'Correção monetária': 15.30,
        'Juros contratuais': 25.00,
        'Valor atualizado': 2540.30,
        'Taxa administrativa': 0.00,
        'Seguro': 0.00,
        'Valor corrigido': 2540.30,
        'Data base de juros': data_hoje,
        'Juros %': 8.0,
        'Tipo de juros': 'Fixo',
        'Data base correção': data_hoje,
        'Data correção': data_hoje,
        'Dias para desconto VP': 0,
        'Juros VP %': 0.0,
        'Valor presente': 2540.30,
        'Valor desconto comercial': 0.00,
        'Dias de atraso': 15,
        'Multa %': 2.0,
        'Juros de mora': 40.30,
        'Valor de acréscimo': 40.30,
        'Valor a receber': 2580.60,
        'Data da baixa': None,
        'Valor da baixa': 0.00,
        'Recebimento líquido': 0.00
    })
    
    return dados

def criar_planilha_cliente_inadimplente():
    """
    Cenário 2: Cliente inadimplente - NÃO PODE REPARCELAR
    - 3 ou mais parcelas CT vencidas
    """
    data_hoje = date.today()
    data_vencida = data_hoje - timedelta(days=120)  # 4 meses atrás
    
    dados = []
    
    # 4 parcelas CT vencidas (inadimplência)
    for i in range(1, 5):
        dados.append({
            'Título': '87654321',
            'Parcela/Sequencial': f'{i:03d}',
            'Parcela/Condição': 'CT',
            'Cód. empresa': '001',
            'Empresa': 'CONSTRUTORA TESTE LTDA',
            'Cód. centro de custo': '100',
            'Centro de custo': 'VENDAS',
            'Documento': 'CT',  # Cobrança em Cartório
            'Nº documento': f'CT{i:03d}',
            'Cód. cliente': '54321',
            'Cliente': 'CLIENTE INADIMPLENTE TESTE',
            'Status da parcela': 'Aberto',
            'Tipo condição': 'CT',
            'Data vencimento': data_vencida + timedelta(days=i*30),
            'Valor original': 3000.00,
            'Indexador': 'IPCA',
            'Correção monetária': 450.00,
            'Juros contratuais': 180.00,
            'Valor atualizado': 3630.00,
            'Taxa administrativa': 50.00,
            'Seguro': 0.00,
            'Valor corrigido': 3680.00,
            'Data base de juros': data_hoje,
            'Juros %': 8.0,
            'Tipo de juros': 'Fixo',
            'Data base correção': data_hoje,
            'Data correção': data_hoje,
            'Dias para desconto VP': 0,
            'Juros VP %': 0.0,
            'Valor presente': 3680.00,
            'Valor desconto comercial': 0.00,
            'Dias de atraso': 120 - (i*30),
            'Multa %': 10.0,
            'Juros de mora': 368.00,
            'Valor de acréscimo': 418.00,
            'Valor a receber': 4098.00,
            'Data da baixa': None,
            'Valor da baixa': 0.00,
            'Recebimento líquido': 0.00
        })
    
    return dados

def criar_planilha_cliente_custas_honorarios():
    """
    Cenário 3: Cliente com pendências de custas/honorários
    - Parcelas REC/FAT pendentes
    """
    data_hoje = date.today()
    data_vencida = data_hoje - timedelta(days=60)
    
    dados = []
    
    # Algumas parcelas normais
    for i in range(1, 4):
        dados.append({
            'Título': '11111111',
            'Parcela/Sequencial': f'{i:03d}',
            'Parcela/Condição': 'Normal',
            'Cód. empresa': '001',
            'Empresa': 'CONSTRUTORA TESTE LTDA',
            'Cód. centro de custo': '100',
            'Centro de custo': 'VENDAS',
            'Documento': 'PM',
            'Nº documento': f'PM{i:03d}',
            'Cód. cliente': '11111',
            'Cliente': 'CLIENTE COM CUSTAS TESTE',
            'Status da parcela': 'Aberto',
            'Tipo condição': 'PM',
            'Data vencimento': data_hoje + timedelta(days=i*30),
            'Valor original': 2000.00,
            'Indexador': 'IGPM',
            'Correção monetária': 0.00,
            'Juros contratuais': 0.00,
            'Valor atualizado': 2000.00,
            'Taxa administrativa': 0.00,
            'Seguro': 0.00,
            'Valor corrigido': 2000.00,
            'Data base de juros': data_hoje,
            'Juros %': 8.0,
            'Tipo de juros': 'Fixo',
            'Data base correção': data_hoje,
            'Data correção': data_hoje,
            'Dias para desconto VP': 0,
            'Juros VP %': 0.0,
            'Valor presente': 2000.00,
            'Valor desconto comercial': 0.00,
            'Dias de atraso': 0,
            'Multa %': 0.0,
            'Juros de mora': 0.00,
            'Valor de acréscimo': 0.00,
            'Valor a receber': 2000.00,
            'Data da baixa': None,
            'Valor da baixa': 0.00,
            'Recebimento líquido': 0.00
        })
    
    # Parcelas REC (custas)
    dados.append({
        'Título': '11111111',
        'Parcela/Sequencial': 'REC001',
        'Parcela/Condição': 'REC',
        'Cód. empresa': '001',
        'Empresa': 'CONSTRUTORA TESTE LTDA',
        'Cód. centro de custo': '100',
        'Centro de custo': 'VENDAS',
        'Documento': 'REC',  # Custas
        'Nº documento': 'REC001',
        'Cód. cliente': '11111',
        'Cliente': 'CLIENTE COM CUSTAS TESTE',
        'Status da parcela': 'Aberto',
        'Tipo condição': 'REC',
        'Data vencimento': data_vencida,
        'Valor original': 500.00,
        'Indexador': 'IGPM',
        'Correção monetária': 0.00,
        'Juros contratuais': 0.00,
        'Valor atualizado': 500.00,
        'Taxa administrativa': 0.00,
        'Seguro': 0.00,
        'Valor corrigido': 500.00,
        'Data base de juros': data_hoje,
        'Juros %': 0.0,
        'Tipo de juros': 'Fixo',
        'Data base correção': data_hoje,
        'Data correção': data_hoje,
        'Dias para desconto VP': 0,
        'Juros VP %': 0.0,
        'Valor presente': 500.00,
        'Valor desconto comercial': 0.00,
        'Dias de atraso': 60,
        'Multa %': 0.0,
        'Juros de mora': 0.00,
        'Valor de acréscimo': 0.00,
        'Valor a receber': 500.00,
        'Data da baixa': None,
        'Valor da baixa': 0.00,
        'Recebimento líquido': 0.00
    })
    
    # Parcela FAT (honorários)
    dados.append({
        'Título': '11111111',
        'Parcela/Sequencial': 'FAT001',
        'Parcela/Condição': 'FAT',
        'Cód. empresa': '001',
        'Empresa': 'CONSTRUTORA TESTE LTDA',
        'Cód. centro de custo': '100',
        'Centro de custo': 'VENDAS',
        'Documento': 'FAT',  # Honorários
        'Nº documento': 'FAT001',
        'Cód. cliente': '11111',
        'Cliente': 'CLIENTE COM CUSTAS TESTE',
        'Status da parcela': 'Aberto',
        'Tipo condição': 'FAT',
        'Data vencimento': data_vencida + timedelta(days=15),
        'Valor original': 800.00,
        'Indexador': 'IGPM',
        'Correção monetária': 0.00,
        'Juros contratuais': 0.00,
        'Valor atualizado': 800.00,
        'Taxa administrativa': 0.00,
        'Seguro': 0.00,
        'Valor corrigido': 800.00,
        'Data base de juros': data_hoje,
        'Juros %': 0.0,
        'Tipo de juros': 'Fixo',
        'Data base correção': data_hoje,
        'Data correção': data_hoje,
        'Dias para desconto VP': 0,
        'Juros VP %': 0.0,
        'Valor presente': 800.00,
        'Valor desconto comercial': 0.00,
        'Dias de atraso': 45,
        'Multa %': 0.0,
        'Juros de mora': 0.00,
        'Valor de acréscimo': 0.00,
        'Valor a receber': 800.00,
        'Data da baixa': None,
        'Valor da baixa': 0.00,
        'Recebimento líquido': 0.00
    })
    
    return dados

def criar_planilha_cliente_limite_inadimplencia():
    """
    Cenário 4: Cliente no limite da inadimplência
    - Exatamente 2 parcelas CT vencidas (ainda pode reparcelar)
    """
    data_hoje = date.today()
    data_vencida = data_hoje - timedelta(days=90)
    
    dados = []
    
    # Parcelas normais futuras
    for i in range(1, 6):
        dados.append({
            'Título': '22222222',
            'Parcela/Sequencial': f'{i:03d}',
            'Parcela/Condição': 'Normal',
            'Cód. empresa': '001',
            'Empresa': 'CONSTRUTORA TESTE LTDA',
            'Cód. centro de custo': '100',
            'Centro de custo': 'VENDAS',
            'Documento': 'PM',
            'Nº documento': f'PM{i:03d}',
            'Cód. cliente': '22222',
            'Cliente': 'CLIENTE LIMITE INADIMPLENCIA',
            'Status da parcela': 'Aberto',
            'Tipo condição': 'PM',
            'Data vencimento': data_hoje + timedelta(days=i*30),
            'Valor original': 1800.00,
            'Indexador': 'IPCA',
            'Correção monetária': 0.00,
            'Juros contratuais': 0.00,
            'Valor atualizado': 1800.00,
            'Taxa administrativa': 0.00,
            'Seguro': 0.00,
            'Valor corrigido': 1800.00,
            'Data base de juros': data_hoje,
            'Juros %': 8.0,
            'Tipo de juros': 'Fixo',
            'Data base correção': data_hoje,
            'Data correção': data_hoje,
            'Dias para desconto VP': 0,
            'Juros VP %': 0.0,
            'Valor presente': 1800.00,
            'Valor desconto comercial': 0.00,
            'Dias de atraso': 0,
            'Multa %': 0.0,
            'Juros de mora': 0.00,
            'Valor de acréscimo': 0.00,
            'Valor a receber': 1800.00,
            'Data da baixa': None,
            'Valor da baixa': 0.00,
            'Recebimento líquido': 0.00
        })
    
    # Exatamente 2 parcelas CT vencidas
    for i in range(1, 3):
        dados.append({
            'Título': '22222222',
            'Parcela/Sequencial': f'CT{i:03d}',
            'Parcela/Condição': 'CT',
            'Cód. empresa': '001',
            'Empresa': 'CONSTRUTORA TESTE LTDA',
            'Cód. centro de custo': '100',
            'Centro de custo': 'VENDAS',
            'Documento': 'CT',
            'Nº documento': f'CT{i:03d}',
            'Cód. cliente': '22222',
            'Cliente': 'CLIENTE LIMITE INADIMPLENCIA',
            'Status da parcela': 'Aberto',
            'Tipo condição': 'CT',
            'Data vencimento': data_vencida + timedelta(days=i*20),
            'Valor original': 1800.00,
            'Indexador': 'IPCA',
            'Correção monetária': 270.00,
            'Juros contratuais': 108.00,
            'Valor atualizado': 2178.00,
            'Taxa administrativa': 25.00,
            'Seguro': 0.00,
            'Valor corrigido': 2203.00,
            'Data base de juros': data_hoje,
            'Juros %': 8.0,
            'Tipo de juros': 'Fixo',
            'Data base correção': data_hoje,
            'Data correção': data_hoje,
            'Dias para desconto VP': 0,
            'Juros VP %': 0.0,
            'Valor presente': 2203.00,
            'Valor desconto comercial': 0.00,
            'Dias de atraso': 90 - (i*20),
            'Multa %': 5.0,
            'Juros de mora': 220.30,
            'Valor de acréscimo': 245.30,
            'Valor a receber': 2448.30,
            'Data da baixa': None,
            'Valor da baixa': 0.00,
            'Recebimento líquido': 0.00
        })
    
    return dados

def criar_planilha_cliente_misto():
    """
    Cenário 5: Cliente com situação mista
    - 1 parcela CT, custas REC e parcelas normais
    """
    data_hoje = date.today()
    data_vencida = data_hoje - timedelta(days=45)
    
    dados = []
    
    # Parcelas normais
    for i in range(1, 8):
        dados.append({
            'Título': '33333333',
            'Parcela/Sequencial': f'{i:03d}',
            'Parcela/Condição': 'Normal',
            'Cód. empresa': '001',
            'Empresa': 'CONSTRUTORA TESTE LTDA',
            'Cód. centro de custo': '100',
            'Centro de custo': 'VENDAS',
            'Documento': 'PM',
            'Nº documento': f'PM{i:03d}',
            'Cód. cliente': '33333',
            'Cliente': 'CLIENTE SITUACAO MISTA',
            'Status da parcela': 'Aberto',
            'Tipo condição': 'PM',
            'Data vencimento': data_hoje + timedelta(days=i*30),
            'Valor original': 2200.00,
            'Indexador': 'IGPM',
            'Correção monetária': 0.00,
            'Juros contratuais': 0.00,
            'Valor atualizado': 2200.00,
            'Taxa administrativa': 0.00,
            'Seguro': 0.00,
            'Valor corrigido': 2200.00,
            'Data base de juros': data_hoje,
            'Juros %': 8.0,
            'Tipo de juros': 'Fixo',
            'Data base correção': data_hoje,
            'Data correção': data_hoje,
            'Dias para desconto VP': 0,
            'Juros VP %': 0.0,
            'Valor presente': 2200.00,
            'Valor desconto comercial': 0.00,
            'Dias de atraso': 0,
            'Multa %': 0.0,
            'Juros de mora': 0.00,
            'Valor de acréscimo': 0.00,
            'Valor a receber': 2200.00,
            'Data da baixa': None,
            'Valor da baixa': 0.00,
            'Recebimento líquido': 0.00
        })
    
    # 1 parcela CT
    dados.append({
        'Título': '33333333',
        'Parcela/Sequencial': 'CT001',
        'Parcela/Condição': 'CT',
        'Cód. empresa': '001',
        'Empresa': 'CONSTRUTORA TESTE LTDA',
        'Cód. centro de custo': '100',
        'Centro de custo': 'VENDAS',
        'Documento': 'CT',
        'Nº documento': 'CT001',
        'Cód. cliente': '33333',
        'Cliente': 'CLIENTE SITUACAO MISTA',
        'Status da parcela': 'Aberto',
        'Tipo condição': 'CT',
        'Data vencimento': data_vencida,
        'Valor original': 2200.00,
        'Indexador': 'IGPM',
        'Correção monetária': 110.00,
        'Juros contratuais': 88.00,
        'Valor atualizado': 2398.00,
        'Taxa administrativa': 30.00,
        'Seguro': 0.00,
        'Valor corrigido': 2428.00,
        'Data base de juros': data_hoje,
        'Juros %': 8.0,
        'Tipo de juros': 'Fixo',
        'Data base correção': data_hoje,
        'Data correção': data_hoje,
        'Dias para desconto VP': 0,
        'Juros VP %': 0.0,
        'Valor presente': 2428.00,
        'Valor desconto comercial': 0.00,
        'Dias de atraso': 45,
        'Multa %': 3.0,
        'Juros de mora': 121.40,
        'Valor de acréscimo': 151.40,
        'Valor a receber': 2579.40,
        'Data da baixa': None,
        'Valor da baixa': 0.00,
        'Recebimento líquido': 0.00
    })
    
    # 1 parcela REC
    dados.append({
        'Título': '33333333',
        'Parcela/Sequencial': 'REC001',
        'Parcela/Condição': 'REC',
        'Cód. empresa': '001',
        'Empresa': 'CONSTRUTORA TESTE LTDA',
        'Cód. centro de custo': '100',
        'Centro de custo': 'VENDAS',
        'Documento': 'REC',
        'Nº documento': 'REC001',
        'Cód. cliente': '33333',
        'Cliente': 'CLIENTE SITUACAO MISTA',
        'Status da parcela': 'Aberto',
        'Tipo condição': 'REC',
        'Data vencimento': data_vencida + timedelta(days=10),
        'Valor original': 350.00,
        'Indexador': 'IGPM',
        'Correção monetária': 0.00,
        'Juros contratuais': 0.00,
        'Valor atualizado': 350.00,
        'Taxa administrativa': 0.00,
        'Seguro': 0.00,
        'Valor corrigido': 350.00,
        'Data base de juros': data_hoje,
        'Juros %': 0.0,
        'Tipo de juros': 'Fixo',
        'Data base correção': data_hoje,
        'Data correção': data_hoje,
        'Dias para desconto VP': 0,
        'Juros VP %': 0.0,
        'Valor presente': 350.00,
        'Valor desconto comercial': 0.00,
        'Dias de atraso': 35,
        'Multa %': 0.0,
        'Juros de mora': 0.00,
        'Valor de acréscimo': 0.00,
        'Valor a receber': 350.00,
        'Data da baixa': None,
        'Valor da baixa': 0.00,
        'Recebimento líquido': 0.00
    })
    
    return dados

def salvar_planilha(dados, nome_arquivo):
    """
    Salva os dados em arquivo Excel
    """
    try:
        # Cria diretório se não existir - usando caminho absoluto
        pasta_exemplos = Path(__file__).parent / "planilhas_exemplo"
        pasta_exemplos.mkdir(parents=True, exist_ok=True)
        
        # Converte para DataFrame
        df = pd.DataFrame(dados)
        
        # Formata colunas de data
        colunas_data = ['Data vencimento', 'Data base de juros', 'Data base correção', 'Data correção', 'Data da baixa']
        for col in colunas_data:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Salva arquivo
        caminho_arquivo = pasta_exemplos / nome_arquivo
        df.to_excel(caminho_arquivo, index=False, engine='openpyxl')
        
        print(f"✅ Planilha criada: {caminho_arquivo}")
        print(f"   📊 {len(dados)} linhas de dados")
        
        return str(caminho_arquivo)
        
    except Exception as e:
        print(f"❌ Erro ao criar planilha {nome_arquivo}: {e}")
        return None

def criar_todas_planilhas():
    """
    Cria todas as planilhas de exemplo para teste
    """
    print("🏗️ CRIANDO PLANILHAS DE EXEMPLO PARA TESTE")
    print("=" * 50)
    
    planilhas_criadas = []
    
    # 1. Cliente adimplente
    print("📋 1. Cliente Adimplente...")
    dados = criar_planilha_cliente_adimplente()
    arquivo = salvar_planilha(dados, "saldo_devedor_adimplente.xlsx")
    if arquivo:
        planilhas_criadas.append(("Adimplente", arquivo))
    
    # 2. Cliente inadimplente
    print("\n📋 2. Cliente Inadimplente...")
    dados = criar_planilha_cliente_inadimplente()
    arquivo = salvar_planilha(dados, "saldo_devedor_inadimplente.xlsx")
    if arquivo:
        planilhas_criadas.append(("Inadimplente", arquivo))
    
    # 3. Cliente com custas/honorários
    print("\n📋 3. Cliente com Custas/Honorários...")
    dados = criar_planilha_cliente_custas_honorarios()
    arquivo = salvar_planilha(dados, "saldo_devedor_custas_honorarios.xlsx")
    if arquivo:
        planilhas_criadas.append(("Custas/Honorários", arquivo))
    
    # 4. Cliente no limite da inadimplência
    print("\n📋 4. Cliente Limite Inadimplência...")
    dados = criar_planilha_cliente_limite_inadimplencia()
    arquivo = salvar_planilha(dados, "saldo_devedor_limite_inadimplencia.xlsx")
    if arquivo:
        planilhas_criadas.append(("Limite Inadimplência", arquivo))
    
    # 5. Cliente situação mista
    print("\n📋 5. Cliente Situação Mista...")
    dados = criar_planilha_cliente_misto()
    arquivo = salvar_planilha(dados, "saldo_devedor_situacao_mista.xlsx")
    if arquivo:
        planilhas_criadas.append(("Situação Mista", arquivo))
    
    print(f"\n✅ CONCLUÍDO - {len(planilhas_criadas)} planilhas criadas")
    print("\n📁 ARQUIVOS CRIADOS:")
    for tipo, caminho in planilhas_criadas:
        print(f"   • {tipo}: {Path(caminho).name}")
    
    return planilhas_criadas

if __name__ == "__main__":
    criar_todas_planilhas()
