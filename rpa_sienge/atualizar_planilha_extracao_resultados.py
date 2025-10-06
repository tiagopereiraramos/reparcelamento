#!/usr/bin/env python3
"""Script de retroalimentação da Planilha Base de Cálculo."""

import argparse
import csv
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import unicodedata
import re
import sys

from dotenv import load_dotenv

PROJETO_RAIZ = Path(__file__).resolve().parent.parent
if str(PROJETO_RAIZ) not in sys.path:
    sys.path.insert(0, str(PROJETO_RAIZ))

load_dotenv(PROJETO_RAIZ / ".env")

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_DISPONIVEL = True
except ImportError:  # pragma: no cover - dependência externa opcional
    gspread = None  # type: ignore
    Credentials = None  # type: ignore
    GOOGLE_SHEETS_DISPONIVEL = False


@dataclass
class ConfiguracaoRetroalimentacao:
    """Configuração principal do script."""

    caminho_csv: Path
    planilha_id: str
    caminho_credenciais: Path
    nome_aba: Optional[str]
    mes_base: Optional[str]


def registrar_log(mensagem: str) -> None:
    """Exibe mensagem formatada em português."""

    print(f"[RETROALIMENTAÇÃO] {mensagem}")


def carregar_csv(caminho: Path) -> List[Dict[str, Any]]:
    """Carrega o CSV de contratos processados."""

    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {caminho}")

    contratos: List[Dict[str, Any]] = []
    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if leitor.fieldnames is None:
            raise ValueError("CSV sem cabeçalho válido.")

        for linha in leitor:
            contrato: Dict[str, Any] = {}
            for chave, valor in linha.items():
                if valor is None:
                    contrato[chave] = ""
                elif isinstance(valor, str):
                    contrato[chave] = valor.strip()
                else:
                    contrato[chave] = valor
            contratos.append(contrato)

    registrar_log(f"Contratos carregados do CSV: {len(contratos)}")
    return contratos


def normalizar_texto(valor: Any) -> str:
    """Normaliza valores textuais para comparação."""

    if valor is None:
        return ""
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto


def gerar_chaves_contrato(codigo: str, titulo: str, lote: str) -> List[str]:
    """Gera diferentes combinações de chave para localizar contratos."""

    codigo_normalizado = normalizar_texto(codigo).lower()
    titulo_normalizado = normalizar_texto(titulo).lower()
    lote_normalizado = normalizar_texto(lote).lower()

    chaves = []
    if lote_normalizado:
        chaves.extend([
            f"{codigo_normalizado}|{lote_normalizado}|{titulo_normalizado}",
            f"{codigo_normalizado}|{lote_normalizado}|{titulo_normalizado.zfill(5)}",
        ])

    chaves.extend([
        f"{codigo_normalizado}|{titulo_normalizado}",
        f"{codigo_normalizado}|{titulo_normalizado.zfill(5)}",
        f"titulo|{titulo_normalizado}",
        f"titulo|{titulo_normalizado.zfill(5)}",
    ])

    return chaves


def normalizar_nome(texto: str) -> str:
    """Normaliza nomes de colunas removendo acentos e caracteres especiais."""

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9]", "", texto)
    return texto


def _normalizar_mes_reajuste(valor: Any) -> Optional[str]:
    """Normaliza valores de mês/ano para o formato MM/AAAA."""

    if not valor:
        return None

    texto = str(valor).strip().lower()
    if not texto:
        return None

    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.replace("-", " ").replace("/", " ").replace(".", " ")
    texto = re.sub(r"\s+", " ", texto)
    partes = texto.split(" ")

    if len(partes) < 2:
        return None

    mes_parte, ano_parte = partes[0], partes[1]
    if ano_parte.isdigit():
        if len(ano_parte) == 2:
            ano_parte = "20" + ano_parte
        elif len(ano_parte) != 4:
            return None
    else:
        return None

    if mes_parte.isdigit():
        mes = int(mes_parte)
        if 1 <= mes <= 12:
            return f"{mes:02d}/{ano_parte}"
        return None

    meses = {
        "jan": 1, "janeiro": 1,
        "fev": 2, "fevereiro": 2,
        "mar": 3, "marco": 3,
        "abr": 4, "abril": 4,
        "mai": 5, "maio": 5,
        "jun": 6, "junho": 6,
        "jul": 7, "julho": 7,
        "ago": 8, "agosto": 8,
        "set": 9, "setembro": 9,
        "out": 10, "outubro": 10,
        "nov": 11, "novembro": 11,
        "dez": 12, "dezembro": 12,
    }

    chave_mes = mes_parte[:3]
    if chave_mes in meses:
        return f"{meses[chave_mes]:02d}/{ano_parte}"

    return None


