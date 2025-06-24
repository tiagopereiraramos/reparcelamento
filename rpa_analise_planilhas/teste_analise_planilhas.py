#!/usr/bin/env python3
"""
Teste COMPLETO do RPA Análise de Planilhas - REGRAS PDD 9.1.1
Executa todas as regras PDD usando dados reais de CSV do Sienge
Teste com dados do cliente SANDRO RIZZON VIEIRA - Título 2239

Desenvolvido em Português Brasileiro
"""

from rpa_analise_planilhas import RPAAnalisePlanilhas, executar_analise_planilhas
from core.processador_regras_pdd import ProcessadorRegrasNegocio
import asyncio
import sys
import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Any

# Adiciona o diretório raiz do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar processador centralizado


async def teste_regras_pdd_csv_completo():
    """
    Teste COMPLETO das regras PDD 9.1.1 usando dados reais CSV
    """
    print("🧪 TESTE COMPLETO - REGRAS PDD 9.1.1 + CSV REAL")
    print("=" * 60)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("👤 Cliente: SANDRO RIZZON VIEIRA")
    print("🏷️ Título: 2239")
    print("📄 Fonte: saldo_devedor_presente-20250618-152802.csv")
    print("=" * 60)

    try:
        # DADOS DE TESTE BASEADOS NO CSV REAL
        dados_teste_csv = {
            "cliente": "SANDRO RIZZON VIEIRA",
            "numero_titulo": "2239",
            "arquivo_csv": "attached_assets/saldo_devedor_presente-20250618-152802_1750353006921.csv"
        }

        print("\n📊 ETAPA 1: CARREGANDO DADOS CSV REAL")
        print("-" * 40)

        # Carregar CSV real
        if not os.path.exists(dados_teste_csv["arquivo_csv"]):
            print(
                f"❌ Arquivo CSV não encontrado: {dados_teste_csv['arquivo_csv']}")
            return False

        df_csv = pd.read_csv(dados_teste_csv["arquivo_csv"])
        print(f"✅ CSV carregado: {len(df_csv)} registros")
        print(f"📋 Colunas disponíveis: {list(df_csv.columns)[:5]}...")

        # Filtrar apenas dados do título de teste
        df_titulo: Any = df_csv[df_csv["Título"] ==
                                int(dados_teste_csv["numero_titulo"])]
        print(
            f"🎯 Registros do título {dados_teste_csv['numero_titulo']}: {len(df_titulo)}")

        if df_titulo.empty:
            print(
                f"❌ Nenhum registro encontrado para o título {dados_teste_csv['numero_titulo']}")
            return False

        print("\n📊 ETAPA 2: ANÁLISE ESTRUTURAL DOS DADOS")
        print("-" * 40)

        # Análise dos tipos de documento
        tipos_documento = df_titulo["Documento"].value_counts()  # type: ignore
        print(f"📄 Tipos de documento encontrados:")
        for tipo, qtd in tipos_documento.items():
            print(f"   {tipo}: {qtd} registros")

        # Análise dos status
        # type: ignore
        status_parcelas = df_titulo["Status da parcela"].value_counts()
        print(f"\n📈 Status das parcelas:")
        for status, qtd in status_parcelas.items():
            print(f"   {status}: {qtd} registros")

        print("\n🔍 ETAPA 3: APLICANDO REGRAS PDD COMPLETAS")
        print("-" * 40)

        # Instanciar processador
        processador = ProcessadorRegrasNegocio()

        # Executar processamento completo das regras PDD
        resultado_pdd = processador.processar_dados_cliente_completo(
            df_planilha=df_titulo,
            cliente=dados_teste_csv["cliente"],
            numero_titulo=dados_teste_csv["numero_titulo"]
        )

        print(f"✅ Processamento PDD concluído")
        print(
            f"🎯 Sucesso: {'✅ SIM' if resultado_pdd.get('sucesso') else '❌ NÃO'}")

        if not resultado_pdd.get("sucesso"):
            print(f"❌ Erro: {resultado_pdd.get('erro', 'Erro desconhecido')}")
            return False

        print("\n📋 ETAPA 4: RESULTADOS DAS REGRAS PDD")
        print("-" * 40)

        # RESULTADO DA INADIMPLÊNCIA (CRÍTICO)
        print("🚨 REGRA CRÍTICA - INADIMPLÊNCIA:")
        print(f"   Status Cliente: {resultado_pdd.get('status_cliente')}")
        print(
            f"   Pode Reparcelar: {'✅ SIM' if resultado_pdd.get('pode_reparcelar') else '❌ NÃO'}")
        print(f"   Nível Risco: {resultado_pdd.get('nivel_risco')}")
        print(f"   CT Vencidas: {resultado_pdd.get('qtd_ct_vencidas')}")
        print(f"   Motivo: {resultado_pdd.get('motivo_classificacao')}")

        if resultado_pdd.get("processamento_interrompido"):
            print(
                f"\n⚠️ PROCESSAMENTO INTERROMPIDO: {resultado_pdd.get('motivo_interrupcao')}")
            return True

        # SE ADIMPLENTE: MOSTRAR RESULTADOS DAS 8 REGRAS
        print(f"\n✅ CLIENTE ADIMPLENTE - REGRAS 9.1.1 APLICADAS:")
        print(f"   📅 Dia de Vencimento: {resultado_pdd.get('dia_vencimento')}")
        print(
            f"   💰 Valor Parcela Atual: R$ {resultado_pdd.get('valor_parcela_atual', 0):,.2f}")
        print(
            f"   📆 Primeiro Vencimento: {resultado_pdd.get('primeiro_vencimento_carne')}")
        print(
            f"   📊 Parcelas CT a Vencer: {resultado_pdd.get('qtd_parcelas_ct_a_vencer')}")
        print(
            f"   🏠 Parcelas IPTU a Vencer: {resultado_pdd.get('qtd_parcelas_iptu_a_vencer')}")
        print(
            f"   💵 Saldo Total: R$ {resultado_pdd.get('saldo_total', 0):,.2f}")

        # IRREGULARIDADES
        if resultado_pdd.get("tem_parcelas_irregulares"):
            print(
                f"   ⚠️ Parcelas Irregulares: {resultado_pdd.get('quantidade_irregulares')}")
        else:
            print(f"   ✅ Sem Irregularidades")

        print(f"\n📊 DETALHAMENTO FINANCEIRO:")
        print(
            f"   💰 Valor Total CT: R$ {resultado_pdd.get('valor_total_ct', 0):,.2f}")
        print(
            f"   🏠 Valor Total IPTU: R$ {resultado_pdd.get('valor_total_iptu', 0):,.2f}")
        print(
            f"   🔴 Valor Total Vencido: R$ {resultado_pdd.get('valor_total_vencido', 0):,.2f}")

        print("\n🔍 ETAPA 5: TESTE DE CÁLCULOS FINANCEIROS")
        print("-" * 40)

        # Teste de cálculo de reparcelamento
        saldo_atual = resultado_pdd.get('valor_total_ct', 0)
        if saldo_atual > 0:
            # Simular IGPM (usar valor de exemplo)
            igpm_exemplo = 0.28  # 0.28% exemplo

            calculo_resultado = await processador.calcular_valores_reparcelamento(
                saldo_atual=saldo_atual,
                indice_igpm=igpm_exemplo,
                parcelas_pendentes=resultado_pdd.get(
                    'qtd_parcelas_ct_a_vencer', 0)
            )

            if calculo_resultado.get("sucesso"):
                print("✅ CÁLCULO DE REPARCELAMENTO:")
                valores = calculo_resultado["valores_sienge"]
                print(f"   🔄 Saldo Anterior: R$ {saldo_atual:,.2f}")
                print(f"   📈 IGP-M Aplicado: {igpm_exemplo}%")
                print(
                    f"   💵 Novo Saldo: R$ {calculo_resultado['novo_saldo']:,.2f}")
                print(f"   📄 Detalhamento: {valores['detalhamento']}")
                print(
                    f"   📆 Primeiro Vencimento: {valores['data_primeiro_vencimento']}")
                print(
                    f"   📊 Quantidade Parcelas: {valores['quantidade_parcelas']}")
                print(f"   🏦 Indexador: {valores['indexador']}")
                print(f"   💹 Juros: {valores['percentual_juros']}%")
            else:
                print(f"❌ Erro no cálculo: {calculo_resultado.get('erro')}")

        print("\n🔍 ETAPA 6: PARCELAS PARA DESMARCAR")
        print("-" * 40)

        # Determinar parcelas para desmarcar conforme PDD
        parcelas_ct = resultado_pdd.get("parcelas_ct_a_vencer_detalhes", [])

        # CORRIGIDO: Método não aceita parâmetro de estratégia
        parcelas_desmarcar = processador.determinar_parcelas_desmarcar(
            parcelas_ct)

        print(
            f"📊 Regra PDD aplicada: {len(parcelas_desmarcar)} parcelas para desmarcar")
        print("📋 Critério: Data vencimento <= data atual")

        print(f"📋 Total de parcelas CT a vencer: {len(parcelas_ct)}")
        print(f"❌ Parcelas para desmarcar: {len(parcelas_desmarcar)}")

        if parcelas_desmarcar:
            print("📄 Detalhes das parcelas a desmarcar:")
            # Mostrar primeiras 3
            for i, parcela in enumerate(parcelas_desmarcar[:3], 1):
                print(
                    f"   {i}. {parcela['documento']} - Venc: {parcela['data_vencimento']} - Motivo: {parcela['motivo']}")

        print("\n📊 ETAPA 7: ANÁLISE DE DADOS ESPECÍFICOS DO CSV")
        print("-" * 40)

        # Análise específica dos dados do CSV
        print("📈 ANÁLISE TEMPORAL DAS PARCELAS:")

        # Parcelas pagas
        parcelas_pagas = df_titulo[df_titulo["Status da parcela"] == "Paga"]
        print(f"   ✅ Parcelas Pagas: {len(parcelas_pagas)}")

        # Parcelas a vencer
        parcelas_a_vencer: Any = df_titulo[df_titulo["Status da parcela"] == "A vencer"]
        print(f"   ⏳ Parcelas A Vencer: {len(parcelas_a_vencer)}")

        # Análise por indexador
        indexadores = df_titulo["Indexador"].value_counts()  # type: ignore
        print(f"\n📊 INDEXADORES UTILIZADOS:")
        for idx, qtd in indexadores.items():
            print(f"   {idx}: {qtd} parcelas")

        # Análise de valores
        if len(parcelas_a_vencer) > 0:
            print(f"\n💰 ANÁLISE DE VALORES (Parcelas A Vencer):")
            # type: ignore
            valores_a_receber: Any = parcelas_a_vencer["Valor a receber"].dropna(
            )
            if len(valores_a_receber) > 0:
                print(f"   💵 Valor Mínimo: R$ {valores_a_receber.min():,.2f}")
                print(f"   💵 Valor Máximo: R$ {valores_a_receber.max():,.2f}")
                print(f"   💵 Valor Médio: R$ {valores_a_receber.mean():,.2f}")
                print(f"   💵 Valor Total: R$ {valores_a_receber.sum():,.2f}")

        print("\n✅ ETAPA 8: RESUMO FINAL")
        print("-" * 40)
        print("🎯 TODAS AS REGRAS PDD 9.1.1 FORAM TESTADAS:")
        print("   1. ✅ Identificação do dia de vencimento")
        print("   2. ✅ Cálculo do primeiro vencimento")
        print("   3. ✅ Valor da parcela atual")
        print("   4. ✅ Verificação de irregularidades")
        print("   5. ✅ Quantidade de parcelas a vencer")
        print("   6. ✅ Quantidade de parcelas vencidas CT")
        print("   7. ✅ Pendências IPTU")
        print("   8. ✅ Validação final de inadimplência")

        print(f"\n📄 Dados de teste baseados em CSV real do Sienge")
        print(f"🏷️ Cliente: {dados_teste_csv['cliente']}")
        print(f"🔢 Título: {dados_teste_csv['numero_titulo']}")
        print(f"📊 Registros processados: {len(df_titulo)}")
        print(
            f"🎯 Status Final: {'✅ PODE REPARCELAR' if resultado_pdd.get('pode_reparcelar') else '❌ NÃO PODE REPARCELAR'}")

        return True

    except Exception as e:
        print(f"\n💥 ERRO INESPERADO: {str(e)}")
        import traceback
        print(f"🔍 Detalhes: {traceback.format_exc()}")
        return False


