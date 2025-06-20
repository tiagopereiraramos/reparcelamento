#!/usr/bin/env python3
"""
Teste Independente - RPA Sienge
Permite testar o RPA fora da orquestração Temporal para desenvolvimento e homologação
Desenvolvido em Português Brasileiro
"""

from rpa_sienge import RPASienge
import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, List
import json

# Adiciona diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Funções auxiliares ---


async def executar_processamento_sienge(contrato: Dict[str, Any],
                                        indices_economicos: Dict[str, Any],
                                        credenciais_sienge: Dict[str, str],
                                        etapa: str = "completa",
                                        autorizar_reparcelamento: bool = False,
                                        notificar_analista: bool = True):
    try:
        rpa = RPASienge()
        await rpa.inicializar()
        resultado = await rpa.executar(
            contrato=contrato,
            credenciais_sienge=credenciais_sienge,
            indices=indices_economicos,
            etapa=etapa,
            autorizar_reparcelamento=autorizar_reparcelamento,
            notificar_analista=notificar_analista
        )
        await rpa.finalizar()
        return resultado
    except Exception as e:
        from core.base_rpa import ResultadoRPA
        return ResultadoRPA(
            sucesso=False,
            mensagem="Erro na execução do RPA Sienge",
            erro=str(e)
        )


async def carregar_fila_contratos() -> List[Dict[str, Any]]:
    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()
        print("🔍 Carregando fila de contratos...")
        fila_dados = await data_manager.obter_fila_sienge()
        contratos = fila_dados.get("contratos", []) if fila_dados else []
        if contratos:
            print(f"✅ Fila carregada: {len(contratos)} contratos")
            for i, contrato in enumerate(contratos[:3]):
                print(
                    f"   {i+1}. {contrato.get('numero_titulo', 'N/A')} - {contrato.get('cliente', 'N/A')} [{contrato.get('status_processamento', 'N/A')}]")
            if len(contratos) > 3:
                print(f"   ... e mais {len(contratos)-3} contratos")
            return contratos
        else:
            print("⚠️ Nenhuma fila encontrada.")
            return []
    except Exception as e:
        print(f"❌ Erro ao carregar fila: {str(e)}")
        return []


async def carregar_indices_economicos() -> Dict[str, Any]:
    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()
        print("📈 Carregando índices econômicos...")
        # Busca os dois índices separadamente
        ipca = await data_manager.obter_indice_mais_recente("ipca")
        igpm = await data_manager.obter_indice_mais_recente("igpm")
        if ipca is not None and igpm is not None:
            print(
                f"✅ Índices carregados do sistema: IPCA={ipca} | IGPM={igpm}")
            return {
                "ipca": {"valor": ipca, "tipo": "IPCA", "periodo": "Recente"},
                "igpm": {"valor": igpm, "tipo": "IGPM", "periodo": "Recente"}
            }
        else:
            print("📊 Usando índices simulados")
            return {
                "ipca": {"valor": 4.62, "tipo": "IPCA", "periodo": "Dezembro/2024"},
                "igpm": {"valor": 3.89, "tipo": "IGPM", "periodo": "Dezembro/2024"}
            }
    except Exception as e:
        print(f"❌ Erro ao carregar índices: {str(e)}")
        return {
            "ipca": {"valor": 4.62, "tipo": "IPCA", "periodo": "Dezembro/2024"},
            "igpm": {"valor": 3.89, "tipo": "IGPM", "periodo": "Dezembro/2024"}
        }

# --- Funções de teste incremental ---


async def teste_completo():
    print("🧪 TESTE RPA SIENGE COMPLETO")
    print("=" * 50)
    contratos_fila = await carregar_fila_contratos()
    if not contratos_fila:
        print("❌ Nenhum contrato encontrado na fila.")
        return False
    indices_economicos = await carregar_indices_economicos()
    print(
        f"   IPCA: {indices_economicos['ipca']['valor']}% | IGPM: {indices_economicos['igpm']['valor']}%")
    contratos_teste = contratos_fila[:3]
    resultados = []
    for i, contrato in enumerate(contratos_teste):
        resultado = await executar_processamento_sienge(
            contrato, indices_economicos, credenciais_sienge_env())
        resultados.append(resultado)
        if i < len(contratos_teste) - 1:
            print("   ⏳ Aguardando 2 segundos...")
            await asyncio.sleep(2)
    sucessos = sum(1 for r in resultados if r and r.sucesso)
    falhas = len(resultados) - sucessos
    print(
        f"\n📈 RESUMO DO TESTE: Sucessos: {sucessos} | Falhas: {falhas} | Total: {len(resultados)}")
    return sucessos > 0


