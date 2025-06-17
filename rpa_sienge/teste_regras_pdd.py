"""
TESTE REGRAS PDD - VALIDAÇÃO INADIMPLÊNCIA
Testa aplicação rigorosa das regras PDD para reparcelamento

Desenvolvido em Português Brasileiro
"""

import pandas as pd
import asyncio
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from validador_inadimplencia_pdd import ValidadorInadimplenciaPDD, CalculadoraReparcelamentoPDD

def criar_dados_teste_inadimplente():
    """Cria dados de teste simulando cliente inadimplente (≥3 CT vencidas)"""
    hoje = date.today()
    
    # Cliente com 4 parcelas CT vencidas (INADIMPLENTE)
    dados = [
        {
            "Documento": "CT001",
            "Status da parcela": "VENCIDA",
            "Data vencimento": (hoje - timedelta(days=90)).strftime("%d/%m/%Y"),
            "Valor a receber": "1500.00"
        },
        {
            "Documento": "CT002", 
            "Status da parcela": "VENCIDA",
            "Data vencimento": (hoje - timedelta(days=60)).strftime("%d/%m/%Y"),
            "Valor a receber": "1500.00"
        },
        {
            "Documento": "CT003",
            "Status da parcela": "VENCIDA", 
            "Data vencimento": (hoje - timedelta(days=30)).strftime("%d/%m/%Y"),
            "Valor a receber": "1500.00"
        },
        {
            "Documento": "CT004",
            "Status da parcela": "VENCIDA",
            "Data vencimento": (hoje - timedelta(days=15)).strftime("%d/%m/%Y"),
            "Valor a receber": "1500.00"
        },
        {
            "Documento": "CT005",
            "Status da parcela": "A VENCER",
            "Data vencimento": (hoje + timedelta(days=30)).strftime("%d/%m/%Y"),
            "Valor a receber": "1500.00"
        },
        {
            "Documento": "REC001",
            "Status da parcela": "A VENCER",
            "Data vencimento": (hoje + timedelta(days=60)).strftime("%d/%m/%Y"),
            "Valor a receber": "2000.00"
        }
    ]
    
    return pd.DataFrame(dados)

def criar_dados_teste_adimplente():
    """Cria dados de teste simulando cliente adimplente (<3 CT vencidas)"""
    hoje = date.today()
    
    # Cliente com apenas 2 parcelas CT vencidas (ADIMPLENTE)
    dados = [
        {
            "Documento": "CT001",
            "Status da parcela": "VENCIDA",
            "Data vencimento": (hoje - timedelta(days=45)).strftime("%d/%m/%Y"),
            "Valor a receber": "1200.00"
        },
        {
            "Documento": "CT002",
            "Status da parcela": "VENCIDA",
            "Data vencimento": (hoje - timedelta(days=15)).strftime("%d/%m/%Y"),
            "Valor a receber": "1200.00"
        },
        {
            "Documento": "CT003",
            "Status da parcela": "A VENCER",
            "Data vencimento": (hoje + timedelta(days=15)).strftime("%d/%m/%Y"),
            "Valor a receber": "1200.00"
        },
        {
            "Documento": "CT004",
            "Status da parcela": "A VENCER",
            "Data vencimento": (hoje + timedelta(days=45)).strftime("%d/%m/%Y"),
            "Valor a receber": "1200.00"
        },
        {
            "Documento": "REC001",
            "Status da parcela": "A VENCER",
            "Data vencimento": (hoje + timedelta(days=30)).strftime("%d/%m/%Y"),
            "Valor a receber": "1800.00"
        }
    ]
    
    return pd.DataFrame(dados)

