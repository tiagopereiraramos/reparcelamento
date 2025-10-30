#!/usr/bin/env python3
"""
Main de produção para execução do RPA Análise de Planilhas

Executa o RPA de análise das planilhas, identifica contratos para reparcelamento e salva a fila de processamento.
Utiliza variáveis de ambiente para configuração.

Pode ser chamado por agendadores, CI/CD ou manualmente.
A persistência híbrida (MongoDB + JSON) é garantida pelo core do RPA.
"""
from rpa_analise_planilhas.rpa_analise_planilhas import executar_analise_planilhas
from core.relatorio_rpa import RelatorioRPA
from core.notificacoes_simples import notificar_sucesso, notificar_erro
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from core.notificacoes_simples import notificar_erro

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
    # Relatório unificado
    relatorio = RelatorioRPA("Analise de Planilhas")
    relatorio.iniciar_execucao()

    resultado = await executar_analise_planilhas(
        planilha_calculo_id=planilha_calculo_id,
        planilha_apoio_id=planilha_apoio_id,
        credenciais_google=credenciais_google,
        headless=True,
        notificar=False
    )
    # Alimenta relatório unificado
    total_aprovados = total_rejeitados = total_nao_processados = 0
    if hasattr(resultado, 'dados') and resultado.dados:
        auditoria = resultado.dados.get('contratos_auditoria', [])
        aprovados = [c for c in auditoria if c.get('status') == 'aprovado']
        rejeitados = [c for c in auditoria if c.get('status') == 'rejeitado']
        nao_processados = [c for c in auditoria if c.get('status') == 'não processado']
        total_aprovados = len(aprovados)
        total_rejeitados = len(rejeitados)
        total_nao_processados = len(nao_processados)
        relatorio.set_metricas({
            "contratos_identificados": resultado.dados.get('contratos_para_reajuste', 0),
            "contratos_ja_processados": resultado.dados.get('contratos_ja_processados', 0)
        })
    if resultado.sucesso:
        relatorio.adicionar_sucesso(
            "Análise concluída",
            {"mensagem": resultado.mensagem,
             "aprovados": total_aprovados,
             "rejeitados": total_rejeitados,
             "nao_processados": total_nao_processados}
        )
    else:
        relatorio.adicionar_erro(
            "Falha na análise",
            resultado.mensagem,
            {"erro": resultado.erro or ""}
        )

    relatorio.finalizar_execucao()

    # Salva relatórios e notifica (anexa TXT)
    try:
        arq_json = relatorio.salvar_relatorio_json()
        arq_txt = relatorio.salvar_relatorio_txt()
        log(f"Relatórios gerados: {arq_json} | {arq_txt}")
    except Exception as e:
        log(f"Falha ao salvar relatórios: {e}")
        arq_txt = None

    # ✅ NOVO: incluir Resumo Executivo (Excel) gerado pelo RPA
    anexos = []
    if arq_txt:
        anexos.append(str(arq_txt))
    try:
        relatorios_dir = Path("outputs/relatorios")
        if relatorios_dir.exists():
            candidatos = sorted(
                relatorios_dir.glob("resumo_executivo*.xlsx"),
                key=lambda p: p.stat().st_mtime
            )
            if candidatos:
                resumo_executivo = candidatos[-1]
                anexos.append(str(resumo_executivo))
                log(f"Anexo incluído: {resumo_executivo}")
    except Exception as e:
        log(f"Falha ao localizar Resumo Executivo: {e}")

    resumo = relatorio.gerar_resumo()["resumo_execucao"]
    try:
        if resultado.sucesso:
            notificar_sucesso(
                nome_rpa="RPA Análise de Planilhas",
                tempo_execucao=resumo["tempo_total"],
                resultados={
                    "titulo": "🎉 RPA ANÁLISE DE PLANILHAS: Concluído",
                    "mensagem": resultado.mensagem,
                    "status": "concluido",
                    "caminhos_anexos": anexos
                }
            )
        else:
            notificar_erro(
                nome_rpa="RPA Análise de Planilhas",
                erro=resultado.mensagem,
                detalhes={
                    "titulo": "❌ RPA ANÁLISE DE PLANILHAS: Falhou",
                    "mensagem": resultado.erro or resultado.mensagem,
                    "status": "falhou",
                    "caminhos_anexos": anexos
                }
            )
    except Exception as e:
        log(f"Falha ao enviar notificação: {e}")

    sys.exit(0 if resultado.sucesso else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Execução interrompida pelo usuário.")
        sys.exit(130)
    except Exception as e:  # pylint: disable=broad-exception-caught
        log(f"Erro fatal: {e}")
        sys.exit(1)
