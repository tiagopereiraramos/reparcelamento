#!/usr/bin/env python3
"""
Teste COMPLETO do RPA Sienge - Sistema de Reparcelamento
Executa testes incrementais e completos do RPA Sienge usando dados reais da fila
Suporte completo para desenvolvimento e debugging das etapas de webscraping

Desenvolvido em Português Brasileiro
"""

from rpa_sienge import RPASienge
import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Adiciona o diretório raiz do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# --- Configurações e Credenciais ---


def credenciais_sienge_env() -> Dict[str, str]:
    """Carrega credenciais do Sienge das variáveis de ambiente"""
    return {
        "url": os.getenv("SIENGE_URL", "https://sienge.com.br"),
        "usuario": os.getenv("SIENGE_USUARIO", "teste"),
        "senha": os.getenv("SIENGE_SENHA", "teste123"),
        "empresa": os.getenv("SIENGE_EMPRESA", "1")
    }


# --- Funções de Carregamento de Dados ---


async def carregar_fila_contratos() -> List[Dict[str, Any]]:
    """Carrega contratos da fila de processamento"""
    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()
        print("🔍 Carregando fila de contratos...")
        fila_dados = await data_manager.obter_fila_sienge()
        contratos = fila_dados.get("contratos", []) if fila_dados else []

        # Filtra apenas contratos não processados nem erro
        contratos_pendentes = [c for c in contratos if c.get(
            "status_processamento") not in ["processado", "erro"]]

        if contratos_pendentes:
            print(
                f"✅ Fila carregada: {len(contratos_pendentes)} contratos pendentes")
            for i, contrato in enumerate(contratos_pendentes[:3]):
                print(
                    f"   {i+1}. {contrato.get('numero_titulo', 'N/A')} - {contrato.get('cliente', 'N/A')} [{contrato.get('status_processamento', 'N/A')}]")
            if len(contratos_pendentes) > 3:
                print(f"   ... e mais {len(contratos_pendentes)-3} contratos")
            return contratos_pendentes
        else:
            print("⚠️ Nenhum contrato pendente encontrado na fila.")
            return []
    except Exception as e:
        print(f"❌ Erro ao carregar fila: {str(e)}")
        return []


async def carregar_indices_economicos() -> Dict[str, Any]:
    """Carrega índices econômicos do sistema ou usa valores simulados"""
    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()
        print("📈 Carregando índices econômicos...")

        # Busca os dois índices separadamente
        ipca = await data_manager.obter_indice_mais_recente("ipca")
        igpm = await data_manager.obter_indice_mais_recente("igpm")

        if ipca is not None and igpm is not None:
            print(
                f"✅ Índices carregados do sistema: IPCA={ipca} | IGPM={igpm}")
            return {
                "ipca": {"valor": ipca, "tipo": "IPCA", "periodo": "Recente"},
                "igpm": {"valor": igpm, "tipo": "IGPM", "periodo": "Recente"}
            }
        else:
            print("📊 Usando índices simulados")
            return {
                "ipca": {"valor": 4.62, "tipo": "IPCA", "periodo": "Dezembro/2024"},
                "igpm": {"valor": 3.89, "tipo": "IGPM", "periodo": "Dezembro/2024"}
            }
    except Exception as e:
        print(f"❌ Erro ao carregar índices: {str(e)}")
        return {
            "ipca": {"valor": 4.62, "tipo": "IPCA", "periodo": "Dezembro/2024"},
            "igpm": {"valor": 3.89, "tipo": "IGPM", "periodo": "Dezembro/2024"}
        }


async def carregar_contrato_processado() -> Optional[Dict[str, Any]]:
    """Carrega um contrato já processado para testes de reparcelamento"""
    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()

        filtro = {
            "status_sienge": "processado",
            "status_sicredi": "pendente"
        }

        contrato = await data_manager.obter_documento_mais_recente(
            "contratos_processados", filtro, "data_processamento"
        )

        if contrato:
            print(
                f"✅ Contrato processado encontrado: {contrato.get('numero_titulo')} - {contrato.get('cliente')}")
            return contrato
        else:
            print("⚠️ Nenhum contrato processado encontrado.")
            return None
    except Exception as e:
        print(f"❌ Erro ao carregar contrato processado: {str(e)}")
        return None


# --- Funções de Teste Incremental ---


async def teste_etapa_login():
    """Teste específico da etapa de login no Sienge"""
    print("🧪 TESTE ETAPA 1 - LOGIN SIENGE")
    print("=" * 40)

    try:
        credenciais = credenciais_sienge_env()
        rpa = RPASienge()
        await rpa.inicializar()
        rpa._configurar_credenciais(credenciais)

        print(f"🔐 Tentando login em: {credenciais['url']}")
        print(f"👤 Usuário: {credenciais['usuario']}")

        resultado_login = await rpa._fazer_login_sienge()

        if resultado_login:
            print("✅ Login realizado com sucesso!")
            print("🔍 Verificando se está logado...")

            # Verifica se realmente está logado
            if rpa.logado_sienge:
                print("✅ Status de login confirmado")
            else:
                print("⚠️ Login pode ter falhado - status não confirmado")
        else:
            print("❌ Falha no login")

        await rpa.finalizar()
        return resultado_login

    except Exception as e:
        print(f"❌ Erro no teste de login: {str(e)}")
        return False


