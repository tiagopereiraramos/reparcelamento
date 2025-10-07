"""RPA Sienge - Módulo de reparcelamento completo (versão JSON).

Responsável por:

1. Buscar contratos elegíveis no repositório JSON transacional.
2. Autenticar no Sienge.
3. Executar webscraping completo do reparcelamento conforme PDD.
4. Atualizar status dos contratos e armazenar metadados relevantes.

Desenvolvido em Português Brasileiro seguindo as diretrizes oficiais.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from core.base_rpa import BaseRPA, ResultadoRPA
from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo
from core.status_contratos import StatusContrato
from core.utils_sienge import carregar_credenciais_sienge, log


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

    def __init__(self, headless: Optional[bool] = None) -> None:
        super().__init__(
            nome_rpa="SiengeReparcelamento",
            usar_browser=True,
            headless=headless,
        )
        self.logado_sienge = False
        self.credenciais_sienge: Dict[str, str] = {}

    async def executar(self, limite: int = 0) -> ResultadoRPA:
        """Processa contratos com status ``APROVACAO_REALIZADA`` da fila."""

        contratos = self._buscar_contratos_aptos(limite=limite)
        if not contratos:
            log("⚠️ Nenhum contrato com status APROVACAO_REALIZADA encontrado.")
            return ResultadoRPA(
                sucesso=True,
                mensagem="Nenhum contrato aguardando reparcelamento.",
                dados={"contratos_processados": 0, "contratos": []},
            )

        log(f"🔧 Iniciando reparcelamento de {len(contratos)} contrato(s)...")

        self.credenciais_sienge = await carregar_credenciais_sienge()
        await self.inicializar()
        await self._fazer_login_sienge()

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
                self._registrar_falha(contrato, mensagem)
                contratos_erro.append({
                    "numero_titulo": contrato.numero_titulo,
                    "codigo_cliente": contrato.codigo_cliente,
                    "mensagem": mensagem,
                })
                log(
                    f"❌ Erro inesperado no contrato {contrato.numero_titulo}: {mensagem}")

        await self.finalizar()

        return ResultadoRPA(
            sucesso=len(contratos_erro) == 0,
            mensagem=(
                "Reparcelamento concluído." if not contratos_erro
                else f"Reparcelamento concluído com {len(contratos_erro)} erro(s)."
            ),
            dados={
                "contratos_processados": len(contratos_sucesso),
                "contratos_erro": contratos_erro,
                "contratos_sucesso": contratos_sucesso,
            },
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
        """Implementação adaptada dos passos 21-28 (extraída do código original)."""

        numero_titulo = parametros.get("numero_titulo", "")
        cliente = parametros.get("cliente", "")
        url_reparcelamento = parametros.get("url_reparcelamento")

        if not numero_titulo or not url_reparcelamento:
            raise ValueError(
                "Parâmetros obrigatórios ausentes para execução do reparcelamento.")

        self.log_progresso("🌐 Iniciando reparcelamento conforme PDD...")
        self.log_progresso(f"📍 Navegando para: {url_reparcelamento}")
        self.get_page(url_reparcelamento)
        self.browser._driver.refresh()
        time.sleep(2)

        iframe_ctx = self.on_iframe(xpath='//iframe[@id="iFramePage"]')
        if iframe_ctx is None:
            raise RuntimeError(
                "Não foi possível localizar o iframe principal do reparcelamento.")

        with iframe_ctx:
            self._preencher_numero_titulo(numero_titulo)
            self._selecionar_documentos()
            data_reparcelamento = self._obter_data_reparcelamento(parametros)
            valores_planilha = self._carregar_valores_planilha(parametros)
            parcelas_selecionadas = self._selecionar_parcelas(
                data_reparcelamento=data_reparcelamento,
                primeiro_vencimento=valores_planilha.get(
                    "primeiro_vencimento_carne", ""),
            )

            if parcelas_selecionadas == 0:
                raise RuntimeError(
                    "Nenhuma parcela selecionada para reparcelamento.")

            self._preencher_detalhamento(valores_planilha)
            self._finalizar_reparcelamento()

        return {
            "sucesso": True,
            "numero_titulo": numero_titulo,
            "cliente": cliente,
            "parcelas_selecionadas": parcelas_selecionadas,
            "timestamp": datetime.now().isoformat(),
        }

    # ============================================================
    # Webscraping helpers (adaptados do código original)
    # ============================================================

    def _preencher_numero_titulo(self, numero_titulo: str) -> None:
        self.log_progresso(f"🔍 PASSO 21: Consultando título: {numero_titulo}")
        titulo = self.browser.check_for_error(
            xpath="//input[@id='titulo.tituloPK.nuTitulo']",
            timeout=10,
            condition="presence",
        )
        if not titulo:
            raise TimeoutError(
                "Campo de número do título não encontrado dentro do tempo esperado.")

        time.sleep(2)
        self.click("//input[@id='titulo.tituloPK.nuTitulo']")
        self.send_text_human_like(
            "//input[@id='titulo.tituloPK.nuTitulo']",
            text=numero_titulo,
        )
        self.click("//input[@type='button' and @name='btFiltrar']")
        time.sleep(3)

    def _selecionar_documentos(self) -> None:
        self.log_progresso(
            "✅ PASSO 22: Título listado - selecionando documentos")
        self.click("//input[@type='button' and @name='btNext']")
        time.sleep(5)

        tabela = self.find_element(xpath='//table[@id="TituloRow"]')
        if not tabela:
            raise RuntimeError("Tabela de documentos não localizada.")

        radios = tabela.find_elements(
            By.XPATH,
            './/input[@type="radio" and contains(@id, "flSelecionado_") and not(ancestor::tr[contains(@style, "display: none")])]',
        )
        for radio in radios:
            radio.click()

        self.click(
            '//input[@type="button" and @name="btNext" and @value="Próximo"]')
        time.sleep(3)

    def _obter_data_reparcelamento(self, parametros: Dict[str, Any]) -> str:
        data_reparcelamento = parametros.get("data_reparcelamento", "")
        if not data_reparcelamento:
            mes_atual = datetime.now()
            data_reparcelamento = (
                (mes_atual.replace(day=1) + timedelta(days=32))
                .replace(day=1)
                .strftime("%d/%m/%Y")
            )
        self.log_progresso(
            f"📅 Data base para reparcelamento: {data_reparcelamento}")
        return data_reparcelamento

    def _carregar_valores_planilha(self, parametros: Dict[str, Any]) -> Dict[str, Any]:
        planilha_id = os.getenv("PLANILHA_CALCULO_ID")
        if not planilha_id:
            raise RuntimeError(
                "PLANILHA_CALCULO_ID não configurada. Conforme PDD, todos os valores devem vir da planilha.")

        if not hasattr(self, "cliente_sheets"):
            import asyncio

            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._conectar_google_sheets())

        import asyncio

        planilha = self.cliente_sheets.open_by_key(planilha_id)
        loop = asyncio.get_event_loop()
        resultado_leitura = loop.run_until_complete(
            self._ler_valores_calculados_planilha(
                planilha_id=planilha_id,
                cliente=parametros.get("cliente", ""),
                numero_titulo=parametros.get("numero_titulo", ""),
            )
        )

        valores_calculados = resultado_leitura.get("valores_calculados", {})
        saldo_final = valores_calculados.get("saldo_devedor_final", 0)
        parcelas_vencer = valores_calculados.get("parcelas_a_vencer", 0)

        if saldo_final <= 0 or parcelas_vencer <= 0:
            raise RuntimeError(
                "Valores essenciais não encontrados na planilha. Conforme PDD, todos os valores devem vir da planilha.")

        return valores_calculados

    def _selecionar_parcelas(self, data_reparcelamento: str, primeiro_vencimento: str) -> int:
        tabela_xpath = '(//table[.//tr[starts-with(@id, "linhaParcelaRow_")]])[1]'
        tabela = self.find_element(xpath=tabela_xpath)
        if not tabela:
            raise RuntimeError("Tabela de parcelas não localizada.")

        linhas = tabela.find_elements(
            By.XPATH,
            './/tr[starts-with(@id, "linhaParcelaRow_") and @linha="true" and not(contains(@style,"display: none"))]',
        )
        if not linhas:
            raise RuntimeError("Nenhuma linha de parcela encontrada.")

        data_vencimento_base = datetime.strptime(
            primeiro_vencimento, "%d/%m/%Y").replace(day=1)
        self.log_progresso(
            f"📅 1º vencimento carnê para comparação: {data_vencimento_base.strftime('%d/%m/%Y')}")

        selecionadas = 0
        for idx, linha in enumerate(linhas, start=1):
            try:
                time.sleep(0.1)
                input_vencto = linha.find_element(
                    By.XPATH, './/input[contains(@id, ".dtVencto_")]')
                data_vencimento_str = input_vencto.get_attribute("value") or ""
                if not data_vencimento_str:
                    continue
                data_vencimento = datetime.strptime(
                    data_vencimento_str, "%d/%m/%Y")

                if data_vencimento >= data_vencimento_base:
                    checkbox = linha.find_element(
                        By.XPATH,
                        './/input[@type="checkbox" and contains(@id, ".flSelecionado_")]',
                    )
                    if not checkbox.is_selected():
                        checkbox.click()
                    selecionadas += 1
            except Exception as erro:
                self.log_warning(f"Erro ao processar parcela {idx}: {erro}")
                continue

        return selecionadas

    def _preencher_detalhamento(self, valores_planilha: Dict[str, Any]) -> None:
        self.click('//textarea[@id="deObservacao" and @name="deObservacao"]')
        time.sleep(1)
        detalhamento = f"CORREÇÃO {datetime.now().strftime('%m/%y')}"
        self.send_text(
            '//textarea[@id="deObservacao" and @name="deObservacao"]',
            text=detalhamento,
            clear=True,
        )
        time.sleep(1)
        self.click(
            '//input[@type="button" and @id="btNovaLinhaCondicaoRow" and @value="Adicionar"]')

        valor_total = valores_planilha.get("saldo_devedor_final", 0)
        qt_parcelas = valores_planilha.get("parcelas_a_vencer", 0)
        primeiro_vencimento = valores_planilha.get(
            "primeiro_vencimento_carne", "")

        self.click(
            '//input[@id="tipoCondicao.tipoCondicaoPK.cdTipoCondicao" and @type="text"]')
        self.send_text(
            '//input[@id="tipoCondicao.tipoCondicaoPK.cdTipoCondicao" and @type="text"]',
            text="PM",
        )

        valor_formatado = str(valor_total).replace('.', ',')
        self.send_text(
            '//input[@type="text" and @id="vlTotal"]', text=valor_formatado, clear=True)
        self.send_text(
            '//input[@type="text" and @id="qtParcelas"]', text=str(qt_parcelas))
        self.send_text(
            '//input[@type="text" and @id="dt1Vencto"]', text=primeiro_vencimento)

        indexador_obj = self.find_element(
            '//input[@id="indexador.indexadorPK.cdIndexador"]')
        if indexador_obj:
            self.send_text(
                '//input[@id="indexador.indexadorPK.cdIndexador"]',
                text="1",
                clear=True,
            )
            indexador_obj.send_keys(Keys.TAB)
            time.sleep(1)
        else:
            raise RuntimeError(
                "Elemento indexador.indexadorPK.cdIndexador não localizado.")

        self.click(
            '//button[@type="button" and @id="CondicaoRowFormConfirmar"]')
        self.click(
            '//input[@type="button" and @name="btNext" and @value="Próximo"]')
        time.sleep(1)

    def _finalizar_reparcelamento(self) -> None:
        self.click(
            '//input[@type="button" and @name="btNext" and @value="Próximo"]')
        time.sleep(1)

        diferenca_valor = self.find_element(
            '//input[@type="text" and @id="vlDiferenca"]')
        if diferenca_valor:
            diferenca_valor_text = diferenca_valor.get_attribute("value") or ""
            if diferenca_valor_text and diferenca_valor_text != "0,00":
                campo_correcao = self.check_for_error(
                    '//input[@type="text" and @id="vlCorrecao"]')
                destino_xpath = (
                    '//input[@type="text" and @id="vlCorrecao"]'
                    if campo_correcao
                    else '//input[@type="text" and @id="vlDesconto"]'
                )
                self.send_text(
                    destino_xpath, text=diferenca_valor_text, clear=True)

            self.click(
                '//input[@type="button" and @name="btSave" and @value="Salvar"]')
            time.sleep(2)
            self.check_for_error()
        else:
            raise RuntimeError("Elemento vlDiferenca não encontrado.")

        if self.check_for_error(
            "//span[text()='Sucesso']/following::p[contains(text(), 'Reparcelamento realizado com sucesso.')]",
        ):
            self.log_progresso("📋 Reparcelamento finalizado com sucesso.")
            self.get_page(
                "https://jmservicos.sienge.com.br/sienge/8/index.html#/common/page/1047")
            time.sleep(2)
        else:
            raise RuntimeError(
                "Mensagem de sucesso do reparcelamento não encontrada.")