def preparar_sinonimos() -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """Normaliza listas de sinônimos para cabeçalhos."""

    req = {chave: [normalizar_nome(item) for item in valores]
           for chave, valores in CABECALHOS_REQUERIDOS.items()}
    atual = {
        chave: [normalizar_nome(item) for item in dados["aliases"]]
        for chave, dados in COLUNAS_ATUALIZACAO.items()
    }
    return req, atual


CABECALHOS_REQUERIDOS = {
    "codigo_cliente": [
        "Código Cliente",
        "Codigo Cliente",
        "codigo cliente",
        "codigo_cliente",
    ],
    "titulo": [
        "Titulo",
        "Título",
        "titulo",
        "titulo do contrato",
    ],
    "lote": [
        "Lote",
        "Lote ",
        "Quadra/Lote",
        "Quadra Lote",
        "lote",
    ],
}

COLUNAS_ATUALIZACAO = {
    "data_consulta_iptu": {
        "contrato": "Data de consulta IPTU",
        "aliases": [
            "Data de consulta IPTU",
            "Data consulta IPTU",
            "data de consulta iptu",
        ],
    },
    "pendencias_pmfi": {
        "contrato": "PENDENCIAS PMFI",
        "aliases": [
            "PENDENCIAS PMFI",
            "Pendencias PMFI",
            "pendencias pmfi",
        ],
    },
    "pendencias_sienge_inad": {
        "contrato": "PENDENCIAS SIENGE INAD",
        "aliases": [
            "PENDENCIAS SIENGE INAD",
            "pendencias sienge inad",
        ],
    },
    "pendencias_sienge": {
        "contrato": "PENDENCIAS SIENGE",
        "aliases": [
            "PENDENCIAS SIENGE",
            "pendencias sienge",
        ],
    },
    "parcelas_a_vencer": {
        "contrato": "Parcelas a vencer",
        "aliases": [
            "Parcelas a vencer",
            "parcelas a vencer",
        ],
    },
    "valor_parcela_base": {
        "contrato": "Valor da Parcela Base",
        "aliases": [
            "Valor da Parcela Base",
            "valor da parcela base",
        ],
    },
    "primeiro_vencimento_carne": {
        "contrato": "1º vencimento carnê",
        "aliases": [
            "1º vencimento carnê",
            "1 º vencimento carnê",
            "1 º vencimento carnê ",
            "1º vencimento carne",
            "1º vencimento carne ",
        ],
    },
}

COLUNAS_FILTRO = {
    "mes_reajuste": [
        "Mês reajuste",
        "Mes reajuste",
        "Mês do reajuste",
        "Mes do reajuste",
        "Reajuste Mês",
        "Reajuste Mes",
    ]
}

PRECISAIS_CANONICOS = ["codigo_cliente", "titulo"]

SINONIMOS_REQUERIDOS, SINONIMOS_ATUALIZACAO = preparar_sinonimos()


