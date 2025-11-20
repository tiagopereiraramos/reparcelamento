"""
Browser Manager - Baseado na sua classe Browser
Mantém compatibilidade com sua arquitetura Firefox/Gecko
Adiciona suporte ao Undetected Chromedriver para RPAs que precisam

Desenvolvido em Português Brasileiro
"""

import logging
import os
import platform
import shutil
from contextlib import contextmanager
import random
from time import sleep
from typing import Iterator, List, Optional, Callable, Dict, Any

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
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.support.select import Select
    from webdriver_manager.firefox import GeckoDriverManager
    SELENIUM_DISPONIVEL = True
except ImportError:
    SELENIUM_DISPONIVEL = False

# Tentar importar Undetected Chromedriver
try:
    import undetected_chromedriver as uc
    UC_CHROME_DISPONIVEL = True
except ImportError:
    uc = None
    UC_CHROME_DISPONIVEL = False

from difflib import get_close_matches


class WindowNotFound(Exception):
    """Browser window not found."""


class RPABrowser:
    """
    Browser Manager baseado na sua classe Browser
    Implementa Firefox/Gecko seguindo sua arquitetura
    Adiciona suporte ao Undetected Chromedriver para RPAs específicos
    """

    def __init__(self, headless: bool = True, eager_load: bool = False, firefox_profile_path: str = '', limpar_cookies_sicredi: bool = False, usar_uc_chrome: bool = False, chrome_profile_path: str = ''):
        """
        Inicializa o browser com suporte a Firefox e Chrome UC

        Args:
            headless: Modo headless
            eager_load: Carregamento eager
            firefox_profile_path: Caminho do perfil Firefox
            limpar_cookies_sicredi: Limpar cookies do Sicredi
            usar_uc_chrome: Usar Undetected Chromedriver
            chrome_profile_path: Caminho do perfil Chrome
        """
        self._driver = None
        self._driver_wait: Optional[WebDriverWait] = None
        self._original_timeout = 30
        self.actions = None
        self.logger = logging.getLogger("RPABrowser")

        # Configurar perfis
        self._firefox_profile_path = firefox_profile_path or os.getenv(
            'FIREFOX_PROFILE_PATH', '').strip()
        self._chrome_profile_path = chrome_profile_path or os.getenv(
            'CHROME_PROFILE_PATH', '').strip()
        self._usar_uc_chrome = usar_uc_chrome
        self._limpar_cookies_sicredi = limpar_cookies_sicredi

        # Verificar disponibilidade
        if usar_uc_chrome and not UC_CHROME_DISPONIVEL:
            self.logger.error(
                "❌ undetected-chromedriver não está instalado. Instale com 'pip install undetected-chromedriver'")
            return
        elif not usar_uc_chrome and not SELENIUM_DISPONIVEL:
            self.logger.warning("⚠️ Selenium não está disponível")
            return

        try:
            self._inicializar_browser(headless, eager_load)

            # Configurar após inicialização
            if self._driver:
                self._driver_wait = WebDriverWait(
                    self._driver, self._original_timeout)
                self._driver.maximize_window()
                self.actions = ActionChains(self._driver)
                self.logger.info("✅ Browser inicializado e configurado")

        except Exception as e:
            self.logger.error(f"❌ Erro ao inicializar browser: {e}")
            self._driver = None

    def _inicializar_browser(self, headless: bool, eager_load: bool):
        """Inicializa o browser (Firefox ou Chrome UC)"""
        if self._usar_uc_chrome:
            self._inicializar_chrome_uc(headless, eager_load)
        else:
            self._inicializar_firefox(headless, eager_load)

    def _detectar_versao_chrome(self) -> Optional[int]:
        """Detecta a versão do Chrome instalada no sistema"""
        try:
            sistema = platform.system()
            if sistema == "Windows":
                # Windows: verificar no registro ou executável
                try:
                    import winreg
                except ImportError:
                    # winreg não disponível (não é Windows ou Python incompleto)
                    pass
                else:
                    try:
                        key = winreg.OpenKey(
                            winreg.HKEY_CURRENT_USER,
                            r"Software\Google\Chrome\BLBeacon"
                        )
                        version = winreg.QueryValueEx(key, "version")[0]
                        winreg.CloseKey(key)
                        version_main = int(version.split('.')[0])
                        self.logger.info(f"✅ Versão do Chrome detectada: {version} (main: {version_main})")
                        return version_main
                    except Exception:
                        pass
            elif sistema == "Darwin":  # macOS
                # macOS: verificar via comando
                import subprocess
                try:
                    result = subprocess.run(
                        ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        version_str = result.stdout.strip()
                        version_main = int(version_str.split()[-1].split('.')[0])
                        self.logger.info(f"✅ Versão do Chrome detectada: {version_str} (main: {version_main})")
                        return version_main
                except Exception:
                    pass
            else:  # Linux
                # Linux: verificar via comando
                import subprocess
                try:
                    result = subprocess.run(
                        ['google-chrome', '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        version_str = result.stdout.strip()
                        version_main = int(version_str.split()[-1].split('.')[0])
                        self.logger.info(f"✅ Versão do Chrome detectada: {version_str} (main: {version_main})")
                        return version_main
                except Exception:
                    pass
            
            self.logger.warning("⚠️ Não foi possível detectar versão do Chrome automaticamente")
            return None
        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao detectar versão do Chrome: {e}")
            return None

    def _inicializar_chrome_uc(self, headless: bool, eager_load: bool):
        """Inicializa Chrome com Undetected Chromedriver com retry e validação robusta"""
        if not UC_CHROME_DISPONIVEL or uc is None:
            raise ImportError("undetected-chromedriver não instalado")

        self.logger.info(
            "🚀 Inicializando Chrome com Undetected Chromedriver...")

        # Detectar versão do Chrome
        version_main = self._detectar_versao_chrome()
        
        # Estratégias de inicialização (sem versão, com versão detectada, fallback)
        estrategias = []
        if version_main:
            estrategias.append({"version_main": version_main, "desc": f"versão detectada ({version_main})"})
        estrategias.append({"version_main": None, "desc": "detecção automática"})
        # Fallback para versões comuns se detecção falhar
        for v in [140, 139, 138, 137, 136]:
            if not version_main or abs(version_main - v) <= 5:
                estrategias.append({"version_main": v, "desc": f"fallback versão {v}"})

        ultimo_erro = None
        for tentativa, estrategia in enumerate(estrategias, 1):
            try:
                self.logger.info(
                    f"🔄 Tentativa {tentativa}/{len(estrategias)}: {estrategia['desc']}")

                # Configurar opções do Chrome
                chrome_options = uc.ChromeOptions()

                # Configurar headless de forma compatível
                if headless:
                    chrome_options.add_argument("--headless=new")

                # Argumentos essenciais para estabilidade
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--disable-extensions")
                chrome_options.add_argument("--disable-web-security")
                chrome_options.add_argument("--allow-running-insecure-content")
                # Argumentos adicionais para estabilidade
                chrome_options.add_argument("--disable-software-rasterizer")
                chrome_options.add_argument("--disable-background-timer-throttling")
                chrome_options.add_argument("--disable-backgrounding-occluded-windows")
                chrome_options.add_argument("--disable-renderer-backgrounding")

                # ✅ CORREÇÃO: Configurar diretório de downloads para Chrome UC
                from platformdirs import user_downloads_dir

                rpa_downloads_folder = os.getenv(
                    'RPA_DOWNLOADS_FOLDER', 'RPA_DOWNLOADS')

                # Tratar barra inicial se houver (como no rpa_sienge.py)
                if rpa_downloads_folder and rpa_downloads_folder.startswith('/'):
                    rpa_downloads_folder = rpa_downloads_folder[1:]

                # Usar platformdirs para cross-platform automático
                downloads_dir = os.path.join(
                    user_downloads_dir(), rpa_downloads_folder)

                os.makedirs(downloads_dir, exist_ok=True)

                # ✅ CONFIGURAÇÃO DE DOWNLOADS PARA CHROME UC
                chrome_options.add_experimental_option(
                    "prefs", {
                        "download.default_directory": downloads_dir,
                        "download.prompt_for_download": False,
                        "download.directory_upgrade": True,
                        "safebrowsing.enabled": True,
                        "safebrowsing.disable_download_protection": True,
                        "profile.default_content_setting_values.automatic_downloads": 1,
                        "profile.default_content_settings.popups": 0,
                        "profile.content_settings.exceptions.automatic_downloads.*.http://*": {
                            "setting": 1
                        },
                        "profile.content_settings.exceptions.automatic_downloads.*.https://*": {
                            "setting": 1
                        }
                    }
                )

                self.logger.info(
                    f"📁 Diretório de downloads configurado: {downloads_dir}")

                # Adicionar perfil do Chrome se fornecido
                if self._chrome_profile_path:
                    self.logger.info(
                        f"✅ Usando perfil do Chrome: {self._chrome_profile_path}")
                    chrome_options.add_argument(
                        f'--user-data-dir={self._chrome_profile_path}')

                # Preparar parâmetros de inicialização
                init_params = {
                    "options": chrome_options,
                    "use_subprocess": True,
                    "suppress_welcome": True,
                }
                
                # Adicionar version_main apenas se especificado
                if estrategia["version_main"] is not None:
                    init_params["version_main"] = estrategia["version_main"]

                # Inicializar Chrome UC
                self._driver = uc.Chrome(**init_params)

                # ✅ VALIDAÇÃO CRÍTICA: Verificar se o driver está realmente funcionando
                try:
                    # Tentar obter a URL atual (isso valida que o browser está vivo)
                    _ = self._driver.current_url
                    # Tentar executar um script simples
                    self._driver.execute_script("return document.readyState")
                    self.logger.info("✅ Validação inicial do browser: OK")
                except Exception as validacao_erro:
                    self.logger.error(f"❌ Browser inicializado mas não está respondendo: {validacao_erro}")
                    if self._driver:
                        try:
                            self._driver.quit()
                        except:
                            pass
                    self._driver = None
                    raise Exception(f"Browser não está respondendo após inicialização: {validacao_erro}")

                # ✅ CONFIGURAÇÃO ADICIONAL APÓS INICIALIZAÇÃO
                # Configurar para evitar detecção
                self._driver.execute_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                # ✅ CONFIGURAR DOWNLOADS APÓS INICIALIZAÇÃO (reforço)
                try:
                    self._driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                        'behavior': 'allow',
                        'downloadPath': downloads_dir
                    })
                except Exception as cdp_erro:
                    self.logger.warning(f"⚠️ Erro ao configurar CDP para downloads (não crítico): {cdp_erro}")

                self.logger.info("✅ Chrome UC inicializado com sucesso")
                self.logger.info(f"📁 Downloads serão salvos em: {downloads_dir}")
                return  # Sucesso - sair do loop

            except Exception as e:
                ultimo_erro = e
                erro_msg = str(e)
                self.logger.warning(
                    f"⚠️ Tentativa {tentativa} falhou: {erro_msg}")
                
                # Limpar driver se foi criado mas falhou
                if self._driver:
                    try:
                        self._driver.quit()
                    except:
                        pass
                    self._driver = None
                
                # Se for erro de processo fechado, tentar próxima estratégia
                if "Process unexpectedly closed" in erro_msg or "status 0" in erro_msg:
                    self.logger.info(f"🔄 Processo fechou inesperadamente, tentando próxima estratégia...")
                    sleep(2)  # Pequeno delay entre tentativas
                    continue
                else:
                    # Outros erros também podem se beneficiar de retry
                    if tentativa < len(estrategias):
                        sleep(2)
                        continue

        # Se chegou aqui, todas as tentativas falharam
        erro_final = f"Falha ao inicializar Chrome UC após {len(estrategias)} tentativas"
        if ultimo_erro:
            erro_final += f": {ultimo_erro}"
        self.logger.error(f"❌ {erro_final}")
        raise Exception(erro_final)

    def _inicializar_firefox(self, headless: bool, eager_load: bool):
        """Inicializa Firefox seguindo sua estrutura original (multiplataforma)"""
        if not SELENIUM_DISPONIVEL:
            return

        import platform
        sistema = platform.system()

        self.options = Options()

        # Configurações baseadas na sua classe
        if headless:
            self.options.add_argument("--headless")

        if eager_load:
            self.options.page_load_strategy = "eager"

        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--no-sandbox")
        # Configurações adicionais para evitar "No buffer space available"
        self.options.add_argument("--disable-background-timer-throttling")
        self.options.add_argument("--disable-backgrounding-occluded-windows")
        self.options.add_argument("--disable-renderer-backgrounding")
        self.options.add_argument("--disable-features=TranslateUI")
        self.options.add_argument("--disable-ipc-flooding-protection")
        self.options.add_argument("--max_old_space_size=4096")

        # Configurações de download - usar platformdirs para cross-platform
        from platformdirs import user_downloads_dir

        rpa_downloads_folder = os.getenv(
            'RPA_DOWNLOADS_FOLDER', 'RPA_DOWNLOADS')

        # Tratar barra inicial se houver (como no rpa_sienge.py)
        if rpa_downloads_folder and rpa_downloads_folder.startswith('/'):
            rpa_downloads_folder = rpa_downloads_folder[1:]

        # Usar platformdirs para cross-platform automático
        downloads_dir = os.path.join(
            user_downloads_dir(), rpa_downloads_folder)

        os.makedirs(downloads_dir, exist_ok=True)

        self.options.set_preference("browser.download.folderList", 2)
        self.options.set_preference("browser.download.dir", downloads_dir)
        self.options.set_preference(
            "browser.helperApps.neverAsk.saveToDisk",
            "application/pdf,application/octet-stream,text/csv,application/vnd.ms-excel"
        )
        self.options.set_preference("browser.download.useDownloadDir", True)
        self.options.set_preference("pdfjs.disabled", True)

        # Tentar usar GeckoDriver com detecção multiplataforma
        gecko_driver_path = None
        try:
            # Usar webdriver-manager que detecta automaticamente o SO
            gecko_driver_path = GeckoDriverManager().install()
            self.logger.info(f"✅ GeckoDriver instalado: {gecko_driver_path}")
        except Exception as e:
            self.logger.warning(f"⚠️  Erro ao instalar GeckoDriver via webdriver-manager: {e}")
            # Fallback para caminhos padrão por SO
            if sistema == "Windows":
                caminhos_fallback = [
                    os.path.expanduser(r"~\AppData\Local\geckodriver\geckodriver.exe"),
                    r"C:\WebDriver\bin\geckodriver.exe",
                    "geckodriver.exe"  # No PATH
                ]
            elif sistema == "Darwin":  # macOS
                caminhos_fallback = [
                    "/usr/local/bin/geckodriver",
                    "/opt/homebrew/bin/geckodriver",
                    "geckodriver"  # No PATH
                ]
            else:  # Linux
                caminhos_fallback = [
                    "/usr/local/bin/geckodriver",
                    "/usr/bin/geckodriver",
                    "~/.local/bin/geckodriver",
                    "geckodriver"  # No PATH
                ]
            
            for caminho in caminhos_fallback:
                caminho_expandido = os.path.expanduser(caminho)
                if os.path.exists(caminho_expandido) or shutil.which(caminho_expandido):
                    gecko_driver_path = caminho_expandido
                    self.logger.info(f"✅ GeckoDriver encontrado: {gecko_driver_path}")
                    break
            
            if not gecko_driver_path:
                # Último fallback: tentar encontrar no PATH
                gecko_driver_path = shutil.which("geckodriver")
                if gecko_driver_path:
                    self.logger.info(f"✅ GeckoDriver encontrado no PATH: {gecko_driver_path}")
                else:
                    self.logger.error("❌ GeckoDriver não encontrado. Instale manualmente ou use webdriver-manager")
                    raise Exception("GeckoDriver não encontrado")

        # Usar perfil Firefox se fornecido
        if self._firefox_profile_path:
            self.options.profile = self._firefox_profile_path
            self.logger.info(
                f"✅ Usando perfil Firefox: {self._firefox_profile_path}")

        # Configurar service com timeout maior para evitar problemas de buffer
        service = Service(gecko_driver_path)
        service.start_error_message = "Erro ao iniciar GeckoDriver"

        # ✅ INICIALIZAÇÃO COM RETRY E VALIDAÇÃO
        max_tentativas = 3
        ultimo_erro = None
        
        for tentativa in range(1, max_tentativas + 1):
            try:
                self.logger.info(f"🔄 Tentativa {tentativa}/{max_tentativas} de inicializar Firefox...")
                
                # Limpar driver anterior se existir
                if self._driver:
                    try:
                        self._driver.quit()
                    except:
                        pass
                    self._driver = None
                
                # Inicializar Firefox
                self._driver = webdriver.Firefox(service=service, options=self.options)

                # ✅ VALIDAÇÃO CRÍTICA: Verificar se o driver está realmente funcionando
                try:
                    # Tentar obter a URL atual (isso valida que o browser está vivo)
                    _ = self._driver.current_url
                    # Tentar executar um script simples
                    self._driver.execute_script("return document.readyState")
                    self.logger.info("✅ Validação inicial do browser Firefox: OK")
                except Exception as validacao_erro:
                    self.logger.error(f"❌ Firefox inicializado mas não está respondendo: {validacao_erro}")
                    if self._driver:
                        try:
                            self._driver.quit()
                        except:
                            pass
                    self._driver = None
                    raise Exception(f"Firefox não está respondendo após inicialização: {validacao_erro}")
                
                # Limpar cookies e finalizar
                self._driver.delete_all_cookies()
                self.logger.info("✅ Browser Firefox inicializado com sucesso")
                return  # Sucesso - sair do loop
                
            except Exception as e:
                ultimo_erro = e
                erro_msg = str(e)
                self.logger.warning(f"⚠️ Tentativa {tentativa} falhou: {erro_msg}")
                
                # Limpar driver se foi criado mas falhou
                if self._driver:
                    try:
                        self._driver.quit()
                    except:
                        pass
                    self._driver = None
                
                # Se for erro de processo fechado, tentar novamente
                if "Process unexpectedly closed" in erro_msg or "status 0" in erro_msg or "connection refused" in erro_msg.lower():
                    if tentativa < max_tentativas:
                        self.logger.info(f"🔄 Processo fechou inesperadamente, tentando novamente em 2 segundos...")
                        sleep(2)  # Pequeno delay entre tentativas
                        continue
                
                # Se não for erro de processo fechado e ainda há tentativas, continuar
                if tentativa < max_tentativas:
                    sleep(2)
                    continue
        
        # Se chegou aqui, todas as tentativas falharam
        erro_final = f"Falha ao inicializar Firefox após {max_tentativas} tentativas"
        if ultimo_erro:
            erro_final += f": {ultimo_erro}"
        self.logger.error(f"❌ {erro_final}")
        raise Exception(erro_final)

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
                     condition: str = "presence"):
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
                      condition: str = "located_all") -> List:
        """Aguarda e retorna lista de elementos"""
        if not self._driver or not self._driver_wait:
            return []

        try:
            condition_func = self._get_condition(condition)
            return self._driver_wait.until(condition_func((By.XPATH, xpath)))
        except TimeoutException as exc:
            raise NoSuchElementException(
                f"Elementos com xpath {xpath} não encontrados. {exc}")

    def click(self, xpath: str, checkbox_action: Optional[str] = None, force_action: bool = False) -> None:
        """
        Clica em elemento com tratamento de erros

        Args:
            xpath: XPath do elemento
            checkbox_action: Ação específica para checkbox ("check", "uncheck", "toggle", None)
                           None = comportamento padrão (clica normalmente)
            force_action: Se True, força a ação mesmo se estado já for o desejado

        Exemplos:
            # Comportamento legado (sem alteração)
            browser.click("//button[@id='submit']")

            # Para checkboxes - marcar (só se não estiver marcado)
            browser.click("//input[@type='checkbox']", checkbox_action="check")

            # Para checkboxes - desmarcar (só se estiver marcado)
            browser.click("//input[@type='checkbox']", checkbox_action="uncheck")

            # Para checkboxes - alternar estado
            browser.click("//input[@type='checkbox']", checkbox_action="toggle")

            # Forçar ação mesmo se estado já for o desejado
            browser.click("//input[@type='checkbox']", checkbox_action="check", force_action=True)
        """
        if not self._driver:
            raise Exception("Browser não inicializado")

        element = self.find_element(xpath, condition="clickable")
        self._driver.execute_script("arguments[0].scrollIntoView(true);",
                                    element)

        # Detectar se é checkbox e aplicar lógica específica
        if checkbox_action and self._is_checkbox(element):
            self._handle_checkbox_click(element, checkbox_action, force_action)
        else:
            # Comportamento padrão (legado)
            try:
                element.click()
            except (ElementClickInterceptedException,
                    ElementNotInteractableException,
                    StaleElementReferenceException):
                self._driver.execute_script("arguments[0].click();", element)

    def _is_checkbox(self, element) -> bool:
        """Verifica se elemento é um checkbox"""
        try:
            # Verificar por tipo de input
            if element.tag_name.lower() == "input":
                input_type = element.get_attribute("type")
                if input_type and input_type.lower() in ["checkbox", "radio"]:
                    return True

            # Verificar por role ARIA
            role = element.get_attribute("role")
            if role and role.lower() in ["checkbox", "radio"]:
                return True

            # Verificar por classes CSS comuns
            class_attr = element.get_attribute("class") or ""
            checkbox_classes = ["checkbox", "check-box",
                                "form-check-input", "custom-control-input"]
            if any(cls in class_attr.lower() for cls in checkbox_classes):
                return True

            return False
        except:
            return False

    def _handle_checkbox_click(self, element, action: str, force_action: bool = False):
        """Gerencia clique em checkbox baseado na ação desejada"""
        try:
            current_state = element.is_selected()

            if action == "check":
                if not current_state:
                    element.click()
                    self.logger.info("✅ Checkbox marcado com sucesso")
                elif force_action:
                    element.click()
                    self.logger.info("✅ Checkbox marcado (forçado)")
                else:
                    self.logger.info(
                        "ℹ️ Checkbox já estava marcado - nenhuma ação necessária")

            elif action == "uncheck":
                if current_state:
                    element.click()
                    self.logger.info("✅ Checkbox desmarcado com sucesso")
                elif force_action:
                    element.click()
                    self.logger.info("✅ Checkbox desmarcado (forçado)")
                else:
                    self.logger.info(
                        "ℹ️ Checkbox já estava desmarcado - nenhuma ação necessária")

            elif action == "toggle":
                element.click()
                new_state = element.is_selected()
                self.logger.info(
                    f"🔄 Checkbox alternado: {'marcado' if new_state else 'desmarcado'}")
            else:
                # Comportamento padrão se ação inválida
                element.click()

        except (ElementClickInterceptedException,
                ElementNotInteractableException,
                StaleElementReferenceException):
            # Fallback para JavaScript se clique normal falhar
            if self._driver:
                if action == "check" and (not element.is_selected() or force_action):
                    self._driver.execute_script(
                        "arguments[0].checked = true; arguments[0].click();", element)
                    self.logger.info("✅ Checkbox marcado via JavaScript")
                elif action == "uncheck" and (element.is_selected() or force_action):
                    self._driver.execute_script(
                        "arguments[0].checked = false; arguments[0].click();", element)
                    self.logger.info("✅ Checkbox desmarcado via JavaScript")
                else:
                    self._driver.execute_script(
                        "arguments[0].click();", element)

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

    def check_for_error(
        self,
        xpath: Optional[str] = None,
        condition: Optional[str] = None,
        retry: int = 1,
        timeout: int = 5,
        accept_alert: bool = True
    ) -> bool:
        """Verifica se há erro na página"""
        if not self._driver:
            return False

        # Se xpath não foi fornecido, só verifica alertas JS
        if xpath is None:
            try:
                if accept_alert:
                    alert = self._driver.switch_to.alert
                    alert.accept()
                    return True
            except:
                pass
            return False

        # Se xpath foi fornecido, verifica elemento HTML
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

    def mark_checkboxes_by_contract_name(
        self,
        contract_name: str,
        grid_selector: str = "#tabelaAgrupParcelaGrid",
        checkbox_selector: str = "input[type='checkbox'][id*='flSelecionado_']",
        case_sensitive: bool = False
    ) -> Dict[str, Any]:
        """
        Marca checkboxes em uma grid baseado no nome do contrato
        Usa exatamente o código JavaScript que funcionou 100%

        Args:
            contract_name: Nome do contrato a ser buscado
            grid_selector: Seletor CSS da tabela/grid (padrão: "#tabelaAgrupParcelaGrid")
            checkbox_selector: Seletor CSS para os checkboxes (padrão: input[type='checkbox'][id*='flSelecionado_'])
            case_sensitive: Se a busca deve ser case-sensitive

        Returns:
            Dict com informações sobre a operação:
            {
                "sucesso": bool,
                "total_marcados": int,
                "erro": str (se houver)
            }
        """
        if not self._driver:
            raise Exception("Browser não inicializado")

        try:

            # Executar exatamente o seu código JavaScript que funcionou
            js_script = f"""
            // Troque pelo nome que deseja buscar
            const nomeBuscado = "{contract_name}";

            // Seleciona todas as linhas da grid
            const linhas = document.querySelectorAll("{grid_selector} tr");

            let totalMarcados = 0;

            linhas.forEach(linha => {{
                // Procura célula com o nome exato (pode ajustar para case-insensitive se quiser)
                const textoLinha = "{case_sensitive}" === "true" ? linha.textContent : linha.textContent.toLowerCase();
                const nomeBusca = "{case_sensitive}" === "true" ? nomeBuscado : nomeBuscado.toLowerCase();
                
                if (textoLinha.includes(nomeBusca)) {{
                    // Procura o checkbox dentro da linha
                    const checkbox = linha.querySelector("{checkbox_selector}");
                    if (checkbox && !checkbox.checked && !checkbox.disabled && checkbox.offsetParent !== null) {{
                        checkbox.click(); // Marca o checkbox (dispara eventos JS)
                        totalMarcados++;
                    }}
                }}
            }});

            console.log(`Total de checkboxes marcados para "${{nomeBuscado}}": ${{totalMarcados}}`);
            return totalMarcados;
            """

            total_marcados = self._driver.execute_script(js_script)

            self.logger.info(
                f"✅ Grid processada: {total_marcados} checkboxes marcados para '{contract_name}'"
            )

            return {
                "sucesso": True,
                "total_marcados": total_marcados,
                "erro": None
            }

        except Exception as e:
            error_msg = f"Erro ao marcar checkboxes para '{contract_name}': {str(e)}"
            self.logger.error(error_msg)
            return {
                "sucesso": False,
                "total_marcados": 0,
                "erro": error_msg
            }

    def verificar_diretorio_downloads(self) -> Dict[str, Any]:
        """
        Verifica se o diretório de downloads está configurado corretamente

        Returns:
            Dict com informações sobre o diretório de downloads
        """
        try:
            from platformdirs import user_downloads_dir

            rpa_downloads_folder = os.getenv(
                'RPA_DOWNLOADS_FOLDER', 'RPA_DOWNLOADS')

            # Tratar barra inicial se houver
            if rpa_downloads_folder and rpa_downloads_folder.startswith('/'):
                rpa_downloads_folder = rpa_downloads_folder[1:]

            downloads_dir = os.path.join(
                user_downloads_dir(), rpa_downloads_folder)

            # Verificar se diretório existe
            diretorio_existe = os.path.exists(downloads_dir)

            # Verificar se é gravável
            gravavel = os.access(
                downloads_dir, os.W_OK) if diretorio_existe else False

            # Listar arquivos existentes
            arquivos_existentes = []
            if diretorio_existe:
                try:
                    arquivos_existentes = [f.name for f in os.scandir(
                        downloads_dir) if f.is_file()]
                except Exception as e:
                    self.logger.error(f"Erro ao listar arquivos: {e}")

            return {
                "sucesso": True,
                "diretorio": downloads_dir,
                "existe": diretorio_existe,
                "gravavel": gravavel,
                "arquivos_existentes": arquivos_existentes,
                "total_arquivos": len(arquivos_existentes)
            }

        except Exception as e:
            self.logger.error(f"Erro ao verificar diretório de downloads: {e}")
            return {
                "sucesso": False,
                "erro": str(e),
                "diretorio": "N/A",
                "existe": False,
                "gravavel": False,
                "arquivos_existentes": [],
                "total_arquivos": 0
            }

    def __del__(self):
        """Destrutor - garante que browser seja fechado"""
        self.close()
