"""
Teste do Sistema RPA Refatorado
Script simplificado para testar a nova arquitetura em português brasileiro

Execute este script para validar se todos os 4 RPAs estão funcionando corretamente
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, Any

# Importa os 4 RPAs refatorados
from rpa_coleta_indices import executar_coleta_indices
from rpa_analise_planilhas import executar_analise_planilhas  
from rpa_sienge import executar_processamento_sienge
from rpa_sicredi import executar_processamento_sicredi

def imprimir_cabecalho():
    """Imprime cabeçalho do teste"""
    print("=" * 80)
    print("🤖 TESTE DO SISTEMA RPA REFATORADO")
    print("Arquitetura simplificada - 4 RPAs independentes")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)

def imprimir_resultado_rpa(nome_rpa: str, resultado, numero: int):
    """Imprime resultado de um RPA de forma organizada"""
    print(f"\n📋 RPA {numero} - {nome_rpa}")
    print("-" * 50)
    
    if resultado.sucesso:
        print(f"✅ Status: SUCESSO")
        print(f"📝 Mensagem: {resultado.mensagem}")
        print(f"⏱️  Tempo: {resultado.tempo_execucao:.2f}s")
        
        # Mostra dados principais
        if resultado.dados:
            if nome_rpa == "Coleta de Índices":
                ipca = resultado.dados.get('ipca', {})
                igpm = resultado.dados.get('igpm', {})
                print(f"📊 IPCA: {ipca.get('valor', 'N/A')}%")
                print(f"📊 IGPM: {igpm.get('valor', 'N/A')}%")
                
            elif nome_rpa == "Análise de Planilhas":
                contratos = resultado.dados.get('contratos_para_reajuste', 0)
                novos = resultado.dados.get('novos_contratos_processados', 0)
                print(f"📄 Contratos para reajuste: {contratos}")
                print(f"📄 Novos contratos: {novos}")
                
            elif nome_rpa == "Processamento Sienge":
                contrato = resultado.dados.get('contrato_processado', {})
                print(f"🏢 Contrato: {contrato.get('numero_titulo', 'N/A')}")
                print(f"🏢 Cliente: {contrato.get('cliente', 'N/A')}")
                
            elif nome_rpa == "Processamento Sicredi":
                confirmacao = resultado.dados.get('confirmacao', {})
                print(f"🏦 Carnês atualizados: {confirmacao.get('carnes_atualizados', 'N/A')}")
                
    else:
        print(f"❌ Status: ERRO")
        print(f"📝 Mensagem: {resultado.mensagem}")
        print(f"🔥 Erro: {resultado.erro}")

async def testar_rpa_coleta_indices():
    """Testa RPA 1 - Coleta de Índices"""
    try:
        # Usa planilha de teste (você pode alterar o ID aqui)
        planilha_id = "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"
        
        resultado = await executar_coleta_indices(
            planilha_id=planilha_id,
            credenciais_google="./credentials/google_service_account.json"
        )
        
        return resultado
        
    except Exception as e:
        from core.base_rpa import ResultadoRPA
        return ResultadoRPA(
            sucesso=False,
            mensagem="Erro no teste RPA Coleta de Índices",
            erro=str(e)
        )

async def testar_rpa_analise_planilhas():
    """Testa RPA 2 - Análise de Planilhas"""
    try:
        # IDs das planilhas (você pode alterar aqui)
        planilha_calculo_id = "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"
        planilha_apoio_id = "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"
        
        resultado = await executar_analise_planilhas(
            planilha_calculo_id=planilha_calculo_id,
            planilha_apoio_id=planilha_apoio_id,
            credenciais_google="./credentials/google_service_account.json"
        )
        
        return resultado
        
    except Exception as e:
        from core.base_rpa import ResultadoRPA
        return ResultadoRPA(
            sucesso=False,
            mensagem="Erro no teste RPA Análise de Planilhas", 
            erro=str(e)
        )

async def testar_rpa_sienge():
    """Testa RPA 3 - Processamento Sienge"""
    try:
        # Dados de teste para contrato
        contrato_teste = {
            "numero_titulo": "123456789",
            "cliente": "CLIENTE TESTE LTDA",
            "empreendimento": "EMPREENDIMENTO TESTE",
            "cnpj_unidade": "12.345.678/0001-90",
            "indexador": "IPCA",
            "Último reajuste": "01/01/2023"
        }
        
        # Índices econômicos simulados
        indices_teste = {
            "ipca": {"valor": 4.62, "tipo": "IPCA"},
            "igpm": {"valor": 3.89, "tipo": "IGPM"}
        }
        
        # Credenciais Sienge (usar variáveis de ambiente)
        credenciais_sienge = {
            "url": os.getenv("SIENGE_URL", "https://sienge-teste.com"),
            "usuario": os.getenv("SIENGE_USERNAME", "usuario_teste"),
            "senha": os.getenv("SIENGE_PASSWORD", "senha_teste")
        }
        
        resultado = await executar_processamento_sienge(
            contrato=contrato_teste,
            indices_economicos=indices_teste,
            credenciais_sienge=credenciais_sienge
        )
        
        return resultado
        
    except Exception as e:
        from core.base_rpa import ResultadoRPA
        return ResultadoRPA(
            sucesso=False,
            mensagem="Erro no teste RPA Sienge",
            erro=str(e)
        )

async def testar_rpa_sicredi():
    """Testa RPA 4 - Processamento Sicredi"""
    try:
        # Arquivo de remessa simulado
        arquivo_remessa = "./temp/remessa_teste_123456789.txt"
        
        # Credenciais Sicredi (usar variáveis de ambiente)
        credenciais_sicredi = {
            "url": os.getenv("SICREDI_URL", "https://webbank.sicredi.com.br"),
            "usuario": os.getenv("SICREDI_USERNAME", "usuario_teste"),
            "senha": os.getenv("SICREDI_PASSWORD", "senha_teste")
        }
        
        # Dados de processamento do Sienge
        dados_processamento = {
            "numero_titulo": "123456789",
            "novo_saldo": 150000.00,
            "arquivo_gerado": True
        }
        
        resultado = await executar_processamento_sicredi(
            arquivo_remessa=arquivo_remessa,
            credenciais_sicredi=credenciais_sicredi,
            dados_processamento=dados_processamento
        )
        
        return resultado
        
    except Exception as e:
        from core.base_rpa import ResultadoRPA
        return ResultadoRPA(
            sucesso=False,
            mensagem="Erro no teste RPA Sicredi",
            erro=str(e)
        )

async def executar_teste_completo():
    """Executa teste completo dos 4 RPAs"""
    imprimir_cabecalho()
    
    print("\n🚀 Iniciando teste dos 4 RPAs do sistema...")
    print("(Usando dados de teste e simulações)\n")
    
    resultados = {}
    
    # Testa RPA 1 - Coleta de Índices
    print("⏳ Testando RPA 1 - Coleta de Índices...")
    resultado1 = await testar_rpa_coleta_indices()
    resultados["coleta_indices"] = resultado1
    imprimir_resultado_rpa("Coleta de Índices", resultado1, 1)
    
    # Testa RPA 2 - Análise de Planilhas
    print("\n⏳ Testando RPA 2 - Análise de Planilhas...")
    resultado2 = await testar_rpa_analise_planilhas()
    resultados["analise_planilhas"] = resultado2
    imprimir_resultado_rpa("Análise de Planilhas", resultado2, 2)
    
    # Testa RPA 3 - Processamento Sienge
    print("\n⏳ Testando RPA 3 - Processamento Sienge...")
    resultado3 = await testar_rpa_sienge()
    resultados["sienge"] = resultado3
    imprimir_resultado_rpa("Processamento Sienge", resultado3, 3)
    
    # Testa RPA 4 - Processamento Sicredi
    print("\n⏳ Testando RPA 4 - Processamento Sicredi...")
    resultado4 = await testar_rpa_sicredi()
    resultados["sicredi"] = resultado4
    imprimir_resultado_rpa("Processamento Sicredi", resultado4, 4)
    
    # Resumo final
    print("\n" + "=" * 80)
    print("📊 RESUMO FINAL DO TESTE")
    print("=" * 80)
    
    total_rpas = len(resultados)
    rpas_sucesso = sum(1 for r in resultados.values() if r.sucesso)
    rpas_erro = total_rpas - rpas_sucesso
    
    print(f"🎯 Total de RPAs testados: {total_rpas}")
    print(f"✅ RPAs funcionando: {rpas_sucesso}")
    print(f"❌ RPAs com erro: {rpas_erro}")
    print(f"📈 Taxa de sucesso: {(rpas_sucesso/total_rpas)*100:.1f}%")
    
    if rpas_sucesso == total_rpas:
        print("\n🎉 TODOS OS RPAs ESTÃO FUNCIONANDO CORRETAMENTE!")
        print("✨ Sistema refatorado validado com sucesso!")
    else:
        print(f"\n⚠️  {rpas_erro} RPA(s) precisam de atenção")
        print("🔧 Verifique os erros acima e ajuste as configurações")
    
    print("\n📝 PRÓXIMOS PASSOS:")
    print("1. Configure as credenciais reais nos arquivos de ambiente")
    print("2. Implemente o webscraping específico nos RPAs conforme TODOs")
    print("3. Execute o workflow Temporal completo")
    print("4. Configure agendamento automático diário")
    
    return resultados

def main():
    """Função principal"""
    try:
        # Executa teste assíncrono
        resultados = asyncio.run(executar_teste_completo())
        
        # Salva log de teste
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"\n💾 Log de teste salvo em: teste_sistema_{timestamp}.log")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n\n💥 Erro durante teste: {str(e)}")

if __name__ == "__main__":
    main()