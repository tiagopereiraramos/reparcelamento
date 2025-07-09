#!/usr/bin/env python3
"""
Main de produção para execução do RPA Sicredi
Sistema automatizado de processamento de arquivos de remessa no Sicredi WebBank

NOVA ARQUITETURA:
- Validação de arquivos de remessa antes do processamento
- Processamento por empresa/CNPJ
- Notificações granulares
- Relatório final consolidado

CONFORME PDD SEÇÃO 10.3:
- Login no Sicredi WebBank
- Upload de arquivos de remessa por empresa
- Validação e processamento
- Confirmação da atualização dos carnês

Desenvolvido em Português Brasileiro
"""

from core.mongodb_manager import mongodb_manager
from rpa_sicredi.rpa_sicredi import RPASicredi
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Garante execução headless em produção
os.environ["HEADLESS"] = "1"  # Força modo headless para Selenium/Browser

# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


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
    Conforme PDD seção 10.3 - Processamento por empresa
    """
    log("📊 DIAGNÓSTICO DE ARQUIVOS DE REMESSA")
    log("=" * 60)

    try:
        # Conectar ao MongoDB
        if not mongodb_manager.conectado:
            await mongodb_manager.conectar()

        if not mongodb_manager.conectado or mongodb_manager.database is None:
            raise Exception("MongoDB não conectado ou database indisponível")

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

        # Inicializar RPA
        headless = os.getenv("HEADLESS", "true").lower() == "true"
        rpa = RPASicredi()
        await rpa.inicializar()

        log(f"🤖 RPA inicializado (headless: {headless})")

        resultados_arquivos = []
        sucessos = 0
        erros = 0

        # Processar cada arquivo de remessa da empresa
        for arquivo_remessa in arquivos_remessa:
            log(f"📁 Processando arquivo: {arquivo_remessa}")

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


async def atualizar_status_contratos(empresa: str, contratos: List[Dict[str, Any]], sucesso: bool):
    """
    Atualiza status dos contratos no MongoDB após processamento no Sicredi
    """
    try:
        if not mongodb_manager.conectado:
            await mongodb_manager.conectar()

        if mongodb_manager.database is None:
            raise Exception("Database não disponível")

        collection = mongodb_manager.database.fila_contratos

        novo_status = "PROCESSADO" if sucesso else "ERRO"

        for contrato in contratos:
            numero_titulo = contrato.get("numero_titulo")
            if numero_titulo:
                collection.update_one(
                    {"numero_titulo": numero_titulo},
                    {
                        "$set": {
                            "status": novo_status,
                            "data_processamento_sicredi": datetime.now(),
                            "empresa_processada": empresa
                        }
                    }
                )

        log(f"📊 Status dos contratos atualizados para: {novo_status}")

    except Exception as e:
        log(f"⚠️ Erro ao atualizar status dos contratos: {str(e)}")


async def gerar_relatorio_final(diagnostico: Dict[str, Any], resultados_empresas: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Gera relatório final consolidado do processamento
    """
    log("\n📊 GERANDO RELATÓRIO FINAL CONSOLIDADO")
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

    relatorio = {
        "timestamp_inicio": diagnostico.get("timestamp_diagnostico"),
        "timestamp_fim": datetime.now().isoformat(),
        "diagnostico_inicial": diagnostico,
        "resultados_por_empresa": resultados_empresas,
        "estatisticas_gerais": {
            "total_empresas": total_empresas,
            "empresas_sucesso": empresas_sucesso,
            "empresas_falha": empresas_falha,
            "total_arquivos": total_arquivos,
            "arquivos_processados": total_processados,
            "arquivos_erro": total_erros,
            "taxa_sucesso_empresas": (empresas_sucesso/total_empresas*100) if total_empresas > 0 else 0,
            "taxa_sucesso_arquivos": (total_processados/total_arquivos*100) if total_arquivos > 0 else 0
        }
    }

    # Log do relatório
    log(f"📈 ESTATÍSTICAS FINAIS:")
    log(f"   🏢 Total de empresas: {total_empresas}")
    log(f"   ✅ Empresas bem-sucedidas: {empresas_sucesso}")
    log(f"   ❌ Empresas com falha: {empresas_falha}")
    log(f"   📁 Total de arquivos: {total_arquivos}")
    log(f"   ✅ Arquivos processados: {total_processados}")
    log(f"   ❌ Arquivos com erro: {total_erros}")
    log(
        f"   📊 Taxa de sucesso empresas: {relatorio['estatisticas_gerais']['taxa_sucesso_empresas']:.1f}%")
    log(
        f"   📊 Taxa de sucesso arquivos: {relatorio['estatisticas_gerais']['taxa_sucesso_arquivos']:.1f}%")

    # Salvar relatório em arquivo
    try:
        relatorio_dir = Path("outputs/relatorios")
        relatorio_dir.mkdir(parents=True, exist_ok=True)

        arquivo_relatorio = relatorio_dir / \
            f"relatorio_sicredi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        import json
        with open(arquivo_relatorio, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2, default=str)

        log(f"📄 Relatório salvo: {arquivo_relatorio}")

    except Exception as e:
        log(f"⚠️ Erro ao salvar relatório: {str(e)}")

    return relatorio


