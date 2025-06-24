#!/usr/bin/env python3
"""
Main de produção para execução do RPA Sienge

Executa o RPA de reparcelamento no Sienge ERP.
Utiliza variáveis de ambiente para configuração.

Pode ser chamado por agendadores, CI/CD ou manualmente.
"""
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from rpa_sienge import RPASienge

# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def credenciais_sienge_env():
    """Carrega credenciais do Sienge das variáveis de ambiente"""
    return {
        "url": os.getenv("SIENGE_URL", "https://sienge.com.br"),
        "usuario": os.getenv("SIENGE_USUARIO", "usuario"),
        "senha": os.getenv("SIENGE_SENHA", "senha"),
        "empresa": os.getenv("SIENGE_EMPRESA", "1")
    }


async def main():
    log("Iniciando execução do RPA Sienge (produção)...")
    credenciais = credenciais_sienge_env()

    # TODO: Implementar busca do próximo contrato da fila
    # Exemplo mock:
    contrato = {
        "numero_titulo": os.getenv("SIENGE_CONTRATO_TITULO", "123456"),
        "cliente": os.getenv("SIENGE_CONTRATO_CLIENTE", "Cliente Teste")
    }

    if not contrato["numero_titulo"]:
        log("ERRO: Número do título do contrato não definido.")
        sys.exit(1)

    rpa = RPASienge()  # Browser visível por padrão
    await rpa.inicializar()
    resultado = await rpa.executar(
        contrato=contrato,
        credenciais_sienge=credenciais,
        indices=None,  # Pode ser carregado conforme necessário
        etapa="completa",
        autorizar_reparcelamento=False,
        notificar_analista=True
    )
    await rpa.finalizar()

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
    except Exception as e:
        log(f"Erro fatal: {e}")
        sys.exit(1)
