#!/usr/bin/env python3
"""
Main de reparcelamento para processamento da Fase 2 do RPA Sienge
Sistema de reparcelamento independente

FASE 2: REPARCELAMENTO 
APROVACAO_REALIZADA → REPARCELADO

Conforme PDD Seção 10.1: Planilha base de cálculo + Webscraping reparcelamento

Desenvolvido em Português Brasileiro
"""

from core.utils_sienge import (
    log,
    notificar_sucesso_simples,
    notificar_erro_simples,
    carregar_credenciais_sienge,
    carregar_indices_economicos,
    get_env_or_fail,
    obter_mes_ano_atual_pt
)
from rpa_sienge.rpa_sienge import RPASienge
from core.gerador_anexos import gerador_anexos
from core.templates_relatorios import templates_relatorios
import os
import sys
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Garante execução headless em produção
os.environ["HEADLESS"] = "0"

# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def executar_fase_reparcelamento(credenciais: Dict[str, str], indices: Dict[str, Any], total_extraidos: int) -> Dict[str, Any]:
    """
    FASE 2: REPARCELAMENTO 
    APROVACAO_REALIZADA → REPARCELADO

    Conforme PDD Seção 10.1: Planilha base de cálculo + Webscraping reparcelamento
    """
    log("\n📤 EXECUTANDO FASE 2: REPARCELAMENTO")
    log("=" * 60)
    log(f"🎯 Meta: Processar {total_extraidos} contratos aprovados")
    log("📋 Processo: Planilha base cálculo + Webscraping reparcelamento PDD 10.1")
    log(f"📈 Índices: IPCA={indices['ipca']['valor']}% | IGPM={indices['igpm']['valor']}%")

    try:
        # ✅ CORREÇÃO: Usar notificação consolidada com título personalizado
        from core.notificacoes_simples import notificar_sucesso

        # Notificação inicial com título personalizado
        resultados_inicial = {
            "titulo": f"🚀 RPA SIENGE: Reparcelamento iniciando",
            "mensagem": f"Processando {total_extraidos if total_extraidos > 0 else 'todos os'} contratos aprovados | Índices: IPCA={indices['ipca']['valor']}% | IGPM={indices['igpm']['valor']}%",
            "caminhos_anexos": []
        }

        notificar_sucesso(
            nome_rpa="RPA Sienge",
            tempo_execucao="00:00:00",
            resultados=resultados_inicial
        )

        # Inicializar RPA com nova sessão
        headless = os.getenv("HEADLESS", "1") == "1"
        usar_uc_chrome = False
        caminho_perfil_chrome = os.getenv("CHROME_PROFILE_PATH", "")

        rpa = RPASienge(
            headless=headless,
            usar_uc_chrome=usar_uc_chrome,
            caminho_perfil_chrome=caminho_perfil_chrome
        )
        await rpa.inicializar()

        log(f"🤖 RPA reinicializado para reparcelamento (headless: {headless})")

        # Executar reparcelamento em lote
        resultado = await rpa.processar_fila_contratos_lote(
            credenciais_sienge=credenciais,
            indices=indices,
            fase="reparcelamento",
            pausar_entre_contratos=False  # Processamento contínuo em produção
        )

        await rpa.finalizar()

        # Processar resultado
        if resultado.get("sucesso"):
            fase_reparcelamento = resultado.get("fase_reparcelamento", {})
            sucessos = fase_reparcelamento.get("contratos_processados", 0)
            erros = fase_reparcelamento.get("contratos_erro", 0)

            log(f"✅ FASE 2 CONCLUÍDA:")
            log(f"   ✅ Sucessos: {sucessos}")
            log(f"   ❌ Erros: {erros}")
            log(f"   📊 Taxa de sucesso: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%")

            # ✅ NOVO: Coletar dados detalhados para anexos
            contratos_sucesso = []
            contratos_erro = []

            if hasattr(rpa, 'contratos_processados_reparcelamento'):
                contratos_sucesso = rpa.contratos_processados_reparcelamento
            elif fase_reparcelamento.get("detalhes_sucesso"):
                contratos_sucesso = fase_reparcelamento.get(
                    "detalhes_sucesso", [])

            if hasattr(rpa, 'contratos_erro_reparcelamento'):
                contratos_erro = rpa.contratos_erro_reparcelamento
            elif fase_reparcelamento.get("detalhes_erro"):
                contratos_erro = fase_reparcelamento.get("detalhes_erro", [])

            # Gera anexos se houver dados
            anexos = {}
            if contratos_sucesso or contratos_erro:
                try:
                    anexos = gerador_anexos.gerar_anexo_reparcelamento(
                        contratos_sucesso=contratos_sucesso,
                        contratos_erro=contratos_erro
                    )
                    log(f"📎 Anexos gerados: {anexos}")
                except Exception as e:
                    log(f"⚠️ Erro ao gerar anexos: {e}")

            # Gera relatório HTML
            estatisticas = {
                'total_contratos': total_extraidos if total_extraidos > 0 else sucessos + erros,
                'contratos_sucesso': sucessos,
                'contratos_erro': erros,
                'tempo_medio': fase_reparcelamento.get('tempo_medio', 'N/A')
            }

            html_relatorio = templates_relatorios.relatorio_reparcelamento(
                estatisticas, anexos)

            # Salva relatório HTML
            diretorio_relatorios = Path("outputs/relatorios")
            diretorio_relatorios.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_html = diretorio_relatorios / \
                f"relatorio_reparcelamento_{timestamp}.html"

            with open(arquivo_html, 'w', encoding='utf-8') as f:
                f.write(html_relatorio)

            log(f"📄 Relatório HTML salvo: {arquivo_html}")

            # Notificar com relatório HTML e arquivos anexados
            from core.notificacoes_simples import notificar_sucesso

            # ✅ CORREÇÃO: Preparar resultados apenas com Excel
            resultados_email = {
                "titulo": f"✅ FASE 2 CONCLUÍDA: Reparcelamento",
                "mensagem": f"Sucessos: {sucessos} | Erros: {erros} | Taxa: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%",
                # ✅ CORREÇÃO: Apenas anexar arquivo Excel
                "caminhos_anexos": [anexos.get('excel')] if anexos.get('excel') else []
            }

            # Notificar com relatório HTML e arquivos anexados
            notificar_sucesso(
                nome_rpa="RPA Sienge",
                tempo_execucao="-",
                resultados=resultados_email
            )

            return {
                "sucesso": True,
                "contratos_processados": sucessos,
                "contratos_erro": erros,
                "detalhes": fase_reparcelamento,
                "relatorio_html": str(arquivo_html),
                "anexos": anexos
            }
        else:
            erro_msg = resultado.get(
                "erro", "Erro desconhecido no reparcelamento")
            log(f"❌ FASE 2 FALHOU: {erro_msg}")

            # ✅ CORREÇÃO: Notificação consolidada será enviada no final
            # notificar_erro_simples(
            #     f"❌ FASE 2 FALHOU: Reparcelamento",
            #     f"Erro: {erro_msg}"
            # )

            return {"sucesso": False, "erro": erro_msg}

    except Exception as e:
        erro_msg = f"Erro crítico na fase de reparcelamento: {str(e)}"
        log(f"💥 {erro_msg}")

        # ✅ CORREÇÃO: Notificação consolidada será enviada no final
        # notificar_erro_simples(
        #     f"💥 FASE 2 ERRO CRÍTICO",
        #     erro_msg
        # )

        return {"sucesso": False, "erro": erro_msg}


