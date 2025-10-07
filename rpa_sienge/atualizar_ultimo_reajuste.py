#!/usr/bin/env python3
"""Script orientado a objetos para retroalimentar o campo "Último reajuste".

Este módulo provê uma interface de linha de comando capaz de localizar um
contrato específico na planilha base de cálculo do Sienge e atualizar o valor
do campo "Último reajuste". A lógica replica o padrão arquitetural utilizado
em `atualizar_planilha_extracao_resultados.py`, mas dispensando a leitura do
CSV intermediário e trabalhando exclusivamente com parâmetros fornecidos via
CLI.

O fluxo principal executa as seguintes etapas:

- Valida e normaliza o valor de data informado pelo usuário.
- Conecta à planilha do Google Sheets utilizando uma conta de serviço.
- Localiza a aba alvo e a linha correspondente ao contrato (código + título).
- Identifica a coluna "Último reajuste" e atualiza a célula com o novo valor.

Todas as mensagens de execução são registradas em português para manter
consistência com os demais scripts do projeto.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PROJETO_RAIZ = Path(__file__).resolve().parent.parent
if str(PROJETO_RAIZ) not in sys.path:
    sys.path.insert(0, str(PROJETO_RAIZ))

load_dotenv(PROJETO_RAIZ / ".env")

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_DISPONIVEL = True
except ImportError:  # pragma: no cover
    gspread = None  # type: ignore
    Credentials = None  # type: ignore
    GOOGLE_SHEETS_DISPONIVEL = False


def registrar_log(mensagem: str) -> None:
    """Exibe mensagem padronizada na saída padrão.

    Args:
        mensagem: Texto que será exibido para o usuário.

    Returns:
        None.
    """

    print(f"[ÚLTIMO REAJUSTE] {mensagem}")


def validar_data(data_reajuste: str) -> str:
    """Valida o formato e normaliza a data do último reajuste.

    Args:
        data_reajuste: Valor textual informado pelo usuário.

    Returns:
        Data normalizada no formato "DD/MM/AAAA" ou "MM/AAAA" conforme entrada.

    Raises:
        ValueError: Caso o valor fornecido não corresponda a nenhum formato
            suportado.
    """

    formatos_suportados = ("%d/%m/%Y", "%d/%m/%y", "%m/%Y", "%m/%y")
    for formato in formatos_suportados:
        try:
            data = datetime.strptime(data_reajuste, formato)
            if len(formato) == 5:  # Formatos MM/AA ou MM/AAAA
                return data.strftime("%m/%Y")
            return data.strftime("%d/%m/%Y")
        except ValueError:
            continue
    raise ValueError(
        "Data de reajuste inválida. Informe no formato DD/MM/AAAA ou MM/AAAA.")


def normalizar_texto(valor: str) -> str:
    """Normaliza texto removendo espaços excedentes e convertendo para minúsculo.

    Args:
        valor: Valor textual a ser normalizado.

    Returns:
        Representação normalizada do valor.
    """

    return str(valor).strip().lower()


def indice_para_coluna_excel(indice: int) -> str:
    """Converte um índice baseado em zero para a notação de coluna do Excel.

    Args:
        indice: Índice numérico baseado em zero.

    Returns:
        Referência de coluna (por exemplo, "A", "B", ..., "AA").
    """

    indice += 1
    referencia = ""
    while indice > 0:
        indice, resto = divmod(indice - 1, 26)
        referencia = chr(65 + resto) + referencia
    return referencia


@dataclass
class ConfiguracaoReajuste:
    """Agrega parâmetros necessários para a atualização do último reajuste.

    Attributes:
        planilha_id: Identificador da planilha no Google Sheets.
        caminho_credenciais: Caminho para o arquivo JSON da conta de serviço.
        nome_aba: Aba alvo (opcional).
        codigo_cliente: Código do cliente a ser localizado.
        titulo: Título do contrato a ser localizado.
        data_reajuste: Valor normalizado que será gravado na coluna.
    """

    planilha_id: str
    caminho_credenciais: Path
    nome_aba: Optional[str]
    codigo_cliente: str
    titulo: str
    data_reajuste: str


class RetroalimentadorUltimoReajuste:
    """Controla o processo de atualização da coluna "Último reajuste".

    Attributes:
        _configuracao: Instância contendo os parâmetros de execução.
        _cliente: Cliente autenticado do gspread.
    """

    def __init__(self, configuracao: ConfiguracaoReajuste) -> None:
        self._configuracao = configuracao
        self._cliente: Optional[gspread.Client] = None

    def executar(self) -> None:
        """Executa o fluxo completo de retroalimentação.

        Raises:
            RuntimeError: Quando bibliotecas do Google não estão instaladas.
            ValueError: Quando a aba, a linha ou a coluna não são localizadas.
        """

        registrar_log("Iniciando atualização do último reajuste.")
        worksheet = self._obter_worksheet()
        valores = worksheet.get_all_values()
        linha = self._localizar_linha(valores)
        coluna = self._localizar_coluna(valores)
        referencia = indice_para_coluna_excel(coluna) + str(linha)
        registrar_log(
            f"Atualizando célula {referencia} com o valor {self._configuracao.data_reajuste}"
        )
        worksheet.update_acell(referencia, self._configuracao.data_reajuste)
        registrar_log("✅ Atualização concluída com sucesso.")

    def _obter_worksheet(self) -> gspread.Worksheet:
        """Conecta ao Google Sheets e retorna a aba que será atualizada.

        Returns:
            Worksheet autenticada para leitura e escrita.

        Raises:
            RuntimeError: Se as bibliotecas necessárias não estiverem disponíveis.
            ValueError: Caso a aba não possa ser determinada automaticamente.
        """

        if not GOOGLE_SHEETS_DISPONIVEL:
            raise RuntimeError(
                "Bibliotecas Google Sheets não disponíveis. Instale gspread e google-auth."
            )

        credenciais = Credentials.from_service_account_file(
            str(self._configuracao.caminho_credenciais),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        self._cliente = gspread.authorize(credenciais)
        planilha = self._cliente.open_by_key(self._configuracao.planilha_id)

        if self._configuracao.nome_aba:
            registrar_log(
                f"Abrindo aba '{self._configuracao.nome_aba}'.")
            return planilha.worksheet(self._configuracao.nome_aba)

        registrar_log("Nenhuma aba informada – tentando localizar aba padrão.")
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
                return aba
            except gspread.WorksheetNotFound:
                continue

        raise ValueError(
            "Aba não informada e nenhuma aba padrão encontrada. Informe via --aba."
        )

    def _localizar_linha(self, valores: list[list[str]]) -> int:
        """Localiza a linha correspondente ao contrato especificado.

        Args:
            valores: Matriz com todas as células da planilha.

        Returns:
            Número da linha (baseado em 1) onde o contrato foi encontrado.

        Raises:
            ValueError: Quando o contrato não é localizado.
        """

        codigo_alvo = normalizar_texto(self._configuracao.codigo_cliente)
        titulo_alvo = normalizar_texto(self._configuracao.titulo)

        cabecalho = valores[0]
        indice_codigo = None
        indice_titulo = None
        for indice_coluna, titulo_coluna in enumerate(cabecalho):
            titulo_normalizado = normalizar_texto(titulo_coluna)
            if titulo_normalizado == normalizar_texto("Código Cliente"):
                indice_codigo = indice_coluna
            if titulo_normalizado == normalizar_texto("Título"):
                indice_titulo = indice_coluna

        if indice_codigo is None or indice_titulo is None:
            raise ValueError(
                "Colunas 'Código Cliente' e 'Título' são obrigatórias na planilha.")

        for indice, linha in enumerate(valores[1:], start=2):
            if not linha:
                continue
            if len(linha) <= max(indice_codigo, indice_titulo):
                continue
            codigo_encontrado = normalizar_texto(linha[indice_codigo])
            titulo_encontrado = normalizar_texto(linha[indice_titulo])

            if codigo_encontrado == codigo_alvo and titulo_encontrado == titulo_alvo:
                registrar_log(f"Linha encontrada para o contrato: {indice}")
                return indice

        raise ValueError(
            "Contrato não localizado na planilha base. Verifique código/título.")

    def _localizar_coluna(self, valores: list[list[str]]) -> int:
        """Identifica a coluna "Último reajuste" no cabeçalho da planilha.

        Args:
            valores: Matriz com o conteúdo completo da planilha.

        Returns:
            Índice baseado em zero da coluna desejada.

        Raises:
            ValueError: Caso a coluna não exista no cabeçalho.
        """

        cabecalho = valores[0]
        for indice, titulo_coluna in enumerate(cabecalho):
            if normalizar_texto(titulo_coluna) == normalizar_texto("Último reajuste"):
                registrar_log(
                    f"Coluna 'Último reajuste' encontrada: índice {indice}")
                return indice
        raise ValueError(
            "Coluna 'Último reajuste' não encontrada na planilha.")


def obter_argumentos() -> argparse.Namespace:
    """Interpreta os argumentos fornecidos via linha de comando.

    Returns:
        Namespace com todas as opções informadas pelo usuário.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Atualiza a coluna 'Último reajuste' na planilha base a partir de parâmetros."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--planilha-id", help="ID da planilha no Google Sheets")
    parser.add_argument(
        "--credenciais",
        help="Caminho para o arquivo de credenciais do Google",
    )
    parser.add_argument(
        "--aba",
        help="Nome da aba onde a atualização deve ser aplicada",
    )
    parser.add_argument(
        "--codigo-cliente",
        required=True,
        help="Código do cliente a ser localizado",
    )
    parser.add_argument(
        "--titulo",
        required=True,
        help="Título do contrato a ser localizado",
    )
    parser.add_argument(
        "--data-reajuste",
        required=True,
        help="Novo valor do campo 'Último reajuste'",
    )

    return parser.parse_args()