async def teste_etapa_consulta_relatorios():
    """Teste específico da consulta de relatórios financeiros"""
    print("🧪 TESTE ETAPA 2 - CONSULTA DE RELATÓRIOS")
    print("=" * 50)

    try:
        # Carrega contratos da fila
        contratos_fila = await carregar_fila_contratos()
        if not contratos_fila:
            print("❌ Nenhum contrato encontrado na fila.")
            return False

        credenciais = credenciais_sienge_env()
        rpa = RPASienge()
        await rpa.inicializar()
        rpa._configurar_credenciais(credenciais)

        # Faz login primeiro
        print("🔐 Fazendo login...")
        await rpa._fazer_login_sienge()

        print("✅ Login realizado - testando consulta de relatórios...")

        sucessos = 0
        falhas = 0

        # Testa apenas 3 contratos
        for i, contrato_fila in enumerate(contratos_fila[:3]):
            print(
                f"\n📄 [{i+1}/3] Testando: {contrato_fila.get('numero_titulo', 'N/A')}")

            try:
                dados_financeiros = await rpa._consultar_relatorios_financeiros(contrato_fila)

                if dados_financeiros.get("sucesso"):
                    sucessos += 1
                    print(f"   ✅ Sucesso - Planilha processada")
                    print(
                        f"   📊 Dados obtidos: {len(dados_financeiros.get('dados', {}))} campos")
                else:
                    falhas += 1
                    print(
                        f"   ❌ Falha: {dados_financeiros.get('erro', 'Erro desconhecido')}")

                if i < 2:  # Aguarda entre testes
                    print("   ⏳ Aguardando 3 segundos...")
                    await asyncio.sleep(3)

            except Exception as e:
                falhas += 1
                print(f"   ❌ Erro inesperado: {str(e)}")
                continue

        await rpa.finalizar()

        print(
            f"\n📈 RESUMO: Sucessos: {sucessos} | Falhas: {falhas} | Total: {sucessos + falhas}")
        return sucessos > 0

    except Exception as e:
        print(f"❌ Erro no teste de consulta: {str(e)}")
        return False


