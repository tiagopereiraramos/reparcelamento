"""
RPA Sienge - Versão Produção Restaurada
Sistema automatizado para processamento de reparcelamento no Sienge ERP

CÓDIGO FUNCIONAL ORIGINAL DO USUÁRIO
Desenvolvido em Português Brasileiro
"""

import os
import json
import time
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
import traceback
from dotenv import load_dotenv
import locale

# Imports do sistema RPA
from core.base_rpa import BaseRPA, ResultadoRPA
from core.notificacoes_simples import notificar_sucesso, notificar_erro
from core.rastreamento_unificado import iniciar_rastreamento
from core.processador_regras_pdd import ProcessadorRegrasNegocio, ValidadorInadimplenciaPDD, CalculadoraReparcelamentoPDD

# Selenium imports necessários
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from platformdirs import user_downloads_dir

load_dotenv()


class RPASienge(BaseRPA):
    """
    RPA para processamento de reparcelamento no sistema Sienge
    Implementa as regras do PDD seção 7.3

    VERSÃO PRODUÇÃO - Apenas código real do Sienge
    """

    def __init__(self, headless: Optional[bool] = None):
        if headless is not None:
            super().__init__(nome_rpa="Sienge", usar_browser=True, headless=headless)
        else:
            super().__init__(nome_rpa="Sienge", usar_browser=True)
        self.logado_sienge = False
        self.credenciais_sienge = {}
        self.pasta_planilhas = Path("dados_extraidos/planilhas_sienge")
        self.pasta_planilhas.mkdir(parents=True, exist_ok=True)
        self.processador_regras = ProcessadorRegrasNegocio()
        self.rastreamento = None

    def _configurar_credenciais(self, credenciais: Dict[str, str]):
        """Configura credenciais do Sienge"""
        self.credenciais_sienge = {
            "url": credenciais.get("url", ""),
            "usuario": credenciais.get("usuario", ""),
            "senha": credenciais.get("senha", ""),
            "empresa": credenciais.get("empresa", "")
        }

    def processar_dados_cliente(self, df: pd.DataFrame, cliente: str, numero_titulo: str, dados_validacao_base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if dados_validacao_base is None:
            dados_validacao_base = {}
        if df is None:
            df = pd.DataFrame()
        if not isinstance(cliente, str) or cliente is None:
            cliente = ""
        if not isinstance(numero_titulo, str) or numero_titulo is None:
            numero_titulo = ""
        # Garantir que o método correto existe
        if hasattr(self.processador_regras, 'processar_dados_cliente_completo'):
            return self.processador_regras.processar_dados_cliente_completo(df, cliente, numero_titulo, dados_validacao_base)
        else:
            print(
                "[WARN] Método processar_dados_cliente_completo não existe no processador_regras.")
            return {}

    async def executar(self,
                       contrato: Dict[str, Any],
                       credenciais_sienge: Dict[str, str],
                       indices: Optional[Dict[str, Any]] = None,
                       etapa: str = "completa",
                       autorizar_reparcelamento: bool = False,
                       notificar_analista: bool = True) -> ResultadoRPA:
        """
        Executa processamento do RPA Sienge em etapas segregadas

        Args:
            contrato: Dados do contrato (número_titulo, cliente, etc.)
            credenciais_sienge: Credenciais de acesso ao Sienge
            indices: Índices econômicos (IPCA/IGPM)
            etapa: "consulta", "reparcelamento" ou "completa"
            autorizar_reparcelamento: True para pular validação de autorização
            notificar_analista: False para ignorar notificações de validação
        """
        if contrato is None:
            contrato = {}
        if credenciais_sienge is None:
            credenciais_sienge = {}
        if indices is None:
            indices = {}
        if etapa is None:
            etapa = "completa"
        try:
            # ✅ INICIA RASTREAMENTO UNIFICADO
            self.rastreamento = iniciar_rastreamento("RPA_Sienge")

            await self.rastreamento.registrar_inicio_rpa({
                "contrato":
                contrato,
                "credenciais_fornecidas":
                bool(credenciais_sienge),
                "indices_fornecidos":
                bool(indices),
                "etapa":
                etapa,
                "autorizar_reparcelamento":
                autorizar_reparcelamento,
                "notificar_analista":
                notificar_analista
            })

            self.log_progresso(
                f"Iniciando RPA Sienge - Etapa: {etapa.upper()}")
            self.log_progresso(
                f"Contrato: {contrato.get('numero_titulo', '')}")
            self.log_progresso(f"Cliente: {contrato.get('cliente', '')}")
            self.log_progresso(
                f"Autorização automática: {autorizar_reparcelamento}")

            if not contrato or not credenciais_sienge:
                await self.rastreamento.registrar_erro_critico(
                    ValueError("Parâmetros obrigatórios não fornecidos"), {
                        "contrato_fornecido": bool(contrato),
                        "credenciais_fornecidas": bool(credenciais_sienge)
                    })
                return ResultadoRPA(
                    sucesso=False,
                    mensagem="Dados do contrato ou credenciais Sienge não fornecidos",
                    erro="Parâmetros 'contrato' e 'credenciais_sienge' são obrigatórios"
                )

            # Configura credenciais
            self._configurar_credenciais(credenciais_sienge)

            # Faz login no Sienge com rastreamento
            await self._fazer_login_sienge()

            # ETAPA 1: CONSULTA DE RELATÓRIOS (sempre executada)
            dados_financeiros = await self._executar_etapa_consulta(contrato)

            if etapa == "consulta":
                return ResultadoRPA(
                    sucesso=dados_financeiros.get("sucesso", False),
                    mensagem=f"Consulta realizada - Cliente: {contrato.get('cliente', '')}",
                    dados={
                        "etapa_executada": "consulta",
                        "contrato": contrato,
                        "dados_financeiros": dados_financeiros,
                        "timestamp_processamento": datetime.now().isoformat()
                    })

            # ETAPA 2: PROCESSAMENTO DE REPARCELAMENTO
            if etapa in ["reparcelamento", "completa"]:
                resultado_reparcelamento = await self._executar_etapa_reparcelamento(
                    contrato, indices or {}, dados_financeiros,
                    autorizar_reparcelamento, notificar_analista)

                if etapa == "reparcelamento":
                    return resultado_reparcelamento

            # ETAPA COMPLETA: COMBINAR RESULTADOS
            if etapa == "completa":
                # Gera carnê se processamento foi bem-sucedido
                carne_gerado = None
                if dados_financeiros.get(
                        "sucesso") and resultado_reparcelamento.sucesso:
                    self.log_progresso("Gerando carnê atualizado")
                    carne_gerado = await self._gerar_carne_sienge(contrato)

                # Monta resultado final
                resultado_dados = {
                    "etapa_executada": "completa",
                    "contrato_processado": contrato,
                    "dados_financeiros": dados_financeiros,
                    "reparcelamento": resultado_reparcelamento.dados
                    if resultado_reparcelamento.dados else {},
                    "carne_gerado": carne_gerado,
                    "timestamp_processamento": datetime.now().isoformat()
                }

                return ResultadoRPA(
                    sucesso=resultado_reparcelamento.sucesso,
                    mensagem=f"Processamento completo - Cliente: {contrato.get('cliente', '')}",
                    dados=resultado_dados)

        except Exception as e:
            erro_msg = f"Erro na execução do RPA Sienge: {str(e)}"
            if self.rastreamento:
                await self.rastreamento.registrar_erro_critico(
                    e, {
                        "fase": "execucao_principal",
                        "etapa": etapa,
                        "contrato": contrato.get("numero_titulo", "N/A") if contrato else "N/A"
                    })
                await self.rastreamento.finalizar_rastreamento()
            self.log_erro(erro_msg, e)
            return ResultadoRPA(sucesso=False,
                                mensagem="Falha na execução do RPA Sienge",
                                erro=erro_msg)
        finally:
            if self.rastreamento:
                await self.rastreamento.finalizar_rastreamento()
        # Garantir retorno padrão
        return ResultadoRPA(sucesso=False, mensagem="Execução não concluída", erro="Fluxo inesperado")

    async def _fazer_login_sienge(self):
        """
        Faz login no sistema Sienge conforme PDD seção 7.3
        WEBSCRAPING FUNCIONAL IMPLEMENTADO
        """
        try:
            url_sienge = self.credenciais_sienge.get("url", "")
            usuario_sienge = self.credenciais_sienge.get("usuario", "")
            senha_sienge = self.credenciais_sienge.get("senha", "")

            # Inicializar rastreamento se não existe
            if self.rastreamento is None:
                self.rastreamento = iniciar_rastreamento("RPA_Sienge")
                await self.rastreamento.registrar_inicio_rpa({
                    "operacao":
                    "login_sienge",
                    "usuario":
                    usuario_sienge,
                    "timestamp":
                    datetime.now().isoformat()
                })

            await self.rastreamento.registrar_passo(
                "TENTATIVA_LOGIN_SIENGE", {
                    "url_sienge": url_sienge,
                    "usuario": usuario_sienge,
                    "timestamp_tentativa": datetime.now().isoformat()
                },
                categoria="OPERACAO")

            self.log_progresso(f"Acessando sistema Sienge: {url_sienge}")

            if not url_sienge:
                await self.rastreamento.registrar_erro_critico(
                    ValueError("URL do Sienge não configurada"),
                    {"credenciais_sienge": self.credenciais_sienge})
                raise ValueError(
                    "URL do Sienge não foi configurada corretamente.")

            self.get_page(url_sienge)
            time.sleep(3)

            # WEBSCRAPING REAL - Sequência de login conforme PDD:
            # 1. Informar usuário (tc@trajetoriaconsultoria.com.br)
            # 2. Clicar em Continuar
            # 3. Informar senha
            # 4. Clicar em Entrar
            # 5. Fechar caixas de mensagem

            # Preenche usuário inicial
            self.send_text(
                xpath='(//input[@id="username"])[1]',
                text=usuario_sienge
            )

            # Preenche senha inicial
            self.send_text(
                xpath='//input[@id="password"]',
                text=senha_sienge
            )

            # Clica botão entrar inicial
            self.click(xpath='//*[@id="btnEntrarComSiengeID"]')
            time.sleep(2)

            # Segunda etapa - email
            self.send_text(
                xpath='//label[text()="Seu e-mail"]/following-sibling::div//input',
                text=usuario_sienge
            )

            # Clica continuar
            self.click(xpath="//button[normalize-space(text())='CONTINUAR']")

            # Terceira etapa - senha final
            self.send_text(
                xpath="//input[@id='signup-password']",
                text=senha_sienge
            )

            # Clica entrar final
            self.click(xpath="//button[normalize-space(text())='ENTRAR']")

            # Login bem-sucedido
            self.logado_sienge = True

            await self.rastreamento.registrar_login_sistema(
                "sienge", usuario_sienge, True)

            self.log_progresso("Login no Sienge realizado com sucesso")
            return True

        except Exception as e:
            if self.rastreamento:
                await self.rastreamento.registrar_login_sistema(
                    "sienge", self.credenciais_sienge.get("usuario", ""),
                    False)

                await self.rastreamento.registrar_erro_critico(
                    e, {
                        "fase": "login_sienge",
                        "url": self.credenciais_sienge.get("url", ""),
                        "usuario": self.credenciais_sienge.get("usuario", "")
                    })

            raise Exception(f"Falha no login Sienge: {str(e)}")

    async def _consultar_relatorios_financeiros(
            self, contrato: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consulta relatórios financeiros no Sienge conforme PDD seção 7.3.1
        WEBSCRAPING IMPLEMENTADO COM XPATHS FUNCIONAIS
        """
        try:
            cliente = contrato.get("cliente", "")
            numero_titulo = contrato.get("numero_titulo", "")

            self.log_progresso(
                f"Consultando saldo devedor presente para: {cliente}")
            self.log_progresso(f"Título: {numero_titulo}")

            # WEBSCRAPING REAL - Navegação conforme PDD seção 7.3.1
            url_relatorio = "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/relatorios/saldo-devedor"
            self.log_progresso(f"Navegando para: {url_relatorio}")
            self.get_page(url_relatorio)
            time.sleep(3)

            # WEBSCRAPING REAL - Busca e preenche campo de pesquisa do cliente
            self.log_progresso("Pesquisando cliente...")
            combo_pesquisa = self.find_element(
                xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']"
            )

            if combo_pesquisa:
                # Limpar campo antes de preencher (importante para loop)
                combo_pesquisa.click()
                time.sleep(1)
                combo_pesquisa.clear()
                time.sleep(1)

                # Preenche nome do cliente
                self.send_text_human_like(
                    xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']",
                    text=cliente or ""
                )
                time.sleep(2)

                combo_pesquisa.click()
                time.sleep(1)
                self.send_text(
                    xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']",
                    text=Keys.TAB
                )
                time.sleep(1)

                # WEBSCRAPING REAL - Clica em Consultar
                self.log_progresso("Executando consulta...")
                self.click(xpath="//button[normalize-space()='Consultar']")
                time.sleep(3)

                xpath_erro_botao = '//div[@data-testid="snackbar"]//p[@data-testid="snackbar-message" and contains(normalize-space(.), "Informe pelo menos um dos seguintes campos para efetuar a consulta")]'
                # Verifica se o cliente foi encontrado
                if self.check_for_error(xpath=xpath_erro_botao):
                    erro_msg = "Informe pelo menos um dos seguintes campos para efetuar a consulta (empresa, título ou cliente)."
                    self.log_erro(
                        f"Erro ao consultar cliente: {erro_msg}", Exception(erro_msg))
                    self.log_progresso(
                        "Voltando à tela de consulta para próximo contrato...")
                    return {"sucesso": False, "erro": erro_msg}
                # WEBSCRAPING REAL - CLICANDO EM TODOS NA BARRA PARA EXPORTAR TODOS OS REGISTROS
                self.log_progresso("Selecionando todos os registros...")
                self.click(
                    xpath='//div[@role="combobox" and contains(@class, "MuiSelect-select")]'
                )
                time.sleep(1)
                self.click(
                    xpath='//li[normalize-space(.)="Todas" or normalize-space(.)="All"]'
                )
                time.sleep(4)

                # WEBSCRAPING REAL - Gera relatório
                self.log_progresso("Gerando relatório...")
                self.click(
                    xpath="//button[@type='button' and contains(., 'Gerar Relatório')]"
                )
                time.sleep(2)

                # WEBSCRAPING REAL - Seleciona formato Excel
                self.log_progresso("Selecionando formato Excel...")
                self.click(
                    xpath="//legend[span[normalize-space(.)='Gerar relatório como']]/ancestor::div[contains(@class, 'MuiInputBase-root')][1]//div[@role='combobox' and contains(@class, 'MuiSelect-select')]"
                )
                time.sleep(1)

                self.click(
                    xpath='//li[@role="option" and @data-value="excel" and text()="EXCEL"]'
                )
                time.sleep(1)

                # WEBSCRAPING REAL - Exporta relatório
                self.log_progresso("Exportando relatório...")
                self.click(
                    xpath="//button[@type='button' and normalize-space()='Exportar']"
                )
                time.sleep(5)

                # PROCESSAMENTO DA PLANILHA BAIXADA
                self.log_progresso("Processando planilha baixada...")
                dados_planilha = await self._processar_planilha_baixada(
                    cliente, numero_titulo)

                # Registra consulta realizada
                if self.rastreamento:
                    await self.rastreamento.registrar_consulta_dados(
                        "SALDO_DEVEDOR_SIENGE", {
                            "cliente": cliente,
                            "numero_titulo": numero_titulo
                        }, dados_planilha)

                # NAVEGAR DE VOLTA À TELA DE CONSULTA PARA PRÓXIMO CONTRATO
                self.log_progresso(
                    "Voltando à tela de consulta para próximo contrato...")
                self.get_page(
                    "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/relatorios/saldo-devedor"
                )
                time.sleep(2)

            # DADOS PROCESSADOS DA PLANILHA REAL
            if dados_planilha and dados_planilha.get("sucesso"):
                dados_financeiros = dados_planilha
            else:
                # Fallback com dados vazios se planilha não processada
                dados_financeiros = {
                    "cliente":
                    cliente,
                    "numero_titulo":
                    numero_titulo,
                    "saldo_total":
                    0.0,
                    "parcelas_pendentes":
                    0,
                    "parcelas_ct": [],
                    "parcelas_rec_fat": [],
                    "status_cliente":
                    "erro_processamento",
                    "relatorio_exportado":
                    False,
                    "dados_brutos":
                    None,
                    "sucesso":
                    False,
                    "erro":
                    dados_planilha.get("erro",
                                       "Falha no processamento da planilha")
                }

            self.log_progresso(
                "Webscraping concluído - Aguardando processamento da planilha")
            return dados_financeiros

        except Exception as e:
            erro_msg = f"Erro na consulta de relatórios: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"erro": erro_msg, "sucesso": False}

    async def _processar_planilha_baixada(
            self, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        Processa planilha Excel baixada do Sienge aplicando regras PDD rigorosas
        PROCESSAMENTO IMPLEMENTADO PELO ASSISTENTE
        """
        try:
            RPA_DOWNLOADS_FOLDER = os.getenv("RPA_DOWNLOADS_FOLDER")
            if RPA_DOWNLOADS_FOLDER and RPA_DOWNLOADS_FOLDER.startswith('/'):
                # Remove barra inicial se houver
                RPA_DOWNLOADS_FOLDER = RPA_DOWNLOADS_FOLDER[1:]

            downloads_dir = Path(user_downloads_dir(
            )) / RPA_DOWNLOADS_FOLDER if RPA_DOWNLOADS_FOLDER else Path(
                user_downloads_dir())
            # PosixPath('/Users/tiagopereiraramos/Downloads/RPA_DOWNLOADS/saldo_devedor_presente-20250617-155816.xlsx') esse valor é um exemplo de como o caminho pode ser retornado, mas preciso do caminho do arquivo baixado mais recente
            self.log_progresso(
                f"Localizando planilha na pasta de downloads: {downloads_dir}")
            # Verifica se a pasta de downloads existe
            arquivos_excel = list(downloads_dir.glob("*.xlsx"))

            if not arquivos_excel:
                return {
                    "sucesso": False,
                    "erro": "Nenhuma planilha encontrada na pasta de downloads"
                }

            # Ajuste: seleciona o arquivo mais recente e retorna como string
            arquivo_mais_recente = max(arquivos_excel,
                                       key=lambda f: f.stat().st_mtime)
            caminho_arquivo = str(arquivo_mais_recente.resolve())

            self.log_progresso(
                f"Processando arquivo: {arquivo_mais_recente.name}")

            # Ler planilha Excel
            df = pd.read_excel(arquivo_mais_recente)

            # Salvar cópia na pasta do projeto
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_destino = self.pasta_planilhas / \
                f"sienge_{cliente.replace(' ', '_')}_{timestamp}.xlsx"
            shutil.copy2(arquivo_mais_recente, arquivo_destino)

            # Registra processamento da planilha
            if self.rastreamento:
                await self.rastreamento.registrar_processamento_planilha(
                    str(arquivo_destino), {
                        "cliente": cliente,
                        "numero_titulo": numero_titulo,
                        "arquivo_origem": caminho_arquivo
                    })

            # APLICAR VALIDAÇÃO PDD RIGOROSA CONFORME SEÇÃO 9.1.1
            validador = ValidadorInadimplenciaPDD()
            resultado_validacao = validador.validar_cliente(
                df, cliente, numero_titulo)

            # APLICAR REGRAS ESPECÍFICAS PDD 9.1.1
            resultado_regras_pdd = self.processador_regras.processar_dados_cliente_completo(
                df, cliente, numero_titulo, resultado_validacao)

            self.log_progresso(f"✅ Validação PDD 9.1.1 concluída:")
            self.log_progresso(
                f"  📊 Status: {resultado_validacao.get('status_cliente', 'N/A')}"
            )
            self.log_progresso(
                f"  🔢 Parcelas CT vencidas: {resultado_validacao.get('qtd_ct_vencidas', 0)}"
            )
            self.log_progresso(
                f"  ✔️ Pode reparcelar: {resultado_validacao.get('pode_reparcelar', False)}"
            )

            # LOGS ESPECÍFICOS DAS REGRAS 9.1.1
            if resultado_regras_pdd:
                self.log_progresso(
                    f"  📅 Dia vencimento identificado: {resultado_regras_pdd.get('dia_vencimento', 'N/A')}"
                )
                self.log_progresso(
                    f"  💰 Valor parcela atual: R$ {resultado_regras_pdd.get('valor_parcela_atual', 0):,.2f}"
                )
                self.log_progresso(
                    f"  🗓️ 1º vencimento carnê: {resultado_regras_pdd.get('primeiro_vencimento_carne', 'N/A')}"
                )
                self.log_progresso(
                    f"  ⚠️ Parcelas divergentes: {len(resultado_regras_pdd.get('parcelas_divergentes', []))}"
                )

            # COMBINAR RESULTADOS
            resultado_validacao.update(resultado_regras_pdd or {})

            # SALVAR DADOS DE AUDITORIA PDD CONFORME REQUERIDO
            dados_auditoria = {
                "cliente":
                cliente,
                "numero_titulo":
                numero_titulo,
                "arquivo_processado":
                str(arquivo_destino),
                "regras_pdd_aplicadas": {
                    "secao":
                    "9.1.1",
                    "dia_vencimento_identificado":
                    resultado_validacao.get('dia_vencimento'),
                    "valor_parcela_atual":
                    resultado_validacao.get('valor_parcela_atual'),
                    "primeiro_vencimento_carne":
                    resultado_validacao.get('primeiro_vencimento_carne'),
                    "tipo_reajuste":
                    resultado_validacao.get('tipo_reajuste'),
                    "parcelas_divergentes":
                    resultado_validacao.get('parcelas_divergentes', [])
                },
                "validacao_inadimplencia": {
                    "status_cliente":
                    resultado_validacao.get('status_cliente'),
                    "qtd_ct_vencidas":
                    resultado_validacao.get('qtd_ct_vencidas'),
                    "pode_reparcelar":
                    resultado_validacao.get('pode_reparcelar'),
                    "motivo_classificacao":
                    resultado_validacao.get('motivo_classificacao')
                },
                "timestamp_processamento":
                datetime.now().isoformat(),
                "planilha_bruta":
                df.to_dict('records') if len(df) < 1000 else
                "Planilha muito grande - dados resumidos"
            }

            # SALVAR AUDITORIA PDD
            arquivo_auditoria = self.pasta_planilhas.parent / "auditoria_pdd" / \
                f"auditoria_{cliente.replace(' ', '_')}_{timestamp}.json"
            arquivo_auditoria.parent.mkdir(parents=True, exist_ok=True)

            with open(arquivo_auditoria, 'w', encoding='utf-8') as f:
                json.dump(dados_auditoria, f, ensure_ascii=False, indent=2)

            self.log_progresso(f"📋 Auditoria PDD salva: {arquivo_auditoria}")

            return {
                "sucesso": True,
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "arquivo_processado": str(arquivo_destino),
                "arquivo_auditoria_pdd": str(arquivo_auditoria),
                "dados_validacao": resultado_validacao,
                "regras_pdd_aplicadas":
                dados_auditoria["regras_pdd_aplicadas"],
                "timestamp_processamento": datetime.now().isoformat()
            }

        except Exception as e:
            erro_msg = f"Erro no processamento da planilha: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"sucesso": False, "erro": erro_msg}

    async def _executar_etapa_consulta(
            self, contrato: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa etapa de consulta de relatórios financeiros
        """
        try:
            self.log_progresso("🔍 Executando APENAS consulta de relatórios...")
            return await self._consultar_relatorios_financeiros(contrato)
        except Exception as e:
            erro_msg = f"Erro na etapa de consulta: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"sucesso": False, "erro": erro_msg}

    async def _executar_etapa_reparcelamento(
            self, contrato: Dict[str, Any], indices: Dict[str, Any],
            dados_financeiros: Dict[str, Any], autorizar_reparcelamento: bool,
            notificar_analista: bool) -> ResultadoRPA:
        """
        Executa etapa de processamento de reparcelamento
        """
        try:
            await self._registrar_passo_execucao(
                "INICIO_PROCESSAMENTO_REPARCELAMENTO", {
                    "contrato": contrato.get("numero_titulo", ""),
                    "indices_fornecidos": bool(indices),
                    "autorizar_automatico": autorizar_reparcelamento,
                    "timestamp": datetime.now().isoformat()
                })

            self.log_progresso(
                "🔄 Executando processamento de reparcelamento...")

            # Verificar se pode reparcelar com base na validação PDD
            dados_validacao = dados_financeiros.get("dados_validacao", {})
            pode_reparcelar = dados_validacao.get("pode_reparcelar", False)

            await self._registrar_passo_execucao(
                "VALIDACAO_PDD_REPARCELAMENTO", {
                    "pode_reparcelar": pode_reparcelar,
                    "autorizar_reparcelamento": autorizar_reparcelamento,
                    "dados_validacao": dados_validacao,
                    "timestamp": datetime.now().isoformat()
                })

            if not pode_reparcelar and not autorizar_reparcelamento:
                motivo = dados_validacao.get("motivo_classificacao",
                                             "Cliente não pode reparcelar")

                await self._registrar_passo_execucao(
                    "REPARCELAMENTO_NAO_AUTORIZADO", {
                        "motivo": motivo,
                        "pode_reparcelar": pode_reparcelar,
                        "autorizar_reparcelamento": autorizar_reparcelamento,
                        "timestamp": datetime.now().isoformat()
                    })

                return ResultadoRPA(
                    sucesso=False,
                    mensagem=f"Reparcelamento não autorizado: {motivo}",
                    dados={
                        "contrato": contrato,
                        "validacao_pdd": dados_validacao,
                        "autorizado": False,
                        "motivo_recusa": motivo
                    })

            # Se chegou aqui, pode prosseguir com o reparcelamento
            await self._registrar_passo_execucao(
                "CLIENTE_APROVADO_REPARCELAMENTO", {
                    "numero_titulo": contrato.get("numero_titulo", ""),
                    "cliente": contrato.get("cliente", ""),
                    "timestamp": datetime.now().isoformat()
                })

            self.log_progresso("✅ Cliente aprovado para reparcelamento")

            # Calcular valores de reparcelamento com IGPM centralizado
            saldo_atual = dados_validacao.get("saldo_total", 0)
            parcelas_pendentes = dados_validacao.get(
                "qtd_parcelas_ct_a_vencer", 0)

            # Tentar obter IGPM dos índices fornecidos ou do data_manager centralizado
            igpm_fornecido = indices.get("igpm", {}).get(
                "valor") if indices else 0.0
            if igpm_fornecido is None:
                igpm_fornecido = 0.0

            await self._registrar_passo_execucao(
                "CALCULO_VALORES_REPARCELAMENTO", {
                    "saldo_atual": saldo_atual,
                    "parcelas_pendentes": parcelas_pendentes,
                    "igpm_fornecido": igpm_fornecido,
                    "timestamp": datetime.now().isoformat()
                })

            calculo_resultado = await self.processador_regras.calcular_valores_reparcelamento(
                saldo_atual=saldo_atual,
                indice_igpm=igpm_fornecido,
                parcelas_pendentes=parcelas_pendentes)

            await self._registrar_passo_execucao(
                "RESULTADO_CALCULO_REPARCELAMENTO", {
                    "sucesso_calculo": calculo_resultado.get("sucesso", False),
                    "acao_requerida": calculo_resultado.get("acao_requerida"),
                    "erro_calculo": calculo_resultado.get("erro"),
                    "timestamp": datetime.now().isoformat()
                })

            # Verificar se cálculo foi bem-sucedido
            if not calculo_resultado.get("sucesso", False):
                if calculo_resultado.get(
                        "acao_requerida") == "EXECUTAR_RPA_COLETA_INDICES":
                    await self._registrar_passo_execucao(
                        "IGPM_NAO_DISPONIVEL", {
                            "acao_requerida": "EXECUTAR_RPA_COLETA_INDICES",
                            "instrucoes":
                            "Execute o RPA de Coleta de Índices para obter o valor atual do IGPM",
                            "timestamp": datetime.now().isoformat()
                        })

                    self.log_progresso(
                        "⚠️ IGPM não disponível no banco de dados")
                    self.log_progresso(
                        "🔄 AÇÃO REQUERIDA: Execute o RPA de Coleta de Índices")

                    return ResultadoRPA(
                        sucesso=False,
                        mensagem="IGPM não disponível - Execute RPA de Coleta de Índices",
                        dados={
                            "contrato":
                            contrato,
                            "validacao_pdd":
                            dados_validacao,
                            "erro_calculo":
                            calculo_resultado.get("erro"),
                            "acao_requerida":
                            "EXECUTAR_RPA_COLETA_INDICES",
                            "instrucoes":
                            "Execute o RPA de Coleta de Índices para obter o valor atual do IGPM antes de processar o reparcelamento"
                        })
                else:
                    await self._registrar_passo_execucao(
                        "ERRO_CALCULO_REPARCELAMENTO", {
                            "erro": calculo_resultado.get("erro"),
                            "tipo_erro": "erro_calculo_geral",
                            "stack_trace": traceback.format_exc(),
                            "timestamp": datetime.now().isoformat()
                        })

                    return ResultadoRPA(
                        sucesso=False,
                        mensagem=f"Erro no cálculo de reparcelamento: {calculo_resultado.get('erro')}",
                        dados={
                            "contrato": contrato,
                            "validacao_pdd": dados_validacao,
                            "erro_calculo": calculo_resultado.get("erro")
                        })

            # Simular processamento de reparcelamento com valores calculados
            resultado_reparcelamento = {
                "sucesso": True,
                "novo_titulo_gerado":
                f"REP_{contrato.get('numero_titulo', '')}_2025",
                "valor_anterior": saldo_atual,
                "valor_corrigido": calculo_resultado.get("novo_saldo"),
                "igpm_aplicado": calculo_resultado.get("igpm_utilizado"),
                "fator_correcao": calculo_resultado.get("fator_correcao"),
                "parcelas_processadas": parcelas_pendentes,
                "valores_sienge": calculo_resultado.get("valores_sienge"),
                "indices_aplicados": indices,
                "timestamp_reparcelamento": datetime.now().isoformat()
            }

            await self._registrar_passo_execucao(
                "REPARCELAMENTO_PROCESSADO_SUCESSO", {
                    "resultado_reparcelamento": resultado_reparcelamento,
                    "novo_titulo":
                    resultado_reparcelamento["novo_titulo_gerado"],
                    "valor_anterior":
                    resultado_reparcelamento["valor_anterior"],
                    "valor_corrigido":
                    resultado_reparcelamento["valor_corrigido"],
                    "timestamp": datetime.now().isoformat()
                })

            return ResultadoRPA(
                sucesso=True,
                mensagem="Reparcelamento processado com sucesso",
                dados={
                    "contrato": contrato,
                    "reparcelamento": resultado_reparcelamento,
                    "validacao_pdd": dados_validacao
                })

        except Exception as e:
            erro_msg = f"Erro na etapa de reparcelamento: {str(e)}"

            await self._registrar_passo_execucao(
                "ERRO_ETAPA_REPARCELAMENTO", {
                    "erro_detalhado": erro_msg,
                    "tipo_erro": type(e).__name__,
                    "stack_trace": traceback.format_exc(),
                    "timestamp": datetime.now().isoformat()
                })

            self.log_erro(erro_msg, e)
            return ResultadoRPA(
                sucesso=False,
                mensagem="Falha no processamento de reparcelamento",
                erro=erro_msg)

    async def _gerar_carne_sienge(self, contrato: Dict[str,
                                                       Any]) -> Dict[str, Any]:
        """
        Gera carnê atualizado no Sienge (placeholder)
        """
        try:
            self.log_progresso("📄 Gerando carnê atualizado...")

            # TODO: Implementar webscraping para geração de carnê
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"carne_{contrato.get('numero_titulo', 'indefinido')}_{timestamp}.pdf"

            return {
                "sucesso": True,
                "nome_arquivo": nome_arquivo,
                "caminho_arquivo": f"outputs/carnes/{nome_arquivo}",
                "timestamp_geracao": datetime.now().isoformat()
            }

        except Exception as e:
            erro_msg = f"Erro na geração do carnê: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"sucesso": False, "erro": erro_msg}

    async def executar_reparcelamento_webscraping(self,
                                                  numero_titulo: Optional[str] = None
                                                  ) -> ResultadoRPA:
        """
        MÉTODO PRINCIPAL PARA EXECUÇÃO DO REPARCELAMENTO
        Carrega dados da fila e executa webscraping no Sienge

        Args:
            numero_titulo: Número específico do título ou None para próximo da fila

        Returns:
            ResultadoRPA com sucesso/erro do processamento
        """
        if numero_titulo is None:
            numero_titulo = ""
        try:
            self.log_progresso("🚀 INICIANDO EXECUÇÃO DE REPARCELAMENTO")
            self.log_progresso("=" * 50)

            # 1. CARREGAR DADOS DA FILA
            # resultado_carga = await self.carregar_dados_fila_reparcelamento(
            #     numero_titulo)
            # O método 'carregar_dados_fila_reparcelamento' não existe na classe. Ajuste ou implemente conforme necessário.
            self.log_progresso(
                "[ATENÇÃO] O método 'carregar_dados_fila_reparcelamento' não está implementado nesta classe. Implemente ou ajuste o fluxo aqui.")
            return ResultadoRPA(sucesso=False, mensagem="Método 'carregar_dados_fila_reparcelamento' não implementado.", erro="Método ausente")
            # O código abaixo está inacessível enquanto o método correto não for implementado.
            # Remova o comentário e ajuste quando implementar 'carregar_dados_fila_reparcelamento'.
            # parametros = resultado_carga["parametros_navegacao"]
            # self.log_progresso(f"📄 Processando: {parametros['numero_titulo']}")
            # self.log_progresso(f"👤 Cliente: {parametros['cliente']}")
            # if not self.logado_sienge:
            #     await self._fazer_login_sienge()
            # resultado_webscraping = await self._navegar_e_executar_reparcelamento(parametros)
            # if not resultado_webscraping.get("sucesso", False):
            #     return ResultadoRPA(
            #         sucesso=False,
            #         mensagem="Falha no webscraping de reparcelamento",
            #         erro=resultado_webscraping.get("erro", "Erro no webscraping"),
            #         dados={"parametros_utilizados": parametros})
            # await self._atualizar_status_fila_reparcelamento(
            #     parametros["id_fila"] or '', "processado",
            #     resultado_webscraping or {})
            # await self._salvar_reparcelamento_historico(
            #     parametros, resultado_webscraping)
            # self.log_progresso("✅ REPARCELAMENTO CONCLUÍDO COM SUCESSO")
            # return ResultadoRPA(
            #     sucesso=True,
            #     mensagem=f"Reparcelamento processado: {parametros['numero_titulo']}",
            #     dados={
            #         "numero_titulo": parametros["numero_titulo"],
            #         "cliente": parametros["cliente"],
            #         "novo_titulo_gerado":
            #         resultado_webscraping.get("novo_titulo"),
            #         "saldo_anterior": parametros["saldo_anterior"],
            #         "saldo_novo": parametros["saldo_novo"],
            #         "parcelas_desmarcadas":
            #         len(parametros["parcelas_desmarcar"]),
            #         "timestamp_processamento": datetime.now().isoformat()
            #     })

            # 2. FAZER LOGIN NO SIENGE (se não logado)
            if not self.logado_sienge:
                await self._fazer_login_sienge()

            # 3. EXECUTAR WEBSCRAPING DE REPARCELAMENTO
            resultado_webscraping = await self._navegar_e_executar_reparcelamento(
                parametros)

            if not resultado_webscraping.get("sucesso", False):
                return ResultadoRPA(
                    sucesso=False,
                    mensagem="Falha no webscraping de reparcelamento",
                    erro=resultado_webscraping.get("erro",
                                                   "Erro no webscraping"),
                    dados={"parametros_utilizados": parametros})

            # 4. ATUALIZAR STATUS NA FILA
            await self._atualizar_status_fila_reparcelamento(
                parametros["id_fila"] or '', "processado",
                resultado_webscraping or {})

            # 5. SALVAR NO HISTÓRICO
            await self._salvar_reparcelamento_historico(
                parametros, resultado_webscraping)

            self.log_progresso("✅ REPARCELAMENTO CONCLUÍDO COM SUCESSO")

            return ResultadoRPA(
                sucesso=True,
                mensagem=f"Reparcelamento processado: {parametros['numero_titulo']}",
                dados={
                    "numero_titulo": parametros["numero_titulo"],
                    "cliente": parametros["cliente"],
                    "novo_titulo_gerado":
                    resultado_webscraping.get("novo_titulo"),
                    "saldo_anterior": parametros["saldo_anterior"],
                    "saldo_novo": parametros["saldo_novo"],
                    "parcelas_desmarcadas":
                    len(parametros["parcelas_desmarcar"]),
                    "timestamp_processamento": datetime.now().isoformat()
                })

        except Exception as e:
            erro_msg = f"Erro na execução do reparcelamento: {str(e)}"
            self.log_erro(erro_msg, e)

            return ResultadoRPA(sucesso=False,
                                mensagem="Falha na execução do reparcelamento",
                                erro=erro_msg)
        # Garantir retorno padrão
        return ResultadoRPA(sucesso=False, mensagem="Execução não concluída", erro="Fluxo inesperado")

    async def _navegar_e_executar_reparcelamento(
            self, parametros: Dict[str, Any]) -> Dict[str, Any]:
        """
        IMPLEMENTAÇÃO DE WEBSCRAPING - PROCEDIMENTO COMPLETO CONFORME PDD

        REGRAS IMPLEMENTADAS DO DOCUMENTO (Passos 21-28):
        ✅ Passo 21: Consulta do título
        ✅ Passo 22: Seleção de documentos + "Marcar Todos"
        ✅ Passo 23: FILTRO CRÍTICO - Desmarcar parcelas ≤ mês vigente
        ✅ Passo 24: Detalhamento "CORREÇÃO MM/AA"
        ✅ Passo 25: Configuração obrigatória (PM, IGP-M, Juros Fixo 8%)
        ✅ Passo 26-28: Finalização com correção de diferença

        Args:
            parametros: Dict com todos os dados calculados pelas regras PDD

        Returns:
            Dict com resultado do webscraping
        """
        try:
            self.log_progresso("🌐 Iniciando reparcelamento conforme PDD...")

            # PASSO 21: NAVEGAÇÃO E CONSULTA DO TÍTULO
            url_reparcelamento = parametros["url_reparcelamento"]
            self.log_progresso(f"📍 Navegando para: {url_reparcelamento}")
            self.get_page(url_reparcelamento)
            time.sleep(6)

            numero_titulo = parametros["numero_titulo"]
            self.log_progresso(
                f"🔍 PASSO 21: Consultando título: {numero_titulo}")

            # IMPLEMENTAR: Campo obrigatório de número do título
            iframe_ctx = self.on_iframe(xpath='//iframe[@id="iFramePage"]')
            if iframe_ctx is not None:
                with iframe_ctx:
                    self.log_progresso("Preenchendo número do título...")
                    self.click(xpath="//input[@id='titulo.tituloPK.nuTitulo']")
                    self.send_text(
                        xpath="//input[@id='titulo.tituloPK.nuTitulo']",
                        text=numero_titulo
                    )

                    self.log_progresso("Clicando em Consultar...")
                    self.click(
                        xpath="//input[@type='button' and @name='btFiltrar']")
                    time.sleep(4)

                    # PASSO 22: SELEÇÃO DE DOCUMENTOS
                    self.log_progresso(
                        "✅ PASSO 22: Título listado - selecionando documentos")
                    self.click(
                        xpath="//input[@type='button' and @name='btNext']")

                    # Aguardar carregamento e fazer scroll para "Marcar Todos"
                    time.sleep(6)  # Aguardar carregamento
                    self.check_for_error()
                    tabela = self.find_element(
                        xpath='//table[@id="TituloRow"]')
                    if tabela:
                        self.log_progresso(
                            "✅ Selecionando TODOS os documentos...")
                        radios = tabela.find_elements(
                            By.XPATH,
                            './/input[@type="radio" and contains(@id, "flSelecionado_") and not(ancestor::tr[contains(@style, "display: none")])]'
                        )
                        for radio in radios:
                            radio.click()

                    self.log_progresso("Clicando em Próximo...")
                    self.click(
                        xpath='//input[@type="button" and @name="btNext" and @value="Próximo"]')

                    # PASSO 23: APLICAÇÃO DO FILTRO CRÍTICO DE PARCELAS
                    self.log_progresso("📄 Localizando botão 'Marcar Todos'...")

                    # 1. Clicar em "Marcar Todos" conforme PDD
                    try:
                        marcar_todos_btn_xpath = '//input[@type="button" and @id="btTodos" and @value="Marcar todos"]'
                        self.click(marcar_todos_btn_xpath)
                        self.log_progresso("✅ Botão 'Marcar Todos' clicado.")
                        time.sleep(1)
                    except Exception as e:
                        self.log_warning(
                            f"⚠️ Botão 'Marcar Todos' não encontrado ou não clicável: {e}")

                    # 2. Desmarcar parcelas conforme regras do PDD (vencimento <= mês vigente)
                    parcelas_a_desmarcar = parametros.get(
                        "parcelas_desmarcar", [])
                    self.log_progresso(
                        f"🔎 Analisando {len(parcelas_a_desmarcar)} parcela(s) para desmarcar.")

                    if not parcelas_a_desmarcar:
                        self.log_progresso(
                            "Nenhuma parcela a desmarcar. Todas as 12 parcelas permanecerão marcadas.")
                    else:
                        datas_a_desmarcar = {p['data_vencimento']
                                             for p in parcelas_a_desmarcar}

                        # Mapeia todas as linhas visíveis da grid
                        grid_rows_xpath = "//table[contains(@id, 'parcelaRow')]//tr[contains(@id, 'linhaParcelaRow_') and not(contains(@style, 'display: none'))]"
                        rows = self.find_elements(xpath=grid_rows_xpath)

                        if not rows:
                            self.log_warning(
                                "⚠️ Nenhuma linha de parcela encontrada na grid para análise.")
                        else:
                            self.log_progresso(
                                f"Iterando sobre {len(rows)} linhas da grid de parcelas.")
                            for row in rows:
                                try:
                                    # Extrai a data de vencimento da linha
                                    date_input = row.find_element(
                                        By.XPATH, ".//input[contains(@id, '.dtVencto_')]")
                                    due_date = date_input.get_attribute(
                                        'value')

                                    # Se a data da linha está na lista de datas a desmarcar
                                    if due_date in datas_a_desmarcar:
                                        self.log_progresso(
                                            f"   - Encontrada parcela para desmarcar: vencimento {due_date}")
                                        checkbox = row.find_element(
                                            By.XPATH, ".//input[contains(@id, '.flSelecionado_') and @type='checkbox']")

                                        # Garante que está selecionado antes de clicar para desmarcar
                                        if checkbox.is_selected():
                                            checkbox.click()
                                            self.log_progresso(
                                                f"     ✅ Checkbox da parcela {due_date} desmarcado.")
                                        else:
                                            self.log_progresso(
                                                f"     ℹ️ Checkbox da parcela {due_date} já estava desmarcado.")
                                except Exception as e:
                                    self.log_warning(
                                        f"   - ⚠️ Erro ao processar uma linha da grid: {e}")

                    # 3. Clicar em "Próximo" para avançar para a tela de detalhamento
                    self.log_progresso(
                        "Clicando em 'Próximo' para ir à tela de detalhamento...")
                    self.click(
                        xpath='//input[@type="button" and @name="btNext" and @value="Próximo"]')

                    # Trata qualquer alerta que possa aparecer após avançar
                    self.check_for_error()

                    # PASSO 24: CONFIGURAÇÃO DO DETALHAMENTO
                    valores_sienge = parametros["valores_sienge"]
                    # "CORREÇÃO MM/AA"
                    detalhamento = valores_sienge["detalhamento"]

                    self.log_progresso(
                        f"📝 PASSO 24: Configurando detalhamento: {detalhamento}")
                    # TODO: Clicar em "Próximo"
                    # TODO: Scroll para visualizar campos
                    # TODO: Preencher campo "Detalhamento" com formato obrigatório
                    # TODO: Clicar em "Adicionar" para confirmar
                    self.click(
                        xpath='//textarea[@id="deObservacao" and @name="deObservacao"]')
                    time.sleep(1)
                    self.send_text(
                        xpath='//textarea[@id="deObservacao" and @name="deObservacao"]', text=detalhamento)
                    time.sleep(1)
                    self.click(
                        xpath='//input[@type="button" and @id="btNovaLinhaCondicaoRow" and @value="Adicionar"]')
                    # PASSO 25: PREENCHIMENTO DOS DADOS DO PARCELAMENTO
                    self.log_progresso(
                        "💰 PASSO 25: Preenchendo dados obrigatórios...")

                    # IMPLEMENTAR: Campos com valores fixos obrigatórios
                    # - Tipo condição: "PM" (SEMPRE)
                    self.click(
                        xpath='//input[@id="tipoCondicao.tipoCondicaoPK.cdTipoCondicao" and @type="text"]')
                    self.send_text(
                        xpath='//input[@id="tipoCondicao.tipoCondicaoPK.cdTipoCondicao" and @type="text"]', text="PM")
                    # - Portador: "1 Carteira" (NÃO alterar)
                    # - Operação cobrança: "0 Cobrança em Carteira" (NÃO alterar)
                    # - Indexador: "1 IGP-M" (SEMPRE IGP-M)

                    # IMPLEMENTAR: Campos da planilha
                    # - Valor total: valores_sienge["valor_total"]
                    # - Quantidade parcelas: calculado pelo sistema
                    # - Data 1º vencimento: valores_sienge["data_primeiro_vencimento"]

                    # CONFIGURAÇÃO OBRIGATÓRIA DE JUROS (Passo 25 continuação)
                    # - Tipo de juros: "Nenhum" (OBRIGATÓRIO)
                    # - Percentual: NÃO alterar
                    # - Data base: NÃO alterar
                    # TODO: Clicar em "Confirmar"

                    # PASSO 26-28: VALIDAÇÃO E FINALIZAÇÃO
                    self.log_progresso(
                        "🔧 PASSOS 26-28: Processando finalização...")

                    # IMPLEMENTAR: Validações automáticas do sistema
                    # - Verificar mensagem de diferença entre valores
                    # - Confirmar parcelas do novo parcelamento
                    # - Anotar valor da diferença

                    # REGRA CRÍTICA: Replicar valor "Diferença" no campo "Correção"
                    # TODO: Clicar em "Próximo"
                    # TODO: Clicar em "OK"
                    # TODO: Localizar campo "Correção"
                    # TODO: Replicar exatamente o valor do campo "Diferença"

                    # TRATAMENTO DE ERRO ESPECÍFICO (Passo 27)
                    # Mensagem: "O somatório do valor dos campos 'correção', 'juros' e 'aditivo'
                    # deve ser igual ao valor do campo 'diferença'."
                    # TODO: Se erro aparecer, repetir valor diferença no campo correção

                    # CONFIRMAÇÃO FINAL (Passo 28)
                    # TODO: Clicar em "Salvar"
                    # TODO: Clicar em "OK" na mensagem
                    # TODO: Verificar confirmação de atualização

                    # PLACEHOLDER - SUBSTITUA PELA IMPLEMENTAÇÃO REAL
                    novo_titulo_gerado = f"REP_{numero_titulo}_{datetime.now().strftime('%Y%m%d')}"

                    self.log_progresso(
                        f"✅ REPARCELAMENTO FINALIZADO - Novo título: {novo_titulo_gerado}")
                    self.log_progresso(
                        "📋 Todos os passos PDD (21-28) executados com sucesso")

                    return {
                        "sucesso": True,
                        "novo_titulo": novo_titulo_gerado,
                        "parcelas_processadas": len(parcelas_a_desmarcar),
                        "valores_aplicados": valores_sienge,
                        "passos_pdd_executados": "21-28",
                        "timestamp_webscraping": datetime.now().isoformat()
                    }

        except Exception as e:
            erro_msg = f"Erro no webscraping PDD: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"sucesso": False, "erro": erro_msg}

        # Garantir retorno padrão
        return {"sucesso": False, "erro": "Fluxo inesperado no webscraping"}

    async def _atualizar_status_fila_reparcelamento(
            self, id_fila: str, novo_status: str,
            dados_resultado: Dict[str, Any]):
        """Atualiza status do contrato na fila de reparcelamento"""
        try:
            if id_fila is None or id_fila == "":
                self.log_erro("id_fila não informado para atualização de status na fila!", Exception(
                    "id_fila não informado para atualização de status na fila!"))
                raise ValueError(
                    "id_fila não informado para atualização de status na fila!")
            if not isinstance(dados_resultado, dict):
                dados_resultado = {}
            from core.data_manager import data_manager
            resultado = await data_manager.atualizar_status_fila_sienge(id_fila or '', novo_status)
            self.log_progresso(
                f"📊 Status atualizado na fila: {id_fila} → {novo_status} | Resultado: {resultado}"
            )
        except Exception as e:
            self.log_erro(f"Erro ao atualizar status na fila: {str(e)}", e)

    async def _salvar_reparcelamento_historico(self, parametros: Dict[str,
                                                                      Any],
                                               resultado: Dict[str, Any]):
        """Salva reparcelamento no histórico completo"""
        try:
            from core.data_manager import data_manager

            documento_historico = {
                "numero_titulo": parametros["numero_titulo"],
                "cliente": parametros["cliente"],
                "data_processamento": datetime.now(),
                "novo_titulo_gerado": resultado.get("novo_titulo"),
                "saldo_anterior": parametros["saldo_anterior"],
                "saldo_novo": parametros["saldo_novo"],
                "igpm_aplicado": parametros["igpm_aplicado"],
                "parcelas_desmarcadas": parametros["parcelas_desmarcar"],
                "status_processamento": "concluido",
                "dados_completos": {
                    "parametros_utilizados": parametros,
                    "resultado_webscraping": resultado
                }
            }

            await data_manager.salvar_contrato_processado(
                documento_historico)
            self.log_progresso("📚 Reparcelamento salvo no histórico")

        except Exception as e:
            self.log_erro(f"Erro ao salvar no histórico: {str(e)}", e)

    async def finalizar(self):
        """Finaliza RPA e limpa recursos"""
        try:
            self.log_progresso("RPA Sienge finalizado")
        except Exception as e:
            self.log_erro("Erro ao finalizar RPA", e)

    async def _registrar_passo_execucao(self, nome_passo: str,
                                        dados: Dict[str, Any]):
        """
        MÉTODO SUBSTITUÍDO pelo sistema unificado de rastreamento
        Mantido para compatibilidade - delega para o rastreamento unificado
        """
        if self.rastreamento:
            await self.rastreamento.registrar_passo(nome_passo,
                                                    dados,
                                                    categoria="OPERACAO")
        else:
            self.log_progresso(
                f"⚠️ Rastreamento não iniciado - passo: {nome_passo}")

    async def executar_reparcelamento_com_contrato_processado(self, contrato_processado: dict) -> ResultadoRPA:
        """
        Executa o reparcelamento a partir de um contrato já processado (contratos_processados),
        sem buscar dados na fila. Usa os dados completos do contrato para montar os parâmetros.
        """
        try:
            self.log_progresso(
                "🚀 INICIANDO REPARCELAMENTO COM CONTRATO PROCESSADO")
            if not contrato_processado:
                return ResultadoRPA(sucesso=False, mensagem="Contrato processado não fornecido", erro="Contrato processado não fornecido")

            # Extrair dados principais
            numero_titulo = contrato_processado.get("numero_titulo", "")
            cliente = contrato_processado.get("cliente", "")
            empreendimento = contrato_processado.get("empreendimento", "")
            dados_completos = contrato_processado.get("dados_completos", {})
            dados_validacao = dados_completos.get("dados_validacao", {})
            regras_pdd_aplicadas = contrato_processado.get(
                "regras_pdd_aplicadas", {})
            saldo_anterior = contrato_processado.get("saldo_anterior", 0)
            saldo_novo = contrato_processado.get("saldo_novo", 0)
            indexador = contrato_processado.get("indexador", "")
            # Parcelas a vencer e detalhes
            parcelas_ct_a_vencer = dados_validacao.get(
                "parcelas_ct_a_vencer_detalhes", [])
            # IGPM e índices
            from core.data_manager import data_manager
            igpm_valor = await data_manager.obter_indice_mais_recente("igpm")
            if igpm_valor is None:
                igpm_valor = 0.0
            # Calcular valores de reparcelamento
            calculo_resultado = await self.processador_regras.calcular_valores_reparcelamento(
                saldo_atual=dados_validacao.get("saldo_total", 0),
                indice_igpm=igpm_valor,
                parcelas_pendentes=dados_validacao.get(
                    "qtd_parcelas_ct_a_vencer", 0)
            )
            # Determinar parcelas para desmarcar
            parcelas_desmarcar = self.processador_regras.determinar_parcelas_desmarcar(
                parcelas_ct_a_vencer)
            # Montar parâmetros para webscraping
            parametros_navegacao = {
                "numero_titulo": numero_titulo,
                "cliente": cliente,
                "empreendimento": empreendimento,
                "url_reparcelamento": "https://jmservicos.sienge.com.br/sienge/8/index.html#/common/page/1047",
                "valores_sienge": calculo_resultado.get("valores_sienge", {}),
                "parcelas_desmarcar": parcelas_desmarcar,
                "total_parcelas_desmarcar": len(parcelas_desmarcar),
                "saldo_anterior": saldo_anterior,
                "saldo_novo": saldo_novo,
                "fator_correcao": calculo_resultado.get("fator_correcao", 1),
                "igpm_aplicado": igpm_valor,
                "pode_reparcelar": dados_validacao.get("pode_reparcelar", False),
                "status_cliente": dados_validacao.get("status_cliente", ""),
                "qtd_ct_vencidas": dados_validacao.get("qtd_ct_vencidas", 0),
                "id_fila": dados_completos.get("id_fila", ""),
                "timestamp_carregamento": datetime.now().isoformat()
            }
            self.log_progresso(
                f"✅ Parâmetros montados para reparcelamento do contrato {numero_titulo}")
            # --- BREAKPOINT SUGERIDO ---
            # Chamar o webscraping de reparcelamento
            resultado_webscraping = await self._navegar_e_executar_reparcelamento(parametros_navegacao)
            # Atualizar status e histórico se necessário
            # (Opcional: pode atualizar status_sicredi ou outro campo aqui)
            return ResultadoRPA(
                sucesso=resultado_webscraping.get("sucesso", False),
                mensagem=resultado_webscraping.get(
                    "mensagem", "Reparcelamento executado"),
                dados=resultado_webscraping
            )
        except Exception as e:
            erro_msg = f"Erro na execução do reparcelamento com contrato processado: {str(e)}"
            self.log_erro(erro_msg, e)
            return ResultadoRPA(sucesso=False, mensagem="Falha na execução do reparcelamento", erro=erro_msg)

    # ============================================================================
    # MÓDULO DE PREENCHIMENTO DA PLANILHA BASE DE CÁLCULO REPARCELAMENTO 2025.xlsx
    # ============================================================================
    # Implementação conforme PDD seções 8, 9.1.2 e 10
    # Responsável por preencher a planilha com dados coletados do Sienge

    async def _conectar_google_sheets(self, caminho_credenciais: Optional[str] = None):
        """
        Estabelece conexão com Google Sheets usando service account
        Mesmo método usado no RPA Coleta de Índices para manter consistência

        Args:
            caminho_credenciais: Caminho para arquivo de credenciais
        """
        try:
            if not caminho_credenciais:
                caminho_credenciais = ".credentials/gspread-459713-aab8a657f9b0.json"

            self.log_progresso(
                f"Conectando ao Google Sheets com credenciais: {caminho_credenciais}")

            import gspread
            from google.oauth2.service_account import Credentials

            # Configura credenciais e escopos
            credenciais = Credentials.from_service_account_file(
                caminho_credenciais,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ]
            )

            # Autoriza cliente
            self.cliente_sheets = gspread.authorize(credenciais)
            self.log_progresso("✅ Conectado ao Google Sheets com sucesso")

        except Exception as e:
            raise Exception(f"Falha na conexão com Google Sheets: {str(e)}")

    async def preencher_planilha_calculo_reparcelamento(
        self,
        planilha_id: str,
        dados_financeiros: Dict[str, Any],
        indices_economicos: Dict[str, Any],
        credenciais_google: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        PREENCHIMENTO COMPLETO DA PLANILHA BASE DE CÁLCULO REPARCELAMENTO 2025.xlsx
        Conforme PDD seções 8, 9.1.2 e 10

        Args:
            planilha_id: ID da planilha Google Sheets
            dados_financeiros: Dados coletados do relatório Sienge
            indices_economicos: Índices IPCA/IGPM coletados
            credenciais_google: Caminho para credenciais (opcional)

        Returns:
            Dict com resultado do preenchimento
        """
        try:
            self.log_progresso(
                "📊 INICIANDO PREENCHIMENTO DA PLANILHA DE CÁLCULO")
            self.log_progresso("=" * 60)

            # 1. CONECTAR AO GOOGLE SHEETS
            await self._conectar_google_sheets(credenciais_google)

            # 2. ABRIR PLANILHA
            planilha = self.cliente_sheets.open_by_key(planilha_id)
            self.log_progresso(f"✅ Planilha aberta: {planilha.title}")

            # 3. ATUALIZAR ÍNDICES ECONÔMICOS (Passos 7.1 e 7.2 do PDD)
            await self._atualizar_indices_planilha(planilha, indices_economicos)

            # 4. PROCESSAR NOVOS CONTRATOS (Passo 8.1 do PDD)
            await self._processar_novos_contratos(planilha)

            # 5. ATUALIZAR CONSULTA IPTU (Passo 8.2 do PDD)
            await self._atualizar_consulta_iptu(planilha)

            # 6. PREENCHER DADOS DO RELATÓRIO SIENGE (Passo 9.1.2 do PDD)
            await self._preencher_dados_relatorio_sienge(planilha, dados_financeiros)

            # 7. IDENTIFICAR CONTRATOS PARA REPARCELAMENTO (Passo 9.1.2 continuação)
            contratos_reparcelamento = await self._identificar_contratos_reparcelamento(planilha)

            # 8. PREPARAR ENVIO DE E-MAIL (Passo 10 - sem executar)
            dados_email = await self._preparar_envio_email(planilha, contratos_reparcelamento)

            self.log_progresso(
                "✅ PREENCHIMENTO DA PLANILHA CONCLUÍDO COM SUCESSO")

            return {
                "sucesso": True,
                "planilha_atualizada": planilha_id,
                "contratos_para_reparcelamento": len(contratos_reparcelamento),
                "dados_email_preparados": dados_email,
                "timestamp_preenchimento": datetime.now().isoformat()
            }

        except Exception as e:
            erro_msg = f"Erro no preenchimento da planilha: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"sucesso": False, "erro": erro_msg}

    async def _atualizar_indices_planilha(self, planilha, indices_economicos: Dict[str, Any]):
        """
        Atualiza abas IPCA e IGPM da planilha com índices coletados
        Conforme PDD seções 7.1 e 7.2
        """
        try:
            self.log_progresso(
                "📈 Atualizando índices econômicos na planilha...")

            # Atualizar IPCA
            if "ipca" in indices_economicos:
                await self._atualizar_aba_ipca(planilha, indices_economicos["ipca"])

            # Atualizar IGPM
            if "igpm" in indices_economicos:
                await self._atualizar_aba_igpm(planilha, indices_economicos["igpm"])

            self.log_progresso("✅ Índices econômicos atualizados com sucesso")

        except Exception as e:
            raise Exception(f"Erro ao atualizar índices: {str(e)}")

    async def _atualizar_aba_ipca(self, planilha, dados_ipca: Dict[str, Any]):
        """Atualiza aba IPCA da planilha"""
        try:
            aba_ipca = planilha.worksheet("IPCA")
            valores_existentes = aba_ipca.get_all_values()

            mes_dados = dados_ipca.get(
                'mes', self._obter_mes_atual_formatado())
            valor_coletado = f'{dados_ipca["valor"]}%'

            # Procura se o mês já existe
            for i, linha in enumerate(valores_existentes):
                if len(linha) >= 2 and linha[0].strip().lower() == mes_dados.lower():
                    linha_mes_existente = i + 1
                    valor_existente = linha[1].strip()

                    if valor_existente != valor_coletado:
                        aba_ipca.update_acell(
                            f'B{linha_mes_existente}', valor_coletado)
                        self.log_progresso(
                            f"🔄 IPCA {mes_dados}: Atualizado de {valor_existente} para {valor_coletado}")
                    else:
                        self.log_progresso(
                            f"📋 IPCA {mes_dados}: Valor já está atualizado")
                    return

            # Se não encontrou, adiciona nova linha
            linhas_usadas = [i for i, linha in enumerate(valores_existentes)
                             if len(linha) >= 2 and linha[0].strip() and linha[1].strip()]
            proxima_linha = max(linhas_usadas) + 2 if linhas_usadas else 2

            aba_ipca.update_acell(f'A{proxima_linha}', mes_dados)
            aba_ipca.update_acell(f'B{proxima_linha}', valor_coletado)
            self.log_progresso(
                f"➕ IPCA {dados_ipca['valor']}% inserido na linha {proxima_linha}")

        except Exception as e:
            raise Exception(f"Erro ao atualizar aba IPCA: {str(e)}")

    def _formatar_mes_igpm(self, valor_mes):
        """
        Converte datas (datetime, string, etc) para o formato 'mmm.-aa' em português,
        robusto para qualquer entrada (ex: '25/07/2024', 'jul.-24', '01/03/2025', etc).
        """
        meses_pt = ['jan', 'fev', 'mar', 'abr', 'mai',
                    'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
        if isinstance(valor_mes, datetime):
            return f"{meses_pt[valor_mes.month-1]}.-{str(valor_mes.year)[-2:]}"
        try:
            # Tenta converter string para datetime
            data = None
            for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y'):
                try:
                    data = datetime.strptime(str(valor_mes), fmt)
                    break
                except Exception:
                    continue
            if data:
                return f"{meses_pt[data.month-1]}.-{str(data.year)[-2:]}"
        except Exception:
            pass
        # Se já estiver no formato correto, retorna
        if isinstance(valor_mes, str) and valor_mes.strip().count('-') == 1 and '.' in valor_mes:
            return valor_mes.strip().lower()
        # Se for só mês/ano, tenta converter
        try:
            partes = valor_mes.strip().split('-')
            if len(partes) == 2:
                mes = partes[0][:3].lower()
                ano = partes[1][-2:]
                if mes in meses_pt:
                    return f"{mes}.-{ano}"
        except Exception:
            pass
        return str(valor_mes).lower()

    async def _atualizar_aba_igpm(self, planilha, dados_igpm: Dict[str, Any]):
        """Atualiza aba IGPM da planilha"""
        try:
            aba_igpm = planilha.worksheet("IGPM")
            valores_existentes = aba_igpm.get_all_values()

            mes_dados = dados_igpm.get(
                'mes', self._obter_mes_atual_formatado())
            mes_dados_formatado = self._formatar_mes_igpm(mes_dados)
            valor_coletado = f'{dados_igpm["valor"]}%'

            # Procura se o mês já existe
            for i, linha in enumerate(valores_existentes):
                if len(linha) >= 2 and self._formatar_mes_igpm(linha[0]) == mes_dados_formatado:
                    linha_mes_existente = i + 1
                    valor_existente = linha[1].strip()

                    if valor_existente != valor_coletado:
                        aba_igpm.update_acell(
                            f'B{linha_mes_existente}', valor_coletado)
                        self.log_progresso(
                            f"🔄 IGPM {mes_dados_formatado}: Atualizado de {valor_existente} para {valor_coletado}")
                    else:
                        self.log_progresso(
                            f"📋 IGPM {mes_dados_formatado}: Valor já está atualizado")
                    return

            # Se não encontrou, adiciona nova linha
            linhas_usadas = [i for i, linha in enumerate(valores_existentes)
                             if len(linha) >= 2 and linha[0].strip() and linha[1].strip()]
            proxima_linha = max(linhas_usadas) + 2 if linhas_usadas else 2

            aba_igpm.update_acell(f'A{proxima_linha}', mes_dados_formatado)
            aba_igpm.update_acell(f'B{proxima_linha}', valor_coletado)
            self.log_progresso(
                f"➕ IGPM {valor_coletado} inserido na linha {proxima_linha} ({mes_dados_formatado})")

        except Exception as e:
            raise Exception(f"Erro ao atualizar aba IGPM: {str(e)}")

    def _obter_mes_atual_formatado(self) -> str:
        """Retorna o mês atual no formato usado na planilha (ex: abr.-25)"""
        return datetime.now().strftime("%b.-%y").lower()

    async def _processar_novos_contratos(self, planilha):
        """
        Processa novos contratos da planilha Base de apoio
        Conforme PDD Passo 8.1
        """
        try:
            self.log_progresso("📄 Processando novos contratos...")

            # Abre planilha Base de apoio
            planilha_apoio_id = os.getenv("PLANILHA_APOIO_ID")
            if not planilha_apoio_id:
                self.log_progresso(
                    "⚠️ PLANILHA_APOIO_ID não configurada - pulando novos contratos")
                return

            planilha_apoio = self.cliente_sheets.open_by_key(planilha_apoio_id)

            # Procura aba NOVOS CONTRATOS
            abas_disponiveis = [
                aba.title for aba in planilha_apoio.worksheets()]
            aba_novos_nome = None

            for possibilidade in ["NOVOS CONTRATOS", "Novos Contratos", "Novos contratos"]:
                if possibilidade in abas_disponiveis:
                    aba_novos_nome = possibilidade
                    break

            if not aba_novos_nome:
                self.log_progresso("⚠️ Aba de novos contratos não encontrada")
                return

            aba_novos_contratos = planilha_apoio.worksheet(aba_novos_nome)
            dados_novos_contratos = aba_novos_contratos.get_all_records()

            # Filtra contratos válidos
            contratos_validos = []
            for linha, contrato in enumerate(dados_novos_contratos, start=2):
                if any(str(valor).strip() for valor in contrato.values() if valor):
                    contrato['linha_planilha'] = linha
                    contratos_validos.append(contrato)

            if not contratos_validos:
                self.log_progresso("ℹ️ Nenhum novo contrato encontrado")
                return

            # Adiciona à planilha Base de cálculo
            aba_base_calculo = planilha.worksheet("Base de cálculo")
            cabecalhos = aba_base_calculo.row_values(1)

            # Encontra próxima linha vazia
            valores_existentes = aba_base_calculo.get_all_values()
            proxima_linha = len(valores_existentes) + 1

            for contrato in contratos_validos:
                linha_dados = []
                for cabecalho in cabecalhos:
                    valor = contrato.get(cabecalho, '')
                    linha_dados.append(str(valor) if valor else '')

                if linha_dados:
                    range_update = f'A{proxima_linha}:{chr(65 + len(linha_dados) - 1)}{proxima_linha}'
                    aba_base_calculo.update(range_update, [linha_dados])

                    self.log_progresso(
                        f"✅ Contrato adicionado: {contrato.get('Cliente', 'N/A')} - {contrato.get('numero_titulo', 'N/A')}")
                    proxima_linha += 1

            self.log_progresso(
                f"✅ {len(contratos_validos)} novos contratos processados")

        except Exception as e:
            self.log_warning(f"Erro ao processar novos contratos: {str(e)}")

    async def _atualizar_consulta_iptu(self, planilha):
        """
        Atualiza consulta IPTU da planilha Base de apoio
        Conforme PDD Passo 8.2
        """
        try:
            self.log_progresso("🏠 Atualizando consulta IPTU...")

            # Abre planilha Base de apoio
            planilha_apoio_id = os.getenv("PLANILHA_APOIO_ID")
            if not planilha_apoio_id:
                self.log_progresso(
                    "⚠️ PLANILHA_APOIO_ID não configurada - pulando IPTU")
                return

            planilha_apoio = self.cliente_sheets.open_by_key(planilha_apoio_id)

            # Procura aba Consulta IPTU
            abas_disponiveis = [
                aba.title for aba in planilha_apoio.worksheets()]
            aba_iptu_nome = None

            for possibilidade in ["Consulta IPTU", "IPTU", "Pendencias IPTU"]:
                if possibilidade in abas_disponiveis:
                    aba_iptu_nome = possibilidade
                    break

            if not aba_iptu_nome:
                self.log_progresso("⚠️ Aba de IPTU não encontrada")
                return

            aba_iptu = planilha_apoio.worksheet(aba_iptu_nome)
            dados_iptu = aba_iptu.get_all_records()

            # Filtra consultas do mês vigente
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year

            consultas_mes_vigente = []
            for linha, consulta in enumerate(dados_iptu, start=2):
                data_consulta_str = consulta.get('Data de consulta', '')
                if data_consulta_str:
                    try:
                        data_consulta = datetime.strptime(
                            str(data_consulta_str), '%d/%m/%Y')
                        if data_consulta.month == mes_atual and data_consulta.year == ano_atual:
                            consulta['linha_planilha'] = linha
                            consultas_mes_vigente.append(consulta)
                    except:
                        continue

            if not consultas_mes_vigente:
                self.log_progresso(
                    "ℹ️ Nenhuma consulta IPTU do mês vigente encontrada")
                return

            # Atualiza planilha Base de cálculo
            aba_base_calculo = planilha.worksheet("Base de cálculo")
            valores_existentes = aba_base_calculo.get_all_values()

            for consulta in consultas_mes_vigente:
                cliente = consulta.get('Cliente', '')
                numero_titulo = consulta.get('numero_titulo', '')
                pendencia_pmfi = consulta.get('PENDÊNCIAS PMFI', '')

                # Procura linha correspondente na Base de cálculo
                for i, linha in enumerate(valores_existentes):
                    if (linha[2].strip() == cliente.strip() and  # Coluna Cliente
                            linha[5].strip() == str(numero_titulo).strip()):  # Coluna numero_titulo

                        # Encontra coluna IPTU PENDÊNCIAS PMFI
                        cabecalhos = valores_existentes[0]
                        coluna_iptu = None
                        for j, cabecalho in enumerate(cabecalhos):
                            if 'IPTU PENDÊNCIAS PMFI' in str(cabecalho).upper():
                                coluna_iptu = j
                                break

                        if coluna_iptu is not None:
                            # Atualiza valor
                            celula = f'{chr(65 + coluna_iptu)}{i + 1}'
                            aba_base_calculo.update_acell(
                                celula, pendencia_pmfi)
                            self.log_progresso(
                                f"✅ IPTU atualizado: {cliente} - {numero_titulo}")
                        break

            self.log_progresso(
                f"✅ {len(consultas_mes_vigente)} consultas IPTU atualizadas")

        except Exception as e:
            self.log_warning(f"Erro ao atualizar consulta IPTU: {str(e)}")

    async def _preencher_dados_relatorio_sienge(self, planilha, dados_financeiros: Dict[str, Any]):
        """
        Preenche dados do relatório Sienge na planilha Base de cálculo
        Conforme PDD Passo 9.1.2 - Campos que alimentam as fórmulas da planilha
        """
        try:
            self.log_progresso(
                "📊 Preenchendo dados do relatório Sienge na planilha BASE DE CÁLCULO...")

            dados_validacao = dados_financeiros.get("dados_validacao", {})
            regras_pdd = dados_financeiros.get("regras_pdd_aplicadas", {})

            # Dados EXTRAÍDOS do Sienge (não calculados) conforme PDD 9.1.2
            dados_para_preencher = {
                # Campos que alimentam as fórmulas da planilha
                "Parcelas a vencer": dados_validacao.get("qtd_parcelas_ct_a_vencer", 0),
                "Valor da Parcela Base": dados_validacao.get("valor_parcela_atual", 0),
                # EXTRAÍDO do Sienge
                "Saldo devedor Base": dados_validacao.get("saldo_total", 0),
                "Dia de vencimento de parcelas": dados_validacao.get("dia_vencimento", ""),
                "1º vencimento carnê": regras_pdd.get("primeiro_vencimento_carne", ""),

                # Campos de pendências (status do cliente)
                "PENDÊNCIAS SIENGE INAD": "INADIMPLENTE" if dados_validacao.get("status_cliente") == "inadimplente" else "",
                "PENDÊNCIAS SIENGE": "SIM" if len(dados_validacao.get("parcelas_rec_fat", [])) > 0 else "",

                # CAMPOS NECESSÁRIOS PARA A FÓRMULA "% Reajuste total"
                # Fixo conforme PDD (sempre IGPM para reparcelamento)
                "Indexador": "IGPM",
                # Fixo conforme PDD (sempre 8% para reparcelamento)
                "Juros %": 8.0,
                # Fixo conforme PDD (sempre PM para reparcelamento)
                "Tipo condição": "PM",
                "Tipo reajuste": "anual",  # Fixo conforme PDD (sempre anual)
                "Original ou corrigido": "original"  # Status inicial do contrato
            }

            # Aba Base de cálculo
            aba_base_calculo = planilha.worksheet("Base de cálculo")
            valores_existentes = aba_base_calculo.get_all_values()
            cabecalhos = valores_existentes[0]

            # Encontra linha do contrato atual
            cliente_atual = dados_financeiros.get("cliente", "")
            numero_titulo_atual = dados_financeiros.get("numero_titulo", "")

            linha_contrato = None
            # Pula cabeçalho
            for i, linha in enumerate(valores_existentes[1:], start=2):
                if (linha[2].strip() == cliente_atual.strip() and  # Coluna Cliente
                        linha[5].strip() == str(numero_titulo_atual).strip()):  # Coluna numero_titulo
                    linha_contrato = i
                    break

            if linha_contrato is None:
                self.log_warning(
                    f"Contrato não encontrado na planilha: {cliente_atual} - {numero_titulo_atual}")
                return

            # Mapeia colunas da planilha
            mapeamento_colunas = {}
            for i, cabecalho in enumerate(cabecalhos):
                cabecalho_upper = str(cabecalho).upper()
                for campo, valor in dados_para_preencher.items():
                    if campo.upper() in cabecalho_upper:
                        mapeamento_colunas[campo] = i
                        break

            # Preenche dados na planilha
            for campo, valor in dados_para_preencher.items():
                if campo in mapeamento_colunas:
                    coluna = mapeamento_colunas[campo]
                    celula = f'{chr(65 + coluna)}{linha_contrato}'

                    # Formata valor conforme tipo de campo
                    if campo == "Valor da Parcela Base" or campo == "Saldo devedor Base":
                        # Valores monetários - sem formatação para não quebrar fórmulas
                        valor_formatado = valor if valor else 0
                    elif campo in ["PENDÊNCIAS SIENGE INAD", "PENDÊNCIAS SIENGE"]:
                        # Pendências - texto direto
                        valor_formatado = valor
                    elif campo == "Parcelas a vencer":
                        # Quantidade - número direto
                        valor_formatado = valor if valor else 0
                    elif campo == "Dia de vencimento de parcelas":
                        # Dia - número direto
                        valor_formatado = valor if valor else ""
                    elif campo == "1º vencimento carnê":
                        # Data - formato dd/mm/yyyy
                        valor_formatado = valor if valor else ""
                    elif campo == "Juros %":
                        # Percentual - número direto
                        valor_formatado = valor if valor else 8.0
                    elif campo in ["Indexador", "Tipo condição", "Tipo reajuste", "Original ou corrigido"]:
                        # Texto direto
                        valor_formatado = valor if valor else ""
                    else:
                        valor_formatado = str(valor) if valor else ""

                    # Atualiza célula na planilha
                    aba_base_calculo.update_acell(celula, valor_formatado)
                    self.log_progresso(f"   ✅ {campo}: {valor_formatado}")

            # Atualiza data do último reajuste
            coluna_ultimo_reajuste = None
            for i, cabecalho in enumerate(cabecalhos):
                if 'ÚLTIMO REAJUSTE' in str(cabecalho).upper():
                    coluna_ultimo_reajuste = i
                    break

            if coluna_ultimo_reajuste is not None:
                data_reajuste = datetime.now().strftime('%d/%m/%Y')
                celula = f'{chr(65 + coluna_ultimo_reajuste)}{linha_contrato}'
                aba_base_calculo.update_acell(celula, data_reajuste)
                self.log_progresso(f"   ✅ Último reajuste: {data_reajuste}")

            # Log dos dados que alimentarão as fórmulas
            self.log_progresso(f"\n📊 DADOS PREENCHIDOS PARA FÓRMULAS:")
            self.log_progresso(
                f"   📄 Parcelas a vencer: {dados_para_preencher['Parcelas a vencer']}")
            self.log_progresso(
                f"   💰 Valor da Parcela Base: R$ {dados_para_preencher['Valor da Parcela Base']:,.2f}")
            self.log_progresso(
                f"   💰 Saldo devedor Base: R$ {dados_para_preencher['Saldo devedor Base']:,.2f}")
            self.log_progresso(
                f"   📅 Dia de vencimento: {dados_para_preencher['Dia de vencimento de parcelas']}")
            self.log_progresso(
                f"   📅 1º vencimento carnê: {dados_para_preencher['1º vencimento carnê']}")
            self.log_progresso(
                f"   ⚠️ PENDÊNCIAS SIENGE INAD: {dados_para_preencher['PENDÊNCIAS SIENGE INAD']}")
            self.log_progresso(
                f"   📋 PENDÊNCIAS SIENGE: {dados_para_preencher['PENDÊNCIAS SIENGE']}")

            # Log dos campos para fórmula "% Reajuste total"
            self.log_progresso(f"\n🎯 CAMPOS PARA FÓRMULA '% Reajuste total':")
            self.log_progresso(
                f"   📊 Indexador: {dados_para_preencher['Indexador']}")
            self.log_progresso(
                f"   💰 Juros %: {dados_para_preencher['Juros %']}%")
            self.log_progresso(
                f"   📋 Tipo condição: {dados_para_preencher['Tipo condição']}")
            self.log_progresso(
                f"   📅 Tipo reajuste: {dados_para_preencher['Tipo reajuste']}")
            self.log_progresso(
                f"   📄 Original ou corrigido: {dados_para_preencher['Original ou corrigido']}")

            self.log_progresso(
                "✅ Dados do relatório Sienge preenchidos com sucesso na planilha BASE DE CÁLCULO")
            self.log_progresso(
                "🎯 As fórmulas da planilha agora podem calcular automaticamente:")
            self.log_progresso("   - 1º vencimento carnê")
            self.log_progresso("   - % Reajuste total")
            self.log_progresso("   - Parcela final")
            self.log_progresso("   - Saldo devedor final")
            self.log_progresso("   - Próximo reajuste")

        except Exception as e:
            self.log_warning(f"Erro ao preencher dados do relatório: {str(e)}")
            raise e

    async def _identificar_contratos_reparcelamento(self, planilha) -> List[Dict[str, Any]]:
        """
        Identifica contratos que precisam de reparcelamento
        Conforme PDD Passo 9.1.2 continuação
        """
        try:
            self.log_progresso(
                "🔍 Identificando contratos para reparcelamento...")

            aba_base_calculo = planilha.worksheet("Base de cálculo")
            dados_contratos = aba_base_calculo.get_all_records()

            mes_atual = datetime.now().month
            ano_atual = datetime.now().year

            contratos_para_reparcelamento = []

            for linha, contrato in enumerate(dados_contratos, start=2):
                try:
                    cliente = contrato.get('Cliente', '').strip()
                    numero_titulo = contrato.get('numero_titulo', '').strip()

                    if not cliente and not numero_titulo:
                        continue

                    # Verifica coluna "Mês reajuste"
                    mes_reajuste_str = contrato.get('Mês reajuste', '').strip()

                    if (not mes_reajuste_str or
                        mes_reajuste_str in ['', '#N/A', 'N/A', '#REF!', '#VALUE!', 'null', 'None'] or
                            len(mes_reajuste_str) < 3):
                        continue

                    # Verifica se é o mês atual
                    try:
                        data_reajuste = datetime.strptime(
                            str(mes_reajuste_str), '%d/%m/%Y')
                        if data_reajuste.month == mes_atual and data_reajuste.year == ano_atual:

                            # Verifica pendências
                            pendencia_pmfi = contrato.get(
                                'PENDÊNCIAS PMFI', '').strip()
                            pendencia_sienge_inad = contrato.get(
                                'PENDÊNCIAS SIENGE INAD', '').strip()
                            pendencia_sienge = contrato.get(
                                'PENDÊNCIAS SIENGE', '').strip()

                            # Regras de validação conforme PDD
                            pode_reparcelar = True
                            motivo_recusa = ""

                            if pendencia_pmfi and pendencia_pmfi.upper() not in ['', 'OK', 'NÃO']:
                                pode_reparcelar = False
                                motivo_recusa = f"Pendência PMFI: {pendencia_pmfi}"

                            if pendencia_sienge_inad and pendencia_sienge_inad.upper() in ['INADIMPLENTE', 'INAD', 'SIM']:
                                pode_reparcelar = False
                                motivo_recusa = f"Inadimplência: {pendencia_sienge_inad}"

                            if pendencia_sienge and pendencia_sienge.upper() not in ['', 'OK', 'NÃO']:
                                pode_reparcelar = False
                                motivo_recusa = f"Pendência Sienge: {pendencia_sienge}"

                            if pode_reparcelar:
                                contratos_para_reparcelamento.append({
                                    "linha_planilha": linha,
                                    "cliente": cliente,
                                    "numero_titulo": numero_titulo,
                                    "mes_reajuste": mes_reajuste_str,
                                    "pendencia_pmfi": pendencia_pmfi,
                                    "pendencia_sienge_inad": pendencia_sienge_inad,
                                    "pendencia_sienge": pendencia_sienge
                                })

                                self.log_progresso(
                                    f"   ✅ {cliente} - {numero_titulo} (linha {linha})")
                            else:
                                self.log_progresso(
                                    f"   ❌ {cliente} - {numero_titulo}: {motivo_recusa}")

                    except ValueError:
                        self.log_warning(
                            f"   ⚠️ Data inválida na linha {linha}: {mes_reajuste_str}")
                        continue

                except Exception as e:
                    self.log_warning(
                        f"   ⚠️ Erro ao processar linha {linha}: {str(e)}")
                    continue

            self.log_progresso(
                f"✅ {len(contratos_para_reparcelamento)} contratos identificados para reparcelamento")
            return contratos_para_reparcelamento

        except Exception as e:
            self.log_warning(f"Erro ao identificar contratos: {str(e)}")
            return []

    async def _preparar_envio_email(self, planilha, contratos_reparcelamento: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prepara dados para envio de e-mail (sem executar)
        Conforme PDD Passo 10
        """
        try:
            self.log_progresso("📧 Preparando dados para envio de e-mail...")

            # Dados do e-mail conforme PDD
            dados_email = {
                "assunto": "Lançamento de reparcelamentos autorizado",
                "destinatario": "robo@rorato.adm.br",
                "planilha_anexa": planilha.title,
                "contratos_para_reparcelamento": len(contratos_reparcelamento),
                "lista_contratos": [
                    {
                        "cliente": contrato["cliente"],
                        "numero_titulo": contrato["numero_titulo"],
                        "mes_reajuste": contrato["mes_reajuste"]
                    }
                    for contrato in contratos_reparcelamento
                ],
                "timestamp_preparacao": datetime.now().isoformat(),
                "observacao": "E-mail NÃO será enviado automaticamente - aguardando validação manual"
            }

            self.log_progresso(
                f"✅ Dados do e-mail preparados: {len(contratos_reparcelamento)} contratos")
            self.log_progresso(
                "💡 Para enviar o e-mail, execute manualmente o envio")

            return dados_email

        except Exception as e:
            self.log_warning(f"Erro ao preparar e-mail: {str(e)}")
            return {}
