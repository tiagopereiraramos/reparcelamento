#!/usr/bin/env python3
"""
Teste do RPA Análise de Planilhas
Executa o RPA de forma independente para validação

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Adiciona o diretório raiz do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rpa_analise_planilhas.rpa_analise_planilhas import RPAAnalisePlanilhas, executar_analise_planilhas


async def teste_completo():
    """
    Executa teste completo do RPA Análise de Planilhas
    """
    print("🧪 TESTE RPA ANÁLISE DE PLANILHAS")
    print("=" * 50)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)

    # Configurações de teste
    # IDs das planilhas do cliente (você pode alterar aqui)
    PLANILHA_CALCULO_ID = "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"
    PLANILHA_APOIO_ID = "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"
    CREDENCIAIS_GOOGLE = "credentials/gspread-459713-aab8a657f9b0.json"

    print(f"📊 Planilha de Cálculo: {PLANILHA_CALCULO_ID}")
    print(f"📋 Planilha de Apoio: {PLANILHA_APOIO_ID}")
    print(f"🔐 Credenciais: {CREDENCIAIS_GOOGLE}")
    print()

    try:
        # Executa RPA usando função auxiliar
        print("🚀 Iniciando execução do RPA...")
        resultado = await executar_analise_planilhas(
            planilha_calculo_id=PLANILHA_CALCULO_ID,
            planilha_apoio_id=PLANILHA_APOIO_ID,
            credenciais_google=CREDENCIAIS_GOOGLE
        )

        # Mostra resultado
        print("\n📋 RESULTADO DA EXECUÇÃO:")
        print("-" * 30)
        print(f"Status: {resultado}")
        print(f"Sucesso: {'✅ SIM' if resultado.sucesso else '❌ NÃO'}")
        print(f"Mensagem: {resultado.mensagem}")

        if resultado.tempo_execucao:
            print(f"Tempo: {resultado.tempo_execucao:.2f} segundos")

        if resultado.sucesso and resultado.dados:
            print("\n📊 DADOS ANALISADOS:")
            dados = resultado.dados

            print(f"   📥 Novos contratos processados: {dados.get('novos_contratos_processados', 0)}")
            print(f"   🏠 Pendências IPTU atualizadas: {dados.get('pendencias_iptu_atualizadas', 0)}")
            print(f"   🔄 Contratos para reajuste: {dados.get('contratos_para_reajuste', 0)}")
            print(f"   📋 Itens na fila de processamento: {len(dados.get('fila_processamento', []))}")

            if "timestamp_analise" in dados:
                print(f"   ⏰ Timestamp da análise: {dados['timestamp_analise']}")

            # Mostra alguns detalhes dos contratos encontrados
            if dados.get('detalhes_contratos'):
                print(f"\n📋 PRIMEIROS 3 CONTRATOS PARA REAJUSTE:")
                for i, contrato in enumerate(dados['detalhes_contratos'][:3], 1):
                    print(f"   {i}. Título: {contrato.get('numero_titulo', 'N/A')}")
                    print(f"      Cliente: {contrato.get('cliente', 'N/A')}")
                    print(f"      Último reajuste: {contrato.get('Último reajuste', 'N/A')}")
                    print(f"      Dias sem reajuste: {contrato.get('dias_desde_ultimo_reajuste', 'N/A')}")
                    print()

        if not resultado.sucesso and resultado.erro:
            print(f"\n❌ ERRO: {resultado.erro}")

        print("\n🔗 LINKS ÚTEIS:")
        print(f"   Planilha Cálculo: https://docs.google.com/spreadsheets/d/{PLANILHA_CALCULO_ID}")
        print(f"   Planilha Apoio: https://docs.google.com/spreadsheets/d/{PLANILHA_APOIO_ID}")

        return resultado.sucesso

    except Exception as e:
        print(f"\n💥 ERRO INESPERADO: {str(e)}")
        import traceback
        print(f"🔍 Detalhes: {traceback.format_exc()}")
        return False


async def teste_conexao_google_sheets():
    """
    Testa apenas a conexão com Google Sheets
    """
    print("🧪 TESTE DE CONEXÃO - GOOGLE SHEETS")
    print("=" * 40)

    try:
        # Cria instância do RPA para testar conexão
        rpa = RPAAnalisePlanilhas()

        # Inicializa recursos
        if await rpa.inicializar():
            print("✅ Recursos inicializados com sucesso")

            # Testa conexão Google Sheets
            await rpa._conectar_google_sheets()
            print("✅ Conexão Google Sheets estabelecida")

            # Testa acesso às planilhas
            PLANILHA_CALCULO_ID = "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"
            PLANILHA_APOIO_ID = "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"

            planilha_calculo = rpa.cliente_sheets.open_by_key(PLANILHA_CALCULO_ID)
            print(f"✅ Planilha de Cálculo acessada: {planilha_calculo.title}")

            planilha_apoio = rpa.cliente_sheets.open_by_key(PLANILHA_APOIO_ID)
            print(f"✅ Planilha de Apoio acessada: {planilha_apoio.title}")

            # Lista abas da planilha de cálculo
            abas_calculo = planilha_calculo.worksheets()
            print(f"📋 Abas da Planilha de Cálculo: {len(abas_calculo)}")
            for i, aba in enumerate(abas_calculo, 1):
                print(f"   {i}. {aba.title}")

            # Lista abas da planilha de apoio
            abas_apoio = planilha_apoio.worksheets()
            print(f"📋 Abas da Planilha de Apoio: {len(abas_apoio)}")
            for i, aba in enumerate(abas_apoio, 1):
                print(f"   {i}. {aba.title}")

            await rpa.finalizar()
            return True

        else:
            print("❌ Falha na inicialização dos recursos")
            return False

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


async def teste_processamento_novos_contratos():
    """
    Testa apenas o processamento de novos contratos
    """
    print("🧪 TESTE DE PROCESSAMENTO - NOVOS CONTRATOS")
    print("=" * 45)

    try:
        rpa = RPAAnalisePlanilhas()
        await rpa.inicializar()
        await rpa._conectar_google_sheets()

        # Testa processamento de novos contratos
        print("📊 Testando processamento de novos contratos...")
        PLANILHA_APOIO_ID = "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"

        novos_contratos = await rpa._processar_novos_contratos(PLANILHA_APOIO_ID)

        print(f"✅ {len(novos_contratos)} novos contratos encontrados")

        if novos_contratos:
            print("\n📋 PRIMEIROS 3 NOVOS CONTRATOS:")
            for i, contrato in enumerate(novos_contratos[:3], 1):
                print(f"   {i}. Linha {contrato.get('linha_planilha', 'N/A')}")
                print(f"      Dados: {list(contrato.keys())[:5]}...")  # Primeiras 5 chaves

        await rpa.finalizar()
        return True

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


async def teste_processamento_iptu():
    """
    Testa apenas o processamento de pendências IPTU
    """
    print("🧪 TESTE DE PROCESSAMENTO - PENDÊNCIAS IPTU")
    print("=" * 45)

    try:
        rpa = RPAAnalisePlanilhas()
        await rpa.inicializar()
        await rpa._conectar_google_sheets()

        # Testa processamento de pendências IPTU
        print("🏠 Testando processamento de pendências IPTU...")
        PLANILHA_APOIO_ID = "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"

        pendencias_iptu = await rpa._processar_pendencias_iptu(PLANILHA_APOIO_ID)

        print(f"✅ {len(pendencias_iptu)} pendências IPTU encontradas")

        if pendencias_iptu:
            print("\n🏠 PRIMEIRAS 3 PENDÊNCIAS IPTU:")
            for i, pendencia in enumerate(pendencias_iptu[:3], 1):
                print(f"   {i}. Linha {pendencia.get('linha_planilha', 'N/A')}")
                print(f"      Dados: {list(pendencia.keys())[:5]}...")  # Primeiras 5 chaves

        await rpa.finalizar()
        return True

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


async def verificar_saude_rpa():
    """
    Verifica saúde geral do RPA
    """
    print("🧪 VERIFICAÇÃO DE SAÚDE - RPA ANÁLISE PLANILHAS")
    print("=" * 50)

    try:
        # Verifica se arquivos essenciais existem
        arquivos_essenciais = [
            "rpa_analise_planilhas.py",
            "../core/base_rpa.py",
            "../core/notificacoes_simples.py"
        ]

        print("📁 Verificando arquivos essenciais:")
        for arquivo in arquivos_essenciais:
            if os.path.exists(arquivo):
                print(f"   ✅ {arquivo}")
            else:
                print(f"   ❌ {arquivo} - AUSENTE")

        # Verifica credenciais
        print("\n🔐 Verificando credenciais:")
        if os.path.exists("credentials/gspread-459713-aab8a657f9b0.json"):
            print("   ✅ Credenciais Google Sheets encontradas")
        elif os.path.exists("../credentials/google_service_account.json"):
            print("   ✅ Credenciais Google Sheets encontradas (padrão)")
        else:
            print("   ❌ Credenciais Google Sheets não encontradas")

        # Verifica dependências
        print("\n📦 Verificando dependências:")
        try:
            import gspread
            print("   ✅ gspread")
        except ImportError:
            print("   ❌ gspread - INSTALAR")

        try:
            from google.oauth2.service_account import Credentials
            print("   ✅ google-auth")
        except ImportError:
            print("   ❌ google-auth - INSTALAR")

        # Testa importação do RPA
        print("\n🤖 Testando importação do RPA:")
        try:
            from rpa_analise_planilhas import RPAAnalisePlanilhas
            print("   ✅ RPAAnalisePlanilhas importado")

            rpa = RPAAnalisePlanilhas()
            print("   ✅ Instância criada")
        except Exception as e:
            print(f"   ❌ Erro na importação: {str(e)}")

        print("\n✅ Verificação de saúde concluída")
        return True

    except Exception as e:
        print(f"❌ Erro na verificação: {str(e)}")
        return False


def menu_interativo():
    """
    Menu interativo para escolher tipo de teste
    """
    print("\n🎯 MENU DE TESTES - RPA ANÁLISE PLANILHAS")
    print("=" * 50)
    print("1. 🚀 Teste Completo (Análise + Planilhas)")
    print("2. 🔗 Teste Conexão Google Sheets")
    print("3. 📥 Teste Novos Contratos")
    print("4. 🏠 Teste Pendências IPTU")
    print("5. 🏥 Verificação de Saúde")
    print("6. ❌ Sair")
    print("=" * 50)

    while True:
        try:
            opcao = input("\n👉 Escolha uma opção (1-6): ").strip()

            if opcao == "1":
                return teste_completo()
            elif opcao == "2":
                return teste_conexao_google_sheets()
            elif opcao == "3":
                return teste_processamento_novos_contratos()
            elif opcao == "4":
                return teste_processamento_iptu()
            elif opcao == "5":
                return verificar_saude_rpa()
            elif opcao == "6":
                print("👋 Encerrando testes...")
                return None
            else:
                print("❌ Opção inválida! Escolha entre 1-6.")

        except KeyboardInterrupt:
            print("\n👋 Teste interrompido pelo usuário")
            return None


async def main():
    """
    Função principal do teste
    """
    print("🤖 SISTEMA DE TESTES RPA - ANÁLISE DE PLANILHAS")
    print("Desenvolvido em Python")
    print("Permite testar RPA independente da orquestração Temporal")
    print()

    # Executa menu interativo
    teste_selecionado = menu_interativo()

    if teste_selecionado:
        print("\n🚀 Executando teste selecionado...")
        sucesso = await teste_selecionado

        print("\n" + "=" * 50)
        if sucesso:
            print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        else:
            print("❌ TESTE FALHOU - Verifique os logs acima")
        print("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {str(e)}")
        import traceback
        print(f"🔍 Detalhes: {traceback.format_exc()}")