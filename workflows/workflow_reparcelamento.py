"""
Workflow Principal de Reparcelamento
Orquestração Temporal.io simplificada em Português Brasileiro

Este workflow coordena os 4 RPAs do sistema de forma sequencial e robusta
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from temporalio import workflow, activity
import structlog

from rpa_coleta_indices.rpa_coleta_indices import executar_coleta_indices
from rpa_analise_planilhas.rpa_analise_planilhas import executar_analise_planilhas
from rpa_sienge.rpa_sienge import executar_processamento_sienge
from rpa_sicredi.rpa_sicredi import executar_processamento_sicredi

logger = structlog.get_logger()

@workflow.defn
class WorkflowReparcelamento:
    """
    Workflow principal que orquestra todo o processo de reparcelamento
    
    Executa os 4 RPAs em sequência:
    1. Coleta de Índices Econômicos (IPCA/IGPM)
    2. Análise de Planilhas (identifica contratos para reajuste)
    3. Processamento Sienge (reparcelamento por contrato)
    4. Processamento Sicredi (upload de carnês atualizados)
    """
    
    @workflow.run
    async def executar_workflow_completo(self, parametros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa workflow completo de reparcelamento
        
        Args:
            parametros: Configurações do workflow contendo:
                - planilha_calculo_id: ID da planilha BASE DE CÁLCULO REPARCELAMENTO
                - planilha_apoio_id: ID da planilha Base de apoio  
                - credenciais_google: Caminho credenciais Google Sheets
                - credenciais_sienge: Dados acesso Sienge (url, usuario, senha)
                - credenciais_sicredi: Dados acesso Sicredi (url, usuario, senha)
                - processar_todos: Se True, processa todos os contratos identificados
        
        Returns:
            Resultado completo do workflow
        """
        try:
            resultado_workflow = {
                "inicio": datetime.now().isoformat(),
                "etapas_concluidas": [],
                "etapas_com_erro": [],
                "resumo_processamento": {}
            }
            
            workflow.logger.info("🚀 Iniciando Workflow de Reparcelamento")
            
            # ETAPA 1: Coleta de Índices Econômicos
            workflow.logger.info("📊 Etapa 1: Coletando índices econômicos")
            
            resultado_indices = await workflow.execute_activity(
                executar_atividade_coleta_indices,
                parametros.get("planilha_calculo_id"),
                parametros.get("credenciais_google"),
                start_to_close_timeout=timedelta(minutes=10)
            )
            
            if not resultado_indices.sucesso:
                raise Exception(f"Falha na coleta de índices: {resultado_indices.erro}")
            
            resultado_workflow["etapas_concluidas"].append("coleta_indices")
            resultado_workflow["resumo_processamento"]["indices_coletados"] = resultado_indices.dados
            
            # ETAPA 2: Análise de Planilhas
            workflow.logger.info("📋 Etapa 2: Analisando planilhas para identificar contratos")
            
            resultado_analise = await workflow.execute_activity(
                executar_atividade_analise_planilhas,
                parametros.get("planilha_calculo_id"),
                parametros.get("planilha_apoio_id"), 
                parametros.get("credenciais_google"),
                start_to_close_timeout=timedelta(minutes=15)
            )
            
            if not resultado_analise.sucesso:
                raise Exception(f"Falha na análise de planilhas: {resultado_analise.erro}")
            
            resultado_workflow["etapas_concluidas"].append("analise_planilhas")
            resultado_workflow["resumo_processamento"]["contratos_identificados"] = resultado_analise.dados
            
            # Obtém lista de contratos para processamento
            contratos_reajuste = resultado_analise.dados.get("detalhes_contratos", [])
            
            if not contratos_reajuste:
                workflow.logger.info("ℹ️ Nenhum contrato identificado para reajuste")
                resultado_workflow["resumo_processamento"]["total_processados"] = 0
                return resultado_workflow
            
            # ETAPA 3: Processamento no Sienge (para cada contrato)
            workflow.logger.info(f"🏢 Etapa 3: Processando {len(contratos_reajuste)} contratos no Sienge")
            
            contratos_processados_sienge = []
            contratos_com_erro_sienge = []
            
            # Decide quantos contratos processar
            processar_todos = parametros.get("processar_todos", False)
            limite_processamento = len(contratos_reajuste) if processar_todos else min(3, len(contratos_reajuste))
            
            for i, contrato in enumerate(contratos_reajuste[:limite_processamento]):
                workflow.logger.info(f"Processando contrato {i+1}/{limite_processamento}: {contrato.get('numero_titulo', '')}")
                
                try:
                    resultado_sienge = await workflow.execute_activity(
                        executar_atividade_processamento_sienge,
                        contrato,
                        resultado_indices.dados,
                        parametros.get("credenciais_sienge"),
                        start_to_close_timeout=timedelta(minutes=20)
                    )
                    
                    if resultado_sienge.sucesso:
                        contratos_processados_sienge.append(resultado_sienge.dados)
                    else:
                        contratos_com_erro_sienge.append({
                            "contrato": contrato,
                            "erro": resultado_sienge.erro
                        })
                        
                except Exception as e:
                    contratos_com_erro_sienge.append({
                        "contrato": contrato,
                        "erro": str(e)
                    })
            
            resultado_workflow["etapas_concluidas"].append("processamento_sienge")
            resultado_workflow["resumo_processamento"]["sienge"] = {
                "processados_com_sucesso": len(contratos_processados_sienge),
                "com_erro": len(contratos_com_erro_sienge),
                "detalhes_processados": contratos_processados_sienge,
                "detalhes_erros": contratos_com_erro_sienge
            }
            
            # ETAPA 4: Processamento no Sicredi (apenas se houver contratos processados)
            if contratos_processados_sienge:
                workflow.logger.info(f"🏦 Etapa 4: Processando {len(contratos_processados_sienge)} arquivos no Sicredi")
                
                resultados_sicredi = []
                
                for processamento in contratos_processados_sienge:
                    arquivo_remessa = processamento.get("carne_gerado", {}).get("nome_arquivo")
                    
                    if arquivo_remessa:
                        try:
                            resultado_sicredi = await workflow.execute_activity(
                                executar_atividade_processamento_sicredi,
                                arquivo_remessa,
                                parametros.get("credenciais_sicredi"),
                                processamento,
                                start_to_close_timeout=timedelta(minutes=15)
                            )
                            
                            resultados_sicredi.append(resultado_sicredi.dados)
                            
                        except Exception as e:
                            workflow.logger.error(f"Erro no processamento Sicredi: {str(e)}")
                
                resultado_workflow["etapas_concluidas"].append("processamento_sicredi")
                resultado_workflow["resumo_processamento"]["sicredi"] = resultados_sicredi
            
            # Finalização
            resultado_workflow["fim"] = datetime.now().isoformat()
            resultado_workflow["duracao_total"] = (
                datetime.fromisoformat(resultado_workflow["fim"]) - 
                datetime.fromisoformat(resultado_workflow["inicio"])
            ).total_seconds()
            
            workflow.logger.info("✅ Workflow de Reparcelamento concluído com sucesso")
            
            return resultado_workflow
            
        except Exception as e:
            workflow.logger.error(f"❌ Erro no Workflow de Reparcelamento: {str(e)}")
            
            resultado_workflow["erro"] = str(e)
            resultado_workflow["fim"] = datetime.now().isoformat()
            
            return resultado_workflow

