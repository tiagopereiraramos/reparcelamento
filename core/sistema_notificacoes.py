"""
Sistema de Notificações - Sistema RPA v2.0
Gerencia notificações por email, SMS e webhooks para eventos do sistema

Desenvolvido em Português Brasileiro
"""

import os
import json
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from enum import Enum
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TipoNotificacao(Enum):
    """Tipos de notificação disponíveis"""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"

class PrioridadeNotificacao(Enum):
    """Níveis de prioridade das notificações"""
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"

class EventoRPA(Enum):
    """Eventos do sistema RPA que podem gerar notificações"""
    RPA_INICIADO = "rpa_iniciado"
    RPA_CONCLUIDO = "rpa_concluido"
    RPA_ERRO = "rpa_erro"
    WORKFLOW_INICIADO = "workflow_iniciado"
    WORKFLOW_CONCLUIDO = "workflow_concluido"
    WORKFLOW_ERRO = "workflow_erro"
    INDICES_ATUALIZADOS = "indices_atualizados"
    CONTRATOS_IDENTIFICADOS = "contratos_identificados"
    PROCESSAMENTO_SIENGE = "processamento_sienge"
    PROCESSAMENTO_SICREDI = "processamento_sicredi"
    SISTEMA_SAUDE = "sistema_saude"
    ERRO_CRITICO = "erro_critico"

