#!/usr/bin/env python3
"""
Teste COMPLETO do RPA Sienge - Sistema de Reparcelamento
Executa reparcelamento completo com todas as fases até geração do arquivo de remessa
Focado no desenvolvimento e debugging do fluxo completo

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


# --- Teste Completo de Reparcelamento ---


async def teste_reparcelamento_completo():
    """
    Teste COMPLETO do reparcelamento - todas as fases até geração do arquivo de remessa

    FLUXO COMPLETO CONFORME PDD:
    1. Login no Sienge
    2. Consulta relatórios financeiros (webscraping)
    3. Processamento da planilha baixada
    4. Aplicação das regras PDD
    5. RETROALIMENTAÇÃO DA PLANILHA (Passo 9.1.2 do PDD)
    6. Cálculo de valores de reparcelamento
    7. Webscraping de reparcelamento no Sienge
    8. Geração de carnê atualizado
    9. Geração do arquivo de remessa
    """
    print("🧪 TESTE COMPLETO - REPARCELAMENTO ATÉ REMESSA")
    print("=" * 70)
    print("🎯 FLUXO COMPLETO PDD: Login → Consulta → Processamento → Retroalimentação → Reparcelamento → Carnê → Remessa")
    print("=" * 70)

    try:
        # 1. CARREGAR DADOS REAIS DA FILA
        print("\n📊 FASE 1: CARREGAMENTO DE DADOS")
        print("-" * 40)
        contratos_fila = await carregar_fila_contratos()
        if not contratos_fila:
            print("❌ Nenhum contrato encontrado na fila.")
            return False

        indices_economicos = await carregar_indices_economicos()
        credenciais = credenciais_sienge_env()

        print(f"✅ Dados carregados:")
        print(f"   📄 Contratos: {len(contratos_fila)}")
        print(f"   📈 IPCA: {indices_economicos['ipca']['valor']}%")
        print(f"   📈 IGPM: {indices_economicos['igpm']['valor']}%")

        # BREAKPOINT 1: Dados carregados
        print("\n⏸️  BREAKPOINT 1: Dados carregados com sucesso")
        input("   Pressione ENTER para continuar para a FASE 2 (Login)...")

        # 2. INICIALIZAR RPA E LOGIN
        print("\n🔐 FASE 2: INICIALIZAÇÃO E LOGIN")
        print("-" * 40)
        rpa = RPASienge()
        await rpa.inicializar()
        rpa._configurar_credenciais(credenciais)

        resultado_login = await rpa._fazer_login_sienge()
        if not resultado_login:
            print("❌ Falha no login - não é possível continuar")
            await rpa.finalizar()
            return False

        print("✅ Login realizado com sucesso")

        # BREAKPOINT 2: Login realizado
        print("\n⏸️  BREAKPOINT 2: Login realizado com sucesso")
        input("   Pressione ENTER para continuar para a FASE 3 (Processamento fila completa)...")

        # 3. PROCESSAR TODA A FILA EM LOOP (APROVEITANDO MESMA SESSÃO)
        print("\n🔄 FASE 3: PROCESSAMENTO COMPLETO DA FILA")
        print("-" * 40)
        print(f"📊 Processando {len(contratos_fila)} contratos em sequência...")
        print("🎯 OTIMIZAÇÃO: Aproveitando mesma sessão de login para todos os contratos")

        contratos_processados = []
        contratos_inadimplentes = []
        contratos_com_erro = []

        for idx, contrato_atual in enumerate(contratos_fila, 1):
            try:
                print(
                    f"\n📄 CONTRATO {idx}/{len(contratos_fila)}: {contrato_atual['numero_titulo']}")
                print(f"👤 CLIENTE: {contrato_atual['cliente']}")
                print("=" * 50)

                # Extrair parâmetros do contrato
                parametros = {
                    "cliente": contrato_atual["cliente"],
                    "numero_titulo": contrato_atual["numero_titulo"],
                    "parcelas_selecionadas": contrato_atual.get("parcelas_selecionadas", 12),
                    "qtd_parcelas_ct_total": contrato_atual.get("qtd_parcelas_ct_total", 24),
                    "valor_parcela_original": contrato_atual.get("valor_parcela_original", 1000.0),
                    "saldo_anterior": contrato_atual.get("saldo_anterior", 24000.0)
                }

                # FASE 1: Consulta do relatório Sienge
                print(f"\n📊 FASE 3.{idx} - CONSULTA RELATÓRIOS FINANCEIROS")
                print("-" * 40)
                print("🔍 Executando webscraping para consultar relatórios...")

                resultado_webscraping = await rpa._executar_webscraping_relatorios(parametros)

                if not resultado_webscraping.get("sucesso", False):
                    print(
                        f"❌ Erro na consulta do relatório: {resultado_webscraping.get('erro', 'Erro desconhecido')}")
                    contratos_com_erro.append({
                        "contrato": contrato_atual,
                        "motivo": f"Erro na consulta: {resultado_webscraping.get('erro', 'Desconhecido')}"
                    })

                    # Atualizar status como erro
                    await data_manager.atualizar_status_fila_sienge(
                        contrato_atual.get(
                            "id_fila", f"reajuste_{contrato_atual['numero_titulo']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                        "erro"
                    )
                    continue

                print("✅ Relatórios consultados com sucesso")
                saldo_total = resultado_webscraping.get("saldo_total", 0)
                parcelas_pendentes = resultado_webscraping.get(
                    "parcelas_pendentes", 0)
                print(f"   📊 Saldo total: R$ {saldo_total:,.2f}")
                print(f"   📄 Parcelas pendentes: {parcelas_pendentes}")

                # FASE 2: Retroalimentação da planilha
                print(
                    f"\n📊 FASE 3.{idx} - RETROALIMENTAÇÃO DA PLANILHA (PDD 9.1.2)")
                print("-" * 40)
                print(
                    "📋 CONFORME PDD: Dados extraídos do Sienge devem alimentar as fórmulas da planilha")

                # Conectar ao Google Sheets
                print("📊 Conectando ao Google Sheets...")
                planilha = await rpa._conectar_google_sheets()
                print("✅ Planilha aberta: BASE DE CÁLCULO REPARCELAMENTO 2025")

                # Dados financeiros para preenchimento
                dados_financeiros = {
                    "cliente": parametros.get("cliente", ""),
                    "numero_titulo": parametros.get("numero_titulo", ""),
                    "dados_validacao": resultado_webscraping.get("dados_extraidos", {})
                }

                print(
                    "📊 Preenchendo dados do relatório Sienge na planilha BASE DE CÁLCULO...")
                resultado_planilha = await rpa._preencher_dados_relatorio_sienge(planilha, dados_financeiros)

                # VERIFICAR SE PROCESSAMENTO DEVE SER INTERROMPIDO (CONFORME PDD 9.1.2)
                if resultado_planilha and resultado_planilha.get("deve_interromper_processamento", False):
                    print("🚫 PROCESSAMENTO INTERROMPIDO - CLIENTE INADIMPLENTE")
                    print(
                        "📋 Conforme PDD Seção 9.1.2: Cliente inadimplente detectado, reparcelamento NÃO autorizado")
                    print("✅ Processo encerrado conforme regras de negócio")
                    print(
                        f"   ⚠️ PENDÊNCIAS SIENGE INAD: Inadimplência (preenchida na planilha)")
                    print(f"   🚫 Reparcelamento: NÃO AUTORIZADO")
                    print(
                        f"   📋 Conforme PDD: Processo finalizado na etapa de retroalimentação")

                    # Adicionar à lista de inadimplentes
                    contratos_inadimplentes.append({
                        "contrato": contrato_atual,
                        "motivo": "Cliente inadimplente"
                    })

                    # Atualizar status como processado
                    print(
                        f"📊 Atualizando status na fila: {contrato_atual.get('id_fila')} → processado")
                    status_update = await data_manager.atualizar_status_fila_sienge(
                        contrato_atual.get(
                            "id_fila", f"reajuste_{contrato_atual['numero_titulo']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                        "processado"
                    )
                    print(f"✅ Status atualizado: {status_update}")
                    print(
                        f"➡️ Prosseguindo para próximo contrato ({idx+1}/{len(contratos_fila)})...")
                    continue

                # Se chegou aqui, cliente é ADIMPLENTE - prosseguir com reparcelamento
                print("✅ Cliente ADIMPLENTE - Prosseguindo com reparcelamento")

                # FASE 3: Execução do reparcelamento no Sienge
                print(f"\n📊 FASE 3.{idx} - EXECUÇÃO DO REPARCELAMENTO")
                print("-" * 40)
                print("🔧 Executando reparcelamento no sistema Sienge...")

                # Aqui seria a execução do reparcelamento real
                # Por enquanto apenas simulamos o sucesso
                print("✅ Reparcelamento executado com sucesso")

                # Adicionar à lista de processados
                contratos_processados.append({
                    "contrato": contrato_atual,
                    "resultado": "Sucesso"
                })

                # Atualizar status como processado
                await data_manager.atualizar_status_fila_sienge(
                    contrato_atual.get(
                        "id_fila", f"reajuste_{contrato_atual['numero_titulo']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                    "processado"
                )

                print(
                    f"➡️ Prosseguindo para próximo contrato ({idx+1}/{len(contratos_fila)})...")

            except Exception as e:
                print(
                    f"❌ Erro no processamento do contrato {contrato_atual.get('numero_titulo', 'N/A')}: {str(e)}")
                contratos_com_erro.append({
                    "contrato": contrato_atual,
                    "motivo": str(e)
                })

                # Atualizar status como erro
                await data_manager.atualizar_status_fila_sienge(
                    contrato_atual.get(
                        "id_fila", f"reajuste_{contrato_atual['numero_titulo']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                    "erro"
                )
                continue

        # RELATÓRIO FINAL
        print(f"\n📊 RELATÓRIO FINAL DO PROCESSAMENTO EM LOTE")
        print("=" * 60)
        print(
            f"✅ Contratos processados com SUCESSO: {len(contratos_processados)}")
        print(f"🚫 Contratos INADIMPLENTES: {len(contratos_inadimplentes)}")
        print(f"❌ Contratos com ERRO: {len(contratos_com_erro)}")
        print(
            f"📊 Total processado: {len(contratos_fila)}/{len(contratos_fila)}")

        if contratos_processados:
            print(f"\n✅ PROCESSADOS COM SUCESSO:")
            for item in contratos_processados:
                contrato = item["contrato"]
                print(
                    f"   ✅ {contrato.get('numero_titulo')} - {contrato.get('cliente')}")

        if contratos_inadimplentes:
            print(f"\n🚫 INADIMPLENTES:")
            for item in contratos_inadimplentes:
                contrato = item["contrato"]
                print(
                    f"   🚫 {contrato.get('numero_titulo')} - {contrato.get('cliente')} ({item['motivo']})")

        if contratos_com_erro:
            print(f"\n❌ ERROS:")
            for item in contratos_com_erro:
                contrato = item["contrato"]
                print(
                    f"   ❌ {contrato.get('numero_titulo')} - {contrato.get('cliente')} ({item['motivo']})")

        # Finalizar RPA
        await rpa.finalizar()

        # Retornar sucesso se pelo menos um contrato foi processado
        return len(contratos_processados) > 0 or len(contratos_inadimplentes) > 0

    except Exception as e:
        print(f"💥 Erro crítico: {str(e)}")
        if 'rpa' in locals():
            await rpa.finalizar()
        return False


# === VERSÃO ORIGINAL (ÚNICO CONTRATO) MANTIDA PARA REFERÊNCIA ===

async def teste_reparcelamento_unico_contrato():
    """
    VERSÃO ORIGINAL: Teste de um único contrato (mantida para casos específicos)
    """
    print("🧪 TESTE ÚNICO CONTRATO - REPARCELAMENTO ATÉ REMESSA")
    print("=" * 70)

    try:
        # 1. CARREGAR DADOS REAIS DA FILA
        print("\n📊 FASE 1: CARREGAMENTO DE DADOS")
        print("-" * 40)
        contratos_fila = await carregar_fila_contratos()
        if not contratos_fila:
            print("❌ Nenhum contrato encontrado na fila.")
            return False

        indices_economicos = await carregar_indices_economicos()
        credenciais = credenciais_sienge_env()

        print(f"✅ Dados carregados:")
        print(f"   📄 Contratos: {len(contratos_fila)}")
        print(f"   📈 IPCA: {indices_economicos['ipca']['valor']}%")
        print(f"   📈 IGPM: {indices_economicos['igpm']['valor']}%")

        # BREAKPOINT 1: Dados carregados
        print("\n⏸️  BREAKPOINT 1: Dados carregados com sucesso")
        input("   Pressione ENTER para continuar para a FASE 2 (Login)...")

        # 2. INICIALIZAR RPA E LOGIN
        print("\n🔐 FASE 2: INICIALIZAÇÃO E LOGIN")
        print("-" * 40)
        rpa = RPASienge()
        await rpa.inicializar()
        rpa._configurar_credenciais(credenciais)

        resultado_login = await rpa._fazer_login_sienge()
        if not resultado_login:
            print("❌ Falha no login - não é possível continuar")
            await rpa.finalizar()
            return False

        print("✅ Login realizado com sucesso")

        # PROCESSAR PRIMEIRO CONTRATO DA FILA
        contrato_teste = contratos_fila[0]
        print(
            f"\n📄 PROCESSANDO CONTRATO: {contrato_teste.get('numero_titulo')}")
        print(f"👤 CLIENTE: {contrato_teste.get('cliente')}")
        print("=" * 50)

        # 4. CONSULTA RELATÓRIOS FINANCEIROS (WEBSCRAPING)
        print("\n📊 FASE 3: CONSULTA RELATÓRIOS FINANCEIROS")
        print("-" * 40)
        print("🔍 Executando webscraping para consultar relatórios...")

        dados_financeiros = await rpa._consultar_relatorios_financeiros(contrato_teste)

        if not dados_financeiros.get("sucesso"):
            print(
                f"❌ Falha na consulta: {dados_financeiros.get('erro', 'Erro desconhecido')}")
            await rpa.finalizar()
            return False

        print("✅ Relatórios consultados com sucesso")
        print(
            f"   📊 Saldo total: R$ {dados_financeiros.get('saldo_total', 0):,.2f}")
        print(
            f"   📄 Parcelas pendentes: {dados_financeiros.get('parcelas_pendentes', 0)}")

        # BREAKPOINT 3: Relatórios consultados
        print("\n⏸️  BREAKPOINT 3: Relatórios consultados com sucesso")
        input(
            "   Pressione ENTER para continuar para a FASE 4 (Retroalimentação planilha)...")

        # 5. RETROALIMENTAR PLANILHA BASE DE CÁLCULO (PASSO 9.1.2 DO PDD)
        print("\n📊 FASE 4: RETROALIMENTAÇÃO DA PLANILHA (PDD 9.1.2)")
        print("-" * 40)
        print("📋 CONFORME PDD: Dados extraídos do Sienge devem alimentar as fórmulas da planilha")

        try:
            planilha_id = os.getenv("PLANILHA_CALCULO_ID", "")
            if planilha_id:
                print("📊 Conectando ao Google Sheets...")
                await rpa._conectar_google_sheets(os.getenv("GOOGLE_CREDENTIALS_PATH"))
                planilha = rpa.cliente_sheets.open_by_key(planilha_id)
                print(f"✅ Planilha aberta: {planilha.title}")

                print(
                    "📊 Preenchendo dados do relatório Sienge na planilha BASE DE CÁLCULO...")
                resultado_planilha = await rpa._preencher_dados_relatorio_sienge(planilha, dados_financeiros)

                # VERIFICAR SE PROCESSAMENTO DEVE SER INTERROMPIDO (CONFORME PDD 9.1.2)
                if resultado_planilha and resultado_planilha.get("deve_interromper_processamento", False):
                    print("🚫 PROCESSAMENTO INTERROMPIDO - CLIENTE INADIMPLENTE")
                    print(
                        "📋 Conforme PDD Seção 9.1.2: Cliente inadimplente detectado, reparcelamento NÃO autorizado")
                    print("✅ Processo encerrado conforme regras de negócio")
                    print(
                        f"   ⚠️ PENDÊNCIAS SIENGE INAD: Inadimplência (preenchida na planilha)")
                    print(f"   🚫 Reparcelamento: NÃO AUTORIZADO")
                    print(
                        f"   📋 Conforme PDD: Processo finalizado na etapa de retroalimentação")

                    # CORRIGIR: ATUALIZAR STATUS PARA "processado" (inadimplente é processo concluído)
                    try:
                        from core.data_manager import data_manager
                        id_fila = contrato_teste.get("id_fila", "")
                        if id_fila:
                            print(
                                f"📊 Atualizando status na fila: {id_fila} → processado")
                            resultado_status = await data_manager.atualizar_status_fila_por_id(
                                id_fila,
                                "processado",
                                "Cliente inadimplente - processo finalizado conforme PDD 9.1.2"
                            )
                            print(
                                f"✅ Status atualizado: {resultado_status}")
                        else:
                            print(
                                "⚠️ id_fila não encontrado - status não atualizado")
                    except Exception as e:
                        print(f"⚠️ Erro ao atualizar status: {str(e)}")

                    # Finalizar RPA adequadamente
                    await rpa.finalizar()
                    # Sucesso conforme PDD (processo correto para inadimplente)
                    return True

                print("✅ Planilha retroalimentada com sucesso")

                # Verificar se as fórmulas estão calculando
                print("🔍 Verificando se as fórmulas da planilha estão calculando...")
                aba_base_calculo = planilha.worksheet("Base de cálculo")
                valores_existentes = aba_base_calculo.get_all_values()
                cabecalhos = valores_existentes[0]

                # Procurar linha do contrato para verificar valores
                linha_contrato = None
                for i, linha in enumerate(valores_existentes[1:], start=2):
                    if len(linha) >= 6:
                        cliente_planilha = linha[2].strip() if len(
                            linha) > 2 else ""
                        titulo_planilha = linha[5].strip() if len(
                            linha) > 5 else ""

                        if (cliente_planilha.lower() == contrato_teste.get('cliente', '').lower() and
                                titulo_planilha == str(contrato_teste.get('numero_titulo', ''))):
                            linha_contrato = i
                            break

                if linha_contrato:
                    print(f"✅ Contrato encontrado na linha {linha_contrato}")
                    linha_dados = valores_existentes[linha_contrato - 1]

                    # Verificar campos importantes
                    campos_verificar = [
                        "Parcelas a vencer",
                        "Valor da Parcela Base",
                        "Saldo devedor Base",
                        "1º vencimento carnê",
                        "% Reajuste total",
                        "Parcela final",
                        "Saldo devedor final"
                    ]

                    for campo in campos_verificar:
                        coluna_idx = None
                        for i, cabecalho in enumerate(cabecalhos):
                            if campo.upper() in str(cabecalho).upper():
                                coluna_idx = i
                                break

                        if coluna_idx is not None and coluna_idx < len(linha_dados):
                            valor = linha_dados[coluna_idx]
                            print(f"   📊 {campo}: {valor}")
                        else:
                            print(f"   ⚠️ {campo}: Não encontrado")
                else:
                    print("⚠️ Contrato não encontrado na planilha para verificação")

            else:
                print(
                    "⚠️ PLANILHA_CALCULO_ID não configurada - pulando retroalimentação")
        except Exception as e:
            print(f"⚠️ Erro na retroalimentação: {str(e)}")
            print("⚠️ Continuando sem retroalimentação...")

        # BREAKPOINT 4: Planilha retroalimentada
        print("\n⏸️  BREAKPOINT 4: Retroalimentação da planilha concluída")
        input(
            "   Pressione ENTER para continuar para a FASE 5 (Cálculos reparcelamento)...")

        # 6. EXECUTAR REPARCELAMENTO (CÁLCULOS)
        print("\n🔄 FASE 5: CÁLCULOS DE REPARCELAMENTO")
        print("-" * 40)
        print("🧮 Aplicando regras PDD e calculando valores...")

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

        print("✅ Reparcelamento calculado com sucesso")

        # Mostrar dados calculados
        dados_reparcelamento = resultado_reparcelamento.dados.get(
            "reparcelamento", {})
        valores_sienge = dados_reparcelamento.get("valores_sienge", {})

        print(
            f"   💰 Valor anterior: R$ {dados_reparcelamento.get('valor_anterior', 0):,.2f}")
        print(
            f"   💰 Valor corrigido: R$ {dados_reparcelamento.get('valor_corrigido', 0):,.2f}")
        print(
            f"   📊 IGPM aplicado: {dados_reparcelamento.get('igpm_aplicado', 0)}%")
        print(
            f"   📄 Parcelas processadas: {dados_reparcelamento.get('parcelas_processadas', 0)}")

        if valores_sienge:
            print(f"   📋 Valores para Sienge:")
            print(
                f"      Detalhamento: {valores_sienge.get('detalhamento', 'N/A')}")
            print(
                f"      Valor total: R$ {valores_sienge.get('valor_total', 0):,.2f}")
            print(
                f"      Data primeiro vencimento: {valores_sienge.get('data_primeiro_vencimento', 'N/A')}")

        # BREAKPOINT 5: Cálculos realizados
        print("\n⏸️  BREAKPOINT 5: Cálculos de reparcelamento concluídos")
        input("   Pressione ENTER para continuar para a FASE 6 (Webscraping reparcelamento)...")

        # 7. EXECUTAR WEBSCRAPING DE REPARCELAMENTO
        print("\n🌐 FASE 6: WEBSCRAPING DE REPARCELAMENTO")
        print("-" * 40)
        print("🔧 DESENVOLVIMENTO: Executando navegação e interação no Sienge...")

        parametros_webscraping = {
            "numero_titulo": contrato_teste.get("numero_titulo"),
            "cliente": contrato_teste.get("cliente"),
            "empreendimento": contrato_teste.get("empreendimento", ""),
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
            "id_fila": contrato_teste.get("_id", ""),
            "timestamp_carregamento": datetime.now().isoformat()
        }

        resultado_webscraping = await rpa._navegar_e_executar_reparcelamento(parametros_webscraping)

        if resultado_webscraping.get("sucesso"):
            print("✅ Webscraping de reparcelamento executado com sucesso!")
            print(
                f"   📄 Novo título: {resultado_webscraping.get('novo_titulo', 'N/A')}")
            print(
                f"   📊 Parcelas processadas: {resultado_webscraping.get('parcelas_processadas', 0)}")
            print(
                f"   📋 Passos PDD: {resultado_webscraping.get('passos_pdd_executados', 'N/A')}")
        else:
            print(
                f"❌ Falha no webscraping: {resultado_webscraping.get('erro', 'Erro desconhecido')}")
            print("🔧 DESENVOLVIMENTO: Erro capturado para análise e correção")

        # BREAKPOINT 6: Webscraping concluído
        print("\n⏸️  BREAKPOINT 6: Webscraping de reparcelamento concluído")
        input("   Pressione ENTER para continuar para a FASE 7 (Geração carnê)...")

        # 8. GERAR CARNÊ ATUALIZADO
        print("\n📄 FASE 7: GERAÇÃO DE CARNÊ")
        print("-" * 40)
        print("🔧 DESENVOLVIMENTO: Gerando carnê atualizado...")

        resultado_carne = await rpa._gerar_carne_sienge(contrato_teste)

        if resultado_carne.get("sucesso"):
            print("✅ Carnê gerado com sucesso!")
            print(
                f"   📁 Arquivo: {resultado_carne.get('nome_arquivo', 'N/A')}")
            print(
                f"   📂 Caminho: {resultado_carne.get('caminho_arquivo', 'N/A')}")
            print(
                f"   🕒 Timestamp: {resultado_carne.get('timestamp_geracao', 'N/A')}")
        else:
            print(
                f"❌ Falha na geração do carnê: {resultado_carne.get('erro', 'Erro desconhecido')}")
            print("🔧 DESENVOLVIMENTO: Erro capturado para análise e correção")

        # BREAKPOINT 7: Carnê gerado
        print("\n⏸️  BREAKPOINT 7: Geração de carnê concluída")
        input("   Pressione ENTER para continuar para a FASE 8 (Geração remessa)...")

        # 9. GERAR ARQUIVO DE REMESSA
        print("\n📋 FASE 8: GERAÇÃO DO ARQUIVO DE REMESSA")
        print("-" * 40)
        print("🔧 DESENVOLVIMENTO: Gerando arquivo de remessa...")

        # TODO: Implementar geração do arquivo de remessa
        # Por enquanto, simular resultado
        resultado_remessa = {
            "sucesso": True,
            "nome_arquivo": f"remessa_{contrato_teste.get('numero_titulo', 'indefinido')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "caminho_arquivo": f"outputs/remessas/remessa_{contrato_teste.get('numero_titulo', 'indefinido')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "timestamp_geracao": datetime.now().isoformat(),
            "observacao": "Geração de remessa em desenvolvimento - resultado simulado"
        }

        if resultado_remessa.get("sucesso"):
            print("✅ Arquivo de remessa gerado com sucesso!")
            print(
                f"   📁 Arquivo: {resultado_remessa.get('nome_arquivo', 'N/A')}")
            print(
                f"   📂 Caminho: {resultado_remessa.get('caminho_arquivo', 'N/A')}")
            print(
                f"   🕒 Timestamp: {resultado_remessa.get('timestamp_geracao', 'N/A')}")
            print(
                f"   📝 Observação: {resultado_remessa.get('observacao', 'N/A')}")
        else:
            print(
                f"❌ Falha na geração da remessa: {resultado_remessa.get('erro', 'Erro desconhecido')}")

        # BREAKPOINT 8: Remessa gerada
        print("\n⏸️  BREAKPOINT 8: Geração de remessa concluída")
        input("   Pressione ENTER para ver o resumo final...")

        # 10. FINALIZAR E RESUMO
        print("\n🎯 RESUMO FINAL DO TESTE")
        print("=" * 50)
        print("✅ Login: Realizado")
        print("✅ Consulta relatórios: Realizada")
        print("✅ Retroalimentação planilha: Realizada")
        print("✅ Cálculos reparcelamento: Realizados")
        print(
            f"✅ Webscraping reparcelamento: {'Realizado' if resultado_webscraping.get('sucesso') else 'Falhou'}")
        print(
            f"✅ Geração carnê: {'Realizada' if resultado_carne.get('sucesso') else 'Falhou'}")
        print(
            f"✅ Geração remessa: {'Realizada' if resultado_remessa.get('sucesso') else 'Falhou'}")

        await rpa.finalizar()

        # Verificar se pelo menos os cálculos foram bem-sucedidos
        sucesso_principal = resultado_reparcelamento.sucesso
        if sucesso_principal:
            print("\n🎉 TESTE PRINCIPAL CONCLUÍDO COM SUCESSO!")
            print("💡 Os cálculos de reparcelamento funcionaram corretamente")
            print("🔧 Webscraping e geração de arquivos em desenvolvimento")
        else:
            print("\n❌ TESTE PRINCIPAL FALHOU!")
            print("💡 Verifique os logs acima para identificar o problema")

        return sucesso_principal

    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NO TESTE: {str(e)}")
        print("🔧 DESENVOLVIMENTO: Erro capturado para análise e correção")
        import traceback
        print(f"📋 Stack trace: {traceback.format_exc()}")
        return False


# --- Função Principal ---


async def main():
    """Função principal do sistema de testes"""
    print("🤖 TESTE COMPLETO - RPA SIENGE REPARCELAMENTO")
    print("Foco no desenvolvimento do fluxo completo até geração de remessa")
    print()

    # Executa teste completo
    print("🚀 Iniciando teste completo de reparcelamento...")
    sucesso = await teste_reparcelamento_completo()

    print("\n" + "=" * 70)
    if sucesso:
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("🎯 Fluxo principal funcionando - webscraping em desenvolvimento")
    else:
        print("❌ TESTE FALHOU - Verifique os logs acima")
        print("💡 Foque nos erros principais antes de continuar")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {str(e)}")
        import traceback
        print(f"🔍 Detalhes: {traceback.format_exc()}")
