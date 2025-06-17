"""
REGRAS DE NEGÓCIO PDD - REPARCELAMENTO SIENGE
Implementação rigorosa das regras oficiais conforme PDD seção 7.3

Desenvolvido em Português Brasileiro
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Tuple
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
import logging

class RegraNegocioPDD:
    """
    Implementação das regras oficiais de negócio para reparcelamento
    Baseado no documento PDD_Reparcelamento_Sienge.pdf
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def aplicar_regras_completas(self, df_planilha: pd.DataFrame, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        Aplica todas as 8 regras PDD de forma sequencial e rigorosa
        
        Returns:
            Dict com resultado de todas as validações e cálculos
        """
        try:
            resultado = {
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "data_processamento": datetime.now().isoformat(),
                "regras_aplicadas": {}
            }
            
            # REGRA 1: Identificação do dia de vencimento
            resultado["regras_aplicadas"]["regra_1"] = self._regra_1_dia_vencimento(df_planilha)
            
            # REGRA 2: Cálculo primeiro vencimento
            resultado["regras_aplicadas"]["regra_2"] = self._regra_2_primeiro_vencimento(df_planilha)
            
            # REGRA 3: Valor da parcela atual
            resultado["regras_aplicadas"]["regra_3"] = self._regra_3_valor_parcela_atual(df_planilha)
            
            # REGRA 4: Verificação parcelas irregulares
            resultado["regras_aplicadas"]["regra_4"] = self._regra_4_parcelas_irregulares(df_planilha)
            
            # REGRA 5: Quantidade parcelas a vencer
            resultado["regras_aplicadas"]["regra_5"] = self._regra_5_parcelas_a_vencer(df_planilha)
            
            # REGRA 6: Quantidade parcelas vencidas CT
            resultado["regras_aplicadas"]["regra_6"] = self._regra_6_parcelas_vencidas_ct(df_planilha)
            
            # REGRA 7: Pendências REC/FAT
            resultado["regras_aplicadas"]["regra_7"] = self._regra_7_pendencias_rec_fat(df_planilha)
            
            # REGRA 8: Validação final de inadimplência
            resultado["regras_aplicadas"]["regra_8"] = self._regra_8_validacao_inadimplencia(
                resultado["regras_aplicadas"]["regra_6"]
            )
            
            # Consolidação dos resultados
            resultado.update(self._consolidar_resultados(resultado["regras_aplicadas"]))
            
            return resultado
            
        except Exception as e:
            return {
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "sucesso": False,
                "erro": f"Erro ao aplicar regras PDD: {str(e)}",
                "data_processamento": datetime.now().isoformat()
            }
    
    def _regra_1_dia_vencimento(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 1 PDD: Identificação do Dia de Vencimento das Parcelas
        
        Extrai o dia comum de vencimento das parcelas "a vencer"
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
    
    def _regra_2_primeiro_vencimento(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        REGRA 2 PDD: Cálculo do 1º Vencimento do Novo Carnê
        
        Define data do primeiro vencimento baseado no tipo de reajuste
        """
        try:
            hoje = date.today()
            
            # Para reparcelamento, usa próximo mês no dia 15
            proximo_mes = hoje.replace(day=1) + timedelta(days=32)
            primeiro_vencimento = proximo_mes.replace(day=15)
            
            return {
                "sucesso": True,
                "data_primeiro_vencimento": primeiro_vencimento.isoformat(),
                "data_primeiro_vencimento_formatada": primeiro_vencimento.strftime("%d/%m/%Y"),
                "tipo_reajuste": "reparcelamento",
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
        
        Identifica valor base das parcelas do contrato
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
        
        Identifica parcelas com valores diferentes do padrão
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
        
        Conta parcelas CT e REC/FAT pendentes
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
        
        Identifica parcelas CT vencidas e não quitadas (crítico para inadimplência)
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
                        
                        parcelas_ct_vencidas.append({
                            "documento": row.get("Documento"),
                            "data_vencimento": data_venc_date.isoformat(),
                            "status": status,
                            "valor": valor,
                            "dias_atraso": (hoje - data_venc_date).days
                        })
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
        
        Identifica pendências administrativas (não impedem reparcelamento)
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
    
    def _regra_8_validacao_inadimplencia(self, regra_6_resultado: Dict[str, Any]) -> Dict[str, Any]:
        """
        REGRA 8 PDD: Validação Final de Inadimplência
        
        Aplica regra crítica: ≥3 CT vencidas = INADIMPLENTE
        """
        try:
            qtd_ct_vencidas = regra_6_resultado.get("quantidade_ct_vencidas", 0)
            
            # REGRA RIGOROSA PDD: ≥3 CT vencidas = INADIMPLENTE
            if qtd_ct_vencidas >= 3:
                status = "INADIMPLENTE"
                pode_reparcelar = False
                motivo = f"Cliente possui {qtd_ct_vencidas} parcelas CT vencidas (≥3 limite PDD)"
                nivel_risco = "ALTO"
            else:
                status = "ADIMPLENTE"
                pode_reparcelar = True
                motivo = f"Cliente possui {qtd_ct_vencidas} parcelas CT vencidas (<3 limite PDD)"
                nivel_risco = "BAIXO" if qtd_ct_vencidas == 0 else "MEDIO"
            
            return {
                "sucesso": True,
                "status_cliente": status,
                "pode_reparcelar": pode_reparcelar,
                "motivo_classificacao": motivo,
                "nivel_risco": nivel_risco,
                "quantidade_ct_vencidas": qtd_ct_vencidas,
                "limite_pdd": 3,
                "regra_aplicada": "PDD_7.3.2_limite_inadimplencia"
            }
            
        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "status_cliente": "ERRO",
                "pode_reparcelar": False
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
            validacao_final = regras_aplicadas["regra_8"]
            
            return {
                "sucesso": True,
                
                # Dados principais do contrato
                "dia_vencimento_parcelas": dia_vencimento,
                "valor_parcela_base": valor_parcela_base,
                "data_primeiro_vencimento": primeiro_vencimento,
                
                # Análise de irregularidades
                "tem_parcelas_irregulares": irregularidades.get("tem_irregularidades", False),
                "quantidade_irregulares": irregularidades.get("quantidade_irregulares", 0),
                "parcelas_irregulares": irregularidades.get("parcelas_irregulares", []),
                
                # Contagens de parcelas
                "qtd_parcelas_ct_a_vencer": parcelas_info.get("quantidade_ct_a_vencer", 0),
                "qtd_parcelas_rec_fat_a_vencer": parcelas_info.get("quantidade_rec_fat_a_vencer", 0),
                "qtd_ct_vencidas": ct_vencidas_info.get("quantidade_ct_vencidas", 0),
                "qtd_pendencias_rec_fat": pendencias_info.get("quantidade_pendencias_rec_fat", 0),
                
                # Valores financeiros
                "saldo_total": parcelas_info.get("saldo_total", 0),
                "valor_total_ct": parcelas_info.get("valor_total_ct", 0),
                "valor_total_rec_fat": parcelas_info.get("valor_total_rec_fat", 0),
                "valor_total_vencido": ct_vencidas_info.get("valor_total_vencido", 0),
                
                # Classificação final (CRÍTICO)
                "status_cliente": validacao_final.get("status_cliente"),
                "pode_reparcelar": validacao_final.get("pode_reparcelar"),
                "motivo_status": validacao_final.get("motivo_classificacao"),
                "nivel_risco": validacao_final.get("nivel_risco"),
                
                # Dados para planilha base de cálculo
                "pendencias_sienge_inad": ct_vencidas_info.get("quantidade_ct_vencidas") if ct_vencidas_info.get("quantidade_ct_vencidas", 0) > 0 else None,
                "pendencias_sienge": pendencias_info.get("quantidade_pendencias_rec_fat") if pendencias_info.get("quantidade_pendencias_rec_fat", 0) > 0 else None,
                "parcelas_a_vencer": parcelas_info.get("quantidade_ct_a_vencer", 0),
                
                # Detalhes para auditoria
                "parcelas_ct_vencidas_detalhes": ct_vencidas_info.get("parcelas_ct_vencidas_detalhes", []),
                "pendencias_rec_fat_detalhes": pendencias_info.get("pendencias_detalhes", []),
                "parcelas_ct_a_vencer_detalhes": parcelas_info.get("parcelas_ct_detalhes", []),
                "parcelas_rec_fat_a_vencer_detalhes": parcelas_info.get("parcelas_rec_fat_detalhes", []),
                
                # Metadados
                "regras_pdd_aplicadas": "REGRAS_NEGOCIO_COMPLETAS_V2",
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

    def calcular_valores_reparcelamento(self, saldo_atual: float, indice_igpm: float, 
                                       parcelas_pendentes: int) -> Dict[str, Any]:
        """
        Calcula valores para reparcelamento conforme regras PDD
        
        Args:
            saldo_atual: Saldo devedor atual
            indice_igpm: Índice IGP-M em percentual (ex: 3.89 para 3,89%)
            parcelas_pendentes: Quantidade de parcelas a vencer
            
        Returns:
            Valores calculados para preenchimento no Sienge
        """
        try:
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
            
            # Detalhes do cálculo
            detalhes_calculo = {
                "saldo_anterior": saldo_atual,
                "indice_igpm_aplicado": indice_igpm,
                "fator_correcao": fator_correcao,
                "novo_saldo": novo_saldo,
                "diferenca_correcao": novo_saldo - saldo_atual,
                "parcelas_total": parcelas_pendentes,
                "data_calculo": hoje.isoformat(),
                "formula_aplicada": f"{saldo_atual} × {fator_correcao} = {novo_saldo}"
            }
            
            return {
                "sucesso": True,
                "valores_sienge": valores_sienge,
                "detalhes_calculo": detalhes_calculo,
                "validacao_pdd": True
            }
            
        except Exception as e:
            return {
                "sucesso": False,
                "erro": f"Erro no cálculo: {str(e)}",
                "valores_sienge": {},
                "detalhes_calculo": {}
            }

    def determinar_parcelas_desmarcar(self, parcelas_ct_a_vencer: List[Dict]) -> List[Dict]:
        """
        Determina quais parcelas devem ser desmarcadas conforme regras PDD
        
        Args:
            parcelas_ct_a_vencer: Lista de parcelas CT pendentes
            
        Returns:
            Lista de parcelas para desmarcar no webscraping
        """
        try:
            hoje = date.today()
            mes_vigente = hoje.replace(day=1)  # Primeiro dia do mês atual
            
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
                
                # REGRA PDD: Desmarcar se vencimento <= mês vigente
                if data_obj <= mes_vigente:
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