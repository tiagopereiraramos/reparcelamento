
"""
Sistema Unificado de Rastreamento e Auditoria
Garante que TODOS os passos dos RPAs sejam registrados em MongoDB + JSON simultaneamente

Desenvolvido em Português Brasileiro
"""

import json
import os
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from core.data_manager import data_manager

logger = logging.getLogger(__name__)


class RastreamentoUnificado:
    """
    Sistema central de rastreamento que garante:
    1. TODOS os passos são registrados
    2. MongoDB + JSON simultâneo (fallback obrigatório)
    3. Auditoria completa para recuperação
    4. Identificação única de cada execução
    """

    def __init__(self, nome_rpa: str):
        self.nome_rpa = nome_rpa
        self.id_execucao = f"{nome_rpa}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:20]}"
        self.pasta_auditoria = Path("dados_processamento/auditoria_completa")
        self.pasta_auditoria.mkdir(parents=True, exist_ok=True)

        # Arquivo específico para esta execução
        self.arquivo_execucao = self.pasta_auditoria / \
            f"{self.id_execucao}.json"
        self.passos_execucao = []
        self.dados_contexto = {}

        logger.info(f"🔍 Rastreamento iniciado: {self.id_execucao}")

    async def registrar_passo(self, nome_passo: str, dados: Dict[str, Any],
                              categoria: str = "OPERACAO",
                              criticidade: str = "INFO") -> str:
        """
        Registra um passo da execução garantindo MongoDB + JSON

        Args:
            nome_passo: Nome identificador do passo
            dados: Dados do passo a serem registrados
            categoria: INICIO, OPERACAO, ERRO, SUCESSO, etc.
            criticidade: INFO, WARNING, ERROR, CRITICAL

        Returns:
            ID único do passo registrado
        """
        timestamp = datetime.now()
        id_passo = f"{self.id_execucao}_{len(self.passos_execucao):04d}"

        documento_passo = {
            "id_passo": id_passo,
            "id_execucao": self.id_execucao,
            "nome_rpa": self.nome_rpa,
            "nome_passo": nome_passo,
            "categoria": categoria,
            "criticidade": criticidade,
            "timestamp": timestamp.isoformat(),
            "dados": dados,
            "ordem_execucao": len(self.passos_execucao) + 1
        }

        # 1. Adiciona à lista local
        self.passos_execucao.append(documento_passo)

        # 2. SEMPRE salvar em JSON (fallback obrigatório)
        await self._salvar_json_imediato(documento_passo)

        # 3. Tentar MongoDB (principal)
        await self._salvar_mongodb_passo(documento_passo)

        # 4. Atualizar contexto se necessário
        if categoria in ["INICIO", "SUCESSO", "ERRO"]:
            self.dados_contexto[f"ultimo_{categoria.lower()}"] = {
                "passo": nome_passo,
                "timestamp": timestamp.isoformat(),
                "dados": dados
            }

        logger.info(f"📝 [{self.nome_rpa}] {categoria}: {nome_passo}")
        return id_passo

    async def registrar_inicio_rpa(self, parametros: Dict[str, Any]) -> str:
        """Registra início da execução do RPA"""
        return await self.registrar_passo(
            "INICIO_EXECUCAO_RPA",
            {
                "parametros_entrada": parametros,
                "usuario_sistema": os.getenv("USER", "sistema"),
                "ip_execucao": self._obter_ip_local(),
                "ambiente": "replit_deployment" if os.getenv("REPL_ID") else "local"
            },
            categoria="INICIO"
        )

    async def registrar_login_sistema(self, sistema: str, usuario: str, sucesso: bool) -> str:
        """Registra tentativa de login em sistema externo"""
        return await self.registrar_passo(
            f"LOGIN_{sistema.upper()}",
            {
                "sistema": sistema,
                "usuario_login": usuario,
                "sucesso_login": sucesso,
                "url_sistema": self._obter_url_sistema(sistema)
            },
            categoria="OPERACAO" if sucesso else "ERRO"
        )

    async def registrar_consulta_dados(self, tipo_consulta: str, parametros: Dict[str, Any],
                                       resultado: Dict[str, Any]) -> str:
        """Registra consulta de dados (relatórios, planilhas, etc.)"""
        return await self.registrar_passo(
            f"CONSULTA_{tipo_consulta.upper()}",
            {
                "tipo_consulta": tipo_consulta,
                "parametros_consulta": parametros,
                "resultado_consulta": resultado,
                "registros_encontrados": resultado.get("total_registros", 0),
                "tamanho_dados": len(str(resultado))
            },
            categoria="OPERACAO"
        )

    async def registrar_processamento_planilha(self, caminho_arquivo: str,
                                               dados_processados: Dict[str, Any]) -> str:
        """Registra processamento de planilha com hash e metadados"""
        import hashlib

        hash_arquivo = None
        tamanho_arquivo = 0

        if os.path.exists(caminho_arquivo):
            # Calcula hash MD5 para auditoria
            with open(caminho_arquivo, 'rb') as f:
                hash_arquivo = hashlib.md5(f.read()).hexdigest()
            tamanho_arquivo = os.path.getsize(caminho_arquivo)

        return await self.registrar_passo(
            "PROCESSAMENTO_PLANILHA",
            {
                "caminho_arquivo": caminho_arquivo,
                "hash_md5": hash_arquivo,
                "tamanho_bytes": tamanho_arquivo,
                "dados_processados": dados_processados,
                "linhas_processadas": dados_processados.get("total_registros", 0),
                "arquivo_existe": os.path.exists(caminho_arquivo)
            },
            categoria="OPERACAO"
        )

    async def registrar_calculo_valores(self, tipo_calculo: str,
                                        entrada: Dict[str, Any],
                                        resultado: Dict[str, Any]) -> str:
        """Registra cálculos de valores (IGPM, reparcelamento, etc.)"""
        return await self.registrar_passo(
            f"CALCULO_{tipo_calculo.upper()}",
            {
                "tipo_calculo": tipo_calculo,
                "valores_entrada": entrada,
                "valores_resultado": resultado,
                "sucesso_calculo": resultado.get("sucesso", False),
                "indices_utilizados": resultado.get("indices_utilizados", {}),
                "fatores_aplicados": resultado.get("fatores_aplicados", {})
            },
            categoria="OPERACAO"
        )

    async def registrar_erro_critico(self, erro: Exception, contexto: Dict[str, Any]) -> str:
        """Registra erros críticos com stack trace completo"""
        import traceback

        return await self.registrar_passo(
            "ERRO_CRITICO",
            {
                "tipo_erro": type(erro).__name__,
                "mensagem_erro": str(erro),
                "stack_trace": traceback.format_exc(),
                "contexto_erro": contexto,
                "pode_recuperar": self._pode_recuperar_erro(erro)
            },
            categoria="ERRO",
            criticidade="CRITICAL"
        )

    async def registrar_sucesso_rpa(self, resultado_final: Dict[str, Any]) -> str:
        """Registra sucesso na execução do RPA"""
        tempo_total = (datetime.now() - datetime.fromisoformat(
            self.passos_execucao[0]["timestamp"]
        )).total_seconds() if self.passos_execucao else 0

        return await self.registrar_passo(
            "SUCESSO_EXECUCAO_RPA",
            {
                "resultado_final": resultado_final,
                "tempo_total_segundos": tempo_total,
                "total_passos_executados": len(self.passos_execucao),
                "estatisticas_execucao": await self._calcular_estatisticas_execucao()
            },
            categoria="SUCESSO"
        )

    async def obter_indice_centralizado(self, tipo_indice: str = "igpm") -> Optional[float]:
        """
        Obtém índice do data_manager e registra a operação para auditoria
        """
        await self.registrar_passo(
            f"SOLICITACAO_INDICE_{tipo_indice.upper()}",
            {
                "tipo_indice": tipo_indice,
                "fonte_dados": "data_manager_centralizado"
            },
            categoria="OPERACAO"
        )

        # Usa data_manager centralizado
        indice_valor = await data_manager.obter_indice_mais_recente(tipo_indice)

        await self.registrar_passo(
            f"RESULTADO_INDICE_{tipo_indice.upper()}",
            {
                "tipo_indice": tipo_indice,
                "valor_obtido": indice_valor,
                "sucesso": indice_valor is not None,
                "fonte_utilizada": "mongodb" if data_manager.mongodb_ativo else "json"
            },
            categoria="OPERACAO"
        )

        return indice_valor

    async def finalizar_rastreamento(self) -> Dict[str, Any]:
        """
        Finaliza rastreamento e consolida todos os dados
        """
        # Documento consolidado final
        documento_final = {
            "id_execucao": self.id_execucao,
            "nome_rpa": self.nome_rpa,
            "timestamp_inicio": self.passos_execucao[0]["timestamp"] if self.passos_execucao else None,
            "timestamp_fim": datetime.now().isoformat(),
            "total_passos": len(self.passos_execucao),
            "dados_contexto": self.dados_contexto,
            "passos_completos": self.passos_execucao,
            "estatisticas_finais": await self._calcular_estatisticas_execucao()
        }

        # Salva documento consolidado
        await self._salvar_documento_consolidado(documento_final)

        # Registra no data_manager para estatísticas gerais
        await data_manager.salvar_execucao_rpa(
            self.nome_rpa,
            self.dados_contexto.get("ultimo_inicio", {}).get("dados", {}),
            {
                "sucesso": "ultimo_sucesso" in self.dados_contexto,
                "tempo_execucao": documento_final["estatisticas_finais"]["tempo_total_segundos"],
                "total_passos": len(self.passos_execucao),
                "id_rastreamento": self.id_execucao
            }
        )

        logger.info(
            f"✅ Rastreamento finalizado: {self.id_execucao} ({len(self.passos_execucao)} passos)")
        return documento_final

    # Métodos auxiliares privados
    async def _salvar_json_imediato(self, documento_passo: Dict[str, Any]):
        """Salva passo imediatamente em JSON"""
        try:
            # Arquivo individual da execução
            if self.arquivo_execucao.exists():
                with open(self.arquivo_execucao, 'r', encoding='utf-8') as f:
                    dados_execucao = json.load(f)
            else:
                dados_execucao = {
                    "id_execucao": self.id_execucao,
                    "nome_rpa": self.nome_rpa,
                    "passos": []
                }

            dados_execucao["passos"].append(documento_passo)
            dados_execucao["ultimo_passo"] = documento_passo["timestamp"]
            dados_execucao["total_passos"] = len(dados_execucao["passos"])

            with open(self.arquivo_execucao, 'w', encoding='utf-8') as f:
                json.dump(dados_execucao, f, indent=2,
                          ensure_ascii=False, default=str)

        except Exception as e:
            logger.error(f"❌ Erro ao salvar JSON: {str(e)}")

    async def _salvar_mongodb_passo(self, documento_passo: Dict[str, Any]):
        """Salva passo no MongoDB se disponível"""
        if not data_manager.mongodb_ativo:
            return

        try:
            from core.mongodb_manager import mongodb_manager

            def _save_step():
                collection = mongodb_manager.database.rastreamento_passos_rpa
                return collection.insert_one(documento_passo)

            result = await asyncio.get_event_loop().run_in_executor(
                None, _save_step
            )

            if result.inserted_id:
                documento_passo["_id_mongodb"] = str(result.inserted_id)

        except Exception as e:
            logger.warning(f"⚠️ MongoDB passo falhou: {str(e)}")

    async def _salvar_documento_consolidado(self, documento_final: Dict[str, Any]):
        """Salva documento consolidado em ambos os sistemas"""
        # JSON (obrigatório)
        arquivo_consolidado = self.pasta_auditoria / \
            f"CONSOLIDADO_{self.id_execucao}.json"
        try:
            with open(arquivo_consolidado, 'w', encoding='utf-8') as f:
                json.dump(documento_final, f, indent=2,
                          ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"❌ Erro ao salvar consolidado JSON: {str(e)}")

        # MongoDB (se disponível)
        if data_manager.mongodb_ativo:
            try:
                from core.mongodb_manager import mongodb_manager

                def _save_consolidated():
                    collection = mongodb_manager.database.execucoes_consolidadas_rpa
                    return collection.insert_one(documento_final)

                result = await asyncio.get_event_loop().run_in_executor(
                    None, _save_consolidated
                )

                logger.info(f"📊 Consolidado MongoDB: {result.inserted_id}")

            except Exception as e:
                logger.warning(f"⚠️ MongoDB consolidado falhou: {str(e)}")

    async def _calcular_estatisticas_execucao(self) -> Dict[str, Any]:
        """Calcula estatísticas da execução"""
        if not self.passos_execucao:
            return {}

        inicio = datetime.fromisoformat(self.passos_execucao[0]["timestamp"])
        fim = datetime.now()
        tempo_total = (fim - inicio).total_seconds()

        categorias = {}
        for passo in self.passos_execucao:
            cat = passo["categoria"]
            categorias[cat] = categorias.get(cat, 0) + 1

        return {
            "tempo_total_segundos": tempo_total,
            "timestamp_inicio": inicio.isoformat(),
            "timestamp_fim": fim.isoformat(),
            "passos_por_categoria": categorias,
            "total_passos": len(self.passos_execucao),
            "sucesso_geral": "ERRO" not in categorias or categorias.get("SUCESSO", 0) > 0
        }

    def _obter_ip_local(self) -> str:
        """Obtém IP local para auditoria"""
        try:
            import socket
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            return "unknown"

    def _obter_url_sistema(self, sistema: str) -> str:
        """Obtém URL do sistema para registro"""
        urls = {
            "sienge": os.getenv("SIENGE_URL", "https://jmservicos.sienge.com.br"),
            "sicredi": os.getenv("SICREDI_URL", "https://empresas.sicredi.com.br"),
            "ibge": "https://www.ibge.gov.br",
            "fgv": "https://portalibre.fgv.br"
        }
        return urls.get(sistema.lower(), "unknown")

    def _pode_recuperar_erro(self, erro: Exception) -> bool:
        """Determina se erro pode ser recuperado"""
        erros_recuperaveis = [
            "ConnectionError", "TimeoutError", "HTTPError",
            "ElementNotFound", "TemporaryFailure"
        ]
        return type(erro).__name__ in erros_recuperaveis


# Função auxiliar para usar em todos os RPAs
def iniciar_rastreamento(nome_rpa: str) -> RastreamentoUnificado:
    """
    Inicia sistema de rastreamento para um RPA

    Args:
        nome_rpa: Nome do RPA (ex: "Coleta_Indices", "Sienge", etc.)

    Returns:
        Instância de RastreamentoUnificado configurada
    """
    return RastreamentoUnificado(nome_rpa)