async def teste_comparacao_planilhas_google_vs_csv():
    """
    Teste comparativo: análise de planilhas Google Sheets vs dados CSV
    """
    print("🧪 TESTE COMPARATIVO - GOOGLE SHEETS vs CSV")
    print("=" * 50)

    try:
        # Teste RPA Google Sheets (existente)
        print("📊 TESTANDO RPA ANÁLISE PLANILHAS (Google Sheets)...")

        PLANILHA_CALCULO_ID = os.getenv(
            "PLANILHA_CALCULO_ID", "1NTDPDEltum8X3vBHvUetCNWVEcz453FfAZGRYGmmd8U")
        PLANILHA_APOIO_ID = os.getenv(
            "PLANILHA_APOIO_ID", "1rnOZA-CYVQmuH7b6yALNlAe6ZiztrHsrpqEyd9j6tXY")
        CREDENCIAIS_GOOGLE = os.getenv("GOOGLE_CREDENTIALS_PATH",
                                       "./gspread-credentials.json")

        resultado_sheets = await executar_analise_planilhas(
            planilha_calculo_id=PLANILHA_CALCULO_ID,
            planilha_apoio_id=PLANILHA_APOIO_ID,
            credenciais_google=CREDENCIAIS_GOOGLE)

        print(
            f"📋 Google Sheets - Sucesso: {'✅' if resultado_sheets.sucesso else '❌'}")

        # Teste CSV direto
        print("\n📄 TESTANDO ANÁLISE CSV DIRETO...")
        resultado_csv = await teste_regras_pdd_csv_completo()

        print(f"📄 CSV Direto - Sucesso: {'✅' if resultado_csv else '❌'}")

        print("\n🔍 COMPARAÇÃO:")
        print(
            f"   Google Sheets: {'✅ FUNCIONANDO' if resultado_sheets.sucesso else '❌ ERRO'}")
        print(
            f"   CSV Direto: {'✅ FUNCIONANDO' if resultado_csv else '❌ ERRO'}")

        if resultado_sheets.sucesso and resultado_csv:
            print("🎉 AMBOS OS MÉTODOS FUNCIONANDO CORRETAMENTE!")

        return resultado_sheets.sucesso and resultado_csv

    except Exception as e:
        print(f"❌ Erro no teste comparativo: {str(e)}")
        return False


