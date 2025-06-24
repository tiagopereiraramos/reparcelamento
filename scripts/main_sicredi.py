#!/usr/bin/env python3
"""
Main de produção para execução do RPA Sicredi

Executa o RPA Sicredi para contratos aptos a reparcelamento.
Utiliza variáveis de ambiente para configuração.

Pode ser chamado por agendadores, CI/CD ou manualmente.
"""
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from rpa_sicredi import RPASicredi
from core.data_manager import data_manager

# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def credenciais_sicredi_env(cnpj_empresa):
    """Carrega credenciais do Sicredi das variáveis de ambiente"""
    return {
        "url": os.getenv("SICREDI_URL", "https://www.sicredi.com.br/home/"),
        "usuario": os.getenv("SICREDI_USUARIO", "usuario_teste"),
        "senha": os.getenv("SICREDI_SENHA", "senha_teste"),
        "cnpj": cnpj_empresa
    }


async def main():
    log("Iniciando execução do RPA Sicredi (produção)...")
    await data_manager.inicializar()
    contratos = await data_manager.buscar_contratos_aptos_reparcelamento()
    if not contratos:
        log("Nenhum contrato apto encontrado para Sicredi. Encerrando execução.")
        sys.exit(0)
    contrato = contratos[0]
    dados_completos = contrato.get("dados_completos", {})
    empresa_nome = (
        dados_completos.get("Empresa")
        or dados_completos.get("empresa")
        or contrato.get("empreendimento")
        or contrato.get("empresa")
        or ""
    )
    cnpj_empresa = await data_manager.buscar_cnpj_por_empresa(empresa_nome)
    if not cnpj_empresa:
        log(
            f"CNPJ não encontrado para empresa: {empresa_nome}. Encerrando execução.")
        sys.exit(0)
    log(f"Processando contrato: {contrato.get('numero_titulo', 'N/A')} - Empresa: {empresa_nome} - CNPJ: {cnpj_empresa}")
    arquivo_remessa = contrato.get(
        "arquivo_remessa", "outputs/2025/06/24/logs20250624.txt")
    parametros = {
        "arquivo_remessa": arquivo_remessa,
        "credenciais_sicredi": credenciais_sicredi_env(cnpj_empresa),
        "dados_processamento": contrato,
        "cnpj_empresa": cnpj_empresa
    }
    rpa = RPASicredi()  # Browser visível por padrão
    await rpa.inicializar()
    resultado = await rpa.executar(parametros)
    await rpa.finalizar()
    if resultado and getattr(resultado, 'sucesso', False):
        log(f"SUCESSO: {getattr(resultado, 'mensagem', '')}")
        sys.exit(0)
    else:
        log(f"FALHA: {getattr(resultado, 'mensagem', '')}")
        log(f"Detalhe do erro: {getattr(resultado, 'erro', 'Erro desconhecido')}")
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
