#!/usr/bin/env python3
"""
Main de produção para execução do RPA Coleta de Índices Econômicos

Executa o RPA de coleta de índices, atualiza a planilha Google Sheets e salva os dados.
Utiliza variáveis de ambiente para configuração.

Pode ser chamado por agendadores, CI/CD ou manualmente.
"""
from rpa_coleta_indices.rpa_coleta_indices import executar_coleta_indices
import os
import sys
import asyncio
import argparse
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
    """Executa o RPA de coleta de índices em produção."""
    # Configurar argumentos de linha de comando
    parser = argparse.ArgumentParser(description='RPA Coleta de Índices')
    parser.add_argument('--teste', action='store_true',
                        help='Executar em modo teste usando planilha de teste')
    args = parser.parse_args()

    # Configurar modo teste se solicitado
    if args.teste:
        log("🧪 MODO TESTE ATIVADO: Usando planilha de teste")
        # Substituir PLANILHA_CALCULO_ID por PLANILHA_TESTE_HOM
        if os.getenv("PLANILHA_TESTE_HOM"):
            os.environ["PLANILHA_CALCULO_ID"] = os.getenv("PLANILHA_TESTE_HOM")
            log(
                f"🔄 Redirecionado para planilha de teste: {os.getenv('PLANILHA_TESTE_HOM')}")
        else:
            log("⚠️ PLANILHA_TESTE_HOM não configurada, usando planilha de produção")
    else:
        log("🏭 MODO PRODUÇÃO: Usando planilha de produção")

    log("Iniciando execução do RPA Coleta de Índices...")

    planilha_calculo_id = get_env_or_fail("PLANILHA_CALCULO_ID")
    credenciais_google = os.getenv(
        "GOOGLE_CREDENTIALS_PATH", "./gspread-credentials.json")

    resultado = await executar_coleta_indices(
        planilha_id=planilha_calculo_id,
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
