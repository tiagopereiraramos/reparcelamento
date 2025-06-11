"""
MongoDB Manager
Sistema de persistência de dados para os RPAs

Desenvolvido em Português Brasileiro
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import pymongo
import json

logger = logging.getLogger(__name__)

class MongoDBManager:
    """
    Gerenciador MongoDB para persistência dos dados dos RPAs
    """
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or "mongodb://localhost:27017"
        self.database_name = "rpa_reparcelamento"
        self.client = None
        self.database = None
        self.conectado = False
    
    async def conectar(self) -> bool:
        """
        Conecta ao MongoDB
        """
        try:
            self.client = AsyncIOMotorClient(self.connection_string)
            self.database = self.client[self.database_name]
            
            # Teste de conexão
            await self.client.admin.command('ismaster')
            
            self.conectado = True
            logger.info("✅ Conectado ao MongoDB com sucesso")
            
            # Criar índices necessários
            await self._criar_indices()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar MongoDB: {str(e)}")
            self.conectado = False
            return False
    
    async def _criar_indices(self):
        """
        Cria índices necessários nas collections
        """
        try:
            # Índices para execuções
            await self.database.execucoes_rpa.create_index([
                ("nome_rpa", pymongo.ASCENDING),
                ("timestamp_inicio", pymongo.DESCENDING)
            ])
            
            # Índices para contratos
            await self.database.contratos_processados.create_index([
                ("numero_titulo", pymongo.ASCENDING),
                ("data_processamento", pymongo.DESCENDING)
            ])
            
            # Índices para fila de processamento Sienge
            await self.database.fila_processamento_sienge.create_index([
                ("timestamp_criacao", pymongo.DESCENDING),
                ("contratos.numero_titulo", pymongo.ASCENDING)
            ])
            
            # Índices para fila de reparcelamento
            await self.database.fila_reparcelamento.create_index([
                ("timestamp_identificacao", pymongo.DESCENDING),
                ("numero_titulo", pymongo.ASCENDING),
                ("status_processamento", pymongo.ASCENDING)
            ])
            
            # Índices para índices econômicos
            await self.database.indices_economicos.create_index([
                ("tipo_indice", pymongo.ASCENDING),
                ("data_coleta", pymongo.DESCENDING)
            ])
            
            # Índices para planilhas extraídas (auditoria)
            await self.database.planilhas_extraidas.create_index([
                ("numero_titulo", pymongo.ASCENDING),
                ("data_extracao", pymongo.DESCENDING)
            ])
            
            await self.database.planilhas_extraidas.create_index([
                ("cliente", pymongo.ASCENDING),
                ("data_extracao", pymongo.DESCENDING)
            ])
            
            await self.database.planilhas_extraidas.create_index([
                ("origem_sistema", pymongo.ASCENDING),
                ("status_auditoria", pymongo.ASCENDING)
            ])
            
            logger.info("✅ Índices MongoDB criados")
            
        except Exception as e:
            logger.error(f"⚠️ Erro ao criar índices: {str(e)}")
    
    async def salvar_execucao_rpa(self, nome_rpa: str, parametros: Dict[str, Any], 
                                 resultado: Dict[str, Any]) -> str:
        """
        Salva execução de RPA no MongoDB
        
        Returns:
            ID da execução salva
        """
        if not self.conectado:
            await self.conectar()
        
        try:
            documento = {
                "nome_rpa": nome_rpa,
                "timestamp_inicio": datetime.now(),
                "timestamp_fim": datetime.now(),
                "parametros_entrada": parametros,
                "resultado": resultado,
                "sucesso": resultado.get("sucesso", False),
                "tempo_execucao_segundos": resultado.get("tempo_execucao", 0),
                "mensagem": resultado.get("mensagem", ""),
                "erro": resultado.get("erro", None)
            }
            
            result = await self.database.execucoes_rpa.insert_one(documento)
            
            logger.info(f"💾 Execução {nome_rpa} salva no MongoDB: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar execução: {str(e)}")
            return None
    
    async def obter_execucoes_recentes(self, limite: int = 30) -> List[Dict[str, Any]]:
        """
        Obtém execuções recentes dos RPAs
        """
        if not self.conectado:
            await self.conectar()
        
        try:
            cursor = self.database.execucoes_rpa.find().sort(
                "timestamp_inicio", pymongo.DESCENDING
            ).limit(limite)
            
            execucoes = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])  # Converter ObjectId para string
                execucoes.append(doc)
            
            return execucoes
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter execuções: {str(e)}")
            return []
    
    async def salvar_indices_economicos(self, indices_data: Dict[str, Any]) -> str:
        """
        Salva índices econômicos coletados
        """
        if not self.conectado:
            await self.conectar()
        
        try:
            # Salvar IPCA
            if "ipca" in indices_data:
                doc_ipca = {
                    "tipo_indice": "IPCA",
                    "valor": indices_data["ipca"]["valor"],
                    "fonte": indices_data["ipca"]["fonte"],
                    "data_coleta": datetime.now(),
                    "periodo": "acumulado_12_meses",
                    "metodo_coleta": indices_data["ipca"].get("metodo", "webscraping")
                }
                await self.database.indices_economicos.insert_one(doc_ipca)
            
            # Salvar IGPM
            if "igpm" in indices_data:
                doc_igpm = {
                    "tipo_indice": "IGPM",
                    "valor": indices_data["igpm"]["valor"],
                    "fonte": indices_data["igpm"]["fonte"],
                    "data_coleta": datetime.now(),
                    "periodo": "acumulado_12_meses",
                    "metodo_coleta": indices_data["igpm"].get("metodo", "webscraping")
                }
                await self.database.indices_economicos.insert_one(doc_igpm)
            
            logger.info("💾 Índices econômicos salvos no MongoDB")
            return "success"
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar índices: {str(e)}")
            return None
    
    async def obter_indices_historico(self, dias: int = 30) -> Dict[str, List]:
        """
        Obtém histórico de índices econômicos
        """
        if not self.conectado:
            await self.conectar()
        
        try:
            data_limite = datetime.now() - timedelta(days=dias)
            
            # IPCA
            cursor_ipca = self.database.indices_economicos.find({
                "tipo_indice": "IPCA",
                "data_coleta": {"$gte": data_limite}
            }).sort("data_coleta", pymongo.DESCENDING)
            
            ipca_historico = []
            async for doc in cursor_ipca:
                doc["_id"] = str(doc["_id"])
                ipca_historico.append(doc)
            
            # IGPM
            cursor_igpm = self.database.indices_economicos.find({
                "tipo_indice": "IGPM", 
                "data_coleta": {"$gte": data_limite}
            }).sort("data_coleta", pymongo.DESCENDING)
            
            igpm_historico = []
            async for doc in cursor_igpm:
                doc["_id"] = str(doc["_id"])
                igpm_historico.append(doc)
            
            return {
                "ipca": ipca_historico,
                "igpm": igpm_historico
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter histórico: {str(e)}")
            return {"ipca": [], "igpm": []}
    
    async def salvar_contrato_processado(self, contrato_data: Dict[str, Any]) -> str:
        """
        Salva dados de contrato processado
        """
        if not self.conectado:
            await self.conectar()
        
        try:
            documento = {
                "numero_titulo": contrato_data.get("numero_titulo"),
                "cliente": contrato_data.get("cliente"),
                "empreendimento": contrato_data.get("empreendimento"),
                "data_processamento": datetime.now(),
                "status_sienge": contrato_data.get("status_sienge", "processado"),
                "status_sicredi": contrato_data.get("status_sicredi", "pendente"),
                "saldo_anterior": contrato_data.get("saldo_anterior", 0),
                "saldo_novo": contrato_data.get("saldo_novo", 0),
                "indice_aplicado": contrato_data.get("indice_aplicado", 0),
                "indexador": contrato_data.get("indexador", ""),
                "dados_completos": contrato_data
            }
            
            # Upsert baseado no número do título
            result = await self.database.contratos_processados.replace_one(
                {"numero_titulo": documento["numero_titulo"]},
                documento,
                upsert=True
            )
            
            logger.info(f"💾 Contrato {documento['numero_titulo']} salvo no MongoDB")
            return str(result.upserted_id) if result.upserted_id else "updated"
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar contrato: {str(e)}")
            return None
    
    async def obter_estatisticas_dashboard(self) -> Dict[str, Any]:
        """
        Obtém estatísticas para o dashboard
        """
        if not self.conectado:
            await self.conectar()
        
        try:
            # Total de execuções
            total_execucoes = await self.database.execucoes_rpa.count_documents({})
            
            # Execuções hoje
            hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            execucoes_hoje = await self.database.execucoes_rpa.count_documents({
                "timestamp_inicio": {"$gte": hoje}
            })
            
            # Taxa de sucesso últimos 30 dias
            data_limite = datetime.now() - timedelta(days=30)
            cursor_recentes = self.database.execucoes_rpa.find({
                "timestamp_inicio": {"$gte": data_limite}
            })
            
            total_recentes = 0
            sucessos_recentes = 0
            
            async for doc in cursor_recentes:
                total_recentes += 1
                if doc.get("sucesso"):
                    sucessos_recentes += 1
            
            taxa_sucesso = (sucessos_recentes / total_recentes * 100) if total_recentes > 0 else 0
            
            # Contratos processados últimos 30 dias
            contratos_processados = await self.database.contratos_processados.count_documents({
                "data_processamento": {"$gte": data_limite}
            })
            
            return {
                "total_execucoes": total_execucoes,
                "execucoes_hoje": execucoes_hoje,
                "taxa_sucesso": round(taxa_sucesso, 1),
                "contratos_processados_mes": contratos_processados,
                "ultima_atualizacao": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas: {str(e)}")
            return {}
    
    async def obter_planilhas_cliente(self, numero_titulo: str = None, cliente: str = None, 
                                     limite: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém planilhas extraídas de um cliente específico para auditoria
        """
        if not self.conectado:
            await self.conectar()
        
        try:
            # Monta filtro
            filtro = {"status_auditoria": "ativo"}
            if numero_titulo:
                filtro["numero_titulo"] = numero_titulo
            if cliente:
                filtro["cliente"] = {"$regex": cliente, "$options": "i"}
            
            cursor = self.database.planilhas_extraidas.find(filtro).sort(
                "data_extracao", pymongo.DESCENDING
            ).limit(limite)
            
            planilhas = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                # Verifica se arquivo ainda existe
                doc["arquivo_existe"] = Path(doc.get("caminho_arquivo", "")).exists()
                planilhas.append(doc)
            
            return planilhas
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter planilhas do cliente: {str(e)}")
            return []

    async def obter_estatisticas_planilhas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas das planilhas extraídas para dashboard
        """
        if not self.conectado:
            await self.conectar()
        
        try:
            # Total de planilhas
            total_planilhas = await self.database.planilhas_extraidas.count_documents({
                "status_auditoria": "ativo"
            })
            
            # Planilhas hoje
            hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            planilhas_hoje = await self.database.planilhas_extraidas.count_documents({
                "data_extracao": {"$gte": hoje},
                "status_auditoria": "ativo"
            })
            
            # Últimos 7 dias
            data_limite = datetime.now() - timedelta(days=7)
            planilhas_semana = await self.database.planilhas_extraidas.count_documents({
                "data_extracao": {"$gte": data_limite},
                "status_auditoria": "ativo"
            })
            
            # Clientes únicos com planilhas
            pipeline = [
                {"$match": {"status_auditoria": "ativo"}},
                {"$group": {"_id": "$cliente"}},
                {"$count": "total"}
            ]
            
            resultado_clientes = await self.database.planilhas_extraidas.aggregate(pipeline).to_list(1)
            clientes_unicos = resultado_clientes[0]["total"] if resultado_clientes else 0
            
            return {
                "total_planilhas": total_planilhas,
                "planilhas_hoje": planilhas_hoje,
                "planilhas_semana": planilhas_semana,
                "clientes_unicos": clientes_unicos,
                "ultima_atualizacao": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter estatísticas de planilhas: {str(e)}")
            return {}

    async def marcar_planilha_inativa(self, planilha_id: str) -> bool:
        """
        Marca planilha como inativa (para exclusão lógica)
        """
        if not self.conectado:
            await self.conectar()
        
        try:
            from bson import ObjectId
            result = await self.database.planilhas_extraidas.update_one(
                {"_id": ObjectId(planilha_id)},
                {
                    "$set": {
                        "status_auditoria": "inativo",
                        "data_inativacao": datetime.now()
                    }
                }
            )
            
            logger.info(f"📋 Planilha {planilha_id} marcada como inativa")
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"❌ Erro ao marcar planilha como inativa: {str(e)}")
            return False

    async def desconectar(self):
        """
        Desconecta do MongoDB
        """
        if self.client:
            self.client.close()
            self.conectado = False
            logger.info("🔌 Desconectado do MongoDB")

# Instância global do MongoDB Manager
mongodb_manager = MongoDBManager()

# Funções auxiliares para facilitar uso
async def salvar_execucao(nome_rpa: str, parametros: Dict[str, Any], resultado: Dict[str, Any]) -> str:
    """Função auxiliar para salvar execução"""
    return await mongodb_manager.salvar_execucao_rpa(nome_rpa, parametros, resultado)

async def obter_execucoes_recentes(limite: int = 30) -> List[Dict[str, Any]]:
    """Função auxiliar para obter execuções recentes"""
    return await mongodb_manager.obter_execucoes_recentes(limite)

async def salvar_indices_economicos(indices_data: Dict[str, Any]) -> str:
    """Função auxiliar para salvar índices"""
    return await mongodb_manager.salvar_indices_economicos(indices_data)

async def obter_estatisticas_dashboard() -> Dict[str, Any]:
    """Função auxiliar para estatísticas do dashboard"""
    return await mongodb_manager.obter_estatisticas_dashboard()