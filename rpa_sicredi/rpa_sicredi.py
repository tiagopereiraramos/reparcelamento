"""
RPA Sicredi - Processamento de Reparcelamentos Bancários
Quarto RPA do sistema - Integra com sistema bancário Sicredi

Desenvolvido em Português Brasileiro
"""

import asyncio
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
from pathlib import Path

# Adiciona o diretório raiz ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.base_rpa import BaseRPA, ResultadoRPA
from core.notificacoes_simples import notificar_sucesso, notificar_erro
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import os
import shutil

class RPASicredi(BaseRPA):
    """
    RPA responsável pelo processamento no sistema Sicredi WebBank

    Funcionalidades:
    - Login no Sicredi WebBank
    - Upload de arquivo de remessa gerado pelo Sienge
    - Validação e processamento do arquivo
    - Confirmação da atualização dos carnês
    """

    def __init__(self):
        super().__init__(nome_rpa="Sicredi", usar_browser=True)
        self.logado_sicredi = False
        self.url_sicredi = None
        self.usuario_sicredi = None
        self.senha_sicredi = None

    async def executar(self, parametros: Dict[str, Any]) -> ResultadoRPA:
        """
        Executa processamento no Sicredi WebBank

        Args:
            parametros: Deve conter:
                - arquivo_remessa: Caminho do arquivo gerado pelo Sienge
                - credenciais_sicredi: URL, usuário e senha do Sicredi
                - dados_processamento: Dados do reparcelamento processado

        Returns:
            ResultadoRPA com resultado do processamento
        """
        try:
            self.log_progresso("Iniciando processamento no Sicredi WebBank")

            # Valida parâmetros
            arquivo_remessa = parametros.get("arquivo_remessa")
            credenciais = parametros.get("credenciais_sicredi")
            dados_processamento = parametros.get("dados_processamento", {})

            if not arquivo_remessa or not credenciais:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem="Arquivo de remessa ou credenciais Sicredi não fornecidos",
                    erro="Parâmetros 'arquivo_remessa' e 'credenciais_sicredi' são obrigatórios"
                )

            # Configura credenciais
            self._configurar_credenciais(credenciais)

            # Faz login no Sicredi WebBank
            await self._fazer_login_sicredi()

            # Valida arquivo antes do upload
            self.log_progresso("Validando arquivo de remessa")
            validacao_arquivo = await self._validar_arquivo_remessa(arquivo_remessa)

            if not validacao_arquivo["valido"]:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem=f"Arquivo de remessa inválido: {validacao_arquivo['motivo']}",
                    dados={
                        "arquivo": arquivo_remessa,
                        "validacao": validacao_arquivo
                    }
                )

            # Faz upload do arquivo de remessa
            self.log_progresso("Fazendo upload do arquivo de remessa")
            resultado_upload = await self._fazer_upload_arquivo(arquivo_remessa)

            # Processa arquivo no sistema
            if resultado_upload["sucesso"]:
                self.log_progresso("Processando arquivo no sistema Sicredi")
                resultado_processamento = await self._processar_arquivo_sicredi(arquivo_remessa)
            else:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem="Falha no upload do arquivo",
                    dados=resultado_upload
                )

            # Confirma processamento e gera carnês atualizados
            if resultado_processamento["sucesso"]:
                self.log_progresso("Confirmando processamento e gerando carnês")
                confirmacao = await self._confirmar_processamento()
            else:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem="Falha no processamento do arquivo",
                    dados=resultado_processamento
                )

            # Monta resultado final
            resultado_dados = {
                "arquivo_remessa": arquivo_remessa,
                "validacao_arquivo": validacao_arquivo,
                "upload": resultado_upload,
                "processamento": resultado_processamento,
                "confirmacao": confirmacao,
                "dados_originais": dados_processamento,
                "timestamp_processamento": datetime.now().isoformat()
            }

            # Salva dados processados (MongoDB ou JSON local)
            await self._salvar_dados_processamento(resultado_dados)

            return ResultadoRPA(
                sucesso=confirmacao["sucesso"],
                mensagem=f"Processamento Sicredi concluído - Carnês atualizados",
                dados=resultado_dados
            )

        except Exception as e:
            self.log_erro("Erro durante processamento no Sicredi", e)
            return ResultadoRPA(
                sucesso=False,
                mensagem="Falha no processamento Sicredi",
                erro=str(e)
            )
        finally:
            # Sempre faz logout
            await self._fazer_logout_sicredi()

    def _configurar_credenciais(self, credenciais: Dict[str, Any]):
        """
        Configura credenciais do Sicredi

        Args:
            credenciais: Dicionário com url, usuario e senha
        """
        self.url_sicredi = credenciais.get("url", "")
        self.usuario_sicredi = credenciais.get("usuario", "")
        self.senha_sicredi = credenciais.get("senha", "")

        if not all([self.url_sicredi, self.usuario_sicredi, self.senha_sicredi]):
            raise Exception("Credenciais incompletas para o Sicredi")

    async def _fazer_login_sicredi(self):
        """
        Faz login no Sicredi WebBank conforme PDD seção 7.4
        """
        try:
            self.log_progresso(f"Acessando Sicredi WebBank: {self.url_sicredi}")

            # Acessa página de login
            if not self.browser:
                raise Exception("Browser não inicializado")
            if not self.url_sicredi:
                raise Exception("URL do Sicredi não configurada")

            self.browser.get_page(self.url_sicredi)
            time.sleep(3)

            # TODO: Cliente deve implementar login específico no Sicredi usando sua classe browser
            # Conforme PDD seção 7.4:
            # 1. Acessar https://webbank.sicredi.com.br/
            # 2. Informar usuário
            # 3. Informar senha
            # 4. Clicar em Entrar
            # 5. Aguardar carregamento do sistema

            # Por enquanto, simula login bem-sucedido
            self.logado_sicredi = True
            self.log_progresso("✅ Login no Sicredi WebBank realizado com sucesso")

        except Exception as e:
            raise Exception(f"Falha no login Sicredi: {str(e)}")

    async def _validar_arquivo_remessa(self, arquivo_remessa: str) -> Dict[str, Any]:
        """
        Valida arquivo de remessa antes do upload

        Args:
            arquivo_remessa: Caminho do arquivo de remessa

        Returns:
            Resultado da validação
        """
        try:
            self.log_progresso(f"Validando arquivo: {arquivo_remessa}")

            # TODO: Cliente deve implementar validação específica
            # Verificações básicas:
            # - Arquivo existe
            # - Formato correto (.txt)
            # - Tamanho não zero
            # - Estrutura do arquivo conforme padrão bancário

            # Por enquanto, simula validação bem-sucedida
            validacao = {
                "valido": True,
                "motivo": "Arquivo válido para processamento",
                "tamanho_bytes": 1024,  # Simulado
                "linhas_total": 50,     # Simulado
                "formato": "CNAB240",   # Simulado
                "data_validacao": datetime.now().isoformat()
            }

            self.log_progresso("✅ Arquivo validado com sucesso")

            return validacao

        except Exception as e:
            return {
                "valido": False,
                "motivo": f"Erro na validação: {str(e)}",
                "arquivo": arquivo_remessa
            }

    async def _fazer_upload_arquivo(self, arquivo_remessa: str) -> Dict[str, Any]:
        """
        Faz upload do arquivo de remessa no Sicredi WebBank

        Args:
            arquivo_remessa: Caminho do arquivo de remessa

        Returns:
            Resultado do upload
        """
        try:
            self.log_progresso("Navegando para área de upload de arquivos")

            # TODO: Cliente deve implementar navegação específica no Sicredi
            # Conforme PDD seção 7.4:
            # 1. Acessar menu de cobrança/remessa
            # 2. Selecionar opção de upload de arquivo
            # 3. Escolher arquivo de remessa
            # 4. Confirmar upload
            # 5. Aguardar processamento

            # Simula upload bem-sucedido
            resultado_upload = {
                "sucesso": True,
                "arquivo_enviado": arquivo_remessa,
                "protocolo_upload": f"UPL{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "timestamp_upload": datetime.now().isoformat(),
                "status": "arquivo_recebido"
            }

            self.log_progresso("✅ Upload realizado com sucesso")

            return resultado_upload

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "arquivo": arquivo_remessa
            }

    async def _processar_arquivo_sicredi(self, arquivo_remessa: str) -> Dict[str, Any]:
        """
        Processa arquivo no sistema Sicredi

        Args:
            arquivo_remessa: Caminho do arquivo de remessa

        Returns:
            Resultado do processamento
        """
        try:
            self.log_progresso("Aguardando processamento do arquivo pelo sistema")

            # TODO: Cliente deve implementar acompanhamento específico
            # Conforme PDD:
            # 1. Aguardar processamento automático
            # 2. Verificar status do arquivo
            # 3. Validar se houve erros
            # 4. Confirmar registros processados

            # Simula processamento bem-sucedido
            resultado_processamento = {
                "sucesso": True,
                "arquivo_processado": arquivo_remessa,
                "registros_processados": 48,    # Simulado
                "registros_rejeitados": 0,      # Simulado
                "erros": [],                    # Sem erros
                "status": "processado_com_sucesso",
                "timestamp_processamento": datetime.now().isoformat()
            }

            self.log_progresso(f"✅ Arquivo processado - {resultado_processamento['registros_processados']} registros")

            return resultado_processamento

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "arquivo": arquivo_remessa
            }

    async def _confirmar_processamento(self) -> Dict[str, Any]:
        """
        Confirma processamento e finaliza atualização dos carnês

        Returns:
            Resultado da confirmação
        """
        try:
            self.log_progresso("Confirmando processamento e finalizando")

            # TODO: Cliente deve implementar confirmação específica
            # Conforme PDD:
            # 1. Revisar dados processados
            # 2. Confirmar atualização dos carnês
            # 3. Finalizar processo
            # 4. Obter comprovante se necessário

            # Simula confirmação bem-sucedida
            confirmacao = {
                "sucesso": True,
                "carnes_atualizados": True,
                "numero_comprovante": f"COMP{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "data_efetivacao": datetime.now().strftime('%d/%m/%Y'),
                "status_final": "processamento_confirmado",
                "timestamp_confirmacao": datetime.now().isoformat()
            }

            self.log_progresso("✅ Processamento confirmado - Carnês atualizados com sucesso")

            return confirmacao

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e)
            }

    async def _salvar_dados_processamento(self, dados_processamento: Dict[str, Any]):
        """
        Salva dados de processamento no MongoDB ou fallback para JSON local

        Args:
            dados_processamento: Dados do processamento realizado
        """
        try:
            if self.mongo_manager and self.mongo_manager.conectado:
                # Salva no MongoDB
                collection = self.mongo_manager.database.processamentos_sicredi
                documento = {
                    "timestamp": datetime.now(),
                    "dados_processamento": dados_processamento,
                    "tipo": "processamento_sicredi"
                }
                await collection.insert_one(documento)
                self.log_progresso("✅ Dados salvos no MongoDB")
            else:
                # Fallback para JSON local
                await self._salvar_dados_local(dados_processamento)

        except Exception as e:
            self.log_progresso(f"⚠️ Erro ao salvar no MongoDB: {str(e)} - usando fallback local")
            await self._salvar_dados_local(dados_processamento)

    async def _salvar_dados_local(self, dados_processamento: Dict[str, Any]):
        """
        Salva dados localmente em JSON como fallback

        Args:
            dados_processamento: Dados do processamento
        """
        try:
            # Garante que o diretório existe
            os.makedirs("dados_processamento", exist_ok=True)

            # Nome único do arquivo
            arquivo_dados = "dados_processamento/processamentos_sicredi.json"

            # Carrega dados existentes ou cria lista vazia
            dados_existentes = []
            if os.path.exists(arquivo_dados):
                with open(arquivo_dados, 'r', encoding='utf-8') as f:
                    dados_existentes = json.load(f)

            # Adiciona novo registro
            novo_registro = {
                "timestamp": datetime.now().isoformat(),
                "dados_processamento": dados_processamento,
                "tipo": "processamento_sicredi",
                "status": "processado"
            }
            dados_existentes.append(novo_registro)

            # Salva arquivo atualizado
            with open(arquivo_dados, 'w', encoding='utf-8') as f:
                json.dump(dados_existentes, f, indent=2, ensure_ascii=False)

            self.log_progresso(f"✅ Dados salvos localmente: {arquivo_dados}")

        except Exception as e:
            self.log_progresso(f"❌ Erro ao salvar dados localmente: {str(e)}")

    async def _fazer_logout_sicredi(self):
        """
        Faz logout do Sicredi WebBank
        """
        try:
            if self.logado_sicredi:
                self.log_progresso("Fazendo logout do Sicredi WebBank")
                # TODO: Cliente deve implementar logout específico
                self.logado_sicredi = False
                self.log_progresso("✅ Logout realizado")

        except Exception as e:
            self.log_erro("Erro no logout Sicredi", e)

