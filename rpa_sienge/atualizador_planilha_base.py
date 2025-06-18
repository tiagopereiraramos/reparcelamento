
"""
ATUALIZADOR PLANILHA BASE DE CÁLCULO
Implementa regra 9.1.2 do documento de processos

Desenvolvido em Português Brasileiro
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import logging

class AtualizadorPlanilhaBase:
    """
    Atualiza planilha BASE DE CÁLCULO REPARCELAMENTO 2025.xlsx
    conforme dados extraídos do Sienge
    """
    
    def __init__(self, caminho_planilha: str = "BASE DE CÁLCULO REPARCELAMENTO 2025.xlsx"):
        self.caminho_planilha = Path(caminho_planilha)
        self.logger = logging.getLogger(__name__)
        
    def atualizar_planilha_base(self, resultados_regras: Dict[str, Any], 
                               numero_titulo: str, cliente: str) -> Dict[str, Any]:
        """
        Atualiza planilha base com dados extraídos conforme regra 9.1.2
        
        Args:
            resultados_regras: Resultado da aplicação das regras PDD
            numero_titulo: Número do título processado
            cliente: Nome do cliente
            
        Returns:
            Status da atualização
        """
        try:
            # Carregar planilha base
            if not self.caminho_planilha.exists():
                return {
                    "sucesso": False,
                    "erro": f"Planilha base não encontrada: {self.caminho_planilha}"
                }
            
            # Ler aba "Base de cálculo"
            df_base = pd.read_excel(self.caminho_planilha, sheet_name="Base de cálculo")
            
            # Encontrar linha do cliente/título
            linha_cliente = self._encontrar_linha_cliente(df_base, numero_titulo, cliente)
            
            if linha_cliente is None:
                return {
                    "sucesso": False,
                    "erro": f"Cliente/título {numero_titulo} não encontrado na planilha base"
                }
            
            # Atualizar colunas conforme regra 9.1.2
            atualizacoes = self._preparar_atualizacoes(resultados_regras)
            
            for coluna, valor in atualizacoes.items():
                if coluna in df_base.columns:
                    df_base.loc[linha_cliente, coluna] = valor
            
            # Salvar planilha atualizada
            with pd.ExcelWriter(self.caminho_planilha, engine='openpyxl', mode='a', 
                               if_sheet_exists='replace') as writer:
                df_base.to_excel(writer, sheet_name="Base de cálculo", index=False)
            
            self.logger.info(f"✅ Planilha base atualizada para título {numero_titulo}")
            
            return {
                "sucesso": True,
                "titulo_atualizado": numero_titulo,
                "cliente": cliente,
                "colunas_atualizadas": list(atualizacoes.keys()),
                "linha_atualizada": linha_cliente,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "sucesso": False,
                "erro": f"Erro ao atualizar planilha base: {str(e)}"
            }
    
    def _encontrar_linha_cliente(self, df: pd.DataFrame, numero_titulo: str, cliente: str) -> int:
        """Encontra linha do cliente na planilha base"""
        try:
            # Tentar encontrar por número do título
            mask_titulo = df['Número Título'].astype(str).str.contains(str(numero_titulo), na=False)
            linhas_titulo = df[mask_titulo]
            
            if not linhas_titulo.empty:
                return linhas_titulo.index[0]
            
            # Tentar encontrar por nome do cliente
            mask_cliente = df['Cliente'].astype(str).str.contains(cliente, case=False, na=False)
            linhas_cliente = df[mask_cliente]
            
            if not linhas_cliente.empty:
                return linhas_cliente.index[0]
            
            return None
            
        except Exception:
            return None
    
    def _preparar_atualizacoes(self, resultados_regras: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara dicionário de atualizações conforme regra 9.1.2
        
        Colunas a atualizar:
        - PENDÊNCIAS SIENGE INAD
        - PENDÊNCIAS SIENGE  
        - Parcelas a vencer
        - Valor da Parcela Base
        - Dia de vencimento de parcelas
        - 1º vencimento carnê
        """
        atualizacoes = {}
        
        # PENDÊNCIAS SIENGE INAD (parcelas CT vencidas com regra 60 dias)
        if resultados_regras.get("quantidade_inadimplencia_60_dias", 0) > 0:
            atualizacoes["PENDÊNCIAS SIENGE INAD"] = resultados_regras["quantidade_inadimplencia_60_dias"]
        
        # PENDÊNCIAS SIENGE (REC/FAT vencidas)
        if resultados_regras.get("qtd_pendencias_rec_fat", 0) > 0:
            atualizacoes["PENDÊNCIAS SIENGE"] = resultados_regras["qtd_pendencias_rec_fat"]
        
        # Parcelas a vencer
        atualizacoes["Parcelas a vencer"] = resultados_regras.get("qtd_parcelas_ct_a_vencer", 0)
        
        # Valor da Parcela Base
        atualizacoes["Valor da Parcela Base"] = resultados_regras.get("valor_parcela_base", 0)
        
        # Dia de vencimento de parcelas
        atualizacoes["Dia de vencimento de parcelas"] = resultados_regras.get("dia_vencimento_parcelas")
        
        # 1º vencimento carnê
        atualizacoes["1º vencimento carnê"] = resultados_regras.get("data_primeiro_vencimento")
        
        return atualizacoes
