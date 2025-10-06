#!/usr/bin/env python3
"""
Script para Atualização Completa da Planilha Base
================================================

Este script autônomo extrai dados dos relatórios Sienge locais e atualiza a planilha base
de cálculo seguindo rigorosamente as regras do PDD, incluindo:

1. Extração do dia de vencimento das parcelas
2. Cálculo correto do 1º vencimento conforme tipo de reajuste (Anual/Aniversário)
3. Contagem precisa de parcelas a vencer
4. Identificação de inadimplência e outras pendências
5. Atualização da planilha com todos os dados extraídos (opcional)
6. Salva resultados em JSON para análise ou atualização posterior

Não requer execução do RPA, apenas acesso aos relatórios salvos localmente.
"""

import os
import sys
from pathlib import Path
import asyncio
import argparse
import re
import json
import unicodedata
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

from dotenv import load_dotenv


# Garante que o diretório raiz esteja disponível para importações locais (ex.: core.*)
PROJETO_RAIZ = Path(__file__).resolve().parent.parent
if str(PROJETO_RAIZ) not in sys.path:
    sys.path.insert(0, str(PROJETO_RAIZ))

# Carrega variáveis de ambiente (.env) para credenciais externas
load_dotenv(PROJETO_RAIZ / ".env")

# Variável global para controlar o modo debug
DEBUG = False
ARQUIVO_LOG_ATUAL: Optional[Path] = None

# Importações do sistema de notificações
try:
    from core.notificacoes_simples import (
        notificar_sucesso,
        notificar_erro,
    )
except ImportError:
    notificar_sucesso = None
    notificar_erro = None

# Importações condicionais para Google Sheets
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_DISPONIVEL = True
except ImportError:
    gspread = None
    Credentials = None
    GOOGLE_SHEETS_DISPONIVEL = False

# Função de log para facilitar a exibição de mensagens


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


@contextmanager
def captura_logs_em_arquivo():
    """Direciona stdout/stderr para logs diário e individual da execução."""
    momento = datetime.now()
    logs_dir = Path("outputs") / momento.strftime("%Y") / \
        momento.strftime("%m")
    logs_dir.mkdir(parents=True, exist_ok=True)

    arquivo_diario = logs_dir / f"logs{momento.strftime('%Y%m%d')}.txt"
    arquivo_execucao = logs_dir / \
        f"logs{momento.strftime('%Y%m%d_%H%M%S')}.txt"

    class Multilog:
        def __init__(self, *destinos):
            self.destinos = destinos

        def write(self, mensagem):
            for destino in self.destinos:
                destino.write(mensagem)

        def flush(self):
            for destino in self.destinos:
                destino.flush()

    stdout_original = sys.stdout
    stderr_original = sys.stderr

    with open(arquivo_diario, "a", encoding="utf-8") as log_diario, open(arquivo_execucao, "a", encoding="utf-8") as log_execucao:
        multilog = Multilog(stdout_original, log_diario, log_execucao)
        sys.stdout = multilog
        sys.stderr = multilog
        try:
            global ARQUIVO_LOG_ATUAL
            ARQUIVO_LOG_ATUAL = arquivo_execucao
            yield
        finally:
            sys.stdout = stdout_original
            sys.stderr = stderr_original


def notificar_sucesso_simples(titulo: str, mensagem: str) -> None:
    """Registra notificação de sucesso simples no console."""

    print(f"\n✅ {titulo}\n{mensagem}")


def notificar_erro_simples(titulo: str, mensagem: str) -> None:
    """Registra notificação de erro simples e dispara alerta pelo sistema padrão."""

    print(f"\n❌ {titulo}\n{mensagem}")

    if notificar_erro:
        detalhes = mensagem
        if ARQUIVO_LOG_ATUAL and Path(ARQUIVO_LOG_ATUAL).exists():
            detalhes = f"{mensagem}\nLog: {ARQUIVO_LOG_ATUAL}"

        try:
            notificar_erro(
                nome_rpa="Processar Regras Reparcelamento",
                erro=titulo,
                detalhes=detalhes
            )
        except Exception as erro_envio:
            log(f"⚠️ Falha ao enviar notificação de erro: {erro_envio}")


def normalizar_tipo_reajuste(valor: Optional[str]) -> Optional[str]:
    """Normaliza string de tipo de reajuste para valores válidos."""
    if valor is None:
        return None

    texto = str(valor).strip().lower()
    if not texto or texto in {"auto", "automático", "automatico"}:
        return None
    if texto.startswith("aniver"):
        return "aniversario"
    if texto.startswith("anual"):
        return "anual"
    return texto


