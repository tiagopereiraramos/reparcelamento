#!/usr/bin/env python3
"""
Main de produção para execução completa do RPA Sienge
Sistema automatizado de reparcelamento em fases otimizadas

NOVA ARQUITETURA DISRUPTIVA:
- Diagnóstico completo da fila antes de processar
- Login específico para cada fase (otimização de sessão)
- Processamento sequencial com fallback robusto
- Notificações granulares por fase e marco
- Relatório final consolidado

FASES DO PROCESSO (conforme PDD):
1. EXTRAÇÃO: PENDENTE → EXTRAIDO (Relatórios Sienge + Validação PDD 9.1.1)
2. REPARCELAMENTO: EXTRAIDO → REPARCELADO (Planilha + Webscraping PDD 10.1)
3. GERAÇÃO CARNÊS: REPARCELADO → CARNE_GERADO (Remessas por empresa PDD 10.2)

Desenvolvido em Português Brasileiro
"""

from core.mongodb_manager import mongodb_manager
from rpa_sienge.rpa_sienge import RPASienge
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Garante execução headless em produção
os.environ["HEADLESS"] = "1"  # Força modo headless para Selenium/Browser

# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


def log(msg):
    """Loga mensagem com timestamp."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def notificar_sucesso_simples(titulo: str, mensagem: str):
    """Notificação simples de sucesso via log"""
    log(f"✅ NOTIFICAÇÃO: {titulo}")
    log(f"   📋 {mensagem}")


def notificar_erro_simples(titulo: str, mensagem: str):
    """Notificação simples de erro via log"""
    log(f"❌ NOTIFICAÇÃO: {titulo}")
    log(f"   📋 {mensagem}")


def get_env_or_fail(var_name, default=None):
    """Obtém variável de ambiente ou encerra o programa se não definida."""
    value = os.getenv(var_name, default)
    if not value:
        log(f"ERRO: Variável de ambiente obrigatória não definida: {var_name}")
        sys.exit(1)
    return value


async def carregar_credenciais_sienge() -> Dict[str, str]:
    """Carrega e valida credenciais do Sienge das variáveis de ambiente."""
    log("🔑 Carregando credenciais do Sienge...")

    credenciais = {
        "url": get_env_or_fail("SIENGE_URL", "https://jmservicos.sienge.com.br/sienge/8/index.html"),
        "usuario": get_env_or_fail("SIENGE_USUARIO"),
        "senha": get_env_or_fail("SIENGE_SENHA"),
        "empresa": get_env_or_fail("SIENGE_EMPRESA", "1")
    }

    log(
        f"✅ Credenciais carregadas: {credenciais['usuario']} @ {credenciais['url']}")
    return credenciais


async def carregar_indices_economicos() -> Dict[str, Any]:
    """Carrega índices econômicos do sistema ou usa valores de fallback."""
    log("📈 Carregando índices econômicos...")

    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()

        # Busca IPCA e IGPM separadamente
        ipca = await data_manager.obter_indice_mais_recente("ipca")
        igpm = await data_manager.obter_indice_mais_recente("igpm")

        if ipca is not None and igpm is not None:
            log(
                f"✅ Índices carregados do sistema: IPCA={ipca}% | IGPM={igpm}%")
            return {
                "ipca": {"valor": ipca, "tipo": "IPCA", "periodo": "Recente"},
                "igpm": {"valor": igpm, "tipo": "IGPM", "periodo": "Recente"}
            }
        else:
            log("⚠️ Usando índices de fallback")
            return {
                "ipca": {"valor": 4.62, "tipo": "IPCA", "periodo": "Fallback"},
                "igpm": {"valor": 3.89, "tipo": "IGPM", "periodo": "Fallback"}
            }

    except Exception as e:
        log(f"❌ Erro ao carregar índices: {str(e)} - Usando fallback")
        return {
            "ipca": {"valor": 4.62, "tipo": "IPCA", "periodo": "Fallback"},
            "igpm": {"valor": 3.89, "tipo": "IGPM", "periodo": "Fallback"}
        }


async def diagnosticar_fila_completa() -> Dict[str, Any]:
    """
    DIAGNÓSTICO DISRUPTIVO: Analisa toda a fila antes de processar
    Conforme estratégia de otimização proposta
    """
    log("📊 DIAGNÓSTICO COMPLETO DA FILA DE CONTRATOS")
    log("=" * 60)

    try:
        # Conectar ao MongoDB
        if not mongodb_manager.conectado:
            await mongodb_manager.conectar()

        if not mongodb_manager.conectado or mongodb_manager.database is None:
            raise Exception("MongoDB não conectado ou database indisponível")

        collection = mongodb_manager.database.fila_contratos

        # Contar por status (conforme fases do processo)
        total = collection.count_documents({})
        pendentes = collection.count_documents({"status": "PENDENTE"})
        extraidos = collection.count_documents({"status": "EXTRAIDO"})
        reparcelados = collection.count_documents({"status": "REPARCELADO"})
        carne_gerados = collection.count_documents({"status": "CARNE_GERADO"})
        processados = collection.count_documents({"status": "PROCESSADO"})
        erros = collection.count_documents({"status": "ERRO"})

        # Análise por empresa (para otimização de carnês)
        pipeline_empresas = [
            {"$match": {"status": "REPARCELADO"}},
            {"$group": {"_id": "$empresa", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        empresas_reparceladas = list(collection.aggregate(pipeline_empresas))

        # Estatísticas detalhadas
        diagnostico = {
            "total_contratos": total,
            "por_status": {
                "PENDENTE": pendentes,
                "EXTRAIDO": extraidos,
                "REPARCELADO": reparcelados,
                "CARNE_GERADO": carne_gerados,
                "PROCESSADO": processados,
                "ERRO": erros
            },
            "empresas_reparceladas": {emp["_id"]: emp["count"] for emp in empresas_reparceladas},
            "fases_necessarias": {
                "extracao": pendentes > 0,
                "reparcelamento": extraidos > 0,
                "geracao_carnes": reparcelados > 0
            },
            "timestamp_diagnostico": datetime.now().isoformat()
        }

        # Log do diagnóstico
        log(f"📋 ESTATÍSTICAS DA FILA:")
        log(f"   📄 Total de contratos: {total}")
        log(f"   ⏳ Pendentes (aguardando extração): {pendentes}")
        log(f"   📥 Extraídos (aguardando reparcelamento): {extraidos}")
        log(f"   📤 Reparcelados (aguardando carnê): {reparcelados}")
        log(f"   🎫 Carnês gerados: {carne_gerados}")
        log(f"   ✅ Processados: {processados}")
        log(f"   ❌ Com erro: {erros}")

        if empresas_reparceladas:
            log(f"🏢 EMPRESAS COM CONTRATOS REPARCELADOS:")
            for empresa, count in list(diagnostico["empresas_reparceladas"].items())[:5]:
                log(f"   📋 {empresa}: {count} contratos")

        # Determinar estratégia de processamento
        if total == 0:
            log("⚠️ Nenhum contrato encontrado na fila")
            return diagnostico

        log("\n🎯 FASES QUE SERÃO EXECUTADAS:")
        if diagnostico["fases_necessarias"]["extracao"]:
            log(f"   📥 EXTRAÇÃO: {pendentes} contratos")
        if diagnostico["fases_necessarias"]["reparcelamento"]:
            log(f"   📤 REPARCELAMENTO: {extraidos} contratos")
        if diagnostico["fases_necessarias"]["geracao_carnes"]:
            log(f"   🎫 GERAÇÃO CARNÊS: {reparcelados} contratos em {len(empresas_reparceladas)} empresas")

        return diagnostico

    except Exception as e:
        log(f"❌ Erro no diagnóstico: {str(e)}")
        raise


async def executar_fase_extracao(credenciais: Dict[str, str], total_pendentes: int) -> Dict[str, Any]:
    """
    FASE 1: EXTRAÇÃO DE RELATÓRIOS
    PENDENTE → EXTRAIDO

    Conforme PDD Seção 9.1: Consulta relatórios + Validação PDD 9.1.1
    """
    log("\n📥 EXECUTANDO FASE 1: EXTRAÇÃO DE RELATÓRIOS")
    log("=" * 60)
    log(f"🎯 Meta: Processar {total_pendentes} contratos pendentes")
    log("📋 Processo: Consulta Sienge + Validação PDD 9.1.1 + Persistência MongoDB")

    try:
        notificar_sucesso_simples(
            f"🚀 FASE 1 INICIADA: Extração de {total_pendentes} relatórios",
            f"Processo: Consulta relatórios Sienge + Validação regras PDD"
        )

        # Inicializar RPA com headless em produção
        headless = os.getenv("HEADLESS", "true").lower() == "true"
        rpa = RPASienge(headless=headless)
        await rpa.inicializar()

        log(f"🤖 RPA inicializado (headless: {headless})")

        # Executar extração em lote (método otimizado)
        resultado = await rpa.processar_fila_contratos_lote(
            credenciais_sienge=credenciais,
            indices=None,  # Não necessário para extração
            fase="extracao",
            pausar_entre_contratos=False  # Processamento contínuo em produção
        )

        await rpa.finalizar()

        # Processar resultado
        if resultado.get("sucesso"):
            fase_extracao = resultado.get("fase_extracao", {})
            sucessos = fase_extracao.get("contratos_processados", 0)
            erros = fase_extracao.get("contratos_erro", 0)

            log(f"✅ FASE 1 CONCLUÍDA:")
            log(f"   ✅ Sucessos: {sucessos}")
            log(f"   ❌ Erros: {erros}")
            log(f"   📊 Taxa de sucesso: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%")

            notificar_sucesso_simples(
                f"✅ FASE 1 CONCLUÍDA: Extração de relatórios",
                f"Sucessos: {sucessos} | Erros: {erros} | Taxa: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%"
            )

            return {
                "sucesso": True,
                "contratos_processados": sucessos,
                "contratos_erro": erros,
                "detalhes": fase_extracao
            }
        else:
            erro_msg = resultado.get("erro", "Erro desconhecido na extração")
            log(f"❌ FASE 1 FALHOU: {erro_msg}")

            notificar_erro_simples(
                f"❌ FASE 1 FALHOU: Extração de relatórios",
                f"Erro: {erro_msg}"
            )

            return {"sucesso": False, "erro": erro_msg}

    except Exception as e:
        erro_msg = f"Erro crítico na fase de extração: {str(e)}"
        log(f"💥 {erro_msg}")

        notificar_erro_simples(
            f"💥 FASE 1 ERRO CRÍTICO",
            erro_msg
        )

        return {"sucesso": False, "erro": erro_msg}


async def executar_fase_reparcelamento(credenciais: Dict[str, str], indices: Dict[str, Any], total_extraidos: int) -> Dict[str, Any]:
    """
    FASE 2: REPARCELAMENTO 
    EXTRAIDO → REPARCELADO

    Conforme PDD Seção 10.1: Planilha base de cálculo + Webscraping reparcelamento
    """
    log("\n📤 EXECUTANDO FASE 2: REPARCELAMENTO")
    log("=" * 60)
    log(f"🎯 Meta: Processar {total_extraidos} contratos extraídos")
    log("📋 Processo: Planilha base cálculo + Webscraping reparcelamento PDD 10.1")
    log(f"📈 Índices: IPCA={indices['ipca']['valor']}% | IGPM={indices['igpm']['valor']}%")

    try:
        notificar_sucesso_simples(
            f"🚀 FASE 2 INICIADA: Reparcelamento de {total_extraidos} contratos",
            f"Índices: IPCA={indices['ipca']['valor']}% | IGPM={indices['igpm']['valor']}%"
        )

        # Inicializar RPA com nova sessão
        headless = os.getenv("HEADLESS", "true").lower() == "true"
        rpa = RPASienge(headless=headless)
        await rpa.inicializar()

        log(f"🤖 RPA reinicializado para reparcelamento (headless: {headless})")

        # Executar reparcelamento em lote
        resultado = await rpa.processar_fila_contratos_lote(
            credenciais_sienge=credenciais,
            indices=indices,
            fase="reparcelamento",
            pausar_entre_contratos=False  # Processamento contínuo em produção
        )

        await rpa.finalizar()

        # Processar resultado
        if resultado.get("sucesso"):
            fase_reparcelamento = resultado.get("fase_reparcelamento", {})
            sucessos = fase_reparcelamento.get("contratos_processados", 0)
            erros = fase_reparcelamento.get("contratos_erro", 0)

            log(f"✅ FASE 2 CONCLUÍDA:")
            log(f"   ✅ Sucessos: {sucessos}")
            log(f"   ❌ Erros: {erros}")
            log(f"   📊 Taxa de sucesso: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%")

            notificar_sucesso_simples(
                f"✅ FASE 2 CONCLUÍDA: Reparcelamento",
                f"Sucessos: {sucessos} | Erros: {erros} | Taxa: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%"
            )

            return {
                "sucesso": True,
                "contratos_processados": sucessos,
                "contratos_erro": erros,
                "detalhes": fase_reparcelamento
            }
        else:
            erro_msg = resultado.get(
                "erro", "Erro desconhecido no reparcelamento")
            log(f"❌ FASE 2 FALHOU: {erro_msg}")

            notificar_erro_simples(
                f"❌ FASE 2 FALHOU: Reparcelamento",
                f"Erro: {erro_msg}"
            )

            return {"sucesso": False, "erro": erro_msg}

    except Exception as e:
        erro_msg = f"Erro crítico na fase de reparcelamento: {str(e)}"
        log(f"💥 {erro_msg}")

        notificar_erro_simples(
            f"💥 FASE 2 ERRO CRÍTICO",
            erro_msg
        )

        return {"sucesso": False, "erro": erro_msg}


async def executar_fase_geracao_carnes(credenciais: Dict[str, str], total_reparcelados: int, empresas_info: Dict[str, int]) -> Dict[str, Any]:
    """
    FASE 3: GERAÇÃO DE CARNÊS
    REPARCELADO → CARNE_GERADO

    Conforme PDD Seção 10.2: Geração de arquivos de remessa por empresa
    """
    log("\n🎫 EXECUTANDO FASE 3: GERAÇÃO DE CARNÊS")
    log("=" * 60)
    log(f"🎯 Meta: Processar {total_reparcelados} contratos reparcelados")
    log(f"🏢 Empresas: {len(empresas_info)} empresas diferentes")
    log("📋 Processo: Geração arquivos remessa conforme PDD 10.2")

    try:
        notificar_sucesso_simples(
            f"🚀 FASE 3 INICIADA: Geração de carnês",
            f"Contratos: {total_reparcelados} | Empresas: {len(empresas_info)}"
        )

        # Inicializar RPA com nova sessão
        headless = os.getenv("HEADLESS", "true").lower() == "true"
        rpa = RPASienge(headless=headless)
        await rpa.inicializar()

        log(
            f"🤖 RPA reinicializado para geração de carnês (headless: {headless})")

        # Executar geração de carnês em lote (por empresa)
        resultado = await rpa.processar_fila_geracao_carnes(
            credenciais_sienge=credenciais,
            pausar_entre_contratos=False  # Processamento contínuo em produção
        )

        await rpa.finalizar()

        # Processar resultado
        if resultado.get("sucesso"):
            sucessos = resultado.get("contratos_processados", 0)
            erros = resultado.get("contratos_erro", 0)
            empresas_processadas = resultado.get("empresas_processadas", 0)

            log(f"✅ FASE 3 CONCLUÍDA:")
            log(f"   ✅ Contratos processados: {sucessos}")
            log(f"   ❌ Contratos com erro: {erros}")
            log(f"   🏢 Empresas processadas: {empresas_processadas}")
            log(f"   📊 Taxa de sucesso: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%")

            notificar_sucesso_simples(
                f"✅ FASE 3 CONCLUÍDA: Geração de carnês",
                f"Contratos: {sucessos} | Empresas: {empresas_processadas} | Taxa: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%"
            )

            return {
                "sucesso": True,
                "contratos_processados": sucessos,
                "contratos_erro": erros,
                "empresas_processadas": empresas_processadas,
                "detalhes": resultado
            }
        else:
            erro_msg = resultado.get(
                "erro", "Erro desconhecido na geração de carnês")
            log(f"❌ FASE 3 FALHOU: {erro_msg}")

            notificar_erro_simples(
                f"❌ FASE 3 FALHOU: Geração de carnês",
                f"Erro: {erro_msg}"
            )

            return {"sucesso": False, "erro": erro_msg}

    except Exception as e:
        erro_msg = f"Erro crítico na fase de geração de carnês: {str(e)}"
        log(f"💥 {erro_msg}")

        notificar_erro_simples(
            f"💥 FASE 3 ERRO CRÍTICO",
            erro_msg
        )

        return {"sucesso": False, "erro": erro_msg}


async def gerar_relatorio_final(diagnostico: Dict[str, Any], resultados_fases: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Gera relatório final consolidado do processamento
    """
    log("\n📊 GERANDO RELATÓRIO FINAL CONSOLIDADO")
    log("=" * 60)

    # Calcular estatísticas gerais
    total_processados = sum(
        resultado.get("contratos_processados", 0)
        for resultado in resultados_fases.values()
        if resultado.get("sucesso")
    )

    total_erros = sum(
        resultado.get("contratos_erro", 0)
        for resultado in resultados_fases.values()
        if resultado.get("sucesso")
    )

    fases_executadas = len(
        [r for r in resultados_fases.values() if r.get("sucesso")])
    fases_falharam = len(
        [r for r in resultados_fases.values() if not r.get("sucesso")])

    relatorio = {
        "timestamp_inicio": diagnostico.get("timestamp_diagnostico"),
        "timestamp_fim": datetime.now().isoformat(),
        "diagnostico_inicial": diagnostico,
        "resultados_por_fase": resultados_fases,
        "estatisticas_gerais": {
            "total_contratos_processados": total_processados,
            "total_erros": total_erros,
            "fases_executadas_sucesso": fases_executadas,
            "fases_com_falha": fases_falharam,
            "taxa_sucesso_geral": (total_processados/(total_processados+total_erros)*100) if (total_processados+total_erros) > 0 else 0
        }
    }

    # Log do relatório
    log(f"📈 ESTATÍSTICAS FINAIS:")
    log(f"   🎯 Total processados: {total_processados}")
    log(f"   ❌ Total com erro: {total_erros}")
    log(f"   ✅ Fases bem-sucedidas: {fases_executadas}")
    log(f"   ❌ Fases com falha: {fases_falharam}")
    log(
        f"   📊 Taxa de sucesso geral: {relatorio['estatisticas_gerais']['taxa_sucesso_geral']:.1f}%")

    # Salvar relatório em arquivo
    try:
        relatorio_dir = Path("outputs/relatorios")
        relatorio_dir.mkdir(parents=True, exist_ok=True)

        arquivo_relatorio = relatorio_dir / \
            f"relatorio_sienge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        import json
        with open(arquivo_relatorio, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2, default=str)

        log(f"📄 Relatório salvo: {arquivo_relatorio}")

    except Exception as e:
        log(f"⚠️ Erro ao salvar relatório: {str(e)}")

    return relatorio