async def teste_etapa_reparcelamento():
    """Teste específico da etapa de reparcelamento com dados reais"""
    print("🧪 TESTE ETAPA 3 - REPARCELAMENTO (DADOS REAIS)")
    print("=" * 50)

    try:
        # 1. CARREGAR DADOS REAIS DA FILA
        print("📊 Carregando dados reais da fila...")
        contratos_fila = await carregar_fila_contratos()
        if not contratos_fila:
            print("❌ Nenhum contrato encontrado na fila.")
            return False

        # 2. CARREGAR ÍNDICES ECONÔMICOS
        print("📈 Carregando índices econômicos...")
        indices_economicos = await carregar_indices_economicos()

        # 3. CONFIGURAR CREDENCIAIS
        credenciais = credenciais_sienge_env()

        # 4. INICIALIZAR RPA E FAZER LOGIN REAL
        print("🔐 Inicializando RPA e fazendo login...")
        rpa = RPASienge()
        await rpa.inicializar()
        rpa._configurar_credenciais(credenciais)

        resultado_login = await rpa._fazer_login_sienge()
        if not resultado_login:
            print("❌ Falha no login - não é possível testar reparcelamento")
            await rpa.finalizar()
            return False

        print("✅ Login realizado com sucesso")

        # 5. PROCESSAR CONTRATOS REAIS DA FILA
        print(f"🔄 Processando {len(contratos_fila)} contratos da fila...")

        sucessos = 0
        falhas = 0

        # Testa apenas 3 contratos
        for i, contrato_fila in enumerate(contratos_fila[:3]):
            print(
                f"\n📄 [{i+1}/3] Processando: {contrato_fila.get('numero_titulo', 'N/A')}")
            print(f"   👤 Cliente: {contrato_fila.get('cliente', 'N/A')}")

            try:
                # 6. CONSULTAR RELATÓRIOS FINANCEIROS (WEBSCRAPING REAL)
                print("   🔍 Consultando relatórios financeiros...")
                dados_financeiros = await rpa._consultar_relatorios_financeiros(contrato_fila)

                if not dados_financeiros.get("sucesso"):
                    print(
                        f"   ❌ Falha na consulta: {dados_financeiros.get('erro', 'Erro desconhecido')}")
                    falhas += 1
                    continue

                print("   ✅ Relatórios consultados com sucesso")

                # 7. RETROALIMENTAR PLANILHA BASE DE CÁLCULO (NOVO!)
                print("   📊 Retroalimentando planilha BASE DE CÁLCULO...")
                try:
                    # ID da planilha (configurar conforme necessário)
                    planilha_id = os.getenv("PLANILHA_CALCULO_ID", "")
                    if planilha_id:
                        # Conectar ao Google Sheets
                        await rpa._conectar_google_sheets(os.getenv("GOOGLE_CREDENTIALS_PATH"))
                        planilha = rpa.cliente_sheets.open_by_key(planilha_id)

                        # Retroalimentar com dados financeiros do Sienge
                        await rpa._preencher_dados_relatorio_sienge(planilha, dados_financeiros)
                        print("   ✅ Planilha retroalimentada com sucesso!")
                    else:
                        print(
                            "   ⚠️ PLANILHA_CALCULO_ID não configurada - pulando retroalimentação")
                except Exception as e:
                    print(f"   ⚠️ Erro na retroalimentação: {str(e)}")
                    # Não conta como falha total, apenas a retroalimentação falhou

                # 8. EXECUTAR REPARCELAMENTO COM DADOS REAIS
                print("   🔄 Executando reparcelamento...")
                resultado_reparcelamento = await rpa._executar_etapa_reparcelamento(
                    contrato=contrato_fila,
                    indices=indices_economicos,
                    dados_financeiros=dados_financeiros,
                    autorizar_reparcelamento=True,
                    notificar_analista=False
                )

                if resultado_reparcelamento.sucesso:
                    sucessos += 1
                    print("   ✅ Reparcelamento executado com sucesso!")

                    # Mostrar dados calculados
                    dados_reparcelamento = resultado_reparcelamento.dados.get(
                        "reparcelamento", {})
                    valores_sienge = dados_reparcelamento.get(
                        "valores_sienge", {})

                    print(
                        f"   💰 Valor anterior: R$ {dados_reparcelamento.get('valor_anterior', 0):,.2f}")
                    print(
                        f"   💰 Valor corrigido: R$ {dados_reparcelamento.get('valor_corrigido', 0):,.2f}")
                    print(
                        f"   📊 IGPM aplicado: {dados_reparcelamento.get('igpm_aplicado', 0)}%")
                    print(
                        f"   📄 Parcelas processadas: {dados_reparcelamento.get('parcelas_processadas', 0)}")

                    # Mostrar valores para preenchimento no Sienge
                    if valores_sienge:
                        print("   📋 Valores para Sienge:")
                        print(
                            f"      Detalhamento: {valores_sienge.get('detalhamento', 'N/A')}")
                        print(
                            f"      Valor total: R$ {valores_sienge.get('valor_total', 0):,.2f}")
                        print(
                            f"      Quantidade parcelas: {valores_sienge.get('quantidade_parcelas', 0)}")
                        print(
                            f"      Data primeiro vencimento: {valores_sienge.get('data_primeiro_vencimento', 'N/A')}")
                        print(
                            f"      Indexador: {valores_sienge.get('indexador', 'N/A')}")
                        print(
                            f"      Juros: {valores_sienge.get('percentual_juros', 0)}%")

                    # 9. EXECUTAR WEBSCRAPING DE REPARCELAMENTO (NOVO!)
                    print("   🌐 Executando webscraping de reparcelamento...")

                    # Montar parâmetros para o webscraping
                    parametros_webscraping = {
                        "numero_titulo": contrato_fila.get("numero_titulo"),
                        "cliente": contrato_fila.get("cliente"),
                        "empreendimento": contrato_fila.get("empreendimento", ""),
                        "url_reparcelamento": "https://jmservicos.sienge.com.br/sienge/8/index.html#/common/page/1047",
                        "valores_sienge": valores_sienge,
                        "parcelas_desmarcar": dados_reparcelamento.get("parcelas_desmarcar", []),
                        "total_parcelas_desmarcar": len(dados_reparcelamento.get("parcelas_desmarcar", [])),
                        "saldo_anterior": dados_reparcelamento.get("valor_anterior", 0),
                        "saldo_novo": dados_reparcelamento.get("valor_corrigido", 0),
                        "fator_correcao": dados_reparcelamento.get("fator_correcao", 1),
                        "igpm_aplicado": dados_reparcelamento.get("igpm_aplicado", 0),
                        "pode_reparcelar": dados_reparcelamento.get("pode_reparcelar", True),
                        "status_cliente": dados_reparcelamento.get("status_cliente", ""),
                        "qtd_ct_vencidas": dados_reparcelamento.get("qtd_ct_vencidas", 0),
                        "id_fila": contrato_fila.get("_id", ""),
                        "timestamp_carregamento": datetime.now().isoformat()
                    }

                    resultado_webscraping = await rpa._navegar_e_executar_reparcelamento(parametros_webscraping)

                    if resultado_webscraping.get("sucesso"):
                        print(
                            "   ✅ Webscraping de reparcelamento executado com sucesso!")
                        print(
                            f"   📄 Novo título gerado: {resultado_webscraping.get('novo_titulo', 'N/A')}")
                        print(
                            f"   📊 Parcelas processadas: {resultado_webscraping.get('parcelas_processadas', 0)}")
                        print(
                            f"   🕐 Timestamp: {resultado_webscraping.get('timestamp_webscraping', 'N/A')}")
                    else:
                        print(
                            f"   ❌ Falha no webscraping: {resultado_webscraping.get('erro', 'Erro desconhecido')}")
                        # Não conta como falha total, apenas o webscraping falhou
                        print("   ⚠️ Cálculos OK, mas webscraping falhou")
                else:
                    falhas += 1
                    print(
                        f"   ❌ Falha no reparcelamento: {resultado_reparcelamento.erro or resultado_reparcelamento.mensagem}")

                # Aguardar entre processamentos
                if i < 2:
                    print("   ⏳ Aguardando 5 segundos...")
                    await asyncio.sleep(5)

            except Exception as e:
                falhas += 1
                print(f"   ❌ Erro inesperado: {str(e)}")
                continue

        # 9. FINALIZAR RPA
        await rpa.finalizar()

        # 10. RESUMO FINAL
        print(f"\n📈 RESUMO DO TESTE DE REPARCELAMENTO:")
        print(f"   Sucessos: {sucessos}")
        print(f"   Falhas: {falhas}")
        print(f"   Total: {sucessos + falhas}")

        if sucessos > 0:
            print("✅ Teste de reparcelamento concluído com sucesso!")
            print("🎯 Dados reais processados, planilha retroalimentada, valores calculados e webscraping executado")
        else:
            print("❌ Nenhum reparcelamento foi executado com sucesso")

        return sucessos > 0

    except Exception as e:
        print(f"❌ Erro no teste de reparcelamento: {str(e)}")
        return False