class AtualizadorPlanilhaBase:
    """
    Classe para atualizar a planilha base de cálculo usando relatórios Sienge locais,
    seguindo rigorosamente as regras do PDD.
    """

    def __init__(self):
        """Inicializa o atualizador da planilha"""
        os.environ.setdefault(
            "PLANILHA_CALCULO_ID", "1NTDPDEltum8X3vBHvUetCNWVEcz453FfAZGRYGmmd8U")
        os.environ.setdefault(
            "PLANILHA_APOIO_ID", "1Czt8Vy6f_3lG9RHM3bNkq0Yq1cv8VpByYtHVtRduX94")
        os.environ.setdefault(
            "GOOGLE_CREDENTIALS_PATH", "./credentials/gspread-459713-aab8a657f9b0.json")

        self.diretorio_relatorios = Path(os.path.expanduser("~")) / "Documents" / \
            "Tragetoria" / "reparcelamentov3" / "reparcelamento" / \
            "dados_extraidos" / "planilhas_sienge"
        if not os.path.exists(self.diretorio_relatorios):
            self.diretorio_relatorios = Path(
                "dados_extraidos") / "planilhas_sienge"

        # Diretório para salvar resultados de auditoria
        self.dir_auditoria = Path(".auditoria")
        self.dir_auditoria.mkdir(exist_ok=True)

        # Cliente Google Sheets (inicializado sob demanda)
        self.cliente_sheets = None
        # Cache da planilha base de cálculo
        self.cache_base_calculo = None

    def extrair_codigo_cliente_arquivo(self, arquivo: Path) -> Optional[str]:
        """Extrai o código do cliente do nome do arquivo usando o padrão sienge_CODIGO_TIMESTAMP.xlsx"""
        nome_arquivo = arquivo.name
        match = re.match(r'sienge_(\d+)_(\d{8}_\d{6})\.xlsx', nome_arquivo)
        return match.group(1) if match else None

    def conectar_google_sheets(self, caminho_credenciais: Optional[str] = None):
        """
        Conecta ao Google Sheets usando credenciais de serviço.

        Args:
            caminho_credenciais: Caminho para o arquivo de credenciais JSON

        Returns:
            bool: True se a conexão foi bem-sucedida, False caso contrário
        """
        if not GOOGLE_SHEETS_DISPONIVEL:
            log("⚠️ Módulo gspread não está disponível. Instalação: pip install gspread google-auth")
            return False

        try:
            # Definir escopo para acesso às planilhas
            SCOPES = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            # Usar caminho padrão se não fornecido
            if not caminho_credenciais:
                caminho_credenciais = os.getenv(
                    'GOOGLE_CREDENTIALS_PATH', 'credentials/gspread-459713-aab8a657f9b0.json')

            # Verificar se arquivo existe
            if not os.path.exists(caminho_credenciais):
                log(
                    f"❌ Arquivo de credenciais não encontrado: {caminho_credenciais}")
                return False

            # Autenticar com Google Sheets
            credenciais = Credentials.from_service_account_file(
                caminho_credenciais, scopes=SCOPES)
            self.cliente_sheets = gspread.authorize(credenciais)
            log("✅ Conexão com Google Sheets estabelecida")
            return True

        except Exception as e:
            log(f"❌ Erro ao conectar ao Google Sheets: {str(e)}")
            return False

    def carregar_todos_dados_iptu(self) -> Dict[str, Dict[str, Any]]:
        """
        Carrega todos os dados de IPTU da planilha de base de apoio de uma vez só.

        Returns:
            Dict mapeando 'codigo_cliente-titulo' para dados de IPTU
        """
        if not GOOGLE_SHEETS_DISPONIVEL:
            log("⚠️ Google Sheets não está disponível. Instalação: pip install gspread google-auth")
            return {}

        try:
            # Verificar se cliente Google Sheets está disponível
            if not self.cliente_sheets:
                if not self.conectar_google_sheets():
                    return {}

            # Obter ID da planilha de apoio
            planilha_apoio_id = os.getenv("PLANILHA_APOIO_ID")
            if not planilha_apoio_id:
                log("⚠️ PLANILHA_APOIO_ID não configurada - retornando dados vazios")
                return {}

            # Abrir planilha de apoio
            log("🔄 Conectando à planilha de apoio...")
            planilha_iptu = self.cliente_sheets.open_by_key(planilha_apoio_id)

            # Encontrar aba IPTU correta
            abas_disponiveis = [
                aba.title for aba in planilha_iptu.worksheets()]
            log(
                f"📋 Abas disponíveis na planilha de apoio: {', '.join(abas_disponiveis)}")

            aba_iptu_nome = None
            for possibilidade in ["Consulta IPTU", "IPTU", "Pendencias IPTU"]:
                if possibilidade in abas_disponiveis:
                    aba_iptu_nome = possibilidade
                    break

            if not aba_iptu_nome:
                log("⚠️ Aba de IPTU não encontrada - retornando dados vazios")
                return {}

            # Acessar aba e obter todos os dados de uma vez
            log(f"📥 Carregando todos os dados da aba '{aba_iptu_nome}'...")
            aba_iptu = planilha_iptu.worksheet(aba_iptu_nome)
            dados_iptu = aba_iptu.get_all_records()

            log(f"📊 Total de registros IPTU carregados: {len(dados_iptu)}")

            # Processar todos os dados e criar um dicionário para acesso rápido
            dados_iptu_processados = {}
            consultas_mes_vigente = 0

            for consulta in dados_iptu:
                codigo_cliente = str(consulta.get(
                    'Código Cliente', '')).strip()
                numero_titulo = str(consulta.get('Titulo', '')).strip()

                if not codigo_cliente or not numero_titulo:
                    continue

                # Normalizar chaves para lidar com variações de espaços e maiúsculas/minúsculas
                chaves_brutas = {(chave or '').strip()                                 : valor for chave, valor in consulta.items()}
                chaves_normalizadas = {
                    re.sub(r'\s+', ' ', chave.lower()): valor
                    for chave, valor in chaves_brutas.items()
                }

                def obter_valor_coluna(*possiveis_nomes: str) -> str:
                    """Retorna o valor da primeira coluna encontrada entre os nomes informados."""
                    for nome in possiveis_nomes:
                        if nome in chaves_brutas and chaves_brutas[nome] not in (None, ''):
                            return str(chaves_brutas[nome]).strip()
                        nome_normalizado = re.sub(
                            r'\s+', ' ', nome.strip().lower())
                        if nome_normalizado in chaves_normalizadas and chaves_normalizadas[nome_normalizado] not in (None, ''):
                            return str(chaves_normalizadas[nome_normalizado]).strip()
                    return ''

                # Usar o nome correto da coluna conforme a planilha base de apoio
                data_consulta_str = obter_valor_coluna(
                    'Data de consulta  IPTU ',
                    'Data de consulta  IPTU',
                    'Data de consulta IPTU',
                    'Data de consulta IPTU ',
                    'Data consulta IPTU'
                )

                # Usar o nome correto da coluna de pendências conforme a planilha base de apoio
                pendencia_str = obter_valor_coluna(
                    'PENDENCIAS PMFI ',
                    'PENDENCIAS PMFI',
                    'Pendencias PMFI'
                )

                # Obter o número do lote para criar uma chave mais específica
                lote = obter_valor_coluna('Lote')

                # Normalizar os dados para garantir correspondência
                codigo_cliente_norm = codigo_cliente.strip().lower()
                numero_titulo_norm = numero_titulo.strip().lower()

                # Remover o .0 do número do título para corresponder com a planilha
                numero_titulo_sem_ponto = numero_titulo_norm.replace('.0', '')

                # Adicionar versões com zeros à esquerda (para números como "123" vs "00123")
                try:
                    numero_titulo_int = int(
                        float(numero_titulo_norm.replace(',', '.')))
                    # 5 dígitos com zeros à esquerda
                    numero_titulo_padded = f"{numero_titulo_int:05d}"
                except (ValueError, TypeError):
                    numero_titulo_padded = numero_titulo_norm

                # Criar várias chaves possíveis para identificação, priorizando a combinação de código_cliente, lote e título
                chaves = []

                # Chaves com código_cliente, lote e título (mais específicas)
                if lote:
                    lote_norm = lote.strip().lower()
                    chaves.extend([
                        # Formato original
                        f"{codigo_cliente}-{lote}-{numero_titulo}",
                        # Sem .0
                        f"{codigo_cliente}-{lote}-{numero_titulo_sem_ponto}",
                        # Normalizado
                        f"{codigo_cliente_norm}-{lote_norm}-{numero_titulo_norm}",
                        # Normalizado sem .0
                        f"{codigo_cliente_norm}-{lote_norm}-{numero_titulo_sem_ponto}",
                        # Com zeros à esquerda
                        f"{codigo_cliente}-{lote}-{numero_titulo_padded}",
                        # Normalizado com zeros à esquerda
                        f"{codigo_cliente_norm}-{lote_norm}-{numero_titulo_padded}",
                    ])

                # Chaves com código_cliente e título (segunda prioridade)
                chaves.extend([
                    # Formato original
                    f"{codigo_cliente}-{numero_titulo}",
                    f"{codigo_cliente}-{numero_titulo_sem_ponto}",        # Sem .0
                    # Normalizado
                    f"{codigo_cliente_norm}-{numero_titulo_norm}",
                    # Normalizado sem .0
                    f"{codigo_cliente_norm}-{numero_titulo_sem_ponto}",
                    # Com zeros à esquerda
                    f"{codigo_cliente}-{numero_titulo_padded}",
                    # Normalizado com zeros à esquerda
                    f"{codigo_cliente_norm}-{numero_titulo_padded}",
                ])

                # Chaves com apenas o título (última opção, menos específica)
                chaves.extend([
                    f"titulo-{numero_titulo}",                 # Apenas título
                    # Apenas título sem .0
                    f"titulo-{numero_titulo_sem_ponto}",
                    # Apenas título com zeros à esquerda
                    f"titulo-{numero_titulo_padded}",
                ])

                dados_iptu = {
                    "data_consulta": data_consulta_str,
                    "pendencia": pendencia_str
                }

                # Armazenar com todas as chaves possíveis para garantir a correspondência
                for chave in chaves:
                    dados_iptu_processados[chave] = dados_iptu

                consultas_mes_vigente += 1

            log(f"✅ {consultas_mes_vigente} consultas IPTU encontradas e processadas")
            return dados_iptu_processados

        except Exception as e:
            log(f"❌ Erro ao carregar dados IPTU: {str(e)}")
            return {}

    def _normalizar_texto(self, texto: str) -> str:
        """Normaliza texto para facilitar comparação de chaves."""
        return re.sub(r"\s+", " ", (texto or "").strip().lower())

    def _criar_chaves_contrato(self, codigo_cliente: str, numero_titulo: str, lote: str = "") -> List[str]:
        """Gera variações de chaves para localizar contratos."""
        chaves = []

        codigo_cliente = str(codigo_cliente or "").strip()
        numero_titulo = str(numero_titulo or "").strip()
        lote = str(lote or "").strip()

        if not codigo_cliente or not numero_titulo:
            return chaves

        numero_titulo_norm = numero_titulo.replace(".0", "")
        numero_titulo_padded = numero_titulo_norm
        try:
            numero_int = int(float(numero_titulo_norm.replace(",", ".")))
            numero_titulo_padded = f"{numero_int:05d}"
        except (ValueError, TypeError):
            pass

        codigo_lower = codigo_cliente.lower()
        titulo_lower = numero_titulo_norm.lower()
        titulo_padded_lower = numero_titulo_padded.lower()

        if lote:
            lote_lower = lote.lower()
            chaves.extend([
                f"{codigo_cliente}-{lote}-{numero_titulo}",
                f"{codigo_cliente}-{lote}-{numero_titulo_norm}",
                f"{codigo_cliente}-{lote}-{numero_titulo_padded}",
                f"{codigo_lower}-{lote_lower}-{titulo_lower}",
                f"{codigo_lower}-{lote_lower}-{titulo_padded_lower}"
            ])

        chaves.extend([
            f"{codigo_cliente}-{numero_titulo}",
            f"{codigo_cliente}-{numero_titulo_norm}",
            f"{codigo_cliente}-{numero_titulo_padded}",
            f"{codigo_lower}-{titulo_lower}",
            f"{codigo_lower}-{titulo_padded_lower}",
            f"titulo-{numero_titulo_norm}",
            f"titulo-{numero_titulo_padded}"
        ])

        return chaves

    def _normalizar_mes_reajuste(self, valor: str) -> Optional[str]:
        """Normaliza valores da coluna 'Mês reajuste' para o formato MM/AAAA."""
        texto = str(valor).strip()
        if not texto:
            return None

        texto = unicodedata.normalize("NFKD", texto)
        texto = texto.encode("ascii", "ignore").decode("ascii")
        texto = texto.lower()
        texto = texto.replace(".", " ")
        texto = texto.replace("-", " ")
        texto = texto.replace("/", " ")
        texto = texto.replace("\\", " ")
        texto = texto.replace("_", " ")
        texto = re.sub(r"\s+", " ", texto).strip()
        if not texto:
            return None

        partes = texto.split(" ")
        if len(partes) < 2:
            return None

        mes_parte = partes[0]
        ano_parte = partes[1]

        if ano_parte.isdigit():
            if len(ano_parte) == 2:
                ano_parte = "20" + ano_parte
            elif len(ano_parte) == 4:
                pass
            else:
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
        if mes_parte in meses:
            mes = meses[mes_parte]
        elif chave_mes in meses:
            mes = meses[chave_mes]
        else:
            return None

        return f"{mes:02d}/{ano_parte}"

    def carregar_dados_base_calculo(self, mes_base: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Carrega e processa dados da planilha base de cálculo para acesso rápido."""
        if mes_base == getattr(self, "cache_base_calculo_mes", None) and self.cache_base_calculo is not None:
            return self.cache_base_calculo

        if not GOOGLE_SHEETS_DISPONIVEL:
            log("⚠️ Google Sheets não disponível - não será possível carregar a planilha base de cálculo")
            self.cache_base_calculo = {}
            self.cache_base_calculo_mes = mes_base
            return self.cache_base_calculo

        if not self.cliente_sheets and not self.conectar_google_sheets():
            self.cache_base_calculo = {}
            self.cache_base_calculo_mes = mes_base
            return self.cache_base_calculo

        planilha_calculo_id = os.getenv("PLANILHA_CALCULO_ID")
        if not planilha_calculo_id:
            log("⚠️ PLANILHA_CALCULO_ID não configurada - retornando dados vazios para base de cálculo")
            self.cache_base_calculo = {}
            self.cache_base_calculo_mes = mes_base
            return self.cache_base_calculo

        try:
            log("🔄 Carregando planilha base de cálculo...")
            planilha = self.cliente_sheets.open_by_key(planilha_calculo_id)
            aba = planilha.worksheet("Base de cálculo")
            registros = aba.get_all_records()

            log(
                f"📊 Total de registros base de cálculo carregados: {len(registros)}")

            total_registros = len(registros)
            registros_processados = 0
            dados_processados: Dict[str, Dict[str, Any]] = {}
            mes_base_normalizado = self._normalizar_mes_reajuste(
                mes_base) if mes_base else None
            for linha in registros:
                colunas_brutas = {(coluna or "").strip()                                  : valor for coluna, valor in linha.items()}
                colunas_normalizadas = {self._normalizar_texto(
                    coluna): valor for coluna, valor in colunas_brutas.items()}

                if mes_base_normalizado:
                    valor_mes_reajuste = colunas_brutas.get(
                        "Mês reajuste") or colunas_brutas.get("Mes reajuste")
                    valor_normalizado = self._normalizar_mes_reajuste(
                        valor_mes_reajuste)
                    if valor_normalizado != mes_base_normalizado:
                        continue

                codigo_cliente = str(linha.get("Código Cliente", "")).strip()
                titulo = str(linha.get("Titulo", "")).strip()
                lote = str(linha.get("Lote", "")).strip()

                if not codigo_cliente or not titulo:
                    continue

                chaves = self._criar_chaves_contrato(
                    codigo_cliente, titulo, lote)
                if not chaves:
                    continue

                registro_processado = {
                    "brutas": colunas_brutas,
                    "normalizadas": colunas_normalizadas
                }

                for chave in chaves:
                    dados_processados[chave] = registro_processado

                registros_processados += 1

            self.cache_base_calculo = dados_processados
            self.cache_base_calculo_mes = mes_base
            log(
                f"✅ Cache da base de cálculo preparado com {len(dados_processados)} chaves (registros válidos: {registros_processados} de {total_registros})")
            return self.cache_base_calculo

        except Exception as e:
            log(f"❌ Erro ao carregar planilha base de cálculo: {str(e)}")
            self.cache_base_calculo = {}
            self.cache_base_calculo_mes = mes_base
            return self.cache_base_calculo

    def obter_dados_base_calculo(self, codigo_cliente: str, numero_titulo: str, mes_base: Optional[str] = None) -> Optional[Dict[str, Dict[str, Any]]]:
        """Retorna o registro da planilha base de cálculo para o contrato informado."""
        cache = self.carregar_dados_base_calculo(mes_base=mes_base)
        if not cache:
            return None

        chaves = self._criar_chaves_contrato(codigo_cliente, numero_titulo)
        for chave in chaves:
            if chave in cache:
                log(
                    f"🔍 Base de cálculo localizada para cliente {codigo_cliente} e título {numero_titulo}")
                return cache[chave]

        log(
            f"⚠️ Base cálculo não encontrada para contrato {codigo_cliente}-{numero_titulo}")
        return None

    def _obter_valor_coluna_base(self, registro_base: Dict[str, Dict[str, Any]], *nomes_possiveis: str) -> str:
        """Obtém valores de colunas da planilha base considerando variações de nomes."""
        if not registro_base:
            return ""

        brutas = registro_base.get("brutas", {})
        normalizadas = registro_base.get("normalizadas", {})

        for nome in nomes_possiveis:
            if nome in brutas and brutas[nome] not in (None, ""):
                return str(brutas[nome]).strip()
            normalizado = self._normalizar_texto(nome)
            if normalizado in normalizadas and normalizadas[normalizado] not in (None, ""):
                return str(normalizadas[normalizado]).strip()

        return ""

    def _parse_data_flex(self, valor: str) -> Optional[datetime]:
        """Converte string em data tentando múltiplos formatos comuns."""
        if not valor:
            return None

        valor = valor.strip()
        if not valor:
            return None

        formatos = [
            "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y",
            "%d.%m.%Y", "%d.%m.%y"
        ]

        for formato in formatos:
            try:
                return datetime.strptime(valor, formato)
            except ValueError:
                continue

        # Caso a célula traga apenas dia (ex: "20")
        if valor.isdigit():
            dia = int(valor)
            if 1 <= dia <= 31:
                hoje = datetime.now()
                return datetime(hoje.year, hoje.month, dia)

        return None

    def extrair_dia_primeiro_vencimento_planilha(self, registro_base: Dict[str, Dict[str, Any]]) -> Optional[int]:
        """Extrai o dia do primeiro vencimento configurado na planilha base de cálculo."""
        valor = self._obter_valor_coluna_base(
            registro_base,
            "1 º vencimento",
            "1º vencimento",
            "1º vencimento carnê",
            "1º vencimento carne",
            "1o vencimento",
            "primeiro vencimento"
        )

        if not valor:
            return None

        data = self._parse_data_flex(valor)
        if data:
            return data.day

        try:
            dia = int(valor)
            if 1 <= dia <= 31:
                return dia
        except ValueError:
            pass

        log(f"⚠️ Não foi possível interpretar '1 º vencimento': '{valor}'")
        return None

    def extrair_dia_aniversario_planilha(self, registro_base):
        """Extrai o dia de aniversário da planilha base."""

        valor = self._obter_valor_coluna_base(
            registro_base,
            "Assinatura ultimo Contrato",
            "Assinatura último Contrato",
            "Assinatura",
        )
        data = self._parse_data_flex(valor)
        if data:
            return data.day

        if valor and valor.isdigit():
            dia = int(valor)
            if 1 <= dia <= 31:
                return dia

        return None

    def extrair_tipo_reajuste_planilha(self, registro_base: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """Obtém o tipo de reajuste configurado na planilha base para o contrato."""
        valor = self._obter_valor_coluna_base(
            registro_base,
            "Tipo reajuste",
            "Tipo de reajuste",
            "Tipo do reajuste",
            "Reajuste"
        )

        if not valor:
            return None

        valor_normalizado = self._normalizar_texto(valor)

        if "anivers" in valor_normalizado:
            return "aniversario"
        if "anual" in valor_normalizado:
            return "anual"

        log(f"⚠️ Tipo de reajuste desconhecido na planilha: '{valor}'")
        return None

    def _extrair_tipo_reajuste_relatorio(self, df_contrato: pd.DataFrame) -> Optional[str]:
        """Identifica o tipo de reajuste diretamente do relatório Sienge."""
        colunas_prioridade = [
            "Tipo reajuste",
            "Tipo de reajuste",
            "Tipo do reajuste",
            "Tipo de Reajuste",
            "Reajuste"
        ]

        for coluna in colunas_prioridade:
            if coluna in df_contrato.columns:
                valor = str(df_contrato[coluna].iloc[0]).strip().lower()
                if "anivers" in valor:
                    return "aniversario"
                if "anual" in valor:
                    return "anual"

        for coluna in df_contrato.columns:
            if "tipo" in coluna.lower() and "reajuste" in coluna.lower():
                valor = str(df_contrato[coluna].iloc[0]).strip().lower()
                if "anivers" in valor:
                    return "aniversario"
                if "anual" in valor:
                    return "anual"

        for coluna in df_contrato.columns:
            if "mês" in coluna.lower() and "reajuste" in coluna.lower():
                valor = str(df_contrato[coluna].iloc[0]).strip().lower()
                if "anivers" in valor:
                    return "aniversario"

        return None

    def atualizar_dados_iptu_batch(self, contratos_processados: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Atualiza os dados de IPTU para uma lista de contratos processados.
        Carrega todos os dados de IPTU de uma vez e faz a correspondência localmente.

        Args:
            contratos_processados: Lista de contratos processados

        Returns:
            Lista atualizada de contratos processados
        """
        if not GOOGLE_SHEETS_DISPONIVEL:
            log("⚠️ Google Sheets não disponível - pulando atualização de IPTU")
            return contratos_processados

        if not contratos_processados:
            log("ℹ️ Nenhum contrato para atualizar dados de IPTU")
            return contratos_processados

        log("🔄 Atualizando dados de IPTU para todos os contratos...")

        # Carregar todos os dados de IPTU de uma vez só
        dados_iptu_cache = self.carregar_todos_dados_iptu()

        if not dados_iptu_cache:
            log("⚠️ Nenhum dado de IPTU disponível - contratos não serão atualizados")
            return contratos_processados

        # Processar cada contrato usando o cache local
        atualizados = 0
        sem_dados = 0

        for contrato in contratos_processados:
            codigo_cliente = str(contrato.get("Código Cliente", "")).strip()
            numero_titulo = str(contrato.get("Titulo", "")).strip()

            if codigo_cliente and numero_titulo:
                # Normalizar os dados para garantir correspondência
                codigo_cliente_norm = codigo_cliente.strip().lower()
                numero_titulo_norm = numero_titulo.strip().lower()

                # Remover o .0 do número do título
                numero_titulo_sem_ponto = numero_titulo_norm.replace('.0', '')

                # Adicionar versões com zeros à esquerda (para números como "123" vs "00123")
                try:
                    numero_titulo_int = int(
                        float(numero_titulo_norm.replace(',', '.')))
                    # 5 dígitos com zeros à esquerda
                    numero_titulo_padded = f"{numero_titulo_int:05d}"
                except (ValueError, TypeError):
                    numero_titulo_padded = numero_titulo_norm

                # Tentar várias chaves possíveis para encontrar os dados de IPTU
                chaves_possiveis = []

                # Obter o lote do contrato, se disponível
                lote = ""
                for campo in ["Lote", "lote"]:
                    if campo in contrato and contrato[campo]:
                        lote = str(contrato[campo]).strip()
                        break

                # Chaves com código_cliente, lote e título (mais específicas)
                if lote:
                    lote_norm = lote.strip().lower()
                    chaves_possiveis.extend([
                        # Formato original
                        f"{codigo_cliente}-{lote}-{numero_titulo}",
                        # Sem .0
                        f"{codigo_cliente}-{lote}-{numero_titulo_sem_ponto}",
                        # Normalizado
                        f"{codigo_cliente_norm}-{lote_norm}-{numero_titulo_norm}",
                        # Normalizado sem .0
                        f"{codigo_cliente_norm}-{lote_norm}-{numero_titulo_sem_ponto}",
                        # Com zeros à esquerda
                        f"{codigo_cliente}-{lote}-{numero_titulo_padded}",
                        # Normalizado com zeros à esquerda
                        f"{codigo_cliente_norm}-{lote_norm}-{numero_titulo_padded}",
                    ])

                # Chaves com código_cliente e título (segunda prioridade)
                chaves_possiveis.extend([
                    # Formato original
                    f"{codigo_cliente}-{numero_titulo}",
                    f"{codigo_cliente}-{numero_titulo_sem_ponto}",        # Sem .0
                    # Normalizado
                    f"{codigo_cliente_norm}-{numero_titulo_norm}",
                    # Normalizado sem .0
                    f"{codigo_cliente_norm}-{numero_titulo_sem_ponto}",
                    # Com zeros à esquerda
                    f"{codigo_cliente}-{numero_titulo_padded}",
                    # Normalizado com zeros à esquerda
                    f"{codigo_cliente_norm}-{numero_titulo_padded}",
                ])

                # Chaves com apenas o título (última opção, menos específica)
                chaves_possiveis.extend([
                    f"titulo-{numero_titulo}",                 # Apenas título
                    # Apenas título sem .0
                    f"titulo-{numero_titulo_sem_ponto}",
                    # Apenas título com zeros à esquerda
                    f"titulo-{numero_titulo_padded}",
                ])

                # Log para debug
                log(
                    f"🔍 DEBUG BUSCA IPTU: Contrato {codigo_cliente}-{numero_titulo}")

                # Tentar encontrar dados de IPTU com alguma das chaves
                dados_iptu = {"data_consulta": "", "pendencia": ""}
                chave_encontrada = None

                for chave in chaves_possiveis:
                    if chave in dados_iptu_cache:
                        dados_iptu = dados_iptu_cache[chave]
                        chave_encontrada = chave
                        log(
                            f"✅ IPTU correspondente encontrado com chave '{chave}'")
                        break

                # Atualizar o contrato com os dados encontrados
                contrato["Data de consulta IPTU"] = dados_iptu.get(
                    "data_consulta", "")
                contrato["PENDENCIAS PMFI"] = dados_iptu.get("pendencia", "")

                # Verificar se encontramos dados de IPTU
                if chave_encontrada:
                    atualizados += 1
                    if contrato.get("PENDENCIAS SIENGE") == "OK" and not dados_iptu.get("pendencia"):
                        log(f"✅ Contrato {codigo_cliente}-{numero_titulo} sem pendências IPTU e SIENGE")
                    else:
                        log(
                            f"ℹ️ IPTU atualizado para {codigo_cliente}-{numero_titulo}: data='{dados_iptu.get('data_consulta')}', pendência='{dados_iptu.get('pendencia')}'"
                        )
                else:
                    sem_dados += 1
                    log(
                        f"⚠️ Sem dados IPTU para contrato {codigo_cliente}-{numero_titulo}")

        log(f"📊 Estatísticas de atualização IPTU:")
        log(f"   ✅ {atualizados} contratos atualizados com dados IPTU")
        log(f"   ⚠️ {sem_dados} contratos sem dados IPTU correspondentes")

        return contratos_processados

    def listar_arquivos_relatorios(self, dias_recentes: int = None) -> List[Path]:
        """
        Lista os arquivos de relatório, filtrando por data se solicitado
        e retornando apenas o arquivo mais recente para cada código de cliente
        """
        if not os.path.exists(self.diretorio_relatorios):
            log(
                f"❌ Diretório de relatórios não encontrado: {self.diretorio_relatorios}")
            return []

        arquivos = list(self.diretorio_relatorios.glob("sienge_*.xlsx"))

        # Filtrar por data de modificação se solicitado
        if dias_recentes:
            data_limite = datetime.now() - timedelta(days=dias_recentes)
            arquivos = [
                arquivo for arquivo in arquivos
                if datetime.fromtimestamp(arquivo.stat().st_mtime) >= data_limite
            ]

        # Ordenar por data de modificação (mais recentes primeiro)
        arquivos.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        arquivos_por_cliente = {}
        for arquivo in arquivos:
            codigo_cliente = self.extrair_codigo_cliente_arquivo(arquivo)
            if codigo_cliente and codigo_cliente not in arquivos_por_cliente:
                arquivos_por_cliente[codigo_cliente] = arquivo

        return list(arquivos_por_cliente.values())

    def carregar_relatorio(self, caminho_arquivo: Path) -> Optional[pd.DataFrame]:
        """Carrega um relatório do Sienge em formato Excel"""
        try:
            df = pd.read_excel(caminho_arquivo)
            return df
        except Exception as e:
            log(f"❌ Erro ao carregar relatório {caminho_arquivo}: {str(e)}")
            return None

    def extrair_dia_vencimento(self, df: pd.DataFrame) -> Optional[int]:
        """
        Extrai o dia de vencimento das parcelas conforme PDD (linhas 246-250).
        Filtra parcelas "A vencer" e extrai o dia da data de vencimento.
        """
        # Filtrar parcelas a vencer do tipo CT
        parcelas_a_vencer = df[
            (df["Status da parcela"] == "A vencer") &
            (df["Documento"] == "CT")
        ]

        if parcelas_a_vencer.empty:
            return None

        # Verificar a data de vencimento da primeira parcela
        for _, parcela in parcelas_a_vencer.iterrows():
            try:
                data_str = parcela["Data vencimento"]
                data = pd.to_datetime(data_str, format="%d/%m/%Y")
                return data.day
            except:
                continue

        return None

    def calcular_primeiro_vencimento(self, dia_vencimento: int, mes_base: str,
                                     tipo_reajuste: str, dia_aniversario: int) -> str:
        """
        Calcula o primeiro vencimento conforme regras do PDD (linhas 252-264).

        Args:
            dia_vencimento: Dia do mês para vencimento
            mes_base: Mês/ano base do reparcelamento (MM/AAAA)
            tipo_reajuste: "anual" ou "aniversario"
            dia_aniversario: Dia do mês em que o contrato foi assinado

        Returns:
            Data do primeiro vencimento no formato DD/MM/AAAA
        """
        # Extrair mês e ano do mês base
        mes, ano = mes_base.split('/')
        mes_num = int(mes)
        ano_num = int(ano)

        # Para tipo Reajuste Anual: 1º vencimento no mesmo mês base
        if tipo_reajuste.lower() == "anual":
            return f"{dia_vencimento:02d}/{mes_num:02d}/{ano_num}"

        # Para tipo Reajuste Aniversário: depende se vencimento cai antes ou depois do aniversário
        elif tipo_reajuste.lower() == "aniversario":
            # Se o vencimento é antes do aniversário, vencimento inicial é no mês seguinte
            if dia_vencimento < dia_aniversario:
                mes_vencimento = mes_num + 1
                ano_vencimento = ano_num

                # Ajuste para caso o mês seja 13 (janeiro do próximo ano)
                if mes_vencimento > 12:
                    mes_vencimento = 1
                    ano_vencimento += 1

                return f"{dia_vencimento:02d}/{mes_vencimento:02d}/{ano_vencimento}"
            else:
                # Se o vencimento é após ou igual ao aniversário, vencimento é no mesmo mês base
                return f"{dia_vencimento:02d}/{mes_num:02d}/{ano_num}"

        # Caso padrão (se tipo inválido): usar regra do reajuste anual
        return f"{dia_vencimento:02d}/{mes_num:02d}/{ano_num}"

    def contar_parcelas_a_vencer(self, df: pd.DataFrame, mes_base: str,
                                 tipo_reajuste: str, dia_vencimento: int,
                                 dia_aniversario: int) -> int:
        """
        Conta as parcelas a vencer conforme regras do PDD (linhas 281-298).

        Args:
            df: DataFrame do relatório
            mes_base: Mês/ano base do reparcelamento (MM/AAAA)
            tipo_reajuste: "anual" ou "aniversario"
            dia_vencimento: Dia do mês para vencimento
            dia_aniversario: Dia do mês em que o contrato foi assinado

        Returns:
            Número de parcelas a vencer
        """
        # Filtrar parcelas a vencer do tipo CT
        parcelas_a_vencer = df[
            (df["Status da parcela"] == "A vencer") &
            (df["Documento"] == "CT")
        ]

        if parcelas_a_vencer.empty:
            return 0

        # Extrair mês e ano do mês base
        mes_base_num = int(mes_base.split('/')[0])
        ano_base_num = int(mes_base.split('/')[1])
        data_base = datetime(ano_base_num, mes_base_num, 1)

        # Definir a data a partir da qual contar as parcelas
        if tipo_reajuste.lower() == "anual":
            # Contar parcelas a partir do mês de reparcelamento
            data_inicial = data_base
        else:  # aniversário
            if dia_vencimento < dia_aniversario:
                # Contar parcelas a partir do mês seguinte ao mês de reparcelamento
                # Aproximação para mês seguinte
                data_inicial = data_base + timedelta(days=31)
                data_inicial = datetime(
                    data_inicial.year, data_inicial.month, 1)
            else:
                # Contar parcelas a partir do mês de reparcelamento
                data_inicial = data_base

        # Contar parcelas com vencimento >= data_inicial
        contador = 0
        for _, parcela in parcelas_a_vencer.iterrows():
            try:
                data_vencimento = pd.to_datetime(
                    parcela["Data vencimento"], format="%d/%m/%Y")
                if data_vencimento >= data_inicial:
                    contador += 1
            except:
                continue

        return contador

    def verificar_inadimplencia(self, df: pd.DataFrame, primeiro_vencimento: str) -> Tuple[bool, str]:
        """
        Verifica inadimplência conforme regras do PDD (linhas 300-306).
        Identifica parcelas vencidas do tipo CT com mais de 60 dias antes do 1º vencimento.

        Returns:
            Tupla (tem_inadimplencia, mensagem)
        """
        try:
            data_primeiro_vencimento = pd.to_datetime(
                primeiro_vencimento, format="%d/%m/%Y")
            data_limite = data_primeiro_vencimento - timedelta(days=60)

            # Filtrar parcelas vencidas do tipo CT
            parcelas_vencidas = df[
                (df["Status da parcela"] == "Vencida") &
                (df["Documento"] == "CT")
            ]

            if parcelas_vencidas.empty:
                return False, ""

            # Verificar se alguma parcela está vencida há mais de 60 dias
            for _, parcela in parcelas_vencidas.iterrows():
                try:
                    data_vencimento = pd.to_datetime(
                        parcela["Data vencimento"], format="%d/%m/%Y")
                    if data_vencimento <= data_limite:
                        return True, "Inadimplência"
                except:
                    continue

            return False, ""

        except Exception as e:
            log(f"❌ Erro ao verificar inadimplência: {str(e)}")
            return False, ""

    def verificar_outras_pendencias(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Verifica outras pendências conforme regras do PDD (linhas 307-310).
        Identifica parcelas vencidas do tipo REC ou FAT.

        Returns:
            Tupla (tem_outras_pendencias, mensagem)
        """
        # Filtrar parcelas vencidas do tipo REC ou FAT
        parcelas_outras = df[
            (df["Status da parcela"] == "Vencida") &
            (df["Documento"].isin(["REC", "FAT"]))
        ]

        if not parcelas_outras.empty:
            return True, "Pendências Sienge"

        return False, ""

    def extrair_valor_parcela_base(self, df: pd.DataFrame, usar_valor_corrigido: bool) -> Optional[float]:
        """
        Extrai o valor da parcela base conforme PDD (linhas 267-273).

        Args:
            df: DataFrame do relatório
            usar_valor_corrigido: Se True, usa o "Valor Corrigido", caso contrário usa "Valor original"

        Returns:
            Valor da parcela base ou None se não encontrado
        """
        # Filtrar parcelas a vencer do tipo CT
        parcelas_a_vencer = df[
            (df["Status da parcela"] == "A vencer") &
            (df["Documento"] == "CT")
        ]

        if parcelas_a_vencer.empty:
            return None

        # Pegar o valor da primeira parcela a vencer
        primeira_parcela = parcelas_a_vencer.iloc[0]
        campo = "Valor corrigido" if usar_valor_corrigido else "Valor original"

        if campo in primeira_parcela:
            return primeira_parcela[campo]

        return None

    def extrair_dados_iptu_planilha(self, registro_base):
        """Extrai campos de IPTU e pendências diretamente da planilha base."""

        data_iptu = self._obter_valor_coluna_base(
            registro_base,
            "Data de consulta IPTU",
            "Data consulta IPTU",
            "Data Consulta IPTU",
            "Data consulta  IPTU",
        )

        pendencia_pmfi = self._obter_valor_coluna_base(
            registro_base,
            "PENDENCIAS PMFI",
            "Pendencias PMFI",
            "Pendência PMFI",
        )

        pendencia_sienge_inad = self._obter_valor_coluna_base(
            registro_base,
            "PENDENCIAS SIENGE INAD",
            "Pendencias Sienge Inad",
            "Pendências Sienge Inad",
        )

        return {
            "Data de consulta IPTU": data_iptu,
            "PENDENCIAS PMFI": pendencia_pmfi,
            "PENDENCIAS SIENGE INAD": pendencia_sienge_inad,
        }

    async def processar_relatorio(
        self,
        codigo_cliente: str,
        numero_titulo: str,
        df: pd.DataFrame,
        mes_base: str,
        tipo_reajuste: Optional[str] = None,
        dia_aniversario: int = 1
    ) -> Dict[str, Any]:
        """
        Processa o relatório de um contrato e extrai todas as informações relevantes.

        Args:
            codigo_cliente: Código do cliente
            numero_titulo: Número do título (contrato)
            df: DataFrame do relatório
            mes_base: Mês/ano base do reparcelamento (MM/AAAA)
            tipo_reajuste: Tipo de reajuste ("anual" ou "aniversario")
            dia_aniversario: Dia do mês em que o contrato foi assinado

        Returns:
            Dicionário com o resultado do processamento
        """
        # Filtrar DataFrame para o título específico
        # Preferir comparação de strings para evitar problemas com formato ".0"
        if "Título" in df.columns:
            # Converter todos os valores para string para comparação consistente
            df_contrato = df[df["Título"].astype(
                str).str.strip() == str(numero_titulo).strip()]
        else:
            df_contrato = df

        if df_contrato.empty:
            return {
                "sucesso": False,
                "erro": f"Contrato {codigo_cliente}-{numero_titulo} não encontrado no relatório"
            }

        # Extrair informações do contrato do relatório
        try:
            # Extrair nome do cliente
            nome_cliente = df_contrato["Cliente"].iloc[0] if "Cliente" in df_contrato.columns else "Desconhecido"

            # Extrair dia de vencimento
            dia_vencimento = self.extrair_dia_vencimento(df_contrato)
            if not dia_vencimento:
                return {
                    "sucesso": False,
                    "erro": "Não foi possível extrair o dia de vencimento"
                }

            fonte_dia_vencimento = "relatorio"
            fonte_dia_aniversario = "parametro"

            # Determinar o tipo de reajuste efetivamente usado para este contrato
            tipo_reajuste_usado = ""
            fonte_tipo_reajuste = "desconhecido"

            # Carregar dados da planilha base de cálculo para complementar informações
            registro_base = self.obter_dados_base_calculo(
                codigo_cliente, numero_titulo, mes_base)

            if registro_base:
                tipo_reajuste_planilha = normalizar_tipo_reajuste(
                    self.extrair_tipo_reajuste_planilha(registro_base))
                if tipo_reajuste_planilha:
                    log(
                        f"🔄 Tipo de reajuste (planilha): {tipo_reajuste_planilha}")
                    tipo_reajuste_usado = tipo_reajuste_planilha
                    fonte_tipo_reajuste = "planilha"

                dia_vencimento_planilha = self.extrair_dia_primeiro_vencimento_planilha(
                    registro_base)
                if dia_vencimento_planilha:
                    log(
                        f"📅 Dia do 1º vencimento (planilha): {dia_vencimento_planilha}")
                    dia_vencimento = dia_vencimento_planilha
                    fonte_dia_vencimento = "planilha"

                dia_aniversario_planilha = self.extrair_dia_aniversario_planilha(
                    registro_base)
                if dia_aniversario_planilha:
                    log(
                        f"🎂 Dia de aniversário (planilha): {dia_aniversario_planilha}")
                    dia_aniversario = dia_aniversario_planilha
                    fonte_dia_aniversario = "planilha"

                dados_iptu_planilha = self.extrair_dados_iptu_planilha(
                    registro_base)

            if not tipo_reajuste_usado:
                tipo_reajuste_relatorio = normalizar_tipo_reajuste(
                    self._extrair_tipo_reajuste_relatorio(df_contrato))
                if tipo_reajuste_relatorio:
                    log(
                        f"📄 Tipo de reajuste (relatório): {tipo_reajuste_relatorio}")
                    tipo_reajuste_usado = tipo_reajuste_relatorio
                    fonte_tipo_reajuste = "relatorio"

            if not tipo_reajuste_usado and tipo_reajuste:
                tipo_reajuste_usado = normalizar_tipo_reajuste(tipo_reajuste)
                fonte_tipo_reajuste = "parametro"

            if not tipo_reajuste_usado:
                return {
                    "sucesso": False,
                    "erro": "Tipo de reajuste não identificado na planilha base ou no relatório"
                }

            if tipo_reajuste_usado not in {"anual", "aniversario"}:
                return {
                    "sucesso": False,
                    "erro": f"Tipo de reajuste desconhecido: {tipo_reajuste_usado}"
                }

            log(
                f"✅ Tipo de reajuste identificado: {tipo_reajuste_usado} (cliente {codigo_cliente}-{numero_titulo})")

            # Calcular o primeiro vencimento
            primeiro_vencimento = self.calcular_primeiro_vencimento(
                dia_vencimento=dia_vencimento,
                mes_base=mes_base,
                tipo_reajuste=tipo_reajuste_usado,
                dia_aniversario=dia_aniversario
            )

            log(
                f"🧮 Memória de cálculo 1º vencimento {codigo_cliente}-{numero_titulo}: "
                f"tipo={tipo_reajuste_usado}/{fonte_tipo_reajuste}; "
                f"dia_venc={dia_vencimento}/{fonte_dia_vencimento}; "
                f"dia_aniv={dia_aniversario}/{fonte_dia_aniversario}; "
                f"resultado={primeiro_vencimento}")

            # Contar parcelas a vencer conforme regra específica do PDD
            parcelas_a_vencer = self.contar_parcelas_a_vencer(
                df=df_contrato,
                mes_base=mes_base,
                tipo_reajuste=tipo_reajuste_usado,
                dia_vencimento=dia_vencimento,
                dia_aniversario=dia_aniversario
            )

            # Verificar inadimplência
            tem_inadimplencia, msg_inadimplencia = self.verificar_inadimplencia(
                df=df_contrato,
                primeiro_vencimento=primeiro_vencimento
            )

            status_inadimplencia = "com inadimplência" if tem_inadimplencia else "sem inadimplência"
            if msg_inadimplencia:
                log(
                    f"🔎 Inadimplência {codigo_cliente}-{numero_titulo}: {status_inadimplencia} | {msg_inadimplencia}"
                )
            else:
                log(
                    f"🔎 Inadimplência {codigo_cliente}-{numero_titulo}: {status_inadimplencia}"
                )

            # Verificar outras pendências
            tem_outras_pendencias, msg_outras_pendencias = self.verificar_outras_pendencias(
                df_contrato)

            status_outras = "com outras pendências" if tem_outras_pendencias else "sem outras pendências"
            if msg_outras_pendencias:
                log(
                    f"🧾 Pendências adicionais {codigo_cliente}-{numero_titulo}: {status_outras} | {msg_outras_pendencias}"
                )
            else:
                log(
                    f"🧾 Pendências adicionais {codigo_cliente}-{numero_titulo}: {status_outras}"
                )

            # Extrair valor da parcela base (tentar original primeiro, depois corrigido)
            valor_parcela_original = self.extrair_valor_parcela_base(
                df_contrato, False)
            valor_parcela_corrigido = self.extrair_valor_parcela_base(
                df_contrato, True)

            # Montar resultado com todos os dados extraídos
            resultado = {
                "sucesso": True,
                "codigo_cliente": codigo_cliente,
                "numero_titulo": numero_titulo,
                "nome_cliente": nome_cliente,
                "dados_extraidos": {
                    "dia_vencimento": dia_vencimento,
                    "primeiro_vencimento": primeiro_vencimento,
                    "parcelas_a_vencer": parcelas_a_vencer,
                    "valor_parcela_original": valor_parcela_original,
                    "valor_parcela_corrigido": valor_parcela_corrigido,
                    "tem_inadimplencia": tem_inadimplencia,
                    "tem_outras_pendencias": tem_outras_pendencias,
                    "mensagem_inadimplencia": msg_inadimplencia,
                    "mensagem_outras_pendencias": msg_outras_pendencias,
                    "tipo_reajuste_usado": tipo_reajuste_usado
                }
            }

            if dados_iptu_planilha:
                dados = resultado["dados_extraidos"]
                if not dados.get("data_consulta_iptu") and dados_iptu_planilha.get("Data de consulta IPTU"):
                    dados["data_consulta_iptu"] = dados_iptu_planilha["Data de consulta IPTU"]
                if not dados.get("pendencias_pmfi") and dados_iptu_planilha.get("PENDENCIAS PMFI"):
                    dados["pendencias_pmfi"] = dados_iptu_planilha["PENDENCIAS PMFI"]
                if not dados.get("pendencias_sienge_inad") and dados_iptu_planilha.get("PENDENCIAS SIENGE INAD"):
                    dados["pendencias_sienge_inad"] = dados_iptu_planilha["PENDENCIAS SIENGE INAD"]

            return resultado

        except Exception as e:
            log(f"❌ Erro ao processar relatório: {str(e)}")
            return {
                "sucesso": False,
                "erro": str(e)
            }

    async def processar_arquivos(self, dias_recentes: int = None,
                                 max_arquivos: int = None,
                                 mes_base: str = "10/2025",
                                 tipo_reajuste: str = "anual",
                                 dia_aniversario: int = 1,
                                 ignorar_nan: bool = False) -> Dict[str, Any]:
        """
        Processa os arquivos de relatório e gera dados para atualização.

        Args:
            dias_recentes: Filtrar por arquivos dos últimos X dias
            max_arquivos: Número máximo de arquivos a processar
            mes_base: Mês/ano base do reparcelamento (MM/AAAA)
            tipo_reajuste: Tipo de reajuste para aplicar a todos os contratos
            dia_aniversario: Dia do aniversário para contratos tipo aniversário

        Returns:
            Estatísticas do processamento e dados processados
        """
        # Listar arquivos
        arquivos = self.listar_arquivos_relatorios(dias_recentes)

        if max_arquivos:
            arquivos = arquivos[:max_arquivos]

        if not arquivos:
            return {"sucesso": False, "erro": "Nenhum arquivo encontrado para processar"}

        log(f"🔄 Processando {len(arquivos)} arquivos para mês base {mes_base}...")

        # Estatísticas
        stats = {
            "arquivos_processados": 0,
            "contratos_processados": 0,
            "contratos_sucesso": 0,
            "erros": 0,
            "contratos_com_inadimplencia": 0,
            "contratos_com_outras_pendencias": 0
        }

        # Lista para armazenar dados processados de cada contrato
        contratos_processados = []

        # Processar arquivos
        for arquivo in arquivos:
            try:
                # Extrair código do cliente do nome do arquivo
                codigo_cliente = self.extrair_codigo_cliente_arquivo(arquivo)
                if not codigo_cliente:
                    log(
                        f"⚠️ Não foi possível extrair código do cliente do arquivo: {arquivo.name}")
                    stats["erros"] += 1
                    continue

                log(f"🔍 Processando arquivo: {arquivo.name} (Cliente: {codigo_cliente})")

                # Carregar relatório
                df = self.carregar_relatorio(arquivo)
                if df is None:
                    stats["erros"] += 1
                    continue

                # Identificar títulos (contratos) no relatório
                titulos = df["Título"].unique(
                ) if "Título" in df.columns else []

                # Cache da base para validar quais títulos devem ser processados
                cache_base = self.carregar_dados_base_calculo(
                    mes_base=mes_base)

                # Filtrar títulos NaN se solicitado
                if ignorar_nan:
                    titulos = [t for t in titulos if pd.notna(t)]

                if not len(titulos):
                    log(
                        f"⚠️ Nenhum título encontrado no relatório: {arquivo.name}")
                    stats["erros"] += 1
                    continue

                # Processar cada título do cliente
                for titulo in titulos:
                    if pd.isna(titulo) or str(titulo).strip() == "":
                        log(
                            f"ℹ️ Contrato com título vazio ignorado para cliente {codigo_cliente}")
                        continue

                    titulo_str = str(titulo).strip()
                    chaves_titulo = self._criar_chaves_contrato(
                        codigo_cliente,
                        titulo_str
                    )

                    possui_base = any(
                        chave in cache_base for chave in chaves_titulo
                    ) if cache_base else False

                    if not possui_base:
                        log(
                            f"ℹ️ Contrato {codigo_cliente}-{titulo_str} ignorado: ausente na planilha base de cálculo"
                        )
                        continue

                    stats["contratos_processados"] += 1

                    log(f"📄 Processando contrato {codigo_cliente}-{titulo_str}")

                    # Processar relatório
                    resultado = await self.processar_relatorio(
                        codigo_cliente=str(codigo_cliente),
                        numero_titulo=titulo_str,
                        df=df,
                        mes_base=mes_base,
                        tipo_reajuste=tipo_reajuste,
                        dia_aniversario=dia_aniversario
                    )

                    if resultado.get("sucesso", False):
                        stats["contratos_sucesso"] += 1
                        dados_contrato = resultado.get("dados_extraidos", {})

                        if dados_contrato.get("tem_inadimplencia", False):
                            stats["contratos_com_inadimplencia"] += 1

                        if dados_contrato.get("tem_outras_pendencias", False):
                            stats["contratos_com_outras_pendencias"] += 1

                        log(f"✅ {codigo_cliente}-{titulo}: "
                            f"1º vencimento={dados_contrato.get('primeiro_vencimento')}, "
                            f"{dados_contrato.get('parcelas_a_vencer')} parcelas, "
                            f"{'com' if dados_contrato.get('tem_inadimplencia') else 'sem'} inadimplência")

                        # Determinar status de pendências conforme PDD
                        # Se não houver pendências, colocar "OK" diretamente nos campos de pendência
                        # Conforme seção 10.2 do PDD: "Geração de carnê é realizada apenas para clientes com status OK nas colunas de Pendência"

                        # Inicializar campos de pendência com valores extraídos, quando existirem
                        pendencias_pmfi = dados_contrato.get(
                            "pendencias_pmfi", "")
                        pendencias_sienge_inad = dados_contrato.get(
                            "mensagem_inadimplencia", "")
                        pendencias_sienge = dados_contrato.get(
                            "mensagem_outras_pendencias", "")

                        # Se não houver pendências de Sienge, preencher o campo PENDENCIAS SIENGE com "OK"
                        if not (pendencias_sienge_inad or pendencias_sienge):
                            pendencias_sienge = "OK"

                        # Extrair o Lote, se disponível
                        lote = ""
                        try:
                            # Tentar encontrar o lote no relatório
                            if "Lote" in df.columns:
                                lote_series = df[df["Título"].astype(
                                    str).str.strip() == str(titulo).strip()]["Lote"]
                                if not lote_series.empty and not pd.isna(lote_series.iloc[0]):
                                    lote = str(lote_series.iloc[0]).strip()
                            elif "Quadra/Lote" in df.columns:
                                quadra_lote_series = df[df["Título"].astype(
                                    str).str.strip() == str(titulo).strip()]["Quadra/Lote"]
                                if not quadra_lote_series.empty and not pd.isna(quadra_lote_series.iloc[0]):
                                    # Tentar extrair o lote da coluna "Quadra/Lote" (formato comum: "Q1-L2")
                                    quadra_lote = str(
                                        quadra_lote_series.iloc[0]).strip()
                                    if "-" in quadra_lote:
                                        lote = quadra_lote.split(
                                            "-")[1].replace("L", "").strip()
                        except Exception as e:
                            log(
                                f"⚠️ Erro ao extrair lote para {codigo_cliente}-{titulo}: {str(e)}")

                        # Adicionar resultado à lista de contratos processados usando os mesmos nomes da planilha
                        # Remover o .0 do título se for o caso
                        titulo_limpo = str(titulo).replace('.0', '') if str(
                            titulo).endswith('.0') else str(titulo)

                        contratos_processados.append({
                            "Código Cliente": str(codigo_cliente),
                            "Titulo": titulo_limpo,
                            "Cliente": resultado.get("nome_cliente", ""),
                            "Data de consulta IPTU": dados_contrato.get(
                                "data_consulta_iptu", ""),
                            "PENDENCIAS PMFI": pendencias_pmfi,
                            "PENDENCIAS SIENGE INAD": pendencias_sienge_inad,
                            "PENDENCIAS SIENGE": pendencias_sienge,
                            "1º vencimento carnê": dados_contrato.get("primeiro_vencimento"),
                            "Parcelas a vencer": dados_contrato.get("parcelas_a_vencer"),
                            "Valor da Parcela Base": dados_contrato.get("valor_parcela_original"),
                            "_lote": lote,
                            "arquivo_origem": arquivo.name,
                            "dia_vencimento": dados_contrato.get("dia_vencimento"),
                            "valor_parcela_corrigido": dados_contrato.get("valor_parcela_corrigido"),
                            "tem_inadimplencia": dados_contrato.get("tem_inadimplencia", False),
                            "tem_outras_pendencias": dados_contrato.get("tem_outras_pendencias", False),
                            "tipo_reajuste_usado": dados_contrato.get("tipo_reajuste_usado", tipo_reajuste),
                            "data_processamento": datetime.now().isoformat()
                        })
                    else:
                        log(
                            f"❌ Falha ao processar {codigo_cliente}-{titulo}: {resultado.get('erro')}")
                        stats["erros"] += 1

                stats["arquivos_processados"] += 1

            except Exception as e:
                log(f"❌ Erro ao processar arquivo {arquivo.name}: {str(e)}")
                stats["erros"] += 1

        return {
            "sucesso": True,
            "estatisticas": stats,
            "contratos_processados": contratos_processados
        }


@dataclass
class ConfiguracaoProcessamento:
    """Estrutura fortemente tipada com os parâmetros de processamento."""

    dias: int = 30
    max_arquivos: Optional[int] = None
    mes_base: str = "10/2025"
    tipo_reajuste: Optional[str] = None
    dia_aniversario: int = 1
    salvar_csv: str = "resultados_processamento.csv"
    ignorar_nan: bool = False
    consultar_iptu: bool = True
    debug: bool = False


def interpretar_argumentos() -> ConfiguracaoProcessamento:
    """Interpreta os argumentos CLI e devolve configuração estruturada."""

    parser = argparse.ArgumentParser(
        description='Processamento e Atualização da Planilha Base de Cálculo',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--dias',
        type=int,
        default=30,
        help='Número de dias recentes para considerar (padrão: 30)'
    )

    parser.add_argument(
        '--max-arquivos',
        type=int,
        default=None,
        help='Número máximo de arquivos a processar (padrão: sem limite)'
    )

    parser.add_argument(
        '--mes-base',
        type=str,
        default="10/2025",
        help='Mês/ano base do reparcelamento no formato MM/AAAA (padrão: 10/2025)'
    )

    parser.add_argument(
        '--tipo-reajuste',
        type=str,
        choices=['auto', 'anual', 'aniversario'],
        default='auto',
        help='Tipo de reajuste padrão para todos os contratos (auto detecta via planilha)'
    )

    parser.add_argument(
        '--dia-aniversario',
        type=int,
        default=1,
        help='Dia do aniversário para contratos tipo aniversário (padrão: 1)'
    )

    parser.add_argument(
        '--salvar-csv',
        type=str,
        default='resultados_processamento.csv',
        help='Arquivo CSV para salvar os resultados em formato tabular'
    )

    parser.add_argument(
        '--ignorar-nan',
        action='store_true',
        help='Ignora contratos com título NaN (frequentemente linhas de soma/total)'
    )

    parser.add_argument(
        '--consultar-iptu',
        action='store_true',
        dest='consultar_iptu',
        default=True,
        help='Consulta dados de IPTU na planilha base de apoio (padrão: habilitado)'
    )
    parser.add_argument(
        '--nao-consultar-iptu',
        action='store_false',
        dest='consultar_iptu',
        help='Desativa a consulta de IPTU na planilha de apoio'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Ativar logs de debug adicionais'
    )

    args = parser.parse_args()

    return ConfiguracaoProcessamento(
        dias=args.dias,
        max_arquivos=args.max_arquivos,
        mes_base=args.mes_base,
        tipo_reajuste=None if args.tipo_reajuste in (
            None, 'auto') else args.tipo_reajuste,
        dia_aniversario=args.dia_aniversario,
        salvar_csv=args.salvar_csv,
        ignorar_nan=args.ignorar_nan,
        consultar_iptu=args.consultar_iptu,
        debug=args.debug,
    )


async def executar_processamento(config: ConfiguracaoProcessamento) -> int:
    """Executa a etapa de regras com base na configuração informada."""

    inicio = datetime.now()

    global DEBUG
    DEBUG = config.debug

    with captura_logs_em_arquivo():
        log("\n🔄 PROCESSAMENTO DE DADOS PARA PLANILHA BASE DE CÁLCULO")
        log("=" * 60)
        log(f"📅 Mês base do reparcelamento: {config.mes_base}")
        tipo_reajuste_parametro = normalizar_tipo_reajuste(
            config.tipo_reajuste)
        if tipo_reajuste_parametro:
            log(f"🔍 Tipo de reajuste padrão: {tipo_reajuste_parametro}")
        else:
            log("🔍 Tipo de reajuste: auto (detecção via planilha/relatório)")
        if tipo_reajuste_parametro == 'aniversario':
            log(f"📅 Dia do aniversário: {config.dia_aniversario}")
        log(f"📋 Processando relatórios dos últimos {config.dias} dias")

        if config.max_arquivos:
            log(f"📋 Limitado a {config.max_arquivos} arquivos")

        try:
            atualizador = AtualizadorPlanilhaBase()

            resultado = await atualizador.processar_arquivos(
                dias_recentes=config.dias,
                max_arquivos=config.max_arquivos,
                mes_base=config.mes_base,
                tipo_reajuste=tipo_reajuste_parametro,
                dia_aniversario=config.dia_aniversario,
                ignorar_nan=config.ignorar_nan
            )

            fim = datetime.now()
            duracao = fim - inicio

            if resultado["sucesso"]:
                contratos_processados = resultado["contratos_processados"]
                stats = resultado["estatisticas"]

                if config.consultar_iptu:
                    log("🔄 Atualizando dados de IPTU via planilha de apoio...")
                    os.environ["PLANILHA_APOIO_ID"] = "1Czt8Vy6f_3lG9RHM3bNkq0Yq1cv8VpByYtHVtRduX94"
                    os.environ["PLANILHA_CALCULO_ID"] = "1NTDPDEltum8X3vBHvUetCNWVEcz453FfAZGRYGmmd8U"
                    os.environ["GOOGLE_CREDENTIALS_PATH"] = "./credentials/gspread-459713-aab8a657f9b0.json"

                    contratos_processados = atualizador.atualizar_dados_iptu_batch(
                        contratos_processados)

                log("\n✅ PROCESSAMENTO DE DADOS CONCLUÍDO")
                log(f"⏱️ Duração: {duracao}")
                log(f"📄 Arquivos processados: {stats['arquivos_processados']}")
                log(f"📋 Contratos processados: {stats['contratos_processados']}")
                log(f"✅ Contratos com sucesso: {stats['contratos_sucesso']}")
                log(
                    f"⚠️ Contratos com inadimplência: {stats['contratos_com_inadimplencia']}")
                log(
                    f"⚠️ Contratos com outras pendências: {stats['contratos_com_outras_pendencias']}")
                log(f"❌ Erros: {stats['erros']}")

                contratos_anuais = 0
                contratos_aniversario = 0

                for contrato in contratos_processados:
                    tipo_reajuste_usado = contrato.get(
                        "tipo_reajuste_usado", "")
                    if tipo_reajuste_usado == "anual":
                        contratos_anuais += 1
                    elif tipo_reajuste_usado == "aniversario":
                        contratos_aniversario += 1

                stats["contratos_anuais"] = contratos_anuais
                stats["contratos_aniversario"] = contratos_aniversario

                csv_path = config.salvar_csv
                try:
                    estatisticas_execucao = {
                        "duracao": str(duracao),
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "mes_base": config.mes_base,
                        "tipo_reajuste": config.tipo_reajuste,
                        "dia_aniversario": config.dia_aniversario,
                        "estatisticas": stats,
                    }

                    # Persistir resumo básico em arquivo para rastreio
                    try:
                        resumo_path = Path("resultados_processamento.txt")
                        with open(resumo_path, "w") as resumo:
                            resumo.write("Resumo do processamento\n")
                            resumo.write(json.dumps(
                                estatisticas_execucao, indent=2, ensure_ascii=False))
                    except Exception as erro_resumo:
                        log(
                            f"⚠️ Não foi possível salvar resumo textual: {erro_resumo}")

                    if contratos_processados:
                        import csv
                        with open(csv_path, 'w', newline='') as f:
                            fieldnames = [
                                'Código Cliente', 'Titulo', 'Cliente',
                                'Data de consulta IPTU', 'PENDENCIAS PMFI', 'PENDENCIAS SIENGE INAD', 'PENDENCIAS SIENGE',
                                'Parcelas a vencer', 'Valor da Parcela Base',
                                '1º vencimento carnê'
                            ]

                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()

                            for contrato in contratos_processados:
                                row = {field: contrato.get(
                                    field, '') for field in fieldnames}
                                valor_base = row.get('Valor da Parcela Base')
                                if isinstance(valor_base, (int, float)):
                                    row['Valor da Parcela Base'] = f"{valor_base:,.2f}".replace(
                                        ',', 'X').replace('.', ',').replace('X', '.')
                                elif isinstance(valor_base, str) and valor_base.strip():
                                    try:
                                        valor_float = float(valor_base)
                                        row['Valor da Parcela Base'] = f"{valor_float:,.2f}".replace(
                                            ',', 'X').replace('.', ',').replace('X', '.')
                                    except ValueError:
                                        pass
                                writer.writerow(row)

                        log(
                            f"📝 Relatório em formato tabular salvo em {csv_path}")
                        log(f"📊 {len(contratos_processados)} contratos registrados no CSV")
                    else:
                        log("ℹ️ Nenhum contrato processado para gerar CSV")

                    anexos_email = []
                    if Path(csv_path).exists():
                        anexos_email.append(csv_path)
                    if ARQUIVO_LOG_ATUAL and Path(ARQUIVO_LOG_ATUAL).exists():
                        anexos_email.append(str(ARQUIVO_LOG_ATUAL))

                    resultados_email = {
                        "titulo": "✅ RPA Processar Regras Extração Sienge e Alimentação de Pendências - Execução Concluída",
                        "Arquivos processados": stats["arquivos_processados"],
                        "Contratos com sucesso": stats["contratos_sucesso"],
                        "Erros": stats["erros"],
                        "caminhos_anexos": anexos_email,
                        "relatorio": ""
                    }

                    enviados = False
                    if notificar_sucesso:
                        try:
                            enviados = notificar_sucesso(
                                nome_rpa="Processar Regras Extração Sienge e Alimentação de Pendências",
                                tempo_execucao=str(duracao),
                                resultados=resultados_email
                            )
                        except Exception as erro_envio:
                            log(
                                f"⚠️ Falha ao enviar notificação de sucesso: {erro_envio}")
                    else:
                        log("ℹ️ Sistema de notificações não configurado. Anexos preparados:")
                        for caminho in anexos_email:
                            log(f"   • {caminho}")

                    if enviados:
                        log("📧 Notificação de sucesso enviada com anexos")
                    else:
                        log("⚠️ Notificação de sucesso não foi enviada")

                except Exception as e:
                    log(
                        f"❌ Erro ao gerar CSV ou enviar notificações: {str(e)}")

                return 0
            else:
                log("\n❌ PROCESSAMENTO DE DADOS FALHOU")
                log(f"⏱️ Duração: {duracao}")
                log(f"❌ Erro: {resultado.get('erro', 'Erro desconhecido')}")

                notificar_erro_simples(
                    "❌ Processamento de dados falhou",
                    f"Erro: {resultado.get('erro', 'Erro desconhecido')} | Duração: {duracao}"
                )

                return 1

        except Exception as e:
            fim = datetime.now()
            duracao = fim - inicio

            log(f"\n💥 ERRO CRÍTICO: {str(e)}")
            log(f"⏱️ Duração: {duracao}")

            import traceback
            traceback.print_exc()

            notificar_erro_simples(
                "💥 Erro crítico no processamento de dados",
                f"Erro: {str(e)} | Duração: {duracao}"
            )

            return 1


async def main() -> int:
    """Função principal da CLI; retorna código de status."""

    config = interpretar_argumentos()
    return await executar_processamento(config)


if __name__ == "__main__":
    status = asyncio.run(main())
    sys.exit(status)
