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

import sys
import asyncio
import os
from pathlib import Path
from rpa_coleta_indices import RPAColetaIndices, executar_coleta_indices
from datetime import datetime

# Adiciona o diretório raiz do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def teste_completo():
    """
    Executa teste completo do RPA Coleta de Índices
    """
    print("🧪 TESTE RPA COLETA DE ÍNDICES")
    print("=" * 50)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)

    # Configurações de teste
    # IDs das planilhas para teste (configurar com suas planilhas)
    PLANILHA_CALCULO_ID = os.getenv("PLANILHA_CALCULO_ID", "")
    CREDENCIAIS_GOOGLE = os.getenv("GOOGLE_CREDENTIALS_PATH",
                                   "./gspread-credentials.json")

    print(f"📊 Planilha de Teste: {PLANILHA_CALCULO_ID}")
    print(f"🔐 Credenciais: {CREDENCIAIS_GOOGLE}")
    print()

    try:
        # Executa RPA usando função auxiliar
        print("🚀 Iniciando execução do RPA...")
        resultado = await executar_coleta_indices(
            planilha_id=PLANILHA_CALCULO_ID,
            credenciais_google=CREDENCIAIS_GOOGLE)

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
            f"   Planilha: https://docs.google.com/spreadsheets/d/{PLANILHA_TESTE_ID}"
        )

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
            PLANILHA_ID = os.getenv(
                "PLANILHA_INDICES_ID",
                "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk")
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
    Teste completo do RPA Coleta de Índices
    """
    print("🚀 Iniciando teste RPA Coleta de Índices")
    print("=" * 60)

    # Inicializar sistema de dados híbrido ANTES do RPA
    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()
        print("🗄️ Sistema de dados híbrido inicializado")
    except Exception as e:
        print(f"⚠️ Aviso: Falha ao inicializar dados híbridos: {e}")

    rpa = RPAColetaIndices()
    # IDs das planilhas para teste (configurar com suas planilhas)
    PLANILHA_CALCULO_ID = os.getenv("PLANILHA_CALCULO_ID", "")
    CREDENCIAIS_GOOGLE = os.getenv("GOOGLE_CREDENTIALS_PATH",
                                   "./gspread-credentials.json")
    # Parâmetros de teste
    parametros_teste = {
        "planilha_id": PLANILHA_CALCULO_ID,
        "credenciais_google": CREDENCIAIS_GOOGLE
    }

    try:
        # Executa RPA COM MONITORAMENTO (força salvamento)
        resultado = await rpa.executar_com_monitoramento(parametros_teste)

        # Processa resultado
        if resultado.sucesso:
            print(f"\n✅ SUCESSO: {resultado.mensagem}")
            print(f"⏱️ Tempo: {resultado.tempo_execucao:.1f}s")

            if resultado.dados:
                ipca = resultado.dados.get("ipca", {})
                igpm = resultado.dados.get("igpm", {})

                print(
                    f"\n📊 IPCA: {ipca.get('valor', 'N/A')}% ({ipca.get('mes', 'N/A')})")
                print(
                    f"📊 IGPM: {igpm.get('valor', 'N/A')}% ({igpm.get('mes', 'N/A')})")
                print(
                    f"📋 Planilha: {resultado.dados.get('planilha_atualizada', 'N/A')}")

                # Verificar se dados foram salvos
                print(f"\n🔍 Verificando persistência dos dados...")
                try:
                    from core.data_manager import data_manager

                    # Debug detalhado
                    debug_info = await data_manager.debug_verificar_indices_salvos()
                    print(
                        f"📈 Total de execuções registradas: {debug_info.get('total_execucoes', 0)}")
                    print(
                        f"📊 Total de índices salvos: {debug_info.get('total_indices_salvos', 0)}")
                    print(
                        f"📄 Arquivo índices existe: {debug_info.get('arquivo_indices_existe', False)}")
                    print(
                        f"📄 Arquivo execuções existe: {debug_info.get('arquivo_execucoes_existe', False)}")

                    # Verificar se arquivo errado foi criado
                    arquivo_errado = "dados_processamento/indices_coletados.json"
                    if os.path.exists(arquivo_errado):
                        print(
                            f"⚠️ ATENÇÃO: Arquivo incorreto encontrado: {arquivo_errado}")
                        print("   Este arquivo deveria ser 'indices_economicos.json'")

                    # Debug adicional se necessário
                    if debug_info.get('ultimo_indice'):
                        print(
                            f"🔍 Último índice salvo: {debug_info['ultimo_indice'].get('timestamp', 'N/A')}")

                    if debug_info.get('ultima_execucao'):
                        print(
                            f"🔍 Última execução: {debug_info['ultima_execucao'].get('nome_rpa', 'N/A')}")

                except Exception as e:
                    print(f"⚠️ Erro ao verificar persistência: {e}")
        else:
            print(f"\n❌ FALHA: {resultado.mensagem}")
            if resultado.erro:
                print(f"🔍 Erro: {resultado.erro}")

    except Exception as e:
        print(f"\n💥 ERRO DURANTE EXECUÇÃO: {str(e)}")

    finally:
        # Cleanup
        if hasattr(rpa, 'browser') and rpa.browser:
            rpa.browser.close()
        print("\n🔄 Cleanup concluído")

    print("=" * 60)
    print("✅ Teste RPA Coleta de Índices finalizado")


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
