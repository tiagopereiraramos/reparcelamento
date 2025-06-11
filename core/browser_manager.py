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

from difflib import get_close_matches


class WindowNotFound(Exception):
    """Browser window not found."""


class RPABrowser:
    """
    Browser Manager baseado na sua classe Browser
    Implementa Firefox/Gecko seguindo sua arquitetura
    """

    def __init__(self, headless: bool = True, eager_load: bool = False):
        self._driver: Optional[webdriver.Firefox] = None
        self._driver_wait: Optional[WebDriverWait] = None
        self._original_timeout = 30
        self.actions = None
        self.logger = logging.getLogger("RPABrowser")

        if not SELENIUM_DISPONIVEL:
            self.logger.warning("⚠️ Selenium não está disponível")
            return

        try:
            self._inicializar_browser(headless, eager_load)
        except Exception as e:
            self.logger.error(f"❌ Erro ao inicializar browser: {e}")
            self._driver = None

    def _inicializar_browser(self, headless: bool, eager_load: bool):
        """Inicializa o browser Firefox seguindo sua estrutura"""
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

        # Configurações de download
        downloads_dir = os.path.expanduser("~/Downloads/RPA_DOWNLOADS")
        os.makedirs(downloads_dir, exist_ok=True)

        self.options.set_preference("browser.download.folderList", 2)
        self.options.set_preference("browser.download.dir", downloads_dir)
        self.options.set_preference(
            "browser.helperApps.neverAsk.saveToDisk",
            "application/pdf,application/octet-stream,text/csv,application/vnd.ms-excel"
        )
        self.options.set_preference("browser.download.useDownloadDir", True)
        self.options.set_preference("pdfjs.disabled", True)

        # Tentar usar GeckoDriver
        try:
            gecko_driver_path = GeckoDriverManager().install()
        except Exception:
            # Fallback para caminho padrão
            gecko_driver_path = "/usr/local/bin/geckodriver"

        self._driver = webdriver.Firefox(service=Service(gecko_driver_path),
                                         options=self.options)

        self._driver.delete_all_cookies()
        self._driver_wait = WebDriverWait(self._driver, self._original_timeout)
        self._driver.maximize_window()
        self.actions = ActionChains(self._driver)

        self.logger.info("✅ Browser Firefox inicializado")

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
                        xpath: str,
                        condition: Optional[str] = None,
                        retry: int = 1) -> bool:
        """Verifica se elemento de erro está presente"""
        try:
            self.set_timeout(5)
            self.find_element(xpath, condition or "presence")
            self.reset_timeout()
            return True
        except NoSuchElementException:
            self.reset_timeout()
            return False

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

    def __del__(self):
        """Destrutor - garante que browser seja fechado"""
        self.close()
