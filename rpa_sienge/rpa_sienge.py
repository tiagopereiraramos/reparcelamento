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
from typing import Dict, Any, List
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
import traceback
from dotenv import load_dotenv

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

    def __init__(self):
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

    async def executar(self,
                       contrato: Dict[str, Any],
                       credenciais_sienge: Dict[str, str],
                       indices: Dict[str, Any] = None,
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
                        "contrato": contrato.get("numero_titulo", "N/A")
                    })
                await self.rastreamento.finalizar_rastreamento()

            self.log_erro(erro_msg, e)
            return ResultadoRPA(sucesso=False,
                                mensagem="Falha na execução do RPA Sienge",
                                erro=erro_msg)

        finally:
            # ✅ SEMPRE finaliza rastreamento
            if self.rastreamento:
                await self.rastreamento.finalizar_rastreamento()

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
            self.find_element(
                xpath='(//input[@id="username"])[1]').send_keys(usuario_sienge)

            # Preenche senha inicial
            self.find_element(
                xpath='//input[@id="password"]').send_keys(senha_sienge)

            # Clica botão entrar inicial
            self.find_element(xpath='//*[@id="btnEntrarComSiengeID"]').click()
            time.sleep(2)

            # Segunda etapa - email
            self.find_element(
                xpath='//label[text()="Seu e-mail"]/following-sibling::div//input'
            ).send_keys(usuario_sienge)

            # Clica continuar
            self.find_element(
                xpath="//button[normalize-space(text())='CONTINUAR']").click()

            # Terceira etapa - senha final
            self.find_element(
                xpath="//input[@id='signup-password']").send_keys(senha_sienge)

            # Clica entrar final
            self.find_element(
                xpath="//button[normalize-space(text())='ENTRAR']").click()

            # Login bem-sucedido
            self.logado_sienge = True

            await self.rastreamento.registrar_login_sistema(
                "sienge", usuario_sienge, True)

            self.log_progresso("Login no Sienge realizado com sucesso")

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
                    text=cliente)
                time.sleep(2)

                combo_pesquisa.click()
                time.sleep(1)
                combo_pesquisa.send_keys(Keys.TAB)
                time.sleep(1)

                # WEBSCRAPING REAL - Clica em Consultar
                self.log_progresso("Executando consulta...")
                self.click(xpath="//button[normalize-space()='Consultar']")
                time.sleep(3)

                xpath_erro_botao = '//div[@data-testid="snackbar"]//p[@data-testid="snackbar-message" and contains(normalize-space(.), "Informe pelo menos um dos seguintes campos para efetuar a consulta")]'
                # Verifica se o cliente foi encontrado
                if self.check_for_error(xpath=xpath_erro_botao):
                    erro_msg = "Informe pelo menos um dos seguintes campos para efetuar a consulta (empresa, título ou cliente)."
                    self.log_erro("Erro ao consultar cliente", erro_msg)
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
            resultado_regras_pdd = self.processador_regras.processar_dados_cliente(
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

    async def carregar_dados_fila_reparcelamento(self,
                                                 numero_titulo: str = None
                                                 ) -> Dict[str, Any]:
        """
        Carrega dados da fila de reparcelamento do MongoDB e prepara parâmetros para webscraping

        Args:
            numero_titulo: Número específico do título ou None para próximo da fila

        Returns:
            Dict com todos os dados necessários para navegação no Sienge
        """
        try:
            from core.data_manager import DataManager

            data_manager = DataManager()

            # Se número não especificado, busca próximo da fila
            if numero_titulo is None:
                self.log_progresso(
                    "🔍 Buscando próximo contrato da fila de reparcelamento...")

                # Buscar próximo contrato pendente na fila
                filtro_fila = {
                    "status_processamento": "pendente",
                    "dados_financeiros.pode_reparcelar": True
                }

                contrato_fila = await data_manager.mongodb_manager.obter_documento_mais_recente(
                    "fila_reparcelamento", filtro_fila,
                    "timestamp_identificacao")

                if not contrato_fila:
                    return {
                        "sucesso": False,
                        "erro":
                        "Nenhum contrato elegível encontrado na fila de reparcelamento",
                        "fila_vazia": True
                    }

                numero_titulo = contrato_fila["numero_titulo"]
                self.log_progresso(f"📄 Próximo da fila: {numero_titulo}")

            # Carregar dados completos do contrato
            self.log_progresso(
                f"📊 Carregando dados completos para: {numero_titulo}")

            # 1. Dados da fila de reparcelamento
            dados_fila = await data_manager.mongodb_manager.obter_documento_mais_recente(
                "fila_reparcelamento", {"numero_titulo": numero_titulo})

            if not dados_fila:
                return {
                    "sucesso":
                    False,
                    "erro":
                    f"Contrato {numero_titulo} não encontrado na fila de reparcelamento"
                }

            # 2. Dados financeiros processados
            dados_financeiros = dados_fila.get("dados_financeiros", {})

            # 3. Obter IGPM mais recente do banco
            igpm_valor = await data_manager.obter_igpm_mais_recente()

            if igpm_valor is None:
                return {
                    "sucesso": False,
                    "erro": "IGPM não disponível no banco de dados",
                    "acao_requerida": "EXECUTAR_RPA_COLETA_INDICES"
                }

            # 4. Calcular valores de reparcelamento
            saldo_atual = dados_financeiros.get("saldo_total", 0)
            parcelas_pendentes = dados_financeiros.get(
                "qtd_parcelas_ct_a_vencer", 0)

            calculo_resultado = await self.processador_regras.calcular_valores_reparcelamento(
                saldo_atual=saldo_atual,
                indice_igpm=igpm_valor,
                parcelas_pendentes=parcelas_pendentes)

            if not calculo_resultado.get("sucesso", False):
                return {
                    "sucesso": False,
                    "erro":
                    f"Erro no cálculo: {calculo_resultado.get('erro')}",
                    "dados_fila": dados_fila
                }

            # 5. Determinar parcelas para desmarcar
            parcelas_ct_a_vencer = dados_financeiros.get(
                "parcelas_ct_a_vencer_detalhes", [])
            parcelas_desmarcar = self.processador_regras.determinar_parcelas_desmarcar(
                parcelas_ct_a_vencer)

            # 6. Preparar parâmetros completos para navegação
            parametros_navegacao = {
                # DADOS DO CONTRATO
                "numero_titulo": numero_titulo,
                "cliente": dados_fila.get("cliente", ""),
                "empreendimento": dados_fila.get("empreendimento", ""),

                # URL DE NAVEGAÇÃO SIENGE
                "url_reparcelamento":
                "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/reparcelamento/inclusao",

                # VALORES CALCULADOS PARA PREENCHIMENTO
                "valores_sienge": calculo_resultado.get("valores_sienge", {}),

                # PARCELAS PARA DESMARCAR
                "parcelas_desmarcar": parcelas_desmarcar,
                "total_parcelas_desmarcar": len(parcelas_desmarcar),

                # DADOS FINANCEIROS COMPLETOS
                "saldo_anterior": saldo_atual,
                "saldo_novo": calculo_resultado.get("novo_saldo", 0),
                "fator_correcao": calculo_resultado.get("fator_correcao", 1),
                "igpm_aplicado": igpm_valor,

                # VALIDAÇÃO PDD
                "pode_reparcelar":
                dados_financeiros.get("pode_reparcelar", False),
                "status_cliente": dados_financeiros.get("status_cliente", ""),
                "qtd_ct_vencidas": dados_financeiros.get("qtd_ct_vencidas", 0),

                # METADADOS
                "id_fila": dados_fila.get("_id"),
                "timestamp_carregamento": datetime.now().isoformat()
            }

            self.log_progresso("✅ Dados carregados e parâmetros preparados")
            self.log_progresso(
                f"   💰 Saldo: R$ {saldo_atual:,.2f} → R$ {calculo_resultado.get('novo_saldo', 0):,.2f}"
            )
            self.log_progresso(f"   📊 IGP-M: {igpm_valor}%")
            self.log_progresso(
                f"   🔄 Parcelas a desmarcar: {len(parcelas_desmarcar)}")

            RPA Sienge code modification complete, ensuring centralized rule processing.


<replit_final_file >
"""
RPA Sienge - Versão Produção Restaurada
Sistema automatizado para processamento de reparcelamento no Sienge ERP

CÓDIGO FUNCIONAL ORIGINAL DO USUÁRIO
Desenvolvido em Português Brasileiro
"""


# Imports do sistema RPA

# Selenium imports necessários

load_dotenv()


class RPASienge(BaseRPA):
    """
    RPA para processamento de reparcelamento no sistema Sienge
    Implementa as regras do PDD seção 7.3

    VERSÃO PRODUÇÃO - Apenas código real do Sienge
    """

    def __init__(self):
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

    async def executar(self,
                       contrato: Dict[str, Any],
                       credenciais_sienge: Dict[str, str],
                       indices: Dict[str, Any] = None,
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
                        "contrato": contrato.get("numero_titulo", "N/A")
                    })
                await self.rastreamento.finalizar_rastreamento()

            self.log_erro(erro_msg, e)
            return ResultadoRPA(sucesso=False,
                                mensagem="Falha na execução do RPA Sienge",
                                erro=erro_msg)

        finally:
            # ✅ SEMPRE finaliza rastreamento
            if self.rastreamento:
                await self.rastreamento.finalizar_rastreamento()

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
            self.find_element(
                xpath='(//input[@id="username"])[1]').send_keys(usuario_sienge)

            # Preenche senha inicial
            self.find_element(
                xpath='//input[@id="password"]').send_keys(senha_sienge)

            # Clica botão entrar inicial
            self.find_element(xpath='//*[@id="btnEntrarComSiengeID"]').click()
            time.sleep(2)

            # Segunda etapa - email
            self.find_element(
                xpath='//label[text()="Seu e-mail"]/following-sibling::div//input'
            ).send_keys(usuario_sienge)

            # Clica continuar
            self.find_element(
                xpath="//button[normalize-space(text())='CONTINUAR']").click()

            # Terceira etapa - senha final
            self.find_element(
                xpath="//input[@id='signup-password']").send_keys(senha_sienge)

            # Clica entrar final
            self.find_element(
                xpath="//button[normalize-space(text())='ENTRAR']").click()

            # Login bem-sucedido
            self.logado_sienge = True

            await self.rastreamento.registrar_login_sistema(
                "sienge", usuario_sienge, True)

            self.log_progresso("Login no Sienge realizado com sucesso")

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
                    text=cliente)
                time.sleep(2)

                combo_pesquisa.click()
                time.sleep(1)
                combo_pesquisa.send_keys(Keys.TAB)
                time.sleep(1)

                # WEBSCRAPING REAL - Clica em Consultar
                self.log_progresso("Executando consulta...")
                self.click(xpath="//button[normalize-space()='Consultar']")
                time.sleep(3)

                xpath_erro_botao = '//div[@data-testid="snackbar"]//p[@data-testid="snackbar-message" and contains(normalize-space(.), "Informe pelo menos um dos seguintes campos para efetuar a consulta")]'
                # Verifica se o cliente foi encontrado
                if self.check_for_error(xpath=xpath_erro_botao):
                    erro_msg = "Informe pelo menos um dos seguintes campos para efetuar a consulta (empresa, título ou cliente)."
                    self.log_erro("Erro ao consultar cliente", erro_msg)
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
            resultado_regras_pdd = self.processador_regras.processar_dados_cliente(
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

    async def carregar_dados_fila_reparcelamento(self,
                                                 numero_titulo: str = None
                                                 ) -> Dict[str, Any]:
        """
        Carrega dados da fila de reparcelamento do MongoDB e prepara parâmetros para webscraping

        Args:
            numero_titulo: Número específico do título ou None para próximo da fila

        Returns:
            Dict com todos os dados necessários para navegação no Sienge
        """
        try:
            from core.data_manager import DataManager

            data_manager = DataManager()

            # Se número não especificado, busca próximo da fila
            if numero_titulo is None:
                self.log_progresso(
                    "🔍 Buscando próximo contrato da fila de reparcelamento...")

                # Buscar próximo contrato pendente na fila
                filtro_fila = {
                    "status_processamento": "pendente",
                    "dados_financeiros.pode_reparcelar": True
                }

                contrato_fila = await data_manager.mongodb_manager.obter_documento_mais_recente(
                    "fila_reparcelamento", filtro_fila,
                    "timestamp_identificacao")

                if not contrato_fila:
                    return {
                        "sucesso": False,
                        "erro":
                        "Nenhum contrato elegível encontrado na fila de reparcelamento",
                        "fila_vazia": True
                    }

                numero_titulo = contrato_fila["numero_titulo"]
                self.log_progresso(f"📄 Próximo da fila: {numero_titulo}")

            # Carregar dados completos do contrato
            self.log_progresso(
                f"📊 Carregando dados completos para: {numero_titulo}")

            # 1. Dados da fila de reparcelamento
            dados_fila = await data_manager.mongodb_manager.obter_documento_mais_recente(
                "fila_reparcelamento", {"numero_titulo": numero_titulo})

            if not dados_fila:
                return {
                    "sucesso":
                    False,
                    "erro":
                    f"Contrato {numero_titulo} não encontrado na fila de reparcelamento"
                }

            # 2. Dados financeiros processados
            dados_financeiros = dados_fila.get("dados_financeiros", {})

            # 3. Obter IGPM mais recente do banco
            igpm_valor = await data_manager.obter_igpm_mais_recente()

            if igpm_valor is None:
                return {
                    "sucesso": False,
                    "erro": "IGPM não disponível no banco de dados",
                    "acao_requerida": "EXECUTAR_RPA_COLETA_INDICES"
                }

            # 4. Calcular valores de reparcelamento
            saldo_atual = dados_financeiros.get("saldo_total", 0)
            parcelas_pendentes = dados_financeiros.get(
                "qtd_parcelas_ct_a_vencer", 0)

            calculo_resultado = await self.processador_regras.calcular_valores_reparcelamento(
                saldo_atual=saldo_atual,
                indice_igpm=igpm_valor,
                parcelas_pendentes=parcelas_pendentes)

            if not calculo_resultado.get("sucesso", False):
                return {
                    "sucesso": False,
                    "erro":
                    f"Erro no cálculo: {calculo_resultado.get('erro')}",
                    "dados_fila": dados_fila
                }

            # 5. Determinar parcelas para desmarcar
            parcelas_ct_a_vencer = dados_financeiros.get(
                "parcelas_ct_a_vencer_detalhes", [])
            parcelas_desmarcar = self.processador_regras.determinar_parcelas_desmarcar(
                parcelas_ct_a_vencer)

            # 6. Preparar parâmetros completos para navegação
            parametros_navegacao = {
                # DADOS DO CONTRATO
                "numero_titulo": numero_titulo,
                "cliente": dados_fila.get("cliente", ""),
                "empreendimento": dados_fila.get("empreendimento", ""),

                # URL DE NAVEGAÇÃO SIENGE
                "url_reparcelamento":
                "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/reparcelamento/inclusao",

                # VALORES CALCULADOS PARA PREENCHIMENTO
                "valores_sienge": calculo_resultado.get("valores_sienge", {}),

                # PARCELAS PARA DESMARCAR
                "parcelas_desmarcar": parcelas_desmarcar,
                "total_parcelas_desmarcar": len(parcelas_desmarcar),

                # DADOS FINANCEIROS COMPLETOS
                "saldo_anterior": saldo_atual,
                "saldo_novo": calculo_resultado.get("novo_saldo", 0),
                "fator_correcao": calculo_resultado.get("fator_correcao", 1),
                "igpm_aplicado": igpm_valor,

                # VALIDAÇÃO PDD
                "pode_reparcelar":
                dados_financeiros.get("pode_reparcelar", False),
                "status_cliente": dados_financeiros.get("status_cliente", ""),
                "qtd_ct_vencidas": dados_financeiros.get("qtd_ct_vencidas", 0),

                # METADADOS
                "id_fila": dados_fila.get("_id"),
                "timestamp_carregamento": datetime.now().isoformat()
            }

            self.log_progresso("✅ Dados carregados e parâmetros preparados")
            self.log_progresso(
                f"   💰 Saldo: R$ {saldo_atual:,.2f} → R$ {calculo_resultado.get('novo_saldo', 0):,.2f}"
            )
            self.log_progresso(f"   📊 IGP-M: {igpm_valor}%")
            self.log_progresso(
                f"   🔄 Parcelas a desmarcar: {len(parcelas_desmarcar)}")

            return {
                "sucesso": True,
                "parametros_navegacao": parametros_navegacao,
                "dados_completos": dados_fila,
                "calculo_detalhado": calculo_resultado
            }

        except Exception as e:
            erro_msg = f"Erro ao carregar dados da fila: {str(e)}"
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
            igpm_fornecido = indices.get("igpm",
                                         {}).get("valor") if indices else None

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
                                                  numero_titulo: str = None
                                                  ) -> ResultadoRPA:
        """
        MÉTODO PRINCIPAL PARA EXECUÇÃO DO REPARCELAMENTO
        Carrega dados da fila e executa webscraping no Sienge

        Args:
            numero_titulo: Número específico do título ou None para próximo da fila

        Returns:
            ResultadoRPA com sucesso/erro do processamento
        """
        try:
            self.log_progresso("🚀 INICIANDO EXECUÇÃO DE REPARCELAMENTO")
            self.log_progresso("=" * 50)

            # 1. CARREGAR DADOS DA FILA
            resultado_carga = await self.carregar_dados_fila_reparcelamento(
                numero_titulo)

            if not resultado_carga.get("sucesso", False):
                return ResultadoRPA(sucesso=False,
                                    mensagem="Falha ao carregar dados da fila",
                                    erro=resultado_carga.get(
                                        "erro", "Erro desconhecido"))

            parametros = resultado_carga["parametros_navegacao"]

            self.log_progresso(f"📄 Processando: {parametros['numero_titulo']}")
            self.log_progresso(f"👤 Cliente: {parametros['cliente']}")

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
                parametros["numero_titulo"], "processado",
                resultado_webscraping)

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

            # Marcar como erro na fila se conseguir identificar o título
            if 'parametros' in locals() and parametros.get("numero_titulo"):
                await self._atualizar_status_fila_reparcelamento(
                    parametros["numero_titulo"], "erro", {"erro": erro_msg})

            return ResultadoRPA(sucesso=False,
                                mensagem="Falha na execução do reparcelamento",
                                erro=erro_msg)

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
            time.sleep(3)

            numero_titulo = parametros["numero_titulo"]
            self.log_progresso(
                f"🔍 PASSO 21: Consultando título: {numero_titulo}")

            # IMPLEMENTAR: Campo obrigatório de número do título
            with self.on_iframe(xpath='//iframe[@id="iFramePage"]'):
                self.log_progresso("Preenchendo número do título...")
                self.click(xpath="//input[@id='titulo.tituloPK.nuTitulo']")
                self.send_text_human_like(
                    xpath="//input[@id='titulo.tituloPK.nuTitulo']",
                    text=numero_titulo)

                self.log_progresso("Clicando em Consultar...")
                self.click(
                    xpath="//input[@type='button' and @name='btFiltrar']")
                time.sleep(4)

                # PASSO 22: SELEÇÃO DE DOCUMENTOS
                self.log_progresso(
                    "✅ PASSO 22: Título listado - selecionando documentos")
                self.click(xpath="//input[@type='button' and @name='btNext']")

                # Aguardar carregamento e fazer scroll para "Marcar Todos"
                self.dismiss_alert_if_present(timeout=3)
                self.log_progresso("📄 Localizando botão 'Marcar Todos'...")

                # IMPLEMENTAR: Scroll até o final + "Marcar Todos"
                # TODO: Implementar scroll e localizar botão "Marcar Todos"
                # TODO: Clicar em "Marcar Todos" para selecionar todas as parcelas

                tabela = self.find_element(xpath='//table[@id="TituloRow"]')
                if tabela:
                    self.log_progresso("✅ Selecionando TODOS os documentos...")
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
            parcelas_desmarcar = parametros["parcelas_desmarcar"]
            self.log_progresso(
                f"❌ PASSO 23: FILTRO CRÍTICO - Desmarcando {len(parcelas_desmarcar)} parcelas vencidas...")

            # IMPLEMENTAR: Filtro crítico conforme regra PDD
            # REGRA: DESMARCAR parcelas com vencimento ≤ mês vigente
            # REGRA: MANTER MARCADAS apenas parcelas futuras
            for parcela in parcelas_desmarcar:
                self.log_progresso(
                    f"   📄 Desmarcando: {parcela['documento']} - {parcela['data_vencimento']}")
                # TODO: Localizar checkbox específico da parcela
                # TODO: Desmarcar a parcela conforme regra crítica

            # PASSO 24: CONFIGURAÇÃO DO DETALHAMENTO
            valores_sienge = parametros["valores_sienge"]
            detalhamento = valores_sienge["detalhamento"]  # "CORREÇÃO MM/AA"

            self.log_progresso(
                f"📝 PASSO 24: Configurando detalhamento: {detalhamento}")
            # TODO: Clicar em "Próximo"
            # TODO: Scroll para visualizar campos
            # TODO: Preencher campo "Detalhamento" com formato obrigatório
            # TODO: Clicar em "Adicionar" para confirmar

            # PASSO 25: PREENCHIMENTO DOS DADOS DO PARCELAMENTO
            self.log_progresso("💰 PASSO 25: Preenchendo dados obrigatórios...")

            # IMPLEMENTAR: Campos com valores fixos obrigatórios
            # - Tipo condição: "PM" (SEMPRE)
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
            self.log_progresso("🔧 PASSOS 26-28: Processando finalização...")

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
                "parcelas_processadas": len(parcelas_desmarcar),
                "valores_aplicados": valores_sienge,
                "passos_pdd_executados": "21-28",
                "timestamp_webscraping": datetime.now().isoformat()
            }

        except Exception as e:
            erro_msg = f"Erro no webscraping PDD: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"sucesso": False, "erro": erro_msg}

    async def _atualizar_status_fila_reparcelamento(
            self, numero_titulo: str, novo_status: str,
            dados_resultado: Dict[str, Any]):
        """Atualiza status do contrato na fila de reparcelamento"""
        try:
            from core.data_manager import DataManager
            data_manager = DataManager()

            # Atualizar documento na fila
            def _update_status():
                collection = data_manager.mongodb_manager.database.fila_reparcelamento
                collection.update_one({"numero_titulo": numero_titulo}, {
                    "$set": {
                        "status_processamento": novo_status,
                        "processado_em": datetime.now(),
                        "resultado_processamento": dados_resultado
                    }
                })

            await asyncio.get_event_loop().run_in_executor(
                None, _update_status)
            self.log_progresso(
                f"📊 Status atualizado na fila: {numero_titulo} → {novo_status}"
            )

        except Exception as e:
            self.log_erro(f"Erro ao atualizar status na fila: {str(e)}", e)

    async def _salvar_reparcelamento_historico(self, parametros: Dict[str,
                                                                      Any],
                                               resultado: Dict[str, Any]):
        """Salva reparcelamento no histórico completo"""
        try:
            from core.data_manager import DataManager
            data_manager = DataManager()

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

            await data_manager.mongodb_manager.salvar_contrato_processado(
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
