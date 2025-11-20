"""
RPA Sienge - Emissão de Carnês (porta dos métodos usados no main_sienge_emissao_carnes)

Implementa, NA ÍNTEGRA, os métodos necessários originalmente presentes em
`rpa_sienge/rpa_sienge.py` para a emissão de carnês.
"""

from __future__ import annotations

import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore

from core.base_rpa import BaseRPA, ResultadoRPA
from core.utils_sienge import obter_conta_corrente_remessa
from core.rastreamento_unificado import iniciar_rastreamento


class RPAEmissaoCarneSienge(BaseRPA):
    """RPA focado na emissão de carnês no Sienge."""

    def __init__(
        self,
        headless: Optional[bool] = None,
        usar_uc_chrome: bool = False,
        caminho_perfil_chrome: str = ""
    ) -> None:
        parametros_base = {
            "nome_rpa": "Sienge-EmissaoCarne",
            "usar_browser": True,
            "usar_uc_chrome": usar_uc_chrome,
            "chrome_profile_path": caminho_perfil_chrome,
        }
        if headless is not None:
            parametros_base["headless"] = headless
        super().__init__(**parametros_base)
        self.logado_sienge = False
        self.credenciais_sienge: Dict[str, str] = {}
        self.usar_uc_chrome = usar_uc_chrome
        self.caminho_perfil_chrome = caminho_perfil_chrome
        self.rastreamento = None

    def _configurar_credenciais(self, credenciais: Dict[str, str]) -> None:
        """Configura credenciais do Sienge (cópia literal)."""
        self.credenciais_sienge = {
            "url": credenciais.get("url", ""),
            "usuario": credenciais.get("usuario", ""),
            "senha": credenciais.get("senha", ""),
            "empresa": credenciais.get("empresa", ""),
        }

    async def _fazer_login_sienge(self):
        """
        Faz login no sistema Sienge conforme PDD.
        CÓPIA NA ÍNTEGRA do método correspondente em rpa_sienge.py.
        """
        try:
            # Inicializar rastreamento se não existe
            if self.rastreamento is None:
                try:
                    self.rastreamento = iniciar_rastreamento(
                        "RPA_Sienge_EmissaoCarne")
                    await self.rastreamento.registrar_inicio_rpa({
                        "operacao": "login_sienge",
                        "usuario": self.credenciais_sienge.get("usuario", "")
                    })
                except Exception:
                    pass  # Não quebra se rastreamento falhar
            url_sienge = self.credenciais_sienge.get("url", "")
            usuario_sienge = self.credenciais_sienge.get("usuario", "")
            senha_sienge = self.credenciais_sienge.get("senha", "")

            self.log_progresso(f"Acessando sistema Sienge: {url_sienge}")
            if not url_sienge:
                raise ValueError(
                    "URL do Sienge não foi configurada corretamente.")

            self.get_page(url_sienge)
            time.sleep(3)
            if self.check_for_error(xpath='//button[@id="btnEntrarComSiengeID"]', timeout=5):
                self.click(xpath='//button[@id="btnEntrarComSiengeID"]')
                time.sleep(2)
            # Preenche usuário inicial
            # self.send_text(
            #     xpath='(//input[@name="username"])', text=usuario_sienge)
            # # Preenche senha inicial
            # self.send_text(xpath='//input[@id="password"]', text=senha_sienge)
            # # Clica botão entrar inicial
            # self.click(xpath='//*[@id="btnEntrarComSiengeID"]')
            # time.sleep(2)

            # Segunda etapa - email
            self.send_text(
                xpath='//label[text()="Seu e-mail"]/following-sibling::div//input',
                text=usuario_sienge,
            )
            # Clica continuar
            self.click(xpath="//button[normalize-space(text())='CONTINUAR']")

            # Terceira etapa - senha final
            self.send_text(
                xpath="//input[@id='signup-password']", text=senha_sienge)
            # Clica entrar final
            self.click(xpath="//button[normalize-space(text())='ENTRAR']")

            if self.check_for_error("//div[contains(@class, 'spwAlertaAviso')]//p[contains(normalize-space(.), 'Deseja prosseguir desconectando')]", timeout=5):
                self.log_warning("Usuário já logado - prosseguindo")
                self.click(
                    xpath="//a[contains(@class, 'Button-prim') and contains(., 'Prosseguir')]")

            self.logado_sienge = True
            self.log_progresso("Login no Sienge realizado com sucesso")

            # Registrar login no rastreamento
            if self.rastreamento:
                try:
                    await self.rastreamento.registrar_login_sistema(
                        "sienge", self.credenciais_sienge.get(
                            "usuario", ""), True
                    )
                except Exception:
                    pass  # Não quebra se rastreamento falhar

            time.sleep(5)
            if self.check_for_error(xpath='//a[@id="pushActionRefuse" and contains(text(), "Não, obrigado")]', timeout=15):
                self.click(
                    xpath='//a[@id="pushActionRefuse" and contains(text(), "Não, obrigado")]')
            if self.check_for_error(xpath='//button[@data-testid="close-button"]', timeout=10):
                self.click(xpath='//button[@data-testid="close-button"]')
            return True

        except Exception as e:
            # Registrar erro de login no rastreamento
            if self.rastreamento:
                try:
                    await self.rastreamento.registrar_login_sistema(
                        "sienge", self.credenciais_sienge.get(
                            "usuario", ""), False
                    )
                    await self.rastreamento.registrar_erro_critico(e, {
                        "fase": "login_sienge"
                    })
                except Exception:
                    pass  # Não quebra se rastreamento falhar
            raise Exception(f"Falha no login Sienge: {str(e)}")

    async def executar(self, parametros: Dict[str, Any]) -> ResultadoRPA:
        """
        Método principal de execução do RPA (requerido pela classe base).

        Este RPA é usado internamente pelo main_sienge_emissao_carnes.py
        que chama diretamente _gerar_carne_empresa_sienge.
        Este método existe apenas para satisfazer a interface abstrata.
        """
        try:
            # Este método não é usado diretamente, mas precisa existir
            # O main chama _gerar_carne_empresa_sienge diretamente
            resultado = await self._gerar_carne_empresa_sienge(parametros)

            if resultado.get("sucesso", False):
                return ResultadoRPA(
                    sucesso=True,
                    mensagem=f"Carnê gerado com sucesso para {parametros.get('empresa', 'N/A')}",
                    dados=resultado
                )
            else:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem=resultado.get(
                        "erro", "Erro desconhecido na geração de carnê"),
                    erro=resultado.get("erro", "Erro desconhecido"),
                    dados=resultado
                )
        except Exception as e:
            return ResultadoRPA(
                sucesso=False,
                mensagem=f"Erro na execução do RPA: {str(e)}",
                erro=str(e)
            )

    async def _gerar_carne_empresa_sienge(self, parametros: Dict[str, Any]) -> Dict[str, Any]:
        """
        CÓPIA NA ÍNTEGRA (com pequenas adaptações de import) do método de geração de carnê.
        """
        try:
            empresa = parametros.get("empresa", "")
            contratos = parametros.get("contratos", [])

            if " - " in empresa:
                codigo_empresa = empresa.split(" - ")[0].strip()
                empresa_original = empresa.split(" - ")[1].strip()
            else:
                codigo_empresa = empresa
                empresa_original = empresa

            try:
                conta_corrente = obter_conta_corrente_remessa(codigo_empresa)
            except (ValueError, FileNotFoundError) as erro:
                mensagem_erro = (
                    f"Erro ao localizar conta corrente de remessa para a empresa "
                    f"'{empresa_original}': {erro}"
                )
                self.log_erro(mensagem_erro, erro)
                return {"sucesso": False, "erro": mensagem_erro}

            self.log_progresso(
                "🎫 Executando webscraping para geração de carnê")
            self.log_progresso(f"📋 Empresa (completa): {empresa}")
            self.log_progresso(
                f"📋 Código empresa (extraído): {codigo_empresa}")
            self.log_progresso(
                f"🏦 Conta corrente de remessa: {conta_corrente}")
            self.log_progresso(f"📋 Contratos esperados: {len(contratos)}")

            self.get(
                url='https://jmservicos.sienge.com.br/sienge/8/index.html#/common/page/1919')
            time.sleep(5)
            if self.check_for_error(xpath='//iframe[@id="iFramePage"]', timeout=10):
                with self.on_iframe(xpath='//iframe[@id="iFramePage"]'):
                    if self.check_for_error(xpath='(//img[contains(@src, "botProcurar.png") and @title="Abre a consulta"])[1]'):
                        self.click(
                            xpath='(//img[@title="Abre a consulta"])[1]')
                        time.sleep(1)
                        # ✅ Fechar popup via JavaScript
                        self._fechar_popup_consulta()
                        if self.check_for_error(xpath='(//img[contains(@src, "botProcurar.png") and @title="Abre a consulta"])[1]'):
                            self.click(
                                xpath='(//img[@title="Abre a consulta"])[1]')
                            time.sleep(1)
                        with self.on_iframe(xpath='//iframe[@id="layerFormConsulta"]'):
                            empresa_campo_pesquisa = self.find_element(
                                xpath='//input[@id="entity.cdEmpresaView"]')
                            if empresa_campo_pesquisa:
                                self.send_text(
                                    xpath='//input[@id="entity.cdEmpresaView"]', text=codigo_empresa)
                                time.sleep(1)
                                self.click(
                                    xpath='//input[@id="pbProcurar" and @type="button"]')
                                time.sleep(1)
                                tabela_resultados = self.find_element(
                                    xpath='//table[@id="tabelaResultado"]')
                                if tabela_resultados:
                                    try:
                                        linhas = tabela_resultados.find_elements(
                                            By.XPATH, ".//tbody/tr")
                                        if not linhas:
                                            return {"sucesso": False, "erro": "Tabela de resultados está vazia - nenhuma empresa encontrada"}
                                        primeira_linha = linhas[0]
                                        radio = primeira_linha.find_element(
                                            By.XPATH, "./td[1]/input[@type='radio']")
                                        if not radio:
                                            return {"sucesso": False, "erro": "Nenhum radio button encontrado na primeira linha da grid."}
                                        radio.click()
                                        self.click(
                                            xpath='//input[@id="pbSelecionar" and @type="button"]')
                                    except Exception as e:
                                        self.log_erro(
                                            f"Erro ao processar tabela de resultados: {str(e)}", e)
                                        return {"sucesso": False, "erro": f"Erro ao processar tabela de resultados: {str(e)}"}
                        time.sleep(1)
                        with self.on_iframe(xpath='//iframe[@id="iFramePage"]'):
                            data_inicial = parametros.get('data_inicial')
                            if data_inicial:
                                self.send_text(
                                    xpath="//input[@type='text' and @id='entity.dtIniVencimento']", text=str(data_inicial))
                            time.sleep(1)
                            data_final_str = parametros.get('data_final')
                            if data_final_str:
                                from datetime import datetime as _dt
                                data_final = _dt.strptime(
                                    data_final_str, "%d/%m/%Y")
                                mes = data_final.month + 2
                                ano = data_final.year
                                if mes > 12:
                                    mes = 1
                                    ano += 1
                                dia = data_final.day
                                try:
                                    data_final_mais_um_mes = data_final.replace(
                                        year=ano, month=mes, day=dia)
                                except ValueError:
                                    from calendar import monthrange
                                    ultimo_dia_mes = monthrange(ano, mes)[1]
                                    data_final_mais_um_mes = data_final.replace(
                                        year=ano, month=mes, day=ultimo_dia_mes)
                                data_final_formatada = data_final_mais_um_mes.strftime(
                                    "%d/%m/%Y")
                                self.send_text(
                                    xpath="//input[@type='text' and @id='entity.dtFimVencimento']", text=str(data_final_formatada))
                            time.sleep(1)
                            self.click(
                                xpath='//input[@id="entity.flIncluirTituloInadimplente" and @type="checkbox"]')
                            time.sleep(1)
                            self.click(
                                xpath='//input[@id="entity.flIncluirTituloSubJudice" and @type="checkbox"]')
                            time.sleep(1)
                            self.click(
                                xpath='(//img[contains(@src, "botProcurar.png") and @title="Abre a consulta"])[13]')
                            with self.on_iframe(xpath='//iframe[@id="layerFormConsulta"]'):
                                nome_conta_corrente_pesquisa = self.find_element(
                                    xpath='//input[@id="entity.nmConta" and @type="text"]')
                                if nome_conta_corrente_pesquisa:
                                    self.send_text(
                                        xpath='//input[@id="entity.nmConta" and @type="text"]', text=conta_corrente)
                                    time.sleep(1)
                                    self.click(
                                        xpath='//input[@id="pbProcurar" and @type="button"]')
                                    time.sleep(1)
                                    tabela_resultados = self.find_element(
                                        xpath='//table[@id="tabelaResultado"]')
                                    if tabela_resultados:
                                        try:
                                            linhas = tabela_resultados.find_elements(
                                                By.XPATH, ".//tbody/tr")
                                            if not linhas:
                                                return {"sucesso": False, "erro": "Tabela de resultados está vazia - nenhuma conta corrente encontrada"}
                                            primeira_linha = linhas[0]
                                            radio = primeira_linha.find_element(
                                                By.XPATH, "./td[1]/input[@type='radio']")
                                            if not radio:
                                                return {"sucesso": False, "erro": "Nenhum radio button encontrado na primeira linha da grid."}
                                            radio.click()
                                            self.click(
                                                xpath='//input[@id="pbSelecionar" and @type="button"]')
                                        except Exception as e:
                                            self.log_erro(
                                                f"Erro ao processar tabela de resultados: {str(e)}", e)
                                            return {"sucesso": False, "erro": f"Erro ao processar tabela de resultados: {str(e)}"}
                            time.sleep(1)
                            with self.on_iframe(xpath='//iframe[@id="iFramePage"]'):
                                numero_conta_cliente = self.find_element(
                                    xpath='//input[@id="entity.contaCorrente.contaCorrentePK.nuConta" and @type="text"]')
                                if numero_conta_cliente:
                                    numero_conta_cliente_text = numero_conta_cliente.get_attribute(
                                        "oldvalue")
                                    sequencial_remessa = self.find_element(
                                        xpath='//input[@id="entity.contaCorrente.nuRemessaCob" and @type="text"]')
                                    sequencial_remessa_text = sequencial_remessa.get_attribute(
                                        "oldvalue") if sequencial_remessa else "1"
                                    nome_arquivo_remessa = self._gerar_nome_arquivo_remessa(
                                        empresa=empresa_original,
                                        numero_conta=str(
                                            numero_conta_cliente_text) if numero_conta_cliente_text else "",
                                        sequencial=int(
                                            sequencial_remessa_text) if sequencial_remessa_text and sequencial_remessa_text.isdigit() else 1,
                                    )
                                    self.send_text(
                                        xpath='//input[@id="entity.nmArquivoRemessa" and @type="text"]', text=nome_arquivo_remessa)
                                    time.sleep(1)
                                    mensagem_remessa = self.find_element(
                                        xpath="//input[@id='entity.contaCorrente.cdMensagemRemessa']")
                                    if mensagem_remessa:
                                        self.send_text(
                                            xpath="//input[@id='entity.contaCorrente.cdMensagemRemessa']", text="1")
                                        time.sleep(1)
                                        mensagem_remessa.send_keys(Keys.TAB)
                                        time.sleep(2)
                                    self.click(
                                        xpath="//input[@type='checkbox' and @id='entity.flImprimirBloqueto']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click(
                                        "//input[@type='checkbox' and @id='entity.flEnviarBoletosPorEmail']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click(
                                        "//input[@type='checkbox' and @id='entity.flAgruparEmailCliente']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click(
                                        "//input[@type='checkbox' and @id='entity.flGerarBoletosEmArquivosSeparados']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click(
                                        "//input[@type='checkbox' and @id='entity.flConsiderarJaEnviadas']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click(
                                        "//input[@type='checkbox' and @id='entity.flConsiderarTpCond']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click(
                                        "//input[@type='checkbox' and @id='entity.flFazerDownloadBoletos']", checkbox_action="uncheck")

                                    time.sleep(1)
                                    mensagem_boleto = self.find_element(
                                        xpath="//input[@id='entity.contaCorrente.cdMensagemBoleto']")
                                    if mensagem_boleto:
                                        self.send_text(
                                            xpath="//input[@id='entity.contaCorrente.cdMensagemBoleto']", text="16", clear=True)
                                        time.sleep(1)
                                        mensagem_boleto.send_keys(Keys.TAB)
                                        time.sleep(1)
                                        self.click(
                                            xpath="//input[@type='button' and @id='btGeracaoRemessaConsultar']")
                                        time.sleep(5)
                                        if self.check_for_error(xpath="//table[@id='tabelaAgrupParcelaGrid']", timeout=35):
                                            contratos_encontrados = self._extrair_contratos_da_tabela()
                                            if contratos_encontrados:
                                                parcelas_validadas = self._validar_contratos_encontrados(
                                                    contratos, contratos_encontrados)
                                                if parcelas_validadas:
                                                    resultado_grid = self._marcar_todos_contratos_tabela(
                                                        parcelas_validadas)
                                                    if resultado_grid["sucesso"]:
                                                        self.click(
                                                            "//input[@type='button' and @id='pbGerar']")
                                                        time.sleep(1)
                                                    else:
                                                        return {"sucesso": False, "erro": "Falha ao marcar contratos na tabela"}
                                                else:
                                                    return {"sucesso": False, "erro": "Nenhum contrato validado encontrado"}
                                            else:
                                                return {"sucesso": False, "erro": "Nenhum contrato encontrado na tabela"}

                                            # Espera pelo arquivo gerado e move para outputs/remessas
                                            RPA_DOWNLOADS_FOLDER = os.getenv(
                                                "RPA_DOWNLOADS_FOLDER", "RPA_DOWNLOADS")
                                            if RPA_DOWNLOADS_FOLDER and RPA_DOWNLOADS_FOLDER.startswith('/'):
                                                RPA_DOWNLOADS_FOLDER = RPA_DOWNLOADS_FOLDER[1:]
                                            from platformdirs import user_downloads_dir  # type: ignore
                                            from pathlib import Path
                                            downloads_dir = Path(
                                                user_downloads_dir()) / RPA_DOWNLOADS_FOLDER
                                            downloads_dir.mkdir(
                                                parents=True, exist_ok=True)
                                            arquivo_remessa_nome = nome_arquivo_remessa
                                            arquivo_remessa_path = downloads_dir / arquivo_remessa_nome
                                            timeout = 60
                                            espera = 0
                                            while not arquivo_remessa_path.exists() and espera < timeout:
                                                time.sleep(1)
                                                espera += 1
                                            if not arquivo_remessa_path.exists():
                                                return {"sucesso": False, "erro": f"Arquivo de remessa '{arquivo_remessa_nome}' não encontrado."}
                                            import shutil
                                            pasta_destino = Path(
                                                "outputs/remessas")
                                            pasta_destino.mkdir(
                                                parents=True, exist_ok=True)
                                            caminho_destino = pasta_destino / arquivo_remessa_nome
                                            shutil.move(
                                                str(arquivo_remessa_path), str(caminho_destino))
                                            try:
                                                caminho_relativo = str(
                                                    caminho_destino.relative_to(Path.cwd()))
                                            except Exception:
                                                caminho_relativo = str(
                                                    caminho_destino.resolve())
                                            # Atualização de status dos contratos via repositorio_contratos_arquivo
                                            await self._atualizar_status_carne_gerado(contratos, {
                                                "arquivo_remessa": caminho_relativo,
                                                "empresa": empresa,
                                                "contratos_processados": len(contratos),
                                            })

            resultado = {
                "sucesso": True,
                "arquivo_remessa": caminho_relativo if 'caminho_relativo' in locals() else "",
                "contratos_processados": len(contratos),
                "empresa": empresa,
                "empresa_original": empresa_original,
                "timestamp_geracao": datetime.now().isoformat(),
            }

            # Registrar sucesso no rastreamento
            if self.rastreamento:
                try:
                    await self.rastreamento.registrar_sucesso_rpa(resultado)
                    await self.rastreamento.finalizar_rastreamento()
                except Exception:
                    pass  # Não quebra se rastreamento falhar

            return resultado

        except Exception as e:
            erro_msg = f"Erro na geração de carnê para empresa {parametros.get('empresa', 'N/A')}: {str(e)}"
            self.log_erro(erro_msg, e)

            # Registrar erro no rastreamento
            if self.rastreamento:
                try:
                    await self.rastreamento.registrar_erro_critico(e, {
                        "fase": "geracao_carne",
                        "empresa": parametros.get('empresa', 'N/A')
                    })
                    await self.rastreamento.finalizar_rastreamento()
                except Exception:
                    pass  # Não quebra se rastreamento falhar

            return {"sucesso": False, "erro": erro_msg}

    def _fechar_popup_consulta(self):
        """
        Fecha popup de consulta (Beamer) que está dentro do iframe beamerNews.
        Fecha o popup e volta ao iframe iFramePage.
        """
        try:
            if not self.browser or not self.browser._driver:
                return

            self.log_progresso("🔄 Fechando popup Beamer...")
            time.sleep(2)

            # Sair do iframe atual e entrar no beamerNews
            self.browser._driver.switch_to.default_content()

            try:
                from selenium.webdriver.support import expected_conditions as EC
                iframe_beamer = self.browser._driver_wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//iframe[@id="beamerNews"]'))
                )
                self.browser._driver.switch_to.frame(iframe_beamer)

                # Tentar fechar via BeamerEmbed.close()
                try:
                    resultado = self.browser._driver.execute_script("""
                        if (typeof BeamerEmbed !== 'undefined' && typeof BeamerEmbed.close === 'function') {
                            BeamerEmbed.close();
                            return true;
                        }
                        return false;
                    """)
                    if resultado:
                        self.log_progresso("✅ Popup fechado")
                        time.sleep(1)
                except Exception:
                    # Se falhar, tentar clicar no botão
                    try:
                        if self.check_for_error(xpath="//div[@class='headerClose']", timeout=2):
                            self.click(xpath="//div[@class='headerClose']")
                            time.sleep(1)
                            self.log_progresso("✅ Popup fechado")
                    except Exception:
                        pass

                # Voltar ao default_content
                self.browser._driver.switch_to.default_content()

                # Voltar ao iframe iFramePage
                try:
                    iframe_original = self.browser._driver_wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//iframe[@id="iFramePage"]'))
                    )
                    self.browser._driver.switch_to.frame(iframe_original)
                except Exception:
                    pass

            except Exception:
                # Se não encontrar beamerNews, tentar voltar ao iFramePage
                try:
                    self.browser._driver.switch_to.default_content()
                    iframe_original = self.browser._driver_wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//iframe[@id="iFramePage"]'))
                    )
                    self.browser._driver.switch_to.frame(iframe_original)
                except Exception:
                    pass

        except Exception:
            pass  # Não quebra o fluxo se falhar

    def _validar_contratos_encontrados(self, contratos_esperados: List[Dict], contratos_encontrados: List[str]) -> List[Dict[str, Any]]:
        """
        Valida contratos encontrados filtrando por título E data de vencimento.

        Retorna lista de dicionários com 'titulo' e 'data_vencimento' das parcelas válidas.
        """
        try:
            # ✅ NOVA LÓGICA: Criar mapa de parcelas esperadas por título
            # Estrutura: {titulo: set(datas_esperadas)}
            parcelas_esperadas_por_titulo = {}

            for contrato in contratos_esperados:
                titulo = contrato.get('Titulo', '').strip()
                if not titulo:
                    continue

                titulo_limpo = str(titulo).strip()
                parcelas_esperadas = contrato.get('parcelas_esperadas', [])

                if parcelas_esperadas:
                    # Normalizar datas para comparação (DD/MM/YYYY)
                    parcelas_normalizadas = set()
                    for parcela in parcelas_esperadas:
                        # Garantir formato DD/MM/YYYY
                        if "/" in parcela:
                            partes = parcela.split("/")
                            if len(partes) == 3:
                                if len(partes[2]) == 2:
                                    # Converter YY para YYYY
                                    ano = int(partes[2])
                                    if ano < 50:
                                        ano += 2000
                                    else:
                                        ano += 1900
                                    parcela_normalizada = f"{partes[0]}/{partes[1]}/{ano}"
                                else:
                                    parcela_normalizada = parcela
                                parcelas_normalizadas.add(parcela_normalizada)

                    if titulo_limpo not in parcelas_esperadas_por_titulo:
                        parcelas_esperadas_por_titulo[titulo_limpo] = set()
                    parcelas_esperadas_por_titulo[titulo_limpo].update(
                        parcelas_normalizadas)

                    self.log_progresso(
                        f"📋 Título {titulo_limpo}: {len(parcelas_normalizadas)} parcelas esperadas")
                else:
                    # Fallback: se não há parcelas esperadas, aceitar todas as parcelas do título
                    self.log_warning(
                        f"⚠️ Título {titulo_limpo} sem parcelas_esperadas - usando validação apenas por título")
                    if titulo_limpo not in parcelas_esperadas_por_titulo:
                        # None = aceitar todas
                        parcelas_esperadas_por_titulo[titulo_limpo] = None

            # ✅ Filtrar contratos_encontrados por título E data
            parcelas_validadas = []

            for contrato_str in contratos_encontrados:
                try:
                    # Extrair título
                    if "(Título:" not in contrato_str:
                        continue

                    titulo_completo = contrato_str.split(
                        "(Título:")[1].split(")")[0].strip()
                    if "/" in titulo_completo:
                        titulo = titulo_completo.split("/")[0].strip()
                    else:
                        titulo = titulo_completo.strip()

                    # Extrair data de vencimento
                    data_vencimento = None
                    if "Data de vencimento:" in contrato_str:
                        data_vencimento = contrato_str.split(
                            "Data de vencimento:")[1].strip()

                    # Verificar se título está nas parcelas esperadas
                    if titulo not in parcelas_esperadas_por_titulo:
                        continue

                    parcelas_esperadas = parcelas_esperadas_por_titulo[titulo]

                    # Se parcelas_esperadas é None, aceitar todas (fallback)
                    if parcelas_esperadas is None:
                        parcelas_validadas.append({
                            'titulo': titulo,
                            'data_vencimento': data_vencimento,
                            'string_original': contrato_str
                        })
                        continue

                    # Normalizar data encontrada para comparação
                    if data_vencimento:
                        if "/" in data_vencimento:
                            partes_data = data_vencimento.split("/")
                            if len(partes_data) == 3:
                                if len(partes_data[2]) == 2:
                                    ano = int(partes_data[2])
                                    if ano < 50:
                                        ano += 2000
                                    else:
                                        ano += 1900
                                    data_normalizada = f"{partes_data[0]}/{partes_data[1]}/{ano}"
                                else:
                                    data_normalizada = data_vencimento

                                # Verificar se data está nas parcelas esperadas
                                if data_normalizada in parcelas_esperadas:
                                    parcelas_validadas.append({
                                        'titulo': titulo,
                                        'data_vencimento': data_vencimento,
                                        'data_normalizada': data_normalizada,
                                        'string_original': contrato_str
                                    })
                                    self.log_progresso(
                                        f"✅ Parcela validada: Título {titulo}, Data {data_vencimento}")
                                else:
                                    self.log_progresso(
                                        f"⚠️ Parcela ignorada: Título {titulo}, Data {data_vencimento} (não está nas 12 esperadas)")

                except Exception as e:
                    self.log_warning(
                        f"Erro ao processar contrato_str: {contrato_str[:50]}... - {str(e)}")
                    continue

            self.log_progresso(
                f"📊 Validação concluída: {len(parcelas_validadas)} parcelas validadas de {len(contratos_encontrados)} encontradas")

            return parcelas_validadas

        except Exception as e:
            self.log_erro(f"Erro na validação de contratos: {str(e)}", e)
            return []

    def _marcar_todos_contratos_tabela(self, parcelas_validadas: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Marca checkboxes apenas das parcelas validadas (título + data correta).

        Args:
            parcelas_validadas: Lista de dicionários com 'titulo', 'data_vencimento', etc.
        """
        try:
            total_marcados = 0
            total_validados = 0
            total_ignorados = 0

            tabela = self.find_element(
                xpath="//table[@id='tabelaAgrupParcelaGrid']")
            if not tabela:
                return {"sucesso": False, "erro": "Tabela de resultados não encontrada"}

            if not parcelas_validadas:
                return {"sucesso": False, "erro": "Parcelas validadas são obrigatórias - nenhuma parcela fornecida"}

            # ✅ Criar conjunto de chaves únicas (titulo + data_normalizada) para busca rápida
            parcelas_validas_set = set()
            for parcela in parcelas_validadas:
                titulo = parcela.get('titulo', '').strip()
                data_normalizada = parcela.get('data_normalizada', '')
                if titulo and data_normalizada:
                    parcelas_validas_set.add(f"{titulo}|{data_normalizada}")
                elif titulo:
                    # Fallback: se não há data_normalizada, usar apenas título
                    parcelas_validas_set.add(f"{titulo}|*")

            self.log_progresso(
                f"🎯 Marcando {len(parcelas_validadas)} parcelas validadas na tabela...")

            linhas = tabela.find_elements(By.XPATH, ".//tbody/tr")
            self.log_progresso(f"📊 Total de linhas na tabela: {len(linhas)}")

            for linha in linhas:
                try:
                    celulas = linha.find_elements(By.XPATH, ".//td")
                    if len(celulas) >= 3:
                        dados_consolidados = celulas[2].text.strip()
                        if dados_consolidados:
                            partes = dados_consolidados.split(" / ")
                            if len(partes) >= 3:
                                # Extrair título
                                titulo_completo = partes[0].strip()
                                if "/" in titulo_completo:
                                    titulo = titulo_completo.split(
                                        "/")[0].strip()
                                else:
                                    titulo = titulo_completo

                                # Extrair data de vencimento
                                data_vencimento = partes[2].strip()

                                # Normalizar data para comparação
                                data_normalizada = None
                                if "/" in data_vencimento:
                                    partes_data = data_vencimento.split("/")
                                    if len(partes_data) == 3:
                                        if len(partes_data[2]) == 2:
                                            ano = int(partes_data[2])
                                            if ano < 50:
                                                ano += 2000
                                            else:
                                                ano += 1900
                                            data_normalizada = f"{partes_data[0]}/{partes_data[1]}/{ano}"
                                        else:
                                            data_normalizada = data_vencimento

                                # Verificar se parcela está nas validadas
                                chave_busca = f"{titulo}|{data_normalizada}" if data_normalizada else f"{titulo}|*"
                                # Fallback sem data
                                chave_busca_alternativa = f"{titulo}|*"

                                if chave_busca in parcelas_validas_set or chave_busca_alternativa in parcelas_validas_set:
                                    checkbox = linha.find_element(
                                        By.XPATH, ".//input[@type='checkbox'][contains(@id, 'flSelecionado_')]")
                                    if not checkbox.is_selected():
                                        checkbox.click()
                                        total_marcados += 1
                                        self.log_progresso(
                                            f"✅ Marcado: Título {titulo}, Data {data_vencimento}")
                                    total_validados += 1
                                else:
                                    total_ignorados += 1
                                    self.log_progresso(
                                        f"⚠️ Ignorado: Título {titulo}, Data {data_vencimento} (não está nas parcelas esperadas)")
                except Exception as e:
                    self.log_warning(
                        f"Erro ao processar linha da tabela: {str(e)}")
                    continue

            self.log_progresso(
                f"📊 Marcação concluída: {total_marcados} marcados, {total_validados} validados, {total_ignorados} ignorados")

            return {
                "sucesso": True,
                "total_marcados": total_marcados,
                "total_validados": total_validados,
                "total_ignorados": total_ignorados,
                "total_checkboxes": len(linhas),
            }
        except Exception as e:
            self.log_erro(f"Erro ao marcar contratos: {str(e)}", e)
            return {"sucesso": False, "erro": f"Erro ao marcar contratos: {str(e)}"}

    async def _atualizar_status_carne_gerado(self, contratos: List[Dict[str, Any]], resultado_carne: Dict[str, Any]):
        """Atualiza status dos contratos para CARNE_GERADO (cópia adaptada)."""
        try:
            from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo
            from datetime import datetime as _dt
            contratos_atualizados = 0
            for contrato in contratos:
                numero_titulo = contrato.get("Titulo", "")
                if numero_titulo:
                    dados_atualizacao = {
                        "status": "CARNE_GERADO",
                        "resultado_final": "CARNE_GERADO",
                        "timestamp_carne_gerado": _dt.now().isoformat(),
                        "timestamp_ultima_atualizacao": _dt.now().isoformat(),
                        "arquivo_remessa": resultado_carne.get("arquivo_remessa", ""),
                        "empresa": resultado_carne.get("empresa", ""),
                        "contratos_processados_carne": resultado_carne.get("contratos_processados", 0),
                    }
                    contratos_encontrados = repositorio_contratos_arquivo.framework.find(
                        {"Titulo": numero_titulo})
                    if contratos_encontrados:
                        contrato_encontrado = contratos_encontrados[0]
                        contrato_id = contrato_encontrado.get("_id")
                        if contrato_id:
                            repositorio_contratos_arquivo.framework.update(
                                {"_id": contrato_id}, dados_atualizacao)
                            contratos_atualizados += 1
        except Exception as e:
            self.log_erro(
                f"Erro ao atualizar status para CARNE_GERADO: {str(e)}", e)

    def _extrair_contratos_da_tabela(self) -> List[str]:
        """Extrai strings consolidadas da grid (cópia literal)."""
        try:
            contratos_encontrados: List[str] = []
            tabela = self.find_element(
                xpath="//table[@id='tabelaAgrupParcelaGrid']")
            if not tabela:
                return contratos_encontrados
            linhas = tabela.find_elements(By.XPATH, ".//tbody/tr")
            for linha in linhas:
                try:
                    celulas = linha.find_elements(By.XPATH, ".//td")
                    if len(celulas) >= 3:
                        dados_consolidados = celulas[2].text.strip()
                        if dados_consolidados:
                            partes = dados_consolidados.split(" / ")
                            if len(partes) >= 3:
                                titulo = partes[0].strip()
                                cliente = partes[1].strip()
                                data_vencimento = partes[2].strip()
                                contratos_encontrados.append(
                                    f"{cliente} (Título: {titulo}) - Data de vencimento: {data_vencimento}")
                except Exception:
                    continue
            return contratos_encontrados
        except Exception:
            return []

    def _gerar_nome_arquivo_remessa(self, empresa: str, numero_conta: str, sequencial: int = 1) -> str:
        """
        Gera nome do arquivo de remessa conforme PDD 10.2

        Regras:
        - Primeiros 5 dígitos da conta corrente (sem zero à esquerda)
        - Número do mês (SEM zero à esquerda) Adicional da regra.. quando for mes 10, 11 ou 12: tem que usar O, N, D ao invés de 10, 11 ou 12
        - Número do dia (SEM zero à esquerda)
        - Ponto (.)
        - Número sequencial da remessa (SEM zero à esquerda)

        Exceções:
        - Rio Almada: usar 06300 ao invés da conta
        - SPE RESIDENCIAL PARQUE DA LAGOA: usar 01870 ao invés da conta

        Args:
            empresa: Nome da empresa
            numero_conta: Número da conta corrente
            sequencial: Número sequencial da remessa (padrão: 1)

        Returns:
            Nome do arquivo de remessa formatado
        """
        try:
            # Obter data atual
            data_atual = datetime.now()
            mes = data_atual.month
            dia = data_atual.day

            # Regras específicas conforme PDD 10.2
            if "ALMADA" in empresa.upper():
                prefixo_conta = "06300"
                self.log_progresso(
                    f"🏢 Almada detectado - usando prefixo: {prefixo_conta}")
            elif "PARQUE DA LAGOA" in empresa.upper():
                prefixo_conta = "01870"
                self.log_progresso(
                    f"🏢 Parque da Lagoa detectado - usando prefixo: {prefixo_conta}")
            else:
                # Usar primeiros 5 dígitos da conta corrente (ignorando zeros à esquerda)
                if numero_conta:
                    # Remove zeros à esquerda e pega os 5 primeiros dígitos significativos
                    numero_sem_zeros = numero_conta.lstrip('0')
                    if numero_sem_zeros:
                        # Pega os 5 primeiros dígitos significativos
                        prefixo_conta = numero_sem_zeros[:5]
                        # Se tem menos de 5 dígitos, completa com zeros à direita
                        if len(prefixo_conta) < 5:
                            prefixo_conta = prefixo_conta.ljust(5, '0')
                        self.log_progresso(
                            f"🏦 Conta '{numero_conta}' → sem zeros: '{numero_sem_zeros}' → prefixo: '{prefixo_conta}'")
                    else:
                        # ❌ SEM FALLBACK: Lançar exceção se a conta só tem zeros
                        erro_msg = "Conta bancária inválida (só contém zeros) - sem fallback"
                        self.log_error(erro_msg)
                        raise ValueError(erro_msg)
                else:
                    # ❌ SEM FALLBACK: Lançar exceção se não tiver conta
                    erro_msg = "Conta bancária não fornecida - sem fallback"
                    self.log_error(erro_msg)
                    raise ValueError(erro_msg)

            # Formatar componentes (mês sem zero à esquerda, dia com zero à esquerda)
            mes_formatado = f"{mes}"  # Sem zero à esquerda (3 em vez de 03)
            if mes == 10:
                mes_formatado = "O"
            elif mes == 11:
                mes_formatado = "N"
            elif mes == 12:
                mes_formatado = "D"
            # Com zero à esquerda (12 em vez de 12)
            dia_formatado = f"{dia:02d}"
            # Sem zero à esquerda (2231 em vez de 0002231)
            sequencial_formatado = f"{sequencial}"

            # Montar nome do arquivo conforme PDD
            nome_arquivo = f"{prefixo_conta}{mes_formatado}{dia_formatado}.{sequencial_formatado}"

            self.log_progresso(
                f"📄 Nome arquivo remessa gerado: {nome_arquivo}")

            return nome_arquivo

        except Exception as e:
            self.log_error(
                f"Erro ao gerar nome do arquivo de remessa: {str(e)}")
            raise
