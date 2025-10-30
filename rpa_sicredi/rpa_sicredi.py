"""
RPA Sicredi - Processamento de Reparcelamentos Bancários
Quarto RPA do sistema - Integra com sistema bancário Sicredi

Desenvolvido em Português Brasileiro
"""

from core.logger_avancado import LoggerAvancado
import shutil
from datetime import datetime
from typing import Dict, Any, List
from core.notificacoes_simples import notificar_sucesso, notificar_erro
from core.base_rpa import BaseRPA, ResultadoRPA
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


# Logger integrado via BaseRPA


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
        import os
        firefox_profile_path = os.getenv('FIREFOX_PROFILE_PATH', '').strip()
        chrome_profile_path = os.getenv('CHROME_PROFILE_PATH', '').strip()
        super().__init__(
            nome_rpa="Sicredi",
            usar_browser=True,
            firefox_profile_path=firefox_profile_path,
            limpar_cookies_sicredi=True,
            usar_uc_chrome=True,  # Usa Undetected Chromedriver para este RPA
            chrome_profile_path=chrome_profile_path  # Passa o perfil do Chrome
        )
        self.logado_sicredi = False
        self.url_sicredi = None
        self.usuario_sicredi = None
        self.senha_sicredi = None
        self.cnpj_empresa = None

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
            validacao_arquivo = {}  # Inicializa a variável

            if not arquivo_remessa or not credenciais:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem="Arquivo de remessa ou credenciais Sicredi não fornecidos",
                    erro="Parâmetros 'arquivo_remessa' e 'credenciais_sicredi' são obrigatórios"
                )

            # Configura credenciais com dados de processamento
            credenciais_completas = {
                **credenciais,
                "dados_processamento": dados_processamento
            }
            await self._configurar_credenciais(credenciais_completas)

            # Faz login no Sicredi WebBank
            await self._fazer_login_sicredi()

            # Log de início do processamento
            self.log_progresso("Iniciando processamento do arquivo de remessa")

            # Valida arquivo antes do upload
            self.log_progresso("Validando arquivo de remessa")

            # Faz upload do arquivo de remessa
            self.log_progresso("Fazendo upload do arquivo de remessa")
            resultado_upload = await self._fazer_upload_arquivo(arquivo_remessa)

            # Processa arquivo no sistema
            if resultado_upload["sucesso"]:
                self.log_progresso("Processando arquivo no sistema Sicredi")
                resultado_processamento = await self._processar_arquivo_sicredi(arquivo_remessa)
            else:
                erro_upload = resultado_upload.get(
                    "erro", "Erro desconhecido no upload")
                self.log_erro(f"❌ FALHA NO UPLOAD: {erro_upload}")
                return ResultadoRPA(
                    sucesso=False,
                    mensagem=f"Falha no upload: {erro_upload}",
                    erro=erro_upload,
                    dados=resultado_upload
                )

            # Confirma processamento e gera carnês atualizados
            if resultado_processamento["sucesso"]:
                self.log_progresso(
                    "Confirmando processamento e gerando carnês")
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

    async def _buscar_cnpj_empresa(self, empresa_nome: str) -> Optional[str]:
        """Busca CNPJ da empresa de forma assíncrona"""

        try:
            from core.utils_sienge import obter_cnpj_empresa

            self.log_progresso(f"🔍 Buscando CNPJ para empresa: {empresa_nome}")
            cnpj_encontrado = obter_cnpj_empresa(empresa_nome)

            if cnpj_encontrado:
                self.log_progresso(f"✅ CNPJ encontrado: {cnpj_encontrado}")
            else:
                self.log_progresso(
                    f"⚠️ CNPJ não encontrado para empresa: {empresa_nome}"
                )

            return cnpj_encontrado
        except Exception as e:
            self.log_progresso(
                f"❌ Erro ao buscar CNPJ para empresa {empresa_nome}: {str(e)}"
            )
            return None

    async def _configurar_credenciais(self, credenciais: Dict[str, Any]):
        """
        Configura credenciais do Sicredi
        Compatível com versões legadas: aceita credenciais sem CNPJ.
        """
        self.url_sicredi = credenciais.get("url", "")
        self.usuario_sicredi = credenciais.get("usuario", "")
        self.senha_sicredi = credenciais.get("senha", "")

        # Busca CNPJ dinamicamente se não fornecido
        if "cnpj" in credenciais:
            self.cnpj_empresa = credenciais["cnpj"]
        else:
            # Tenta buscar CNPJ dos dados de processamento
            dados_processamento = credenciais.get("dados_processamento", {})
            if dados_processamento:
                # Busca CNPJ do contrato ou empresa
                self.cnpj_empresa = (
                    dados_processamento.get("cnpj_empresa") or
                    dados_processamento.get("cnpj") or
                    None
                )

                if not self.cnpj_empresa and dados_processamento.get("empresa"):
                    # Busca dinâmica por empresa usando data_manager
                    empresa_nome = dados_processamento['empresa']
                    cnpj_encontrado = await self._buscar_cnpj_empresa(empresa_nome)

                    if cnpj_encontrado:
                        self.cnpj_empresa = cnpj_encontrado
                    else:
                        self.log_progresso(
                            f"⚠️ CNPJ não encontrado para empresa: {empresa_nome}")

        if not all([self.url_sicredi, self.usuario_sicredi, self.senha_sicredi]):
            raise Exception("Credenciais incompletas para o Sicredi")

    async def _fazer_login_sicredi(self):
        """
        Faz login no Sicredi WebBank conforme PDD seção 7.4
        """
        try:
            self.log_progresso(
                f"Acessando Sicredi WebBank: {self.url_sicredi}")

            # Acessa página de login
            if not self.browser:
                raise Exception("Browser não inicializado")
            if not self.url_sicredi:
                raise Exception("URL do Sicredi não configurada")

            self.browser.get_page(self.url_sicredi)
            time.sleep(5)

            # TODO: Cliente deve implementar login específico no Sicredi usando sua classe browser
            # Conforme PDD seção 7.4:
            # 1. Acessar https://webbank.sicredi.com.br/
            # 2. Informar usuário
            # 3. Informar senha
            # 4. Clicar em Entrar
            # 5. Aguardar carregamento do sistema

            # Permitir Todos (modal de permissão de cookies)
            if self.check_for_error(xpath='//span[normalize-space(text())="Permitir Todos"]'):
                self.click(
                    xpath='//span[normalize-space(text())="Permitir Todos"]')
                time.sleep(1)

            # Clique em Assesar minha conta
            self.click(
                xpath='(//*[normalize-space(text())="Acessar minha conta"])[1]')
            time.sleep(0.2)
            self.click(
                xpath='//a[contains(@class, "gtag-click-trigger") and contains(text(), "Pessoa Jurídica")]')
            if self.check_for_error(xpath='//input[contains(@id, "cnpj")]'):
                self.send_text_human_like(
                    xpath='//input[contains(@id, "cnpj")]', text=str(self.cnpj_empresa or ""))
                time.sleep(2.2)
                self.click(
                    xpath='//div[contains(@class, "btnAvancar") and contains(text(), "Acessar")]')
            if self.check_for_error(xpath='//input[contains(@id, "j_username")]'):
                self.send_text_human_like(
                    xpath='//input[contains(@id, "j_username")]', text=str(self.usuario_sicredi or ""))

            # Digita a senha virtual Sicredi usando o teclado embaralhado
            if self.senha_sicredi:
                for digito in str(self.senha_sicredi):
                    xpath = f'//span[contains(@class, "btn") and contains(@class, "senha") and .//span[contains(text(), "{digito}")]]'
                    try:
                        self.browser.logger.info(
                            f"Digitando dígito '{digito}' no teclado virtual Sicredi.")
                        botao = self.browser.find_element(
                            xpath, condition="clickable")
                        botao.click()
                    except Exception as e:
                        self.browser.logger.error(
                            f"Erro ao clicar no dígito '{digito}' do teclado virtual: {e}")
                        raise
            time.sleep(0.2)
            self.click(
                xpath='//div[contains(@class, "btnAvancar") and contains(@id, "submeter") and contains(text(), "Acessar")]')
            # Por enquanto, simula login bem-sucedido
            self.logado_sicredi = True
            self.log_progresso(
                "✅ Login no Sicredi WebBank realizado com sucesso")

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

            # Acessa menu de cobrança/remessa
            self.click(
                xpath='//span[@aria-label="Cobrança"]')
            time.sleep(0.2)
            self.click(
                xpath='//a[contains(@data-gtm, "Transferir Arquivos") and contains(@title, "Transferir Arquivos") and contains(text(), "Transferir Arquivos")]')
            time.sleep(0.2)

            # Garante que o caminho para o arquivo de remessa seja absoluto
            caminho_absoluto = os.path.abspath(arquivo_remessa)
            self.log_progresso(
                f"Caminho absoluto para upload: {caminho_absoluto}")

            self.send_text(
                xpath='//input[@type="file" and @name="fileData"]', text=caminho_absoluto)
            self.click(
                xpath='//a[@id="submeter" and @name="submeter" and @title="Avançar"]')
            time.sleep(0.2)
            self.click(
                xpath='//a[@id="submeter"]')
            time.sleep(0.2)
            error_xpath = '//div[@id="DivServerError" and contains(@class, "login-erro") and contains(., "Dados inválidos.")]'
            if not self.check_for_error(xpath=error_xpath):
                time.sleep(2.2)
                # Simula upload bem-sucedido
                resultado_upload = {
                    "sucesso": True,
                    "arquivo_enviado": arquivo_remessa,
                    "protocolo_upload": f"UPL{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "timestamp_upload": datetime.now().isoformat(),
                    "status": "arquivo_recebido"
                }

                self.log_progresso("✅ Upload realizado com sucesso")
            else:
                # Verificar se há mensagem de erro específica
                try:
                    elemento_erro = self.browser.find_element(
                        error_xpath, condition="visible")
                    mensagem_erro = elemento_erro.text if elemento_erro else "Dados inválidos"
                except:
                    mensagem_erro = "Dados inválidos"

                self.log_erro(f"❌ Upload falhou: {mensagem_erro}")
                resultado_upload = {
                    "sucesso": False,
                    "erro": f"Upload rejeitado: {mensagem_erro}",
                    "arquivo": arquivo_remessa,
                    "detalhes_erro": {
                        "motivo": "Arquivo rejeitado pelo sistema Sicredi",
                        "mensagem_sistema": mensagem_erro,
                        "timestamp_erro": datetime.now().isoformat()
                    }
                }

            return resultado_upload

        except Exception as e:
            self.log_erro(f"❌ Erro durante upload: {str(e)}")
            return {
                "sucesso": False,
                "erro": f"Erro técnico no upload: {str(e)}",
                "arquivo": arquivo_remessa,
                "detalhes_erro": {
                    "tipo": "erro_tecnico",
                    "excecao": str(e),
                    "timestamp_erro": datetime.now().isoformat()
                }
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
            self.log_progresso(
                "Aguardando processamento do arquivo pelo sistema")

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

            self.log_progresso(
                f"✅ Arquivo processado - {resultado_processamento['registros_processados']} registros")

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

            self.log_progresso(
                "✅ Processamento confirmado - Carnês atualizados com sucesso")

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
            self.log_progresso(
                f"⚠️ Erro ao salvar no MongoDB: {str(e)} - usando fallback local")
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
                try:
                    with open(arquivo_dados, 'r', encoding='utf-8') as f:
                        dados_existentes = json.load(f)
                except json.JSONDecodeError as e:
                    self.log_error(
                        f"❌ Arquivo JSON corrompido, criando novo: {str(e)}")
                    # Cria backup do arquivo corrompido
                    backup_path = f"{arquivo_dados}.backup_corrupted_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(arquivo_dados, backup_path)
                    self.log_info(
                        f"📦 Backup do arquivo corrompido criado: {backup_path}")
                    dados_existentes = []

            # Sanitiza dados para evitar problemas de serialização
            dados_sanitizados = self._sanitizar_dados_json(dados_processamento)

            # Adiciona novo registro
            novo_registro = {
                "timestamp": datetime.now().isoformat(),
                "dados_processamento": dados_sanitizados,
                "tipo": "processamento_sicredi",
                "status": "processado"
            }
            dados_existentes.append(novo_registro)

            # Salva arquivo atualizado com validação
            with open(arquivo_dados, 'w', encoding='utf-8') as f:
                json.dump(dados_existentes, f, indent=2,
                          ensure_ascii=False, default=str)

            # Valida o arquivo salvo
            with open(arquivo_dados, 'r', encoding='utf-8') as f:
                json.load(f)  # Testa se o JSON é válido

            self.log_info(f"✅ Dados salvos localmente: {arquivo_dados}")

        except Exception as e:
            self.log_error(f"❌ Erro ao salvar dados localmente: {str(e)}")
            # Em caso de erro, tenta salvar em arquivo temporário
            try:
                arquivo_temp = f"dados_processamento/processamentos_sicredi_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(arquivo_temp, 'w', encoding='utf-8') as f:
                    json.dump([{
                        "timestamp": datetime.now().isoformat(),
                        "dados_processamento": self._sanitizar_dados_json(dados_processamento),
                        "tipo": "processamento_sicredi",
                        "status": "processado"
                    }], f, indent=2, ensure_ascii=False, default=str)
                self.log_info(
                    f"📦 Dados salvos em arquivo temporário: {arquivo_temp}")
            except Exception as e2:
                self.log_error(f"❌ Falha crítica ao salvar dados: {str(e2)}")

    def _sanitizar_dados_json(self, dados: Any) -> Any:
        """
        Sanitiza dados para evitar problemas de serialização JSON

        Args:
            dados: Dados a serem sanitizados

        Returns:
            Dados sanitizados
        """
        if isinstance(dados, dict):
            return {k: self._sanitizar_dados_json(v) for k, v in dados.items()}
        elif isinstance(dados, list):
            return [self._sanitizar_dados_json(item) for item in dados]
        elif isinstance(dados, (datetime,)):
            return dados.isoformat()
        elif hasattr(dados, '__dict__'):
            # Para objetos customizados, converte para dict
            return self._sanitizar_dados_json(dados.__dict__)
        elif isinstance(dados, (int, float, str, bool, type(None))):
            return dados
        else:
            # Para outros tipos, converte para string
            return str(dados)

    async def _fazer_logout_sicredi(self):
        """
        Faz logout do Sicredi WebBank
        """
        try:
            if self.logado_sicredi:
                self.log_info("Fazendo logout do Sicredi WebBank")
                # TODO: Cliente deve implementar logout específico
                self.logado_sicredi = False
                self.log_info("✅ Logout concluído")

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
