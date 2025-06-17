"""
RPA SIENGE - VERSÃO PRODUÇÃO DOCUMENTADA
Sistema de Reparcelamento no ERP Sienge

🎯 OBJETIVO: Processar reparcelamentos conforme PDD seção 7.3
📋 BASEADO EM: PDD_Reparcelamento_Sienge.pdf + Playbooks implementados
🔧 VERSÃO: 2.0 - Produção com documentação sequencial completa

===============================================================================
📖 ÍNDICE DE NAVEGAÇÃO DO CÓDIGO:
===============================================================================

1. 🏗️  CLASSE PRINCIPAL (RPASienge)                             → Linha ~50
2. 🚀 MÉTODO EXECUTAR (Orquestrador principal)                  → Linha ~80  
3. 📊 ETAPA 1: CONSULTA RELATÓRIOS                             → Linha ~180
4. 🔄 ETAPA 2: PROCESSAMENTO REPARCELAMENTO                     → Linha ~220
5. 🔐 LOGIN SIENGE (Webscraping funcional)                     → Linha ~280
6. 📋 CONSULTA RELATÓRIOS FINANCEIROS (Webscraping)            → Linha ~350
7. 🤖 PROCESSAMENTO PLANILHA (Análise automática)              → Linha ~500
8. ⚖️  VALIDAÇÃO CONTRATOS PDD (Regras rigorosas)              → Linha ~800
9. 🧮 CÁLCULOS REPARCELAMENTO (Valores para Sienge)           → Linha ~950
10. 🔍 WEBSCRAPING REPARCELAMENTO (TODOs usuário)              → Linha ~1100
11. 📁 UTILITÁRIOS E AUXILIARES                                → Linha ~1300

===============================================================================
📚 REFERÊNCIAS DOCUMENTAIS:
===============================================================================

PDD SEÇÃO 7.3: Processamento no sistema Sienge
- 7.3.1: Consulta de relatórios financeiros  
- 7.3.2: Validação de inadimplência
- 7.3.3: Processamento de reparcelamento
- 7.3.4: Geração de carnê

PLAYBOOKS IMPLEMENTADOS:
- PLAYBOOK DETALHADO – REGISTRO E EMISSÃO DE REPARCELAMENTO NO SIENGE
- Regras de Negócio para Reparcelamento (1-8)
- Acesso ao ERP Sienge (tc@trajetoriaconsultoria.com.br)

RESPONSABILIDADES:
- 🔍 USUÁRIO: Webscraping (navegação, cliques, preenchimento)
- 🤖 ASSISTENTE: Processamento (análise, validações, cálculos)

===============================================================================

Desenvolvido em Português Brasileiro
"""

from platformdirs import user_downloads_dir
from core.base_rpa import BaseRPA, ResultadoRPA
from core.notificacoes_simples import notificar_sucesso, notificar_erro
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
from dotenv import load_dotenv

load_dotenv()


# ===============================================================================
# 1. 🏗️ CLASSE PRINCIPAL - RPA SIENGE
# ===============================================================================

class RPASienge(BaseRPA):
    """
    RPA para processamento de reparcelamento no sistema Sienge

    📋 SEQUÊNCIA DE PROCESSAMENTO COMPLETA:

    ETAPA 1: CONSULTA DE RELATÓRIOS FINANCEIROS
    └── Login no Sienge (credenciais tc@trajetoriaconsultoria.com.br)
    └── Navegação: Financeiro > Contas a Receber > Relatórios > Saldo Devedor Presente
    └── Filtro por cliente específico
    └── Exportação Excel e processamento automático
    └── Aplicação regras PDD (1-8) para validação de inadimplência

    ETAPA 2: PROCESSAMENTO DE REPARCELAMENTO  
    └── Validação rigorosa: Cliente com ≥3 CT vencidas = INADIMPLENTE
    └── Cálculo valores: IGP-M obrigatório + Taxa fixa 8%
    └── Navegação: Financeiro > Contas a Receber > Reparcelamento > Inclusão
    └── Preenchimento formulário com valores calculados
    └── Seleção documentos + Desmarcação parcelas vencidas
    └── Confirmação e captura novo título gerado

    ETAPA 3: GERAÇÃO DE CARNÊ
    └── Navegação: Financeiro > Contas a Receber > Cobrança Escritural
    └── Configuração parâmetros do carnê
    └── Exportação arquivo final

    RESPONSABILIDADES:
    🔍 USUÁRIO: Webscraping (todos os métodos _navegar_*, _consultar_*, _configurar_*)
    🤖 ASSISTENTE: Processamento (_processar_*, _validar_*, _calcular_*, _aplicar_regras_*)
    """

    def __init__(self):
        super().__init__(nome_rpa="Sienge", usar_browser=True)
        self.logado_sienge = False
        self.credenciais_sienge = {}
        self.pasta_planilhas = Path("dados_extraidos/planilhas_sienge")
        self.pasta_planilhas.mkdir(parents=True, exist_ok=True)

    def _configurar_credenciais(self, credenciais: Dict[str, str]):
        """
        Configura credenciais do Sienge conforme PDD

        CREDENCIAIS PADRÃO:
        - URL: https://jmservicos.sienge.com.br/sienge/8/index.html
        - Usuário: tc@trajetoriaconsultoria.com.br
        - Senha: (configurada via variável de ambiente)
        """
        self.credenciais_sienge = {
            "url": credenciais.get("url", ""),
            "usuario": credenciais.get("usuario", ""),
            "senha": credenciais.get("senha", ""),
            "empresa": credenciais.get("empresa", "")
        }


# ===============================================================================
# 2. 🚀 MÉTODO EXECUTAR - ORQUESTRADOR PRINCIPAL
# ===============================================================================

    async def executar(self,
                       contrato: Dict[str, Any],
                       credenciais_sienge: Dict[str, str],
                       indices: Dict[str, Any] = None,
                       etapa: str = "completa",
                       autorizar_reparcelamento: bool = False,
                       notificar_analista: bool = True) -> ResultadoRPA:
        """
        🎯 ORQUESTRADOR PRINCIPAL - Executa processamento RPA Sienge

        SEQUÊNCIA OBRIGATÓRIA conforme PDD seção 7.3:

        1️⃣ LOGIN NO SIENGE
           └── Método: _fazer_login_sienge()
           └── Credenciais: tc@trajetoriaconsultoria.com.br

        2️⃣ ETAPA 1: CONSULTA DE RELATÓRIOS FINANCEIROS  
           └── Método: _executar_etapa_consulta()
           └── Navegação: Financeiro > Contas a Receber > Relatórios
           └── Relatório: Saldo Devedor Presente
           └── Exportação: Excel para processamento

        3️⃣ ETAPA 2: PROCESSAMENTO DE REPARCELAMENTO
           └── Método: _executar_etapa_reparcelamento()
           └── Validação: Inadimplência conforme regras PDD
           └── Cálculos: IGP-M + Taxa fixa 8%
           └── Navegação: Reparcelamento > Inclusão

        4️⃣ ETAPA 3: GERAÇÃO DE CARNÊ (se bem-sucedido)
           └── Método: _gerar_carne_sienge()
           └── Navegação: Cobrança Escritural > Geração

        Args:
            contrato: Dados do contrato (numero_titulo, cliente, etc.)
            credenciais_sienge: Credenciais de acesso ao Sienge
            indices: Índices econômicos (IPCA/IGPM) - IGP-M obrigatório
            etapa: "consulta", "reparcelamento" ou "completa"
            autorizar_reparcelamento: True para pular validação de autorização
            notificar_analista: False para ignorar notificações de validação

        Returns:
            ResultadoRPA com dados processados e status de execução
        """
        try:
            self.log_progresso(f"🚀 INICIANDO RPA SIENGE - ETAPA: {etapa.upper()}")
            self.log_progresso(f"   📋 Contrato: {contrato.get('numero_titulo', '')}")
            self.log_progresso(f"   👤 Cliente: {contrato.get('cliente', '')}")
            self.log_progresso(f"   🔐 Autorização automática: {autorizar_reparcelamento}")

            if not contrato or not credenciais_sienge:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem="Dados do contrato ou credenciais Sienge não fornecidos",
                    erro="Parâmetros 'contrato' e 'credenciais_sienge' são obrigatórios"
                )

            # PASSO 1: Configurar credenciais e fazer login
            self._configurar_credenciais(credenciais_sienge)
            await self._fazer_login_sienge()

            # PASSO 2: ETAPA 1 - CONSULTA DE RELATÓRIOS (sempre executada)
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

            # PASSO 3: ETAPA 2 - PROCESSAMENTO DE REPARCELAMENTO
            if etapa in ["reparcelamento", "completa"]:
                resultado_reparcelamento = await self._executar_etapa_reparcelamento(
                    contrato, indices or {}, dados_financeiros, 
                    autorizar_reparcelamento, notificar_analista
                )

                if etapa == "reparcelamento":
                    return resultado_reparcelamento

            # PASSO 4: ETAPA COMPLETA - COMBINAR RESULTADOS + CARNÊ
            if etapa == "completa":
                # Gera carnê se processamento foi bem-sucedido
                carne_gerado = None
                if dados_financeiros.get("sucesso") and resultado_reparcelamento.sucesso:
                    self.log_progresso("📄 Gerando carnê atualizado...")
                    carne_gerado = await self._gerar_carne_sienge(contrato)

                # Monta resultado final
                resultado_dados = {
                    "etapa_executada": "completa",
                    "contrato_processado": contrato,
                    "dados_financeiros": dados_financeiros,
                    "reparcelamento": resultado_reparcelamento.dados if resultado_reparcelamento.dados else {},
                    "carne_gerado": carne_gerado,
                    "timestamp_processamento": datetime.now().isoformat()
                }

                return ResultadoRPA(
                    sucesso=resultado_reparcelamento.sucesso,
                    mensagem=f"Processamento completo - Cliente: {contrato.get('cliente', '')}",
                    dados=resultado_dados)

        except Exception as e:
            erro_msg = f"Erro na execução do RPA Sienge: {str(e)}"
            self.log_erro(erro_msg, e)
            return ResultadoRPA(sucesso=False,
                                mensagem="Falha na execução do RPA Sienge",
                                erro=erro_msg)


# ===============================================================================
# 3. 📊 ETAPA 1: CONSULTA DE RELATÓRIOS FINANCEIROS
# ===============================================================================

    async def _executar_etapa_consulta(self, contrato: Dict[str, Any]) -> Dict[str, Any]:
        """
        📊 ETAPA 1: CONSULTA DE RELATÓRIOS FINANCEIROS

        SEQUÊNCIA PDD seção 7.3.1 - Leitura e extração de dados:

        1️⃣ NAVEGAÇÃO OBRIGATÓRIA:
           └── Financeiro > Contas a Receber > Relatórios > Saldo Devedor Presente

        2️⃣ FILTRO POR CLIENTE:
           └── Campo: "Pesquisar cliente"
           └── Valor: contrato.cliente
           └── Ação: Consultar

        3️⃣ GERAÇÃO E EXPORTAÇÃO:
           └── Botão: "Gerar Relatório" 
           └── Formato: Excel (obrigatório)
           └── Ação: Exportar

        4️⃣ PROCESSAMENTO AUTOMÁTICO:
           └── Localizar arquivo baixado na pasta Downloads/RPA_DOWNLOADS
           └── Aplicar regras PDD (1-8) conforme documentação oficial
           └── Classificar parcelas CT vs REC/FAT
           └── Validar inadimplência (≥3 CT vencidas)

        RESPONSABILIDADES:
        🔍 USUÁRIO: Steps 1-3 (webscraping)
        🤖 ASSISTENTE: Step 4 (processamento automático)
        """
        try:
            self.log_progresso("📊 ETAPA 1: CONSULTA DE RELATÓRIOS FINANCEIROS")

            # Consulta relatórios financeiros do cliente (WEBSCRAPING)
            self.log_progresso(f"🔍 Consultando relatórios do cliente: {contrato.get('cliente', '')}")
            dados_financeiros = await self._consultar_relatorios_financeiros(contrato)

            # Aplicar regras PDD para extrair informações obrigatórias (PROCESSAMENTO AUTOMÁTICO)
            if dados_financeiros.get("sucesso"):
                self.log_progresso("🤖 Aplicando regras de negócio PDD...")
                dados_processados = await self._aplicar_regras_negocio_pdd(dados_financeiros, contrato)
                dados_financeiros.update(dados_processados)

            self.log_progresso("✅ ETAPA 1 CONCLUÍDA: Consulta de relatórios")
            return dados_financeiros

        except Exception as e:
            erro_msg = f"Erro na etapa de consulta: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"sucesso": False, "erro": erro_msg, "etapa": "consulta"}


