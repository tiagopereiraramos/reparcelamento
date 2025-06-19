
"""
PROCESSADOR REGRAS PDD - CENTRALIZADO
Implementação completa de todas as regras de negócio PDD para reparcelamento Sienge
Centralizado na pasta core para acesso por todos os RPAs

Desenvolvido em Português Brasileiro
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
import logging

class ProcessadorRegrasNegocio:
    """
    Processador centralizado de todas as regras PDD para reparcelamento

    RESPONSABILIDADES:
    - Validação rigorosa de inadimplência (≥3 CT vencidas = INADIMPLENTE)
    - Implementação das 8 regras PDD seção 9.1.1
    - Cálculos financeiros de reparcelamento
    - Determinação de parcelas para desmarcar
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.limite_inadimplencia = 3  # REGRA CRÍTICA PDD

    def processar_dados_cliente_completo(self, df_planilha: pd.DataFrame, cliente: str, 
                                       numero_titulo: str, dados_validacao_base: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Processa todos os dados do cliente aplicando TODAS as regras PDD 9.1.1

        Args:
            df_planilha: DataFrame com dados do Sienge (formato CSV real)
            cliente: Nome do cliente
            numero_titulo: Número do título
            dados_validacao_base: Dados de validação prévia (opcional)

        Returns:
            Dict com resultado completo de todas as validações e regras
        """
        try:
            self.logger.info(f"🔍 Processando regras PDD COMPLETAS para cliente: {cliente}")

            # VALIDAÇÃO ESTRUTURAL INICIAL
            if df_planilha.empty:
                return self._retorno_erro("Planilha vazia", cliente, numero_titulo)

            validacao_estrutura = self._validar_estrutura_planilha_csv(df_planilha)
            if not validacao_estrutura["valida"]:
                return self._retorno_erro(f"Estrutura inválida: {validacao_estrutura['motivo']}", cliente, numero_titulo)

            # APLICAR REGRA CRÍTICA DE INADIMPLÊNCIA PRIMEIRO
            validacao_inadimplencia = self._aplicar_regra_inadimplencia_csv(df_planilha)

            # SE INADIMPLENTE, RETORNAR IMEDIATAMENTE (NÃO PROCESSAR OUTRAS REGRAS)
            if not validacao_inadimplencia.get("pode_reparcelar", False):
                resultado_final = {
                    "cliente": cliente,
                    "numero_titulo": numero_titulo,
                    "data_processamento": datetime.now().isoformat(),
                    "sucesso": True,
                    **validacao_inadimplencia,
                    "regras_pdd_aplicadas": "INADIMPLENCIA_DETECTADA",
                    "processamento_interrompido": True,
                    "motivo_interrupcao": "Cliente inadimplente - não pode reparcelar"
                }
                return resultado_final

            # CLIENTE ADIMPLENTE: APLICAR REGRAS COMPLETAS 9.1.1
            self.logger.info("✅ Cliente adimplente - aplicando regras completas 9.1.1")

            resultado_regras = {
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "data_processamento": datetime.now().isoformat(),
                "regras_aplicadas": {}
            }

            # REGRA 1: Identificação do dia de vencimento
            resultado_regras["regras_aplicadas"]["regra_1"] = self._regra_1_dia_vencimento_csv(df_planilha)

            # REGRA 2: Cálculo primeiro vencimento
            resultado_regras["regras_aplicadas"]["regra_2"] = self._regra_2_primeiro_vencimento_csv(df_planilha)

            # REGRA 3: Valor da parcela atual
            resultado_regras["regras_aplicadas"]["regra_3"] = self._regra_3_valor_parcela_atual_csv(df_planilha)

            # REGRA 4: Verificação parcelas irregulares
            resultado_regras["regras_aplicadas"]["regra_4"] = self._regra_4_parcelas_irregulares_csv(df_planilha)

            # REGRA 5: Quantidade parcelas a vencer
            resultado_regras["regras_aplicadas"]["regra_5"] = self._regra_5_parcelas_a_vencer_csv(df_planilha)

            # REGRA 6: Quantidade parcelas vencidas CT
            resultado_regras["regras_aplicadas"]["regra_6"] = self._regra_6_parcelas_vencidas_ct_csv(df_planilha)

            # REGRA 7: Pendências REC/FAT/IPTU
            resultado_regras["regras_aplicadas"]["regra_7"] = self._regra_7_pendencias_rec_fat_iptu_csv(df_planilha)

            # REGRA 8: Validação final de inadimplência (confirmação)
            resultado_regras["regras_aplicadas"]["regra_8"] = validacao_inadimplencia

            # CONSOLIDAÇÃO DOS RESULTADOS
            resultado_consolidado = self._consolidar_resultados_completos(resultado_regras["regras_aplicadas"])

            # COMBINAR COM DADOS DE INADIMPLÊNCIA
            resultado_consolidado.update(validacao_inadimplencia)
            resultado_consolidado["regras_pdd_aplicadas"] = "REGRAS_COMPLETAS_9_1_1"
            resultado_consolidado["total_regras_aplicadas"] = 8
            resultado_consolidado["processamento_completo"] = True

            return resultado_consolidado

        except Exception as e:
            erro_msg = f"Erro ao processar regras PDD: {str(e)}"
            self.logger.error(erro_msg)
            return self._retorno_erro(erro_msg, cliente, numero_titulo)

    def _validar_estrutura_planilha_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Valida se a planilha CSV tem a estrutura esperada do Sienge"""
        try:
            if df.empty:
                return {"valida": False, "motivo": "Planilha vazia"}

            # Colunas obrigatórias conforme CSV real do Sienge
            colunas_obrigatorias = [
                "Título", "Parcela/Condição", "Documento", "Cliente", 
                "Status da parcela", "Data vencimento", "Valor a receber"
            ]

            colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
            if colunas_faltantes:
                return {
                    "valida": False, 
                    "motivo": f"Colunas ausentes: {colunas_faltantes}"
                }

            return {"valida": True, "total_registros": len(df)}

        except Exception as e:
            return {"valida": False, "motivo": f"Erro na validação: {str(e)}"}

    def _aplicar_regra_inadimplencia_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Aplica regra crítica PDD usando CSV real: ≥3 CT vencidas = INADIMPLENTE
        """
        try:
            hoje = date.today()

            # Filtrar apenas parcelas CT usando coluna "Documento"
            parcelas_ct = df[
                df["Documento"].str.contains("CT", case=False, na=False)
            ].copy()

            # Identificar CT vencidas e não quitadas
            ct_vencidas = []
            for _, row in parcelas_ct.iterrows():
                try:
                    # Converter data
                    data_venc = pd.to_datetime(row["Data vencimento"], errors='coerce')
                    if pd.isna(data_venc):
                        continue

                    data_venc_date = data_venc.date()
                    status = str(row.get("Status da parcela", "")).strip().upper()

                    # Critério rigoroso: vencida E não quitada
                    vencida = data_venc_date < hoje
                    quitada = status in ["PAGA", "QUITADA", "LIQUIDADA", "BAIXADA"]
                    a_vencer = status in ["A VENCER", "PENDENTE", "EM ABERTO"]

                    # Só conta como CT vencida se: data passou E não está quitada
                    if vencida and not quitada:
                        valor = 0
                        try:
                            valor_str = str(row.get("Valor a receber", "0")).replace(",", ".")
                            valor = float(valor_str) if valor_str else 0
                        except:
                            pass

                        ct_vencidas.append({
                            "documento": row.get("Documento"),
                            "parcela_condicao": row.get("Parcela/Condição"),
                            "data_vencimento": data_venc_date.isoformat(),
                            "status": status,
                            "valor": valor,
                            "dias_atraso": (hoje - data_venc_date).days
                        })
                except:
                    continue

            qtd_ct_vencidas = len(ct_vencidas)

            # APLICAR REGRA RIGOROSA PDD
            if qtd_ct_vencidas >= self.limite_inadimplencia:
                status_cliente = "INADIMPLENTE"
                pode_reparcelar = False
                motivo = f"Cliente possui {qtd_ct_vencidas} parcelas CT vencidas (≥{self.limite_inadimplencia} limite PDD)"
                nivel_risco = "ALTO"
            else:
                status_cliente = "ADIMPLENTE"
                pode_reparcelar = True
                motivo = f"Cliente possui {qtd_ct_vencidas} parcelas CT vencidas (<{self.limite_inadimplencia} limite PDD)"
                nivel_risco = "BAIXO" if qtd_ct_vencidas == 0 else "MEDIO"

            return {
                "status_cliente": status_cliente,
                "pode_reparcelar": pode_reparcelar,
                "motivo_classificacao": motivo,
                "nivel_risco": nivel_risco,
                "qtd_ct_vencidas": qtd_ct_vencidas,
                "ct_vencidas_detalhes": ct_vencidas,
                "limite_pdd": self.limite_inadimplencia
            }

        except Exception as e:
            return {
                "status_cliente": "ERRO",
                "pode_reparcelar": False,
                "motivo_classificacao": f"Erro na validação: {str(e)}",
                "qtd_ct_vencidas": 0,
                "ct_vencidas_detalhes": []
            }

    # ============= REGRAS 9.1.1 COMPLETAS ADAPTADAS PARA CSV =============

    def _regra_1_dia_vencimento_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 1 PDD: Identificação do Dia de Vencimento das Parcelas CT A VENCER
        """
        try:
            # Filtrar apenas parcelas CT a vencer
            parcelas_ct_a_vencer = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER", na=False)) &
                (df["Documento"].str.contains("CT", case=False, na=False))
            ].copy()

            if parcelas_ct_a_vencer.empty:
                return {
                    "sucesso": False,
                    "motivo": "Nenhuma parcela CT a vencer encontrada",
                    "dia_vencimento": None
                }

            # Extrair dias de vencimento
            dias_vencimento = []
            for _, row in parcelas_ct_a_vencer.iterrows():
                data_venc = pd.to_datetime(row["Data vencimento"], errors='coerce')
                if pd.notna(data_venc):
                    dias_vencimento.append(data_venc.day)

            if not dias_vencimento:
                return {
                    "sucesso": False,
                    "motivo": "Datas de vencimento inválidas",
                    "dia_vencimento": None
                }

            # Determinar dia mais comum
            dia_comum = max(set(dias_vencimento), key=dias_vencimento.count)

            return {
                "sucesso": True,
                "dia_vencimento": dia_comum,
                "total_parcelas_analisadas": len(dias_vencimento),
                "distribuicao_dias": {dia: dias_vencimento.count(dia) for dia in set(dias_vencimento)},
                "parcelas_ct_a_vencer": len(parcelas_ct_a_vencer)
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "dia_vencimento": None
            }

    def _regra_2_primeiro_vencimento_csv(self, df: pd.DataFrame, tipo_reajuste: str = "ANUAL") -> Dict[str, Any]:
        """
        REGRA 2 PDD: Cálculo do 1º Vencimento do Novo Carnê
        """
        try:
            hoje = date.today()

            # Obter dia de vencimento das parcelas
            regra_1 = self._regra_1_dia_vencimento_csv(df)
            dia_vencimento = regra_1.get("dia_vencimento", 5)  # Padrão dia 5 conforme CSV

            # Próximo mês disponível
            proximo_mes = hoje.replace(day=1) + timedelta(days=32)
            primeiro_vencimento = proximo_mes.replace(day=dia_vencimento)

            # Se a data já passou no mês atual, usar o mês seguinte
            if primeiro_vencimento <= hoje:
                primeiro_vencimento = (primeiro_vencimento.replace(day=1) + timedelta(days=32)).replace(day=dia_vencimento)

            return {
                "sucesso": True,
                "data_primeiro_vencimento": primeiro_vencimento.isoformat(),
                "data_primeiro_vencimento_formatada": primeiro_vencimento.strftime("%d/%m/%Y"),
                "tipo_reajuste": tipo_reajuste,
                "dia_vencimento_usado": dia_vencimento,
                "observacao_regra": f"Próximo vencimento no dia {dia_vencimento}",
                "dias_ate_vencimento": (primeiro_vencimento - hoje).days
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "data_primeiro_vencimento": None
            }

    def _regra_3_valor_parcela_atual_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 3 PDD: Valor da Parcela Atual CT (usando Valor original)
        """
        try:
            # Filtrar parcelas CT a vencer
            parcelas_ct = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER", na=False)) &
                (df["Documento"].str.contains("CT", case=False, na=False))
            ].copy()

            if parcelas_ct.empty:
                return {
                    "sucesso": False,
                    "motivo": "Nenhuma parcela CT a vencer encontrada",
                    "valor_parcela_base": 0
                }

            # Converter valores para numérico
            valores = []
            for _, row in parcelas_ct.iterrows():
                try:
                    valor_str = str(row.get("Valor original", "0")).replace(",", ".")
                    valor = float(valor_str)
                    if valor > 0:
                        valores.append(valor)
                except:
                    continue

            if not valores:
                return {
                    "sucesso": False,
                    "motivo": "Valores de parcela inválidos",
                    "valor_parcela_base": 0
                }

            # Valor mais comum (moda)
            valor_base = max(set(valores), key=valores.count)

            return {
                "sucesso": True,
                "valor_parcela_base": valor_base,
                "total_parcelas_analisadas": len(valores),
                "valor_minimo": min(valores),
                "valor_maximo": max(valores),
                "valores_unicos": len(set(valores)),
                "valor_mais_comum": valor_base
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "valor_parcela_base": 0
            }

    def _regra_4_parcelas_irregulares_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 4 PDD: Verificação de Parcelas CT com Valores Irregulares
        """
        try:
            valor_base_info = self._regra_3_valor_parcela_atual_csv(df)
            valor_base = valor_base_info.get("valor_parcela_base", 0)

            if valor_base == 0:
                return {
                    "sucesso": False,
                    "motivo": "Valor base não determinado",
                    "parcelas_irregulares": []
                }

            # Filtrar parcelas CT a vencer
            parcelas_ct = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER", na=False)) &
                (df["Documento"].str.contains("CT", case=False, na=False))
            ].copy()

            parcelas_irregulares = []
            for _, row in parcelas_ct.iterrows():
                try:
                    valor_original = float(str(row.get("Valor original", "0")).replace(",", "."))
                    tipo_condicao = str(row.get("Tipo condição", "")).strip()

                    # Tolerância de 1% para diferenças
                    if valor_base > 0:
                        diferenca_percentual = abs(valor_original - valor_base) / valor_base * 100

                        if diferenca_percentual > 1:
                            parcelas_irregulares.append({
                                "documento": row.get("Documento"),
                                "parcela_condicao": row.get("Parcela/Condição"),
                                "data_vencimento": row.get("Data vencimento"),
                                "valor_original": valor_original,
                                "valor_base": valor_base,
                                "tipo_condicao": tipo_condicao,
                                "diferenca_absoluta": valor_original - valor_base,
                                "diferenca_percentual": diferenca_percentual
                            })
                except:
                    continue

            return {
                "sucesso": True,
                "tem_irregularidades": len(parcelas_irregulares) > 0,
                "quantidade_irregulares": len(parcelas_irregulares),
                "parcelas_irregulares": parcelas_irregulares,
                "valor_base_referencia": valor_base
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "parcelas_irregulares": []
            }

    def _regra_5_parcelas_a_vencer_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 5 PDD: Quantidade de Parcelas a Vencer (CT e IPTU)
        """
        try:
            # Parcelas CT a vencer
            parcelas_ct = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER", na=False)) &
                (df["Documento"].str.contains("CT", case=False, na=False))
            ]

            # Parcelas IPTU a vencer
            parcelas_iptu = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER", na=False)) &
                (df["Documento"].str.contains("IPTU", case=False, na=False))
            ]

            # Calcular valores
            valor_ct = 0
            for _, row in parcelas_ct.iterrows():
                try:
                    valor = float(str(row.get("Valor a receber", "0")).replace(",", "."))
                    valor_ct += valor
                except:
                    continue

            valor_iptu = 0
            for _, row in parcelas_iptu.iterrows():
                try:
                    valor = float(str(row.get("Valor a receber", "0")).replace(",", "."))
                    valor_iptu += valor
                except:
                    continue

            return {
                "sucesso": True,
                "quantidade_ct_a_vencer": len(parcelas_ct),
                "quantidade_iptu_a_vencer": len(parcelas_iptu),
                "valor_total_ct": valor_ct,
                "valor_total_iptu": valor_iptu,
                "saldo_total": valor_ct + valor_iptu,
                "parcelas_ct_detalhes": parcelas_ct.to_dict('records'),
                "parcelas_iptu_detalhes": parcelas_iptu.to_dict('records')
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "quantidade_ct_a_vencer": 0,
                "quantidade_iptu_a_vencer": 0
            }

    def _regra_6_parcelas_vencidas_ct_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 6 PDD: Quantidade de Parcelas Vencidas CT (já implementada no método de inadimplência)
        """
        return self._aplicar_regra_inadimplencia_csv(df)

    def _regra_7_pendencias_rec_fat_iptu_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 7 PDD: Pendências IPTU e outros tipos (REC/FAT se existirem)
        """
        try:
            hoje = date.today()

            # Filtrar parcelas IPTU vencidas
            parcelas_iptu_vencidas = []
            parcelas_iptu = df[df["Documento"].str.contains("IPTU", case=False, na=False)]

            for _, row in parcelas_iptu.iterrows():
                try:
                    data_venc = pd.to_datetime(row["Data vencimento"], errors='coerce')
                    if pd.isna(data_venc):
                        continue

                    data_venc_date = data_venc.date()
                    status = str(row.get("Status da parcela", "")).strip().upper()

                    # Vencida e não paga
                    vencida = data_venc_date < hoje
                    quitada = status in ["PAGA", "QUITADA", "LIQUIDADA", "BAIXADA"]

                    if vencida and not quitada:
                        valor = 0
                        try:
                            valor = float(str(row.get("Valor a receber", "0")).replace(",", "."))
                        except:
                            pass

                        parcelas_iptu_vencidas.append({
                            "documento": row.get("Documento"),
                            "data_vencimento": data_venc_date.isoformat(),
                            "status": status,
                            "valor": valor,
                            "tipo": "IPTU"
                        })
                except:
                    continue

            return {
                "sucesso": True,
                "quantidade_pendencias_iptu": len(parcelas_iptu_vencidas),
                "pendencias_iptu_detalhes": parcelas_iptu_vencidas,
                "valor_total_pendencias": sum(p["valor"] for p in parcelas_iptu_vencidas),
                "observacao": "Pendências IPTU não impedem reparcelamento (PDD 7.3.2)"
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "quantidade_pendencias_iptu": 0
            }

    def _consolidar_resultados_completos(self, regras_aplicadas: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consolida resultados de todas as regras 9.1.1 em formato estruturado
        """
        try:
            # Extrair dados principais
            dia_vencimento = regras_aplicadas["regra_1"].get("dia_vencimento")
            primeiro_vencimento = regras_aplicadas["regra_2"].get("data_primeiro_vencimento_formatada")
            valor_parcela_base = regras_aplicadas["regra_3"].get("valor_parcela_base", 0)

            irregularidades = regras_aplicadas["regra_4"]
            parcelas_info = regras_aplicadas["regra_5"]
            ct_vencidas_info = regras_aplicadas["regra_6"]
            pendencias_info = regras_aplicadas["regra_7"]

            return {
                "sucesso": True,

                # DADOS PRINCIPAIS DO CONTRATO (9.1.1)
                "dia_vencimento": dia_vencimento,
                "valor_parcela_atual": valor_parcela_base,
                "primeiro_vencimento_carne": primeiro_vencimento,

                # ANÁLISE DE IRREGULARIDADES
                "tem_parcelas_irregulares": irregularidades.get("tem_irregularidades", False),
                "quantidade_irregulares": irregularidades.get("quantidade_irregulares", 0),
                "parcelas_divergentes": irregularidades.get("parcelas_irregulares", []),

                # CONTAGENS DE PARCELAS
                "qtd_parcelas_ct_a_vencer": parcelas_info.get("quantidade_ct_a_vencer", 0),
                "qtd_parcelas_iptu_a_vencer": parcelas_info.get("quantidade_iptu_a_vencer", 0),
                "qtd_pendencias_iptu": pendencias_info.get("quantidade_pendencias_iptu", 0),

                # VALORES FINANCEIROS
                "saldo_total": parcelas_info.get("saldo_total", 0),
                "valor_total_ct": parcelas_info.get("valor_total_ct", 0),
                "valor_total_iptu": parcelas_info.get("valor_total_iptu", 0),
                "valor_total_vencido": ct_vencidas_info.get("valor_total_vencido", 0),

                # DETALHES PARA AUDITORIA
                "parcelas_ct_vencidas_detalhes": ct_vencidas_info.get("ct_vencidas_detalhes", []),
                "pendencias_iptu_detalhes": pendencias_info.get("pendencias_iptu_detalhes", []),
                "parcelas_ct_a_vencer_detalhes": parcelas_info.get("parcelas_ct_detalhes", []),
                "parcelas_iptu_a_vencer_detalhes": parcelas_info.get("parcelas_iptu_detalhes", []),

                # CONFIGURAÇÕES PDD FIXAS
                "tipo_reajuste": "ANUAL",
                "indexador": "IGP-M",
                "juros_fixo": 8.0,
                "tipo_condicao": "PM",

                # METADADOS
                "regras_pdd_aplicadas": "REGRAS_COMPLETAS_9_1_1",
                "total_regras_aplicadas": 8,
                "todas_regras_sucesso": all(
                    regra.get("sucesso", False) for regra in regras_aplicadas.values()
                ),
                "timestamp_processamento": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": f"Erro na consolidação: {str(e)}"
            }

    # ============= CÁLCULOS FINANCEIROS =============

    async def calcular_valores_reparcelamento(self, saldo_atual: float, indice_igpm: float = None, 
                                       parcelas_pendentes: int = 0) -> Dict[str, Any]:
        """
        Calcula valores para reparcelamento conforme regras PDD
        """
        try:
            # Se IGPM não foi fornecido, tentar buscar no MongoDB
            if indice_igpm is None:
                from core.data_manager import DataManager
                data_manager = DataManager()
                indice_igpm = await data_manager.obter_igpm_mais_recente()

                if indice_igpm is None:
                    return {
                        "sucesso": False,
                        "erro": "IGPM não disponível",
                        "acao_requerida": "EXECUTAR_RPA_COLETA_INDICES"
                    }

            # Aplicar correção IGP-M
            fator_correcao = 1 + (indice_igpm / 100)
            novo_saldo = saldo_atual * fator_correcao
            novo_saldo = float(Decimal(str(novo_saldo)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

            # Data primeiro vencimento (próximo mês, dia 15)
            hoje = date.today()
            primeiro_vencimento = (hoje.replace(day=1) + timedelta(days=32)).replace(day=15)

            # Valores para preenchimento no Sienge
            valores_sienge = {
                "detalhamento": f"CORREÇÃO {hoje.strftime('%m/%y')}",
                "tipo_condicao": "PM",
                "valor_total": novo_saldo,
                "quantidade_parcelas": parcelas_pendentes,
                "data_primeiro_vencimento": primeiro_vencimento.strftime("%d/%m/%Y"),
                "indexador": "1 IGP-M",
                "tipo_juros": "Fixo",
                "percentual_juros": 8.0
            }

            return {
                "sucesso": True,
                "valores_sienge": valores_sienge,
                "novo_saldo": novo_saldo,
                "fator_correcao": fator_correcao,
                "diferenca_correcao": novo_saldo - saldo_atual,
                "igpm_utilizado": indice_igpm
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": f"Erro no cálculo: {str(e)}"
            }

    def determinar_parcelas_desmarcar(self, parcelas_ct_a_vencer: List[Dict]) -> List[Dict]:
        """
        Determina quais parcelas devem ser desmarcadas conforme regras PDD
        """
        try:
            hoje = date.today()
            parcelas_desmarcar = []

            for parcela in parcelas_ct_a_vencer:
                data_vencimento = parcela.get("Data vencimento")

                # Converter data
                if isinstance(data_vencimento, str):
                    data_obj = pd.to_datetime(data_vencimento, errors='coerce')
                    if pd.notna(data_obj):
                        data_obj = data_obj.date()
                    else:
                        continue
                else:
                    data_obj = data_vencimento

                # REGRA PDD: Desmarcar se vencimento <= hoje
                if data_obj <= hoje:
                    parcelas_desmarcar.append({
                        "documento": parcela.get("Documento"),
                        "data_vencimento": data_obj.strftime("%d/%m/%Y"),
                        "valor": parcela.get("Valor a receber", 0),
                        "motivo": "Vencimento igual ou anterior ao mês vigente (PDD)"
                    })

            return parcelas_desmarcar

        except Exception as e:
            self.logger.error(f"Erro ao determinar parcelas para desmarcar: {str(e)}")
            return []

    def _retorno_erro(self, erro: str, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """Helper para retornos de erro padronizados"""
        return {
            "cliente": cliente,
            "numero_titulo": numero_titulo,
            "sucesso": False,
            "erro": erro,
            "pode_reparcelar": False,
            "status_cliente": "ERRO_PROCESSAMENTO",
            "data_processamento": datetime.now().isoformat()
        }


# ============= CLASSES LEGACY PARA COMPATIBILIDADE =============

class ValidadorInadimplenciaPDD:
    """Wrapper de compatibilidade - usa ProcessadorRegrasNegocio"""

    def __init__(self):
        self.processador = ProcessadorRegrasNegocio()

    def validar_cliente(self, df_planilha: pd.DataFrame, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        return self.processador._aplicar_regra_inadimplencia_csv(df_planilha)


class CalculadoraReparcelamentoPDD:
    """Wrapper de compatibilidade - usa ProcessadorRegrasNegocio"""

    def __init__(self):
        self.processador = ProcessadorRegrasNegocio()

    async def calcular_valores_sienge(self, saldo_atual: float, indice_igpm: float, parcelas_pendentes: int) -> Dict[str, Any]:
        return await self.processador.calcular_valores_reparcelamento(saldo_atual, indice_igpm, parcelas_pendentes)

    def determinar_parcelas_desmarcar(self, parcelas_ct_a_vencer: List[Dict]) -> List[Dict]:
        return self.processador.determinar_parcelas_desmarcar(parcelas_ct_a_vencer)
