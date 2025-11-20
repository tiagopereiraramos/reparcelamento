"""
RPA Análise de Planilhas
Segundo RPA do sistema - Analisa planilhas para identificar clientes que precisam de reparcelamento

Desenvolvido em Português Brasileiro
Baseado no PDD seção 7 - Processamento de dados das planilhas
"""

from core.rastreamento_unificado import iniciar_rastreamento
from core.notificacoes_simples import notificar_sucesso
from core.base_rpa import BaseRPA, ResultadoRPA
import asyncio
from datetime import datetime
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
        from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo
        self.repositorio_contratos = repositorio_contratos_arquivo
        self.log_info("💾 Repositório JSON transacional inicializado")

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

            # ✅ NOVO: Inicializa gerador de anexos
            from core.gerador_anexos import gerador_anexos
            self.gerador_anexos = gerador_anexos

            # ✅ FORÇA inicialização do sistema híbrido ANTES de tudo
            self.log_info("🔧 Persistência baseada em JSON pronta para uso")

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
            # self.log_progresso("Processando pendências de IPTU")
            # pendencias_iptu = await self._processar_pendencias_iptu(planilha_apoio_id)

            # Atualiza planilha principal com novos dados SOMENTE se houver aprovados
            # if novos_contratos_aprovados or pendencias_iptu:
            #    self.log_progresso(
            #        "Atualizando planilha principal com novos dados")
            #    await self._atualizar_planilha_principal(
            #        planilha_calculo_id, novos_contratos_aprovados, pendencias_iptu
            #    )

            # --- Separação de logs: Auditoria da planilha de apoio ---
            self.log_progresso(
                "\n" + "=" * 80)
            self.log_progresso(
                "📋 LEITURA DA ABA DE NOVOS CONTRATOS (PLANILHA DE APOIO)")
            self.log_progresso(
                "=" * 80)

            for c in contratos_auditoria_apoio:
                status_emoji = "✅" if c['status'] == 'aprovado' else "❌" if c['status'] == 'rejeitado' else "⚠️"
                self.log_progresso(
                    f"{status_emoji} [Apoio][{c['status'].upper()}] Cliente: {c['cliente']}, Título: {c['titulo']}")
                self.log_progresso(
                    f"     Motivo: {c['motivo']}")

            # --- Processamento da base de cálculo e verificação de integridade ---
            self.log_progresso(
                "\n" + "=" * 80)
            self.log_progresso(
                "📋 LEITURA DA PLANILHA BASE DE CÁLCULO")
            self.log_progresso(
                "=" * 80)

            contratos_reajuste, contratos_auditoria_base = await self._identificar_contratos_reajuste(planilha_calculo_id)

            # REMOVIDO: Verificação de integridade entre planilhas
            # REGRA ATUALIZADA: Base de cálculo pode ter contratos homologados diretamente
            # Planilha de apoio é apenas para NOVOS clientes que entrarão na base
            self.log_progresso(
                "\n✅ Base de cálculo: Contratos homologados processados normalmente")

            # Gera fila para próximos RPAs
            self.log_progresso(
                f"Identificados {len(contratos_reajuste)} contratos para gerar a fila.")
            fila_processamento = await self._gerar_fila_processamento(contratos_reajuste)
            self.log_progresso(
                f"Fila de processamento gerada com {len(fila_processamento)} itens.")

            # ✅ NOVO: Obtém estatísticas de contratos já processados da função _salvar_fila_data_manager
            contratos_ja_processados = getattr(
                self, 'contratos_ja_processados', 0)

            # Monta resultado final
            resultado_dados = {
                "novos_contratos_processados": len(novos_contratos_aprovados),
                "contratos_para_reajuste": len(contratos_reajuste),
                # ✅ NOVO: Contratos já processados
                "contratos_ja_processados": contratos_ja_processados,
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

            # Após análise, se houver pendências IPTU identificadas, notificar explicitamente
            if hasattr(self, 'pendencias_iptu_identificadas') and self.pendencias_iptu_identificadas:
                self.log_progresso(
                    f"\n🔔 RELATÓRIO DE PENDÊNCIAS IPTU IDENTIFICADAS:")
                for pend in self.pendencias_iptu_identificadas:
                    self.log_progresso(
                        f" - Cliente: {pend['cliente']}, Título: {pend['titulo']}, Pendência: {pend['pendencia_pmfi']}, Data consulta: {pend['data_consulta_iptu']}, Motivo: {pend['motivo']}")

            # Após análise, se houver pendências IPTU identificadas, notificar explicitamente
            if hasattr(self, 'pendencias_iptu_identificadas') and self.pendencias_iptu_identificadas:
                self.log_progresso(
                    f"\n🔔 RELATÓRIO DE PENDÊNCIAS IPTU IDENTIFICADAS:")
                for pend in self.pendencias_iptu_identificadas:
                    self.log_progresso(
                        f" - Cliente: {pend['cliente']}, Título: {pend['titulo']}, Pendência: {pend['pendencia_pmfi']}, Data consulta: {pend['data_consulta_iptu']}, Motivo: {pend['motivo']}")

            # --- Monta relatório detalhado para notificação ---
            relatorio = ""

            # ✅ NOVO: RELATÓRIO DA LEITURA DA ABA DE NOVOS CONTRATOS
            relatorio += "=" * 80 + "\n"
            relatorio += "📋 LEITURA DA ABA DE NOVOS CONTRATOS (PLANILHA DE APOIO)\n"
            relatorio += "=" * 80 + "\n"

            # Filtra contratos da planilha de apoio
            contratos_apoio = [c for c in resultado_dados.get('contratos_auditoria', [])
                               if c.get('origem', '') == 'planilha_apoio' or 'novos_contratos' in str(c.get('motivo', '')).lower()]

            if contratos_apoio:
                aprovados_apoio = [
                    c for c in contratos_apoio if c.get('status') == 'aprovado']
                rejeitados_apoio = [
                    c for c in contratos_apoio if c.get('status') == 'rejeitado']
                nprocessados_apoio = [c for c in contratos_apoio if c.get(
                    'status') == 'não processado']

                relatorio += f"📊 RESUMO DA PLANILHA DE APOIO:\n"
                relatorio += f"   ✅ Contratos aprovados: {len(aprovados_apoio)}\n"
                relatorio += f"   ❌ Contratos rejeitados: {len(rejeitados_apoio)}\n"
                relatorio += f"   ⚠️ Contratos não processados: {len(nprocessados_apoio)}\n"
                relatorio += f"   📋 Total lidos: {len(contratos_apoio)}\n\n"

                if aprovados_apoio:
                    relatorio += "✅ CONTRATOS APROVADOS (ELEGÍVEIS PARA MIGRAÇÃO):\n"
                    for c in aprovados_apoio:
                        relatorio += f"   - Cliente: {c.get('cliente')}, Título: {c.get('titulo')}\n"
                        relatorio += f"     Motivo: {c.get('motivo')}\n"
                    relatorio += "\n"

                if rejeitados_apoio:
                    relatorio += "❌ CONTRATOS REJEITADOS:\n"
                    for c in rejeitados_apoio:
                        relatorio += f"   - Cliente: {c.get('cliente')}, Título: {c.get('titulo')}\n"
                        relatorio += f"     Motivo: {c.get('motivo')}\n"
                    relatorio += "\n"
            else:
                relatorio += "ℹ️ Nenhum contrato encontrado na aba de novos contratos.\n\n"

            # ✅ NOVO: RELATÓRIO DA LEITURA DA PLANILHA BASE DE CÁLCULO
            relatorio += "=" * 80 + "\n"
            relatorio += "📋 LEITURA DA PLANILHA BASE DE CÁLCULO\n"
            relatorio += "=" * 80 + "\n"

            # Filtra contratos da base de cálculo
            contratos_base = [c for c in resultado_dados.get('contratos_auditoria', [])
                              if c.get('origem', '') == 'base_calculo' or 'base de cálculo' in str(c.get('motivo', '')).lower()]

            if not contratos_base:
                # Se não há filtro específico, usa todos os contratos de auditoria
                contratos_base = resultado_dados.get('contratos_auditoria', [])

            if contratos_base:
                aprovados_base = [
                    c for c in contratos_base if c.get('status') == 'aprovado']
                rejeitados_base = [
                    c for c in contratos_base if c.get('status') == 'rejeitado']
                nprocessados_base = [c for c in contratos_base if c.get(
                    'status') == 'não processado']

                relatorio += f"📊 RESUMO DA BASE DE CÁLCULO:\n"
                relatorio += f"   ✅ Contratos elegíveis para reparcelamento: {len(aprovados_base)}\n"
                relatorio += f"   ❌ Contratos rejeitados: {len(rejeitados_base)}\n"
                relatorio += f"   ⚠️ Contratos não processados: {len(nprocessados_base)}\n"
                relatorio += f"   📋 Total lidos: {len(contratos_base)}\n\n"

                if aprovados_base:
                    relatorio += "✅ CONTRATOS ELEGÍVEIS PARA REPARCELAMENTO:\n"
                    for c in aprovados_base:
                        relatorio += f"   - Cliente: {c.get('cliente')}, Título: {c.get('titulo')}\n"
                        relatorio += f"     Motivo: {c.get('motivo')}\n"
                        # Adiciona informações de pendências IPTU se disponível
                        if c.get('tem_pendencia_iptu'):
                            relatorio += f"     ⚠️ Pendência IPTU identificada (será validada no Sienge)\n"
                    relatorio += "\n"

                if rejeitados_base:
                    relatorio += "❌ CONTRATOS REJEITADOS:\n"
                    for c in rejeitados_base:
                        relatorio += f"   - Cliente: {c.get('cliente')}, Título: {c.get('titulo')}\n"
                        relatorio += f"     Motivo: {c.get('motivo')}\n"
                    relatorio += "\n"

                if nprocessados_base:
                    relatorio += "⚠️ CONTRATOS NÃO PROCESSADOS:\n"
                    for c in nprocessados_base:
                        relatorio += f"   - Cliente: {c.get('cliente')}, Título: {c.get('titulo')}\n"
                        relatorio += f"     Motivo: {c.get('motivo')}\n"
                    relatorio += "\n"
            else:
                relatorio += "ℹ️ Nenhum contrato encontrado na base de cálculo.\n\n"

            # ✅ NOVO: RELATÓRIO DE PENDÊNCIAS IPTU IDENTIFICADAS
            if hasattr(self, 'pendencias_iptu_identificadas') and self.pendencias_iptu_identificadas:
                relatorio += "=" * 80 + "\n"
                relatorio += "⚠️ RELATÓRIO DE PENDÊNCIAS IPTU IDENTIFICADAS\n"
                relatorio += "=" * 80 + "\n"
                relatorio += "ℹ️ ATENÇÃO: Os contratos abaixo têm pendências IPTU identificadas e serão reportados no e-mail:\n"
                relatorio += "   (Estas pendências são apenas informativas - NÃO bloqueiam o processamento)\n\n"

                for pend in self.pendencias_iptu_identificadas:
                    relatorio += f"   - Cliente: {pend['cliente']}, Título: {pend['titulo']}\n"
                    relatorio += f"     Pendência PMFI: {pend['pendencia_pmfi']}\n"
                    relatorio += f"     Data consulta IPTU: {pend['data_consulta_iptu']}\n"
                    relatorio += f"     Motivo: {pend['motivo']}\n\n"

                relatorio += f"📊 Total de contratos com pendências IPTU identificadas: {len(self.pendencias_iptu_identificadas)}\n\n"

            # ESTATÍSTICAS GERAIS
            relatorio += "=" * 80 + "\n"
            relatorio += "📊 ESTATÍSTICAS GERAIS\n"
            relatorio += "=" * 80 + "\n"

            total_lidos = len(resultado_dados.get('contratos_auditoria', []))
            total_aprovados = len([c for c in resultado_dados.get(
                'contratos_auditoria', []) if c.get('status') == 'aprovado'])
            total_rejeitados = len([c for c in resultado_dados.get(
                'contratos_auditoria', []) if c.get('status') == 'rejeitado'])
            total_nprocessados = len([c for c in resultado_dados.get(
                'contratos_auditoria', []) if c.get('status') == 'não processado'])
            contratos_ja_processados = resultado_dados.get(
                'contratos_ja_processados', 0)
            data_analise = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

            relatorio += f"📋 PLANILHA DE APOIO (NOVOS CONTRATOS):\n"
            relatorio += f"   - Total lidos: {len(contratos_apoio) if 'contratos_apoio' in locals() else 0}\n"
            relatorio += f"   - Aprovados para migração: {len(aprovados_apoio) if 'aprovados_apoio' in locals() else 0}\n"
            relatorio += f"   - Rejeitados: {len(rejeitados_apoio) if 'rejeitados_apoio' in locals() else 0}\n\n"

            relatorio += f"📋 BASE DE CÁLCULO:\n"
            relatorio += f"   - Total lidos: {len(contratos_base) if 'contratos_base' in locals() else 0}\n"
            relatorio += f"   - Elegíveis para reparcelamento: {len(aprovados_base) if 'aprovados_base' in locals() else 0}\n"
            relatorio += f"   - Rejeitados: {len(rejeitados_base) if 'rejeitados_base' in locals() else 0}\n"
            relatorio += f"   - Não processados: {len(nprocessados_base) if 'nprocessados_base' in locals() else 0}\n\n"

            relatorio += f"📊 RESUMO GERAL:\n"
            relatorio += f"   - Total de contratos lidos: {total_lidos}\n"
            relatorio += f"   - Total aprovados/elegíveis: {total_aprovados}\n"
            relatorio += f"   - Total rejeitados: {total_rejeitados}\n"
            relatorio += f"   - Total não processados: {total_nprocessados}\n"
            relatorio += f"   - Total já processados (ignorados): {contratos_ja_processados}\n"
            relatorio += f"   - Data/hora da análise: {data_analise}\n"

            if hasattr(self, 'pendencias_iptu_identificadas'):
                relatorio += f"   - Total com pendências IPTU identificadas: {len(self.pendencias_iptu_identificadas)}\n"

            relatorio += "\n"

            # ✅ NOVO: Observações importantes
            relatorio += "📋 OBSERVAÇÕES IMPORTANTES:\n"
            relatorio += "   ✅ Todos os contratos aprovados podem ser reparcelados (conforme PDD)\n"
            relatorio += "   ✅ Validação de pendências SIENGE será feita no RPA Sienge após extração\n"
            relatorio += "   ✅ Pendências IPTU identificadas são apenas para informação\n"
            relatorio += "   ✅ Nenhum contrato foi bloqueado por pendências\n"
            relatorio += "   ✅ Fase atual: Geração de fila para extração de relatórios\n"
            relatorio += "   ✅ Próxima fase: RPA Sienge fará validação com dados reais\n"

            relatorio += "\n✅ Integridade OK: Processamento concluído com sucesso.\n"
            relatorio += "O sistema continuará monitorando as próximas execuções automaticamente.\n"

            # ✅ NOVO: Gera anexos Excel com dados detalhados dos contratos
            self.log_progresso("\n📎 Gerando anexos para relatório...")
            anexos_paths = await self._gerar_anexos_relatorio(
                contratos_auditoria_apoio,
                contratos_auditoria_base,
                resultado_dados
            )

            # Monta resultados para notificação
            contratos_identificados = resultado_dados.get(
                'contratos_para_reajuste', 0)
            contratos_ja_processados = resultado_dados.get(
                'contratos_ja_processados', 0)

            if contratos_ja_processados > 0:
                mensagem = f"Análise concluída - {contratos_identificados} contratos elegíveis para reparcelamento ({contratos_ja_processados} já processados anteriormente)"
            else:
                mensagem = f"Análise concluída - {contratos_identificados} contratos elegíveis para reparcelamento"

            resultados_notificacao = {
                "Mensagem": mensagem,
                "relatorio": relatorio,
            }
            # Adiciona outros campos principais
            resultados_notificacao["contratos_identificados"] = contratos_identificados
            resultados_notificacao["contratos_ja_processados"] = contratos_ja_processados
            resultados_notificacao["planilhas_analisadas"] = "2"
            resultados_notificacao["status"] = "Análise concluída - Fila gerada para extração"
            resultados_notificacao["observacao"] = "Fase 1: Geração de fila para extração de relatórios. Validação PDD será feita no RPA Sienge com dados reais"

            # ✅ NOVO: Adiciona informações sobre pendências IPTU
            if hasattr(self, 'pendencias_iptu_identificadas'):
                resultados_notificacao["pendencias_iptu_identificadas"] = len(
                    self.pendencias_iptu_identificadas)
                resultados_notificacao["tem_pendencias_iptu"] = len(
                    self.pendencias_iptu_identificadas) > 0

            # ✅ NOVO: Adiciona anexos ao e-mail
            if anexos_paths:
                resultados_notificacao["caminhos_anexos"] = anexos_paths
                self.log_progresso(
                    f"✅ {len(anexos_paths)} anexo(s) preparado(s) para envio")

            # Envia notificação de sucesso (opcional, preferimos centralizar no main)
            if parametros.get("notificar", False):
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
                        'motivo': motivo_str,
                        'origem': 'planilha_apoio'
                    })
                    continue
                # Se passou, aprovado para migração
                auditoria.append({
                    'cliente': cliente or 'Sem nome',
                    'titulo': numero_titulo or 'N/A',
                    'status': 'aprovado',
                    'motivo': 'Aprovado para migração (dados válidos na planilha de apoio)',
                    'origem': 'planilha_apoio'
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
                    tempo_espera = (tentativa + 1) * \
                        30  # 30, 60, 90 segundos
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
                # self.log_progresso(f"DEBUG CONTRATO MIGRADO: {contrato}")  # Removido para não poluir o log
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
        ✅ CORRIGIDO: Logs detalhados linha por linha + NÃO bloqueia contratos

        Processo:
        1. Verifica para cada cliente/título a atualização data consulta do IPTU
        2. Copia informação da coluna IPTU PENDÊNCIAS PMFI para clientes cuja "Data de consulta" é do mês vigente
        3. Cola as informações na coluna correspondente da Base de cálculo
        4. ✅ NOVO: Log detalhado de cada atualização
        5. ✅ CORRIGIDO: NÃO bloqueia contratos, apenas identifica pendências para relatório

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
                f"🔍 PROCESSANDO PENDÊNCIAS IPTU - Mês atual: {mes_atual}/{ano_atual}")
            self.log_progresso(
                f"📊 Total de registros IPTU para análise: {len(pendencias_iptu)}")

            # Lê dados atuais da Base de cálculo
            dados_base_calculo = aba_base_calculo.get_all_records()

            atualizacoes_realizadas = 0
            pendencias_encontradas = []
            # ✅ CORRIGIDO: Lista de pendências identificadas (NÃO bloqueadas)
            pendencias_identificadas = []

            for idx, pendencia in enumerate(pendencias_iptu, 1):
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

                    # ✅ NOVO: Log detalhado de cada registro IPTU
                    self.log_progresso(
                        f"\n📋 REGISTRO IPTU #{idx}:")
                    self.log_progresso(
                        f"   Cliente: '{cliente_iptu}'")
                    self.log_progresso(
                        f"   Título: '{titulo_iptu}'")
                    self.log_progresso(
                        f"   Data consulta: '{data_consulta_str}'")
                    self.log_progresso(
                        f"   Pendência PMFI: '{pendencia_pmfi}'")

                    # Valida se tem dados mínimos
                    if not cliente_iptu and not titulo_iptu:
                        self.log_progresso(
                            f"   ❌ REJEITADO: Cliente e título vazios")
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
                                        self.log_progresso(
                                            f"   ✅ Data consulta OK: {data_consulta.strftime('%d/%m/%Y')} (mês vigente)")
                                    break
                                except ValueError:
                                    continue
                        except:
                            pass

                    # Se consulta não é do mês atual, registra pendência
                    if not consulta_mes_atual:
                        motivo = f"Consulta IPTU não atualizada no mês vigente (data: '{data_consulta_str}')"
                        self.log_progresso(
                            f"   ⚠️ PENDÊNCIA: {motivo}")
                        pendencias_encontradas.append({
                            'cliente': cliente_iptu,
                            'titulo': titulo_iptu,
                            'data_consulta': data_consulta_str,
                            'motivo': motivo
                        })
                        continue

                    # ✅ CORRIGIDO: Identifica pendências PMFI (NÃO BLOQUEIA)
                    pendencia_pmfi_upper = pendencia_pmfi.upper()
                    pendencia_valida = pendencia_pmfi_upper in [
                        'OK', 'SEM PENDÊNCIA', 'REGULAR', '']

                    if not pendencia_valida:
                        self.log_progresso(
                            f"   ⚠️ PENDÊNCIA PMFI IDENTIFICADA: '{pendencia_pmfi}' (será reportada no e-mail)")
                        pendencias_identificadas.append({
                            'cliente': cliente_iptu,
                            'titulo': titulo_iptu,
                            'pendencia_pmfi': pendencia_pmfi,
                            'data_consulta_iptu': data_consulta_str,
                            'motivo': f"Pendência PMFI: '{pendencia_pmfi}' - Será reportada no e-mail"
                        })
                        # ✅ CORRIGIDO: NÃO bloqueia - continua processando
                    else:
                        self.log_progresso(
                            f"   ✅ Pendência PMFI OK: '{pendencia_pmfi}'")

                    # Procura contrato correspondente na Base de cálculo
                    contrato_encontrado = False
                    for linha, contrato in enumerate(dados_base_calculo, start=2):
                        cliente_base = str(contrato.get('Cliente', '')).strip()
                        titulo_base = str(contrato.get(
                            'numero_titulo', contrato.get('Titulo', ''))).strip()

                        # Verifica correspondência por cliente OU título
                        if (cliente_iptu and cliente_iptu.lower() in cliente_base.lower()) or \
                           (titulo_iptu and titulo_iptu == titulo_base):

                            contrato_encontrado = True
                            self.log_progresso(
                                f"   ✅ CONTRATO ENCONTRADO na Base de cálculo (linha {linha})")
                            self.log_progresso(
                                f"   📋 Cliente Base: '{cliente_base}'")
                            self.log_progresso(
                                f"   📋 Título Base: '{titulo_base}'")

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
                                    # ✅ NOVO: Log detalhado da atualização
                                    celula = f'{chr(64 + coluna_pendencia)}{linha}'
                                    valor_anterior = aba_base_calculo.acell(
                                        celula).value

                                    self.log_progresso(
                                        f"   📝 ATUALIZANDO CÉLULA: {celula}")
                                    self.log_progresso(
                                        f"   📝 Valor anterior: '{valor_anterior}'")
                                    self.log_progresso(
                                        f"   📝 Valor novo: '{pendencia_pmfi}'")

                                    # Atualiza célula específica
                                    aba_base_calculo.update(
                                        celula, pendencia_pmfi)

                                    self.log_progresso(
                                        f"   ✅ ATUALIZAÇÃO CONCLUÍDA: {cliente_base} - {titulo_base}")
                                    self.log_progresso(
                                        f"   ✅ Coluna: '{cabecalhos[coluna_pendencia-1]}'")
                                    self.log_progresso(
                                        f"   ✅ Linha: {linha}")

                                    atualizacoes_realizadas += 1
                                else:
                                    self.log_progresso(
                                        f"   ❌ ERRO: Coluna PENDÊNCIAS PMFI não encontrada")
                                    self.log_progresso(
                                        f"   📋 Cabeçalhos disponíveis: {cabecalhos}")

                            except Exception as e:
                                self.log_progresso(
                                    f"   ❌ ERRO ao atualizar IPTU para {cliente_base}: {str(e)}")

                            break  # Encontrou correspondência, para de procurar

                    if not contrato_encontrado:
                        self.log_progresso(
                            f"   ⚠️ CONTRATO NÃO ENCONTRADO na Base de cálculo")
                        self.log_progresso(
                            f"   📋 Cliente procurado: '{cliente_iptu}'")
                        self.log_progresso(
                            f"   📋 Título procurado: '{titulo_iptu}'")

                except Exception as e:
                    self.log_progresso(
                        f"   ❌ ERRO ao processar pendência IPTU #{idx}: {str(e)}")
                    continue

            # ✅ NOVO: Relatório final detalhado
            self.log_progresso(
                f"\n📊 RELATÓRIO FINAL - PROCESSAMENTO IPTU:")
            self.log_progresso(
                f"   ✅ Atualizações realizadas: {atualizacoes_realizadas}")
            self.log_progresso(
                f"   ⚠️ Pendências encontradas: {len(pendencias_encontradas)}")
            self.log_progresso(
                f"   📋 Pendências identificadas para relatório: {len(pendencias_identificadas)}")

            # Registra no log as pendências encontradas
            if pendencias_encontradas:
                self.log_progresso(
                    f"\n⚠️ CLIENTES/TÍTULOS COM CONSULTA IPTU PENDENTE:")
                for pendencia in pendencias_encontradas:
                    self.log_progresso(
                        f"   - {pendencia['cliente']} (Título: {pendencia['titulo']}) - {pendencia['motivo']}")

            # ✅ CORRIGIDO: Registra pendências identificadas (NÃO bloqueadas)
            if pendencias_identificadas:
                self.log_progresso(
                    f"\n📋 CLIENTES/TÍTULOS COM PENDÊNCIAS PMFI IDENTIFICADAS (serão reportadas no e-mail):")
                for pendencia in pendencias_identificadas:
                    self.log_progresso(
                        f"   - {pendencia['cliente']} (Título: {pendencia['titulo']}) - {pendencia['motivo']}")

            # ✅ CORRIGIDO: Salva pendências identificadas para relatório no e-mail
            if pendencias_identificadas:
                if not hasattr(self, 'pendencias_iptu_identificadas'):
                    self.pendencias_iptu_identificadas = []
                self.pendencias_iptu_identificadas.extend(
                    pendencias_identificadas)

            self.log_progresso(
                f"✅ Processamento IPTU concluído - NENHUM CONTRATO BLOQUEADO")

        except Exception as e:
            raise Exception(
                f"Erro ao atualizar pendências IPTU conforme PDD: {str(e)}")

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
                    "Empresa": str(contrato.get('Empresa', '')).strip(),
                    "Loteamento": str(contrato.get('Loteamento', '')).strip(),
                    "Código Cliente": normalizar_codigo_cliente(str(contrato.get('Código Cliente', '')).strip()),
                    "Cliente": cliente_nome,
                    "Quadra": str(contrato.get('Quadra', '')).strip(),
                    "Lote": str(contrato.get('Lote', '')).strip(),
                    "Titulo": numero_titulo,
                    "Data de consulta  IPTU ": str(contrato.get('Data de consulta IPTU', '') or '').strip(),
                    "PENDENCIAS PMFI ": str(contrato.get('PENDENCIAS PMFI', '') or '').strip(),
                    "PENDENCIAS SIENGE INAD": str(contrato.get('PENDENCIAS SIENGE INAD', '') or '').strip(),
                    "PENDENCIAS SIENGE": str(contrato.get('PENDENCIAS SIENGE', '') or '').strip(),
                    "Assinatura ultimo Contrato": str(contrato.get('Assinatura ultimo Contrato', '') or '').strip(),
                    "1 º vencimento": str(contrato.get('1 º vencimento', '') or '').strip(),
                    "Índice": str(contrato.get('Índice', '') or '').strip(),
                    "Juros": str(contrato.get('Juros', '') or '').strip(),
                    "Tipo reajuste": str(contrato.get('Tipo reajuste', '') or '').strip(),
                    "\"original ou corrigido\"": str(contrato.get('"original ou corrigido"', '') or '').strip(),
                    "Último reajuste": str(ultimo_reajuste or '').strip(),
                    "Valor da Parcela Base": str(contrato.get('Valor da Parcela Base', '') or '').strip(),
                    "Parcelas a vencer": str(contrato.get('Parcelas a vencer', '') or '').strip(),
                    "Saldo devedor Base": str(contrato.get('Saldo devedor Base', '') or '').strip(),
                    "OK, se acaso precisar na Catacuy use esta": str(contrato.get('OK, se acaso precisar na Catacuy use esta', '') or '').strip(),
                    "Mês reajuste": str(contrato.get('Mês reajuste', '') or '').strip(),
                    "1º vencimento carnê": str(contrato.get('1º vencimento carnê', '') or '').strip(),
                    "% Reajuste total": str(contrato.get('% Reajuste total', '') or '').strip(),
                    "Parcela final": str(contrato.get('Parcela final', '') or '').strip(),
                    "Saldo devedor final": str(contrato.get('Saldo devedor final', '') or '').strip(),
                    "Próximo reajuste": str(contrato.get('Próximo reajuste', '') or '').strip(),
                    "Data de Migração": str(contrato.get('Data de Migração', '') or '').strip(),
                    "status": "PENDENTE",
                    "_metadata": {
                        "prioridade": self._calcular_prioridade(contrato),
                        "origem_identificacao": "rpa_analise_planilhas"
                    }
                }

                for campo in item_fila:
                    if campo == "_metadata":
                        continue
                    if item_fila[campo] is None:
                        item_fila[campo] = ""

                fila_processamento.append(item_fila)

            # Ordena por prioridade (mais urgente primeiro)
            fila_processamento.sort(
                key=lambda x: x['_metadata']['prioridade'], reverse=True)

            # ✅ NOVO: Salva fila usando data_manager.py (MongoDB + JSON)
            await self._persistir_fila_contratos(fila_processamento)

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

    async def _persistir_fila_contratos(self, fila_processamento: List[Dict[str, Any]]):
        if not fila_processamento:
            self.log_progresso("⚠️ Nenhum item para salvar na fila")
            return

        resultado = self.repositorio_contratos.salvar_lote(fila_processamento)
        self.contratos_salvos = resultado.get("inseridos", 0)
        self.contratos_atualizados = resultado.get("atualizados", 0)
        self.contratos_ja_processados = resultado.get("ignorados", 0)
        self.contratos_falharam = resultado.get("erros", 0)

        self.log_progresso("\n📊 RELATÓRIO DE PROCESSAMENTO DA FILA:")
        self.log_progresso(
            f"   ✅ Contratos inseridos: {self.contratos_salvos}")
        self.log_progresso(
            f"   🔄 Contratos atualizados: {self.contratos_atualizados}")
        self.log_progresso(
            f"   ⚠️ Contratos ignorados: {self.contratos_ja_processados}")
        self.log_progresso(
            f"   ❌ Contratos com erro: {self.contratos_falharam}")

        await self._salvar_fila_local(fila_processamento)
        self.log_progresso("Persistência da fila de contratos concluída.")

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

    async def _gerar_anexos_relatorio(
        self,
        contratos_auditoria_apoio: List[Dict[str, Any]],
        contratos_auditoria_base: List[Dict[str, Any]],
        resultado_dados: Dict[str, Any]
    ) -> List[str]:
        """
        Gera anexos Excel com dados detalhados dos contratos para envio por e-mail

        Args:
            contratos_auditoria_apoio: Lista de contratos da planilha de apoio
            contratos_auditoria_base: Lista de contratos da base de cálculo
            resultado_dados: Dados completos do resultado da análise

        Returns:
            Lista de caminhos dos arquivos gerados
        """
        anexos = []

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # ✅ ANEXO 1: Planilha de Apoio (Novos Contratos)
            if contratos_auditoria_apoio:
                dados_apoio = []
                for contrato in contratos_auditoria_apoio:
                    dados_apoio.append({
                        'Cliente': contrato.get('cliente', 'N/A'),
                        'Título': contrato.get('titulo', 'N/A'),
                        'Status': contrato.get('status', 'N/A').upper(),
                        'Motivo': contrato.get('motivo', 'N/A'),
                        'Origem': 'Planilha de Apoio'
                    })

                if dados_apoio:
                    caminho_excel_apoio = self.gerador_anexos.gerar_anexo_excel(
                        dados=dados_apoio,
                        nome_arquivo="analise_planilha_apoio",
                        nome_aba="Novos Contratos"
                    )
                    anexos.append(caminho_excel_apoio)
                    self.log_progresso(
                        f"   ✅ Anexo gerado: {os.path.basename(caminho_excel_apoio)}")

            # ✅ ANEXO 2: Base de Cálculo (Contratos para Reparcelamento)
            if contratos_auditoria_base:
                dados_base = []
                for contrato in contratos_auditoria_base:
                    dados_base.append({
                        'Cliente': contrato.get('cliente', 'N/A'),
                        'Título': contrato.get('titulo', 'N/A'),
                        'Status': contrato.get('status', 'N/A').upper(),
                        'Motivo': contrato.get('motivo', 'N/A'),
                        'Tem Pendência IPTU': 'SIM' if contrato.get('tem_pendencia_iptu', False) else 'NÃO',
                        'Origem': 'Base de Cálculo'
                    })

                if dados_base:
                    caminho_excel_base = self.gerador_anexos.gerar_anexo_excel(
                        dados=dados_base,
                        nome_arquivo="analise_base_calculo",
                        nome_aba="Contratos Reparcelamento"
                    )
                    anexos.append(caminho_excel_base)
                    self.log_progresso(
                        f"   ✅ Anexo gerado: {os.path.basename(caminho_excel_base)}")

            # ✅ ANEXO 3: Fila de Processamento (Contratos Aprovados para Extração)
            fila_processamento = resultado_dados.get('fila_processamento', [])
            if fila_processamento:
                dados_fila = []
                for item in fila_processamento:
                    dados_fila.append({
                        'Empresa': item.get('Empresa', 'N/A'),
                        'Loteamento': item.get('Loteamento', 'N/A'),
                        'Cliente': item.get('Cliente', 'N/A'),
                        'Código Cliente': item.get('Código Cliente', 'N/A'),
                        'Título': item.get('Titulo', 'N/A'),
                        'Último Reajuste': item.get('Último reajuste', 'N/A'),
                        'Mês Reajuste': item.get('Mês reajuste', 'N/A'),
                        'Status': item.get('status', 'PENDENTE'),
                        'Prioridade': item.get('_metadata', {}).get('prioridade', 0)
                    })

                if dados_fila:
                    caminho_excel_fila = self.gerador_anexos.gerar_anexo_excel(
                        dados=dados_fila,
                        nome_arquivo="fila_processamento_sienge",
                        nome_aba="Fila de Extração"
                    )
                    anexos.append(caminho_excel_fila)
                    self.log_progresso(
                        f"   ✅ Anexo gerado: {os.path.basename(caminho_excel_fila)}")

            # ✅ ANEXO 4: Pendências IPTU (se existirem)
            if hasattr(self, 'pendencias_iptu_identificadas') and self.pendencias_iptu_identificadas:
                dados_pendencias = []
                for pendencia in self.pendencias_iptu_identificadas:
                    dados_pendencias.append({
                        'Cliente': pendencia.get('cliente', 'N/A'),
                        'Título': pendencia.get('titulo', 'N/A'),
                        'Pendência PMFI': pendencia.get('pendencia_pmfi', 'N/A'),
                        'Data Consulta IPTU': pendencia.get('data_consulta_iptu', 'N/A'),
                        'Motivo': pendencia.get('motivo', 'N/A'),
                        'Observação': 'Apenas informativo - NÃO bloqueia processamento'
                    })

                if dados_pendencias:
                    caminho_excel_pendencias = self.gerador_anexos.gerar_anexo_excel(
                        dados=dados_pendencias,
                        nome_arquivo="pendencias_iptu_identificadas",
                        nome_aba="Pendências IPTU"
                    )
                    anexos.append(caminho_excel_pendencias)
                    self.log_progresso(
                        f"   ✅ Anexo gerado: {os.path.basename(caminho_excel_pendencias)}")

            # ✅ ANEXO 5: Resumo Executivo
            dados_resumo = [{
                'Métrica': 'Total de Contratos Lidos (Planilha de Apoio)',
                'Valor': len(contratos_auditoria_apoio)
            }, {
                'Métrica': 'Total de Contratos Aprovados (Planilha de Apoio)',
                'Valor': len([c for c in contratos_auditoria_apoio if c.get('status') == 'aprovado'])
            }, {
                'Métrica': 'Total de Contratos Rejeitados (Planilha de Apoio)',
                'Valor': len([c for c in contratos_auditoria_apoio if c.get('status') == 'rejeitado'])
            }, {
                'Métrica': 'Total de Contratos Lidos (Base de Cálculo)',
                'Valor': len(contratos_auditoria_base)
            }, {
                'Métrica': 'Total Elegíveis para Reparcelamento',
                'Valor': len([c for c in contratos_auditoria_base if c.get('status') == 'aprovado'])
            }, {
                'Métrica': 'Total de Contratos na Fila de Processamento',
                'Valor': len(fila_processamento)
            }, {
                'Métrica': 'Total de Contratos Já Processados (Ignorados)',
                'Valor': resultado_dados.get('contratos_ja_processados', 0)
            }, {
                'Métrica': 'Total de Pendências IPTU Identificadas',
                'Valor': len(self.pendencias_iptu_identificadas) if hasattr(self, 'pendencias_iptu_identificadas') else 0
            }, {
                'Métrica': 'Data/Hora da Análise',
                'Valor': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            }]

            caminho_excel_resumo = self.gerador_anexos.gerar_anexo_excel(
                dados=dados_resumo,
                nome_arquivo="resumo_executivo_analise",
                nome_aba="Resumo Executivo"
            )
            anexos.append(caminho_excel_resumo)
            self.log_progresso(
                f"   ✅ Anexo gerado: {os.path.basename(caminho_excel_resumo)}")

            self.log_progresso(f"✅ Total de anexos gerados: {len(anexos)}")
            return anexos

        except Exception as e:
            self.log_erro("Erro ao gerar anexos do relatório", e)
            return []

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

    def log_progresso(self, mensagem: str):
        """Log de progresso formatado"""
        self.logger.info(mensagem)

    async def _identificar_contratos_reajuste(self, planilha_calculo_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Identifica contratos que precisam de reajuste conforme PDD
        ✅ CORRIGIDO: Foca apenas nas responsabilidades do RPA Análise de Planilhas

        Responsabilidades:
        - Gerar fila para extração dos relatórios do Sienge
        - Verificar pendências com prefeitura (IPTU) na planilha base de cálculo
        - NÃO bloquear contratos com pendências (apenas identificar)
        - Enviar relatório de pendências no e-mail de notificação

        Args:
            planilha_calculo_id: ID da planilha de cálculo

        Returns:
            Lista de contratos que precisam de reajuste
        """
        try:
            self.log_progresso(
                "🔍 ANALISANDO CONTRATOS PARA REPARCELAMENTO (PDD)")

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
            contratos_auditoria = []  # Lista para rastreamento completo
            # ✅ NOVO: Lista de pendências IPTU para relatório
            pendencias_iptu_identificadas = []

            self.log_progresso(
                f"📅 Mês atual: {mes_atual:02d}/{ano_atual}")
            self.log_progresso(
                f"📊 Total de contratos na base: {len(dados_contratos)}")

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
                        contratos_auditoria.append({
                            'cliente': 'Sem nome',
                            'titulo': 'N/A',
                            'status': 'rejeitado',
                            'motivo': 'Cliente e título vazios',
                            'origem': 'base_calculo'
                        })
                        continue

                    mes_reajuste_str = str(
                        contrato.get('Mês reajuste', '')).strip()

                    if (not mes_reajuste_str or
                        mes_reajuste_str in ['', '#N/A', 'N/A', '#REF!', '#VALUE!', 'null', 'None'] or
                            len(mes_reajuste_str) < 3):
                        contratos_auditoria.append({
                            'cliente': cliente or 'Sem nome',
                            'titulo': numero_titulo or 'N/A',
                            'status': 'rejeitado',
                            'motivo': f"Mês reajuste vazio ou inválido: '{mes_reajuste_str}'",
                            'origem': 'base_calculo'
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
                                    continue

                                # Validação do ano
                                if not ano_str or len(ano_str) != 2:
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
                                    continue
                            else:
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
                                        continue
                                except ValueError:
                                    continue

                                # Validação do ano
                                if not ano_str or len(ano_str) != 2:
                                    continue

                                # Converte ano (25 -> 2025, 24 -> 2024)
                                try:
                                    ano_reajuste = int(ano_str)
                                    if ano_reajuste < 50:  # Assume 2000+
                                        ano_reajuste += 2000
                                    elif ano_reajuste < 100:  # Assume 1900+
                                        ano_reajuste += 1900
                                except ValueError:
                                    continue
                            else:
                                continue

                    esta_no_mes_atual = ano_atual == ano_reajuste and mes_atual == mes_reajuste
                    proximo_mes = mes_atual + 1
                    proximo_ano = ano_atual
                    if proximo_mes > 12:
                        proximo_mes = 1
                        proximo_ano += 1
                    esta_no_mes_seguinte = (
                        ano_reajuste == proximo_ano and mes_reajuste == proximo_mes
                    )

                    if esta_no_mes_atual or esta_no_mes_seguinte:
                        # ✅ ELEGÍVEL: mês atual ou imediatamente seguinte

                        # ===================== VERIFICAÇÃO PENDÊNCIAS IPTU (RESPONSABILIDADE CORRETA) =====================

                        # ✅ VERIFICA pendências PMFI (IPTU) - apenas para relatório
                        pendencia_pmfi = str(contrato.get(
                            'PENDÊNCIAS PMFI', '')).strip().upper()
                        consulta_iptu_ok = pendencia_pmfi in [
                            'OK', 'SEM PENDÊNCIA', 'REGULAR', '']

                        # ✅ VERIFICA data de consulta IPTU - apenas para relatório
                        data_consulta_str = str(contrato.get(
                            'Data de consulta IPTU', '')).strip()
                        consulta_iptu_atualizada = False
                        if data_consulta_str:
                            try:
                                for formato in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']:
                                    try:
                                        data_consulta = datetime.strptime(
                                            data_consulta_str, formato)
                                        if data_consulta.month == mes_atual and data_consulta.year == ano_atual:
                                            consulta_iptu_atualizada = True
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                pass

                        # ✅ IDENTIFICA pendências IPTU para relatório (NÃO BLOQUEIA)
                        if not consulta_iptu_ok or not consulta_iptu_atualizada:
                            motivo_pendencia = []
                            if not consulta_iptu_ok:
                                motivo_pendencia.append(
                                    f"pendência PMFI: '{pendencia_pmfi}'")
                            if not consulta_iptu_atualizada:
                                motivo_pendencia.append(
                                    f"data de consulta IPTU inválida ou ausente: '{data_consulta_str}'")

                            pendencias_iptu_identificadas.append({
                                'cliente': cliente or 'Sem nome',
                                'titulo': numero_titulo or 'N/A',
                                'pendencia_pmfi': pendencia_pmfi,
                                'data_consulta_iptu': data_consulta_str,
                                'motivo': "; ".join(motivo_pendencia)
                            })

                        # ===================== APLICAÇÃO DAS REGRAS PDD =====================

                        # ✅ PDD: Todos podem reparcelar - NÃO BLOQUEIA
                        pode_reparcelar = True  # Conforme PDD: todos podem reparcelar

                        self.log_progresso(
                            f"   📋 Pode reparcelar: {'✅ SIM' if pode_reparcelar else '❌ NÃO'}")
                        self.log_progresso(
                            f"   📋 Validação SIENGE: Será feita no RPA Sienge após extração")

                        # ✅ APROVA contrato para processamento (validação SIENGE será feita depois)
                        titulo_final = str(numero_titulo or 'N/A')

                        # Cria cópia com dados essenciais preservados
                        contrato_processado = contrato.copy()
                        contrato_processado['linha_planilha'] = linha
                        contrato_processado['mes_reajuste_original'] = mes_reajuste_str
                        contrato_processado[
                            'motivo_elegibilidade'] = f"Mês de reajuste atual: {mes_reajuste_str}"

                        # ✅ VALIDAÇÃO PDD APLICADA (sem bloqueios)
                        contrato_processado['validacao_pdd'] = json.dumps({
                            'status_cliente': 'APROVADO_PARA_EXTRACAO',
                            'pode_reparcelar': pode_reparcelar,
                            'pendencia_pmfi': pendencia_pmfi,
                            'data_consulta_iptu': data_consulta_str,
                            'consulta_iptu_atualizada': consulta_iptu_atualizada,
                            'observacao': 'Conforme PDD: Todos podem reparcelar. Validação SIENGE será feita após extração.',
                            'regras_aplicadas': 'PDD_TODOS_PODEM_REPARCELAR'
                        })

                        self.log_progresso(
                            f"   ✅ CONTRATO ELEGÍVEL para reparcelamento")
                        self.log_progresso(
                            f"   📋 Pendências IPTU identificadas para relatório")

                        # Garante que campos essenciais estejam presentes
                        contrato_processado['cliente'] = cliente or contrato_processado.get(
                            'Cliente', 'N/A')
                        contrato_processado['numero_titulo'] = titulo_final

                        contratos_para_reajuste.append(
                            contrato_processado)
                        contratos_auditoria.append({
                            'cliente': cliente or 'Sem nome',
                            'titulo': titulo_final,
                            'status': 'aprovado',
                            'motivo': f"Elegível para reparcelamento (mês de reajuste atual: {mes_reajuste_str})",
                            'tem_pendencia_iptu': not consulta_iptu_ok or not consulta_iptu_atualizada,
                            'origem': 'base_calculo'
                        })

                    elif ano_atual > ano_reajuste or (ano_atual == ano_reajuste and mes_atual > mes_reajuste):
                        # ⚠️ ATRASADO: Deveria ter sido processado antes
                        self.log_progresso(
                            f"   ⚠️ ATRASADO: Deveria ter sido processado antes")
                        contratos_auditoria.append({
                            'cliente': cliente or 'Sem nome',
                            'titulo': numero_titulo or 'N/A',
                            'status': 'não processado',
                            'motivo': f"Contrato atrasado: {mes_reajuste_str} (deveria ter sido processado)",
                            'origem': 'base_calculo'
                        })

                    else:
                        # ❌ AINDA NÃO VENCEU: Mês seguinte conforme PDD
                        # Logs de contratos fora do mês atual podem ser consultados
                        # via auditoria; evitamos registrar item a item para reduzir ruído
                        contratos_auditoria.append({
                            'cliente': cliente or 'Sem nome',
                            'titulo': numero_titulo or 'N/A',
                            'status': 'não processado',
                            'motivo': f"Contrato não está no mês de reajuste atual: {mes_reajuste_str}",
                            'origem': 'base_calculo'
                        })

                except (ValueError, TypeError, AttributeError) as e:
                    # Formato inválido, pula contrato
                    self.log_progresso(
                        f"   ❌ ERRO: {str(e)} - dados: {mes_reajuste_str}")
                    continue

            # ✅ NOVO: Relatório final detalhado
            self.log_progresso(
                f"\n📊 RELATÓRIO FINAL - IDENTIFICAÇÃO DE CONTRATOS:")
            self.log_progresso(
                f"   ✅ Contratos elegíveis para reparcelamento: {len(contratos_para_reajuste)}")
            self.log_progresso(
                f"   ⚠️ Contratos não processados: {len([c for c in contratos_auditoria if c['status'] == 'não processado'])}")
            self.log_progresso(
                f"   📋 Contratos com pendências IPTU identificadas: {len(pendencias_iptu_identificadas)}")
            self.log_progresso(
                f"   📧 Pendências IPTU serão reportadas no e-mail de notificação")

            # ✅ NOVO: Salva pendências IPTU para relatório no e-mail
            if pendencias_iptu_identificadas:
                if not hasattr(self, 'pendencias_iptu_identificadas'):
                    self.pendencias_iptu_identificadas = []
                self.pendencias_iptu_identificadas.extend(
                    pendencias_iptu_identificadas)

            # NOVO: retorna também a lista de auditoria detalhada
            self.contratos_auditoria = contratos_auditoria
            return contratos_para_reajuste, contratos_auditoria

        except Exception as e:
            self.log_erro("Erro ao identificar contratos para reajuste", e)
            return [], []

# Função auxiliar para uso direto


async def executar_analise_planilhas(
    planilha_calculo_id: str,
    planilha_apoio_id: str,
    credenciais_google: Optional[str] = None,
    headless: Optional[bool] = None,
    notificar: bool = False
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
            "credenciais_google": credenciais_google,
            "notificar": notificar
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


def normalizar_codigo_cliente(codigo: str) -> str:
    """Normaliza o código do cliente, removendo caracteres não numéricos."""
    if not codigo:
        return ""
    return re.sub(r'\D', '', str(codigo)).strip()


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
