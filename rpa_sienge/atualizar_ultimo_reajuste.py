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
import pandas as pd

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import shutil

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

# Notificações e exportação
try:
    from core.notificacoes_simples import notificar_sucesso, notificar_erro
except Exception:  # pragma: no cover
    def notificar_sucesso(**kwargs):  # type: ignore
        _ = kwargs
        pass

    def notificar_erro(**kwargs):  # type: ignore
        _ = kwargs
        pass


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
    """Normaliza texto para comparação robusta com cabeçalhos da planilha.

    - Remove acentos/diacríticos
    - Converte para minúsculo
    - Colapsa espaços e remove caracteres não alfanuméricos básicos

    Args:
        valor: Valor textual a ser normalizado.

    Returns:
        Representação normalizada do valor (ex.: "Mês reajuste" -> "mes reajuste").
    """

    import unicodedata
    import re

    texto = str(valor).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    # Mantém letras, números e espaços; remove o restante
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def converter_mes_curto_para_mm_aaaa(valor: str) -> str:
    """Converte formatos como "nov.-25", "nov/25", "nov 25" em "11/2025".

    Aceita também valores que já estejam como "MM/AAAA" ou "MM/AA" e normaliza.

    Args:
        valor: Texto do mês abreviado com ano de dois dígitos.

    Returns:
        String no formato "MM/AAAA".

    Raises:
        ValueError: Se o valor não puder ser interpretado.
    """

    v = normalizar_texto(valor).replace(".", "").replace(
        "_", " ").replace("-", " ").replace("/", " ")
    partes = [p for p in v.split() if p]

    meses = {
        "jan": "01", "fev": "02", "mar": "03", "abr": "04", "mai": "05", "jun": "06",
        "jul": "07", "ago": "08", "set": "09", "out": "10", "nov": "11", "dez": "12",
    }

    # Se já estiver nos formatos aceitos por validar_data, apenas normaliza
    try:
        return validar_data(valor)
    except Exception:
        pass

    if len(partes) != 2:
        raise ValueError("Formato de mês inválido. Ex.: 'nov.-25'.")

    mes_txt, ano_txt = partes[0][:3], partes[1][-2:]
    if mes_txt not in meses or not ano_txt.isdigit():
        raise ValueError("Mês/ano inválidos no valor informado.")

    mes = meses[mes_txt]
    ano = int(ano_txt)
    ano += 2000 if ano < 70 else 1900  # regra simples para dois dígitos
    return f"{mes}/{ano}"


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
        modo_lote: Quando True, ativa atualização em lote.
        mes_reajuste_alvo: Valor textual do campo "Mês reajuste" a filtrar (ex.: "nov.-25").
        valor_ultimo_reajuste_lote: Valor a gravar em "Último reajuste" no lote. Se ausente, será derivado do mês.
    """

    planilha_id: str
    caminho_credenciais: Path
    nome_aba: Optional[str]
    codigo_cliente: str
    titulo: str
    data_reajuste: str
    modo_lote: bool = False
    mes_reajuste_alvo: Optional[str] = None
    valor_ultimo_reajuste_lote: Optional[str] = None
    notificar: bool = True


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

        if self._configuracao.modo_lote:
            valor_aplicado = self._executar_lote(worksheet, valores)
            # Renomeia fila conforme a data aplicada
            try:
                self._renomear_fila_contratos(valor_aplicado)
            except Exception as e:
                registrar_log(f"Aviso ao renomear fila_contratos: {e}")
            return

        linha = self._localizar_linha(valores)
        coluna = self._localizar_coluna_por_titulo(valores, "Último reajuste")
        referencia = indice_para_coluna_excel(coluna) + str(linha)
        registrar_log(
            f"Atualizando célula {referencia} com o valor {self._configuracao.data_reajuste}"
        )
        worksheet.update_acell(referencia, self._configuracao.data_reajuste)
        registrar_log("✅ Atualização concluída com sucesso.")
        # Renomeia fila conforme a data aplicada
        try:
            self._renomear_fila_contratos(self._configuracao.data_reajuste)
        except Exception as e:
            registrar_log(f"Aviso ao renomear fila_contratos: {e}")

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

        # Usa função unificada de conexão
        cliente = conectar_google_sheets(
            self._configuracao.caminho_credenciais)

        try:
            planilha = cliente.open_by_key(self._configuracao.planilha_id)
        except Exception as e:
            raise ValueError(
                "Não foi possível abrir a planilha pelo ID fornecido. "
                "Verifique se: (1) o ID é o real (sem < >), (2) a planilha existe, "
                "e (3) o e-mail da conta de serviço possui acesso (compartilhe a planilha)."
            ) from e

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

        # Fallback: procurar aba com cabeçalho contendo Código Cliente e Título
        registrar_log(
            "Nenhuma aba padrão encontrada – procurando cabeçalho válido.")
        for aba in planilha.worksheets():
            try:
                valores = aba.get_all_values()
            except Exception:
                continue
            if not valores:
                continue
            cabecalho = [normalizar_texto(c) for c in valores[0]]
            if normalizar_texto("Código Cliente") in cabecalho and normalizar_texto("Título") in cabecalho:
                registrar_log(
                    f"Aba '{aba.title}' selecionada por cabeçalho válido.")
                return aba

        raise ValueError(
            "Aba não informada e nenhuma aba válida encontrada. Informe via --aba.")

    def _executar_lote(self, worksheet: gspread.Worksheet, valores: list[list[str]]) -> str:
        """Atualiza em lote todas as linhas cujo "Mês reajuste" corresponda ao alvo.

        Args:
            worksheet: Worksheet autenticada.
            valores: Matriz com o conteúdo completo da planilha.

        Raises:
            ValueError: Caso a coluna de filtro ou alvo não exista ou não hajam linhas.
        """

        cabecalho = valores[0]
        idx_mes = self._localizar_coluna_por_titulo(
            [cabecalho], "Mês reajuste")
        idx_ultimo = self._localizar_coluna_por_titulo(
            [cabecalho], "Último reajuste")

        alvo_mm_aaaa = converter_mes_curto_para_mm_aaaa(
            self._configuracao.mes_reajuste_alvo or "")

        if self._configuracao.valor_ultimo_reajuste_lote:
            valor_gravar = validar_data(
                self._configuracao.valor_ultimo_reajuste_lote)
        else:
            # Usar o dia 1 do mês de reparcelamento quando não informada
            # alvo_mm_aaaa já está no formato "MM/AAAA" (ex: "12/2025")
            mm, aaaa = alvo_mm_aaaa.split("/")
            data_reajuste = datetime(int(aaaa), int(mm), 1)
            valor_gravar = data_reajuste.strftime("%d/%m/%Y")

        linhas_afetadas_indices: list[int] = []
        atualizacoes_batch: list[dict] = []
        for i, linha in enumerate(valores[1:], start=2):
            if not linha or len(linha) <= max(idx_mes, idx_ultimo):
                continue
            try:
                mes_linha = converter_mes_curto_para_mm_aaaa(linha[idx_mes])
            except Exception:
                # Tenta normalização adicional: se já estiver "MM/AAAA" ou "DD/MM/AAAA"
                try:
                    v = validar_data(linha[idx_mes])
                    if len(v) == 7:  # MM/AAAA
                        mes_linha = v
                    else:  # DD/MM/AAAA -> MM/AAAA
                        dia, mm, aaaa = v.split("/")
                        mes_linha = f"{mm}/{aaaa}"
                except Exception:
                    continue
            if mes_linha == alvo_mm_aaaa:
                referencia = indice_para_coluna_excel(idx_ultimo) + str(i)
                atualizacoes_batch.append({
                    "range": f"{referencia}:{referencia}",
                    "values": [[valor_gravar]],
                })
                linhas_afetadas_indices.append(i)

        total = len(linhas_afetadas_indices)
        registrar_log(
            f"✅ Atualização em lote concluída. Linhas afetadas: {total}")

        # Enviar em lote para reduzir solicitações de escrita (como no atualizar_planilha_extracao_resultados)
        if total > 0 and atualizacoes_batch:
            try:
                worksheet.batch_update(
                    atualizacoes_batch, value_input_option="USER_ENTERED"
                )
            except Exception as e:
                # Backoff simples para 429 (cota por minuto)
                from gspread.exceptions import APIError  # type: ignore
                import time
                if isinstance(e, APIError) and "Quota exceeded" in str(e):
                    registrar_log(
                        "Cota de escrita excedida. Aguardando 65s para retry...")
                    time.sleep(65)
                    worksheet.batch_update(
                        atualizacoes_batch, value_input_option="USER_ENTERED"
                    )
                else:
                    raise

        # Exportar Excel com TODAS as colunas das linhas afetadas (após atualização)
        if total > 0:
            # Recarrega a planilha para refletir os valores já atualizados
            valores_atualizados = worksheet.get_all_values()
            linhas_export = [valores_atualizados[0]] + [valores_atualizados[i-1]
                                                        for i in linhas_afetadas_indices]
            df = pd.DataFrame(linhas_export[1:], columns=linhas_export[0])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dir_export = Path(PROJETO_RAIZ) / "outputs" / "relatorios"
            dir_export.mkdir(parents=True, exist_ok=True)
            caminho_excel = dir_export / \
                f"atualizacoes_ultimo_reajuste_{timestamp}.xlsx"
            with pd.ExcelWriter(caminho_excel, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Atualizacoes")

            # Notificar sucesso no molde do main_sicredi
            if self._configuracao.notificar:
                try:
                    mensagem = (
                        f"Atualização em lote concluída.\n"
                        f"Linhas atualizadas: {total}\n"
                        f"Valor aplicado em 'Último reajuste': {valor_gravar}"
                    )
                    notificar_sucesso(
                        nome_rpa="RPA Sienge - Atualização Último Reajuste",
                        tempo_execucao="-",
                        resultados={
                            "titulo": "Atualização do campo 'Último reajuste'",
                            "mensagem": mensagem,
                            "status": "concluido",
                            "caminhos_anexos": [str(caminho_excel)]
                        }
                    )
                except Exception as e:  # pragma: no cover
                    registrar_log(f"Aviso: falha ao enviar notificação: {e}")
        else:
            if self._configuracao.notificar:
                try:
                    notificar_erro(
                        nome_rpa="RPA Sienge - Atualização Último Reajuste",
                        erro="Nenhuma linha correspondente encontrada",
                        detalhes=f"Filtro de mês: {self._configuracao.mes_reajuste_alvo}"
                    )
                except Exception as e:  # pragma: no cover
                    registrar_log(
                        f"Aviso: falha ao enviar notificação de erro: {e}")

        # Retorna a data aplicada para renomeação da fila
        return valor_gravar

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

    def _localizar_coluna_por_titulo(self, valores: list[list[str]], titulo: str) -> int:
        """Identifica a coluna pelo título informado no cabeçalho.

        Args:
            valores: Matriz com o conteúdo completo da planilha (apenas cabeçalho é usado).
            titulo: Título a localizar.

        Returns:
            Índice baseado em zero da coluna desejada.

        Raises:
            ValueError: Caso a coluna não exista no cabeçalho.
        """

        cabecalho = valores[0]
        for indice, titulo_coluna in enumerate(cabecalho):
            if normalizar_texto(titulo_coluna) == normalizar_texto(titulo):
                registrar_log(f"Coluna '{titulo}' encontrada: índice {indice}")
                return indice
        raise ValueError(f"Coluna '{titulo}' não encontrada na planilha.")

    def _renomear_fila_contratos(self, data_utilizada: str) -> None:
        """Renomeia o arquivo de fila conforme a data utilizada.

        Usa o valor aplicado em "Último reajuste" para gerar o sufixo
        no formato dd_mm_aaaa. Quando a data estiver no formato MM/AAAA,
        assume-se o dia "01".

        Args:
            data_utilizada: String de data ("DD/MM/AAAA" ou "MM/AAAA").
        """

        # Normaliza para DD/MM/AAAA ao máximo
        data_txt = data_utilizada.strip()
        if len(data_txt) == 7:  # MM/AAAA
            mm, aaaa = data_txt.split("/")
            data_txt = f"01/{mm}/{aaaa}"
        # Constrói sufixo dd_mm_aaaa
        try:
            dt = datetime.strptime(data_txt, "%d/%m/%Y")
        except ValueError:
            # Fallback: tenta extrair números
            partes = [p for p in data_txt.replace("-", "/").split("/") if p]
            if len(partes) == 3 and all(partes):
                d, m, a = partes
                dt = datetime(int(a), int(m), int(d))
            else:
                raise ValueError(
                    "Data inválida para renomeação da fila de contratos.")

        sufixo = dt.strftime("%d_%m_%Y")
        pasta_data = Path(PROJETO_RAIZ) / "data"
        origem = pasta_data / "fila_contratos.json"
        destino = pasta_data / f"fila_contratos_{sufixo}.json"

        if not origem.exists():
            registrar_log(
                f"Arquivo de fila não encontrado para renomear: {origem}")
            return

        # Se já existir, cria um nome alternativo com timestamp
        if destino.exists():
            timestamp = datetime.now().strftime("%H%M%S")
            destino = pasta_data / f"fila_contratos_{sufixo}_{timestamp}.json"

        shutil.move(str(origem), str(destino))
        registrar_log(f"Arquivo de fila renomeado para: {destino.name}")


def conectar_google_sheets(caminho_credenciais: Path) -> gspread.Client:
    """Estabelece conexão com o Google Sheets (padrão unificado)."""

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

    # Modo contrato único
    parser.add_argument(
        "--codigo-cliente",
        help="Código do cliente a ser localizado",
    )
    parser.add_argument(
        "--titulo",
        help="Título do contrato a ser localizado",
    )
    parser.add_argument(
        "--data-reajuste",
        help="Novo valor do campo 'Último reajuste'",
    )

    # Modo lote
    parser.add_argument(
        "--lote-mes-reajuste",
        help="Valor textual do campo 'Mês reajuste' a filtrar (ex.: 'nov.-25')",
    )
    parser.add_argument(
        "--lote-ultimo-reajuste",
        help=(
            "Valor a gravar em 'Último reajuste' no lote (ex.: '11/2025' ou '01/11/2025'). "
            "Se omitido, será derivado do mês do filtro."
        ),
    )

    # Controle de notificação
    def _str_para_bool(v: str) -> bool:
        return str(v).strip().lower() not in {"false", "0", "no", "n"}

    parser.add_argument(
        "--notificar",
        help="Controla o envio de notificações por e-mail (true/false)",
        default="true",
        type=_str_para_bool,
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

    # Preferir .env quando o argumento é placeholder (contém "..." ou tokens genéricos)
    arg_id = (args.planilha_id or "").strip()
    if (not arg_id) or ("..." in arg_id) or (arg_id in {"ID_REAL", "<ID_REAL>", "<ID>", "ID", "1AbCdEfG...ID_REAL..."}):
        planilha_id = os.getenv("PLANILHA_CALCULO_ID")
    else:
        planilha_id = arg_id

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

    modo_lote = bool(args.lote_mes_reajuste)

    if modo_lote:
        # Validar que o parâmetro de filtro existe
        if not args.lote_mes_reajuste:
            raise ValueError("Para modo lote, informe --lote-mes-reajuste.")
        # Validar ou derivar o valor a ser gravado
        valor_lote = args.lote_ultimo_reajuste
        if valor_lote:
            valor_lote = validar_data(valor_lote)
        # Não exige código/título/data no modo lote
        return ConfiguracaoReajuste(
            planilha_id=planilha_id,
            caminho_credenciais=caminho_credenciais,
            nome_aba=args.aba,
            codigo_cliente="",
            titulo="",
            data_reajuste="",
            modo_lote=True,
            mes_reajuste_alvo=args.lote_mes_reajuste,
            valor_ultimo_reajuste_lote=valor_lote,
            notificar=bool(args.notificar),
        )

    # Modo contrato único (valida obrigatórios)
    if not args.codigo_cliente or not args.titulo or not args.data_reajuste:
        raise ValueError(
            "Para modo individual, informe --codigo-cliente, --titulo e --data-reajuste."
        )

    data_reajuste = validar_data(args.data_reajuste)

    return ConfiguracaoReajuste(
        planilha_id=planilha_id,
        caminho_credenciais=caminho_credenciais,
        nome_aba=args.aba,
        codigo_cliente=args.codigo_cliente,
        titulo=args.titulo,
        data_reajuste=data_reajuste,
        notificar=bool(args.notificar),
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
