#!/usr/bin/env python3
"""Gerenciador de autorização de reparcelamentos via planilha Google Sheets.

Este módulo implementa a lógica para:
1. Conectar à planilha base de cálculo no Google Sheets
2. Verificar a aba "LANÇAMENTO DE REPARCELAMENTOS AUTORIZADO"
3. Buscar pelo mês atual na coluna B
4. Verificar se a coluna C está como "SIM"
5. Atualizar status de contratos de AGUARDANDO_AUTORIZACAO para APROVACAO_REALIZADA

Desenvolvido em Português Brasileiro seguindo as diretrizes do projeto.
"""

from __future__ import annotations
from core.utils_sienge import log
from core.status_contratos import StatusContrato
from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

PROJETO_RAIZ = Path(__file__).resolve().parent.parent
if str(PROJETO_RAIZ) not in sys.path:
    sys.path.insert(0, str(PROJETO_RAIZ))

load_dotenv(PROJETO_RAIZ / ".env")

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_DISPONIVEL = True
except ImportError:  # pragma: no cover - dependência externa opcional
    gspread = None  # type: ignore
    Credentials = None  # type: ignore
    GOOGLE_SHEETS_DISPONIVEL = False


class AutorizadorReparcelamentos:
    """Gerenciador de autorização de reparcelamentos via planilha Google Sheets."""

    def __init__(self, planilha_id: Optional[str] = None, credenciais_path: Optional[str] = None):
        """
        Inicializa o autorizador de reparcelamentos.

        Args:
            planilha_id: ID da planilha no Google Sheets (padrão: variável de ambiente)
            credenciais_path: Caminho para credenciais Google (padrão: variável de ambiente)
        """
        self.planilha_id = planilha_id or os.getenv("PLANILHA_CALCULO_ID")
        self.credenciais_path = credenciais_path or os.getenv(
            "GOOGLE_CREDENTIALS_PATH",
            "./credentials/gspread-459713-aab8a657f9b0.json"
        )
        self.cliente_google: Optional[gspread.Client] = None

        if not self.planilha_id:
            raise ValueError(
                "ID da planilha não informado. Defina PLANILHA_CALCULO_ID ou passe planilha_id.")

        if not Path(self.credenciais_path).exists():
            raise FileNotFoundError(
                f"Arquivo de credenciais não encontrado: {self.credenciais_path}")

    def _conectar_google_sheets(self) -> None:
        """Estabelece conexão com Google Sheets."""

        if not GOOGLE_SHEETS_DISPONIVEL:
            raise RuntimeError(
                "Bibliotecas do Google Sheets ausentes. Instale gspread e google-auth."
            )

        escopos = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        credenciais = Credentials.from_service_account_file(
            self.credenciais_path, scopes=escopos
        )

        self.cliente_google = gspread.authorize(credenciais)
        log("✅ Conectado ao Google Sheets com sucesso.")

    def _obter_proximo_mes_planilha(self) -> tuple[str, str]:
        """Retorna o próximo mês no formato da planilha (ano, mês_por_extenso)."""
        from datetime import datetime

        # Obter mês atual
        hoje = datetime.now()

        # Adicionar 1 mês
        if hoje.month == 12:
            # Se estamos em dezembro, próximo mês é janeiro do próximo ano
            proximo_mes = hoje.replace(year=hoje.year + 1, month=1)
        else:
            # Caso contrário, apenas incrementar o mês
            proximo_mes = hoje.replace(month=hoje.month + 1)

        # Mapear número do mês para nome em português
        meses_pt = {
            1: "JANEIRO", 2: "FEVEREIRO", 3: "MARÇO", 4: "ABRIL",
            5: "MAIO", 6: "JUNHO", 7: "JULHO", 8: "AGOSTO",
            9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
        }

        ano = str(proximo_mes.year)
        mes_nome = meses_pt[proximo_mes.month]

        return ano, mes_nome

    def _localizar_aba_autorizacao(self) -> gspread.Worksheet:
        """Localiza a aba 'LANÇAMENTO DE REPARCELAMENTOS AUTORIZADO'."""

        if not self.cliente_google:
            raise RuntimeError("Cliente Google Sheets não inicializado.")

        planilha = self.cliente_google.open_by_key(self.planilha_id)

        # Nomes possíveis para a aba
        nomes_aba = [
            "Lançamento de reparcelamento no Sienge autorizado",
            "LANÇAMENTO DE REPARCELAMENTO NO SIENGE AUTORIZADO",
            "Lançamento de Reparcelamento no Sienge Autorizado",
            "lançamento de reparcelamento no sienge autorizado",
            "LANCAMENTO DE REPARCELAMENTO NO SIENGE AUTORIZADO",
            "Lancamento de Reparcelamento no Sienge Autorizado",
            "LANÇAMENTO DE REPARCELAMENTOS AUTORIZADO",
            "Lançamento de Reparcelamentos Autorizado",
            "lançamento de reparcelamentos autorizado",
            "LANCAMENTO DE REPARCELAMENTOS AUTORIZADO",
            "Lancamento de Reparcelamentos Autorizado"
        ]

        for nome in nomes_aba:
            try:
                aba = planilha.worksheet(nome)
                log(f"✅ Aba encontrada: '{nome}'")
                return aba
            except gspread.WorksheetNotFound:
                continue

        raise ValueError(
            "Aba 'Lançamento de reparcelamento no Sienge autorizado' não encontrada na planilha."
        )

    def _verificar_autorizacao_mes_atual(self, aba: gspread.Worksheet) -> bool:
        """
        Verifica se o reparcelamento está autorizado para o mês atual.

        Args:
            aba: Worksheet da aba de autorização

        Returns:
            True se autorizado, False caso contrário
        """
        try:
            # Obter todos os valores da aba
            valores = aba.get_all_values()

            if not valores:
                log("⚠️ Aba de autorização está vazia.")
                return False

            # Procurar pelo próximo mês nas colunas A (ano) e B (mês)
            ano_proximo, mes_proximo = self._obter_proximo_mes_planilha()
            log(f"🔍 Procurando autorização para: {ano_proximo} - {mes_proximo}")

            for indice_linha, linha in enumerate(valores):
                if len(linha) >= 3:  # Garantir que tem pelo menos 3 colunas
                    ano_planilha = linha[0].strip() if len(
                        linha) > 0 else ""  # Coluna A (ANO)
                    mes_planilha = linha[1].strip().upper() if len(
                        linha) > 1 else ""  # Coluna B (MÊS)
                    autorizado = linha[2].strip().upper() if len(
                        linha) > 2 else ""  # Coluna C (SIM/NÃO)

                    # Verificar se é a linha do próximo mês
                    if ano_planilha == ano_proximo and mes_planilha == mes_proximo:
                        log(
                            f"📅 Mês encontrado na linha {indice_linha + 1}: {ano_planilha} - {mes_planilha}")
                        log(f"🔐 Status de autorização: {autorizado}")

                        if autorizado == "SIM":
                            log("✅ Reparcelamento AUTORIZADO para este mês!")
                            return True
                        else:
                            log("❌ Reparcelamento NÃO autorizado para este mês.")
                            return False

            log(f"⚠️ Próximo mês {ano_proximo} - {mes_proximo} não encontrado na planilha de autorização.")
            return False

        except Exception as e:
            log(f"❌ Erro ao verificar autorização: {str(e)}")
            return False

    def _buscar_contratos_aguardando_autorizacao(self) -> List[Dict[str, Any]]:
        """Busca contratos com status AGUARDANDO_APROVACAO."""

        contratos = repositorio_contratos_arquivo.framework.find({
            "status": "AGUARDANDO_APROVACAO"
        })

        log(f"📋 Encontrados {len(contratos)} contratos aguardando autorização.")
        return contratos

    def _atualizar_status_contratos(self, contratos: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Atualiza status dos contratos para APROVACAO_REALIZADA.

        Args:
            contratos: Lista de contratos para atualizar

        Returns:
            Dicionário com estatísticas da atualização
        """
        sucessos = 0
        erros = 0

        for contrato in contratos:
            try:
                # Atualizar status no repositório
                repositorio_contratos_arquivo.framework.update(
                    {"_id": contrato["_id"]},
                    {
                        "status": "APROVACAO_REALIZADA",
                        "data_autorizacao": datetime.now().isoformat(),
                        "autorizado_por": "sistema_automatico"
                    }
                )

                sucessos += 1
                log(f"✅ Contrato {contrato.get('numero_titulo', 'N/A')} autorizado com sucesso.")

            except Exception as e:
                erros += 1
                log(
                    f"❌ Erro ao autorizar contrato {contrato.get('numero_titulo', 'N/A')}: {str(e)}")

        return {
            "sucessos": sucessos,
            "erros": erros,
            "total": len(contratos)
        }

    async def executar_autorizacao(self) -> Dict[str, Any]:
        """
        Executa o processo completo de autorização de reparcelamentos.

        Returns:
            Dicionário com resultado da operação
        """
        try:
            log("🚀 Iniciando processo de autorização de reparcelamentos...")

            # 1. Conectar ao Google Sheets
            self._conectar_google_sheets()

            # 2. Localizar aba de autorização
            aba_autorizacao = self._localizar_aba_autorizacao()

            # 3. Verificar se está autorizado para o mês atual
            autorizado = self._verificar_autorizacao_mes_atual(aba_autorizacao)

            if not autorizado:
                log("⚠️ Reparcelamento não autorizado para este mês. Nenhuma ação será tomada.")
                return {
                    "sucesso": True,
                    "autorizado": False,
                    "mensagem": "Reparcelamento não autorizado para este mês.",
                    "contratos_processados": 0,
                    "sucessos": 0,
                    "erros": 0
                }

            # 4. Buscar contratos aguardando autorização
            contratos = self._buscar_contratos_aguardando_autorizacao()

            if not contratos:
                log("ℹ️ Nenhum contrato aguardando autorização encontrado.")
                return {
                    "sucesso": True,
                    "autorizado": True,
                    "mensagem": "Nenhum contrato aguardando autorização.",
                    "contratos_processados": 0,
                    "sucessos": 0,
                    "erros": 0
                }

            # 5. Atualizar status dos contratos
            log(f"🔄 Atualizando status de {len(contratos)} contratos...")
            estatisticas = self._atualizar_status_contratos(contratos)

            # 6. Relatório final
            log("\n📊 RESUMO DA AUTORIZAÇÃO:")
            log(f"   ✅ Contratos autorizados: {estatisticas['sucessos']}")
            log(f"   ❌ Erros: {estatisticas['erros']}")
            log(f"   📦 Total processados: {estatisticas['total']}")

            return {
                "sucesso": True,
                "autorizado": True,
                "mensagem": f"Processo de autorização concluído com sucesso.",
                "contratos_processados": estatisticas['total'],
                "sucessos": estatisticas['sucessos'],
                "erros": estatisticas['erros']
            }

        except Exception as e:
            log(f"💥 Erro durante autorização: {str(e)}")
            return {
                "sucesso": False,
                "autorizado": False,
                "mensagem": f"Erro durante autorização: {str(e)}",
                "contratos_processados": 0,
                "sucessos": 0,
                "erros": 0
            }


async def autorizar_reparcelamentos(
    planilha_id: Optional[str] = None,
    credenciais_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Função de conveniência para executar autorização de reparcelamentos.

    Args:
        planilha_id: ID da planilha (opcional, usa variável de ambiente se não informado)
        credenciais_path: Caminho das credenciais (opcional, usa variável de ambiente se não informado)

    Returns:
        Dicionário com resultado da operação
    """
    autorizador = AutorizadorReparcelamentos(planilha_id, credenciais_path)
    return await autorizador.executar_autorizacao()


if __name__ == "__main__":
    """Execução direta do módulo para testes."""
    import asyncio

    async def main():
        resultado = await autorizar_reparcelamentos()
        print(f"Resultado: {resultado}")

    asyncio.run(main())
