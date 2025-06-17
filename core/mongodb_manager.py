
"""
MongoDB Manager - Sistema RPA v2.0
Gerenciador de conexão e operações MongoDB usando integração Replit

Desenvolvido em Português Brasileiro
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


class MongoDBManager:
    """
    Gerenciador unificado para operações MongoDB
    """

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database = None
        self.conectado = False
        self._url_conexao = None

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
            self.client = AsyncIOMotorClient(
                mongodb_uri,
                serverSelectionTimeoutMS=5000,  # 5 segundos
                connectTimeoutMS=5000,
                socketTimeoutMS=10000
            )

            logger.info("🏓 Testando conexão com ping...")
            # Testa conexão
            ping_result = await self.client.admin.command('ping')
            logger.info(f"✅ Ping successful: {ping_result}")
            
            logger.info(f"🗄️ Configurando database: {database_name}")
            # Define database
            self.database = self.client[database_name]
            
            # Teste prático com a database
            logger.info("🧪 Testando operação na database...")
            test_collection = self.database.teste_conexao_inicial
            test_doc = {"teste": True, "timestamp": datetime.now()}
            result = await test_collection.insert_one(test_doc)
            logger.info(f"✅ Teste inserção: {result.inserted_id}")
            
            # Remove documento de teste
            await test_collection.delete_one({"_id": result.inserted_id})
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
            # Índices para execucoes_rpa
            await self.database.execucoes_rpa.create_index("nome_rpa")
            await self.database.execucoes_rpa.create_index("timestamp_inicio")
            await self.database.execucoes_rpa.create_index("sucesso")

            # Índices para indices_economicos
            await self.database.indices_economicos.create_index("timestamp_coleta")
            await self.database.indices_economicos.create_index("fonte_coleta")

            # Índices para contratos_processados
            await self.database.contratos_processados.create_index("numero_titulo")
            await self.database.contratos_processados.create_index("data_processamento")
            await self.database.contratos_processados.create_index("status_sienge")

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

            result = await self.database.execucoes_rpa.insert_one(documento)
            logger.debug(f"📊 Execução {nome_rpa} salva no MongoDB: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"❌ Erro ao salvar execução no MongoDB: {str(e)}")
            return None

    async def salvar_indices_economicos(self, indices_data: Dict[str, Any]) -> Optional[str]:
        """
        Salva índices econômicos no MongoDB
        
        Returns:
            ID do documento inserido ou None se falhou
        """
        if not self.conectado:
            return None

        try:
            documento = {
                "timestamp_coleta": datetime.now(),
                "indices": indices_data,
                "fonte_coleta": "rpa_coleta_indices"
            }

            result = await self.database.indices_economicos.insert_one(documento)
            logger.debug(f"📊 Índices salvos no MongoDB: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"❌ Erro ao salvar índices no MongoDB: {str(e)}")
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

            # Upsert baseado no número do título
            result = await self.database.contratos_processados.replace_one(
                {"numero_titulo": documento["numero_titulo"]},
                documento,
                upsert=True
            )

            document_id = str(result.upserted_id) if result.upserted_id else "updated"
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
            cursor = self.database.execucoes_rpa.find().sort("timestamp_inicio", -1).limit(limite)
            execucoes = await cursor.to_list(length=limite)
            
            # Converte ObjectId para string
            for execucao in execucoes:
                if "_id" in execucao:
                    execucao["_id"] = str(execucao["_id"])
                # Converte datetime para ISO string para compatibilidade JSON
                for campo in ["timestamp_inicio", "timestamp_fim"]:
                    if campo in execucao and execucao[campo]:
                        execucao[campo] = execucao[campo].isoformat()

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
            # Execuções hoje
            hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            execucoes_hoje = await self.database.execucoes_rpa.count_documents({
                "timestamp_inicio": {"$gte": hoje}
            })

            # Taxa de sucesso (últimas 30 execuções)
            cursor = self.database.execucoes_rpa.find().sort("timestamp_inicio", -1).limit(30)
            execucoes_recentes = await cursor.to_list(length=30)
            
            if execucoes_recentes:
                sucessos = sum(1 for e in execucoes_recentes if e.get("sucesso", False))
                taxa_sucesso = (sucessos / len(execucoes_recentes)) * 100
            else:
                taxa_sucesso = 0

            # Total de execuções
            total_execucoes = await self.database.execucoes_rpa.count_documents({})

            # Contratos processados este mês
            inicio_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            contratos_mes = await self.database.contratos_processados.count_documents({
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

            # Testa comando ping
            await self.client.admin.command('ping')
            
            # Conta documentos para verificar acesso
            total_execucoes = await self.database.execucoes_rpa.count_documents({})
            
            return {
                "status": "conectado",
                "url": self._url_conexao.split('@')[-1] if self._url_conexao else "unknown",
                "database": self.database.name if self.database is not None else "none",
                "total_execucoes": total_execucoes,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "status": "erro",
                "erro": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def desconectar(self):
        """
        Fecha conexão MongoDB
        """
        try:
            if self.client:
                self.client.close()
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
