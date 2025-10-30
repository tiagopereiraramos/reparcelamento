#!/usr/bin/env python3
"""Main dedicado ao reparcelamento utilizando o repositório JSON transacional.

Fluxo executado:

1. Verifica autorização na planilha Google Sheets (aba "LANÇAMENTO DE REPARCELAMENTOS AUTORIZADO")
   - Busca pelo próximo mês nas colunas A (ano) e B (mês)
   - Verifica se coluna C está como "SIM"
   - Atualiza contratos de AGUARDANDO_APROVACAO para APROVACAO_REALIZADA (se autorizado)
2. Carrega contratos no status ``APROVACAO_REALIZADA`` (ou filtro parametrizável) a partir do ``JSONRPAFramework``;
3. Busca índices econômicos (IPCA e IGPM) diretamente da planilha base de cálculo:
   - Navega pelas abas "IPCA" e "IGPM"
   - Busca o último valor na coluna B de cada aba
4. Invoca ``RPAReparcelamentoSienge`` com lista explícita de contratos;
5. Atualiza status dos contratos e gera relatório resumido no console.

Desenvolvido em Português Brasileiro seguindo as diretrizes do projeto.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo
from core.status_contratos import StatusContrato
from core.utils_sienge import log
from rpa_sienge.rpa_sienge_reparcelamento import RPAReparcelamentoSienge
from rpa_sienge.autorizador_reparcelamentos import autorizar_reparcelamentos
import gspread
from google.oauth2.service_account import Credentials
import os


async def executar_autorizacao_previa() -> Dict[str, Any]:
    """Executa autorização prévia de reparcelamentos via planilha Google Sheets."""

    log("🔐 Verificando autorização de reparcelamentos...")

    try:
        resultado_autorizacao = await autorizar_reparcelamentos()

        if resultado_autorizacao.get("sucesso"):
            if resultado_autorizacao.get("autorizado"):
                log(
                    f"✅ Autorização executada: {resultado_autorizacao.get('sucessos', 0)} contratos autorizados")
            else:
                log("⚠️ Reparcelamento não autorizado para este mês")
        else:
            log(f"❌ Erro na autorização: {resultado_autorizacao.get('mensagem', 'Erro desconhecido')}")

        return resultado_autorizacao

    except Exception as e:
        log(f"💥 Erro durante autorização prévia: {str(e)}")
        return {
            "sucesso": False,
            "autorizado": False,
            "mensagem": f"Erro durante autorização: {str(e)}",
            "contratos_processados": 0,
            "sucessos": 0,
            "erros": 0
        }


async def carregar_indices_economicos() -> Dict[str, Any]:
    """Obtém índices econômicos diretamente da planilha base de cálculo."""

    log("📈 Carregando índices econômicos da planilha base de cálculo...")

    try:
        # Obter credenciais e planilha
        credenciais_path = os.getenv(
            "GOOGLE_CREDENTIALS_PATH", "./credentials/gspread-459713-aab8a657f9b0.json")
        planilha_id = os.getenv("PLANILHA_CALCULO_ID")

        if not planilha_id:
            raise RuntimeError(
                "PLANILHA_CALCULO_ID não definida nas variáveis de ambiente")

        # Conectar ao Google Sheets
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        credenciais = Credentials.from_service_account_file(
            credenciais_path, scopes=scopes)
        gc = gspread.authorize(credenciais)
        planilha = gc.open_by_key(planilha_id)

        # Buscar IPCA
        log("🔍 Buscando índice IPCA na aba 'IPCA'...")
        try:
            aba_ipca = planilha.worksheet("IPCA")
            valores_ipca = aba_ipca.get_all_values()

            log(f"📊 Total de linhas na aba IPCA: {len(valores_ipca)}")

            # Encontrar último valor na coluna B (ou outras colunas se B estiver vazia)
            ipca_valor = None

            # Primeiro, tentar coluna B
            for i, linha in enumerate(reversed(valores_ipca)):
                # Mostra primeiras 5 colunas
                log(f"🔍 Linha {len(valores_ipca) - i}: {linha[:5]}...")
                if len(linha) >= 2 and linha[1].strip():  # Coluna B
                    try:
                        valor_str = linha[1].strip()
                        log(
                            f"🔍 Tentando converter valor da coluna B: '{valor_str}'")
                        # Remove % e converte vírgula para ponto
                        valor_limpo = valor_str.replace(
                            '%', '').replace(',', '.')
                        ipca_valor = float(valor_limpo)
                        log(f"✅ IPCA encontrado na coluna B: {ipca_valor}%")
                        break
                    except ValueError as ve:
                        log(f"⚠️ Erro ao converter '{linha[1]}': {ve}")
                        continue

            # Se não encontrou na coluna B, tentar outras colunas
            if ipca_valor is None:
                log("🔍 Coluna B vazia, tentando outras colunas...")
                for i, linha in enumerate(reversed(valores_ipca)):
                    log(f"🔍 Linha {len(valores_ipca) - i}: {linha[:5]}...")
                    # Tenta colunas C, D, E, F
                    for col_idx in range(2, min(len(linha), 6)):
                        if linha[col_idx].strip():
                            try:
                                valor_str = linha[col_idx].strip()
                                log(
                                    f"🔍 Tentando converter valor da coluna {chr(65+col_idx)}: '{valor_str}'")
                                # Remove % e converte vírgula para ponto
                                valor_limpo = valor_str.replace(
                                    '%', '').replace(',', '.')
                                ipca_valor = float(valor_limpo)
                                log(
                                    f"✅ IPCA encontrado na coluna {chr(65+col_idx)}: {ipca_valor}%")
                                break
                            except ValueError as ve:
                                log(
                                    f"⚠️ Erro ao converter '{linha[col_idx]}': {ve}")
                                continue
                    if ipca_valor is not None:
                        break

            if ipca_valor is None:
                log("❌ Nenhum valor numérico encontrado em nenhuma coluna da aba IPCA")
                raise RuntimeError("IPCA não encontrado na planilha")

        except Exception as e:
            log(f"❌ Erro ao buscar IPCA: {str(e)}")
            raise RuntimeError(f"Erro ao buscar IPCA: {str(e)}")

        # Buscar IGPM
        log("🔍 Buscando índice IGPM na aba 'IGPM'...")
        try:
            aba_igpm = planilha.worksheet("IGPM")
            valores_igpm = aba_igpm.get_all_values()

            log(f"📊 Total de linhas na aba IGPM: {len(valores_igpm)}")

            # Encontrar último valor na coluna B (ou outras colunas se B estiver vazia)
            igpm_valor = None

            # Primeiro, tentar coluna B
            for i, linha in enumerate(reversed(valores_igpm)):
                # Mostra primeiras 5 colunas
                log(f"🔍 Linha {len(valores_igpm) - i}: {linha[:5]}...")
                if len(linha) >= 2 and linha[1].strip():  # Coluna B
                    try:
                        valor_str = linha[1].strip()
                        log(
                            f"🔍 Tentando converter valor da coluna B: '{valor_str}'")
                        # Remove % e converte vírgula para ponto
                        valor_limpo = valor_str.replace(
                            '%', '').replace(',', '.')
                        igpm_valor = float(valor_limpo)
                        log(f"✅ IGPM encontrado na coluna B: {igpm_valor}%")
                        break
                    except ValueError as ve:
                        log(f"⚠️ Erro ao converter '{linha[1]}': {ve}")
                        continue

            # Se não encontrou na coluna B, tentar outras colunas
            if igpm_valor is None:
                log("🔍 Coluna B vazia, tentando outras colunas...")
                for i, linha in enumerate(reversed(valores_igpm)):
                    log(f"🔍 Linha {len(valores_igpm) - i}: {linha[:5]}...")
                    # Tenta colunas C, D, E, F
                    for col_idx in range(2, min(len(linha), 6)):
                        if linha[col_idx].strip():
                            try:
                                valor_str = linha[col_idx].strip()
                                log(
                                    f"🔍 Tentando converter valor da coluna {chr(65+col_idx)}: '{valor_str}'")
                                # Remove % e converte vírgula para ponto
                                valor_limpo = valor_str.replace(
                                    '%', '').replace(',', '.')
                                igpm_valor = float(valor_limpo)
                                log(
                                    f"✅ IGPM encontrado na coluna {chr(65+col_idx)}: {igpm_valor}%")
                                break
                            except ValueError as ve:
                                log(
                                    f"⚠️ Erro ao converter '{linha[col_idx]}': {ve}")
                                continue
                    if igpm_valor is not None:
                        break

            if igpm_valor is None:
                log("❌ Nenhum valor numérico encontrado em nenhuma coluna da aba IGPM")
                raise RuntimeError("IGPM não encontrado na planilha")

        except Exception as e:
            log(f"❌ Erro ao buscar IGPM: {str(e)}")
            raise RuntimeError(f"Erro ao buscar IGPM: {str(e)}")

        log("✅ Índices econômicos carregados com sucesso da planilha")
        return {
            "ipca": {"valor": ipca_valor, "fonte": "planilha_base_calculo"},
            "igpm": {"valor": igpm_valor, "fonte": "planilha_base_calculo"},
        }

    except Exception as e:
        log(f"💥 Erro ao carregar índices da planilha: {str(e)}")
        raise RuntimeError(f"Índices econômicos indisponíveis: {str(e)}")


def obter_contratos(args: argparse.Namespace) -> List[Dict[str, Any]]:
    """Recupera contratos prontos para reparcelamento."""

    if args.contratos_json:
        caminho = Path(args.contratos_json)
        if not caminho.exists():
            raise FileNotFoundError(
                f"Arquivo JSON com contratos não encontrado: {caminho}"
            )
        log(f"📄 Carregando contratos manualmente do arquivo: {caminho}")
        return json.loads(caminho.read_text(encoding="utf-8"))

    status_alvo = args.status or StatusContrato.APROVACAO_REALIZADA
    log(
        f"📥 Buscando contratos no status '{status_alvo}' a partir do repositório transacional..."
    )

    contratos = repositorio_contratos_arquivo.framework.find(
        {"status": status_alvo})
    log(f"✅ {len(contratos)} contratos encontrados para reparcelamento.")
    return contratos


async def executar_reparcelamento(args: argparse.Namespace) -> Dict[str, Any]:
    """Executa o reparcelamento baseado nos argumentos informados."""

    # 1. Executar autorização prévia (se não for --autorizar)
    if not args.autorizar:
        log("🔐 Executando autorização prévia de reparcelamentos...")
        resultado_autorizacao = await executar_autorizacao_previa()

        if not resultado_autorizacao.get("sucesso"):
            log("❌ Falha na autorização prévia. Abortando execução.")
            return {
                "sucesso": False,
                "processados": 0,
                "sucessos": 0,
                "erros": 0,
                "contratos_sucesso": [],
                "contratos_erro": [],
                "erro_autorizacao": resultado_autorizacao.get("mensagem", "Erro desconhecido")
            }

        if not resultado_autorizacao.get("autorizado"):
            log("⚠️ Reparcelamento não autorizado para este mês. Abortando execução.")
            return {
                "sucesso": False,
                "processados": 0,
                "sucessos": 0,
                "erros": 0,
                "contratos_sucesso": [],
                "contratos_erro": [],
                "nao_autorizado": True
            }
    else:
        log("⚠️ Modo --autorizar ativado. Pulando verificação de autorização.")

    # 2. Obter contratos para reparcelamento
    contratos = obter_contratos(args)

    if not contratos:
        log("⚠️ Nenhum contrato disponível para reparcelamento.")
        return {
            "sucesso": False,
            "processados": 0,
            "sucessos": 0,
            "erros": 0,
            "contratos_sucesso": [],
            "contratos_erro": [],
        }

    # 3. Carregar índices econômicos
    indices = await carregar_indices_economicos()

    # 4. Executar reparcelamento
    rpa = RPAReparcelamentoSienge(headless=args.headless == "0")
    # O RPA busca contratos internamente, não recebe lista
    resultado = await rpa.executar(limite=len(contratos))

    log("\n📊 RESUMO DO REPARCELAMENTO:")
    log(f"   ✅ Sucessos: {resultado.dados.get('contratos_processados', 0)}")
    log(f"   ❌ Erros: {len(resultado.dados.get('contratos_erro', []))}")
    log(f"   📦 Processados: {resultado.dados.get('contratos_processados', 0)}")

    return resultado


def montar_argumentos() -> argparse.Namespace:
    """Configura argumentos de linha de comando."""

    parser = argparse.ArgumentParser(
        description="RPA Sienge - Reparcelamento com repositório JSON",
    )

    parser.add_argument(
        "--headless",
        choices=["0", "1"],
        default="1",
        help="Define se o navegador deve operar em modo headless (1 = sim).",
    )
    parser.add_argument(
        "--autorizar",
        action="store_true",
        help="Autoriza reparcelamento mesmo quando as regras indicarem bloqueio.",
    )
    parser.add_argument(
        "--notificar",
        action="store_true",
        help="Ativa notificações para acompanhamento humano durante o processamento.",
    )
    parser.add_argument(
        "--status",
        type=str,
        help="Status que será filtrado no repositório (padrão: APROVACAO_REALIZADA).",
    )
    parser.add_argument(
        "--contratos-json",
        type=str,
        help="Caminho para arquivo JSON contendo a lista completa de contratos a processar.",
    )

    return parser.parse_args()


def main() -> int:
    """Função principal síncrona da CLI."""

    args = montar_argumentos()

    inicio = datetime.now()
    log("🎯 Iniciando reparcelamento via JSONRPAFramework")
    log(f"⏱️ Início: {inicio}")

    try:
        resultado = asyncio.run(executar_reparcelamento(args))
        # resultado pode ser dict ou ResultadoRPA
        if hasattr(resultado, 'sucesso'):
            sucesso = bool(resultado.sucesso)
        else:
            sucesso = bool(resultado.get("sucesso", False))
        return 0 if sucesso else 1
    except KeyboardInterrupt:  # pragma: no cover - interação humana
        log("🚫 Execução interrompida pelo usuário.")
        return 130
    except Exception as erro:  # pylint: disable=broad-except
        log(f"💥 Erro crítico durante o reparcelamento: {erro}")
        return 1
    finally:
        fim = datetime.now()
        log(f"⏱️ Fim: {fim}")
        log(f"⌛ Duração: {fim - inicio}")


if __name__ == "__main__":
    sys.exit(main())
