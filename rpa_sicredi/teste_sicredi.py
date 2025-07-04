#!/usr/bin/env python3
"""
Teste Independente - RPA Sicredi
Permite testar o RPA Sicredi fora da orquestração Temporal para desenvolvimento e homologação
Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
from typing import Dict, Any, List
from datetime import datetime
from rpa_sicredi import RPASicredi
from core.data_manager import data_manager
import logging

# Configuração global de logging para garantir logs do RPABrowser
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("RPABrowser").setLevel(logging.DEBUG)

# --- Funções auxiliares ---


async def executar_processamento_sicredi(contrato: Dict[str, Any], cnpj_empresa: str) -> Any:
    """
    Executa o processamento Sicredi para um contrato e CNPJ de empresa.
    """
    # TODO: Ajustar caminho do arquivo de remessa conforme integração real
    arquivo_remessa = contrato.get(
        "arquivo_remessa", "dados_extraidos/arquivo_remessa/19605620.219")
    credenciais_sicredi = {
        "url": os.getenv("SICREDI_URL", "https://www.sicredi.com.br/home/"),
        "usuario": os.getenv("SICREDI_USUARIO", "usuario_teste"),
        "senha": os.getenv("SICREDI_SENHA", "senha_teste"),
        "cnpj": cnpj_empresa
    }
    parametros = {
        "arquivo_remessa": arquivo_remessa,
        "credenciais_sicredi": credenciais_sicredi,
        "dados_processamento": contrato,
        "cnpj_empresa": cnpj_empresa
    }
    rpa = RPASicredi()
    await rpa.inicializar()
    resultado = await rpa.executar(parametros)
    return resultado


async def carregar_contratos_aptos_sicredi() -> List[Dict[str, Any]]:
    await data_manager.inicializar()
    contratos = await data_manager.buscar_contratos_aptos_reparcelamento()
    if not contratos:
        print("❌ Nenhum contrato apto encontrado para Sicredi.")
    else:
        print(f"✅ {len(contratos)} contratos aptos encontrados para Sicredi.")
    return contratos


async def teste_incremental_sicredi():
    print("🧪 TESTE RPA SICREDI INCREMENTAL")
    print("=" * 50)
    contratos = await carregar_contratos_aptos_sicredi()
    if not contratos:
        return False
    resultados = []
    for i, contrato in enumerate(contratos):
        print("-" * 60)
        dados_completos = contrato.get("dados_completos", {})
        empresa_nome = (
            dados_completos.get("Empresa")
            or dados_completos.get("empresa")
            or contrato.get("empreendimento")
            or contrato.get("empresa")
            or ""
        )
        print(f"[{i+1}/{len(contratos)}] Processando contrato: {contrato.get('numero_titulo', 'N/A')} - Empresa: {empresa_nome}")
        cnpj_empresa = await data_manager.buscar_cnpj_por_empresa(empresa_nome)
        if not cnpj_empresa:
            print(f"❌ CNPJ não encontrado para empresa: {empresa_nome}")
            resultados.append(
                {"sucesso": False, "mensagem": f"CNPJ não encontrado para {empresa_nome}"})
            continue
        print(f"🔗 CNPJ encontrado: {cnpj_empresa}")
        resultado = await executar_processamento_sicredi(contrato, cnpj_empresa)
        if resultado and getattr(resultado, 'sucesso', False):
            print(f"   ✅ Sucesso: {getattr(resultado, 'mensagem', '')}")
        else:
            print(f"   ❌ Falha: {getattr(resultado, 'mensagem', '')}")
            print(
                f"      ERRO: {getattr(resultado, 'erro', 'Erro desconhecido')}")
        resultados.append(resultado)
    # Resumo final
    sucessos = sum(1 for r in resultados if r and getattr(r, 'sucesso', False))
    falhas = len(resultados) - sucessos
    print("=" * 60)
    print(
        f"📈 RESUMO FINAL: Sucessos: {sucessos} | Falhas: {falhas} | Total: {len(resultados)}")
    print("=" * 60)
    return sucessos > 0


def menu_interativo():
    print("\n🎯 MENU DE TESTES - RPA SICREDI")
    print("=" * 50)
    print("1. 🚀 Teste Incremental Sicredi (Contratos Aptos)")
    print("2. ❌ Sair")
    print("=" * 50)
    while True:
        try:
            opcao = input("\n👉 Escolha uma opção (1-2): ").strip()
            if opcao == "1":
                return teste_incremental_sicredi()
            elif opcao == "2":
                print("👋 Encerrando testes...")
                return None
            else:
                print("❌ Opção inválida! Escolha entre 1-2.")
        except KeyboardInterrupt:
            print("\n👋 Teste interrompido pelo usuário")
            return None


async def main():
    print("🤖 SISTEMA DE TESTES RPA - SICREDI")
    print("Desenvolvido em Python")
    print("Permite testar RPA independente da orquestração Temporal")
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        if comando == "incremental":
            sucesso = await teste_incremental_sicredi()
        else:
            print(f"❌ Comando inválido: {comando}")
            print("Comandos disponíveis: incremental")
            return False
        return sucesso
    else:
        teste_escolhido = menu_interativo()
        if teste_escolhido:
            sucesso = await teste_escolhido
            if sucesso:
                print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
            else:
                print("\n❌ TESTE FALHOU!")
            return sucesso
        return True

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        resultado = asyncio.run(main())
        if resultado is not None:
            sys.exit(0 if resultado else 1)
        else:
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n👋 Teste cancelado pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erro fatal: {str(e)}")
        sys.exit(1)
