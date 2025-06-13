"""
Sistema de Notificações Simples - Sistema RPA v2.0
Notificações por email usando Google Gmail API com conta de serviço

Desenvolvido em Português Brasileiro
"""

import logging
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import os
import base64
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from enum import Enum
from core.logger_avancado import LoggerAvancado


# Configurar logger para notificações
logger_manager = LoggerAvancado(
    nome_rpa="NotificacoesSimples",
    empresa="Sistema RPA"
)
logger = logger_manager.logger

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    GOOGLE_DISPONIVEL = True
except ImportError:
    GOOGLE_DISPONIVEL = False
    logger.warning("Bibliotecas do Google não disponíveis. Instale: pip install google-api-python-client google-auth")

class TipoEvento(Enum):
    """Tipos de evento do sistema RPA"""
    SUCESSO = "sucesso"
    ERRO = "erro"
    INICIO = "inicio"
    CONCLUIDO = "concluido"
    ALERTA = "alerta"

class NotificadorEmail:
    """Notificador simples usando Gmail API"""

    def __init__(self):
        self.service = None
        self.email_remetente = None
        self._inicializar_gmail()

    def _inicializar_gmail(self):
        """Inicializa conexão com Gmail API"""
        try:
            if not GOOGLE_DISPONIVEL:
                logger.warning("Google APIs não disponíveis")
                return

            # Verificar se existe arquivo de credenciais
            arquivo_credenciais = None
            possiveis_arquivos = [
                'credentials/google_service_account.json',
                'deploy/credentials/google_service_account.json',
                'gspread-459713-aab8a657f9b0.json'  # Arquivo existente do projeto
            ]

            for arquivo in possiveis_arquivos:
                if os.path.exists(arquivo):
                    arquivo_credenciais = arquivo
                    break

            if not arquivo_credenciais:
                logger.warning("Arquivo de credenciais do Google não encontrado")
                return

            # Carregar credenciais
            credentials = Credentials.from_service_account_file(
                arquivo_credenciais,
                scopes=['https://www.googleapis.com/auth/gmail.send']
            )

            # Configurar email do remetente (deve ser delegado na conta de serviço)
            self.email_remetente = os.getenv('EMAIL_REMETENTE', 'sistema.rpa@empresa.com')

            # Delegar credenciais para o email remetente
            delegated_credentials = credentials.with_subject(self.email_remetente)

            # Criar serviço Gmail
            self.service = build('gmail', 'v1', credentials=delegated_credentials)

            logger.info(f"Gmail API inicializada com sucesso para {self.email_remetente}")

        except Exception as e:
            logger.error(f"Erro ao inicializar Gmail API: {e}")
            self.service = None

    def enviar_email(self, destinatario: str, assunto: str, corpo_html: str) -> bool:
        """Envia email usando Gmail API"""
        try:
            if not self.service:
                logger.warning("Gmail API não inicializada")
                return False

            # Criar mensagem
            message = MIMEMultipart('alternative')
            message['to'] = destinatario
            message['from'] = self.email_remetente
            message['subject'] = assunto

            # Adicionar corpo HTML
            html_part = MIMEText(corpo_html, 'html', 'utf-8')
            message.attach(html_part)

            # Codificar mensagem
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Enviar via Gmail API
            self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            logger.info(f"Email enviado com sucesso para {destinatario}")
            return True

        except Exception as e:
            logger.error(f"Erro ao enviar email para {destinatario}: {e}")
            return False