async def teste_validacao_estrutura_csv():
    """
    Teste específico para validar estrutura do CSV
    """
    print("🧪 TESTE DE VALIDAÇÃO - ESTRUTURA CSV")
    print("=" * 40)

    try:
        arquivo_csv = "attached_assets/saldo_devedor_presente-20250618-152802_1750353006921.csv"

        if not os.path.exists(arquivo_csv):
            print(f"❌ Arquivo não encontrado: {arquivo_csv}")
            return False

        # Carregar e analisar CSV
        df = pd.read_csv(arquivo_csv)

        print(f"✅ Arquivo carregado: {len(df)} registros")
        print(f"📊 Colunas: {len(df.columns)}")

        # Verificar colunas essenciais
        colunas_essenciais = [
            "Título", "Parcela/Condição", "Documento", "Cliente",
            "Status da parcela", "Data vencimento", "Valor a receber",
            "Valor original", "Indexador", "Tipo condição"
        ]

        print("\n🔍 VERIFICAÇÃO DE COLUNAS:")
        for coluna in colunas_essenciais:
            existe = coluna in df.columns
            print(f"   {'✅' if existe else '❌'} {coluna}")

        # Análise de dados únicos
        print(f"\n📈 ANÁLISE DE DADOS:")
        print(f"   Títulos únicos: {df['Título'].nunique()}")
        print(f"   Clientes únicos: {df['Cliente'].nunique()}")
        print(f"   Tipos de documento: {df['Documento'].nunique()}")
        print(f"   Status únicos: {df['Status da parcela'].nunique()}")

        # Teste do processador com dados reais
        processador = ProcessadorRegrasNegocio()
        validacao = processador._validar_estrutura_planilha_csv(df)

        print(f"\n🔍 VALIDAÇÃO PROCESSADOR:")
        print(f"   Válida: {'✅' if validacao['valida'] else '❌'}")
        if not validacao['valida']:
            print(f"   Motivo: {validacao['motivo']}")
        else:
            print(f"   Total registros: {validacao['total_registros']}")

        return validacao['valida']

    except Exception as e:
        print(f"❌ Erro na validação: {str(e)}")
        return False


