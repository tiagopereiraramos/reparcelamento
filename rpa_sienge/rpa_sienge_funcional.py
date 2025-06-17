"""
RPA Sienge - Versão Funcional Restaurada
Sistema automatizado para processamento de reparcelamento no Sienge ERP
com aplicação rigorosa das regras PDD 7.3.2

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
from rpa_sienge.validador_inadimplencia_pdd import ValidadorInadimplenciaPDD, CalculadoraReparcelamentoPDD

# Selenium imports necessários
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from platformdirs import user_downloads_dir

load_dotenv()

class RPASienge(BaseRPA):
    """
    RPA para processamento de reparcelamento no sistema Sienge
    Implementa as regras do PDD seção 7.3

    RESPONSABILIDADES:
    - USUÁRIO: Webscraping (métodos _navegar_*, _consultar_*, _configurar_*)
    - ASSISTENTE: Processamento (_processar_*, _validar_*, _calcular_*, _aplicar_regras_*)
    """

    def __init__(self):
        super().__init__(nome_rpa="Sienge", usar_browser=True)
        self.logado_sienge = False
        self.credenciais_sienge = {}
        self.pasta_planilhas = Path("dados_extraidos/planilhas_sienge")
        self.pasta_planilhas.mkdir(parents=True, exist_ok=True)
        self.validador_pdd = ValidadorInadimplenciaPDD()
        self.calculadora_pdd = CalculadoraReparcelamentoPDD()

    def _configurar_credenciais(self, credenciais: Dict[str, str]):
        """Configura credenciais do Sienge"""
        self.credenciais_sienge = {
            "url": credenciais.get("url", ""),
            "usuario": credenciais.get("usuario", ""),
            "senha": credenciais.get("senha", ""),
            "empresa": credenciais.get("empresa", "")
        }

    async def executar(self, parametros: Dict[str, Any]) -> ResultadoRPA:
        """
        Executa processo completo de reparcelamento no Sienge
        
        Args:
            parametros: {
                "contrato": str - Número do contrato
                "cliente": str - Nome do cliente  
                "numero_titulo": str - Número do título
                "indice_igpm": float - Índice IGP-M atual
                "credenciais": Dict[str, str] - Credenciais Sienge
            }
        """
        try:
            # VALIDAR PARÂMETROS
            contrato = parametros.get("contrato")
            cliente = parametros.get("cliente")
            numero_titulo = parametros.get("numero_titulo")
            indice_igpm = parametros.get("indice_igpm", 0.0)
            credenciais = parametros.get("credenciais", {})
            
            if not all([contrato, cliente, numero_titulo]):
                raise ValueError("Parâmetros obrigatórios: contrato, cliente, numero_titulo")
            
            self._configurar_credenciais(credenciais)
            
            # EXECUTAR PROCESSO PRINCIPAL
            self.log_info(f"Iniciando reparcelamento - Cliente: {cliente}, Título: {numero_titulo}")
            
            # ETAPA 1: Login no Sienge (USUÁRIO)
            await self._fazer_login_sienge()
            
            # ETAPA 2: Consultar relatório saldo devedor (USUÁRIO + ASSISTENTE)
            planilha_cliente = await self._consultar_relatorio_saldo_devedor(cliente, numero_titulo)
            
            # ETAPA 3: Processar dados aplicando regras PDD (ASSISTENTE)
            resultado_processamento = await self._processar_planilha_cliente(
                planilha_cliente, cliente, numero_titulo, indice_igpm
            )
            
            if not resultado_processamento["pode_reparcelar"]:
                self.log_info(f"Cliente não pode reparcelar: {resultado_processamento['motivo_classificacao']}")
                return ResultadoRPA(
                    sucesso=False,
                    mensagem=f"Cliente inadimplente - não pode reparcelar",
                    dados=resultado_processamento
                )
            
            # ETAPA 4: Registrar reparcelamento (USUÁRIO)
            resultado_registro = await self._registrar_reparcelamento_sienge(
                resultado_processamento["dados_reparcelamento"]
            )
            
            # ETAPA 5: Emitir carnê atualizado (USUÁRIO)
            if resultado_registro["sucesso"]:
                resultado_carne = await self._emitir_carne_atualizado(cliente)
                resultado_processamento["carne_emitido"] = resultado_carne
            
            self.log_info(f"Reparcelamento concluído com sucesso - Cliente: {cliente}")
            
            return ResultadoRPA(
                sucesso=True,
                mensagem=f"Reparcelamento processado com sucesso - Cliente: {cliente}",
                dados=resultado_processamento
            )
            
        except Exception as e:
            erro_msg = f"Erro na execução do RPA Sienge: {str(e)}"
            self.log_erro(erro_msg, e)
            return ResultadoRPA(sucesso=False, mensagem="Falha na execução do RPA Sienge", erro=erro_msg)

    async def _fazer_login_sienge(self):
        """
        Faz login no sistema Sienge conforme PDD seção 7.3
        WEBSCRAPING FUNCIONAL IMPLEMENTADO
        """
        try:
            url_sienge = self.credenciais_sienge.get("url", "")
            usuario_sienge = self.credenciais_sienge.get("usuario", "")
            senha_sienge = self.credenciais_sienge.get("senha", "")

            self.log_progresso(f"Acessando sistema Sienge: {url_sienge}")

            if not url_sienge:
                raise ValueError("URL do Sienge não foi configurada corretamente.")

            self.get_page(url_sienge)
            time.sleep(3)

            # WEBSCRAPING REAL - Sequência de login conforme PDD:
            # 1. Informar usuário
            # 2. Clicar em Continuar
            # 3. Informar senha
            # 4. Clicar em Entrar
            # 5. Fechar caixas de mensagem

            # Preenche usuário inicial
            self.find_element(xpath='(//input[@id="username"])[1]').send_keys(usuario_sienge)

            # Preenche senha inicial
            self.find_element(xpath='//input[@id="password"]').send_keys(senha_sienge)

            # Clica botão entrar inicial
            self.find_element(xpath='//*[@id="btnEntrarComSiengeID"]').click()
            time.sleep(2)

            # Segunda etapa - email
            self.find_element(
                xpath='//label[text()="Seu e-mail"]/following-sibling::div//input'
            ).send_keys(usuario_sienge)

            # Clica continuar
            self.find_element(xpath="//button[normalize-space(text())='CONTINUAR']").click()

            # Terceira etapa - senha final
            self.find_element(xpath="//input[@id='signup-password']").send_keys(senha_sienge)

            # Clica entrar final
            self.find_element(xpath="//button[normalize-space(text())='ENTRAR']").click()

            # Login bem-sucedido
            self.logado_sienge = True
            self.log_progresso("Login no Sienge realizado com sucesso")

        except Exception as e:
            raise Exception(f"Falha no login Sienge: {str(e)}")

    async def _consultar_relatorio_saldo_devedor(self, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        Consulta relatório de saldo devedor no Sienge
        WEBSCRAPING FUNCIONAL IMPLEMENTADO
        """
        try:
            self.log_progresso(f"Consultando saldo devedor presente para: {cliente}")
            
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
                combo_pesquisa.click()
                time.sleep(3)

                # Preenche nome do cliente
                self.send_text(
                    xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']",
                    text=cliente)

                combo_pesquisa.click()
                time.sleep(1)
                combo_pesquisa.send_keys(Keys.TAB)
                time.sleep(1)

                # WEBSCRAPING REAL - Clica em Consultar
                self.log_progresso("Executando consulta...")
                self.click(xpath="//button[normalize-space()='Consultar']")
                time.sleep(3)

                # WEBSCRAPING REAL - Gera relatório
                self.log_progresso("Gerando relatório...")
                self.click(xpath="//button[@type='button' and contains(., 'Gerar Relatório')]")
                time.sleep(2)

                # WEBSCRAPING REAL - Seleciona formato Excel
                self.log_progresso("Selecionando formato Excel...")
                self.click(
                    xpath="//legend[span[normalize-space(.)='Gerar relatório como']]/ancestor::div[contains(@class, 'MuiInputBase-root')][1]//div[@role='combobox' and contains(@class, 'MuiSelect-select')]"
                )
                time.sleep(1)

                self.click(xpath='//li[@role="option" and @data-value="excel" and text()="EXCEL"]')
                time.sleep(1)

                # WEBSCRAPING REAL - Exporta relatório
                self.log_progresso("Exportando relatório...")
                self.click(xpath="//button[@type='button' and normalize-space()='Exportar']")
                time.sleep(5)

                # PROCESSAMENTO DA PLANILHA BAIXADA
                self.log_progresso("Processando planilha baixada...")
                dados_planilha = await self._processar_planilha_baixada(cliente, numero_titulo)

                return dados_planilha

        except Exception as e:
            erro_msg = f"Erro na consulta de relatórios: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"erro": erro_msg, "sucesso": False}

    async def _processar_planilha_baixada(self, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        Processa planilha Excel baixada do Sienge aplicando regras PDD
        PROCESSAMENTO RIGOROSO IMPLEMENTADO PELO ASSISTENTE
        """
        try:
            # Localizar arquivo baixado mais recente
            downloads_dir = user_downloads_dir()
            arquivos_excel = list(Path(downloads_dir).glob("*.xlsx"))
            
            if not arquivos_excel:
                return {"sucesso": False, "erro": "Nenhuma planilha encontrada na pasta de downloads"}
            
            # Arquivo mais recente
            arquivo_mais_recente = max(arquivos_excel, key=lambda x: x.stat().st_mtime)
            
            self.log_progresso(f"Processando arquivo: {arquivo_mais_recente.name}")
            
            # Ler planilha Excel
            df = pd.read_excel(arquivo_mais_recente)
            
            # Salvar cópia na pasta do projeto
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_destino = self.pasta_planilhas / f"sienge_{cliente.replace(' ', '_')}_{timestamp}.xlsx"
            shutil.copy2(arquivo_mais_recente, arquivo_destino)
            
            # APLICAR VALIDAÇÃO PDD RIGOROSA
            resultado_validacao = self.validador_pdd.validar_inadimplencia(df)
            
            self.log_progresso(f"Validação PDD concluída:")
            self.log_progresso(f"  Status: {resultado_validacao['status_cliente']}")
            self.log_progresso(f"  Parcelas CT vencidas: {resultado_validacao['detalhes']['qtd_ct_vencidas']}")
            self.log_progresso(f"  Pode reparcelar: {resultado_validacao['pode_reparcelar']}")
            
            return {
                "sucesso": True,
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "arquivo_processado": str(arquivo_destino),
                "dados_validacao": resultado_validacao,
                "planilha_bruta": df.to_dict('records') if len(df) < 1000 else "Planilha muito grande - dados resumidos",
                "timestamp_processamento": datetime.now().isoformat()
            }
            
        except Exception as e:
            erro_msg = f"Erro no processamento da planilha: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"sucesso": False, "erro": erro_msg}

    async def _processar_planilha_cliente(self, dados_planilha: Dict[str, Any], cliente: str, numero_titulo: str, indice_igpm: float) -> Dict[str, Any]:
        """
        Processa dados do cliente aplicando regras PDD e calculando reparcelamento
        PROCESSAMENTO COMPLETO IMPLEMENTADO PELO ASSISTENTE
        """
        try:
            if not dados_planilha.get("sucesso"):
                return {
                    "pode_reparcelar": False,
                    "motivo_classificacao": "Erro no processamento da planilha",
                    "dados_reparcelamento": None
                }
            
            resultado_validacao = dados_planilha["dados_validacao"]
            
            # VERIFICAR SE PODE REPARCELAR
            if not resultado_validacao["pode_reparcelar"]:
                return {
                    "pode_reparcelar": False,
                    "motivo_classificacao": resultado_validacao["motivo_classificacao"],
                    "detalhes_inadimplencia": resultado_validacao["detalhes"],
                    "dados_reparcelamento": None
                }
            
            # CALCULAR REPARCELAMENTO
            self.log_progresso("Cliente apto - calculando reparcelamento...")
            
            # Extrair dados necessários para cálculo
            parcelas_pendentes = resultado_validacao["detalhes"]["parcelas_para_reparcelar"]
            
            resultado_calculo = self.calculadora_pdd.calcular_reparcelamento({
                "parcelas_pendentes": parcelas_pendentes,
                "indice_igpm": indice_igpm,
                "cliente": cliente,
                "numero_titulo": numero_titulo
            })
            
            self.log_progresso(f"Cálculo concluído:")
            self.log_progresso(f"  Valor original: R$ {resultado_calculo['valor_original']:,.2f}")
            self.log_progresso(f"  Valor corrigido: R$ {resultado_calculo['valor_total_corrigido']:,.2f}")
            self.log_progresso(f"  Novas parcelas: {resultado_calculo['quantidade_parcelas_novas']}")
            
            return {
                "pode_reparcelar": True,
                "motivo_classificacao": "Cliente apto para reparcelamento",
                "dados_reparcelamento": resultado_calculo,
                "detalhes_validacao": resultado_validacao["detalhes"],
                "arquivo_planilha": dados_planilha["arquivo_processado"]
            }
            
        except Exception as e:
            erro_msg = f"Erro no processamento do cliente: {str(e)}"
            self.log_erro(erro_msg, e)
            return {
                "pode_reparcelar": False,
                "motivo_classificacao": f"Erro no processamento: {erro_msg}",
                "dados_reparcelamento": None
            }

    async def _registrar_reparcelamento_sienge(self, dados_reparcelamento: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registra reparcelamento no sistema Sienge
        WEBSCRAPING PARA IMPLEMENTAÇÃO PELO USUÁRIO
        """
        try:
            self.log_progresso("Registrando reparcelamento no Sienge...")
            
            # TODO USUÁRIO: Implementar navegação e preenchimento do formulário de reparcelamento
            # URL esperada: /financeiro/contas-receber/reparcelamento
            # Campos: parcelas a desmarcar, novos valores, novas datas
            
            # SIMULAÇÃO TEMPORÁRIA - REMOVER QUANDO WEBSCRAPING ESTIVER PRONTO
            time.sleep(2)
            
            return {
                "sucesso": True,
                "mensagem": "Reparcelamento registrado com sucesso",
                "numero_reparcelamento": f"REPAR_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            erro_msg = f"Erro no registro do reparcelamento: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"sucesso": False, "erro": erro_msg}

    async def _emitir_carne_atualizado(self, cliente: str) -> Dict[str, Any]:
        """
        Emite carnê atualizado após reparcelamento
        WEBSCRAPING PARA IMPLEMENTAÇÃO PELO USUÁRIO
        """
        try:
            self.log_progresso("Emitindo carnê atualizado...")
            
            # TODO USUÁRIO: Implementar navegação e emissão de carnê
            # URL esperada: /financeiro/contas-receber/carne
            
            # SIMULAÇÃO TEMPORÁRIA - REMOVER QUANDO WEBSCRAPING ESTIVER PRONTO
            time.sleep(2)
            
            return {
                "sucesso": True,
                "mensagem": "Carnê emitido com sucesso",
                "arquivo_carne": f"carne_{cliente.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            erro_msg = f"Erro na emissão do carnê: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"sucesso": False, "erro": erro_msg}

    async def finalizar(self):
        """Finaliza RPA e limpa recursos"""
        try:
            self.log_progresso("RPA Sienge finalizado")
        except Exception as e:
            self.log_erro("Erro ao finalizar RPA", e)


# Função de teste
async def testar_rpa_sienge():
    """Teste básico do RPA Sienge"""
    rpa = RPASienge()
    
    try:
        await rpa.inicializar()
        
        parametros_teste = {
            "contrato": "12345",
            "cliente": "CLIENTE TESTE",
            "numero_titulo": "CT001",
            "indice_igpm": 0.52,
            "credenciais": {
                "url": "https://jmservicos.sienge.com.br",
                "usuario": "usuario_teste",
                "senha": "senha_teste"
            }
        }
        
        resultado = await rpa.executar(parametros_teste)
        print(f"Resultado: {resultado.mensagem}")
        print(f"Sucesso: {resultado.sucesso}")
        
    finally:
        await rpa.finalizar()

if __name__ == "__main__":
    import asyncio
    asyncio.run(testar_rpa_sienge())