async def verificar_autorizacao_planilha() -> bool:
    """
    Verifica se o reparcelamento está autorizado na planilha
    """
    log("🔍 Verificando autorização na planilha antes do reparcelamento...")

    try:
        planilha_id = get_env_or_fail("PLANILHA_CALCULO_ID")
        credenciais_google = os.getenv("GOOGLE_CREDENTIALS_PATH", "")

        # Inicializar RPA temporariamente para verificar autorização
        headless = os.getenv("HEADLESS", "1") == "1"
        rpa_temp = RPASienge(headless=headless)
        await rpa_temp.inicializar()

        # Verificar autorização na planilha
        resultado_autorizacao = await rpa_temp.verificar_autorizacao_reparcelamento_planilha(
            planilha_id=planilha_id,
            credenciais_google=credenciais_google
        )

        await rpa_temp.finalizar()

        autorizacao_aprovada = resultado_autorizacao.get("autorizado", False)

        if not autorizacao_aprovada:
            periodo = obter_mes_ano_atual_pt()
            log(f"❌ Reparcelamento NÃO AUTORIZADO na planilha para {periodo}")
            # ✅ CORREÇÃO: Notificação individual removida - será consolidada no final
            # from core.notificacoes_simples import notificar_erro

            # notificar_erro(
            #     nome_rpa="RPA Sienge",
            #     erro=f"❌ RPA SIENGE: Reparcelamento não autorizado - {periodo}",
            #     detalhes=f"Não há autorização na planilha 'LANÇAMENTO DE REPARCELAMENTOS AUTORIZADO' para {periodo}. "
            #              f"É necessário colocar 'SIM' na coluna de autorização para permitir o reparcelamento."
            # )
        else:
            log("✅ Reparcelamento AUTORIZADO na planilha para o mês corrente")

        return autorizacao_aprovada

    except Exception as e:
        log(
            f"⚠️ Erro ao verificar autorização: {str(e)} - Continuando reparcelamento")
        # Em caso de erro na verificação, continua o reparcelamento
        return True


