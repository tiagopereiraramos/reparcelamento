#!/usr/bin/env python3
"""
Utilitários compartilhados para os mains do RPA Sienge
Funções comuns utilizadas por todos os módulos de processamento

Desenvolvido em Português Brasileiro
"""

import csv
import os
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from core.notificacoes_simples import notificar_sucesso, notificar_erro


def log(msg):
    """Loga mensagem com timestamp."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


CAMINHO_ARQUIVO_CONTAS = Path(__file__).resolve(
).parent.parent / "docs" / "empresas_contas_correntes.csv"
_CACHE_CONTAS_CORRENTES: Dict[str, str] = {}


def _normalizar_empresa(valor: str) -> str:
    """Normaliza nomes de empresa removendo acentos e padronizando caixa.

    Args:
        valor: Nome da empresa informado.

    Returns:
        Representação normalizada para comparação.
    """

    texto = unicodedata.normalize("NFKD", valor)
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return texto.strip().lower()


def _carregar_contas_correntes() -> Dict[str, str]:
    """Carrega o mapeamento de empresas para contas corrente de remessa.

    Returns:
        Dicionário onde a chave é o nome normalizado da empresa e o valor é a
        conta corrente correspondente.

    Raises:
        FileNotFoundError: Quando o arquivo CSV não está presente.
        ValueError: Se o arquivo estiver vazio ou com cabeçalho inválido.
    """

    if _CACHE_CONTAS_CORRENTES:
        return _CACHE_CONTAS_CORRENTES

    if not CAMINHO_ARQUIVO_CONTAS.exists():
        raise FileNotFoundError(
            f"Arquivo de contas corrente não encontrado: {CAMINHO_ARQUIVO_CONTAS}"
        )

    with CAMINHO_ARQUIVO_CONTAS.open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if not leitor.fieldnames or "EMPRESA" not in leitor.fieldnames or "CONTA CORRENTE REMESSA" not in leitor.fieldnames:
            raise ValueError(
                "Cabeçalho do CSV de contas corrente inválido. Esperado colunas 'EMPRESA' e 'CONTA CORRENTE REMESSA'."
            )

        for linha in leitor:
            empresa = linha.get("EMPRESA")
            conta = linha.get("CONTA CORRENTE REMESSA")
            if not empresa or not conta:
                continue
            chave = _normalizar_empresa(empresa)
            if chave and chave not in _CACHE_CONTAS_CORRENTES:
                _CACHE_CONTAS_CORRENTES[chave] = conta.strip()

    if not _CACHE_CONTAS_CORRENTES:
        raise ValueError(
            "CSV de contas corrente não possui registros válidos.")

    return _CACHE_CONTAS_CORRENTES


def obter_conta_corrente_remessa(nome_empresa: str) -> str:
    """Obtém a conta corrente de remessa associada a uma empresa.

    Args:
        nome_empresa: Nome da empresa conforme padronização do CSV.

    Returns:
        Texto da coluna "CONTA CORRENTE REMESSA" correspondente.

    Raises:
        ValueError: Se o nome informado for vazio ou a empresa não estiver no CSV.
        FileNotFoundError: Quando o arquivo de contas corrente não é encontrado.
    """

    if not nome_empresa or not nome_empresa.strip():
        raise ValueError(
            "Nome da empresa é obrigatório para obter a conta corrente de remessa."
        )

    contas = _carregar_contas_correntes()
    chave = _normalizar_empresa(nome_empresa)
    conta = contas.get(chave)

    if conta is None:
        raise ValueError(
            f"Empresa '{nome_empresa}' não localizada no mapeamento de contas corrente."
        )

    return conta


def sanitizar_nome_arquivo(nome: str) -> str:
    """
    Sanitiza nome para uso em arquivos, removendo caracteres especiais problemáticos.

    Args:
        nome: Nome original do cliente

    Returns:
        Nome sanitizado seguro para uso em nomes de arquivo
    """
    import re
    if not nome:
        return "CLIENTE_VAZIO"

    # ✅ CORREÇÃO: Substituir caracteres problemáticos por underscore
    # Remove/substitui: / \ : * ? " < > | e outros caracteres especiais
    nome_sanitizado = re.sub(r'[/\\:*?"<>|]', '_', nome)

    # Substituir espaços múltiplos e espaços por underscore
    nome_sanitizado = re.sub(r'\s+', '_', nome_sanitizado)

    # Remover underscores múltiplos consecutivos
    nome_sanitizado = re.sub(r'_+', '_', nome_sanitizado)

    # Remover underscores no início e fim
    nome_sanitizado = nome_sanitizado.strip('_')

    # Limitar tamanho para evitar nomes muito longos
    if len(nome_sanitizado) > 100:
        nome_sanitizado = nome_sanitizado[:100]

    return nome_sanitizado if nome_sanitizado else "CLIENTE_SANITIZADO"


def notificar_sucesso_simples(titulo: str, mensagem: str):
    """Notificação de sucesso via e-mail (padrão legado)"""
    notificar_sucesso(
        nome_rpa="RPA Sienge",
        tempo_execucao="-",
        resultados={
            "titulo": titulo,
            "mensagem": mensagem
        }
    )


def notificar_erro_simples(titulo: str, mensagem: str):
    """Notificação de erro via e-mail (padrão legado)"""
    notificar_erro(
        nome_rpa="RPA Sienge",
        erro=titulo,
        detalhes=mensagem
    )


def get_env_or_fail(var_name, default=None):
    """Obtém variável de ambiente ou encerra o programa se não definida."""
    value = os.getenv(var_name, default)
    if not value:
        log(f"ERRO: Variável de ambiente obrigatória não definida: {var_name}")
        sys.exit(1)
    return value


async def carregar_credenciais_sienge() -> Dict[str, str]:
    """Carrega e valida credenciais do Sienge das variáveis de ambiente."""
    log("🔑 Carregando credenciais do Sienge...")

    credenciais = {
        "url": get_env_or_fail("SIENGE_URL", "https://jmservicos.sienge.com.br/sienge/8/index.html"),
        "usuario": get_env_or_fail("SIENGE_USUARIO"),
        "senha": get_env_or_fail("SIENGE_SENHA"),
        "empresa": get_env_or_fail("SIENGE_EMPRESA", "1")
    }

    log(
        f"✅ Credenciais carregadas: {credenciais['usuario']} @ {credenciais['url']}")
    return credenciais


async def carregar_indices_economicos() -> Dict[str, Any]:
    """Carrega índices econômicos do sistema ou usa valores de fallback."""
    log("📈 Carregando índices econômicos...")

    try:
        from core.data_manager import data_manager
        await data_manager.inicializar()

        # Busca IPCA e IGPM separadamente
        ipca = await data_manager.obter_indice_mais_recente("ipca")
        igpm = await data_manager.obter_indice_mais_recente("igpm")

        if ipca is not None and igpm is not None:
            log(
                f"✅ Índices carregados do sistema: IPCA={ipca}% | IGPM={igpm}%")
            return {
                "ipca": {"valor": ipca, "tipo": "IPCA", "periodo": "Recente"},
                "igpm": {"valor": igpm, "tipo": "IGPM", "periodo": "Recente"}
            }
        else:
            log("⚠️ Usando índices de fallback")
            return {
                "ipca": {"valor": 4.62, "tipo": "IPCA", "periodo": "Fallback"},
                "igpm": {"valor": 3.89, "tipo": "IGPM", "periodo": "Fallback"}
            }

    except Exception as e:
        log(f"❌ Erro ao carregar índices: {str(e)} - Usando fallback")
        return {
            "ipca": {"valor": 4.62, "tipo": "IPCA", "periodo": "Fallback"},
            "igpm": {"valor": 3.89, "tipo": "IGPM", "periodo": "Fallback"}
        }


def obter_mes_ano_atual_pt():
    """Obtém mês/ano atual em português."""
    data_atual = datetime.now()
    meses_pt = {
        "JANUARY": "JANEIRO", "FEBRUARY": "FEVEREIRO", "MARCH": "MARÇO",
        "APRIL": "ABRIL", "MAY": "MAIO", "JUNE": "JUNHO",
        "JULY": "JULHO", "AUGUST": "AGOSTO", "SEPTEMBER": "SETEMBRO",
        "OCTOBER": "OUTUBRO", "NOVEMBER": "NOVEMBRO", "DECEMBER": "DEZEMBRO"
    }
    mes_en = data_atual.strftime("%B").upper()
    mes_pt = meses_pt.get(mes_en, mes_en)
    ano_atual = str(data_atual.year)
    return f"{mes_pt}/{ano_atual}"


def verificar_priorizar_reparcelamento() -> bool:
    """Verifica se deve priorizar reparcelamento."""
    return os.getenv("PRIORIZAR_REPARCELAMENTO", "true").lower() == "true"


# ============= FUNÇÕES PARA CONTRATOS ANIVERSÁRIO =============

def identificar_contrato_aniversario(tipo_reajuste: str, data_assinatura: str = None) -> bool:
    """
    Identifica se um contrato é do tipo aniversário

    Args:
        tipo_reajuste: Tipo de reajuste do contrato
        data_assinatura: Data de assinatura do contrato

    Returns:
        bool: True se for contrato aniversário, False caso contrário
    """
    if not tipo_reajuste:
        return False

    tipo_lower = str(tipo_reajuste).lower()
    return 'anivers' in tipo_lower and data_assinatura is not None


def extrair_data_aniversario(data_assinatura: str) -> int:
    """
    Extrai o dia de aniversário da data de assinatura

    Args:
        data_assinatura: Data de assinatura no formato dd/mm/yyyy, dd/mm/yy, ou yyyy-mm-dd

    Returns:
        int: Dia do aniversário (1-31) ou None se inválida
    """
    if not data_assinatura:
        return None

    try:
        # Tentar formato dd/mm/yyyy
        data_obj = datetime.strptime(data_assinatura, "%d/%m/%Y")
        return data_obj.day
    except ValueError:
        try:
            # Tentar formato dd/mm/yy
            data_obj = datetime.strptime(data_assinatura, "%d/%m/%y")
            return data_obj.day
        except ValueError:
            try:
                # Tentar formato yyyy-mm-dd
                data_obj = datetime.strptime(data_assinatura, "%Y-%m-%d")
                return data_obj.day
            except ValueError:
                log(f"⚠️ Data de assinatura inválida: {data_assinatura}")
                return None


def comparar_datas_vencimento_aniversario(dia_vencimento: int, dia_aniversario: int) -> str:
    """
    Compara dia de vencimento com dia de aniversário

    Args:
        dia_vencimento: Dia de vencimento da parcela (1-31)
        dia_aniversario: Dia de aniversário do contrato (1-31)

    Returns:
        str: 'anterior', 'igual', ou 'posterior'
    """
    if dia_vencimento < dia_aniversario:
        return "anterior"
    elif dia_vencimento == dia_aniversario:
        return "igual"
    else:
        return "posterior"


def determinar_mes_reparcelamento(dia_vencimento: int, dia_aniversario: int, mes_atual: int = None, ano_atual: int = None) -> Dict[str, Any]:
    """
    Determina o mês de início do reparcelamento para contratos aniversário

    Args:
        dia_vencimento: Dia de vencimento da parcela
        dia_aniversario: Dia de aniversário do contrato
        mes_atual: Mês atual (opcional, usa datetime.now() se não fornecido)
        ano_atual: Ano atual (opcional, usa datetime.now() se não fornecido)

    Returns:
        Dict com informações do mês de reparcelamento
    """
    if mes_atual is None or ano_atual is None:
        hoje = datetime.now()
        mes_atual = hoje.month
        ano_atual = hoje.year

    comparacao = comparar_datas_vencimento_aniversario(
        dia_vencimento, dia_aniversario)

    if comparacao == "anterior":
        # Vencimento antes do aniversário: mês seguinte
        mes_reparcelamento = mes_atual + 1
        ano_reparcelamento = ano_atual
        if mes_reparcelamento > 12:
            mes_reparcelamento = 1
            ano_reparcelamento += 1

        return {
            "mes_reparcelamento": mes_reparcelamento,
            "ano_reparcelamento": ano_reparcelamento,
            "aplicar_imediato": False,
            "motivo": "Vencimento anterior ao aniversário",
            "comparacao": comparacao
        }
    else:
        # Vencimento igual ou posterior ao aniversário: mês atual
        return {
            "mes_reparcelamento": mes_atual,
            "ano_reparcelamento": ano_atual,
            "aplicar_imediato": True,
            "motivo": "Vencimento igual ou posterior ao aniversário",
            "comparacao": comparacao
        }


async def agendar_reparcelamento_contrato(contrato: Dict[str, Any], mes_reparcelamento: int, ano_reparcelamento: int) -> Dict[str, Any]:
    """
    Agenda um contrato para reparcelamento futuro

    Args:
        contrato: Dados do contrato
        mes_reparcelamento: Mês para reparcelamento
        ano_reparcelamento: Ano para reparcelamento

    Returns:
        Dict com resultado do agendamento
    """
    try:
        from core.mongodb_manager import mongodb_manager

        # Conectar ao MongoDB se necessário
        if not mongodb_manager.conectado:
            await mongodb_manager.conectar()

        if not mongodb_manager.conectado or mongodb_manager.database is None:
            raise Exception("MongoDB não conectado")

        collection = mongodb_manager.database.fila_contratos

        # Dados do agendamento
        dados_agendamento = {
            "numero_titulo": contrato.get("numero_titulo"),
            "cliente": contrato.get("cliente"),
            "status": "AGENDADO_ANIVERSARIO",
            "mes_reparcelamento": mes_reparcelamento,
            "ano_reparcelamento": ano_reparcelamento,
            "tipo_contrato": "aniversario",
            "data_agendamento": datetime.now().isoformat(),
            "motivo_agendamento": "Vencimento anterior ao aniversário",
            "processado": False
        }

        # Atualizar ou inserir na fila
        resultado = collection.update_one(
            {"numero_titulo": contrato.get("numero_titulo")},
            {"$set": dados_agendamento},
            upsert=True
        )

        log(f"📅 Contrato {contrato.get('numero_titulo')} agendado para {mes_reparcelamento:02d}/{ano_reparcelamento}")

        return {
            "sucesso": True,
            "contrato_agendado": dados_agendamento,
            "modificado": resultado.modified_count > 0,
            "inserido": resultado.upserted_id is not None
        }

    except Exception as e:
        log(f"❌ Erro ao agendar contrato: {str(e)}")
        return {
            "sucesso": False,
            "erro": str(e)
        }


async def processar_contratos_agendados() -> Dict[str, Any]:
    """
    Processa contratos agendados para o mês atual

    Returns:
        Dict com resultado do processamento
    """
    try:
        from core.mongodb_manager import mongodb_manager

        # Conectar ao MongoDB se necessário
        if not mongodb_manager.conectado:
            await mongodb_manager.conectar()

        if not mongodb_manager.conectado or mongodb_manager.database is None:
            raise Exception("MongoDB não conectado")

        collection = mongodb_manager.database.fila_contratos

        hoje = datetime.now()
        mes_atual = hoje.month
        ano_atual = hoje.year

        # Buscar contratos agendados para o mês atual
        contratos_agendados = list(collection.find({
            "status": "AGENDADO_ANIVERSARIO",
            "mes_reparcelamento": mes_atual,
            "ano_reparcelamento": ano_atual,
            "processado": False
        }))

        log(f"📅 Encontrados {len(contratos_agendados)} contratos agendados para {mes_atual:02d}/{ano_atual}")

        contratos_processados = []
        contratos_erro = []

        for contrato in contratos_agendados:
            try:
                # Marcar como processado
                collection.update_one(
                    {"_id": contrato["_id"]},
                    {"$set": {"processado": True,
                              "data_processamento": datetime.now().isoformat()}}
                )

                contratos_processados.append(contrato)
                log(f"✅ Contrato {contrato.get('numero_titulo')} processado")

            except Exception as e:
                contratos_erro.append({
                    "contrato": contrato,
                    "erro": str(e)
                })
                log(
                    f"❌ Erro ao processar contrato {contrato.get('numero_titulo')}: {str(e)}")

        return {
            "sucesso": True,
            "total_agendados": len(contratos_agendados),
            "processados": len(contratos_processados),
            "erros": len(contratos_erro),
            "contratos_processados": contratos_processados,
            "contratos_erro": contratos_erro
        }

    except Exception as e:
        log(f"❌ Erro ao processar contratos agendados: {str(e)}")
        return {
            "sucesso": False,
            "erro": str(e)
        }
