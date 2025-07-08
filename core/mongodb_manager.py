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
import json
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
            logger.info("Conectando ao MongoDB...")

            # Tenta variáveis do Replit Database primeiro
            mongodb_uri = os.getenv('DATABASE_URL') or os.getenv(
                'MONGODB_URI') or os.getenv('MONGO_URL')
            database_name = os.getenv('DATABASE_NAME', 'sistema_rpa')

            logger.info(f"🔍 Variáveis de ambiente:")
            logger.info(
                f"   DATABASE_URL: {'SET' if os.getenv('DATABASE_URL') else 'NOT SET'}")
            logger.info(
                f"   MONGODB_URI: {'SET' if os.getenv('MONGODB_URI') else 'NOT SET'}")
            logger.info(
                f"   MONGO_URL: {'SET' if os.getenv('MONGO_URL') else 'NOT SET'}")
            logger.info(f"   DATABASE_NAME: {database_name}")

            if not mongodb_uri:
                # Fallback para conexão local se não tiver Replit Database
                mongodb_uri = "mongodb://localhost:27017"
                logger.warning(
                    "⚠️ Usando MongoDB local - configure DATABASE_URL para produção")
            else:
                # Log da URI mascarada (sem senha)
                uri_masked = mongodb_uri
                if '@' in uri_masked:
                    parts = uri_masked.split('@')
                    if len(parts) > 1:
                        credentials = parts[0].split('//')[-1]
                        if ':' in credentials:
                            user = credentials.split(':')[0]
                            uri_masked = uri_masked.replace(
                                credentials, f"{user}:***")
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
                self.database.indices_economicos.create_index(
                    "timestamp_coleta")
                self.database.indices_economicos.create_index("fonte_coleta")

                # Índices para contratos_processados
                self.database.contratos_processados.create_index(
                    "numero_titulo")
                self.database.contratos_processados.create_index(
                    "data_processamento")
                self.database.contratos_processados.create_index(
                    "status_sienge")

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
            logger.warning(
                "⚠️ MongoDB não conectado - não pode salvar execução")
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

            logger.info(
                f"📊 Execução {nome_rpa} salva no MongoDB: {document_id}")
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
            logger.warning(
                "⚠️ MongoDB não conectado - não pode salvar índices")
            logger.warning(
                f"   Estado conexão: conectado={self.conectado}, client={self.client is not None}, database={self.database is not None}")
            return None

        try:
            logger.info(f"🔍 Preparando documento para MongoDB...")
            logger.info(
                f"   Dados recebidos: {json.dumps(indices_data, indent=2, ensure_ascii=False, default=str)}")

            documento = {
                "timestamp_coleta": datetime.now(),
                "indices": indices_data,
                "fonte_coleta": "rpa_coleta_indices"
            }

            logger.info(
                f"📄 Documento preparado: {json.dumps(documento, indent=2, ensure_ascii=False, default=str)}")
            logger.info(f"🗄️ Collection alvo: indices_economicos")
            logger.info(f"🔗 Database: {self.database.name}")

            def _save_indices():
                logger.info(f"💾 Executando insert_one na collection...")
                collection = self.database.indices_economicos
                result = collection.insert_one(documento)
                logger.info(f"✅ Insert realizado, ID: {result.inserted_id}")
                return str(result.inserted_id)

            document_id = await asyncio.get_event_loop().run_in_executor(
                self.executor, _save_indices
            )

            logger.info(
                f"📊 Índices econômicos salvos no MongoDB: {document_id}")

            # Verificação adicional
            def _verify_save():
                count = self.database.indices_economicos.count_documents({})
                last_doc = self.database.indices_economicos.find_one(
                    sort=[("timestamp_coleta", -1)])
                return count, last_doc

            count, last_doc = await asyncio.get_event_loop().run_in_executor(
                self.executor, _verify_save
            )
            logger.info(
                f"🔍 Verificação: {count} documentos na collection, último: {last_doc['_id'] if last_doc else 'None'}")

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

            logger.debug(
                f"📊 Contrato {documento['numero_titulo']} salvo no MongoDB: {document_id}")
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
                cursor = self.database.execucoes_rpa.find().sort(
                    "timestamp_inicio", -1).limit(limite)
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
                    sucessos = sum(
                        1 for e in execucoes_recentes if e.get("sucesso", False))
                    taxa_sucesso = (sucessos / len(execucoes_recentes)) * 100
                else:
                    taxa_sucesso = 0

                # Total de execuções
                total_execucoes = self.database.execucoes_rpa.count_documents({
                })

                # Contratos processados este mês
                inicio_mes = datetime.now().replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0)
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
                total_execucoes = self.database.execucoes_rpa.count_documents({
                })

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
                    indice_data = resultado[0].get(
                        "indices", {}).get(tipo_indice.lower(), {})
                    valor_str = indice_data.get("valor", "")

                    # Converter valor string para float
                    if isinstance(valor_str, str):
                        # Remove % e converte vírgula para ponto
                        valor_limpo = valor_str.replace(
                            "%", "").replace(",", ".").strip()
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
                cursor = collection.find(filtro or {}).sort(
                    campo_ordenacao, -1).limit(1)

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
            logger.error(
                f"❌ Erro ao obter documento mais recente de {collection_name}: {str(e)}")
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

    async def salvar_documento(self, collection_name: str, documento: Dict[str, Any]) -> Optional[str]:
        """
        Salva documento genérico em uma collection

        Args:
            collection_name: Nome da collection
            documento: Documento a ser salvo

        Returns:
            ID do documento inserido ou None se falhou
        """
        if not self.conectado:
            logger.warning(
                f"⚠️ MongoDB não conectado - não pode salvar em {collection_name}")
            return None

        try:
            def _save_document():
                collection = self.database[collection_name]
                # Upsert baseado no _id se existir
                if "_id" in documento:
                    result = collection.replace_one(
                        {"_id": documento["_id"]},
                        documento,
                        upsert=True
                    )
                    return documento["_id"] if result.upserted_id else documento["_id"]
                else:
                    result = collection.insert_one(documento)
                    return str(result.inserted_id)

            document_id = await asyncio.get_event_loop().run_in_executor(
                self.executor, _save_document
            )

            logger.info(
                f"📊 Documento salvo em {collection_name}: {document_id}")
            return document_id

        except Exception as e:
            logger.error(
                f"❌ Erro ao salvar documento em {collection_name}: {str(e)}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return None

    async def atualizar_status_fila_contrato(self, numero_titulo: str, novo_status: str,
                                             dados_adicionais: Dict[str, Any] = None) -> bool:
        """
        Atualiza status de um contrato na fila de processamento

        Args:
            numero_titulo: Número do título do contrato
            novo_status: Novo status (PENDENTE, EXTRAINDO, EXTRAIDO, PROCESSANDO, PROCESSADO, ERRO)
            dados_adicionais: Dados adicionais para atualizar

        Returns:
            True se sucesso, False se falhou
        """
        if not self.conectado or self.database is None:
            logger.warning(
                "⚠️ MongoDB não conectado ou database não disponível - não pode atualizar status da fila")
            return False

        try:
            def _update_status():
                # ✅ CORRIGIDO: Usar nova collection fila_contratos
                collection = self.database.fila_contratos

                update_data = {
                    "status": novo_status,
                    "timestamp_ultima_atualizacao": datetime.now()
                }

                if dados_adicionais:
                    for key, value in dados_adicionais.items():
                        update_data[key] = value

                # ✅ CORRIGIDO: Buscar diretamente por numero_titulo (não em array)
                result = collection.update_one(
                    {"numero_titulo": numero_titulo},
                    {"$set": update_data}
                )

                return result.modified_count > 0

            sucesso = await asyncio.get_event_loop().run_in_executor(
                self.executor, _update_status
            )

            if sucesso:
                logger.info(
                    f"✅ Status atualizado para {numero_titulo}: {novo_status}")
            else:
                logger.warning(
                    f"⚠️ Falha ao atualizar status para {numero_titulo} - contrato não encontrado na fila")

            return sucesso

        except Exception as e:
            logger.error(f"❌ Erro ao atualizar status da fila: {str(e)}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return False

    async def buscar_dados_extraidos_recentes(self, numero_titulo: str, dias: int = 7) -> Optional[Dict[str, Any]]:
        """
        Busca dados extraídos recentemente do Sienge para um contrato

        Args:
            numero_titulo: Número do título do contrato
            dias: Número de dias para buscar dados recentes

        Returns:
            Dados extraídos mais recentes ou None se não encontrado
        """
        if not self.conectado:
            logger.warning(
                "⚠️ MongoDB não conectado - não pode buscar dados extraídos")
            return None

        try:
            def _search_recent_data():
                from datetime import timedelta

                collection = self.database.dados_extraidos_sienge

                # Data limite para busca
                data_limite = datetime.now() - timedelta(days=dias)

                # Buscar dados recentes para o título
                cursor = collection.find({
                    "numero_titulo": numero_titulo,
                    "timestamp_extracao": {"$gte": data_limite.isoformat()},
                    "status_extracao": "EXTRAIDO"
                }).sort("timestamp_extracao", -1).limit(1)

                resultado = list(cursor)
                if resultado:
                    documento = resultado[0]
                    # Converte ObjectId para string
                    if "_id" in documento:
                        documento["_id"] = str(documento["_id"])
                    return documento

                return None

            dados = await asyncio.get_event_loop().run_in_executor(
                self.executor, _search_recent_data
            )

            return dados

        except Exception as e:
            logger.error(
                f"❌ Erro ao buscar dados extraídos recentes: {str(e)}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return None

    async def registrar_uso_fallback(self, numero_titulo: str, tipo_fallback: str) -> bool:
        """
        Registra uso de fallback para auditoria e monitoramento

        Args:
            numero_titulo: Número do título do contrato
            tipo_fallback: Tipo de fallback utilizado

        Returns:
            True se registrado com sucesso, False se falhou
        """
        if not self.conectado:
            logger.warning(
                "⚠️ MongoDB não conectado - não pode registrar fallback")
            return False

        try:
            def _register_fallback():
                collection = self.database.uso_fallbacks

                documento = {
                    "numero_titulo": numero_titulo,
                    "tipo_fallback": tipo_fallback,
                    "timestamp_uso": datetime.now(),
                    "motivo": "Dados não disponíveis na extração atual",
                    "origem": "rpa_sienge"
                }

                result = collection.insert_one(documento)
                return result.inserted_id is not None

            sucesso = await asyncio.get_event_loop().run_in_executor(
                self.executor, _register_fallback
            )

            if sucesso:
                logger.info(
                    f"📊 Uso de fallback registrado para {numero_titulo}: {tipo_fallback}")

            return sucesso

        except Exception as e:
            logger.error(f"❌ Erro ao registrar uso de fallback: {str(e)}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return False


# Instância global
mongodb_manager = MongoDBManager()

# Função para inicializar MongoDB automaticamente


async def inicializar_mongodb() -> bool:
    """Inicializa conexão MongoDB automaticamente"""
    return await mongodb_manager.conectar()

# Compatibilidade com código existente
MONGODB_DISPONIVEL = True
