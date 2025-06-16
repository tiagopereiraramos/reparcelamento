"""
The code has been modified to load environment variables from a .env file and use them as defaults for planilha and credentials configurations in the API endpoints for enhanced flexibility and security.
"""
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import structlog
from dotenv import load_dotenv

load_dotenv()

# Importa os 4 RPAs refatorados
from rpa_coleta_indices.rpa_coleta_indices import executar_coleta_indices
from rpa_analise_planilhas.rpa_analise_planilhas import executar_analise_planilhas
from rpa_sienge.rpa_sienge import executar_processamento_sienge
from rpa_sicredi.rpa_sicredi import executar_processamento_sicredi

# Configuração de logs
logger = structlog.get_logger()

# FastAPI app
app = FastAPI(
    title="Sistema RPA de Reparcelamento",
    description="API REST para orquestração dos 4 RPAs de reparcelamento",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class ParametrosWorkflow(BaseModel):
    """Parâmetros para executar workflow completo"""
    planilha_calculo_id: str = Field(..., description="ID da planilha BASE DE CÁLCULO REPARCELAMENTO")
    planilha_apoio_id: str = Field(..., description="ID da planilha Base de apoio")
    processar_todos: bool = Field(False, description="Se True, processa todos os contratos identificados")
    credenciais_google: Optional[str] = Field(None, description="Caminho para credenciais Google Sheets")

class ParametrosColetaIndices(BaseModel):
    """Parâmetros para RPA Coleta de Índices"""
    planilha_id: str = Field(..., description="ID da planilha para atualizar")
    credenciais_google: Optional[str] = Field(None, description="Caminho para credenciais Google Sheets")

class ParametrosAnalisePlanilhas(BaseModel):
    """Parâmetros para RPA Análise de Planilhas"""
    planilha_calculo_id: str = Field(..., description="ID da planilha BASE DE CÁLCULO REPARCELAMENTO")
    planilha_apoio_id: str = Field(..., description="ID da planilha Base de apoio")
    credenciais_google: Optional[str] = Field(None, description="Caminho para credenciais Google Sheets")

class ParametrosSienge(BaseModel):
    """Parâmetros para RPA Sienge"""
    contrato: Dict[str, Any] = Field(..., description="Dados do contrato para processar")
    indices_economicos: Dict[str, Any] = Field(..., description="Índices IPCA/IGPM atualizados")
    credenciais_sienge: Dict[str, str] = Field(..., description="Credenciais Sienge (url, usuario, senha)")

class ParametrosSicredi(BaseModel):
    """Parâmetros para RPA Sicredi"""
    arquivo_remessa: str = Field(..., description="Caminho do arquivo de remessa")
    credenciais_sicredi: Dict[str, str] = Field(..., description="Credenciais Sicredi (url, usuario, senha)")
    dados_processamento: Optional[Dict[str, Any]] = Field(None, description="Dados do processamento anterior")

class RespostaAPI(BaseModel):
    """Resposta padrão da API"""
    sucesso: bool
    mensagem: str
    dados: Optional[Dict[str, Any]] = None
    erro: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# ============================================================================
# STORAGE SIMPLES PARA EXECUÇÕES EM ANDAMENTO
# ============================================================================

execucoes_ativas: Dict[str, Dict[str, Any]] = {}

def gerar_id_execucao() -> str:
    """Gera ID único para execução"""
    return f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

def salvar_execucao(execucao_id: str, dados: Dict[str, Any]):
    """Salva dados da execução"""
    execucoes_ativas[execucao_id] = dados

def obter_execucao(execucao_id: str) -> Optional[Dict[str, Any]]:
    """Obtém dados da execução"""
    return execucoes_ativas.get(execucao_id)

# ============================================================================
# ENDPOINTS PRINCIPAIS
# ============================================================================

@app.get("/", response_model=RespostaAPI)
async def root():
    """Endpoint raiz com informações do sistema"""
    return RespostaAPI(
        sucesso=True,
        mensagem="Sistema RPA de Reparcelamento v2.0 - Arquitetura Refatorada",
        dados={
            "versao": "2.0.0",
            "rpas_disponveis": [
                "Coleta de Índices Econômicos",
                "Análise de Planilhas", 
                "Processamento Sienge",
                "Processamento Sicredi"
            ],
            "status": "online",
            "execucoes_ativas": len(execucoes_ativas)
        }
    )

@app.get("/health", response_model=RespostaAPI)
async def health_check():
    """Health check do sistema"""
    return RespostaAPI(
        sucesso=True,
        mensagem="Sistema funcionando corretamente",
        dados={
            "status": "healthy",
            "memoria_execucoes": len(execucoes_ativas),
            "timestamp_verificacao": datetime.now().isoformat()
        }
    )

# ============================================================================
# WORKFLOW COMPLETO
# ============================================================================

@app.post("/workflow/reparcelamento", response_model=RespostaAPI)
async def executar_workflow_reparcelamento(
    parametros: ParametrosWorkflow,
    background_tasks: BackgroundTasks
):
    """
    Executa workflow completo de reparcelamento (4 RPAs em sequência)
    """
    try:
        execucao_id = gerar_id_execucao()

        # Salva execução como iniciada
        salvar_execucao(execucao_id, {
            "status": "iniciado",
            "etapa_atual": "preparando",
            "inicio": datetime.now().isoformat(),
            "parametros": parametros.dict()
        })

        # Executa workflow em background
        background_tasks.add_task(
            executar_workflow_background,
            execucao_id,
            parametros
        )

        return RespostaAPI(
            sucesso=True,
            mensagem="Workflow de reparcelamento iniciado com sucesso",
            dados={
                "execucao_id": execucao_id,
                "status": "em_execucao",
                "endpoint_status": f"/workflow/status/{execucao_id}"
            }
        )

    except Exception as e:
        logger.error(f"Erro ao iniciar workflow: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/workflow/status/{execucao_id}", response_model=RespostaAPI)
async def obter_status_workflow(execucao_id: str):
    """
    Obtém status de execução do workflow
    """
    execucao = obter_execucao(execucao_id)

    if not execucao:
        raise HTTPException(status_code=404, detail="Execução não encontrada")

    return RespostaAPI(
        sucesso=True,
        mensagem=f"Status da execução {execucao_id}",
        dados=execucao
    )

async def executar_workflow_background(execucao_id: str, parametros: ParametrosWorkflow):
    """
    Executa workflow completo em background
    """
    try:
        # Atualiza status
        execucao = obter_execucao(execucao_id)
        execucao["etapa_atual"] = "rpa_coleta_indices"
        execucao["etapas_concluidas"] = []

        # ETAPA 1: Coleta de Índices
        logger.info(f"[{execucao_id}] Executando RPA Coleta de Índices")
        resultado_indices = await executar_coleta_indices(
            planilha_id=parametros.planilha_calculo_id,
            credenciais_google=parametros.credenciais_google
        )

        if not resultado_indices.sucesso:
            execucao["status"] = "erro"
            execucao["erro"] = f"Falha na coleta de índices: {resultado_indices.erro}"
            return

        execucao["etapas_concluidas"].append("coleta_indices")
        execucao["resultado_indices"] = resultado_indices.dados
        execucao["etapa_atual"] = "rpa_analise_planilhas"

        # ETAPA 2: Análise de Planilhas
        logger.info(f"[{execucao_id}] Executando RPA Análise de Planilhas")
        resultado_analise = await executar_analise_planilhas(
            planilha_calculo_id=parametros.planilha_calculo_id,
            planilha_apoio_id=parametros.planilha_apoio_id,
            credenciais_google=parametros.credenciais_google
        )

        if not resultado_analise.sucesso:
            execucao["status"] = "erro"
            execucao["erro"] = f"Falha na análise de planilhas: {resultado_analise.erro}"
            return

        execucao["etapas_concluidas"].append("analise_planilhas")
        execucao["resultado_analise"] = resultado_analise.dados

        # Verifica se há contratos para processar
        contratos_reajuste = resultado_analise.dados.get("detalhes_contratos", [])

        if not contratos_reajuste:
            execucao["status"] = "concluido"
            execucao["mensagem"] = "Workflow concluído - Nenhum contrato identificado para reajuste"
            execucao["fim"] = datetime.now().isoformat()
            return

        # ETAPA 3: Processamento Sienge
        execucao["etapa_atual"] = "rpa_sienge"
        contratos_processados = []

        limite = len(contratos_reajuste) if parametros.processar_todos else min(3, len(contratos_reajuste))

        for i, contrato in enumerate(contratos_reajuste[:limite]):
            logger.info(f"[{execucao_id}] Processando contrato {i+1}/{limite} no Sienge")

            # Obtém credenciais Sienge das variáveis de ambiente
            credenciais_sienge = {
                "url": os.getenv("SIENGE_URL", ""),
                "usuario": os.getenv("SIENGE_USERNAME", ""),
                "senha": os.getenv("SIENGE_PASSWORD", "")
            }

            # Criar instância do RPA Sienge
            # rpa_sienge = RPASienge()

            resultado_sienge = await executar_processamento_sienge(
                contrato=contrato,
                indices_economicos=resultado_indices.dados,
                credenciais_sienge=credenciais_sienge
            )

            if resultado_sienge.sucesso:
                contratos_processados.append(resultado_sienge.dados)

        execucao["etapas_concluidas"].append("processamento_sienge")
        execucao["contratos_processados_sienge"] = contratos_processados

        # ETAPA 4: Processamento Sicredi (se houver contratos processados)
        if contratos_processados:
            execucao["etapa_atual"] = "rpa_sicredi"
            resultados_sicredi = []

            credenciais_sicredi = {
                "url": os.getenv("SICREDI_URL", ""),
                "usuario": os.getenv("SICREDI_USERNAME", ""),
                "senha": os.getenv("SICREDI_PASSWORD", "")
            }

            for processamento in contratos_processados:
                arquivo_remessa = processamento.get("carne_gerado", {}).get("nome_arquivo")

                if arquivo_remessa:
                    resultado_sicredi = await executar_processamento_sicredi(
                        arquivo_remessa=arquivo_remessa,
                        credenciais_sicredi=credenciais_sicredi,
                        dados_processamento=processamento
                    )

                    if resultado_sicredi.sucesso:
                        resultados_sicredi.append(resultado_sicredi.dados)

            execucao["etapas_concluidas"].append("processamento_sicredi")
            execucao["resultados_sicredi"] = resultados_sicredi

        # Finalização
        execucao["status"] = "concluido"
        execucao["fim"] = datetime.now().isoformat()
        execucao["mensagem"] = f"Workflow concluído com sucesso - {len(contratos_processados)} contratos processados"

        logger.info(f"[{execucao_id}] Workflow concluído com sucesso")

    except Exception as e:
        logger.error(f"[{execucao_id}] Erro no workflow: {str(e)}")
        execucao = obter_execucao(execucao_id)
        execucao["status"] = "erro"
        execucao["erro"] = str(e)
        execucao["fim"] = datetime.now().isoformat()

# ============================================================================
# ENDPOINTS INDIVIDUAIS DOS RPAS
# ============================================================================

@app.post("/rpa/coleta-indices", response_model=RespostaAPI)
async def executar_rpa_coleta_indices(parametros: ParametrosColetaIndices):
    """
    Executa apenas o RPA de Coleta de Índices Econômicos
    """
    try:
        # Configuração da planilha via variáveis de ambiente
        parametros_dict = parametros.dict()
        planilha_id = parametros_dict.get("planilha_id") or os.getenv("PLANILHA_INDICES_ID") or os.getenv("PLANILHA_CALCULO_ID", "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk")
        credenciais_google = parametros_dict.get("credenciais_google") or os.getenv("GOOGLE_CREDENTIALS_PATH", "./gspread-credentials.json")
        resultado = await executar_coleta_indices(
            planilha_id=planilha_id,
            credenciais_google=credenciais_google
        )

        return RespostaAPI(
            sucesso=resultado.sucesso,
            mensagem=resultado.mensagem,
            dados=resultado.dados,
            erro=resultado.erro
        )

    except Exception as e:
        logger.error(f"Erro no RPA Coleta de Índices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/rpa/analise-planilhas", response_model=RespostaAPI)
async def executar_rpa_analise_planilhas(parametros: ParametrosAnalisePlanilhas):
    """
    Executa apenas o RPA de Análise de Planilhas
    """
    try:
        # Configuração das planilhas via variáveis de ambiente
        parametros_dict = parametros.dict()
        planilha_calculo_id = parametros_dict.get("planilha_calculo_id") or os.getenv("PLANILHA_CALCULO_ID", "1NTDPDEltum8X3vBHvUetCNWVEcz453FfAZGRYGmmd8U")
        planilha_apoio_id = parametros_dict.get("planilha_apoio_id") or os.getenv("PLANILHA_APOIO_ID", "1f723KXu5_KooZNHiYIB3EettKb-hUsOzDYMg7LNC_hk")
        credenciais_google = parametros_dict.get("credenciais_google") or os.getenv("GOOGLE_CREDENTIALS_PATH", "./gspread-credentials.json")


        resultado = await executar_analise_planilhas(
            planilha_calculo_id=planilha_calculo_id,
            planilha_apoio_id=planilha_apoio_id,
            credenciais_google=credenciais_google
        )

        return RespostaAPI(
            sucesso=resultado.sucesso,
            mensagem=resultado.mensagem,
            dados=resultado.dados,
            erro=resultado.erro
        )

    except Exception as e:
        logger.error(f"Erro no RPA Análise de Planilhas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/rpa/sienge", response_model=RespostaAPI)
async def executar_rpa_sienge(parametros: ParametrosSienge):
    """
    Executa apenas o RPA de Processamento Sienge
    """
    try:
        resultado = await executar_processamento_sienge(
            contrato=parametros.contrato,
            indices_economicos=parametros.indices_economicos,
            credenciais_sienge=parametros.credenciais_sienge
        )

        return RespostaAPI(
            sucesso=resultado.sucesso,
            mensagem=resultado.mensagem,
            dados=resultado.dados,
            erro=resultado.erro
        )

    except Exception as e:
        logger.error(f"Erro no RPA Sienge: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.post("/rpa/sicredi", response_model=RespostaAPI)
async def executar_rpa_sicredi(parametros: ParametrosSicredi):
    """
    Executa apenas o RPA de Processamento Sicredi
    """
    try:
        resultado = await executar_processamento_sicredi(
            arquivo_remessa=parametros.arquivo_remessa,
            credenciais_sicredi=parametros.credenciais_sicredi,
            dados_processamento=parametros.dados_processamento
        )

        return RespostaAPI(
            sucesso=resultado.sucesso,
            mensagem=resultado.mensagem,
            dados=resultado.dados,
            erro=resultado.erro
        )

    except Exception as e:
        logger.error(f"Erro no RPA Sicredi: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# ============================================================================
# ENDPOINTS DE MONITORAMENTO
# ============================================================================

@app.get("/execucoes", response_model=RespostaAPI)
async def listar_execucoes():
    """
    Lista todas as execuções ativas na memória
    """
    return RespostaAPI(
        sucesso=True,
        mensagem=f"Total de {len(execucoes_ativas)} execuções na memória",
        dados={
            "total": len(execucoes_ativas),
            "execucoes": list(execucoes_ativas.keys()),
            "detalhes": execucoes_ativas
        }
    )

@app.delete("/execucoes/{execucao_id}", response_model=RespostaAPI)
async def limpar_execucao(execucao_id: str):
    """
    Remove execução da memória
    """
    if execucao_id in execucoes_ativas:
        del execucoes_ativas[execucao_id]
        return RespostaAPI(
            sucesso=True,
            mensagem=f"Execução {execucao_id} removida da memória"
        )
    else:
        raise HTTPException(status_code=404, detail="Execução não encontrada")

@app.delete("/execucoes", response_model=RespostaAPI)
async def limpar_todas_execucoes():
    """
    Limpa todas as execuções da memória
    """
    total = len(execucoes_ativas)
    execucoes_ativas.clear()

    return RespostaAPI(
        sucesso=True,
        mensagem=f"{total} execuções removidas da memória",
        dados={"execucoes_removidas": total}
    )

# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Inicia servidor da API
    """
    print("🚀 Iniciando API do Sistema RPA de Reparcelamento v2.0")
    print("📋 Arquitetura Refatorada - 4 RPAs Independentes")
    print("🌐 Documentação: http://localhost:5000/docs")
    print("=" * 60)

    uvicorn.run(
        "api_rpa:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()