async def testar_validacao_inadimplente():
    """Testa validação de cliente inadimplente"""
    print("=== TESTE: CLIENTE INADIMPLENTE ===")
    
    validador = ValidadorInadimplenciaPDD()
    df_teste = criar_dados_teste_inadimplente()
    
    resultado = validador.validar_cliente(df_teste, "CLIENTE INADIMPLENTE LTDA", "12345")
    
    print(f"Status Cliente: {resultado['status_cliente']}")
    print(f"Pode Reparcelar: {resultado['pode_reparcelar']}")
    print(f"Motivo: {resultado['motivo_classificacao']}")
    print(f"CT Vencidas: {resultado['qtd_ct_vencidas']}")
    print(f"Nivel Risco: {resultado['nivel_risco']}")
    
    # Validar resultado esperado
    assert resultado['status_cliente'] == "INADIMPLENTE"
    assert resultado['pode_reparcelar'] == False
    assert resultado['qtd_ct_vencidas'] >= 3
    
    print("✓ TESTE INADIMPLENTE PASSOU\n")
    return resultado

async def testar_validacao_adimplente():
    """Testa validação de cliente adimplente"""
    print("=== TESTE: CLIENTE ADIMPLENTE ===")
    
    validador = ValidadorInadimplenciaPDD()
    df_teste = criar_dados_teste_adimplente()
    
    resultado = validador.validar_cliente(df_teste, "CLIENTE ADIMPLENTE LTDA", "67890")
    
    print(f"Status Cliente: {resultado['status_cliente']}")
    print(f"Pode Reparcelar: {resultado['pode_reparcelar']}")
    print(f"Motivo: {resultado['motivo_classificacao']}")
    print(f"CT Vencidas: {resultado['qtd_ct_vencidas']}")
    print(f"Nivel Risco: {resultado['nivel_risco']}")
    
    # Validar resultado esperado
    assert resultado['status_cliente'] == "ADIMPLENTE"
    assert resultado['pode_reparcelar'] == True
    assert resultado['qtd_ct_vencidas'] < 3
    
    print("✓ TESTE ADIMPLENTE PASSOU\n")
    return resultado

async def testar_calculo_reparcelamento():
    """Testa cálculo de valores para reparcelamento"""
    print("=== TESTE: CÁLCULO REPARCELAMENTO ===")
    
    calculadora = CalculadoraReparcelamentoPDD()
    
    # Valores de teste
    saldo_atual = 10000.00
    indice_igpm = 3.89  # Exemplo real
    parcelas_pendentes = 8
    
    resultado = calculadora.calcular_valores_sienge(saldo_atual, indice_igpm, parcelas_pendentes)
    
    print(f"Saldo Anterior: R$ {saldo_atual:,.2f}")
    print(f"Índice IGP-M: {indice_igpm}%")
    print(f"Novo Saldo: R$ {resultado['detalhes_calculo']['novo_saldo']:,.2f}")
    print(f"Correção: R$ {resultado['detalhes_calculo']['diferenca_correcao']:,.2f}")
    
    valores_sienge = resultado['valores_sienge']
    print(f"Detalhamento: {valores_sienge['detalhamento']}")
    print(f"Tipo Condição: {valores_sienge['tipo_condicao']}")
    print(f"Indexador: {valores_sienge['indexador']}")
    print(f"Juros: {valores_sienge['percentual_juros']}%")
    
    # Validar cálculos
    assert resultado['sucesso'] == True
    assert valores_sienge['indexador'] == "1 IGP-M"  # SEMPRE IGP-M
    assert valores_sienge['percentual_juros'] == 8.0  # FIXO 8%
    assert valores_sienge['tipo_condicao'] == "PM"  # Prazo Mensal
    
    print("✓ TESTE CÁLCULO PASSOU\n")
    return resultado