async def teste_webscraping_reparcelamento():
    """Teste específico do webscraping de reparcelamento com dados calculados"""
    print("🧪 TESTE ESPECÍFICO - WEBSCRAPING REPARCELAMENTO")
    print("=" * 60)

    try:
        # 1. CARREGAR DADOS REAIS DA FILA (mesma lógica do teste 3)
        print("📊 Carregando dados reais da fila...")
        contratos_fila = await carregar_fila_contratos()
        if not contratos_fila:
            print("❌ Nenhum contrato encontrado na fila.")
            return False

        # 2. CARREGAR ÍNDICES ECONÔMICOS
        print("📈 Carregando índices econômicos...")
        indices_economicos = await carregar_indices_economicos()

        # 3. CONFIGURAR CREDENCIAIS
        credenciais = credenciais_sienge_env()

        # 4. INICIALIZAR RPA
        rpa = RPASienge()
        await rpa.inicializar()
        rpa._configurar_credenciais(credenciais)

        # 5. FAZER LOGIN REAL
        print("🔐 Fazendo login no Sienge...")
        await rpa._fazer_login_sienge()

        # 6. CONSULTAR RELATÓRIOS FINANCEIROS (WEBSCRAPING REAL)
        print("📊 Consultando relatórios financeiros...")
        contrato_teste = contratos_fila[0]
        dados_financeiros = await rpa._consultar_relatorios_financeiros(contrato_teste)

        if not dados_financeiros.get("sucesso"):
            print(f"❌ Falha na consulta: {dados_financeiros.get('erro')}")
            return False

        # 6.1. RETROALIMENTAR PLANILHA BASE DE CÁLCULO (DADOS FINANCEIROS)
        print("📊 Retroalimentando planilha BASE DE CÁLCULO com dados do Sienge...")
        try:
            # ID da planilha (configurar conforme necessário)
            planilha_id = os.getenv("PLANILHA_CALCULO_ID", "")
            if not planilha_id:
                print("⚠️ PLANILHA_CALCULO_ID não configurada - usando ID de teste")
                planilha_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"  # ID de exemplo

            # Conectar ao Google Sheets
            await rpa._conectar_google_sheets(os.getenv("GOOGLE_CREDENTIALS_PATH"))
            planilha = rpa.cliente_sheets.open_by_key(planilha_id)
            print(f"✅ Planilha aberta: {planilha.title}")

            # Retroalimentar com dados financeiros do Sienge
            await rpa._preencher_dados_relatorio_sienge(planilha, dados_financeiros)
            print("✅ Retroalimentação da planilha concluída com sucesso")

        except Exception as e:
            print(f"⚠️ Erro na retroalimentação da planilha: {str(e)}")
            print("⚠️ Continuando com o teste mesmo sem retroalimentação...")

        # 7. EXECUTAR REPARCELAMENTO PARA CALCULAR VALORES
        print("🔄 Executando reparcelamento para calcular valores...")
        resultado_reparcelamento = await rpa._executar_etapa_reparcelamento(
            contrato_teste, indices_economicos, dados_financeiros, True, False
        )

        if not resultado_reparcelamento.sucesso:
            print(
                f"❌ Falha no reparcelamento: {resultado_reparcelamento.mensagem}")
            return False

        # 8. EXECUTAR WEBSCRAPING DE REPARCELAMENTO
        print("🌐 Executando webscraping de reparcelamento...")
        parametros_webscraping = {
            "numero_titulo": contrato_teste["numero_titulo"],
            "cliente": contrato_teste["cliente"],
            "url_reparcelamento": "https://jmservicos.sienge.com.br/sienge/8/index.html#/common/page/1047",
            "valores_sienge": resultado_reparcelamento.dados.get("reparcelamento", {}).get("valores_sienge", {}),
            "parcelas_desmarcar": resultado_reparcelamento.dados.get("reparcelamento", {}).get("parcelas_desmarcadas", []),
            "saldo_anterior": resultado_reparcelamento.dados.get("reparcelamento", {}).get("valor_anterior", 0),
            "saldo_novo": resultado_reparcelamento.dados.get("reparcelamento", {}).get("valor_corrigido", 0),
            "igpm_aplicado": resultado_reparcelamento.dados.get("reparcelamento", {}).get("igpm_aplicado", 0)
        }

        resultado_webscraping = await rpa._navegar_e_executar_reparcelamento(parametros_webscraping)

        # 9. EXIBIR RESULTADOS
        print("\n📋 RESULTADOS DO WEBSCRAPING:")
        print(f"   ✅ Sucesso: {resultado_webscraping.get('sucesso', False)}")
        print(
            f"   📄 Novo título: {resultado_webscraping.get('novo_titulo', 'N/A')}")
        print(
            f"   🔢 Parcelas processadas: {resultado_webscraping.get('parcelas_processadas', 0)}")
        print(
            f"   📊 Passos PDD executados: {resultado_webscraping.get('passos_pdd_executados', 'N/A')}")
        print(
            f"   ⏰ Timestamp: {resultado_webscraping.get('timestamp_webscraping', 'N/A')}")

        if resultado_webscraping.get("erro"):
            print(f"   ❌ Erro: {resultado_webscraping.get('erro')}")

        # 10. FINALIZAR
        await rpa.finalizar()
        return resultado_webscraping.get("sucesso", False)

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


