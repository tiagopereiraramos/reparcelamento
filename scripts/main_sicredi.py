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

from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo
from rpa_sicredi.rpa_sicredi import RPASicredi
from core.notificacoes_simples import notificar_sucesso, notificar_erro
from core.relatorio_sicredi import RelatorioSicredi
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Garante execução headless em produção
# os.environ["HEADLESS"] = "1"  # Força modo headless para Selenium/Browser - COMENTADO PARA GRAVAÇÃO DE VÍDEO

# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# MODO TESTE: Processar apenas empresa específica
MODO_TESTE_EMPRESA = os.getenv("TESTE_EMPRESA", "").strip()


def log(msg):
    """Loga mensagem com timestamp."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def notificar_inicio_processamento(diagnostico: Dict[str, Any], relatorio: RelatorioSicredi):
    """
    Notifica o início do processamento de forma simplificada
    """
    log("🚀 INICIANDO PROCESSAMENTO SICREDI")
    log(f"📊 {diagnostico['empresas_com_arquivos']} empresas para processar")
    log(f"📁 {diagnostico['arquivos_validos']} arquivos de remessa")
    log(f"📋 {diagnostico['total_contratos_carne_gerado']} contratos totais")

    # Notificação via email (mantém compatibilidade)
    try:
        notificar_sucesso(
            nome_rpa="RPA Sicredi - Processamento Arquivos",
            tempo_execucao="0s",
            resultados={
                "titulo": "🚀 RPA SICREDI: Processamento iniciado",
                "mensagem": f"Processando {diagnostico['empresas_com_arquivos']} empresas com {diagnostico['arquivos_validos']} arquivos",
                "status": "iniciando"
            }
        )
    except Exception as e:
        log(f"⚠️ Erro ao enviar notificação de início: {e}")


def notificar_resultado_final(relatorio: RelatorioSicredi):
    """
    Notifica o resultado final de forma simplificada
    """
    mensagem_cliente = relatorio.gerar_mensagem_cliente()
    log("\n" + "="*60)
    log("📊 RELATÓRIO FINAL - RPA SICREDI")
    log("="*60)
    log(mensagem_cliente)

    # Salvar relatórios para o cliente
    try:
        arquivo_json = relatorio.salvar_relatorio_cliente()
        arquivo_txt = relatorio.salvar_mensagem_cliente()
        log(f"📄 Relatório JSON salvo: {arquivo_json}")
        log(f"📄 Relatório TXT salvo: {arquivo_txt}")
    except Exception as e:
        log(f"⚠️ Erro ao salvar relatórios: {e}")

    # Notificação via email (mantém compatibilidade)
    try:
        resumo = relatorio.gerar_relatorio_resumido()["resumo_execucao"]

        if resumo["status_geral"] == "SUCESSO_COMPLETO":
            notificar_sucesso(
                nome_rpa="RPA Sicredi - Processamento Arquivos",
                tempo_execucao=resumo["tempo_total"],
                resultados={
                    "titulo": "🎉 RPA SICREDI: Processamento concluído",
                    "mensagem": f"✅ {resumo['empresas_sucesso']} empresas processadas | 📁 {resumo['arquivos_enviados']} arquivos | 📋 {resumo['contratos_vinculados']} contratos",
                    "status": "concluido",
                    "caminhos_anexos": [arquivo_txt]  # Anexar relatório TXT
                }
            )
        else:
            detalhes_txt = (
                f"⚠️ RPA SICREDI: Processamento com falhas\n"
                f"✅ Sucessos: {resumo['empresas_sucesso']}\n"
                f"❌ Erros: {resumo['empresas_erro']}\n"
                f"📁 Arquivos: {resumo['arquivos_enviados']}\n"
            )
            if 'arquivo_txt' in locals() and arquivo_txt:
                detalhes_txt += f"\n📎 Relatório em anexo: {arquivo_txt}"

            notificar_erro(
                nome_rpa="RPA Sicredi - Processamento Arquivos",
                erro="Processamento com falhas",
                detalhes=detalhes_txt
            )
    except Exception as e:
        log(f"⚠️ Erro ao enviar notificação final: {e}")


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

    MODO TESTE: Se TESTE_EMPRESA estiver definido, processa apenas essa empresa
    """
    if MODO_TESTE_EMPRESA:
        log(
            f"📊 DIAGNÓSTICO DE ARQUIVOS DE REMESSA (MODO TESTE - EMPRESA {MODO_TESTE_EMPRESA})")
    else:
    log("📊 DIAGNÓSTICO DE ARQUIVOS DE REMESSA")
    log("=" * 60)

    try:
        # Construir filtro de busca
        filtro_busca = {"status": "CARNE_GERADO"}

        if MODO_TESTE_EMPRESA:
            # MODO TESTE: Buscar apenas contratos da empresa específica
            filtro_busca["Empresa"] = MODO_TESTE_EMPRESA
            log(
                f"🔍 MODO TESTE: Buscando apenas contratos da empresa {MODO_TESTE_EMPRESA}")
        else:
            log("🔍 MODO PRODUÇÃO: Buscando todos os contratos com status CARNE_GERADO")

        contratos_carne_gerado = repositorio_contratos_arquivo.framework.find(
            filtro_busca)

        if MODO_TESTE_EMPRESA:
            log(f"🔍 Encontrados {len(contratos_carne_gerado)} contratos da empresa {MODO_TESTE_EMPRESA} com status CARNE_GERADO")
        else:
            log(f"🔍 Encontrados {len(contratos_carne_gerado)} contratos com status CARNE_GERADO")

        # Agrupar por empresa
        empresas_arquivos = {}
        for contrato in contratos_carne_gerado:
            empresa = contrato.get("Empresa", "Empresa Desconhecida")
            arquivo_remessa = contrato.get("arquivo_remessa", "")

            # Verificar se o arquivo existe
            if arquivo_remessa and os.path.exists(arquivo_remessa):
                # No modo teste, processar apenas a empresa especificada
                if MODO_TESTE_EMPRESA and empresa != MODO_TESTE_EMPRESA:
                    continue

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
        if MODO_TESTE_EMPRESA:
            log(
                f"📋 ESTATÍSTICAS DOS ARQUIVOS (MODO TESTE - EMPRESA {MODO_TESTE_EMPRESA}):")
            log(
                f"   📄 Total de contratos da empresa {MODO_TESTE_EMPRESA} com carnê gerado: {diagnostico['total_contratos_carne_gerado']}")
        else:
        log(f"📋 ESTATÍSTICAS DOS ARQUIVOS:")
        log(
            f"   📄 Total de contratos com carnê gerado: {diagnostico['total_contratos_carne_gerado']}")

        log(
            f"   🏢 Empresas com arquivos: {diagnostico['empresas_com_arquivos']}")
        log(f"   📁 Arquivos válidos: {diagnostico['arquivos_validos']}")

        if empresas_arquivos:
            modo_texto = "MODO TESTE" if MODO_TESTE_EMPRESA else "MODO PRODUÇÃO"
            log(f"🏢 EMPRESAS COM ARQUIVOS DE REMESSA ({modo_texto}):")
            for empresa, dados in empresas_arquivos.items():
                log(
                    f"   📋 {empresa}: {len(dados['arquivos'])} arquivos, {len(dados['contratos'])} contratos")
                if dados.get("cnpj"):
                    log(f"      🏦 CNPJ: {dados['cnpj']}")

                # Log específico do arquivo de remessa
                for arquivo in dados['arquivos']:
                    log(f"      📁 Arquivo: {arquivo}")
                    log(f"      ✅ Arquivo existe: {os.path.exists(arquivo)}")

        # Determinar estratégia de processamento
        if diagnostico["arquivos_validos"] == 0:
            if MODO_TESTE_EMPRESA:
                log(
                    f"⚠️ Nenhum arquivo de remessa válido encontrado para empresa {MODO_TESTE_EMPRESA}")
            else:
            log("⚠️ Nenhum arquivo de remessa válido encontrado")
            return diagnostico

        modo_texto = "MODO TESTE" if MODO_TESTE_EMPRESA else "MODO PRODUÇÃO"
        log(f"\n🎯 EMPRESAS QUE SERÃO PROCESSADAS ({modo_texto}):")
        for empresa, dados in empresas_arquivos.items():
            log(f"   🏢 {empresa}: {len(dados['arquivos'])} arquivos")
            for arquivo in dados['arquivos']:
                log(f"      📁 {arquivo}")

        return diagnostico

    except Exception as e:
        log(f"❌ Erro no diagnóstico: {str(e)}")
        raise


