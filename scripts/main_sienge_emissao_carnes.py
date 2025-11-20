#!/usr/bin/env python3
"""
Main de emissão de carnês para processamento da Fase 2 do RPA Sienge
Sistema de geração de carnês independente

FASE 2: EMISSÃO DE CARNÊS
REPARCELADO → CARNE_GERADO

Conforme PDD Seção 10.2: Emissão de carnê + Geração de arquivos de remessa

Desenvolvido em Português Brasileiro
"""

from core.utils_sienge import (
    log,
    notificar_sucesso_simples,
    notificar_erro_simples,
    carregar_credenciais_sienge,
    get_env_or_fail
)
from rpa_sienge.rpa_sienge_emissao_carne import RPAEmissaoCarneSienge
from core.gerador_anexos import gerador_anexos
from core.templates_relatorios import templates_relatorios
import os
import sys
from pathlib import Path
import asyncio
import argparse
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import calendar
import json
import csv

# Garante execução com browser visível para debug
os.environ["HEADLESS"] = "0"
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
ARQUIVO_LOG_ATUAL: Optional[Path] = None


class LoggerMultiplo:
    """Direciona logs para stdout e arquivo do fluxo."""

    def __init__(self, *destinos):
        self.destinos = destinos

    def write(self, mensagem):
        for destino in self.destinos:
            destino.write(mensagem)

    def flush(self):
        for destino in self.destinos:
            destino.flush()


def preparar_logs_execucao():
    """Configura saída padrão para registrar logs da execução em arquivo."""
    global ARQUIVO_LOG_ATUAL

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ARQUIVO_LOG_ATUAL = LOGS_DIR / f"emissao_carnes_{timestamp}.log"

    stdout_original = sys.stdout
    stderr_original = sys.stderr

    arquivo_log = open(ARQUIVO_LOG_ATUAL, "a", encoding="utf-8")
    multilog = LoggerMultiplo(stdout_original, arquivo_log)
    sys.stdout = multilog
    sys.stderr = multilog
    log(f"📁 Log da execução: {ARQUIVO_LOG_ATUAL}")
    return arquivo_log, stdout_original, stderr_original


# Garante que o diretório raiz está no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def obter_contratos_reparcelados() -> List[Dict[str, Any]]:
    """
    FASE 1: Buscar contratos com status REPARCELADO no repositório JSON

    Returns:
        Lista de contratos com status REPARCELADO
    """
    log("\n💾 FASE 1: BUSCANDO CONTRATOS REPARCELADOS NO REPOSITÓRIO JSON...")
    log("=" * 60)

    try:
        # ✅ USAR JSONRPAFramework - PRINCIPAL (não mais fallback)
        from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo

        # Buscar contratos com status REPARCELADO
        contratos_reparcelados = repositorio_contratos_arquivo.framework.find(
            {"status": "REPARCELADO"})

        # 🔍 DEBUG: Verificar estrutura dos contratos encontrados
        if contratos_reparcelados:
            log(f"🔍 DEBUG: Primeiro contrato encontrado:")
            primeiro_contrato = contratos_reparcelados[0]
            log(f"   📋 Chaves disponíveis: {list(primeiro_contrato.keys())}")
            log(f"   📋 Código Cliente: '{primeiro_contrato.get('Código Cliente', 'N/A')}'")
            log(f"   📋 Cliente: '{primeiro_contrato.get('Cliente', 'N/A')}'")
            log(f"   📋 Título: '{primeiro_contrato.get('Titulo', 'N/A')}'")
            log(f"   📋 Status: '{primeiro_contrato.get('status', 'N/A')}'")

        if not contratos_reparcelados:
            log("⚠️ Nenhum contrato com status REPARCELADO encontrado no repositório")
            return []

        log(f"✅ Encontrados {len(contratos_reparcelados)} contratos com status REPARCELADO:")
        for i, contrato in enumerate(contratos_reparcelados[:5], 1):
            codigo_cliente = contrato.get('Código Cliente', 'N/A')
            cliente = contrato.get('Cliente', 'N/A')
            numero_titulo = contrato.get('Titulo', 'N/A')
            log(f"   {i}. {codigo_cliente} - {cliente} (Título: {numero_titulo})")

        if len(contratos_reparcelados) > 5:
            log(f"   ... e mais {len(contratos_reparcelados) - 5} contratos")

        return contratos_reparcelados

    except Exception as e:
        log(f"❌ Erro ao buscar contratos reparcelados: {str(e)}")
        raise Exception(
            f"Erro ao buscar contratos reparcelados: {str(e)} - sem fallback")


async def carregar_dados_planilha_base_calculo() -> Dict[str, Any]:
    """
    FASE 2: Carregar dados da planilha base de cálculo

    Returns:
        Dados indexados da planilha por código_cliente + número_titulo
    """
    log("\n📋 FASE 2: CARREGANDO DADOS DA PLANILHA BASE DE CÁLCULO...")
    log("=" * 60)

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        # Configurar credenciais Google Sheets
        credenciais_path = get_env_or_fail("GOOGLE_CREDENTIALS_PATH")
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_file(
            credenciais_path, scopes=scope)
        cliente_sheets = gspread.authorize(credentials)

        # Abrir planilha base de cálculo
        planilha_calculo_id = get_env_or_fail("PLANILHA_CALCULO_ID")
        planilha_calculo = cliente_sheets.open_by_key(planilha_calculo_id)
        aba_base_calculo = planilha_calculo.worksheet("Base de cálculo")

        # Obter todos os dados da planilha
        dados_planilha_brutos = aba_base_calculo.get_all_records()

        # 🔍 DEBUG: Verificar primeiros registros
        if dados_planilha_brutos:
            log(f"🔍 DEBUG: Primeiro registro da planilha:")
            primeiro_registro = dados_planilha_brutos[0]
            for chave, valor in primeiro_registro.items():
                if 'empresa' in chave.lower() or 'loteamento' in chave.lower():
                    log(f"   📋 '{chave}': '{valor}' (tipo: {type(valor)})")

        # Indexar dados por código_cliente + número_titulo para busca rápida
        dados_indexados = {}
        # Linha 2 é o primeiro registro
        for i, registro in enumerate(dados_planilha_brutos, 2):
            codigo_cliente_raw = registro.get("Código Cliente", "")
            numero_titulo_raw = registro.get("Titulo", "")

            codigo_cliente = str(codigo_cliente_raw).strip(
            ) if codigo_cliente_raw is not None else ""
            numero_titulo = str(numero_titulo_raw).strip(
            ) if numero_titulo_raw is not None else ""

            if codigo_cliente and numero_titulo:
                chave_busca = f"{codigo_cliente}_{numero_titulo}"
                # Adicionar número da linha para futuras atualizações
                registro['linha_planilha'] = i
                dados_indexados[chave_busca] = registro

        log(f"✅ Carregados {len(dados_indexados)} registros da planilha base de cálculo")
        log(f"📋 Dados indexados por código_cliente + número_titulo")

        return dados_indexados

    except Exception as e:
        log(f"❌ Erro ao carregar dados da planilha: {str(e)}")
        raise Exception(
            f"Erro ao carregar dados da planilha: {str(e)} - sem fallback")


