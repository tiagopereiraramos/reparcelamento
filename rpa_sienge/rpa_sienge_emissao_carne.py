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

from core.base_rpa import BaseRPA
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
                    self.rastreamento = iniciar_rastreamento("RPA_Sienge_EmissaoCarne")
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
                raise ValueError("URL do Sienge não foi configurada corretamente.")

            self.get_page(url_sienge)
            time.sleep(3)

            # Preenche usuário inicial
            self.send_text(xpath='(//input[@id="username"])[1]', text=usuario_sienge)
            # Preenche senha inicial
            self.send_text(xpath='//input[@id="password"]', text=senha_sienge)
            # Clica botão entrar inicial
            self.click(xpath='//*[@id="btnEntrarComSiengeID"]')
            time.sleep(2)

            # Segunda etapa - email
            self.send_text(
                xpath='//label[text()="Seu e-mail"]/following-sibling::div//input',
                text=usuario_sienge,
            )
            # Clica continuar
            self.click(xpath="//button[normalize-space(text())='CONTINUAR']")

            # Terceira etapa - senha final
            self.send_text(xpath="//input[@id='signup-password']", text=senha_sienge)
            # Clica entrar final
            self.click(xpath="//button[normalize-space(text())='ENTRAR']")

            if self.check_for_error("//div[contains(@class, 'spwAlertaAviso')]//p[contains(normalize-space(.), 'Deseja prosseguir desconectando')]", timeout=5):
                self.log_warning("Usuário já logado - prosseguindo")
                self.click(xpath="//a[contains(@class, 'Button-prim') and contains(., 'Prosseguir')]")

            self.logado_sienge = True
            self.log_progresso("Login no Sienge realizado com sucesso")
            
            # Registrar login no rastreamento
            if self.rastreamento:
                try:
                    await self.rastreamento.registrar_login_sistema(
                        "sienge", self.credenciais_sienge.get("usuario", ""), True
                    )
                except Exception:
                    pass  # Não quebra se rastreamento falhar

            time.sleep(5)
            if self.check_for_error(xpath='//a[@id="pushActionRefuse" and contains(text(), "Não, obrigado")]', timeout=15):
                self.click(xpath='//a[@id="pushActionRefuse" and contains(text(), "Não, obrigado")]')
            if self.check_for_error(xpath='//button[@data-testid="close-button"]', timeout=10):
                self.click(xpath='//button[@data-testid="close-button"]')
            return True

        except Exception as e:
            # Registrar erro de login no rastreamento
            if self.rastreamento:
                try:
                    await self.rastreamento.registrar_login_sistema(
                        "sienge", self.credenciais_sienge.get("usuario", ""), False
                    )
                    await self.rastreamento.registrar_erro_critico(e, {
                        "fase": "login_sienge"
                    })
                except Exception:
                    pass  # Não quebra se rastreamento falhar
            raise Exception(f"Falha no login Sienge: {str(e)}")

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

            self.log_progresso("🎫 Executando webscraping para geração de carnê")
            self.log_progresso(f"📋 Empresa (completa): {empresa}")
            self.log_progresso(f"📋 Código empresa (extraído): {codigo_empresa}")
            self.log_progresso(f"🏦 Conta corrente de remessa: {conta_corrente}")
            self.log_progresso(f"📋 Contratos esperados: {len(contratos)}")

            self.get(url='https://jmservicos.sienge.com.br/sienge/8/index.html#/common/page/1919')
            time.sleep(5)
            if self.check_for_error(xpath='//iframe[@id="iFramePage"]', timeout=10):
                with self.on_iframe(xpath='//iframe[@id="iFramePage"]'):
                    if self.check_for_error(xpath='(//img[contains(@src, "botProcurar.png") and @title="Abre a consulta"])[1]'):
                        self.click(xpath='(//img[@title="Abre a consulta"])[1]')
                        time.sleep(1)
                        with self.on_iframe(xpath='//iframe[@id="layerFormConsulta"]'):
                            empresa_campo_pesquisa = self.find_element(xpath='//input[@id="entity.cdEmpresaView"]')
                            if empresa_campo_pesquisa:
                                self.send_text(xpath='//input[@id="entity.cdEmpresaView"]', text=codigo_empresa)
                                time.sleep(1)
                                self.click(xpath='//input[@id="pbProcurar" and @type="button"]')
                                time.sleep(1)
                                tabela_resultados = self.find_element(xpath='//table[@id="tabelaResultado"]')
                                if tabela_resultados:
                                    try:
                                        linhas = tabela_resultados.find_elements(By.XPATH, ".//tbody/tr")
                                        if not linhas:
                                            return {"sucesso": False, "erro": "Tabela de resultados está vazia - nenhuma empresa encontrada"}
                                        primeira_linha = linhas[0]
                                        radio = primeira_linha.find_element(By.XPATH, "./td[1]/input[@type='radio']")
                                        if not radio:
                                            return {"sucesso": False, "erro": "Nenhum radio button encontrado na primeira linha da grid."}
                                        radio.click()
                                        self.click(xpath='//input[@id="pbSelecionar" and @type="button"]')
                                    except Exception as e:
                                        self.log_erro(f"Erro ao processar tabela de resultados: {str(e)}", e)
                                        return {"sucesso": False, "erro": f"Erro ao processar tabela de resultados: {str(e)}"}
                        time.sleep(1)
                        with self.on_iframe(xpath='//iframe[@id="iFramePage"]'):
                            data_inicial = parametros.get('data_inicial')
                            if data_inicial:
                                self.send_text(xpath="//input[@type='text' and @id='entity.dtIniVencimento']", text=str(data_inicial))
                            time.sleep(1)
                            data_final_str = parametros.get('data_final')
                            if data_final_str:
                                from datetime import datetime as _dt
                                data_final = _dt.strptime(data_final_str, "%d/%m/%Y")
                                mes = data_final.month + 1
                                ano = data_final.year
                                if mes > 12:
                                    mes = 1
                                    ano += 1
                                dia = data_final.day
                                try:
                                    data_final_mais_um_mes = data_final.replace(year=ano, month=mes, day=dia)
                                except ValueError:
                                    from calendar import monthrange
                                    ultimo_dia_mes = monthrange(ano, mes)[1]
                                    data_final_mais_um_mes = data_final.replace(year=ano, month=mes, day=ultimo_dia_mes)
                                data_final_formatada = data_final_mais_um_mes.strftime("%d/%m/%Y")
                                self.send_text(xpath="//input[@type='text' and @id='entity.dtFimVencimento']", text=str(data_final_formatada))
                            time.sleep(1)
                            self.click(xpath='//input[@id="entity.flIncluirTituloInadimplente" and @type="checkbox"]')
                            time.sleep(1)
                            self.click(xpath='//input[@id="entity.flIncluirTituloSubJudice" and @type="checkbox"]')
                            time.sleep(1)
                            self.click(xpath='(//img[contains(@src, "botProcurar.png") and @title="Abre a consulta"])[13]')
                            with self.on_iframe(xpath='//iframe[@id="layerFormConsulta"]'):
                                nome_conta_corrente_pesquisa = self.find_element(xpath='//input[@id="entity.nmConta" and @type="text"]')
                                if nome_conta_corrente_pesquisa:
                                    self.send_text(xpath='//input[@id="entity.nmConta" and @type="text"]', text=conta_corrente)
                                    time.sleep(1)
                                    self.click(xpath='//input[@id="pbProcurar" and @type="button"]')
                                    time.sleep(1)
                                    tabela_resultados = self.find_element(xpath='//table[@id="tabelaResultado"]')
                                    if tabela_resultados:
                                        try:
                                            linhas = tabela_resultados.find_elements(By.XPATH, ".//tbody/tr")
                                            if not linhas:
                                                return {"sucesso": False, "erro": "Tabela de resultados está vazia - nenhuma conta corrente encontrada"}
                                            primeira_linha = linhas[0]
                                            radio = primeira_linha.find_element(By.XPATH, "./td[1]/input[@type='radio']")
                                            if not radio:
                                                return {"sucesso": False, "erro": "Nenhum radio button encontrado na primeira linha da grid."}
                                            radio.click()
                                            self.click(xpath='//input[@id="pbSelecionar" and @type="button"]')
                                        except Exception as e:
                                            self.log_erro(f"Erro ao processar tabela de resultados: {str(e)}", e)
                                            return {"sucesso": False, "erro": f"Erro ao processar tabela de resultados: {str(e)}"}
                            time.sleep(1)
                            with self.on_iframe(xpath='//iframe[@id="iFramePage"]'):
                                numero_conta_cliente = self.find_element(xpath='//input[@id="entity.contaCorrente.contaCorrentePK.nuConta" and @type="text"]')
                                if numero_conta_cliente:
                                    numero_conta_cliente_text = numero_conta_cliente.get_attribute("oldvalue")
                                    sequencial_remessa = self.find_element(xpath='//input[@id="entity.contaCorrente.nuRemessaCob" and @type="text"]')
                                    sequencial_remessa_text = sequencial_remessa.get_attribute("oldvalue") if sequencial_remessa else "1"
                                    nome_arquivo_remessa = self._gerar_nome_arquivo_remessa(
                                        empresa=empresa_original,
                                        numero_conta=str(numero_conta_cliente_text) if numero_conta_cliente_text else "",
                                        sequencial=int(sequencial_remessa_text) if sequencial_remessa_text and sequencial_remessa_text.isdigit() else 1,
                                    )
                                    self.send_text(xpath='//input[@id="entity.nmArquivoRemessa" and @type="text"]', text=nome_arquivo_remessa)
                                    time.sleep(1)
                                    mensagem_remessa = self.find_element(xpath="//input[@id='entity.contaCorrente.cdMensagemRemessa']")
                                    if mensagem_remessa:
                                        self.send_text(xpath="//input[@id='entity.contaCorrente.cdMensagemRemessa']", text="1")
                                        time.sleep(1)
                                        mensagem_remessa.send_keys(Keys.TAB)
                                        time.sleep(2)
                                    self.click(xpath="//input[@type='checkbox' and @id='entity.flImprimirBloqueto']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click("//input[@type='checkbox' and @id='entity.flEnviarBoletosPorEmail']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click("//input[@type='checkbox' and @id='entity.flAgruparEmailCliente']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click("//input[@type='checkbox' and @id='entity.flGerarBoletosEmArquivosSeparados']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click("//input[@type='checkbox' and @id='entity.flConsiderarJaEnviadas']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click("//input[@type='checkbox' and @id='entity.flConsiderarTpCond']", checkbox_action="check")
                                    time.sleep(0.3)
                                    self.click("//input[@type='checkbox' and @id='entity.flFazerDownloadBoletos']", checkbox_action="uncheck")

                                    time.sleep(1)
                                    mensagem_boleto = self.find_element(xpath="//input[@id='entity.contaCorrente.cdMensagemBoleto']")
                                    if mensagem_boleto:
                                        self.send_text(xpath="//input[@id='entity.contaCorrente.cdMensagemBoleto']", text="16", clear=True)
                                        time.sleep(1)
                                        mensagem_boleto.send_keys(Keys.TAB)
                                        time.sleep(1)
                                        self.click(xpath="//input[@type='button' and @id='btGeracaoRemessaConsultar']")
                                        time.sleep(5)
                                        if self.check_for_error(xpath="//table[@id='tabelaAgrupParcelaGrid']", timeout=35):
                                            contratos_encontrados = self._extrair_contratos_da_tabela()
                                            if contratos_encontrados:
                                                titulos_validados = self._validar_contratos_encontrados(contratos, contratos_encontrados)
                                                if titulos_validados:
                                                    resultado_grid = self._marcar_todos_contratos_tabela(titulos_validados)
                                                    if resultado_grid["sucesso"]:
                                                        self.click("//input[@type='button' and @id='pbGerar']")
                                                        time.sleep(1)
                                                    else:
                                                        return {"sucesso": False, "erro": "Falha ao marcar contratos na tabela"}
                                                else:
                                                    return {"sucesso": False, "erro": "Nenhum contrato validado encontrado"}
                                            else:
                                                return {"sucesso": False, "erro": "Nenhum contrato encontrado na tabela"}

                                            # Espera pelo arquivo gerado e move para outputs/remessas
                                            RPA_DOWNLOADS_FOLDER = os.getenv("RPA_DOWNLOADS_FOLDER", "RPA_DOWNLOADS")
                                            if RPA_DOWNLOADS_FOLDER and RPA_DOWNLOADS_FOLDER.startswith('/'):
                                                RPA_DOWNLOADS_FOLDER = RPA_DOWNLOADS_FOLDER[1:]
                                            from platformdirs import user_downloads_dir  # type: ignore
                                            from pathlib import Path
                                            downloads_dir = Path(user_downloads_dir()) / RPA_DOWNLOADS_FOLDER
                                            downloads_dir.mkdir(parents=True, exist_ok=True)
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
                                            pasta_destino = Path("outputs/remessas")
                                            pasta_destino.mkdir(parents=True, exist_ok=True)
                                            caminho_destino = pasta_destino / arquivo_remessa_nome
                                            shutil.move(str(arquivo_remessa_path), str(caminho_destino))
                                            try:
                                                caminho_relativo = str(caminho_destino.relative_to(Path.cwd()))
                                            except Exception:
                                                caminho_relativo = str(caminho_destino.resolve())
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

    def _validar_contratos_encontrados(self, contratos_esperados: List[Dict], contratos_encontrados: List[str]) -> List[str]:
        """Cópia literal do validador usado no rpa_sienge.py."""
        try:
            titulos_esperados = set()
            for contrato in contratos_esperados:
                titulo = contrato.get('Titulo', '').strip()
                if titulo:
                    titulos_esperados.add(str(titulo).strip())

            titulos_encontrados = set()
            for contrato_str in contratos_encontrados:
                if "(Título:" in contrato_str:
                    titulo_completo = contrato_str.split("(Título:")[1].split(")")[0].strip()
                    if "/" in titulo_completo:
                        titulo = titulo_completo.split("/")[0].strip()
                    else:
                        titulo = titulo_completo
                    titulos_encontrados.add(str(titulo).strip())

            intersecao = titulos_esperados & titulos_encontrados
            return sorted(list(intersecao))
        except Exception:
            return []

    def _marcar_todos_contratos_tabela(self, titulos_validados: List[str]) -> Dict[str, Any]:
        """Cópia literal do marcador de checkboxes por título."""
        try:
            total_marcados = 0
            total_validados = 0
            tabela = self.find_element(xpath="//table[@id='tabelaAgrupParcelaGrid']")
            if not tabela:
                return {"sucesso": False, "erro": "Tabela de resultados não encontrada"}
            if not titulos_validados:
                return {"sucesso": False, "erro": "Títulos validados são obrigatórios - nenhum título fornecido"}

            linhas = tabela.find_elements(By.XPATH, ".//tbody/tr")
            for linha in linhas:
                try:
                    celulas = linha.find_elements(By.XPATH, ".//td")
                    if len(celulas) >= 3:
                        dados_consolidados = celulas[2].text.strip()
                        if dados_consolidados:
                            partes = dados_consolidados.split(" / ")
                            if len(partes) >= 2:
                                titulo_completo = partes[0].strip()
                                if "/" in titulo_completo:
                                    titulo = titulo_completo.split("/")[0].strip()
                                else:
                                    titulo = titulo_completo
                                if titulo in titulos_validados:
                                    checkbox = linha.find_element(By.XPATH, ".//input[@type='checkbox'][contains(@id, 'flSelecionado_')]")
                                    if not checkbox.is_selected():
                                        checkbox.click()
                                        total_marcados += 1
                                    total_validados += 1
                except Exception:
                    continue

            return {
                "sucesso": True,
                "total_marcados": total_marcados,
                "total_validados": total_validados,
                "total_checkboxes": len(linhas),
            }
        except Exception as e:
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
                    contratos_encontrados = repositorio_contratos_arquivo.framework.find({"Titulo": numero_titulo})
                    if contratos_encontrados:
                        contrato_encontrado = contratos_encontrados[0]
                        contrato_id = contrato_encontrado.get("_id")
                        if contrato_id:
                            repositorio_contratos_arquivo.framework.update(contrato_id, dados_atualizacao)
                            contratos_atualizados += 1
        except Exception as e:
            self.log_erro(f"Erro ao atualizar status para CARNE_GERADO: {str(e)}", e)

    def _extrair_contratos_da_tabela(self) -> List[str]:
        """Extrai strings consolidadas da grid (cópia literal)."""
        try:
            contratos_encontrados: List[str] = []
            tabela = self.find_element(xpath="//table[@id='tabelaAgrupParcelaGrid']")
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
                                contratos_encontrados.append(f"{cliente} (Título: {titulo}) - Data de vencimento: {data_vencimento}")
                except Exception:
                    continue
            return contratos_encontrados
        except Exception:
            return []


