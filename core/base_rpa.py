"""
BaseRPA - Classe base para todos os RPAs do sistema
Desenvolvido em Português Brasileiro para máxima simplicidade e manutenção
"""

import structlog
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING
import json
import traceback
import logging
import os
from core.logger_avancado import LoggerAvancado

# Import para type hints
if TYPE_CHECKING:
    from core.browser_manager import RPABrowser


# Importações para persistência
try:
    from core.mongodb_manager import mongodb_manager
    MONGODB_DISPONIVEL = True
except ImportError:
    MONGODB_DISPONIVEL = False

logger = structlog.get_logger()


class ResultadoRPA:
    """
    Resultado padronizado de execução de RPA
    """

    def __init__(self,
                 sucesso: bool,
                 mensagem: str,
                 dados: Optional[Dict[str, Any]] = None,
                 erro: Optional[str] = None,
                 tempo_execucao: Optional[float] = None):
        self.sucesso = sucesso
        self.mensagem = mensagem
        self.dados = dados or {}
        self.erro = erro
        self.tempo_execucao = tempo_execucao
        self.timestamp = datetime.now()

    def para_dict(self) -> Dict[str, Any]:
        """Converte resultado para dicionário"""
        return {
            "sucesso": self.sucesso,
            "mensagem": self.mensagem,
            "dados": self.dados,
            "erro": self.erro,
            "tempo_execucao": self.tempo_execucao,
            "timestamp": self.timestamp.isoformat()
        }

    def __str__(self) -> str:
        status = "✅ SUCESSO" if self.sucesso else "❌ ERRO"
        return f"{status}: {self.mensagem}"