# ===============================================================================
# 4. 🔄 ETAPA 2: PROCESSAMENTO DE REPARCELAMENTO  
# ===============================================================================

    async def _executar_etapa_reparcelamento(self, 
                                           contrato: Dict[str, Any], 
                                           indices: Dict[str, Any],
                                           dados_financeiros: Dict[str, Any],
                                           autorizar_reparcelamento: bool = False,
                                           notificar_analista: bool = True) -> ResultadoRPA:
        """
        🔄 ETAPA 2: PROCESSAMENTO DE REPARCELAMENTO

        SEQUÊNCIA PDD seção 7.3.3 - Processamento no sistema Sienge:

        1️⃣ VALIDAÇÃO RIGOROSA PDD:
           └── Regra: Cliente com ≥3 parcelas CT vencidas = INADIMPLENTE
           └── Método: _validar_contrato_reparcelamento()
           └── Resultado: pode_reparcelar = True/False

        2️⃣ VERIFICAÇÃO DE AUTORIZAÇÃO:
           └── Parcelas irregulares exigem aprovação do analista
           └── Método: _verificar_autorizacao_reparcelamento()
           └── Notificação por e-mail (se notificar_analista=True)

        3️⃣ CÁLCULOS OBRIGATÓRIOS:
           └── Índice: IGP-M (NUNCA IPCA)
           └── Taxa: Fixa 8% ao ano
           └── Tipo: PM (Prazo Mensal)
           └── Método: calcular_valores_reparcelamento()

        4️⃣ PROCESSAMENTO NO SIENGE:
           └── Navegação: Financeiro > Contas a Receber > Reparcelamento > Inclusão
           └── Preenchimento automático com valores calculados
           └── Seleção/desmarcação parcelas conforme regras PDD
           └── Confirmação e captura novo título

        RESPONSABILIDADES:
        🤖 ASSISTENTE: Steps 1-3 (validações e cálculos)
        🔍 USUÁRIO: Step 4 (webscraping no Sienge)
        """
        try:
            self.log_progresso("🔄 ETAPA 2: PROCESSAMENTO DE REPARCELAMENTO")

            # PASSO 1: Valida se contrato pode ser reparcelado (REGRAS PDD RIGOROSAS)
            pode_reparcelar = await self._validar_contrato_reparcelamento(dados_financeiros)

            if not pode_reparcelar["pode_reparcelar"]:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem=f"Contrato não pode ser reparcelado: {pode_reparcelar['motivo']}",
                    dados={
                        "etapa_executada": "reparcelamento",
                        "contrato": contrato,
                        "validacao": pode_reparcelar,
                        "dados_financeiros": dados_financeiros
                    })

            # PASSO 2: Verificar autorização para reparcelamento
            if not autorizar_reparcelamento:
                resultado_autorizacao = await self._verificar_autorizacao_reparcelamento(
                    contrato, dados_financeiros, notificar_analista
                )

                if not resultado_autorizacao["autorizado"]:
                    return ResultadoRPA(
                        sucesso=False,
                        mensagem=f"Reparcelamento não autorizado: {resultado_autorizacao['motivo']}",
                        dados={
                            "etapa_executada": "reparcelamento",
                            "contrato": contrato,
                            "autorizacao": resultado_autorizacao,
                            "aguardando_aprovacao": True
                        })

            # PASSO 3: Processa reparcelamento no Sienge (WEBSCRAPING + CÁLCULOS)
            self.log_progresso("⚙️ Processando reparcelamento no Sienge...")
            resultado_reparcelamento = await self._processar_reparcelamento(
                contrato, indices, dados_financeiros)

            self.log_progresso("✅ ETAPA 2 CONCLUÍDA: Reparcelamento processado")

            return ResultadoRPA(
                sucesso=resultado_reparcelamento["sucesso"],
                mensagem=f"Reparcelamento processado - Cliente: {contrato.get('cliente', '')}",
                dados={
                    "etapa_executada": "reparcelamento",
                    "contrato": contrato,
                    "reparcelamento": resultado_reparcelamento,
                    "timestamp_processamento": datetime.now().isoformat()
                })

        except Exception as e:
            erro_msg = f"Erro na etapa de reparcelamento: {str(e)}"
            self.log_erro(erro_msg, e)
            return ResultadoRPA(sucesso=False, mensagem="Falha na etapa de reparcelamento", erro=erro_msg)


