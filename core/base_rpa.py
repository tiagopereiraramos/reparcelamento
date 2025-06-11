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

# Import para type hints
if TYPE_CHECKING:
    from core.browser_manager import RPABrowser


def get_logger(nome: str) -> logging.Logger:
    """Cria logger simples para RPA sem duplicação"""
    logger = logging.getLogger(nome)

    # Evita duplicação - limpa handlers existentes
    if logger.handlers:
        logger.handlers.clear()

    # Evita propagação para o logger raiz (evita duplicação)
    logger.propagate = False

    # Adiciona apenas um handler personalizado
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger


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

    def __init__(self, nome_rpa: str, usar_browser: bool = True):
        """
        Inicializa RPA base

        Args:
            nome_rpa: Nome identificador do RPA
            usar_browser: Se deve inicializar o browser Selenium
        """
        self.nome_rpa = nome_rpa
        self.usar_browser = usar_browser
        self.browser: Optional['RPABrowser'] = None
        self.mongo_manager: Optional[Any] = None
        self.inicio_execucao = None
        self.logger = get_logger(f"RPA.{nome_rpa}")

        self.logger.info(f"🤖 Inicializando RPA: {nome_rpa}")

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
        Salva execução no MongoDB para auditoria

        Args:
            parametros: Parâmetros de entrada
            resultado: Resultado da execução
        """
        try:
            if not self.mongo_manager or not self.mongo_manager.conectado:
                return

            # Usa a estrutura correta do MongoDB Manager
            collection = self.mongo_manager.database.execucoes_rpa

            documento = {
                "nome_rpa": self.nome_rpa,
                "timestamp_inicio": self.inicio_execucao,
                "timestamp_fim": datetime.now(),
                "parametros_entrada": parametros,
                "resultado": resultado.para_dict(),
                "sucesso": resultado.sucesso,
                "tempo_execucao_segundos": resultado.tempo_execucao,
                "mensagem": resultado.mensagem,
                "erro": resultado.erro
            }

            await collection.insert_one(documento)
            self.logger.info("💾 Execução salva no MongoDB para auditoria")

        except Exception as e:
            self.logger.error(f"⚠️ Erro ao salvar execução: {str(e)}")

    def log_progresso(self,
                      mensagem: str,
                      dados: Optional[Dict[str, Any]] = None):
        """
        Log de progresso durante execução

        Args:
            mensagem: Mensagem de progresso
            dados: Dados adicionais para log
        """
        if dados:
            self.logger.info(f"📈 {mensagem}", extra=dados)
        else:
            self.logger.info(f"📈 {mensagem}")

    def log_erro(self, mensagem: str, erro: Exception):
        """
        Log de erro detalhado

        Args:
            mensagem: Mensagem de contexto
            erro: Exception ocorrida
        """
        self.logger.error(f"❌ {mensagem}: {str(erro)}")
        self.logger.error(f"🔍 Traceback: {traceback.format_exc()}")

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
