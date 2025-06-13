"""
RPA Coleta de Índices Econômicos
Primeiro RPA do sistema - Coleta IPCA e IGPM dos sites oficiais e atualiza planilhas Google Sheets

Desenvolvido em Português Brasileiro
Baseado no PDD seções 6.1.1.1 e 6.1.1.2
"""

from io import BytesIO
import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import re
import time
import json
import unicodedata
import gspread
from google.oauth2.service_account import Credentials
from PyPDF2 import PdfReader
import requests
import aiohttp

# Adiciona o diretório raiz ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.base_rpa import BaseRPA, ResultadoRPA
from core.notificacoes_simples import notificar_sucesso, notificar_erro


class RPAColetaIndices(BaseRPA):
    """
    RPA responsável pela coleta automática de índices econômicos (IPCA/IGPM)
    e atualização das planilhas Google Sheets conforme especificado no PDD
    """

    def __init__(self):
        super().__init__(nome_rpa="Coleta_Indices", usar_browser=True)
        self.cliente_sheets = None
 # Ensure browser is initialized

    async def executar(self, parametros: Dict[str, Any]) -> ResultadoRPA:
        """
        Executa coleta completa de índices econômicos

        Args:
            parametros: Deve conter:
                - planilha_id: ID da planilha Google Sheets para atualizar
                - credenciais_google: Caminho para arquivo de credenciais (opcional)

        Returns:
            ResultadoRPA com dados dos índices coletados
        """
        try:
            self.log_info("📊 Iniciando coleta de índices econômicos...")
            # Valida parâmetros
            planilha_id = parametros.get("planilha_id")
            if not planilha_id:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem="ID da planilha não fornecido",
                    erro="Parâmetro 'planilha_id' é obrigatório"
                )

            # Conecta ao Google Sheets
            await self._conectar_google_sheets(parametros.get("credenciais_google") or "./credentials/google_service_account.json")

            # Coleta IPCA do IBGE
            self.log_progresso("Coletando IPCA do site oficial do IBGE")
            dados_ipca = await self._coletar_ipca_ibge()

            # Coleta IGPM da FGV
            self.log_progresso("Coletando IGPM do site oficial da FGV")
            dados_igpm = await self._coletar_igpm_fgv()

            # Atualiza planilha Google Sheets
            self.log_progresso("Atualizando planilha Google Sheets")
            await self._atualizar_planilha_sheets(planilha_id, dados_ipca, dados_igpm)

            # Salva índices coletados (MongoDB ou JSON local)
            await self._salvar_indices_coletados(dados_ipca, dados_igpm, planilha_id)

            # Monta resultado final
            resultado_dados = {
                "ipca": dados_ipca,
                "igpm": dados_igpm,
                "planilha_atualizada": planilha_id,
                "timestamp_coleta": datetime.now().isoformat()
            }

            return ResultadoRPA(
                sucesso=True,
                mensagem=f"Índices coletados com sucesso - IPCA: {dados_ipca['valor']}%, IGPM: {dados_igpm['valor']}%",
                dados=resultado_dados
            )

        except Exception as e:
            self.log_erro("Erro durante coleta de índices", e)
            return ResultadoRPA(
                sucesso=False,
                mensagem="Falha na coleta de índices econômicos",
                erro=str(e)
            )

    async def _conectar_google_sheets(self, caminho_credenciais: Optional[str] = None):
        """
        Estabelece conexão com Google Sheets usando service account

        Args:
            caminho_credenciais: Caminho para arquivo de credenciais (padrão: ./credentials/google_service_account.json)
        """
        try:
            if not caminho_credenciais:
                caminho_credenciais = ".credentials/gspread-459713-aab8a657f9b0.json"

            self.log_progresso(
                f"Conectando ao Google Sheets com credenciais: {caminho_credenciais}")

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

    async def _coletar_ipca_ibge(self) -> Dict[str, Any]:
        """
        Coleta IPCA acumulado 12 meses do site oficial do IBGE
        Conforme PDD seção 6.1.1.1

        Returns:
            Dicionário com dados do IPCA coletado
        """
        try:
            # URL oficial do IBGE conforme PDD
            url_ibge = "https://www.ibge.gov.br/explica/inflacao.php"

            if self.browser:
                self.browser.get_page(url_ibge)
            else:
                raise Exception("Browser não foi inicializado corretamente.")

            # Aguarda carregamento completo
            time.sleep(2)

            self.log_progresso("Capturando o IPCA do IBGE")
            ipca_valor = self.browser.find_element(
                xpath="(//p[@class='variavel-dado'])[2]").text

            ipca_mes_ref = self.browser.find_element(
                xpath="(//p[@class='variavel-periodo'])[2]").text
            # Se o scrapping retornar o mês junto com o valor, extrair e converter
            # Por enquanto, usa o mês atual formatado

            dados_ipca = {
                "tipo": "IPCA",
                "valor": ipca_valor.replace("%", "").strip(),
                "mes": self._converter_formato_mes(ipca_mes_ref),
                "periodo": "acumulado_12_meses",
                "fonte": "IBGE",
                "url": url_ibge,
                "metodo": "webscraping_selenium",
                "timestamp": datetime.now().isoformat()
            }

            self.log_progresso(f"✅ IPCA coletado: {ipca_valor}%")
            return dados_ipca

        except Exception as e:
            raise Exception(f"Erro na coleta do IPCA: {str(e)}")

    async def _coletar_igpm_fgv(self) -> Dict[str, Any]:
        """
        Coleta IGPM acumulado 12 meses do site oficial da FGV
        Conforme PDD seção 6.1.1.2

        Returns:
            Dicionário com dados do IGPM coletado
        """

        def obter_mes_corrente_extenso() -> str:
            """Retorna o mês e ano correntes no formato 'abril de 2025'."""
            meses = [
                "janeiro", "fevereiro", "março", "abril", "maio", "junho",
                "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
            ]
            agora = datetime.now()
            return f"{meses[agora.month - 1]} de {agora.year}"

        def extrair_acumulado_12_meses_pdf(pdf_em_memoria: BytesIO) -> Optional[Tuple[str, str]]:
            """
            Extrai o valor referente a 'Acumulado 12 meses' do PDF e o mês de referência,
            ambos como string, no formato utilizado pela planilha.

            Retorna uma tupla (valor_percentual_str, mes_referencia_str) ou None se não encontrar ambos.
            Exemplo de retorno: ("7.02", "mai.-25")
            """
            leitor = PdfReader(pdf_em_memoria)
            texto_pdf = "\n".join(pagina.extract_text()
                                  or "" for pagina in leitor.pages)
            linhas = [linha.strip()
                      for linha in texto_pdf.splitlines() if linha.strip()]

            # 1. Extrair mês de referência das primeiras linhas
            mes_referencia = None
            meses_map = {
                "janeiro": "jan.", "fevereiro": "fev.", "marco": "mar.", "março": "mar.",
                "abril": "abr.", "maio": "mai.", "junho": "jun.",
                "julho": "jul.", "agosto": "ago.", "setembro": "set.",
                "outubro": "out.", "novembro": "nov.", "dezembro": "dez."
            }
            for linha in linhas[:10]:
                linha_clean = unicodedata.normalize('NFKD', linha).encode(
                    'ASCII', 'ignore').decode('ASCII').lower()
                match = re.search(
                    r"\d{1,2}\s+de\s+([a-z]+)\s+de\s+(\d{4})", linha_clean)
                if match:
                    mes_nome = match.group(1)
                    ano = match.group(2)[2:]  # Dois últimos dígitos
                    abrev = meses_map.get(mes_nome)
                    if abrev:
                        mes_referencia = f"{abrev}-{ano}".lower()
                        break

            # 2. Extrair valor acumulado 12 meses
            valor_acumulado = None
            for i, linha in enumerate(linhas):
                if re.search(r"Acumulado\s*12\s*meses", linha, re.IGNORECASE):
                    for j in range(i + 1, min(i + 4, len(linhas))):
                        percentuais = re.findall(
                            r"([+-]?\d{1,3},\d{2})\s*%", linhas[j])
                        if percentuais:
                            valor_str = percentuais[-1].replace(",", ".")
                            valor_acumulado = valor_str
                            break
                    if valor_acumulado is not None:
                        break

            if valor_acumulado is None:
                percentuais = re.findall(
                    r"([+-]?\d{1,3},\d{2})\s*%", texto_pdf)
                if percentuais:
                    valor_str = max(
                        percentuais, key=lambda x: float(x.replace(",", ".")))
                    valor_acumulado = valor_str.replace(",", ".")

            if valor_acumulado is not None and mes_referencia:
                return valor_acumulado, mes_referencia

            return None

        def limpar_pasta_download(diretorio: str):
            """Remove todos os arquivos do diretório de download."""
            for f in os.listdir(diretorio):
                try:
                    os.remove(os.path.join(diretorio, f))
                except Exception:
                    pass

        def aguardar_download_pasta(diretorio: str, timeout: int = 30) -> str:
            """Aguarda até um arquivo PDF aparecer no diretório."""
            tempo_inicial = time.time()
            while time.time() - tempo_inicial < timeout:
                arquivos = [f for f in os.listdir(
                    diretorio) if f.lower().endswith(".pdf")]
                if arquivos:
                    return os.path.join(diretorio, arquivos[0])
                time.sleep(1)
            raise TimeoutError("PDF não foi baixado no tempo esperado.")

        try:
            url_fgv = "https://portalibre.fgv.br/taxonomy/term/94"
            if not self.browser:
                raise Exception("Browser não foi inicializado corretamente.")

            self.browser.get_page(url_fgv)
            time.sleep(3)

            mes_corrente = obter_mes_corrente_extenso()

            # 1. Encontrar o primeiro artigo usando XPath robusto
            xpath_artigo = "//article"
            artigos = self.browser.find_elements(xpath=xpath_artigo)
            artigo_encontrado = artigos[0] if artigos else None

            if not artigo_encontrado:
                raise Exception("Nenhum artigo encontrado na página.")

            # 2. Clicar em "Leia mais" dentro do artigo encontrado
            try:
                link = artigo_encontrado.find_element(
                    'xpath', ".//a[contains(text(), 'Leia mais')]")
                if self.browser and self.browser._driver:
                    self.browser._driver.execute_script(
                        "arguments[0].scrollIntoView();", link)
                link.click()
            except Exception:
                raise Exception(
                    "Não foi possível clicar no link 'Leia mais' do artigo mais recente.")

            time.sleep(2)

            # 3. Encontrar o link do PDF
            xpath_pdf = "//span[contains(@class, 'file--application-pdf')]/a[contains(@href, '.pdf')]"
            links_pdf = self.find_elements(xpath=xpath_pdf)
            if not links_pdf:
                raise Exception(
                    "Link de PDF não encontrado na página do artigo.")
            link_pdf = links_pdf[0]

            # 4. Baixar o PDF pelo navegador (Selenium) e processar da pasta de download
            # Descobre o diretório padrão de download configurado
            downloads_dir = os.path.expanduser("~/Downloads/RPA_DOWNLOADS")
            limpar_pasta_download(downloads_dir)
            link_pdf.click()  # dispara o download

            caminho_pdf = aguardar_download_pasta(downloads_dir, timeout=40)
            with open(caminho_pdf, "rb") as f:
                pdf_mem = BytesIO(f.read())

            valor_igpm, mes_formatado = extrair_acumulado_12_meses_pdf(pdf_mem)

            if valor_igpm is None:
                raise Exception(
                    "Valor 'Acumulado 12 meses' não encontrado no PDF.")

            # Se o scrapping retornar o mês junto com o valor, extrair e converter
            # Por enquanto, usa o mês atual formatado
            # mes_formatado = self._obter_mes_atual_formatado()

            dados_igpm = {
                "tipo": "IGPM",
                "valor": valor_igpm.replace(".", ",").strip(),
                "mes": mes_formatado,
                "periodo": "acumulado_12_meses",
                "fonte": "FGV",
                "url": url_fgv,
                "metodo": "webscraping_selenium_download",
                "timestamp": datetime.now().isoformat()
            }

            self.log_progresso(f"✅ IGPM coletado: {valor_igpm}%")
            return dados_igpm

        except Exception as e:
            raise Exception(f"Erro na coleta do IGPM: {str(e)}")

    async def _coletar_ipca_api_bcb(self) -> float:
        """
        Coleta IPCA via API do Banco Central (fallback)

        Returns:
            Valor do IPCA acumulado 12 meses
        """
        import aiohttp

        try:
            # API do BCB para IPCA acumulado 12 meses
            url_api = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.13522/dados/ultimos/1?formato=json"

            async with aiohttp.ClientSession() as session:
                async with session.get(url_api, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        dados = await response.json()
                        if dados and len(dados) > 0:
                            return float(dados[0]["valor"])

            # Se API não funcionar, usa valor de referência
            self.log_progresso(
                "⚠️ API BCB indisponível, usando valor de referência")
            return 4.62  # Valor de referência

        except Exception as e:
            self.log_progresso(
                f"⚠️ Erro na API BCB: {str(e)}, usando valor de referência")
            return 4.62

    async def _coletar_igpm_api_bcb(self) -> float:
        """
        Coleta IGPM via API do Banco Central (fallback)

        Returns:
            Valor do IGPM acumulado 12 meses
        """
        import aiohttp

        try:
            # API do BCB para IGPM acumulado 12 meses
            url_api = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.28655/dados/ultimos/1?formato=json"

            async with aiohttp.ClientSession() as session:
                async with session.get(url_api, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        dados = await response.json()
                        if dados and len(dados) > 0:
                            return float(dados[0]["valor"])

            # Se API não funcionar, usa valor de referência
            self.log_progresso(
                "⚠️ API BCB indisponível, usando valor de referência")
            return 3.89  # Valor de referência

        except Exception as e:
            self.log_progresso(
                f"⚠️ Erro na API BCB: {str(e)}, usando valor de referência")
            return 3.89

    async def _atualizar_planilha_sheets(self, planilha_id: str, dados_ipca: Dict[str, Any], dados_igpm: Dict[str, Any]):
        """
        Atualiza planilha Google Sheets com os índices coletados
        Conforme estrutura identificada na planilha do cliente

        Args:
            planilha_id: ID da planilha Google Sheets
            dados_ipca: Dados do IPCA coletado
            dados_igpm: Dados do IGPM coletado
        """
        try:
            # Abre planilha
            if not self.cliente_sheets:
                raise Exception("Cliente Google Sheets não inicializado")

            planilha = self.cliente_sheets.open_by_key(planilha_id)
            self.log_progresso(f"✅ Planilha aberta: {planilha.title}")

            # Atualiza aba IPCA
            await self._atualizar_aba_ipca(planilha, dados_ipca)

            # Atualiza aba IGPM
            await self._atualizar_aba_igpm(planilha, dados_igpm)

            self.log_progresso(
                "✅ Planilha Google Sheets atualizada com sucesso")

        except Exception as e:
            raise Exception(f"Erro ao atualizar planilha: {str(e)}")

    def _obter_mes_atual_formatado(self) -> str:
        """Retorna o mês atual no formato usado na planilha (ex: abr.-25)"""
        return datetime.now().strftime("%b.-%y").lower()

    def _converter_formato_mes(self, mes_scrapping: str) -> str:
        """
        Converte formato do scrapping (Abr/2025) para formato da planilha (abr.-25)

        Args:
            mes_scrapping: Mês no formato do scrapping (ex: "Abr/2025")

        Returns:
            Mês no formato da planilha (ex: "abr.-25")
        """
        try:
            # Mapeia meses em português para abreviações
            meses_pt = {
                'Jan': 'jan.', 'Fev': 'fev.', 'Mar': 'mar.', 'Abr': 'abr.',
                'Mai': 'mai.', 'Jun': 'jun.', 'Jul': 'jul.', 'Ago': 'ago.',
                'Set': 'set.', 'Out': 'out.', 'Nov': 'nov.', 'Dez': 'dez.'
            }

            # Parse do formato "Abr/2025"
            if '/' in mes_scrapping:
                mes_abrev, ano = mes_scrapping.strip().split('/')
                mes_abrev = mes_abrev.strip()
                ano = int(ano)

                if mes_abrev in meses_pt:
                    # Converte para formato da planilha: "abr.-25"
                    return f"{meses_pt[mes_abrev]}-{ano % 100:02d}"
                else:
                    raise ValueError(f"Mês não reconhecido: {mes_abrev}")
            else:
                # Se já está no formato esperado, retorna como está
                return mes_scrapping.lower()

        except Exception as e:
            raise Exception(
                f"Erro ao converter formato do mês '{mes_scrapping}': {str(e)}")

    def _obter_proximo_mes_esperado(self, ultimo_mes_planilha: str) -> str:
        """
        Calcula qual seria o próximo mês após o último da planilha

        Args:
            ultimo_mes_planilha: Último mês na planilha (formato: abr.-25)

        Returns:
            Próximo mês esperado no mesmo formato
        """
        try:
            # Mapeia abreviações para números
            meses_abrev = {
                'jan.': 1, 'fev.': 2, 'mar.': 3, 'abr.': 4, 'mai.': 5, 'jun.': 6,
                'jul.': 7, 'ago.': 8, 'set.': 9, 'out.': 10, 'nov.': 11, 'dez.': 12
            }

            # Parse do último mês da planilha
            partes = ultimo_mes_planilha.strip().split('-')
            if len(partes) != 2:
                raise ValueError(
                    f"Formato de mês inválido: {ultimo_mes_planilha}")

            mes_abrev = partes[0].lower()
            ano_curto = int(partes[1])

            if mes_abrev not in meses_abrev:
                raise ValueError(
                    f"Abreviação de mês desconhecida: {mes_abrev}")

            mes_num = meses_abrev[mes_abrev]

            # Calcula próximo mês
            if mes_num == 12:  # Dezembro -> Janeiro do próximo ano
                proximo_mes = 1
                proximo_ano = ano_curto + 1
            else:
                proximo_mes = mes_num + 1
                proximo_ano = ano_curto

            # Converte de volta para o formato da planilha
            meses_abrev_inv = {v: k for k, v in meses_abrev.items()}
            proximo_mes_abrev = meses_abrev_inv[proximo_mes]

            return f"{proximo_mes_abrev}-{proximo_ano:02d}"

        except Exception as e:
            raise Exception(f"Erro ao calcular próximo mês: {str(e)}")

    def _encontrar_ultimo_mes_com_dados(self, valores_planilha: list) -> str:
        """
        Encontra o último mês que possui dados na planilha

        Args:
            valores_planilha: Lista de todas as linhas da planilha

        Returns:
            Último mês com dados ou string vazia se não houver dados
        """
        ultimo_mes = ""

        for linha in valores_planilha:
            if len(linha) >= 2 and linha[0].strip() and linha[1].strip():
                # Linha tem mês e valor preenchidos
                ultimo_mes = linha[0].strip()

        return ultimo_mes

    async def _atualizar_aba_ipca(self, planilha, dados_ipca: Dict[str, Any]):
        """
        Atualiza aba IPCA da planilha com lógica flexível para meses

        Args:
            planilha: Objeto da planilha Google Sheets
            dados_ipca: Dados do IPCA para inserir
        """
        try:
            # Acessa aba IPCA
            aba_ipca = planilha.worksheet("IPCA")
            valores_existentes = aba_ipca.get_all_values()

            # Adiciona mês aos dados se não estiver presente
            if 'mes' not in dados_ipca:
                dados_ipca['mes'] = self._obter_mes_atual_formatado()

            mes_dados = dados_ipca['mes']
            valor_coletado = f'{dados_ipca["valor"]}%'

            # Procura se o mês já existe na planilha
            linha_mes_existente = None
            for i, linha in enumerate(valores_existentes):
                if len(linha) >= 2 and linha[0].strip().lower() == mes_dados.lower():
                    linha_mes_existente = i + 1  # Google Sheets usa índice baseado em 1
                    valor_existente = linha[1].strip()

                    if valor_existente == valor_coletado:
                        self.log_progresso(
                            f"📋 IPCA {mes_dados}: Valor coletado ({valor_coletado}) "
                            f"é igual ao valor existente na planilha. Nenhuma alteração necessária."
                        )
                        return
                    else:
                        self.log_progresso(
                            f"🔄 IPCA {mes_dados}: Atualizando valor de {valor_existente} "
                            f"para {valor_coletado} (linha {linha_mes_existente})"
                        )
                        # Atualiza valor na linha existente
                        aba_ipca.update_acell(
                            f'B{linha_mes_existente}', valor_coletado)
                        self.log_progresso(
                            f"✅ IPCA {mes_dados} atualizado com sucesso na linha {linha_mes_existente}"
                        )
                        return

            # Se chegou aqui, o mês não existe na planilha - criar nova linha
            self.log_progresso(
                f"➕ IPCA {mes_dados}: Mês não encontrado na planilha, criando nova linha"
            )

            # Encontra próxima linha vazia (abaixo do último valor válido)
            linhas_usadas = [i for i, linha in enumerate(valores_existentes)
                             if len(linha) >= 2 and linha[0].strip() and linha[1].strip()]
            # +2 porque índice é baseado em 1 e queremos linha abaixo
            proxima_linha = max(linhas_usadas) + 2 if linhas_usadas else 2

            # Atualiza células
            aba_ipca.update_acell(f'A{proxima_linha}', mes_dados)
            aba_ipca.update_acell(f'B{proxima_linha}', valor_coletado)

            self.log_progresso(
                f"✅ IPCA {dados_ipca['valor']}% inserido na linha {proxima_linha} "
                f"para o mês {mes_dados}"
            )

        except Exception as e:
            raise Exception(f"Erro ao atualizar aba IPCA: {str(e)}")

    async def _atualizar_aba_igpm(self, planilha, dados_igpm: Dict[str, Any]):
        """
        Atualiza aba IGPM da planilha com lógica flexível para meses

        Args:
            planilha: Objeto da planilha Google Sheets
            dados_igpm: Dados do IGPM para inserir
        """
        try:
            # Acessa aba IGPM
            aba_igpm = planilha.worksheet("IGPM")
            valores_existentes = aba_igpm.get_all_values()

            # Adiciona mês aos dados se não estiver presente
            if 'mes' not in dados_igpm:
                dados_igpm['mes'] = self._obter_mes_atual_formatado()

            mes_dados = dados_igpm['mes']
            valor_coletado = f'{dados_igpm["valor"]}%'

            # Procura se o mês já existe na planilha
            linha_mes_existente = None
            for i, linha in enumerate(valores_existentes):
                if len(linha) >= 2 and linha[0].strip().lower() == mes_dados.lower():
                    linha_mes_existente = i + 1  # Google Sheets usa índice baseado em 1
                    valor_existente = linha[1].strip()

                    if valor_existente == valor_coletado:
                        self.log_progresso(
                            f"📋 IGPM {mes_dados}: Valor coletado ({valor_coletado}) "
                            f"é igual ao valor existente na planilha. Nenhuma alteração necessária."
                        )
                        return
                    else:
                        self.log_progresso(
                            f"🔄 IGPM {mes_dados}: Atualizando valor de {valor_existente} "
                            f"para {valor_coletado} (linha {linha_mes_existente})"
                        )
                        # Atualiza valor na linha existente
                        aba_igpm.update_acell(
                            f'B{linha_mes_existente}', valor_coletado)
                        self.log_progresso(
                            f"✅ IGPM {mes_dados} atualizado com sucesso na linha {linha_mes_existente}"
                        )
                        return

            # Se chegou aqui, o mês não existe na planilha - criar nova linha
            self.log_progresso(
                f"➕ IGPM {mes_dados}: Mês não encontrado na planilha, criando nova linha"
            )

            # Encontra próxima linha vazia (abaixo do último valor válido)
            linhas_usadas = [i for i, linha in enumerate(valores_existentes)
                             if len(linha) >= 2 and linha[0].strip() and linha[1].strip()]
            # +2 porque índice é baseado em 1 e queremos linha abaixo
            proxima_linha = max(linhas_usadas) + 2 if linhas_usadas else 2

            # Atualiza células
            aba_igpm.update_acell(f'A{proxima_linha}', mes_dados)
            aba_igpm.update_acell(f'B{proxima_linha}', valor_coletado)

            self.log_progresso(
                f"✅ IGPM {dados_igpm['valor']}% inserido na linha {proxima_linha} "
                f"para o mês {mes_dados}"
            )

        except Exception as e:
            raise Exception(f"Erro ao atualizar aba IGPM: {str(e)}")

    def processar_dados_com_mes_scrapping(self, dados_indice: Dict[str, Any], mes_scrapping: str) -> Dict[str, Any]:
        """
        Processa dados do índice substituindo o mês pelo formato do scrapping convertido

        Args:
            dados_indice: Dados originais do índice
            mes_scrapping: Mês no formato do scrapping (ex: "Abr/2025")

        Returns:
            Dados atualizados com mês convertido
        """
        dados_atualizados = dados_indice.copy()
        dados_atualizados['mes'] = self._converter_formato_mes(mes_scrapping)
        dados_atualizados['mes_original_scrapping'] = mes_scrapping
        return dados_atualizados

    async def _salvar_indices_coletados(self, dados_ipca: Dict[str, Any], dados_igpm: Dict[str, Any], planilha_id: str):
        """
        Salva índices coletados no MongoDB ou fallback para JSON local

        Args:
            dados_ipca: Dados do IPCA coletado
            dados_igpm: Dados do IGPM coletado
            planilha_id: ID da planilha atualizada
        """
        try:
            if self.mongo_manager and self.mongo_manager.conectado:
                # Salva no MongoDB
                collection = self.mongo_manager.database.indices_coletados
                documento = {
                    "timestamp": datetime.now(),
                    "ipca": dados_ipca,
                    "igpm": dados_igpm,
                    "planilha_id": planilha_id,
                    "tipo": "coleta_indices"
                }
                await collection.insert_one(documento)
                self.log_progresso("✅ Índices salvos no MongoDB")
            else:
                # Fallback para JSON local
                await self._salvar_indices_local(dados_ipca, dados_igpm, planilha_id)

        except Exception as e:
            self.log_progresso(
                f"⚠️ Erro ao salvar no MongoDB: {str(e)} - usando fallback local")
            await self._salvar_indices_local(dados_ipca, dados_igpm, planilha_id)

    async def _salvar_indices_local(self, dados_ipca: Dict[str, Any], dados_igpm: Dict[str, Any], planilha_id: str):
        """
        Salva índices localmente em JSON como fallback

        Args:
            dados_ipca: Dados do IPCA
            dados_igpm: Dados do IGPM
            planilha_id: ID da planilha
        """
        try:
            # Garante que o diretório existe
            os.makedirs("dados_processamento", exist_ok=True)

            # Nome único do arquivo
            arquivo_indices = "dados_processamento/indices_coletados.json"

            # Carrega dados existentes ou cria lista vazia
            dados_existentes = []
            if os.path.exists(arquivo_indices):
                with open(arquivo_indices, 'r', encoding='utf-8') as f:
                    dados_existentes = json.load(f)

            # Adiciona novo registro
            novo_registro = {
                "timestamp": datetime.now().iso