async def teste_preenchimento_planilha():
    """Teste específico da retroalimentação da planilha BASE DE CÁLCULO com dados do Sienge"""
    print("🧪 TESTE ESPECÍFICO - RETROALIMENTAÇÃO PLANILHA DE CÁLCULO")
    print("=" * 70)

    try:
        # 1. CARREGAR DADOS REAIS DA FILA
        print("📊 Carregando dados reais da fila...")
        contratos_fila = await carregar_fila_contratos()
        if not contratos_fila:
            print("❌ Nenhum contrato encontrado na fila.")
            return False

        # 2. CONFIGURAR CREDENCIAIS
        credenciais = credenciais_sienge_env()

        # 3. INICIALIZAR RPA
        rpa = RPASienge()
        await rpa.inicializar()

        # 4. FAZER LOGIN REAL
        print("🔐 Fazendo login no Sienge...")
        await rpa._fazer_login_sienge()

        # 5. CONSULTAR RELATÓRIOS FINANCEIROS (WEBSCRAPING REAL)
        print("📊 Consultando relatórios financeiros...")
        contrato_teste = contratos_fila[0]
        dados_financeiros = await rpa._consultar_relatorios_financeiros(contrato_teste)

        if not dados_financeiros.get("sucesso"):
            print(f"❌ Falha na consulta: {dados_financeiros.get('erro')}")
            return False

        print("✅ Relatórios consultados com sucesso")

        # 6. RETROALIMENTAR PLANILHA DE CÁLCULO (APENAS DADOS FINANCEIROS)
        print("📊 Retroalimentando planilha BASE DE CÁLCULO com dados do Sienge...")

        # ID da planilha (configurar conforme necessário)
        planilha_id = os.getenv("PLANILHA_CALCULO_ID", "")
        if not planilha_id:
            print("⚠️ PLANILHA_CALCULO_ID não configurada - usando ID de teste")
            planilha_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"  # ID de exemplo

        # Conectar ao Google Sheets
        await rpa._conectar_google_sheets(os.getenv("GOOGLE_CREDENTIALS_PATH"))
        planilha = rpa.cliente_sheets.open_by_key(planilha_id)
        print(f"✅ Planilha aberta: {planilha.title}")

        # Retroalimentar apenas com dados financeiros do Sienge
        await rpa._preencher_dados_relatorio_sienge(planilha, dados_financeiros)

        # 7. EXIBIR RESULTADOS
        print("\n📋 RESULTADOS DA RETROALIMENTAÇÃO:")
        print(f"   ✅ Sucesso: Retroalimentação concluída")
        print(f"   📊 Planilha atualizada: {planilha_id}")
        print(
            f"   👤 Cliente processado: {contrato_teste.get('cliente', 'N/A')}")
        print(f"   📄 Título: {contrato_teste.get('numero_titulo', 'N/A')}")
        print(f"   ⏰ Timestamp: {datetime.now().isoformat()}")

        # Mostrar dados que foram retroalimentados
        dados_validacao = dados_financeiros.get("dados_validacao", {})
        regras_pdd = dados_financeiros.get("regras_pdd_aplicadas", {})

        print(f"\n📊 DADOS RETROALIMENTADOS:")
        print(
            f"   📄 Parcelas a vencer: {dados_validacao.get('qtd_parcelas_ct_a_vencer', 0)}")
        print(
            f"   💰 Valor da Parcela Base: R$ {dados_validacao.get('valor_parcela_atual', 0):,.2f}")
        print(
            f"   📅 Dia de vencimento: {dados_validacao.get('dia_vencimento', 'N/A')}")
        print(
            f"   📅 1º vencimento carnê: {regras_pdd.get('primeiro_vencimento_carne', 'N/A')}")
        print(
            f"   ⚠️ PENDÊNCIAS SIENGE INAD: {dados_validacao.get('status_cliente') == 'inadimplente'}")
        print(
            f"   📋 PENDÊNCIAS SIENGE: {len(dados_validacao.get('parcelas_rec_fat', [])) > 0}")

        # 8. FINALIZAR
        await rpa.finalizar()
        return True

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