def associar_contratos_com_planilha(contratos_reparcelados: List[Dict[str, Any]],
                                    dados_planilha: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    FASE 3: Associar contratos do banco com dados da planilha

    Args:
        contratos_reparcelados: Lista de contratos do banco
        dados_planilha: Dados indexados da planilha

    Returns:
        Lista de contratos com dados da planilha associados
    """
    log("\n🔗 FASE 3: ASSOCIANDO CONTRATOS COM DADOS DA PLANILHA...")
    log("=" * 60)

    contratos_associados = []
    contratos_nao_encontrados = []

    for contrato in contratos_reparcelados:
        codigo_cliente = contrato.get('Código Cliente', '').strip()
        numero_titulo = contrato.get('Titulo', '').strip()
        cliente = contrato.get('Cliente', 'N/A')

        if not codigo_cliente or not numero_titulo:
            log(f"⚠️ Contrato {cliente} sem código_cliente ou número_titulo válidos")
            contratos_nao_encontrados.append(contrato)
            continue

        # Buscar na planilha usando código + título
        chave_busca = f"{codigo_cliente}_{numero_titulo}"
        dados_planilha_contrato = dados_planilha.get(chave_busca)

        if dados_planilha_contrato:
            # Associar dados da planilha ao contrato
            contrato['dados_planilha'] = dados_planilha_contrato
            contratos_associados.append(contrato)
            log(f"✅ {cliente} (Código: {codigo_cliente}, Título: {numero_titulo}) - Dados da planilha associados")
        else:
            log(f"❌ {cliente} (Código: {codigo_cliente}, Título: {numero_titulo}) - NÃO encontrado na planilha")
            contratos_nao_encontrados.append(contrato)

    log(f"\n📊 RESULTADO DA ASSOCIAÇÃO:")
    log(f"   ✅ Contratos associados: {len(contratos_associados)}")
    log(
        f"   ❌ Contratos não encontrados na planilha: {len(contratos_nao_encontrados)}")

    if contratos_nao_encontrados:
        log(f"\n⚠️ CONTRATOS NÃO ENCONTRADOS NA PLANILHA:")
        for contrato in contratos_nao_encontrados:
            codigo = contrato.get('Código Cliente', 'N/A')
            titulo = contrato.get('Titulo', 'N/A')
            cliente = contrato.get('Cliente', 'N/A')
            log(f"   ❌ {cliente} (Código: {codigo}, Título: {titulo})")

        log(f"\n📋 CONTINUANDO COM {len(contratos_associados)} CONTRATOS ENCONTRADOS")
        log(f"📄 Contratos não encontrados serão incluídos no relatório de erro")

    return contratos_associados, contratos_nao_encontrados


def verificar_pendencias_contrato(contrato: Dict[str, Any]) -> Dict[str, Any]:
    """
    FASE 4: Verificar pendências IPTU e inadimplência conforme PDD

    Args:
        contrato: Contrato com dados da planilha associados

    Returns:
        Resultado da verificação de pendências
    """
    dados_planilha = contrato.get('dados_planilha', {})
    cliente = contrato.get('cliente', 'N/A')

    def obter_valor_coluna(nome_coluna: str) -> str:
        valor = dados_planilha.get(nome_coluna)
        if valor is None:
            nome_normalizado = nome_coluna.strip().upper()
            for chave_existente, valor_existente in dados_planilha.items():
                if isinstance(chave_existente, str) and chave_existente.strip().upper() == nome_normalizado:
                    valor = valor_existente
                    break
        return str(valor or "").strip()

    # Verificar PENDÊNCIAS PMFI (IPTU)
    pendencias_pmfi = obter_valor_coluna("PENDENCIAS PMFI")

    # Verificar PENDÊNCIAS SIENGE INAD (Inadimplência)
    pendencias_sienge_inad = obter_valor_coluna("PENDENCIAS SIENGE INAD")

    # Verificar PENDÊNCIAS SIENGE (Outras pendências)
    pendencias_sienge = obter_valor_coluna("PENDENCIAS SIENGE")

    # ✅ LÓGICA CORRETA CONFORME PDD ATUALIZADO:
    # IPTU: "NÃO" = SEM pendências (apto); vazio ou qualquer outro valor = COM pendências (inapto)
    # INADIMPLÊNCIA: vazio = adimplente (apto); qualquer valor preenchido (incluindo "Inadimplência" ou "OK") = COM pendência (inapto)
    # OUTRAS PENDÊNCIAS: "OK" = SEM pendências (apto); vazio ou qualquer outro valor = COM pendência (inapto)

    # ✅ Apenas "NÃO" é considerado apto para PENDENCIAS PMFI (vazio = inapto)
    # Normalizar para garantir comparação correta (remover espaços e converter para maiúsculo)
    pendencias_pmfi_normalizada = pendencias_pmfi.strip().upper() if pendencias_pmfi else ""
    pmfi_ok = pendencias_pmfi_normalizada == "NÃO"

    # ✅ Apenas vazio é considerado apto para PENDENCIAS SIENGE INAD (qualquer valor preenchido = inapto)
    # Verificar se está realmente vazio (após strip) - obter_valor_coluna sempre retorna string
    sienge_inad_ok = not pendencias_sienge_inad.strip()

    # ✅ Apenas "OK" é considerado apto para PENDENCIAS SIENGE (vazio = inapto)
    # Normalizar para garantir comparação correta (remover espaços e converter para maiúsculo)
    pendencia_sienge_normalizada = pendencias_sienge.strip(
    ).upper() if pendencias_sienge else ""
    sienge_ok = pendencia_sienge_normalizada == "OK"

    # Contrato apto se TODAS as pendências estão OK
    contrato_apto = pmfi_ok and sienge_inad_ok and sienge_ok

    resultado = {
        "contrato_apto": contrato_apto,
        "pendencias_pmfi": pendencias_pmfi if pendencias_pmfi else "OK",
        "pendencias_sienge_inad": pendencias_sienge_inad if pendencias_sienge_inad else "OK",
        "pendencias_sienge": pendencias_sienge if pendencias_sienge else "OK",
        "cliente": cliente
    }

    status_msg = "APTO" if contrato_apto else "PENDENTE"
    codigo_cliente = contrato.get('Código Cliente', 'N/A')
    titulo = contrato.get('Titulo', 'N/A')
    log(f"   🔍 {cliente} (Código: {codigo_cliente}, Título: {titulo}): {status_msg}")

    if contrato_apto:
        # ✅ Log detalhado para contratos APTOS (para debug e conferência)
        log(f"      ✅ PMFI: '{pendencias_pmfi}' | SIENGE INAD: '{pendencias_sienge_inad}' | SIENGE: '{pendencias_sienge}'")
    else:
        if not pmfi_ok:
            log(
                f"      ❌ PENDÊNCIAS PMFI: '{pendencias_pmfi}' (deve ser 'NÃO' para ser apto)")
        if not sienge_inad_ok:
            log(
                f"      ❌ PENDÊNCIAS SIENGE INAD: '{pendencias_sienge_inad}' (deve estar vazio para ser adimplente)")
        if not sienge_ok:
            log(
                f"      ❌ PENDÊNCIAS SIENGE: '{pendencias_sienge}' (deve ser 'OK' para ser apto)")

    return resultado


def filtrar_contratos_aptos(contratos_associados: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    FASE 4: Filtrar contratos aptos para geração de carnê

    Args:
        contratos_associados: Lista de contratos com dados da planilha

    Returns:
        Tupla com (contratos_aptos, contratos_com_pendencias)
        contratos_com_pendencias: Lista de dicts com 'contrato' e 'motivo'
    """
    log("\n🔍 FASE 4: VERIFICANDO PENDÊNCIAS E FILTRANDO CONTRATOS APTOS...")
    log("=" * 60)

    contratos_aptos = []
    contratos_com_pendencias = []

    for contrato in contratos_associados:
        resultado_verificacao = verificar_pendencias_contrato(contrato)

        if resultado_verificacao["contrato_apto"]:
            contratos_aptos.append(contrato)
        else:
            # Montar motivo detalhado
            motivos = []
            if resultado_verificacao["pendencias_pmfi"] != "OK":
                motivos.append(
                    f"Pendências PMFI: {resultado_verificacao['pendencias_pmfi']}")
            if resultado_verificacao["pendencias_sienge_inad"] != "OK":
                motivos.append(
                    f"Pendências SIENGE INAD: {resultado_verificacao['pendencias_sienge_inad']}")
            if resultado_verificacao["pendencias_sienge"] != "OK":
                motivos.append(
                    f"Pendências SIENGE: {resultado_verificacao['pendencias_sienge']}")

            motivo_completo = " | ".join(
                motivos) if motivos else "Pendências não especificadas"

            contratos_com_pendencias.append({
                "contrato": contrato,
                "motivo": motivo_completo,
                "pendencias": resultado_verificacao
            })

    log(f"\n📊 RESULTADO DA VERIFICAÇÃO DE PENDÊNCIAS:")
    log(f"   ✅ Contratos aptos: {len(contratos_aptos)}")
    log(f"   ❌ Contratos com pendências: {len(contratos_com_pendencias)}")

    if contratos_com_pendencias:
        log(f"\n⚠️ CONTRATOS COM PENDÊNCIAS:")
        for item in contratos_com_pendencias:
            contrato = item["contrato"]
            pendencias = item["pendencias"]
            cliente = contrato.get('Cliente', 'N/A')
            log(f"   ❌ {cliente}:")
            if pendencias["pendencias_pmfi"] != "OK":
                log(f"      📋 PMFI: {pendencias['pendencias_pmfi']}")
            if pendencias["pendencias_sienge_inad"] != "OK":
                log(
                    f"      📋 SIENGE INAD: {pendencias['pendencias_sienge_inad']}")
            if pendencias["pendencias_sienge"] != "OK":
                log(f"      📋 SIENGE: {pendencias['pendencias_sienge']}")

    if not contratos_aptos:
        # ❌ SEM FALLBACK: Erro se não há contratos aptos
        raise Exception(
            "Nenhum contrato apto para geração de carnê encontrado - sem fallback")

    return contratos_aptos, contratos_com_pendencias


def calcular_12_parcelas_esperadas(primeiro_vencimento: str) -> List[str]:
    """
    Calcula as 12 datas de vencimento esperadas a partir do 1º vencimento.

    Args:
        primeiro_vencimento: Data no formato DD/MM/YYYY ou DD/MM/YY

    Returns:
        Lista com 12 datas no formato DD/MM/YYYY
    """
    try:
        # Parse flexível da data
        if "/" in primeiro_vencimento:
            if len(primeiro_vencimento.split("/")[2]) == 2:
                data_base = datetime.strptime(primeiro_vencimento, "%d/%m/%y")
            else:
                data_base = datetime.strptime(primeiro_vencimento, "%d/%m/%Y")
        else:
            raise ValueError(
                f"Formato de data não reconhecido: {primeiro_vencimento}")

        parcelas = []
        for i in range(12):
            # Adicionar i meses à data base
            mes_novo = data_base.month + i
            ano_novo = data_base.year + (mes_novo - 1) // 12
            mes_novo = ((mes_novo - 1) % 12) + 1

            # Garantir que o dia existe no mês (ex: 31/01 -> 31 não existe em fevereiro)
            ultimo_dia_mes = calendar.monthrange(ano_novo, mes_novo)[1]
            dia_parcela = min(data_base.day, ultimo_dia_mes)

            parcela = datetime(ano_novo, mes_novo, dia_parcela)
            parcelas.append(parcela.strftime("%d/%m/%Y"))

        return parcelas
    except Exception as e:
        log(
            f"❌ Erro ao calcular 12 parcelas para {primeiro_vencimento}: {str(e)}")
        raise


async def executar_fase_geracao_carnes(rpa: RPAEmissaoCarneSienge, contratos_aptos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    FASE 5: Executar geração de carnês via RPA Sienge

    Args:
        rpa: Instância inicializada do RPA Sienge
        contratos_aptos: Lista de contratos aptos para geração

    Returns:
        Resultado da geração de carnês
    """
    log("\n🎫 FASE 5: EXECUTANDO GERAÇÃO DE CARNÊS VIA RPA SIENGE...")
    log("=" * 60)
    log(f"📋 Contratos para processar: {len(contratos_aptos)}")

    try:
        # ✅ USAR MÉTODO DIRETO DE GERAÇÃO DE CARNÊS
        # Agrupar contratos por empresa e chamar _gerar_carne_empresa_sienge diretamente
        contratos_por_empresa = {}
        for contrato in contratos_aptos:
            dados_planilha = contrato.get('dados_planilha', {})
            empresa = dados_planilha.get('Empresa', '')

            # 🔍 DEBUG: Verificar estrutura dos dados
            if not empresa:
                log(
                    f"❌ ERRO: Empresa vazia para contrato {contrato.get('numero_titulo', 'N/A')}")
                log(
                    f"   📋 Dados planilha disponíveis: {list(dados_planilha.keys())}")
                if 'Empresa' in dados_planilha:
                    log(
                        f"   📋 Valor 'Empresa': '{dados_planilha['Empresa']}' (tipo: {type(dados_planilha['Empresa'])})")
                    log(
                        f"   📋 Valor 'Empresa' repr: {repr(dados_planilha['Empresa'])}")

                # 🔍 DEBUG: Verificar se há outras colunas de empresa
                for chave in dados_planilha.keys():
                    if 'empresa' in chave.lower() or 'loteamento' in chave.lower():
                        log(
                            f"   📋 Coluna relacionada '{chave}': '{dados_planilha[chave]}'")

                # ❌ SEM FALLBACK: Erro se empresa estiver vazia
                raise Exception(
                    f"Empresa vazia para contrato {contrato.get('numero_titulo', 'N/A')} - sem fallback")

            if empresa not in contratos_por_empresa:
                contratos_por_empresa[empresa] = []
            contratos_por_empresa[empresa].append(contrato)

        log(
            f"📊 Contratos agrupados por empresa: {len(contratos_por_empresa)} empresas")
        for empresa, contratos in contratos_por_empresa.items():
            log(f"   🏢 {empresa}: {len(contratos)} contratos")

        # 🔍 DEBUG: Verificar se há múltiplas empresas
        if len(contratos_por_empresa) == 1:
            log(f"⚠️ ATENÇÃO: Apenas 1 empresa encontrada - loop executará apenas 1 vez")
        else:
            log(f"✅ {len(contratos_por_empresa)} empresas encontradas - loop executará {len(contratos_por_empresa)} vezes")

        # 🔍 DEBUG: Verificar se todos os contratos foram agrupados
        total_contratos_agrupados = sum(
            len(contratos) for contratos in contratos_por_empresa.values())
        log(
            f"🔍 DEBUG: Total de contratos agrupados: {total_contratos_agrupados}")
        log(
            f"🔍 DEBUG: Total de contratos aptos recebidos: {len(contratos_aptos)}")

        if total_contratos_agrupados != len(contratos_aptos):
            log(
                f"⚠️ ATENÇÃO: Discrepância! Contratos agrupados ({total_contratos_agrupados}) ≠ Contratos aptos ({len(contratos_aptos)})")

        contratos_processados = 0
        contratos_erro = 0
        carnês_gerados = []  # Lista para armazenar todos os carnês processados
        contratos_nao_gerados = []  # ✅ Lista para rastrear contratos não gerados com motivo

        # Processar cada empresa
        log(f"\n🔄 INICIANDO LOOP DE PROCESSAMENTO...")
        log(
            f"📊 Total de empresas para processar: {len(contratos_por_empresa)}")

        for i, (empresa, contratos_empresa) in enumerate(contratos_por_empresa.items(), 1):
            log(f"\n🏢 PROCESSANDO EMPRESA {i}/{len(contratos_por_empresa)}: {empresa}")
            log(f"📋 {len(contratos_empresa)} contratos para esta empresa")

            try:
                # ✅ NOVA LÓGICA: Calcular 12 parcelas esperadas para cada contrato
                log(
                    f"📅 Calculando parcelas esperadas para {len(contratos_empresa)} contratos...")

                primeiros_vencimentos = []
                todas_parcelas = []  # Todas as parcelas de todos os contratos

                for contrato in contratos_empresa:
                    dados_planilha = contrato.get('dados_planilha', {})

                    # ✅ USAR PARCELAS JÁ CALCULADAS (se existirem) ou calcular agora
                    if 'parcelas_esperadas' in contrato and contrato['parcelas_esperadas']:
                        parcelas_12 = contrato['parcelas_esperadas']
                        vencimento = contrato.get(
                            'primeiro_vencimento', dados_planilha.get('1º vencimento carnê', ''))
                        log(
                            f"   ✅ Contrato {contrato.get('Titulo', 'N/A')}: Usando parcelas já calculadas")
                    else:
                        vencimento = dados_planilha.get(
                            '1º vencimento carnê', '')
                        if not vencimento:
                            log(
                                f"⚠️ Contrato {contrato.get('Titulo', 'N/A')} sem 1º vencimento carnê")
                            continue
                        # Calcular 12 parcelas para este contrato
                        parcelas_12 = calcular_12_parcelas_esperadas(
                            vencimento)
                        contrato['parcelas_esperadas'] = parcelas_12
                        contrato['primeiro_vencimento'] = vencimento
                        log(f"   ✅ Contrato {contrato.get('Titulo', 'N/A')}: 1º vencimento = {vencimento}, 12 parcelas calculadas")

                    primeiros_vencimentos.append(vencimento)
                    todas_parcelas.extend(parcelas_12)

                    log(
                        f"      📅 Parcelas: {parcelas_12[0]} até {parcelas_12[-1]}")

                    # ✅ GRAVAR PARCELAS ESPERADAS NO REPOSITÓRIO JSON
                    try:
                        from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo
                        numero_titulo = contrato.get('Titulo', '')
                        if numero_titulo:
                            # Buscar contrato no repositório
                            contratos_encontrados = repositorio_contratos_arquivo.framework.find(
                                {"Titulo": numero_titulo}
                            )
                            if contratos_encontrados:
                                contrato_encontrado = contratos_encontrados[0]
                                contrato_id = contrato_encontrado.get("_id")
                                if contrato_id:
                                    # Atualizar com parcelas esperadas e primeiro vencimento
                                    dados_atualizacao = {
                                        "parcelas_esperadas": parcelas_12,
                                        "primeiro_vencimento_carne": vencimento,
                                        "timestamp_parcelas_calculadas": datetime.now().isoformat(),
                                        "timestamp_ultima_atualizacao": datetime.now().isoformat()
                                    }
                                    repositorio_contratos_arquivo.framework.update(
                                        {"_id": contrato_id}, dados_atualizacao
                                    )
                                    log(
                                        f"      💾 Parcelas gravadas no repositório para título {numero_titulo}")
                                else:
                                    log(
                                        f"      ⚠️ Contrato {numero_titulo} sem ID válido para gravação")
                            else:
                                log(
                                    f"      ⚠️ Contrato {numero_titulo} não encontrado no repositório para gravação")
                    except Exception as e:
                        log(
                            f"      ⚠️ Erro ao gravar parcelas no repositório para título {numero_titulo}: {str(e)}")
                        # Não quebra o fluxo se a gravação falhar

                if not primeiros_vencimentos:
                    raise Exception(
                        f"Nenhum 1º vencimento carnê encontrado para empresa {empresa} - sem fallback")

                # ✅ Calcular data_inicial: MENOR mês entre todos os 1º vencimentos
                datas_primeiro_vencimento = []
                for venc in primeiros_vencimentos:
                    if "/" in venc:
                        if len(venc.split("/")[2]) == 2:
                            data_temp = datetime.strptime(venc, "%d/%m/%y")
                        else:
                            data_temp = datetime.strptime(venc, "%d/%m/%Y")
                        # Usar dia 1 do mês para data_inicial
                        datas_primeiro_vencimento.append(
                            data_temp.replace(day=1))

                if not datas_primeiro_vencimento:
                    raise Exception(
                        f"Erro ao processar primeiros vencimentos para empresa {empresa}")

                # Encontrar a menor data (mês mais antigo)
                data_inicial = min(datas_primeiro_vencimento)
                data_inicial_formatada = data_inicial.strftime("%d/%m/%Y")
                log(
                    f"📅 Data inicial calculada: {data_inicial_formatada} (menor mês entre todos os 1º vencimentos)")

                # ✅ Calcular data_final: MAIOR mês entre todas as 12ª parcelas + 2 meses (margem)
                datas_ultima_parcela = []
                for parcela_str in todas_parcelas:
                    if "/" in parcela_str:
                        if len(parcela_str.split("/")[2]) == 2:
                            data_parcela = datetime.strptime(
                                parcela_str, "%d/%m/%y")
                        else:
                            data_parcela = datetime.strptime(
                                parcela_str, "%d/%m/%Y")
                        # Usar último dia do mês para data_final
                        ultimo_dia = calendar.monthrange(
                            data_parcela.year, data_parcela.month)[1]
                        datas_ultima_parcela.append(
                            data_parcela.replace(day=ultimo_dia))

                if not datas_ultima_parcela:
                    raise Exception(
                        f"Erro ao processar parcelas para empresa {empresa}")

                # Encontrar a maior data (mês mais recente)
                data_final_base = max(datas_ultima_parcela)

                # Adicionar 2 meses de margem para garantir que todas as parcelas apareçam na grid
                mes_final = data_final_base.month + 2
                ano_final = data_final_base.year
                if mes_final > 12:
                    mes_final = mes_final - 12
                    ano_final += 1

                ultimo_dia_mes_final = calendar.monthrange(
                    ano_final, mes_final)[1]
                data_final = data_final_base.replace(
                    year=ano_final, month=mes_final, day=ultimo_dia_mes_final)
                data_final_formatada = data_final.strftime("%d/%m/%Y")
                log(
                    f"📅 Data final calculada: {data_final_formatada} (maior mês + 2 meses de margem)")

                parametros_empresa = {
                    "empresa": empresa,
                    "contratos": contratos_empresa,
                    "data_inicial": data_inicial_formatada,
                    "data_final": data_final_formatada
                }

                # Chamar webscraping real
                resultado_carne = await rpa._gerar_carne_empresa_sienge(parametros_empresa)

                if resultado_carne.get("sucesso", False):
                    contratos_processados += len(contratos_empresa)
                    log(f"✅ Carnê gerado com sucesso para {empresa}")

                    # ✅ ADICIONAR CARNÊ À LISTA DE CARNÊS GERADOS
                    carnês_gerados.append({
                        "empresa": empresa,
                        "arquivo_remessa": resultado_carne.get("arquivo_remessa", ""),
                        "contratos_processados": len(contratos_empresa),
                        "timestamp_geracao": resultado_carne.get("timestamp_geracao", ""),
                        "contratos": [c.get('Titulo', c.get('numero_titulo', 'N/A')) for c in contratos_empresa]
                    })
                else:
                    contratos_erro += len(contratos_empresa)
                    erro_msg = resultado_carne.get(
                        "erro", "Erro não especificado na geração de carnê")
                    log(
                        f"❌ Erro na geração de carnê para {empresa}: {erro_msg}")

                    # ✅ RASTREAR CONTRATOS NÃO GERADOS
                    for contrato in contratos_empresa:
                        contratos_nao_gerados.append({
                            "contrato": contrato,
                            "motivo": f"Erro na geração de carnê: {erro_msg}"
                        })

            except Exception as e:
                contratos_erro += len(contratos_empresa)
                erro_msg = str(e)
                log(
                    f"❌ Exceção na geração de carnê para {empresa}: {erro_msg}")

                # ✅ RASTREAR CONTRATOS NÃO GERADOS
                for contrato in contratos_empresa:
                    contratos_nao_gerados.append({
                        "contrato": contrato,
                        "motivo": f"Exceção na geração: {erro_msg}"
                    })

            log(f"✅ EMPRESA {i}/{len(contratos_por_empresa)} CONCLUÍDA: {empresa}")

        log(f"\n🎯 LOOP CONCLUÍDO!")
        log(f"📊 Empresas processadas: {len(contratos_por_empresa)}")
        log(f"📊 Contratos processados: {contratos_processados}")
        log(f"📊 Contratos com erro: {contratos_erro}")

        resultado = {
            "sucesso": True,
            "contratos_processados": contratos_processados,
            "contratos_erro": contratos_erro,
            "empresas_processadas": len(contratos_por_empresa),
            "carnês_gerados": carnês_gerados,  # ✅ LISTA DE TODOS OS CARNÊS PROCESSADOS
            # ✅ LISTA DE CONTRATOS NÃO GERADOS COM MOTIVO
            "contratos_nao_gerados": contratos_nao_gerados
        }

        if not resultado.get("sucesso"):
            erro_msg = resultado.get(
                "erro", "Erro não especificado na geração de carnês")
            log(f"❌ Falha na geração de carnês: {erro_msg}")
            # ❌ SEM FALLBACK: Lançar exceção se método principal falhar
            raise Exception(
                f"Falha na geração de carnês: {erro_msg} - sem fallback")

        log(f"✅ Geração de carnês concluída com sucesso!")
        log(f"📊 Contratos processados: {resultado.get('contratos_processados', 0)}")
        log(f"📊 Contratos com erro: {resultado.get('contratos_erro', 0)}")

        return resultado

    except Exception as e:
        log(f"❌ Erro na execução da geração de carnês: {str(e)}")
        raise Exception(
            f"Erro na execução da geração de carnês: {str(e)} - sem fallback")


async def vincular_arquivos_gerados_banco(resultado_carnes: Dict[str, Any]) -> Dict[str, Any]:
    """
    FASE 6: Vincular arquivos de remessa gerados aos contratos no repositório JSON

    Args:
        resultado_carnes: Resultado da geração de carnês

    Returns:
        Resultado da vinculação
    """
    log("\n🔗 FASE 6: VINCULANDO ARQUIVOS GERADOS AOS CONTRATOS NO REPOSITÓRIO...")
    log("=" * 60)

    try:
        # ✅ USAR JSONRPAFramework - PRINCIPAL (não mais fallback)
        from core.repositorio_contratos_arquivo import repositorio_contratos_arquivo

        # Verificar se há carnês gerados com sucesso
        carnes_gerados = resultado_carnes.get("carnês_gerados", [])

        if not carnes_gerados:
            log("⚠️ Nenhum carnê foi gerado com sucesso para vincular")
            return {"sucesso": True, "contratos_vinculados": 0}

        contratos_vinculados = 0

        for carne in carnes_gerados:
            arquivo_remessa = carne.get("arquivo_remessa", "")
            # Lista de números de título
            contratos_empresa = carne.get("contratos", [])

            if arquivo_remessa and contratos_empresa:
                # Atualizar cada contrato da empresa
                for numero_titulo in contratos_empresa:
                    if numero_titulo and numero_titulo != 'N/A':
                        # Buscar contrato pelo número do título
                        contratos_encontrados = repositorio_contratos_arquivo.framework.find(
                            {"Titulo": numero_titulo}
                        )

                        if contratos_encontrados:
                            # Pegar o primeiro (deve ser único)
                            contrato = contratos_encontrados[0]

                            # Preparar dados de atualização
                            update_data = {
                                "status": "CARNE_GERADO",
                                "arquivo_remessa": arquivo_remessa,
                                "timestamp_carne_gerado": datetime.now().isoformat(),
                                "timestamp_ultima_atualizacao": datetime.now().isoformat(),
                            }

                            # Atualizar contrato no repositório JSON
                            contrato_id = contrato.get("_id")
                            if contrato_id:
                                resultado = repositorio_contratos_arquivo.framework.update(
                                    contrato_id, update_data
                                )

                                if resultado:
                                    contratos_vinculados += 1
                                    log(
                                        f"✅ Contrato {numero_titulo} vinculado ao arquivo {arquivo_remessa}"
                                    )
                                else:
                                    log(
                                        f"❌ Falha ao vincular contrato {numero_titulo}"
                                    )
                            else:
                                log(f"❌ Contrato {numero_titulo} sem ID válido")
                        else:
                            log(
                                f"❌ Contrato {numero_titulo} não encontrado no repositório"
                            )

        log(f"✅ Vinculação concluída: {contratos_vinculados} contratos vinculados")

        return {
            "sucesso": True,
            "contratos_vinculados": contratos_vinculados,
            "arquivos_vinculados": len(carnes_gerados)
        }

    except Exception as e:
        log(f"❌ Erro ao vincular arquivos ao repositório: {str(e)}")
        raise Exception(
            f"Erro ao vincular arquivos ao repositório: {str(e)} - sem fallback")


async def main():
    """
    MAIN DE EMISSÃO DE CARNÊS: Execução completa do fluxo
    """
    parser = argparse.ArgumentParser(
        description='RPA Sienge - Emissão de Carnês',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Fluxo de execução:
1. Buscar contratos REPARCELADOS no banco
2. Carregar dados da planilha base de cálculo  
3. Associar contratos com dados da planilha
4. Verificar pendências IPTU e inadimplência
5. Filtrar contratos aptos
6. Executar geração de carnês via RPA
7. Vincular arquivos gerados aos contratos no banco

Exemplos de uso:
  python main_sienge_emissao_carnes.py                    # Execução completa
  python main_sienge_emissao_carnes.py --teste            # Modo teste
        '''
    )
    parser.add_argument('--teste', action='store_true',
                        help='Executar em modo teste usando planilha de teste')
    args = parser.parse_args()

    # Configurar modo teste se solicitado
    if args.teste:
        log("🧪 MODO TESTE ATIVADO: Usando planilha de teste")
        planilha_teste = os.getenv("PLANILHA_TESTE_HOM")
        if planilha_teste:
            os.environ["PLANILHA_CALCULO_ID"] = planilha_teste
            log(f"🔄 Redirecionado para planilha de teste: {planilha_teste}")
        else:
            log("⚠️ PLANILHA_TESTE_HOM não configurada, usando planilha de produção")
    else:
        log("🏭 MODO PRODUÇÃO: Usando planilha de produção")

    inicio_execucao = datetime.now()

    log("🎫 RPA SIENGE - EMISSÃO DE CARNÊS")
    log("🎯 Fluxo: REPARCELADO → CARNE_GERADO")
    log("📋 Conforme PDD Seção 10.2: Emissão de carnê + Geração de arquivos de remessa")
    log("=" * 60)

    try:
        arquivo_log_execucao, stdout_original, stderr_original = preparar_logs_execucao()

        # FASE 1: Buscar contratos reparcelados no banco
        contratos_reparcelados = await obter_contratos_reparcelados()

        if not contratos_reparcelados:
            log("✅ Nenhum contrato para processar. Execução concluída.")
            notificar_sucesso_simples(
                "✅ EMISSÃO DE CARNÊS",
                "Nenhum contrato com status REPARCELADO encontrado para processar."
            )
            return 0

        # FASE 2: Carregar dados da planilha
        dados_planilha = await carregar_dados_planilha_base_calculo()

        # FASE 3: Associar contratos com planilha
        contratos_associados, contratos_nao_encontrados = associar_contratos_com_planilha(
            contratos_reparcelados, dados_planilha)

        # ✅ NOTIFICAÇÃO INICIAL DETALHADA: Mostrar resultados da busca e associação
        # Usar HTML para formatação adequada no email
        mensagem_notificacao = f"<p><strong>📋 SELEÇÃO DE CONTRATOS PARA GERAÇÃO DE CARNÊS</strong></p>"
        mensagem_notificacao += f"<p>⚠️ <strong>ATENÇÃO:</strong> Os carnês e arquivos de remessa AINDA NÃO foram gerados.<br>"
        mensagem_notificacao += f"Os contratos abaixo foram SELECIONADOS e serão processados em seguida.</p>"
        mensagem_notificacao += f"<p><strong>Contratos encontrados para reparcelar:</strong> {len(contratos_reparcelados)}</p>"
        mensagem_notificacao += f"<p><strong>Carnês não encontrados:</strong> {len(contratos_nao_encontrados)}</p>"

        if contratos_nao_encontrados:
            mensagem_notificacao += f"<p><strong>Listar não gerados:</strong></p>"
            mensagem_notificacao += f"<ul style=\"margin: 10px 0; padding-left: 20px;\">"
            for i, contrato in enumerate(contratos_nao_encontrados, 1):
                codigo = contrato.get('Código Cliente', 'N/A')
                titulo = contrato.get('Titulo', 'N/A')
                cliente = contrato.get('Cliente', 'N/A')
                mensagem_notificacao += f"<li><strong>Contrato não encontrado na planilha</strong> - {cliente} (Código: {codigo}, Título: {titulo})</li>"
            mensagem_notificacao += f"</ul>"

        mensagem_notificacao += f"<p>📎 Verifique o anexo 'parcelas_esperadas.csv' para ver as 12 parcelas que serão geradas para cada contrato.</p>"

        # FASE 4: Verificar pendências e filtrar contratos aptos
        contratos_aptos, contratos_com_pendencias = filtrar_contratos_aptos(
            contratos_associados)

        # ✅ AGRUPAR CONTRATOS APTOS POR EMPRESA E MOSTRAR NOS LOGS
        log(f"\n📊 CONTRATOS ELEGÍVEIS PARA EMISSÃO DE CARNÊS (AGRUPADOS POR EMPRESA):")
        log("=" * 60)
        contratos_aptos_por_empresa = {}
        for contrato in contratos_aptos:
            dados_planilha = contrato.get('dados_planilha', {})
            empresa = dados_planilha.get('Empresa', 'SEM EMPRESA')
            if empresa not in contratos_aptos_por_empresa:
                contratos_aptos_por_empresa[empresa] = []
            contratos_aptos_por_empresa[empresa].append(contrato)

        for empresa, contratos_empresa in contratos_aptos_por_empresa.items():
            log(f"\n🏢 {empresa}: {len(contratos_empresa)} contrato(s) elegível(eis)")
            for i, contrato in enumerate(contratos_empresa, 1):
                codigo = contrato.get('Código Cliente', 'N/A')
                titulo = contrato.get('Titulo', 'N/A')
                cliente = contrato.get('Cliente', 'N/A')
                dados_planilha_contrato = contrato.get('dados_planilha', {})
                loteamento = dados_planilha_contrato.get('Loteamento', 'N/A')
                log(f"   {i}. {cliente} (Código: {codigo}, Título: {titulo}, Loteamento: {loteamento})")

        log(
            f"\n✅ Total de contratos elegíveis: {len(contratos_aptos)} em {len(contratos_aptos_por_empresa)} empresa(s)")

        # ✅ CALCULAR PARCELAS E CRIAR ARQUIVO COM TODAS AS PARCELAS ESPERADAS
        # Isso é feito DEPOIS de filtrar contratos aptos para incluir apenas os elegíveis
        arquivo_parcelas = None
        try:
            import json

            # Preparar dados das parcelas esperadas - CALCULAR AGORA
            # Usar apenas contratos aptos (elegíveis) para o arquivo de parcelas
            dados_parcelas = []
            for contrato in contratos_aptos:
                numero_titulo = contrato.get('Titulo', '')
                codigo_cliente = contrato.get('Código Cliente', '')
                cliente = contrato.get('Cliente', 'N/A')
                dados_planilha_contrato = contrato.get('dados_planilha', {})
                empresa = dados_planilha_contrato.get('Empresa', 'N/A')
                loteamento = dados_planilha_contrato.get('Loteamento', 'N/A')
                primeiro_vencimento = dados_planilha_contrato.get(
                    '1º vencimento carnê', '')

                # ✅ CALCULAR AS 12 PARCELAS AGORA (mesma lógica do loop)
                parcelas_esperadas = []
                if primeiro_vencimento:
                    try:
                        parcelas_esperadas = calcular_12_parcelas_esperadas(
                            primeiro_vencimento)
                        # Armazenar no contrato para usar depois no loop
                        contrato['parcelas_esperadas'] = parcelas_esperadas
                        contrato['primeiro_vencimento'] = primeiro_vencimento
                    except Exception as e:
                        log(
                            f"⚠️ Erro ao calcular parcelas para contrato {numero_titulo}: {str(e)}")
                        parcelas_esperadas = []
                        primeiro_vencimento = 'N/A'

                dados_parcelas.append({
                    "empresa": empresa,
                    "loteamento": loteamento,
                    "codigo_cliente": codigo_cliente,
                    "cliente": cliente,
                    "titulo": numero_titulo,
                    "primeiro_vencimento": primeiro_vencimento,
                    "parcelas_esperadas": parcelas_esperadas,
                    "total_parcelas": len(parcelas_esperadas)
                })

            # Salvar arquivo CSV com TODOS os contratos e TODAS as parcelas
            diretorio_outputs = Path("outputs/relatorios")
            diretorio_outputs.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_parcelas = diretorio_outputs / \
                f"parcelas_esperadas_{timestamp}.csv"

            # Criar CSV com estrutura: Empresa, Loteamento, Código Cliente, Cliente, Título, Primeiro Vencimento, Parcela 1, Parcela 2, ..., Parcela 12, Total Parcelas
            with open(arquivo_parcelas, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter=';')

                # Cabeçalho
                cabecalho = [
                    'Empresa',
                    'Loteamento',
                    'Código Cliente',
                    'Cliente',
                    'Título',
                    'Primeiro Vencimento',
                    'Parcela 1',
                    'Parcela 2',
                    'Parcela 3',
                    'Parcela 4',
                    'Parcela 5',
                    'Parcela 6',
                    'Parcela 7',
                    'Parcela 8',
                    'Parcela 9',
                    'Parcela 10',
                    'Parcela 11',
                    'Parcela 12',
                    'Total Parcelas'
                ]
                writer.writerow(cabecalho)

                # Dados
                for item in dados_parcelas:
                    parcelas = item.get('parcelas_esperadas', [])
                    # Garantir que sempre temos 12 parcelas (preencher com vazio se necessário)
                    parcelas_completas = parcelas + [''] * (12 - len(parcelas))

                    linha = [
                        item.get('empresa', ''),
                        item.get('loteamento', ''),
                        item.get('codigo_cliente', ''),
                        item.get('cliente', ''),
                        item.get('titulo', ''),
                        item.get('primeiro_vencimento', ''),
                    ] + parcelas_completas[:12] + [
                        item.get('total_parcelas', len(parcelas))
                    ]
                    writer.writerow(linha)

            log(f"📄 Arquivo de parcelas esperadas criado: {arquivo_parcelas}")
            log(f"   📊 Total de contratos: {len(dados_parcelas)}")
            log(f"   📊 Total de parcelas: {sum(len(d.get('parcelas_esperadas', [])) for d in dados_parcelas)}")

        except Exception as e:
            log(f"⚠️ Erro ao criar arquivo de parcelas esperadas: {str(e)}")
            # Não quebra o fluxo se falhar

        # ✅ SIMPLIFICAR NOTIFICAÇÃO INICIAL: Apenas resumos no email, detalhes no TXT
        mensagem_notificacao += f"<p><strong>Contratos elegíveis para emissão de carnê:</strong> {len(contratos_aptos)}</p>"
        if contratos_aptos_por_empresa:
            mensagem_notificacao += f"<p><strong>Resumo por empresa:</strong></p>"
            for empresa, contratos_empresa in contratos_aptos_por_empresa.items():
                mensagem_notificacao += f"<p style=\"margin: 5px 0;\"><strong>{empresa}:</strong> {len(contratos_empresa)} contrato(s)</p>"
            mensagem_notificacao += f"<p style=\"margin-top: 15px; color: #666; font-size: 0.9em;\">📎 Ver detalhamento completo no arquivo TXT anexo</p>"

        # ✅ GERAR ARQUIVO TXT COM DETALHAMENTO COMPLETO
        arquivo_detalhamento_txt = None
        try:
            diretorio_outputs = Path("outputs/relatorios")
            diretorio_outputs.mkdir(parents=True, exist_ok=True)
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_detalhamento_txt = diretorio_outputs / \
                f"detalhamento_contratos_elegiveis_{timestamp_str}.txt"

            with open(arquivo_detalhamento_txt, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(
                    "DETALHAMENTO COMPLETO - CONTRATOS ELEGÍVEIS PARA EMISSÃO DE CARNÊS\n")
                f.write("=" * 80 + "\n\n")
                f.write(
                    f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write(
                    f"Total de contratos elegíveis: {len(contratos_aptos)}\n\n")

                if contratos_aptos_por_empresa:
                    for empresa, contratos_empresa in contratos_aptos_por_empresa.items():
                        f.write("-" * 80 + "\n")
                        f.write(f"EMPRESA: {empresa}\n")
                        f.write(
                            f"Total de contratos: {len(contratos_empresa)}\n")
                        f.write("-" * 80 + "\n\n")

                        for i, contrato in enumerate(contratos_empresa, 1):
                            codigo = contrato.get('Código Cliente', 'N/A')
                            titulo = contrato.get('Titulo', 'N/A')
                            cliente = contrato.get('Cliente', 'N/A')
                            primeiro_venc = contrato.get(
                                'primeiro_vencimento_carne', 'N/A')

                            f.write(f"  {i}. Cliente: {cliente}\n")
                            f.write(f"     Código Cliente: {codigo}\n")
                            f.write(f"     Título: {titulo}\n")
                            f.write(
                                f"     Primeiro Vencimento: {primeiro_venc}\n")

                            # Listar parcelas esperadas
                            parcelas = contrato.get('parcelas_esperadas', [])
                            if parcelas:
                                f.write(
                                    f"     Parcelas Esperadas ({len(parcelas)}):\n")
                                for j, parcela in enumerate(parcelas, 1):
                                    f.write(f"       {j}. {parcela}\n")

                            f.write("\n")

            log(
                f"📄 Arquivo de detalhamento criado: {arquivo_detalhamento_txt}")

        except Exception as e:
            log(f"⚠️ Erro ao criar arquivo de detalhamento: {str(e)}")
            arquivo_detalhamento_txt = None

        # Enviar notificação inicial com todas as informações (incluindo contratos elegíveis)
        from core.notificacoes_simples import notificar_sucesso
        anexos = []
        if arquivo_parcelas and arquivo_parcelas.exists():
            anexos.append(str(arquivo_parcelas))
        if arquivo_detalhamento_txt and arquivo_detalhamento_txt.exists():
            anexos.append(str(arquivo_detalhamento_txt))
        notificar_sucesso(
            nome_rpa="RPA Sienge - Emissão Carnês",
            tempo_execucao="-",
            resultados={
                "titulo": "🚀 EMISSÃO DE CARNÊS INICIADA - CONTRATOS SELECIONADOS",
                "mensagem": mensagem_notificacao,
                "caminhos_anexos": anexos
            }
        )

        # Inicializar RPA Sienge
        log(f"\n🤖 INICIALIZANDO RPA SIENGE...")
        headless = False  # Browser visível para acompanhar o processo
        rpa = RPAEmissaoCarneSienge(headless=headless)
        await rpa.inicializar()

        # Carregar credenciais e fazer login
        credenciais = await carregar_credenciais_sienge()
        rpa._configurar_credenciais(credenciais)
        await rpa._fazer_login_sienge()
        log("✅ Login no Sienge realizado com sucesso")

        # FASE 5: Executar geração de carnês
        resultado_carnes = await executar_fase_geracao_carnes(rpa, contratos_aptos)

        # Finalizar RPA
        await rpa.finalizar()

        # ✅ NOTA: Atualização do último reajuste será executada via cron separadamente
        log("ℹ️ Atualização do último reajuste será executada via cron separadamente")

        # ✅ FASE 6 REMOVIDA: O RPA já vincula os arquivos ao banco automaticamente
        # resultado_vinculacao = await vincular_arquivos_gerados_banco(resultado_carnes)

        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        # Processar resultados
        contratos_processados = resultado_carnes.get(
            "contratos_processados", 0)
        contratos_erro = resultado_carnes.get("contratos_erro", 0)
        # contratos_vinculados = resultado_vinculacao.get("contratos_vinculados", 0)
        contratos_vinculados = contratos_processados  # RPA já vincula automaticamente

        log(f"\n🎉 EMISSÃO DE CARNÊS CONCLUÍDA COM SUCESSO!")
        log(f"⏱️ Duração: {duracao}")
        log(
            f"📋 Contratos reparcelados encontrados: {len(contratos_reparcelados)}")
        log(
            f"🔗 Contratos associados com planilha: {len(contratos_associados)}")
        log(f"✅ Contratos aptos: {len(contratos_aptos)}")
        log(f"🎫 Carnês processados: {contratos_processados}")
        log(f"❌ Contratos com erro: {contratos_erro}")
        log(f"🔗 Contratos vinculados ao banco: {contratos_vinculados}")

        carnês_gerados = resultado_carnes.get("carnês_gerados", [])
        # ✅ LOG FINAL: CONTRATOS GERADOS AGRUPADOS POR EMPRESA
        log(f"\n📊 CONTRATOS COM CARNÊ GERADOS (AGRUPADOS POR EMPRESA):")
        log("=" * 60)
        contratos_gerados_por_empresa_log = {}
        for carne in carnês_gerados:
            empresa = carne.get("empresa", "SEM EMPRESA")
            contratos_titulos = carne.get("contratos", [])
            if empresa not in contratos_gerados_por_empresa_log:
                contratos_gerados_por_empresa_log[empresa] = []
            contratos_gerados_por_empresa_log[empresa].extend(
                contratos_titulos)

        for empresa, titulos in contratos_gerados_por_empresa_log.items():
            log(f"\n🏢 {empresa}: {len(titulos)} carnê(s) gerado(s)")
            # Limitar a 10 para não sobrecarregar
            for i, titulo in enumerate(titulos[:10], 1):
                log(f"   {i}. Título: {titulo}")
            if len(titulos) > 10:
                log(f"   ... e mais {len(titulos) - 10} carnê(s)")

        # Gerar relatório HTML - ajustar para template existente
        empresas_processadas = resultado_carnes.get("empresas_processadas", 0)
        estatisticas = {
            'total_empresas': empresas_processadas,
            'carnes_sucesso': contratos_processados,
            'carnes_erro': contratos_erro,
            'total_contratos': len(contratos_aptos),
            'contratos_reparcelados': len(contratos_reparcelados),
            'contratos_associados': len(contratos_associados),
            'contratos_nao_encontrados': len(contratos_nao_encontrados),
            'contratos_aptos': len(contratos_aptos),
            'contratos_vinculados': contratos_vinculados,
            'carnês_gerados': carnês_gerados,  # ✅ LISTA DE CARNÊS PARA ANEXO
            'duracao': str(duracao)
        }

        html_relatorio = templates_relatorios.relatorio_carnes(estatisticas)

        # Salvar relatório HTML
        diretorio_relatorios = Path("outputs/relatorios")
        diretorio_relatorios.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_html = diretorio_relatorios / \
            f"relatorio_emissao_carnes_{timestamp}.html"

        with open(arquivo_html, 'w', encoding='utf-8') as f:
            f.write(html_relatorio)

        log(f"📄 Relatório HTML salvo: {arquivo_html}")

        # ✅ PREPARAR MENSAGEM FINAL COM LAYOUT SOLICITADO
        contratos_nao_gerados_final = []

        # Adicionar contratos não encontrados na planilha
        for contrato in contratos_nao_encontrados:
            contratos_nao_gerados_final.append({
                "contrato": contrato,
                "motivo": "Contrato não encontrado na planilha"
            })

        # Adicionar contratos com pendências
        for item in contratos_com_pendencias:
            contratos_nao_gerados_final.append({
                "contrato": item["contrato"],
                "motivo": item["motivo"]
            })

        # Adicionar contratos que falharam na geração
        contratos_nao_gerados_final.extend(
            resultado_carnes.get("contratos_nao_gerados", []))

        # ✅ AGRUPAR CONTRATOS GERADOS POR EMPRESA PARA NOTIFICAÇÃO FINAL
        contratos_gerados_por_empresa = {}
        for carne in carnês_gerados:
            empresa = carne.get("empresa", "SEM EMPRESA")
            contratos_titulos = carne.get("contratos", [])
            if empresa not in contratos_gerados_por_empresa:
                contratos_gerados_por_empresa[empresa] = []
            contratos_gerados_por_empresa[empresa].extend(contratos_titulos)

        # Montar mensagem final com HTML para formatação adequada
        mensagem_final = f"<p><strong>📊 RELATÓRIO FINAL DE EMISSÃO DE CARNÊS</strong></p>"
        mensagem_final += f"<p><strong>Contratos reparcelados:</strong> {len(contratos_reparcelados)}</p>"
        mensagem_final += f"<p><strong>Contratos com carnê gerados:</strong> {contratos_processados}</p>"
        mensagem_final += f"<p><strong>Carnês não gerados:</strong> {len(contratos_nao_gerados_final)}</p>"

        # ✅ SIMPLIFICAR NOTIFICAÇÃO FINAL: Apenas resumos no email, detalhes no TXT
        if contratos_gerados_por_empresa:
            mensagem_final += f"<p><strong>Contratos com carnê gerados (resumo por empresa):</strong></p>"
            for empresa, titulos in contratos_gerados_por_empresa.items():
                mensagem_final += f"<p style=\"margin: 5px 0;\"><strong>{empresa}:</strong> {len(titulos)} carnê(s) gerado(s)</p>"

        if contratos_nao_gerados_final:
            mensagem_final += f"<p style=\"margin-top: 15px;\"><strong>Carnês não gerados:</strong> {len(contratos_nao_gerados_final)}</p>"
            mensagem_final += f"<p style=\"margin-top: 10px; color: #666; font-size: 0.9em;\">📎 Ver detalhamento completo no arquivo TXT anexo</p>"

        mensagem_final += f"<p style=\"margin-top: 15px;\">⏱️ <strong>Duração:</strong> {duracao}</p>"

        # ✅ GERAR ARQUIVO TXT COM DETALHAMENTO COMPLETO DA NOTIFICAÇÃO FINAL
        arquivo_detalhamento_final_txt = None
        try:
            diretorio_outputs = Path("outputs/relatorios")
            diretorio_outputs.mkdir(parents=True, exist_ok=True)
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_detalhamento_final_txt = diretorio_outputs / \
                f"detalhamento_final_emissao_carnes_{timestamp_str}.txt"

            with open(arquivo_detalhamento_final_txt, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(
                    "DETALHAMENTO COMPLETO - RELATÓRIO FINAL DE EMISSÃO DE CARNÊS\n")
                f.write("=" * 80 + "\n\n")
                f.write(
                    f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write(f"Duração: {duracao}\n\n")

                f.write(
                    f"Contratos reparcelados: {len(contratos_reparcelados)}\n")
                f.write(
                    f"Contratos com carnê gerados: {contratos_processados}\n")
                f.write(
                    f"Carnês não gerados: {len(contratos_nao_gerados_final)}\n\n")

                # Detalhamento de contratos gerados por empresa
                if contratos_gerados_por_empresa:
                    f.write("=" * 80 + "\n")
                    f.write(
                        "CONTRATOS COM CARNÊ GERADOS (DETALHAMENTO POR EMPRESA)\n")
                    f.write("=" * 80 + "\n\n")

                    for empresa, titulos in contratos_gerados_por_empresa.items():
                        f.write("-" * 80 + "\n")
                        f.write(f"EMPRESA: {empresa}\n")
                        f.write(f"Total de carnês gerados: {len(titulos)}\n")
                        f.write("-" * 80 + "\n")
                        for i, titulo in enumerate(titulos, 1):
                            f.write(f"  {i}. Título: {titulo}\n")
                        f.write("\n")

                # Detalhamento de contratos não gerados
                if contratos_nao_gerados_final:
                    f.write("=" * 80 + "\n")
                    f.write("CARNÊS NÃO GERADOS (DETALHAMENTO COMPLETO)\n")
                    f.write("=" * 80 + "\n\n")

                    for i, item in enumerate(contratos_nao_gerados_final, 1):
                        contrato = item["contrato"]
                        motivo = item["motivo"]
                        codigo = contrato.get('Código Cliente', 'N/A')
                        titulo = contrato.get('Titulo', 'N/A')
                        cliente = contrato.get('Cliente', 'N/A')

                        f.write(f"{i}. Motivo: {motivo}\n")
                        f.write(f"   Cliente: {cliente}\n")
                        f.write(f"   Código Cliente: {codigo}\n")
                        f.write(f"   Título: {titulo}\n")
                        f.write("\n")

            log(
                f"📄 Arquivo de detalhamento final criado: {arquivo_detalhamento_final_txt}")

        except Exception as e:
            log(f"⚠️ Erro ao criar arquivo de detalhamento final: {str(e)}")
            arquivo_detalhamento_final_txt = None

        # Notificar sucesso
        from core.notificacoes_simples import notificar_sucesso

        anexos_final = [str(ARQUIVO_LOG_ATUAL), str(arquivo_html)]
        if arquivo_detalhamento_final_txt and arquivo_detalhamento_final_txt.exists():
            anexos_final.append(str(arquivo_detalhamento_final_txt))

        resultados_notificacao = {
            "titulo": "🎉 RPA SIENGE: Emissão de carnês concluída",
            "mensagem": mensagem_final,
            "caminhos_anexos": anexos_final
        }

        notificar_sucesso(
            nome_rpa="RPA Sienge - Emissão Carnês",
            tempo_execucao=str(duracao),
            resultados=resultados_notificacao
        )

        return 0  # Sucesso

    except Exception as e:
        fim_execucao = datetime.now()
        duracao = fim_execucao - inicio_execucao

        log(f"\n❌ EMISSÃO DE CARNÊS FALHOU")
        log(f"⏱️ Duração: {duracao}")
        log(f"❌ Erro: {str(e)}")

        # Gerar relatório de erro com contratos não encontrados
        detalhes_erro = str(e)
        if 'contratos_nao_encontrados' in locals():
            if contratos_nao_encontrados:
                detalhes_erro += f"\n\n📋 CONTRATOS NÃO ENCONTRADOS NA PLANILHA ({len(contratos_nao_encontrados)}):\n"
                for contrato in contratos_nao_encontrados:
                    codigo = contrato.get('Código Cliente', 'N/A')
                    titulo = contrato.get('Titulo', 'N/A')
                    cliente = contrato.get('Cliente', 'N/A')
                    detalhes_erro += f"   ❌ {cliente} (Código: {codigo}, Título: {titulo})\n"

        html_erro = templates_relatorios.relatorio_erro(
            "RPA Sienge - Emissão de Carnês",
            detalhes_erro,
            f"Duração até erro: {duracao}"
        )

        # Salvar relatório de erro
        diretorio_relatorios = Path("outputs/relatorios")
        diretorio_relatorios.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_html_erro = diretorio_relatorios / \
            f"erro_emissao_carnes_{timestamp}.html"

        with open(arquivo_html_erro, 'w', encoding='utf-8') as f:
            f.write(html_erro)

        log(f"📄 Relatório de erro HTML salvo: {arquivo_html_erro}")

        # Notificar erro
        from core.notificacoes_simples import notificar_sucesso

        resultados_erro = {
            "titulo": "❌ RPA SIENGE: Emissão de carnês falhou",
            "mensagem": f"Erro: {str(e)} | Duração: {duracao}",
            "caminhos_anexos": [str(ARQUIVO_LOG_ATUAL)]
        }

        notificar_sucesso(
            nome_rpa="RPA Sienge - Emissão Carnês",
            tempo_execucao=str(duracao),
            resultados=resultados_erro
        )

        return 1  # Falha

    finally:
        try:
            arquivo_log_execucao.close()
        except Exception:
            pass

        if 'stdout_original' in locals() and 'stderr_original' in locals():
            sys.stdout = stdout_original
            sys.stderr = stderr_original
            try:
                arquivo_log_execucao.close()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log("Execução interrompida pelo usuário.")
        sys.exit(130)
    except Exception as e:
        log(f"Erro fatal: {e}")
        sys.exit(1)
