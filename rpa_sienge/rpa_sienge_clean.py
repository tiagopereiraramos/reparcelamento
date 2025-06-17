"""
RPA SIENGE - REPARCELAMENTO PDD
Sistema automatizado para processamento de reparcelamento no Sienge ERP
com aplicação rigorosa das regras PDD 7.3.2

DIVISÃO DE RESPONSABILIDADES:
- USUÁRIO: Webscraping (navegação, consultas, preenchimento de formulários)
- ASSISTENTE: Regras de negócio PDD, processamento de dados, cálculos

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
from .validador_inadimplencia_pdd import ValidadorInadimplenciaPDD, CalculadoraReparcelamentoPDD

load_dotenv()

class RPASienge(BaseRPA):
    """
    RPA para processamento de reparcelamento no Sienge ERP
    
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
        """Configura credenciais do Sienge conforme PDD"""
        self.credenciais_sienge = credenciais
        self.log_info("Credenciais Sienge configuradas")

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
                self.log_aviso(f"Cliente não pode reparcelar: {resultado_processamento['motivo_classificacao']}")
                return ResultadoRPA(
                    sucesso=False,
                    mensagem=f"Cliente inadimplente: {resultado_processamento['motivo_classificacao']}",
                    dados=resultado_processamento
                )
            
            # ETAPA 4: Executar reparcelamento no Sienge (USUÁRIO)
            resultado_reparcelamento = await self._executar_reparcelamento_sienge(resultado_processamento)
            
            # CONSOLIDAR RESULTADO FINAL
            dados_finais = {
                **resultado_processamento,
                **resultado_reparcelamento,
                "contrato": contrato,
                "processamento_completo": True,
                "timestamp_final": datetime.now().isoformat()
            }
            
            mensagem_sucesso = f"Reparcelamento concluído - Cliente: {cliente}, Status: {resultado_processamento['status_cliente']}"
            self.log_sucesso(mensagem_sucesso)
            
            return ResultadoRPA(
                sucesso=True,
                mensagem=mensagem_sucesso,
                dados=dados_finais
            )
            
        except Exception as e:
            erro_msg = f"Erro no reparcelamento: {str(e)}"
            self.log_erro(erro_msg, e)
            return ResultadoRPA(
                sucesso=False,
                mensagem=erro_msg,
                dados={"erro": str(e), "traceback": traceback.format_exc()}
            )

    # ===============================================================================
    # MÉTODOS DE WEBSCRAPING - RESPONSABILIDADE DO USUÁRIO
    # ===============================================================================

    async def _fazer_login_sienge(self):
        """
        USUÁRIO: Implementar login no Sienge
        
        URL: https://jmservicos.sienge.com.br/sienge
        Campos: usuario e senha
        Validação: chegada no dashboard principal
        """
        try:
            url_sienge = self.credenciais_sienge.get("url", "https://jmservicos.sienge.com.br/sienge")
            usuario = self.credenciais_sienge.get("usuario", "")
            senha = self.credenciais_sienge.get("senha", "")
            
            self.log_progresso(f"Fazendo login no Sienge: {url_sienge}")
            
            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING COMPLETO
            # Sequência: acessar URL, preencher campos, clicar entrar, validar login
            
            self.logado_sienge = True
            self.log_sucesso("Login realizado com sucesso")
            
        except Exception as e:
            raise Exception(f"Erro no login Sienge: {str(e)}")

    async def _consultar_relatorio_saldo_devedor(self, cliente: str, numero_titulo: str) -> pd.DataFrame:
        """
        USUÁRIO: Implementar consulta de relatório saldo devedor
        
        Fluxo:
        1. Navegar para: /financeiro/contas-receber/relatorios/saldo-devedor
        2. Pesquisar cliente
        3. Filtrar por número do título
        4. Executar relatório
        5. Baixar planilha
        6. ASSISTENTE: Carregar e validar dados
        """
        try:
            self.log_progresso(f"Consultando relatório para cliente: {cliente}")
            
            # PASSO 1-5: TODO USUÁRIO - IMPLEMENTAR WEBSCRAPING
            # Navegação, pesquisa, filtros, download
            
            # PASSO 6: ASSISTENTE - Processar planilha baixada
            return await self._carregar_planilha_baixada(cliente, numero_titulo)
            
        except Exception as e:
            raise Exception(f"Erro na consulta de relatório: {str(e)}")

    async def _executar_reparcelamento_sienge(self, dados_processamento: Dict[str, Any]) -> Dict[str, Any]:
        """
        USUÁRIO: Implementar reparcelamento no Sienge
        
        Usa dados calculados pelo ASSISTENTE para preencher formulário
        """
        try:
            valores_sienge = dados_processamento.get("valores_sienge", {})
            parcelas_desmarcar = dados_processamento.get("parcelas_desmarcar", [])
            
            self.log_progresso("Executando reparcelamento no Sienge")
            
            # TODO USUÁRIO: IMPLEMENTAR WEBSCRAPING COMPLETO
            # 1. Navegar para tela de reparcelamento
            # 2. Desmarcar parcelas conforme lista
            # 3. Preencher campos com valores_sienge
            # 4. Salvar reparcelamento
            # 5. Capturar número do novo acordo
            
            return {
                "reparcelamento_executado": True,
                "numero_acordo": "SIMULAR_12345",  # TODO: capturar do Sienge
                "observacao": "Reparcelamento simulado - implementar webscraping"
            }
            
        except Exception as e:
            raise Exception(f"Erro na execução do reparcelamento: {str(e)}")

    # ===============================================================================
    # MÉTODOS DE PROCESSAMENTO - RESPONSABILIDADE DO ASSISTENTE
    # ===============================================================================

    async def _carregar_planilha_baixada(self, cliente: str, numero_titulo: str) -> pd.DataFrame:
        """
        ASSISTENTE: Carrega e valida planilha baixada do Sienge
        """
        try:
            # Localizar planilha mais recente na pasta de downloads
            pasta_downloads = Path(user_downloads_dir())
            arquivos_excel = list(pasta_downloads.glob("*.xlsx"))
            
            if not arquivos_excel:
                raise FileNotFoundError("Nenhuma planilha encontrada na pasta de downloads")
            
            # Ordenar por data de modificação (mais recente primeiro)
            arquivo_mais_recente = max(arquivos_excel, key=lambda f: f.stat().st_mtime)
            
            self.log_info(f"Carregando planilha: {arquivo_mais_recente.name}")
            
            # Carregar dados
            df = pd.read_excel(arquivo_mais_recente)
            
            # Validar estrutura básica
            if df.empty:
                raise ValueError("Planilha está vazia")
            
            # Mover para pasta de controle
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo_destino = f"sienge_{numero_titulo}_{timestamp}.xlsx"
            caminho_destino = self.pasta_planilhas / nome_arquivo_destino
            
            shutil.move(str(arquivo_mais_recente), str(caminho_destino))
            self.log_info(f"Planilha movida para: {caminho_destino}")
            
            return df
            
        except Exception as e:
            raise Exception(f"Erro ao carregar planilha: {str(e)}")

    async def _processar_planilha_cliente(self, df_planilha: pd.DataFrame, cliente: str, numero_titulo: str, indice_igpm: float) -> Dict[str, Any]:
        """
        ASSISTENTE: Processa dados do cliente aplicando regras PDD
        
        Valida inadimplência e calcula valores para reparcelamento
        conforme PDD seção 7.3.2
        """
        try:
            # ETAPA 1: Validar cliente conforme PDD
            self.log_info(f"Validando cliente {cliente} com título {numero_titulo}")
            resultado_validacao = self.validador_pdd.validar_cliente(
                df_planilha, cliente, numero_titulo
            )
            
            if not resultado_validacao["pode_reparcelar"]:
                self.log_aviso(f"Cliente não pode reparcelar: {resultado_validacao['motivo_classificacao']}")
                return resultado_validacao
            
            # ETAPA 2: Calcular valores para Sienge
            saldo_total = resultado_validacao.get("saldo_total", 0)
            parcelas_pendentes = resultado_validacao.get("qtd_parcelas_ct_a_vencer", 0)
            
            resultado_calculo = self.calculadora_pdd.calcular_valores_sienge(
                saldo_total, indice_igpm, parcelas_pendentes
            )
            
            if not resultado_calculo["sucesso"]:
                self.log_erro(f"Erro no cálculo: {resultado_calculo['erro']}")
                return resultado_calculo
            
            # ETAPA 3: Determinar parcelas para desmarcar
            parcelas_ct_a_vencer = resultado_validacao.get("parcelas_ct_a_vencer", [])
            parcelas_desmarcar = self.calculadora_pdd.determinar_parcelas_desmarcar(parcelas_ct_a_vencer)
            
            # CONSOLIDAR RESULTADO FINAL
            resultado_final = {
                **resultado_validacao,
                **resultado_calculo,
                "parcelas_desmarcar": parcelas_desmarcar,
                "processamento_concluido": True,
                "timestamp": datetime.now().isoformat()
            }
            
            self.log_sucesso(f"Cliente {cliente} processado - Status: {resultado_validacao['status_cliente']}")
            return resultado_final
            
        except Exception as e:
            erro_msg = f"Erro no processamento: {str(e)}"
            self.log_erro(erro_msg, e)
            return {
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "sucesso": False,
                "erro": erro_msg,
                "pode_reparcelar": False,
                "status_cliente": "ERRO_PROCESSAMENTO"
            }

    # ===============================================================================
    # MÉTODOS AUXILIARES
    # ===============================================================================

    def _salvar_auditoria_processamento(self, dados: Dict[str, Any]):
        """
        ASSISTENTE: Salva auditoria do processamento para compliance PDD
        """
        try:
            pasta_auditoria = Path("dados_processamento/auditoria_planilhas")
            pasta_auditoria.mkdir(parents=True, exist_ok=True)
            
            numero_titulo = dados.get("numero_titulo", "sem_titulo")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_auditoria = pasta_auditoria / f"auditoria_{numero_titulo}_{timestamp}.json"
            
            with open(arquivo_auditoria, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=2, ensure_ascii=False, default=str)
            
            self.log_info(f"Auditoria salva: {arquivo_auditoria}")
            
        except Exception as e:
            self.log_erro(f"Erro ao salvar auditoria: {str(e)}")

    def obter_status_processamento(self) -> Dict[str, Any]:
        """
        ASSISTENTE: Retorna status atual do processamento
        """
        return {
            "logado_sienge": self.logado_sienge,
            "credenciais_configuradas": bool(self.credenciais_sienge),
            "pasta_planilhas": str(self.pasta_planilhas),
            "validador_pdd_ativo": self.validador_pdd is not None,
            "calculadora_pdd_ativa": self.calculadora_pdd is not None
        }


# ===============================================================================
# UTILITÁRIOS PARA TESTE E DESENVOLVIMENTO
# ===============================================================================

async def testar_regras_pdd_local():
    """
    Testa aplicação das regras PDD com planilha de exemplo
    """
    try:
        rpa = RPASienge()
        
        # Carregar planilha de teste
        pasta_exemplos = Path("rpa_sienge/planilhas_exemplo")
        arquivo_teste = pasta_exemplos / "saldo_devedor_inadimplente.xlsx"
        
        if arquivo_teste.exists():
            df_teste = pd.read_excel(arquivo_teste)
            
            resultado = await rpa._processar_planilha_cliente(
                df_teste, 
                "CLIENTE TESTE", 
                "123456789",
                3.89  # IGP-M exemplo
            )
            
            print("=== RESULTADO TESTE REGRAS PDD ===")
            print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))
            
        else:
            print(f"Arquivo de teste não encontrado: {arquivo_teste}")
            
    except Exception as e:
        print(f"Erro no teste: {str(e)}")

if __name__ == "__main__":
    asyncio.run(testar_regras_pdd_local())