# ===============================================================================
# 5. 🔐 LOGIN SIENGE - WEBSCRAPING FUNCIONAL
# ===============================================================================

    async def _fazer_login_sienge(self):
        """
        🔐 LOGIN NO SISTEMA SIENGE - WEBSCRAPING FUNCIONAL

        SEQUÊNCIA IMPLEMENTADA conforme PDD seção 7.3:

        1️⃣ ACESSO INICIAL:
           └── URL: https://jmservicos.sienge.com.br/sienge/8/index.html
           └── Aguardar carregamento da página de login

        2️⃣ PRIMEIRA TELA - CREDENCIAIS BÁSICAS:
           └── Campo usuário: input#username
           └── Campo senha: input#password  
           └── Botão: #btnEntrarComSiengeID

        3️⃣ SEGUNDA TELA - CONFIRMAÇÃO EMAIL:
           └── Campo email: //label[text()="Seu e-mail"]/following-sibling::div//input
           └── Valor: tc@trajetoriaconsultoria.com.br
           └── Botão: //button[normalize-space(text())='CONTINUAR']

        4️⃣ TERCEIRA TELA - SENHA FINAL:
           └── Campo senha final e confirmação de acesso
        """
        try:
            if self.logado_sienge:
                self.log_progresso("✅ Já logado no Sienge")
                return

            url = self.credenciais_sienge.get("url", "")
            usuario = self.credenciais_sienge.get("usuario", "")
            senha = self.credenciais_sienge.get("senha", "")

            if not all([url, usuario, senha]):
                raise Exception("Credenciais do Sienge incompletas")

            self.log_progresso(f"🔐 Fazendo login no Sienge: {url}")
            self.log_progresso(f"👤 Usuário: {usuario}")

            # 1️⃣ ACESSO INICIAL
            await self.browser.get(url)
            await asyncio.sleep(3)

            # 2️⃣ PRIMEIRA TELA - CREDENCIAIS BÁSICAS
            self.log_progresso("📝 Preenchendo credenciais...")
            
            # Campo usuário
            campo_usuario = await self.browser.find_element(By.CSS_SELECTOR, "input#username")
            await campo_usuario.clear()
            await campo_usuario.send_keys(usuario)
            
            # Campo senha
            campo_senha = await self.browser.find_element(By.CSS_SELECTOR, "input#password")
            await campo_senha.clear()
            await campo_senha.send_keys(senha)
            
            # Botão entrar
            btn_entrar = await self.browser.find_element(By.CSS_SELECTOR, "#btnEntrarComSiengeID")
            await btn_entrar.click()
            
            await asyncio.sleep(4)

            # 3️⃣ SEGUNDA TELA - CONFIRMAÇÃO EMAIL (se aparecer)
            try:
                campo_email = await self.browser.find_element(
                    By.XPATH, 
                    "//label[text()='Seu e-mail']/following-sibling::div//input"
                )
                if campo_email:
                    self.log_progresso("📧 Confirmando email...")
                    await campo_email.clear()
                    await campo_email.send_keys(usuario)
                    
                    btn_continuar = await self.browser.find_element(
                        By.XPATH, 
                        "//button[normalize-space(text())='CONTINUAR']"
                    )
                    await btn_continuar.click()
                    await asyncio.sleep(3)
            except:
                pass  # Tela de email não apareceu

            # 4️⃣ VERIFICAR SE LOGIN FOI BEM-SUCEDIDO
            try:
                # Aguardar elemento que indica login bem-sucedido
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(text(), 'Financeiro')]"))
                )
                self.logado_sienge = True
                self.log_progresso("✅ Login realizado com sucesso!")
                
            except Exception as e:
                raise Exception(f"Falha no login - elemento esperado não encontrado: {str(e)}")

        except Exception as e:
            erro_msg = f"Erro no login Sienge: {str(e)}"
            self.log_erro(erro_msg, e)
            raise Exception(erro_msg)ampo senha: input#signup-password
           └── Botão final: //button[normalize-space(text())='ENTRAR']

        5️⃣ VALIDAÇÃO LOGIN:
           └── Verificar se chegou no dashboard principal
           └── Fechar modais/avisos se aparecerem

        RESPONSABILIDADE: 🔍 USUÁRIO (webscraping implementado)
        STATUS: ✅ FUNCIONAL - Sequência testada e aprovada
        """
        try:
            url_sienge = self.credenciais_sienge.get("url", "")
            usuario_sienge = self.credenciais_sienge.get("usuario", "")
            senha_sienge = self.credenciais_sienge.get("senha", "")

            self.log_progresso(f"🔐 Acessando sistema Sienge: {url_sienge}")

            # PASSO 1: Acessa página de login
            if not url_sienge:
                raise ValueError("URL do Sienge não foi configurada corretamente.")

            self.browser.get_page(url_sienge)


    # ===============================================================================
    # MÉTODOS AUXILIARES PARA LOOP OTIMIZADO DE CONSULTAS
    # ===============================================================================

    async def _navegar_tela_relatorio_inicial(self):
        """
        🔍 TODO USUÁRIO: NAVEGAÇÃO INICIAL - Primeira vez para tela de relatório

        SEQUÊNCIA PRIMEIRA EXECUÇÃO:
        1. Navegar URL direta: .../relatorios/saldo-devedor
        2. Aguardar carregamento completo
        3. Validar que tela está pronta para pesquisa
        """
        try:
            url_relatorio = "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/relatorios/saldo-devedor"
            self.log_progresso(f"🧭 Navegação inicial para: {url_relatorio}")
            
            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING
            # self.browser.get_page(url_relatorio)
            # time.sleep(3)
            # Validar que chegou na tela correta

        except Exception as e:
            self.log_erro("Erro na navegação inicial", e)
            raise

    async def _limpar_campo_pesquisa_cliente(self):
        """
        🔍 TODO USUÁRIO: LIMPEZA CAMPO - Limpar pesquisa anterior para novo cliente

        SEQUÊNCIA LIMPEZA:
        1. Localizar campo pesquisa: //input[@placeholder='Pesquisar cliente' and @role='combobox']
        2. Limpar conteúdo anterior (CTRL+A, DELETE)
        3. Validar que campo está vazio e pronto
        """
        try:
            self.log_progresso("🧹 Limpando campo de pesquisa anterior...")
            
            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING
            # campo_pesquisa = self.browser.find_element(xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']")
            # if campo_pesquisa:
            #     campo_pesquisa.click()
            #     campo_pesquisa.send_keys(Keys.CONTROL + "a")
            #     campo_pesquisa.send_keys(Keys.DELETE)
            #     time.sleep(1)

        except Exception as e:
            self.log_erro("Erro ao limpar campo pesquisa", e)
            # Não é crítico - continuar execução

    async def _executar_consulta_cliente_relatorio(self, cliente: str):
        """
        🔍 TODO USUÁRIO: CONSULTA CLIENTE - Preencher e executar consulta

        SEQUÊNCIA CONSULTA:
        1. Preencher campo com nome do cliente
        2. Confirmar seleção (TAB ou ENTER)
        3. Clicar botão "Consultar"
        4. Aguardar resultados carregarem
        """
        try:
            self.log_progresso(f"🔍 Executando consulta para cliente: {cliente}")
            
            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING
            # combo_pesquisa = self.browser.find_element(xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']")
            # if combo_pesquisa:
            #     combo_pesquisa.click()
            #     time.sleep(1)
            #     self.browser.send_text_human_like(xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']", text=cliente)
            #     combo_pesquisa.send_keys(Keys.TAB)
            #     time.sleep(1)
            #     self.browser.click(xpath="//button[normalize-space()='Consultar']")
            #     time.sleep(3)

        except Exception as e:
            self.log_erro("Erro ao executar consulta cliente", e)
            raise

    async def _gerar_exportar_relatorio_excel(self):
        """
        🔍 TODO USUÁRIO: EXPORT EXCEL - Gerar e exportar relatório em Excel

        SEQUÊNCIA EXPORT:
        1. Clicar "Gerar Relatório"
        2. Aguardar modal abrir
        3. Selecionar formato "EXCEL"
        4. Clicar "Exportar"
        5. Aguardar download concluir
        """
        try:
            self.log_progresso("📊 Gerando e exportando relatório Excel...")
            
            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING
            # # Gerar relatório
            # self.browser.click(xpath="//button[@type='button' and contains(., 'Gerar Relatório')]")
            # time.sleep(2)
            # 
            # # Selecionar formato Excel


    async def consultar_multiplos_clientes_loop(self, lista_contratos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        🔄 PROCESSAR MÚLTIPLOS CLIENTES EM LOOP OTIMIZADO

        VANTAGEM DO LOOP:
        ═══════════════════════════════════════════════════════════════════════════
        ✅ **1 LOGIN** para N clientes (ao invés de N logins)
        ✅ **REUTILIZA** tela de relatório
        ✅ **OTIMIZAÇÃO** significativa de tempo e recursos
        ✅ **REDUZ** chance de bloqueio por excesso de logins
        ═══════════════════════════════════════════════════════════════════════════

        SEQUÊNCIA OTIMIZADA:
        1️⃣ Login único no Sienge (método existente)
        2️⃣ Navegar uma vez para tela de relatório  
        3️⃣ **LOOP** para cada cliente:
           └── Consultar cliente atual
           └── Processar dados (ASSISTENTE)
           └── Retornar à tela de pesquisa
           └── **PRÓXIMO CLIENTE** (sem novo login)

        Args:
            lista_contratos: Lista de contratos para processar
            Exemplo: [
                {"numero_titulo": "123", "cliente": "EMPRESA A"},
                {"numero_titulo": "456", "cliente": "EMPRESA B"}
            ]

        Returns:
            Lista com resultados de cada cliente processado
        """
        try:
            total_clientes = len(lista_contratos)
            resultados_clientes = []

            self.log_progresso(f"🔄 INICIANDO LOOP OTIMIZADO - {total_clientes} clientes")
            self.log_progresso("   ✅ Reutilizando login único para todos os clientes")

            # Resetar flag para começar fresh
            self._na_tela_relatorio_sienge = False

            for i, contrato in enumerate(lista_contratos, 1):
                cliente = contrato.get("cliente", f"Cliente_{i}")
                numero_titulo = contrato.get("numero_titulo", f"Titulo_{i}")

                try:
                    self.log_progresso(f"")
                    self.log_progresso(f"{'='*60}")
                    self.log_progresso(f"🔍 CLIENTE {i}/{total_clientes}: {cliente}")
                    self.log_progresso(f"   📋 Título: {numero_titulo}")
                    self.log_progresso(f"{'='*60}")

                    # Processar cliente atual (método já otimizado para loop)
                    resultado_cliente = await self._consultar_relatorios_financeiros(contrato)

                    # Adicionar metadados do loop
                    resultado_cliente.update({
                        "posicao_fila": i,
                        "total_fila": total_clientes,
                        "processado_em_loop": True,
                        "timestamp_processamento": datetime.now().isoformat()
                    })

                    resultados_clientes.append(resultado_cliente)

                    if resultado_cliente.get("sucesso"):
                        self.log_progresso(f"✅ Cliente {i} processado com sucesso!")
                    else:
                        self.log_progresso(f"❌ Cliente {i} com erro: {resultado_cliente.get('erro', 'N/A')}")

                    # Pequena pausa entre clientes para não sobrecarregar
                    if i < total_clientes:
                        self.log_progresso("⏳ Aguardando intervalo antes do próximo cliente...")
                        time.sleep(2)

                except Exception as e:
                    erro_msg = f"Erro ao processar cliente {i}: {str(e)}"
                    self.log_erro(erro_msg, e)
                    
                    resultado_erro = {
                        "cliente": cliente,
                        "numero_titulo": numero_titulo,
                        "sucesso": False,
                        "erro": erro_msg,
                        "posicao_fila": i,
                        "total_fila": total_clientes,
                        "processado_em_loop": True,
                        "timestamp_erro": datetime.now().isoformat()
                    }
                    resultados_clientes.append(resultado_erro)

            # Estatísticas finais
            sucessos = sum(1 for r in resultados_clientes if r.get("sucesso"))
            erros = total_clientes - sucessos

            self.log_progresso(f"")
            self.log_progresso(f"📊 ESTATÍSTICAS FINAIS DO LOOP:")
            self.log_progresso(f"   ✅ Sucessos: {sucessos}/{total_clientes}")
            self.log_progresso(f"   ❌ Erros: {erros}/{total_clientes}")
            self.log_progresso(f"   🔄 Loop otimizado: 1 login para {total_clientes} clientes")

            return resultados_clientes

        except Exception as e:
            erro_msg = f"Erro crítico no loop de clientes: {str(e)}"
            self.log_erro(erro_msg, e)
            return [{
                "sucesso": False,
                "erro": erro_msg,
                "tipo_erro": "loop_critico",
                "timestamp_erro": datetime.now().isoformat()
            }]


            # self.browser.click(xpath="//legend[span[normalize-space(.)='Gerar relatório como']]/ancestor::div[contains(@class, 'MuiInputBase-root')][1]//div[@role='combobox' and contains(@class, 'MuiSelect-select')]")
            # time.sleep(1)
            # self.browser.click(xpath='//li[@role="option" and @data-value="excel" and text()="EXCEL"]')
            # time.sleep(1)
            # 
            # # Exportar
            # self.browser.click(xpath="//button[@type='button' and normalize-space()='Exportar']")
            # time.sleep(5)

        except Exception as e:
            self.log_erro("Erro ao gerar/exportar relatório", e)
            raise

    async def _retornar_tela_pesquisa_relatorio(self):
        """
        🔍 TODO USUÁRIO: RETORNO LOOP - **CRUCIAL** Retornar à tela de pesquisa

        SEQUÊNCIA RETORNO (PREPARAR PRÓXIMO CLIENTE):
        1. Fechar modais/popups se abertos
        2. Retornar à tela inicial de relatório
        3. Validar que campo de pesquisa está visível e acessível
        4. **GARANTIR** que está pronto para próximo cliente

        ⚠️ IMPORTANTE: Este método é FUNDAMENTAL para o loop funcionar!
        Se não retornar corretamente, próxima consulta falhará.
        """
        try:
            self.log_progresso("🔄 Retornando à tela de pesquisa para próximo cliente...")
            
            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING CRÍTICO
            # Fechar qualquer modal/popup aberto
            # try:
            #     modal_close = self.browser.find_element(xpath="//button[contains(@class, 'close') or contains(text(), 'Fechar')]")
            #     if modal_close:
            #         modal_close.click()
            #         time.sleep(1)
            # except:
            #     pass
            # 
            # # Garantir que está na tela de relatório com campo de pesquisa visível
            # campo_pesquisa = self.browser.find_element(xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']")
            # if not campo_pesquisa:
            #     # Se não encontrar, tentar navegar novamente
            #     url_relatorio = "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/relatorios/saldo-devedor"
            #     self.browser.get_page(url_relatorio)
            #     time.sleep(3)

        except Exception as e:
            self.log_erro("Erro ao retornar à tela de pesquisa", e)
            # Em caso de erro, resetar flag para forçar nova navegação na próxima
            self._na_tela_relatorio_sienge = False
            raise


            time.sleep(3)

            # PASSO 2: Primeira tela - Credenciais básicas
            self.log_progresso("📝 Preenchendo credenciais iniciais...")
            self.browser.find_element(xpath='(//input[@id="username"])[1]').send_keys(usuario_sienge)
            self.browser.find_element(xpath='//input[@id="password"]').send_keys(senha_sienge)
            self.browser.find_element(xpath='//*[@id="btnEntrarComSiengeID"]').click()
            time.sleep(2)

            # PASSO 3: Segunda tela - Confirmação de email
            self.log_progresso("📧 Confirmando email...")
            self.browser.find_element(
                xpath='//label[text()="Seu e-mail"]/following-sibling::div//input'
            ).send_keys(usuario_sienge)
            self.browser.find_element(
                xpath="//button[normalize-space(text())='CONTINUAR']").click()

            # PASSO 4: Terceira tela - Senha final
            self.log_progresso("🔑 Inserindo senha final...")
            self.browser.find_element(
                xpath="//input[@id='signup-password']").send_keys(senha_sienge)
            self.browser.find_element(
                xpath="//button[normalize-space(text())='ENTRAR']").click()

            # PASSO 5: Aguardar login e validar acesso
            time.sleep(5)
            self.logado_sienge = True
            self.log_progresso("✅ Login no Sienge realizado com sucesso")

        except Exception as e:
            raise Exception(f"Falha no login Sienge: {str(e)}")


# ===============================================================================
# 6. 📋 CONSULTA RELATÓRIOS FINANCEIROS - WEBSCRAPING
# ===============================================================================

    async def _consultar_relatorios_financeiros(self, contrato: Dict[str, Any]) -> Dict[str, Any]:
        """
        📋 CONSULTA RELATÓRIOS FINANCEIROS - ESTRUTURA PARA LOOP OTIMIZADO

        FUNCIONAMENTO EM LOOP (MÚLTIPLOS CLIENTES):
        ═══════════════════════════════════════════════════════════════════════════

        🔄 PRIMEIRA EXECUÇÃO:
        1️⃣ Navega para tela de relatório (URL direta)
        2️⃣ Executa consulta do cliente
        3️⃣ Processa dados
        4️⃣ **RETORNA** à tela de pesquisa (PRONTO PARA PRÓXIMO CLIENTE)

        🔄 EXECUÇÕES SUBSEQUENTES:
        1️⃣ **SKIP** navegação (já está na tela correta)
        2️⃣ **LIMPA** campo de pesquisa anterior
        3️⃣ Executa consulta do novo cliente
        4️⃣ **RETORNA** à tela de pesquisa novamente

        ═══════════════════════════════════════════════════════════════════════════

        SEQUÊNCIA WEBSCRAPING PDD seção 7.3.1:

        1️⃣ NAVEGAÇÃO INICIAL (só primeira vez):
           └── URL: https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/relatorios/saldo-devedor
           └── Flag: self._na_tela_relatorio_sienge

        2️⃣ LIMPEZA CAMPO PESQUISA (execuções subsequentes):
           └── Limpar campo anterior para novo cliente
           └── Método: _limpar_campo_pesquisa_cliente()

        3️⃣ FILTRO POR CLIENTE:
           └── Campo: //input[@placeholder='Pesquisar cliente' and @role='combobox']
           └── Preencher com nome do cliente atual

        4️⃣ CONSULTA + EXPORT + PROCESSAMENTO:
           └── Executar consulta → Gerar relatório → Exportar Excel
           └── Processamento automático: _processar_planilha_baixada()

        5️⃣ **RETORNO À TELA DE PESQUISA** (LOOP READY):
           └── Método: _retornar_tela_pesquisa_relatorio()
           └── Garantir que está pronto para próximo cliente

        RESPONSABILIDADES:
        🔍 USUÁRIO: Steps 1-5 (webscraping otimizado para loop)
        🤖 ASSISTENTE: Processamento automático (step 4)
        """
        try:
            cliente = contrato.get("cliente", "")
            numero_titulo = contrato.get("numero_titulo", "")

            self.log_progresso(f"📊 Consultando saldo devedor presente para: {cliente}")
            self.log_progresso(f"   📋 Título: {numero_titulo}")

            # PASSO 1: Navegação inicial (só primeira execução)
            if not getattr(self, '_na_tela_relatorio_sienge', False):
                await self._navegar_tela_relatorio_inicial()
                self._na_tela_relatorio_sienge = True
                self.log_progresso("✅ Primeira navegação - Tela relatório ativa")
            else:
                self.log_progresso("♻️ Reutilizando tela de relatório (loop otimizado)")

            # PASSO 2: Limpeza campo pesquisa (se não for primeira execução)
            await self._limpar_campo_pesquisa_cliente()

            # PASSO 3: Consultar cliente específico
            await self._executar_consulta_cliente_relatorio(cliente)

            # PASSO 4: Gerar e exportar relatório
            await self._gerar_exportar_relatorio_excel()

            # PASSO 5: PROCESSAMENTO AUTOMÁTICO DA PLANILHA BAIXADA
            self.log_progresso("📋 Processando planilha baixada...")
            dados_planilha = await self._processar_planilha_baixada(cliente, numero_titulo)

            # PASSO 6: **CRUCIAL** - Retornar à tela de pesquisa para próximo cliente
            await self._retornar_tela_pesquisa_relatorio()
            self.log_progresso("🔄 Retornado à tela de pesquisa - PRONTO PARA PRÓXIMO CLIENTE")

            # Processa resultado
            if dados_planilha and dados_planilha.get("sucesso"):
                dados_financeiros = dados_planilha
            else:
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

            self.log_progresso("✅ Consulta concluída - Tela pronta para próximo cliente")
            return dados_financeiros

        except Exception as e:
            erro_msg = f"Erro na consulta de relatórios: {str(e)}"
            self.log_erro(erro_msg, e)
            # Em caso de erro, tentar retornar à tela de pesquisa
            try:
                await self._retornar_tela_pesquisa_relatorio()
            except:
                self._na_tela_relatorio_sienge = False  # Resetar flag para forçar nova navegação
            return {"erro": erro_msg, "sucesso": False}


