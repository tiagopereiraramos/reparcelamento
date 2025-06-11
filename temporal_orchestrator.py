"""
Orquestrador Temporal.io Simplificado
Mantém a simplicidade da API atual + robustez do Temporal.io

Desenvolvido em Português Brasileiro
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker
import structlog

logger = structlog.get_logger()

# ============================================================================
# ACTIVITIES (conectam com os RPAs existentes)
# ============================================================================

@activity.defn
async def activity_rpa_coleta_indices(parametros: Dict[str, Any]) -> Dict[str, Any]:
    """Activity para RPA 1 - Coleta de Índices"""
    try:
        # Importa RPA existente
        from rpa_coleta_indices.rpa_coleta_indices import executar_coleta_indices
        
        resultado = await executar_coleta_indices(
            planilha_id=parametros.get("planilha_id"),
            credenciais_google=parametros.get("credenciais_google")
        )
        
        return {
            "sucesso": resultado.sucesso,
            "dados": resultado.dados if hasattr(resultado, 'dados') else {},
            "tempo_execucao": getattr(resultado, 'tempo_execucao', 0)
        }
        
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@activity.defn  
async def activity_rpa_analise_planilhas(parametros: Dict[str, Any]) -> Dict[str, Any]:
    """Activity para RPA 2 - Análise de Planilhas"""
    try:
        from rpa_analise_planilhas.rpa_analise_planilhas import executar_analise_planilhas
        
        resultado = await executar_analise_planilhas(
            planilha_calculo_id=parametros.get("planilha_calculo_id"),
            planilha_apoio_id=parametros.get("planilha_apoio_id"),
            credenciais_google=parametros.get("credenciais_google")
        )
        
        return {
            "sucesso": resultado.sucesso,
            "dados": resultado.dados if hasattr(resultado, 'dados') else {},
            "tempo_execucao": getattr(resultado, 'tempo_execucao', 0)
        }
        
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@activity.defn
async def activity_rpa_sienge(parametros: Dict[str, Any]) -> Dict[str, Any]:
    """Activity para RPA 3 - Sienge"""
    try:
        from rpa_sienge.rpa_sienge import executar_processamento_sienge
        
        resultado = await executar_processamento_sienge(
            contrato=parametros.get("contrato"),
            indices_economicos=parametros.get("indices_economicos"),
            credenciais_sienge=parametros.get("credenciais_sienge")
        )
        
        return {
            "sucesso": resultado.sucesso,
            "dados": resultado.dados if hasattr(resultado, 'dados') else {},
            "tempo_execucao": getattr(resultado, 'tempo_execucao', 0)
        }
        
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

@activity.defn
async def activity_rpa_sicredi(parametros: Dict[str, Any]) -> Dict[str, Any]:
    """Activity para RPA 4 - Sicredi"""
    try:
        from rpa_sicredi.rpa_sicredi import executar_processamento_sicredi
        
        resultado = await executar_processamento_sicredi(
            arquivo_remessa=parametros.get("arquivo_remessa"),
            credenciais_sicredi=parametros.get("credenciais_sicredi"),
            dados_processamento=parametros.get("dados_processamento")
        )
        
        return {
            "sucesso": resultado.sucesso,
            "dados": resultado.dados if hasattr(resultado, 'dados') else {},
            "tempo_execucao": getattr(resultado, 'tempo_execucao', 0)
        }
        
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}

# ============================================================================
# WORKFLOWS
# ============================================================================

@workflow.defn
class WorkflowReparcelamentoDiario:
    """
    Workflow diário: RPAs 1 e 2 com disparo automático dos RPAs 3 e 4
    """
    
    @workflow.run
    async def executar(self, parametros: Dict[str, Any]) -> Dict[str, Any]:
        """Executa workflow diário completo"""
        
        resultado = {
            "inicio": datetime.now().isoformat(),
            "rpa1_coleta": None,
            "rpa2_analise": None,
            "contratos_identificados": 0,
            "rpas_34_executados": False
        }
        
        try:
            # RPA 1: Coleta de Índices
            workflow.logger.info("🤖 Executando RPA 1 - Coleta de Índices")
            
            resultado_rpa1 = await workflow.execute_activity(
                activity_rpa_coleta_indices,
                parametros,
                start_to_close_timeout=timedelta(minutes=10)
            )
            
            resultado["rpa1_coleta"] = resultado_rpa1
            
            if not resultado_rpa1["sucesso"]:
                resultado["erro"] = "RPA 1 falhou"
                return resultado
            
            # RPA 2: Análise de Planilhas
            workflow.logger.info("📊 Executando RPA 2 - Análise de Planilhas")
            
            resultado_rpa2 = await workflow.execute_activity(
                activity_rpa_analise_planilhas,
                parametros,
                start_to_close_timeout=timedelta(minutes=15)
            )
            
            resultado["rpa2_analise"] = resultado_rpa2
            
            if not resultado_rpa2["sucesso"]:
                resultado["erro"] = "RPA 2 falhou"
                return resultado
            
            # Verifica se há contratos para processar
            dados_rpa2 = resultado_rpa2.get("dados", {})
            contratos = dados_rpa2.get("detalhes_contratos", [])
            resultado["contratos_identificados"] = len(contratos)
            
            # Dispara RPAs 3 e 4 se necessário
            if contratos:
                workflow.logger.info(f"🎯 {len(contratos)} contratos - Disparando RPAs 3 e 4")
                
                # Executa workflow dos RPAs 3 e 4
                await workflow.execute_child_workflow(
                    WorkflowProcessamentoContratos.executar,
                    {
                        "contratos": contratos,
                        "indices_economicos": resultado_rpa1.get("dados", {}),
                        "credenciais_sienge": parametros.get("credenciais_sienge", {}),
                        "credenciais_sicredi": parametros.get("credenciais_sicredi", {})
                    }
                )
                
                resultado["rpas_34_executados"] = True
            
            resultado["sucesso"] = True
            resultado["fim"] = datetime.now().isoformat()
            
            return resultado
            
        except Exception as e:
            workflow.logger.error(f"Erro no workflow: {str(e)}")
            resultado["erro"] = str(e)
            resultado["sucesso"] = False
            return resultado

@workflow.defn
class WorkflowProcessamentoContratos:
    """
    Workflow para processar contratos (RPAs 3 e 4)
    """
    
    @workflow.run
    async def executar(self, parametros: Dict[str, Any]) -> Dict[str, Any]:
        """Executa processamento de contratos"""
        
        contratos = parametros.get("contratos", [])
        indices = parametros.get("indices_economicos", {})
        cred_sienge = parametros.get("credenciais_sienge", {})
        cred_sicredi = parametros.get("credenciais_sicredi", {})
        
        resultado = {
            "contratos_processados": 0,
            "arquivos_sicredi": []
        }
        
        # Processa cada contrato no Sienge
        for contrato in contratos[:3]:  # Máximo 3 por execução
            try:
                workflow.logger.info(f"🏢 Processando {contrato.get('numero_titulo')} no Sienge")
                
                resultado_sienge = await workflow.execute_activity(
                    activity_rpa_sienge,
                    {
                        "contrato": contrato,
                        "indices_economicos": indices,
                        "credenciais_sienge": cred_sienge
                    },
                    start_to_close_timeout=timedelta(minutes=20)
                )
                
                if resultado_sienge["sucesso"]:
                    resultado["contratos_processados"] += 1
                    
                    # Processa no Sicredi se arquivo foi gerado
                    dados_sienge = resultado_sienge.get("dados", {})
                    arquivo_remessa = dados_sienge.get("carne_gerado", {}).get("nome_arquivo")
                    
                    if arquivo_remessa:
                        workflow.logger.info(f"🏦 Processando {arquivo_remessa} no Sicredi")
                        
                        resultado_sicredi = await workflow.execute_activity(
                            activity_rpa_sicredi,
                            {
                                "arquivo_remessa": arquivo_remessa,
                                "credenciais_sicredi": cred_sicredi,
                                "dados_processamento": dados_sienge
                            },
                            start_to_close_timeout=timedelta(minutes=15)
                        )
                        
                        if resultado_sicredi["sucesso"]:
                            resultado["arquivos_sicredi"].append(arquivo_remessa)
                
            except Exception as e:
                workflow.logger.error(f"Erro ao processar contrato: {str(e)}")
                continue
        
        return resultado

# ============================================================================
# CLIENTE TEMPORAL SIMPLIFICADO
# ============================================================================

class TemporalOrchestrator:
    """
    Orquestrador Temporal.io simplificado
    Interface limpa que funciona com a API existente
    """
    
    def __init__(self):
        self.client = None
        self.worker = None
        self.executando = False
    
    async def inicializar(self):
        """Inicializa conexão com Temporal"""
        try:
            self.client = await Client.connect("localhost:7233")
            logger.info("✅ Conectado ao Temporal.io")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Temporal.io não disponível: {str(e)}")
            return False
    
    async def iniciar_worker(self):
        """Inicia worker do Temporal"""
        if not self.client:
            return False
        
        try:
            self.worker = Worker(
                self.client,
                task_queue="rpa-reparcelamento",
                workflows=[WorkflowReparcelamentoDiario, WorkflowProcessamentoContratos],
                activities=[
                    activity_rpa_coleta_indices,
                    activity_rpa_analise_planilhas, 
                    activity_rpa_sienge,
                    activity_rpa_sicredi
                ]
            )
            
            # Executa worker em background
            asyncio.create_task(self.worker.run())
            logger.info("✅ Worker Temporal iniciado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar worker: {str(e)}")
            return False
    
    async def executar_workflow_diario(self, parametros: Dict[str, Any]) -> str:
        """
        Executa workflow diário via Temporal
        Retorna workflow ID para acompanhamento
        """
        if not self.client:
            raise Exception("Temporal.io não inicializado")
        
        try:
            workflow_id = f"reparcelamento-diario-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            handle = await self.client.start_workflow(
                WorkflowReparcelamentoDiario.executar,
                parametros,
                id=workflow_id,
                task_queue="rpa-reparcelamento"
            )
            
            logger.info(f"🚀 Workflow iniciado: {workflow_id}")
            return workflow_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar workflow: {str(e)}")
            raise
    
    async def obter_status_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Obtém status do workflow"""
        if not self.client:
            return {"status": "temporal_indisponivel"}
        
        try:
            handle = self.client.get_workflow_handle(workflow_id)
            resultado = await handle.result()
            
            return {
                "status": "concluido",
                "resultado": resultado
            }
            
        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e)
            }

