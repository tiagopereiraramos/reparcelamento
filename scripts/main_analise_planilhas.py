#!/usr/bin/env python3
"""
Main de produção para execução do RPA Análise de Planilhas

Executa o RPA de análise das planilhas, identifica contratos para reparcelamento e salva a fila de processamento.
Utiliza variáveis de ambiente para configuração.

Pode ser chamado por agendadores, CI/CD ou manualmente.
A persistência híbrida (MongoDB + JSON) é garantida pelo core do RPA.
"""
from rpa_analise_planilhas import executar_analise_planilhas
import os
import sys
import asyncio
from datetime import datetime
from pathlib import Path
from core.notificacoes_simples import notificar_sucesso, notificar_erro

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
    resultado = await executar_analise_planilhas(
        planilha_calculo_id=planilha_calculo_id,
        planilha_apoio_id=planilha_apoio_id,
        credenciais_google=credenciais_google,
        headless=True
    )

    # Relatório detalhado de aprovação, rejeição e não processados
    corpo_relatorio = ""
    total_processados = 0
    total_aprovados = 0
    total_rejeitados_iptu = 0
    total_nao_processados = 0
    aprovados = []
    rejeitados_iptu = []
    nao_processados = []
    if hasattr(resultado, 'dados') and resultado.dados:
        auditoria = resultado.dados.get('contratos_auditoria', [])
        violacoes_base = resultado.dados.get('violacoes_base_calculo', [])
        for c in auditoria:
            status = c.get('status')
            if status == 'aprovado':
                aprovados.append(c)
            elif status == 'rejeitado':
                rejeitados_iptu.append(c)
            else:
                nao_processados.append(c)
        total_aprovados = len(aprovados)
        total_rejeitados_iptu = len(rejeitados_iptu)
        total_nao_processados = len(nao_processados)
        total_processados = total_aprovados + \
            total_rejeitados_iptu + total_nao_processados

    corpo_relatorio += "\nRELATÓRIO DE CONTRATOS APROVADOS:\n"
    if aprovados:
        for c in aprovados:
            corpo_relatorio += f" - Cliente: {c.get('cliente','N/A')}, Título: {c.get('titulo','N/A')}, Motivo: {c.get('motivo','')}\n"
    else:
        corpo_relatorio += "Nenhum contrato aprovado para reparcelamento.\n"

    corpo_relatorio += "\nRELATÓRIO DE CONTRATOS REJEITADOS:\n"
    if rejeitados_iptu:
        for c in rejeitados_iptu:
            corpo_relatorio += f" - Cliente: {c.get('cliente','N/A')}, Título: {c.get('titulo','N/A')}, Motivo: {c.get('motivo','')}\n"
    else:
        corpo_relatorio += "Nenhum contrato rejeitado.\n"

    corpo_relatorio += "\nRELATÓRIO DE CONTRATOS NÃO PROCESSADOS:\n"
    if nao_processados:
        for c in nao_processados:
            corpo_relatorio += f" - Cliente: {c.get('cliente','N/A')}, Título: {c.get('titulo','N/A')}, Motivo: {c.get('motivo','')}\n"
    else:
        corpo_relatorio += "Nenhum contrato fora do mês de reajuste ou com dados inválidos.\n"

    # Estatísticas gerais
    corpo_relatorio += f"\nESTATÍSTICAS GERAIS:\n"
    corpo_relatorio += f" - Total de contratos lidos: {total_processados}\n"
    corpo_relatorio += f" - Total aprovados: {total_aprovados}\n"
    corpo_relatorio += f" - Total rejeitados: {total_rejeitados_iptu}\n"
    corpo_relatorio += f" - Total não processados: {total_nao_processados}\n"
    corpo_relatorio += f" - Data/hora da análise: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"

    # Alerta de violação de integridade
    if 'violacoes_base' in locals() and violacoes_base:
        corpo_relatorio += "\n⚠️ <b>VIOLAÇÃO DE INTEGRIDADE:</b> Foram encontrados contratos na base de cálculo que não vieram da planilha de apoio (violação do PDD):\n"
        for v in violacoes_base:
            corpo_relatorio += f" - Cliente: {v.get('cliente','N/A')}, Título: {v.get('titulo','N/A')}, Motivo: {v.get('motivo','')}\n"
    elif 'violacoes_base' in locals():
        corpo_relatorio += "\n✅ Integridade OK: Todos os contratos da base de cálculo vieram da planilha de apoio.\n"

    tempo_execucao = f"{getattr(resultado, 'tempo_execucao', 0):.2f}s"

    if resultado.sucesso:
        log(f"SUCESSO: {resultado.mensagem}")
        # ✅ REMOVIDO: Notificação duplicada - já enviada dentro da classe RPAAnalisePlanilhas.executar()
        # notificar_sucesso(
        #     nome_rpa="RPA Análise de Planilhas",
        #     tempo_execucao=tempo_execucao,
        #     resultados={
        #         "mensagem": resultado.mensagem,
        #         "relatorio": corpo_relatorio
        #     }
        # )
        sys.exit(0)
    else:
        log(f"FALHA: {resultado.mensagem}")
        if resultado.erro:
            log(f"Detalhe do erro: {resultado.erro}")
        notificar_erro(
            nome_rpa="RPA Análise de Planilhas",
            erro=resultado.mensagem,
            detalhes=corpo_relatorio or resultado.erro or "Erro desconhecido"
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