class BaseRPA(ABC):
    """
    Classe base para todos os RPAs do sistema

    Fornece funcionalidades comuns:
    - Inicialização do browser
    - Conexão com MongoDB
    - Logging estruturado
    - Tratamento de erros
    - Persistência de resultados
    """

    def __init__(self, nome_rpa: str, usar_browser: bool = True, webhook_enabled: bool = False, webhook_url: Optional[str] = None, company_name: str = "Sistema RPA"):
        """
        Inicializa RPA base

        Args:
            nome_rpa: Nome identificador do RPA
            usar_browser: Se deve inicializar o browser Selenium
            webhook_enabled: Se deve enviar logs para webhook (default: False)
            webhook_url: URL do webhook (se habilitado)
            company_name: Nome da empresa/cliente
        """
        self.nome_rpa = nome_rpa
        self.usar_browser = usar_browser
        self.browser: Optional['RPABrowser'] = None
        self.mongo_manager: Optional[Any] = None
        self.inicio_execucao = None

        # Sistema de logging avançado
        self.logger_avancado = LoggerAvancado(
            nome_rpa=nome_rpa,
            empresa=company_name,
            webhook_url=webhook_url
        )

        self.webhook_enabled = webhook_enabled
        self.webhook_url = webhook_url
        self.company_name = company_name

        # Compatibilidade com código antigo
        self.logger = structlog.get_logger()

        self.log_info(f"🤖 Inicializando RPA: {nome_rpa}")

    async def inicializar(self) -> bool:
        """
        Inicializa recursos necessários para o RPA

        Returns:
            True se inicialização bem-sucedida
        """
        try:
            self.logger.info("🔧 Inicializando recursos do RPA...")

            # Conecta ao MongoDB se disponível
            if MONGODB_DISPONIVEL:
                self.mongo_manager = mongodb_manager
                self.logger.info("✅ MongoDB conectado com sucesso")

            # Inicializa browser se necessário
            if self.usar_browser:
                try:
                    from core.browser_manager import RPABrowser
                    self.browser = RPABrowser(headless=False)
                    self.logger.info("✅ Browser Selenium inicializado")
                except ImportError:
                    self.logger.warning("⚠️ Browser não disponível")
                    self.browser = None

            return True

        except Exception as e:
            self.logger.error(f"❌ Erro na inicialização: {str(e)}")
            return False

    async def finalizar(self):
        """
        Finaliza recursos e limpa conexões
        """
        try:
            self.logger.info("🧹 Finalizando recursos do RPA...")

            # Fecha browser
            if self.browser:
                self.browser.close()
                self.logger.info("✅ Browser fechado")

            # Desconecta MongoDB
            if self.mongo_manager:
                if hasattr(self.mongo_manager, 'desconectar'):
                    await self.mongo_manager.desconectar()
                elif hasattr(self.mongo_manager, 'disconnect'):
                    await self.mongo_manager.disconnect()
                self.logger.info("✅ MongoDB desconectado")

        except Exception as e:
            self.logger.error(f"⚠️ Erro na finalização: {str(e)}")

    @abstractmethod
    async def executar(self, parametros: Dict[str, Any]) -> ResultadoRPA:
        """
        Método principal que deve ser implementado por cada RPA

        Args:
            parametros: Parâmetros específicos para execução do RPA

        Returns:
            ResultadoRPA com resultado da execução
        """
        pass

    async def executar_com_monitoramento(
            self, parametros: Dict[str, Any]) -> ResultadoRPA:
        """
        Executa RPA com monitoramento completo e persistência

        Args:
            parametros: Parâmetros para execução

        Returns:
            ResultadoRPA com resultado da execução
        """
        self.inicio_execucao = datetime.now()
        resultado = None

        try:
            self.logger.info(f"🚀 Iniciando execução do RPA: {self.nome_rpa}")
            self.logger.info(
                f"📋 Parâmetros: {json.dumps(parametros, indent=2, ensure_ascii=False)}"
            )

            # Inicializa recursos
            if not await self.inicializar():
                return ResultadoRPA(
                    sucesso=False,
                    mensagem="Falha na inicialização dos recursos",
                    erro="Erro na inicialização")

            # Executa RPA específico
            resultado = await self.executar(parametros)

            # Calcula tempo de execução
            tempo_execucao = (datetime.now() -
                              self.inicio_execucao).total_seconds()
            resultado.tempo_execucao = tempo_execucao

            # Log do resultado
            if resultado.sucesso:
                self.logger.info(
                    f"✅ RPA executado com sucesso em {tempo_execucao:.2f}s")
                self.logger.info(f"📊 Resultado: {resultado.mensagem}")
            else:
                self.logger.error(f"❌ RPA falhou após {tempo_execucao:.2f}s")
                self.logger.error(f"💥 Erro: {resultado.erro}")

            # Persiste resultado no MongoDB
            await self._salvar_execucao(parametros, resultado)

            return resultado

        except Exception as e:
            tempo_execucao = (datetime.now() -
                              self.inicio_execucao).total_seconds()
            erro_detalhado = f"{str(e)}\n{traceback.format_exc()}"

            self.logger.error(f"💥 Erro inesperado no RPA: {erro_detalhado}")

            resultado = ResultadoRPA(
                sucesso=False,
                mensagem=f"Erro inesperado durante execução",
                erro=erro_detalhado,
                tempo_execucao=tempo_execucao)

            # Persiste erro no MongoDB
            await self._salvar_execucao(parametros, resultado)

            return resultado

        finally:
            # Sempre finaliza recursos
            await self.finalizar()

    async def _salvar_execucao(self, parametros: Dict[str, Any],
                               resultado: ResultadoRPA):
        """
        Salva execução usando data_manager unificado (MongoDB + JSON)

        Args:
            parametros: Parâmetros de entrada
            resultado: Resultado da execução
        """
        try:
            # Usa data_manager unificado que SEMPRE salva em MongoDB + JSON
            from core.data_manager import data_manager
            
            resultados_salvamento = await data_manager.salvar_execucao_rpa(
                nome_rpa=self.nome_rpa,
                parametros=parametros,
                resultado=resultado.para_dict()
            )

            # Log do resultado
            if resultados_salvamento.get("json") == "sucesso":
                self.logger.info("💾 Execução salva com sucesso (sistema híbrido)")
            else:
                self.logger.warning("⚠️ Falha ao salvar execução")

        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar execução: {str(e)}")

    def log_progresso(self,
                      mensagem: str,
                      dados: Optional[Dict[str, Any]] = None):
        """
        Log de progresso durante execução

        Args:
            mensagem: Mensagem de progresso
            dados: Dados adicionais para log
        """
        self.log_info(f"📈 {mensagem}", dados_extras=dados)

    def log_erro(self, mensagem: str, erro: Exception):
        """
        Log de erro detalhado

        Args:
            mensagem: Mensagem de contexto
            erro: Exception ocorrida
        """
        erro_detalhes = {
            "erro_tipo": type(erro).__name__,
            "erro_mensagem": str(erro),
            "traceback": traceback.format_exc()
        }
        self.log_error(f"❌ {mensagem}: {str(erro)}", dados_extras=erro_detalhes)
        self.log_error(f"🔍 Traceback: {traceback.format_exc()}")

    # Métodos de logging melhorados
    def log_info(self, mensagem: str, dados_extras: Optional[Dict[str, Any]] = None):
        """Log de informação com webhook opcional"""
        self.logger_avancado.register_log(
            mensagem, "info", dados_extras, self.webhook_enabled
        )

    def log_error(self, mensagem: str, dados_extras: Optional[Dict[str, Any]] = None):
        """Log de erro com webhook opcional"""
        self.logger_avancado.register_log(
            mensagem, "error", dados_extras, self.webhook_enabled
        )

    def log_warning(self, mensagem: str, dados_extras: Optional[Dict[str, Any]] = None):
        """Log de aviso com webhook opcional"""
        self.logger_avancado.register_log(
            mensagem, "warning", dados_extras, self.webhook_enabled
        )

    def log_debug(self, mensagem: str, dados_extras: Optional[Dict[str, Any]] = None):
        """Log de debug com webhook opcional"""
        self.logger_avancado.register_log(
            mensagem, "debug", dados_extras, self.webhook_enabled
        )

    def log_critical(self, mensagem: str, dados_extras: Optional[Dict[str, Any]] = None):
        """Log crítico com webhook opcional"""
        self.logger_avancado.register_log(
            mensagem, "critical", dados_extras, self.webhook_enabled
        )

    # ========== MÉTODOS DO BROWSER (DELEGATE) ==========
    # Estes métodos delegam para self.browser e aparecem no IntelliSense

    def get(self, url: str):
        """Navega para URL (delegate para browser)"""
        if self.browser:
            return self.browser.get(url)

    def get_page(self, url: str) -> bool:
        """Navega para página com validação (delegate para browser)"""
        if self.browser:
            return self.browser.get_page(url)
        return False

    def find_element(self, xpath: str, condition: str = "presence"):
        """Encontra elemento na página (delegate para browser)"""
        if self.browser:
            return self.browser.find_element(xpath, condition)
        return None

    def find_elements(self, xpath: str, condition: str = "located_all"):
        """Encontra elementos na página (delegate para browser)"""
        if self.browser:
            return self.browser.find_elements(xpath, condition)
        return []

    def click(self, xpath: str) -> None:
        """Clica em elemento (delegate para browser)"""
        if self.browser:
            return self.browser.click(xpath)

    def send_text(self,
                  xpath: str,
                  text: str,
                  clear: bool = False,
                  timeout: int = 15,
                  verify: bool = False) -> None:
        """Envia texto para elemento (delegate para browser)"""
        if self.browser:
            return self.browser.send_text(xpath, text, clear, timeout, verify)

    def get_text(self, xpath: str, timeout: int = 10) -> str:
        """Obtém texto do elemento (delegate para browser)"""
        if self.browser:
            return self.browser.get_text(xpath, timeout)
        return ""

    def check_for_error(self,
                        xpath: str,
                        condition: Optional[str] = None,
                        retry: int = 1) -> bool:
        """Verifica se elemento de erro está presente (delegate para browser)"""
        if self.browser:
            return self.browser.check_for_error(xpath, condition, retry)
        return False

    def set_timeout(self, timeout: int):
        """Define timeout do browser (delegate para browser)"""
        if self.browser:
            return self.browser.set_timeout(timeout)

    def reset_timeout(self):
        """Reseta timeout do browser (delegate para browser)"""
        if self.browser:
            return self.browser.reset_timeout()

    def get_page_source(self) -> str:
        """Obtém código fonte da página (delegate para browser)"""
        if self.browser:
            return self.browser.get_page_source()
        return ""

    def on_new_window(self, url: str):
        """Context manager para nova janela (delegate para browser)"""
        if self.browser:
            return self.browser.on_new_window(url)
        return None

    def on_iframe(self, xpath: str):
        """Context manager para iframe (delegate para browser)"""
        if self.browser:
            return self.browser.on_iframe(xpath)
        return None