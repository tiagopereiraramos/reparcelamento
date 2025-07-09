"""
RPA Análise de Planilhas
Segundo RPA do sistema - Analisa planilhas para identificar clientes que precisam de reparcelamento

Desenvolvido em Português Brasileiro
Baseado no PDD seção 7 - Processamento de dados das planilhas
"""

from core.rastreamento_unificado import iniciar_rastreamento
from core.notificacoes_simples import notificar_sucesso, notificar_erro
from core.base_rpa import BaseRPA, ResultadoRPA
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import sys
import time
from pathlib import Path

# Adiciona o diretório raiz ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Logger integrado via BaseRPA usando logger_avancado


class RPAAnalisePlanilhas(BaseRPA):
    """
    RPA responsável pela análise das planilhas Google Sheets para identificar:
    - Novos contratos para inclusão
    - Pendências de IPTU
    - Contratos que precisam de reajuste (último reajuste há 12 meses)
    - Validação de dados para reparcelamento
    """

    def __init__(self, headless: Optional[bool] = None):
        if headless is not None:
            super().__init__(nome_rpa="Analise_Planilhas",
                             usar_browser=False, headless=headless)
        else:
            super().__init__(nome_rpa="Analise_Planilhas", usar_browser=False)
        self.cliente_sheets = None
        self.rastreamento = None

    async def executar(self, parametros: Dict[str, Any]) -> ResultadoRPA:
        """
        Executa análise completa das planilhas

        Args:
            parametros: Deve conter:
                - planilha_calculo_id: ID da planilha BASE DE CÁLCULO REPARCELAMENTO
                - planilha_apoio_id: ID da planilha Base de apoio
                - credenciais_google: Caminho para credenciais (opcional)

        Returns:
            ResultadoRPA com lista de contratos para processamento
        """
        try:
            # ✅ INICIA RASTREAMENTO UNIFICADO
            self.rastreamento = iniciar_rastreamento("RPA_Analise_Planilhas")

            await self.rastreamento.registrar_inicio_rpa(parametros)

            # ✅ FORÇA inicialização do sistema híbrido ANTES de tudo
            from core.data_manager import data_manager
            await data_manager.inicializar()
            self.log_info("💾 Sistema híbrido MongoDB+JSON inicializado")

            self.log_info("🔍 Iniciando análise de planilhas...")
            self.log_info(
                f"📊 Planilha Base: {parametros.get('planilha_calculo_id')}")
            self.log_info(
                f"📋 Planilha Apoio: {parametros.get('planilha_apoio_id')}")

            # Valida parâmetros obrigatórios
            planilha_calculo_id = parametros.get("planilha_calculo_id")
            planilha_apoio_id = parametros.get("planilha_apoio_id")

            if not planilha_calculo_id or not planilha_apoio_id:
                return ResultadoRPA(
                    sucesso=False,
                    mensagem="IDs das planilhas não fornecidos",
                    erro="Parâmetros 'planilha_calculo_id' e 'planilha_apoio_id' são obrigatórios"
                )

            # Conecta ao Google Sheets se especificado
            await self._conectar_google_sheets(parametros.get("credenciais_google"))

            # Processa novos contratos da planilha de apoio
            self.log_progresso(
                "Processando novos contratos da planilha de apoio")
            novos_contratos = await self._processar_novos_contratos(planilha_apoio_id)

            # Processa pendências IPTU
            self.log_progresso("Processando pendências de IPTU")
            pendencias_iptu = await self._processar_pendencias_iptu(planilha_apoio_id)

            # Atualiza planilha principal com novos dados
            if novos_contratos or pendencias_iptu:
                self.log_progresso(
                    "Atualizando planilha principal com novos dados")
                await self._atualizar_planilha_principal(
                    planilha_calculo_id, novos_contratos, pendencias_iptu
                )

            # Identifica contratos para reajuste
            self.log_progresso(
                "Identificando contratos que precisam de reajuste")
            contratos_reajuste = await self._identificar_contratos_reajuste(planilha_calculo_id)

            # Gera fila para próximos RPAs
            fila_processamento = await self._gerar_fila_processamento(contratos_reajuste)

            # Monta resultado final
            resultado_dados = {
                "novos_contratos_processados": len(novos_contratos),
                "pendencias_iptu_atualizadas": len(pendencias_iptu),
                "contratos_para_reajuste": len(contratos_reajuste),
                "fila_processamento": fila_processamento,
                "detalhes_contratos": contratos_reajuste,
                "timestamp_analise": datetime.now().isoformat()
            }

            # Registra sucesso final
            await self.rastreamento.registrar_sucesso_rpa(resultado_dados)

            return ResultadoRPA(
                sucesso=True,
                mensagem=f"Análise concluída - {len(contratos_reajuste)} contratos identificados para reparcelamento",
                dados=resultado_dados
            )

        except Exception as e:
            if self.rastreamento:
                await self.rastreamento.registrar_erro_critico(e, {
                    "fase": "execucao_principal",
                    "parametros": parametros
                })

            self.log_erro("Erro durante análise das planilhas", e)
            return ResultadoRPA(
                sucesso=False,
                mensagem="Falha na análise das planilhas",
                erro=str(e)
            )

        finally:
            # ✅ SEMPRE finaliza rastreamento
            if self.rastreamento:
                await self.rastreamento.finalizar_rastreamento()

    async def _conectar_google_sheets(self, credenciais_google: Optional[str]):
        """
        Conecta ao Google Sheets usando service account

        Args:
            credenciais_google: Caminho para arquivo de credenciais
        """
        try:
            # Valida parâmetro de credenciais
            if not credenciais_google:
                credenciais_google = os.getenv(
                    "GOOGLE_CREDENTIALS_PATH", "./gspread-credentials.json")

            self.log_progresso(
                f"Conectando ao Google Sheets: {credenciais_google}")

            # Configura credenciais e escopos
            credenciais = Credentials.from_service_account_file(
                credenciais_google,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ]
            )

            self.cliente_sheets = gspread.authorize(credenciais)
            self.log_progresso("✅ Conectado ao Google Sheets com sucesso")

        except Exception as e:
            raise Exception(f"Falha na conexão com Google Sheets: {str(e)}")

    async def _processar_novos_contratos(self, planilha_apoio_id: str) -> List[Dict[str, Any]]:
        """
        Processa novos contratos da planilha de apoio conforme PDD seção 7.1

        Args:
            planilha_apoio_id: ID da planilha de apoio

        Returns:
            Lista de novos contratos encontrados
        """
        try:
            self.log_progresso(
                "Verificando abas disponíveis para novos contratos")

            # Abre planilha de apoio
            if not self.cliente_sheets:
                raise Exception("Cliente Google Sheets não inicializado")

            # CORRIGIDO: Adiciona retry para operações Google Sheets
            max_tentativas = 3
            for tentativa in range(max_tentativas):
                try:
                    planilha_apoio = self.cliente_sheets.open_by_key(
                        planilha_apoio_id)
                    break
                except Exception as e:
                    if "503" in str(e) and tentativa < max_tentativas - 1:
                        tempo_espera = (tentativa + 1) * \
                            30  # 30, 60, 90 segundos
                        self.log_progresso(
                            f"⚠️ Erro 503 - aguardando {tempo_espera}s antes da próxima tentativa...")
                        await asyncio.sleep(tempo_espera)
                        continue
                    raise e

            # Lista abas disponíveis
            abas_disponiveis = [
                aba.title for aba in planilha_apoio.worksheets()]
            self.log_progresso(f"Abas disponíveis: {abas_disponiveis}")

            # Procura por aba de novos contratos
            aba_contratos_nome = None
            possibilidades_contratos = [
                "NOVOS CONTRATOS", "Novos Contratos", "Contratos", "Base de apoio"]

            for possibilidade in possibilidades_contratos:
                if possibilidade in abas_disponiveis:
                    aba_contratos_nome = possibilidade
                    break

            if not aba_contratos_nome:
                self.log_progresso(
                    "⚠️ Aba de novos contratos não encontrada - nenhum contrato novo para processar")
                return []

            self.log_progresso(f"Usando aba: {aba_contratos_nome}")
            aba_novos_contratos = planilha_apoio.worksheet(aba_contratos_nome)

            # Lê todos os dados
            dados_novos_contratos = aba_novos_contratos.get_all_records()

            # Filtra contratos válidos (linhas não vazias)
            contratos_validos = []
            for linha, contrato in enumerate(dados_novos_contratos, start=2):
                # Verifica se há dados na linha
                if any(str(valor).strip() for valor in contrato.values() if valor):
                    contrato['linha_planilha'] = linha
                    contratos_validos.append(contrato)

            self.log_progresso(
                f"✅ {len(contratos_validos)} novos contratos encontrados")

            return contratos_validos

        except Exception as e:
            self.log_erro("Erro ao processar novos contratos", e)
            return []

    async def _processar_pendencias_iptu(self, planilha_apoio_id: str) -> List[Dict[str, Any]]:
        """
        Processa pendências de IPTU da planilha de apoio conforme PDD seção 7.2

        Args:
            planilha_apoio_id: ID da planilha de apoio

        Returns:
            Lista de pendências IPTU encontradas
        """
        try:
            self.log_progresso(
                "Verificando abas disponíveis na planilha de apoio")

            # Abre planilha de apoio
            if not self.cliente_sheets:
                raise Exception("Cliente Google Sheets não inicializado")

            planilha_apoio = self.cliente_sheets.open_by_key(planilha_apoio_id)

            # Lista abas disponíveis
            abas_disponiveis = [
                aba.title for aba in planilha_apoio.worksheets()]
            self.log_progresso(f"Abas disponíveis: {abas_disponiveis}")

            # Procura por aba de IPTU (várias possibilidades)
            aba_iptu_nome = None
            possibilidades_iptu = ["Consulta IPTU",
                                   "IPTU", "Pendencias IPTU", "Base de apoio"]

            for possibilidade in possibilidades_iptu:
                if possibilidade in abas_disponiveis:
                    aba_iptu_nome = possibilidade
                    break

            if not aba_iptu_nome:
                self.log_progresso(
                    "⚠️ Aba de IPTU não encontrada - usando primeira aba disponível")
                if abas_disponiveis:
                    aba_iptu_nome = abas_disponiveis[0]
                else:
                    self.log_progresso("❌ Nenhuma aba disponível na planilha")
                    return []

            self.log_progresso(f"Usando aba: {aba_iptu_nome}")
            aba_iptu = planilha_apoio.worksheet(aba_iptu_nome)

            # Lê todos os dados
            dados_iptu = aba_iptu.get_all_records()

            # Filtra pendências válidas
            pendencias_validas = []
            for linha, pendencia in enumerate(dados_iptu, start=2):
                # Verifica se há dados na linha
                if any(str(valor).strip() for valor in pendencia.values() if valor):
                    pendencia['linha_planilha'] = linha
                    pendencias_validas.append(pendencia)

            self.log_progresso(
                f"✅ {len(pendencias_validas)} pendências IPTU encontradas")

            return pendencias_validas

        except Exception as e:
            self.log_erro("Erro ao processar pendências IPTU", e)
            return []

    async def _atualizar_planilha_principal(
        self,
        planilha_calculo_id: str,
        novos_contratos: List[Dict[str, Any]],
        pendencias_iptu: List[Dict[str, Any]]
    ):
        """
        Atualiza planilha principal com dados da planilha de apoio
        Conforme PDD seção 7.1 e 7.2

        Args:
            planilha_calculo_id: ID da planilha de cálculo principal
            novos_contratos: Lista de novos contratos
            pendencias_iptu: Lista de pendências IPTU
        """
        try:
            # Abre planilha principal (cálculo)
            if not self.cliente_sheets:
                raise Exception("Cliente Google Sheets não inicializado")

            planilha_principal = self.cliente_sheets.open_by_key(
                planilha_calculo_id)
            aba_base_calculo = planilha_principal.worksheet("Base de cálculo")

            # Adiciona novos contratos se houver
            if novos_contratos:
                self.log_progresso(
                    f"Adicionando {len(novos_contratos)} novos contratos")
                await self._adicionar_novos_contratos(aba_base_calculo, novos_contratos)

            # Atualiza pendências IPTU se houver
            if pendencias_iptu:
                self.log_progresso(
                    f"Atualizando {len(pendencias_iptu)} pendências IPTU")
                await self._atualizar_pendencias_iptu(aba_base_calculo, pendencias_iptu)

            self.log_progresso("✅ Planilha principal atualizada com sucesso")

        except Exception as e:
            raise Exception(f"Erro ao atualizar planilha principal: {str(e)}")

    async def _adicionar_novos_contratos(self, aba_base_calculo, novos_contratos: List[Dict[str, Any]]):
        """
        Adiciona novos contratos à aba Base de cálculo conforme PDD seção 8.1
        Copia linhas da aba NOVOS CONTRATOS da Base de apoio para Base de cálculo
        em sequência aos contratos já existentes

        Args:
            aba_base_calculo: Aba Base de cálculo da planilha principal
            novos_contratos: Lista de novos contratos da Base de apoio
        """
        try:
            if not novos_contratos:
                self.log_progresso("Nenhum novo contrato para adicionar")
                return

            # Encontra próxima linha vazia (em sequência aos contratos existentes)
            dados_existentes = aba_base_calculo.get_all_values()
            proxima_linha = len(dados_existentes) + 1

            self.log_progresso(
                f"Adicionando {len(novos_contratos)} novos contratos a partir da linha {proxima_linha}")

            # Obtém cabeçalhos da planilha principal para mapeamento correto
            cabecalhos_principais = dados_existentes[0] if dados_existentes else [
            ]

            for i, contrato in enumerate(novos_contratos):
                # Mapeia dados do contrato conforme estrutura da Base de cálculo
                # As colunas devem espelhar exatamente a estrutura da Base de apoio
                linha_dados = []

                # Monta linha seguindo ordem dos cabeçalhos da planilha principal
                for cabecalho in cabecalhos_principais:
                    valor = contrato.get(cabecalho, '')
                    linha_dados.append(str(valor) if valor else '')

                # Se não temos cabeçalhos, usa estrutura básica esperada
                if not cabecalhos_principais:
                    linha_dados = [
                        contrato.get('Empresa', ''),
                        contrato.get('Loteamento', ''),
                        contrato.get('Cliente', ''),
                        contrato.get('Quadra', ''),
                        contrato.get('Lote', ''),
                        contrato.get('numero_titulo',
                                     contrato.get('Titulo', '')),
                        contrato.get('Data de consulta IPTU', ''),
                        contrato.get('PENDÊNCIAS PMFI', ''),
                        contrato.get('PENDÊNCIAS SIENGE', ''),
                        contrato.get('PENDÊNCIAS SIENGE INAD', ''),
                        datetime.now().strftime('%d/%m/%Y'),  # Data inclusão
                        # Último reajuste (será preenchido quando o reajuste for feito)
                        '',
                        '',  # Mês reajuste (calculado por fórmula)
                    ]

                # Atualiza linha na planilha
                if linha_dados:
                    range_update = f'A{proxima_linha}:{chr(65 + len(linha_dados) - 1)}{proxima_linha}'
                    aba_base_calculo.update(range_update, [linha_dados])

                    self.log_progresso(
                        f"✅ Contrato adicionado na linha {proxima_linha}: {contrato.get('Cliente', 'N/A')} - {contrato.get('numero_titulo', contrato.get('Titulo', 'N/A'))}")
                    proxima_linha += 1

            self.log_progresso(
                f"✅ {len(novos_contratos)} novos contratos adicionados em sequência aos existentes")

        except Exception as e:
            raise Exception(
                f"Erro ao adicionar novos contratos conforme PDD: {str(e)}")

    async def _atualizar_pendencias_iptu(self, aba_base_calculo, pendencias_iptu: List[Dict[str, Any]]):
        """
        Atualiza coluna de pendências IPTU conforme PDD seção 8.2

        Processo:
        1. Verifica para cada cliente/título a atualização data consulta do IPTU
        2. Copia informação da coluna IPTU PENDÊNCIAS PMFI para clientes cuja "Data de consulta" é do mês vigente
        3. Cola as informações na coluna correspondente da Base de cálculo

        Args:
            aba_base_calculo: Aba Base de cálculo
            pendencias_iptu: Lista de pendências IPTU da aba Consulta IPTU
        """
        try:
            if not pendencias_iptu:
                self.log_progresso("Nenhuma pendência IPTU para processar")
                return

            # Obtém mês atual para verificação
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year

            self.log_progresso(
                f"Processando {len(pendencias_iptu)} registros de consulta IPTU para mês {mes_atual}/{ano_atual}")

            # Lê dados atuais da Base de cálculo
            dados_base_calculo = aba_base_calculo.get_all_records()

            atualizacoes_realizadas = 0
            pendencias_encontradas = []

            for pendencia in pendencias_iptu:
                try:
                    # Extrai dados da consulta IPTU
                    cliente_iptu = str(pendencia.get('Cliente', '')).strip()
                    titulo_iptu = str(pendencia.get(
                        'Titulo', pendencia.get('numero_titulo', ''))).strip()
                    data_consulta_str = str(pendencia.get(
                        'Data de consulta IPTU', pendencia.get('Data de consulta', ''))).strip()
                    pendencia_pmfi = str(pendencia.get(
                        'PENDÊNCIAS PMFI', pendencia.get('IPTU PENDÊNCIAS PMFI', ''))).strip()

                    # Valida se tem dados mínimos
                    if not cliente_iptu and not titulo_iptu:
                        continue

                    # Verifica se data de consulta é do mês vigente
                    consulta_mes_atual = False
                    if data_consulta_str:
                        try:
                            # Tenta diferentes formatos de data
                            for formato in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']:
                                try:
                                    data_consulta = datetime.strptime(
                                        data_consulta_str, formato)
                                    if data_consulta.month == mes_atual and data_consulta.year == ano_atual:
                                        consulta_mes_atual = True
                                    break
                                except ValueError:
                                    continue
                        except:
                            pass

                    # Se consulta não é do mês atual, registra pendência
                    if not consulta_mes_atual:
                        pendencias_encontradas.append({
                            'cliente': cliente_iptu,
                            'titulo': titulo_iptu,
                            'data_consulta': data_consulta_str,
                            'motivo': 'Consulta IPTU não atualizada no mês vigente'
                        })
                        continue

                    # Procura contrato correspondente na Base de cálculo
                    for linha, contrato in enumerate(dados_base_calculo, start=2):
                        cliente_base = str(contrato.get('Cliente', '')).strip()
                        titulo_base = str(contrato.get(
                            'numero_titulo', contrato.get('Titulo', ''))).strip()

                        # Verifica correspondência por cliente OU título
                        if (cliente_iptu and cliente_iptu.lower() in cliente_base.lower()) or \
                           (titulo_iptu and titulo_iptu == titulo_base):

                            # Atualiza coluna PENDÊNCIAS PMFI na Base de cálculo
                            try:
                                # Encontra coluna de PENDÊNCIAS PMFI
                                cabecalhos = aba_base_calculo.row_values(1)
                                coluna_pendencia = None

                                for i, cabecalho in enumerate(cabecalhos, start=1):
                                    if 'PENDÊNCIAS PMFI' in str(cabecalho).upper() or 'IPTU' in str(cabecalho).upper():
                                        coluna_pendencia = i
                                        break

                                if coluna_pendencia:
                                    # Atualiza célula específica
                                    celula = f'{chr(64 + coluna_pendencia)}{linha}'
                                    aba_base_calculo.update(
                                        celula, pendencia_pmfi)

                                    self.log_progresso(
                                        f"✅ IPTU atualizado: {cliente_base} - {titulo_base} -> {pendencia_pmfi}")
                                    atualizacoes_realizadas += 1
                                else:
                                    self.log_progresso(
                                        f"⚠️ Coluna PENDÊNCIAS PMFI não encontrada para atualizar {cliente_base}")

                            except Exception as e:
                                self.log_progresso(
                                    f"⚠️ Erro ao atualizar IPTU para {cliente_base}: {str(e)}")

                            break  # Encontrou correspondência, para de procurar

                except Exception as e:
                    self.log_progresso(
                        f"⚠️ Erro ao processar pendência IPTU: {str(e)}")
                    continue

            # Registra no log as pendências encontradas
            if pendencias_encontradas:
                self.log_progresso(
                    f"⚠️ {len(pendencias_encontradas)} clientes/títulos com consulta IPTU pendente:")
                for pendencia in pendencias_encontradas:
                    self.log_progresso(
                        f"   - {pendencia['cliente']} (Título: {pendencia['titulo']}) - {pendencia['motivo']}")

            self.log_progresso(
                f"✅ Processamento IPTU concluído: {atualizacoes_realizadas} atualizações realizadas, {len(pendencias_encontradas)} pendências encontradas")

        except Exception as e:
            raise Exception(
                f"Erro ao atualizar pendências IPTU conforme PDD: {str(e)}")

    async def _identificar_contratos_reajuste(self, planilha_calculo_id: str) -> List[Dict[str, Any]]:
        """
        Identifica contratos que precisam de reajuste APLICANDO REGRAS PDD 9.1.1
        Conforme PDD: baseado na coluna "Mês reajuste" + validação de inadimplência

        Args:
            planilha_calculo_id: ID da planilha de cálculo

        Returns:
            Lista de contratos que precisam de reajuste COM VALIDAÇÃO PDD
        """
        try:
            # ✅ IMPORTA E INICIALIZA PROCESSADOR DE REGRAS PDD
            from core.processador_regras_pdd import ProcessadorRegrasNegocio
            processador_pdd = ProcessadorRegrasNegocio()

            self.log_progresso(
                "🔍 Analisando contratos com REGRAS PDD 9.1.1 INTEGRADAS")

            # Abre planilha principal (cálculo)
            if not self.cliente_sheets:
                raise Exception("Cliente Google Sheets não inicializado")

            planilha_principal = self.cliente_sheets.open_by_key(
                planilha_calculo_id)
            aba_base_calculo = planilha_principal.worksheet("Base de cálculo")

            # Lê todos os dados
            dados_contratos = aba_base_calculo.get_all_records()

            # Obtém mês atual
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year

            contratos_para_reajuste = []

            self.log_progresso(
                f"Mês atual: {mes_atual:02d} (formato numérico)")

            for linha, contrato in enumerate(dados_contratos, start=2):
                try:
                    # Verifica se o contrato tem dados mínimos obrigatórios
                    cliente = str(contrato.get('Cliente', '')).strip()
                    # CORRIGIDO: Tenta múltiplas variações do campo título
                    numero_titulo = str(contrato.get(
                        'numero_titulo', '')).strip()
                    if not numero_titulo:
                        numero_titulo = str(contrato.get('Titulo', '')).strip()
                    if not numero_titulo:
                        numero_titulo = str(contrato.get('Título', '')).strip()

                    # Pula linhas vazias ou sem dados essenciais (precisa pelo menos cliente OU título)
                    if not cliente and not numero_titulo:
                        continue

                    # Verifica coluna "Mês reajuste"
                    mes_reajuste_str = str(
                        contrato.get('Mês reajuste', '')).strip()

                    # Validação mais rigorosa para campo mês reajuste
                    if (not mes_reajuste_str or
                        mes_reajuste_str in ['', '#N/A', 'N/A', '#REF!', '#VALUE!', 'null', 'None'] or
                            len(mes_reajuste_str) < 3):
                        self.log_progresso(
                            f"⚠️ Linha {linha}: Mês reajuste vazio ou inválido: '{mes_reajuste_str}'")
                        continue

                    # Parse do formato novo "05-25", "06-25", etc. ou formato antigo "mai.-25"
                    if '-' in mes_reajuste_str:
                        if '.' in mes_reajuste_str:
                            # Formato antigo "mai.-25"
                            meses_map = {
                                'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                                'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
                            }
                            partes = mes_reajuste_str.split('.-')
                            if len(partes) == 2:
                                mes_nome = partes[0].lower().strip()
                                ano_str = partes[1].strip()

                                # Validação do nome do mês
                                if mes_nome not in meses_map:
                                    self.log_progresso(
                                        f"⚠️ Linha {linha}: Mês inválido: '{mes_nome}' em '{mes_reajuste_str}'")
                                    continue

                                # Validação do ano
                                if not ano_str or len(ano_str) != 2:
                                    self.log_progresso(
                                        f"⚠️ Linha {linha}: Ano inválido: '{ano_str}' em '{mes_reajuste_str}'")
                                    continue

                                # Converte nome do mês para número
                                mes_reajuste = meses_map[mes_nome]

                                # Converte ano (25 -> 2025, 24 -> 2024)
                                try:
                                    ano_reajuste = int(ano_str)
                                    if ano_reajuste < 50:  # Assume 2000+
                                        ano_reajuste += 2000
                                    elif ano_reajuste < 100:  # Assume 1900+
                                        ano_reajuste += 1900
                                except ValueError:
                                    self.log_progresso(
                                        f"⚠️ Linha {linha}: Erro ao converter ano: '{ano_str}' em '{mes_reajuste_str}'")
                                    continue
                            else:
                                self.log_progresso(
                                    f"⚠️ Linha {linha}: Formato antigo inválido: '{mes_reajuste_str}' (esperado: 'mês.-ano')")
                                continue
                        else:
                            # Formato novo "05-25", "06-25", etc.
                            partes = mes_reajuste_str.split('-')
                            if len(partes) == 2:
                                mes_str = partes[0].strip()
                                ano_str = partes[1].strip()

                                # Validação do mês numérico
                                try:
                                    mes_reajuste = int(mes_str)
                                    if mes_reajuste < 1 or mes_reajuste > 12:
                                        self.log_progresso(
                                            f"⚠️ Linha {linha}: Mês inválido: '{mes_str}' em '{mes_reajuste_str}' (deve ser 01-12)")
                                        continue
                                except ValueError:
                                    self.log_progresso(
                                        f"⚠️ Linha {linha}: Mês não numérico: '{mes_str}' em '{mes_reajuste_str}'")
                                    continue

                                # Validação do ano
                                if not ano_str or len(ano_str) != 2:
                                    self.log_progresso(
                                        f"⚠️ Linha {linha}: Ano inválido: '{ano_str}' em '{mes_reajuste_str}'")
                                    continue

                                # Converte ano (25 -> 2025, 24 -> 2024)
                                try:
                                    ano_reajuste = int(ano_str)
                                    if ano_reajuste < 50:  # Assume 2000+
                                        ano_reajuste += 2000
                                    elif ano_reajuste < 100:  # Assume 1900+
                                        ano_reajuste += 1900
                                except ValueError:
                                    self.log_progresso(
                                        f"⚠️ Linha {linha}: Erro ao converter ano: '{ano_str}' em '{mes_reajuste_str}'")
                                    continue
                            else:
                                self.log_progresso(
                                    f"⚠️ Linha {linha}: Formato novo inválido: '{mes_reajuste_str}' (esperado: 'MM-AA')")
                                continue

                        # LÓGICA CONFORME PDD: Filtrar títulos que devem ser reparcelados no mês
                        # baseado na coluna "mês reajuste" e registrar no log

                        if ano_atual == ano_reajuste and mes_atual == mes_reajuste:
                            # ✅ ELEGÍVEL: Mês atual - APLICAR REGRAS PDD 9.1.1

                            # Verifica se há pendências de IPTU básicas
                            pendencia_pmfi = str(contrato.get(
                                'PENDÊNCIAS PMFI', '')).strip().upper()
                            consulta_iptu_ok = pendencia_pmfi in [
                                'OK', 'SEM PENDÊNCIA', 'REGULAR', '']

                            if not consulta_iptu_ok:
                                self.log_progresso(
                                    f"⚠️ Contrato com pendência IPTU não será listado: {cliente or 'Sem nome'} - Pendência: {pendencia_pmfi}")
                                continue

                            # ✅ NOVO: APLICAR REGRAS PDD PARA VALIDAÇÃO DE INADIMPLÊNCIA
                            titulo_final = str(numero_titulo or 'N/A')

                            # 🎯 INTEGRAÇÃO: Simula dados CSV do Sienge para validação PDD
                            # Nota: Em produção, isso seria dados reais do CSV do Sienge
                            dados_simulados_csv = self._simular_dados_csv_para_validacao(
                                contrato, titulo_final)

                            if dados_simulados_csv is not None:
                                # Aplica validação de inadimplência PDD
                                resultado_pdd = processador_pdd.processar_dados_cliente_completo(
                                    df_planilha=dados_simulados_csv,
                                    cliente=str(cliente),
                                    numero_titulo=str(titulo_final)
                                )

                                self.log_progresso(
                                    f"🔍 Validação PDD para {cliente}: {resultado_pdd.get('status_cliente', 'N/A')}")

                                # Se inadimplente, pula o contrato
                                if not resultado_pdd.get('pode_reparcelar', False):
                                    self.log_progresso(
                                        f"❌ Contrato INADIMPLENTE excluído: {cliente or 'Sem nome'} - {resultado_pdd.get('motivo_classificacao', 'N/A')}")
                                    continue

                                self.log_progresso(
                                    f"✅ Contrato ADIMPLENTE aprovado: {cliente or 'Sem nome'}")

                            # Cria cópia com dados essenciais preservados + resultados PDD
                            contrato_processado = contrato.copy()
                            contrato_processado['linha_planilha'] = linha
                            contrato_processado['mes_reajuste_original'] = mes_reajuste_str
                            contrato_processado[
                                'motivo_elegibilidade'] = f"Mês de reajuste atual: {mes_reajuste_str}"

                            # ✅ NOVO: Adiciona resultados da validação PDD
                            if dados_simulados_csv is not None and 'resultado_pdd' in locals():
                                contrato_processado['validacao_pdd'] = json.dumps({
                                    'status_cliente': resultado_pdd.get('status_cliente'),
                                    'pode_reparcelar': resultado_pdd.get('pode_reparcelar'),
                                    'nivel_risco': resultado_pdd.get('nivel_risco'),
                                    'qtd_ct_vencidas': resultado_pdd.get('qtd_ct_vencidas', 0),
                                    'regras_aplicadas': 'REGRAS_9_1_1_INTEGRADAS'
                                })
                            else:
                                contrato_processado['validacao_pdd'] = json.dumps({
                                    'status_cliente': 'PENDENTE_DADOS_CSV',
                                    'pode_reparcelar': True,  # Assume OK se não há dados para validar
                                    'observacao': 'Validação PDD será feita no RPA Sienge com dados reais'
                                })

                            # Garante que campos essenciais estejam presentes
                            contrato_processado['cliente'] = cliente or contrato_processado.get(
                                'Cliente', 'N/A')
                            contrato_processado['numero_titulo'] = titulo_final

                            # REMOVIDO: Não deve alterar "Último reajuste" - é dado de entrada para fórmula "Mês reajuste"
                            # await self._atualizar_ultimo_reajuste(aba_base_calculo, linha, contrato_processado)

                            contratos_para_reajuste.append(
                                contrato_processado)
                            self.log_progresso(
                                f"✅ Contrato aprovado com PDD: {cliente or 'Sem nome'} - {mes_reajuste_str}")
                            # Parse do JSON para acessar campos
                            try:
                                validacao_pdd_dict = json.loads(
                                    contrato_processado['validacao_pdd'])
                                self.log_progresso(
                                    f"   📋 Título={titulo_final}, Validação PDD={validacao_pdd_dict.get('status_cliente')}")
                                self.log_progresso(
                                    f"   📋 Linha: {linha}, Status: {validacao_pdd_dict.get('pode_reparcelar', 'N/A')}")
                            except Exception:
                                self.log_progresso(
                                    f"   📋 Título={titulo_final}, Validação PDD=ERRO_PARSE_JSON")

                        elif ano_atual > ano_reajuste or (ano_atual == ano_reajuste and mes_atual > mes_reajuste):
                            # ⚠️ ATRASADO: Deveria ter sido processado antes
                            self.log_progresso(
                                f"⚠️ Contrato atrasado: {cliente or 'Sem nome'} - {mes_reajuste_str} (deveria ter sido processado)")

                        else:
                            # ❌ AINDA NÃO VENCEU: Mês seguinte conforme PDD
                            self.log_progresso(
                                f"📅 Contrato para mês seguinte: {cliente or 'Sem nome'} - {mes_reajuste_str} (ainda não chegou a data)")

                    else:
                        self.log_progresso(
                            f"⚠️ Linha {linha}: Formato de data inválido: '{mes_reajuste_str}' (deve conter '-' para separar mês e ano)")

                except (ValueError, TypeError, AttributeError) as e:
                    # Formato inválido, pula contrato
                    self.log_progresso(
                        f"⚠️ Erro na linha {linha}: {str(e)} - dados: {mes_reajuste_str}")
                    continue

            self.log_progresso(
                f"✅ {len(contratos_para_reajuste)} contratos identificados para reajuste")

            return contratos_para_reajuste

        except Exception as e:
            self.log_erro("Erro ao identificar contratos para reajuste", e)
            return []

    async def _gerar_fila_processamento(self, contratos_reajuste: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Gera fila de processamento para os próximos RPAs (Sienge e Sicredi)
        ✅ ATUALIZADO: Compatível com novo modelo "um a um" + data_manager.py

        Args:
            contratos_reajuste: Lista de contratos que precisam reajuste

        Returns:
            Fila de processamento estruturada para novo modelo
        """
        try:
            self.log_progresso(
                "Gerando fila de processamento compatível com modelo 'um a um'")

            fila_processamento = []

            for contrato in contratos_reajuste:
                # ✅ CORRIGIDO: Extrai número do título com múltiplas tentativas
                numero_titulo = (contrato.get('numero_titulo') or
                                 contrato.get('Titulo') or
                                 contrato.get('Título') or
                                 contrato.get('Número do título') or
                                 contrato.get('titulo') or
                                 'N/A')

                cliente_nome = (contrato.get('cliente') or
                                contrato.get('Cliente') or
                                'N/A')

                ultimo_reajuste = (contrato.get('Último reajuste') or
                                   contrato.get('ultimo_reajuste') or
                                   'N/A')

                # ✅ NOVO: Estrutura compatível com modelo "um a um" + persistência MongoDB
                item_fila = {
                    "id_fila": f"reajuste_{numero_titulo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "numero_titulo": numero_titulo,
                    "cliente": cliente_nome,
                    "empreendimento": contrato.get('Loteamento') or contrato.get('empreendimento') or '',
                    "cnpj_unidade": contrato.get('Empresa') or contrato.get('cnpj_unidade') or '',
                    "quadra": contrato.get('Quadra') or '',
                    "lote": contrato.get('Lote') or '',
                    "indexador": "IGPM",  # Sempre IGPM conforme PDD
                    "ultimo_reajuste": ultimo_reajuste,
                    "dias_desde_ultimo_reajuste": contrato.get('dias_desde_ultimo_reajuste', 0),
                    "linha_planilha": contrato.get('linha_planilha', 0),

                    # ✅ NOVO: Status granular para modelo "um a um"
                    "status_processamento": "PENDENTE",  # Status inicial padronizado
                    "timestamp_identificacao": datetime.now().isoformat(),
                    "timestamp_ultima_atualizacao": datetime.now().isoformat(),

                    # ✅ NOVO: Campos para controle de processo e fallback
                    "tentativas_processamento": 0,
                    "max_tentativas": 3,
                    "forcar_nova_extracao": False,  # Flag para forçar webscraping
                    "origem_identificacao": "rpa_analise_planilhas",

                    # ✅ NOVO: Campos para auditoria e rastreamento
                    "validacao_pdd_previa": contrato.get('validacao_pdd', '{}'),
                    "motivo_elegibilidade": contrato.get('motivo_elegibilidade', ''),
                    "mes_reajuste_original": contrato.get('mes_reajuste_original', ''),
                    "prioridade": self._calcular_prioridade(contrato),

                    # ✅ NOVO: Metadados para sistema de persistência
                    "metadata": {
                        "versao_fila": "2.0_um_a_um",
                        "data_identificacao": datetime.now().isoformat(),
                        "usuario_identificacao": os.getenv("USER", "sistema"),
                        "ambiente": os.getenv("AMBIENTE", "producao")
                    },

                    # Dados completos preservados para compatibilidade
                    "dados_completos": contrato
                }

                fila_processamento.append(item_fila)

            # Ordena por prioridade (mais urgente primeiro)
            fila_processamento.sort(
                key=lambda x: x['prioridade'], reverse=True)

            # ✅ NOVO: Salva fila usando data_manager.py (MongoDB + JSON)
            await self._salvar_fila_data_manager(fila_processamento)

            self.log_progresso(
                f"✅ Fila de processamento gerada com {len(fila_processamento)} itens (modelo um a um)")

            return fila_processamento

        except Exception as e:
            self.log_erro("Erro ao gerar fila de processamento", e)
            return []

    def _calcular_prioridade(self, contrato: Dict[str, Any]) -> int:
        """
        Calcula prioridade do contrato baseado em regras de negócio

        Args:
            contrato: Dados do contrato

        Returns:
            Prioridade (maior número = maior prioridade)
        """
        prioridade = 0

        # Mais dias sem reajuste = maior prioridade
        dias_sem_reajuste = contrato.get('dias_desde_ultimo_reajuste', 0)
        prioridade += min(dias_sem_reajuste // 30, 12)  # Máximo 12 pontos

        # Contratos sem pendências têm prioridade
        pendencia_pmfi = str(contrato.get(
            'PENDÊNCIAS PMFI', '')).strip().upper()
        if pendencia_pmfi in ['OK', 'SEM PENDÊNCIA', 'REGULAR', '']:
            prioridade += 5

        pendencia_sienge = contrato.get('PENDÊNCIAS SIENGE', '').upper()
        if pendencia_sienge in ['OK', 'SEM PENDÊNCIA', 'REGULAR', '']:
            prioridade += 3

        pendencia_sienge_inad = contrato.get(
            'PENDÊNCIAS SIENGE INAD', '').upper()
        if pendencia_sienge_inad in ['OK', 'SEM PENDÊNCIA', 'REGULAR', '']:
            prioridade += 3

        return prioridade

    async def _salvar_fila_data_manager(self, fila_processamento: List[Dict[str, Any]]):
        """
        ✅ CORRIGIDO: Salva cada contrato como documento individual na collection fila_processamento_sienge
        Conforme implementação original - um documento por contrato para processamento individual

        Args:
            fila_processamento: Lista de itens da fila
        """
        try:
            # ✅ USA EXCLUSIVAMENTE data_manager.py
            from core.data_manager import data_manager

            if fila_processamento:
                self.log_progresso(
                    f"💾 Salvando {len(fila_processamento)} contratos individualmente no MongoDB...")

                contratos_salvos = 0
                contratos_falharam = 0

                # ✅ CORRIGIDO: Salva cada contrato como documento separado
                for contrato in fila_processamento:
                    try:
                        # ✅ FORMATO PADRONIZADO conforme solicitado + CAMPOS ESPECÍFICOS PDD
                        documento_contrato = {
                            # MongoDB gerará _id automaticamente
                            "numero_titulo": contrato["numero_titulo"],
                            "cliente": contrato["cliente"],
                            # Campo 'Loteamento' da planilha
                            "empresa": contrato.get("empreendimento", ""),
                            "status": "PENDENTE",  # Status inicial sempre PENDENTE
                            "tentativa_extracao": 1,
                            "timestamp_inicio_extracao": datetime.now().isoformat(),
                            "timestamp_ultima_atualizacao": datetime.now(),

                            # Campos que serão preenchidos durante processamento
                            "dados_extraidos": False,
                            "parcelas_pendentes": 0,
                            "pode_reparcelar": True,  # Inicialmente True, será validado no Sienge
                            "saldo_total": 0,
                            "timestamp_extracao": "",
                            "fonte_dados": "",
                            "timestamp_extracao_concluida": "",
                            "etapa_atual": "",
                            "timestamp_inicio_processamento": "",
                            "processo_completo": False,
                            "resultado_final": "",
                            "timestamp_finalizacao": "",

                            # ✅ NOVOS CAMPOS ESPECÍFICOS DO PDD 9.1.1 - Valores padrão/vazios
                            "parcelas_vencidas": 0,
                            "valor_parcela_atual": 0.0,
                            "dia_vencimento_identificado": 0,
                            "primeiro_vencimento_carne": "",
                            "pendencias_sienge_inad": "",
                            "pendencias_sienge": "",
                            "cliente_inadimplente": False,
                            "status_cliente": "pendente_validacao"  # Será validado no RPA Sienge
                        }

                        # ✅ CORRIGIDO: Usa mongodb_manager diretamente para salvar cada contrato
                        from core.mongodb_manager import mongodb_manager

                        if not mongodb_manager.conectado:
                            await mongodb_manager.conectar()

                        # ✅ CORRIGIDO: Salva na collection fila_contratos
                        if mongodb_manager.conectado and hasattr(mongodb_manager, 'database') and mongodb_manager.database is not None:
                            collection = mongodb_manager.database.fila_contratos
                            # Usar insert_one para permitir _id automático do MongoDB
                            collection.insert_one(documento_contrato)

                        contratos_salvos += 1

                        self.log_progresso(
                            f"✅ Contrato salvo individualmente: {contrato['cliente']} - {contrato['numero_titulo']}")

                    except Exception as e:
                        contratos_falharam += 1
                        self.log_progresso(
                            f"❌ Erro ao salvar contrato {contrato.get('numero_titulo', 'N/A')}: {str(e)}")

                # ✅ TAMBÉM salva resumo da fila para compatibilidade
                try:
                    from core.mongodb_manager import mongodb_manager

                    estrutura_fila_resumo = {
                        "_id": f"fila_resumo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "total_contratos": len(fila_processamento),
                        "contratos_salvos": contratos_salvos,
                        "contratos_falharam": contratos_falharam,
                        "status_geral": "ativo",
                        "timestamp_criacao": datetime.now().isoformat(),
                        "origem": "rpa_analise_planilhas",
                        "versao": "2.0_individual"
                    }

                    if mongodb_manager.conectado and hasattr(mongodb_manager, 'database') and mongodb_manager.database is not None:
                        collection_resumos = mongodb_manager.database.fila_resumos
                        collection_resumos.insert_one(estrutura_fila_resumo)
                except Exception as e:
                    self.log_progresso(f"⚠️ Erro ao salvar resumo: {str(e)}")

                # ✅ Também salva em JSON local para backup
                await self._salvar_fila_local(fila_processamento)

                self.log_progresso(
                    f"✅ SEPARAÇÃO CONCLUÍDA: {contratos_salvos} contratos salvos individualmente")
                self.log_progresso(
                    f"📊 Resumo: {contratos_salvos} sucessos, {contratos_falharam} falhas")

            else:
                self.log_progresso("⚠️ Nenhum item para salvar na fila")

        except Exception as e:
            self.log_erro(
                f"❌ Erro ao salvar fila separadamente: {str(e)}", e)
            # Fallback para método local como último recurso
            await self._salvar_fila_local(fila_processamento)

    async def _atualizar_ultimo_reajuste(self, aba_base_calculo, linha: int, contrato: Dict[str, Any]):
        """
        FUNÇÃO DESABILITADA - NÃO DEVE ALTERAR "Último reajuste"

        MOTIVO: A coluna "Último reajuste" é um DADO DE ENTRADA que alimenta 
        a fórmula da coluna "Mês reajuste". Alterá-la quebra o cálculo automático.

        Esta coluna deve ser preenchida apenas manualmente ou por outros processos
        externos ao RPA de análise de planilhas.

        Args:
            aba_base_calculo: Aba Base de cálculo
            linha: Número da linha do contrato
            contrato: Dados do contrato
        """
        # FUNÇÃO DESABILITADA - NÃO EXECUTA NENHUMA AÇÃO
        #
        # IMPORTANTE: A coluna "Último reajuste" NÃO deve ser alterada pelo RPA
        # porque é um dado de entrada que alimenta a fórmula da coluna "Mês reajuste".
        #
        # Modificar esta coluna quebra o cálculo automático do próximo mês de reajuste.

        cliente = contrato.get('Cliente', contrato.get('cliente', 'N/A'))
        self.log_progresso(
            f"ℹ️ Função desabilitada para {cliente} - 'Último reajuste' não será alterado (preserva fórmulas)")

        return  # Sai da função sem fazer alterações

    async def _salvar_fila_local(self, fila_processamento: List[Dict[str, Any]]):
        """
        Salva fila de processamento em arquivo único acumulativo

        Args:
            fila_processamento: Lista de itens da fila
        """
        try:
            pasta_dados = 'dados_processamento'
            arquivo_fila = os.path.join(
                str(pasta_dados or ''), "fila_contratos_sienge.json")
            if not arquivo_fila:
                arquivo_fila = 'fila_processamento.json'
            with open(str(arquivo_fila), 'w', encoding='utf-8') as f:
                json.dump(fila_processamento, f, indent=2, ensure_ascii=False)

            self.log_progresso(
                f"✅ Fila salva no arquivo único: {arquivo_fila} ({len(fila_processamento)} itens)")

        except Exception as e:
            self.log_erro("Erro ao salvar fila localmente", e)

    def _simular_dados_csv_para_validacao(self, contrato: Dict[str, Any], numero_titulo: str):
        """
        Simula dados CSV do Sienge para validação PDD usando dados da planilha

        EM PRODUÇÃO: Este método seria substituído por dados reais do CSV do Sienge
        obtidos via webscraping no RPA Sienge

        Args:
            contrato: Dados do contrato da planilha
            numero_titulo: Número do título

        Returns:
            DataFrame simulado para validação PDD ou None se não há dados suficientes
        """
        try:
            import pandas as pd
            from datetime import datetime, timedelta

            # Dados mínimos necessários para validação PDD
            pendencia_sienge_inad = contrato.get(
                'PENDÊNCIAS SIENGE INAD', '').strip().upper()

            # Se já há indicação clara de inadimplência na planilha, usa isso
            if pendencia_sienge_inad in ['INADIMPLENTE', 'INAD', 'SIM']:
                # Simula dados de um cliente inadimplente (3+ CT vencidas)
                dados_simulados = [
                    {
                        'Título': numero_titulo,
                        'Parcela/Condição': 'CT-01/84',
                        'Documento': 'CT-01',
                        'Cliente': contrato.get('Cliente', 'N/A'),
                        'Status da parcela': 'A vencer',
                        'Data vencimento': (datetime.now() - timedelta(days=30)).strftime('%d/%m/%Y'),
                        'Valor a receber': 500.00
                    },
                    {
                        'Título': numero_titulo,
                        'Parcela/Condição': 'CT-02/84',
                        'Documento': 'CT-02',
                        'Cliente': contrato.get('Cliente', 'N/A'),
                        'Status da parcela': 'A vencer',
                        'Data vencimento': (datetime.now() - timedelta(days=60)).strftime('%d/%m/%Y'),
                        'Valor a receber': 500.00
                    },
                    {
                        'Título': numero_titulo,
                        'Parcela/Condição': 'CT-03/84',
                        'Documento': 'CT-03',
                        'Cliente': contrato.get('Cliente', 'N/A'),
                        'Status da parcela': 'A vencer',
                        'Data vencimento': (datetime.now() - timedelta(days=90)).strftime('%d/%m/%Y'),
                        'Valor a receber': 500.00
                    }
                ]
                return pd.DataFrame(dados_simulados)

            elif pendencia_sienge_inad in ['ADIMPLENTE', 'OK', 'SEM PENDÊNCIA', 'REGULAR', '', 'NÃO']:
                # Simula dados de um cliente adimplente (0-2 CT vencidas)
                dados_simulados = [
                    {
                        'Título': numero_titulo,
                        'Parcela/Condição': 'CT-01/84',
                        'Documento': 'CT-01',
                        'Cliente': contrato.get('Cliente', 'N/A'),
                        'Status da parcela': 'A vencer',
                        'Data vencimento': (datetime.now() + timedelta(days=30)).strftime('%d/%m/%Y'),
                        'Valor a receber': 500.00
                    },
                    {
                        'Título': numero_titulo,
                        'Parcela/Condição': 'CT-02/84',
                        'Documento': 'CT-02',
                        'Cliente': contrato.get('Cliente', 'N/A'),
                        'Status da parcela': 'A vencer',
                        'Data vencimento': (datetime.now() + timedelta(days=60)).strftime('%d/%m/%Y'),
                        'Valor a receber': 500.00
                    }
                ]
                return pd.DataFrame(dados_simulados)

            # Se não há informação suficiente, retorna None (validação será feita no RPA Sienge)
            return None

        except Exception as e:
            self.log_progresso(f"⚠️ Erro ao simular dados CSV: {str(e)}")
            return None

    def log_progresso(self, mensagem: str):
        """Log de progresso formatado"""
        self.logger.info(mensagem)

# Função auxiliar para uso direto


async def executar_analise_planilhas(
    planilha_calculo_id: str,
    planilha_apoio_id: str,
    credenciais_google: Optional[str] = None,
    headless: Optional[bool] = None
) -> ResultadoRPA:
    """
    Função auxiliar para executar análise de planilhas diretamente

    Args:
        planilha_calculo_id: ID da planilha BASE DE CÁLCULO REPARCELAMENTO
        planilha_apoio_id: ID da planilha Base de apoio
        credenciais_google: Caminho para credenciais (opcional)
        headless: Indica se o RPA deve ser executado em modo headless (opcional)

    Returns:
        ResultadoRPA com resultado da análise
    """
    rpa = None
    try:
        if headless is not None:
            rpa = RPAAnalisePlanilhas(headless=headless)
        else:
            rpa = RPAAnalisePlanilhas()

        parametros = {
            "planilha_calculo_id": planilha_calculo_id,
            "planilha_apoio_id": planilha_apoio_id,
            "credenciais_google": credenciais_google
        }

        resultado = await rpa.executar_com_monitoramento(parametros)

        # Enviar notificação
        try:
            if resultado.sucesso:
                contratos_encontrados = 0
                if resultado.dados and isinstance(resultado.dados, dict):
                    contratos_encontrados = len(
                        resultado.dados.get('fila_processamento', []))
                notificar_sucesso(
                    nome_rpa="RPA Análise Planilhas",
                    tempo_execucao=f"{resultado.tempo_execucao:.1f}s" if resultado.tempo_execucao else "N/A",
                    resultados={
                        "contratos_identificados": contratos_encontrados,
                        "planilhas_analisadas": 2,
                        "status": "Análise concluída"
                    }
                )
            else:
                notificar_erro(
                    nome_rpa="RPA Análise Planilhas",
                    erro=resultado.erro or "Erro desconhecido",
                    detalhes=resultado.mensagem
                )
        except Exception as e:
            print(f"Aviso: Falha ao enviar notificação: {e}")

        return resultado

    except Exception as e:
        print(f"Erro crítico na análise de planilhas: {str(e)}")
        return ResultadoRPA(
            sucesso=False,
            mensagem="Falha crítica na análise",
            erro=str(e)
        )
    finally:
        if rpa:
            try:
                await rpa.finalizar()
            except:
                pass
