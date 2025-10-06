"""
RPA Sienge - Módulo de extração de relatórios
============================================

Responsável apenas por autenticar no Sienge, navegar até o relatório de
saldo devedor e realizar o download do arquivo Excel correspondente ao
contrato informado. Não realiza cálculos, persistência em banco ou
retroalimentação de planilhas.

Desenvolvido em Português Brasileiro seguindo o PDD original.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from core.base_rpa import BaseRPA, ResultadoRPA
from core.utils_sienge import carregar_credenciais_sienge

# As importações de selenium permanecem alinhadas ao módulo original
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


@dataclass
class ContratoExtracao:
    """Estrutura validada para o contrato alvo da extração."""

    codigo_cliente: str
    numero_titulo: str
    cliente: Optional[str] = None


class RPAExtracaoRelatorioSienge(BaseRPA):
    """RPA dedicado exclusivamente à extração de relatórios financeiros."""

    def __init__(self, headless: Optional[bool] = None) -> None:
        super().__init__(
            nome_rpa="SiengeExtracao",
            usar_browser=True,
            headless=headless,
        )
        self.logado_sienge = False
        self.credenciais_sienge: Dict[str, str] = {}
        self.pasta_planilhas = Path("dados_extraidos/planilhas_sienge")
        self.pasta_planilhas.mkdir(parents=True, exist_ok=True)

    async def executar(self, parametros: Dict[str, Any]) -> ResultadoRPA:
        """Executa a extração utilizando a fila de contratos pendentes."""

        limite = parametros.get("limite", 0)

        credenciais = await carregar_credenciais_sienge()
        contratos = await self._buscar_contratos_pendentes(limite=limite)

        if not contratos:
            self.log("Nenhum contrato com status PENDENTE foi encontrado.")
            return ResultadoRPA(
                sucesso=True,
                mensagem="Nenhum contrato pendente para extração",
                dados={"contratos_processados": 0, "contratos": []},
            )

        self.log(
            f"Iniciando extração de {len(contratos)} contrato(s) pendente(s)."
        )

        self._configurar_credenciais(credenciais)
        await self.inicializar()
        await self._fazer_login_sienge()

        contratos_processados: List[Dict[str, Any]] = []
        erros: List[Dict[str, Any]] = []

        for contrato_raw in contratos:
            try:
                contrato = self._validar_contrato(contrato_raw)
                self.log(
                    f"Exportando relatório para contrato {contrato.codigo_cliente}-{contrato.numero_titulo}."
                )
                arquivo_relatorio = await self._exportar_relatorio_contrato(
                    contrato
                )

                await self._atualizar_status_contrato(
                    numero_titulo=contrato.numero_titulo,
                    status="AGUARDANDO_APROVACAO",
                    dados_adicionais={
                        "timestamp_download": datetime.now().isoformat(),
                        "arquivo_relatorio": str(arquivo_relatorio),
                    },
                )

                contratos_processados.append(
                    {
                        "codigo_cliente": contrato.codigo_cliente,
                        "numero_titulo": contrato.numero_titulo,
                        "cliente": contrato.cliente,
                        "arquivo_relatorio": str(arquivo_relatorio),
                    }
                )
                self.log(
                    f"Contrato {contrato.numero_titulo} atualizado para AGUARDANDO_APROVACAO."
                )
            except Exception as erro:
                await self._atualizar_status_contrato(
                    numero_titulo=str(contrato_raw.get("numero_titulo", "")),
                    status="ERRO",
                    dados_adicionais={
                        "erro_extracao": str(erro),
                        "timestamp_erro": datetime.now().isoformat(),
                    },
                )
                erros.append(
                    {
                        "numero_titulo": contrato_raw.get("numero_titulo"),
                        "codigo_cliente": contrato_raw.get("codigo_cliente"),
                        "erro": str(erro),
                    }
                )
                self.log(
                    f"Erro ao processar contrato {contrato_raw.get('numero_titulo')}: {erro}"
                )

        await self.finalizar()

        mensagem = (
            f"Contratos extraídos: {len(contratos_processados)} | "
            f"Erros: {len(erros)}"
        )

        self.log(mensagem)

        return ResultadoRPA(
            sucesso=len(erros) == 0,
            mensagem=mensagem,
            dados={
                "contratos_processados": len(contratos_processados),
                "contratos": contratos_processados,
                "erros": erros,
            },
        )

    def _validar_contrato(self, contrato_raw: Any) -> ContratoExtracao:
        if not isinstance(contrato_raw, dict):
            raise ValueError(
                "Contrato inválido: esperado dicionário com os campos exigidos.")

        codigo = str(contrato_raw.get("codigo_cliente", "")).strip()
        titulo = str(contrato_raw.get("numero_titulo", "")).strip()
        cliente = contrato_raw.get("cliente")

        if not codigo or not titulo:
            raise ValueError(
                "Contrato inválido: informe 'codigo_cliente' e 'numero_titulo'.")

        return ContratoExtracao(codigo_cliente=codigo, numero_titulo=titulo, cliente=cliente)

    def _configurar_credenciais(self, credenciais: Dict[str, str]) -> None:
        self.credenciais_sienge = credenciais

    async def _buscar_contratos_pendentes(self, limite: int = 0) -> List[Dict[str, Any]]:
        """Busca contratos com status PENDENTE no repositório transacional."""

        from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo

        contratos = repositorio_contratos_arquivo.listar_por_status(
            "PENDENTE", limite=limite or None)

        # Normaliza campos fundamentais
        for contrato in contratos:
            contrato["numero_titulo"] = str(contrato.get(
                "Titulo", contrato.get("numero_titulo", ""))).strip()
            contrato["codigo_cliente"] = str(contrato.get(
                "Código Cliente", contrato.get("codigo_cliente", ""))).strip()
            contrato["cliente"] = contrato.get(
                "Cliente", contrato.get("cliente", ""))
            contrato["_id"] = contrato.get("_id")

        self.log(f"Contratos selecionados para extração: {len(contratos)}")
        return contratos

    def log(self, mensagem: str) -> None:
        """Encapsula registro de logs padronizados."""

        print(f"[EXTRACAO_SIENGE] {mensagem}")

    async def _atualizar_status_contrato(
        self,
        numero_titulo: str,
        status: str,
        dados_adicionais: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Atualiza o status do contrato no MongoDB/JSON com metadados adicionais."""

        from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo

        dados_extra = dados_adicionais or {}

        # Localiza contrato pelo título
        registro = repositorio_contratos_arquivo.obter_por_titulo(
            numero_titulo)
        if not registro:
            try:
                numero_titulo_int = int(numero_titulo)
            except ValueError:
                numero_titulo_int = None

            if numero_titulo_int is not None:
                registros = repositorio_contratos_arquivo.listar_por_status(
                    "PENDENTE")
                for item in registros:
                    if item.get("Titulo") == numero_titulo_int:
                        registro = item
                        break

        if not registro:
            raise RuntimeError(
                f"Contrato {numero_titulo} não localizado no repositório para atualização de status.")

        repositorio_contratos_arquivo.atualizar_status(
            registro.get("_id"),
            status,
            dados_extra,
        )

    async def _fazer_login_sienge(self) -> None:
        """Realiza autenticação no Sienge utilizando o fluxo oficial."""

        if self.logado_sienge:
            return

        url_sienge = self.credenciais_sienge.get("url", "")
        usuario_sienge = self.credenciais_sienge.get("usuario", "")
        senha_sienge = self.credenciais_sienge.get("senha", "")

        if not url_sienge:
            raise ValueError("URL do Sienge não configurada.")

        self.get_page(url_sienge)
        time.sleep(3)

        self.send_text(
            xpath='(//input[@id="username"])[1]', text=usuario_sienge)
        self.send_text(xpath='//input[@id="password"]', text=senha_sienge)
        self.click(xpath='//*[@id="btnEntrarComSiengeID"]')
        time.sleep(2)

        self.send_text(
            xpath='//label[text()="Seu e-mail"]/following-sibling::div//input', text=usuario_sienge)
        self.click(xpath="//button[normalize-space(text())='CONTINUAR']")
        self.send_text(
            xpath="//input[@id='signup-password']", text=senha_sienge)
        self.click(xpath="//button[normalize-space(text())='ENTRAR']")

        if self.check_for_error(
            "//div[contains(@class, 'spwAlertaAviso')]//p[contains(normalize-space(.), 'Deseja prosseguir desconectando')]",
            timeout=5,
        ):
            self.click(
                xpath="//a[contains(@class, 'Button-prim') and contains(., 'Prosseguir')]")

        self.logado_sienge = True
        time.sleep(5)

        if self.check_for_error(xpath='//a[@id="pushActionRefuse" and contains(text(), "Não, obrigado")]', timeout=15):
            self.click(
                xpath='//a[@id="pushActionRefuse" and contains(text(), "Não, obrigado")]')

        if self.check_for_error(
            xpath="//div[contains(@class, 'beamerAnnouncementSnippet') and contains(@class, 'active')]",
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

        if self.check_for_error(xpath='//button[@data-testid="close-button"]', timeout=10):
            self.click(xpath='//button[@data-testid="close-button"]')

    async def _exportar_relatorio_contrato(self, contrato: ContratoExtracao) -> Path:
        """Realiza a navegação no relatório e exporta o arquivo Excel."""

        url_relatorio = (
            "https://jmservicos.sienge.com.br/sienge/8/index.html#/financeiro/contas-receber/"
            "relatorios/saldo-devedor"
        )
        self.get_page(url_relatorio)
        time.sleep(3)

        combo_pesquisa = self.find_element(
            xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']",
            condition="clickable",
        )
        combo_pesquisa.click()
        time.sleep(1)
        combo_pesquisa.clear()
        time.sleep(1)

        self.send_text_human_like(
            xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']",
            text=contrato.codigo_cliente,
        )
        time.sleep(2)
        combo_pesquisa.click()
        time.sleep(1)
        self.send_text(
            xpath="//input[@placeholder='Pesquisar cliente' and @role='combobox']",
            text=Keys.TAB,
        )
        time.sleep(1)

        self.click(xpath="//button[normalize-space()='Consultar']")
        time.sleep(3)

        if self.check_for_error(
            xpath=(
                "//div[@data-testid='snackbar']//p[@data-testid='snackbar-message' "
                "and contains(normalize-space(.), 'Informe pelo menos um dos seguintes campos')]"
            )
        ):
            raise RuntimeError(
                "Não foi possível localizar o cliente no relatório de saldo devedor."
            )

        self.click(
            xpath='//div[@role="combobox" and contains(@class, "MuiSelect-select")]')
        time.sleep(1)
        self.click(
            xpath='//li[normalize-space(.)="Todas" or normalize-space(.)="All"]')
        time.sleep(4)

        self.click(
            xpath="//button[@type='button' and contains(., 'Gerar Relatório')]")
        time.sleep(2)
        self.click(
            xpath=(
                "//legend[span[normalize-space(.)='Gerar relatório como']]/ancestor::div"
                "[contains(@class, 'MuiInputBase-root')][1]//div[@role='combobox' and contains(@class, 'MuiSelect-select')]"
            )
        )
        time.sleep(1)
        self.click(
            xpath='//li[@role="option" and @data-value="excel" and text()="EXCEL"]')
        time.sleep(1)

        self.click(
            xpath="//button[@type='button' and normalize-space()='Exportar']")
        time.sleep(5)

        arquivo_relatorio = self._localizar_planilha_baixada(contrato)
        return arquivo_relatorio

    def _localizar_planilha_baixada(self, contrato: ContratoExtracao) -> Path:
        """Localiza o arquivo mais recente e realiza a cópia para a pasta do projeto."""

        rpa_downloads_folder = os.getenv(
            "RPA_DOWNLOADS_FOLDER", "RPA_DOWNLOADS")
        if rpa_downloads_folder.startswith("/"):
            rpa_downloads_folder = rpa_downloads_folder[1:]

        # Import local para manter compatibilidade
        from platformdirs import user_downloads_dir

        downloads_dir = Path(user_downloads_dir()) / rpa_downloads_folder
        arquivos_excel = list(downloads_dir.glob("*.xlsx"))

        if not arquivos_excel:
            raise FileNotFoundError(
                "Nenhum arquivo Excel foi encontrado na pasta de downloads do RPA."
            )

        arquivo_mais_recente = max(
            arquivos_excel, key=lambda item: item.stat().st_mtime)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = self.pasta_planilhas / \
            f"sienge_{contrato.codigo_cliente}_{timestamp}.xlsx"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(arquivo_mais_recente.read_bytes())

        return destino
