"""
PROCESSADOR REGRAS PDD - CONSOLIDADO
Implementação completa de todas as regras de negócio PDD para reparcelamento Sienge
Consolida validação de inadimplência e regras 9.1.1

Desenvolvido em Português Brasileiro
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
import logging

class ProcessadorRegrasNegocio:
    """
    Processador consolidado de todas as regras PDD para reparcelamento

    RESPONSABILIDADES:
    - Validação rigorosa de inadimplência (≥3 CT vencidas = INADIMPLENTE)
    - Implementação das 8 regras PDD seção 9.1.1
    - Cálculos financeiros de reparcelamento
    - Determinação de parcelas para desmarcar
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.limite_inadimplencia = 3  # REGRA CRÍTICA PDD

    def processar_dados_cliente(self, df_planilha: pd.DataFrame, cliente: str, 
                               numero_titulo: str, dados_validacao_base: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Processa todos os dados do cliente aplicando regras PDD completas

        Args:
            df_planilha: DataFrame com dados do Sienge
            cliente: Nome do cliente
            numero_titulo: Número do título
            dados_validacao_base: Dados de validação prévia (opcional)

        Returns:
            Dict com resultado completo de todas as validações e regras
        """
        try:
            self.logger.info(f"Processando regras PDD para cliente: {cliente}")

            # VALIDAÇÃO ESTRUTURAL INICIAL
            if df_planilha.empty:
                return self._retorno_erro("Planilha vazia", cliente, numero_titulo)

            validacao_estrutura = self._validar_estrutura_planilha(df_planilha)
            if not validacao_estrutura["valida"]:
                return self._retorno_erro(f"Estrutura inválida: {validacao_estrutura['motivo']}", cliente, numero_titulo)

            # APLICAR REGRA CRÍTICA DE INADIMPLÊNCIA PRIMEIRO
            validacao_inadimplencia = self._aplicar_regra_inadimplencia(df_planilha)

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
            self.logger.info("Cliente adimplente - aplicando regras 9.1.1")

            resultado_regras = {
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "data_processamento": datetime.now().isoformat(),
                "regras_aplicadas": {}
            }

            # REGRA 1: Identificação do dia de vencimento
            resultado_regras["regras_aplicadas"]["regra_1"] = self._regra_1_dia_vencimento(df_planilha)

            # REGRA 2: Cálculo primeiro vencimento
            resultado_regras["regras_aplicadas"]["regra_2"] = self._regra_2_primeiro_vencimento(df_planilha)

            # REGRA 3: Valor da parcela atual
            resultado_regras["regras_aplicadas"]["regra_3"] = self._regra_3_valor_parcela_atual(df_planilha)

            # REGRA 4: Verificação parcelas irregulares
            resultado_regras["regras_aplicadas"]["regra_4"] = self._regra_4_parcelas_irregulares(df_planilha)

            # REGRA 5: Quantidade parcelas a vencer
            resultado_regras["regras_aplicadas"]["regra_5"] = self._regra_5_parcelas_a_vencer(df_planilha)

            # REGRA 6: Quantidade parcelas vencidas CT
            resultado_regras["regras_aplicadas"]["regra_6"] = self._regra_6_parcelas_vencidas_ct(df_planilha)

            # REGRA 7: Pendências REC/FAT
            resultado_regras["regras_aplicadas"]["regra_7"] = self._regra_7_pendencias_rec_fat(df_planilha)

            # REGRA 8: Validação final de inadimplência (confirmação)
            resultado_regras["regras_aplicadas"]["regra_8"] = validacao_inadimplencia

            # CONSOLIDAÇÃO DOS RESULTADOS
            resultado_consolidado = self._consolidar_resultados(resultado_regras["regras_aplicadas"])

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

    def validar_cliente_inadimplencia(self, df_planilha: pd.DataFrame, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        Aplica APENAS validação rigorosa de inadimplência conforme PDD

        Args:
            df_planilha: DataFrame com dados do Sienge
            cliente: Nome do cliente
            numero_titulo: Número do título

        Returns:
            Dict com resultado da validação de inadimplência
        """
        try:
            resultado = {
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "data_validacao": datetime.now().isoformat(),
                "sucesso": True
            }

            # VALIDAR ESTRUTURA DA PLANILHA
            validacao_estrutura = self._validar_estrutura_planilha(df_planilha)
            if not validacao_estrutura["valida"]:
                resultado.update({
                    "sucesso": False,
                    "erro": f"Estrutura inválida: {validacao_estrutura['motivo']}",
                    "pode_reparcelar": False,
                    "status_cliente": "ERRO_DADOS"
                })
                return resultado

            # APLICAR REGRA CRÍTICA DE INADIMPLÊNCIA
            validacao_inadimplencia = self._aplicar_regra_inadimplencia(df_planilha)

            # CALCULAR VALORES FINANCEIROS
            valores_financeiros = self._calcular_valores_financeiros(df_planilha)

            # CONSOLIDAR RESULTADO
            resultado.update({
                **validacao_inadimplencia,
                **valores_financeiros,
                "regra_aplicada": "PDD_7.3.2_limite_3_CT_vencidas"
            })

            return resultado

        except Exception as e:
            self.logger.error(f"Erro na validação: {str(e)}")
            return {
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "sucesso": False,
                "erro": f"Erro na validação: {str(e)}",
                "pode_reparcelar": False,
                "status_cliente": "ERRO_PROCESSAMENTO"
            }

    def _validar_estrutura_planilha(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Valida se a planilha tem a estrutura esperada do Sienge"""
        try:
            if df.empty:
                return {"valida": False, "motivo": "Planilha vazia"}

            colunas_obrigatorias = [
                "Status da parcela", "Documento", "Data vencimento", "Valor a receber"
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

    def _aplicar_regra_inadimplencia(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Aplica regra crítica PDD: ≥3 CT vencidas = INADIMPLENTE
        """
        try:
            hoje = date.today()

            # Filtrar apenas parcelas CT
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
                    quitada = status in ["QUITADA", "LIQUIDADA", "PAGA", "BAIXADA"]
                    a_vencer = status in ["A VENCER", "PENDENTE", "EM ABERTO"]

                    # Só conta como CT vencida se: data passou E não está quitada E não está marcada como "A VENCER"
                    if vencida and not quitada and not a_vencer:
                        valor = 0
                        try:
                            valor_str = str(row.get("Valor a receber", "0")).replace(",", ".")
                            valor = float(valor_str)
                        except:
                            pass

                        ct_vencidas.append({
                            "documento": row.get("Documento"),
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

    def _calcular_valores_financeiros(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calcula valores financeiros para o reparcelamento"""
        try:
            # Parcelas CT a vencer
            parcelas_ct_a_vencer = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER|PENDENTE", na=False)) &
                (df["Documento"].str.contains("CT", case=False, na=False))
            ]

            # Parcelas REC/FAT a vencer
            parcelas_rec_fat_a_vencer = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER|PENDENTE", na=False)) &
                (df["Documento"].str.contains("REC|FAT", case=False, na=False))
            ]

            # Calcular valores
            valor_ct = 0
            for _, row in parcelas_ct_a_vencer.iterrows():
                try:
                    valor_str = str(row.get("Valor a receber", "0")).replace(",", ".")
                    valor_ct += float(valor_str)
                except:
                    continue

            valor_rec_fat = 0
            for _, row in parcelas_rec_fat_a_vencer.iterrows():
                try:
                    valor_str = str(row.get("Valor a receber", "0")).replace(",", ".")
                    valor_rec_fat += float(valor_str)
                except:
                    continue

            return {
                "qtd_parcelas_ct_a_vencer": len(parcelas_ct_a_vencer),
                "qtd_parcelas_rec_fat_a_vencer": len(parcelas_rec_fat_a_vencer),
                "valor_total_ct": valor_ct,
                "valor_total_rec_fat": valor_rec_fat,
                "saldo_total": valor_ct + valor_rec_fat,
                "parcelas_ct_a_vencer": parcelas_ct_a_vencer.to_dict('records') if not parcelas_ct_a_vencer.empty else [],
                "parcelas_rec_fat_a_vencer": parcelas_rec_fat_a_vencer.to_dict('records') if not parcelas_rec_fat_a_vencer.empty else []
            }

        except Exception as e:
            return {
                "qtd_parcelas_ct_a_vencer": 0,
                "qtd_parcelas_rec_fat_a_vencer": 0,
                "valor_total_ct": 0,
                "valor_total_rec_fat": 0,
                "saldo_total": 0,
                "parcelas_ct_a_vencer": [],
                "parcelas_rec_fat_a_vencer": [],
                "erro_calculo": str(e)
            }

    # ============= REGRAS 9.1.1 COMPLETAS =============

    def _regra_1_dia_vencimento(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 1 PDD: Identificação do Dia de Vencimento das Parcelas
        """
        try:
            # Filtrar apenas parcelas a vencer
            parcelas_a_vencer = df[
                df["Status da parcela"].str.upper().str.contains("VENCER|PENDENTE", na=False)
            ].copy()

            if parcelas_a_vencer.empty:
                return {
                    "sucesso": False,
                    "motivo": "Nenhuma parcela a vencer encontrada",
                    "dia_vencimento": None
                }

            # Extrair dias de vencimento
            dias_vencimento = []
            for _, row in parcelas_a_vencer.iterrows():
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
                "distribuicao_dias": {dia: dias_vencimento.count(dia) for dia in set(dias_vencimento)}
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "dia_vencimento": None
            }

    def _regra_2_primeiro_vencimento(self, df: pd.DataFrame, tipo_reajuste: str = "ANUAL", 
                                   dia_aniversario: int = None, mes_base_reparcelamento: int = None) -> Dict[str, Any]:
        """
        REGRA 2 PDD: Cálculo do 1º Vencimento do Novo Carnê conforme documento 9.1.1
        """
        try:
            hoje = date.today()

            # Obter dia de vencimento das parcelas
            regra_1 = self._regra_1_dia_vencimento(df)
            dia_vencimento = regra_1.get("dia_vencimento", 15)

            # Determinar mês base se não fornecido
            if mes_base_reparcelamento is None:
                mes_base_reparcelamento = hoje.month

            if tipo_reajuste.upper() == "ANUAL":
                # REGRA ANUAL: Mesmo mês base do reparcelamento
                primeiro_vencimento = date(hoje.year, mes_base_reparcelamento, dia_vencimento)
                if primeiro_vencimento < hoje:
                    primeiro_vencimento = primeiro_vencimento.replace(year=hoje.year + 1)

                observacao = f"Tipo Anual: 1º vencimento no mês base {mes_base_reparcelamento}"

            elif tipo_reajuste.upper() == "ANIVERSARIO":
                # REGRA ANIVERSÁRIO: Depende se vence antes ou após aniversário
                if dia_aniversario is None:
                    dia_aniversario = 1  # Default se não informado

                if dia_vencimento < dia_aniversario:
                    # Vence ANTES do aniversário → próximo mês
                    proximo_mes = mes_base_reparcelamento + 1
                    if proximo_mes > 12:
                        proximo_mes = 1
                        ano = hoje.year + 1
                    else:
                        ano = hoje.year
                    primeiro_vencimento = date(ano, proximo_mes, dia_vencimento)
                    observacao = f"Tipo Aniversário: Vencimento antes do dia {dia_aniversario} → mês seguinte"
                else:
                    # Vence APÓS o aniversário → mesmo mês base
                    primeiro_vencimento = date(hoje.year, mes_base_reparcelamento, dia_vencimento)
                    if primeiro_vencimento < hoje:
                        primeiro_vencimento = primeiro_vencimento.replace(year=hoje.year + 1)
                    observacao = f"Tipo Aniversário: Vencimento após o dia {dia_aniversario} → mesmo mês"
            else:
                # Fallback para reparcelamento simples
                proximo_mes = hoje.replace(day=1) + timedelta(days=32)
                primeiro_vencimento = proximo_mes.replace(day=dia_vencimento)
                observacao = "Tipo padrão: próximo mês disponível"

            return {
                "sucesso": True,
                "data_primeiro_vencimento": primeiro_vencimento.isoformat(),
                "data_primeiro_vencimento_formatada": primeiro_vencimento.strftime("%d/%m/%Y"),
                "tipo_reajuste": tipo_reajuste,
                "dia_vencimento_usado": dia_vencimento,
                "mes_base_reparcelamento": mes_base_reparcelamento,
                "dia_aniversario": dia_aniversario,
                "observacao_regra": observacao,
                "dias_ate_vencimento": (primeiro_vencimento - hoje).days
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "data_primeiro_vencimento": None
            }

    def _regra_3_valor_parcela_atual(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 3 PDD: Valor da Parcela Atual
        """
        try:
            # Filtrar parcelas CT a vencer
            parcelas_ct = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER|PENDENTE", na=False)) &
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
                "distribuicao_valores": {v: valores.count(v) for v in set(valores)}
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "valor_parcela_base": 0
            }

    def _regra_4_parcelas_irregulares(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 4 PDD: Verificação de Parcelas Abertas Irregulares
        """
        try:
            valor_base_info = self._regra_3_valor_parcela_atual(df)
            valor_base = valor_base_info.get("valor_parcela_base", 0)

            if valor_base == 0:
                return {
                    "sucesso": False,
                    "motivo": "Valor base não determinado",
                    "parcelas_irregulares": []
                }

            # Filtrar parcelas CT a vencer
            parcelas_ct = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER|PENDENTE", na=False)) &
                (df["Documento"].str.contains("CT", case=False, na=False))
            ].copy()

            parcelas_irregulares = []
            for _, row in parcelas_ct.iterrows():
                try:
                    valor_original = float(str(row.get("Valor original", "0")).replace(",", "."))
                    tipo_condicao = str(row.get("Tipo condição", "")).strip().upper()

                    # Tolerância de 1% para diferenças
                    diferenca_percentual = abs(valor_original - valor_base) / valor_base * 100

                    if diferenca_percentual > 1 and tipo_condicao != "PARCELA MENSAL":
                        parcelas_irregulares.append({
                            "documento": row.get("Documento"),
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

    def _regra_5_parcelas_a_vencer(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 5 PDD: Quantidade de Parcelas a Vencer
        """
        try:
            # Parcelas CT a vencer
            parcelas_ct = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER|PENDENTE", na=False)) &
                (df["Documento"].str.contains("CT", case=False, na=False))
            ]

            # Parcelas REC/FAT a vencer
            parcelas_rec_fat = df[
                (df["Status da parcela"].str.upper().str.contains("VENCER|PENDENTE", na=False)) &
                (df["Documento"].str.contains("REC|FAT", case=False, na=False))
            ]

            # Calcular valores
            valor_ct = 0
            for _, row in parcelas_ct.iterrows():
                try:
                    valor = float(str(row.get("Valor a receber", "0")).replace(",", "."))
                    valor_ct += valor
                except:
                    continue

            valor_rec_fat = 0
            for _, row in parcelas_rec_fat.iterrows():
                try:
                    valor = float(str(row.get("Valor a receber", "0")).replace(",", "."))
                    valor_rec_fat += valor
                except:
                    continue

            return {
                "sucesso": True,
                "quantidade_ct_a_vencer": len(parcelas_ct),
                "quantidade_rec_fat_a_vencer": len(parcelas_rec_fat),
                "valor_total_ct": valor_ct,
                "valor_total_rec_fat": valor_rec_fat,
                "saldo_total": valor_ct + valor_rec_fat,
                "parcelas_ct_detalhes": parcelas_ct.to_dict('records'),
                "parcelas_rec_fat_detalhes": parcelas_rec_fat.to_dict('records')
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "quantidade_ct_a_vencer": 0,
                "quantidade_rec_fat_a_vencer": 0
            }

    def _regra_6_parcelas_vencidas_ct(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 6 PDD: Quantidade de Parcelas Vencidas CT
        """
        try:
            hoje = date.today()

            # Filtrar todas as parcelas CT
            todas_parcelas_ct = df[
                df["Documento"].str.contains("CT", case=False, na=False)
            ].copy()

            parcelas_ct_vencidas = []

            for _, row in todas_parcelas_ct.iterrows():
                try:
                    # Verificar data de vencimento
                    data_venc = pd.to_datetime(row["Data vencimento"], errors='coerce')
                    if pd.isna(data_venc):
                        continue

                    data_venc_date = data_venc.date()
                    status = str(row.get("Status da parcela", "")).strip().upper()

                    # Critério rigoroso: vencida E não quitada
                    vencida = data_venc_date < hoje
                    quitada = status in ["QUITADA", "LIQUIDADA", "PAGA", "BAIXADA"]

                    if vencida and not quitada:
                        valor = 0
                        try:
                            valor = float(str(row.get("Valor a receber", "0")).replace(",", "."))
                        except:
                            pass

                        parcela_info = {
                            "documento": row.get("Documento"),
                            "data_vencimento": data_venc_date.isoformat(),
                            "status": status,
                            "valor": valor,
                            "dias_atraso": (hoje - data_venc_date).days
                        }

                        parcelas_ct_vencidas.append(parcela_info)

                except:
                    continue

            quantidade_vencidas = len(parcelas_ct_vencidas)

            return {
                "sucesso": True,
                "quantidade_ct_vencidas": quantidade_vencidas,
                "parcelas_ct_vencidas_detalhes": parcelas_ct_vencidas,
                "valor_total_vencido": sum(p["valor"] for p in parcelas_ct_vencidas),
                "data_analise": hoje.isoformat()
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "quantidade_ct_vencidas": 0
            }

    def _regra_7_pendencias_rec_fat(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 7 PDD: Pendências REC/FAT
        """
        try:
            hoje = date.today()

            # Filtrar parcelas REC/FAT
            parcelas_rec_fat = df[
                df["Documento"].str.contains("REC|FAT", case=False, na=False)
            ].copy()

            pendencias_vencidas = []
            for _, row in parcelas_rec_fat.iterrows():
                try:
                    data_venc = pd.to_datetime(row["Data vencimento"], errors='coerce')
                    if pd.isna(data_venc):
                        continue

                    data_venc_date = data_venc.date()
                    status = str(row.get("Status da parcela", "")).strip().upper()

                    # Vencida e não quitada
                    vencida = data_venc_date < hoje
                    quitada = status in ["QUITADA", "LIQUIDADA", "PAGA", "BAIXADA"]

                    if vencida and not quitada:
                        valor = 0
                        try:
                            valor = float(str(row.get("Valor a receber", "0")).replace(",", "."))
                        except:
                            pass

                        pendencias_vencidas.append({
                            "documento": row.get("Documento"),
                            "data_vencimento": data_venc_date.isoformat(),
                            "status": status,
                            "valor": valor,
                            "tipo": "REC" if "REC" in str(row.get("Documento", "")) else "FAT"
                        })
                except:
                    continue

            return {
                "sucesso": True,
                "quantidade_pendencias_rec_fat": len(pendencias_vencidas),
                "pendencias_detalhes": pendencias_vencidas,
                "valor_total_pendencias": sum(p["valor"] for p in pendencias_vencidas),
                "observacao": "Pendências REC/FAT não impedem reparcelamento (PDD 7.3.2)"
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "quantidade_pendencias_rec_fat": 0
            }

    def _consolidar_resultados(self, regras_aplicadas: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consolida resultados de todas as regras em um formato estruturado
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

                # Dados principais do contrato
                "dia_vencimento": dia_vencimento,
                "valor_parcela_atual": valor_parcela_base,
                "primeiro_vencimento_carne": primeiro_vencimento,

                # Análise de irregularidades
                "tem_parcelas_irregulares": irregularidades.get("tem_irregularidades", False),
                "quantidade_irregulares": irregularidades.get("quantidade_irregulares", 0),
                "parcelas_divergentes": irregularidades.get("parcelas_irregulares", []),

                # Contagens de parcelas
                "qtd_parcelas_ct_a_vencer": parcelas_info.get("quantidade_ct_a_vencer", 0),
                "qtd_parcelas_rec_fat_a_vencer": parcelas_info.get("quantidade_rec_fat_a_vencer", 0),
                "qtd_pendencias_rec_fat": pendencias_info.get("quantidade_pendencias_rec_fat", 0),

                # Valores financeiros
                "saldo_total": parcelas_info.get("saldo_total", 0),
                "valor_total_ct": parcelas_info.get("valor_total_ct", 0),
                "valor_total_rec_fat": parcelas_info.get("valor_total_rec_fat", 0),
                "valor_total_vencido": ct_vencidas_info.get("valor_total_vencido", 0),

                # Detalhes para auditoria
                "parcelas_ct_vencidas_detalhes": ct_vencidas_info.get("parcelas_ct_vencidas_detalhes", []),
                "pendencias_rec_fat_detalhes": pendencias_info.get("pendencias_detalhes", []),
                "parcelas_ct_a_vencer_detalhes": parcelas_info.get("parcelas_ct_detalhes", []),
                "parcelas_rec_fat_a_vencer_detalhes": parcelas_info.get("parcelas_rec_fat_detalhes", []),

                # Tipo de reajuste (pode ser determinado posteriormente)
                "tipo_reajuste": "ANUAL",  # Default - pode ser customizado

                # Metadados
                "regras_pdd_aplicadas": "REGRAS_COMPLETAS_9_1_1",
                "total_regras_aplicadas": 8,
                "todas_regras_sucesso": all(
                    regra.get("sucesso", False) for regra in regras_aplicadas.values()
                )
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
        Busca IGPM no MongoDB se não fornecido
        """
        try:
            # Se IGPM não foi fornecido, tentar buscar no MongoDB
            if indice_igpm is None:
                #indice_igpm = await self._obter_igpm_mongodb()
                from core.data_manager import DataManager
                data_manager = DataManager()
                indice_igpm = await data_manager.obter_igpm_mais_recente()

                if indice_igpm is None:
                    return {
                        "sucesso": False,
                        "erro": "IGPM não disponível",
                        "acao_requerida": "EXECUTAR_RPA_COLETA_INDICES",
                        "mensagem": "Execute o RPA de Coleta de Índices para obter o valor atual do IGPM"
                    }

            # Aplicar correção IGP-M
            fator_correcao = 1 + (indice_igpm / 100)
            novo_saldo = saldo_atual * fator_correcao

            # Arredondar para 2 casas decimais
            novo_saldo = float(Decimal(str(novo_saldo)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

            # Data primeiro vencimento (próximo mês, dia 15)
            hoje = date.today()
            primeiro_vencimento = (hoje.replace(day=1) + timedelta(days=32)).replace(day=15)

            # Valores para preenchimento no Sienge
            valores_sienge = {
                "detalhamento": f"CORREÇÃO {hoje.strftime('%m/%y')}",
                "tipo_condicao": "PM",  # Prazo Mensal
                "valor_total": novo_saldo,
                "quantidade_parcelas": parcelas_pendentes,
                "data_primeiro_vencimento": primeiro_vencimento.strftime("%d/%m/%Y"),
                "portador": "1 Carteira",
                "operacao_cobranca": "0 Cobrança em Carteira",
                "indexador": "1 IGP-M",
                "tipo_juros": "Fixo",
                "percentual_juros": 8.0,
                "data_base_juros": primeiro_vencimento.strftime("%d/%m/%Y")
            }

            return {
                "sucesso": True,
                "valores_sienge": valores_sienge,
                "novo_saldo": novo_saldo,
                "fator_correcao": fator_correcao,
                "diferenca_correcao": novo_saldo - saldo_atual,
                "igpm_utilizado": indice_igpm,
                "fonte_igpm": "mongodb" if indice_igpm else "parametro"
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": f"Erro no cálculo: {str(e)}"
            }

    # Método removido - agora usa data_manager.obter_igpm_mais_recente() centralizado
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
        return self.processador.validar_cliente_inadimplencia(df_planilha, cliente, numero_titulo)


class CalculadoraReparcelamentoPDD:
    """Wrapper de compatibilidade - usa ProcessadorRegrasNegocio"""

    def __init__(self):
        self.processador = ProcessadorRegrasNegocio()

    async def calcular_valores_sienge(self, saldo_atual: float, indice_igpm: float, parcelas_pendentes: int) -> Dict[str, Any]:
        return await self.processador.calcular_valores_reparcelamento(saldo_atual, indice_igpm, parcelas_pendentes)

    def determinar_parcelas_desmarcar(self, parcelas_ct_a_vencer: List[Dict]) -> List[Dict]:
        return self.processador.determinar_parcelas_desmarcar(parcelas_ct_a_vencer)