async def testar_parcelas_desmarcar():
    """Testa determinação de parcelas para desmarcar"""
    print("=== TESTE: PARCELAS PARA DESMARCAR ===")
    
    calculadora = CalculadoraReparcelamentoPDD()
    hoje = date.today()
    
    # Parcelas CT a vencer (algumas devem ser desmarcadas)
    parcelas_ct = [
        {
            "Documento": "CT001",
            "Data vencimento": (hoje - timedelta(days=5)).strftime("%d/%m/%Y"),  # Deve desmarcar
            "Valor a receber": "1000.00"
        },
        {
            "Documento": "CT002", 
            "Data vencimento": hoje.strftime("%d/%m/%Y"),  # Deve desmarcar
            "Valor a receber": "1000.00"
        },
        {
            "Documento": "CT003",
            "Data vencimento": (hoje + timedelta(days=30)).strftime("%d/%m/%Y"),  # Não desmarcar
            "Valor a receber": "1000.00"
        }
    ]
    
    parcelas_desmarcar = calculadora.determinar_parcelas_desmarcar(parcelas_ct)
    
    print(f"Total parcelas analisadas: {len(parcelas_ct)}")
    print(f"Parcelas para desmarcar: {len(parcelas_desmarcar)}")
    
    for parcela in parcelas_desmarcar:
        print(f"- {parcela['documento']}: {parcela['data_vencimento']} - {parcela['motivo']}")
    
    # Validar resultado
    assert len(parcelas_desmarcar) == 2  # CT001 e CT002
    
    print("✓ TESTE PARCELAS DESMARCAR PASSOU\n")
    return parcelas_desmarcar

async def executar_todos_testes():
    """Executa bateria completa de testes das regras PDD"""
    print("🧪 INICIANDO TESTES REGRAS PDD")
    print("=" * 50)
    
    try:
        # Teste 1: Cliente inadimplente
        resultado_inadimplente = await testar_validacao_inadimplente()
        
        # Teste 2: Cliente adimplente  
        resultado_adimplente = await testar_validacao_adimplente()
        
        # Teste 3: Cálculo de reparcelamento
        resultado_calculo = await testar_calculo_reparcelamento()
        
        # Teste 4: Parcelas para desmarcar
        resultado_parcelas = await testar_parcelas_desmarcar()
        
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("=" * 50)
        
        # Salvar resultados para análise
        resultados_completos = {
            "teste_inadimplente": resultado_inadimplente,
            "teste_adimplente": resultado_adimplente,
            "teste_calculo": resultado_calculo,
            "teste_parcelas": resultado_parcelas,
            "timestamp_teste": datetime.now().isoformat(),
            "status_geral": "SUCESSO"
        }
        
        # Salvar arquivo de teste
        pasta_testes = Path("dados_processamento/testes_pdd")
        pasta_testes.mkdir(parents=True, exist_ok=True)
        
        arquivo_resultado = pasta_testes / f"teste_pdd_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(arquivo_resultado, 'w', encoding='utf-8') as f:
            json.dump(resultados_completos, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📄 Resultados salvos em: {arquivo_resultado}")
        
        return resultados_completos
        
    except Exception as e:
        print(f"❌ ERRO NOS TESTES: {str(e)}")
        raise

def validar_planilha_exemplo():
    """Valida se as planilhas de exemplo existem e têm estrutura correta"""
    pasta_exemplos = Path("planilhas_exemplo")
    
    if not pasta_exemplos.exists():
        print("⚠️ Pasta de exemplos não encontrada - criando dados de teste em memória")
        return False
    
    arquivos_exemplo = list(pasta_exemplos.glob("*.xlsx"))
    
    print(f"📁 Encontrados {len(arquivos_exemplo)} arquivos de exemplo:")
    for arquivo in arquivos_exemplo:
        print(f"  - {arquivo.name}")
    
    return len(arquivos_exemplo) > 0

if __name__ == "__main__":
    print("🚀 SISTEMA DE TESTE REGRAS PDD")
    print("Validação rigorosa da regra: ≥3 CT vencidas = INADIMPLENTE")
    print()
    
    # Verificar planilhas de exemplo
    validar_planilha_exemplo()
    print()
    
    # Executar testes
    asyncio.run(executar_todos_testes())