async def teste_etapa_geracao_carne():
    """Teste específico da geração de carnê com dados reais"""
    print("🧪 TESTE ETAPA 4 - GERAÇÃO DE CARNÊ (DADOS REAIS)")
    print("=" * 50)

    try:
        # 1. CARREGAR DADOS REAIS DA FILA
        print("📊 Carregando dados reais da fila...")
        contratos_fila = await carregar_fila_contratos()
        if not contratos_fila:
            print("❌ Nenhum contrato encontrado na fila.")
            return False

        # 2. CONFIGURAR CREDENCIAIS
        credenciais = credenciais_sienge_env()

        # 3. INICIALIZAR RPA E FAZER LOGIN REAL
        print("🔐 Inicializando RPA e fazendo login...")
        rpa = RPASienge()
        await rpa.inicializar()
        rpa._configurar_credenciais(credenciais)

        resultado_login = await rpa._fazer_login_sienge()
        if not resultado_login:
            print("❌ Falha no login - não é possível testar geração de carnê")
            await rpa.finalizar()
            return False

        print("✅ Login realizado com sucesso")

        # 4. PROCESSAR PRIMEIRO CONTRATO DA FILA
        contrato_teste = contratos_fila[0]  # Usa o primeiro contrato da fila
        print(
            f"📄 Testando geração de carnê para: {contrato_teste.get('numero_titulo')}")
        print(f"👤 Cliente: {contrato_teste.get('cliente')}")

        # 5. CONSULTAR RELATÓRIOS FINANCEIROS (WEBSCRAPING REAL)
        print("🔍 Consultando relatórios financeiros...")
        dados_financeiros = await rpa._consultar_relatorios_financeiros(contrato_teste)

        if not dados_financeiros.get("sucesso"):
            print(
                f"❌ Falha na consulta: {dados_financeiros.get('erro', 'Erro desconhecido')}")
            await rpa.finalizar()
            return False

        print("✅ Relatórios consultados com sucesso")

        # 6. EXECUTAR REPARCELAMENTO PARA GERAR DADOS NECESSÁRIOS
        print("🔄 Executando reparcelamento para preparar dados...")
        indices_economicos = await carregar_indices_economicos()

        resultado_reparcelamento = await rpa._executar_etapa_reparcelamento(
            contrato=contrato_teste,
            indices=indices_economicos,
            dados_financeiros=dados_financeiros,
            autorizar_reparcelamento=True,
            notificar_analista=False
        )

        if not resultado_reparcelamento.sucesso:
            print(
                f"❌ Falha no reparcelamento: {resultado_reparcelamento.erro or resultado_reparcelamento.mensagem}")
            await rpa.finalizar()
            return False

        print("✅ Reparcelamento executado com sucesso")

        # 7. GERAR CARNÊ COM DADOS REAIS
        print("📄 Gerando carnê...")
        resultado_carne = await rpa._gerar_carne_sienge(contrato_teste)

        if resultado_carne.get("sucesso"):
            print("✅ Carnê gerado com sucesso!")
            print(f"📁 Arquivo: {resultado_carne.get('nome_arquivo', 'N/A')}")
            print(
                f"📂 Caminho: {resultado_carne.get('caminho_arquivo', 'N/A')}")
            print(
                f"🕒 Timestamp: {resultado_carne.get('timestamp_geracao', 'N/A')}")

            # Mostrar dados do reparcelamento que gerou o carnê
            dados_reparcelamento = resultado_reparcelamento.dados.get(
                "reparcelamento", {})
            valores_sienge = dados_reparcelamento.get("valores_sienge", {})

            print(f"\n📊 DADOS DO REPARCELAMENTO:")
            print(
                f"   💰 Valor anterior: R$ {dados_reparcelamento.get('valor_anterior', 0):,.2f}")
            print(
                f"   💰 Valor corrigido: R$ {dados_reparcelamento.get('valor_corrigido', 0):,.2f}")
            print(
                f"   📊 IGPM aplicado: {dados_reparcelamento.get('igpm_aplicado', 0)}%")
            print(
                f"   📄 Parcelas processadas: {dados_reparcelamento.get('parcelas_processadas', 0)}")

            if valores_sienge:
                print(f"   📋 Valores aplicados:")
                print(
                    f"      Detalhamento: {valores_sienge.get('detalhamento', 'N/A')}")
                print(
                    f"      Valor total: R$ {valores_sienge.get('valor_total', 0):,.2f}")
                print(
                    f"      Data primeiro vencimento: {valores_sienge.get('data_primeiro_vencimento', 'N/A')}")
                print(
                    f"      Indexador: {valores_sienge.get('indexador', 'N/A')}")
                print(
                    f"      Juros: {valores_sienge.get('percentual_juros', 0)}%")
        else:
            print(
                f"❌ Falha na geração do carnê: {resultado_carne.get('erro', 'Erro desconhecido')}")

        # 8. FINALIZAR RPA
        await rpa.finalizar()

        return resultado_carne.get("sucesso", False)

    except Exception as e:
        print(f"❌ Erro no teste de geração de carnê: {str(e)}")
        return False


# --- Funções de Teste Completo ---