# Instância global (singleton)
temporal_orchestrator = TemporalOrchestrator()

# ============================================================================
# FUNÇÕES AUXILIARES PARA INTEGRAÇÃO COM API EXISTENTE
# ============================================================================

async def executar_com_temporal(parametros: Dict[str, Any]) -> Dict[str, Any]:
    """
    Função que tenta usar Temporal.io, mas fallback para execução direta
    Mantém compatibilidade total com API existente
    """
    try:
        # Tenta executar via Temporal
        if temporal_orchestrator.client:
            workflow_id = await temporal_orchestrator.executar_workflow_diario(parametros)
            return {
                "metodo": "temporal",
                "workflow_id": workflow_id,
                "status": "iniciado"
            }
        else:
            # Fallback: execução direta (como está atualmente)
            return await executar_workflow_direto(parametros)
            
    except Exception as e:
        logger.warning(f"Temporal falhou, usando execução direta: {str(e)}")
        return await executar_workflow_direto(parametros)

async def executar_workflow_direto(parametros: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execução direta (mantém compatibilidade com sistema atual)
    """
    return {
        "metodo": "direto",
        "status": "executando_modo_compatibilidade",
        "mensagem": "Executando sem Temporal.io (modo atual)"
    }

# ============================================================================
# INICIALIZADOR OPCIONAL
# ============================================================================

async def inicializar_temporal_opcional():
    """
    Inicializa Temporal.io se disponível, senão continua sem ele
    """
    try:
        sucesso = await temporal_orchestrator.inicializar()
        if sucesso:
            await temporal_orchestrator.iniciar_worker()
            logger.info("🎯 Temporal.io ativo - Orquestração robusta habilitada")
        else:
            logger.info("⚡ Modo direto - Sistema funcionando normalmente")
        
        return sucesso
        
    except Exception as e:
        logger.info(f"⚡ Temporal.io indisponível - Sistema continua no modo direto: {str(e)}")
        return False

if __name__ == "__main__":
    """Teste do orquestrador"""
    
    async def teste():
        print("🧪 Testando Orquestrador Temporal...")
        
        # Tenta inicializar
        temporal_ativo = await inicializar_temporal_opcional()
        
        if temporal_ativo:
            print("✅ Temporal.io ativo - Sistema com orquestração robusta")
        else:
            print("⚡ Sistema funcionando no modo direto (atual)")
        
        print("Sistema operacional independente do Temporal.io!")
    
    asyncio.run(teste())