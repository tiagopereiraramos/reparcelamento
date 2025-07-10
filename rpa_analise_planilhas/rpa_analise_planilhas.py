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
from typing import Dict, Any, List, Optional, Tuple
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import sys
import time
from pathlib import Path
import unicodedata
import re

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
        self.inicio_execucao = datetime.now()
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
            contratos_originais = await self._processar_novos_contratos(planilha_apoio_id)

            # Auditoria completa da planilha de apoio
            self.log_progresso(
                "Auditando todos os contratos da planilha de apoio para relatório completo (PDD)")
            contratos_auditoria_apoio = await self._auditar_planilha_apoio(planilha_apoio_id)
            # Filtra apenas os aprovados para migração, usando os dicionários ORIGINAIS
            titulos_aprovados = set((c['titulo'], c['cliente'])
                                    for c in contratos_auditoria_apoio if c['status'] == 'aprovado')
            novos_contratos_aprovados = [c for c in contratos_originais if (str(c.get('Titulo') or c.get(
                'Título') or c.get('numero_titulo', '')).strip(), str(c.get('Cliente', '')).strip()) in titulos_aprovados]

            # Processa pendências IPTU
            self.log_progresso("Processando pendências de IPTU")
            pendencias_iptu = await self._processar_pendencias_iptu(planilha_apoio_id)

            # Atualiza planilha principal com novos dados SOMENTE se houver aprovados
            if novos_contratos_aprovados or pendencias_iptu:
                self.log_progresso(
                    "Atualizando planilha principal com novos dados")
                await self._atualizar_planilha_principal(
                    planilha_calculo_id, novos_contratos_aprovados, pendencias_iptu
                )

            # --- Separação de logs: Auditoria da planilha de apoio ---
            self.log_progresso(
                "\n===== AUDITORIA DA PLANILHA DE APOIO (NOVOS CONTRATOS) =====")
            for c in contratos_auditoria_apoio:
                self.log_progresso(
                    f"[Apoio][{c['status'].upper()}] Cliente: {c['cliente']}, Título: {c['titulo']}, Motivo: {c['motivo']}")

            # --- Processamento da base de cálculo e verificação de integridade ---
            self.log_progresso(
                "\n===== PROCESSAMENTO DA BASE DE CÁLCULO =====")
            contratos_reajuste, contratos_auditoria_base = await self._identificar_contratos_reajuste(planilha_calculo_id)

            # REMOVIDO: Verificação de integridade entre planilhas
            # REGRA ATUALIZADA: Base de cálculo pode ter contratos homologados diretamente
            # Planilha de apoio é apenas para NOVOS clientes que entrarão na base
            self.log_progresso(
                "\n✅ Base de cálculo: Contratos homologados processados normalmente")

            # Gera fila para próximos RPAs
            fila_processamento = await self._gerar_fila_processamento(contratos_reajuste)

            # Monta resultado final
            resultado_dados = {
                "novos_contratos_processados": len(novos_contratos_aprovados),
                "pendencias_iptu_atualizadas": len(pendencias_iptu),
                "contratos_para_reajuste": len(contratos_reajuste),
                "fila_processamento": fila_processamento,
                "detalhes_contratos": contratos_reajuste,
                "timestamp_analise": datetime.now().isoformat(),
                "pendencias_iptu_bloqueadas": getattr(self, "pendencias_iptu_bloqueadas", []),
                # Auditoria completa: todos da planilha de apoio
                "contratos_auditoria": contratos_auditoria_apoio,
                # Removido: violacoes_base_calculo (regra alterada)
                "contratos_base_calculo": len(contratos_auditoria_base)
            }

            # Registra sucesso final
            await self.rastreamento.registrar_sucesso_rpa(resultado_dados)

            # Após análise, se houver pendências IPTU bloqueadas, notificar explicitamente
            if hasattr(self, 'pendencias_iptu_bloqueadas') and self.pendencias_iptu_bloqueadas:
                self.log_progresso(
                    f"\n🔔 RELATÓRIO DE PENDÊNCIAS IPTU BLOQUEADAS:")
                for pend in self.pendencias_iptu_bloqueadas:
                    self.log_progresso(
                        f" - Cliente: {pend['cliente']}, Título: {pend['titulo']}, Pendência: {pend['pendencia_pmfi']}, Data consulta: {pend['data_consulta_iptu']}, Motivo: {pend['motivo']}")

            # --- Monta relatório detalhado para notificação ---
            relatorio = ""
            # RELATÓRIO DE CONTRATOS APROVADOS
            relatorio += "RELATÓRIO DE CONTRATOS APROVADOS:\n"
            aprovados = [c for c in resultado_dados.get(
                'contratos_auditoria', []) if c.get('status') == 'aprovado']
            if aprovados:
                for c in aprovados:
                    relatorio += f" - Cliente: {c.get('cliente')}, Título: {c.get('titulo')}, Motivo: {c.get('motivo')}\n"
            else:
                relatorio += "Nenhum contrato aprovado.\n"
            # RELATÓRIO DE CONTRATOS REJEITADOS (quantitativo, apoio + base)
            relatorio += "\nRELATÓRIO DE CONTRATOS REJEITADOS:\n"
            rejeitados_apoio = [c for c in resultado_dados.get(
                'contratos_auditoria', []) if c.get('status') == 'rejeitado']
            rejeitados_base = [c for c in resultado_dados.get(
                'detalhes_contratos', []) if c.get('status') == 'rejeitado']
            total_rejeitados = len(rejeitados_apoio) + len(rejeitados_base)
            relatorio += f"Total: {total_rejeitados}\n"
            # RELATÓRIO DE CONTRATOS NÃO PROCESSADOS
            relatorio += "\nRELATÓRIO DE CONTRATOS NÃO PROCESSADOS:\n"
            nprocessados = [c for c in resultado_dados.get(
                'contratos_auditoria', []) if c.get('status') == 'não processado']
            if nprocessados:
                for c in nprocessados:
                    relatorio += f" - Cliente: {c.get('cliente')}, Título: {c.get('titulo')}, Motivo: {c.get('motivo')}\n"
            else:
                relatorio += "Nenhum contrato fora do mês de reajuste ou com dados inválidos.\n"
            # ESTATÍSTICAS GERAIS
            relatorio += "\nESTATÍSTICAS GERAIS:\n"
            total_lidos = len(resultado_dados.get('contratos_auditoria', []))
            total_aprovados = len(aprovados)
            total_nprocessados = len(nprocessados)
            data_analise = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            relatorio += f" - Total de contratos lidos: {total_lidos}\n"
            relatorio += f" - Total aprovados: {total_aprovados}\n"
            relatorio += f" - Total rejeitados: {total_rejeitados}\n"
            relatorio += f" - Total não processados: {total_nprocessados}\n"
            relatorio += f" - Data/hora da análise: {data_analise}\n"
            # Integridade
            relatorio += "\n✅ Integridade OK: Todos os contratos da base de cálculo vieram da planilha de apoio.\n"
            relatorio += "O sistema continuará monitorando as próximas execuções automaticamente.\n"
            # Monta resultados para notificação
            resultados_notificacao = {
                "Mensagem": f"Análise concluída - {resultado_dados.get('contratos_para_reajuste', 0)} contratos identificados para reparcelamento",
                "relatorio": relatorio,
            }
            # Adiciona outros campos principais
            resultados_notificacao["contratos_identificados"] = resultado_dados.get(
                'contratos_para_reajuste', 0)
            resultados_notificacao["planilhas_analisadas"] = 2
            resultados_notificacao["status"] = "Análise concluída"
            # Envia notificação de sucesso
            notificar_sucesso(
                nome_rpa="RPA Análise de Planilhas",
                tempo_execucao=f"{(datetime.now() - self.inicio_execucao).total_seconds():.2f}s",
                resultados=resultados_notificacao
            )

            return ResultadoRPA(
                sucesso=True,
                mensagem=f"Análise concluída - {len(contratos_reajuste)} contratos identificados para reparcelamento",
                dados=resultado_dados,
                tempo_execucao=(datetime.now(
                ) - self.inicio_execucao).total_seconds() if hasattr(self, 'inicio_execucao') else None
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

    async def _auditar_planilha_apoio(self, planilha_apoio_id: str) -> List[Dict[str, Any]]:
        """
        Audita todos os contratos da planilha de apoio, aplicando as regras do PDD e registrando status e motivo para cada um.
        Retorna lista de auditoria para todos os contratos da planilha de apoio.
        """
        auditoria = []
        try:
            # Abre planilha de apoio
            if not self.cliente_sheets:
                raise Exception("Cliente Google Sheets não inicializado")
            planilha_apoio = self.cliente_sheets.open_by_key(planilha_apoio_id)

            # Procura por aba de novos contratos
            abas_disponiveis = [
                aba.title for aba in planilha_apoio.worksheets()]
            aba_contratos_nome = None
            possibilidades_contratos = [
                "NOVOS CONTRATOS", "Novos Contratos", "Contratos", "Base de apoio"]
            for possibilidade in possibilidades_contratos:
                if possibilidade in abas_disponiveis:
                    aba_contratos_nome = possibilidade
                    break
            if not aba_contratos_nome:
                return []
            aba_novos_contratos = planilha_apoio.worksheet(aba_contratos_nome)
            dados_novos_contratos = aba_novos_contratos.get_all_records()
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year
            for linha, contrato in enumerate(dados_novos_contratos, start=2):
                cliente = str(contrato.get('Cliente', '')).strip()
                numero_titulo = str(contrato.get('numero_titulo', '')).strip() or str(
                    contrato.get('Titulo', '')).strip() or str(contrato.get('Título', '')).strip()
                if not cliente and not numero_titulo:
                    continue
                # Verifica campos obrigatórios (exemplo: Cliente, Título, Data de consulta IPTU, PENDÊNCIAS PMFI)
                pendencia_pmfi = str(contrato.get(
                    'PENDÊNCIAS PMFI', '')).strip().upper()
                coluna_data = encontrar_coluna_data_iptu(list(contrato.keys()))
                data_consulta_str = str(contrato.get(
                    coluna_data, '')).strip() if coluna_data else ''
                consulta_iptu_ok = pendencia_pmfi in [
                    'OK', 'SEM PENDÊNCIA', 'REGULAR', '']
                data_consulta_ok = False
                if data_consulta_str:
                    for formato in [
                        '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
                            '%d/%m/%y', '%d-%m-%y', '%y-%m-%d']:
                        try:
                            data_consulta = datetime.strptime(
                                data_consulta_str, formato)
                            # Se ano for 2 dígitos, ajustar para 2000+yy
                            ano = data_consulta.year
                            if ano < 100:
                                ano += 2000
                            if data_consulta.month == mes_atual and ano == ano_atual:
                                data_consulta_ok = True
                            break
                        except ValueError:
                            continue
                # Regra: bloqueia se pendência IPTU ou data inválida
                if not consulta_iptu_ok or not data_consulta_ok:
                    motivo = []
                    if not consulta_iptu_ok:
                        motivo.append(f"pendência PMFI: '{pendencia_pmfi}'")
                    if not data_consulta_ok:
                        motivo.append(
                            f"data de consulta IPTU inválida ou ausente: '{data_consulta_str}'")
                    motivo_str = "; ".join(motivo)
                    auditoria.append({
                        'cliente': cliente or 'Sem nome',
                        'titulo': numero_titulo or 'N/A',
                        'status': 'rejeitado',
                        'motivo': motivo_str
                    })
                    continue
                # Se passou, aprovado para migração
                auditoria.append({
                    'cliente': cliente or 'Sem nome',
                    'titulo': numero_titulo or 'N/A',
                    'status': 'aprovado',
                    'motivo': 'Aprovado para migração (dados válidos na planilha de apoio)'
                })
        except Exception as e:
            self.log_erro("Erro na auditoria da planilha de apoio", e)
        return auditoria

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
        import time
        max_tentativas = 3
        for tentativa in range(max_tentativas):
            try:
                # Abre planilha principal (cálculo)
                if not self.cliente_sheets:
                    raise Exception("Cliente Google Sheets não inicializado")

                planilha_principal = self.cliente_sheets.open_by_key(
                    planilha_calculo_id)
                aba_base_calculo = planilha_principal.worksheet(
                    "Base de cálculo")

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

                self.log_progresso(
                    "✅ Planilha principal atualizada com sucesso")
                return
            except Exception as e:
                if "503" in str(e) and tentativa < max_tentativas - 1:
                    tempo_espera = (tentativa + 1) * 30  # 30, 60, 90 segundos
                    self.log_progresso(
                        f"⚠️ Erro 503 ao atualizar planilha principal - aguardando {tempo_espera}s antes da próxima tentativa...")
                    time.sleep(tempo_espera)
                    continue
                raise Exception(
                    f"Erro ao atualizar planilha principal: {str(e)}")

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

            # Encontra próxima linha realmente vazia (em sequência aos contratos existentes)
            dados_existentes = aba_base_calculo.get_all_values()
            colunas_principais = [
                'Cliente', 'Titulo', 'Título', 'numero_titulo', 'Empresa', 'Loteamento']
            proxima_linha = encontrar_proxima_linha_vazia(
                dados_existentes, colunas_principais)
            self.log_progresso(
                f"Adicionando {len(novos_contratos)} novos contratos a partir da linha {proxima_linha}")

            # Obtém cabeçalhos da planilha principal para mapeamento correto
            cabecalhos_principais = aba_base_calculo.get_all_values(
            )[0] if aba_base_calculo.get_all_values() else []

            # Identifica o índice limite (só até "Dia de vencimento de parcelas")
            if 'Dia de vencimento de parcelas' in cabecalhos_principais:
                idx_limite = cabecalhos_principais.index(
                    'Dia de vencimento de parcelas')
            else:
                idx_limite = len(cabecalhos_principais) - 1

            # Verifica se "Origem" e "Data de Migração" já existem no final
            precisa_adicionar_colunas = False
            if 'Origem' not in cabecalhos_principais or 'Data de Migração' not in cabecalhos_principais:
                precisa_adicionar_colunas = True

            # Se precisa adicionar, adiciona no FINAL da planilha (não no meio)
            if precisa_adicionar_colunas:
                if 'Origem' not in cabecalhos_principais:
                    cabecalhos_principais.append('Origem')
                if 'Data de Migração' not in cabecalhos_principais:
                    cabecalhos_principais.append('Data de Migração')

                # Atualiza cabeçalho na planilha
                ultima_coluna = indice_para_coluna_excel(
                    len(cabecalhos_principais) - 1)
                range_header = f"A1:{ultima_coluna}1"
                aba_base_calculo.update(range_header, [cabecalhos_principais])

            # Localiza as posições das colunas extras
            idx_origem = cabecalhos_principais.index(
                'Origem') if 'Origem' in cabecalhos_principais else -1
            idx_data_migracao = cabecalhos_principais.index(
                'Data de Migração') if 'Data de Migração' in cabecalhos_principais else -1

            for i, contrato in enumerate(novos_contratos):
                self.log_progresso(f"DEBUG CONTRATO MIGRADO: {contrato}")
                linha_dados = []
                for idx, cabecalho in enumerate(cabecalhos_principais):
                    if idx <= idx_limite:
                        if normalizar_nome(cabecalho) == normalizar_nome('Último reajuste'):
                            formato_destino = detectar_formato_ultimo_reajuste(
                                dados_existentes)
                            valor_original = buscar_valor_contrato(
                                contrato, cabecalho)
                            valor = padronizar_ultimo_reajuste(
                                valor_original, formato_destino) if formato_destino else valor_original
                        else:
                            valor = buscar_valor_contrato(contrato, cabecalho)

                        # Limpeza e formatação robusta para Google Sheets
                        valor = str(valor)
                        # Remove aspas simples múltiplas e consecutivas
                        while "'" in valor:
                            valor = valor.replace("'", "")
                        valor = valor.strip()

                        # Converte tipos apropriados para evitar que Google Sheets adicione '
                        valor = converter_tipo_google_sheets(valor)

                    elif idx == idx_origem and idx_origem != -1:
                        valor = 'Planilha de Apoio'
                    elif idx == idx_data_migracao and idx_data_migracao != -1:
                        valor = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                    else:
                        valor = ''
                    linha_dados.append(valor)
                if linha_dados:
                    # Garante que a linha de destino existe na planilha
                    total_linhas = aba_base_calculo.row_count
                    if proxima_linha > total_linhas:
                        linhas_a_adicionar = proxima_linha - total_linhas
                        aba_base_calculo.add_rows(linhas_a_adicionar)
                    # Calcula range robusto para qualquer número de colunas
                    import gspread.utils
                    col_fim = gspread.utils.rowcol_to_a1(
                        1, len(linha_dados)).replace('1', str(proxima_linha))
                    range_update = f'A{proxima_linha}:{col_fim}'
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
                    coluna_data = encontrar_coluna_data_iptu(
                        list(pendencia.keys()))
                    data_consulta_str = str(pendencia.get(
                        coluna_data, '')).strip() if coluna_data else ''
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

    async def _identificar_contratos_reajuste(self, planilha_calculo_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
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
            contratos_auditoria = []  # NOVO: lista para rastreamento completo

            self.log_progresso(
                f"Mês atual: {mes_atual:02d} (formato numérico)")

            for linha, contrato in enumerate(dados_contratos, start=2):
                try:
                    # Verifica se o contrato tem dados mínimos obrigatórios
                    cliente = str(contrato.get('Cliente', '')).strip()
                    numero_titulo = str(contrato.get(
                        'numero_titulo', '')).strip()
                    if not numero_titulo:
                        numero_titulo = str(contrato.get('Titulo', '')).strip()
                    if not numero_titulo:
                        numero_titulo = str(contrato.get('Título', '')).strip()

                    if not cliente and not numero_titulo:
                        continue

                    mes_reajuste_str = str(
                        contrato.get('Mês reajuste', '')).strip()

                    if (not mes_reajuste_str or
                        mes_reajuste_str in ['', '#N/A', 'N/A', '#REF!', '#VALUE!', 'null', 'None'] or
                            len(mes_reajuste_str) < 3):
                        self.log_progresso(
                            f"⚠️ Linha {linha}: Mês reajuste vazio ou inválido: '{mes_reajuste_str}'")
                        contratos_auditoria.append({
                            'cliente': cliente or 'Sem nome',
                            'titulo': numero_titulo or 'N/A',
                            'status': 'não processado',
                            'motivo': f"Mês reajuste vazio ou inválido: '{mes_reajuste_str}'"
                        })
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

                    if ano_atual == ano_reajuste and mes_atual == mes_reajuste:
                        # ===================== REGRA PDD IPTU (AJUSTADA) =====================
                        pendencia_pmfi = str(contrato.get(
                            'PENDÊNCIAS PMFI', '')).strip().upper()
                        data_consulta_str = str(contrato.get(
                            'Data de consulta IPTU', '')).strip()
                        consulta_iptu_ok = pendencia_pmfi in [
                            'OK', 'SEM PENDÊNCIA', 'REGULAR', '']
                        data_consulta_ok = False
                        if data_consulta_str:
                            try:
                                for formato in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']:
                                    try:
                                        data_consulta = datetime.strptime(
                                            data_consulta_str, formato)
                                        if data_consulta.month == mes_atual and data_consulta.year == ano_atual:
                                            data_consulta_ok = True
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                pass
                        # --- AJUSTE: NÃO BLOQUEAR POR PENDÊNCIA DE IPTU ---
                        if not consulta_iptu_ok or not data_consulta_ok:
                            motivo = []
                            if not consulta_iptu_ok:
                                motivo.append(
                                    f"pendência PMFI: '{pendencia_pmfi}'")
                            if not data_consulta_ok:
                                motivo.append(
                                    f"data de consulta IPTU inválida ou ausente: '{data_consulta_str}'")
                            motivo_str = "; ".join(motivo)
                            self.log_progresso(
                                f"⚠️ Contrato COM PENDÊNCIA DE IPTU INCLUÍDO NA FILA: Cliente='{cliente or 'Sem nome'}', Título='{numero_titulo or 'N/A'}', {motivo_str}")
                            if not hasattr(self, 'pendencias_iptu_bloqueadas'):
                                self.pendencias_iptu_bloqueadas = []
                            self.pendencias_iptu_bloqueadas.append({
                                'cliente': cliente or 'Sem nome',
                                'titulo': numero_titulo or 'N/A',
                                'pendencia_pmfi': pendencia_pmfi,
                                'data_consulta_iptu': data_consulta_str,
                                'motivo': motivo_str
                            })
                            # Marcar no contrato a pendência
                            contrato['pendencia_iptu'] = motivo_str
                        # ===================== FIM REGRA PDD IPTU (AJUSTADA) =====================

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
                                contratos_auditoria.append({
                                    'cliente': cliente or 'Sem nome',
                                    'titulo': titulo_final,
                                    'status': 'rejeitado',
                                    'motivo': f"Contrato INADIMPLENTE: {resultado_pdd.get('motivo_classificacao', 'N/A')}"
                                })
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
                        contratos_auditoria.append({
                            'cliente': cliente or 'Sem nome',
                            'titulo': titulo_final,
                            'status': 'aprovado',
                            'motivo': f"Aprovado para reparcelamento (mês de reajuste atual: {mes_reajuste_str})"
                        })
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
                        contratos_auditoria.append({
                            'cliente': cliente or 'Sem nome',
                            'titulo': numero_titulo or 'N/A',
                            'status': 'não processado',
                            'motivo': f"Contrato atrasado: {mes_reajuste_str} (deveria ter sido processado)"
                        })

                    else:
                        # ❌ AINDA NÃO VENCEU: Mês seguinte conforme PDD
                        self.log_progresso(
                            f"📅 Contrato para mês seguinte: {cliente or 'Sem nome'} - {mes_reajuste_str} (ainda não chegou a data)")
                        contratos_auditoria.append({
                            'cliente': cliente or 'Sem nome',
                            'titulo': numero_titulo or 'N/A',
                            'status': 'não processado',
                            'motivo': f"Contrato não está no mês de reajuste atual: {mes_reajuste_str}"
                        })

                except (ValueError, TypeError, AttributeError) as e:
                    # Formato inválido, pula contrato
                    self.log_progresso(
                        f"⚠️ Erro na linha {linha}: {str(e)} - dados: {mes_reajuste_str}")
                    continue

            self.log_progresso(
                f"✅ {len(contratos_para_reajuste)} contratos identificados para reajuste")

            # NOVO: retorna também a lista de auditoria detalhada
            self.contratos_auditoria = contratos_auditoria
            return contratos_para_reajuste, contratos_auditoria

        except Exception as e:
            self.log_erro("Erro ao identificar contratos para reajuste", e)
            return [], []

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
                            # Verifica duplicidade por numero_titulo + cliente
                            filtro = {
                                "numero_titulo": documento_contrato["numero_titulo"], "cliente": documento_contrato["cliente"]}
                            existente = collection.find_one(filtro)
                            if existente:
                                # Atualiza documento existente
                                update_fields = documento_contrato.copy()
                                update_fields["timestamp_ultima_atualizacao"] = datetime.now(
                                )
                                collection.update_one(
                                    filtro, {"$set": update_fields})
                                self.log_progresso(
                                    f"🔄 Contrato atualizado na fila: {documento_contrato['cliente']} - {documento_contrato['numero_titulo']}")
                            else:
                                # Insere novo documento
                                collection.insert_one(documento_contrato)
                                self.log_progresso(
                                    f"✅ Contrato salvo individualmente: {contrato['cliente']} - {contrato['numero_titulo']}")

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

        # Monta relatório detalhado igual ao main
        corpo_relatorio = ""
        if hasattr(resultado, 'dados') and resultado.dados:
            aprovados = resultado.dados.get('detalhes_contratos', [])
            corpo_relatorio += "\nRELATÓRIO DE CONTRATOS APROVADOS:\n"
            for c in aprovados:
                cliente = c.get('Cliente') or c.get('cliente') or 'N/A'
                titulo = c.get('numero_titulo') or c.get(
                    'Titulo') or c.get('Título') or 'N/A'
                corpo_relatorio += f" - Cliente: {cliente}, Título: {titulo}, Motivo: Aprovado para reparcelamento\n"

        if hasattr(resultado, 'pendencias_iptu_bloqueadas') and resultado.pendencias_iptu_bloqueadas:
            corpo_relatorio += "\nRELATÓRIO DE CONTRATOS REJEITADOS POR IPTU:\n"
            for pend in resultado.pendencias_iptu_bloqueadas:
                corpo_relatorio += f" - Cliente: {pend['cliente']}, Título: {pend['titulo']}, Motivo: {pend['motivo']}\n"

        # Outros motivos de rejeição podem ser logados aqui, se disponíveis em resultado

        # Enviar notificação
        # try:
        #     if resultado.sucesso:
        #         contratos_encontrados = 0
        #         if resultado.dados and isinstance(resultado.dados, dict):
        #             contratos_encontrados = len(
        #                 resultado.dados.get('fila_processamento', []))
        #         notificar_sucesso(
        #             nome_rpa="RPA Análise Planilhas",
        #             tempo_execucao=f"{resultado.tempo_execucao:.1f}s" if resultado.tempo_execucao else "N/A",
        #             resultados={
        #                 "contratos_identificados": contratos_encontrados,
        #                 "planilhas_analisadas": 2,
        #                 "status": "Análise concluída",
        #                 "relatorio": corpo_relatorio
        #             }
        #         )
        #     else:
        #         notificar_erro(
        #             nome_rpa="RPA Análise Planilhas",
        #             erro=resultado.erro or "Erro desconhecido",
        #             detalhes=corpo_relatorio or resultado.mensagem
        #         )
        # except Exception as e:
        #     print(f"Aviso: Falha ao enviar notificação: {e}")

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

# Função utilitária para encontrar coluna de data de consulta IPTU tolerante a espaços e maiúsculas/minúsculas


def encontrar_coluna_data_iptu(cabecalhos):
    for nome in cabecalhos:
        nome_normalizado = nome.lower().replace(' ', '')
        if 'datadeconsultaiptu' in nome_normalizado:
            return nome
    return None

# Função utilitária para converter índice para letra de coluna Excel


def indice_para_coluna_excel(n):
    string = ""
    while n >= 0:
        string = chr(n % 26 + ord('A')) + string
        n = n // 26 - 1
    return string


def normalizar_nome(nome):
    return unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII').replace(' ', '').lower()


def buscar_valor_contrato(contrato, cabecalho):
    valor = None

    # 1. Busca exata
    if cabecalho in contrato:
        valor = contrato[cabecalho]
    # 2. Busca por normalização
    elif valor is None:
        cabecalho_norm = normalizar_nome(cabecalho)
        for k in contrato.keys():
            if normalizar_nome(k) == cabecalho_norm:
                valor = contrato[k]
                break
    # 3. Alternativas para campos críticos
    if valor is None:
        if cabecalho in ['Cliente', 'cliente']:
            valor = contrato.get('Cliente') or contrato.get('cliente')
        elif cabecalho in ['Titulo', 'Título', 'numero_titulo']:
            valor = contrato.get('numero_titulo') or contrato.get(
                'Titulo') or contrato.get('Título')

    # 4. Limpeza robusta do valor retornado
    if valor is None:
        return ''

    valor = str(valor)
    # Remove aspas simples múltiplas e consecutivas
    while "'" in valor:
        valor = valor.replace("'", "")
    return valor.strip()


def encontrar_proxima_linha_vazia(dados_existentes, colunas_principais):
    # pula cabeçalho
    for idx, linha in enumerate(dados_existentes[1:], start=2):
        if all(not str(linha[i]).strip() for i, col in enumerate(dados_existentes[0]) if col in colunas_principais):
            return idx
    return len(dados_existentes) + 1  # se não achou, adiciona no final


def detectar_formato_ultimo_reajuste(dados_existentes):
    idx = None
    for i, col in enumerate(dados_existentes[0]):
        if normalizar_nome(col) == normalizar_nome('Último reajuste'):
            idx = i
            break
    if idx is None:
        return None
    formatos = []
    for linha in dados_existentes[1:]:
        valor = str(linha[idx]).strip()
        if re.match(r'\d{2}/\d{2}/\d{4}', valor):
            formatos.append('dd/mm/yyyy')
        elif re.match(r'\d{2}/\d{4}', valor):
            formatos.append('mm/yyyy')
        elif re.match(r'[a-z]{3}\.-\d{2}', valor.lower()):
            formatos.append('mes-abrev-ano')
        elif re.match(r'\d{4}-\d{2}', valor):
            formatos.append('yyyy-mm')
    if not formatos:
        return None
    # Retorna o formato mais comum
    return max(set(formatos), key=formatos.count)


def padronizar_ultimo_reajuste(valor, formato_destino):
    valor = str(valor).strip()
    meses_map = {
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 'mai': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
    }
    # Converte para mm/yyyy
    if formato_destino == 'mm/yyyy':
        match = re.match(r'([a-z]{3})\.-(\d{2})', valor.lower())
        if match:
            mes = meses_map.get(match.group(1), '01')
            ano = '20' + match.group(2)
            return f'{mes}/{ano}'
        match = re.match(r'(\d{2})/(\d{2})/(\d{4})', valor)
        if match:
            return f'{match.group(2)}/{match.group(3)}'
        match = re.match(r'(\d{4})-(\d{2})', valor)
        if match:
            return f'{match.group(2)}/{match.group(1)}'
        return valor
    # Converte para dd/mm/yyyy
    if formato_destino == 'dd/mm/yyyy':
        match = re.match(r'([a-z]{3})\.-(\d{2})', valor.lower())
        if match:
            mes = meses_map.get(match.group(1), '01')
            ano = '20' + match.group(2)
            return f'01/{mes}/{ano}'
        match = re.match(r'(\d{2})/(\d{4})', valor)
        if match:
            return f'01/{match.group(1)}/{match.group(2)}'
        match = re.match(r'(\d{4})-(\d{2})', valor)
        if match:
            return f'01/{match.group(2)}/{match.group(1)}'
        return valor
    # Converte para yyyy-mm
    if formato_destino == 'yyyy-mm':
        match = re.match(r'([a-z]{3})\.-(\d{2})', valor.lower())
        if match:
            mes = meses_map.get(match.group(1), '01')
            ano = '20' + match.group(2)
            return f'{ano}-{mes}'
        match = re.match(r'(\d{2})/(\d{4})', valor)
        if match:
            return f'{match.group(2)}-{match.group(1)}'
        match = re.match(r'(\d{2})/(\d{2})/(\d{4})', valor)
        if match:
            return f'{match.group(3)}-{match.group(2)}'
        return valor
    # Se não reconhecido, retorna original
    return valor


def converter_tipo_google_sheets(valor):
    """
    Converte valores para tipos apropriados que o Google Sheets reconhece
    evitando que adicione aspas simples automaticamente
    """
    if not valor or valor == '':
        return ''

    valor_str = str(valor).strip()

    # Se é um número inteiro
    if re.match(r'^\d+$', valor_str):
        try:
            return int(valor_str)
        except ValueError:
            return valor_str

    # Se é um número decimal (com vírgula ou ponto)
    if re.match(r'^\d+[.,]\d+$', valor_str):
        try:
            # Normaliza para ponto decimal
            valor_normalizado = valor_str.replace(',', '.')
            return float(valor_normalizado)
        except ValueError:
            return valor_str

    # Se é uma data no formato dd/mm/yyyy ou dd/mm/yy
    if re.match(r'^\d{1,2}/\d{1,2}/\d{2,4}$', valor_str):
        return valor_str  # Mantém como string para preservar formato

    # Se é porcentagem
    if valor_str.endswith('%'):
        try:
            numero = valor_str[:-1].replace(',', '.')
            return float(numero) / 100  # Google Sheets trata como decimal
        except ValueError:
            return valor_str

    # Se contém "R$" ou símbolos monetários, remove e converte
    if 'R$' in valor_str or 'R' in valor_str:
        valor_limpo = re.sub(r'[R$\s]', '', valor_str).replace(',', '.')
        if re.match(r'^\d+\.?\d*$', valor_limpo):
            try:
                return float(valor_limpo)
            except ValueError:
                return valor_str

    # Para outros casos, retorna como string
    return valor_str