async def main():
    """
    MAIN DE REPARCELAMENTO: Execução isolada da fase de reparcelamento
    """
    # Configurar argumentos de linha de comando
    parser = argparse.ArgumentParser(description='RPA Sienge - Reparcelamento')
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

    inicio_execucao = datetime.now()

    log("📤 RPA SIENGE - REPARCELAMENTO ISOLADO")
    log("🎯 Fase 2: Processamento de contratos APROVACAO_REALIZADA → REPARCELADO")
    log("=" * 60)

    try:
        # Carregar credenciais e índices
        credenciais = await carregar_credenciais_sienge()
        indices = await carregar_indices_economicos()

        # Verificar autorização na planilha
        autorizado = await verificar_autorizacao_planilha()

        if not autorizado:
            log("🛑 Interrompendo processamento - reparcelamento não autorizado")
            return 0  # Sucesso (não é erro, apenas não autorizado)

        # Para execução isolada, vamos processar todos os contratos aprovados
        # Em produção, isso seria determinado pelo diagnóstico
        log("🔍 Executando reparcelamento para todos os contratos aprovados...")

        # Executar reparcelamento
        # -1 indica todos os aprovados
        resultado = await executar_fase_reparcelamento(credenciais, indices, -1)

        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        if resultado.get("sucesso"):
            sucessos = resultado.get("contratos_processados", 0)
            erros = resultado.get("contratos_erro", 0)
            relatorio_html = resultado.get("relatorio_html", "N/A")
            anexos = resultado.get("anexos", {})

            log(f"\n🎉 REPARCELAMENTO CONCLUÍDO COM SUCESSO!")
            log(f"⏱️ Duração: {duracao}")
            log(f"✅ Contratos processados: {sucessos}")
            log(f"❌ Contratos com erro: {erros}")
            log(f"📊 Taxa de sucesso: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%")
            log(f"📄 Relatório HTML: {relatorio_html}")
            log(f"📎 Anexos gerados: {len(anexos)}")

            # Envia notificação com relatório HTML e informações dos anexos
            resultados_notificacao = {
                "mensagem": f"Reparcelamento concluído com sucesso - {sucessos} contratos processados",
                "relatorio_html": relatorio_html,
                "anexos_gerados": len(anexos),
                "estatisticas": {
                    "contratos_sucesso": sucessos,
                    "contratos_erro": erros,
                    "taxa_sucesso": f"{(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%",
                    "duracao": str(duracao)
                }
            }

            if anexos:
                resultados_notificacao["caminhos_anexos"] = anexos

                # Notificar com relatório HTML e arquivos anexados
            from core.notificacoes_simples import notificar_sucesso

            # ✅ CORREÇÃO: Preparar resultados apenas com Excel
            resultados_email = {
                "titulo": f"🎉 RPA SIENGE: Reparcelamento concluído",
                "mensagem": f"Duração: {duracao} | Sucessos: {sucessos} | Erros: {erros} | Taxa: {(sucessos/(sucessos+erros)*100) if (sucessos+erros) > 0 else 0:.1f}%",
                # ✅ CORREÇÃO: Apenas anexar arquivo Excel
                "caminhos_anexos": [anexos.get('excel')] if anexos.get('excel') else []
            }

            # Notificar com relatório HTML e arquivos anexados
            notificar_sucesso(
                nome_rpa="RPA Sienge",
                tempo_execucao=str(duracao),
                resultados=resultados_email
            )

            return 0  # Sucesso
        else:
            erro_msg = resultado.get("erro", "Erro desconhecido")
            log(f"\n❌ REPARCELAMENTO FALHOU")
            log(f"⏱️ Duração: {duracao}")
            log(f"❌ Erro: {erro_msg}")

            # Gera relatório de erro
            html_erro = templates_relatorios.relatorio_erro(
                "RPA Sienge - Reparcelamento",
                erro_msg,
                f"Duração até erro: {duracao}"
            )

            # Salva relatório de erro
            diretorio_relatorios = Path("outputs/relatorios")
            diretorio_relatorios.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_html_erro = diretorio_relatorios / \
                f"erro_reparcelamento_{timestamp}.html"

            with open(arquivo_html_erro, 'w', encoding='utf-8') as f:
                f.write(html_erro)

            log(f"📄 Relatório de erro HTML salvo: {arquivo_html_erro}")

            # ✅ CORREÇÃO: Notificar com relatório HTML anexado usando notificação consolidada
            from core.notificacoes_simples import notificar_sucesso

            resultados_erro = {
                "titulo": f"❌ RPA SIENGE: Reparcelamento falhou",
                "mensagem": f"Erro: {erro_msg} | Duração: {duracao}",
                # ✅ CORREÇÃO: Sem anexos para erros
                "caminhos_anexos": []
            }

            notificar_sucesso(
                nome_rpa="RPA Sienge",
                tempo_execucao=str(duracao),
                resultados=resultados_erro
            )

            return 1  # Falha

    except Exception as e:
        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        log(f"💥 ERRO CRÍTICO NO REPARCELAMENTO: {str(e)}")
        log(f"⏱️ Duração até erro: {duracao}")

        # Gera relatório de erro
        html_erro = templates_relatorios.relatorio_erro(
            "RPA Sienge - Reparcelamento",
            f"Erro crítico: {str(e)}",
            f"Duração até erro: {duracao}"
        )

        # Salva relatório de erro
        diretorio_relatorios = Path("outputs/relatorios")
        diretorio_relatorios.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_html_erro = diretorio_relatorios / \
            f"erro_critico_reparcelamento_{timestamp}.html"

        with open(arquivo_html_erro, 'w', encoding='utf-8') as f:
            f.write(html_erro)

        log(f"📄 Relatório de erro crítico HTML salvo: {arquivo_html_erro}")

        # ✅ CORREÇÃO: Notificar com relatório HTML anexado usando notificação consolidada
        from core.notificacoes_simples import notificar_sucesso

        resultados_erro_critico = {
            "titulo": f"💥 RPA SIENGE: Erro crítico no reparcelamento",
            "mensagem": f"Erro: {str(e)} | Duração: {duracao}",
            # ✅ CORREÇÃO: Sem anexos para erros
            "caminhos_anexos": []
        }

        notificar_sucesso(
            nome_rpa="RPA Sienge",
            tempo_execucao=str(duracao),
            resultados=resultados_erro_critico
        )

        return 1  # Erro crítico


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log("Execução interrompida pelo usuário.")
        sys.exit(130)
    except Exception as e:  # pylint: disable=broad-exception-caught
        log(f"Erro fatal: {e}")
        sys.exit(1)