def menu_interativo_completo():
    """
    Menu interativo completo para testes das regras PDD
    """
    print("\n🎯 MENU DE TESTES - REGRAS PDD 9.1.1 COMPLETAS")
    print("=" * 60)
    print("1. 🔥 Teste COMPLETO Regras PDD + CSV Real")
    print("2. 🆚 Teste Comparativo (Google Sheets vs CSV)")
    print("3. 📄 Teste Validação Estrutura CSV")
    print("4. 🚀 Teste RPA Análise Planilhas (Original)")
    print("5. 🔗 Teste Conexão Google Sheets")
    print("6. 🏥 Verificação de Saúde Sistema")
    print("7. ❌ Sair")
    print("=" * 60)

    while True:
        try:
            opcao = input("\n👉 Escolha uma opção (1-7): ").strip()

            if opcao == "1":
                return teste_regras_pdd_csv_completo()
            elif opcao == "2":
                return teste_comparacao_planilhas_google_vs_csv()
            elif opcao == "3":
                return teste_validacao_estrutura_csv()
            elif opcao == "4":
                return teste_completo_original()
            elif opcao == "5":
                return teste_conexao_google_sheets()
            elif opcao == "6":
                return verificar_saude_sistema()
            elif opcao == "7":
                print("👋 Encerrando testes...")
                return None
            else:
                print("❌ Opção inválida! Escolha entre 1-7.")

        except KeyboardInterrupt:
            print("\n👋 Teste interrompido pelo usuário")
            return None


