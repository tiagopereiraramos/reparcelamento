"""
Data Manager Híbrido
Sistema de persistência que usa MongoDB + JSON fallback mantendo simplicidade

Desenvolvido em Português Brasileiro
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

# Tentar importar MongoDB
try:
    from core.mongodb_manager import mongodb_manager
    MONGODB_DISPONIVEL = True
except ImportError:
    MONGODB_DISPONIVEL = False

logger = logging.getLogger(__name__)


class DataManagerHibrido:
    """
    Gerenciador de dados híbrido que mantém simplicidade do JSON
    mas adiciona robustez do MongoDB quando disponível
    """

    def __init__(self):
        self.pasta_logs = "logs"
        self.arquivo_historico = os.path.join(self.pasta_logs,
                                              "historico_execucoes.json")
        self.mongodb_ativo = False
        self._garantir_pasta_logs()

    def _garantir_pasta_logs(self):
        """Cria pasta de logs se não existir"""
        if not os.path.exists(self.pasta_logs):
            os.makedirs(self.pasta_logs)

    async def inicializar(self):
        """Inicializa sistema híbrido"""
        if MONGODB_DISPONIVEL:
            try:
                self.mongodb_ativo = await mongodb_manager.conectar()
                if self.mongodb_ativo:
                    logger.info("🗄️ Sistema híbrido: MongoDB + JSON ativo")
                else:
                    logger.info("📄 Sistema híbrido: Apenas JSON ativo")
            except Exception as e:
                logger.warning(
                    f"⚠️ MongoDB indisponível, usando apenas JSON: {str(e)}")
                self.mongodb_ativo = False
        else:
            logger.info("📄 Sistema simplificado: Apenas JSON")

    async def salvar_execucao(self, nome_rpa: str, parametros: Dict[str, Any],
                              resultado: Dict[str, Any]) -> bool:
        """
        Salva execução usando sistema híbrido
        """
        dados_execucao = {
            "nome_rpa": nome_rpa,
            "timestamp": datetime.now().isoformat(),
            "parametros": parametros,
            "resultado": resultado
        }

        sucesso_mongodb = False
        sucesso_json = False

        # Tentar MongoDB primeiro (se disponível)
        if self.mongodb_ativo:
            try:
                await mongodb_manager.salvar_execucao_rpa(
                    nome_rpa, parametros, resultado)
                sucesso_mongodb = True
                logger.debug(f"💾 [{nome_rpa}] Salvo no MongoDB")
            except Exception as e:
                logger.warning(f"⚠️ [{nome_rpa}] Falha MongoDB: {str(e)}")

        # Sempre salvar em JSON (fallback garantido)
        try:
            await self._salvar_json(dados_execucao)
            sucesso_json = True
            logger.debug(f"📄 [{nome_rpa}] Salvo em JSON")
        except Exception as e:
            logger.error(f"❌ [{nome_rpa}] Falha JSON: {str(e)}")

        return sucesso_mongodb or sucesso_json

    async def _salvar_json(self, dados_execucao: Dict[str, Any]):
        """Salva dados em arquivo JSON"""
        try:
            # Carregar histórico existente
            historico = []
            if os.path.exists(self.arquivo_historico):
                with open(self.arquivo_historico, 'r', encoding='utf-8') as f:
                    historico = json.load(f)

            # Adicionar nova execução
            historico.append(dados_execucao)

            # Manter apenas últimas 200 execuções
            if len(historico) > 200:
                historico = historico[-200:]

            # Salvar arquivo
            with open(self.arquivo_historico, 'w', encoding='utf-8') as f:
                json.dump(historico, f, indent=2, ensure_ascii=False)

        except Exception as e:
            raise Exception(f"Erro ao salvar JSON: {str(e)}")

    async def obter_execucoes_recentes(self,
                                       limite: int = 30
                                       ) -> List[Dict[str, Any]]:
        """
        Obtém execuções recentes do melhor source disponível
        """
        # Tentar MongoDB primeiro
        if self.mongodb_ativo:
            try:
                return await mongodb_manager.obter_execucoes_recentes(limite)
            except Exception as e:
                logger.warning(f"⚠️ Falha ao ler MongoDB: {str(e)}")

        # Fallback para JSON
        return await self._obter_execucoes_json(limite)

    async def _obter_execucoes_json(self,
                                    limite: int = 30) -> List[Dict[str, Any]]:
        """Lê execuções do arquivo JSON"""
        try:
            if not os.path.exists(self.arquivo_historico):
                return []

            with open(self.arquivo_historico, 'r', encoding='utf-8') as f:
                historico = json.load(f)

            # Retornar últimas execuções
            return historico[-limite:] if len(
                historico) > limite else historico

        except Exception as e:
            logger.error(f"❌ Erro ao ler JSON: {str(e)}")
            return []

    async def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas do sistema
        """
        if self.mongodb_ativo:
            try:
                return await mongodb_manager.obter_estatisticas_dashboard()
            except Exception as e:
                logger.warning(f"⚠️ Falha estatísticas MongoDB: {str(e)}")

        # Calcular estatísticas do JSON
        return await self._calcular_estatisticas_json()

    async def _calcular_estatisticas_json(self) -> Dict[str, Any]:
        """Calcula estatísticas dos dados JSON"""
        try:
            execucoes = await self._obter_execucoes_json(100)  # Últimas 100

            if not execucoes:
                return {
                    "total_execucoes": 0,
                    "execucoes_hoje": 0,
                    "taxa_sucesso": 0,
                    "contratos_processados_mes": 0
                }

            total_execucoes = len(execucoes)

            # Execuções hoje
            hoje = datetime.now().strftime('%Y-%m-%d')
            execucoes_hoje = sum(1 for ex in execucoes
                                 if ex.get('timestamp', '').startswith(hoje))

            # Taxa de sucesso
            sucessos = sum(1 for ex in execucoes
                           if ex.get('resultado', {}).get('sucesso', False))
            taxa_sucesso = (sucessos / total_execucoes *
                            100) if total_execucoes > 0 else 0

            # Contratos processados (estimativa)
            contratos = sum(
                ex.get('resultado', {}).get('dados', {}).get(
                    'contratos_identificados', 0) for ex in execucoes)

            return {
                "total_execucoes": total_execucoes,
                "execucoes_hoje": execucoes_hoje,
                "taxa_sucesso": round(taxa_sucesso, 1),
                "contratos_processados_mes": contratos,
                "fonte_dados": "JSON" if not self.mongodb_ativo else "MongoDB"
            }

        except Exception as e:
            logger.error(f"❌ Erro ao calcular estatísticas: {str(e)}")
            return {}

    async def salvar_indices_economicos(self, indices_data: Dict[str,
                                                                 Any]) -> bool:
        """Salva índices econômicos"""
        if self.mongodb_ativo:
            try:
                await mongodb_manager.salvar_indices_economicos(indices_data)
                return True
            except Exception as e:
                logger.warning(
                    f"⚠️ Falha ao salvar índices no MongoDB: {str(e)}")

        # Fallback: salvar em arquivo específico
        try:
            arquivo_indices = os.path.join(self.pasta_logs,
                                           "indices_economicos.json")

            # Carregar histórico
            historico_indices = []
            if os.path.exists(arquivo_indices):
                with open(arquivo_indices, 'r', encoding='utf-8') as f:
                    historico_indices = json.load(f)

            # Adicionar novos dados
            entrada = {
                "timestamp": datetime.now().isoformat(),
                "dados": indices_data
            }
            historico_indices.append(entrada)

            # Manter últimas 50 entradas
            if len(historico_indices) > 50:
                historico_indices = historico_indices[-50:]

            # Salvar
            with open(arquivo_indices, 'w', encoding='utf-8') as f:
                json.dump(historico_indices, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            logger.error(f"❌ Erro ao salvar índices: {str(e)}")
            return False


# Instância global do gerenciador híbrido
data_manager = DataManagerHibrido()


# Funções de conveniência
async def inicializar_sistema_dados():
    """Inicializa sistema de dados"""
    await data_manager.inicializar()


async def salvar_execucao_rpa(nome_rpa: str, parametros: Dict[str, Any],
                              resultado: Dict[str, Any]) -> bool:
    """Salva execução de RPA"""
    return await data_manager.salvar_execucao(nome_rpa, parametros, resultado)


async def obter_execucoes_recentes(limite: int = 30) -> List[Dict[str, Any]]:
    """Obtém execuções recentes"""
    return await data_manager.obter_execucoes_recentes(limite)


async def obter_estatisticas_sistema() -> Dict[str, Any]:
    """Obtém estatísticas do sistema"""
    return await data_manager.obter_estatisticas()