async def main():
    """
    MAIN: Execução otimizada do RPA Sicredi em produção

    ESTRATÉGIA IMPLEMENTADA:
    - Diagnóstico de arquivos de remessa disponíveis
    - Processamento por empresa/CNPJ
    - Validações conforme PDD 10.3
    - Notificações granulares
    - Relatório consolidado
    """
    inicio_execucao = datetime.now()

    log("🤖 RPA SICREDI - PROCESSAMENTO DE ARQUIVOS DE REMESSA")
    log("🚀 ARQUITETURA: Diagnóstico → Processamento por empresa → Relatório")
    log("✅ CONFORME PDD: Implementação completa da seção 10.3")
    log("=" * 80)

    try:
        # FASE 0: PREPARAÇÃO E DIAGNÓSTICO
        log("🔧 FASE 0: PREPARAÇÃO E DIAGNÓSTICO")
        log("-" * 40)

        credenciais = await carregar_credenciais_sicredi()
        diagnostico = await diagnosticar_arquivos_remessa()

        # Verificar se há trabalho a fazer
        if diagnostico["arquivos_validos"] == 0:
            log("✅ Nenhum arquivo de remessa válido encontrado - execução desnecessária")
            notificar_sucesso_simples(
                "✅ RPA SICREDI: Execução desnecessária",
                "Todos os arquivos já foram processados ou não há arquivos válidos"
            )
            sys.exit(0)

        log(
            f"📋 Total de arquivos válidos identificados: {diagnostico['arquivos_validos']}")

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

            # Atualizar status dos contratos no MongoDB
            await atualizar_status_contratos(
                empresa,
                contratos,
                resultado_empresa["sucesso"]
            )

        # RELATÓRIO FINAL E NOTIFICAÇÃO
        relatorio_final = await gerar_relatorio_final(diagnostico, resultados_empresas)

        # Determinar sucesso geral
        empresas_com_sucesso = len(
            [r for r in resultados_empresas.values() if r.get("sucesso")])
        sucesso_geral = empresas_com_sucesso > 0  # Pelo menos uma empresa teve sucesso

        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        if sucesso_geral:
            log(f"\n🎉 PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
            log(f"⏱️ Duração total: {duracao}")
            log(
                f"✅ Empresas bem-sucedidas: {empresas_com_sucesso}/{len(resultados_empresas)}")

            notificar_sucesso_simples(
                f"🎉 RPA SICREDI: Processamento concluído",
                f"Duração: {duracao} | Empresas: {empresas_com_sucesso}/{len(resultados_empresas)} | Arquivos: {relatorio_final['estatisticas_gerais']['arquivos_processados']}"
            )

            sys.exit(0)
        else:
            log(f"\n❌ PROCESSAMENTO FALHOU EM TODAS AS EMPRESAS")
            log(f"⏱️ Duração: {duracao}")

            notificar_erro_simples(
                f"❌ RPA SICREDI: Falha completa",
                f"Todas as empresas falharam - Verifique logs detalhados"
            )

            sys.exit(1)

    except KeyboardInterrupt:
        log("👋 Processamento interrompido pelo usuário")
        notificar_erro_simples(
            "⚠️ RPA SICREDI: Interrompido",
            "Processamento cancelado pelo usuário"
        )
        sys.exit(130)

    except Exception as e:
        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        log(f"💥 ERRO CRÍTICO NO PROCESSAMENTO: {str(e)}")
        log(f"⏱️ Duração até erro: {duracao}")

        notificar_erro_simples(
            f"💥 RPA SICREDI: Erro crítico",
            f"Erro: {str(e)} | Duração: {duracao}"
        )

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