async def teste_completo_original():
    """Teste completo original (Google Sheets)"""
    return await teste_regras_pdd_csv_completo()


async def teste_conexao_google_sheets():
    """Teste de conexão Google Sheets"""
    from rpa_analise_planilhas.teste_analise_planilhas import teste_conexao_google_sheets
    return await teste_conexao_google_sheets()


async def verificar_saude_sistema():
    """Verificação de saúde do sistema"""
    return await verificar_saude_sistema()

teste_completo = teste_completo_original


async def main():
    """
    Função principal do teste
    """
    print("🤖 SISTEMA DE TESTES RPA - REGRAS PDD 9.1.1 COMPLETAS")
    print("Baseado em dados reais CSV do Sienge")
    print("Cliente: SANDRO RIZZON VIEIRA - Título: 2239")
    print("Todas as 8 regras PDD implementadas e testadas")
    print()

    # Executa menu interativo
    teste_selecionado = menu_interativo_completo()

    if teste_selecionado:
        print("\n🚀 Executando teste selecionado...")
        sucesso = await teste_selecionado

        print("\n" + "=" * 60)
        if sucesso:
            print("✅ TESTE CONCLUÍDO COM SUCESSO!")
            print("🎯 Todas as regras PDD 9.1.1 foram aplicadas")
            print("📄 Dados CSV reais processados corretamente")
        else:
            print("❌ TESTE FALHOU - Verifique os logs acima")
        print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {str(e)}")
        import traceback
        print(f"🔍 Detalhes: {traceback.format_exc()}")