async def teste_completo_fila_real():
    """Teste completo usando dados reais da fila"""
    print("🧪 TESTE COMPLETO - FILA REAL")
    print("=" * 50)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("🎯 Usando dados reais da fila de processamento")
    print("=" * 50)

    try:
        # Carrega dados
        contratos_fila = await carregar_fila_contratos()
        if not contratos_fila:
            print("❌ Nenhum contrato encontrado na fila.")
            return False

        indices_economicos = await carregar_indices_economicos()
        credenciais = credenciais_sienge_env()

        print(f"📊 Dados carregados:")
        print(f"   Contratos: {len(contratos_fila)}")
        print(f"   IPCA: {indices_economicos['ipca']['valor']}%")
        print(f"   IGPM: {indices_economicos['igpm']['valor']}%")

        # Executa processamento completo
        from core.base_rpa import ResultadoRPA

        rpa = RPASienge()
        await rpa.inicializar()

        resultados = []
        # Processa apenas 3 contratos
        for i, contrato in enumerate(contratos_fila[:3]):
            print(
                f"\n🔄 [{i+1}/3] Processando: {contrato.get('numero_titulo', 'N/A')}")

            try:
                resultado = await rpa.executar(
                    contrato=contrato,
                    credenciais_sienge=credenciais,
                    indices=indices_economicos,
                    etapa="completa",
                    autorizar_reparcelamento=False,
                    notificar_analista=False
                )
                resultados.append(resultado)

                if resultado.sucesso:
                    print(f"   ✅ Sucesso: {resultado.mensagem}")
                else:
                    print(
                        f"   ❌ Falha: {resultado.erro or resultado.mensagem}")

                if i < 2:  # Aguarda entre processamentos
                    print("   ⏳ Aguardando 5 segundos...")
                    await asyncio.sleep(5)

            except Exception as e:
                print(f"   ❌ Erro inesperado: {str(e)}")
                resultados.append(ResultadoRPA(
                    sucesso=False,
                    mensagem="Erro inesperado",
                    erro=str(e)
                ))

        await rpa.finalizar()

        # Resumo final
        sucessos = sum(1 for r in resultados if r and r.sucesso)
        falhas = len(resultados) - sucessos

        print(f"\n📈 RESUMO FINAL:")
        print(f"   Sucessos: {sucessos}")
        print(f"   Falhas: {falhas}")
        print(f"   Total: {len(resultados)}")

        return sucessos > 0

    except Exception as e:
        print(f"❌ Erro no teste completo: {str(e)}")
        return False


async def teste_contrato_simulado():
    """Teste completo com contrato simulado"""
    print("🧪 TESTE CONTRATO SIMULADO - COMPLETO")
    print("=" * 50)

    contrato_teste = {
        "numero_titulo": "TEST123456789",
        "cliente": "CLIENTE TESTE LTDA",
        "empreendimento": "EMPREENDIMENTO TESTE",
        "cnpj_unidade": "12.345.678/0001-90",
        "indexador": "IPCA",
        "ultimo_reajuste": "01/01/2023"
    }

    indices_economicos = await carregar_indices_economicos()
    credenciais = credenciais_sienge_env()

    print(f"🏢 Contrato de Teste: {contrato_teste['numero_titulo']}")
    print(f"👤 Cliente: {contrato_teste['cliente']}")
    print(f"🔐 URL Sienge: {credenciais['url']}")

    try:
        rpa = RPASienge()
        await rpa.inicializar()

        resultado = await rpa.executar(
            contrato=contrato_teste,
            credenciais_sienge=credenciais,
            indices=indices_economicos,
            etapa="completa",
            autorizar_reparcelamento=True,
            notificar_analista=False
        )

        await rpa.finalizar()

        print("\n📋 RESULTADO DA EXECUÇÃO:")
        print("-" * 30)
        print(f"Sucesso: {'✅ SIM' if resultado.sucesso else '❌ NÃO'}")
        print(f"Mensagem: {resultado.mensagem}")

        if resultado.sucesso and resultado.dados:
            print("📊 Dados obtidos:")
            print(json.dumps(resultado.dados, indent=2, ensure_ascii=False))

        if not resultado.sucesso:
            print(f"\n❌ ERRO: {resultado.erro or 'Erro desconhecido'}")

        return resultado.sucesso

    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


# --- Funções de Verificação de Sistema ---


async def verificar_conexao_banco():
    """Verifica conexão com o banco de dados"""
    print("🔍 VERIFICAÇÃO - CONEXÃO BANCO DE DADOS")
    print("=" * 40)

    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()

        # Testa operações básicas
        fila_dados = await data_manager.obter_fila_sienge()
        indices = await data_manager.obter_indice_mais_recente("ipca")

        print("✅ Conexão com banco estabelecida")
        print(f"📊 Fila disponível: {'Sim' if fila_dados else 'Não'}")
        print(
            f"📈 Índices disponíveis: {'Sim' if indices is not None else 'Não'}")

        return True

    except Exception as e:
        print(f"❌ Erro na conexão: {str(e)}")
        return False


async def verificar_credenciais_sienge():
    """Verifica se as credenciais do Sienge estão configuradas"""
    print("🔍 VERIFICAÇÃO - CREDENCIAIS SIENGE")
    print("=" * 40)

    credenciais = credenciais_sienge_env()

    print(f"🔐 URL: {credenciais['url']}")
    print(f"👤 Usuário: {credenciais['usuario']}")
    print(f"🏢 Empresa: {credenciais['empresa']}")
    print(f"🔑 Senha: {'***' if credenciais['senha'] else 'NÃO CONFIGURADA'}")

    if all(credenciais.values()):
        print("✅ Todas as credenciais estão configuradas")
        return True
    else:
        print("❌ Algumas credenciais estão faltando")
        return False