class NotificadorEmail:
    """Gerenciador de notificações por email"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_usuario = os.getenv('EMAIL_USUARIO')
        self.email_senha = os.getenv('EMAIL_SENHA')
        self.email_remetente = os.getenv('EMAIL_REMETENTE', self.email_usuario)
        
    def enviar_email(self, destinatario: str, assunto: str, corpo: str, html: bool = False) -> bool:
        """Envia email para destinatário específico"""
        try:
            if not all([self.email_usuario, self.email_senha]):
                logger.warning("Credenciais de email não configuradas")
                return False
                
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_remetente
            msg['To'] = destinatario
            msg['Subject'] = assunto
            
            if html:
                msg.attach(MIMEText(corpo, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as servidor:
                servidor.starttls()
                servidor.login(self.email_usuario, self.email_senha)
                servidor.send_message(msg)
                
            logger.info(f"Email enviado com sucesso para {destinatario}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return False

class NotificadorSMS:
    """Gerenciador de notificações por SMS via Twilio"""
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.numero_twilio = os.getenv('TWILIO_PHONE_NUMBER')
        
    def enviar_sms(self, numero_destino: str, mensagem: str) -> bool:
        """Envia SMS para número específico"""
        try:
            if not all([self.account_sid, self.auth_token, self.numero_twilio]):
                logger.warning("Credenciais do Twilio não configuradas")
                return False
                
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            
            message = client.messages.create(
                body=mensagem,
                from_=self.numero_twilio,
                to=numero_destino
            )
            
            logger.info(f"SMS enviado com sucesso para {numero_destino}: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar SMS: {e}")
            return False

class NotificadorWebhook:
    """Gerenciador de notificações via webhook"""
    
    def enviar_webhook(self, url: str, dados: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> bool:
        """Envia notificação via webhook"""
        try:
            headers_default = {'Content-Type': 'application/json'}
            if headers:
                headers_default.update(headers)
                
            response = requests.post(
                url,
                json=dados,
                headers=headers_default,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook enviado com sucesso para {url}")
                return True
            else:
                logger.warning(f"Webhook falhou: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar webhook: {e}")
            return False

class SistemaNotificacoes:
    """Sistema principal de notificações do RPA"""
    
    def __init__(self):
        self.notificador_email = NotificadorEmail()
        self.notificador_sms = NotificadorSMS()
        self.notificador_webhook = NotificadorWebhook()
        self.configuracoes = self._carregar_configuracoes()
        
    def _carregar_configuracoes(self) -> Dict[str, Any]:
        """Carrega configurações de notificação"""
        try:
            if os.path.exists('config/notificacoes.json'):
                with open('config/notificacoes.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar configurações: {e}")
            
        # Configurações padrão
        return {
            "email": {
                "habilitado": True,
                "destinatarios": [
                    os.getenv('EMAIL_ADMIN', 'admin@empresa.com')
                ]
            },
            "sms": {
                "habilitado": False,
                "numeros": [
                    os.getenv('TELEFONE_ADMIN', '+5511999999999')
                ]
            },
            "webhook": {
                "habilitado": False,
                "urls": []
            },
            "eventos": {
                EventoRPA.RPA_ERRO.value: {
                    "prioridade": PrioridadeNotificacao.ALTA.value,
                    "canais": [TipoNotificacao.EMAIL.value, TipoNotificacao.SMS.value]
                },
                EventoRPA.ERRO_CRITICO.value: {
                    "prioridade": PrioridadeNotificacao.CRITICA.value,
                    "canais": [TipoNotificacao.EMAIL.value, TipoNotificacao.SMS.value, TipoNotificacao.WEBHOOK.value]
                },
                EventoRPA.RPA_CONCLUIDO.value: {
                    "prioridade": PrioridadeNotificacao.BAIXA.value,
                    "canais": [TipoNotificacao.EMAIL.value]
                },
                EventoRPA.WORKFLOW_CONCLUIDO.value: {
                    "prioridade": PrioridadeNotificacao.MEDIA.value,
                    "canais": [TipoNotificacao.EMAIL.value]
                }
            }
        }
    
    def salvar_configuracoes(self):
        """Salva configurações de notificação"""
        try:
            os.makedirs('config', exist_ok=True)
            with open('config/notificacoes.json', 'w', encoding='utf-8') as f:
                json.dump(self.configuracoes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
    
    def notificar_evento(self, evento: EventoRPA, dados: Dict[str, Any]) -> Dict[str, bool]:
        """Notifica sobre um evento do sistema"""
        resultado = {}
        
        try:
            config_evento = self.configuracoes.get('eventos', {}).get(evento.value, {})
            canais = config_evento.get('canais', [])
            prioridade = config_evento.get('prioridade', PrioridadeNotificacao.MEDIA.value)
            
            # Gerar conteúdo da notificação
            conteudo = self._gerar_conteudo_notificacao(evento, dados, prioridade)
            
            # Enviar por cada canal configurado
            for canal in canais:
                if canal == TipoNotificacao.EMAIL.value:
                    resultado['email'] = self._enviar_notificacao_email(evento, conteudo, dados)
                elif canal == TipoNotificacao.SMS.value:
                    resultado['sms'] = self._enviar_notificacao_sms(evento, conteudo, dados)
                elif canal == TipoNotificacao.WEBHOOK.value:
                    resultado['webhook'] = self._enviar_notificacao_webhook(evento, conteudo, dados)
            
            # Log do resultado
            sucessos = sum(1 for v in resultado.values() if v)
            total = len(resultado)
            logger.info(f"Evento {evento.value}: {sucessos}/{total} notificações enviadas")
            
        except Exception as e:
            logger.error(f"Erro ao processar notificação do evento {evento.value}: {e}")
            
        return resultado
    
    def _gerar_conteudo_notificacao(self, evento: EventoRPA, dados: Dict[str, Any], prioridade: str) -> Dict[str, str]:
        """Gera conteúdo personalizado para cada tipo de notificação"""
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        # Mapeamento de eventos para títulos e mensagens
        templates = {
            EventoRPA.RPA_INICIADO: {
                'assunto': f'🚀 RPA Iniciado - {dados.get("nome_rpa", "Sistema")}',
                'corpo': f'RPA "{dados.get("nome_rpa", "Desconhecido")}" foi iniciado às {timestamp}.',
                'sms': f'RPA {dados.get("nome_rpa", "")} iniciado às {timestamp}'
            },
            EventoRPA.RPA_CONCLUIDO: {
                'assunto': f'✅ RPA Concluído com Sucesso - {dados.get("nome_rpa", "Sistema")}',
                'corpo': f'RPA "{dados.get("nome_rpa", "")}" concluído com sucesso.\nTempo de execução: {dados.get("tempo_execucao", "N/A")}\nResultados: {dados.get("resumo_resultados", "N/A")}',
                'sms': f'✅ RPA {dados.get("nome_rpa", "")} concluído com sucesso em {dados.get("tempo_execucao", "")}'
            },
            EventoRPA.RPA_ERRO: {
                'assunto': f'❌ ERRO no RPA - {dados.get("nome_rpa", "Sistema")}',
                'corpo': f'ERRO detectado no RPA "{dados.get("nome_rpa", "")}".\nErro: {dados.get("erro", "Não especificado")}\nDetalhes: {dados.get("detalhes", "N/A")}\nAção necessária: Verificar logs e corrigir problema.',
                'sms': f'❌ ERRO no RPA {dados.get("nome_rpa", "")}: {dados.get("erro", "")[:100]}'
            },
            EventoRPA.WORKFLOW_CONCLUIDO: {
                'assunto': f'🔄 Workflow Completo - Sistema RPA',
                'corpo': f'Workflow de reparcelamento concluído.\nRPAs executados: {dados.get("rpas_executados", "N/A")}\nContratos processados: {dados.get("contratos_processados", 0)}\nTempo total: {dados.get("tempo_total", "N/A")}',
                'sms': f'🔄 Workflow concluído: {dados.get("contratos_processados", 0)} contratos processados'
            },
            EventoRPA.INDICES_ATUALIZADOS: {
                'assunto': f'📊 Índices Econômicos Atualizados',
                'corpo': f'Índices econômicos atualizados com sucesso.\nIPCA: {dados.get("ipca", "N/A")}\nIGPM: {dados.get("igpm", "N/A")}\nData de referência: {dados.get("data_referencia", "N/A")}',
                'sms': f'📊 Índices atualizados: IPCA {dados.get("ipca", "")} IGPM {dados.get("igpm", "")}'
            },
            EventoRPA.CONTRATOS_IDENTIFICADOS: {
                'assunto': f'📋 Contratos para Reparcelamento Identificados',
                'corpo': f'Foram identificados {dados.get("quantidade_contratos", 0)} contratos para reparcelamento.\nCritérios: {dados.get("criterios", "N/A")}\nPróxima ação: Processamento automático via RPAs 3 e 4.',
                'sms': f'📋 {dados.get("quantidade_contratos", 0)} contratos identificados para reparcelamento'
            }
        }
        
        template = templates.get(evento, {
            'assunto': f'Sistema RPA - {evento.value}',
            'corpo': f'Evento: {evento.value}\nDados: {json.dumps(dados, indent=2)}',
            'sms': f'Sistema RPA: {evento.value}'
        })
        
        # Adicionar prioridade ao assunto se alta ou crítica
        if prioridade in [PrioridadeNotificacao.ALTA.value, PrioridadeNotificacao.CRITICA.value]:
            template['assunto'] = f"[{prioridade.upper()}] {template['assunto']}"
        
        return template
    
    def _enviar_notificacao_email(self, evento: EventoRPA, conteudo: Dict[str, str], dados: Dict[str, Any]) -> bool:
        """Envia notificação por email"""
        if not self.configuracoes.get('email', {}).get('habilitado', False):
            return False
            
        destinatarios = self.configuracoes.get('email', {}).get('destinatarios', [])
        
        # Gerar HTML para email
        corpo_html = self._gerar_email_html(evento, conteudo, dados)
        
        sucesso = True
        for destinatario in destinatarios:
            resultado = self.notificador_email.enviar_email(
                destinatario,
                conteudo['assunto'],
                corpo_html,
                html=True
            )
            sucesso = sucesso and resultado
            
        return sucesso
    
    def _enviar_notificacao_sms(self, evento: EventoRPA, conteudo: Dict[str, str], dados: Dict[str, Any]) -> bool:
        """Envia notificação por SMS"""
        if not self.configuracoes.get('sms', {}).get('habilitado', False):
            return False
            
        numeros = self.configuracoes.get('sms', {}).get('numeros', [])
        
        sucesso = True
        for numero in numeros:
            resultado = self.notificador_sms.enviar_sms(numero, conteudo['sms'])
            sucesso = sucesso and resultado
            
        return sucesso
    
    def _enviar_notificacao_webhook(self, evento: EventoRPA, conteudo: Dict[str, str], dados: Dict[str, Any]) -> bool:
        """Envia notificação via webhook"""
        if not self.configuracoes.get('webhook', {}).get('habilitado', False):
            return False
            
        urls = self.configuracoes.get('webhook', {}).get('urls', [])
        
        payload = {
            'evento': evento.value,
            'timestamp': datetime.now().isoformat(),
            'assunto': conteudo['assunto'],
            'corpo': conteudo['corpo'],
            'dados': dados
        }
        
        sucesso = True
        for url in urls:
            resultado = self.notificador_webhook.enviar_webhook(url, payload)
            sucesso = sucesso and resultado
            
        return sucesso
    
    def _gerar_email_html(self, evento: EventoRPA, conteudo: Dict[str, str], dados: Dict[str, Any]) -> str:
        """Gera email em formato HTML"""
        # Cores baseadas no tipo de evento
        cores = {
            EventoRPA.RPA_CONCLUIDO: "#28a745",
            EventoRPA.WORKFLOW_CONCLUIDO: "#28a745",
            EventoRPA.RPA_ERRO: "#dc3545",
            EventoRPA.ERRO_CRITICO: "#dc3545",
            EventoRPA.RPA_INICIADO: "#007bff",
            EventoRPA.INDICES_ATUALIZADOS: "#17a2b8",
            EventoRPA.CONTRATOS_IDENTIFICADOS: "#ffc107"
        }
        
        cor = cores.get(evento, "#6c757d")
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{conteudo['assunto']}</title>
        </head>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="background-color: {cor}; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0; font-size: 24px;">{conteudo['assunto']}</h1>
                </div>
                <div style="padding: 20px;">
                    <div style="white-space: pre-line; line-height: 1.6; color: #333;">
                        {conteudo['corpo']}
                    </div>
                    <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 4px; border-left: 4px solid {cor};">
                        <strong>Detalhes Técnicos:</strong><br>
                        <small style="color: #666;">
                            Sistema: RPA de Reparcelamento v2.0<br>
                            Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br>
                            Evento: {evento.value}
                        </small>
                    </div>
                </div>
                <div style="padding: 20px; background-color: #f8f9fa; border-radius: 0 0 8px 8px; text-align: center; color: #666; font-size: 12px;">
                    Esta é uma notificação automática do Sistema RPA de Reparcelamento.<br>
                    Não responda a este email.
                </div>
            </div>
        </body>
        </html>
        """
    
    def testar_configuracao(self) -> Dict[str, Any]:
        """Testa todas as configurações de notificação"""
        resultados = {}
        
        # Testar email
        if self.configuracoes.get('email', {}).get('habilitado', False):
            resultado_email = self.notificar_evento(
                EventoRPA.SISTEMA_SAUDE,
                {
                    'nome_rpa': 'Teste de Configuração',
                    'status': 'Sistema funcionando corretamente',
                    'timestamp': datetime.now().isoformat()
                }
            )
            resultados['email'] = resultado_email.get('email', False)
        
        # Testar SMS
        if self.configuracoes.get('sms', {}).get('habilitado', False):
            resultado_sms = self.notificar_evento(
                EventoRPA.SISTEMA_SAUDE,
                {'status': 'Teste SMS'}
            )
            resultados['sms'] = resultado_sms.get('sms', False)
        
        # Testar webhook
        if self.configuracoes.get('webhook', {}).get('habilitado', False):
            resultado_webhook = self.notificar_evento(
                EventoRPA.SISTEMA_SAUDE,
                {'status': 'Teste Webhook'}
            )
            resultados['webhook'] = resultado_webhook.get('webhook', False)
        
        return resultados

# Instância global do sistema de notificações
sistema_notificacoes = SistemaNotificacoes()

def notificar(evento: EventoRPA, dados: Dict[str, Any]) -> Dict[str, bool]:
    """Função utilitária para notificar eventos"""
    return sistema_notificacoes.notificar_evento(evento, dados)

def configurar_notificacoes(config: Dict[str, Any]):
    """Atualiza configurações de notificação"""
    sistema_notificacoes.configuracoes.update(config)
    sistema_notificacoes.salvar_configuracoes()

def testar_notificacoes() -> Dict[str, Any]:
    """Testa configurações de notificação"""
    return sistema_notificacoes.testar_configuracao()