"""
VALIDADOR DE INADIMPLÊNCIA PDD - REGRAS CRÍTICAS
Implementação rigorosa da regra principal: ≥3 CT vencidas = INADIMPLENTE

Desenvolvido em Português Brasileiro
"""

from datetime import datetime, date
from typing import Dict, Any, List
import pandas as pd
import logging

class ValidadorInadimplenciaPDD:
    """
    Validador rigoroso de inadimplência conforme PDD seção 7.3.2
    
    REGRA PRINCIPAL:
    Cliente com 3 ou mais parcelas CT vencidas = INADIMPLENTE (não pode reparcelar)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validar_cliente(self, df_planilha: pd.DataFrame, cliente: str, numero_titulo: str) -> Dict[str, Any]:
        """
        Aplica validação rigorosa de inadimplência conforme PDD
        
        Args:
            df_planilha: DataFrame com dados do Sienge
            cliente: Nome do cliente
            numero_titulo: Número do título
            
        Returns:
            Dict com resultado da validação e dados estruturados
        """
        try:
            resultado = {
                "cliente": cliente,
                "numero_titulo": numero_titulo,
                "data_validacao": datetime.now().isoformat(),
                "sucesso": True
            }
            
            # PASSO 1: Validar estrutura da planilha
            validacao_estrutura = self._validar_estrutura_planilha(df_planilha)
            if not validacao_estrutura["valida"]:
                resultado.update({
                    "sucesso": False,
                    "erro": f"Estrutura inválida: {validacao_estrutura['motivo']}",
                    "pode_reparcelar": False,
                    "status_cliente": "ERRO_DADOS"
                })
                return resultado
            
            # PASSO 2: Aplicar regra crítica de inadimplência
            validacao_inadimplencia = self._aplicar_regra_inadimplencia(df_planilha)
            
            # PASSO 3: Calcular valores financeiros
            valores_financeiros = self._calcular_valores_financeiros(df_planilha)
            
            # PASSO 4: Consolidar resultado
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
            if qtd_ct_vencidas >= 3:
                status_cliente = "INADIMPLENTE"
                pode_reparcelar = False
                motivo = f"Cliente possui {qtd_ct_vencidas} parcelas CT vencidas (≥3 limite PDD)"
                nivel_risco = "ALTO"
            else:
                status_cliente = "ADIMPLENTE"
                pode_reparcelar = True
                motivo = f"Cliente possui {qtd_ct_vencidas} parcelas CT vencidas (<3 limite PDD)"
                nivel_risco = "BAIXO" if qtd_ct_vencidas == 0 else "MEDIO"
            
            return {
                "status_cliente": status_cliente,
                "pode_reparcelar": pode_reparcelar,
                "motivo_classificacao": motivo,
                "nivel_risco": nivel_risco,
                "qtd_ct_vencidas": qtd_ct_vencidas,
                "ct_vencidas_detalhes": ct_vencidas,
                "limite_pdd": 3
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

class CalculadoraReparcelamentoPDD:
    """
    Calculadora para valores de reparcelamento conforme regras PDD
    """
    
    def calcular_valores_sienge(self, saldo_atual: float, indice_igpm: float, 
                               parcelas_pendentes: int) -> Dict[str, Any]:
        """
        Calcula valores para preenchimento no Sienge
        
        Args:
            saldo_atual: Saldo devedor atual
            indice_igpm: Índice IGP-M em percentual (ex: 3.89)
            parcelas_pendentes: Quantidade de parcelas a vencer
            
        Returns:
            Valores calculados para webscraping
        """
        try:
            # Aplicar correção IGP-M obrigatória
            fator_correcao = 1 + (indice_igpm / 100)
            novo_saldo = round(saldo_atual * fator_correcao, 2)
            
            # Data primeiro vencimento (próximo mês, dia 15)
            hoje = date.today()
            if hoje.month == 12:
                primeiro_vencimento = date(hoje.year + 1, 1, 15)
            else:
                primeiro_vencimento = date(hoje.year, hoje.month + 1, 15)
            
            # Valores para preenchimento no Sienge (RESPONSABILIDADE DO USUÁRIO)
            valores_sienge = {
                "detalhamento": f"CORREÇÃO {hoje.strftime('%m/%y')}",
                "tipo_condicao": "PM",  # Prazo Mensal - OBRIGATÓRIO PDD
                "valor_total": novo_saldo,
                "quantidade_parcelas": parcelas_pendentes,
                "data_primeiro_vencimento": primeiro_vencimento.strftime("%d/%m/%Y"),
                "portador": "1 Carteira",
                "operacao_cobranca": "0 Cobrança em Carteira",
                "indexador": "1 IGP-M",  # SEMPRE IGP-M - NUNCA IPCA
                "tipo_juros": "Fixo",
                "percentual_juros": 8.0,  # FIXO 8% - IMUTÁVEL PDD
                "data_base_juros": primeiro_vencimento.strftime("%d/%m/%Y")
            }
            
            # Detalhes do cálculo para auditoria
            detalhes_calculo = {
                "saldo_anterior": saldo_atual,
                "indice_igpm": indice_igpm,
                "fator_correcao": fator_correcao,
                "novo_saldo": novo_saldo,
                "diferenca_correcao": novo_saldo - saldo_atual,
                "parcelas_total": parcelas_pendentes,
                "formula_aplicada": f"{saldo_atual} × {fator_correcao} = {novo_saldo}",
                "data_calculo": hoje.isoformat()
            }
            
            return {
                "sucesso": True,
                "valores_sienge": valores_sienge,
                "detalhes_calculo": detalhes_calculo,
                "observacao": "Valores calculados conforme PDD - usar no webscraping"
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
        Determina quais parcelas CT devem ser desmarcadas no webscraping
        
        REGRA PDD: Desmarcar parcelas com vencimento <= mês vigente
        """
        try:
            hoje = date.today()
            
            parcelas_desmarcar = []
            
            for parcela in parcelas_ct_a_vencer:
                data_vencimento = parcela.get("Data vencimento")
                
                # Converter data se necessário
                if isinstance(data_vencimento, str):
                    try:
                        data_obj = pd.to_datetime(data_vencimento, dayfirst=True, errors='coerce')
                        if pd.notna(data_obj):
                            data_obj = data_obj.date()
                        else:
                            continue
                    except:
                        continue
                else:
                    data_obj = data_vencimento
                
                # REGRA PDD: Vencimento <= hoje = DESMARCAR (parcelas já vencidas ou vencendo hoje)
                if data_obj and data_obj <= hoje:
                    parcelas_desmarcar.append({
                        "documento": parcela.get("Documento"),
                        "data_vencimento": data_obj.strftime("%d/%m/%Y"),
                        "valor": parcela.get("Valor a receber", 0),
                        "motivo": "Vencimento igual ou anterior ao mês vigente (PDD)"
                    })
            
            return parcelas_desmarcar
            
        except Exception as e:
            logging.error(f"Erro ao determinar parcelas para desmarcar: {str(e)}")
            return []