async def processar_empresa_sicredi(
    empresa: str,
    arquivos_remessa: List[str],
    contratos: List[Dict[str, Any]],
    credenciais: Dict[str, str],
    relatorio: RelatorioSicredi
) -> Dict[str, Any]:
    """
    Processa uma empresa específica no Sicredi

    Args:
        empresa: Nome da empresa
        arquivos_remessa: Lista de arquivos de remessa da empresa, mas processar apenas o primeiro arquivo de remessa, porque é o mesmo arquivo agrupado por empresa
        contratos: Lista de contratos da empresa
        credenciais: Credenciais do Sicredi
    """
    try:
        rpa = RPASicredi()
        await rpa.inicializar()
        resultados_arquivos = []
        sucessos = 0
        erros = 0

        # o primeiro arquivo de remessa é o que deve ser processado, porque é o mesmo arquivo agrupado por empresa
        arquivo_remessa = arquivos_remessa[0]

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

            # Adicionar ao relatório
            relatorio.adicionar_empresa_sucesso(
                empresa=empresa,
                arquivo=arquivo_remessa,
                contratos=len(contratos),
                detalhes={
                    "arquivos_processados": sucessos,
                    "arquivos_erro": erros,
                    "taxa_sucesso": f"{(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%"
                }
            )
        else:
            log(f"❌ EMPRESA {empresa} FALHOU: Todos os arquivos com erro")

            # Adicionar erro ao relatório
            erro_msg = f"Todos os {len(arquivos_remessa)} arquivos falharam"
            relatorio.adicionar_empresa_erro(
                empresa=empresa,
                arquivo=arquivo_remessa,
                erro=erro_msg,
                detalhes={
                    "arquivos_tentados": len(arquivos_remessa),
                    "arquivos_erro": erros
                }
            )

        return resultado_empresa

    except Exception as e:
        erro_msg = f"Erro crítico no processamento da empresa {empresa}: {str(e)}"
        log(f"💥 {erro_msg}")

        # Adicionar erro crítico ao relatório
        relatorio.adicionar_empresa_erro(
            empresa=empresa,
            arquivo=arquivos_remessa[0] if arquivos_remessa else "N/A",
            erro=erro_msg,
            detalhes={
                "tipo_erro": "erro_critico",
                "arquivos_tentados": len(arquivos_remessa)
            }
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
    Atualiza status dos contratos no JSON após processamento no Sicredi

    Args:
        empresa: Nome completo da empresa (ex: "15 - URUCUI SCP")
        contratos: Lista de contratos a serem atualizados
        sucesso: True se processamento foi bem-sucedido, False caso contrário
    """
    try:
        novo_status = "PROCESSADO_SICREDI" if sucesso else "ERRO_SICREDI"
        contratos_atualizados = 0

        log(f"🔄 Atualizando status de {len(contratos)} contratos da empresa {empresa} para {novo_status}")

        for contrato in contratos:
            titulo = contrato.get("Titulo")
            if not titulo:
                log(f"⚠️ Contrato sem título, pulando...")
                continue

            try:
                # Preparar dados de atualização
                dados_atualizacao = {
                            "status": novo_status,
                    "data_processamento_sicredi": datetime.now().isoformat(),
                    "empresa_processada": empresa,
                    "timestamp_ultima_atualizacao": datetime.now().isoformat()
                }

                # Buscar contrato pelo título e atualizar
                # O método update espera um query dict como primeiro parâmetro
                query = {"Titulo": titulo}

                resultado = repositorio_contratos_arquivo.framework.update(
                    query,
                    dados_atualizacao,
                    multi=False  # Atualiza apenas o primeiro registro encontrado
                )

                if resultado > 0:
                    contratos_atualizados += 1
                    log(f"✅ Contrato {titulo} atualizado para {novo_status}")
                else:
                    log(f"⚠️ Contrato {titulo} não encontrado ou não foi atualizado")

    except Exception as e:
                log(f"❌ Erro ao atualizar contrato {titulo}: {str(e)}")
                import traceback
                log(f"   Traceback: {traceback.format_exc()}")

        log(f"📊 Status dos contratos atualizados: {contratos_atualizados}/{len(contratos)} contratos atualizados para {novo_status}")

    except Exception as e:
        log(f"⚠️ Erro crítico ao atualizar status dos contratos: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """
    MAIN: Execução otimizada do RPA Sicredi em produção

    ESTRATÉGIA IMPLEMENTADA:
    - Diagnóstico de arquivos de remessa disponíveis
    - Processamento por empresa/CNPJ
    - Validações conforme PDD 10.3
    - Relatórios simplificados para o cliente
    - Tracking de tempo de execução
    """
    # Inicializar sistema de relatórios
    relatorio = RelatorioSicredi()
    relatorio.iniciar_execucao()

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
            relatorio.adicionar_erro_geral("Nenhum arquivo válido encontrado")
            relatorio.finalizar_execucao()
            notificar_resultado_final(relatorio)
            sys.exit(0)

        log(
            f"📋 Total de arquivos válidos identificados: {diagnostico['arquivos_validos']}")

        # Notificar início do processamento
        notificar_inicio_processamento(diagnostico, relatorio)

        # EXECUÇÃO POR EMPRESA
        log("\n🔄 FASE 1: PROCESSAMENTO POR EMPRESA")
        log("-" * 40)

        for empresa, dados in diagnostico["empresas_arquivos"].items():
            arquivos_remessa = dados["arquivos"]
            contratos = dados["contratos"]

            log(f"\n🏢 Processando empresa: {empresa}")
            log(f"   📁 Arquivo: {arquivos_remessa[0]}")
            log(f"   📋 Contratos: {len(contratos)}")

            # Extrair código da empresa se necessário
            if " - " in empresa:
                codigo_empresa = empresa.split(" - ")[0].strip()
            else:
                codigo_empresa = empresa

            # Processar empresa no Sicredi
            resultado_empresa = await processar_empresa_sicredi(
                codigo_empresa,
                arquivos_remessa,
                contratos,
                credenciais,
                relatorio
            )

            # Atualizar status dos contratos no JSON
            await atualizar_status_contratos(
                empresa,  # Nome completo da empresa (ex: "15 - URUCUI SCP")
                contratos,
                resultado_empresa["sucesso"]
            )

        # FINALIZAR RELATÓRIO E NOTIFICAR
        relatorio.finalizar_execucao()
        notificar_resultado_final(relatorio)

        # Determinar status de saída
        resumo = relatorio.gerar_relatorio_resumido()["resumo_execucao"]
        if resumo["status_geral"] == "FALHA_COMPLETA":
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        log("👋 Processamento interrompido pelo usuário")
        relatorio.adicionar_erro_geral(
            "Processamento interrompido pelo usuário")
        relatorio.finalizar_execucao()
        notificar_resultado_final(relatorio)
        sys.exit(130)

    except Exception as e:
        log(f"💥 ERRO CRÍTICO NO PROCESSAMENTO: {str(e)}")
        relatorio.adicionar_erro_geral(f"Erro crítico: {str(e)}")
        relatorio.finalizar_execucao()
        notificar_resultado_final(relatorio)
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