def encontrar_cabecalho(valores: List[List[str]]) -> Tuple[int, Dict[str, int]]:
    """Localiza a linha de cabeçalho e retorna índices mapeados por chave canônica."""

    for indice_linha, linha in enumerate(valores):
        mapa_normalizado: Dict[str, Tuple[str, int]] = {}
        for indice_coluna, celula in enumerate(linha):
            chave_norm = normalizar_nome(celula)
            if chave_norm and chave_norm not in mapa_normalizado:
                mapa_normalizado[chave_norm] = (celula, indice_coluna)

        if all(any(alias in mapa_normalizado for alias in SINONIMOS_REQUERIDOS[chave]) for chave in PRECISAIS_CANONICOS):
            indices: Dict[str, int] = {}
            for chave, aliases in SINONIMOS_REQUERIDOS.items():
                for alias in aliases:
                    if alias in mapa_normalizado:
                        indices[chave] = mapa_normalizado[alias][1]
                        break

            for chave, aliases in SINONIMOS_ATUALIZACAO.items():
                for alias in aliases:
                    if alias in mapa_normalizado:
                        indices[chave] = mapa_normalizado[alias][1]
                        break

            for chave, aliases in COLUNAS_FILTRO.items():
                for alias in aliases:
                    alias_norm = normalizar_nome(alias)
                    if alias_norm in mapa_normalizado:
                        indices[chave] = mapa_normalizado[alias_norm][1]
                        break

            return indice_linha, indices

    raise ValueError(
        "Cabeçalho com colunas obrigatórias não encontrado na planilha.")


def diagnosticar_cabecalho(valores: List[List[str]], quantidade: int = 5) -> None:
    """Exibe as primeiras linhas da planilha para auxiliar no diagnóstico."""

    registrar_log("Pré-visualização das primeiras linhas da planilha:")
    limite = min(quantidade, len(valores))
    for indice in range(limite):
        linha = valores[indice]
        registrar_log(f"Linha {indice + 1}: {linha}")


def montar_mapas_planilha(valores: List[List[str]], mes_base: Optional[str]) -> Tuple[Dict[str, int], Dict[str, List[int]]]:
    """Cria mapas de cabeçalhos e linhas para atualização rápida, com filtro opcional."""

    if not valores:
        raise ValueError("Planilha sem conteúdos – verifique a aba informada.")

    try:
        indice_cabecalho, indices = encontrar_cabecalho(valores)
        linha_cabecalho = valores[indice_cabecalho]

        for chave in PRECISAIS_CANONICOS:
            if chave not in indices:
                raise ValueError(
                    f"Coluna obrigatória ausente na planilha: {chave}")

        mapa_linhas: Dict[str, List[int]] = defaultdict(list)
        mes_base_normalizado = _normalizar_mes_reajuste(mes_base)
        coluna_mes_reajuste = indices.get("mes_reajuste")
        for deslocamento, linha in enumerate(valores[indice_cabecalho + 1:], start=indice_cabecalho + 2):
            codigo = ""
            titulo = ""
            lote = ""

            coluna_codigo = indices.get("codigo_cliente")
            if coluna_codigo is not None and len(linha) > coluna_codigo:
                codigo = normalizar_texto(linha[coluna_codigo])

            coluna_titulo = indices.get("titulo")
            if coluna_titulo is not None and len(linha) > coluna_titulo:
                titulo = normalizar_texto(linha[coluna_titulo])

            coluna_lote = indices.get("lote")
            if coluna_lote is not None and len(linha) > coluna_lote:
                lote = normalizar_texto(linha[coluna_lote])

            if mes_base_normalizado and coluna_mes_reajuste is not None and len(linha) > coluna_mes_reajuste:
                valor_mes_reajuste = linha[coluna_mes_reajuste]
                if _normalizar_mes_reajuste(valor_mes_reajuste) != mes_base_normalizado:
                    continue

            for chave in gerar_chaves_contrato(codigo, titulo, lote):
                if chave:
                    mapa_linhas[chave].append(deslocamento)

        registrar_log(
            f"Linhas indexadas na planilha: {len(mapa_linhas)} chaves únicas.")

        colunas_identificadas = []
        for chave, indice in indices.items():
            if chave in COLUNAS_ATUALIZACAO:
                nome_planilha = linha_cabecalho[indice] if indice < len(
                    linha_cabecalho) else ""
                colunas_identificadas.append(
                    f"{COLUNAS_ATUALIZACAO[chave]['contrato']} -> '{nome_planilha}' (coluna {indice_para_coluna_excel(indice)})"
                )
        if colunas_identificadas:
            registrar_log("Colunas de atualização mapeadas:")
            for descricao in colunas_identificadas:
                registrar_log(f"   • {descricao.rstrip()}")

        return indices, mapa_linhas
    except ValueError as erro:
        diagnosticar_cabecalho(valores)
        raise