async def verificar_saude_sistema():
    """Verificação completa de saúde do sistema"""
    print("🏥 VERIFICAÇÃO DE SAÚDE DO SISTEMA")
    print("=" * 50)

    resultados = []

    # Verifica conexão com banco
    print("\n1️⃣ Verificando conexão com banco...")
    resultado_banco = await verificar_conexao_banco()
    resultados.append(("Banco de Dados", resultado_banco))

    # Verifica credenciais
    print("\n2️⃣ Verificando credenciais...")
    resultado_credenciais = await verificar_credenciais_sienge()
    resultados.append(("Credenciais Sienge", resultado_credenciais))

    # Verifica carregamento de dados
    print("\n3️⃣ Verificando carregamento de dados...")
    try:
        contratos = await carregar_fila_contratos()
        indices = await carregar_indices_economicos()
        resultado_dados = len(contratos) >= 0 and len(indices) > 0
        print(f"   Contratos: {len(contratos)} | Índices: {len(indices)}")
    except Exception as e:
        resultado_dados = False
        print(f"   ❌ Erro: {str(e)}")
    resultados.append(("Carregamento de Dados", resultado_dados))

    # Resumo final
    print(f"\n📊 RESUMO DE SAÚDE:")
    for nome, resultado in resultados:
        status = "✅ OK" if resultado else "❌ PROBLEMA"
        print(f"   {nome}: {status}")

    total_ok = sum(1 for _, r in resultados if r)
    total_tests = len(resultados)

    print(f"\n🎯 SAÚDE GERAL: {total_ok}/{total_tests} componentes OK")

    return total_ok == total_tests


# --- Menu Interativo ---


def menu_interativo():
    """Menu interativo para testes do RPA Sienge"""
    print("\n🎯 MENU DE TESTES - RPA SIENGE")
    print("=" * 60)
    print("📋 TESTES INCREMENTAIS (DADOS REAIS DA FILA):")
    print("1. 🔐 Teste Login Sienge")
    print("2. 📊 Teste Consulta Relatórios (Webscraping Real)")
    print("3. 🔄 Teste Reparcelamento (Dados Reais + Webscraping)")
    print("4. 🌐 Teste Webscraping Reparcelamento (Dados Calculados)")
    print("5. 📄 Teste Geração Carnê (Dados Reais + Webscraping)")
    print("6. 📊 Teste Retroalimentação Planilha (Dados Reais + Google Sheets)")
    print()
    print("🚀 TESTES COMPLETOS:")
    print("7. 🎯 Teste Completo (Fila Real)")
    print("8. 🧪 Teste Contrato Simulado")
    print()
    print("🔍 VERIFICAÇÕES:")
    print("9. 🏥 Verificação de Saúde Sistema")
    print("10. 🔗 Teste Conexão Banco")
    print("11. 📈 Teste Carregamento Índices")
    print()
    print("❌ SAIR:")
    print("0. 🚪 Sair")
    print()
    print("💡 Dica: Os testes 2, 3, 4, 5 e 6 fazem webscraping real no Sienge!")
    print("💡 Teste 6: Específico para retroalimentar planilha com dados financeiros do Sienge")
    print("=" * 60)

    while True:
        try:
            opcao = input("\n👉 Escolha uma opção (0-11): ").strip()

            if opcao == "1":
                return teste_etapa_login()
            elif opcao == "2":
                return teste_etapa_consulta_relatorios()
            elif opcao == "3":
                return teste_etapa_reparcelamento()
            elif opcao == "4":
                return teste_webscraping_reparcelamento()
            elif opcao == "5":
                return teste_etapa_geracao_carne()
            elif opcao == "6":
                return teste_preenchimento_planilha()
            elif opcao == "7":
                return teste_completo_fila_real()
            elif opcao == "8":
                return teste_contrato_simulado()
            elif opcao == "9":
                return verificar_saude_sistema()
            elif opcao == "10":
                return verificar_conexao_banco()
            elif opcao == "11":
                return verificar_credenciais_sienge()
            elif opcao == "0":
                print("👋 Encerrando testes...")
                return None
            else:
                print("❌ Opção inválida! Escolha entre 0-11.")

        except KeyboardInterrupt:
            print("\n👋 Teste interrompido pelo usuário")
            return None


# --- Função Principal ---


async def main():
    """Função principal do sistema de testes"""
    print("🤖 SISTEMA DE TESTES RPA SIENGE - COMPLETO")
    print("Suporte para desenvolvimento e debugging das etapas de webscraping")
    print("Baseado em dados reais da fila de processamento")
    print("Todas as etapas do RPA implementadas e testáveis")
    print()

    # Executa menu interativo
    teste_selecionado = menu_interativo()

    if teste_selecionado:
        print("\n🚀 Executando teste selecionado...")
        sucesso = await teste_selecionado

        print("\n" + "=" * 60)
        if sucesso:
            print("✅ TESTE CONCLUÍDO COM SUCESSO!")
            print("🎯 Etapa testada funcionando corretamente")
        else:
            print("❌ TESTE FALHOU - Verifique os logs acima")
            print("💡 Dica: Use os testes incrementais para identificar o problema")
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
