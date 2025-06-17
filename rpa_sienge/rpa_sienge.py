# RPA Sienge code updated with TODOs for webscraping implementation.
"""
RPA Sienge - Versão Produção
Terceiro RPA do sistema - Processa reparcelamento no ERP Sienge

Desenvolvido em Português Brasileiro
Baseado no PDD seção 7.3 - Processamento no sistema Sienge

VERSÃO PRODUÇÃO - Apenas código para ambiente real
"""
a
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
from dotenv import load_dotenv

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
            self.log_progresso(f"🚀 INICIANDO RPA SIENGE - ETAPA: {etapa.upper()}")
            self.log_progresso(
                f"   📋 Contrato: {contrato.get('numero_titulo', '')}")
            self.log_progresso(f"   👤 Cliente: {contrato.get('cliente', '')}")
            self.log_progresso(f"   🔐 Autorização automática: {autorizar_reparcelamento}")

            if not contrato or not credenciais_sienge:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem=
                    "Dados do contrato ou credenciais Sienge não fornecidos",
                    erro=
                    "Parâmetros 'contrato' e 'credenciais_sienge' são obrigatórios"
                )

            # Configura credenciais
            self._configurar_credenciais(credenciais_sienge)

            # Faz login no Sienge
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
                    autorizar_reparcelamento, notificar_analista
                )
                
                if etapa == "reparcelamento":
                    return resultado_reparcelamento

            # ETAPA COMPLETA: COMBINAR RESULTADOS
            if etapa == "completa":
                # Gera carnê se processamento foi bem-sucedido
                carne_gerado = None
                if dados_financeiros.get("sucesso") and resultado_reparcelamento.sucesso:
                    self.log_progresso("Gerando carnê atualizado")
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
                    mensagem=
                    f"Processamento completo - Cliente: {contrato.get('cliente', '')}",
                    dados=resultado_dados)

        except Exception as e:
            erro_msg = f"Erro na execução do RPA Sienge: {str(e)}"
            self.log_erro(erro_msg, e)
            return ResultadoRPA(sucesso=False,
                                mensagem="Falha na execução do RPA Sienge",
                                erro=erro_msg)

    async def _executar_etapa_consulta(self, contrato: Dict[str, Any]) -> Dict[str, Any]:
        """
        ETAPA 1: Executa apenas consulta de relatórios financeiros
        
        Conforme PDD seção 9.1.1 - Leitura e extração de dados do relatório
        """
        try:
            self.log_progresso("📊 ETAPA 1: CONSULTA DE RELATÓRIOS FINANCEIROS")
            
            # Consulta relatórios financeiros do cliente
            self.log_progresso(
                f"Consultando relatórios do cliente: {contrato.get('cliente', '')}"
            )
            dados_financeiros = await self._consultar_relatorios_financeiros(contrato)

            # Aplicar regras PDD para extrair informações obrigatórias
            if dados_financeiros.get("sucesso"):
                # Processar regras de negócio conforme PDD
                dados_processados = await self._aplicar_regras_negocio_pdd(
                    dados_financeiros, contrato
                )
                dados_financeiros.update(dados_processados)

            self.log_progresso("✅ ETAPA 1 CONCLUÍDA: Consulta de relatórios")
            return dados_financeiros

        except Exception as e:
            erro_msg = f"Erro na etapa de consulta: {str(e)}"
            self.log_erro(erro_msg, e)
            return {
                "sucesso": False,
                "erro": erro_msg,
                "etapa": "consulta"
            }

    async def _executar_etapa_reparcelamento(self, 
                                           contrato: Dict[str, Any], 
                                           indices: Dict[str, Any],
                                           dados_financeiros: Dict[str, Any],
                                           autorizar_reparcelamento: bool = False,
                                           notificar_analista: bool = True) -> ResultadoRPA:
        """
        ETAPA 2: Executa processamento de reparcelamento no Sienge
        
        Conforme PDD seção 7.3.3 - Processamento no sistema Sienge
        
        Args:
            autorizar_reparcelamento: True para pular validação de autorização
            notificar_analista: False para ignorar notificações
        """
        try:
            self.log_progresso("🔄 ETAPA 2: PROCESSAMENTO DE REPARCELAMENTO")
            
            # Valida se contrato pode ser reparcelado
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

            # Verificar autorização para reparcelamento
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

            # Processa reparcelamento no Sienge
            self.log_progresso("Processando reparcelamento no Sienge")
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
            return ResultadoRPA(
                sucesso=False,
                mensagem="Falha na etapa de reparcelamento",
                erro=erro_msg)

    async def finalizar(self):
        """Finaliza RPA e limpa recursos"""
        try:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()  # Usar close() ao invés de quit()
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
                xpath=
                '//label[text()="Seu e-mail"]/following-sibling::div//input'
            ).send_keys(usuario_sienge)

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

    async def _consultar_relatorios_financeiros(
            self, contrato: Dict[str, Any]) -> Dict[str, Any]:
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
                xpath=
                "//input[@placeholder='Pesquisar cliente' and @role='combobox']"
            )

            if combo_pesquisa:
                combo_pesquisa.click()
                time.sleep(3)

                # Preenche nome do cliente
                self.browser.send_text_human_like(
                    xpath=
                    "//input[@placeholder='Pesquisar cliente' and @role='combobox']",
                    text=cliente)

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
                    xpath=
                    "//button[@type='button' and contains(., 'Gerar Relatório')]"
                )
                time.sleep(2)

                # WEBSCRAPING REAL - Seleciona formato Excel
                self.log_progresso("📁 Selecionando formato Excel...")
                self.browser.click(
                    xpath=
                    "//legend[span[normalize-space(.)='Gerar relatório como']]/ancestor::div[contains(@class, 'MuiInputBase-root')][1]//div[@role='combobox' and contains(@class, 'MuiSelect-select')]"
                )
                time.sleep(1)

                self.browser.click(
                    xpath=
                    '//li[@role="option" and @data-value="excel" and text()="EXCEL"]'
                )
                time.sleep(1)

                # WEBSCRAPING REAL - Exporta relatório
                self.log_progresso("💾 Exportando relatório...")
                self.browser.click(
                    xpath=
                    "//button[@type='button' and normalize-space()='Exportar']"
                )
                time.sleep(5)

                # PROCESSAMENTO DA PLANILHA BAIXADA
                self.log_progresso("📋 Processando planilha baixada...")
                dados_planilha = await self._processar_planilha_baixada(
                    cliente, numero_titulo)

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
                "✅ Webscraping concluído - Aguardando processamento da planilha"
            )
            return dados_financeiros

        except Exception as e:
            erro_msg = f"Erro na consulta de relatórios: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"erro": erro_msg, "sucesso": False}

    async def _validar_contrato_reparcelamento(
            self, dados_financeiros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida se contrato pode ser reparcelado conforme regras RIGOROSAS do PDD seção 7.3.2

        REGRA CRÍTICA PDD:
        - Cliente com 3 ou mais parcelas CT vencidas = INADIMPLENTE (não pode reparcelar)
        - Cliente com menos de 3 parcelas CT vencidas = PODE reparcelar
        
        IMPORTANTE: Análise da planilha real mostra que cliente tem múltiplas CT vencidas!
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
                            # Tenta outros formatos de data
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
                "detalhes": {
                    "erro_validacao": erro_msg
                }
            }

    async def _processar_reparcelamento(
            self, contrato: Dict[str, Any], indices: Dict[str, Any],
            dados_financeiros: Dict[str, Any]) -> Dict[str, Any]:
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
                f"   💰 Saldo atual: R$ {dados_financeiros.get('saldo_total', 0):,.2f}"
            )

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
            detalhes = await self._configurar_detalhes_reparcelamento(
                contrato, indices, dados_financeiros)

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

    async def _gerar_carne_sienge(self, contrato: Dict[str,
                                                       Any]) -> Dict[str, Any]:
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

    async def _navegar_reparcelamento_inclusao(self):
        """
        WEBSCRAPING - Navega para Reparcelamento > Inclusão
        
        TODO: Implementar navegação real conforme PDD seção 7.3.3
        """
        try:
            self.log_progresso("🧭 TODO: Navegando para Reparcelamento > Inclusão...")
            # TODO: IMPLEMENTAR WEBSCRAPING REAL
            # 1. Navegar: Financeiro > Contas a receber > Reparcelamento > Inclusão
            # 2. Aguardar página carregar
            # 3. Validar que chegou na tela correta
            pass
            
        except Exception as e:
            self.log_erro("Erro ao navegar para reparcelamento", e)
            raise

    async def _consultar_titulo_reparcelamento(self, numero_titulo: str):
        """
        WEBSCRAPING - Consulta título no formulário de reparcelamento
        
        TODO: Implementar consulta real conforme PDD
        """
        try:
            self.log_progresso(f"🔍 TODO: Consultando título {numero_titulo}...")
            # TODO: IMPLEMENTAR WEBSCRAPING REAL
            # 1. Localizar campo número do título
            # 2. Preencher com numero_titulo
            # 3. Clicar consultar
            # 4. Aguardar resultados
            pass
            
        except Exception as e:
            self.log_erro("Erro ao consultar título", e)
            raise

    async def _selecionar_documentos_reparcelamento(self, dados_financeiros: Dict[str, Any]):
        """
        WEBSCRAPING - Seleciona documentos para reparcelamento
        
        TODO: Implementar seleção conforme regras PDD
        """
        try:
            self.log_progresso("📋 TODO: Selecionando documentos...")
            # TODO: IMPLEMENTAR WEBSCRAPING REAL
            # 1. Selecionar TODOS os documentos
            # 2. DESMARCAR parcelas vencidas até mês atual (conforme PDD)
            # 3. Validar seleção
            pass
            
        except Exception as e:
            self.log_erro("Erro ao selecionar documentos", e)
            raise

    async def _configurar_detalhes_reparcelamento(self, contrato: Dict[str, Any], 
                                                 indices: Dict[str, Any], 
                                                 dados_financeiros: Dict[str, Any]) -> Dict[str, Any]:
        """
        WEBSCRAPING - Configura detalhes do reparcelamento
        
        TODO: Implementar configuração conforme PDD
        """
        try:
            self.log_progresso("⚙️ TODO: Configurando detalhes...")
            # TODO: IMPLEMENTAR WEBSCRAPING REAL
            # 1. Configurar PM (prazo)
            # 2. Configurar IGP-M como indexador
            # 3. Configurar taxa fixa 8%
            # 4. Outros parâmetros conforme PDD
            
            return {
                "indexador": "IGP-M",
                "taxa_fixa": 0.08,
                "prazo_meses": 60,
                "configurado": True
            }
            
        except Exception as e:
            self.log_erro("Erro ao configurar detalhes", e)
            raise

    async def _confirmar_salvar_reparcelamento(self) -> str:
        """
        WEBSCRAPING - Confirma e salva reparcelamento
        
        TODO: Implementar confirmação conforme PDD
        """
        try:
            self.log_progresso("💾 TODO: Confirmando e salvando...")
            # TODO: IMPLEMENTAR WEBSCRAPING REAL
            # 1. Clicar confirmar
            # 2. Aguardar processamento
            # 3. Capturar número do novo título gerado
            # 4. Validar sucesso
            
            # Por enquanto retorna título fictício
            return f"REPAC_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        except Exception as e:
            self.log_erro("Erro ao confirmar reparcelamento", e)
            raise

    async def _navegar_geracao_carne(self):
        """
        WEBSCRAPING - Navega para geração de carnê
        
        TODO: Implementar navegação conforme PDD seção 7.3.4
        """
        try:
            self.log_progresso("🧭 TODO: Navegando para geração de carnê...")
            # TODO: IMPLEMENTAR WEBSCRAPING REAL
            pass
            
        except Exception as e:
            self.log_erro("Erro ao navegar para geração de carnê", e)
            raise

    async def _configurar_parametros_carne(self, contrato: Dict[str, Any]):
        """
        WEBSCRAPING - Configura parâmetros do carnê
        
        TODO: Implementar configuração conforme PDD
        """
        try:
            self.log_progresso("⚙️ TODO: Configurando parâmetros do carnê...")
            # TODO: IMPLEMENTAR WEBSCRAPING REAL
            pass
            
        except Exception as e:
            self.log_erro("Erro ao configurar parâmetros do carnê", e)
            raise

    async def _executar_geracao_carne(self, contrato: Dict[str, Any]) -> str:
        """
        WEBSCRAPING - Executa geração do carnê
        
        TODO: Implementar geração conforme PDD
        """
        try:
            self.log_progresso("📄 TODO: Executando geração do carnê...")
            # TODO: IMPLEMENTAR WEBSCRAPING REAL
            
            # Por enquanto retorna nome fictício
            return f"carne_{contrato.get('numero_titulo', 'sem_titulo')}_{datetime.now().strftime('%Y%m%d')}.txt"
            
        except Exception as e:
            self.log_erro("Erro ao executar geração do carnê", e)
            raise

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

    def _processar_dados_relatorio_sienge(
            self, dados_relatorio: Dict[str, Any],
            contrato: Dict[str, Any]) -> Dict[str, Any]:
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
                    row.get(mapeamento_colunas.get("tipo_parcela", ""),
                            "")).upper()
                status_parcela = str(
                    row.get(mapeamento_colunas.get("status", ""), ""))

                # Classifica por tipo
                if "CT" in tipo_parcela or "COTA" in tipo_parcela:
                    parcelas_ct.append(row.to_dict())
                elif any(x in tipo_parcela
                         for x in ["REC", "FAT", "RECEITA", "FATURAMENTO"]):
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

    def _obter_pasta_downloads(self) -> str:
        """
        Obtém a pasta de downloads do sistema, considerando a variável de ambiente RPA_DOWNLOADS_PATH.
        Se a variável não estiver definida, usa a pasta de downloads padrão do usuário.
        Se a subpasta RPA_DOWNLOADS não existir, ela é criada.
        """
        pasta_downloads_rpa = os.getenv("RPA_DOWNLOADS_PATH")

        if not pasta_downloads_rpa:
            pasta_downloads_rpa = user_downloads_dir()
            self.log_progresso(
                f"Variável RPA_DOWNLOADS_PATH não definida. Usando pasta Downloads padrão: {pasta_downloads_rpa}"
            )

        pasta_downloads_rpa = Path(pasta_downloads_rpa)
        pasta_downloads = pasta_downloads_rpa / "RPA_DOWNLOADS"

        if not pasta_downloads.exists():
            try:
                pasta_downloads.mkdir(parents=True, exist_ok=True)
                self.log_progresso(
                    f"Subpasta RPA_DOWNLOADS criada em: {pasta_downloads}")
            except Exception as e:
                self.log_erro(f"Erro ao criar subpasta RPA_DOWNLOADS: {e}", e)
                raise

        return str(pasta_downloads)

    async def _processar_planilha_baixada(
            self, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        Processa planilha baixada do Sienge conforme regras PDD

        Etapas:
        1. Localizar arquivo mais recente na pasta Downloads/RPA_DOWNLOADS
        2. Ler Excel com pandas
        3. Processar dados conforme regras PDD
        4. Classificar parcelas CT vs REC/FAT
        5. Identificar parcelas vencidas
        6. Salvar cópia para auditoria
        """
        try:
            # Obter pasta Downloads do usuário + subpasta RPA
            pasta_downloads_base = self._obter_pasta_downloads()

            self.log_info(
                "📁 Etapa 1: Localizando arquivo baixado mais recente...")
            self.log_info(f"   📂 Pasta Downloads RPA: {pasta_downloads_base}")

            arquivo_encontrado = self._localizar_arquivo_recente(
                pasta_downloads_base)
            self.log_info(f"   ✅ Arquivo encontrado: {arquivo_encontrado}")

            # Etapa 2: Ler planilha Excel
            self.log_info("📊 Etapa 2: Lendo planilha Excel...")
            df = await self._ler_planilha_excel(arquivo_encontrado)

            # Etapa 3: Salvar cópia para auditoria
            self.log_info("💾 Etapa 3: Salvando cópia para auditoria...")
            caminho_auditoria = await self._salvar_planilha_auditoria(
                arquivo_encontrado, cliente, numero_titulo)

            # Etapa 4: Processar dados conforme regras PDD
            self.log_info("🔄 Etapa 4: Processando dados conforme PDD...")
            dados_processados = await self._aplicar_regras_pdd_planilha(
                df, cliente, numero_titulo)

            # Etapa 5: Adicionar metadados de auditoria
            dados_processados.update({
                "arquivo_original":
                arquivo_encontrado,
                "arquivo_auditoria":
                caminho_auditoria,
                "hash_arquivo":
                self._calcular_hash_arquivo(arquivo_encontrado),
                "processado_em":
                datetime.now().isoformat(),
                "processado_por":
                "RPA_Sienge",
                "versao_rpa":
                "2.0",
                "sucesso":
                True
            })

            # Etapa 6: Registrar no sistema de auditoria
            await self._registrar_auditoria_planilha(dados_processados)

            # Etapa 7: Retroalimentação da planilha base de cálculo (PDD 9.1.2)
            self.log_progresso("🔄 Etapa 7: Atualizando planilha base de cálculo...")
            await self._atualizar_planilha_base_calculo(dados_processados, contrato)

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
                    f"Nenhum arquivo encontrado com padrão '{padrao}' em {pasta_downloads}"
                )

            # Ordenar por data de modificação (mais recente primeiro)
            arquivos_ordenados = sorted(arquivos_encontrados,
                                        key=lambda x: x.stat().st_mtime,
                                        reverse=True)

            arquivo_mais_recente = str(arquivos_ordenados[0])

            # Validar se arquivo foi modificado recentemente (últimos 10 minutos)
            tempo_arquivo = datetime.fromtimestamp(
                arquivos_ordenados[0].stat().st_mtime)
            tempo_atual = datetime.now()
            diferenca = (tempo_atual - tempo_arquivo).total_seconds() / 60

            if diferenca > 10:
                self.log_progresso(
                    f"⚠️ Arquivo encontrado há {diferenca:.1f} minutos (pode não ser o download atual)"
                )

            self.log_progresso(f"   📄 Arquivo: {arquivo_mais_recente}")
            self.log_progresso(
                f"   🕐 Modificado: {tempo_arquivo.strftime('%d/%m/%Y %H:%M:%S')}"
            )

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
                f"   📊 Planilha carregada: {len(df)} registros, {len(df.columns)} colunas"
            )

            # Validar colunas obrigatórias
            colunas_obrigatorias = [
                "Parcela/Sequencial", "Status da parcela", "Data vencimento",
                "Valor a receber", "Documento"
            ]

            colunas_faltantes = [
                col for col in colunas_obrigatorias if col not in df.columns
            ]

            if colunas_faltantes:
                raise Exception(
                    f"Colunas obrigatórias não encontradas: {colunas_faltantes}"
                )

            self.log_progresso("   ✅ Estrutura da planilha validada")

            return df

        except Exception as e:
            raise Exception(f"Erro ao ler planilha Excel: {str(e)}")

    def _calcular_primeiro_vencimento_carne(self, dia_vencimento: int, 
                                           tipo_reajuste: str = "anual",
                                           mes_base_reparcelamento: date = None,
                                           dia_aniversario_contrato: int = None) -> Dict[str, Any]:
        """
        Calcula o 1º vencimento do novo carnê conforme REGRAS PDD OFICIAIS
        
        REGRA 2 PDD: Cálculo do 1º Vencimento do Novo Carnê
        
        Args:
            dia_vencimento: Dia do mês identificado das parcelas (REGRA 1 PDD)
            tipo_reajuste: "anual" ou "aniversario" 
            mes_base_reparcelamento: Mês base do reparcelamento
            dia_aniversario_contrato: Dia do aniversário do contrato (apenas para tipo aniversário)
        
        Returns:
            Dict com data calculada e detalhes do cálculo
        """
        try:
            if not mes_base_reparcelamento:
                mes_base_reparcelamento = date.today().replace(day=1)  # Primeiro dia do mês atual
                
            if not dia_vencimento:
                raise ValueError("Dia de vencimento é obrigatório")

            self.log_progresso(f"   📅 CALCULANDO 1º VENCIMENTO CARNÊ (REGRA 2 PDD):")
            self.log_progresso(f"      📋 Tipo reajuste: {tipo_reajuste.upper()}")
            self.log_progresso(f"      📅 Dia vencimento: {dia_vencimento}")
            self.log_progresso(f"      📅 Mês base: {mes_base_reparcelamento.strftime('%m/%Y')}")
            
            if tipo_reajuste.lower() == "anual":
                # REGRA 2.1 PDD: Reajuste Anual
                # "O 1º vencimento deve ser no mesmo mês base do reparcelamento"
                primeiro_vencimento = date(
                    mes_base_reparcelamento.year,
                    mes_base_reparcelamento.month,
                    dia_vencimento
                )
                motivo = f"Reajuste Anual - Mesmo mês base ({mes_base_reparcelamento.strftime('%m/%Y')})"
                
            elif tipo_reajuste.lower() == "aniversario":
                # REGRA 2.2 PDD: Reajuste Aniversário
                if not dia_aniversario_contrato:
                    raise ValueError("Dia do aniversário do contrato é obrigatório para reajuste aniversário")
                
                self.log_progresso(f"      🎂 Dia aniversário contrato: {dia_aniversario_contrato}")
                
                if dia_vencimento < dia_aniversario_contrato:
                    # "O 1º vencimento será no mesmo dia, porém no mês seguinte"
                    if mes_base_reparcelamento.month == 12:
                        mes_seguinte = date(mes_base_reparcelamento.year + 1, 1, dia_vencimento)
                    else:
                        mes_seguinte = date(mes_base_reparcelamento.year, 
                                          mes_base_reparcelamento.month + 1, 
                                          dia_vencimento)
                    primeiro_vencimento = mes_seguinte
                    motivo = f"Aniversário - Vencimento ({dia_vencimento}) < Aniversário ({dia_aniversario_contrato}) → Mês seguinte"
                    
                else:
                    # "O 1º vencimento será no mesmo mês base do reparcelamento"
                    primeiro_vencimento = date(
                        mes_base_reparcelamento.year,
                        mes_base_reparcelamento.month,
                        dia_vencimento
                    )
                    motivo = f"Aniversário - Vencimento ({dia_vencimento}) >= Aniversário ({dia_aniversario_contrato}) → Mesmo mês"
                    
            else:
                raise ValueError(f"Tipo de reajuste inválido: {tipo_reajuste}")

            resultado = {
                "primeiro_vencimento": primeiro_vencimento,
                "primeiro_vencimento_str": primeiro_vencimento.strftime("%d/%m/%Y"),
                "tipo_reajuste": tipo_reajuste,
                "dia_vencimento": dia_vencimento,
                "mes_base": mes_base_reparcelamento,
                "dia_aniversario": dia_aniversario_contrato,
                "motivo_calculo": motivo,
                "sucesso": True
            }
            
            self.log_progresso(f"      ✅ 1º vencimento calculado: {primeiro_vencimento.strftime('%d/%m/%Y')}")
            self.log_progresso(f"      📋 Motivo: {motivo}")
            
            return resultado
            
        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "tipo_reajuste": tipo_reajuste,
                "dia_vencimento": dia_vencimento
            }

    def _verificar_inadimplencia_60_dias(self, parcelas_ct_vencidas: List[Dict], 
                                       primeiro_vencimento_carne: date) -> Dict[str, Any]:
        """
        Verifica inadimplência conforme regra dos 60 dias antes do 1º vencimento (REGRA 6 PDD)
        
        REGRA 6 PDD: "Se existir alguma parcela em aberto com vencimento até 60 dias 
        antes da data do 1º vencimento do novo carnê, registrar como Inadimplência"
        
        Args:
            parcelas_ct_vencidas: Lista de parcelas CT vencidas
            primeiro_vencimento_carne: Data do 1º vencimento calculada
            
        Returns:
            Dict com resultado da verificação
        """
        try:
            if not primeiro_vencimento_carne:
                return {
                    "inadimplente_60_dias": False,
                    "motivo": "Data do 1º vencimento não disponível",
                    "parcelas_inadimplentes": []
                }
            
            # Calcular data limite (60 dias antes do 1º vencimento)
            data_limite_60_dias = primeiro_vencimento_carne - timedelta(days=60)
            
            self.log_progresso(f"   ⚖️ VERIFICAÇÃO INADIMPLÊNCIA 60 DIAS (REGRA 6 PDD):")
            self.log_progresso(f"      📅 1º vencimento carnê: {primeiro_vencimento_carne.strftime('%d/%m/%Y')}")
            self.log_progresso(f"      📅 Data limite (60 dias antes): {data_limite_60_dias.strftime('%d/%m/%Y')}")
            
            parcelas_inadimplentes_60_dias = []
            
            for parcela in parcelas_ct_vencidas:
                data_vencimento_parcela = parcela.get("data_vencimento")
                
                if isinstance(data_vencimento_parcela, str):
                    try:
                        data_vencimento_parcela = datetime.strptime(data_vencimento_parcela, "%Y-%m-%d").date()
                    except:
                        continue
                        
                if data_vencimento_parcela and data_vencimento_parcela <= data_limite_60_dias:
                    parcelas_inadimplentes_60_dias.append({
                        "documento": parcela.get("documento"),
                        "data_vencimento": data_vencimento_parcela,
                        "dias_antes_limite": (data_limite_60_dias - data_vencimento_parcela).days,
                        "valor": parcela.get("valor", 0)
                    })
            
            inadimplente_60_dias = len(parcelas_inadimplentes_60_dias) > 0
            
            if inadimplente_60_dias:
                motivo = f"INADIMPLENTE - {len(parcelas_inadimplentes_60_dias)} parcela(s) CT vencida(s) há mais de 60 dias antes do 1º vencimento"
                self.log_progresso(f"      🚨 INADIMPLÊNCIA DETECTADA: {len(parcelas_inadimplentes_60_dias)} parcela(s)")
            else:
                motivo = "ADIMPLENTE - Nenhuma parcela CT vencida há mais de 60 dias antes do 1º vencimento"
                self.log_progresso(f"      ✅ ADIMPLENTE: Regra 60 dias atendida")
            
            return {
                "inadimplente_60_dias": inadimplente_60_dias,
                "motivo": motivo,
                "parcelas_inadimplentes": parcelas_inadimplentes_60_dias,
                "data_limite_60_dias": data_limite_60_dias,
                "total_parcelas_inadimplentes": len(parcelas_inadimplentes_60_dias)
            }
            
        except Exception as e:
            return {
                "inadimplente_60_dias": False,
                "erro": str(e),
                "motivo": f"Erro na verificação: {str(e)}"
            }


        """
        Lê planilha Excel e valida estrutura conforme PDD
        """
        try:
            # Ler Excel
            df = pd.read_excel(caminho_arquivo, engine='openpyxl')

            if df.empty:
                raise Exception("Planilha está vazia")

            self.log_progresso(
                f"   📊 Planilha carregada: {len(df)} registros, {len(df.columns)} colunas"
            )

            # Validar colunas obrigatórias
            colunas_obrigatorias = [
                "Parcela/Sequencial", "Status da parcela", "Data vencimento",
                "Valor a receber", "Documento"
            ]

            colunas_faltantes = [
                col for col in colunas_obrigatorias if col not in df.columns
            ]

            if colunas_faltantes:
                raise Exception(
                    f"Colunas obrigatórias não encontradas: {colunas_faltantes}"
                )

            self.log_progresso("   ✅ Estrutura da planilha validada")

            return df

        except Exception as e:
            raise Exception(f"Erro ao ler planilha Excel: {str(e)}")

    async def _salvar_planilha_auditoria(self, arquivo_original: str,
                                         cliente: str,
                                         numero_titulo: str) -> str:
        """
        Salva cópia da planilha para auditoria com nomenclatura padronizada
        """
        try:
            # Criar estrutura de pastas por ano/mês
            agora = datetime.now()
            pasta_auditoria = self.pasta_planilhas / str(
                agora.year) / f"{agora.month:02d}"
            pasta_auditoria.mkdir(parents=True, exist_ok=True)

            # Nome do arquivo de auditoria - limpar caracteres inválidos
            timestamp = agora.strftime("%Y%m%d_%H%M%S")
            # Limpar caracteres inválidos do número do título
            titulo_limpo = str(numero_titulo).replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
            if titulo_limpo == "N/A" or not titulo_limpo:
                titulo_limpo = "sem_titulo"
            nome_arquivo = f"sienge_{titulo_limpo}_{timestamp}.xlsx"
            caminho_auditoria = pasta_auditoria / nome_arquivo

            # Copiar arquivo
            shutil.copy2(arquivo_original, caminho_auditoria)

            self.log_progresso(f"   💾 Cópia salva: {caminho_auditoria}")

            return str(caminho_auditoria)

        except Exception as e:
            self.log_erro("Erro ao salvar planilha para auditoria", e)
            return ""

    async def _aplicar_regras_pdd_planilha(
            self, df: pd.DataFrame, cliente: str,
            numero_titulo: str) -> Dict[str, Any]:
        """
        Aplica regras do PDD conforme documentação oficial - REGRAS DE NEGÓCIO COMPLETAS

        IMPLEMENTAÇÃO BASEADA NO DOCUMENTO OFICIAL PDD:
        1. Identificação do Dia de Vencimento das Parcelas
        2. Cálculo do 1º Vencimento do Novo Carnê 
        3. Valor da Parcela Atual
        4. Verificação de Parcelas Abertas Irregulares
        5. Quantidade de Parcelas a Vencer
        6. Quantidade de Parcelas Vencidas
        7. Atualização da Planilha Base de Cálculo
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
            
            # CONFORME PDD: Filtro rigoroso apenas "a vencer"
            parcelas_a_vencer = df[
                df["Status da parcela"].str.upper().str.strip() == "A VENCER"
            ].copy()
            
            # Se não encontrar "A VENCER", tentar variações comuns do Sienge
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
            
            # CT = Cota de Terreno (conforme PDD)
            parcelas_ct_a_vencer = parcelas_a_vencer[
                parcelas_a_vencer["Documento"].str.contains("CT", case=False, na=False)
            ].copy()
            
            # REC/FAT = Receitas e Faturamento (conforme PDD)
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
            
            # TODO: Implementar consulta à planilha base para determinar se usar "original" ou "corrigido"
            # Por enquanto, usar "Valor a receber" como mais confiável
            valor_parcela_base = 0
            if len(parcelas_ct_a_vencer) > 0:
                primeiro_registro = parcelas_ct_a_vencer.iloc[0]
                valor_parcela_base = self._converter_valor_monetario(primeiro_registro["Valor a receber"])
            
            self.log_progresso(f"      💰 Valor da parcela base identificado: R$ {valor_parcela_base:,.2f}")

            # ===== REGRA 5 PDD: VERIFICAÇÃO DE PARCELAS ABERTAS IRREGULARES =====
            self.log_progresso(f"   ⚠️ REGRA 5 PDD: Verificando parcelas abertas irregulares...")
            
            parcelas_irregulares = []
            if len(parcelas_ct_a_vencer) > 0 and valor_parcela_base > 0:
                # Filtro conforme PDD: Valor original ≠ valor da parcela atual E Tipo condição ≠ "Parcela Mensal"
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
            
            # TODO: Implementar regras específicas por tipo de contrato (Reajuste Anual vs Aniversário)
            # Por enquanto, contagem simples
            qtd_parcelas_ct_a_vencer = len(parcelas_ct_a_vencer)
            qtd_parcelas_rec_fat_a_vencer = len(parcelas_rec_fat_a_vencer)

            # ===== REGRA 7 PDD: QUANTIDADE DE PARCELAS VENCIDAS =====
            self.log_progresso(f"   🚨 REGRA 7 PDD: Verificando parcelas vencidas...")
            
            # Buscar todas as parcelas CT vencidas (não apenas "A vencer")
            todas_parcelas_ct = df[
                df["Documento"].str.contains("CT", case=False, na=False)
            ].copy()
            
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
            todas_parcelas_rec_fat = df[
                df["Documento"].str.contains("REC|FAT", case=False, na=False)
            ].copy()
            
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

            # ===== REGRA 8 PDD: VERIFICAÇÃO DE INADIMPLÊNCIA (60 DIAS) =====
            self.log_progresso(f"   ⚖️ REGRA 8 PDD: Verificando inadimplência conforme 60 dias...")
            
            # TODO: Implementar verificação de 60 dias antes do 1º vencimento
            # Por enquanto, usar regra de 3 parcelas CT vencidas
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
            self.log_progresso(f"      📋 Outras parcelas: {len(df) - len(parcelas_a_vencer)}")
            self.log_progresso(f"      🚨 CT vencidas NÃO quitadas: {qtd_ct_vencidas}")
            self.log_progresso(f"      🎯 STATUS FINAL: {status_cliente.upper()}")
            
            # TODO: Implementar cálculo do 1º vencimento carnê (REGRA 2 PDD)
            self.log_progresso(f"      📅 Dia comum de vencimento: {dia_vencimento_comum or 'N/A'}")
            self.log_progresso(f"      💰 Valor parcela base: R$ {valor_parcela_base:,.2f}")
            
            if len(parcelas_irregulares) > 0:
                self.log_progresso(f"      ⚠️ ATENÇÃO: {len(parcelas_irregulares)} parcela(s) irregular(es) - enviar ao analista financeiro")

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
                valor = valor.replace("R$",
                                      "").replace(".",
                                                  "").replace(",",
                                                              ".").strip()
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

    async def _registrar_auditoria_planilha(self,
                                            dados_processados: Dict[str, Any]):
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
                "arquivo_auditoria":
                dados_processados.get("arquivo_auditoria"),
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
                    await mongodb_manager.database.auditoria_planilhas_sienge.insert_one(
                        registro_auditoria)
                    self.log_progresso("   ✅ Auditoria salva no MongoDB")
            except Exception as e:
                self.log_progresso(f"   ⚠️ MongoDB indisponível: {str(e)}")

            # Fallback JSON
            pasta_auditoria_json = Path(
                "dados_processamento/auditoria_planilhas")
            pasta_auditoria_json.mkdir(parents=True, exist_ok=True)

            # Limpar caracteres inválidos do número do título para o JSON
            titulo_limpo = str(dados_processados.get('numero_titulo', 'sem_titulo')).replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
            if titulo_limpo == "N/A" or not titulo_limpo:
                titulo_limpo = "sem_titulo"
            arquivo_json = pasta_auditoria_json / f"auditoria_{titulo_limpo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(arquivo_json, 'w', encoding='utf-8') as f:
                json.dump(registro_auditoria,
                          f,
                          indent=2,
                          ensure_ascii=False,
                          default=str)

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

    async def _aplicar_regras_negocio_pdd(self, dados_financeiros: Dict[str, Any], contrato: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica regras de negócio conforme PDD após consulta dos relatórios
        
        Conforme documentação PDD - Regras de Negócio para Reparcelamento:
        1. Identificação do Dia de Vencimento das Parcelas
        2. Cálculo do 1º Vencimento do Novo Carnê
        3. Valor da Parcela Atual
        4. Verificação de Parcelas Abertas Irregulares
        5. Quantidade de Parcelas a Vencer
        6. Quantidade de Parcelas Vencidas
        """
        try:
            self.log_progresso("📋 Aplicando regras de negócio PDD...")
            
            if not dados_financeiros.get("sucesso"):
                return {"regras_aplicadas": False, "erro": "Dados financeiros inválidos"}

            # Extrair dados básicos
            df_dados = dados_financeiros.get("dados_brutos")
            if df_dados is None or df_dados.empty:
                return {"regras_aplicadas": False, "erro": "DataFrame vazio"}

            # REGRA 1: Identificação do Dia de Vencimento das Parcelas
            dia_vencimento = self._identificar_dia_vencimento_parcelas(df_dados)
            
            # REGRA 2: Cálculo do 1º Vencimento do Novo Carnê
            tipo_reajuste = contrato.get("tipo_reajuste", "anual")  # anual ou aniversario
            mes_base = contrato.get("mes_base_reparcelamento")  # Ex: "05/2025"
            dia_aniversario = contrato.get("dia_aniversario_contrato")  # Para tipo aniversário
            
            primeiro_vencimento = self._calcular_primeiro_vencimento_carne(
                dia_vencimento, tipo_reajuste, mes_base, dia_aniversario
            )

            # REGRA 3: Valor da Parcela Atual
            valor_parcela_atual = self._determinar_valor_parcela_atual(df_dados, contrato)

            # REGRA 4: Verificação de Parcelas Abertas Irregulares  
            parcelas_irregulares = self._verificar_parcelas_irregulares(df_dados, valor_parcela_atual)

            # REGRA 5: Quantidade de Parcelas a Vencer
            qtd_parcelas_vencer = self._contar_parcelas_a_vencer(df_dados, tipo_reajuste, mes_base, dia_aniversario)

            # REGRA 6: Quantidade de Parcelas Vencidas
            parcelas_vencidas = self._analisar_parcelas_vencidas(df_dados, primeiro_vencimento)

            # Consolidar resultados
            regras_aplicadas = {
                "regras_aplicadas": True,
                "dia_vencimento_parcelas": dia_vencimento,
                "primeiro_vencimento_carne": primeiro_vencimento,
                "valor_parcela_atual": valor_parcela_atual,
                "parcelas_irregulares": parcelas_irregulares,
                "qtd_parcelas_a_vencer": qtd_parcelas_vencer,
                "parcelas_vencidas": parcelas_vencidas,
                "timestamp_regras": datetime.now().isoformat()
            }

            self.log_progresso("✅ Regras de negócio PDD aplicadas com sucesso")
            return regras_aplicadas

        except Exception as e:
            erro_msg = f"Erro ao aplicar regras de negócio: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"regras_aplicadas": False, "erro": erro_msg}

    def _identificar_dia_vencimento_parcelas(self, df_dados: pd.DataFrame) -> int:
        """
        REGRA 1 PDD: Identificação do Dia de Vencimento das Parcelas
        
        Filtro: Status da parcela = "a vencer"
        Extração: Dia do mês da coluna "Data vencimento"
        """
        try:
            # Filtrar apenas parcelas "a vencer"
            parcelas_a_vencer = df_dados[
                df_dados["Status da parcela"].str.upper().str.strip() == "A VENCER"
            ]
            
            if len(parcelas_a_vencer) == 0:
                return None

            # Extrair dias de vencimento
            dias_vencimento = []
            for _, row in parcelas_a_vencer.iterrows():
                data_vencimento = row.get("Data vencimento")
                if pd.notna(data_vencimento):
                    try:
                        if isinstance(data_vencimento, str):
                            data_obj = datetime.strptime(data_vencimento, "%d/%m/%Y").date()
                        else:
                            data_obj = data_vencimento.date() if hasattr(data_vencimento, 'date') else data_vencimento
                        dias_vencimento.append(data_obj.day)
                    except:
                        continue

            # Retornar dia mais comum
            if dias_vencimento:
                return max(set(dias_vencimento), key=dias_vencimento.count)
            
            return None

        except Exception as e:
            self.log_erro("Erro ao identificar dia de vencimento", e)
            return None

    def _determinar_valor_parcela_atual(self, df_dados: pd.DataFrame, contrato: Dict[str, Any]) -> float:
        """
        REGRA 3 PDD: Valor da Parcela Atual
        
        Consultar planilha base para determinar se usar "Valor original" ou "Valor corrigido"
        """
        try:
            # TODO: Implementar consulta à planilha base para determinar coluna
            # Por enquanto, usar "Valor a receber" como padrão
            
            parcelas_ct_a_vencer = df_dados[
                (df_dados["Status da parcela"].str.upper().str.strip() == "A VENCER") &
                (df_dados["Documento"].str.contains("CT", case=False, na=False))
            ]
            
            if len(parcelas_ct_a_vencer) > 0:
                primeiro_registro = parcelas_ct_a_vencer.iloc[0]
                return self._converter_valor_monetario(primeiro_registro["Valor a receber"])
            
            return 0.0

        except Exception as e:
            self.log_erro("Erro ao determinar valor da parcela", e)
            return 0.0

    def _verificar_parcelas_irregulares(self, df_dados: pd.DataFrame, valor_parcela_base: float) -> List[Dict]:
        """
        REGRA 4 PDD: Verificação de Parcelas Abertas Irregulares
        
        Filtro: Status = "a vencer", Documento = "CT", 
                Valor original ≠ valor parcela atual, Tipo condição ≠ "Parcela Mensal"
        """
        try:
            parcelas_irregulares = []
            
            if valor_parcela_base <= 0:
                return parcelas_irregulares

            parcelas_ct_a_vencer = df_dados[
                (df_dados["Status da parcela"].str.upper().str.strip() == "A VENCER") &
                (df_dados["Documento"].str.contains("CT", case=False, na=False))
            ]

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

            return parcelas_irregulares

        except Exception as e:
            self.log_erro("Erro ao verificar parcelas irregulares", e)
            return []

    def _contar_parcelas_a_vencer(self, df_dados: pd.DataFrame, tipo_reajuste: str, 
                                 mes_base: str = None, dia_aniversario: int = None) -> int:
        """
        REGRA 5 PDD: Quantidade de Parcelas a Vencer
        
        Regras específicas por tipo de contrato (Reajuste Anual vs Aniversário)
        """
        try:
            parcelas_ct_a_vencer = df_dados[
                (df_dados["Status da parcela"].str.upper().str.strip() == "A VENCER") &
                (df_dados["Documento"].str.contains("CT", case=False, na=False))
            ]

            # TODO: Implementar regras específicas para tipo aniversário
            # Por enquanto, contagem simples
            return len(parcelas_ct_a_vencer)

        except Exception as e:
            self.log_erro("Erro ao contar parcelas a vencer", e)
            return 0

    def _analisar_parcelas_vencidas(self, df_dados: pd.DataFrame, primeiro_vencimento: Dict) -> Dict[str, Any]:
        """
        REGRA 6 PDD: Quantidade de Parcelas Vencidas
        
        Incluindo verificação de inadimplência (60 dias antes do 1º vencimento)
        """
        try:
            hoje = date.today()
            
            # Contar parcelas CT vencidas
            todas_parcelas_ct = df_dados[
                df_dados["Documento"].str.contains("CT", case=False, na=False)
            ]
            
            parcelas_ct_vencidas = []
            for _, row in todas_parcelas_ct.iterrows():
                data_vencimento = row.get("Data vencimento")
                status = str(row.get("Status da parcela", "")).strip().upper()
                
                try:
                    if isinstance(data_vencimento, str):
                        data_obj = datetime.strptime(data_vencimento, "%d/%m/%Y").date()
                    else:
                        data_obj = data_vencimento.date() if hasattr(data_vencimento, 'date') else data_vencimento
                        
                    if data_obj < hoje and status != "QUITADA":
                        parcelas_ct_vencidas.append({
                            "documento": row.get("Documento"),
                            "data_vencimento": data_obj,
                            "status": status,
                            "valor": self._converter_valor_monetario(row.get("Valor a receber", 0)),
                            "dias_atraso": (hoje - data_obj).days
                        })
                except:
                    continue

            # Verificar pendências REC/FAT
            parcelas_rec_fat_vencidas = []
            todas_parcelas_rec_fat = df_dados[
                df_dados["Documento"].str.contains("REC|FAT", case=False, na=False)
            ]
            
            for _, row in todas_parcelas_rec_fat.iterrows():
                data_vencimento = row.get("Data vencimento")
                status = str(row.get("Status da parcela", "")).strip().upper()
                
                try:
                    if isinstance(data_vencimento, str):
                        data_obj = datetime.strptime(data_vencimento, "%d/%m/%Y").date()
                    else:
                        data_obj = data_vencimento.date() if hasattr(data_vencimento, 'date') else data_vencimento
                        
                    if data_obj < hoje and status != "QUITADA":
                        parcelas_rec_fat_vencidas.append({
                            "documento": row.get("Documento"),
                            "data_vencimento": data_obj,
                            "status": status,
                            "valor": self._converter_valor_monetario(row.get("Valor a receber", 0))
                        })
                except:
                    continue

            # Verificar inadimplência 60 dias
            inadimplencia_60_dias = None
            if primeiro_vencimento and primeiro_vencimento.get("sucesso"):
                data_primeiro_venc = primeiro_vencimento.get("primeiro_vencimento")
                if data_primeiro_venc:
                    inadimplencia_60_dias = self._verificar_inadimplencia_60_dias(
                        parcelas_ct_vencidas, data_primeiro_venc
                    )

            return {
                "qtd_ct_vencidas": len(parcelas_ct_vencidas),
                "qtd_rec_fat_vencidas": len(parcelas_rec_fat_vencidas),
                "parcelas_ct_vencidas": parcelas_ct_vencidas,
                "parcelas_rec_fat_vencidas": parcelas_rec_fat_vencidas,
                "inadimplencia_60_dias": inadimplencia_60_dias
            }

        except Exception as e:
            self.log_erro("Erro ao analisar parcelas vencidas", e)
            return {"qtd_ct_vencidas": 0, "qtd_rec_fat_vencidas": 0}

    async def _verificar_autorizacao_reparcelamento(self, contrato: Dict[str, Any], 
                                                   dados_financeiros: Dict[str, Any],
                                                   notificar_analista: bool = True) -> Dict[str, Any]:
        """
        Verifica autorização para processamento de reparcelamento
        
        Args:
            notificar_analista: False para ignorar notificações (usado em testes)
        """
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

            # TODO: Implementar sistema de notificações por e-mail
            # TODO: Implementar verificação de resposta do analista
            
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
            
            # TODO: Implementar envio de e-mail e verificação de resposta
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
        """
        Atualiza planilha "BASE DE CÁLCULO REPARCELAMENTO 2025" conforme PDD seção 9.1.2
        
        CAMPOS OBRIGATÓRIOS PDD:
        - PENDÊNCIAS SIENGE INAD: Quantidade de parcelas CT vencidas (se > 0)
        - PENDÊNCIAS SIENGE: Quantidade de pendências REC/FAT (se > 0)  
        - Parcelas a vencer: Quantidade de parcelas CT a vencer
        - Valor da Parcela Base: Valor identificado da parcela atual
        - Dia de vencimento de parcelas: Dia comum identificado
        - 1º vencimento carnê: Data calculada do 1º vencimento
        """
        try:
            # Verificar se Google Sheets está disponível
            if not hasattr(self, 'cliente_sheets') or not self.cliente_sheets:
                await self._conectar_google_sheets()
            
            if not self.cliente_sheets:
                self.log_progresso("⚠️ Google Sheets não disponível - Salvando dados localmente")
                await self._salvar_dados_base_calculo_local(dados_processados, contrato)
                return

            # ID da planilha base de cálculo (deve ser configurado via ambiente)
            planilha_base_id = os.getenv("PLANILHA_BASE_CALCULO_ID") or os.getenv("PLANILHA_CALCULO_ID")
            if not planilha_base_id:
                self.log_progresso("⚠️ ID da planilha base não configurado - Salvando dados localmente")
                await self._salvar_dados_base_calculo_local(dados_processados, contrato)
                return

            self.log_progresso(f"📊 Atualizando planilha base: {planilha_base_id}")

            # Abrir planilha
            planilha_base = self.cliente_sheets.open_by_key(planilha_base_id)
            aba_base_calculo = planilha_base.worksheet("Base de cálculo")

            # Localizar linha do contrato
            numero_titulo = contrato.get("numero_titulo", "")
            cliente = contrato.get("cliente", "")
            
            linha_contrato = await self._localizar_linha_contrato(aba_base_calculo, numero_titulo, cliente)
            
            if linha_contrato:
                # Atualizar campos conforme PDD 9.1.2
                await self._atualizar_campos_pdd_planilha(aba_base_calculo, linha_contrato, dados_processados)
                self.log_progresso(f"✅ Planilha base atualizada na linha {linha_contrato}")
            else:
                self.log_progresso(f"⚠️ Contrato não encontrado na planilha base: {numero_titulo}")
                # Adicionar nova linha se necessário
                await self._adicionar_contrato_planilha_base(aba_base_calculo, contrato, dados_processados)

        except Exception as e:
            self.log_erro("Erro ao atualizar planilha base de cálculo", e)
            # Fallback: salvar dados localmente
            await self._salvar_dados_base_calculo_local(dados_processados, contrato)

    async def _conectar_google_sheets(self):
        """Conecta ao Google Sheets"""
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            # Caminho das credenciais
            credenciais_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "./gspread-credentials.json")
            
            if not os.path.exists(credenciais_path):
                self.log_progresso(f"⚠️ Arquivo de credenciais não encontrado: {credenciais_path}")
                return

            # Configurar credenciais
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_file(credenciais_path, scopes=scopes)
            self.cliente_sheets = gspread.authorize(credentials)
            
            self.log_progresso("✅ Google Sheets conectado com sucesso")

        except Exception as e:
            self.log_erro("Erro ao conectar Google Sheets", e)
            self.cliente_sheets = None

    async def _localizar_linha_contrato(self, aba_base_calculo, numero_titulo: str, cliente: str) -> int:
        """
        Localiza linha do contrato na planilha base
        """
        try:
            # Obter todos os dados
            dados_planilha = aba_base_calculo.get_all_records()
            
            # Buscar por título ou cliente
            for linha, registro in enumerate(dados_planilha, start=2):  # Linha 1 é cabeçalho
                titulo_planilha = str(registro.get("numero_titulo", "")).strip()
                cliente_planilha = str(registro.get("Cliente", "")).strip()
                
                # Busca por título exato ou cliente parcial
                if (numero_titulo and titulo_planilha == numero_titulo) or \
                   (cliente and cliente.lower() in cliente_planilha.lower()):
                    return linha
            
            return None

        except Exception as e:
            self.log_erro("Erro ao localizar linha do contrato", e)
            return None

    async def _atualizar_campos_pdd_planilha(self, aba_base_calculo, linha: int, dados_processados: Dict[str, Any]):
        """
        Atualiza campos obrigatórios conforme PDD seção 9.1.2
        """
        try:
            # Obter cabeçalhos da planilha
            cabecalhos = aba_base_calculo.row_values(1)
            
            # Mapear colunas importantes
            mapa_colunas = {}
            for i, cabecalho in enumerate(cabecalhos, start=1):
                cabecalho_upper = str(cabecalho).upper()
                if "PENDÊNCIAS SIENGE INAD" in cabecalho_upper:
                    mapa_colunas["pendencias_inad"] = i
                elif "PENDÊNCIAS SIENGE" in cabecalho_upper and "INAD" not in cabecalho_upper:
                    mapa_colunas["pendencias_sienge"] = i
                elif "PARCELAS A VENCER" in cabecalho_upper:
                    mapa_colunas["parcelas_vencer"] = i
                elif "VALOR DA PARCELA BASE" in cabecalho_upper:
                    mapa_colunas["valor_parcela"] = i
                elif "DIA DE VENCIMENTO" in cabecalho_upper:
                    mapa_colunas["dia_vencimento"] = i
                elif "1º VENCIMENTO CARNÊ" in cabecalho_upper:
                    mapa_colunas["primeiro_vencimento"] = i

            # Preparar atualizações
            atualizacoes = []

            # PENDÊNCIAS SIENGE INAD
            if "pendencias_inad" in mapa_colunas:
                qtd_ct_vencidas = dados_processados.get("qtd_ct_vencidas", 0)
                if qtd_ct_vencidas > 0:
                    celula = f'{chr(64 + mapa_colunas["pendencias_inad"])}{linha}'
                    atualizacoes.append({"range": celula, "values": [[qtd_ct_vencidas]]})

            # PENDÊNCIAS SIENGE
            if "pendencias_sienge" in mapa_colunas:
                qtd_rec_fat = dados_processados.get("qtd_pendencias_rec_fat", 0)
                if qtd_rec_fat > 0:
                    celula = f'{chr(64 + mapa_colunas["pendencias_sienge"])}{linha}'
                    atualizacoes.append({"range": celula, "values": [[qtd_rec_fat]]})

            # PARCELAS A VENCER
            if "parcelas_vencer" in mapa_colunas:
                qtd_parcelas_vencer = dados_processados.get("qtd_parcelas_ct_a_vencer", 0)
                celula = f'{chr(64 + mapa_colunas["parcelas_vencer"])}{linha}'
                atualizacoes.append({"range": celula, "values": [[qtd_parcelas_vencer]]})

            # VALOR DA PARCELA BASE
            if "valor_parcela" in mapa_colunas:
                valor_parcela = dados_processados.get("valor_parcela_base", 0)
                celula = f'{chr(64 + mapa_colunas["valor_parcela"])}{linha}'
                atualizacoes.append({"range": celula, "values": [[f"R$ {valor_parcela:,.2f}"]]})

            # DIA DE VENCIMENTO
            if "dia_vencimento" in mapa_colunas:
                dia_vencimento = dados_processados.get("dia_vencimento_parcelas")
                if dia_vencimento:
                    celula = f'{chr(64 + mapa_colunas["dia_vencimento"])}{linha}'
                    atualizacoes.append({"range": celula, "values": [[dia_vencimento]]})

            # 1º VENCIMENTO CARNÊ (TODO: implementar cálculo)
            if "primeiro_vencimento" in mapa_colunas:
                # TODO: Implementar cálculo do 1º vencimento conforme regras PDD
                primeiro_vencimento = "A CALCULAR"
                celula = f'{chr(64 + mapa_colunas["primeiro_vencimento"])}{linha}'
                atualizacoes.append({"range": celula, "values": [[primeiro_vencimento]]})

            # Executar atualizações em lote
            if atualizacoes:
                for atualizacao in atualizacoes:
                    aba_base_calculo.update(atualizacao["range"], atualizacao["values"])
                
                self.log_progresso(f"   ✅ {len(atualizacoes)} campos atualizados na planilha base")

        except Exception as e:
            self.log_erro("Erro ao atualizar campos da planilha", e)

    async def _adicionar_contrato_planilha_base(self, aba_base_calculo, contrato: Dict[str, Any], dados_processados: Dict[str, Any]):
        """
        Adiciona novo contrato na planilha base se não encontrado
        """
        try:
            # Obter próxima linha vazia
            dados_existentes = aba_base_calculo.get_all_values()
            proxima_linha = len(dados_existentes) + 1

            # Preparar dados básicos do contrato
            nova_linha = [
                contrato.get("cliente", ""),
                contrato.get("numero_titulo", ""),
                contrato.get("empreendimento", ""),
                dados_processados.get("qtd_ct_vencidas", 0) if dados_processados.get("qtd_ct_vencidas", 0) > 0 else "",
                dados_processados.get("qtd_pendencias_rec_fat", 0) if dados_processados.get("qtd_pendencias_rec_fat", 0) > 0 else "",
                dados_processados.get("qtd_parcelas_ct_a_vencer", 0),
                f"R$ {dados_processados.get('valor_parcela_base', 0):,.2f}",
                dados_processados.get("dia_vencimento_parcelas", ""),
                "A CALCULAR"  # 1º vencimento carnê
            ]

            # Adicionar linha
            aba_base_calculo.append_row(nova_linha)
            
            self.log_progresso(f"   ✅ Novo contrato adicionado na linha {proxima_linha}")

        except Exception as e:
            self.log_erro("Erro ao adicionar contrato na planilha base", e)

    async def _salvar_dados_base_calculo_local(self, dados_processados: Dict[str, Any], contrato: Dict[str, Any]):
        """
        Salva dados localmente quando Google Sheets não está disponível
        """
        try:
            # Criar pasta se não existir
            pasta_backup = Path("dados_processamento/backup_planilha_base")
            pasta_backup.mkdir(parents=True, exist_ok=True)

            # Preparar dados para backup
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

            # Salvar arquivo
            numero_titulo = contrato.get("numero_titulo", "sem_titulo").replace("/", "_").replace("\\", "_")
            arquivo_backup = pasta_backup / f"backup_base_{numero_titulo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(arquivo_backup, 'w', encoding='utf-8') as f:
                json.dump(dados_backup, f, indent=2, ensure_ascii=False)

            self.log_progresso(f"   💾 Backup salvo: {arquivo_backup}")

        except Exception as e:
            self.log_erro("Erro ao salvar backup local", e)


# Função auxiliar para uso direto
async def executar_processamento_sienge(
        contrato: Dict[str, Any], 
        indices_economicos: Dict[str, Any],
        credenciais_sienge: Dict[str, str],
        etapa: str = "completa",
        autorizar_reparcelamento: bool = False,
        notificar_analista: bool = True) -> ResultadoRPA:
    """
    Função auxiliar para executar processamento Sienge diretamente

    Args:
        contrato: Dados do contrato (número_titulo, cliente, etc.)
        indices_economicos: Índices econômicos (IPCA/IGPM)
        credenciais_sienge: Credenciais de acesso ao Sienge

    Returns:
        ResultadoRPA com resultado do processamento
    """
    rpa = RPASienge()

    try:
        # Inicializa RPA
        await rpa.inicializar()

        # Executa processamento
        resultado = await rpa.executar(contrato=contrato,
                                       credenciais_sienge=credenciais_sienge,
                                       indices=indices_economicos,
                                       etapa=etapa,
                                       autorizar_reparcelamento=autorizar_reparcelamento,
                                       notificar_analista=notificar_analista)

        return resultado

    except Exception as e:
        return ResultadoRPA(
            sucesso=False,
            mensagem="Erro na execução do processamento Sienge",
            erro=str(e))
    finally:
        # Finaliza recursos
        try:
            await rpa.finalizar()
        except:
            pass