def preparar_atualizacoes(contratos: List[Dict[str, Any]],
                          mapa_cabecalhos: Dict[str, int],
                          mapa_linhas: Dict[str, List[int]]) -> List[Dict[str, Any]]:
    """Monta payload para batch_update com o mínimo de chamadas possível."""

    atualizacoes_por_celula: List[Dict[str, Any]] = []
    total_sem_correspondencia = 0
    contagem_por_coluna: Dict[str, Dict[str, int]] = defaultdict(lambda: {
        "celulas": 0,
        "preenchidos": 0,
        "vazios": 0,
    })

    for contrato in contratos:
        codigo = contrato.get("Código Cliente", "")
        titulo = contrato.get("Titulo", "")
        lote = contrato.get("_lote", "")

        chaves = gerar_chaves_contrato(codigo, titulo, lote)
        linhas_correspondentes: List[int] = []
        for chave in chaves:
            if chave in mapa_linhas:
                linhas_correspondentes = mapa_linhas[chave]
                break

        if not linhas_correspondentes:
            total_sem_correspondencia += 1
            registrar_log(
                f"⚠️ Contrato não localizado na planilha: {codigo}-{titulo}")
            continue

        linha_excel = linhas_correspondentes[0]
        campos_atualizaveis = [
            "data_consulta_iptu",
            "pendencias_pmfi",
            "pendencias_sienge_inad",
            "pendencias_sienge",
            "parcelas_a_vencer",
            "valor_parcela_base",
            "primeiro_vencimento_carne",
        ]

        for chave_canonica in campos_atualizaveis:
            if chave_canonica not in mapa_cabecalhos:
                continue

            info = COLUNAS_ATUALIZACAO[chave_canonica]
            valor = contrato.get(info["contrato"], "")
            indice_coluna = mapa_cabecalhos[chave_canonica]
            letra_coluna = indice_para_coluna_excel(indice_coluna)
            intervalo = f"{letra_coluna}{linha_excel}:{letra_coluna}{linha_excel}"
            atualizacoes_por_celula.append(
                {"range": intervalo, "values": [[valor]]})

            contagem_por_coluna[chave_canonica]["celulas"] += 1
            if valor:
                contagem_por_coluna[chave_canonica]["preenchidos"] += 1
            else:
                contagem_por_coluna[chave_canonica]["vazios"] += 1

    registrar_log(
        f"Contratos sem correspondência: {total_sem_correspondencia}")
    registrar_log(
        f"Células preparadas para atualização: {len(atualizacoes_por_celula)}")

    if contagem_por_coluna:
        registrar_log("Resumo de valores por coluna:")
        for chave, contagem in contagem_por_coluna.items():
            info = COLUNAS_ATUALIZACAO[chave]
            registrar_log(
                f"   • {info['contrato']}: {contagem['preenchidos']} preenchidos, {contagem['vazios']} vazios (total {contagem['celulas']})"
            )
    return atualizacoes_por_celula


def conectar_google_sheets(caminho_credenciais: Path) -> gspread.Client:
    """Estabelece conexão com o Google Sheets."""

    if not GOOGLE_SHEETS_DISPONIVEL:
        raise RuntimeError(
            "Bibliotecas do Google Sheets ausentes. Instale gspread e google-auth.")

    if not caminho_credenciais.exists():
        raise FileNotFoundError(
            f"Credenciais não encontradas: {caminho_credenciais}")

    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credenciais = Credentials.from_service_account_file(
        str(caminho_credenciais), scopes=escopos)
    registrar_log("Autenticação realizada com sucesso.")
    return gspread.authorize(credenciais)


