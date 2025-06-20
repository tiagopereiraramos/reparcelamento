
"""
Sistema de Logging Avançado - Sistema RPA v2.0
Extensão do sistema de logging com estrutura hierárquica de pastas e webhook
Baseado na solicitação do cliente mas integrado ao nosso sistema existente

Desenvolvido em Português Brasileiro
"""

import os
import json
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum

class NivelLog(Enum):
    """Níveis de log padronizados"""
    INFO = "info"
    ERROR = "error"
    CRITICAL = "critical"
    DEBUG = "debug"
    WARNING = "warning"

class StatusLog(Enum):
    """Status mapeados conforme solicitação do cliente"""
    SUCESSO = "1"      # info
    ERRO = "2"         # error
    CRITICO = "3"      # critical
    DEBUG = "4"        # debug
    ALERTA = "5"       # warning

class LoggerAvancado:
    """
    Sistema de logging avançado com estrutura hierárquica e webhook
    Integra com o sistema existente do RPA
    """
    
    def __init__(self, 
                 nome_rpa: str = "Sistema",
                 empresa: str = "Empresa", 
                 webhook_url: Optional[str] = None):
        """
        Inicializa logger avançado
        
        Args:
            nome_rpa: Nome do RPA/robô
            empresa: Nome da empresa
            webhook_url: URL do webhook para envio de logs
        """
        self.nome_rpa = nome_rpa
        self.empresa = empresa
        self.webhook_url = webhook_url or os.getenv('WEBHOOK_LOGS_URL', 'http://177.39.21.61:3009/logs')
        
        # Configurar logger padrão
        self.logger = self._configurar_logger()
        
        # Mapeamento de níveis para status
        self.status_map = {
            NivelLog.INFO.value: StatusLog.SUCESSO.value,
            NivelLog.ERROR.value: StatusLog.ERRO.value,
            NivelLog.CRITICAL.value: StatusLog.CRITICO.value,
            NivelLog.DEBUG.value: StatusLog.DEBUG.value,
            NivelLog.WARNING.value: StatusLog.ALERTA.value
        }
    
    def _configurar_logger(self) -> logging.Logger:
        """
        Configura logger com estrutura de pastas hierárquica
        Formato: outputs/YYYY/MM/DD/logsYYYYMMDD.txt
        """
        try:
            # Obtém data atual
            now = datetime.now()
            
            # Estrutura de pastas: outputs/YYYY/MM/DD/
            log_dir = Path("outputs") / now.strftime('%Y') / now.strftime('%m') / now.strftime('%d')
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Nome do arquivo: logsYYYYMMDD.txt
            log_file = log_dir / f"logs{now.strftime('%Y%m%d')}.txt"
            
            # Criar logger específico para evitar conflitos
            logger_name = f"RPA.{self.nome_rpa}.Avancado"
            logger = logging.getLogger(logger_name)
            
            # Limpar handlers existentes para evitar duplicação
            if logger.handlers:
                logger.handlers.clear()
            
            # Configurar handler de arquivo
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)
            
            # Configurar handler de console
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            
            # Adicionar handlers
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
            # Configurar nível
            logger.setLevel(logging.DEBUG)
            logger.propagate = False  # Evita duplicação
            
            return logger
            
        except Exception as e:
            print(f"❌ Erro ao configurar logger avançado: {e}")
            # Fallback para logger padrão
            return logging.getLogger(f"RPA.{self.nome_rpa}")
    
    def register_log(self, 
                    message: str, 
                    level: str = "info", 
                    dados_extras: Optional[Dict[str, Any]] = None,
                    enviar_webhook: bool = True) -> bool:
        """
        Registra log no arquivo e envia via webhook
        
        Args:
            message: Mensagem do log
            level: Nível do log (info, error, critical, debug, warning)
            dados_extras: Dados adicionais para incluir no log
            enviar_webhook: Se deve enviar via webhook
            
        Returns:
            True se log foi registrado com sucesso
        """
        try:
            # Validar nível
            nivel = level.lower()
            if nivel not in [e.value for e in NivelLog]:
                nivel = NivelLog.INFO.value
            
            # Mapear função de log
            log_functions = {
                NivelLog.INFO.value: self.logger.info,
                NivelLog.ERROR.value: self.logger.error,
                NivelLog.CRITICAL.value: self.logger.critical,
                NivelLog.DEBUG.value: self.logger.debug,
                NivelLog.WARNING.value: self.logger.warning
            }
            
            # Registrar no arquivo
            log_function = log_functions.get(nivel, self.logger.info)
            log_function(message)
            
            # Preparar dados para webhook
            if enviar_webhook:
                log_entry = {
                    "cliente": self.empresa,
                    "id_robo": self.nome_rpa,
                    "nivel": nivel.upper(),
                    "status": self.status_map.get(nivel, StatusLog.SUCESSO.value),
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "dados_extras": dados_extras or {}
                }
                
                # Enviar webhook em background (não bloquear execução)
                self._enviar_webhook(log_entry)
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao registrar log: {e}")
            return False
    
    def _enviar_webhook(self, log_entry: Dict[str, Any]) -> bool:
        """
        Envia log via webhook (não bloqueia execução principal)
        """
        try:
            if not self.webhook_url:
                return False
                
            response = requests.post(
                self.webhook_url, 
                json=log_entry,
                timeout=5  # Timeout curto para não travar
            )
            
            if response.status_code == 201:
                print(f"✅ Log enviado via webhook: {log_entry['nivel']}")
                return True
            else:
                print(f"⚠️ Webhook falhou: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"⚠️ Erro no webhook (não crítico): {e}")
            return False
    
    # Métodos de conveniência
    def info(self, message: str, dados_extras: Optional[Dict[str, Any]] = None):
        """Log de informação"""
        return self.register_log(message, "info", dados_extras)
    
    def error(self, message: str, dados_extras: Optional[Dict[str, Any]] = None):
        """Log de erro"""
        return self.register_log(message, "error", dados_extras)
    
    def critical(self, message: str, dados_extras: Optional[Dict[str, Any]] = None):
        """Log crítico"""
        return self.register_log(message, "critical", dados_extras)
    
    def debug(self, message: str, dados_extras: Optional[Dict[str, Any]] = None):
        """Log de debug"""
        return self.register_log(message, "debug", dados_extras)
    
    def warning(self, message: str, dados_extras: Optional[Dict[str, Any]] = None):
        """Log de aviso"""
        return self.register_log(message, "warning", dados_extras)


class RPAComLoggerAvancado:
    """
    Classe mixin para adicionar logger avançado aos RPAs existentes
    """
    
    def __init__(self, nome_rpa: str, empresa: str = "Empresa"):
        self.logger_avancado = LoggerAvancado(
            nome_rpa=nome_rpa,
            empresa=empresa
        )
    
    def log_avancado(self, 
                    message: str, 
                    level: str = "info", 
                    dados_extras: Optional[Dict[str, Any]] = None):
        """
        Método de conveniência para logging avançado
        Mantém compatibilidade com log_progresso existente
        """
        return self.logger_avancado.register_log(message, level, dados_extras)


# Funções de conveniência (compatibilidade com código do cliente)
def setup_logger():
    """Função de compatibilidade - mantém interface do cliente"""
    pass  # Nossa configuração é automática

def register_log(message: str, 
                level: str = "info", 
                company_name: str = "Empresa", 
                robot_name: str = "Sistema"):
    """
    Função de compatibilidade com código do cliente
    Cria logger temporário para chamadas avulsas
    """
    logger = LoggerAvancado(
        nome_rpa=robot_name,
        empresa=company_name
    )
    return logger.register_log(message, level)

# Instância global para uso direto
logger_global = LoggerAvancado()

# Funções globais de conveniência
def log_info(message: str, dados_extras: Optional[Dict[str, Any]] = None):
    """Log global de informação"""
    return logger_global.info(message, dados_extras)

def log_error(message: str, dados_extras: Optional[Dict[str, Any]] = None):
    """Log global de erro"""
    return logger_global.error(message, dados_extras)

def log_critical(message: str, dados_extras: Optional[Dict[str, Any]] = None):
    """Log global crítico"""
    return logger_global.critical(message, dados_extras)

def log_debug(message: str, dados_extras: Optional[Dict[str, Any]] = None):
    """Log global de debug"""
    return logger_global.debug(message, dados_extras)

def log_warning(message: str, dados_extras: Optional[Dict[str, Any]] = None):
    """Log global de warning"""
    return logger_global.warning(message, dados_extras)