async def teste_contrato_unico():
    print("🧪 TESTE CONTRATO ÚNICO - COMPLETO")
    print("=" * 40)
    contrato_teste = {
        "numero_titulo": "TEST123456789",
        "cliente": "CLIENTE TESTE LTDA",
        "empreendimento": "EMPREENDIMENTO TESTE",
        "cnpj_unidade": "12.345.678/0001-90",
        "indexador": "IPCA",
        "ultimo_reajuste": "01/01/2023"
    }
    indices_economicos = await carregar_indices_economicos()
    print(f"🏢 Contrato de Teste: {contrato_teste['numero_titulo']}")
    print(f"👤 Cliente: {contrato_teste['cliente']}")
    print(f"🔐 URL Sienge: {credenciais_sienge_env()['url']}")
    resultado = await executar_processamento_sienge(
        contrato=contrato_teste,
        indices_economicos=indices_economicos,
        credenciais_sienge=credenciais_sienge_env(),
        etapa="completa",
        autorizar_reparcelamento=True,
        notificar_analista=False)
    print("\n📋 RESULTADO DA EXECUÇÃO:")
    print("-" * 30)
    print(f"Sucesso: {'✅ SIM' if resultado.sucesso else '❌ NÃO'}")
    print(f"Mensagem: {resultado.mensagem}")
    if resultado.sucesso and resultado.dados:
        print(json.dumps(resultado.dados, indent=2, ensure_ascii=False))
    if not resultado.sucesso:
        print(f"\n❌ ERRO: {resultado.erro or 'Erro desconhecido'}")
    return resultado.sucesso


async def teste_etapa_consulta():
    print("🧪 TESTE ETAPA 1 - CONSULTA DE RELATÓRIOS (FILA REAL)")
    print("=" * 60)
    contratos_fila = await carregar_fila_contratos()
    if not contratos_fila:
        print("❌ Nenhum contrato encontrado na fila real.")
        return False
    indices_economicos = await carregar_indices_economicos()
    credenciais = credenciais_sienge_env()
    rpa = RPASienge()
    await rpa.inicializar()
    rpa._configurar_credenciais(credenciais)
    await rpa._fazer_login_sienge()
    print("✅ Login único realizado - processando fila...")
    sucessos = 0
    falhas = 0
    for i, contrato_fila in enumerate(contratos_fila):
        print(
            f"\n📄 [{i+1}/{len(contratos_fila)}] Processando: {contrato_fila.get('numero_titulo', 'N/A')}")
        try:
            dados_financeiros = await rpa._consultar_relatorios_financeiros(contrato_fila)
            if dados_financeiros.get("sucesso"):
                sucessos += 1
                print(f"   ✅ Sucesso - Planilha processada")
            else:
                falhas += 1
                print(
                    f"   ❌ Falha: {dados_financeiros.get('erro', 'Erro desconhecido')}")
            if i < len(contratos_fila) - 1:
                print("   ⏳ Aguardando 3 segundos...")
                await asyncio.sleep(3)
        except Exception as e:
            falhas += 1
            print(f"   ❌ Erro inesperado: {str(e)}")
            continue
    await rpa.finalizar()
    print(
        f"\n📈 RESUMO DO PROCESSAMENTO: Sucessos: {sucessos} | Falhas: {falhas} | Total: {len(contratos_fila)}")
    return sucessos > 0

# ... (demais funções: etapa 2 reparcelamento, validação, cálculo, saúde, menu, main) ...


def credenciais_sienge_env():
    return {
        "url": os.getenv("SIENGE_URL", "https://sienge-teste.com"),
        "usuario": os.getenv("SIENGE_USERNAME", "tc@trajetoriaconsultoria.com.br"),
        "senha": os.getenv("SIENGE_PASSWORD", "senha_teste")
    }


def menu_interativo():
    print("\n🎯 MENU DE TESTES - RPA SIENGE")
    print("=" * 50)
    print("1. 🚀 Teste Completo (Processamento Fila)")
    print("2. 🏢 Teste Contrato Único")
    print("3. 🔍 Teste Etapa 1 - Consulta")
    print("4. ❌ Sair")
    print("=" * 50)
    while True:
        try:
            opcao = input("\n👉 Escolha uma opção (1-4): ").strip()
            if opcao == "1":
                return teste_completo()
            elif opcao == "2":
                return teste_contrato_unico()
            elif opcao == "3":
                return teste_etapa_consulta()
            elif opcao == "4":
                print("👋 Encerrando testes...")
                return None
            else:
                print("❌ Opção inválida! Escolha entre 1-4.")
        except KeyboardInterrupt:
            print("\n👋 Teste interrompido pelo usuário")
            return None


async def main():
    print("🤖 SISTEMA DE TESTES RPA - SIENGE")
    print("Desenvolvido em Python")
    print("Permite testar RPA independente da orquestração Temporal")
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        if comando == "completo":
            sucesso = await teste_completo()
        elif comando == "unico":
            sucesso = await teste_contrato_unico()
        elif comando == "consulta":
            sucesso = await teste_etapa_consulta()
        else:
            print(f"❌ Comando inválido: {comando}")
            print("Comandos disponíveis: completo, unico, consulta")
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