def obter_worksheet(client: gspread.Client, planilha_id: str, nome_aba: Optional[str]) -> Tuple[gspread.Worksheet, List[List[str]]]:
    """Obtém a worksheet alvo e seus valores; tenta detectar aba correta se não for informada."""

    planilha = client.open_by_key(planilha_id)

    def _carregar(aba: gspread.Worksheet) -> Tuple[gspread.Worksheet, List[List[str]]]:
        valores = aba.get_all_values()
        return aba, valores

    if nome_aba:
        registrar_log(f"Abrindo aba '{nome_aba}'.")
        aba = planilha.worksheet(nome_aba)
        return _carregar(aba)

    prioridade = [
        "Base de cálculo",
        "Base de cálculo ",
        "base de calculo",
        "Base de Calculo",
    ]
    for nome in prioridade:
        try:
            aba = planilha.worksheet(nome)
            registrar_log(f"Aba '{nome}' selecionada automaticamente.")
            return _carregar(aba)
        except gspread.WorksheetNotFound:
            continue

    registrar_log(
        "Nenhuma aba especificada – procurando aba com cabeçalho válido.")
    for aba in planilha.worksheets():
        valores = aba.get_all_values()
        try:
            encontrar_cabecalho(valores)
            registrar_log(
                f"Aba '{aba.title}' selecionada após análise de cabeçalho.")
            return aba, valores
        except ValueError:
            continue

    raise ValueError(
        "Nenhuma aba com cabeçalho válido encontrada. Informe explicitamente via --aba.")


def indice_para_coluna_excel(indice: int) -> str:
    """Converte índice de coluna (base zero) em referência estilo Excel."""

    indice += 1
    resultado = ""
    while indice > 0:
        indice, resto = divmod(indice - 1, 26)
        resultado = chr(65 + resto) + resultado
    return resultado


def executar_atualizacao(config: ConfiguracaoRetroalimentacao) -> None:
    """Fluxo principal de retroalimentação."""

    registrar_log("Iniciando retroalimentação da planilha base.")
    contratos = carregar_csv(config.caminho_csv)

    cliente = conectar_google_sheets(config.caminho_credenciais)
    worksheet, valores_planilha = obter_worksheet(
        cliente, config.planilha_id, config.nome_aba)

    registrar_log("Carregando dados atuais da planilha...")
    mapa_cabecalhos, mapa_linhas = montar_mapas_planilha(
        valores_planilha, config.mes_base)

    atualizacoes = preparar_atualizacoes(
        contratos, mapa_cabecalhos, mapa_linhas)
    if not atualizacoes:
        registrar_log("Nenhuma atualização necessária.")
        return

    registrar_log("Enviando batch_update ao Google Sheets...")
    worksheet.batch_update(atualizacoes)
    registrar_log("✅ Retroalimentação concluída com sucesso.")


def construir_configuracao(args: argparse.Namespace) -> ConfiguracaoRetroalimentacao:
    """Cria objeto de configuração a partir dos argumentos e variáveis de ambiente."""

    caminho_csv = Path(args.csv)
    planilha_id = args.planilha_id or os.getenv("PLANILHA_CALCULO_ID")
    if not planilha_id:
        raise ValueError(
            "PLANILHA_CALCULO_ID não informado via argumento ou variável de ambiente.")

    caminho_credenciais = Path(
        args.credenciais or os.getenv(
            "GOOGLE_CREDENTIALS_PATH", "./credentials/gspread-459713-aab8a657f9b0.json")
    )

    return ConfiguracaoRetroalimentacao(
        caminho_csv=caminho_csv,
        planilha_id=planilha_id,
        caminho_credenciais=caminho_credenciais,
        nome_aba=args.aba,
        mes_base=args.mes_base,
    )


def obter_argumentos() -> argparse.Namespace:
    """Interpreta os argumentos de linha de comando."""

    parser = argparse.ArgumentParser(
        description="Atualiza a planilha base de cálculo a partir do JSON gerado pelo processamento local.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--csv", default="resultados_processamento.csv", help="Arquivo CSV de entrada")
    parser.add_argument(
        "--planilha-id", help="ID da planilha de cálculo no Google Sheets")
    parser.add_argument(
        "--credenciais", help="Caminho para o arquivo de credenciais do Google")
    parser.add_argument(
        "--aba", help="Nome da aba da planilha que será atualizada")
    parser.add_argument(
        "--mes-base", help="Filtro de mês/ano (MM/AAAA) para limitar a retroalimentação")

    return parser.parse_args()


def main() -> None:
    """Ponto de entrada do script de retroalimentação."""

    args = obter_argumentos()
    configuracao = construir_configuracao(args)
    executar_atualizacao(configuracao)


if __name__ == "__main__":
    main()
