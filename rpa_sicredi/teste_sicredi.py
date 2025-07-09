#!/usr/bin/env python3
"""
Teste Independente - RPA Sicredi
Permite testar o RPA Sicredi fora da orquestração Temporal para desenvolvimento e homologação

NOVA ARQUITETURA COM PAUSAS:
- Diagnóstico de arquivos de remessa
- Processamento por empresa/CNPJ
- Pausas estratégicas para acompanhamento
- Relatório detalhado

Desenvolvido em Português Brasileiro
"""

import asyncio
import sys
import os
from typing import Dict, Any, List
from datetime import datetime
from rpa_sicredi import RPASicredi
from core.data_manager import data_manager
from core.mongodb_manager import mongodb_manager
import logging

# Configuração global de logging para garantir logs do RPABrowser
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("RPABrowser").setLevel(logging.DEBUG)

# --- Funções auxiliares ---


def log(msg):
    """Loga mensagem com timestamp."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def notificar_sucesso_simples(titulo: str, mensagem: str):
    """Notificação simples de sucesso via log"""
    log(f"✅ NOTIFICAÇÃO: {titulo}")
    log(f"   📋 {mensagem}")


def notificar_erro_simples(titulo: str, mensagem: str):
    """Notificação simples de erro via log"""
    log(f"❌ NOTIFICAÇÃO: {titulo}")
    log(f"   📋 {mensagem}")


def get_env_or_fail(var_name, default=None):
    """Obtém variável de ambiente ou encerra o programa se não definida."""
    value = os.getenv(var_name, default)
    if not value:
        log(f"ERRO: Variável de ambiente obrigatória não definida: {var_name}")
        sys.exit(1)
    return value


async def carregar_credenciais_sicredi() -> Dict[str, str]:
    """Carrega e valida credenciais do Sicredi das variáveis de ambiente."""
    log("🔑 Carregando credenciais do Sicredi...")

    credenciais = {
        "url": get_env_or_fail("SICREDI_URL", "https://www.sicredi.com.br/home/"),
        "usuario": get_env_or_fail("SICREDI_USUARIO"),
        "senha": get_env_or_fail("SICREDI_SENHA")
    }

    log(
        f"✅ Credenciais carregadas: {credenciais['usuario']} @ {credenciais['url']}")
    return credenciais


async def diagnosticar_arquivos_remessa() -> Dict[str, Any]:
    """
    DIAGNÓSTICO: Analisa arquivos de remessa disponíveis para processamento
    """
    log("📊 DIAGNÓSTICO DE ARQUIVOS DE REMESSA")
    log("=" * 60)

    try:
        # Conectar ao MongoDB
        if not mongodb_manager.conectado:
            await mongodb_manager.conectar()

        if mongodb_manager.database is None:
            raise Exception("Database não disponível")

        collection = mongodb_manager.database.fila_contratos

        # Buscar contratos com carnês gerados (status CARNE_GERADO)
        contratos_carne_gerado = list(
            collection.find({"status": "CARNE_GERADO"}))

        # Agrupar por empresa
        empresas_arquivos = {}
        for contrato in contratos_carne_gerado:
            empresa = contrato.get("empresa", "Empresa Desconhecida")
            arquivo_remessa = contrato.get("arquivo_remessa", "")

            if arquivo_remessa and os.path.exists(arquivo_remessa):
                if empresa not in empresas_arquivos:
                    empresas_arquivos[empresa] = {
                        "arquivos": [],
                        "contratos": [],
                        "cnpj": contrato.get("cnpj_empresa", "")
                    }

                empresas_arquivos[empresa]["arquivos"].append(arquivo_remessa)
                empresas_arquivos[empresa]["contratos"].append(contrato)

        # Estatísticas detalhadas
        diagnostico = {
            "total_contratos_carne_gerado": len(contratos_carne_gerado),
            "empresas_com_arquivos": len(empresas_arquivos),
            "empresas_arquivos": empresas_arquivos,
            "arquivos_validos": sum(len(dados["arquivos"]) for dados in empresas_arquivos.values()),
            "timestamp_diagnostico": datetime.now().isoformat()
        }

        # Log do diagnóstico
        log(f"📋 ESTATÍSTICAS DOS ARQUIVOS:")
        log(
            f"   📄 Total de contratos com carnê gerado: {diagnostico['total_contratos_carne_gerado']}")
        log(
            f"   🏢 Empresas com arquivos: {diagnostico['empresas_com_arquivos']}")
        log(f"   📁 Arquivos válidos: {diagnostico['arquivos_validos']}")

        if empresas_arquivos:
            log(f"🏢 EMPRESAS COM ARQUIVOS DE REMESSA:")
            for empresa, dados in empresas_arquivos.items():
                log(
                    f"   📋 {empresa}: {len(dados['arquivos'])} arquivos, {len(dados['contratos'])} contratos")
                if dados.get("cnpj"):
                    log(f"      🏦 CNPJ: {dados['cnpj']}")

        # Determinar estratégia de processamento
        if diagnostico["arquivos_validos"] == 0:
            log("⚠️ Nenhum arquivo de remessa válido encontrado")
            return diagnostico

        log(f"\n🎯 EMPRESAS QUE SERÃO PROCESSADAS:")
        for empresa, dados in empresas_arquivos.items():
            log(f"   🏢 {empresa}: {len(dados['arquivos'])} arquivos")

        return diagnostico

    except Exception as e:
        log(f"❌ Erro no diagnóstico: {str(e)}")
        raise


async def processar_empresa_sicredi(
    empresa: str,
    arquivos_remessa: List[str],
    contratos: List[Dict[str, Any]],
    credenciais: Dict[str, str]
) -> Dict[str, Any]:
    """
    Processa uma empresa específica no Sicredi

    Args:
        empresa: Nome da empresa
        arquivos_remessa: Lista de arquivos de remessa da empresa
        contratos: Lista de contratos da empresa
        credenciais: Credenciais do Sicredi

    Returns:
        Resultado do processamento da empresa
    """
    log(f"\n🏢 PROCESSANDO EMPRESA: {empresa}")
    log("=" * 60)
    log(f"📁 Arquivos de remessa: {len(arquivos_remessa)}")
    log(f"📋 Contratos: {len(contratos)}")

    try:
        notificar_sucesso_simples(
            f"🚀 INICIANDO: Processamento Sicredi para {empresa}",
            f"Arquivos: {len(arquivos_remessa)} | Contratos: {len(contratos)}"
        )

        # BREAKPOINT: Antes de inicializar RPA
        print(f"\n⏸️  BREAKPOINT: Antes de processar empresa {empresa}")
        print(f"   📁 Arquivos: {len(arquivos_remessa)}")
        print(f"   📋 Contratos: {len(contratos)}")
        input(f"   Pressione ENTER para processar {empresa}...")

        # Inicializar RPA
        headless = os.getenv("HEADLESS", "false").lower() == "true"
        log(f"🌐 Inicializando RPA (headless: {headless})...")

        rpa = RPASicredi()
        await rpa.inicializar()

        log(f"✅ RPA inicializado com sucesso (headless: {headless})")

        resultados_arquivos = []
        sucessos = 0
        erros = 0

        # Processar cada arquivo de remessa da empresa
        for i, arquivo_remessa in enumerate(arquivos_remessa):
            log(f"📁 Processando arquivo {i+1}/{len(arquivos_remessa)}: {arquivo_remessa}")

            # BREAKPOINT: Antes de processar arquivo
            print(
                f"\n⏸️  BREAKPOINT: Antes de processar arquivo {i+1}/{len(arquivos_remessa)}")
            print(f"   📁 Arquivo: {arquivo_remessa}")
            print(f"   🏢 Empresa: {empresa}")
            input(f"   Pressione ENTER para processar este arquivo...")

            # Preparar parâmetros
            parametros = {
                "arquivo_remessa": arquivo_remessa,
                "credenciais_sicredi": credenciais,
                "dados_processamento": {
                    "empresa": empresa,
                    "contratos": contratos,
                    "arquivo": arquivo_remessa
                }
            }

            # Executar processamento
            resultado = await rpa.executar(parametros)

            if resultado.sucesso:
                sucessos += 1
                log(f"✅ Arquivo processado com sucesso: {arquivo_remessa}")
            else:
                erros += 1
                log(f"❌ Erro no arquivo: {arquivo_remessa} - {resultado.erro}")

            resultados_arquivos.append({
                "arquivo": arquivo_remessa,
                "sucesso": resultado.sucesso,
                "mensagem": resultado.mensagem,
                "erro": resultado.erro if not resultado.sucesso else None
            })

        await rpa.finalizar()

        # Processar resultado
        resultado_empresa = {
            "empresa": empresa,
            "sucesso": sucessos > 0,  # Pelo menos um arquivo foi processado
            "arquivos_processados": sucessos,
            "arquivos_erro": erros,
            "total_arquivos": len(arquivos_remessa),
            "resultados_detalhados": resultados_arquivos,
            "contratos_envolvidos": len(contratos)
        }

        if resultado_empresa["sucesso"]:
            log(f"✅ EMPRESA {empresa} CONCLUÍDA:")
            log(f"   ✅ Arquivos processados: {sucessos}")
            log(f"   ❌ Arquivos com erro: {erros}")
            log(f"   📊 Taxa de sucesso: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%")

            notificar_sucesso_simples(
                f"✅ EMPRESA {empresa} CONCLUÍDA",
                f"Sucessos: {sucessos} | Erros: {erros} | Taxa: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%"
            )
        else:
            log(f"❌ EMPRESA {empresa} FALHOU: Todos os arquivos com erro")

            notificar_erro_simples(
                f"❌ EMPRESA {empresa} FALHOU",
                f"Todos os {len(arquivos_remessa)} arquivos com erro"
            )

        return resultado_empresa

    except Exception as e:
        erro_msg = f"Erro crítico no processamento da empresa {empresa}: {str(e)}"
        log(f"💥 {erro_msg}")

        notificar_erro_simples(
            f"💥 EMPRESA {empresa} ERRO CRÍTICO",
            erro_msg
        )

        return {
            "empresa": empresa,
            "sucesso": False,
            "erro": erro_msg,
            "arquivos_processados": 0,
            "arquivos_erro": len(arquivos_remessa),
            "total_arquivos": len(arquivos_remessa)
        }


async def teste_sicredi_completo():
    """
    TESTE COMPLETO: RPA Sicredi com pausas estratégicas
    """
    log("🧪 TESTE COMPLETO - RPA SICREDI COM PAUSAS")
    log("=" * 70)
    log("🎯 ARQUITETURA: Diagnóstico → Processamento por empresa → Relatório")
    log("✅ PAUSAS ESTRATÉGICAS: Para acompanhamento completo")
    log("=" * 70)

    # BREAKPOINT 0: Início do teste
    print("\n⏸️  BREAKPOINT 0: Início do teste")
    print("   🧪 Teste de processamento Sicredi")
    print("   📋 Vamos configurar o teste passo a passo")
    input("   Pressione ENTER para começar...")

    try:
        # FASE 1: PREPARAÇÃO E DIAGNÓSTICO
        log("🔧 FASE 1: PREPARAÇÃO E DIAGNÓSTICO")
        log("-" * 40)

        credenciais = await carregar_credenciais_sicredi()

        # BREAKPOINT 1: Credenciais carregadas
        print("\n⏸️  BREAKPOINT 1: Credenciais carregadas")
        print(f"   🔗 URL: {credenciais['url']}")
        print(f"   👤 Usuário: {credenciais['usuario']}")
        input("   Pressione ENTER para diagnosticar arquivos...")

        diagnostico = await diagnosticar_arquivos_remessa()

        # Verificar se há trabalho a fazer
        if diagnostico["arquivos_validos"] == 0:
            log("✅ Nenhum arquivo de remessa válido encontrado - execução desnecessária")
            notificar_sucesso_simples(
                "✅ RPA SICREDI: Execução desnecessária",
                "Todos os arquivos já foram processados ou não há arquivos válidos"
            )
            return True

        log(
            f"📋 Total de arquivos válidos identificados: {diagnostico['arquivos_validos']}")

        # BREAKPOINT 2: Diagnóstico concluído
        print("\n⏸️  BREAKPOINT 2: Diagnóstico concluído")
        print(f"   🏢 Empresas: {diagnostico['empresas_com_arquivos']}")
        print(f"   📁 Arquivos: {diagnostico['arquivos_validos']}")
        input("   Pressione ENTER para iniciar processamento...")

        # EXECUÇÃO POR EMPRESA
        resultados_empresas = {}

        for empresa, dados in diagnostico["empresas_arquivos"].items():
            arquivos_remessa = dados["arquivos"]
            contratos = dados["contratos"]

            # Processar empresa no Sicredi
            resultado_empresa = await processar_empresa_sicredi(
                empresa,
                arquivos_remessa,
                contratos,
                credenciais
            )

            resultados_empresas[empresa] = resultado_empresa

        # BREAKPOINT 3: Processamento concluído
        print("\n⏸️  BREAKPOINT 3: Processamento concluído")
        print("   📊 Gerando relatório final...")
        input("   Pressione ENTER para ver o relatório...")

        # RELATÓRIO FINAL
        log("\n📊 RELATÓRIO FINAL")
        log("=" * 60)

        # Calcular estatísticas gerais
        total_empresas = len(resultados_empresas)
        empresas_sucesso = len(
            [r for r in resultados_empresas.values() if r.get("sucesso")])
        empresas_falha = total_empresas - empresas_sucesso

        total_arquivos = sum(r.get("total_arquivos", 0)
                             for r in resultados_empresas.values())
        total_processados = sum(r.get("arquivos_processados", 0)
                                for r in resultados_empresas.values())
        total_erros = sum(r.get("arquivos_erro", 0)
                          for r in resultados_empresas.values())

        log(f"📈 ESTATÍSTICAS FINAIS:")
        log(f"   🏢 Total de empresas: {total_empresas}")
        log(f"   ✅ Empresas bem-sucedidas: {empresas_sucesso}")
        log(f"   ❌ Empresas com falha: {empresas_falha}")
        log(f"   📁 Total de arquivos: {total_arquivos}")
        log(f"   ✅ Arquivos processados: {total_processados}")
        log(f"   ❌ Arquivos com erro: {total_erros}")
        log(f"   📊 Taxa de sucesso empresas: {(empresas_sucesso/total_empresas*100) if total_empresas > 0 else 0:.1f}%")
        log(f"   📊 Taxa de sucesso arquivos: {(total_processados/total_arquivos*100) if total_arquivos > 0 else 0:.1f}%")

        # Determinar sucesso geral
        sucesso_geral = empresas_sucesso > 0  # Pelo menos uma empresa teve sucesso

        if sucesso_geral:
            log(f"\n🎉 PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
            log(f"✅ Empresas bem-sucedidas: {empresas_sucesso}/{total_empresas}")

            notificar_sucesso_simples(
                f"🎉 RPA SICREDI: Processamento concluído",
                f"Empresas: {empresas_sucesso}/{total_empresas} | Arquivos: {total_processados}"
            )

            return True
        else:
            log(f"\n❌ PROCESSAMENTO FALHOU EM TODAS AS EMPRESAS")

            notificar_erro_simples(
                f"❌ RPA SICREDI: Falha completa",
                f"Todas as empresas falharam - Verifique logs detalhados"
            )

            return False

    except Exception as e:
        log(f"💥 ERRO CRÍTICO NO PROCESSAMENTO: {str(e)}")

        notificar_erro_simples(
            f"💥 RPA SICREDI: Erro crítico",
            f"Erro: {str(e)}"
        )

        return False


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
        log("❌ Nenhum contrato apto encontrado para Sicredi.")
    else:
        log(f"✅ {len(contratos)} contratos aptos encontrados para Sicredi.")
    return contratos


async def teste_incremental_sicredi():
    log("🧪 TESTE RPA SICREDI INCREMENTAL")
    log("=" * 50)
    contratos = await carregar_contratos_aptos_sicredi()
    if not contratos:
        return False
    resultados = []
    for i, contrato in enumerate(contratos):
        log("-" * 60)
        dados_completos = contrato.get("dados_completos", {})
        empresa_nome = (
            dados_completos.get("Empresa")
            or dados_completos.get("empresa")
            or contrato.get("empreendimento")
            or contrato.get("empresa")
            or ""
        )
        log(f"[{i+1}/{len(contratos)}] Processando contrato: {contrato.get('numero_titulo', 'N/A')} - Empresa: {empresa_nome}")
        cnpj_empresa = await data_manager.buscar_cnpj_por_empresa(empresa_nome)
        if not cnpj_empresa:
            log(f"❌ CNPJ não encontrado para empresa: {empresa_nome}")
            resultados.append(
                {"sucesso": False, "mensagem": f"CNPJ não encontrado para {empresa_nome}"})
            continue
        log(f"🔗 CNPJ encontrado: {cnpj_empresa}")
        resultado = await executar_processamento_sicredi(contrato, cnpj_empresa)
        if resultado and getattr(resultado, 'sucesso', False):
            log(f"   ✅ Sucesso: {getattr(resultado, 'mensagem', '')}")
        else:
            log(f"   ❌ Falha: {getattr(resultado, 'mensagem', '')}")
            log(
                f"      ERRO: {getattr(resultado, 'erro', 'Erro desconhecido')}")
        resultados.append(resultado)
    # Resumo final
    sucessos = sum(1 for r in resultados if r and getattr(r, 'sucesso', False))
    falhas = len(resultados) - sucessos
    log("=" * 60)
    log(
        f"📈 RESUMO FINAL: Sucessos: {sucessos} | Falhas: {falhas} | Total: {len(resultados)}")
    log("=" * 60)
    return sucessos > 0


def menu_interativo():
    print("\n🎯 MENU DE TESTES - RPA SICREDI")
    print("=" * 50)
    print("1. 🚀 Teste Completo Sicredi (Com pausas estratégicas)")
    print("2. 🔄 Teste Incremental Sicredi (Contratos Aptos)")
    print("3. ❌ Sair")
    print("=" * 50)
    while True:
        try:
            opcao = input("\n👉 Escolha uma opção (1-3): ").strip()
            if opcao == "1":
                return teste_sicredi_completo()
            elif opcao == "2":
                return teste_incremental_sicredi()
            elif opcao == "3":
                print("👋 Encerrando testes...")
                return None
            else:
                print("❌ Opção inválida! Escolha entre 1-3.")
        except KeyboardInterrupt:
            print("\n👋 Teste interrompido pelo usuário")
            return None


async def main():
    print("🤖 SISTEMA DE TESTES RPA - SICREDI")
    print("Desenvolvido em Python")
    print("Permite testar RPA independente da orquestração Temporal")
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        if comando == "completo":
            sucesso = await teste_sicredi_completo()
        elif comando == "incremental":
            sucesso = await teste_incremental_sicredi()
        else:
            print(f"❌ Comando inválido: {comando}")
            print("Comandos disponíveis: completo, incremental")
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
