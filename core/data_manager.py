"""
Data Manager Híbrido Unificado
Sistema que SEMPRE grava simultaneamente em MongoDB (principal) + JSON (fallback)
Economiza código, tempo e facilita manutenção

Desenvolvido em Português Brasileiro
"""

import asyncio
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Importa MongoDB manager
try:
    from core.mongodb_manager import mongodb_manager
    MONGODB_DISPONIVEL = True
except ImportError:
    MONGODB_DISPONIVEL = False

logger = logging.getLogger(__name__)


class DataManagerUnificado:
    """
    Gerenciador unificado que SEMPRE grava em MongoDB + JSON simultaneamente
    MongoDB = Principal, JSON = Fallback garantido
    """

    def __init__(self):
        self.pasta_dados = "dados_processamento"
        self.arquivo_execucoes = os.path.join(self.pasta_dados, "execucoes_rpa.json")
        self.arquivo_contratos = os.path.join(self.pasta_dados, "contratos_processados.json")
        self.arquivo_indices = os.path.join(self.pasta_dados, "indices_economicos.json")
        self.arquivo_fila_sienge = os.path.join(self.pasta_dados, "fila_contratos_sienge.json")
        self.arquivo_planilhas = os.path.join(self.pasta_dados, "planilhas_extraidas.json")

        self.mongodb_ativo = False
        self._garantir_estrutura_dados()

    def _garantir_estrutura_dados(self):
        """Cria estrutura de pastas e arquivos se não existir"""
        Path(self.pasta_dados).mkdir(parents=True, exist_ok=True)

        # Inicializa arquivos JSON se não existirem
        arquivos_base = [
            (self.arquivo_execucoes, []),
            (self.arquivo_contratos, []),
            (self.arquivo_indices, []),
            (self.arquivo_fila_sienge, {"timestamp_ultima_atualizacao": "", "total_contratos": 0, "status_geral": "ativo", "contratos": []}),
            (self.arquivo_planilhas, [])
        ]

        for arquivo, estrutura_inicial in arquivos_base:
            if not os.path.exists(arquivo):
                self._salvar_json_seguro(arquivo, estrutura_inicial)

    async def inicializar(self):
        """Inicializa sistema híbrido com debug detalhado"""
        logger.info("🔧 Inicializando data_manager...")

        # Debug das variáveis de ambiente
        logger.info("🔍 Verificando variáveis de ambiente MongoDB...")
        db_url = os.getenv('DATABASE_URL') or os.getenv('MONGODB_URI') or os.getenv('MONGO_URL')
        db_name = os.getenv('DATABASE_NAME', 'sistema_rpa')
        logger.info(f"   DATABASE_URL: {'SET' if db_url else 'NOT SET'}")
        logger.info(f"   DATABASE_NAME: {db_name}")

        self._garantir_estrutura_dados()  # Garante que arquivos existem

        # Tenta conectar MongoDB
        if MONGODB_DISPONIVEL:
            try:
                logger.info("🔄 Tentando conectar ao MongoDB...")
                logger.info(f"   Usando URL: {db_url[:20] + '...' if db_url else 'localhost:27017'}")

                # Força reconexão se já estava conectado
                if mongodb_manager.conectado:
                    logger.info("♻️ Desconectando MongoDB anterior...")
                    await mongodb_manager.desconectar()

                self.mongodb_ativo = await mongodb_manager.conectar()
                logger.info(f"🔍 Resultado conexão MongoDB: {self.mongodb_ativo}")
                logger.info(f"🔍 mongodb_manager.conectado: {mongodb_manager.conectado}")

                if self.mongodb_ativo and mongodb_manager.conectado:
                    logger.info("✅ Sistema Híbrido: MongoDB + JSON ativo")

                    # Teste prático de inserção
                    try:
                        def _test_insert():
                            # Teste direto no MongoDB
                            test_collection = mongodb_manager.database.teste_conexao
                            test_doc = {"teste": True, "timestamp": datetime.now()}
                            result = test_collection.insert_one(test_doc)
                            # Remove documento de teste
                            test_collection.delete_one({"_id": result.inserted_id})
                            return str(result.inserted_id)

                        test_id = await asyncio.get_event_loop().run_in_executor(
                            None, _test_insert
                        )

                        logger.info(f"✅ Teste inserção MongoDB: {test_id}")


                    except Exception as test_e:
                        logger.error(f"❌ Falha no teste de inserção: {str(test_e)}")
                        self.mongodb_ativo = False

                    # Verifica saúde inicial
                    await self._verificar_saude_mongodb()

                else:
                    logger.warning("⚠️ MongoDB conectou mas algo está incorreto")
                    logger.warning(f"   mongodb_ativo: {self.mongodb_ativo}")
                    logger.warning(f"   manager.conectado: {mongodb_manager.conectado}")
                    self.mongodb_ativo = False
                    logger.info("📄 Sistema Fallback: Apenas JSON (MongoDB com problemas)")

            except Exception as e:
                logger.error(f"❌ Falha ao conectar MongoDB: {str(e)}")
                logger.error(f"   Tipo do erro: {type(e).__name__}")
                import traceback
                logger.error(f"   Traceback: {traceback.format_exc()}")
                self.mongodb_ativo = False
                logger.info("📄 Sistema Fallback: Apenas JSON")
        else:
            logger.warning("⚠️ MONGODB_DISPONIVEL = False")
            logger.info("📄 Sistema JSON: MongoDB não disponível nesta instalação")

        logger.info(f"✅ Data manager inicializado - MongoDB ativo: {self.mongodb_ativo}")

        # Debug final do estado
        logger.info("🔍 Estado final da inicialização:")
        logger.info(f"   MONGODB_DISPONIVEL: {MONGODB_DISPONIVEL}")
        logger.info(f"   self.mongodb_ativo: {self.mongodb_ativo}")
        logger.info(f"   mongodb_manager.conectado: {mongodb_manager.conectado if MONGODB_DISPONIVEL else 'N/A'}")
        logger.info(f"   mongodb_manager.database: {'SET' if MONGODB_DISPONIVEL and mongodb_manager.database is not None else 'NOT SET'}")

    async def _verificar_saude_mongodb(self):
        """Verifica saúde do MongoDB e reconecta se necessário"""
        if not MONGODB_DISPONIVEL:
            return

        try:
            saude = await mongodb_manager.verificar_saude()
            if saude.get("status") != "conectado":
                logger.warning("⚠️ MongoDB não saudável, tentando reconectar...")
                self.mongodb_ativo = await mongodb_manager.conectar()
        except Exception as e:
            logger.warning(f"⚠️ Erro ao verificar saúde MongoDB: {str(e)}")
            self.mongodb_ativo = False

    async def salvar_execucao_rpa(self, nome_rpa: str, parametros: Dict[str, Any], 
                                  resultado: Dict[str, Any]) -> Dict[str, str]:
        """
        SEMPRE salva execução em MongoDB + JSON simultaneamente

        Returns:
            Dict com status de cada operação
        """
        dados_execucao = {
            "nome_rpa": nome_rpa,
            "timestamp_inicio": datetime.now().isoformat(),
            "timestamp_fim": datetime.now().isoformat(),
            "parametros_entrada": parametros,
            "resultado": resultado,
            "sucesso": resultado.get("sucesso", False),
            "tempo_execucao_segundos": resultado.get("tempo_execucao", 0),
            "mensagem": resultado.get("mensagem", ""),
            "erro": resultado.get("erro", None)
        }

        resultados = {"mongodb": "falhou", "json": "falhou"}

        # Debug do estado MongoDB
        logger.info(f"🔍 Estado MongoDB antes do salvamento:")
        logger.info(f"   MONGODB_DISPONIVEL: {MONGODB_DISPONIVEL}")
        logger.info(f"   self.mongodb_ativo: {self.mongodb_ativo}")
        logger.info(f"   mongodb_manager existe: {mongodb_manager is not None}")
        logger.info(f"   mongodb_manager.conectado: {mongodb_manager.conectado if mongodb_manager else 'N/A'}")
        logger.info(f"   mongodb_manager.database: {'SET' if mongodb_manager and mongodb_manager.database else 'NOT SET'}")

        # Tentar MongoDB primeiro - usar conectado ao invés de mongodb_ativo
        if MONGODB_DISPONIVEL and mongodb_manager and mongodb_manager.conectado:
            try:
                resultado_mongodb = await mongodb_manager.salvar_execucao_rpa(
                    nome_rpa, parametros, resultado
                )

                if resultado_mongodb:
                    resultados["mongodb"] = "sucesso"
                    dados_execucao["_id_mongodb"] = resultado_mongodb
                    logger.info(f"📊 [MongoDB] Execução {nome_rpa} salva: {resultado_mongodb}")
                else:
                    resultados["mongodb"] = "falha: retorno None"
                    logger.warning(f"⚠️ [MongoDB] Falha no salvamento de {nome_rpa}")

            except Exception as e:
                resultados["mongodb"] = f"erro: {str(e)}"
                logger.error(f"❌ [MongoDB] Erro ao salvar {nome_rpa}: {str(e)}")
        else:
            motivo = []
            if not MONGODB_DISPONIVEL:
                motivo.append("MONGODB_DISPONIVEL=False")
            if not mongodb_manager:
                motivo.append("mongodb_manager=None")
            elif not mongodb_manager.conectado:
                motivo.append("mongodb_manager.conectado=False")

            resultados["mongodb"] = f"nao_tentado: {', '.join(motivo)}"
            logger.warning(f"⚠️ MongoDB não tentado: {', '.join(motivo)}")

        # 2. SEMPRE salvar JSON (fallback garantido) - FORÇA SUCESSO
        logger.info(f"📄 Salvando JSON para {nome_rpa}...")
        try:
            await self._salvar_execucao_json(dados_execucao)
            resultados["json"] = "sucesso"
            logger.info(f"✅ [{nome_rpa}] JSON salvo com sucesso")
        except Exception as e:
            logger.error(f"❌ [{nome_rpa}] JSON falhou: {str(e)}")
            logger.error(f"   Traceback JSON: {traceback.format_exc()}")
            resultados["json"] = f"erro: {str(e)}"

        # Log consolidado
        if resultados["mongodb"] == "sucesso" and resultados["json"] == "sucesso":
            logger.info(f"✅ [{nome_rpa}] Salvo em MongoDB + JSON")
        elif resultados["json"] == "sucesso":
            logger.info(f"📄 [{nome_rpa}] Salvo apenas em JSON (MongoDB indisponível)")
        else:
            logger.error(f"❌ [{nome_rpa}] FALHA TOTAL - nenhum sistema funcionou!")

        return resultados

    async def salvar_contrato_processado(self, contrato_data: Dict[str, Any]) -> Dict[str, str]:
        """
        SEMPRE salva contrato em MongoDB + JSON simultaneamente
        """
        documento = {
            "numero_titulo": contrato_data.get("numero_titulo"),
            "cliente": contrato_data.get("cliente"),
            "empreendimento": contrato_data.get("empreendimento"),
            "data_processamento": datetime.now().isoformat(),
            "status_sienge": contrato_data.get("status_sienge", "processado"),
            "status_sicredi": contrato_data.get("status_sicredi", "pendente"),
            "saldo_anterior": contrato_data.get("saldo_anterior", 0),
            "saldo_novo": contrato_data.get("saldo_novo", 0),
            "indice_aplicado": contrato_data.get("indice_aplicado", 0),
            "indexador": contrato_data.get("indexador", ""),
            "dados_completos": contrato_data
        }

        resultados = {"mongodb": "falhou", "json": "falhou"}

        # 1. MongoDB (principal)
        if self.mongodb_ativo:
            try:
                mongo_id = await mongodb_manager.salvar_contrato_processado(contrato_data)
                if mongo_id:
                    resultados["mongodb"] = "sucesso"
                    documento["_id_mongodb"] = str(mongo_id)
            except Exception as e:
                logger.warning(f"⚠️ Contrato MongoDB falhou: {str(e)}")
                resultados["mongodb"] = f"erro: {str(e)}"

        # 2. JSON (fallback garantido)
        try:
            await self._salvar_contrato_json(documento)
            resultados["json"] = "sucesso"
        except Exception as e:
            logger.error(f"❌ Contrato JSON falhou: {str(e)}")
            resultados["json"] = f"erro: {str(e)}"

        titulo = documento.get("numero_titulo", "N/A")
        if resultados["mongodb"] == "sucesso" and resultados["json"] == "sucesso":
            logger.info(f"✅ Contrato {titulo} salvo em MongoDB + JSON")
        elif resultados["json"] == "sucesso":
            logger.info(f"📄 Contrato {titulo} salvo apenas em JSON")

        return resultados

    async def salvar_indices_economicos(self, indices_data: Dict[str, Any]) -> Dict[str, str]:
        """
        SEMPRE salva índices em MongoDB + JSON simultaneamente
        """
        documento = {
            "timestamp_coleta": datetime.now().isoformat(),
            "indices": indices_data,
            "fonte_coleta": "rpa_coleta_indices"
        }

        resultados = {"mongodb": "falhou", "json": "falhou"}

        # 1. MongoDB (principal)
        if self.mongodb_ativo:
            try:
                mongo_id = await mongodb_manager.salvar_indices_economicos(indices_data)
                if mongo_id:
                    resultados["mongodb"] = "sucesso"
                    documento["_id_mongodb"] = mongo_id
            except Exception as e:
                logger.warning(f"⚠️ Índices MongoDB falhou: {str(e)}")
                resultados["mongodb"] = f"erro: {str(e)}"
        else:
            resultados["mongodb"] = "desconectado"

        # 2. JSON (fallback garantido)
        try:
            await self._salvar_indices_json(documento)
            resultados["json"] = "sucesso"
        except Exception as e:
            logger.error(f"❌ Índices JSON falhou: {str(e)}")
            resultados["json"] = f"erro: {str(e)}"

        if resultados["mongodb"] == "sucesso" and resultados["json"] == "sucesso":
            logger.info("✅ Índices salvos em MongoDB + JSON")
        elif resultados["json"] == "sucesso":
            logger.info("📄 Índices salvos apenas em JSON")

        return resultados

    async def salvar_fila_sienge(self, fila_dados: Dict[str, Any]) -> Dict[str, str]:
        """
        SEMPRE salva fila Sienge em MongoDB + JSON simultaneamente
        """
        documento = {
            "timestamp_ultima_atualizacao": datetime.now().isoformat(),
            "total_contratos": fila_dados.get("total_contratos", 0),
            "status_geral": "ativo",
            "contratos": fila_dados.get("contratos", [])
        }

        resultados = {"mongodb": "falhou", "json": "falhou"}

        # 1. MongoDB (principal)
        if self.mongodb_ativo:
            try:
                collection = mongodb_manager.database.fila_processamento_sienge
                result = await collection.replace_one({}, documento, upsert=True)
                resultados["mongodb"] = "sucesso"
                documento["_id_mongodb"] = str(result.upserted_id) if result.upserted_id else "updated"
            except Exception as e:
                logger.warning(f"⚠️ Fila Sienge MongoDB falhou: {str(e)}")
                resultados["mongodb"] = f"erro: {str(e)}"

        # 2. JSON (fallback garantido)
        try:
            self._salvar_json_seguro(self.arquivo_fila_sienge, documento)
            resultados["json"] = "sucesso"
        except Exception as e:
            logger.error(f"❌ Fila Sienge JSON falhou: {str(e)}")
            resultados["json"] = f"erro: {str(e)}"

        total = documento.get("total_contratos", 0)
        if resultados["mongodb"] == "sucesso" and resultados["json"] == "sucesso":
            logger.info(f"✅ Fila Sienge ({total} contratos) salva em MongoDB + JSON")
        elif resultados["json"] == "sucesso":
            logger.info(f"📄 Fila Sienge ({total} contratos) salva apenas em JSON")

        return resultados

    async def salvar_planilha_extraida(self, dados_planilha: Dict[str, Any]) -> Dict[str, str]:
        """
        SEMPRE salva dados de planilha extraída em MongoDB + JSON simultaneamente
        """
        documento = {
            "numero_titulo": dados_planilha.get("numero_titulo"),
            "cliente": dados_planilha.get("cliente"),
            "caminho_arquivo": dados_planilha.get("caminho_arquivo"),
            "data_extracao": datetime.now().isoformat(),
            "origem_sistema": "sienge",
            "status_auditoria": "ativo",
            "hash_arquivo": dados_planilha.get("hash_arquivo"),
            "tamanho_arquivo": dados_planilha.get("tamanho_arquivo"),
            "metadados": dados_planilha
        }

        resultados = {"mongodb": "falhou", "json": "falhou"}

        # 1. MongoDB (principal)
        if self.mongodb_ativo:
            try:
                collection = mongodb_manager.database.planilhas_extraidas
                result = await collection.insert_one(documento)
                resultados["mongodb"] = "sucesso"
                documento["_id_mongodb"] = str(result.inserted_id)
            except Exception as e:
                logger.warning(f"⚠️ Planilha MongoDB falhou: {str(e)}")
                resultados["mongodb"] = f"erro: {str(e)}"

        # 2. JSON (fallback garantido)
        try:
            await self._salvar_planilha_json(documento)
            resultados["json"] = "sucesso"
        except Exception as e:
            logger.error(f"❌ Planilha JSON falhou: {str(e)}")
            resultados["json"] = f"erro: {str(e)}"

        titulo = documento.get("numero_titulo", "N/A")
        if resultados["mongodb"] == "sucesso" and resultados["json"] == "sucesso":
            logger.info(f"✅ Planilha {titulo} salva em MongoDB + JSON")
        elif resultados["json"] == "sucesso":
            logger.info(f"📄 Planilha {titulo} salva apenas em JSON")

        return resultados

    async def obter_execucoes_recentes(self, limite: int = 30) -> List[Dict[str, Any]]:
        """
        Obtém execuções recentes - MongoDB primeiro, JSON como fallback
        """
        # Tentar MongoDB primeiro
        if self.mongodb_ativo:
            try:
                execucoes = await mongodb_manager.obter_execucoes_recentes(limite)
                if execucoes:
                    logger.debug(f"📊 {len(execucoes)} execuções obtidas do MongoDB")
                    return execucoes
            except Exception as e:
                logger.warning(f"⚠️ Falha ao ler MongoDB: {str(e)}")

        # Fallback para JSON
        try:
            execucoes = await self._obter_execucoes_json(limite)
            logger.debug(f"📄 {len(execucoes)} execuções obtidas do JSON")
            return execucoes
        except Exception as e:
            logger.error(f"❌ Falha ao ler JSON: {str(e)}")
            return []

    async def obter_fila_sienge(self) -> Dict[str, Any]:
        """
        Obtém fila Sienge - MongoDB primeiro, JSON como fallback
        """
        # Tentar MongoDB primeiro
        if self.mongodb_ativo:
            try:
                collection = mongodb_manager.database.fila_processamento_sienge
                documento = await collection.find_one()
                if documento:
                    # Remove _id do MongoDB para compatibilidade
                    documento.pop("_id", None)
                    logger.debug("📊 Fila Sienge obtida do MongoDB")
                    return documento
            except Exception as e:
                logger.warning(f"⚠️ Falha ao ler fila MongoDB: {str(e)}")

        # Fallback para JSON
        try:
            if os.path.exists(self.arquivo_fila_sienge):
                with open(self.arquivo_fila_sienge, 'r', encoding='utf-8') as f:
                    fila = json.load(f)
                    logger.debug("📄 Fila Sienge obtida do JSON")
                    return fila
        except Exception as e:
            logger.error(f"❌ Falha ao ler fila JSON: {str(e)}")

        # Retorna estrutura vazia se tudo falhar
        return {
            "timestamp_ultima_atualizacao": "",
            "total_contratos": 0,
            "status_geral": "ativo",
            "contratos": []
        }

    async def obter_estatisticas_dashboard(self) -> Dict[str, Any]:
        """
        Obtém estatísticas - MongoDB primeiro, JSON como fallback
        """
        # Tentar MongoDB primeiro
        if self.mongodb_ativo:
            try:
                stats = await mongodb_manager.obter_estatisticas_dashboard()
                if stats:
                    logger.debug("📊 Estatísticas obtidas do MongoDB")
                    return stats
            except Exception as e:
                logger.warning(f"⚠️ Falha estatísticas MongoDB: {str(e)}")

        # Fallback para JSON
        try:
            stats = await self._calcular_estatisticas_json()
            logger.debug("📄 Estatísticas calculadas do JSON")
            return stats
        except Exception as e:
            logger.error(f"❌ Falha estatísticas JSON: {str(e)}")
            return {}

    async def debug_verificar_dados_salvos(self) -> Dict[str, Any]:
        """
        Método de debug para verificar dados salvos
        """
        try:
            indices = self._carregar_json_seguro(self.arquivo_indices, [])
            execucoes = self._carregar_json_seguro(self.arquivo_execucoes, [])

            # Verifica MongoDB também
            mongo_stats = {}
            if self.mongodb_ativo and MONGODB_DISPONIVEL:
                try:
                    mongo_stats = await mongodb_manager.obter_estatisticas_dashboard()
                except Exception as e:
                    mongo_stats = {"erro": str(e)}

            # Estrutura correta que o teste está esperando
            return {
                "total_execucoes": len(execucoes),
                "total_indices_salvos": len(indices),
                "ultimo_indice": indices[-1] if indices else None,
                "ultima_execucao": execucoes[-1] if execucoes else None,
                "arquivo_indices_existe": os.path.exists(self.arquivo_indices),
                "arquivo_execucoes_existe": os.path.exists(self.arquivo_execucoes),
                "json": {
                    "total_indices_salvos": len(indices),
                    "total_execucoes": len(execucoes),
                    "ultimo_indice": indices[-1] if indices else None,
                    "ultima_execucao": execucoes[-1] if execucoes else None,
                    "arquivo_indices_existe": os.path.exists(self.arquivo_indices),
                    "arquivo_execucoes_existe": os.path.exists(self.arquivo_execucoes)
                },
                "mongodb": mongo_stats,
                "sistema_ativo": {
                    "mongodb_ativo": self.mongodb_ativo,
                    "mongodb_disponivel": MONGODB_DISPONIVEL
                }
            }
        except Exception as e:
            logger.error(f"❌ Erro no debug: {str(e)}")
            return {"erro": str(e)}

    async def debug_verificar_indices_salvos(self) -> Dict[str, Any]:
        """
        Método de debug para verificar se índices foram salvos (mantido para compatibilidade)
        """
        return await self.debug_verificar_dados_salvos()

    # Métodos auxiliares JSON
    async def _salvar_execucao_json(self, dados_execucao: Dict[str, Any]):
        """Salva execução em JSON"""
        historico = self._carregar_json_seguro(self.arquivo_execucoes, [])
        historico.append(dados_execucao)

        # Manter apenas últimas 200 execuções
        if len(historico) > 200:
            historico = historico[-200:]

        self._salvar_json_seguro(self.arquivo_execucoes, historico)

    async def _salvar_contrato_json(self, documento: Dict[str, Any]):
        """Salva contrato em JSON"""
        contratos = self._carregar_json_seguro(self.arquivo_contratos, [])

        # Remove contrato anterior com mesmo número de título
        numero_titulo = documento.get("numero_titulo")
        if numero_titulo:
            contratos = [c for c in contratos if c.get("numero_titulo") != numero_titulo]

        contratos.append(documento)
        self._salvar_json_seguro(self.arquivo_contratos, contratos)

    async def _salvar_indices_json(self, documento: Dict[str, Any]):
        """Salva índices em JSON"""
        try:
            indices = self._carregar_json_seguro(self.arquivo_indices, [])
            indices.append(documento)

            # Manter apenas últimos 50 registros
            if len(indices) > 50:
                indices = indices[-50:]

            self._salvar_json_seguro(self.arquivo_indices, indices)
            logger.info(f"✅ Índices salvos em {self.arquivo_indices}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar índices JSON: {str(e)}")
            raise

    async def _salvar_planilha_json(self, documento: Dict[str, Any]):
        """Salva planilha em JSON"""
        planilhas = self._carregar_json_seguro(self.arquivo_planilhas, [])
        planilhas.append(documento)
        self._salvar_json_seguro(self.arquivo_planilhas, planilhas)

    async def _obter_execucoes_json(self, limite: int = 30) -> List[Dict[str, Any]]:
        """Obtém execuções do JSON"""
        historico = self._carregar_json_seguro(self.arquivo_execucoes, [])
        return historico[-limite:] if len(historico) > limite else historico

    async def _calcular_estatisticas_json(self) -> Dict[str, Any]:
        """Calcula estatísticas dos dados JSON"""
        try:
            execucoes = self._carregar_json_seguro(self.arquivo_execucoes, [])
            contratos = self._carregar_json_seguro(self.arquivo_contratos, [])

            # Estatísticas básicas
            hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            execucoes_hoje = len([e for e in execucoes if e.get("timestamp_inicio", "").startswith(hoje.strftime("%Y-%m-%d"))])

            # Taxa de sucesso últimos 30 registros
            execucoes_recentes = execucoes[-30:] if len(execucoes) > 30 else execucoes
            sucessos = len([e for e in execucoes_recentes if e.get("sucesso", False)])
            taxa_sucesso = (sucessos / len(execucoes_recentes) * 100) if execucoes_recentes else 0

            return {
                "total_execucoes": len(execucoes),
                "execucoes_hoje": execucoes_hoje,
                "taxa_sucesso": round(taxa_sucesso, 1),
                "contratos_processados_mes": len(contratos),
                "ultima_atualizacao": datetime.now().isoformat(),
                "fonte_dados": "json_fallback"
            }
        except Exception as e:
            logger.error(f"❌ Erro ao calcular estatísticas JSON: {str(e)}")
            return {}

    def _carregar_json_seguro(self, arquivo: str, default):
        """Carrega JSON com tratamento de erro"""
        try:
            if os.path.exists(arquivo):
                with open(arquivo, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except Exception as e:
            logger.warning(f"⚠️ Erro ao carregar {arquivo}: {str(e)}")
            return default

    def _salvar_json_seguro(self, arquivo: str, dados):
        """Salva JSON com tratamento de erro"""
        try:
            with open(arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"❌ Erro ao salvar {arquivo}: {str(e)}")
            raise


# Instância global unificada
data_manager = DataManagerUnificado()

# Funções auxiliares para facilitar uso
async def salvar_execucao(nome_rpa: str, parametros: Dict[str, Any], resultado: Dict[str, Any]) -> Dict[str, str]:
    """Função auxiliar para salvar execução simultaneamente"""
    return await data_manager.salvar_execucao_rpa(nome_rpa, parametros, resultado)

async def salvar_contrato(contrato_data: Dict[str, Any]) -> Dict[str, str]:
    """Função auxiliar para salvar contrato simultaneamente"""
    return await data_manager.salvar_contrato_processado(contrato_data)

async def salvar_indices(indices_data: Dict[str, Any]) -> Dict[str, str]:
    """Função auxiliar para salvar índices simultaneamente"""
    return await data_manager.salvar_indices_economicos(indices_data)

async def salvar_fila_sienge(fila_dados: Dict[str, Any]) -> Dict[str, str]:
    """Função auxiliar para salvar fila simultaneamente"""
    return await data_manager.salvar_fila_sienge(fila_dados)

async def obter_execucoes_recentes(limite: int = 30) -> List[Dict[str, Any]]:
    """Função auxiliar para obter execuções"""
    return await data_manager.obter_execucoes_recentes(limite)

async def obter_fila_sienge() -> Dict[str, Any]:
    """Função auxiliar para obter fila Sienge"""
    return await data_manager.obter_fila_sienge()

async def obter_estatisticas_dashboard() -> Dict[str, Any]:
    """Função auxiliar para estatísticas"""
    return await data_manager.obter_estatisticas_dashboard()