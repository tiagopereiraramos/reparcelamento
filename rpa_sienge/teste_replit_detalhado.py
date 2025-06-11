#!/usr/bin/env python3
"""
Teste Replit Detalhado - RPA Sienge
Simula processamento usando arquivo Excel real com logs precisos de cada regra

Baseado em:
- saldo_devedor_presente-20250610-093716.xlsx 
- teste_reparcelamento_pdd.py
- Regras rigorosas do PDD

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple
import pandas as pd
import logging
from dataclasses import dataclass, asdict

# Adiciona o diretório pai ao path para importar módulos core
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

try:
    from core.base_rpa import ResultadoRPA
    from rpa_sienge.simulador_sienge import SimuladorSienge
except ImportError:
    print("⚠️ Executando sem dependências core - modo standalone")


@dataclass
class LogRegra:
    """Estrutura para logs detalhados de regras"""
    timestamp: str
    etapa: str
    regra: str
    criterio: str
    valor_avaliado: Any
    resultado: str
    aprovado: bool
    detalhes: Dict[str, Any]


@dataclass
class ResultadoProcessamento:
    """Resultado detalhado do processamento"""
    contrato: str
    cliente: str
    status_final: str
    pode_reparcelar: bool
    logs_regras: List[LogRegra]
    dados_calculados: Dict[str, Any]
    timestamp_processamento: str


class TesteReplitDetalhado:
    """
    Teste detalhado para Replit com logs precisos de cada regra PDD
    Suporta arquivos Excel locais e integração com Google Sheets
    """

    def __init__(self, arquivo_fonte: str = None, usar_google_sheets: bool = False, planilha_id: str = None):
        # Arquivo fonte (Excel local ou Google Sheets)
        if arquivo_fonte:
            self.arquivo_excel = Path(arquivo_fonte)
        else:
            self.arquivo_excel = Path(__file__).parent.parent / "saldo_devedor_presente-20250610-093716.xlsx"

        # Configurações Google Sheets conforme PDD
        self.usar_google_sheets = usar_google_sheets
        self.planilha_id = planilha_id
        self.cliente_sheets = None

        self.logs_regras: List[LogRegra] = []
        self.logger = self._configurar_logger()

    def _configurar_logger(self) -> logging.Logger:
        """Configura logger detalhado"""
        logger = logging.getLogger('TesteReplitDetalhado')
        logger.setLevel(logging.DEBUG)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Handler para arquivo
        file_handler = logging.FileHandler(f'teste_replit_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        file_handler.setLevel(logging.DEBUG)

        # Formato detalhado
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def log_regra(self, etapa: str, regra: str, criterio: str, valor_avaliado: Any, 
                  resultado: str, aprovado: bool, detalhes: Dict[str, Any] = None):
        """Registra log detalhado de uma regra"""
        log_entry = LogRegra(
            timestamp=datetime.now().isoformat(),
            etapa=etapa,
            regra=regra,
            criterio=criterio,
            valor_avaliado=valor_avaliado,
            resultado=resultado,
            aprovado=aprovado,
            detalhes=detalhes or {}
        )

        self.logs_regras.append(log_entry)

        # Log visual detalhado
        status_icon = "✅" if aprovado else "❌"
        self.logger.info(f"{status_icon} REGRA {etapa}: {regra}")
        self.logger.info(f"   📋 Critério: {criterio}")
        self.logger.info(f"   📊 Valor avaliado: {valor_avaliado}")
        self.logger.info(f"   🎯 Resultado: {resultado}")

        if detalhes:
            for chave, valor in detalhes.items():
                self.logger.debug(f"   🔍 {chave}: {valor}")

    async def _inicializar_google_sheets(self):
        """Inicializa cliente Google Sheets conforme PDD"""
        if not self.usar_google_sheets:
            return

        try:
            import gspread
            from google.oauth2.service_account import Credentials

            # Configuração conforme PDD
            SCOPES = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            # Busca credenciais
            creds_path = Path("gspread-credentials.json")
            if not creds_path.exists():
                creds_path = Path(__file__).parent.parent / "gspread-credentials.json"

            if creds_path.exists():
                creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
                self.cliente_sheets = gspread.authorize(creds)

                self.log_regra(
                    etapa="CONFIGURACAO_SHEETS",
                    regra="AUTENTICACAO_GOOGLE",
                    criterio="Credenciais Google devem estar configuradas",
                    valor_avaliado=str(creds_path),
                    resultado="Autenticado com sucesso",
                    aprovado=True,
                    detalhes={"arquivo_credenciais": str(creds_path)}
                )
            else:
                raise FileNotFoundError("Credenciais Google não encontradas")

        except Exception as e:
            self.log_regra(
                etapa="CONFIGURACAO_SHEETS",
                regra="AUTENTICACAO_GOOGLE",
                criterio="Credenciais Google devem estar configuradas",
                valor_avaliado="Google Sheets",
                resultado=f"ERRO: {str(e)}",
                aprovado=False,
                detalhes={"erro": str(e)}
            )
            raise

    async def carregar_dados_google_sheets(self) -> pd.DataFrame:
        """Carrega dados do Google Sheets conforme PDD seção 7.3"""
        try:
            self.logger.info("📊 CARREGANDO DADOS GOOGLE SHEETS")
            self.logger.info(f"   📋 Planilha ID: {self.planilha_id}")

            await self._inicializar_google_sheets()

            # Abre planilha conforme PDD
            planilha = self.cliente_sheets.open_by_key(self.planilha_id)

            # Busca aba "Saldo Devedor Presente" ou primeira aba
            try:
                worksheet = planilha.worksheet("Saldo Devedor Presente")
            except:
                worksheet = planilha.get_worksheet(0)

            # Carrega dados
            dados = worksheet.get_all_records()
            df = pd.DataFrame(dados)

            self.log_regra(
                etapa="CARREGAMENTO_SHEETS",
                regra="PLANILHA_GOOGLE_SHEETS",
                criterio="Planilha deve ser acessível e conter dados",
                valor_avaliado=f"ID: {self.planilha_id}",
                resultado=f"Carregada com sucesso - {len(df)} registros",
                aprovado=True,
                detalhes={
                    "planilha_id": self.planilha_id,
                    "aba_utilizada": worksheet.title,
                    "total_registros": len(df),
                    "colunas": list(df.columns)
                }
            )

            return df

        except Exception as e:
            self.log_regra(
                etapa="CARREGAMENTO_SHEETS",
                regra="PLANILHA_GOOGLE_SHEETS",
                criterio="Planilha deve ser acessível e conter dados",
                valor_avaliado=f"ID: {self.planilha_id}",
                resultado=f"ERRO: {str(e)}",
                aprovado=False,
                detalhes={"erro": str(e)}
            )
            raise

    async def carregar_dados_excel_real(self) -> pd.DataFrame:
        """Carrega dados do arquivo Excel real com logs detalhados"""
        try:
            self.logger.info("📊 CARREGANDO ARQUIVO EXCEL REAL")
            self.logger.info(f"   📁 Arquivo: {self.arquivo_excel}")

            if not self.arquivo_excel.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {self.arquivo_excel}")

            # Carrega Excel
            df = pd.read_excel(self.arquivo_excel)

            self.log_regra(
                etapa="CARREGAMENTO",
                regra="ARQUIVO_EXCEL_VALIDO",
                criterio="Arquivo deve existir e ser legível",
                valor_avaliado=str(self.arquivo_excel),
                resultado=f"Carregado com sucesso - {len(df)} registros",
                aprovado=True,
                detalhes={
                    "total_registros": len(df),
                    "colunas": list(df.columns),
                    "tamanho_arquivo": self.arquivo_excel.stat().st_size
                }
            )

            return df

        except Exception as e:
            self.log_regra(
                etapa="CARREGAMENTO",
                regra="ARQUIVO_EXCEL_VALIDO",
                criterio="Arquivo deve existir e ser legível",
                valor_avaliado=str(self.arquivo_excel),
                resultado=f"ERRO: {str(e)}",
                aprovado=False,
                detalhes={"erro": str(e)}
            )
            raise

    def analisar_dados_excel(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analisa dados do Excel aplicando regras PDD com logs detalhados"""

        self.logger.info("🔍 ANÁLISE DETALHADA DOS DADOS EXCEL")
        self.logger.info("=" * 60)

        # REGRA 1: Validação estrutura do arquivo
        colunas_obrigatorias = [
            'Número da parcela', 'Data de vencimento', 'Valor',
            'Tipo documento', 'Status'
        ]

        colunas_presentes = []
        colunas_ausentes = []

        for coluna in colunas_obrigatorias:
            # Busca coluna com variações
            coluna_encontrada = None
            for col_df in df.columns:
                if any(termo in col_df.lower() for termo in coluna.lower().split()):
                    coluna_encontrada = col_df
                    break

            if coluna_encontrada:
                colunas_presentes.append(coluna_encontrada)
            else:
                colunas_ausentes.append(coluna)

        self.log_regra(
            etapa="VALIDACAO_ESTRUTURA",
            regra="COLUNAS_OBRIGATORIAS",
            criterio="Arquivo deve conter colunas essenciais para processamento",
            valor_avaliado=colunas_presentes,
            resultado=f"Encontradas {len(colunas_presentes)}/{len(colunas_obrigatorias)} colunas",
            aprovado=len(colunas_ausentes) == 0,
            detalhes={
                "colunas_presentes": colunas_presentes,
                "colunas_ausentes": colunas_ausentes,
                "todas_colunas_arquivo": list(df.columns)
            }
        )

        # REGRA 2: Análise de tipos de documento
        tipos_documento = df['Tipo documento'].value_counts() if 'Tipo documento' in df.columns else {}

        for tipo, quantidade in tipos_documento.items():
            self.log_regra(
                etapa="ANALISE_DOCUMENTOS",
                regra="CONTAGEM_TIPO_DOCUMENTO",
                criterio=f"Identificar quantidade de documentos tipo {tipo}",
                valor_avaliado=quantidade,
                resultado=f"Encontrados {quantidade} documentos do tipo {tipo}",
                aprovado=True,
                detalhes={"tipo_documento": tipo, "quantidade": quantidade}
            )

        # REGRA 3: Análise de vencimentos (regra crítica PDD)
        data_atual = date.today()
        parcelas_vencidas = []
        parcelas_ct_vencidas = []
        parcelas_rec_fat = []

        for index, row in df.iterrows():
            try:
                # Processa data de vencimento
                data_venc_str = str(row.get('Data de vencimento', ''))
                tipo_doc = str(row.get('Tipo documento', ''))
                valor = float(row.get('Valor', 0))

                if '/' in data_venc_str:
                    data_venc = datetime.strptime(data_venc_str, '%d/%m/%Y').date()
                else:
                    continue

                # REGRA 3.1: Identificar parcelas vencidas
                if data_venc < data_atual:
                    parcela_info = {
                        "numero": str(row.get('Número da parcela', f'P{index+1}')),
                        "data_vencimento": data_venc,
                        "valor": valor,
                        "tipo_documento": tipo_doc,
                        "dias_vencido": (data_atual - data_venc).days
                    }

                    parcelas_vencidas.append(parcela_info)

                    self.log_regra(
                        etapa="ANALISE_VENCIMENTOS",
                        regra="PARCELA_VENCIDA_IDENTIFICADA",
                        criterio="Data vencimento < Data atual",
                        valor_avaliado=f"{data_venc} < {data_atual}",
                        resultado=f"Parcela vencida há {(data_atual - data_venc).days} dias",
                        aprovado=False,  # Vencida é negativo
                        detalhes=parcela_info
                    )

                    # REGRA 3.2: Classificar por tipo (crítico para PDD)
                    if tipo_doc == "CT":
                        parcelas_ct_vencidas.append(parcela_info)

                        self.log_regra(
                            etapa="CLASSIFICACAO_INADIMPLENCIA",
                            regra="PARCELA_CT_VENCIDA",
                            criterio="Parcela CT vencida conta para inadimplência",
                            valor_avaliado=parcela_info,
                            resultado="CT vencida - impacta elegibilidade",
                            aprovado=False,
                            detalhes={"impacto_inadimplencia": True}
                        )

                    elif tipo_doc in ["REC", "FAT"]:
                        parcelas_rec_fat.append(parcela_info)

                        self.log_regra(
                            etapa="CLASSIFICACAO_INADIMPLENCIA",
                            regra="PARCELA_REC_FAT_VENCIDA",
                            criterio="Parcela REC/FAT vencida NÃO impede reparcelamento",
                            valor_avaliado=parcela_info,
                            resultado="REC/FAT vencida - não impacta elegibilidade",
                            aprovado=True,
                            detalhes={"impacto_inadimplencia": False}
                        )

            except Exception as e:
                self.log_regra(
                    etapa="ANALISE_VENCIMENTOS",
                    regra="PROCESSAMENTO_LINHA",
                    criterio="Cada linha deve ser processável",
                    valor_avaliado=f"Linha {index}",
                    resultado=f"ERRO: {str(e)}",
                    aprovado=False,
                    detalhes={"erro": str(e), "linha": index}
                )

        # REGRA 4: Aplicação da regra crítica PDD (3 CT vencidas)
        qtd_ct_vencidas = len(parcelas_ct_vencidas)
        limite_inadimplencia = 3

        pode_reparcelar = qtd_ct_vencidas < limite_inadimplencia

        self.log_regra(
            etapa="VALIDACAO_ELEGIBILIDADE",
            regra="LIMITE_INADIMPLENCIA_PDD",
            criterio=f"Cliente com {limite_inadimplencia} ou mais parcelas CT vencidas = INADIMPLENTE",
            valor_avaliado=qtd_ct_vencidas,
            resultado=f"{'PODE' if pode_reparcelar else 'NÃO PODE'} reparcelar",
            aprovado=pode_reparcelar,
            detalhes={
                "qtd_ct_vencidas": qtd_ct_vencidas,
                "limite_pdd": limite_inadimplencia,
                "status_cliente": "ADIMPLENTE" if pode_reparcelar else "INADIMPLENTE",
                "parcelas_ct_detalhes": parcelas_ct_vencidas
            }
        )

        # REGRA 5: Cálculo do saldo total
        saldo_total = df['Valor'].sum() if 'Valor' in df.columns else 0.0

        self.log_regra(
            etapa="CALCULO_FINANCEIRO",
            regra="SALDO_TOTAL",
            criterio="Soma de todos os valores pendentes",
            valor_avaliado=saldo_total,
            resultado=f"R$ {saldo_total:,.2f}",
            aprovado=saldo_total > 0,
            detalhes={
                "saldo_formatado": f"R$ {saldo_total:,.2f}",
                "total_parcelas": len(df),
                "valor_medio_parcela": saldo_total / len(df) if len(df) > 0 else 0
            }
        )

        return {
            "saldo_total": saldo_total,
            "total_parcelas": len(df),
            "parcelas_vencidas": parcelas_vencidas,
            "parcelas_ct_vencidas": parcelas_ct_vencidas,
            "parcelas_rec_fat": parcelas_rec_fat,
            "pode_reparcelar": pode_reparcelar,
            "status_cliente": "ADIMPLENTE" if pode_reparcelar else "INADIMPLENTE",
            "dados_brutos": df
        }

    def calcular_reparcelamento_detalhado(self, dados_analise: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula reparcelamento aplicando regras PDD com logs detalhados"""

        self.logger.info("💰 CÁLCULO DETALHADO DO REPARCELAMENTO")
        self.logger.info("=" * 60)

        if not dados_analise.get("pode_reparcelar", False):
            self.log_regra(
                etapa="CALCULO_REPARCELAMENTO",
                regra="ELEGIBILIDADE_PREREQUISITO",
                criterio="Cliente deve estar apto para reparcelamento",
                valor_avaliado=dados_analise.get("status_cliente"),
                resultado="BLOQUEADO - cliente inadimplente",
                aprovado=False,
                detalhes={"motivo_bloqueio": "Cliente com 3 ou mais CT vencidas"}
            )
            return {"erro": "Cliente não elegível para reparcelamento"}

        # REGRA 6: Índices econômicos (sempre IGP-M conforme PDD)
        indices = {
            "ipca": {"valor": 4.62, "periodo": "Dezembro/2024"},
            "igpm": {"valor": 3.89, "periodo": "Dezembro/2024"}
        }

        indice_aplicado = "igpm"  # SEMPRE IGP-M conforme PDD
        valor_indice = indices[indice_aplicado]["valor"]

        self.log_regra(
            etapa="CALCULO_REPARCELAMENTO",
            regra="INDICE_ECONOMICO_PDD",
            criterio="SEMPRE usar IGP-M conforme especificação PDD",
            valor_avaliado=f"IGP-M: {valor_indice}%",
            resultado=f"Índice IGP-M {valor_indice}% será aplicado",
            aprovado=True,
            detalhes={
                "indice_escolhido": "IGP-M",
                "valor_percentual": valor_indice,
                "periodo_referencia": indices[indice_aplicado]["periodo"],
                "ipca_disponivel": indices["ipca"]["valor"],
                "motivo_escolha": "Obrigatório conforme PDD"
            }
        )

        # REGRA 7: Cálculo do novo saldo
        saldo_atual = dados_analise["saldo_total"]
        fator_correcao = 1 + (valor_indice / 100)
        novo_saldo = saldo_atual * fator_correcao
        diferenca_valor = novo_saldo - saldo_atual

        self.log_regra(
            etapa="CALCULO_REPARCELAMENTO",
            regra="CALCULO_NOVO_SALDO",
            criterio="Saldo atual × (1 + IGP-M/100)",
            valor_avaliado=f"R$ {saldo_atual:,.2f} × {fator_correcao:.4f}",
            resultado=f"R$ {novo_saldo:,.2f}",
            aprovado=novo_saldo > saldo_atual,
            detalhes={
                "saldo_anterior": saldo_atual,
                "fator_correcao": fator_correcao,
                "novo_saldo": novo_saldo,
                "diferenca_valor": diferenca_valor,
                "percentual_aumento": ((novo_saldo / saldo_atual - 1) * 100) if saldo_atual > 0 else 0
            }
        )

        # REGRA 8: Configurações obrigatórias PDD
        configuracoes_pdd = {
            "tipo_condicao": "PM",  # FIXO
            "indexador": "IGP-M",   # SEMPRE IGP-M
            "tipo_juros": "Fixo",   # FIXO
            "percentual_juros": 8.0  # FIXO 8%
        }

        for config, valor in configuracoes_pdd.items():
            self.log_regra(
                etapa="CONFIGURACAO_PDD",
                regra=f"PARAMETRO_{config.upper()}",
                criterio=f"Valor {config} deve ser fixo conforme PDD",
                valor_avaliado=valor,
                resultado=f"Configurado: {valor}",
                aprovado=True,
                detalhes={"parametro": config, "valor_configurado": valor}
            )

        # REGRA 9: Data primeiro vencimento
        data_atual = date.today()
        if data_atual.month == 12:
            data_primeiro_vencimento = date(data_atual.year + 1, 1, 15)
        else:
            data_primeiro_vencimento = date(data_atual.year, data_atual.month + 1, 15)

        self.log_regra(
            etapa="CONFIGURACAO_PDD",
            regra="DATA_PRIMEIRO_VENCIMENTO",
            criterio="Próximo mês, dia 15",
            valor_avaliado=data_primeiro_vencimento.strftime("%d/%m/%Y"),
            resultado=f"1º vencimento: {data_primeiro_vencimento.strftime('%d/%m/%Y')}",
            aprovado=True,
            detalhes={
                "data_calculada": data_primeiro_vencimento.isoformat(),
                "data_referencia": data_atual.isoformat(),
                "regra_aplicada": "Próximo mês dia 15"
            }
        )

        # REGRA 10: Quantidade de parcelas
        parcelas_pendentes = dados_analise.get("total_parcelas", 1)
        valor_parcela_estimado = novo_saldo / parcelas_pendentes if parcelas_pendentes > 0 else 0

        self.log_regra(
            etapa="CALCULO_REPARCELAMENTO",
            regra="QUANTIDADE_PARCELAS",
            criterio="Manter número de parcelas pendentes",
            valor_avaliado=parcelas_pendentes,
            resultado=f"{parcelas_pendentes} parcelas × R$ {valor_parcela_estimado:,.2f}",
            aprovado=parcelas_pendentes > 0,
            detalhes={
                "quantidade_parcelas": parcelas_pendentes,
                "valor_parcela_estimado": valor_parcela_estimado,
                "valor_total": novo_saldo
            }
        )

        # Resultado final do cálculo
        resultado_calculo = {
            **configuracoes_pdd,
            "valor_total": novo_saldo,
            "quantidade_parcelas": parcelas_pendentes,
            "data_primeiro_vencimento": data_primeiro_vencimento.strftime("%d/%m/%Y"),
            "detalhamento": f"CORREÇÃO IGP-M {datetime.now().strftime('%m/%Y')}",
            "indice_aplicado": valor_indice,
            "fator_correcao": fator_correcao,
            "saldo_anterior": saldo_atual,
            "diferenca_valor": diferenca_valor,
            "valor_parcela_estimado": valor_parcela_estimado,
            "data_calculo": datetime.now().isoformat()
        }

        return resultado_calculo

    async def _registrar_inicio_teste_mongodb(self):
        """Registra início do teste no MongoDB para auditoria"""
        try:
            from core.mongodb_manager import mongodb_manager

            documento_teste = {
                "tipo_teste": "teste_replit_detalhado",
                "timestamp_inicio": datetime.now(),
                "fonte_dados": "Google Sheets" if self.usar_google_sheets else str(self.arquivo_excel),
                "planilha_id": self.planilha_id if self.usar_google_sheets else None,
                "usuario_sistema": os.getenv('USER', 'sistema_rpa'),
                "status": "iniciado"
            }

            await mongodb_manager.conectar()
            result = await mongodb_manager.database.testes_executados.insert_one(documento_teste)

            self.logger.info(f"🗃️ Teste registrado no MongoDB: {result.inserted_id}")

        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao registrar teste no MongoDB: {str(e)}")

    async def _registrar_resultado_teste_mongodb(self, resultado: ResultadoProcessamento):
        """Registra resultado do teste no MongoDB"""
        try:
            from core.mongodb_manager import mongodb_manager

            # Atualiza documento do teste com resultado
            await mongodb_manager.database.testes_executados.update_one(
                {"usuario_sistema": os.getenv('USER', 'sistema_rpa'), "status": "iniciado"},
                {
                    "$set": {
                        "timestamp_fim": datetime.now(),
                        "status": "concluido",
                        "resultado_teste": {
                            "contrato": resultado.contrato,
                            "cliente": resultado.cliente,
                            "status_final": resultado.status_final,
                            "pode_reparcelar": resultado.pode_reparcelar,
                            "total_regras": len(resultado.logs_regras),
                            "regras_aprovadas": sum(1 for log in resultado.logs_regras if log.aprovado)
                        }
                    }
                }
            )

        except Exception as e:
            self.logger.warning(f"⚠️ Erro ao atualizar resultado no MongoDB: {str(e)}")

    async def executar_teste_completo(self) -> ResultadoProcessamento:
        """Executa teste completo com logs detalhados"""

        fonte_dados = "Google Sheets" if self.usar_google_sheets else self.arquivo_excel.name

        self.logger.info("🚀 INICIANDO TESTE REPLIT DETALHADO")
        self.logger.info("=" * 80)
        self.logger.info(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        self.logger.info(f"📁 Fonte dados: {fonte_dados}")
        if self.usar_google_sheets:
            self.logger.info(f"📋 Planilha ID: {self.planilha_id}")
        self.logger.info("=" * 80)

        try:
            # Registra inicio do teste no MongoDB
            await self._registrar_inicio_teste_mongodb()

            # Etapa 1: Carregar dados (Excel ou Google Sheets)
            if self.usar_google_sheets and self.planilha_id:
                df = await self.carregar_dados_google_sheets()
            else:
                df = await self.carregar_dados_excel_real()

            # Etapa 2: Analisar dados
            dados_analise = self.analisar_dados_excel(df)

            # Etapa 3: Calcular reparcelamento
            dados_calculados = self.calcular_reparcelamento_detalhado(dados_analise)

            # Etapa 4: Gerar resultado final
            resultado = ResultadoProcessamento(
                contrato="TESTE_REPLIT_001",
                cliente="CLIENTE TESTE EXCEL REAL",
                status_final=dados_analise.get("status_cliente", "ERRO"),
                pode_reparcelar=dados_analise.get("pode_reparcelar", False),
                logs_regras=self.logs_regras,
                dados_calculados=dados_calculados,
                timestamp_processamento=datetime.now().isoformat()
            )

            # Etapa 5: Retroalimentar Google Sheets (conforme PDD)
            if self.usar_google_sheets:
                await self.retroalimentar_google_sheets(resultado)

            # Registra resultado no MongoDB
            await self._registrar_resultado_teste_mongodb(resultado)

            # Log final resumido
            self._gerar_log_resumo_final(resultado)

            return resultado

        except Exception as e:
            self.log_regra(
                etapa="EXECUCAO_TESTE",
                regra="TESTE_COMPLETO",
                criterio="Teste deve executar sem erros",
                valor_avaliado="Execução completa",
                resultado=f"ERRO FATAL: {str(e)}",
                aprovado=False,
                detalhes={"erro_fatal": str(e)}
            )
            raise

    def _gerar_log_resumo_final(self, resultado: ResultadoProcessamento):
        """Gera log resumo final detalhado"""

        self.logger.info("\n📊 RESUMO FINAL DO TESTE")
        self.logger.info("=" * 60)
        self.logger.info(f"📋 Contrato: {resultado.contrato}")
        self.logger.info(f"👤 Cliente: {resultado.cliente}")
        self.logger.info(f"🎯 Status: {resultado.status_final}")
        self.logger.info(f"✅ Pode reparcelar: {'SIM' if resultado.pode_reparcelar else 'NÃO'}")

        # Estatísticas das regras
        total_regras = len(resultado.logs_regras)
        regras_aprovadas = sum(1 for log in resultado.logs_regras if log.aprovado)
        regras_reprovadas = total_regras - regras_aprovadas

        self.logger.info(f"📈 Regras processadas: {total_regras}")
        self.logger.info(f"✅ Regras aprovadas: {regras_aprovadas}")
        self.logger.info(f"❌ Regras reprovadas: {regras_reprovadas}")

        # Detalhes financeiros se calculados
        if resultado.pode_reparcelar and 'valor_total' in resultado.dados_calculados:
            dados = resultado.dados_calculados
            self.logger.info(f"💰 Novo saldo: R$ {dados['valor_total']:,.2f}")
            self.logger.info(f"📊 Parcelas: {dados['quantidade_parcelas']}")
            self.logger.info(f"📅 1º vencimento: {dados['data_primeiro_vencimento']}")
            self.logger.info(f"📈 Índice aplicado: IGP-M {dados['indice_aplicado']}%")

        self.logger.info("=" * 60)

    async def retroalimentar_google_sheets(self, resultado: ResultadoProcessamento):
        """
        Retroalimenta Google Sheets with resultados conforme PDDsection 7.3
        Atualiza status de processamento e resultados
        """
        if not self.usar_google_sheets or not self.planilha_id:
            return

        try:
            self.logger.info("🔄 RETROALIMENTANDO GOOGLE SHEETS")

            planilha = self.cliente_sheets.open_by_key(self.planilha_id)

            # Busca ou cria aba "Resultados Processamento"
            try:
                worksheet = planilha.worksheet("Resultados Processamento")
            except:
                worksheet = planilha.add_worksheet("Resultados Processamento", rows=1000, cols=20)
                # Cabeçalhos conforme PDD
                headers = [
                    "Timestamp", "Contrato", "Cliente", "Status Final", 
                    "Pode Reparcelar", "Novo Saldo", "Parcelas", 
                    "Primeiro Vencimento", "Indice Aplicado", "Observacoes"
                ]
                worksheet.append_row(headers)

            # Dados para retroalimentação
            dados_resultado = [
                resultado.timestamp_processamento,
                resultado.contrato,
                resultado.cliente,
                resultado.status_final,
                "SIM" if resultado.pode_reparcelar else "NÃO",
                resultado.dados_calculados.get('valor_total', 0) if resultado.pode_reparcelar else 0,
                resultado.dados_calculados.get('quantidade_parcelas', 0) if resultado.pode_reparcelar else 0,
                resultado.dados_calculados.get('data_primeiro_vencimento', '') if resultado.pode_reparcelar else '',
                resultado.dados_calculados.get('indice_aplicado', 0) if resultado.pode_reparcelar else 0,
                f"Regras: {len(resultado.logs_regras)} processadas"
            ]

            # Adiciona linha de resultado
            worksheet.append_row(dados_resultado)

            self.log_regra(
                etapa="RETROALIMENTACAO",
                regra="ATUALIZACAO_GOOGLE_SHEETS",
                criterio="Planilha deve ser atualizada com resultados conforme PDD",
                valor_avaliado="Resultado do processamento",
                resultado="Planilha atualizada com sucesso",
                aprovado=True,
                detalhes={
                    "planilha_id": self.planilha_id,
                    "aba_atualizada": "Resultados Processamento",
                    "dados_inseridos": len(dados_resultado)
                }
            )

        except Exception as e:
            self.log_regra(
                etapa="RETROALIMENTACAO",
                regra="ATUALIZACAO_GOOGLE_SHEETS",
                criterio="Planilha deve ser atualizada com resultados conforme PDD",
                valor_avaliado="Resultado do processamento",
                resultado=f"ERRO: {str(e)}",
                aprovado=False,
                detalhes={"erro": str(e)}
            )

    def salvar_relatorio_json(self, resultado: ResultadoProcessamento, arquivo: str = None):
        """Salva relatório detalhado em JSON"""
        if not arquivo:
            arquivo = f"relatorio_teste_replit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        fonte_dados = "Google Sheets" if self.usar_google_sheets else str(self.arquivo_excel)

        # Converte para dict serializável
        relatorio = {
            "metadados": {
                "fonte_dados": fonte_dados,
                "planilha_id": self.planilha_id if self.usar_google_sheets else None,
                "usar_google_sheets": self.usar_google_sheets,
                "timestamp_teste": datetime.now().isoformat(),
                "versao_teste": "2.0.0"
            },
            "resultado": asdict(resultado),
            "logs_detalhados": [asdict(log) for log in resultado.logs_regras]
        }

        with open(arquivo, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"📄 Relatório salvo em: {arquivo}")


async def main(arquivo_fonte: str = None, planilha_id: str = None):
    """
    Função principal do teste

    Args:
        arquivo_fonte: Caminho para arquivo Excel (opcional)
        planilha_id: ID da planilha Google Sheets (opcional)
    """

    print("🤖 TESTE REPLIT DETALHADO - RPA SIENGE")
    print("Simulação com logs precisos de cada regra PDD")

    # Determina fonte de dados
    usar_google_sheets = bool(planilha_id)

    if usar_google_sheets:
        print(f"📊 Fonte: Google Sheets (ID: {planilha_id})")
        print("🔄 Com retroalimentação conforme PDD")
    elif arquivo_fonte:
        print(f"📁 Fonte: {arquivo_fonte}")
    else:
        print("📁 Fonte: saldo_devedor_presente-20250610-093716.xlsx (padrão)")

    print("📋 Regras: PDD Reparcelamento Sienge")
    print()

    teste = TesteReplitDetalhado(
        arquivo_fonte=arquivo_fonte,
        usar_google_sheets=usar_google_sheets,
        planilha_id=planilha_id
    )

    try:
        # Executa teste completo
        resultado = await teste.executar_teste_completo()

        # Salva relatório
        teste.salvar_relatorio_json(resultado)

        # Resultado final
        if resultado.pode_reparcelar:
            print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            print(f"✅ Cliente PODE ser reparcelado")
            print(f"💰 Novo saldo: R$ {resultado.dados_calculados.get('valor_total', 0):,.2f}")
        else:
            print("\n⚠️ TESTE CONCLUÍDO - CLIENTE INADIMPLENTE")
            print(f"❌ Cliente NÃO PODE ser reparcelado")
            print(f"🚫 Status: {resultado.status_final}")

        print(f"📊 Total de regras verificadas: {len(resultado.logs_regras)}")
        print(f"📋 Logs detalhados salvos em arquivo")

        return True

    except Exception as e:
        print(f"\n💥 ERRO NO TESTE: {str(e)}")
        return False


if __name__ == "__main__":
    # Configurar event loop
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        resultado = asyncio.run(main())
        sys.exit(0 if resultado else 1)
    except KeyboardInterrupt:
        print("\n👋 Teste cancelado pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erro fatal: {str(e)}")
        sys.exit(1)