# Activities (atividades que executam os RPAs)

@activity.defn
async def executar_atividade_coleta_indices(
    planilha_id: str, 
    credenciais_google: str = None
):
    """Atividade para executar RPA de Coleta de Índices"""
    logger.info("Executando RPA Coleta de Índices")
    
    return await executar_coleta_indices(
        planilha_id=planilha_id,
        credenciais_google=credenciais_google
    )

@activity.defn  
async def executar_atividade_analise_planilhas(
    planilha_calculo_id: str,
    planilha_apoio_id: str, 
    credenciais_google: str = None
):
    """Atividade para executar RPA de Análise de Planilhas"""
    logger.info("Executando RPA Análise de Planilhas")
    
    return await executar_analise_planilhas(
        planilha_calculo_id=planilha_calculo_id,
        planilha_apoio_id=planilha_apoio_id,
        credenciais_google=credenciais_google
    )

@activity.defn
async def executar_atividade_processamento_sienge(
    contrato: Dict[str, Any],
    indices_economicos: Dict[str, Any], 
    credenciais_sienge: Dict[str, Any]
):
    """Atividade para executar RPA Sienge"""
    logger.info(f"Executando RPA Sienge para contrato: {contrato.get('numero_titulo', '')}")
    
    return await executar_processamento_sienge(
        contrato=contrato,
        indices_economicos=indices_economicos,
        credenciais_sienge=credenciais_sienge
    )

@activity.defn
async def executar_atividade_processamento_sicredi(
    arquivo_remessa: str,
    credenciais_sicredi: Dict[str, Any],
    dados_processamento: Dict[str, Any] = None
):
    """Atividade para executar RPA Sicredi"""
    logger.info(f"Executando RPA Sicredi para arquivo: {arquivo_remessa}")
    
    return await executar_processamento_sicredi(
        arquivo_remessa=arquivo_remessa,
        credenciais_sicredi=credenciais_sicredi,
        dados_processamento=dados_processamento
    )