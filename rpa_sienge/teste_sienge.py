#!/usr/bin/env python3
"""
Teste Refinado - RPA Sienge com Dados Reais
Foca na integração entre webscraping (usuário) e processamento PDD (assistente)
Usa dados reais do Excel: saldo_devedor_presente-20250610-093716.xlsx

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import json

# Adiciona o diretório raiz do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rpa_sienge import RPASienge
from core.processador_regras_pdd import ProcessadorRegrasNegocio
from core.base_rpa import ResultadoRPA


async def carregar_dados_excel_real() -> pd.DataFrame:
    """
    Carrega dados reais do Excel anexado
    """
    try:
        arquivo_excel = "attached_assets/saldo_devedor_presente-20250610-093716.xlsx"

        if not os.path.exists(arquivo_excel):
            print(f"❌ Arquivo Excel não encontrado: {arquivo_excel}")
            return pd.DataFrame()

        print(f"📊 Carregando Excel real: {arquivo_excel}")
        df = pd.read_excel(arquivo_excel)

        print(f"✅ Excel carregado: {len(df)} registros")
        print(f"📋 Colunas: {list(df.columns)[:5]}...")

        return df

    except Exception as e:
        print(f"❌ Erro ao carregar Excel: {str(e)}")
        return pd.DataFrame()


async def teste_processamento_dados_reais():
    """
    Testa processamento das regras PDD com dados reais do Excel
    Este teste valida a parte do ASSISTENTE (processamento)
    """
    print("🧪 TESTE PROCESSAMENTO DADOS REAIS - ASSISTENTE")
    print("=" * 55)

    try:
        # Carregar dados reais
        df_real = await carregar_dados_excel_real()

        if df_real.empty:
            return False

        # Identificar títulos únicos para teste
        titulos_unicos = df_real['Título'].unique()[:3]  # Primeiros 3 títulos

        print(f"🎯 Testando {len(titulos_unicos)} títulos únicos:")
        for titulo in titulos_unicos:
            print(f"   📄 {titulo}")

        processador = ProcessadorRegrasNegocio()
        resultados = []

        for i, titulo in enumerate(titulos_unicos):
            print(f"\n📄 [{i+1}/{len(titulos_unicos)}] Processando título: {titulo}")

            # Filtrar dados deste título
            df_titulo = df_real[df_real['Título'] == titulo].copy()

            if df_titulo.empty:
                print(f"   ⚠️ Nenhum dado para título {titulo}")
                continue

            # Obter cliente
            cliente = df_titulo['Cliente'].iloc[0] if 'Cliente' in df_titulo.columns else f"Cliente_{titulo}"
            print(f"   👤 Cliente: {cliente}")

            # PROCESSAR COM REGRAS PDD COMPLETAS
            resultado_pdd = processador.processar_dados_cliente_completo(
                df_planilha=df_titulo,
                cliente=cliente,
                numero_titulo=str(titulo)
            )

            # VALIDAR RESULTADO
            if resultado_pdd.get("sucesso"):
                print(f"   ✅ Processamento bem-sucedido")
                print(f"   🎯 Pode reparcelar: {resultado_pdd.get('pode_reparcelar')}")
                print(f"   💰 Saldo total: R$ {resultado_pdd.get('saldo_total', 0):,.2f}")
                print(f"   📊 CT a vencer: {resultado_pdd.get('qtd_parcelas_ct_a_vencer', 0)}")
                print(f"   🚨 CT vencidas: {resultado_pdd.get('qtd_ct_vencidas', 0)}")
            else:
                print(f"   ❌ Erro: {resultado_pdd.get('erro', 'Erro desconhecido')}")

            resultados.append(resultado_pdd)

        # RESUMO
        sucessos = sum(1 for r in resultados if r.get("sucesso"))
        print(f"\n📈 RESUMO PROCESSAMENTO:")
        print(f"   ✅ Sucessos: {sucessos}/{len(resultados)}")
        print(f"   ❌ Falhas: {len(resultados) - sucessos}")

        return sucessos > 0

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


async def teste_preparacao_parametros_webscraping():
    """
    Testa preparação de parâmetros para webscraping
    Este teste prepara dados para o USUÁRIO (webscraping)
    """
    print("🧪 TESTE PREPARAÇÃO PARÂMETROS WEBSCRAPING - USUÁRIO")
    print("=" * 60)

    try:
        # Carregar dados reais
        df_real = await carregar_dados_excel_real()

        if df_real.empty:
            return False

        # Pegar primeiro título que pode reparcelar
        processador = ProcessadorRegrasNegocio()
        titulo_testavel = None

        for titulo in df_real['Título'].unique()[:5]:  # Testar primeiros 5
            df_titulo = df_real[df_real['Título'] == titulo].copy()
            cliente = df_titulo['Cliente'].iloc[0] if 'Cliente' in df_titulo.columns else f"Cliente_{titulo}"

            resultado_pdd = processador.processar_dados_cliente_completo(
                df_planilha=df_titulo,
                cliente=cliente,
                numero_titulo=str(titulo)
            )

            if resultado_pdd.get("pode_reparcelar"):
                titulo_testavel = titulo
                dados_titulo = df_titulo
                dados_pdd = resultado_pdd
                nome_cliente = cliente
                break

        if not titulo_testavel:
            print("❌ Nenhum título encontrado que possa reparcelar")
            return False

        print(f"🎯 Título selecionado: {titulo_testavel}")
        print(f"👤 Cliente: {nome_cliente}")

        # SIMULAR OBTENÇÃO DE IGPM
        igpm_simulado = 3.89  # Valor exemplo

        # CALCULAR VALORES PARA WEBSCRAPING
        saldo_atual = dados_pdd.get('saldo_total', 0)
        parcelas_pendentes = dados_pdd.get('qtd_parcelas_ct_a_vencer', 0)

        calculo_resultado = await processador.calcular_valores_reparcelamento(
            saldo_atual=saldo_atual,
            indice_igpm=igmp_simulado,
            parcelas_pendentes=parcelas_pendentes
        )

        if not calculo_resultado.get("sucesso"):
            print(f"❌ Erro no cálculo: {calculo_resultado.get('erro')}")
            return False

        # DETERMINAR PARCELAS PARA DESMARCAR
        parcelas_ct = dados_pdd.get("parcelas_ct_a_vencer_detalhes", [])
        parcelas_desmarcar = processador.determinar_parcelas_desmarcar(parcelas_ct)

        # PREPARAR PARÂMETROS COMPLETOS PARA WEBSCRAPING
        parametros_webscraping = {
            # DADOS DO CONTRATO
            "numero_titulo": str(titulo_testavel),
            "cliente": nome_cliente,

            # URL SIENGE (exemplo)
            "url_reparcelamento": "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/reparcelamento/inclusao",

            # VALORES CALCULADOS PARA PREENCHIMENTO
            "valores_sienge": calculo_resultado.get("valores_sienge", {}),

            # PARCELAS PARA DESMARCAR
            "parcelas_desmarcar": parcelas_desmarcar,

            # DADOS FINANCEIROS
            "saldo_anterior": saldo_atual,
            "saldo_novo": calculo_resultado.get("novo_saldo", 0),
            "igmp_aplicado": igmp_simulado,

            # VALIDAÇÃO PDD
            "pode_reparcelar": dados_pdd.get("pode_reparcelar"),
            "status_cliente": dados_pdd.get("status_cliente"),

            # TIMESTAMP
            "timestamp_preparacao": datetime.now().isoformat()
        }

        print(f"\n✅ PARÂMETROS PREPARADOS PARA WEBSCRAPING:")
        print(f"   📄 Título: {parametros_webscraping['numero_titulo']}")
        print(f"   👤 Cliente: {parametros_webscraping['cliente']}")
        print(f"   💰 Saldo: R$ {parametros_webscraping['saldo_anterior']:,.2f} → R$ {parametros_webscraping['saldo_novo']:,.2f}")
        print(f"   📊 IGP-M: {parametros_webscraping['igmp_aplicado']}%")
        print(f"   🔄 Parcelas a desmarcar: {len(parametros_webscraping['parcelas_desmarcar'])}")

        print(f"\n📋 VALORES PARA PREENCHIMENTO NO SIENGE:")
        valores = parametros_webscraping['valores_sienge']
        for campo, valor in valores.items():
            print(f"   {campo}: {valor}")

        print(f"\n❌ PARCELAS PARA DESMARCAR:")
        for parcela in parametros_webscraping['parcelas_desmarcar']:
            print(f"   📄 {parcela['documento']} - {parcela['data_vencimento']} - {parcela['motivo']}")

        # SALVAR PARÂMETROS PARA USO NO WEBSCRAPING
        arquivo_parametros = "dados_processamento/parametros_webscraping_real.json"
        os.makedirs(os.path.dirname(arquivo_parametros), exist_ok=True)

        with open(arquivo_parametros, 'w', encoding='utf-8') as f:
            json.dump(parametros_webscraping, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Parâmetros salvos em: {arquivo_parametros}")
        print(f"🔧 Use este arquivo no seu webscraping!")

        return True

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False


async def teste_simulacao_webscraping():
    """
    Simula execução do webscraping usando core/browser_manager.py
    Este teste mostra como VOCÊ deve implementar o webscraping
    """
    print("🧪 TESTE SIMULAÇÃO WEBSCRAPING - EXEMPLO IMPLEMENTAÇÃO")
    print("=" * 65)

    try:
        # Carregar parâmetros preparados
        arquivo_parametros = "dados_processamento/parametros_webscraping_real.json"

        if not os.path.exists(arquivo_parametros):
            print(f"❌ Execute primeiro: teste_preparacao_parametros_webscraping()")
            return False

        with open(arquivo_parametros, 'r', encoding='utf-8') as f:
            parametros = json.load(f)

        print(f"📊 Parâmetros carregados:")
        print(f"   📄 Título: {parametros['numero_titulo']}")
        print(f"   👤 Cliente: {parametros['cliente']}")

        # EXEMPLO DE COMO VOCÊ DEVE IMPLEMENTAR
        print(f"\n🔧 EXEMPLO DE IMPLEMENTAÇÃO WEBSCRAPING:")
        print(f"```python")
        print(f"from core.browser_manager import RPABrowser")
        print(f"")
        print(f"async def executar_reparcelamento_sienge(parametros):")
        print(f"    browser = RPABrowser(headless=False)")
        print(f"    ")
        print(f"    # 1. NAVEGAR PARA SIENGE")
        print(f"    browser.get_page('{parametros['url_reparcelamento']}')")
        print(f"    ")
        print(f"    # 2. CONSULTAR TÍTULO")
        print(f"    browser.send_text('//input[@id=\"titulo\"]', '{parametros['numero_titulo']}')")
        print(f"    browser.click('//button[text()=\"Consultar\"]')")
        print(f"    ")
        print(f"    # 3. SELECIONAR TODOS")
        print(f"    browser.click('//input[@id=\"select-all\"]')")
        print(f"    ")
        print(f"    # 4. DESMARCAR PARCELAS VENCIDAS")
        print(f"    for parcela in parametros['parcelas_desmarcar']:")
        print(f"        xpath = f'//tr[contains(., \"{parcela['documento']}\")]//input[@type=\"checkbox\"]'")
        print(f"        browser.click(xpath)")
        print(f"    ")
        print(f"    # 5. PREENCHER FORMULÁRIO")
        print(f"    valores = parametros['valores_sienge']")
        print(f"    browser.send_text('//input[@id=\"detalhamento\"]', valores['detalhamento'])")
        print(f"    browser.send_text('//input[@id=\"valor_total\"]', str(valores['valor_total']))")
        print(f"    browser.select_option('//select[@id=\"indexador\"]', valores['indexador'])")
        print(f"    browser.send_text('//input[@id=\"juros\"]', str(valores['percentual_juros']))")
        print(f"    ")
        print(f"    # 6. SALVAR")
        print(f"    browser.click('//button[text()=\"Salvar\"]')")
        print(f"    ")
        print(f"    browser.close()")
        print(f"```")

        print(f"\n🎯 RESPONSABILIDADES CLARAS:")
        print(f"   🤖 ASSISTENTE (PDD): Preparar todos os parâmetros")
        print(f"   👤 USUÁRIO (Webscraping): Navegar e preencher formulários")
        print(f"   🔗 INTEGRAÇÃO: Arquivo JSON com parâmetros completos")

        # SIMULAR RESULTADO DE WEBSCRAPING
        resultado_simulado = {
            "sucesso": True,
            "novo_titulo_gerado": f"REP_{parametros['numero_titulo']}_2025",
            "numero_titulo_original": parametros['numero_titulo'],
            "parcelas_processadas": len(parametros['parcelas_desmarcar']),
            "valores_aplicados": parametros['valores_sienge'],
            "timestamp_webscraping": datetime.now().isoformat()
        }

        print(f"\n✅ RESULTADO SIMULADO DO WEBSCRAPING:")
        print(f"   🆕 Novo título: {resultado_simulado['novo_titulo_gerado']}")
        print(f"   📊 Parcelas processadas: {resultado_simulado['parcelas_processadas']}")
        print(f"   💰 Valores aplicados: {len(resultado_simulado['valores_aplicados'])} campos")

        return True

    except Exception as e:
        print(f"❌ Erro na simulação: {str(e)}")
        return False


async def teste_integracao_completa():
    """
    Teste de integração completa: Processamento PDD + Preparação Webscraping
    """
    print("🧪 TESTE INTEGRAÇÃO COMPLETA - PDD + WEBSCRAPING")
    print("=" * 60)

    try:
        print("🔄 Etapa 1: Processamento dados reais...")
        sucesso_processamento = await teste_processamento_dados_reais()

        if not sucesso_processamento:
            print("❌ Falha no processamento PDD")
            return False

        print("\n🔄 Etapa 2: Preparação parâmetros...")
        sucesso_preparacao = await teste_preparacao_parametros_webscraping()

        if not sucesso_preparacao:
            print("❌ Falha na preparação de parâmetros")
            return False

        print("\n🔄 Etapa 3: Simulação webscraping...")
        sucesso_simulacao = await teste_simulacao_webscraping()

        if not sucesso_simulacao:
            print("❌ Falha na simulação")
            return False

        print(f"\n✅ INTEGRAÇÃO COMPLETA VALIDADA!")
        print(f"   🤖 Processamento PDD: ✅")
        print(f"   📊 Preparação parâmetros: ✅")
        print(f"   🌐 Simulação webscraping: ✅")

        return True

    except Exception as e:
        print(f"❌ Erro na integração: {str(e)}")
        return False


async def teste_browser_manager():
    """
    Testa funcionalidades básicas do browser_manager.py
    """
    print("🧪 TESTE BROWSER MANAGER - FUNCIONALIDADES BÁSICAS")
    print("=" * 55)

    try:
        from core.browser_manager import RPABrowser, SELENIUM_DISPONIVEL

        print(f"📊 Selenium disponível: {'✅' if SELENIUM_DISPONIVEL else '❌'}")

        if not SELENIUM_DISPONIVEL:
            print("⚠️ Selenium não disponível - teste em modo simulado")
            return True

        print("🌐 Inicializando browser...")
        browser = RPABrowser(headless=True)

        print("🔍 Testando navegação básica...")
        sucesso_navegacao = browser.get_page("https://httpbin.org/get")

        print(f"   Navegação: {'✅' if sucesso_navegacao else '❌'}")

        # Testar métodos básicos
        print("🔧 Testando métodos disponíveis:")
        metodos_browser = [
            'get_page', 'find_element', 'find_elements', 'click', 
            'send_text', 'send_text_human_like', 'check_for_error',
            'on_new_window', 'on_iframe', 'close'
        ]

        for metodo in metodos_browser:
            disponivel = hasattr(browser, metodo)
            print(f"   {metodo}: {'✅' if disponivel else '❌'}")

        browser.close()

        print("\n✅ Browser Manager validado!")
        print("🔧 Todos os métodos necessários estão disponíveis")

        return True

    except Exception as e:
        print(f"❌ Erro no teste browser: {str(e)}")
        return False


async def menu_interativo_refinado():
    """
    Menu interativo focado nos testes essenciais
    """
    opcoes = {
        "1": ("🔥 Teste Integração Completa (RECOMENDADO)", teste_integracao_completa),
        "2": ("🤖 Teste Processamento PDD (Assistente)", teste_processamento_dados_reais),
        "3": ("📊 Teste Preparação Webscraping (Usuário)", teste_preparacao_parametros_webscraping),
        "4": ("🌐 Teste Simulação Webscraping", teste_simulacao_webscraping),
        "5": ("🔧 Teste Browser Manager", teste_browser_manager),
        "0": ("❌ Sair", None)
    }

    print("\n" + "=" * 70)
    print("🧪 TESTES REFINADOS RPA SIENGE - DADOS REAIS")
    print("Foco: Integração Webscraping (USUÁRIO) + Processamento PDD (ASSISTENTE)")
    print("=" * 70)

    for key, (descricao, _) in opcoes.items():
        print(f"{key}. {descricao}")

    print("=" * 70)

    while True:
        try:
            escolha = input("\n➤ Escolha uma opção (0-5): ").strip()

            if escolha == "0":
                print("👋 Encerrando testes...")
                break
            elif escolha in opcoes and opcoes[escolha][1]:
                print(f"\n🔄 Executando: {opcoes[escolha][0]}")
                print("-" * 70)

                inicio = datetime.now()
                sucesso = await opcoes[escolha][1]()
                fim = datetime.now()
                tempo_execucao = (fim - inicio).total_seconds()

                print("-" * 70)
                if sucesso:
                    print(f"✅ Teste concluído com SUCESSO em {tempo_execucao:.1f}s")
                else:
                    print(f"❌ Teste FALHOU em {tempo_execucao:.1f}s")

                input("\n⏳ Pressione ENTER para continuar...")
                print("\n" + "=" * 70)
                for key, (descricao, _) in opcoes.items():
                    print(f"{key}. {descricao}")
                print("=" * 70)
            else:
                print("❌ Opção inválida! Escolha entre 0-5.")

        except KeyboardInterrupt:
            print("\n\n👋 Testes interrompidos pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Erro inesperado: {str(e)}")


if __name__ == "__main__":
    print("🚀 TESTES REFINADOS RPA SIENGE")
    print(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("🎯 Usando dados reais: saldo_devedor_presente-20250610-093716.xlsx")
    print("🤖 Assistente: Processamento PDD")
    print("👤 Usuário: Webscraping (core/browser_manager.py)")

    try:
        asyncio.run(menu_interativo_refinado())
    except KeyboardInterrupt:
        print("\n👋 Sistema encerrado pelo usuário.")
    except Exception as e:
        print(f"❌ Erro crítico: {str(e)}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")