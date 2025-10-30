#!/usr/bin/env python3
"""
Main de extração e processamento completo Sienge
===============================================

Orquestra a sequência:
1. Extração via webscraping dos relatórios Sienge (RPA).
2. Processamento local das regras de negócio e geração dos JSON/CSV.
3. Retroalimentação da planilha base de cálculo no Google Sheets.

Cada etapa pode ser executada isoladamente conforme flags da CLI.
"""

from __future__ import annotations
from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo
from core.notificacoes_simples import notificar_inicio, notificar_sucesso, notificar_erro
from core.relatorio_rpa import RelatorioRPA
from rpa_sienge.atualizar_planilha_extracao_resultados import (
    construir_configuracao,
    executar_atualizacao,
)
from rpa_sienge.processar_regras_extracao_inadimplencia import (
    ConfiguracaoProcessamento,
    executar_processamento,
)
from rpa_sienge.rpa_sienge_extracao import RPAExtracaoRelatorioSienge

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from datetime import datetime

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def carregar_json(path: Path) -> Dict[str, Any]:
    """Lê um arquivo JSON e devolve seu conteúdo como dicionário."""

    with path.open("r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def montar_argumentos() -> argparse.Namespace:
    """Constrói o parser de argumentos principal do pipeline."""

    hoje = datetime.now()
    mes_seguinte = hoje.month + 1
    ano_seguinte = hoje.year
    if mes_seguinte > 12:
        mes_seguinte = 1
        ano_seguinte += 1
    mes_base_default = f"{mes_seguinte:02d}/{ano_seguinte}"

    parser = argparse.ArgumentParser(
        description="Executa extração, processamento e retroalimentação do fluxo Sienge",
    )
    parser.add_argument(
        "--headless",
        choices=["0", "1"],
        default="0",
        help="Define se o navegador deve rodar em modo headless (1 para sim).",
    )
    parser.add_argument(
        "--saida-log",
        type=Path,
        default=None,
        help="Arquivo opcional para salvar o resultado da etapa selecionada em JSON.",
    )

    parser.add_argument(
        "--resultados-csv",
        type=Path,
        default=Path("resultados_processamento.csv"),
        help="Arquivo CSV gerado pela etapa de regras.",
    )

    parser.add_argument(
        "--planilha-id",
        type=str,
        help="ID da planilha de cálculo no Google Sheets.",
    )
    parser.add_argument(
        "--credenciais-google",
        type=Path,
        default=None,
        help="Caminho para credenciais Google. Se omitido, usa variável de ambiente.",
    )
    parser.add_argument(
        "--aba-planilha",
        type=str,
        default=None,
        help="Nome da aba da planilha que será atualizada.",
    )

    parser.add_argument(
        "--dias",
        type=int,
        default=30,
        help="Número de dias recentes para considerar na etapa de regras.",
    )
    parser.add_argument(
        "--max-arquivos",
        type=int,
        default=None,
        help="Número máximo de arquivos a processar na etapa de regras.",
    )
    parser.add_argument(
        "--mes-base",
        type=str,
        default=mes_base_default,
        help=f"Mês/ano base do reparcelamento para processamento de regras (padrão: {mes_base_default}).",
    )
    # Parâmetros de regras passam a ser derivados da planilha; evita sobrescrever lógica
    parser.add_argument(
        "--ignorar-nan",
        action="store_true",
        help="Ignora linhas cujo título esteja vazio/NaN.",
    )
    parser.add_argument(
        "--consultar-iptu",
        action="store_true",
        dest="consultar_iptu",
        default=True,
        help="Efetua consulta do IPTU durante o processamento de regras (padrão: ativado).",
    )
    parser.add_argument(
        "--nao-consultar-iptu",
        action="store_false",
        dest="consultar_iptu",
        help="Desativa a consulta do IPTU durante o processamento de regras.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Ativa logs detalhados nas etapas aplicáveis.",
    )

    parser.add_argument(
        "--executar-extracao",
        action="store_true",
        help="Executa somente a etapa de extração de relatórios via RPA usando a fila de pendentes (credenciais via .env).",
    )
    parser.add_argument(
        "--executar-regras",
        action="store_true",
        help="Executa somente a etapa de processamento das regras.",
    )
    parser.add_argument(
        "--executar-retro",
        action="store_true",
        help="Executa somente a etapa de retroalimentação da planilha.",
    )

    parser.add_argument(
        "--pipeline-completo",
        action="store_true",
        help="Executa as três etapas em sequência (extracao → regras → retro).",
    )

    parser.add_argument(
        "--limite-extracao",
        type=int,
        default=0,
        help="Limite opcional de contratos PENDENTE para executar na extração web.",
    )

    return parser.parse_args()


def verificar_relatorios_extraidos(contratos: List[Dict[str, Any]]) -> List[Path]:
    """Valida se todos os arquivos gerados na extração existem fisicamente."""

    if not contratos:
        print("ℹ️ Nenhum contrato extraído nesta execução.")
        return []

    print(f"📂 Validando {len(contratos)} relatórios exportados...")

    caminhos_validos: List[Path] = []
    arquivos_inexistentes: List[str] = []

    for contrato in contratos:
        caminho_raw = contrato.get("arquivo_relatorio")
        if not caminho_raw:
            arquivos_inexistentes.append("<indefinido>")
            continue

        caminho = Path(caminho_raw)
        if not caminho.is_absolute():
            caminho = Path.cwd() / caminho

        if not caminho.exists():
            arquivos_inexistentes.append(str(caminho))
            continue

        caminhos_validos.append(caminho)

    if arquivos_inexistentes:
        raise FileNotFoundError(
            "Relatórios esperados não foram encontrados: " +
            ", ".join(arquivos_inexistentes)
        )

    print("✅ Relatórios validados com sucesso.")
    return caminhos_validos


async def etapa_extracao(args: argparse.Namespace) -> Tuple[Any, Dict[str, Any], List[Path]]:
    """Executa somente a etapa de webscraping e retorna resultado, dict serializado e caminhos validados."""

    headless = args.headless == "1"

    rpa = RPAExtracaoRelatorioSienge(headless=headless)
    resultado_obj = await rpa.executar({
        "limite": args.limite_extracao,
    })
    resultado_dict = resultado_obj.para_dict()

    contratos = resultado_dict.get("dados", {}).get("contratos", [])
    relatorios = []
    if resultado_obj.sucesso:
        relatorios = verificar_relatorios_extraidos(contratos)

    return resultado_obj, resultado_dict, relatorios


async def etapa_regras(args: argparse.Namespace) -> int:
    """Roda a etapa de regras utilizando as opções da CLI."""

    config = ConfiguracaoProcessamento(
        dias=args.dias,
        max_arquivos=args.max_arquivos,
        mes_base=args.mes_base,
        tipo_reajuste=None,
        dia_aniversario=None,
        salvar_csv=str(args.resultados_csv),
        ignorar_nan=args.ignorar_nan,
        consultar_iptu=args.consultar_iptu,
        debug=args.debug,
    )
    return await executar_processamento(config)


def etapa_retroalimentacao(args: argparse.Namespace) -> None:
    """Aciona o script de retroalimentação com os argumentos informados."""

    argumentos_retro = argparse.Namespace(
        planilha_id=args.planilha_id,
        credenciais=args.credenciais_google,
        aba=args.aba_planilha,
        csv=args.resultados_csv,
        mes_base=args.mes_base,
        limite=None,
    )
    configuracao = construir_configuracao(argumentos_retro)
    executar_atualizacao(configuracao)


async def main_async() -> None:
    """Executa o pipeline completo, respeitando flags individuais."""

    args = montar_argumentos()

    etapas_descricao = [
        "1️⃣ Etapa de Webscrapping",
        "2️⃣ Etapa de Processar Regras Extração Sienge e Alimentação de Pendências",
        "3️⃣ Retroalimentação da Planilha Base de Cálculo",
    ]

    descricao_inicio = (
        "🚀 RPA Processar Regras Extração Sienge e Alimentação de Pendências\n"
        + "\n".join(etapas_descricao)
    )
    try:
        notificar_inicio(descricao_inicio)
    except Exception as exc:
        print(f"⚠️ Falha ao enviar notificação de início: {exc}")

    executar_todas = args.pipeline_completo or not any([
        args.executar_extracao,
        args.executar_regras,
        args.executar_retro,
    ])

    resultados: Dict[str, Any] = {}
    resultado_extracao_obj = None
    relatorios_extraidos: List[Path] = []

    if args.executar_extracao or executar_todas:
        resultado_extracao_obj, resultado_extracao, relatorios_extraidos = await etapa_extracao(args)
        resultados["extracao"] = resultado_extracao
        print("✅ Extração concluída:")
        print(json.dumps(resultado_extracao, indent=2, ensure_ascii=False))
        if args.saida_log:
            escrever_saida(args.saida_log, resultado_extracao)

        if not resultado_extracao_obj.sucesso:
            raise RuntimeError(
                "Etapa de extração falhou. Consulte os logs antes de prosseguir.")

    executar_regras_flag = args.executar_regras or executar_todas
    if executar_regras_flag and resultado_extracao_obj is not None and not relatorios_extraidos:
        print("ℹ️ Nenhum relatório válido encontrado após a extração; etapa de regras será pulada.")
        executar_regras_flag = False

    regras_concluidas = False

    if executar_regras_flag:
        status_regras = await etapa_regras(args)
        resultados["regras_status"] = status_regras
        if status_regras != 0:
            raise RuntimeError(
                "Etapa de regras falhou; interrompendo pipeline.")
        if args.saida_log:
            escrever_saida(args.saida_log, {
                "regras_status": status_regras,
                "csv": str(args.resultados_csv),
            })
        regras_concluidas = True

    executar_retro_flag = args.executar_retro or executar_todas
    if executar_retro_flag and executar_todas and not regras_concluidas:
        print(
            "ℹ️ Retroalimentação pulada: etapa de regras não foi executada nesta execução.")
        executar_retro_flag = False

    if executar_retro_flag:
        csv_path = Path(args.resultados_csv)
        if not csv_path.exists():
            raise FileNotFoundError(
                f"Arquivo CSV '{csv_path}' não localizado para retroalimentação."
            )
        etapa_retroalimentacao(args)
        resultados["retroalimentacao"] = "ok"
        if args.saida_log:
            escrever_saida(args.saida_log, {
                "retroalimentacao": "ok",
            })

    if not args.saida_log:
        print("✅ Fluxo concluído com sucesso.")


def escrever_saida(caminho: Path, dados: Dict[str, Any]) -> None:
    """Salva ou atualiza um arquivo JSON com o resultado parcial da etapa."""

    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists():
        conteudo_atual = json.loads(caminho.read_text(encoding="utf-8"))
    else:
        conteudo_atual = {}
    conteudo_atual.update(dados)
    caminho.write_text(json.dumps(conteudo_atual, indent=2,
                       ensure_ascii=False), encoding="utf-8")


def main() -> None:
    """Função principal síncrona da CLI."""
    # Executa pipeline e, ao final, envia notificação com anexos TXT/CSV
    relatorio = RelatorioRPA("Extracao Relatorio Sienge")
    relatorio.iniciar_execucao()

    args = montar_argumentos()
    resultados_csv = Path(args.resultados_csv)
    resultados_txt = Path("resultados_processamento.txt")

    sucesso = True
    erro_msg = ""
    try:
        asyncio.run(main_async())
    except Exception as e:  # pylint: disable=broad-exception-caught
        sucesso = False
        erro_msg = str(e)
    finally:
        relatorio.finalizar_execucao()

    # Alimenta relatório e envia notificação
    anexos: List[str] = []
    metricas: Dict[str, Any] = {}

    try:
        if resultados_txt.exists():
            anexos.append(str(resultados_txt))
            # Tenta extrair métricas básicas do TXT (JSON embutido)
            try:
                conteudo = resultados_txt.read_text(encoding="utf-8")
                import json as _json
                # procura primeira chave '{' e ultima '}' para extrair bloco JSON
                ini = conteudo.find("{")
                fim = conteudo.rfind("}")
                if ini != -1 and fim != -1 and fim > ini:
                    blob = conteudo[ini:fim+1]
                    dados_txt = _json.loads(blob)
                    est = dados_txt.get("estatisticas", {})
                    metricas.update({
                        "arquivos_processados": est.get("arquivos_processados"),
                        "contratos_processados": est.get("contratos_processados"),
                        "contratos_sucesso": est.get("contratos_sucesso"),
                        "erros": est.get("erros"),
                    })
            except Exception:
                pass

        if resultados_csv.exists():
            anexos.append(str(resultados_csv))
    except Exception:
        pass

    relatorio.set_metricas(metricas)

    if sucesso:
        relatorio.adicionar_sucesso(
            "Pipeline concluído",
            {"mensagem": "Extração/Regras/Retro executados com sucesso",
             **metricas}
        )
    else:
        relatorio.adicionar_erro(
            "Falha no pipeline",
            erro_msg or "Erro desconhecido"
        )

    try:
        arq_json = relatorio.salvar_relatorio_json()
        arq_txt_rel = relatorio.salvar_relatorio_txt()
        anexos.append(str(arq_txt_rel))
        # Não anexamos o JSON genérico por padrão; mantemos local para suporte
    except Exception:
        pass

    resumo = relatorio.gerar_resumo()["resumo_execucao"]

    try:
        if sucesso:
            notificar_sucesso(
                nome_rpa="RPA Extração/Processamento Sienge",
                tempo_execucao=resumo.get("tempo_total", "0s"),
                resultados={
                    "titulo": "🎉 RPA SIENGE: Processamento concluído",
                    "mensagem": (
                        f"Arquivos: {metricas.get('arquivos_processados','-')} | "
                        f"Contratos: {metricas.get('contratos_processados','-')} | "
                        f"Sucesso: {metricas.get('contratos_sucesso','-')} | "
                        f"Erros: {metricas.get('erros','-')}"
                    ),
                    "status": "concluido",
                    "caminhos_anexos": anexos
                }
            )
        else:
            detalhes_txt = (
                "❌ RPA SIENGE: Falha no processamento\n" + (erro_msg or "")
            )
            notificar_erro(
                nome_rpa="RPA Extração/Processamento Sienge",
                erro="Falha no pipeline",
                detalhes=detalhes_txt
            )
    except Exception as e:
        print(f"⚠️ Falha ao enviar notificação final: {e}")


if __name__ == "__main__":
    main()