async def main():
    """
    MAIN DISRUPTIVO: Execução otimizada do RPA Sienge em produção

    ESTRATÉGIA IMPLEMENTADA:
    - Diagnóstico completo antes de processar
    - Login específico para cada fase
    - Processamento sequencial com fallback robusto
    - Notificações granulares
    - Relatório consolidado
    """
    inicio_execucao = datetime.now()

    log("🤖 RPA SIENGE - PROCESSAMENTO DISRUPTIVO EM PRODUÇÃO")
    log("🚀 NOVA ARQUITETURA: Diagnóstico → Fases otimizadas → Relatório")
    log("✅ CONFORMIDADE PDD: Implementação completa das seções 9.1, 10.1 e 10.2")
    log("=" * 80)

    try:
        # FASE 0: PREPARAÇÃO E DIAGNÓSTICO
        log("🔧 FASE 0: PREPARAÇÃO E DIAGNÓSTICO")
        log("-" * 40)

        credenciais = await carregar_credenciais_sienge()
        indices = await carregar_indices_economicos()
        diagnostico = await diagnosticar_fila_completa()

        # Verificar se há trabalho a fazer
        total_trabalho = (
            diagnostico["por_status"]["PENDENTE"] +
            diagnostico["por_status"]["EXTRAIDO"] +
            diagnostico["por_status"]["REPARCELADO"]
        )

        if total_trabalho == 0:
            log("✅ Nenhum trabalho pendente encontrado - execução desnecessária")
            notificar_sucesso_simples(
                "✅ RPA SIENGE: Execução desnecessária",
                "Todos os contratos já foram processados"
            )
            sys.exit(0)

        log(f"📋 Total de trabalho identificado: {total_trabalho} contratos")

        # EXECUÇÃO DAS FASES CONFORME DIAGNÓSTICO
        resultados_fases = {}

        # FASE 1: EXTRAÇÃO (se necessária)
        if diagnostico["fases_necessarias"]["extracao"]:
            resultado_extracao = await executar_fase_extracao(
                credenciais,
                diagnostico["por_status"]["PENDENTE"]
            )
            resultados_fases["extracao"] = resultado_extracao

            # Se extração falhou completamente, interromper
            if not resultado_extracao["sucesso"]:
                log("❌ Extração falhou - interrompendo processamento")
                raise Exception(
                    f"Falha crítica na extração: {resultado_extracao.get('erro')}")

        # FASE 2: REPARCELAMENTO (se necessária)
        if diagnostico["fases_necessarias"]["reparcelamento"]:
            # Recalcular contratos extraídos (podem ter aumentado na fase 1)
            diagnostico_atualizado = await diagnosticar_fila_completa()
            total_extraidos = diagnostico_atualizado["por_status"]["EXTRAIDO"]

            if total_extraidos > 0:
                resultado_reparcelamento = await executar_fase_reparcelamento(
                    credenciais,
                    indices,
                    total_extraidos
                )
                resultados_fases["reparcelamento"] = resultado_reparcelamento

                # Continuar mesmo se reparcelamento falhar (pode ter processado alguns)
                if not resultado_reparcelamento["sucesso"]:
                    log("⚠️ Reparcelamento falhou - continuando para próxima fase se possível")

        # FASE 3: GERAÇÃO DE CARNÊS (se necessária)
        if diagnostico["fases_necessarias"]["geracao_carnes"]:
            # Recalcular contratos reparcelados (podem ter aumentado na fase 2)
            diagnostico_final = await diagnosticar_fila_completa()
            total_reparcelados = diagnostico_final["por_status"]["REPARCELADO"]
            empresas_info = diagnostico_final["empresas_reparceladas"]

            if total_reparcelados > 0:
                resultado_carnes = await executar_fase_geracao_carnes(
                    credenciais,
                    total_reparcelados,
                    empresas_info
                )
                resultados_fases["geracao_carnes"] = resultado_carnes

                # Continuar mesmo se geração de carnês falhar
                if not resultado_carnes["sucesso"]:
                    log("⚠️ Geração de carnês falhou - finalizando com o que foi processado")

        # RELATÓRIO FINAL E NOTIFICAÇÃO
        relatorio_final = await gerar_relatorio_final(diagnostico, resultados_fases)

        # Determinar sucesso geral
        fases_com_sucesso = len(
            [r for r in resultados_fases.values() if r.get("sucesso")])
        sucesso_geral = fases_com_sucesso > 0  # Pelo menos uma fase teve sucesso

        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        if sucesso_geral:
            log(f"\n🎉 PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
            log(f"⏱️ Duração total: {duracao}")
            log(f"✅ Fases bem-sucedidas: {fases_com_sucesso}/{len(resultados_fases)}")

            notificar_sucesso_simples(
                f"🎉 RPA SIENGE: Processamento concluído",
                f"Duração: {duracao} | Fases: {fases_com_sucesso}/{len(resultados_fases)} | Contratos: {relatorio_final['estatisticas_gerais']['total_contratos_processados']}"
            )

            sys.exit(0)
        else:
            log(f"\n❌ PROCESSAMENTO FALHOU EM TODAS AS FASES")
            log(f"⏱️ Duração: {duracao}")

            notificar_erro_simples(
                f"❌ RPA SIENGE: Falha completa",
                f"Todas as fases falharam - Verifique logs detalhados"
            )

            sys.exit(1)

    except KeyboardInterrupt:
        log("👋 Processamento interrompido pelo usuário")
        notificar_erro_simples(
            "⚠️ RPA SIENGE: Interrompido",
            "Processamento cancelado pelo usuário"
        )
        sys.exit(130)

    except Exception as e:
        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        log(f"💥 ERRO CRÍTICO NO PROCESSAMENTO: {str(e)}")
        log(f"⏱️ Duração até erro: {duracao}")

        notificar_erro_simples(
            f"💥 RPA SIENGE: Erro crítico",
            f"Erro: {str(e)} | Duração: {duracao}"
        )

        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Execução interrompida pelo usuário.")
        sys.exit(130)
    except Exception as e:  # pylint: disable=broad-exception-caught
        log(f"Erro fatal: {e}")
        sys.exit(1)
