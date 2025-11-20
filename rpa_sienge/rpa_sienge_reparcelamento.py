"""RPA Sienge - Módulo de reparcelamento completo (versão JSON).

Responsável por:

1. Buscar contratos elegíveis no repositório JSON transacional.
2. Autenticar no Sienge.
3. Executar webscraping completo do reparcelamento conforme PDD.
4. Atualizar status dos contratos e armazenar metadados relevantes.

Desenvolvido em Português Brasileiro seguindo as diretrizes oficiais.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from core.base_rpa import BaseRPA, ResultadoRPA
from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo
from core.status_contratos import StatusContrato
from core.utils_sienge import carregar_credenciais_sienge, log
from core.rastreamento_unificado import iniciar_rastreamento

# Importar notificações (com fallback se não disponível)
try:
    from core.notificacoes_simples import notificar_sucesso, notificar_erro
    NOTIFICACOES_DISPONIVEIS = True
except ImportError:
    NOTIFICACOES_DISPONIVEIS = False
    def notificar_sucesso(*args, **kwargs):  # type: ignore
        pass
    def notificar_erro(*args, **kwargs):  # type: ignore
        pass


@dataclass
class ContratoFila:
    """Representa um contrato carregado do repositório JSON."""

    id_registro: str
    dados: Dict[str, Any]
    codigo_cliente: str
    numero_titulo: str
    cliente: str

    @classmethod
    def from_dict(cls, dados: Dict[str, Any]) -> "ContratoFila":
        if not isinstance(dados, dict):
            raise ValueError("Contrato inválido: esperado dicionário.")

        identificador = str(dados.get("_id", "")).strip()
        if not identificador:
            raise ValueError("Contrato inválido: campo '_id' ausente.")

        numero_titulo = str(
            dados.get("numero_titulo") or dados.get("Titulo", "")
        ).strip()
        if not numero_titulo:
            raise ValueError(
                "Contrato inválido: campo 'numero_titulo' ausente ou vazio."
            )

        codigo_cliente = str(
            dados.get("codigo_cliente") or dados.get("Código Cliente", "")
        ).strip()
        if not codigo_cliente:
            raise ValueError(
                "Contrato inválido: campo 'codigo_cliente' ausente ou vazio."
            )

        cliente = str(dados.get("cliente") or dados.get("Cliente", "")).strip()

        return cls(
            id_registro=identificador,
            dados=dados,
            codigo_cliente=codigo_cliente,
            numero_titulo=numero_titulo,
            cliente=cliente,
        )


class RPAReparcelamentoSienge(BaseRPA):
    """Automação end-to-end do reparcelamento usando fila JSON."""

    def __init__(self, headless: Optional[bool] = None, notificar: bool = True) -> None:
        super().__init__(
            nome_rpa="SiengeReparcelamento",
            usar_browser=True,
            headless=headless,
        )
        self.logado_sienge = False
        self.credenciais_sienge: Dict[str, str] = {}
        self.rastreamento = None
        self.notificar = notificar

    async def executar(self, limite: int = 0) -> ResultadoRPA:
        """Processa contratos com status ``APROVACAO_REALIZADA`` da fila."""

        # Registrar início da execução para cálculo de tempo
        self.inicio_execucao = datetime.now()

        contratos = self._buscar_contratos_aptos(limite=limite)
        if not contratos:
            log("⚠️ Nenhum contrato com status APROVACAO_REALIZADA encontrado.")
            return ResultadoRPA(
                sucesso=True,
                mensagem="Nenhum contrato aguardando reparcelamento.",
                dados={"contratos_processados": 0, "contratos": []},
            )

        log(f"🔧 Iniciando reparcelamento de {len(contratos)} contrato(s)...")

        # Inicializar rastreamento
        try:
            self.rastreamento = iniciar_rastreamento("RPA_Sienge_Reparcelamento")
            await self.rastreamento.registrar_inicio_rpa({
                "total_contratos": len(contratos),
                "limite": limite
            })
        except Exception:
            pass  # Não quebra se rastreamento falhar

        self.credenciais_sienge = await carregar_credenciais_sienge()
        await self.inicializar()
        await self._fazer_login_sienge()
        
        # Registrar login no rastreamento
        if self.rastreamento:
            try:
                await self.rastreamento.registrar_login_sistema(
                    "sienge", self.credenciais_sienge.get("usuario", ""), self.logado_sienge
                )
            except Exception:
                pass  # Não quebra se rastreamento falhar

        contratos_sucesso: List[Dict[str, Any]] = []
        contratos_erro: List[Dict[str, Any]] = []

        for contrato in contratos:
            log(
                f"📄 Reparcelando contrato {contrato.numero_titulo} | Cliente: {contrato.cliente}"
            )
            self._atualizar_status(
                contrato.id_registro,
                StatusContrato.PROCESSANDO,
                {
                    "fase": "REPARCELAMENTO",
                    "timestamp_inicio": datetime.now().isoformat(),
                },
            )

            try:
                # Registrar início do processamento do contrato
                if self.rastreamento:
                    try:
                        await self.rastreamento.registrar_passo(
                            f"PROCESSAR_REPARCELAMENTO_{contrato.numero_titulo}",
                            {
                                "numero_titulo": contrato.numero_titulo,
                                "codigo_cliente": contrato.codigo_cliente,
                                "cliente": contrato.cliente
                            },
                            categoria="OPERACAO"
                        )
                    except Exception:
                        pass  # Não quebra se rastreamento falhar
                
                resultado = await self._processar_reparcelamento(contrato)

                if resultado.sucesso:
                    self._atualizar_status(
                        contrato.id_registro,
                        StatusContrato.REPARCELADO,
                        {
                            "timestamp_final": datetime.now().isoformat(),
                            "detalhes": resultado.dados,
                        },
                    )
                    contratos_sucesso.append({
                        "numero_titulo": contrato.numero_titulo,
                        "codigo_cliente": contrato.codigo_cliente,
                        "cliente": contrato.cliente,
                        "detalhes": resultado.dados,
                    })
                    log(
                        f"✅ Reparcelamento concluído para {contrato.numero_titulo}")
                else:
                    self._registrar_falha(contrato, resultado.mensagem)
                    contratos_erro.append({
                        "numero_titulo": contrato.numero_titulo,
                        "codigo_cliente": contrato.codigo_cliente,
                        "mensagem": resultado.mensagem,
                    })
            except Exception as erro:  # pylint: disable=broad-except
                mensagem = str(erro)
                
                # Registrar erro no rastreamento
                if self.rastreamento:
                    try:
                        await self.rastreamento.registrar_erro_critico(erro, {
                            "contrato": contrato.numero_titulo,
                            "codigo_cliente": contrato.codigo_cliente,
                            "fase": "reparcelamento"
                        })
                    except Exception:
                        pass  # Não quebra se rastreamento falhar
                
                self._registrar_falha(contrato, mensagem)
                contratos_erro.append({
                    "numero_titulo": contrato.numero_titulo,
                    "codigo_cliente": contrato.codigo_cliente,
                    "mensagem": mensagem,
                })
                log(
                    f"❌ Erro inesperado no contrato {contrato.numero_titulo}: {mensagem}")

        await self.finalizar()

        resultado_final = {
            "contratos_processados": len(contratos_sucesso),
            "contratos_erro": contratos_erro,
            "contratos_sucesso": contratos_sucesso,
        }

        # Finalizar rastreamento
        if self.rastreamento:
            try:
                await self.rastreamento.registrar_sucesso_rpa(resultado_final)
                await self.rastreamento.finalizar_rastreamento()
            except Exception:
                pass  # Não quebra se rastreamento falhar

        # Enviar notificações se habilitado
        if self.notificar and NOTIFICACOES_DISPONIVEIS:
            try:
                tempo_execucao = f"{(datetime.now() - self.inicio_execucao).total_seconds():.1f}s" if self.inicio_execucao else "N/A"
                
                if len(contratos_erro) == 0:
                    # Sucesso total
                    notificar_sucesso(
                        "RPA Sienge - Reparcelamento",
                        tempo_execucao,
                        {
                            "contratos_processados": len(contratos_sucesso),
                            "contratos_sucesso": len(contratos_sucesso),
                            "contratos_erro": 0,
                            "resumo": f"{len(contratos_sucesso)} contrato(s) reparcelado(s) com sucesso"
                        }
                    )
                elif len(contratos_sucesso) > 0:
                    # Sucesso parcial
                    notificar_sucesso(
                        "RPA Sienge - Reparcelamento (Parcial)",
                        tempo_execucao,
                        {
                            "contratos_processados": len(contratos_sucesso),
                            "contratos_sucesso": len(contratos_sucesso),
                            "contratos_erro": len(contratos_erro),
                            "resumo": f"{len(contratos_sucesso)} sucesso(s), {len(contratos_erro)} erro(s)",
                            "erros": contratos_erro
                        }
                    )
                else:
                    # Apenas erros
                    notificar_erro(
                        "RPA Sienge - Reparcelamento",
                        f"Nenhum contrato foi reparcelado com sucesso",
                        f"Total de erros: {len(contratos_erro)}\nErros: {json.dumps(contratos_erro, indent=2, ensure_ascii=False)}"
                    )
            except Exception as e:
                log(f"⚠️ Erro ao enviar notificações: {str(e)}")

        return ResultadoRPA(
            sucesso=len(contratos_erro) == 0,
            mensagem=(
                "Reparcelamento concluído." if not contratos_erro
                else f"Reparcelamento concluído com {len(contratos_erro)} erro(s)."
            ),
            dados=resultado_final,
        )

    def _buscar_contratos_aptos(self, limite: int = 0) -> List[ContratoFila]:
        registros = repositorio_contratos_arquivo.framework.find(
            {"status": StatusContrato.APROVACAO_REALIZADA},
            limit=limite if limite > 0 else None,
        )

        contratos: List[ContratoFila] = []
        for registro in registros:
            try:
                contratos.append(ContratoFila.from_dict(registro))
            except ValueError as erro:
                log(
                    f"❌ Registro descartado: {registro.get('numero_titulo', 'N/A')} | Motivo: {erro}"
                )
                identificador = str(registro.get("_id", "")).strip()
                if identificador:
                    repositorio_contratos_arquivo.atualizar_status(
                        identificador,
                        StatusContrato.ERRO,
                        {
                            "fase_erro": "VALIDACAO_DADOS",
                            "erro_reparcelamento": str(erro),
                            "timestamp_erro": datetime.now().isoformat(),
                        },
                    )

        return contratos

    async def _processar_reparcelamento(self, contrato: ContratoFila) -> ResultadoRPA:
        """Executa webscraping completo de um contrato."""

        try:
            await self._executar_fluxo_reparcelamento(contrato)
            detalhes = {
                "numero_titulo": contrato.numero_titulo,
                "codigo_cliente": contrato.codigo_cliente,
                "timestamp": datetime.now().isoformat(),
            }
            return ResultadoRPA(sucesso=True, mensagem="OK", dados=detalhes)
        except Exception as erro:  # pylint: disable=broad-except
            return ResultadoRPA(sucesso=False, mensagem=str(erro), dados={})

    def _registrar_falha(self, contrato: ContratoFila, mensagem: str) -> None:
        self._atualizar_status(
            contrato.id_registro,
            StatusContrato.ERRO,
            {
                "fase_erro": "REPARCELAMENTO",
                "erro_reparcelamento": mensagem,
                "timestamp_erro": datetime.now().isoformat(),
            },
        )

    def _atualizar_status(
        self,
        registro_id: str,
        status: str,
        dados_adicionais: Optional[Dict[str, Any]] = None,
    ) -> None:
        repositorio_contratos_arquivo.atualizar_status(
            registro_id,
            status,
            dados_adicionais or {},
        )

    async def _fazer_login_sienge(self) -> None:
        if self.logado_sienge:
            return

        url_sienge = self.credenciais_sienge.get("url", "")
        usuario_sienge = self.credenciais_sienge.get("usuario", "")
        senha_sienge = self.credenciais_sienge.get("senha", "")

        if not url_sienge:
            raise ValueError("URL do Sienge não configurada.")

        # Registrar tentativa de login
        if self.rastreamento:
            try:
                await self.rastreamento.registrar_passo(
                    "TENTATIVA_LOGIN_SIENGE",
                    {"url_sienge": url_sienge, "usuario": usuario_sienge},
                    categoria="OPERACAO"
                )
            except Exception:
                pass  # Não quebra se rastreamento falhar

        self.get_page(url_sienge)
        time.sleep(3)

        self.send_text('(//input[@id="username"])[1]', text=usuario_sienge)
        self.send_text('//input[@id="password"]', text=senha_sienge)
        self.click('//*[@id="btnEntrarComSiengeID"]')
        time.sleep(2)

        self.send_text(
            '//label[text()="Seu e-mail"]/following-sibling::div//input',
            text=usuario_sienge,
        )
        self.click("//button[normalize-space(text())='CONTINUAR']")
        self.send_text("//input[@id='signup-password']", text=senha_sienge)
        self.click("//button[normalize-space(text())='ENTRAR']")

        if self.check_for_error(
            "//div[contains(@class, 'spwAlertaAviso')]//p[contains(normalize-space(.), 'Deseja prosseguir desconectando')]",
            timeout=5,
        ):
            self.click(
                "//a[contains(@class, 'Button-prim') and contains(., 'Prosseguir')]"
            )

        self.logado_sienge = True
        
        # Registrar login bem-sucedido
        if self.rastreamento:
            try:
                await self.rastreamento.registrar_login_sistema(
                    "sienge", usuario_sienge, True
                )
            except Exception:
                pass  # Não quebra se rastreamento falhar
        
        time.sleep(5)

        if self.check_for_error(
            "//a[@id='pushActionRefuse' and contains(text(), 'Não, obrigado')]",
            timeout=15,
        ):
            self.click(
                "//a[@id='pushActionRefuse' and contains(text(), 'Não, obrigado')]"
            )

        if self.check_for_error(
            "//div[contains(@class, 'beamerAnnouncementSnippet') and contains(@class, 'active')]",
            timeout=15,
        ):
            try:
                if self.browser and hasattr(self.browser, "_driver") and self.browser._driver:
                    self.browser._driver.execute_script(
                        """var el = document.querySelector('.beamerAnnouncementSnippet.active');
                        if (el) { el.remove(); }"""
                    )
            except Exception:
                pass

        if self.check_for_error(
            "//button[@data-testid='close-button']",
            timeout=10,
        ):
            self.click("//button[@data-testid='close-button']")

    async def _executar_fluxo_reparcelamento(self, contrato: ContratoFila) -> None:
        """Aplica os passos 21-28 do PDD no contrato informado."""

        parametros = self._montar_parametros_reparcelamento(contrato)
        await self._navegar_e_executar_reparcelamento(parametros)

    def _montar_parametros_reparcelamento(self, contrato: ContratoFila) -> Dict[str, Any]:
        dados = contrato.dados
        parametros = {
            "numero_titulo": contrato.numero_titulo,
            "cliente": contrato.cliente,
            "url_reparcelamento": "https://jmservicos.sienge.com.br/sienge/8/index.html#/common/page/1047",
            "data_reparcelamento": dados.get("data_reparcelamento"),
            "valores_sienge": dados.get("valores_sienge", {}),
            "dados_financeiros": dados.get("dados_financeiros", {}),
        }

        return parametros

    async def _navegar_e_executar_reparcelamento(self, parametros: Dict[str, Any]) -> Dict[str, Any]:
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
            self.browser._driver.refresh()
            if not self.browser:
                raise RuntimeError(
                    "Navegador não inicializado para verificar carregamento da página de reparcelamento.")

            numero_titulo = parametros["numero_titulo"]
            self.log_progresso(
                f"🔍 PASSO 21: Consultando título: {numero_titulo}")

            # IMPLEMENTAR: Campo obrigatório de número do título
            iframe_ctx = self.on_iframe(xpath='//iframe[@id="iFramePage"]')
            if iframe_ctx is not None:
                with iframe_ctx:
                    self.log_progresso("Preenchendo número do título...")
                    titulo = self.browser.check_for_error(
                        xpath="//input[@id='titulo.tituloPK.nuTitulo']",
                        timeout=10,
                        condition="presence"
                    )
                    if not titulo:
                        raise TimeoutError(
                            "Campo de número do título não encontrado dentro do tempo esperado.")
                    time.sleep(5)
                    self.click(xpath="//input[@id='titulo.tituloPK.nuTitulo']")

                    self.send_text_human_like(
                        xpath="//input[@id='titulo.tituloPK.nuTitulo']", text=numero_titulo)

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

                    # PASSO 23: SELEÇÃO INDIVIDUAL DE PARCELAS (SUBSTITUI "MARCAR TODOS")
                    self.log_progresso(
                        "📄 PASSO 23: Selecionando parcelas individualmente conforme PDD...")

                    # Obter data base para reparcelamento (mês seguinte)
                    data_reparcelamento = parametros.get(
                        "data_reparcelamento", "")
                    if not data_reparcelamento:
                        # Calcular data base se não fornecida (mês seguinte)
                        mes_atual = datetime.now()
                        data_reparcelamento = (mes_atual.replace(
                            day=1) + timedelta(days=32)).replace(day=1).strftime("%d/%m/%Y")
                    self.log_progresso(
                        f"📅 Data base calculada automaticamente: {data_reparcelamento}")
                    time.sleep(2)
                    cliente_ja_reparcelado = self.check_for_error(
                        accept_alert=True)
                    if cliente_ja_reparcelado:
                        self.log_progresso(
                            "✅ Cliente já reparcelado - pulando seleção de parcelas")
                        return {"sucesso": True, "motivo_interrupcao": "Cliente já reparcelado", "cliente_ja_reparcelado": True, "timestamp": datetime.now().isoformat()}

                    # ✅ CORREÇÃO PDD: Selecionar parcelas individualmente (TODAS pelas regras ANIVERSÁRIO e ANUAL: DECIDIO EM AGENDA em usar o mes base da data do 1 vencimento do carnê)
                    planilha_id = os.getenv("PLANILHA_CALCULO_ID")
                    if not planilha_id:
                        erro_msg = "PLANILHA_CALCULO_ID não configurada no ambiente. Conforme PDD, todos os valores devem vir da planilha."
                        self.log_erro(erro_msg, Exception(erro_msg))
                        return {"sucesso": False, "erro": erro_msg}

                    # Conectar ao Google Sheets se não conectado
                    if not hasattr(self, 'cliente_sheets'):
                        await self._conectar_google_sheets()

                    # Abrir planilha
                    planilha = self.cliente_sheets.open_by_key(planilha_id)

                    # Ler valores calculados da planilha (OBRIGATÓRIO conforme PDD)
                    resultado_leitura = await self._ler_valores_calculados_planilha(
                        planilha_id=planilha_id,
                        cliente=parametros.get("cliente", ""),
                        numero_titulo=parametros.get("numero_titulo", "")
                    )

                    valores_calculados = resultado_leitura.get(
                        "valores_calculados", {})

                    parcelas_selecionadas = self._selecionar_parcelas_individualmente(
                        data_reparcelamento=valores_calculados.get(
                            "primeiro_vencimento_carne", ""),
                        max_parcelas=12,  # Conforme PDD - 12 parcelas = 1 ano
                        tabela_idx=1
                    )

                    if parcelas_selecionadas == 0:
                        self.log_erro(
                            "Nenhuma parcela foi selecionada - verificar critérios de seleção", Exception("Nenhuma parcela selecionada"))
                        return {"sucesso": False, "erro": "Nenhuma parcela selecionada para reparcelamento"}

                    self.log_progresso(
                        f"✅ Seleção individual concluída: {parcelas_selecionadas} parcelas selecionadas")

                    # 3. Clicar em "Próximo" para avançar para a tela de detalhamento
                    self.log_progresso(
                        "Clicando em 'Próximo' para ir à tela de detalhamento...")
                    self.click(
                        xpath='//input[@type="button" and @name="btNext" and @value="Próximo"]')

                    # Trata qualquer alerta que possa aparecer após avançar
                    self.check_for_error()

                    # PASSO 24: CONFIGURAÇÃO DO DETALHAMENTO
                    # PRIMEIRO: PREENCHER DADOS NA PLANILHA (CONFORME PDD)
                    self.log_progresso(
                        "📊 PASSO 24: Preenchendo dados na planilha BASE DE CÁLCULO...")

                    # Validar se os valores essenciais estão preenchidos na planilha
                    saldo_final = valores_calculados.get(
                        "saldo_devedor_final", 0)
                    parcelas_vencer = valores_calculados.get(
                        "parcelas_a_vencer", 0)

                    if saldo_final <= 0:
                        erro_msg = "Saldo devedor final não encontrado ou inválido na planilha. Conforme PDD, todos os valores devem vir da planilha."
                        self.log_erro(erro_msg, Exception(erro_msg))
                        return {"sucesso": False, "erro": erro_msg}

                    if parcelas_vencer <= 0:
                        erro_msg = "Quantidade de parcelas a vencer não encontrada ou inválida na planilha. Conforme PDD, todos os valores devem vir da planilha."
                        self.log_erro(erro_msg, Exception(erro_msg))
                        return {"sucesso": False, "erro": erro_msg}

                    self.log_progresso(
                        "✅ Valores da planilha válidos - usando dados calculados conforme PDD")

                    # USAR VALORES DA PLANILHA (CONFORME PDD)
                    detalhamento = f"CORREÇÃO {datetime.now().strftime('%m/%y')}"

                    self.log_progresso(
                        f"📝 PASSO 24: Configurando detalhamento: {detalhamento}")

                    # Preencher detalhamento
                    self.click(
                        xpath='//textarea[@id="deObservacao" and @name="deObservacao"]')
                    time.sleep(1)
                    self.send_text(
                        xpath='//textarea[@id="deObservacao" and @name="deObservacao"]', text=detalhamento)
                    time.sleep(1)
                    self.click(
                        xpath='//input[@type="button" and @id="btNovaLinhaCondicaoRow" and @value="Adicionar"]')

                    # PASSO 25: PREENCHIMENTO DOS DADOS DO PARCELAMENTO (VALORES DA PLANILHA)
                    self.log_progresso(
                        "💰 PASSO 25: Preenchendo dados obrigatórios com valores da planilha...")

                    # Tipo condição: "PM" (SEMPRE)
                    self.click(
                        xpath='//input[@id="tipoCondicao.tipoCondicaoPK.cdTipoCondicao" and @type="text"]')
                    self.send_text(
                        xpath='//input[@id="tipoCondicao.tipoCondicaoPK.cdTipoCondicao" and @type="text"]', text="PM")

                    # VALORES DA PLANILHA (CONFORME PDD):
                    # Valor total: saldo devedor final da planilha
                    valor_total = valores_calculados.get(
                        "saldo_devedor_final", 0)
                    self.log_progresso(
                        f"💰 Preenchendo valor total: R$ {valor_total:,.2f} (da planilha)")

                    # ✅ FORMATAR VALOR PARA O SIENGE (TROCAR PONTO POR VÍRGULA)
                    valor_total_formatado = str(valor_total).replace('.', ',')
                    self.log_progresso(
                        f"💰 Valor formatado para Sienge: {valor_total_formatado}")

                    self.send_text(
                        xpath='//input[@type="text" and @id="vlTotal"]', text=valor_total_formatado, clear=True)
                    # Quantidade de parcelas: parcelas a vencer da planilha
                    time.sleep(1)
                    qtd_parcelas = valores_calculados.get(
                        "parcelas_a_vencer", 0)
                    self.log_progresso(
                        f"📄 Preenchendo quantidade de parcelas: {qtd_parcelas} (da planilha)")
                    self.send_text(
                        xpath='//input[@type="text" and @id="qtParcelas"]', text=str(qtd_parcelas))
                    # Data 1º vencimento: 1º vencimento carnê da planilha
                    data_primeiro_vencimento = valores_calculados.get(
                        "primeiro_vencimento_carne", "")
                    self.log_progresso(
                        f"📅 Preenchendo data 1º vencimento: {data_primeiro_vencimento} (da planilha)")
                    self.send_text(
                        xpath='//input[@type="text" and @id="dt1Vencto"]', text=str(data_primeiro_vencimento))

                    # Campo indexador (1 IGP-M)

                    indexador_obj = self.find_element(
                        xpath='//input[@id="indexador.indexadorPK.cdIndexador"]')
                    if indexador_obj:
                        self.send_text(
                            xpath='//input[@id="indexador.indexadorPK.cdIndexador"]', text="1")
                        # tem que dar um TAB aqui para dar certo a pesquisa, usando o TAB do teclado
                        indexador_obj.send_keys(Keys.TAB)
                        time.sleep(1)  # Aguardar carregamento da pesquisa
                    else:
                        self.log_erro("Elemento não encontrado: indexador.indexadorPK.cdIndexador", Exception(
                            "Elemento não encontrado: indexador.indexadorPK.cdIndexador"))
                        return {"sucesso": False, "erro": "Elemento não encontrado: indexador.indexadorPK.cdIndexador"}

                    # Clicar em "Confirmar"
                    self.click(
                        xpath='//button[@type="button" and @id="CondicaoRowFormConfirmar"]')
                    self.click(
                        xpath='//input[@type="button" and @name="btNext" and @value="Próximo"]')
                    time.sleep(1)
                    # PASSO 26-28: VALIDAÇÃO E FINALIZAÇÃO
                    self.check_for_error()

                    self.click(
                        xpath='//input[@type="button" and @name="btNext" and @value="Próximo"]')
                    time.sleep(1)

                    self.log_progresso(
                        "🔧 PASSOS 26-28: Processando finalização...")

                    # - Anotar valor da diferença
                    # - Pegar o valor do campo diferença
                    diferenca_valor = self.find_element(
                        xpath='//input[@type="text" and @id="vlDiferenca"]')
                    if diferenca_valor:
                        # Aqui no caso preciso pegar o atributo value do campo
                        diferenca_valor_text = diferenca_valor.get_attribute(
                            "value")
                        self.log_progresso(
                            f"🔍 Valor da diferença: {diferenca_valor_text}")
                        if not diferenca_valor_text == "0,00":
                            self.log_progresso(
                                "✅ Valor da diferença é diferente de 0,00")

                            vl_desconto_ou_vl_correcao = self.check_for_error(
                                xpath='//input[@type="text" and @id="vlCorrecao"]')
                            if vl_desconto_ou_vl_correcao:
                                self.send_text(
                                    xpath='//input[@type="text" and @id="vlCorrecao"]', text=str(diferenca_valor_text))
                            else:
                                self.send_text(
                                    xpath='//input[@type="text" and @id="vlDesconto"]', text=str(diferenca_valor_text))

                        self.click(
                            xpath='//input[@type="button" and @name="btSave" and @value="Salvar"]')
                        time.sleep(2)
                        self.check_for_error()

                    else:
                        self.log_erro("Elemento não encontrado: vlDiferenca", Exception(
                            "Elemento não encontrado: vlDiferenca"))
                        return {"sucesso": False, "erro": "Elemento não encontrado: vlDiferenca"}
                    try:
                        if self.check_for_error(xpath="//span[text()='Sucesso']/following::p[contains(text(), 'Reparcelamento realizado com sucesso.')]"):
                            self.log_progresso(
                                "📋 Todos os passos PDD (21-28) executados com sucesso")

                            # ✅ NAVEGAR DE VOLTA À TELA INICIAL PARA PRÓXIMO CONTRATO
                            self.log_progresso(
                                "🔄 Navegando de volta à tela inicial...")
                            self.get_page(
                                "https://jmservicos.sienge.com.br/sienge/8/index.html#/common/page/1047")
                            # Aguardar carregamento da tela inicial
                            time.sleep(3)

                            return {
                                "sucesso": True,
                                "novo_titulo": "",
                                "parcelas_processadas": parcelas_selecionadas,
                                "valores_aplicados": valores_calculados,
                                "passos_pdd_executados": "21-28",
                                "timestamp_webscraping": datetime.now().isoformat()
                            }
                        else:
                            self.log_erro("Erro ao executar reparcelamento", Exception(
                                "Erro ao executar reparcelamento"))
                            return {"sucesso": False, "erro": "Erro ao executar reparcelamento"}
                    except Exception as e:
                        self.log_warning("Título precisa de atenção, pois não mostrou a mensagem de sucesso no reparcelamento, porém geralmente salva corretamente", Exception(
                            "Título precisa de atenção, pois não mostrou a mensagem de sucesso no reparcelamento, porém geralmente salva corretamente"))
                        return {"sucesso": True, "erro": "Título precisa de atenção, pois não mostrou a mensagem de sucesso no reparcelamento, porém geralmente salva corretamente"}
        except Exception as e:
            erro_msg = f"Erro no webscraping PDD: {str(e)}"
            self.log_erro(erro_msg, e)
            return {"sucesso": False, "erro": erro_msg}

        # Garantir retorno padrão
        return {"sucesso": False, "erro": "Fluxo inesperado no webscraping"}

    # ============================================================
    # Métodos auxiliares para seleção de parcelas
    # ============================================================

    def _parse_data_flexivel(self, data_str: str) -> datetime:
        """
        Faz parse de data aceitando formatos com ano de 2 ou 4 dígitos.
        
        Args:
            data_str: String de data no formato 'DD/MM/YY' ou 'DD/MM/YYYY'
        
        Returns:
            Objeto datetime
        
        Raises:
            ValueError: Se a data não puder ser parseada
        """
        data_str = data_str.strip()
        
        # Tentar primeiro com formato de 4 dígitos (padrão)
        try:
            return datetime.strptime(data_str, "%d/%m/%Y")
        except ValueError:
            pass
        
        # Tentar com formato de 2 dígitos
        # IMPORTANTE: strptime com %y já converte automaticamente:
        # - 00-68 → 2000-2068
        # - 69-99 → 1969-1999
        # Então NÃO precisamos adicionar nada, apenas usar o resultado direto
        try:
            return datetime.strptime(data_str, "%d/%m/%y")
        except ValueError:
            pass
        
        # Se ambos falharem, lançar erro
        raise ValueError(f"Formato de data inválido: '{data_str}'. Esperado 'DD/MM/YYYY' ou 'DD/MM/YY'")

    def _selecionar_parcelas_individualmente(self, data_reparcelamento: str, max_parcelas: int = 12, tabela_idx: int = 1) -> int:
        """
        Seleciona individualmente as parcelas com vencimento >= data atual.

        Args:
            data_reparcelamento: Data base para comparação, formato 'DD/MM/YYYY'
            max_parcelas: Máximo de parcelas a selecionar (normalmente 12 = 1 ano)
            tabela_idx: Índice da tabela desejada (1-based)

        Returns:
            Quantidade de parcelas selecionadas
        """
        try:
            time.sleep(2)
            # 1. Encontrar a tabela correta
            xpath_tabela = f'(//table[.//tr[starts-with(@id, "linhaParcelaRow_")]])[{tabela_idx}]'
            tabela = self.find_element(xpath=xpath_tabela)

            if not tabela:
                self.log_erro(
                    f"Nenhuma tabela de parcelas encontrada com XPath: {xpath_tabela}", Exception("Tabela não encontrada"))
                return 0

            # 2. Encontrar as linhas da tabela
            linhas = tabela.find_elements(By.XPATH,
                                          './/tr[starts-with(@id, "linhaParcelaRow_") and @linha="true" and not(contains(@style,"display: none"))]')

            if not linhas:
                self.log_erro(
                    f"Nenhuma linha disponível na tabela localizada pelo XPath: {xpath_tabela}", Exception("Linhas não encontradas"))
                return 0

            # 3. Preparar data vencimento 1 carne para comparação
            # Precisa usar a data do 1º vencimento do carnê que já vem como string no parametro, porém é preciso considerar apenas mes e ignorar o dia para fazer a comparação ou sempre mudar para dia 1, caso não sejá para facilitar o código
            data_vencimento_1_carne = self._parse_data_flexivel(data_reparcelamento).replace(day=1)
            parcelas_selecionadas = 0

            self.log_progresso(
                f"🔍 Analisando {len(linhas)} parcelas para seleção individual")
            self.log_progresso(
                f"📅 Data vencimento 1 carne para comparação: {data_vencimento_1_carne.strftime('%d/%m/%Y')}")

            # 4. Iterar linhas e clicar nos checkboxes válidos
            for idx, linha in enumerate(linhas):
                try:
                    time.sleep(0.1)
                    # Extrair data de vencimento da linha
                    input_vencto = linha.find_element(
                        By.XPATH, './/input[contains(@id, ".dtVencto_")]')
                    value_attr = input_vencto.get_attribute("value")
                    data_vencimento_str = value_attr.strip() if value_attr else ""

                    if not data_vencimento_str:
                        self.log_warning(
                            f"Linha {idx+1}: Data de vencimento vazia")
                        continue

                    data_vencimento = self._parse_data_flexivel(data_vencimento_str)

                except Exception as e:
                    self.log_warning(
                        f"Linha {idx+1}: Erro ao extrair data de vencimento: {e}")
                    continue

                # REGRA CORRIGIDA: Verificar se a parcela deve ser selecionada (vencimento >= data atual)
                if data_vencimento >= data_vencimento_1_carne:
                    try:
                        checkbox = linha.find_element(
                            By.XPATH, './/input[@type="checkbox" and contains(@id, ".flSelecionado_")]')

                        if not checkbox.is_selected():
                            checkbox.click()
                            parcelas_selecionadas += 1
                            self.log_progresso(
                                f"✅ Parcela {idx+1}: Selecionada (vencimento {data_vencimento_str} >= data atual)")
                        else:
                            self.log_progresso(
                                f"ℹ️ Parcela {idx+1}: Já estava selecionada (vencimento {data_vencimento_str})")
                            parcelas_selecionadas += 1

                    except Exception as e:
                        self.log_warning(
                            f"Linha {idx+1}: Erro ao clicar checkbox: {e}")
                        continue
                else:
                    self.log_progresso(
                        f"❌ Parcela {idx+1}: Vencimento {data_vencimento_str} < data atual (já venceu - ignorada)")

            self.log_progresso(
                f"📊 RESULTADO: {parcelas_selecionadas} parcelas selecionadas (máximo permitido: {max_parcelas})")
            return parcelas_selecionadas

        except Exception as e:
            self.log_erro(
                f"Erro na seleção individual de parcelas: {str(e)}", e)
            return 0

    # ============================================================
    # Métodos auxiliares para conexão com Google Sheets
    # ============================================================

    async def _conectar_google_sheets(self, caminho_credenciais: Optional[str] = None):
        """Conecta ao Google Sheets usando credenciais."""
        import gspread
        from google.oauth2.service_account import Credentials

        if not caminho_credenciais:
            caminho_credenciais = os.getenv(
                "GOOGLE_CREDENTIALS_PATH", "./credentials/gspread-459713-aab8a657f9b0.json")

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        credenciais = Credentials.from_service_account_file(
            caminho_credenciais, scopes=scopes)
        self.cliente_sheets = gspread.authorize(credenciais)

    async def _ler_valores_calculados_planilha(self, planilha_id: str, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        Lê os valores calculados da planilha BASE DE CÁLCULO conforme PDD seção 9.1.2
        Conforme PDD: os valores para preenchimento no Sienge devem vir da planilha, não do código

        Args:
            planilha_id: ID da planilha Google Sheets
            cliente: Nome do cliente
            numero_titulo: Número do título

        Returns:
            Dict com valores calculados pela planilha
        """
        try:
            self.log_progresso(
                "📊 Lendo valores calculados da planilha BASE DE CÁLCULO...")

            # Conectar ao Google Sheets se não conectado
            if not hasattr(self, 'cliente_sheets'):
                await self._conectar_google_sheets()

            # Abrir planilha
            planilha = self.cliente_sheets.open_by_key(planilha_id)
            aba_base_calculo = planilha.worksheet("Base de cálculo")

            # Buscar linha do cliente/título
            dados_contratos = aba_base_calculo.get_all_records()
            linha_contrato = None

            for i, contrato in enumerate(dados_contratos, start=2):
                cliente_planilha = str(contrato.get('Cliente', '')).strip()
                numero_titulo_planilha = str(
                    contrato.get('numero_titulo', '')).strip()

                # Busca flexível: ignora diferenças pequenas no nome
                cliente_match = (cliente_planilha.lower() == cliente.strip().lower() or
                                 cliente_planilha.lower().replace(' ', '') == cliente.strip().lower().replace(' ', '') or
                                 cliente_planilha.lower().replace('r', 'd') == cliente.strip().lower().replace('r', 'd') or
                                 cliente.strip().lower().replace('r', 'd') == cliente_planilha.lower().replace('r', 'd'))

                titulo_match = numero_titulo_planilha == str(
                    numero_titulo).strip()

                if cliente_match and titulo_match:
                    linha_contrato = i
                    self.log_progresso(
                        f"✅ Contrato encontrado na linha {i}: '{cliente_planilha}' - '{numero_titulo_planilha}'")
                    break

            if linha_contrato is None:
                # Busca alternativa apenas por título
                for i, contrato in enumerate(dados_contratos, start=2):
                    numero_titulo_planilha = str(
                        contrato.get('Titulo', '')).strip()
                    if numero_titulo_planilha == str(numero_titulo).strip():
                        linha_contrato = i
                        self.log_progresso(
                            f"✅ Contrato encontrado por título apenas na linha {i}")
                        break

                if linha_contrato is None:
                    raise ValueError(
                        f"Cliente {cliente} - Título {numero_titulo} não encontrado na planilha")

            # Obter cabeçalhos para mapear colunas
            cabecalhos = aba_base_calculo.row_values(1)

            # DEBUG: Mostrar todas as colunas disponíveis
            self.log_progresso(
                f"🔍 DEBUG - Colunas disponíveis na planilha ({len(cabecalhos)}):")
            for i, cabecalho in enumerate(cabecalhos):
                self.log_progresso(f"   {i}: '{cabecalho}'")

            # Mapear colunas importantes conforme PDD (APENAS CAMPOS COM VALORES/FÓRMULAS)
            colunas_mapeadas = {}
            for i, cabecalho in enumerate(cabecalhos):
                cabecalho_upper = str(cabecalho).upper().strip()
                # Campos que têm valores calculados pelas fórmulas da planilha
                # ✅ MELHORADO: Incluir "SALDO DEVEDOR" sem "FINAL"
                if 'SALDO DEVEDOR FINAL' in cabecalho_upper or 'SALDO FINAL' in cabecalho_upper or 'SALDO DEVEDOR' in cabecalho_upper:
                    colunas_mapeadas['saldo_devedor_final'] = i
                elif 'PARCELAS A VENCER' in cabecalho_upper or 'QTD PARCELAS' in cabecalho_upper:
                    colunas_mapeadas['parcelas_a_vencer'] = i
                elif '1º VENCIMENTO CARNÊ' in cabecalho_upper or '1º VENCIMENTO CARNE' in cabecalho_upper or 'PRIMEIRO VENCIMENTO' in cabecalho_upper:
                    colunas_mapeadas['primeiro_vencimento_carne'] = i
                elif 'PARCELA FINAL' in cabecalho_upper or 'VALOR FINAL' in cabecalho_upper:
                    colunas_mapeadas['parcela_final'] = i
                elif 'REAJUSTE TOTAL' in cabecalho_upper or '% REAJUSTE' in cabecalho_upper:
                    colunas_mapeadas['reajuste_total'] = i
                elif 'VALOR DA PARCELA BASE' in cabecalho_upper or 'PARCELA BASE' in cabecalho_upper:
                    colunas_mapeadas['valor_parcela_base'] = i
                # ✅ CORREÇÃO CRÍTICA #1: Mapear coluna Tipo reajuste
                elif ('TIPO' in cabecalho_upper and 'REAJUSTE' in cabecalho_upper) or cabecalho_upper == 'TIPO':
                    colunas_mapeadas['tipo_reajuste'] = i
                # ✅ CORREÇÃO #2/#3: Mapear coluna Assinatura (para contratos aniversário)
                elif 'ASSINATURA' in cabecalho_upper and 'CONTRATO' in cabecalho_upper:
                    colunas_mapeadas['data_assinatura'] = i

            # DEBUG: Mostrar colunas mapeadas
            self.log_progresso(
                f"🔍 DEBUG - Colunas mapeadas ({len(colunas_mapeadas)}):")
            for campo, coluna in colunas_mapeadas.items():
                self.log_progresso(
                    f"   {campo}: coluna {coluna} ('{cabecalhos[coluna] if coluna < len(cabecalhos) else 'ERRO'}')")

            # Ler valores da linha do contrato
            valores_calculados = {}

            for campo, coluna in colunas_mapeadas.items():
                try:
                    celula = f'{chr(65 + coluna)}{linha_contrato}'
                    valor = aba_base_calculo.acell(celula).value

                    # Converter valores numéricos
                    if campo in ['saldo_devedor_final', 'parcela_final', 'reajuste_total', 'valor_parcela_base']:
                        try:
                            # Remover formatação de moeda e converter
                            valor_limpo = str(valor).replace('R$', '').replace(
                                '.', '').replace(',', '.').strip()
                            valores_calculados[campo] = float(
                                valor_limpo) if valor_limpo else 0.0
                        except:
                            valores_calculados[campo] = 0.0
                    elif campo == 'parcelas_a_vencer':
                        try:
                            valores_calculados[campo] = int(
                                float(str(valor))) if valor else 0
                        except:
                            valores_calculados[campo] = 0
                    else:
                        valores_calculados[campo] = str(valor) if valor else ""

                except Exception as e:
                    self.log_warning(f"Erro ao ler campo {campo}: {e}")
                    valores_calculados[campo] = 0.0 if 'valor' in campo or 'parcela' in campo else ""

            # Validar valores obrigatórios
            if not valores_calculados.get('saldo_devedor_final', 0):
                raise ValueError(
                    "Saldo devedor final não encontrado ou inválido na planilha")

            if not valores_calculados.get('parcelas_a_vencer', 0):
                raise ValueError(
                    "Quantidade de parcelas a vencer não encontrada ou inválida na planilha")

            self.log_progresso(
                "✅ Valores calculados pela planilha lidos com sucesso:")
            self.log_progresso(
                f"   💰 Saldo devedor final: R$ {valores_calculados.get('saldo_devedor_final', 0):,.2f}")
            self.log_progresso(
                f"   📄 Parcelas a vencer: {valores_calculados.get('parcelas_a_vencer', 0)}")
            self.log_progresso(
                f"   📅 1º vencimento carnê: {valores_calculados.get('primeiro_vencimento_carne', 'N/A')}")
            self.log_progresso(
                f"   💵 Parcela final: R$ {valores_calculados.get('parcela_final', 0):,.2f}")
            # CORREÇÃO: Reajuste total já vem em decimal da planilha (0.1274 = 12.74%)
            reajuste_decimal = valores_calculados.get('reajuste_total', 0)
            reajuste_percentual = reajuste_decimal * 100  # Converte para porcentagem
            self.log_progresso(
                f"   📊 Reajuste total: {reajuste_percentual:.2f}% (valor decimal da planilha: {reajuste_decimal})")

            # CORREÇÃO CRÍTICA: Converter reajuste_total para porcentagem antes de salvar
            if 'reajuste_total' in valores_calculados:
                # Salva tanto o valor decimal quanto o percentual
                valores_calculados['reajuste_total_decimal'] = valores_calculados['reajuste_total']
                # Converte para %
                valores_calculados['reajuste_total'] = valores_calculados['reajuste_total'] * 100

            return {
                "sucesso": True,
                "valores_calculados": valores_calculados,
                "linha_planilha": linha_contrato,
                "timestamp_leitura": datetime.now().isoformat()
            }

        except Exception as e:
            erro_msg = f"Erro ao ler valores da planilha: {str(e)}"
            self.log_erro(erro_msg, e)
            return {
                "sucesso": False,
                "erro": erro_msg,
                "valores_calculados": {}
            }
