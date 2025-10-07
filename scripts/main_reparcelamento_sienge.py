#!/usr/bin/env python3
"""Main dedicado ao reparcelamento utilizando o repositório JSON transacional.

Fluxo executado:

1. Carrega contratos no status ``APROVACAO_REALIZADA`` (ou filtro
   parametrizável) a partir do ``JSONRPAFramework``;
2. Prepara índices econômicos necessários para cálculo;
3. Invoca ``RPAReparcelamentoSienge`` com lista explícita de contratos;
4. Atualiza status dos contratos e gera relatório resumido no console.

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

from core.data_manager import data_manager
from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo
from core.status_contratos import StatusContrato
from core.utils_sienge import log
from rpa_sienge.rpa_sienge_reparcelamento import RPAReparcelamentoSienge


async def carregar_indices_economicos() -> Dict[str, Any]:
    """Obtém índices econômicos atualizados via ``data_manager`` sem fallback."""

    log("📈 Carregando índices econômicos para reparcelamento...")

    await data_manager.inicializar()
    ipca = await data_manager.obter_indice_mais_recente("ipca")
    igpm = await data_manager.obter_indice_mais_recente("igpm")

    if ipca is None or igpm is None:
        raise RuntimeError(
            "Índices econômicos indisponíveis. Execute o RPA de coleta de índices antes do reparcelamento."
        )

    return {
        "ipca": {"valor": ipca, "fonte": "data_manager"},
        "igpm": {"valor": igpm, "fonte": "data_manager"},
    }


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

    indices = await carregar_indices_economicos()

    rpa = RPAReparcelamentoSienge(headless=args.headless == "1")
    resultado = await rpa.executar(contratos)

    log("\n📊 RESUMO DO REPARCELAMENTO:")
    log(f"   ✅ Sucessos: {resultado.get('sucessos', 0)}")
    log(f"   ❌ Erros: {resultado.get('erros', 0)}")
    log(f"   📦 Processados: {resultado.get('processados', 0)}")

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
        sucesso = bool(resultado.get("sucesso"))
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
