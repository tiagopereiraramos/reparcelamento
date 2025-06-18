
"""
MongoDB Manager - Sistema RPA v2.0
Gerenciador de conexão e operações MongoDB usando PyMongo com executor assíncrono

Desenvolvido em Português Brasileiro
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import concurrent.futures

logger = logging.getLogger(__name__)


class MongoDBManager:
    """
    Gerenciador unificado para operações MongoDB
    """

    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.database = None
        self.conectado = False
        self._url_conexao = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    async def conectar(self) -> bool:
        """
        Conecta ao MongoDB usando variáveis de ambiente do Replit
        """
        try:
            logger.info("🔧 Iniciando conexão MongoDB...")
            
            # Tenta variáveis do Replit Database primeiro
            mongodb_uri = os.getenv('DATABASE_URL') or os.getenv('MONGODB_URI') or os.getenv('MONGO_URL')
            database_name = os.getenv('DATABASE_NAME', 'sistema_rpa')
            
            logger.info(f"🔍 Variáveis de ambiente:")
            logger.info(f"   DATABASE_URL: {'SET' if os.getenv('DATABASE_URL') else 'NOT SET'}")
            logger.info(f"   MONGODB_URI: {'SET' if os.getenv('MONGODB_URI') else 'NOT SET'}")
            logger.info(f"   MONGO_URL: {'SET' if os.getenv('MONGO_URL') else 'NOT SET'}")
            logger.info(f"   DATABASE_NAME: {database_name}")
            
            if not mongodb_uri:
                # Fallback para conexão local se não tiver Replit Database
                mongodb_uri = "mongodb://localhost:27017"
                logger.warning("⚠️ Usando MongoDB local - configure DATABASE_URL para produção")
            else:
                # Log da URI mascarada (sem senha)
                uri_masked = mongodb_uri
                if '@' in uri_masked:
                    parts = uri_masked.split('@')
                    if len(parts) > 1:
                        credentials = parts[0].split('//')[-1]
                        if ':' in credentials:
                            user = credentials.split(':')[0]
                            uri_masked = uri_masked.replace(credentials, f"{user}:***")
                logger.info(f"   URI: {uri_masked}")

            self._url_conexao = mongodb_uri
            
            logger.info("🔌 Criando cliente MongoDB...")
            # Configura cliente com timeout menor para falhar rápido
            self.client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=5000,  # 5 segundos
                connectTimeoutMS=5000,
                socketTimeoutMS=10000
            )

            logger.info("🏓 Testando conexão com ping...")
            # Testa conexão de forma síncrona em executor
            def _test_connection():
                ping_result = self.client.admin.command('ping')
                return ping_result
            
            ping_result = await asyncio.get_event_loop().run_in_executor(
                self.executor, _test_connection
            )
            logger.info(f"✅ Ping successful: {ping_result}")
            
            logger.info(f"🗄️ Configurando database: {database_name}")
            # Define database
            self.database = self.client[database_name]
            
            # Teste prático com a database
            logger.info("🧪 Testando operação na database...")
            def _test_database():
                test_collection = self.database.teste_conexao_inicial
                test_doc = {"teste": True, "timestamp": datetime.now()}
                result = test_collection.insert_one(test_doc)
                # Remove documento de teste
                test_collection.delete_one({"_id": result.inserted_id})
                return result.inserted_id
            
            test_id = await asyncio.get_event_loop().run_in_executor(
                self.executor, _test_database
            )
            logger.info(f"✅ Teste inserção: {test_id}")
            logger.info("🧹 Documento de teste removido")
            
            self.conectado = True
            logger.info(f"✅ MongoDB conectado com sucesso: {database_name}")
            
            # Cria índices necessários
            logger.info("📊 Criando índices...")
            await self._criar_indices()
            
            logger.info("🎉 MongoDB totalmente inicializado!")
            return True

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"⚠️ MongoDB não disponível (timeout): {str(e)}")
            self.conectado = False
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao conectar MongoDB: {str(e)}")
            logger.error(f"   Tipo do erro: {type(e).__name__}")
            import traceback
            logger.error(f"   Traceback completo: {traceback.format_exc()}")
            self.conectado = False
            return False

    async def _criar_indices(self):
        """Cria índices necessários nas collections"""
        try:
            def _create_indexes():
                # Índices para execucoes_rpa
                self.database.execucoes_rpa.create_index("nome_rpa")
                self.database.execucoes_rpa.create_index("timestamp_inicio")
                self.database.execucoes_rpa.create_index("sucesso")

                # Índices para indices_economicos
                self.database.indices_economicos.create_index("timestamp_coleta")
                self.database.indices_economicos.create_index("fonte_coleta")

                # Índices para contratos_processados
                self.database.contratos_processados.create_index("numero_titulo")
                self.database.contratos_processados.create_index("data_processamento")
                self.database.contratos_processados.create_index("status_sienge")

            await asyncio.get_event_loop().run_in_executor(
                self.executor, _create_indexes
            )
            logger.debug("📊 Índices MongoDB criados com sucesso")

        except Exception as e:
            logger.warning(f"⚠️ Erro ao criar índices: {str(e)}")

    async def salvar_execucao_rpa(self, nome_rpa: str, parametros: Dict[str, Any], 
                                  resultado: Dict[str, Any]) -> Optional[str]:
        """
        Salva execução de RPA no MongoDB
        
        Returns:
            ID do documento inserido ou None se falhou
        """
        if not self.conectado:
            logger.warning("⚠️ MongoDB não conectado - não pode salvar execução")
            return None

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

            def _save_execution():
                result = self.database.execucoes_rpa.insert_one(documento)
                return str(result.inserted_id)

            document_id = await asyncio.get_event_loop().run_in_executor(
                self.executor, _save_execution
            )
            
            logger.info(f"📊 Execução {nome_rpa} salva no MongoDB: {document_id}")
            return document_id

        except Exception as e:
            logger.error(f"❌ Erro ao salvar execução no MongoDB: {str(e)}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return None

    async def salvar_indices_economicos(self, indices_data: Dict[str, Any]) -> Optional[str]:
        """
        Salva índices econômicos no MongoDB
        
        Returns:
            ID do documento inserido ou None se falhou
        """
        if not self.conectado:
            logger.warning("⚠️ MongoDB não conectado - não pode salvar índices")
            return None

        try:
            documento = {
                "timestamp_coleta": datetime.now(),
                "indices": indices_data,
                "fonte_coleta": "rpa_coleta_indices"
            }

            def _save_indices():
                result = self.database.indices_economicos.insert_one(documento)
                return str(result.inserted_id)

            document_id = await asyncio.get_event_loop().run_in_executor(
                self.executor, _save_indices
            )
            
            logger.info(f"📊 Índices econômicos salvos no MongoDB: {document_id}")
            return document_id

        except Exception as e:
            logger.error(f"❌ Erro ao salvar índices no MongoDB: {str(e)}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return None

    async def salvar_contrato_processado(self, contrato_data: Dict[str, Any]) -> Optional[str]:
        """
        Salva contrato processado no MongoDB
        
        Returns:
            ID do documento inserido ou None se falhou
        """
        if not self.conectado:
            return None

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

            def _save_contract():
                # Upsert baseado no número do título
                result = self.database.contratos_processados.replace_one(
                    {"numero_titulo": documento["numero_titulo"]},
                    documento,
                    upsert=True
                )
                return str(result.upserted_id) if result.upserted_id else "updated"

            document_id = await asyncio.get_event_loop().run_in_executor(
                self.executor, _save_contract
            )
            
            logger.debug(f"📊 Contrato {documento['numero_titulo']} salvo no MongoDB: {document_id}")
            return document_id

        except Exception as e:
            logger.error(f"❌ Erro ao salvar contrato no MongoDB: {str(e)}")
            return None

    async def obter_execucoes_recentes(self, limite: int = 30) -> List[Dict[str, Any]]:
        """
        Obtém execuções recentes do MongoDB
        """
        if not self.conectado:
            return []

        try:
            def _get_executions():
                cursor = self.database.execucoes_rpa.find().sort("timestamp_inicio", -1).limit(limite)
                execucoes = list(cursor)
                
                # Converte ObjectId para string
                for execucao in execucoes:
                    if "_id" in execucao:
                        execucao["_id"] = str(execucao["_id"])
                    # Converte datetime para ISO string para compatibilidade JSON
                    for campo in ["timestamp_inicio", "timestamp_fim"]:
                        if campo in execucao and execucao[campo]:
                            execucao[campo] = execucao[campo].isoformat()

                return execucoes

            execucoes = await asyncio.get_event_loop().run_in_executor(
                self.executor, _get_executions
            )
            
            return execucoes

        except Exception as e:
            logger.error(f"❌ Erro ao obter execuções do MongoDB: {str(e)}")
            return []

    async def obter_estatisticas_dashboard(self) -> Dict[str, Any]:
        """
        Calcula estatísticas para dashboard
        """
        if not self.conectado:
            return {}

        try:
            def _get_stats():
                # Execuções hoje
                hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                execucoes_hoje = self.database.execucoes_rpa.count_documents({
                    "timestamp_inicio": {"$gte": hoje}
                })

                # Taxa de sucesso (últimas 30 execuções)
                cursor = self.database.execucoes_rpa.find().sort("timestamp_inicio", -1).limit(30)
                execucoes_recentes = list(cursor)
                
                if execucoes_recentes:
                    sucessos = sum(1 for e in execucoes_recentes if e.get("sucesso", False))
                    taxa_sucesso = (sucessos / len(execucoes_recentes)) * 100
                else:
                    taxa_sucesso = 0

                # Total de execuções
                total_execucoes = self.database.execucoes_rpa.count_documents({})

                # Contratos processados este mês
                inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                contratos_mes = self.database.contratos_processados.count_documents({
                    "data_processamento": {"$gte": inicio_mes}
                })

                return {
                    "total_execucoes": total_execucoes,
                    "execucoes_hoje": execucoes_hoje,
                    "taxa_sucesso": round(taxa_sucesso, 1),
                    "contratos_processados_mes": contratos_mes,
                    "ultima_atualizacao": datetime.now().isoformat(),
                    "fonte_dados": "mongodb"
                }

            stats = await asyncio.get_event_loop().run_in_executor(
                self.executor, _get_stats
            )
            
            return stats

        except Exception as e:
            logger.error(f"❌ Erro ao calcular estatísticas MongoDB: {str(e)}")
            return {}

    async def verificar_saude(self) -> Dict[str, Any]:
        """
        Verifica saúde da conexão MongoDB
        """
        try:
            if not self.conectado:
                return {
                    "status": "desconectado",
                    "erro": "Cliente não conectado"
                }

            def _check_health():
                # Testa comando ping
                self.client.admin.command('ping')
                
                # Conta documentos para verificar acesso
                total_execucoes = self.database.execucoes_rpa.count_documents({})
                
                return {
                    "status": "conectado",
                    "url": self._url_conexao.split('@')[-1] if self._url_conexao else "unknown",
                    "database": self.database.name if self.database is not None else "none",
                    "total_execucoes": total_execucoes,
                    "timestamp": datetime.now().isoformat()
                }

            health = await asyncio.get_event_loop().run_in_executor(
                self.executor, _check_health
            )
            
            return health

        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def obter_indice_mais_recente(self, tipo_indice: str = "igpm") -> Optional[float]:
        """
        Obtém índice econômico mais recente do MongoDB
        
        Args:
            tipo_indice: "igpm" ou "ipca"
            
        Returns:
            Valor do índice como float ou None se não encontrado
        """
        if not self.conectado:
            return None

        try:
            def _get_latest_index():
                # Buscar último documento com o índice solicitado
                cursor = self.database.indices_economicos.find(
                    {f"indices.{tipo_indice.lower()}": {"$exists": True}},
                    sort=[("timestamp_coleta", -1)]
                ).limit(1)
                
                resultado = list(cursor)
                if resultado:
                    indice_data = resultado[0].get("indices", {}).get(tipo_indice.lower(), {})
                    valor_str = indice_data.get("valor", "")
                    
                    # Converter valor string para float
                    if isinstance(valor_str, str):
                        # Remove % e converte vírgula para ponto
                        valor_limpo = valor_str.replace("%", "").replace(",", ".").strip()
                        return float(valor_limpo)
                    elif isinstance(valor_str, (int, float)):
                        return float(valor_str)
                
                return None

            indice_valor = await asyncio.get_event_loop().run_in_executor(
                self.executor, _get_latest_index
            )
            
            return indice_valor

        except Exception as e:
            logger.error(f"❌ Erro ao obter {tipo_indice} do MongoDB: {str(e)}")
            return None

    async def obter_documento_mais_recente(self, collection_name: str, filtro: Dict[str, Any] = None, 
                                          campo_ordenacao: str = "timestamp_coleta") -> Optional[Dict[str, Any]]:
        """
        Obtém documento mais recente de uma collection
        
        Args:
            collection_name: Nome da collection
            filtro: Filtro para a busca (opcional)
            campo_ordenacao: Campo para ordenação descendente
            
        Returns:
            Documento mais recente ou None se não encontrado
        """
        if not self.conectado:
            return None

        try:
            def _get_latest_document():
                collection = self.database[collection_name]
                cursor = collection.find(filtro or {}).sort(campo_ordenacao, -1).limit(1)
                
                resultado = list(cursor)
                if resultado:
                    documento = resultado[0]
                    # Converte ObjectId para string
                    if "_id" in documento:
                        documento["_id"] = str(documento["_id"])
                    # Converte datetime para ISO string
                    for campo, valor in documento.items():
                        if hasattr(valor, 'isoformat'):
                            documento[campo] = valor.isoformat()
                    return documento
                
                return None

            documento = await asyncio.get_event_loop().run_in_executor(
                self.executor, _get_latest_document
            )
            
            return documento

        except Exception as e:
            logger.error(f"❌ Erro ao obter documento mais recente de {collection_name}: {str(e)}")
            return None

    async def desconectar(self):
        """
        Fecha conexão MongoDB
        """
        try:
            if self.client:
                def _close_client():
                    self.client.close()
                
                await asyncio.get_event_loop().run_in_executor(
                    self.executor, _close_client
                )
                
                self.conectado = False
                logger.info("✅ MongoDB desconectado")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao desconectar MongoDB: {str(e)}")


# Instância global
mongodb_manager = MongoDBManager()

# Função para inicializar MongoDB automaticamente
async def inicializar_mongodb() -> bool:
    """Inicializa conexão MongoDB automaticamente"""
    return await mongodb_manager.conectar()

# Compatibilidade com código existente
MONGODB_DISPONIVEL = True
