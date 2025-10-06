"""
Gerador de Anexos para Relatórios RPA
Sistema unificado para gerar anexos Excel/TXT com dados detalhados dos contratos processados

Desenvolvido em Português Brasileiro
"""

import pandas as pd
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import json


class GeradorAnexos:
    """Classe para gerar anexos Excel e TXT com dados dos contratos processados"""

    def __init__(self, diretorio_saida: str = "outputs/relatorios"):
        """
        Inicializa o gerador de anexos

        Args:
            diretorio_saida: Diretório onde os anexos serão salvos
        """
        self.diretorio_saida = Path(diretorio_saida)
        self.diretorio_saida.mkdir(parents=True, exist_ok=True)

    def gerar_anexo_excel(self,
                          dados: List[Dict[str, Any]],
                          nome_arquivo: str,
                          colunas: Optional[List[str]] = None,
                          nome_aba: str = "Contratos") -> str:
        """
        Gera anexo Excel com dados dos contratos

        Args:
            dados: Lista de dicionários com dados dos contratos
            nome_arquivo: Nome do arquivo Excel (sem extensão)
            colunas: Lista de colunas a incluir (se None, usa todas)
            nome_aba: Nome da aba do Excel

        Returns:
            str: Caminho completo do arquivo gerado
        """
        if not dados:
            raise ValueError("Lista de dados está vazia")

        # Cria DataFrame
        df = pd.DataFrame(dados)

        # Filtra colunas se especificado
        if colunas:
            colunas_disponiveis = [col for col in colunas if col in df.columns]
            df = df[colunas_disponiveis]

        # Gera nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_completo = f"{nome_arquivo}_{timestamp}.xlsx"
        caminho_arquivo = self.diretorio_saida / nome_completo

        # Cria o arquivo Excel
        with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=nome_aba, index=False)

            # Ajusta largura das colunas
            worksheet = writer.sheets[nome_aba]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                # Máximo de 50 caracteres
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        return str(caminho_arquivo)

    def gerar_anexo_txt(self,
                        dados: List[Dict[str, Any]],
                        nome_arquivo: str,
                        colunas: Optional[List[str]] = None,
                        separador: str = " | ") -> str:
        """
        Gera anexo TXT com dados dos contratos

        Args:
            dados: Lista de dicionários com dados dos contratos
            nome_arquivo: Nome do arquivo TXT (sem extensão)
            colunas: Lista de colunas a incluir (se None, usa todas)
            separador: Separador entre colunas

        Returns:
            str: Caminho completo do arquivo gerado
        """
        if not dados:
            raise ValueError("Lista de dados está vazia")

        # Gera nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_completo = f"{nome_arquivo}_{timestamp}.txt"
        caminho_arquivo = self.diretorio_saida / nome_completo

        # Determina colunas a usar
        if colunas:
            colunas_disponiveis = [
                col for col in colunas if col in dados[0].keys()]
        else:
            colunas_disponiveis = list(dados[0].keys())

        # Escreve cabeçalho
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            # Cabeçalho
            f.write(f"RELATÓRIO: {nome_arquivo}\n")
            f.write(
                f"DATA/HORA: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"TOTAL DE REGISTROS: {len(dados)}\n")
            f.write("=" * 80 + "\n\n")

            # Cabeçalhos das colunas
            f.write(separador.join(colunas_disponiveis) + "\n")
            f.write("-" * (len(separador.join(colunas_disponiveis))) + "\n")

            # Dados
            for registro in dados:
                linha = []
                for coluna in colunas_disponiveis:
                    valor = registro.get(coluna, 'N/A')
                    linha.append(str(valor))
                f.write(separador.join(linha) + "\n")

        return str(caminho_arquivo)

    def gerar_anexo_analise_planilhas(self,
                                      contratos_aprovados: List[Dict[str, Any]],
                                      contratos_rejeitados: List[Dict[str, Any]],
                                      contratos_nao_processados: List[Dict[str, Any]],
                                      novos_contratos: List[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Gera anexos para o main_analise_planilhas.py

        Args:
            contratos_aprovados: Lista de contratos aprovados
            contratos_rejeitados: Lista de contratos rejeitados
            contratos_nao_processados: Lista de contratos não processados
            novos_contratos: Lista de novos contratos encontrados

        Returns:
            Dict[str, str]: Dicionário com caminhos dos arquivos gerados
        """
        anexos = {}

        # Anexo Excel com todos os contratos
        todos_contratos = []

        # Adiciona contratos aprovados
        for contrato in contratos_aprovados:
            contrato['status'] = 'APROVADO'
            todos_contratos.append(contrato)

        # Adiciona contratos rejeitados
        for contrato in contratos_rejeitados:
            contrato['status'] = 'REJEITADO'
            todos_contratos.append(contrato)

        # Adiciona contratos não processados
        for contrato in contratos_nao_processados:
            contrato['status'] = 'NÃO PROCESSADO'
            todos_contratos.append(contrato)

        # Adiciona novos contratos se existirem
        if novos_contratos:
            for contrato in novos_contratos:
                contrato['status'] = 'NOVO'
                todos_contratos.append(contrato)

        if todos_contratos:
            # Colunas padrão para análise de planilhas
            colunas = [
                'codigo_cliente', 'cliente', 'titulo', 'mes_reparcelamento',
                'status', 'motivo', 'linha_planilha'
            ]

            # Filtra colunas disponíveis
            colunas_disponiveis = [
                col for col in colunas if col in todos_contratos[0].keys()]

            # Gera Excel
            anexos['excel'] = self.gerar_anexo_excel(
                todos_contratos,
                "analise_planilhas_contratos",
                colunas_disponiveis,
                "Análise de Planilhas"
            )

            # Gera TXT
            anexos['txt'] = self.gerar_anexo_txt(
                todos_contratos,
                "analise_planilhas_contratos",
                colunas_disponiveis
            )

        return anexos

    def gerar_anexo_extracao(self,
                             contratos_processados: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Gera anexos para o main_sienge_extracao.py
        ✅ CORREÇÃO: Apenas Excel com status de sucesso/falha

        Args:
            contratos_processados: Lista de contratos processados na extração

        Returns:
            Dict[str, str]: Dicionário com caminhos dos arquivos gerados
        """
        anexos = {}

        if contratos_processados:
            # ✅ NOVO: Colunas otimizadas com status e motivo de falha
            colunas = [
                'codigo_cliente', 'cliente', 'numero_titulo', 'status_processamento',
                'motivo_falha', 'timestamp_processamento'
            ]

            # ✅ NOVO: Processar dados para incluir status de sucesso/falha
            dados_processados = []
            for contrato in contratos_processados:
                dados_contrato = {
                    'codigo_cliente': contrato.get('codigo_cliente', ''),
                    'cliente': contrato.get('cliente', ''),
                    'numero_titulo': contrato.get('numero_titulo', ''),
                    'status_processamento': 'SUCESSO' if contrato.get('sucesso', False) else 'FALHA',
                    'motivo_falha': contrato.get('erro', '') if not contrato.get('sucesso', False) else '',
                    'timestamp_processamento': contrato.get('timestamp_processamento', datetime.now().isoformat())
                }
                dados_processados.append(dados_contrato)

            # ✅ CORREÇÃO: Gera apenas Excel (sem TXT)
            anexos['excel'] = self.gerar_anexo_excel(
                dados_processados,
                "extracao_contratos",
                colunas,
                "Extração de Contratos - Status e Resultados"
            )

        return anexos

    def gerar_anexo_reparcelamento(self,
                                   contratos_sucesso: List[Dict[str, Any]],
                                   contratos_erro: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Gera anexos para o main_sienge_reparcelamento.py

        Args:
            contratos_sucesso: Lista de contratos processados com sucesso
            contratos_erro: Lista de contratos com erro

        Returns:
            Dict[str, str]: Dicionário com caminhos dos arquivos gerados
        """
        anexos = {}

        todos_contratos = []

        # Adiciona contratos com sucesso
        for contrato in contratos_sucesso:
            contrato['status_processamento'] = 'SUCESSO'
            contrato['motivo_erro'] = 'N/A'
            todos_contratos.append(contrato)

        # Adiciona contratos com erro
        for contrato in contratos_erro:
            contrato['status_processamento'] = 'ERRO'
            todos_contratos.append(contrato)

        if todos_contratos:
            # Colunas padrão para reparcelamento
            colunas = [
                'codigo_cliente', 'cliente', 'titulo', 'mes_reparcelamento',
                'status_processamento', 'motivo_erro', 'data_processamento'
            ]

            # Filtra colunas disponíveis
            colunas_disponiveis = [
                col for col in colunas if col in todos_contratos[0].keys()]

            # ✅ CORREÇÃO: Gera apenas Excel (sem TXT)
            anexos['excel'] = self.gerar_anexo_excel(
                todos_contratos,
                "reparcelamento_contratos",
                colunas_disponiveis,
                "Reparcelamento de Contratos"
            )

            # ✅ CORREÇÃO: TXT removido - apenas Excel
            # anexos['txt'] = self.gerar_anexo_txt(
            #     todos_contratos,
            #     "reparcelamento_contratos",
            #     colunas_disponiveis
            # )

        return anexos

    def gerar_anexo_carnes(self,
                           carnes_sucesso: List[Dict[str, Any]] = None,
                           carnes_erro: List[Dict[str, Any]] = None,
                           contratos_rejeitados: List[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Gera anexos para o main_sienge_carnes.py

        Args:
            carnes_sucesso: Lista de carnês gerados com sucesso
            carnes_erro: Lista de carnês com erro
            contratos_rejeitados: Lista de contratos rejeitados por pendências

        Returns:
            Dict[str, str]: Dicionário com caminhos dos arquivos gerados
        """
        anexos = {}

        todos_carnes = []

        # Adiciona carnês com sucesso
        if carnes_sucesso:
            for carne in carnes_sucesso:
                carne['status_processamento'] = 'SUCESSO'
                carne['motivo_erro'] = 'N/A'
                todos_carnes.append(carne)

        # Adiciona carnês com erro
        if carnes_erro:
            for carne in carnes_erro:
                carne['status_processamento'] = 'ERRO'
                todos_carnes.append(carne)

        # ✅ NOVO: Adiciona contratos rejeitados
        if contratos_rejeitados:
            for contrato in contratos_rejeitados:
                contrato['status_processamento'] = 'REJEITADO'
                contrato['motivo_erro'] = contrato.get('motivo', 'N/A')
                todos_carnes.append(contrato)

        if todos_carnes:
            # Colunas padrão para carnês (incluindo contratos rejeitados)
            colunas = [
                'codigo_cliente', 'cliente', 'numero_titulo', 'empresa',
                'status_processamento', 'motivo_erro', 'data_processamento'
            ]

            # Filtra colunas disponíveis
            colunas_disponiveis = [
                col for col in colunas if col in todos_carnes[0].keys()]

            # ✅ CORREÇÃO: Gera apenas Excel (sem TXT)
            anexos['excel'] = self.gerar_anexo_excel(
                todos_carnes,
                "geracao_carnes",
                colunas_disponiveis,
                "Geração de Carnês"
            )

        return anexos

    def limpar_arquivos_antigos(self, dias_para_manter: int = 30):
        """
        Remove arquivos antigos para economizar espaço

        Args:
            dias_para_manter: Número de dias para manter os arquivos
        """
        if not self.diretorio_saida.exists():
            return

        data_limite = datetime.now().timestamp() - (dias_para_manter * 24 * 60 * 60)

        for arquivo in self.diretorio_saida.iterdir():
            if arquivo.is_file():
                if arquivo.stat().st_mtime < data_limite:
                    try:
                        arquivo.unlink()
                        print(f"🗑️ Arquivo antigo removido: {arquivo.name}")
                    except Exception as e:
                        print(
                            f"⚠️ Erro ao remover arquivo {arquivo.name}: {e}")


# Instância global para uso em outros módulos
gerador_anexos = GeradorAnexos()
