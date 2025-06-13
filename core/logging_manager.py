
"""
Sistema de Logging Melhorado para RPA
Baseado no código do cliente, adaptado para nossa arquitetura
"""

import logging
import os
import requests
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class LoggingManager:
    """
    Gerenciador de logs melhorado com suporte a webhook opcional
    """
    
    def __init__(self, nome_rpa: str):
        self.nome_rpa = nome_rpa
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """
        Configura o logger para salvar logs com estrutura de pastas por data
        """
        try:
            # Obtém a data atual para o nome do arquivo
            now = datetime.now()
            log_dir = f"logs/{now.strftime('%Y')}/{now.strftime('%m')}/{now.strftime('%d')}"
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"logs{now.strftime('%Y%m%d')}.txt")
            
            # Criar logger específico para evitar duplicação
            logger_name = f"RPA.{self.nome_rpa}"
            logger = logging.getLogger(logger_name)
            
            # Limpa handlers existentes para evitar duplicação
            if logger.handlers:
                logger.handlers.clear()
            
            logger.propagate = False
            logger.setLevel(logging.INFO)
            
            # Formatter personalizado
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            
            # Handler para arquivo
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            # Handler para console
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            return logger
            
        except Exception as e:
            # Fallback para logger simples
            print(f"❌ Erro ao configurar logger avançado: {e}")
            logger = logging.getLogger(f"RPA.{self.nome_rpa}")
            logger.setLevel(logging.INFO)
            return logger
    
    def register_log(self, 
                    message: str, 
                    level: str = "info", 
                    company_name: str = "Sistema RPA",
                    webhook_enabled: bool = False,
                    webhook_url: Optional[str] = None,
                    dados_extras: Optional[Dict[str, Any]] = None):
        """
        Registra mensagens de log e opcionalmente envia para webhook
        
        Args:
            message: Mensagem do log
            level: Nível do log (info, error, critical, debug)
            company_name: Nome da empresa/cliente
            webhook_enabled: Se deve enviar para webhook (default: False)
            webhook_url: URL do webhook (se habilitado)
            dados_extras: Dados adicionais para o log
        """
        
        # Mapeamento de níveis
        levels = {
            "info": logging.info,
            "error": logging.error,
            "critical": logging.critical,
            "debug": logging.debug,
            "warning": logging.warning
        }
        
        # Mapeamento do status conforme o nível do log
        status_map = {
            "info": "1",
            "error": "2", 
            "critical": "3",
            "debug": "4",
            "warning": "2"
        }
        
        # Registra no sistema de logging padrão (sempre)
        log_function = levels.get(level.lower(), logging.info)
        log_function(self.logger, message)
        
        # Prepara dados para webhook (se habilitado)
        if webhook_enabled and webhook_url:
            try:
                log_entry = {
                    "cliente": company_name,
                    "id_robo": self.nome_rpa,
                    "nivel": level.upper(),
                    "status": status_map.get(level.lower(), "1"),
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "dados_extras": dados_extras or {}
                }
                
                # Envia para webhook
                self._enviar_webhook(webhook_url, log_entry)
                
            except Exception as e:
                # Se webhook falhar, não para o sistema - apenas registra o erro
                self.logger.warning(f"⚠️ Falha ao enviar webhook: {str(e)}")
    
    def _enviar_webhook(self, webhook_url: str, dados: Dict[str, Any]):
        """
        Envia dados para webhook de forma assíncrona
        """
        try:
            response = requests.post(
                webhook_url,
                json=dados,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                self.logger.debug(f"✅ Webhook enviado com sucesso")
            else:
                self.logger.warning(f"⚠️ Webhook retornou status {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.logger.warning("⚠️ Timeout ao enviar webhook")
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"⚠️ Erro de rede no webhook: {str(e)}")
        except Exception as e:
            self.logger.warning(f"⚠️ Erro inesperado no webhook: {str(e)}")
    
    # Métodos de conveniência para diferentes níveis
    def info(self, message: str, webhook_enabled: bool = False, **kwargs):
        """Log de informação"""
        self.register_log(message, "info", webhook_enabled=webhook_enabled, **kwargs)
    
    def error(self, message: str, webhook_enabled: bool = False, **kwargs):
        """Log de erro"""
        self.register_log(message, "error", webhook_enabled=webhook_enabled, **kwargs)
    
    def warning(self, message: str, webhook_enabled: bool = False, **kwargs):
        """Log de aviso"""
        self.register_log(message, "warning", webhook_enabled=webhook_enabled, **kwargs)
    
    def debug(self, message: str, webhook_enabled: bool = False, **kwargs):
        """Log de debug"""
        self.register_log(message, "debug", webhook_enabled=webhook_enabled, **kwargs)
    
    def critical(self, message: str, webhook_enabled: bool = False, **kwargs):
        """Log crítico"""
        self.register_log(message, "critical", webhook_enabled=webhook_enabled, **kwargs)