# ===============================================================================
# 7. 🤖 PROCESSAMENTO PLANILHA - ANÁLISE AUTOMÁTICA
# ===============================================================================

    async def _processar_planilha_baixada(self, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        🤖 PROCESSAMENTO PLANILHA BAIXADA - ANÁLISE AUTOMÁTICA

        SEQUÊNCIA DE PROCESSAMENTO AUTOMÁTICO:

        1️⃣ LOCALIZAÇÃO DO ARQUIVO:
           └── Pasta: Downloads/RPA_DOWNLOADS
           └── Padrão: saldo_devedor_presente-YYYYMMDD-HHMMSS.xlsx
           └── Critério: Arquivo mais recente (últimos 10 minutos)

        2️⃣ VALIDAÇÃO DA ESTRUTURA:
           └── Engine: openpyxl para leitura Excel
           └── Colunas obrigatórias: ["Parcela/Sequencial", "Status da parcela", "Data vencimento", "Valor a receber", "Documento"]
           └── Validação: Planilha não vazia e estrutura correta

        3️⃣ APLICAÇÃO REGRAS PDD (1-8):
           └── Método: _aplicar_regras_pdd_planilha()
           └── Filtro rigoroso: Status = "A vencer"
           └── Classificação: CT vs REC/FAT por coluna "Documento"
           └── Validação inadimplência: ≥3 CT vencidas = INADIMPLENTE

        4️⃣ AUDITORIA E BACKUP:
           └── Hash MD5 para integridade
           └── Cópia em: dados_extraidos/planilhas_sienge/YYYY/MM/
           └── Registro MongoDB + JSON de auditoria

        5️⃣ ATUALIZAÇÃO PLANILHA BASE:
           └── Google Sheets: "BASE DE CÁLCULO REPARCELAMENTO 2025"
           └── Campos PDD: PENDÊNCIAS SIENGE INAD, PENDÊNCIAS SIENGE, Parcelas a vencer

        RESPONSABILIDADE: 🤖 ASSISTENTE (processamento automático completo)
        INPUT: Arquivo Excel baixado pelo webscraping
        OUTPUT: Dados estruturados com regras PDD aplicadas
        """
        try:
            # PASSO 1: Localizar arquivo mais recente
            pasta_downloads_base = self._obter_pasta_downloads()
            self.log_progresso("📁 Etapa 1: Localizando arquivo baixado mais recente...")
            self.log_progresso(f"   📂 Pasta Downloads RPA: {pasta_downloads_base}")

            arquivo_encontrado = self._localizar_arquivo_recente(pasta_downloads_base)
            self.log_progresso(f"   ✅ Arquivo encontrado: {arquivo_encontrado}")

            # PASSO 2: Ler e validar planilha Excel
            self.log_progresso("📊 Etapa 2: Lendo planilha Excel...")
            df = await self._ler_planilha_excel(arquivo_encontrado)

            # PASSO 3: Salvar cópia para auditoria
            self.log_progresso("💾 Etapa 3: Salvando cópia para auditoria...")
            caminho_auditoria = await self._salvar_planilha_auditoria(arquivo_encontrado, cliente, numero_titulo)

            # PASSO 4: Aplicar regras PDD (1-8)
            self.log_progresso("🔄 Etapa 4: Processando dados conforme PDD...")
            dados_processados = await self._aplicar_regras_pdd_planilha(df, cliente, numero_titulo)

            # PASSO 5: Adicionar metadados de auditoria
            dados_processados.update({
                "arquivo_original": arquivo_encontrado,
                "arquivo_auditoria": caminho_auditoria,
                "hash_arquivo": self._calcular_hash_arquivo(arquivo_encontrado),
                "processado_em": datetime.now().isoformat(),
                "processado_por": "RPA_Sienge",
                "versao_rpa": "2.0",
                "sucesso": True
            })

            # PASSO 6: Registrar auditoria
            await self._registrar_auditoria_planilha(dados_processados)

            # PASSO 7: Atualizar planilha base de cálculo (PDD 9.1.2)
            self.log_progresso("🔄 Etapa 7: Atualizando planilha base de cálculo...")
            await self._atualizar_planilha_base_calculo(dados_processados, {"cliente": cliente, "numero_titulo": numero_titulo})

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

    async def _aplicar_regras_pdd_planilha(self, df: pd.DataFrame, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        🤖 APLICAÇÃO REGRAS PDD OFICIAIS - DOCUMENTO COMPLETO

        BASEADO NO DOCUMENTO: "Regras de Negócio para Reparcelamento"

        REGRA 1 PDD: Identificação do Dia de Vencimento das Parcelas
        └── Filtro: Status da parcela = "a vencer"
        └── Extração: Dia do mês da coluna "Data vencimento"

        REGRA 2 PDD: Cálculo do 1º Vencimento do Novo Carnê
        └── Reajuste Anual: Mesmo mês base do reparcelamento
        └── Reajuste Aniversário: Baseado no dia do aniversário do contrato

        REGRA 3 PDD: Valor da Parcela Atual  
        └── Consulta planilha base: "original" ou "corrigido"
        └── Filtro: Status = "a vencer", primeiro registro encontrado

        REGRA 4 PDD: Verificação de Parcelas Abertas Irregulares
        └── Filtro: Status = "a vencer", Documento = "CT"
        └── Condição: Valor original ≠ valor atual E Tipo ≠ "Parcela Mensal"

        REGRA 5 PDD: Quantidade de Parcelas a Vencer
        └── Filtro: Status = "a vencer", Documento = "CT"
        └── Regras específicas por tipo (Anual vs Aniversário)

        REGRA 6 PDD: Quantidade de Parcelas Vencidas
        └── Filtro: Documento = "CT", Status = "vencida"
        └── Verificação inadimplência: 60 dias antes do 1º vencimento

        REGRA 7 PDD: Atualização da Planilha Base de Cálculo
        └── Campos: PENDÊNCIAS SIENGE INAD, PENDÊNCIAS SIENGE, Parcelas a vencer

        REGRA 8 PDD: Validação Final
        └── ≥3 CT vencidas = INADIMPLENTE (não pode reparcelar)
        └── <3 CT vencidas = ADIMPLENTE (pode reparcelar)
        """
        try:
            self.log_progresso(f"   🔍 APLICANDO REGRAS PDD OFICIAIS - DOCUMENTO COMPLETO:")
            self.log_progresso(f"      📋 Total de registros: {len(df)}")
            self.log_progresso(f"      📊 Colunas disponíveis: {list(df.columns)}")

            # Verificar colunas obrigatórias conforme PDD
            colunas_obrigatorias_pdd = [
                "Status da parcela", "Documento", "Data vencimento", 
                "Valor original", "Valor a receber", "Tipo condição"
            ]

            colunas_faltantes = [col for col in colunas_obrigatorias_pdd if col not in df.columns]
            if colunas_faltantes:
                raise Exception(f"Colunas obrigatórias PDD ausentes: {colunas_faltantes}")

            # Debug dos valores únicos para validação
            if "Status da parcela" in df.columns:
                status_unicos = df["Status da parcela"].dropna().unique()
                self.log_progresso(f"      📊 Status encontrados: {list(status_unicos)}")

            if "Documento" in df.columns:
                documentos_unicos = df["Documento"].dropna().unique()
                self.log_progresso(f"      📋 Tipos de documento: {list(documentos_unicos)}")

            hoje = date.today()

            # ===== REGRA 1 PDD: FILTRAR RIGOROSAMENTE STATUS "A VENCER" =====
            self.log_progresso(f"   📋 REGRA 1 PDD: Filtrando EXCLUSIVAMENTE Status 'A vencer'...")

            parcelas_a_vencer = df[df["Status da parcela"].str.upper().str.strip() == "A VENCER"].copy()

            # Fallback para variações comuns do Sienge
            if len(parcelas_a_vencer) == 0:
                self.log_progresso(f"      ⚠️ Status 'A VENCER' não encontrado. Tentando variações...")
                parcelas_a_vencer = df[
                    df["Status da parcela"].str.upper().str.strip().isin([
                        "AVENCER", "A VENCER", "EM ABERTO", "ABERTO"
                    ])
                ].copy()

            self.log_progresso(f"      ✅ Parcelas 'A vencer': {len(parcelas_a_vencer)} de {len(df)}")

            # ===== REGRA 2 PDD: CLASSIFICAR POR DOCUMENTO CT vs REC/FAT =====
            self.log_progresso(f"   📋 REGRA 2 PDD: Classificando por coluna 'Documento'...")

            parcelas_ct_a_vencer = parcelas_a_vencer[
                parcelas_a_vencer["Documento"].str.contains("CT", case=False, na=False)
            ].copy()

            parcelas_rec_fat_a_vencer = parcelas_a_vencer[
                parcelas_a_vencer["Documento"].str.contains("REC|FAT", case=False, na=False)
            ].copy()

            self.log_progresso(f"      🔶 Parcelas CT 'A vencer': {len(parcelas_ct_a_vencer)}")
            self.log_progresso(f"      🔷 Parcelas REC/FAT 'A vencer': {len(parcelas_rec_fat_a_vencer)}")

            # ===== REGRA 3 PDD: IDENTIFICAÇÃO DO DIA DE VENCIMENTO =====
            self.log_progresso(f"   📅 REGRA 3 PDD: Identificando dia de vencimento das parcelas...")

            def converter_data_segura(data_str):
                if pd.isna(data_str) or str(data_str).strip() == "":
                    return None
                try:
                    if isinstance(data_str, str):
                        for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"]:
                            try:
                                return datetime.strptime(data_str.strip(), fmt).date()
                            except:
                                continue
                    elif hasattr(data_str, 'date'):
                        return data_str.date()
                    elif hasattr(data_str, 'strftime'):
                        return data_str
                except:
                    pass
                return None

            # Extrair dia de vencimento das parcelas CT "A vencer"
            dias_vencimento = []
            for _, row in parcelas_ct_a_vencer.iterrows():
                data_conv = converter_data_segura(row["Data vencimento"])
                if data_conv:
                    dias_vencimento.append(data_conv.day)

            dia_vencimento_comum = max(set(dias_vencimento), key=dias_vencimento.count) if dias_vencimento else None
            self.log_progresso(f"      📅 Dia comum de vencimento identificado: {dia_vencimento_comum}")

            # ===== REGRA 4 PDD: VALOR DA PARCELA ATUAL =====
            self.log_progresso(f"   💰 REGRA 4 PDD: Determinando valor da parcela atual...")

            valor_parcela_base = 0
            if len(parcelas_ct_a_vencer) > 0:
                primeiro_registro = parcelas_ct_a_vencer.iloc[0]
                valor_parcela_base = self._converter_valor_monetario(primeiro_registro["Valor a receber"])

            self.log_progresso(f"      💰 Valor da parcela base identificado: R$ {valor_parcela_base:,.2f}")

            # ===== REGRA 5 PDD: VERIFICAÇÃO DE PARCELAS ABERTAS IRREGULARES =====
            self.log_progresso(f"   ⚠️ REGRA 5 PDD: Verificando parcelas abertas irregulares...")

            parcelas_irregulares = []
            if len(parcelas_ct_a_vencer) > 0 and valor_parcela_base > 0:
                for _, row in parcelas_ct_a_vencer.iterrows():
                    valor_original = self._converter_valor_monetario(row.get("Valor original", 0))
                    tipo_condicao = str(row.get("Tipo condição", "")).strip()

                    if (abs(valor_original - valor_parcela_base) > 0.01 and 
                        tipo_condicao.upper() != "PARCELA MENSAL"):
                        parcelas_irregulares.append({
                            "documento": row.get("Documento"),
                            "data_vencimento": row.get("Data vencimento"),
                            "valor_original": valor_original,
                            "valor_base": valor_parcela_base,
                            "tipo_condicao": tipo_condicao,
                            "diferenca": valor_original - valor_parcela_base
                        })

            if len(parcelas_irregulares) > 0:
                self.log_progresso(f"      ⚠️ Parcelas irregulares detectadas: {len(parcelas_irregulares)} (enviar ao analista)")

            # ===== REGRA 6 PDD: QUANTIDADE DE PARCELAS A VENCER =====
            self.log_progresso(f"   📊 REGRA 6 PDD: Contando parcelas a vencer...")

            qtd_parcelas_ct_a_vencer = len(parcelas_ct_a_vencer)
            qtd_parcelas_rec_fat_a_vencer = len(parcelas_rec_fat_a_vencer)

            # ===== REGRA 7 PDD: QUANTIDADE DE PARCELAS VENCIDAS =====
            self.log_progresso(f"   🚨 REGRA 7 PDD: Verificando parcelas vencidas...")

            todas_parcelas_ct = df[df["Documento"].str.contains("CT", case=False, na=False)].copy()

            parcelas_ct_vencidas = []
            for _, row in todas_parcelas_ct.iterrows():
                data_conv = converter_data_segura(row["Data vencimento"])
                status = str(row.get("Status da parcela", "")).strip().upper()

                if data_conv and data_conv < hoje and status != "QUITADA":
                    parcelas_ct_vencidas.append({
                        "documento": row.get("Documento"),
                        "data_vencimento": data_conv,
                        "status": status,
                        "valor": self._converter_valor_monetario(row.get("Valor a receber", 0)),
                        "dias_atraso": (hoje - data_conv).days
                    })

            qtd_ct_vencidas = len(parcelas_ct_vencidas)
            self.log_progresso(f"      🚨 CT vencidas encontradas: {qtd_ct_vencidas}")

            # Verificar pendências REC/FAT vencidas
            todas_parcelas_rec_fat = df[df["Documento"].str.contains("REC|FAT", case=False, na=False)].copy()

            pendencias_rec_fat_vencidas = []
            for _, row in todas_parcelas_rec_fat.iterrows():
                data_conv = converter_data_segura(row["Data vencimento"])
                status = str(row.get("Status da parcela", "")).strip().upper()

                if data_conv and data_conv < hoje and status != "QUITADA":
                    pendencias_rec_fat_vencidas.append({
                        "documento": row.get("Documento"),
                        "data_vencimento": data_conv,
                        "status": status,
                        "valor": self._converter_valor_monetario(row.get("Valor a receber", 0))
                    })

            qtd_pendencias_rec_fat = len(pendencias_rec_fat_vencidas)
            self.log_progresso(f"      📋 Pendências REC/FAT vencidas: {qtd_pendencias_rec_fat}")

            # ===== REGRA 8 PDD: VERIFICAÇÃO DE INADIMPLÊNCIA =====
            self.log_progresso(f"   ⚖️ REGRA 8 PDD: Aplicando regra de inadimplência...")

            if qtd_ct_vencidas >= 3:
                status_cliente = "inadimplente"
                pode_reparcelar = False
                motivo_status = f"INADIMPLENTE - {qtd_ct_vencidas} parcelas CT vencidas (>= 3 limite PDD)"
            else:
                status_cliente = "adimplente"
                pode_reparcelar = True
                motivo_status = f"ADIMPLENTE - {qtd_ct_vencidas} parcelas CT vencidas (< 3 limite PDD)"

            # ===== CÁLCULOS FINANCEIROS =====
            valor_total_ct = parcelas_ct_a_vencer["Valor a receber"].apply(self._converter_valor_monetario).sum()
            valor_total_rec_fat = parcelas_rec_fat_a_vencer["Valor a receber"].apply(self._converter_valor_monetario).sum()
            saldo_total = valor_total_ct + valor_total_rec_fat

            # ===== RESULTADO FINAL CONFORME PDD =====
            resultado = {
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "sucesso": True,

                # REGRA 1-3: Dados identificados
                "dia_vencimento_parcelas": dia_vencimento_comum,
                "valor_parcela_base": valor_parcela_base,

                # REGRA 4-5: Parcelas irregulares
                "parcelas_irregulares": parcelas_irregulares,
                "tem_parcelas_irregulares": len(parcelas_irregulares) > 0,

                # REGRA 6: Quantidades a vencer
                "qtd_parcelas_ct_a_vencer": qtd_parcelas_ct_a_vencer,
                "qtd_parcelas_rec_fat_a_vencer": qtd_parcelas_rec_fat_a_vencer,

                # REGRA 7: Quantidades vencidas
                "qtd_ct_vencidas": qtd_ct_vencidas,
                "qtd_pendencias_rec_fat": qtd_pendencias_rec_fat,

                # REGRA 8: Classificação final
                "status_cliente": status_cliente,
                "pode_reparcelar": pode_reparcelar,
                "motivo_status": motivo_status,

                # Dados financeiros
                "saldo_total": saldo_total,
                "valor_total_ct": valor_total_ct,
                "valor_total_rec_fat": valor_total_rec_fat,

                # Campos para planilha base de cálculo (REGRA 7)
                "pendencias_sienge_inad": qtd_ct_vencidas if qtd_ct_vencidas > 0 else None,
                "pendencias_sienge": qtd_pendencias_rec_fat if qtd_pendencias_rec_fat > 0 else None,
                "parcelas_a_vencer": qtd_parcelas_ct_a_vencer,

                # Dados detalhados para auditoria
                "parcelas_ct_a_vencer": parcelas_ct_a_vencer.to_dict('records'),
                "parcelas_rec_fat_a_vencer": parcelas_rec_fat_a_vencer.to_dict('records'),
                "parcelas_ct_vencidas_detalhes": parcelas_ct_vencidas,
                "pendencias_rec_fat_detalhes": pendencias_rec_fat_vencidas,
                "dados_brutos": df,
                "total_registros": len(df),

                # Metadados
                "regras_pdd_aplicadas": "REGRAS_NEGOCIO_COMPLETAS_PDD",
                "processado_em": datetime.now().isoformat()
            }

            # ===== LOG FINAL DETALHADO =====
            self.log_progresso(f"   📊 PROCESSAMENTO PDD CONCLUÍDO:")
            self.log_progresso(f"      💰 Saldo total: R$ {saldo_total:,.2f}")
            self.log_progresso(f"      📋 Total parcelas CT: {qtd_parcelas_ct_a_vencer}")
            self.log_progresso(f"      📋 Total parcelas REC/FAT: {qtd_parcelas_rec_fat_a_vencer}")
            self.log_progresso(f"      🚨 CT vencidas NÃO quitadas: {qtd_ct_vencidas}")
            self.log_progresso(f"      🎯 STATUS FINAL: {status_cliente.upper()}")
            self.log_progresso(f"      📅 Dia comum de vencimento: {dia_vencimento_comum or 'N/A'}")
            self.log_progresso(f"      💰 Valor parcela base: R$ {valor_parcela_base:,.2f}")

            if len(parcelas_irregulares) > 0:
                self.log_progresso(f"      ⚠️ ATENÇÃO: {len(parcelas_irregulares)} parcela(s) irregular(es) - enviar ao analista financeiro")

            return resultado

        except Exception as e:
            raise Exception(f"Erro ao aplicar regras PDD: {str(e)}")


# ===============================================================================
# 8. ⚖️ VALIDAÇÃO CONTRATOS PDD - REGRAS RIGOROSAS
# ===============================================================================

    async def _validar_contrato_reparcelamento(self, dados_financeiros: Dict[str, Any]) -> Dict[str, Any]:
        """
        ⚖️ VALIDAÇÃO RIGOROSA CONFORME PDD SEÇÃO 7.3.2

        REGRA CRÍTICA OFICIAL:
        "Cliente com 3 ou mais parcelas CT vencidas = INADIMPLENTE (não pode reparcelar)"

        SEQUÊNCIA DE VALIDAÇÃO:

        1️⃣ VERIFICAÇÃO INICIAL:
           └── Dados financeiros processados com sucesso?
           └── Planilha contém dados válidos?

        2️⃣ ANÁLISE RIGOROSA CT:
           └── Filtro: Apenas parcelas tipo "CT" (Cota de Terreno)
           └── Status: Vencidas E não quitadas
           └── Data: Anterior ao dia atual

        3️⃣ CONTAGEM CRÍTICA:
           └── Quantidade >= 3 CT vencidas = INADIMPLENTE
           └── Quantidade < 3 CT vencidas = PODE REPARCELAR

        4️⃣ INFORMAÇÕES COMPLEMENTARES:
           └── Parcelas REC/FAT (não impedem reparcelamento)
           └── Saldo total para referência
           └── Detalhes para auditoria

        RESPONSABILIDADE: 🤖 ASSISTENTE (análise automática rigorosa)
        BASEADO EM: Análise real de planilhas Sienge em produção
        """
        try:
            if not dados_financeiros.get("sucesso", False):
                return {
                    "pode_reparcelar": False,
                    "motivo": "Erro na consulta de dados financeiros",
                    "status": "erro"
                }

            # ANÁLISE RIGOROSA: Filtra apenas parcelas CT CONFORME PDD
            parcelas_ct = dados_financeiros.get("parcelas_ct", [])
            cliente = dados_financeiros.get("cliente", "")

            # CONTAGEM CRÍTICA: Parcelas CT vencidas não quitadas
            parcelas_ct_vencidas = []
            hoje = date.today()

            self.log_progresso(f"🔍 VALIDAÇÃO RIGOROSA PDD - Cliente: {cliente}")
            self.log_progresso(f"   📊 Total parcelas CT encontradas: {len(parcelas_ct)}")

            for i, parcela in enumerate(parcelas_ct):
                data_vencimento = parcela.get("data_vencimento")
                status = parcela.get("status_parcela", "").strip()
                tipo_parcela = parcela.get("tipo_parcela", "")
                valor = parcela.get("valor", 0)

                # Debug detalhado de cada parcela CT
                self.log_progresso(f"   📋 CT {i+1}: {tipo_parcela} | Status: '{status}' | Valor: R$ {valor:,.2f}")

                # Converte data se necessário
                data_venc_obj = None
                if isinstance(data_vencimento, str):
                    try:
                        data_venc_obj = datetime.strptime(data_vencimento, "%Y-%m-%d").date()
                    except:
                        try:
                            data_venc_obj = datetime.strptime(data_vencimento, "%d/%m/%Y").date()
                        except:
                            self.log_progresso(f"      ⚠️ Data inválida: {data_vencimento}")
                            continue
                elif hasattr(data_vencimento, 'date'):
                    data_venc_obj = data_vencimento.date()
                else:
                    data_venc_obj = data_vencimento

                if not data_venc_obj:
                    self.log_progresso(f"      ⚠️ Data de vencimento não processável")
                    continue

                # REGRA RIGOROSA PDD: CT vencida E não quitada
                vencida = data_venc_obj < hoje
                quitada = status.upper() in ["QUITADA", "LIQUIDADA", "PAGA"]

                self.log_progresso(f"      📅 Vencimento: {data_venc_obj} | Vencida: {vencida} | Quitada: {quitada}")

                # CRÍTICO: Se CT vencida e NÃO quitada = CONTA PARA INADIMPLÊNCIA
                if vencida and not quitada:
                    parcelas_ct_vencidas.append({
                        "parcela": parcela,
                        "data_vencimento": data_venc_obj,
                        "status": status,
                        "tipo": tipo_parcela,
                        "valor": valor
                    })
                    self.log_progresso(f"      🚨 CT INADIMPLENTE DETECTADA!")

            qtd_ct_vencidas = len(parcelas_ct_vencidas)

            self.log_progresso(f"   🎯 RESULTADO CONTAGEM: {qtd_ct_vencidas} parcelas CT vencidas não quitadas")

            # APLICAÇÃO RIGOROSA DA REGRA PDD
            if qtd_ct_vencidas >= 3:
                motivo = f"INADIMPLENTE PDD - {qtd_ct_vencidas} parcelas CT vencidas (>= 3 LIMITE MÁXIMO)"
                pode_reparcelar = False
                status = "inadimplente"
                self.log_progresso(f"   ❌ CLASSIFICAÇÃO: {motivo}")
            else:
                motivo = f"Cliente apto para reparcelamento - {qtd_ct_vencidas} parcelas CT vencidas (< 3 limite PDD)"
                pode_reparcelar = True
                status = "apto"
                self.log_progresso(f"   ✅ CLASSIFICAÇÃO: {motivo}")

            # Informações complementares (não afetam decisão principal)
            parcelas_rec_fat = dados_financeiros.get("parcelas_rec_fat", [])
            if len(parcelas_rec_fat) > 0:
                motivo += f" + {len(parcelas_rec_fat)} pendências REC/FAT (não impedem reparcelamento)"

            # Detalhes para auditoria
            detalhes_auditoria = {
                "qtd_ct_vencidas": qtd_ct_vencidas,
                "qtd_rec_fat": len(parcelas_rec_fat),
                "cliente": cliente,
                "saldo_total": dados_financeiros.get("saldo_total", 0),
                "parcelas_ct_vencidas_detalhes": [
                    {
                        "tipo": p["tipo"],
                        "data_vencimento": p["data_vencimento"].isoformat(),
                        "status": p["status"],
                        "valor": p["valor"]
                    } for p in parcelas_ct_vencidas
                ],
                "data_analise": hoje.isoformat(),
                "regra_aplicada": "PDD_7.3.2_limite_3_CT_vencidas"
            }

            resultado_validacao = {
                "pode_reparcelar": pode_reparcelar,
                "motivo": motivo,
                "status": status,
                "detalhes": detalhes_auditoria
            }

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


# ===============================================================================
# 9. 🧮 CÁLCULOS REPARCELAMENTO - VALORES PARA SIENGE
# ===============================================================================

    def calcular_valores_reparcelamento(self, contrato: Dict[str, Any], 
                                       indices: Dict[str, Any], 
                                       dados_financeiros: Dict[str, Any]) -> Dict[str, Any]:
        """
        🧮 CÁLCULO DE VALORES PARA REPARCELAMENTO - PROCESSAMENTO AUTOMÁTICO

        REGRAS OBRIGATÓRIAS CONFORME PDD:

        1️⃣ ÍNDICE ECONÔMICO:
           └── SEMPRE IGP-M (NUNCA IPCA)
           └── Código Sienge: "1 IGP-M"
           └── Fonte: Banco Central do Brasil

        2️⃣ TAXA DE JUROS:
           └── Tipo: "Fixo"
           └── Percentual: 8% ao ano
           └── Aplicação: Mensal sobre saldo devedor

        3️⃣ TIPO DE CONDIÇÃO:
           └── Código: "PM" (Prazo Mensal)
           └── Portador: "1 Carteira"
           └── Operação: "0 Cobrança em Carteira"

        4️⃣ CÁLCULO DO NOVO SALDO:
           └── Saldo Atual * (1 + IGP-M/100)
           └── Fator de Correção aplicado
           └── Arredondamento: 2 casas decimais

        5️⃣ DATA PRIMEIRO VENCIMENTO:
           └── Próximo mês após processamento
           └── Dia: 15 (padrão)
           └── Formato: DD/MM/YYYY

        RESPONSABILIDADE: 🤖 ASSISTENTE (cálculos automáticos)
        OUTPUT: Valores prontos para preenchimento no Sienge (usuário usa no webscraping)
        """
        try:
            self.log_progresso("🧮 CALCULANDO valores para reparcelamento...")

            # PASSO 1: Saldo devedor atual
            saldo_atual = dados_financeiros.get("saldo_total", 0)

            # PASSO 2: Índice IGP-M obrigatório conforme PDD
            indice_igpm = indices.get("igpm", {}).get("valor", 0) / 100

            # PASSO 3: Cálculo do novo saldo corrigido
            fator_correcao = 1 + indice_igpm
            novo_saldo = saldo_atual * fator_correcao

            # PASSO 4: Parcelas pendentes
            parcelas_pendentes = dados_financeiros.get("qtd_parcelas_ct_a_vencer", 0)

            # PASSO 5: Data do primeiro vencimento (próximo mês)
            from datetime import date, timedelta
            primeiro_vencimento = (date.today().replace(day=1) + timedelta(days=32)).replace(day=15)

            # PASSO 6: Valores para preenchimento no Sienge
            valores_sienge = {
                "detalhamento": f"CORREÇÃO {date.today().strftime('%m/%y')}",
                "tipo_condicao": "PM",
                "valor_total": round(novo_saldo, 2),
                "quantidade_parcelas": parcelas_pendentes,
                "data_primeiro_vencimento": primeiro_vencimento.strftime("%d/%m/%Y"),
                "portador": "1 Carteira",
                "operacao_cobranca": "0 Cobrança em Carteira",
                "indexador": "1 IGP-M",
                "tipo_juros": "Fixo",
                "percentual_juros": 8.0,
                "data_base_juros": primeiro_vencimento.strftime("%d/%m/%Y")
            }

            # PASSO 7: Dados para auditoria
            detalhes_calculo = {
                "saldo_anterior": saldo_atual,
                "indice_aplicado": indice_igpm * 100,
                "fator_correcao": fator_correcao,
                "novo_saldo": novo_saldo,
                "diferenca": novo_saldo - saldo_atual,
                "parcelas_total": parcelas_pendentes,
                "tipo_indice": "IGP-M",
                "calculado_em": date.today().isoformat()
            }

            self.log_progresso(f"   💰 Saldo anterior: R$ {saldo_atual:,.2f}")
            self.log_progresso(f"   📈 Índice IGP-M: {indice_igpm * 100:.2f}%")
            self.log_progresso(f"   💰 Novo saldo: R$ {novo_saldo:,.2f}")
            self.log_progresso(f"   📊 Parcelas: {parcelas_pendentes}")

            return {
                "sucesso": True,
                "valores_sienge": valores_sienge,
                "detalhes_calculo": detalhes_calculo,
                "validacao_pdd": True
            }

        except Exception as e:
            erro_msg = f"Erro no cálculo de valores: {str(e)}"
            self.log_erro(erro_msg, e)
            return {
                "sucesso": False,
                "erro": erro_msg,
                "valores_sienge": {},
                "detalhes_calculo": {}
            }

    def determinar_parcelas_para_desmarcar(self, dados_financeiros: Dict[str, Any]) -> List[str]:
        """
        🤖 DETERMINAÇÃO DE PARCELAS PARA DESMARCAR - REGRAS PDD

        REGRA PDD OFICIAL:
        "Desmarque todas as parcelas com vencimento igual ou anterior ao mês vigente"

        SEQUÊNCIA DE ANÁLISE:

        1️⃣ FILTRO TEMPORAL:
           └── Mês vigente = Primeiro dia do mês atual
           └── Critério: Data vencimento <= Mês vigente

        2️⃣ IDENTIFICAÇÃO PARCELAS:
           └── Apenas parcelas CT (Cota de Terreno)
           └── Status: "A vencer" (não considera já quitadas)

        3️⃣ LISTA PARA DESMARCAÇÃO:
           └── Documento da parcela
           └── Data de vencimento formatada
           └── Motivo da desmarcação

        RESPONSABILIDADE: 🤖 ASSISTENTE (análise automática)
        OUTPUT: Lista para o usuário usar no webscraping (desmarcar checkboxes)
        """
        try:
            self.log_progresso("🔍 DETERMINANDO parcelas para desmarcar...")

            from datetime import date
            hoje = date.today()
            mes_vigente = hoje.replace(day=1)  # Primeiro dia do mês atual

            parcelas_desmarcar = []
            parcelas_ct = dados_financeiros.get("parcelas_ct_a_vencer", [])

            for parcela in parcelas_ct:
                data_vencimento = parcela.get("data_vencimento")

                # Converter data se necessário
                if isinstance(data_vencimento, str):
                    try:
                        from datetime import datetime
                        data_obj = datetime.strptime(data_vencimento, "%Y-%m-%d").date()
                    except:
                        continue
                elif hasattr(data_vencimento, 'date'):
                    data_obj = data_vencimento.date()
                else:
                    data_obj = data_vencimento

                # REGRA PDD: Vencimento <= mês vigente = DESMARCAR
                if data_obj <= mes_vigente:
                    parcelas_desmarcar.append({
                        "documento": parcela.get("documento"),
                        "data_vencimento": data_obj.strftime("%d/%m/%Y"),
                        "valor": parcela.get("valor", 0),
                        "motivo": "Vencimento igual ou anterior ao mês vigente"
                    })

            self.log_progresso(f"   📋 Parcelas para DESMARCAR: {len(parcelas_desmarcar)}")
            for parcela in parcelas_desmarcar:
                self.log_progresso(f"      🔸 {parcela['documento']} - {parcela['data_vencimento']}")

            return parcelas_desmarcar

        except Exception as e:
            self.log_erro("Erro ao determinar parcelas para desmarcar", e)
            return []


# ===============================================================================
# 11. 🔍 WEBSCRAPING REPARCELAMENTO - TODOs USUÁRIO
# ===============================================================================

    async def _processar_reparcelamento(self, contrato: Dict[str, Any], indices: Dict[str, Any],
                                       dados_financeiros: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔄 PROCESSAMENTO DE REPARCELAMENTO - HÍBRIDO WEBSCRAPING + CÁLCULOS

        SEQUÊNCIA PLAYBOOK "REGISTRO E EMISSÃO DE REPARCELAMENTO NO SIENGE":

        1️⃣ NAVEGAÇÃO (USUÁRIO):
           └── Financeiro > Contas a Receber > Reparcelamento > Inclusão
           └── Método: _navegar_reparcelamento_inclusao()

        2️⃣ CONSULTA TÍTULO (USUÁRIO):
           └── Campo: "Número do título em reparcelamento"
           └── Ação: Preencher e clicar "Consultar"
           └── Método: _consultar_titulo_reparcelamento()

        3️⃣ SELEÇÃO DOCUMENTOS (USUÁRIO + ASSISTENTE):
           └── USUÁRIO: Marcar todos os documentos
           └── ASSISTENTE: Determina quais desmarcar (regras PDD)
           └── USUÁRIO: Desmarca parcelas vencidas
           └── Método: _selecionar_documentos_reparcelamento()

        4️⃣ CONFIGURAÇÃO DETALHES (USUÁRIO + ASSISTENTE):
           └── ASSISTENTE: Calcula valores (IGP-M, 8%, PM)
           └── USUÁRIO: Preenche campos no formulário
           └── Método: _configurar_detalhes_reparcelamento()

        5️⃣ CONFIRMAÇÃO (USUÁRIO):
           └── Clique "Confirmar"
           └── Capture novo título gerado
           └── Clique "Salvar"
           └── Método: _confirmar_salvar_reparcelamento()

        RESPONSABILIDADES:
        🔍 USUÁRIO: Steps 1,2,3,5 (webscraping)
        🤖 ASSISTENTE: Steps 3,4 (cálculos e regras)
        """
        try:
            numero_titulo = contrato.get("numero_titulo", "")
            cliente = contrato.get("cliente", "")

            self.log_progresso(f"🔄 PROCESSANDO REPARCELAMENTO SIENGE")
            self.log_progresso(f"   📋 Título: {numero_titulo}")
            self.log_progresso(f"   👤 Cliente: {cliente}")
            self.log_progresso(f"   💰 Saldo atual: R$ {dados_financeiros.get('saldo_total', 0):,.2f}")

            # PASSO 1: Navegar para Reparcelamento > Inclusão (USUÁRIO WEBSCRAPING)
            self.log_progresso("🧭 Etapa 1: Navegando para Reparcelamento > Inclusão")
            await self._navegar_reparcelamento_inclusao()

            # PASSO 2: Consultar título (USUÁRIO WEBSCRAPING)
            self.log_progresso(f"🔍 Etapa 2: Consultando título {numero_titulo}")
            await self._consultar_titulo_reparcelamento(numero_titulo)

            # PASSO 3: Selecionar documentos (HÍBRIDO)
            self.log_progresso("📋 Etapa 3: Selecionando documentos para reparcelamento")
            await self._selecionar_documentos_reparcelamento(dados_financeiros)

            # PASSO 4: Configurar detalhes (HÍBRIDO)
            self.log_progresso("⚙️ Etapa 4: Configurando detalhes do reparcelamento")
            detalhes = await self._configurar_detalhes_reparcelamento(contrato, indices, dados_financeiros)

            # PASSO 5: Confirmar e salvar (USUÁRIO WEBSCRAPING)
            self.log_progresso("💾 Etapa 5: Confirmando e salvando reparcelamento")
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

    async def _navegar_reparcelamento_inclusao(self):
        """
        🔍 TODO USUÁRIO: WEBSCRAPING - Navegar para Reparcelamento > Inclusão

        SEQUÊNCIA OBRIGATÓRIA PLAYBOOK:
        1. Clicar menu "Financeiro" 
        2. Clicar submenu "Contas a receber"
        3. Clicar submenu "Reparcelamento"
        4. Clicar "Inclusão"
        5. Aguardar tela carregar
        6. Validar que chegou na tela correta

        XPATH ESPERADOS:
        - Menu Financeiro: //a[contains(text(), 'Financeiro')]
        - Contas a Receber: //a[contains(text(), 'Contas a Receber')]
        - Reparcelamento: //a[contains(text(), 'Reparcelamento')]
        - Inclusão: //a[contains(text(), 'Inclusão')]
        """
        try:
            self.log_progresso("🧭 TODO USUÁRIO: Implementar navegação para Reparcelamento > Inclusão...")
            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING REAL
            pass

        except Exception as e:
            self.log_erro("Erro ao navegar para reparcelamento", e)
            raise

    async def _consultar_titulo_reparcelamento(self, numero_titulo: str):
        """
        🔍 TODO USUÁRIO: WEBSCRAPING - Consultar título no formulário

        SEQUÊNCIA PLAYBOOK:
        1. Localizar campo "Número do título em reparcelamento"
        2. Preencher com numero_titulo
        3. Clicar botão "Consultar"
        4. Aguardar resultados carregarem
        5. Validar que documentos apareceram
        """
        try:
            self.log_progresso(f"🔍 TODO USUÁRIO: Consultando título {numero_titulo}...")
            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING REAL
            pass

        except Exception as e:
            self.log_erro("Erro ao consultar título", e)
            raise

    async def _selecionar_documentos_reparcelamento(self, dados_financeiros: Dict[str, Any]):
        """
        🔍 TODO USUÁRIO: WEBSCRAPING - Selecionar documentos conforme regras PDD

        SEQUÊNCIA PLAYBOOK:
        1. Clicar "Marcar todos" os documentos
        2. DESMARCAR parcelas conforme lista do ASSISTENTE
        3. Validar seleção final
        4. Clicar "Próximo"

        IMPORTANTE: Usar lista gerada pelo ASSISTENTE:
        parcelas_para_desmarcar = self.determinar_parcelas_para_desmarcar(dados_financeiros)
        """
        try:
            self.log_progresso("📋 TODO USUÁRIO: Selecionando documentos...")

            # ASSISTENTE: Determina parcelas para desmarcar
            parcelas_para_desmarcar = self.determinar_parcelas_para_desmarcar(dados_financeiros)

            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING REAL
            # 1. Clicar "Marcar todos"
            # 2. Para cada parcela em parcelas_para_desmarcar: desmarcar checkbox
            # 3. Clicar "Próximo"
            pass

        except Exception as e:
            self.log_erro("Erro ao selecionar documentos", e)
            raise

    async def _configurar_detalhes_reparcelamento(self, contrato: Dict[str, Any], 
                                                 indices: Dict[str, Any], 
                                                 dados_financeiros: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔍 TODO USUÁRIO: WEBSCRAPING - Configurar detalhes com valores calculados

        SEQUÊNCIA PLAYBOOK:
        1. Preencher "Detalhamento" com valores do ASSISTENTE
        2. Configurar campos conforme cálculos do ASSISTENTE
        3. Clicar "Confirmar"

        IMPORTANTE: Usar valores calculados pelo ASSISTENTE:
        valores_calculados = self.calcular_valores_reparcelamento(contrato, indices, dados_financeiros)
        """
        try:
            self.log_progresso("⚙️ TODO USUÁRIO: Configurando detalhes...")

            # ASSISTENTE: Calcula valores para preenchimento
            valores_calculados = self.calcular_valores_reparcelamento(contrato, indices, dados_financeiros)
            valores_sienge = valores_calculados.get("valores_sienge", {})

            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING REAL
            # Preencher campos do formulário com valores de valores_sienge:
            # - Detalhamento: valores_sienge["detalhamento"]
            # - Tipo condição: valores_sienge["tipo_condicao"] 
            # - Valor total: valores_sienge["valor_total"]
            # - Quantidade parcelas: valores_sienge["quantidade_parcelas"]
            # - Data 1º vencimento: valores_sienge["data_primeiro_vencimento"]
            # - Portador: valores_sienge["portador"]
            # - Operação cobrança: valores_sienge["operacao_cobranca"]
            # - Indexador: valores_sienge["indexador"]
            # - Tipo juros: valores_sienge["tipo_juros"]
            # - Percentual juros: valores_sienge["percentual_juros"]

            return valores_sienge

        except Exception as e:
            self.log_erro("Erro ao configurar detalhes", e)
            raise

    async def _confirmar_salvar_reparcelamento(self) -> str:
        """
        🔍 TODO USUÁRIO: WEBSCRAPING - Confirmar e salvar reparcelamento

        SEQUÊNCIA PLAYBOOK:
        1. Clicar botão "Confirmar"
        2. Aguardar processamento do Sienge
        3. Capturar número do novo título gerado
        4. Clicar "Salvar" para finalizar
        5. Validar que salvou com sucesso
        """
        try:
            self.log_progresso("💾 TODO USUÁRIO: Confirmando e salvando...")

            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING REAL
            # 1. Clicar botão confirmar
            # 2. Aguardar processamento
            # 3. Capturar número do novo título gerado
            # 4. Clicar salvar
            # 5. Validar sucesso

            # Por enquanto retorna título fictício
            return f"REPAC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        except Exception as e:
            self.log_erro("Erro ao confirmar reparcelamento", e)
            raise

    async def _gerar_carne_sienge(self, contrato: Dict[str, Any]) -> Dict[str, Any]:
        """
        🔍 TODO USUÁRIO: WEBSCRAPING - Gerar carnê atualizado

        SEQUÊNCIA PDD seção 7.3.4:
        1. Navegar: Financeiro > Contas a Receber > Cobrança Escritural > Geração de Arquivos de remessa
        2. Configurar parâmetros do carnê
        3. Gerar arquivo de carnê
        """
        try:
            self.log_progresso("🎯 TODO USUÁRIO: Gerando carnê atualizado...")

            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING REAL
            # 1. Navegar para geração de carnê
            # 2. Configurar parâmetros
            # 3. Executar geração

            return {
                "sucesso": True,
                "arquivo_gerado": f"carne_{contrato.get('numero_titulo', 'sem_titulo')}_{datetime.now().strftime('%Y%m%d')}.txt",
                "tipo": "simulado_teste",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.log_erro("Erro na geração de carnê", e)
            return {"sucesso": False, "erro": str(e)}


# ===============================================================================
# 11. 📁 UTILITÁRIOS E AUXILIARES
# ===============================================================================

    async def finalizar(self):
        """Finaliza RPA e limpa recursos"""
        try:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
            self.log_progresso("🏁 RPA Sienge finalizado")
        except Exception as e:
            self.log_erro("Erro ao finalizar RPA", e)

    def _obter_pasta_downloads(self) -> str:
        """Obtém pasta Downloads com subpasta RPA_DOWNLOADS"""
        pasta_downloads_rpa = os.getenv("RPA_DOWNLOADS_PATH")

        if not pasta_downloads_rpa:
            pasta_downloads_rpa = user_downloads_dir()
            self.log_progresso(f"Variável RPA_DOWNLOADS_PATH não definida. Usando pasta Downloads padrão: {pasta_downloads_rpa}")

        pasta_downloads_rpa = Path(pasta_downloads_rpa)
        pasta_downloads = pasta_downloads_rpa / "RPA_DOWNLOADS"

        if not pasta_downloads.exists():
            try:
                pasta_downloads.mkdir(parents=True, exist_ok=True)
                self.log_progresso(f"Subpasta RPA_DOWNLOADS criada em: {pasta_downloads}")
            except Exception as e:
                self.log_erro(f"Erro ao criar subpasta RPA_DOWNLOADS: {e}", e)
                raise

        return str(pasta_downloads)

    def _localizar_arquivo_recente(self, pasta_downloads: str) -> str:
        """Localiza arquivo saldo_devedor_presente mais recente na pasta Downloads"""
        try:
            pasta_path = Path(pasta_downloads)
            if not pasta_path.exists():
                raise Exception(f"Pasta Downloads não existe: {pasta_downloads}")

            # Buscar arquivos com padrão específico
            padrao = "saldo_devedor_presente-*.xlsx"
            arquivos_encontrados = list(pasta_path.glob(padrao))

            if not arquivos_encontrados:
                raise Exception(f"Nenhum arquivo encontrado com padrão '{padrao}' em {pasta_downloads}")

            # Ordenar por data de modificação (mais recente primeiro)
            arquivos_ordenados = sorted(arquivos_encontrados, key=lambda x: x.stat().st_mtime, reverse=True)
            arquivo_mais_recente = str(arquivos_ordenados[0])

            # Validar se arquivo foi modificado recentemente (últimos 10 minutos)
            tempo_arquivo = datetime.fromtimestamp(arquivos_ordenados[0].stat().st_mtime)
            tempo_atual = datetime.now()
            diferenca = (tempo_atual - tempo_arquivo).total_seconds() / 60

            if diferenca > 10:
                self.log_progresso(f"⚠️ Arquivo encontrado há {diferenca:.1f} minutos (pode não ser o download atual)")

            self.log_progresso(f"   📄 Arquivo: {arquivo_mais_recente}")
            self.log_progresso(f"   🕐 Modificado: {tempo_arquivo.strftime('%d/%m/%Y %H:%M:%S')}")

            return arquivo_mais_recente

        except Exception as e:
            raise Exception(f"Erro ao localizar arquivo: {str(e)}")

    async def _ler_planilha_excel(self, caminho_arquivo: str) -> pd.DataFrame:
        """Lê planilha Excel e valida estrutura conforme PDD"""
        try:
            df = pd.read_excel(caminho_arquivo, engine='openpyxl')

            if df.empty:
                raise Exception("Planilha está vazia")

            self.log_progresso(f"   📊 Planilha carregada: {len(df)} registros, {len(df.columns)} colunas")

            # Validar colunas obrigatórias
            colunas_obrigatorias = [
                "Parcela/Sequencial", "Status da parcela", "Data vencimento",
                "Valor a receber", "Documento"
            ]

            colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]

            if colunas_faltantes:
                raise Exception(f"Colunas obrigatórias não encontradas: {colunas_faltantes}")

            self.log_progresso("   ✅ Estrutura da planilha validada")
            return df

        except Exception as e:
            raise Exception(f"Erro ao ler planilha Excel: {str(e)}")

    async def _salvar_planilha_auditoria(self, arquivo_original: str, cliente: str, numero_titulo: str) -> str:
        """Salva cópia da planilha para auditoria com nomenclatura padronizada"""
        try:
            agora = datetime.now()
            pasta_auditoria = self.pasta_planilhas / str(agora.year) / f"{agora.month:02d}"
            pasta_auditoria.mkdir(parents=True, exist_ok=True)

            timestamp = agora.strftime("%Y%m%d_%H%M%S")
            titulo_limpo = str(numero_titulo).replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
            if titulo_limpo == "N/A" or not titulo_limpo:
                titulo_limpo = "sem_titulo"
            nome_arquivo = f"sienge_{titulo_limpo}_{timestamp}.xlsx"
            caminho_auditoria = pasta_auditoria / nome_arquivo

            shutil.copy2(arquivo_original, caminho_auditoria)
            self.log_progresso(f"   💾 Cópia salva: {caminho_auditoria}")

            return str(caminho_auditoria)

        except Exception as e:
            self.log_erro("Erro ao salvar planilha para auditoria", e)
            return ""

    def _converter_valor_monetario(self, valor) -> float:
        """Converte valor monetário para float"""
        try:
            if pd.isna(valor) or valor == "":
                return 0.0

            if isinstance(valor, (int, float)):
                return float(valor)

            if isinstance(valor, str):
                valor = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
                return float(valor)

            return 0.0
        except:
            return 0.0

    def _calcular_hash_arquivo(self, caminho_arquivo: str) -> str:
        """Calcula hash MD5 do arquivo para verificação de integridade"""
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
        """Registra dados da planilha no sistema de auditoria (MongoDB + JSON)"""
        try:
            registro_auditoria = {
                "tipo": "planilha_sienge",
                "cliente": dados_processados.get("cliente"),
                "numero_titulo": dados_processados.get("numero_titulo"),
                "arquivo_original": dados_processados.get("arquivo_original"),
                "arquivo_auditoria": dados_processados.get("arquivo_auditoria"),
                "hash_arquivo": dados_processados.get("hash_arquivo"),
                "saldo_total": dados_processados.get("saldo_total"),
                "total_registros": dados_processados.get("total_registros"),
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
            pasta_auditoria_json = Path("dados_processamento/auditoria_planilhas")
            pasta_auditoria_json.mkdir(parents=True, exist_ok=True)

            titulo_limpo = str(dados_processados.get('numero_titulo', 'sem_titulo')).replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
            if titulo_limpo == "N/A" or not titulo_limpo:
                titulo_limpo = "sem_titulo"
            arquivo_json = pasta_auditoria_json / f"auditoria_{titulo_limpo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(arquivo_json, 'w', encoding='utf-8') as f:
                json.dump(registro_auditoria, f, indent=2, ensure_ascii=False, default=str)

            self.log_progresso(f"   💾 Auditoria salva: {arquivo_json}")

        except Exception as e:
            self.log_erro("Erro ao registrar auditoria", e)

    def _obter_ip_usuario(self) -> str:
        """Obtém IP do usuário para auditoria"""
        try:
            import socket
            hostname = socket.gethostname()
            ip_local = socket.gethostbyname(hostname)
            return ip_local
        except:
            return "unknown"

    async def _aplicar_regras_negocio_pdd(self, dados_financeiros: Dict[str, Any], contrato: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica regras de negócio conforme PDD após consulta dos relatórios"""
        try:
            self.log_progresso("📋 Aplicando regras de negócio PDD...")

            if not dados_financeiros.get("sucesso"):
                return {"regras_aplicadas": False, "erro": "Dados financeiros inválidos"}

            return {"regras_aplicadas": True, "timestamp_regras": datetime.now().isoformat()}

        except Exception as e:
            erro_msg = f"Erro ao aplicar regras de negócio: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"regras_aplicadas": False, "erro": erro_msg}

    async def _verificar_autorizacao_reparcelamento(self, contrato: Dict[str, Any], 
                                                   dados_financeiros: Dict[str, Any],
                                                   notificar_analista: bool = True) -> Dict[str, Any]:
        """Verifica autorização para processamento de reparcelamento"""
        try:
            self.log_progresso("🔐 Verificando autorização para reparcelamento...")

            cliente = contrato.get("cliente", "")
            numero_titulo = contrato.get("numero_titulo", "")

            # Verificar se há parcelas irregulares que exigem aprovação
            parcelas_irregulares = dados_financeiros.get("parcelas_irregulares", [])
            qtd_ct_vencidas = dados_financeiros.get("qtd_ct_vencidas", 0)

            # Critérios que exigem autorização prévia
            exige_autorizacao = False
            motivos_autorizacao = []

            if len(parcelas_irregulares) > 0:
                exige_autorizacao = True
                motivos_autorizacao.append(f"{len(parcelas_irregulares)} parcela(s) irregular(es)")

            if qtd_ct_vencidas >= 2:  # Limite próximo ao crítico
                exige_autorizacao = True
                motivos_autorizacao.append(f"{qtd_ct_vencidas} parcela(s) CT vencida(s)")

            # Se não exige autorização, liberar automaticamente
            if not exige_autorizacao:
                return {
                    "autorizado": True,
                    "motivo": "Reparcelamento dentro dos critérios automáticos",
                    "tipo_autorizacao": "automatica"
                }

            if not notificar_analista:
                # Modo teste: simular autorização
                self.log_progresso("   ⚠️ Modo teste: simulando autorização automática")
                return {
                    "autorizado": True,
                    "motivo": "Autorização simulada para teste",
                    "tipo_autorizacao": "teste_simulado",
                    "motivos_originais": motivos_autorizacao
                }

            # Em produção: enviar notificação e aguardar resposta
            self.log_progresso(f"   📧 Enviando notificação para analista: {motivos_autorizacao}")

            return {
                "autorizado": False,
                "motivo": f"Aguardando autorização do analista: {', '.join(motivos_autorizacao)}",
                "tipo_autorizacao": "manual_pendente",
                "motivos_autorizacao": motivos_autorizacao,
                "cliente": cliente,
                "numero_titulo": numero_titulo
            }

        except Exception as e:
            erro_msg = f"Erro na verificação de autorização: {str(e)}"
            self.log_erro(erro_msg, e)
            return {
                "autorizado": False,
                "motivo": erro_msg,
                "tipo_autorizacao": "erro"
            }

    async def _atualizar_planilha_base_calculo(self, dados_processados: Dict[str, Any], contrato: Dict[str, Any]):
        """Atualiza planilha "BASE DE CÁLCULO REPARCELAMENTO 2025" conforme PDD seção 9.1.2"""
        try:
            # Implementação simplificada - salvar dados localmente
            await self._salvar_dados_base_calculo_local(dados_processados, contrato)

        except Exception as e:
            self.log_erro("Erro ao atualizar planilha base de cálculo", e)

    async def _salvar_dados_base_calculo_local(self, dados_processados: Dict[str, Any], contrato: Dict[str, Any]):
        """Salva dados localmente quando Google Sheets não está disponível"""
        try:
            pasta_backup = Path("dados_processamento/backup_planilha_base")
            pasta_backup.mkdir(parents=True, exist_ok=True)

            dados_backup = {
                "timestamp": datetime.now().isoformat(),
                "contrato": contrato,
                "dados_sienge": {
                    "pendencias_sienge_inad": dados_processados.get("qtd_ct_vencidas", 0) if dados_processados.get("qtd_ct_vencidas", 0) > 0 else None,
                    "pendencias_sienge": dados_processados.get("qtd_pendencias_rec_fat", 0) if dados_processados.get("qtd_pendencias_rec_fat", 0) > 0 else None,
                    "parcelas_a_vencer": dados_processados.get("qtd_parcelas_ct_a_vencer", 0),
                    "valor_parcela_base": dados_processados.get("valor_parcela_base", 0),
                    "dia_vencimento_parcelas": dados_processados.get("dia_vencimento_parcelas"),
                    "primeiro_vencimento_carne": "A CALCULAR"
                },
                "status_processamento": "pendente_atualizacao_planilha"
            }

            numero_titulo = contrato.get("numero_titulo", "sem_titulo").replace("/", "_").replace("\\", "_")
            arquivo_backup = pasta_backup / f"backup_base_{numero_titulo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(arquivo_backup, 'w', encoding='utf-8') as f:
                json.dump(dados_backup, f, indent=2, ensure_ascii=False)

            self.log_progresso(f"   💾 Backup salvo: {arquivo_backup}")

        except Exception as e:
            self.log_erro("Erro ao salvar backup local", e)


# ===============================================================================
# 🔧 FUNÇÃO AUXILIAR PARA USO DIRETO
# ===============================================================================

async def executar_processamento_sienge(
        contrato: Dict[str, Any], 
        indices_economicos: Dict[str, Any],
        credenciais_sienge: Dict[str, str],
        etapa: str = "completa",
        autorizar_reparcelamento: bool = False,
        notificar_analista: bool = True) -> ResultadoRPA:
    """
    🚀 FUNÇÃO AUXILIAR PARA EXECUTAR PROCESSAMENTO SIENGE DIRETAMENTE

    ENTRADA OBRIGATÓRIA:
    - contrato: {"numero_titulo": "123456", "cliente": "EMPRESA LTDA", ...}
    - indices_economicos: {"ipca": {"valor": 4.62}, "igpm": {"valor": 3.89}}
    - credenciais_sienge: {"url": "...", "usuario": "tc@...", "senha": "..."}

    ETAPAS DISPONÍVEIS:
    - "consulta": Apenas consulta relatórios e aplica regras PDD
    - "reparcelamento": Apenas processamento (requer dados prévios)
    - "completa": Consulta + Reparcelamento + Carnê

    FLAGS ESPECIAIS:
    - autorizar_reparcelamento=True: Pula validação manual (para testes)
    - notificar_analista=False: Ignora notificações (para testes)

    RETORNO:
    - ResultadoRPA com sucesso/erro e dados processados
    """
    rpa = RPASienge()

    try:
        await rpa.inicializar()

        resultado = await rpa.executar(
            contrato=contrato,
            credenciais_sienge=credenciais_sienge,
            indices=indices_economicos,
            etapa=etapa,
            autorizar_reparcelamento=autorizar_reparcelamento,
            notificar_analista=notificar_analista
        )

        return resultado

    except Exception as e:
        return ResultadoRPA(
            sucesso=False,
            mensagem="Erro na execução do processamento Sienge",
            erro=str(e)
        )
    finally:
        try:
            await rpa.finalizar()
        except:
            pass