class GeradorTemplates:
    """Gerador de templates HTML para notificações"""

    @staticmethod
    def gerar_template_base(titulo: str, conteudo: str, tipo_evento: TipoEvento) -> str:
        """Gera template HTML base para notificações"""

        # Cores por tipo de evento
        cores = {
            TipoEvento.SUCESSO: {"primaria": "#28a745", "secundaria": "#d4edda"},
            TipoEvento.ERRO: {"primaria": "#dc3545", "secundaria": "#f8d7da"},
            TipoEvento.ALERTA: {"primaria": "#ffc107", "secundaria": "#fff3cd"},
            TipoEvento.INICIO: {"primaria": "#007bff", "secundaria": "#d1ecf1"},
            TipoEvento.CONCLUIDO: {"primaria": "#17a2b8", "secundaria": "#d1ecf1"}
        }

        cor_config = cores.get(tipo_evento, cores[TipoEvento.ALERTA])

        # Ícones por tipo
        icones = {
            TipoEvento.SUCESSO: "✅",
            TipoEvento.ERRO: "❌",
            TipoEvento.ALERTA: "⚠️",
            TipoEvento.INICIO: "🚀",
            TipoEvento.CONCLUIDO: "🎉"
        }

        icone = icones.get(tipo_evento, "📋")
        timestamp = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')

        return f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{titulo}</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f5f5;">
                <tr>
                    <td align="center" style="padding: 40px 20px;">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); overflow: hidden;">

                            <!-- Cabeçalho -->
                            <tr>
                                <td style="background: linear-gradient(135deg, {cor_config['primaria']}, {cor_config['primaria']}dd); color: white; padding: 30px; text-align: center;">
                                    <div style="font-size: 48px; margin-bottom: 10px;">{icone}</div>
                                    <h1 style="margin: 0; font-size: 24px; font-weight: 600;">{titulo}</h1>
                                    <p style="margin: 8px 0 0 0; font-size: 14px; opacity: 0.9;">Sistema RPA de Reparcelamento</p>
                                </td>
                            </tr>

                            <!-- Conteúdo Principal -->
                            <tr>
                                <td style="padding: 30px;">
                                    <div style="line-height: 1.6; color: #333; font-size: 16px;">
                                        {conteudo}
                                    </div>
                                </td>
                            </tr>

                            <!-- Informações Técnicas -->
                            <tr>
                                <td style="padding: 0 30px 30px 30px;">
                                    <div style="background-color: {cor_config['secundaria']}; padding: 20px; border-radius: 8px; border-left: 4px solid {cor_config['primaria']};">
                                        <h3 style="margin: 0 0 10px 0; color: {cor_config['primaria']}; font-size: 16px;">📊 Informações do Sistema</h3>
                                        <table width="100%" style="font-size: 14px; color: #666;">
                                            <tr>
                                                <td width="30%"><strong>Data/Hora:</strong></td>
                                                <td>{timestamp}</td>
                                            </tr>
                                            <tr>
                                                <td><strong>Sistema:</strong></td>
                                                <td>RPA de Reparcelamento v2.0</td>
                                            </tr>
                                            <tr>
                                                <td><strong>Tipo de Evento:</strong></td>
                                                <td>{tipo_evento.value.title()}</td>
                                            </tr>
                                        </table>
                                    </div>
                                </td>
                            </tr>

                            <!-- Rodapé -->
                            <tr>
                                <td style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e9ecef;">
                                    <p style="margin: 0; font-size: 12px; color: #6c757d;">
                                        Esta é uma notificação automática do Sistema RPA.<br>
                                        Para dúvidas ou suporte, entre em contato com a equipe de TI.
                                    </p>
                                </td>
                            </tr>

                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

    @staticmethod
    def template_rpa_concluido(nome_rpa: str, tempo_execucao: str, resultados: Dict[str, Any]) -> str:
        """Template para RPA concluído com sucesso"""
        conteudo = f"""
        <h2 style="color: #28a745; margin-bottom: 20px;">🎉 Execução Concluída com Sucesso!</h2>

        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #495057;">📋 Resumo da Execução</h3>
            <table width="100%" style="margin: 15px 0;">
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 10px 0; font-weight: bold; width: 30%;">RPA Executado:</td>
                    <td style="padding: 10px 0;">{nome_rpa}</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 10px 0; font-weight: bold;">Tempo de Execução:</td>
                    <td style="padding: 10px 0;">{tempo_execucao}</td>
                </tr>
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 10px 0; font-weight: bold;">Status:</td>
                    <td style="padding: 10px 0; color: #28a745; font-weight: bold;">✅ Sucesso</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #e7f3ff; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff;">
            <h4 style="margin-top: 0; color: #0056b3;">📊 Resultados Principais</h4>
            <ul style="margin: 10px 0; padding-left: 20px;">
        """

        for chave, valor in resultados.items():
            conteudo += f"<li><strong>{chave.replace('_', ' ').title()}:</strong> {valor}</li>"

        conteudo += """
            </ul>
        </div>

        <p style="margin-top: 25px; color: #6c757d; font-style: italic;">
            O sistema continuará monitorando as próximas execuções automaticamente.
        </p>
        """

        return GeradorTemplates.gerar_template_base(
            f"RPA {nome_rpa} - Execução Concluída",
            conteudo,
            TipoEvento.SUCESSO
        )

    @staticmethod
    def template_erro_rpa(nome_rpa: str, erro: str, detalhes: str) -> str:
        """Template para erro no RPA"""
        conteudo = f"""
        <h2 style="color: #dc3545; margin-bottom: 20px;">⚠️ Erro Detectado no Sistema</h2>

        <div style="background-color: #f8d7da; padding: 20px; border-radius: 8px; border-left: 4px solid #dc3545; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #721c24;">🚨 Detalhes do Erro</h3>
            <table width="100%" style="margin: 15px 0;">
                <tr style="border-bottom: 1px solid #f5c6cb;">
                    <td style="padding: 10px 0; font-weight: bold; width: 30%;">RPA Afetado:</td>
                    <td style="padding: 10px 0;">{nome_rpa}</td>
                </tr>
                <tr style="border-bottom: 1px solid #f5c6cb;">
                    <td style="padding: 10px 0; font-weight: bold;">Tipo de Erro:</td>
                    <td style="padding: 10px 0; color: #dc3545; font-weight: bold;">{erro}</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107;">
            <h4 style="margin-top: 0; color: #856404;">📝 Detalhes Técnicos</h4>
            <div style="background-color: #ffffff; padding: 15px; border-radius: 4px; font-family: monospace; font-size: 14px; color: #495057; white-space: pre-wrap;">{detalhes}</div>
        </div>

        <div style="background-color: #d1ecf1; padding: 20px; border-radius: 8px; margin-top: 20px;">
            <h4 style="margin-top: 0; color: #0c5460;">🔧 Próximos Passos</h4>
            <ol style="margin: 10px 0; padding-left: 20px; color: #495057;">
                <li>Verificar os logs detalhados no sistema</li>
                <li>Analisar as condições que causaram o erro</li>
                <li>Aplicar correções necessárias</li>
                <li>Executar teste para validar a correção</li>
            </ol>
        </div>
        """

        return GeradorTemplates.gerar_template_base(
            f"ERRO - RPA {nome_rpa}",
            conteudo,
            TipoEvento.ERRO
        )

