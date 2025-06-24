"""
Browser Manager - Baseado na sua classe Browser
Mantém compatibilidade com sua arquitetura Firefox/Gecko

Desenvolvido em Português Brasileiro
"""

import logging
import os
from contextlib import contextmanager
import random
from time import sleep
from typing import Iterator, List, Optional, Callable
import sqlite3

# Tentar importar Selenium
try:
    from selenium import webdriver
    from selenium.common.exceptions import (
        ElementClickInterceptedException,
        ElementNotInteractableException,
        InvalidElementStateException,
        NoSuchElementException,
        StaleElementReferenceException,
        TimeoutException,
    )
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service
    from selenium.webdriver.remote.webelement import WebElement
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait
    from webdriver_manager.firefox import GeckoDriverManager
    SELENIUM_DISPONIVEL = True
except ImportError:
    SELENIUM_DISPONIVEL = False

try:
    import undetected_chromedriver as uc  # type: ignore
    UC_CHROME_DISPONIVEL = True
except ImportError:
    uc = None  # type: ignore
    UC_CHROME_DISPONIVEL = False

from difflib import get_close_matches


class WindowNotFound(Exception):
    """Browser window not found."""


class RPABrowser:
    """
    Browser Manager baseado na sua classe Browser
    Implementa Firefox/Gecko seguindo sua arquitetura
    """

    def __init__(self, headless: bool = True, eager_load: bool = False, firefox_profile_path: str = '', limpar_cookies_sicredi: bool = False, usar_uc_chrome: bool = False, chrome_profile_path: str = ''):
        """
        Se firefox_profile_path não for passado, tenta buscar em FIREFOX_PROFILE_PATH do ambiente.
        """
        self._driver: Optional[WebDriver] = None
        self._driver_wait: Optional[WebDriverWait] = None
        self._original_timeout = 30
        self.actions = None
        self.logger = logging.getLogger("RPABrowser")
        # Se não passar explicitamente, tenta buscar do ambiente
        if not firefox_profile_path:
            firefox_profile_path = os.getenv(
                'FIREFOX_PROFILE_PATH', '').strip()
        self._firefox_profile_path = firefox_profile_path
        self._chrome_profile_path = chrome_profile_path

        # Inicializa o driver como None
        self._driver = None

        if usar_uc_chrome and not UC_CHROME_DISPONIVEL:
            self.logger.error(
                "❌ undetected-chromedriver não está instalado. Instale com 'pip install undetected-chromedriver'")
            return
        elif not usar_uc_chrome and not SELENIUM_DISPONIVEL:
            self.logger.warning("⚠️ Selenium não está disponível")
            return

        try:
            self._inicializar_browser(
                headless, eager_load, self._firefox_profile_path, limpar_cookies_sicredi, usar_uc_chrome, self._chrome_profile_path)

            # Se o driver foi inicializado com sucesso, configura o restante
            if self._driver:
                if usar_uc_chrome:
                    # Adiciona uma pequena pausa para o UC se estabilizar antes de interagir
                    sleep(2)

                self._driver_wait = WebDriverWait(
                    self._driver, self._original_timeout)
                self._driver.maximize_window()
                self.actions = ActionChains(self._driver)
                self.logger.info("✅ Browser inicializado e configurado")

        except Exception as e:
            self.logger.error(f"❌ Erro ao inicializar browser: {e}")
            self._driver = None

    def _inicializar_browser(self, headless: bool, eager_load: bool, firefox_profile_path: str = '', limpar_cookies_sicredi: bool = False, usar_uc_chrome: bool = False, chrome_profile_path: str = ''):
        """Inicializa o driver do browser (Firefox ou UC Chrome) e atribui a self._driver."""

        if usar_uc_chrome:
            if not UC_CHROME_DISPONIVEL or uc is None:
                self.logger.error(
                    "❌ undetected-chromedriver não está instalado. Por favor, instale com 'pip install undetected-chromedriver'")
                raise ImportError("undetected-chromedriver não instalado")

            self.logger.info("🚀 Inicializando com Undetected Chromedriver...")
            chrome_options = uc.ChromeOptions()
            if headless:
                chrome_options.add_argument("--headless")

            # Adiciona o perfil do Chrome se fornecido
            if chrome_profile_path:
                self.logger.info(
                    f"✅ Usando perfil do Chrome: {chrome_profile_path}")
                chrome_options.add_argument(
                    f'--user-data-dir={chrome_profile_path}')

            self._driver = uc.Chrome(
                options=chrome_options, enable_cdp_events=True)
            self.logger.info("✅ Undetected Chromedriver inicializado")

        else:  # Lógica do Firefox
            if not SELENIUM_DISPONIVEL:
                return

            self.options = Options()

            # Configurações baseadas na sua classe
            if headless:
                self.options.add_argument("--headless")

            if eager_load:
                self.options.page_load_strategy = "eager"

            self.options.add_argument("--disable-dev-shm-usage")
            self.options.add_argument("--no-sandbox")

            # Configurações de download - usar pasta RPA parametrizada
            downloads_base = os.path.expanduser("~/Downloads")
            rpa_downloads_folder = os.getenv(
                'RPA_DOWNLOADS_FOLDER', 'RPA_DOWNLOADS')

            # Garantir concatenação correta do caminho - todos os casos
            if downloads_base.endswith('/') and rpa_downloads_folder.startswith('/'):
                # Caso: "/Downloads/" + "/RPA_DOWNLOADS" -> "/Downloads/RPA_DOWNLOADS"
                downloads_dir = downloads_base + rpa_downloads_folder[1:]
            elif downloads_base.endswith('/') and not rpa_downloads_folder.startswith('/'):
                # Caso: "/Downloads/" + "RPA_DOWNLOADS" -> "/Downloads/RPA_DOWNLOADS"
                downloads_dir = downloads_base + rpa_downloads_folder
            elif not downloads_base.endswith('/') and rpa_downloads_folder.startswith('/'):
                # Caso: "/Downloads" + "/RPA_DOWNLOADS" -> "/Downloads/RPA_DOWNLOADS"
                downloads_dir = downloads_base + rpa_downloads_folder
            else:
                # Caso: "/Downloads" + "RPA_DOWNLOADS" -> "/Downloads/RPA_DOWNLOADS"
                downloads_dir = os.path.join(
                    downloads_base, rpa_downloads_folder)

            os.makedirs(downloads_dir, exist_ok=True)

            self.options.set_preference("browser.download.folderList", 2)
            self.options.set_preference("browser.download.dir", downloads_dir)
            self.options.set_preference(
                "browser.helperApps.neverAsk.saveToDisk",
                "application/pdf,application/octet-stream,text/csv,application/vnd.ms-excel"
            )
            self.options.set_preference(
                "browser.download.useDownloadDir", True)
            self.options.set_preference("pdfjs.disabled", True)

            # Opções de SSL/TLS para ambientes restritos (NÃO altera legado)
            # Para aceitar certificados inválidos, defina RPA_ACCEPT_INSECURE_CERTS=true no ambiente
            if os.getenv('RPA_ACCEPT_INSECURE_CERTS', 'false').lower() == 'true':
                self.options.set_preference(
                    'webdriver_accept_untrusted_certs', True)
                self.options.set_preference(
                    'webdriver_assume_untrusted_issuer', False)
                self.logger.warning(
                    '⚠️ Aceitando certificados SSL inseguros (apenas para debug)!')

            # Tentar usar GeckoDriver
            try:
                gecko_driver_path = GeckoDriverManager().install()
            except Exception:
                # Fallback para caminho padrão
                gecko_driver_path = "/usr/local/bin/geckodriver"

            # Se um perfil for fornecido, use-o (para plugins bancários, certificados, etc)
            if firefox_profile_path and isinstance(firefox_profile_path, str) and firefox_profile_path.strip():
                # Limpa cookies do Sicredi apenas se explicitamente solicitado
                if limpar_cookies_sicredi:
                    self.logger.info(
                        f"Iniciando limpeza de cookies do Sicredi no profile: {firefox_profile_path}")
                    cookies_file = os.path.join(
                        firefox_profile_path, "cookies.sqlite")
                    if os.path.exists(cookies_file):
                        try:
                            conn = sqlite3.connect(cookies_file)
                            cur = conn.cursor()
                            # Tenta executar a query, mas não falha se a coluna não existir
                            try:
                                cur.execute(
                                    "SELECT COUNT(*) FROM moz_cookies WHERE baseDomain LIKE '%sicredi.com.br%'")
                                count = cur.fetchone()[0]
                                if count > 0:
                                    self.logger.info(
                                        f"Encontrados {count} cookies do Sicredi. Removendo...")
                                    cur.execute(
                                        "DELETE FROM moz_cookies WHERE baseDomain LIKE '%sicredi.com.br%'")
                                    conn.commit()
                                    self.logger.info(
                                        f"{count} cookies do Sicredi removidos do profile antes de inicializar o browser.")
                                else:
                                    self.logger.info(
                                        "Nenhum cookie do Sicredi encontrado para remover.")
                            except sqlite3.OperationalError as db_err:
                                self.logger.warning(
                                    f"Não foi possível limpar cookies do Sicredi (schema do banco pode ter mudado): {db_err}")

                            conn.close()
                        except Exception as e:
                            self.logger.warning(
                                f"Falha ao acessar o arquivo de cookies do Sicredi: {e}")
                    else:
                        self.logger.info(
                            f"Arquivo de cookies não encontrado no profile: {cookies_file}")

                # ATUALIZADO: Carrega o perfil diretamente no options, que é a forma moderna e mais estável
                self.options.profile = firefox_profile_path

                self._driver = webdriver.Firefox(
                    service=Service(gecko_driver_path),
                    options=self.options
                )
                self.logger.info(
                    f"✅ Firefox inicializado com perfil: {firefox_profile_path}")
                # Limpa todos os cookies da sessão ao iniciar com perfil
                if self._driver:
                    self._driver.delete_all_cookies()
            else:
                self._driver = webdriver.Firefox(service=Service(gecko_driver_path),
                                                 options=self.options)

        # Não configurar o restante aqui, será feito no __init__

    def set_timeout(self, timeout: int):
        """Define timeout personalizado"""
        if self._driver_wait:
            self._driver_wait._timeout = timeout

    def reset_timeout(self):
        """Reseta timeout para valor original"""
        if self._driver_wait:
            self._driver_wait._timeout = self._original_timeout

    def get(self, url: str):
        """Navega para URL"""
        if self._driver:
            self._driver.get(url)

    def get_page(self, url: str) -> bool:
        """Navega para uma página - compatibilidade"""
        try:
            self.get(url)
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro ao acessar {url}: {e}")
            return False

    @staticmethod
    def _get_condition(condition: str) -> Callable:
        """Retorna função de condição baseada no nome"""
        conditions = {
            "visible": EC.visibility_of_element_located,
            "visible_any": EC.visibility_of_any_elements_located,
            "visible_all": EC.visibility_of_all_elements_located,
            "clickable": EC.element_to_be_clickable,
            "selected": EC.element_to_be_selected,
            "located_all": EC.presence_of_all_elements_located,
            "presence": EC.presence_of_element_located,
        }
        return conditions.get(condition, EC.presence_of_element_located)

    def find_element(self,
                     xpath: str,
                     condition: str = "presence") -> WebElement:
        """Aguarda e retorna elemento único"""
        if not self._driver or not self._driver_wait:
            raise NoSuchElementException("Browser não inicializado")

        try:
            condition_func = self._get_condition(condition)
            return self._driver_wait.until(condition_func((By.XPATH, xpath)))
        except TimeoutException as exc:
            raise NoSuchElementException(
                f"Elemento com xpath {xpath} não encontrado. {exc}")

    def find_elements(self,
                      xpath: str,
                      condition: str = "located_all") -> List[WebElement]:
        """Aguarda e retorna lista de elementos"""
        if not self._driver or not self._driver_wait:
            return []

        try:
            condition_func = self._get_condition(condition)
            return self._driver_wait.until(condition_func((By.XPATH, xpath)))
        except TimeoutException as exc:
            raise NoSuchElementException(
                f"Elementos com xpath {xpath} não encontrados. {exc}")

    def click(self, xpath: str) -> None:
        """Clica em elemento com tratamento de erros"""
        if not self._driver:
            raise Exception("Browser não inicializado")

        element = self.find_element(xpath, condition="clickable")
        self._driver.execute_script("arguments[0].scrollIntoView(true);",
                                    element)

        try:
            element.click()
        except (ElementClickInterceptedException,
                ElementNotInteractableException,
                StaleElementReferenceException):
            self._driver.execute_script("arguments[0].click();", element)

    def get_text(self, xpath: str, timeout: int = 10) -> str:
        """Obtém texto do elemento"""
        while timeout > 0:
            try:
                return self.find_element(xpath).text
            except NoSuchElementException:
                sleep(1)
                timeout -= 1
        raise NoSuchElementException(
            f"Elemento com xpath {xpath} não encontrado.")

    def send_text_human_like(self,
                             xpath: str,
                             text: str,
                             clear: bool = False,
                             timeout: int = 15,
                             verify: bool = False) -> None:
        """Envia texto para elemento simulando digitação humana avançada"""
        if not self._driver:
            raise Exception("Browser não inicializado")
        element = None
        while timeout > 0:
            try:
                element = self.find_element(xpath, "clickable")
                if clear:
                    element.clear()
                # Digitação rápida, mas com pequenas variações
                for char in str(text):
                    element.send_keys(char)
                    # 30-90ms por tecla, ajustável
                    sleep(random.uniform(0.03, 0.09))

                if not verify or element.get_attribute("value") == str(text):
                    return

            except InvalidElementStateException as exc:
                if "Element is read-only" in str(exc):
                    if self._driver:
                        self._driver.execute_script(
                            "arguments[0].removeAttribute('readonly')",
                            element)
                    else:
                        raise Exception("Browser não inicializado")
                else:
                    raise
                continue

            sleep(2)
            timeout -= 1

        raise TimeoutException(
            f"Timeout enviando texto para elemento com xpath {xpath}")

    def send_text(self,
                  xpath: str,
                  text: str,
                  clear: bool = False,
                  timeout: int = 15,
                  verify: bool = False) -> None:
        """Envia texto para elemento"""
        if not self._driver:
            raise Exception("Browser não inicializado")
        element = None
        while timeout > 0:
            try:
                element = self.find_element(xpath, "clickable")
                if clear:
                    element.clear()
                element.send_keys(str(text))

                if not verify or element.get_attribute("value") == str(text):
                    return

            except InvalidElementStateException as exc:
                if "Element is read-only" in str(exc):
                    if self._driver:
                        self._driver.execute_script(
                            "arguments[0].removeAttribute('readonly')",
                            element)
                    else:
                        raise Exception("Browser não inicializado")
                    continue

            sleep(2)
            timeout -= 1

        raise TimeoutException(
            f"Timeout enviando texto para elemento com xpath {xpath}")

    def check_for_error(self,
                        xpath: Optional[str] = None,
                        condition: Optional[str] = None,
                        timeout: int = 5,
                        accept_alert: bool = True
                        ) -> bool:
        """
        Se xpath for fornecido, verifica apenas o elemento de erro HTML (legado).
        Se xpath não for fornecido (None ou ''), verifica e lida apenas com alertas JS.
        Retorna True se encontrar/tratar o erro ou alerta, False caso contrário.
        """
        if not self._driver:
            raise Exception("Browser não inicializado")

        if not xpath:
            # Só verifica alerta JS
            try:
                WebDriverWait(self._driver, timeout).until(
                    EC.alert_is_present())
                alert = self._driver.switch_to.alert
                if accept_alert:
                    alert.accept()
                    self.logger.info("✅ Alerta JS aceito (check_for_error).")
                else:
                    alert.dismiss()
                    self.logger.info(
                        "✅ Alerta JS rejeitado (check_for_error).")
                return True
            except TimeoutException:
                self.logger.info("Nenhum alerta JS exibido.")
                return False

        # Só verifica elemento de erro HTML (legado)
        try:
            self.set_timeout(timeout)
            self.find_element(xpath, condition or "presence")
            return True
        except NoSuchElementException:
            return False
        finally:
            self.reset_timeout()

    @contextmanager
    def on_new_window(self, url: str) -> Iterator[None]:
        """Abre nova janela com URL e gerencia contexto"""
        if not self._driver:
            raise Exception("Browser não inicializado")

        last_handle = self._driver.current_window_handle
        self._driver.execute_script(f"window.open('{url}')")
        new_handle = None

        while not new_handle:
            for handle in self._driver.window_handles:
                if handle != last_handle:
                    self._driver.switch_to.window(handle)
                    if self._driver.current_url == url:
                        if self._driver.execute_script(
                                "return document.readyState") == "complete":
                            new_handle = handle
                            break
            sleep(1)

        yield
        self._driver.close()
        self._driver.switch_to.window(last_handle)

    @contextmanager
    def on_iframe(self, xpath: str) -> Iterator[None]:
        """Troca para iframe"""
        if not self._driver or not self._driver_wait:
            raise Exception("Browser não inicializado")

        iframe = self._driver_wait.until(
            EC.presence_of_element_located((By.XPATH, xpath)))
        self._driver.switch_to.frame(iframe)
        yield
        self._driver.switch_to.default_content()

    def get_page_source(self) -> str:
        """Obtém código fonte da página"""
        if not self._driver:
            return ""
        return self._driver.page_source

    def close(self):
        """Fecha o browser"""
        if self._driver:
            try:
                self._driver.quit()
                self.logger.info("✅ Browser fechado")
            except Exception as e:
                self.logger.error(f"❌ Erro ao fechar browser: {e}")
            finally:
                self._driver = None
                self._driver_wait = None

    # ----------- MÉTODOS COMPLEMENTARES (vindos da Browser original) -----------

    @contextmanager
    def on_window(self, has_element: str, retry: int = 10) -> Iterator[None]:
        """Troca para janela que tenha determinado xpath."""
        if not self._driver:
            raise Exception("Browser não inicializado")
        default_handler = self._driver.current_window_handle
        found_handle = None
        while not found_handle and retry > 0:
            for handle in self._driver.window_handles:
                if handle == default_handler:
                    continue
                self._driver.switch_to.window(handle)
                try:
                    if self._driver.find_elements(By.XPATH, has_element):
                        found_handle = handle
                        break
                except Exception:
                    continue
            if not found_handle:
                sleep(1)
                retry -= 1
            if retry < 1:
                raise WindowNotFound(
                    f"Window with xpath {has_element} not found.")
        yield
        self._driver.switch_to.window(default_handler)

    def select_option(self,
                      xpath: str,
                      option: str,
                      timeout: int = 10,
                      verify: bool = False) -> None:
        """Seleciona option em elemento select"""
        if not self._driver:
            raise Exception("Browser não inicializado")
        element = None
        while timeout > 0:
            element = self.find_element(xpath, condition="clickable")
            select = Select(element)
            select.select_by_visible_text(option)
            if not verify:
                return

            current_value = element.get_attribute("value")
            for opt in self.find_elements(
                    f'//option[@value="{current_value}"]'):
                text = opt.get_attribute("innerText")
                if text == option:
                    return
            sleep(2)
            timeout -= 1
        raise NoSuchElementException(
            f"Option {option} not found in select element with xpath {xpath}.")

    def get_texts_from_select(self, xpath: str) -> List[str]:
        """Obtém todos os textos das opções de um select"""
        element = self.find_element(xpath, condition="visible")
        select_element = Select(element)
        return [opt.text for opt in select_element.options]

    def select_option_by_similarity(
        self,
        xpath: str,
        option: str,
        similarity_threshold: float = 0.6,
        timeout: int = 10,
        verify: bool = False,
    ) -> None:
        """
        Seleciona opção de select pela similaridade, ignorando case
        """
        available_options = self.get_texts_from_select(xpath)
        option_upper = option.upper()
        available_options_upper = [opt.upper() for opt in available_options]
        closest_matches = get_close_matches(
            option_upper,
            available_options_upper,
            n=1,
            cutoff=similarity_threshold,
        )

        if not closest_matches:
            raise NoSuchElementException(
                f"No similar option found for '{option}' in select element with xpath '{xpath}'."
            )

        closest_option = available_options[available_options_upper.index(
            closest_matches[0])]

        if not self._driver:
            raise Exception("Browser não inicializado")

        while timeout > 0:
            self.select_option(xpath, closest_option)
            if not verify:
                return

            current_value = self.find_element(xpath).get_attribute("value")
            for opt in self.find_elements(
                    f'//option[@value="{current_value}"]'):
                text = opt.get_attribute("innerText")
                if text and text.upper() == closest_option.upper():
                    return

            sleep(2)
            timeout -= 1

        raise NoSuchElementException(
            f"Failed to select option '{closest_option}' in select element with xpath '{xpath}'."
        )

    def handle_alert(self, accept: bool = True, timeout: int = 5) -> bool:
        """Tenta lidar com um alerta JS (popup) se aparecer. Retorna True se tratou, False se não havia alerta."""
        if not self._driver:
            raise Exception("Browser não inicializado")
        try:
            WebDriverWait(self._driver, timeout).until(EC.alert_is_present())
            alert = self._driver.switch_to.alert
            if accept:
                alert.accept()
                self.logger.info("✅ Alerta JS aceito.")
            else:
                alert.dismiss()
                self.logger.info("✅ Alerta JS rejeitado.")
            return True
        except TimeoutException:
            self.logger.info("Nenhum alerta JS exibido.")
            return False

    def __del__(self):
        """Destrutor - garante que browser seja fechado"""
        self.close()