def construir_configuracao(args: argparse.Namespace) -> ConfiguracaoReajuste:
    """Constrói a configuração de execução a partir dos argumentos.

    Args:
        args: Argumentos retornados pelo parser.

    Returns:
        Instância preenchida de `ConfiguracaoReajuste`.

    Raises:
        ValueError: Em caso de ausência de planilha ou data inválida.
        FileNotFoundError: Se o arquivo de credenciais não existir.
    """

    planilha_id = args.planilha_id or os.getenv("PLANILHA_CALCULO_ID")
    if not planilha_id:
        raise ValueError(
            "ID da planilha não informado. Use --planilha-id ou defina PLANILHA_CALCULO_ID."
        )

    caminho_credenciais = Path(
        args.credenciais
        or os.getenv(
            "GOOGLE_CREDENTIALS_PATH",
            "./credentials/gspread-459713-aab8a657f9b0.json",
        )
    )

    if not caminho_credenciais.exists():
        raise FileNotFoundError(
            f"Arquivo de credenciais não encontrado: {caminho_credenciais}"
        )

    data_reajuste = validar_data(args.data_reajuste)

    return ConfiguracaoReajuste(
        planilha_id=planilha_id,
        caminho_credenciais=caminho_credenciais,
        nome_aba=args.aba,
        codigo_cliente=args.codigo_cliente,
        titulo=args.titulo,
        data_reajuste=data_reajuste,
    )


def main() -> None:
    """Ponto de entrada responsável por orquestrar a execução CLI.

    Returns:
        None.
    """

    argumentos = obter_argumentos()
    configuracao = construir_configuracao(argumentos)
    executor = RetroalimentadorUltimoReajuste(configuracao)
    executor.executar()


if __name__ == "__main__":
    main()