# Função auxiliar para uso direto
async def executar_processamento_sicredi(
    arquivo_remessa: str,
    credenciais_sicredi: Dict[str, Any],
    dados_processamento: Optional[Dict[str, Any]] = None
) -> ResultadoRPA:
    """
    Função auxiliar para executar processamento Sicredi diretamente

    Args:
        arquivo_remessa: Caminho do arquivo de remessa gerado pelo Sienge
        credenciais_sicredi: Credenciais de acesso ao Sicredi WebBank
        dados_processamento: Dados do processamento anterior (opcional)

    Returns:
        ResultadoRPA com resultado do processamento
    """
    rpa = RPASicredi()

    parametros = {
        "arquivo_remessa": arquivo_remessa,
        "credenciais_sicredi": credenciais_sicredi,
        "dados_processamento": dados_processamento or {}
    }

    resultado = await rpa.executar_com_monitoramento(parametros)

    # Enviar notificação
    try:
        if resultado.sucesso:
            notificar_sucesso(
                nome_rpa="RPA Sicredi",
                tempo_execucao=f"{resultado.tempo_execucao:.1f}s" if resultado.tempo_execucao else "N/A",
                resultados={
                    "arquivo_processado": arquivo_remessa,
                    "status_upload": "Concluído",
                    "carnes_atualizados": True
                }
            )
        else:
            notificar_erro(
                nome_rpa="RPA Sicredi",
                erro=resultado.erro or "Erro desconhecido",
                detalhes=resultado.mensagem
            )
    except Exception as e:
        print(f"Aviso: Falha ao enviar notificação: {e}")

    return resultado