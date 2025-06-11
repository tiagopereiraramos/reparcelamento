#!/usr/bin/env python3
"""
Teste do RPA Coleta de Índices
Executa o RPA de forma independente para validação

Desenvolvido em Português Brasileiro
"""

#!/usr/bin/env python3
"""
Teste do RPA Coleta de Índices
Executa o RPA de forma independente para validação

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Adiciona o diretório raiz do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rpa_coleta_indices.rpa_coleta_indices import RPAColetaIndices, executar_coleta_indices


async def teste_completo():
    """
    Executa teste completo do RPA Coleta de Índices
    """
    print("🧪 TESTE RPA COLETA DE ÍNDICES")
    print("=" * 50)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)

    # Configurações de teste
    # ID da planilha do cliente
    PLANILHA_ID = "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"
    CREDENCIAIS_GOOGLE = "credentials/gspread-459713-aab8a657f9b0.json"

    print(f"📊 Planilha de Teste: {PLANILHA_ID}")
    print(f"🔐 Credenciais: {CREDENCIAIS_GOOGLE}")
    print()

    try:
        # Executa RPA usando função auxiliar
        print("🚀 Iniciando execução do RPA...")
        resultado = await executar_coleta_indices(
            planilha_id=PLANILHA_ID,
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
            print("\n📊 DADOS COLETADOS:")
            dados = resultado.dados

            if "ipca" in dados:
                ipca = dados["ipca"]
                print(f"   IPCA: {ipca['valor']}% ({ipca['fonte']})")
                print(f"   Período: {ipca['periodo']}")

            if "igpm" in dados:
                igpm = dados["igpm"]
                print(f"   IGPM: {igpm['valor']}% ({igpm['fonte']})")
                print(f"   Período: {igpm['periodo']}")

            if "planilha_atualizada" in dados:
                print(
                    f"   Planilha atualizada: {dados['planilha_atualizada']}")

        if not resultado.sucesso and resultado.erro:
            print(f"\n❌ ERRO: {resultado.erro}")

        print("\n🔗 LINKS ÚTEIS:")
        print(
            f"   Planilha: https://docs.google.com/spreadsheets/d/{PLANILHA_ID}")

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
        # Cria instância do RPA apenas para testar conexão
        rpa = RPAColetaIndices()

        # Inicializa recursos
        if await rpa.inicializar():
            print("✅ Recursos inicializados com sucesso")

            # Testa conexão Google Sheets
            await rpa._conectar_google_sheets()
            print("✅ Conexão Google Sheets estabelecida")

            # Testa acesso à planilha
            PLANILHA_ID = "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk"
            planilha = rpa.cliente_sheets.open_by_key(PLANILHA_ID)
            print(f"✅ Planilha acessada: {planilha.title}")

            # Lista abas
            abas = planilha.worksheets()
            print(f"📋 Abas encontradas: {len(abas)}")
            for i, aba in enumerate(abas, 1):
                print(f"   {i}. {aba.title}")

            await rpa.finalizar()
            return True

        else:
            print("❌ Falha na inicialização dos recursos")
            return False

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


async def teste_coleta_apis():
    """
    Testa apenas a coleta via APIs (sem webscraping)
    """
    print("🧪 TESTE DE COLETA - APIs BANCO CENTRAL")
    print("=" * 45)

    try:
        rpa = RPAColetaIndices()
        await rpa.inicializar()

        # Testa coleta IPCA
        print("📊 Testando coleta IPCA via API BCB...")
        ipca_valor = await rpa._coletar_ipca_api_bcb()
        print(f"✅ IPCA coletado: {ipca_valor}%")

        # Testa coleta IGPM
        print("📊 Testando coleta IGPM via API BCB...")
        igpm_valor = await rpa._coletar_igpm_api_bcb()
        print(f"✅ IGPM coletado: {igpm_valor}%")

        await rpa.finalizar()
        return True

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


async def verificar_saude_rpa():
    """
    Verifica saúde do RPA (recursos disponíveis)
    """
    print("🧪 VERIFICAÇÃO DE SAÚDE - RPA")
    print("=" * 35)

    try:
        rpa = RPAColetaIndices()
        saude = await rpa.verificar_saude()

        print(f"Status Geral: {saude['status'].upper()}")
        print(f"Timestamp: {saude['timestamp']}")
        print("\nDetalhes:")
        for componente, status in saude['detalhes'].items():
            emoji = "✅" if "conectado" in status or "disponivel" in status else "❌"
            print(f"  {emoji} {componente}: {status}")

        return saude['status'] == 'saudavel'

    except Exception as e:
        print(f"❌ Erro na verificação: {str(e)}")
        return False


def menu_interativo():
    """
    Menu interativo para escolher tipo de teste
    """
    print("\n🎯 MENU DE TESTES - RPA COLETA DE ÍNDICES")
    print("=" * 50)
    print("1. 🚀 Teste Completo (Coleta + Planilha)")
    print("2. 🔗 Teste Conexão Google Sheets")
    print("3. 📊 Teste Coleta APIs")
    print("4. 🏥 Verificação de Saúde")
    print("5. ❌ Sair")
    print("=" * 50)

    while True:
        try:
            opcao = input("\n👉 Escolha uma opção (1-5): ").strip()

            if opcao == "1":
                return teste_completo()
            elif opcao == "2":
                return teste_conexao_google_sheets()
            elif opcao == "3":
                return teste_coleta_apis()
            elif opcao == "4":
                return verificar_saude_rpa()
            elif opcao == "5":
                print("👋 Encerrando testes...")
                return None
            else:
                print("❌ Opção inválida! Escolha entre 1-5.")

        except KeyboardInterrupt:
            print("\n👋 Teste interrompido pelo usuário")
            return None


async def main():
    """
    Função principal do teste
    """
    print("🤖 SISTEMA DE TESTES RPA - COLETA DE ÍNDICES")
    print("Desenvolvido em Python")
    print("Permite testar RPA independente da orquestração Temporal")

    # Verifica se é execução direta ou interativa
    if len(sys.argv) > 1:
        # Execução direta com parâmetros
        comando = sys.argv[1].lower()

        if comando == "completo":
            sucesso = await teste_completo()
        elif comando == "conexao":
            sucesso = await teste_conexao_google_sheets()
        elif comando == "apis":
            sucesso = await teste_coleta_apis()
        elif comando == "saude":
            sucesso = await verificar_saude_rpa()
        else:
            print(f"❌ Comando inválido: {comando}")
            print("Comandos disponíveis: completo, conexao, apis, saude")
            return False

        return sucesso

    else:
        # Menu interativo
        teste_escolhido = menu_interativo()
        if teste_escolhido:
            sucesso = await teste_escolhido

            if sucesso:
                print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            else:
                print("\n❌ TESTE FALHOU!")

            return sucesso

        return True

if __name__ == "__main__":
    # Configura event loop para Windows se necessário
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Executa teste
    try:
        resultado = asyncio.run(main())

        if resultado is not None:
            sys.exit(0 if resultado else 1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n👋 Teste cancelado pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erro fatal: {str(e)}")
        sys.exit(1)