class SistemaNotificacoes:
    """Sistema principal de notificações"""

    def __init__(self):
        self.notificador = NotificadorEmail()
        self.configuracoes = self._carregar_configuracoes()

    def _carregar_configuracoes(self) -> Dict[str, Any]:
        """Carrega configurações de notificação"""
        config_padrao = {
            "habilitado": True,
            "destinatarios": [
                os.getenv('EMAIL_ADMIN', 'admin@empresa.com')
            ],
            "eventos": {
                "rpa_concluido": True,
                "rpa_erro": True,
                "workflow_concluido": True,
                "indices_atualizados": False,
                "contratos_identificados": True
            }
        }

        try:
            if os.path.exists('config/notificacoes.json'):
                with open('config/notificacoes.json', 'r', encoding='utf-8') as f:
                    config_arquivo = json.load(f)
                    config_padrao.update(config_arquivo)
        except Exception as e:
            logger.warning(f"Erro ao carregar configurações: {e}")

        return config_padrao

    def salvar_configuracoes(self):
        """Salva configurações"""
        try:
            os.makedirs('config', exist_ok=True)
            with open('config/notificacoes.json', 'w', encoding='utf-8') as f:
                json.dump(self.configuracoes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")

    def notificar_rpa_concluido(self, nome_rpa: str, tempo_execucao: str, resultados: Dict[str, Any]) -> bool:
        """Notifica conclusão bem-sucedida de RPA"""
        if not self.configuracoes.get('eventos', {}).get('rpa_concluido', True):
            return True

        html = GeradorTemplates.template_rpa_concluido(nome_rpa, tempo_execucao, resultados)
        sucesso = self._enviar_para_todos(f"✅ RPA {nome_rpa} - Execução Concluída", html)

        if sucesso:
            logger_manager.info(f"📢 Notificação de sucesso enviada: {nome_rpa}")
            logger_manager.debug("Detalhes da notificação de sucesso", {
                "nome_rpa": nome_rpa,
                "tempo_execucao": tempo_execucao,
                "resultados": resultados
            })
        else:
            logger_manager.error(f"❌ Erro ao enviar notificação de sucesso: {str(e)}")

        return sucesso

    def notificar_erro_rpa(self, nome_rpa: str, erro: str, detalhes: str) -> bool:
        """Notifica erro no RPA"""
        if not self.configuracoes.get('eventos', {}).get('rpa_erro', True):
            return True

        html = GeradorTemplates.template_erro_rpa(nome_rpa, erro, detalhes)
        sucesso = self._enviar_para_todos(f"🚨 ERRO - RPA {nome_rpa}", html)

        if sucesso:
            logger_manager.warning(f"⚠️ Notificação de erro enviada: {nome_rpa} - {erro}")
            logger_manager.debug("Detalhes da notificação de erro", {
                "nome_rpa": nome_rpa,
                "erro": erro,
                "detalhes": detalhes
            })
        else:
            logger_manager.error(f"❌ Erro ao enviar notificação de erro: {str(e)}")

        return sucesso

    def notificar_workflow_concluido(self, rpas_executados: List[str], contratos_processados: int, tempo_total: str) -> bool:
        """Notifica conclusão de workflow completo"""
        if not self.configuracoes.get('eventos', {}).get('workflow_concluido', True):
            return True

        conteudo = f"""
        <h2 style="color: #17a2b8; margin-bottom: 20px;">🔄 Workflow de Reparcelamento Concluído</h2>

        <div style="background-color: #e7f3ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #0056b3;">📊 Resumo da Execução</h3>
            <table width="100%" style="margin: 15px 0;">
                <tr style="border-bottom: 1px solid #b8daff;">
                    <td style="padding: 10px 0; font-weight: bold; width: 30%;">RPAs Executados:</td>
                    <td style="padding: 10px 0;">{', '.join(rpas_executados)}</td>
                </tr>
                <tr style="border-bottom: 1px solid #b8daff;">
                    <td style="padding: 10px 0; font-weight: bold;">Contratos Processados:</td>
                    <td style="padding: 10px 0; color: #17a2b8; font-weight: bold;">{contratos_processados}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; font-weight: bold;">Tempo Total:</td>
                    <td style="padding: 10px 0;">{tempo_total}</td>
                </tr>
            </table>
        </div>
        """

        html = GeradorTemplates.gerar_template_base(
            "Workflow de Reparcelamento Concluído",
            conteudo,
            TipoEvento.CONCLUIDO
        )

        return self._enviar_para_todos("🔄 Workflow de Reparcelamento Concluído", html)

    def _enviar_para_todos(self, assunto: str, html: str) -> bool:
        """Envia notificação para todos os destinatários configurados"""
        if not self.configuracoes.get('habilitado', True):
            return True

        destinatarios = self.configuracoes.get('destinatarios', [])
        if not destinatarios:
            logger.warning("Nenhum destinatário configurado")
            return False

        sucesso_geral = True
        for destinatario in destinatarios:
            sucesso = self.notificador.enviar_email(destinatario, assunto, html)
            sucesso_geral = sucesso_geral and sucesso

        return sucesso_geral

    def testar_configuracao(self) -> bool:
        """Testa configuração de notificações"""
        conteudo = """
        <h2 style="color: #007bff;">🧪 Teste de Configuração</h2>
        <p>Este é um teste para verificar se as notificações estão funcionando corretamente.</p>
        <div style="background-color: #d1ecf1; padding: 15px; border-radius: 8px;">
            <strong>Status:</strong> Sistema de notificações operacional ✅
        </div>
        """

        html = GeradorTemplates.gerar_template_base(
            "Teste de Notificações - Sistema RPA",
            conteudo,
            TipoEvento.INICIO
        )

        return self._enviar_para_todos("🧪 Teste - Sistema de Notificações", html)

# Instância global
notificacoes = SistemaNotificacoes()

# Funções utilitárias
def notificar_sucesso(nome_rpa: str, tempo_execucao: str, resultados: Dict[str, Any]) -> bool:
    """Notifica sucesso de RPA"""
    return notificacoes.notificar_rpa_concluido(nome_rpa, tempo_execucao, resultados)

def notificar_erro(nome_rpa: str, erro: str, detalhes: str) -> bool:
    """Notifica erro de RPA"""
    return notificacoes.notificar_erro_rpa(nome_rpa, erro, detalhes)

def notificar_workflow(rpas: List[str], contratos: int, tempo: str) -> bool:
    """Notifica conclusão de workflow"""
    return notificacoes.notificar_workflow_concluido(rpas, contratos, tempo)

def testar_notificacoes() -> bool:
    """Testa sistema de notificações"""
    return notificacoes.testar_configuracao()
```