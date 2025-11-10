#!/usr/bin/env python3
"""
Agendador para atualização do campo "Último reajuste" no Google Sheets.

Este script verifica o arquivo `data/fila_contratos.json` e, caso existam
contratos com status "PROCESSADO_SICREDI", dispara a execução do
`rpa_sienge/atualizar_ultimo_reajuste.py` para o mês informado.

Uso típico (cron):
  PYTHONPATH=. /usr/bin/python3 scripts/schedule_atualizar_ultimo_reajuste.py \
    --mes "nov.-25" --aba "Base de cálculo"

Requisitos:
  - Variável de ambiente PLANILHA_CALCULO_ID definida no .env
  - GOOGLE_CREDENTIALS_PATH apontando para o JSON da conta de serviço
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

PROJETO_RAIZ = Path(__file__).resolve().parent.parent
if str(PROJETO_RAIZ) not in sys.path:
    sys.path.insert(0, str(PROJETO_RAIZ))

load_dotenv(PROJETO_RAIZ / ".env")


def log(msg: str) -> None:
    """Loga mensagem com prefixo padronizado."""
    print(f"[SCHEDULE-ULT.REAJUSTE] {msg}")


def carregar_fila(caminho: Path) -> List[Dict[str, Any]]:
    """Carrega a fila de contratos a partir do JSON."""
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    with caminho.open("r", encoding="utf-8") as f:
        return json.load(f)


def possui_processados_sicredi(contratos: List[Dict[str, Any]]) -> bool:
    """Retorna True se existir algum contrato com status PROCESSADO_SICREDI."""
    for item in contratos:
        status = str(item.get("status", "")).upper().strip()
        if status == "PROCESSADO_SICREDI":
            return True
    return False


def obter_argumentos() -> argparse.Namespace:
    """Interpreta argumentos de CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Verifica a fila e dispara a atualização do 'Último reajuste' quando houver contratos PROCESSADO_SICREDI."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--mes",
        required=True,
        help="Mês-alvo no formato aceito pelo atualizador (ex.: 'nov.-25').",
    )
    parser.add_argument(
        "--aba",
        default="Base de cálculo",
        help="Nome da aba no Google Sheets.",
    )
    parser.add_argument(
        "--fila",
        default=str(PROJETO_RAIZ / "data" / "fila_contratos.json"),
        help="Caminho do arquivo de fila de contratos.",
    )
    return parser.parse_args()


def main() -> None:
    """Fluxo principal: verifica fila e dispara atualização condicionalmente."""
    args = obter_argumentos()

    planilha_id = os.getenv("PLANILHA_CALCULO_ID")
    if not planilha_id:
        log("ERRO: PLANILHA_CALCULO_ID ausente no .env")
        sys.exit(2)

    credenciais = os.getenv(
        "GOOGLE_CREDENTIALS_PATH", "./credentials/gspread-459713-aab8a657f9b0.json"
    )

    try:
        contratos = carregar_fila(Path(args.fila))
    except Exception as e:
        log(f"ERRO ao carregar fila: {e}")
        sys.exit(3)

    if not possui_processados_sicredi(contratos):
        log("Sem contratos com status PROCESSADO_SICREDI. Nada a fazer.")
        sys.exit(0)

    cmd = [
        sys.executable,
        str(PROJETO_RAIZ / "rpa_sienge" / "atualizar_ultimo_reajuste.py"),
        "--planilha-id",
        planilha_id,
        "--credenciais",
        credenciais,
        "--aba",
        args.aba,
        "--lote-mes-reajuste",
        args.mes,
    ]

    log(f"Disparando atualizador: {' '.join(cmd)}")
    try:
        resultado = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if resultado.stdout:
            print(resultado.stdout)
        if resultado.stderr:
            print(resultado.stderr, file=sys.stderr)
        sys.exit(resultado.returncode)
    except Exception as e:
        log(f"ERRO ao executar atualizador: {e}")
        sys.exit(4)


if __name__ == "__main__":
    main()


