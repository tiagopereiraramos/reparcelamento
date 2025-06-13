# RPA Sienge code updated with TODOs for webscraping implementation.
"""
RPA Sienge - Versão Produção
Terceiro RPA do sistema - Processa reparcelamento no ERP Sienge

Desenvolvido em Português Brasileiro
Baseado no PDD seção 7.3 - Processamento no sistema Sienge

VERSÃO PRODUÇÃO - Apenas código para ambiente real
"""

from platformdirs import user_downloads_dir
from core.base_rpa import BaseRPA, ResultadoRPA
from core.notificacoes_simples import notificar_sucesso, notificar_erro
from trio import sleep
from selenium.webdriver.common.keys import Keys
import os
import json
import time
import shutil
from typing import Dict, Any, List
from datetime import datetime, date, timedelta
from pathlib import Path
import asyncio
import pandas as pd
import traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


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

    def _configurar_credenciais(self, credenciais: Dict[str, str]):
        """Configura credenciais do Sienge"""
        self.credenciais_sienge = {
            "url": credenciais.get("url", ""),
            "usuario": credenciais.get("usuario", ""),
            "senha": credenciais.get("senha", ""),
            "empresa": credenciais.get("empresa", "")
        }

    async def executar(
        self,
        contrato: Dict[str, Any],
        credenciais_sienge: Dict[str, str],
        indices: Dict[str, Any] = None
    ) -> ResultadoRPA:
        """
        Executa processamento completo do RPA Sienge

        Args:
            contrato: Dados do contrato (número_titulo, cliente, etc.)
            credenciais_sienge: Credenciais de acesso ao Sienge
            indices: Índices econômicos (IPCA/IGPM)
        """
        try:
            self.log_progresso("🚀 INICIANDO RPA SIENGE")
            self.log_progresso(
                f"   📋 Contrato: {contrato.get('numero_titulo', '')}")
            self.log_progresso(f"   👤 Cliente: {contrato.get('cliente', '')}")

            if not contrato or not credenciais_sienge:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem="Dados do contrato ou credenciais Sienge não fornecidos",
                    erro="Parâmetros 'contrato' e 'credenciais_sienge' são obrigatórios"
                )

            # Configura credenciais
            self._configurar_credenciais(credenciais_sienge)

            # Faz login no Sienge
            await self._fazer_login_sienge()

            # Consulta relatórios financeiros do cliente
            self.log_progresso(
                f"Consultando relatórios do cliente: {contrato.get('cliente', '')}")
            dados_financeiros = await self._consultar_relatorios_financeiros(contrato)

            # Valida se contrato pode ser reparcelado
            pode_reparcelar = await self._validar_contrato_reparcelamento(dados_financeiros)

            if not pode_reparcelar["pode_reparcelar"]:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem=f"Contrato não pode ser reparcelado: {pode_reparcelar['motivo']}",
                    dados={
                        "contrato": contrato,
                        "validacao": pode_reparcelar,
                        "dados_financeiros": dados_financeiros
                    }
                )

            # Processa reparcelamento
            self.log_progresso("Processando reparcelamento no Sienge")
            indices = indices or {}
            resultado_reparcelamento = await self._processar_reparcelamento(contrato, indices, dados_financeiros)

            # Gera carnê se processamento foi bem-sucedido
            carne_gerado = None
            if resultado_reparcelamento["sucesso"]:
                self.log_progresso("Gerando carnê atualizado")
                carne_gerado = await self._gerar_carne_sienge(contrato)

            # Monta resultado final
            resultado_dados = {
                "contrato_processado": contrato,
                "dados_financeiros": dados_financeiros,
                "reparcelamento": resultado_reparcelamento,
                "carne_gerado": carne_gerado,
                "timestamp_processamento": datetime.now().isoformat()
            }

            return ResultadoRPA(
                sucesso=resultado_reparcelamento["sucesso"],
                mensagem=f"Reparcelamento processado - Cliente: {contrato.get('cliente', '')}",
                dados=resultado_dados
            )

        except Exception as e:
            erro_msg = f"Erro na execução do RPA Sienge: {str(e)}"
            self.log_erro(erro_msg, e)
            return ResultadoRPA(
                sucesso=False,
                mensagem="Falha na execução do RPA Sienge",
                erro=erro_msg
            )

    async def finalizar(self):
        """Finaliza RPA e limpa recursos"""
        try:
            if hasattr(self, 'browser') and self.browser:
                await self.browser.quit()
            self.log_progresso("🏁 RPA Sienge finalizado")
        except Exception as e:
            self.log_erro("Erro ao finalizar RPA", e)

    # =================தான்யா
    # MÉTODOS SIENGE REAL
    # ========================

    async def _fazer_login_sienge(self):
        """
        Faz login no sistema Sienge conforme PDD seção 7.3

        🎯 WEBSCRAPING FUNCIONAL IMPLEMENTADO:
        Sequência exata que estava funcionando antes
        """
        try:
            url_sienge = self.credenciais_sienge.get("url", "")
            usuario_sienge = self.credenciais_sienge.get("usuario", "")
            senha_sienge = self.credenciais_sienge.get("senha", "")

            self.log_progresso(f"Acessando sistema Sienge: {url_sienge}")

            # Acessa página de login
            if not url_sienge:
                raise ValueError(
                    "URL do Sienge não foi configurada corretamente.")

            self.browser.get_page(url_sienge)
            time.sleep(3)

            # WEBSCRAPING REAL - Sequência de login conforme PDD:
            # 1. Informar usuário (tc@trajetoriaconsultoria.com.br)
            # 2. Clicar em Continuar
            # 3. Informar senha
            # 4. Clicar em Entrar
            # 5. Fechar caixas de mensagem

            # Preenche usuário inicial
            self.browser.find_element(
                xpath='(//input[@id="username"])[1]').send_keys(usuario_sienge)

            # Preenche senha inicial
            self.browser.find_element(
                xpath='//input[@id="password"]').send_keys(senha_sienge)

            # Clica botão entrar inicial
            self.browser.find_element(
                xpath='//*[@id="btnEntrarComSiengeID"]').click()
            time.sleep(2)

            # Segunda etapa - email
            self.browser.find_element(
                xpath='//label[text()="Seu e-mail"]/following-sibling::div//input').send_keys(usuario_sienge)

            # Clica continuar
            self.browser.find_element(
                xpath="//button[normalize-space(text())='CONTINUAR']").click()

            # Terceira etapa - senha final
            self.browser.find_element(
                xpath="//input[@id='signup-password']").send_keys(senha_sienge)

            # Clica entrar final
            self.browser.find_element(
                xpath="//button[normalize-space(text())='ENTRAR']").click()

            # Login bem-sucedido
            self.logado_sienge = True
            self.log_progresso("✅ Login no Sienge realizado com sucesso")

        except Exception as e:
            raise Exception(f"Falha no login Sienge: {str(e)}")

    async def _consultar_relatorios_financeiros(self, contrato: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consulta relatórios financeiros no Sienge conforme PDD seção 7.3.1

        🎯 WEBSCRAPING IMPLEMENTADO:
        1. Navega para relatório Saldo Devedor Presente
        2. Pesquisa por cliente específico  
        3. Executa consulta e gera relatório
        4. Exporta em formato Excel
        5. TODO: Processar planilha baixada (próxima etapa)

        Args:
            contrato: Dados do contrato

        Returns:
            Dados financeiros extraídos do Sienge
        """
        try:
            cliente = contrato.get("cliente", "")
            numero_titulo = contrato.get("numero_titulo", "")

            self.log_progresso(
                f"📊 Consultando saldo devedor presente para: {cliente}")
            self.log_progresso(f"   📋 Título: {numero_titulo}")

            # WEBSCRAPING REAL - Navegação conforme PDD seção 7.3.1
            url_relatorio = "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/relatorios/saldo-devedor"
            self.log_progresso(f"🧭 Navegando para: {url_relatorio}")
            self.browser.get_page(url_relatorio)
            time.sleep(3)

            # WEBSCRAPING REAL - Busca e preenche campo de pesquisa do cliente
            self.log_progresso("🔍 Pesquisando cliente...")
            combo_pesquisa = self.browser.find_element(
                xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']")

            if combo_pesquisa:
                combo_pesquisa.click()
                time.sleep(3)

                # Preenche nome do cliente
                self.browser.send_text_human_like(
                    xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']",
                    text=cliente
                )

                combo_pesquisa.click()
                time.sleep(1)
                combo_pesquisa.send_keys(Keys.TAB)
                time.sleep(1)

                # WEBSCRAPING REAL - Clica em Consultar
                self.log_progresso("📋 Executando consulta...")
                self.browser.click(
                    xpath="//button[normalize-space()='Consultar']")
                time.sleep(3)

                # WEBSCRAPING REAL - Gera relatório
                self.log_progresso("📊 Gerando relatório...")
                self.browser.click(
                    xpath="//button[@type='button' and contains(., 'Gerar Relatório')]")
                time.sleep(2)

                # WEBSCRAPING REAL - Seleciona formato Excel
                self.log_progresso("📁 Selecionando formato Excel...")
                self.browser.click(xpath='//div[@id="mui-144"]')
                time.sleep(1)

                self.browser.click(
                    xpath='//li[@role="option" and @data-value="excel" and text()="EXCEL"]')
                time.sleep(1)

                # WEBSCRAPING REAL - Exporta relatório
                self.log_progresso("💾 Exportando relatório...")
                self.browser.click(
                    xpath="//button[@type='button' and normalize-space()='Exportar']")
                time.sleep(5)

                # PROCESSAMENTO DA PLANILHA BAIXADA
                self.log_progresso("📋 Processando planilha baixada...")
                dados_planilha = await self._processar_planilha_baixada(cliente, numero_titulo)

            # DADOS PROCESSADOS DA PLANILHA REAL
            if dados_planilha and dados_planilha.get("sucesso"):
                dados_financeiros = dados_planilha
            else:
                # Fallback com dados vazios se planilha não processada
                dados_financeiros = {
                    "cliente": cliente,
                    "numero_titulo": numero_titulo,
                    "saldo_total": 0.0,
                    "parcelas_pendentes": 0,
                    "parcelas_ct": [],
                    "parcelas_rec_fat": [],
                    "status_cliente": "erro_processamento",
                    "relatorio_exportado": False,
                    "dados_brutos": None,
                    "sucesso": False,
                    "erro": dados_planilha.get("erro", "Falha no processamento da planilha")
                }

            self.log_progresso(
                "✅ Webscraping concluído - Aguardando processamento da planilha")
            return dados_financeiros

        except Exception as e:
            erro_msg = f"Erro na consulta de relatórios: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"erro": erro_msg, "sucesso": False}

    async def _validar_contrato_reparcelamento(self, dados_financeiros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida se contrato pode ser reparcelado conforme regras do PDD seção 7.3.2

        REGRA PRINCIPAL:
        - Cliente com 3 ou mais parcelas CT vencidas = INADIMPLENTE (não pode reparcelar)
        - Cliente com menos de 3 parcelas CT vencidas = PODE reparcelar
        """
        try:
            if not dados_financeiros.get("sucesso", False):
                return {
                    "pode_reparcelar": False,
                    "motivo": "Erro na consulta de dados financeiros",
                    "status": "erro"
                }

            # Filtra apenas parcelas CT CONFORME PDD
            parcelas_ct = dados_financeiros.get("parcelas_ct", [])

            # Conta parcelas CT vencidas CONFORME PDD - status exato "Quitada"
            parcelas_ct_vencidas = []
            hoje = date.today()

            for parcela in parcelas_ct:
                data_vencimento = parcela.get("data_vencimento")
                status = parcela.get("status_parcela", "")

                # Converte data se necessário
                if isinstance(data_vencimento, str):
                    try:
                        data_vencimento = datetime.strptime(
                            data_vencimento, "%Y-%m-%d").date()
                    except:
                        continue

                # REGRA PDD: Verifica se é CT vencida e NÃO está "Quitada" (status exato)
                if (data_vencimento < hoje and
                        status != "Quitada"):  # Status exato conforme PDD
                    parcelas_ct_vencidas.append(parcela)

            qtd_ct_vencidas = len(parcelas_ct_vencidas)
            cliente = dados_financeiros.get("cliente", "")

            # Regra principal do PDD
            if qtd_ct_vencidas >= 3:
                motivo = f"Cliente inadimplente - {qtd_ct_vencidas} parcelas CT vencidas (>= 3)"
                pode_reparcelar = False
                status = "inadimplente"
            else:
                motivo = f"Cliente apto para reparcelamento - {qtd_ct_vencidas} parcelas CT vencidas (< 3)"
                pode_reparcelar = True
                status = "apto"

            # Informações adicionais
            parcelas_rec_fat = dados_financeiros.get("parcelas_rec_fat", [])
            if len(parcelas_rec_fat) > 0 and pode_reparcelar:
                motivo += f" + {len(parcelas_rec_fat)} pendências REC/FAT (não impedem)"

            resultado_validacao = {
                "pode_reparcelar": pode_reparcelar,
                "motivo": motivo,
                "status": status,
                "detalhes": {
                    "qtd_ct_vencidas": qtd_ct_vencidas,
                    "qtd_rec_fat": len(parcelas_rec_fat),
                    "cliente": cliente,
                    "saldo_total": dados_financeiros.get("saldo_total", 0)
                }
            }

            if pode_reparcelar:
                self.log_progresso("✅ Cliente aprovado para reparcelamento")
            else:
                self.log_progresso(f"❌ Cliente reprovado: {motivo}")

            return resultado_validacao

        except Exception as e:
            erro_msg = f"Erro na validação: {str(e)}"
            self.log_erro("Falha na validação de reparcelamento", e)
            return {
                "pode_reparcelar": False,
                "motivo": erro_msg,
                "status": "erro",
                "detalhes": {"erro_validacao": erro_msg}
            }

    async def _processar_reparcelamento(
        self,
        contrato: Dict[str, Any],
        indices: Dict[str, Any],
        dados_financeiros: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Processa reparcelamento no Sienge conforme PDD seção 7.3.3

        REGRAS RIGOROSAS PDD:
        1. Navegar para Financeiro > Contas a receber > Reparcelamento > Inclusão
        2. Consultar título pelo número
        3. Selecionar TODOS os documentos
        4. DESMARCAR parcelas vencidas até mês atual (conforme PDD)
        5. Configurar detalhes: PM, IGP-M, Fixo 8%
        6. Confirmar e salvar
        """
        try:
            numero_titulo = contrato.get("numero_titulo", "")
            cliente = contrato.get("cliente", "")

            self.log_progresso(f"🔄 PROCESSANDO REPARCELAMENTO SIENGE")
            self.log_progresso(f"   📋 Título: {numero_titulo}")
            self.log_progresso(f"   👤 Cliente: {cliente}")
            self.log_progresso(
                f"   💰 Saldo atual: R$ {dados_financeiros.get('saldo_total', 0):,.2f}")

            # Etapa 1: Navegar para Reparcelamento > Inclusão
            self.log_progresso(
                "🧭 Etapa 1: Navegando para Reparcelamento > Inclusão")
            await self._navegar_reparcelamento_inclusao()

            # Etapa 2: Consultar título
            self.log_progresso(
                f"🔍 Etapa 2: Consultando título {numero_titulo}")
            await self._consultar_titulo_reparcelamento(numero_titulo)

            # Etapa 3: Selecionar documentos
            self.log_progresso(
                "📋 Etapa 3: Selecionando documentos para reparcelamento")
            await self._selecionar_documentos_reparcelamento(dados_financeiros)

            # Etapa 4: Configurar detalhes
            self.log_progresso(
                "⚙️ Etapa 4: Configurando detalhes do reparcelamento")
            detalhes = await self._configurar_detalhes_reparcelamento(contrato, indices, dados_financeiros)

            # Etapa 5: Confirmar e salvar
            self.log_progresso(
                "💾 Etapa 5: Confirmando e salvando reparcelamento")
            novo_titulo = await self._confirmar_salvar_reparcelamento()

            # Resultado final
            resultado = {
                "sucesso": True,
                "numero_titulo_original": numero_titulo,
                "novo_titulo_gerado": novo_titulo,
                "detalhes_reparcelamento": detalhes,
                "timestamp_processamento": datetime.now().isoformat(),
                "tipo_processamento": "real_sienge"
            }

            self.log_progresso("✅ Reparcelamento processado com sucesso!")
            return resultado

        except Exception as e:
            erro_msg = f"Erro no processamento de reparcelamento: {str(e)}"
            self.log_erro(erro_msg, e)
            return {
                "sucesso": False,
                "erro": erro_msg,
                "numero_titulo": numero_titulo,
                "tipo_processamento": "erro"
            }

    async def _gerar_carne_sienge(self, contrato: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera carnê no Sienge conforme PDD seção 7.3.4
        Financeiro > Contas a Receber > Cobrança Escritural > Geração de Arquivos de remessa
        """
        try:
            self.log_progresso("🎯 Gerando carnê atualizado...")

            # Navegar para geração de carnê
            await self._navegar_geracao_carne()

            # Configurar parâmetros do carnê
            await self._configurar_parametros_carne(contrato)

            # Gerar arquivo
            nome_arquivo = await self._executar_geracao_carne(contrato)

            return {
                "sucesso": True,
                "arquivo_gerado": nome_arquivo,
                "tipo": "real_sienge",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.log_erro("Erro na geração de carnê", e)
            return {"sucesso": False, "erro": str(e)}

    # ========================
    # MÉTODOS AUXILIARES SIENGE
    # ========================

    async def _navegar_menu_financeiro(self):
        """
        WEBSCRAPING - Navega para menu Financeiro

        🎯 IMPLEMENTAÇÃO WEBSCRAPING:
        INPUT: Nenhum (apenas usa self.browser já logado)
        AÇÃO: Clica no menu "Financeiro" principal do Sienge
        OUTPUT: Deve deixar navegador na página do menu Financeiro
        ERRO: Raise Exception se menu não encontrado

        📍 XPATH ESPERADOS:
        - Menu principal: //a[contains(text(), 'Financeiro')]
        - Submenu: //span[contains(text(), 'Financeiro')]
        """
        # TODO: IMPLEMENTAR NAVEGAÇÃO REAL
        # 1. Localizar menu "Financeiro"
        # 2. Clicar no menu
        # 3. Aguardar carregamento da página
        # 4. Validar que está na página correta
        try:
            self.log_progresso("🧭 TODO: Navegando para menu Financeiro...")
            # IMPLEMENTAR WEBSCRAPING AQUI
            pass

        except Exception as e:
            self.log_erro("Erro ao navegar para menu Financeiro", e)
            raise

    async def _acessar_relatorio_saldo_devedor(self):
        """
        WEBSCRAPING - Acessa relatório Saldo Devedor Presente

        🎯 IMPLEMENTAÇÃO WEBSCRAPING:
        INPUT: Navegador já deve estar no menu Financeiro
        NAVEGAÇÃO OBRIGATÓRIA (conforme PDD 7.3.1):
        1. Financeiro > Contas a Receber
        2. Contas a Receber > Relatórios  
        3. Relatórios > Saldo Devedor Presente
        OUTPUT: Deve deixar navegador na tela do relatório
        ERRO: Raise Exception se qualquer link não encontrado

        📍 XPATH ESPERADOS SIENGE:
        - Contas a Receber: //a[contains(text(), 'Contas a Receber')]
        - Relatórios: //a[contains(text(), 'Relatórios')]
        - Saldo Devedor: //a[contains(text(), 'Saldo Devedor Presente')]
        """
        # TODO: IMPLEMENTAR NAVEGAÇÃO REAL
        # 1. Clicar "Contas a Receber"
        # 2. Clicar "Relatórios"
        # 3. Clicar "Saldo Devedor Presente"
        # 4. Validar que chegou na tela correta
        try:
            self.log_progresso("📊 TODO: Acessando Saldo Devedor Presente...")
            # IMPLEMENTAR WEBSCRAPING AQUI
            pass

        except Exception as e:
            self.log_erro("Erro ao acessar relatório Saldo Devedor", e)
            raise

    async def _filtrar_por_titulo(self, numero_titulo: str):
        """
        WEBSCRAPING - Filtra relatório por número do título

        🎯 IMPLEMENTAÇÃO WEBSCRAPING:
        INPUT: numero_titulo (string) - ex: "123456789"
        AÇÃO: Localizar campo de filtro e inserir número do título
        OUTPUT: Campo preenchido e pronto para consulta
        ERRO: Raise Exception se campo não encontrado

        📍 CAMPOS ESPERADOS SIENGE:
        - Campo título: //input[@name='numero_titulo'] ou similar
        - Por placeholder: //input[contains(@placeholder, 'título')]
        - Por label: //label[text()='Título']/..//input

        ⚠️ IMPORTANTE: Deve limpar campo antes de inserir novo valor
        """
        # TODO: IMPLEMENTAR PREENCHIMENTO REAL
        # 1. Localizar campo do número do título
        # 2. Limpar conteúdo existente (clear())
        # 3. Inserir numero_titulo recebido
        # 4. Validar que valor foi inserido
        try:
            self.log_progresso(
                f"🔍 TODO: Filtrando por título: {numero_titulo}")
            # IMPLEMENTAR WEBSCRAPING AQUI
            pass

        except Exception as e:
            self.log_erro("Erro ao filtrar por título", e)
            raise

    async def _executar_relatorio(self) -> Dict[str, Any]:
        """
        WEBSCRAPING - Executa o relatório e coleta dados da tabela

        🎯 IMPLEMENTAÇÃO WEBSCRAPING:
        INPUT: Navegador com filtros já preenchidos
        AÇÃO: 
        1. Clicar botão "Consultar/Executar"
        2. Aguardar tabela de resultados carregar
        3. Extrair dados da tabela HTML

        OUTPUT OBRIGATÓRIO: Dict com estrutura:
        {
            "sucesso": True/False,
            "cabecalhos": ["Título", "Cliente", "Status da parcela", ...],
            "dados_brutos": DataFrame pandas com dados,
            "total_linhas": int,
            "dados_lista": [{"coluna1": "valor1", ...}, ...]
        }

        📍 ELEMENTOS SIENGE:
        - Botão executar: //button[contains(text(), 'Consultar')]
        - Tabela resultado: //table[.//th] ou similar
        - Células: //td para dados, //th para cabeçalhos

        ⚠️ CRÍTICO: Deve aguardar tabela aparecer antes de extrair
        """
        # TODO: IMPLEMENTAR EXECUÇÃO E EXTRAÇÃO REAL
        # 1. Clicar botão Consultar/Executar
        # 2. Aguardar tabela carregar (WebDriverWait)
        # 3. Verificar se houve erro no Sienge
        # 4. Chamar self._extrair_dados_tabela_sienge()
        try:
            self.log_progresso("🔄 TODO: Executando relatório...")
            # IMPLEMENTAR WEBSCRAPING AQUI

            # Por enquanto retorna estrutura vazia para testes
            return {
                "sucesso": False,
                "erro": "Método não implementado - aguardando webscraping",
                "dados_brutos": pd.DataFrame(),
                "total_linhas": 0
            }

        except Exception as e:
            self.log_erro("Erro ao executar relatório", e)
            raise

    def _extrair_dados_tabela_sienge(self) -> Dict[str, Any]:
        """
        WEBSCRAPING - Extrai dados da tabela HTML do relatório Sienge

        🎯 IMPLEMENTAÇÃO WEBSCRAPING:
        INPUT: Navegador com tabela de resultados já carregada
        AÇÃO: Extrair TODOS os dados da tabela HTML

        OUTPUT OBRIGATÓRIO - Dict com estrutura exata:
        {
            "sucesso": True,
            "cabecalhos": ["Título", "Cliente", "Parcela/Condição", "Status da parcela", 
                          "Data vencimento", "Valor a receber", ...],
            "dados_brutos": DataFrame pandas,
            "total_linhas": int,
            "dados_lista": [
                {"Título": "123", "Cliente": "TESTE", "Status da parcela": "Pendente", ...},
                ...
            ]
        }

        📍 ESTRUTURA ESPERADA SIENGE:
        <table>
          <tr><th>Título</th><th>Cliente</th><th>Parcela/Condição</th>...</tr>
          <tr><td>123456</td><td>CLIENTE A</td><td>CT-001</td>...</tr>
          ...
        </table>

        ⚠️ CRÍTICO PARA REGRAS PDD:
        - Coluna "Parcela/Condição": Identifica CT vs REC/FAT
        - Coluna "Status da parcela": Identifica "Quitada" vs outros
        - Coluna "Data vencimento": Para calcular vencidas
        - Coluna "Valor a receber": Para somar saldos
        """
        # TODO: IMPLEMENTAR EXTRAÇÃO REAL DA TABELA
        # 1. Localizar tabela: //table[.//th]
        # 2. Extrair cabeçalhos: .//th (text)
        # 3. Extrair linhas: .//tr[position()>1]
        # 4. Para cada linha: .//td (text)
        # 5. Montar DataFrame e lista
        try:
            self.log_progresso("🔍 TODO: Extraindo dados da tabela...")
            # IMPLEMENTAR WEBSCRAPING AQUI

            # Por enquanto retorna estrutura vazia para testes
            return {
                "sucesso": False,
                "erro": "Método não implementado - aguardando webscraping",
                "cabecalhos": [],
                "dados_brutos": pd.DataFrame(),
                "total_linhas": 0,
                "dados_lista": []
            }

        except Exception as e:
            self.log_erro("Erro na extração de dados da tabela", e)
            return {
                "sucesso": False,
                "erro": str(e),
                "dados_brutos": pd.DataFrame(),
                "total_linhas": 0
            }

    def _processar_dados_relatorio_sienge(self, dados_relatorio: Dict[str, Any], contrato: Dict[str, Any]) -> Dict[str, Any]:
        """Processa dados do relatório do Sienge conforme regras do PDD"""
        try:
            if not dados_relatorio.get("sucesso", False):
                return {
                    "sucesso": False,
                    "erro": "Falha na extração de dados do Sienge"
                }

            df = dados_relatorio.get("dados_brutos", pd.DataFrame())
            if df.empty:
                return {
                    "sucesso": False,
                    "erro": "Nenhum dado encontrado no relatório"
                }

            self.log_progresso("🔄 Processando dados conforme regras PDD...")

            # Identifica colunas importantes (mapping flexível)
            mapeamento_colunas = self._mapear_colunas_sienge(
                df.columns.tolist())

            # Filtra parcelas CT (Cota de Terreno) - REGRA PRINCIPAL PDD
            parcelas_ct = []
            parcelas_rec_fat = []
            parcelas_outras = []

            for _, row in df.iterrows():
                tipo_parcela = str(
                    row.get(mapeamento_colunas.get("tipo_parcela", ""), "")).upper()
                status_parcela = str(
                    row.get(mapeamento_colunas.get("status", ""), ""))

                # Classifica por tipo
                if "CT" in tipo_parcela or "COTA" in tipo_parcela:
                    parcelas_ct.append(row.to_dict())
                elif any(x in tipo_parcela for x in ["REC", "FAT", "RECEITA", "FATURAMENTO"]):
                    parcelas_rec_fat.append(row.to_dict())
                else:
                    parcelas_outras.append(row.to_dict())

            # Calcula saldo total
            coluna_valor = mapeamento_colunas.get("valor", "")
            saldo_total = 0
            if coluna_valor:
                try:
                    saldo_total = df[coluna_valor].apply(
                        self._converter_valor_monetario).sum()
                except:
                    saldo_total = 0

            # Estrutura resultado final
            resultado = {
                "sucesso": True,
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "total_parcelas_ct": len(parcelas_ct),
                "total_parcelas_rec_fat": len(parcelas_rec_fat),
                "saldo_total": saldo_total,
                "parcelas_ct": parcelas_ct,
                "parcelas_rec_fat": parcelas_rec_fat,
                "parcelas_outras": parcelas_outras,
                "dados_brutos": df,
                "mapeamento_colunas": mapeamento_colunas,
                "timestamp_processamento": datetime.now().isoformat()
            }

            self.log_progresso(f"✅ Processamento concluído:")
            self.log_progresso(f"   📊 Total parcelas CT: {len(parcelas_ct)}")
            self.log_progresso(
                f"   📊 Total parcelas REC/FAT: {len(parcelas_rec_fat)}")
            self.log_progresso(f"   💰 Saldo total: R$ {saldo_total:,.2f}")

            return resultado

        except Exception as e:
            self.log_erro("Erro no processamento de dados do relatório", e)
            return {
                "sucesso": False,
                "erro": str(e),
                "cliente": contrato.get("cliente", ""),
                "numero_titulo": contrato.get("numero_titulo", "")
            }

    async def _processar_planilha_baixada(self, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        Processa planilha baixada do Sienge conforme regras PDD

        Etapas:
        1. Localizar arquivo mais recente na pasta Downloads
        2. Ler Excel com pandas
        3. Processar dados conforme regras PDD
        4. Classificar parcelas CT vs REC/FAT
        5. Identificar parcelas vencidas
        6. Salvar cópia para auditoria
        """
        try:
            self.log_progresso(
                "📁 Etapa 1: Localizando arquivo baixado mais recente...")

            # Usar platformdirs para diretório de downloads
            pasta_downloads = user_downloads_dir()
            self.log_progresso(f"   📂 Pasta Downloads: {pasta_downloads}")

            # Buscar arquivo com padrão saldo_devedor_presente-YYYYMMDD-HHMMSS.xlsx
            arquivo_encontrado = self._localizar_arquivo_recente(
                pasta_downloads)

            if not arquivo_encontrado:
                raise Exception(
                    "Arquivo saldo_devedor_presente não encontrado na pasta Downloads")

            self.log_progresso(
                f"   ✅ Arquivo encontrado: {arquivo_encontrado}")

            # Etapa 2: Ler Excel com pandas
            self.log_progresso("📊 Etapa 2: Lendo planilha Excel...")
            df = await self._ler_planilha_excel(arquivo_encontrado)

            # Etapa 3: Salvar cópia para auditoria
            self.log_progresso("💾 Etapa 3: Salvando cópia para auditoria...")
            caminho_auditoria = await self._salvar_planilha_auditoria(arquivo_encontrado, cliente, numero_titulo)

            # Etapa 4: Processar dados conforme regras PDD
            self.log_progresso("🔄 Etapa 4: Processando dados conforme PDD...")
            dados_processados = await self._aplicar_regras_pdd_planilha(df, cliente, numero_titulo)

            # Etapa 5: Adicionar metadados de auditoria
            dados_processados.update({
                "arquivo_original": arquivo_encontrado,
                "arquivo_auditoria": caminho_auditoria,
                "hash_arquivo": self._calcular_hash_arquivo(arquivo_encontrado),
                "processado_em": datetime.now().isoformat(),
                "processado_por": "RPA_Sienge",
                "versao_rpa": "2.0",
                "sucesso": True
            })

            # Etapa 6: Registrar no sistema de auditoria
            await self._registrar_auditoria_planilha(dados_processados)

            self.log_progresso("✅ Planilha processada com sucesso!")
            return dados_processados

        except Exception as e:
            erro_msg = f"Erro no processamento da planilha: {str(e)}"
            self.log_erro(erro_msg, e)
            return {
                "sucesso": False,
                "erro": erro_msg,
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "timestamp_erro": datetime.now().isoformat()
            }

    def _localizar_arquivo_recente(self, pasta_downloads: str) -> str:
        """
        Localiza arquivo saldo_devedor_presente mais recente na pasta Downloads

        Padrão esperado: saldo_devedor_presente-YYYYMMDD-HHMMSS.xlsx
        """
        try:
            pasta_path = Path(pasta_downloads)
            if not pasta_path.exists():
                raise Exception(
                    f"Pasta Downloads não existe: {pasta_downloads}")

            # Buscar arquivos com padrão específico
            padrao = "saldo_devedor_presente-*.xlsx"
            arquivos_encontrados = list(pasta_path.glob(padrao))

            if not arquivos_encontrados:
                raise Exception(
                    f"Nenhum arquivo encontrado com padrão '{padrao}' em {pasta_downloads}")

            # Ordenar por data de modificação (mais recente primeiro)
            arquivos_ordenados = sorted(
                arquivos_encontrados, key=lambda x: x.stat().st_mtime, reverse=True)

            arquivo_mais_recente = str(arquivos_ordenados[0])

            # Validar se arquivo foi modificado recentemente (últimos 10 minutos)
            tempo_arquivo = datetime.fromtimestamp(
                arquivos_ordenados[0].stat().st_mtime)
            tempo_atual = datetime.now()
            diferenca = (tempo_atual - tempo_arquivo).total_seconds() / 60

            if diferenca > 10:
                self.log_progresso(
                    f"⚠️ Arquivo encontrado há {diferenca:.1f} minutos (pode não ser o download atual)")

            self.log_progresso(f"   📄 Arquivo: {arquivo_mais_recente}")
            self.log_progresso(
                f"   🕐 Modificado: {tempo_arquivo.strftime('%d/%m/%Y %H:%M:%S')}")

            return arquivo_mais_recente

        except Exception as e:
            raise Exception(f"Erro ao localizar arquivo: {str(e)}")

    async def _ler_planilha_excel(self, caminho_arquivo: str) -> pd.DataFrame:
        """
        Lê planilha Excel e valida estrutura conforme PDD
        """
        try:
            # Ler Excel
            df = pd.read_excel(caminho_arquivo, engine='openpyxl')

            if df.empty:
                raise Exception("Planilha está vazia")

            self.log_progresso(
                f"   📊 Planilha carregada: {len(df)} registros, {len(df.columns)} colunas")

            # Validar colunas obrigatórias
            colunas_obrigatorias = [
                "Parcela/Sequencial", "Status da parcela", "Data vencimento",
                "Valor a receber", "Documento"
            ]

            colunas_faltantes = [
                col for col in colunas_obrigatorias if col not in df.columns]

            if colunas_faltantes:
                raise Exception(
                    f"Colunas obrigatórias não encontradas: {colunas_faltantes}")

            self.log_progresso("   ✅ Estrutura da planilha validada")

            return df

        except Exception as e:
            raise Exception(f"Erro ao ler planilha Excel: {str(e)}")

    async def _salvar_planilha_auditoria(self, arquivo_original: str, cliente: str, numero_titulo: str) -> str:
        """
        Salva cópia da planilha para auditoria com nomenclatura padronizada
        """
        try:
            # Criar estrutura de pastas por ano/mês
            agora = datetime.now()
            pasta_auditoria = self.pasta_planilhas / \
                str(agora.year) / f"{agora.month:02d}"
            pasta_auditoria.mkdir(parents=True, exist_ok=True)

            # Nome do arquivo de auditoria
            timestamp = agora.strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"sienge_{numero_titulo}_{timestamp}.xlsx"
            caminho_auditoria = pasta_auditoria / nome_arquivo

            # Copiar arquivo
            shutil.copy2(arquivo_original, caminho_auditoria)

            self.log_progresso(f"   💾 Cópia salva: {caminho_auditoria}")

            return str(caminho_auditoria)

        except Exception as e:
            self.log_erro("Erro ao salvar planilha para auditoria", e)
            return ""

    async def _aplicar_regras_pdd_planilha(self, df: pd.DataFrame, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        Aplica regras do PDD para processar dados da planilha

        Regras principais:
        1. Classificar parcelas CT vs REC/FAT
        2. Identificar parcelas vencidas
        3. Calcular inadimplência (≥3 CT vencidas)
        4. Calcular saldos totais
        """
        try:
            parcelas_ct = []
            parcelas_rec_fat = []
            parcelas_outras = []

            hoje = date.today()

            for _, row in df.iterrows():
                # Extrair dados da linha
                parcela_sequencial = str(
                    row.get("Parcela/Sequencial", "")).upper()
                status_parcela = str(row.get("Status da parcela", ""))
                data_vencimento_str = row.get("Data vencimento", "")
                valor_str = row.get("Valor a receber", 0)
                documento = str(row.get("Documento", ""))

                # Converter data de vencimento
                data_vencimento = None
                if data_vencimento_str:
                    try:
                        if isinstance(data_vencimento_str, str):
                            data_vencimento = datetime.strptime(
                                data_vencimento_str, "%d/%m/%Y").date()
                        else:
                            data_vencimento = data_vencimento_str.date()
                    except:
                        pass

                # Converter valor
                valor = self._converter_valor_monetario(valor_str)

                # Verificar se está vencida
                vencida = data_vencimento and data_vencimento < hoje if data_vencimento else False

                # Dados da parcela
                dados_parcela = {
                    "tipo_parcela": parcela_sequencial,
                    "status_parcela": status_parcela,
                    "data_vencimento": data_vencimento.isoformat() if data_vencimento else None,
                    "valor": valor,
                    "documento": documento,
                    "vencida": vencida,
                    "quitada": status_parcela.upper() == "QUITADA"
                }

                # Classificar por tipo (REGRA PDD)
                if "CT" in parcela_sequencial or "COTA" in parcela_sequencial:
                    parcelas_ct.append(dados_parcela)
                elif any(x in parcela_sequencial for x in ["REC", "FAT", "RECEITA", "FATURAMENTO"]):
                    parcelas_rec_fat.append(dados_parcela)
                else:
                    parcelas_outras.append(dados_parcela)

            # Calcular parcelas CT vencidas (REGRA CRÍTICA PDD)
            parcelas_ct_vencidas = [
                p for p in parcelas_ct
                if p["vencida"] and not p["quitada"]
            ]

            # Determinar status do cliente
            qtd_ct_vencidas = len(parcelas_ct_vencidas)
            status_cliente = "inadimplente" if qtd_ct_vencidas >= 3 else "adimplente"

            # Calcular saldo total
            saldo_total = sum(p["valor"] for p in parcelas_ct +
                              parcelas_rec_fat + parcelas_outras)

            resultado = {
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "saldo_total": saldo_total,
                "parcelas_pendentes": len([p for p in parcelas_ct if not p["quitada"]]),
                "parcelas_ct": parcelas_ct,
                "parcelas_rec_fat": parcelas_rec_fat,
                "parcelas_outras": parcelas_outras,
                "parcelas_ct_vencidas": parcelas_ct_vencidas,
                "qtd_ct_vencidas": qtd_ct_vencidas,
                "status_cliente": status_cliente,
                "relatorio_exportado": True,
                "dados_brutos": df,
                "total_registros": len(df),
                "resumo": {
                    "total_ct": len(parcelas_ct),
                    "total_rec_fat": len(parcelas_rec_fat),
                    "total_outras": len(parcelas_outras),
                    "ct_vencidas": qtd_ct_vencidas,
                    "pode_reparcelar": status_cliente == "adimplente"
                }
            }

            self.log_progresso(f"   📊 Processamento PDD concluído:")
            self.log_progresso(f"      💰 Saldo total: R$ {saldo_total:,.2f}")
            self.log_progresso(f"      📋 Parcelas CT: {len(parcelas_ct)}")
            self.log_progresso(
                f"      📋 Parcelas REC/FAT: {len(parcelas_rec_fat)}")
            self.log_progresso(f"      ⚠️ CT vencidas: {qtd_ct_vencidas}")
            self.log_progresso(f"      🎯 Status: {status_cliente.upper()}")

            return resultado

        except Exception as e:
            raise Exception(f"Erro ao aplicar regras PDD: {str(e)}")

    def _converter_valor_monetario(self, valor) -> float:
        """
        Converte valor monetário para float
        """
        try:
            if pd.isna(valor) or valor == "":
                return 0.0

            if isinstance(valor, (int, float)):
                return float(valor)

            # Remover formatação brasileira
            if isinstance(valor, str):
                valor = valor.replace("R$", "").replace(
                    ".", "").replace(",", ".").strip()
                return float(valor)

            return 0.0
        except:
            return 0.0

    def _calcular_hash_arquivo(self, caminho_arquivo: str) -> str:
        """
        Calcula hash MD5 do arquivo para verificação de integridade
        """
        try:
            import hashlib
            hash_md5 = hashlib.md5()
            with open(caminho_arquivo, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return ""

    async def _registrar_auditoria_planilha(self, dados_processados: Dict[str, Any]):
        """
        Registra dados da planilha no sistema de auditoria (MongoDB + JSON)
        """
        try:
            # Preparar dados para auditoria
            registro_auditoria = {
                "tipo": "planilha_sienge",
                "cliente": dados_processados.get("cliente"),
                "numero_titulo": dados_processados.get("numero_titulo"),
                "arquivo_original": dados_processados.get("arquivo_original"),
                "arquivo_auditoria": dados_processados.get("arquivo_auditoria"),
                "hash_arquivo": dados_processados.get("hash_arquivo"),
                "saldo_total": dados_processados.get("saldo_total"),
                "total_registros": dados_processados.get("total_registros"),
                "resumo": dados_processados.get("resumo"),
                "processado_em": dados_processados.get("processado_em"),
                "processado_por": dados_processados.get("processado_por"),
                "versao_rpa": dados_processados.get("versao_rpa"),
                "ip_usuario": self._obter_ip_usuario(),
                "usuario_sistema": os.getenv("USER", "sistema")
            }

            # Salvar no MongoDB (se disponível)
            try:
                from core.mongodb_manager import mongodb_manager
                if hasattr(mongodb_manager, 'database'):
                    await mongodb_manager.database.auditoria_planilhas_sienge.insert_one(registro_auditoria)
                    self.log_progresso("   ✅ Auditoria salva no MongoDB")
            except Exception as e:
                self.log_progresso(f"   ⚠️ MongoDB indisponível: {str(e)}")

            # Fallback JSON
            pasta_auditoria_json = Path(
                "dados_processamento/auditoria_planilhas")
            pasta_auditoria_json.mkdir(parents=True, exist_ok=True)

            arquivo_json = pasta_auditoria_json / \
                f"auditoria_{dados_processados.get('numero_titulo')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(arquivo_json, 'w', encoding='utf-8') as f:
                json.dump(registro_auditoria, f, indent=2,
                          ensure_ascii=False, default=str)

            self.log_progresso(f"   💾 Auditoria salva: {arquivo_json}")

        except Exception as e:
            self.log_erro("Erro ao registrar auditoria", e)

    def _obter_ip_usuario(self) -> str:
        """
        Obtém IP do usuário para auditoria
        """
        try:
            import socket
            hostname = socket.gethostname()
            ip_local = socket.gethostbyname(hostname)
            return ip_local
        except:
            return "unknown"
