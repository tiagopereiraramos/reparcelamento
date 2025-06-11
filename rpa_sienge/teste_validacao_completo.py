
#!/usr/bin/env python3
"""
Teste Completo de Validação RPA Sienge
Testa todas as regras do PDD usando planilhas Excel mockadas

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Adiciona o diretório pai ao path para importar módulos
sys.path.append(str(Path(__file__).parent.parent))

# Import funciona tanto quando executado da raiz quanto da pasta rpa_sienge
try:
    from rpa_sienge.rpa_sienge import RPASienge
except ImportError:
    from rpa_sienge import RPASienge

try:
    from rpa_sienge.criar_planilhas_exemplo import criar_todas_planilhas
except ImportError:
    from criar_planilhas_exemplo import criar_todas_planilhas

async def testar_cenario_especifico(rpa, arquivo_planilha, nome_cenario, resultado_esperado):
    """
    Testa um cenário específico com arquivo de planilha mockado
    
    Args:
        rpa: Instância do RPA Sienge
        arquivo_planilha: Caminho para o arquivo Excel de teste
        nome_cenario: Nome do cenário para logging
        resultado_esperado: Resultado esperado (pode_reparcelar = True/False)
    
    Returns:
        Resultado do teste (True se passou, False se falhou)
    """
    try:
        print(f"\n🧪 TESTANDO: {nome_cenario}")
        print("-" * 50)
        
        # Dados de contrato exemplo para teste
        contrato_teste = {
            "cliente": f"CLIENTE {nome_cenario.upper()}",
            "numero_titulo": f"12345{hash(nome_cenario) % 10000:04d}",
            "cnpj_unidade": "12.345.678/0001-90",
            "indexador": "IPCA"
        }
        
        # Verifica se arquivo existe
        if not os.path.exists(arquivo_planilha):
            print(f"❌ Arquivo não encontrado: {arquivo_planilha}")
            return False
        
        print(f"📁 Processando: {Path(arquivo_planilha).name}")
        
        # Processa o relatório Excel mockado
        dados_financeiros = await rpa._processar_relatorio_excel(arquivo_planilha, contrato_teste)
        
        # Exibe resultados detalhados
        print(f"\n📊 RESULTADOS DO PROCESSAMENTO:")
        print(f"   Cliente: {dados_financeiros.get('cliente', 'N/A')}")
        print(f"   Título: {dados_financeiros.get('numero_titulo', 'N/A')}")
        print(f"   Total Parcelas: {dados_financeiros.get('total_parcelas', 0)}")
        print(f"   Parcelas Pendentes: {dados_financeiros.get('parcelas_pendentes', 0)}")
        print(f"   Parcelas Vencidas: {len(dados_financeiros.get('parcelas_vencidas', []))}")
        print(f"   Parcelas CT Vencidas: {len(dados_financeiros.get('parcelas_ct_vencidas', []))}")
        print(f"   Parcelas REC/FAT: {len(dados_financeiros.get('parcelas_rec_fat', []))}")
        print(f"   Saldo Total: R$ {dados_financeiros.get('saldo_total', 0):,.2f}")
        print(f"   Status Cliente: {dados_financeiros.get('status_cliente', 'N/A')}")
        
        # Resultado da validação
        pode_reparcelar = dados_financeiros.get('pode_reparcelar', False)
        motivo = dados_financeiros.get('motivo_validacao', 'N/A')
        
        print(f"\n🔍 VALIDAÇÃO DE REPARCELAMENTO:")
        print(f"   Pode Reparcelar: {'✅ SIM' if pode_reparcelar else '❌ NÃO'}")
        print(f"   Motivo: {motivo}")
        
        # Verifica se resultado está conforme esperado
        if pode_reparcelar == resultado_esperado:
            print(f"✅ TESTE PASSOU - Resultado conforme esperado")
            
            # Log adicional das parcelas para verificação
            if dados_financeiros.get('parcelas_ct_vencidas'):
                print(f"\n📋 PARCELAS CT VENCIDAS ({len(dados_financeiros['parcelas_ct_vencidas'])}):")
                for i, parcela in enumerate(dados_financeiros['parcelas_ct_vencidas'][:3], 1):
                    print(f"   {i}. {parcela.get('numero_parcela', 'N/A')} - "
                          f"Venc: {parcela.get('data_vencimento', 'N/A')} - "
                          f"Valor: R$ {parcela.get('valor', 0):,.2f}")
            
            if dados_financeiros.get('parcelas_rec_fat'):
                print(f"\n📋 PARCELAS REC/FAT ({len(dados_financeiros['parcelas_rec_fat'])}):")
                for i, parcela in enumerate(dados_financeiros['parcelas_rec_fat'][:3], 1):
                    print(f"   {i}. {parcela.get('numero_parcela', 'N/A')} - "
                          f"Tipo: {parcela.get('tipo_documento', 'N/A')} - "
                          f"Valor: R$ {parcela.get('valor', 0):,.2f}")
            
            return True
        else:
            print(f"❌ TESTE FALHOU - Esperado: {resultado_esperado}, Obtido: {pode_reparcelar}")
            return False
            
    except Exception as e:
        print(f"❌ ERRO NO TESTE: {str(e)}")
        import traceback
        print(f"🔍 Detalhes: {traceback.format_exc()}")
        return False

async def executar_teste_completo():
    """
    Executa teste completo de validação com todos os cenários do PDD
    """
    print("🧪 TESTE COMPLETO DE VALIDAÇÃO - RPA SIENGE")
    print("=" * 60)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 1. Cria planilhas de exemplo se não existirem
        print("🏗️ Verificando planilhas de exemplo...")
        pasta_exemplos = Path(__file__).parent / "planilhas_exemplo"
        
        if not pasta_exemplos.exists() or len(list(pasta_exemplos.glob("*.xlsx"))) < 5:
            print("📋 Criando planilhas de exemplo...")
            criar_todas_planilhas()
        else:
            print("✅ Planilhas de exemplo já existem")
        
        # 2. Cria instância do RPA
        rpa = RPASienge()
        
        # 3. Define cenários de teste - usando caminhos absolutos
        pasta_base = Path(__file__).parent / "planilhas_exemplo"
        cenarios_teste = [
            {
                "arquivo": str(pasta_base / "saldo_devedor_adimplente.xlsx"),
                "nome": "Cliente Adimplente",
                "esperado": True,  # PODE reparcelar
                "descricao": "Cliente sem parcelas CT vencidas, apenas parcelas normais"
            },
            {
                "arquivo": str(pasta_base / "saldo_devedor_inadimplente.xlsx"), 
                "nome": "Cliente Inadimplente",
                "esperado": False,  # NÃO PODE reparcelar
                "descricao": "Cliente com 3+ parcelas CT vencidas"
            },
            {
                "arquivo": str(pasta_base / "saldo_devedor_custas_honorarios.xlsx"),
                "nome": "Cliente com Custas/Honorários", 
                "esperado": True,  # PODE reparcelar (mas com pendências)
                "descricao": "Cliente com parcelas REC/FAT pendentes"
            },
            {
                "arquivo": str(pasta_base / "saldo_devedor_limite_inadimplencia.xlsx"),
                "nome": "Cliente Limite Inadimplência",
                "esperado": True,  # PODE reparcelar (2 CT < 3)
                "descricao": "Cliente com exatamente 2 parcelas CT vencidas"
            },
            {
                "arquivo": str(pasta_base / "saldo_devedor_situacao_mista.xlsx"),
                "nome": "Cliente Situação Mista",
                "esperado": True,  # PODE reparcelar (1 CT + REC)
                "descricao": "Cliente com 1 parcela CT e parcelas REC/FAT"
            }
        ]
        
        # 4. Executa todos os testes
        resultados = []
        print(f"\n🚀 EXECUTANDO {len(cenarios_teste)} CENÁRIOS DE TESTE")
        print("=" * 60)
        
        for i, cenario in enumerate(cenarios_teste, 1):
            print(f"\n📋 CENÁRIO {i}/{len(cenarios_teste)}: {cenario['nome']}")
            print(f"📝 Descrição: {cenario['descricao']}")
            print(f"🎯 Resultado Esperado: {'✅ PODE reparcelar' if cenario['esperado'] else '❌ NÃO PODE reparcelar'}")
            
            resultado = await testar_cenario_especifico(
                rpa=rpa,
                arquivo_planilha=cenario['arquivo'],
                nome_cenario=cenario['nome'],
                resultado_esperado=cenario['esperado']
            )
            
            resultados.append({
                "cenario": cenario['nome'],
                "passou": resultado,
                "esperado": cenario['esperado']
            })
        
        # 5. Resume resultados
        print("\n" + "=" * 60)
        print("📊 RESUMO DOS TESTES")
        print("=" * 60)
        
        testes_passaram = sum(1 for r in resultados if r['passou'])
        total_testes = len(resultados)
        
        for i, resultado in enumerate(resultados, 1):
            status = "✅ PASSOU" if resultado['passou'] else "❌ FALHOU"
            print(f"   {i}. {resultado['cenario']}: {status}")
        
        print(f"\n🏆 RESULTADO GERAL: {testes_passaram}/{total_testes} testes passaram")
        
        if testes_passaram == total_testes:
            print("🎉 TODOS OS TESTES PASSARAM! Sistema validado conforme PDD.")
            return True
        else:
            print("⚠️ ALGUNS TESTES FALHARAM. Revisar implementação.")
            return False
            
    except Exception as e:
        print(f"💥 ERRO GERAL NO TESTE: {str(e)}")
        import traceback
        print(f"🔍 Detalhes: {traceback.format_exc()}")
        return False

async def testar_cenario_individual(nome_cenario):
    """
    Testa apenas um cenário específico
    
    Args:
        nome_cenario: Nome do cenário para testar ('adimplente', 'inadimplente', etc.)
    """
    print(f"🧪 TESTE INDIVIDUAL - {nome_cenario.upper()}")
    print("=" * 50)
    
    pasta_base = Path(__file__).parent / "planilhas_exemplo"
    mapeamento_arquivos = {
        'adimplente': (str(pasta_base / 'saldo_devedor_adimplente.xlsx'), True),
        'inadimplente': (str(pasta_base / 'saldo_devedor_inadimplente.xlsx'), False),
        'custas': (str(pasta_base / 'saldo_devedor_custas_honorarios.xlsx'), True),
        'limite': (str(pasta_base / 'saldo_devedor_limite_inadimplencia.xlsx'), True),
        'misto': (str(pasta_base / 'saldo_devedor_situacao_mista.xlsx'), True)
    }
    
    if nome_cenario.lower() not in mapeamento_arquivos:
        print(f"❌ Cenário '{nome_cenario}' não encontrado")
        print(f"📋 Cenários disponíveis: {', '.join(mapeamento_arquivos.keys())}")
        return False
    
    arquivo, esperado = mapeamento_arquivos[nome_cenario.lower()]
    
    # Cria planilha se necessário
    if not os.path.exists(arquivo):
        print("📋 Criando planilha de exemplo...")
        criar_todas_planilhas()
    
    # Testa cenário
    rpa = RPASienge()
    resultado = await testar_cenario_especifico(
        rpa=rpa,
        arquivo_planilha=arquivo,
        nome_cenario=nome_cenario,
        resultado_esperado=esperado
    )
    
    return resultado

if __name__ == "__main__":
    # Verifica se foi passado um cenário específico
    if len(sys.argv) > 1:
        cenario = sys.argv[1]
        resultado = asyncio.run(testar_cenario_individual(cenario))
    else:
        resultado = asyncio.run(executar_teste_completo())
    
    if resultado:
        print("\n🎉 TESTE(S) APROVADO(S)!")
        sys.exit(0)
    else:
        print("\n💥 TESTE(S) FALHOU/FALHARAM!")
        sys.exit(1)
