#!/usr/bin/env python3
"""
Main de produção para execução do RPA Análise de Planilhas

Executa o RPA de análise das planilhas, identifica contratos para reparcelamento e salva a fila de processamento.
Utiliza variáveis de ambiente para configuração.

Pode ser chamado por agendadores, CI/CD ou manualmente.
A persistência híbrida (MongoDB + JSON) é garantida pelo core do RPA.
"""
from rpa_analise_planilhas import executar_analise_planilhas
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Garante execução headless em produção
os.environ["HEADLESS"] = "1"  # Força modo headless para Selenium/Browser

# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


def log(msg):
    """Loga mensagem com timestamp."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def get_env_or_fail(var_name, default=None):
    """Obtém variável de ambiente ou encerra o programa se não definida."""
    value = os.getenv(var_name, default)
    if not value:
        log(f"ERRO: Variável de ambiente obrigatória não definida: {var_name}")
        sys.exit(1)
    return value


async def main():
    """Executa o RPA de análise de planilhas em produção."""
    log("Iniciando execução do RPA Análise de Planilhas (produção)...")

    planilha_calculo_id = get_env_or_fail("PLANILHA_CALCULO_ID")
    planilha_apoio_id = get_env_or_fail("PLANILHA_APOIO_ID")
    credenciais_google = os.getenv(
        "GOOGLE_CREDENTIALS_PATH", "./gspread-credentials.json")

    # Ao chamar o RPA, garanta que headless=True está sendo passado para execução em produção.
    resultado = await executar_analise_planilhas(
        planilha_calculo_id=planilha_calculo_id,
        planilha_apoio_id=planilha_apoio_id,
        credenciais_google=credenciais_google,
        headless=True
    )

    if resultado.sucesso:
        log(f"SUCESSO: {resultado.mensagem}")
        sys.exit(0)
    else:
        log(f"FALHA: {resultado.mensagem}")
        if resultado.erro:
            log(f"Detalhe do erro: {resultado.erro}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Execução interrompida pelo usuário.")
        sys.exit(130)
    except Exception as e:  # pylint: disable=broad-exception-caught
        log(f"Erro fatal: {e}")
        sys.exit(1)
